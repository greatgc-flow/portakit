#requires -version 2.0
<#
Manual same-host Aegis menu. No background polling or automatic arrangement.
The default data folder is the sibling aegis-data directory, outside the tool.
Use -DataDirectory for another approved local folder. Existing data is preserved.
Library loads functions only for development checks; it does not run the menu.
#>
param([string]$DataDirectory='', [switch]$Library)

function Get-AegisMenuLocalPath {
    param([string]$Path)
    if ([string]::IsNullOrEmpty($Path) -or $Path.Length -gt 1024 -or $Path -match '[\x00-\x1f"*?]' -or $Path.StartsWith('\\') -or $Path.StartsWith('//')) { throw 'Use a literal local filesystem path.' }
    if ($Path -match ':' -and $Path -notmatch '\A[A-Za-z]:[\\/][^:]*\z') { throw 'Use a local absolute drive path, not a provider or stream path.' }
    if (-not [IO.Path]::IsPathRooted($Path)) {
        $location=Get-Location
        if ($location.Provider.Name -ne 'FileSystem') { throw 'Relative paths require a filesystem working directory.' }
        $Path=[IO.Path]::Combine($location.ProviderPath,$Path)
    }
    return [IO.Path]::GetFullPath($Path)
}

function Assert-AegisMenuPlainPath {
    param([string]$Path)
    $cursor=Get-AegisMenuLocalPath $Path
    while (-not [string]::IsNullOrEmpty($cursor)) {
        try {
            $attributes=[IO.File]::GetAttributes($cursor)
            if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Symbolic links, junctions and reparse paths are not supported.' }
        } catch [IO.FileNotFoundException] { } catch [IO.DirectoryNotFoundException] { }
        $parent=[IO.Path]::GetDirectoryName($cursor)
        if ([string]::Equals($cursor,$parent,[StringComparison]::OrdinalIgnoreCase)) { break }
        $cursor=$parent
    }
}

function Get-AegisMenuDataDirectory {
    param([string]$PackageDirectory,[string]$Requested='')
    $package=Get-AegisMenuLocalPath $PackageDirectory
    if ([string]::IsNullOrEmpty($Requested)) { $Requested=[IO.Path]::Combine([IO.Path]::GetDirectoryName($package),'aegis-data') }
    $data=Get-AegisMenuLocalPath $Requested
    $prefix=$package.TrimEnd([char[]]@([IO.Path]::DirectorySeparatorChar,[IO.Path]::AltDirectorySeparatorChar))+[IO.Path]::DirectorySeparatorChar
    if ([string]::Equals($data,$package,[StringComparison]::OrdinalIgnoreCase) -or $data.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'DataDirectory must be outside the Aegis program folder so update/remove cannot delete user data.' }
    Assert-AegisMenuPlainPath $package
    Assert-AegisMenuPlainPath $data
    if ([IO.File]::Exists($data)) { throw 'DataDirectory is a file.' }
    return $data
}

function Initialize-AegisMenuData {
    param([string]$PackageDirectory,[string]$Requested='')
    $data=Get-AegisMenuDataDirectory $PackageDirectory $Requested
    $template=[IO.Path]::Combine($PackageDirectory,'Aegis.Processes.csv')
    $config=[IO.Path]::Combine($data,'Aegis.Processes.csv')
    $profiles=[IO.Path]::Combine($data,'profiles')
    foreach ($path in @($template,$config,$profiles)) { Assert-AegisMenuPlainPath $path }
    if (-not [IO.File]::Exists($template) -or (New-Object IO.FileInfo $template).Length -gt 262144) { throw 'The packaged CSV template is missing or too large.' }
    if ([IO.Directory]::Exists($config) -or [IO.File]::Exists($profiles)) { throw 'User data file/directory types do not match the expected layout.' }
    try {
        [void][IO.Directory]::CreateDirectory($data)
        [void][IO.Directory]::CreateDirectory($profiles)
        Assert-AegisMenuPlainPath $data
        Assert-AegisMenuPlainPath $profiles
        if (-not [IO.File]::Exists($config)) {
            $temporary=[IO.Path]::Combine($data,('.aegis-config-'+[Guid]::NewGuid().ToString('N')+'.tmp'))
            try {
                [IO.File]::Copy($template,$temporary,$false)
                Assert-AegisMenuPlainPath $config
                # Move does not replace a concurrently created destination.
                try { [IO.File]::Move($temporary,$config) }
                catch [IO.IOException] { if (-not [IO.File]::Exists($config)) { throw } }
            } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
        }
        Assert-AegisMenuPlainPath $config
    } catch { throw ('Cannot prepare Aegis user data. Use -DataDirectory with an approved writable local folder. '+$_.Exception.Message) }
    return @{DataDirectory=$data;ConfigPath=$config;ProfileDirectory=$profiles}
}

