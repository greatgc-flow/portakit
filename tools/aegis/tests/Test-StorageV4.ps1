#requires -version 2.0
param([string]$ScriptPath='', [string]$ReportPath='')
$testDirectory=Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($ScriptPath)) { $ScriptPath=Join-Path (Split-Path -Parent $testDirectory) 'Aegis.ps1' }
. (Join-Path $testDirectory 'ReportPathSafety.ps1')
$ReportPath=Resolve-AegisHarnessReportPath -Path $ReportPath -ProductPath $ScriptPath -HarnessPath $MyInvocation.MyCommand.Path -PackageRoot (Split-Path -Parent $testDirectory)
$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Stop'
. $ScriptPath -Action Library
$testResults=New-Object System.Collections.ArrayList
function Assert-StorageV4 { param([bool]$Condition,[string]$Message) if (-not $Condition) { throw $Message } }
function Assert-StorageV4Throws { param([scriptblock]$Body) $thrown=$false;try { & $Body | Out-Null } catch {$thrown=$true};if (-not $thrown) {throw 'Expected rejection did not occur.'} }
function Invoke-StorageV4Case {
    param([string]$Id,[string]$Name,[scriptblock]$Body)
    $status='PASS';$detail=''
    try { & $Body | Out-Null } catch { $status='FAIL';$detail=$_.Exception.Message }
    [void]$testResults.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
    Write-Host ($status+' '+$Id+' '+$Name);if ($detail -ne '') {Write-Host $detail}
}
$testTemp=[IO.Path]::Combine([IO.Path]::GetTempPath(),('aegis-storage-'+[Guid]::NewGuid().ToString('N')))
[void][IO.Directory]::CreateDirectory($testTemp)
$savedGlobals=@{}
foreach ($name in @('AegisLayoutProfile','AegisPendingMoves','AegisLastResult','AegisLastExitCode')) {
    $variable=Get-Variable -Name $name -Scope Global -ErrorAction SilentlyContinue
    $savedGlobals[$name]=@{Exists=($null -ne $variable);Value=$null};if ($null -ne $variable) {$savedGlobals[$name].Value=$variable.Value}
}
try {
    $csv=Join-Path $testTemp 'processes.csv';$xml=Join-Path $testTemp 'home.xml'
    $rules=@(ConvertTo-AegisRules @(@{Id='terminal';ProcessName='putty';Title='작업 <A> & B';Tier=2;GroupId='work';Priority=100;GroupPriority=100;GroupWeight=2;SizeMode='Exact';Width=500;Height=340}))
    $options=New-AegisOptions @{Weights=@{3=40;2=40;1=20}}
    $layout=New-AegisProfile $rules $options 'Coordinate:Test|M1:0,0,1600,1000'
    $window=@{Id='101';ProcessId=1001;ThreadId=2001;ProcessStart='0000000000001001';ClassName='한글 & Class';RuleId='terminal';Tier=2;GroupId='work';Priority=100;GroupPriority=100;GroupWeight=2;SizeMode='Exact';DesiredWidth=500;DesiredHeight=340;Monitor=@{Id='M1';Left=0;Top=0;Width=1600;Height=1000}}
    $plan=@{Left=8;Top=8;Width=500;Height=340;ZoneRect=@{Left=8;Top=8;Width=1584;Height=984}}
    $layout.Slots=@((New-AegisSlot $window $plan 'terminal:001' 0))
    $layout.Zones=@(@{Level='Tier';Tier=2;GroupId='';Left=8;Top=8;Width=1584;Height=984;MonitorId='M1'},@{Level='Group';Tier=2;GroupId='work';Left=8;Top=8;Width=1584;Height=984;MonitorId='M1'})
    Test-AegisProfile $layout
    Invoke-StorageV4Case 'S01' 'CSV exact process size and executable-name normalization' {
        [IO.File]::WriteAllText($csv,"Id,ProcessName,Tier,SizeMode,Width,Height`r`nterminal,PuTTY.exe,2,Exact,800,600`r`n",[Text.Encoding]::UTF8)
        $loaded=@(Import-AegisProcessRules $csv)
        Assert-StorageV4 ($loaded.Count -eq 1 -and $loaded[0].ProcessName -ceq 'PuTTY' -and $loaded[0].Width -eq 800 -and $loaded[0].Height -eq 600) 'CSV size/name not normalized.'
    }
    Invoke-StorageV4Case 'S02' 'Blank optional CSV fields use conservative defaults' {
        [IO.File]::WriteAllText($csv,"Id,ProcessName,Width,Height,Include`r`na,notepad,,,`r`n",[Text.Encoding]::UTF8)
        $loaded=@(Import-AegisProcessRules $csv)
        Assert-StorageV4 ($loaded[0].SizeMode -eq 'Preserve' -and $loaded[0].GroupId -eq 'default' -and $loaded[0].Include) 'Defaults invalid.'
    }
    Invoke-StorageV4Case 'S03' 'Misspelled CSV columns are rejected' {
        [IO.File]::WriteAllText($csv,"Id,ProcessName,Heigth`r`na,notepad,400`r`n")
        Assert-StorageV4Throws { Import-AegisProcessRules $csv }
    }
    Invoke-StorageV4Case 'S04' 'CSV title content remains literal data' {
        [IO.File]::WriteAllText($csv,'Id,ProcessName,Title'+"`r`n"+'a,notepad,$(throw 123)' + "`r`n")
        $loaded=@(Import-AegisProcessRules $csv)
        Assert-StorageV4 ($loaded[0].Title -ceq '$(throw 123)') 'CSV title was evaluated or changed.'
    }
    Invoke-StorageV4Case 'S05' 'Invalid exact size cannot become a rule' {
        Assert-StorageV4Throws { ConvertTo-AegisRules @(@{Id='a';ProcessName='notepad';SizeMode='Exact';Width=300.5;Height=400}) }
        Assert-StorageV4Throws { ConvertTo-AegisRules @(@{Id='a';ProcessName='notepad';SizeMode='Exact';Width=300;Height=0}) }
    }
    Invoke-StorageV4Case 'S06' 'Conflicting group weights and duplicate rule IDs reject' {
        Assert-StorageV4Throws { ConvertTo-AegisRules @(@{Id='a';ProcessName='one';GroupWeight=1},@{Id='b';ProcessName='two';GroupWeight=2}) }
        Assert-StorageV4Throws { ConvertTo-AegisRules @(@{Id='a';ProcessName='one'},@{Id='a';ProcessName='two'}) }
    }
    Invoke-StorageV4Case 'S07' 'Populated XML profile roundtrip preserves Korean and geometry' {
        Save-AegisProfile $layout $xml;$loaded=Import-AegisProfile $xml
        Assert-StorageV4 ($loaded.PolicyFingerprint -ceq $layout.PolicyFingerprint -and $loaded.Rules[0].Title -ceq $layout.Rules[0].Title) 'Policy/text changed in XML.'
        Assert-StorageV4 (Test-AegisRectMatch $loaded.Slots[0].HomeRect $layout.Slots[0].HomeRect 0) 'Home changed in XML.'
        Assert-StorageV4 ($loaded.Slots[0].Identity.ClassName -ceq $layout.Slots[0].Identity.ClassName -and $loaded.Options.Weights[3] -eq 40) 'Identity hint or weights changed.'
    }
    Invoke-StorageV4Case 'S08' 'Rejected save preserves previous good file bytes' {
        $before=[Convert]::ToBase64String([IO.File]::ReadAllBytes($xml));$bad=Copy-AegisData $layout;$bad.Slots[0].HomeRect.Left=99999
        Assert-StorageV4Throws { Save-AegisProfile $bad $xml }
        Assert-StorageV4 ($before -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($xml))) 'Previous file was changed by rejected save.'
    }
    Invoke-StorageV4Case 'S09' 'Valid replacement is readable and cleans temporary files' {
        $updated=Copy-AegisData $layout;$updated.Revision=2;Save-AegisProfile $updated $xml
        Assert-StorageV4 ((Import-AegisProfile $xml).Revision -eq 2) 'New revision not written.'
        Assert-StorageV4 ([IO.Directory]::GetFiles($testTemp,'*.tmp').Length -eq 0) 'Temporary file leaked.'
    }
    Invoke-StorageV4Case 'S10' 'DTD and external entities are prohibited' {
        $badPath=Join-Path $testTemp 'dtd.xml'
        [IO.File]::WriteAllText($badPath,'<!DOCTYPE AegisProfile [<!ENTITY x SYSTEM "file:///never-read">]><AegisProfile>&x;</AegisProfile>')
        Assert-StorageV4Throws { Import-AegisProfile $badPath }
    }
    Invoke-StorageV4Case 'S11' 'Unexpected XML fields reject rather than execute' {
        $badPath=Join-Path $testTemp 'unexpected.xml';$raw=[IO.File]::ReadAllText($xml)
        [IO.File]::WriteAllText($badPath,$raw.Replace('<Slots>','<Slots><Command>throw 123</Command>'))
        Assert-StorageV4Throws { Import-AegisProfile $badPath }
    }
    Invoke-StorageV4Case 'S12' 'Oversized and network data paths reject' {
        $badPath=Join-Path $testTemp 'large.xml';[IO.File]::WriteAllText($badPath,('x'*262145))
        Assert-StorageV4Throws { Import-AegisProfile $badPath }
        Assert-StorageV4Throws { Get-AegisDataPath '\\server\share\config.csv' $true }
    }
    Invoke-StorageV4Case 'S13' 'Duplicate XML options reject' {
        $badPath=Join-Path $testTemp 'duplicate.xml';$raw=[IO.File]::ReadAllText($xml)
        [IO.File]::WriteAllText($badPath,$raw.Replace('</Options>','<Option Key="Gap" Value="8" /></Options>'))
        Assert-StorageV4Throws { Import-AegisProfile $badPath }
    }
    Invoke-StorageV4Case 'S14' 'Failed LoadProfile keeps the active profile' {
        $global:AegisLayoutProfile=$layout;$global:AegisPendingMoves=@()
        $badPath=Join-Path $testTemp 'dtd.xml';$result=& $ScriptPath -Action LoadProfile -ProfilePath $badPath -PassThru
        Assert-StorageV4 ($result.ExitCode -ne 0 -and [object]::ReferenceEquals($global:AegisLayoutProfile,$layout)) 'Failed load replaced active state.'
    }
    Invoke-StorageV4Case 'S15' 'LoadProfile succeeds with initially absent pending state' {
        $global:AegisLayoutProfile=$null;$global:AegisPendingMoves=$null
        $result=& $ScriptPath -Action LoadProfile -ProfilePath $xml -PassThru
        Assert-StorageV4 ($result.ExitCode -eq 0 -and $global:AegisLayoutProfile.Revision -eq 2) 'Fresh-runspace LoadProfile failed.'
    }
    Invoke-StorageV4Case 'S16' 'Preview cannot silently write a profile' {
        $target=Join-Path $testTemp 'must-not-write.xml'
        $result=& $ScriptPath -Action SaveProfile -ProfilePath $target -Preview -PassThru
        Assert-StorageV4 ($result.ExitCode -ne 0 -and -not [IO.File]::Exists($target)) 'Preview wrote a file.'
    }
    Invoke-StorageV4Case 'S17' 'An empty profile roundtrips without null-array corruption' {
        $empty=New-AegisProfile @() (New-AegisOptions) 'TestEmpty'
        $emptyPath=Join-Path $testTemp 'empty.xml';Save-AegisProfile $empty $emptyPath;$loaded=Import-AegisProfile $emptyPath
        Assert-StorageV4 ($loaded.Rules.Count -eq 0 -and $loaded.Slots.Count -eq 0 -and $loaded.Zones.Count -eq 0) 'Empty profile array shape changed.'
    }
    $failures=@($testResults | Where-Object {$_.Status -ne 'PASS'}).Count
    $sha=[Security.Cryptography.SHA256]::Create()
    try {$sourceHash=[BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($ScriptPath))).Replace('-','').ToLowerInvariant()} finally {$sha.Clear()}
    $summary=New-Object PSObject -Property @{ProductSha256=$sourceHash;EngineVersion=[string]$PSVersionTable.PSVersion;ActualPS2Execution=$(if($PSVersionTable.PSVersion.Major -eq 2){'RUN'}else{'NOT_RUN'});WindowsIntegration='NOT_RUN';Total=$testResults.Count;Passed=($testResults.Count-$failures);Failed=$failures;Cases=$testResults.ToArray()}
    if (-not [string]::IsNullOrEmpty($ReportPath)) {$summary | Export-Clixml -Path $ReportPath}
    $summary
    if ($failures -gt 0) { throw ('Storage failures: '+$failures) }
} finally {
    foreach ($name in $savedGlobals.Keys) {
        if ($savedGlobals[$name].Exists) {Set-Variable -Name $name -Scope Global -Value $savedGlobals[$name].Value}
        else {Remove-Variable -Name $name -Scope Global -ErrorAction SilentlyContinue}
    }
    [IO.Directory]::Delete($testTemp,$true);$ErrorActionPreference=$oldPreference
}
