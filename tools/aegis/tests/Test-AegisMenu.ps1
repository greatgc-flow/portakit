#requires -version 2.0
# Actual menu functions, synthetic engine/editor boundaries, no window mutations.
param([string]$MenuPath='', [string]$ProductPath='', [string]$ReportPath='')
$menuTestFolder=Split-Path -Parent $MyInvocation.MyCommand.Path
$menuPackage=Split-Path -Parent $menuTestFolder
if ($MenuPath -eq '') {$MenuPath=Join-Path $menuPackage 'Aegis.Menu.ps1'}
if ($ProductPath -eq '') {$ProductPath=Join-Path $menuPackage 'Aegis.ps1'}
. (Join-Path $menuTestFolder 'ReportPathSafety.ps1')
$ReportPath=Resolve-AegisHarnessReportPath $ReportPath $ProductPath $MyInvocation.MyCommand.Path $menuPackage @($MenuPath,(Join-Path $menuPackage 'Start-Aegis.cmd'))
$oldMenuPreference=$ErrorActionPreference;$ErrorActionPreference='Stop'
$menuResults=New-Object Collections.ArrayList
$menuFixtureRoot=Join-Path ([IO.Path]::GetTempPath()) ('aegis-menu-'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($menuFixtureRoot)
$savedMenuGlobals=@{}
foreach ($name in @('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult','AegisLastExitCode')) {
    $existing=Get-Variable -Name $name -Scope Global -ErrorAction SilentlyContinue
    $savedMenuGlobals[$name]=@{Exists=($null -ne $existing);Value=$null}
    if ($null -ne $existing) {$savedMenuGlobals[$name].Value=$existing.Value}
}
. $MenuPath -Library
function Assert-Menu {param([bool]$Value,[string]$Message) if (-not $Value) {throw $Message}}
function Reject-Menu {param([scriptblock]$Body) $rejected=$false;try {& $Body | Out-Null} catch {$rejected=$true};Assert-Menu $rejected 'Expected rejection did not occur.'}
function Case-Menu {param([string]$Id,[string]$Name,[scriptblock]$Body)
    $status='PASS';$detail=''
    try { & $Body | Out-Null } catch {$status='FAIL';$detail=$_.Exception.Message}
    [void]$menuResults.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
    Write-Host ($Id+' '+$status+' '+$Name+' '+$detail)
}
function Fixture-Menu {param([scriptblock]$Body)
    $directory=Join-Path $menuFixtureRoot ([Guid]::NewGuid().ToString('N'))
    $package=Join-Path $directory 'program';[void][IO.Directory]::CreateDirectory($package)
    [IO.File]::WriteAllText((Join-Path $package 'Aegis.ps1'),'# never executed; injected engine boundary')
    [IO.File]::WriteAllText((Join-Path $package 'Aegis.Processes.csv'),'Id,ProcessName'+"`r`n"+'terminal,putty'+"`r`n")
    $script:menuCalls=New-Object Collections.ArrayList;$script:menuEditorCalls=New-Object Collections.ArrayList
    $global:AegisLayoutProfile=$null;$global:AegisUndoState=$null;$global:AegisPendingMoves=@()
    $script:menuEngine={param($Path,$Parameters)
        $record=$Parameters.Clone();$record.HostId=$PID;[void]$script:menuCalls.Add($record)
        if ($Parameters.Action -eq 'Arrange' -and -not $Parameters.Preview) {
            $global:AegisLayoutProfile=@{Marker='same-host-home'};$global:AegisUndoState=@{Marker='same-host-undo'}
        }
        if ($Parameters.Action -eq 'Undo') {Assert-Menu ($global:AegisUndoState.Marker -eq 'same-host-undo') 'Undo state did not survive in the same host.'}
        return @{Status='Complete';ExitCode=0;PendingCount=0;Items=@();Warnings=@()}
    }
    $script:menuEditor={param($Path) [void]$script:menuEditorCalls.Add($Path)}
    $session=New-AegisMenuSession $package '' $script:menuEngine $script:menuEditor
    & $Body $session $package $directory
}
function Exercise-MenuInputEnd {
    param([hashtable]$Session,[string[]]$Prefix=@(),[string]$Failure='Throw')
    $script:menuPromptPrefix=$Prefix;$script:menuPromptFailure=$Failure;$script:menuReadCount=0
    $script:menuPromptWarnings=New-Object Collections.ArrayList
    function Write-Host {param($Object)}
    function Write-Warning {param($Message) [void]$script:menuPromptWarnings.Add([string]$Message)}
    function Read-Host {param([string]$Prompt,[string]$ErrorAction)
        $script:menuReadCount++
        if ($script:menuReadCount -le $script:menuPromptPrefix.Count) {return $script:menuPromptPrefix[$script:menuReadCount-1]}
        if ($script:menuReadCount -eq $script:menuPromptPrefix.Count+1) {
            if ($script:menuPromptFailure -eq 'Null') {return $null}
            throw 'Synthetic console input failure.'
        }
        return 'Q' # Bounds a broken implementation so the regression fails without hanging.
    }
    $global:AegisLayoutProfile=@{Marker='preserved-input-home'};$global:AegisUndoState=@{Marker='preserved-input-undo'}
    $storedHome=$global:AegisLayoutProfile;$storedUndo=$global:AegisUndoState
    Invoke-AegisMenuLoop $Session
    Assert-Menu ($script:menuReadCount -eq $Prefix.Count+1) 'Input failure/EOF retried the menu instead of ending once.'
    Assert-Menu ($script:menuCalls.Count -eq 0) 'An incomplete command reached the engine.'
    Assert-Menu ($script:menuPromptWarnings.Count -eq 1 -and $script:menuPromptWarnings[0] -match 'Console input') 'Terminal input warning was absent or repeated.'
    Assert-Menu ([object]::ReferenceEquals($storedHome,$global:AegisLayoutProfile) -and [object]::ReferenceEquals($storedUndo,$global:AegisUndoState)) 'Terminal input failure cleared saved state.'
}
function Hash-Menu {param([string]$Path)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {return [BitConverter]::ToString($hash.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace('-','').ToLowerInvariant()} finally {$hash.Clear()}
}
try {
    Case-Menu 'M01' 'Default data location follows the package, independent of working directory' {
        Fixture-Menu {param($s,$package,$directory)
            Push-Location $menuFixtureRoot
            try { $resolved=Get-AegisMenuDataDirectory $package '' } finally {Pop-Location}
            Assert-Menu ($resolved -eq (Join-Path $directory 'aegis-data')) 'Foreign working directory changed the default data location.'
            Assert-Menu ([IO.File]::Exists($s.ConfigPath) -and [IO.Directory]::Exists($s.ProfileDirectory)) 'Initial data layout missing.'
            Assert-Menu ($script:menuCalls.Count -eq 0) 'Preparing data invoked the window engine.'
        }
    }
    Case-Menu 'M02' 'Repeated startup preserves user CSV and saved profile bytes' {
        Fixture-Menu {param($s,$package,$directory)
            [IO.File]::WriteAllText($s.ConfigPath,'user-owned-config')
            $savedProfilePath=Join-Path $s.ProfileDirectory 'home.xml';[IO.File]::WriteAllText($savedProfilePath,'user-owned-profile')
            $again=New-AegisMenuSession $package '' $script:menuEngine $script:menuEditor
            Assert-Menu ([IO.File]::ReadAllText($again.ConfigPath) -eq 'user-owned-config') 'Startup overwrote existing CSV.'
            Assert-Menu ([IO.File]::ReadAllText($savedProfilePath) -eq 'user-owned-profile') 'Startup overwrote existing profile.'
            Assert-Menu ($script:menuCalls.Count -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Startup automatically loaded a profile or arranged windows.'
        }
    }
    Case-Menu 'M03' 'Data inside the installed program and unsafe paths are rejected before creation' {
        Fixture-Menu {param($s,$package,$directory)
            Reject-Menu {Initialize-AegisMenuData $package $package}
            $nested=Join-Path $package 'user-data';Reject-Menu {Initialize-AegisMenuData $package $nested}
            Assert-Menu (-not [IO.Directory]::Exists($nested)) 'Rejected data location was created.'
            $unc='\\server\share'
            Assert-Menu ($unc[0] -eq [char]92 -and $unc[1] -eq [char]92 -and $unc[2] -ne [char]92) 'UNC fixture does not start with exactly two backslashes.'
            $uncReason='';try {[void](Get-AegisMenuLocalPath $unc)} catch {$uncReason=$_.Exception.Message}
            Assert-Menu ($uncReason -eq 'Use a literal local filesystem path.') 'UNC was not rejected by the local-path guard.'
            foreach ($bad in @('//server/share','Env:\TEMP','name:stream','bad*path',('bad'+[char]10+'path'))) {Reject-Menu {Get-AegisMenuLocalPath $bad}}
        }
    }
    Case-Menu 'M04' 'Explicit user data location supports spaces and Unicode without command interpolation' {
        Fixture-Menu {param($s,$package,$directory)
            $target=Join-Path $directory '업무 설정 (A)'
            $custom=New-AegisMenuSession $package $target $script:menuEngine $script:menuEditor
            Assert-Menu ($custom.DataDirectory -eq $target -and [IO.File]::Exists($custom.ConfigPath)) 'Unicode/space data path failed.'
            [void](Invoke-AegisMenuAction $custom Inspect)
            Assert-Menu ($script:menuCalls[0].ConfigPath -eq $custom.ConfigPath) 'Configuration path changed when passed as an engine argument.'
        }
    }
    Case-Menu 'M05' 'Preview then Arrange Return Undo reuse one host and the saved home/undo state' {
        Fixture-Menu {param($s,$package,$directory)
            [void](Invoke-AegisMenuAction $s Arrange -Preview)
            Assert-Menu ($null -eq $global:AegisLayoutProfile -and $null -eq $global:AegisUndoState) 'Preview published a synthetic home or Undo.'
            [void](Invoke-AegisMenuAction $s Arrange)
            $storedHome=$global:AegisLayoutProfile
            [void](Invoke-AegisMenuAction $s Return -RuleIds terminal -Tier 2 -GroupId work -KeepSize)
            [void](Invoke-AegisMenuAction $s Undo)
            Assert-Menu ([object]::ReferenceEquals($storedHome,$global:AegisLayoutProfile)) 'Return lost/replaced same-host profile.'
            Assert-Menu (@($script:menuCalls | Where-Object {$_.HostId -ne $PID}).Count -eq 0) 'An engine action changed hosts.'
            Assert-Menu ($script:menuCalls[2].KeepSize -and $script:menuCalls[2].RuleIds[0] -eq 'terminal' -and $script:menuCalls[2].Tier -eq 2 -and $script:menuCalls[2].GroupId -eq 'work') 'Selection/KeepSize parameters lost.'
            Assert-Menu (-not $script:menuCalls[2].ContainsKey('ConfigPath')) 'Normal Return unexpectedly reloaded CSV policy.'
        }
    }
    Case-Menu 'M06' 'Reflow explicitly reloads CSV while normal stored-home actions preserve their policy' {
        Fixture-Menu {param($s,$package,$directory)
            [void](Invoke-AegisMenuAction $s Arrange)
            [IO.File]::WriteAllText($s.ConfigPath,'changed-csv')
            [void](Invoke-AegisMenuAction $s Inspect)
            [void](Invoke-AegisMenuAction $s Reflow -Tier 2 -GroupId work -Preview)
            Assert-Menu (-not $script:menuCalls[1].ContainsKey('ConfigPath')) 'Stored-home Inspect unexpectedly adopted changed CSV.'
            Assert-Menu ($script:menuCalls[2].ConfigPath -eq $s.ConfigPath -and $script:menuCalls[2].Preview) 'Reflow did not reload CSV or lost Preview.'
        }
    }
    Case-Menu 'M07' 'Unconfirmed moves block changes and normal quit until Inspect resolves them' {
        Fixture-Menu {param($s,$package,$directory)
            $global:AegisPendingMoves=@(@{Marker='pending'})
            foreach ($action in @('Arrange','Return','Reflow','Undo','SaveProfile','LoadProfile','EditConfig','Quit')) {Reject-Menu {Invoke-AegisMenuAction $s $action}}
            Assert-Menu ($script:menuCalls.Count -eq 0 -and $script:menuEditorCalls.Count -eq 0) 'Pending guard dispatched an action.'
            $s.EngineInvoker={param($Path,$Parameters) Assert-Menu ($Parameters.Action -eq 'Inspect') 'Unexpected pending action.';$global:AegisPendingMoves=@();return @{Status='Complete';ExitCode=0;PendingCount=0}}
            [void](Invoke-AegisMenuAction $s Inspect)
            Assert-Menu ((Invoke-AegisMenuAction $s Quit).Status -eq 'Quit') 'Quit did not resume after confirmed resolution.'
        }
    }
    Case-Menu 'M08' 'Pending report alone also prevents a false clean exit' {
        Fixture-Menu {param($s,$package,$directory)
            $s.LastReport=@{Status='BlockedPending';ExitCode=3;PendingCount=1}
            Reject-Menu {Invoke-AegisMenuAction $s Quit}
            [void](Invoke-AegisMenuAction $s Inspect)
            Assert-Menu ((Invoke-AegisMenuAction $s Quit).Status -eq 'Quit') 'Fresh confirmed report did not clear report-only pending guard.'
        }
    }
    Case-Menu 'M09' 'An engine exception preserves current home Undo and Pending for subsequent Inspect' {
        Fixture-Menu {param($s,$package,$directory)
            [void](Invoke-AegisMenuAction $s Arrange)
            $storedHome=$global:AegisLayoutProfile;$undo=$global:AegisUndoState
            $s.EngineInvoker={param($Path,$Parameters) $global:AegisPendingMoves=@(@{Marker='accepted'});throw 'injected boundary failure'}
            Reject-Menu {Invoke-AegisMenuAction $s Return}
            Assert-Menu ([object]::ReferenceEquals($storedHome,$global:AegisLayoutProfile) -and [object]::ReferenceEquals($undo,$global:AegisUndoState)) 'Exception cleared the working state.'
            Reject-Menu {Invoke-AegisMenuAction $s Quit}
            $s.EngineInvoker={param($Path,$Parameters) $global:AegisPendingMoves=@();return @{Status='Complete';ExitCode=0;PendingCount=0}}
            [void](Invoke-AegisMenuAction $s Inspect)
            Assert-Menu (-not (Test-AegisMenuPending $s)) 'Inspect did not recover the preserved session.'
        }
    }
    Case-Menu 'M10' 'Profile paths are confined to named local files and existing saves require explicit replacement' {
        Fixture-Menu {param($s,$package,$directory)
            foreach ($name in @('../outside','C:\elsewhere','CON','COM1','bad.name',([string][char]0x212a),('home'+[char]10))) {Reject-Menu {Get-AegisMenuProfilePath $s $name}}
            $savedProfilePath=Get-AegisMenuProfilePath $s home;[IO.File]::WriteAllText($savedProfilePath,'existing')
            Reject-Menu {Invoke-AegisMenuAction $s SaveProfile -ProfileName home}
            Assert-Menu ($script:menuCalls.Count -eq 0 -and [IO.File]::ReadAllText($savedProfilePath) -eq 'existing') 'Unconfirmed save overwrote or invoked engine.'
            [void](Invoke-AegisMenuAction $s SaveProfile -ProfileName home -OverwriteProfile)
            [void](Invoke-AegisMenuAction $s LoadProfile -ProfileName home)
            Assert-Menu ($script:menuCalls[0].ProfilePath -eq $savedProfilePath -and $script:menuCalls[1].ProfilePath -eq $savedProfilePath) 'Explicit Save/Load did not use the selected data file.'
        }
    }
    Case-Menu 'M11' 'Configuration editing dispatches only the exact user CSV to the editor boundary' {
        Fixture-Menu {param($s,$package,$directory)
            $before=[IO.File]::ReadAllBytes($s.ConfigPath)
            [void](Invoke-AegisMenuAction $s EditConfig)
            Assert-Menu ($script:menuCalls.Count -eq 0 -and $script:menuEditorCalls.Count -eq 1 -and $script:menuEditorCalls[0] -eq $s.ConfigPath) 'Edit launched the engine or changed the editor path.'
            Assert-Menu ([Convert]::ToBase64String($before) -eq [Convert]::ToBase64String([IO.File]::ReadAllBytes($s.ConfigPath))) 'Opening config changed its bytes.'
        }
    }
    Case-Menu 'M12' 'Reparse-linked data directories are rejected without writing through the link' {
        Fixture-Menu {param($s,$package,$directory)
            $target=Join-Path $directory 'target';$link=Join-Path $directory 'linked';[void][IO.Directory]::CreateDirectory($target)
            if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
                $cmd=[IO.Path]::Combine([Environment]::GetFolderPath([Environment+SpecialFolder]::System),'cmd.exe')
                & $cmd /d /c ('mklink /J "'+$link+'" "'+$target+'"') | Out-Null
            } else { & /bin/ln -s $target $link }
            Assert-Menu ($LASTEXITCODE -eq 0) 'Could not create isolated link fixture.'
            try { Reject-Menu {Initialize-AegisMenuData $package $link};Assert-Menu ([IO.Directory]::GetFileSystemEntries($target).Length -eq 0) 'Data was written through a link.' }
            finally { [IO.Directory]::Delete($link) }
        }
    }
    Case-Menu 'M13' 'Session mutex rejects another process and becomes available after release' {
        $name='AegisMenuTest_'+[Guid]::NewGuid().ToString('N')
        $child=Join-Path $menuFixtureRoot 'lock-probe.ps1'
        [IO.File]::WriteAllText($child,('param([string]$MenuPath,[string]$MutexName)'+"`r`n"+'. $MenuPath -Library'+"`r`n"+'$handle=$null;try {$handle=Enter-AegisMenuLock $MutexName;exit 0} catch {exit 6} finally {Exit-AegisMenuLock $handle}'))
        $runtime=Join-Path $PSHOME 'powershell.exe';if (-not [IO.File]::Exists($runtime)) {$runtime=Join-Path $PSHOME 'pwsh.exe'};if (-not [IO.File]::Exists($runtime)) {$runtime=Join-Path $PSHOME 'pwsh'}
        $handle=Enter-AegisMenuLock $name
        try {
            & $runtime -NoLogo -NoProfile -NonInteractive -File $child -MenuPath $MenuPath -MutexName $name
            Assert-Menu ($LASTEXITCODE -eq 6) 'Second host entered the same menu session.'
        } finally {Exit-AegisMenuLock $handle}
        & $runtime -NoLogo -NoProfile -NonInteractive -File $child -MenuPath $MenuPath -MutexName $name
        Assert-Menu ($LASTEXITCODE -eq 0) 'Session mutex remained held after exit.'
    }
    Case-Menu 'M14' 'Unknown actions and malformed engine reports cannot be reported as success' {
        Fixture-Menu {param($s,$package,$directory)
            Reject-Menu {Invoke-AegisMenuAction $s 'unexpected'}
            Assert-Menu ($script:menuCalls.Count -eq 0) 'Unknown action reached the engine.'
            $s.EngineInvoker={param($Path,$Parameters) return 'unexpected-output'}
            Reject-Menu {Invoke-AegisMenuAction $s Inspect}
            Assert-Menu ($null -eq $s.LastReport) 'Malformed report was accepted.'
        }
    }
    Case-Menu 'M15' 'The actual menu loop stops once on command input failure or null EOF' {
        foreach ($failure in @('Throw','Null')) {
            Fixture-Menu {param($s,$package,$directory) Exercise-MenuInputEnd -Session $s -Failure $failure}
        }
    }
    Case-Menu 'M16' 'Input loss at every subprompt ends once before dispatching a partial command' {
        foreach ($sample in @(@{Prefix=@('4')},@{Prefix=@('4','')},@{Prefix=@('4','','')},@{Prefix=@('6','','')},@{Prefix=@('9')},@{Prefix=@('9','home')})) {
            foreach ($failure in @('Throw','Null')) {
                Fixture-Menu {param($s,$package,$directory)
                    [IO.File]::WriteAllText((Get-AegisMenuProfilePath $s home),'existing saved profile')
                    Exercise-MenuInputEnd -Session $s -Prefix $sample.Prefix -Failure $failure
                }
            }
        }
    }
    Case-Menu 'M17' 'Empty EOF is bounded while one blank command and recoverable action errors keep the loop usable' {
        Fixture-Menu {param($s,$package,$directory)
            $script:menuReadCount=0
            function Write-Host {param($Object)}
            function Write-Warning {param($Message)}
            function Read-Host {param([string]$Prompt,[string]$ErrorAction) $script:menuReadCount++;if ($script:menuReadCount -gt 4) {return 'Q'};return ''}
            Invoke-AegisMenuLoop $s
            Assert-Menu ($script:menuReadCount -eq 3 -and $script:menuCalls.Count -eq 0) 'Repeated empty input was not bounded at three commands.'
        }
        Fixture-Menu {param($s,$package,$directory)
            $script:menuReadCount=0;$script:menuLoopWarnings=New-Object Collections.ArrayList
            function Write-Host {param($Object)}
            function Write-Warning {param($Message) [void]$script:menuLoopWarnings.Add([string]$Message)}
            function Read-Host {param([string]$Prompt,[string]$ErrorAction)
                $script:menuReadCount++;if ($script:menuReadCount -eq 1) {return ''};if ($script:menuReadCount -eq 2) {return '1'};return 'Q'
            }
            $s.EngineInvoker={param($Path,$Parameters) [void]$script:menuCalls.Add($Parameters);throw (New-Object IO.EndOfStreamException 'Synthetic engine read failure.')}
            Invoke-AegisMenuLoop $s
            Assert-Menu ($script:menuReadCount -eq 3 -and $script:menuCalls.Count -eq 1) 'One blank or an engine error terminated the usable command loop.'
            Assert-Menu ($script:menuLoopWarnings.Count -eq 1 -and $script:menuLoopWarnings[0] -match 'Synthetic engine') 'Recoverable engine failure was not reported once.'
        }
    }
    Case-Menu 'M18' 'Result display removes routine noise and prioritizes actionable rows within a reported forty-row bound' {
        $script:menuDisplay=New-Object Collections.ArrayList
        function Write-Host {param($Object) [void]$script:menuDisplay.Add([string]$Object)}
        $items=New-Object Collections.ArrayList
        for ($i=0;$i -lt 40;$i++) {[void]$items.Add(@{RuleId=('noise_'+$i);Status='Skipped';Reason=@('HiddenWindow','SystemWindowClass','OwnHostWindow')[$i%3]})}
        [void]$items.Add(@{RuleId='target_failed';Tier=2;GroupId='work';ProcessName='terminal';Status='Failed';Reason='AccessDenied';ErrorCode=5})
        $report=@{Status='Partial';ExitCode=1;PendingCount=0;Items=$items.ToArray();Warnings=@()}
        Show-AegisMenuResult $report
        $display=[string]::Join([Environment]::NewLine,[string[]]$script:menuDisplay.ToArray())
        Assert-Menu ($display -match 'target_failed' -and $display -match 'AccessDenied' -and $display -match 'Tier' -and $display -match 'GroupId' -and $display -match 'ErrorCode') 'The actionable target or diagnostic columns were hidden.'
        Assert-Menu ($display -notmatch 'noise_[0-9]' -and $display -match 'rows omitted: 40') 'Routine omissions were displayed or not counted.'
        Assert-Menu ($report.Items.Count -eq 41) 'Display filtering modified the full report.'
        $script:menuDisplay.Clear();$items.Clear()
        for ($i=0;$i -lt 41;$i++) {[void]$items.Add(@{RuleId=('normal_'+$i);Tier=1;GroupId='normal';ProcessName='terminal';Status='Moved';Reason='';ErrorCode=0})}
        foreach ($status in @('Failed','Uncertain')) {[void]$items.Add(@{RuleId=('target_'+$status.ToLowerInvariant());Tier=3;GroupId='work';ProcessName='terminal';Status=$status;Reason='MoveNotConfirmed';ErrorCode=0})}
        [void]$items.Add(@{RuleId='target_denied';Tier=2;GroupId='work';ProcessName='terminal';Status='Skipped';Reason='AccessDenied';ErrorCode=5})
        $report.Items=$items.ToArray();Show-AegisMenuResult $report
        $display=[string]::Join([Environment]::NewLine,[string[]]$script:menuDisplay.ToArray())
        Assert-Menu ($display -match 'target_failed' -and $display -match 'target_uncertain' -and $display -match 'target_denied') 'Actionable rows placed after forty successful rows were lost.'
        Assert-Menu ($display.IndexOf('target_failed') -lt $display.IndexOf('normal_0')) 'Actionable rows were not prioritized.'
        Assert-Menu ([regex]::Matches($display,'(?m)^\s*(normal_[0-9]+|target_failed|target_uncertain|target_denied)\s').Count -eq 40 -and $display -match 'Additional relevant rows omitted: 4') 'Visible rows exceeded forty or the omitted count was incorrect.'
    }
    $passed=@($menuResults | Where-Object {$_.Status -eq 'PASS'}).Count
    $summary=New-Object PSObject -Property @{Total=$menuResults.Count;Passed=$passed;Failed=($menuResults.Count-$passed);Cases=$menuResults.ToArray();ProductSha256=(Hash-Menu $ProductPath);MenuSha256=(Hash-Menu $MenuPath);EngineVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[string][Environment]::Version;ActualPS2Execution='NOT_RUN';ActualWindowsUI='NOT_RUN';Boundary='Actual menu loop with synthetic console/engine/editor; isolated filesystem and process mutex checks only'}
    if ($ReportPath -ne '') {$summary | Export-Clixml -Path $ReportPath -Depth 8}
    Write-Host ('Menu checks '+$passed+'/'+$menuResults.Count)
    if ($summary.Failed -gt 0) {throw ('Menu checks failed: '+$summary.Failed)}
} finally {
    foreach ($name in $savedMenuGlobals.Keys) {
        if ($savedMenuGlobals[$name].Exists) {Set-Variable -Name $name -Scope Global -Value $savedMenuGlobals[$name].Value}
        else {Remove-Variable -Name $name -Scope Global -ErrorAction SilentlyContinue}
    }
    if ([IO.Directory]::Exists($menuFixtureRoot)) {[IO.Directory]::Delete($menuFixtureRoot,$true)}
    $ErrorActionPreference=$oldMenuPreference
}