function Enter-AegisMenuLock {
    param([string]$Name='Local\PortaKit_Aegis_Menu_v1')
    $handle=New-Object Threading.Mutex ($false,$Name)
    $owned=$false
    try {
        try { $owned=$handle.WaitOne(0,$false) } catch [Threading.AbandonedMutexException] { $owned=$true }
        if (-not $owned) { throw 'Another Aegis menu is already open in this Windows session. Return to that menu.' }
        return $handle
    } catch { if ($owned) { [void]$handle.ReleaseMutex() };$handle.Close();throw }
}

function Exit-AegisMenuLock {
    param($Handle)
    if ($null -ne $Handle) { try { [void]$Handle.ReleaseMutex() } finally { $Handle.Close() } }
}

function Test-AegisMenuPending {
    param([hashtable]$Session)
    if ($null -ne $global:AegisPendingMoves -and @($global:AegisPendingMoves).Count -gt 0) { return $true }
    if ($null -ne $Session.LastReport -and ([int]$Session.LastReport.ExitCode -eq 3 -or [int]$Session.LastReport.PendingCount -gt 0)) { return $true }
    return $false
}

function New-AegisMenuSession {
    param([string]$PackageDirectory,[string]$Requested='', [scriptblock]$EngineInvoker=$null,[scriptblock]$EditorInvoker=$null)
    $package=Get-AegisMenuLocalPath $PackageDirectory
    $engine=[IO.Path]::Combine($package,'Aegis.ps1')
    Assert-AegisMenuPlainPath $engine
    if (-not [IO.File]::Exists($engine)) { throw 'Aegis.ps1 is missing beside the menu.' }
    $data=Initialize-AegisMenuData $package $Requested
    if ($null -eq $EngineInvoker) { $EngineInvoker={param($Path,$Parameters) & $Path @Parameters} }
    if ($null -eq $EditorInvoker) {
        $EditorInvoker={param($Path)
            $editor=[IO.Path]::Combine([Environment]::GetFolderPath([Environment+SpecialFolder]::System),'notepad.exe')
            if (-not [IO.File]::Exists($editor)) { throw 'Windows Notepad is unavailable. Edit the displayed CSV path in your approved text editor.' }
            Start-Process -FilePath $editor -ArgumentList ('"'+$Path+'"')
        }
    }
    return @{PackageDirectory=$package;EnginePath=$engine;DataDirectory=$data.DataDirectory;ConfigPath=$data.ConfigPath;ProfileDirectory=$data.ProfileDirectory;EngineInvoker=$EngineInvoker;EditorInvoker=$EditorInvoker;LastReport=$null}
}

function Get-AegisMenuProfilePath {
    param([hashtable]$Session,[string]$Name='home')
    if ($Name -cnotmatch '\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\z' -or $Name -match '\A(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])\z') { throw 'Profile name must use 1-64 ASCII letters, digits, underscore or hyphen, and cannot be a Windows device name.' }
    $path=[IO.Path]::Combine($Session.ProfileDirectory,($Name+'.xml'))
    Assert-AegisMenuPlainPath $path
    if ([IO.Directory]::Exists($path)) { throw 'Profile destination is a directory.' }
    return $path
}

function Invoke-AegisMenuAction {
    param([hashtable]$Session,[string]$Action,[string[]]$RuleIds=@(),[int]$Tier=0,[string]$GroupId='',
          [switch]$Preview,[switch]$KeepSize,[string]$ProfileName='home',[switch]$OverwriteProfile)
    if (@('Inspect','Arrange','Return','Reflow','Undo','SaveProfile','LoadProfile','EditConfig','Quit') -notcontains $Action) { throw 'Unknown menu action.' }
    if (Test-AegisMenuPending $Session) {
        if ($Action -ne 'Inspect') { throw 'A move is still unconfirmed. Keep this session open and use Inspect; closing or restarting does not cancel the OS request.' }
    }
    if ($Action -eq 'Quit') { return @{Status='Quit';ExitCode=0;PendingCount=0} }
    Assert-AegisMenuPlainPath $Session.EnginePath
    Assert-AegisMenuPlainPath $Session.ConfigPath
    if ($Action -eq 'EditConfig') {
        & $Session.EditorInvoker $Session.ConfigPath | Out-Null
        return @{Status='ConfigOpened';ExitCode=0;PendingCount=0}
    }
    $parameters=@{Action=$Action;PassThru=$true}
    if ($Action -eq 'SaveProfile' -or $Action -eq 'LoadProfile') {
        $path=Get-AegisMenuProfilePath $Session $ProfileName
        if ($Action -eq 'SaveProfile' -and [IO.File]::Exists($path) -and -not $OverwriteProfile) { throw 'A saved layout already has this name. Confirm replacement or use another name.' }
        $parameters.ProfilePath=$path
    } else {
        if ($Action -eq 'Reflow' -or $null -eq $global:AegisLayoutProfile) { $parameters.ConfigPath=$Session.ConfigPath }
        if ($RuleIds.Count -gt 0) { $parameters.RuleIds=$RuleIds }
        if ($Tier -ne 0) { $parameters.Tier=$Tier }
        if (-not [string]::IsNullOrEmpty($GroupId)) { $parameters.GroupId=$GroupId }
        if ($Preview) { $parameters.Preview=$true }
        if ($KeepSize) { $parameters.KeepSize=$true }
    }
    $report=& $Session.EngineInvoker $Session.EnginePath $parameters
    if ($report -isnot [System.Collections.IDictionary] -or -not $report.Contains('ExitCode') -or -not $report.Contains('Status')) { throw 'The Aegis engine did not return a status report. Keep this session open and use Inspect.' }
    $Session.LastReport=$report
    return $report
}

function Show-AegisMenuResult {
    param($Report)
    Write-Host ('Result: '+$Report.Status+' | exit='+$Report.ExitCode+' | pending='+$Report.PendingCount)
    if (-not [string]::IsNullOrEmpty([string]$Report.Detail)) { Write-Host $Report.Detail }
    $priority=New-Object Collections.ArrayList;$ordinary=New-Object Collections.ArrayList
    $routineCount=0;$relevantCount=0
    foreach ($item in @($Report.Items)) {
        if ($null -eq $item) { continue }
        if ($item.Status -eq 'Skipped' -and @('HiddenWindow','SystemWindowClass','OwnHostWindow') -contains $item.Reason) { $routineCount++;continue }
        $relevantCount++
        $important=(@('Failed','Uncertain','Deferred','Disappeared','Blocked') -contains $item.Status -or $item.Reason -eq 'AccessDenied' -or [int]$item.ErrorCode -ne 0)
        if ($important) { if ($priority.Count -lt 40) { [void]$priority.Add($item) } }
        elseif ($ordinary.Count -lt 40) { [void]$ordinary.Add($item) }
    }
    $selected=@(($priority.ToArray()+$ordinary.ToArray()) | Select-Object -First 40)
    $rows=@(foreach ($item in $selected) {
        New-Object PSObject -Property @{RuleId=$item.RuleId;Tier=$item.Tier;GroupId=$item.GroupId;ProcessName=$item.ProcessName;Status=$item.Status;Reason=$item.Reason;ErrorCode=$item.ErrorCode}
    })
    if ($rows.Count -gt 0) { Write-Host ($rows | Format-Table RuleId,Tier,GroupId,ProcessName,Status,Reason,ErrorCode -AutoSize | Out-String -Width 220) }
    if ($routineCount -gt 0) { Write-Host ('Routine hidden/system/own-host rows omitted: '+$routineCount+'.') }
    if ($relevantCount -gt $rows.Count) { Write-Host ('Additional relevant rows omitted: '+($relevantCount-$rows.Count)+'. Full details: $global:AegisLastResult.Items') }
    foreach ($warning in @($Report.Warnings)) { if ($null -ne $warning) { Write-Warning ([string]$warning) } }
}

function Read-AegisMenuInput {
    param([string]$Prompt)
    try { $value=Read-Host $Prompt -ErrorAction Stop }
    catch { throw (New-Object IO.EndOfStreamException 'Console input is unavailable. The menu is closing.') }
    if ($null -eq $value) { throw (New-Object IO.EndOfStreamException 'Console input ended. The menu is closing.') }
    return [string]$value
}

function Read-AegisMenuSelection {
    param([switch]$WholeGroups)
    $ids=@()
    if (-not $WholeGroups) {
        $text=(Read-AegisMenuInput 'Rule IDs (comma separated; Enter = all in scope)').Trim()
        if ($text -ne '') { $ids=@($text.Split(',') | ForEach-Object {$_.Trim()});if (@($ids | Where-Object {$_ -eq ''}).Count -gt 0) { throw 'Empty rule ID in selection.' } }
    }
    $tierText=(Read-AegisMenuInput 'Tier (1/2/3; Enter = all)').Trim()
    [int]$selectedTier=0
    if ($tierText -ne '' -and (-not [int]::TryParse($tierText,[ref]$selectedTier) -or $selectedTier -lt 1 -or $selectedTier -gt 3)) { throw 'Tier must be 1, 2 or 3.' }
    $group=(Read-AegisMenuInput 'Group ID (Enter = all in scope)').Trim()
    return @{RuleIds=$ids;Tier=$selectedTier;GroupId=$group}
}

function Invoke-AegisMenuLoop {
    param([hashtable]$Session)
    $blankCommands=0
    while ($true) {
        Write-Host ''
        Write-Host '1 Inspect  2 Preview Arrange  3 Arrange  4 Return  5 Return KeepSize'
        Write-Host '6 Reflow (scope / preview choice)  7 Undo  8 Edit CSV  9 Save profile  L Load profile  Q Quit'
        try {
            $choice=(Read-AegisMenuInput 'Choose').Trim().ToUpperInvariant()
            if ($choice -eq '') {
                $blankCommands++
                if ($blankCommands -ge 3) { Write-Warning 'Three empty commands received. Closing the menu to avoid an input retry loop.';break }
                Write-Host 'Enter a displayed command. Three consecutive empty commands close this menu.'
                continue
            }
            $blankCommands=0
            $request=@{Session=$session};$selected=@{}
            if (@('4','5','6','7') -contains $choice) {
                $selected=Read-AegisMenuSelection -WholeGroups:($choice -eq '6')
                foreach ($key in $selected.Keys) {$request[$key]=$selected[$key]}
            }
            switch ($choice) {
                '1' {$request.Action='Inspect'}
                '2' {$request.Action='Arrange';$request.Preview=$true}
                '3' {$request.Action='Arrange'}
                '4' {$request.Action='Return'}
                '5' {$request.Action='Return';$request.KeepSize=$true}
                '6' {
                    $request.Action='Reflow'
                    Write-Host 'Reflow reloads the CSV and changes saved homes in the selected scope.'
                    $mode=(Read-AegisMenuInput 'P = preview, A = apply (Enter = preview)').Trim().ToUpperInvariant()
                    if ($mode -ne '' -and $mode -ne 'P' -and $mode -ne 'A') { throw 'Choose P or A.' }
                    $request.Preview=($mode -ne 'A')
                }
                '7' {$request.Action='Undo'}
                '8' {$request.Action='EditConfig';Write-Host 'After editing, use Reflow to apply changed rules. Return keeps the stored policy.'}
                '9' {$request.Action='SaveProfile'}
                'L' {$request.Action='LoadProfile'}
                'Q' {$request.Action='Quit'}
                default {throw 'Choose one of the displayed commands.'}
            }
            if (@('SaveProfile','LoadProfile') -contains $request.Action) {
                $name=(Read-AegisMenuInput 'Profile name (Enter = home)').Trim();if ($name -eq '') {$name='home'}
                $request.ProfileName=$name
                $target=Get-AegisMenuProfilePath $session $name
                if ($request.Action -eq 'SaveProfile' -and [IO.File]::Exists($target)) {
                    $confirm=(Read-AegisMenuInput 'Replace this saved layout? Type YES').Trim()
                    if ($confirm -cne 'YES') { throw 'Save cancelled; existing layout preserved.' }
                    $request.OverwriteProfile=$true
                }
            }
        } catch [IO.EndOfStreamException] { Write-Warning $_.Exception.Message;break }
        catch { Write-Warning $_.Exception.Message;continue }
        try {
            $report=Invoke-AegisMenuAction @request
            if ($report.Status -eq 'Quit') { break }
            Show-AegisMenuResult $report
        } catch { Write-Warning $_.Exception.Message }
    }
}

function Start-AegisMenu {
    param([string]$PackageDirectory,[string]$Requested='')
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::UserInteractive) { throw 'The menu requires an interactive Windows desktop.' }
    $lock=$null;$session=$null
    try {
        $lock=Enter-AegisMenuLock
        $session=New-AegisMenuSession $PackageDirectory $Requested
        Write-Host ('Aegis user data: '+$session.DataDirectory)
        Write-Host ('Process settings: '+$session.ConfigPath)
        Write-Host 'One PowerShell session holds homes, Undo and unconfirmed moves. No automatic arrangement.'
        try { Show-AegisMenuResult (Invoke-AegisMenuAction $session 'Inspect') }
        catch { Write-Warning $_.Exception.Message }
        Invoke-AegisMenuLoop $session
    } finally {
        try {
            if (($null -ne $global:AegisPendingMoves -and @($global:AegisPendingMoves).Count -gt 0) -or ($null -ne $session -and (Test-AegisMenuPending $session))) { Write-Warning 'This host is ending with unconfirmed OS moves. They were not cancelled; do not treat a restart as recovery.' }
        } finally { Exit-AegisMenuLock $lock }
    }
}

if ($Library) { return }
$menuPackage=Split-Path -Parent $MyInvocation.MyCommand.Path
Start-AegisMenu -PackageDirectory $menuPackage -Requested $DataDirectory
