#requires -version 2.0
<#
Entry-point and caller-state regressions. Actual product functions, no native
window mutations. Uses temporary local data files and a tiny SelfTest fixture.
#>
param([string]$ProductPath='', [string]$ReportPath='')
$testDirectory=Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($ProductPath)) {$ProductPath=Join-Path (Split-Path -Parent $testDirectory) 'Aegis.ps1'}
. (Join-Path $testDirectory 'ReportPathSafety.ps1')
$ReportPath=Resolve-AegisHarnessReportPath -Path $ReportPath -ProductPath $ProductPath -HarnessPath $MyInvocation.MyCommand.Path -PackageRoot (Split-Path -Parent $testDirectory)
$ProductPath=[IO.Path]::GetFullPath($ProductPath)
$hashProvider=[Security.Cryptography.SHA256]::Create()
try {$sourceHash=[BitConverter]::ToString($hashProvider.ComputeHash([IO.File]::ReadAllBytes($ProductPath))).Replace('-','').ToLowerInvariant()}
finally {$hashProvider.Clear()}
& {
    $previousPreference=$ErrorActionPreference;$ErrorActionPreference='Stop'
    $results=New-Object System.Collections.ArrayList
    $savedGlobals=@{}
    foreach ($variableName in @('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult','AegisLastExitCode')) {
        $existing=Get-Variable -Name $variableName -Scope Global -ErrorAction SilentlyContinue
        $savedGlobals[$variableName]=@{Exists=($null -ne $existing);Value=$null}
        if ($null -ne $existing) {$savedGlobals[$variableName].Value=$existing.Value}
        Set-Variable -Name $variableName -Scope Global -Value $null
    }
    $temporaryDirectory=Join-Path ([IO.Path]::GetTempPath()) ('aegis-entry-v4-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($temporaryDirectory)
    function Assert-EntryV4 {param([bool]$Condition,[string]$Message) if (-not $Condition) {throw $Message}}
    function Invoke-EntryV4Case {
        param([string]$Id,[string]$Name,[scriptblock]$Body,[bool]$Skip=$false)
        $status='PASS';$detail=''
        if ($Skip) {$status='SKIP';$detail='This protection branch applies only to a non-Windows development host.'}
        else {try {& $Body | Out-Null} catch {$status='FAIL';$detail=$_.Exception.Message}}
        [void]$results.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
        Write-Host ($status+' '+$Id+' '+$Name)
        if ($status -eq 'FAIL') {Write-Host ('  '+$detail)}
    }
    try {
        . $ProductPath -Action Library
        Set-StrictMode -Version 2
        Invoke-EntryV4Case 'EP01' 'Library loading preserves caller strict mode' {
            . $ProductPath -Action Library
            $strictStillEnabled=$false;$probe=@{}
            try {$null=$probe.PropertyThatDoesNotExist} catch {$strictStillEnabled=$true}
            Assert-EntryV4 $strictStillEnabled 'Library loading disabled caller strict mode.'
        }
        Invoke-EntryV4Case 'EP02' 'Invalid options report failure before any native activity under a strict caller' {
            $result=& $ProductPath -Action Inspect -Options @{NotARealOption=1} -PassThru
            Assert-EntryV4 ($result.Status -eq 'Aborted' -and $result.ExitCode -eq 2) 'Invalid option did not yield deterministic failure.'
            Assert-EntryV4 ($result.Detail -like '*Unknown option*') 'Invalid-option validation did not run first.'
            $strictStillEnabled=$false;$probe=@{}
            try {$null=$probe.PropertyThatDoesNotExist} catch {$strictStillEnabled=$true}
            Assert-EntryV4 $strictStillEnabled 'Main changed caller strict mode.'
        }
        Invoke-EntryV4Case 'EP03' 'Invalid process rule is rejected before native initialization' {
            $badRules=@(@{Id='bad';ProcessName='fixture';Tier=99})
            $result=& $ProductPath -Action Arrange -Rules $badRules -PassThru
            Assert-EntryV4 ($result.Status -eq 'Aborted' -and $result.ExitCode -eq 2 -and $result.Detail -like '*Tier*') 'Invalid rule reached platform or native execution.'
        }
        $windowsHost=([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
        Invoke-EntryV4Case 'EP04' 'Default Inspect fails safely on a non-Windows host' {
            $result=& $ProductPath -PassThru
            Assert-EntryV4 ($result.Action -eq 'Inspect') 'Default action is not Inspect.'
            Assert-EntryV4 ($result.Status -eq 'Aborted' -and $result.ExitCode -eq 2 -and $result.Detail -like '*Windows desktop*') 'Non-Windows protection did not return the expected safe failure.'
        } $windowsHost
        Invoke-EntryV4Case 'EP05' 'SaveProfile rejects Preview without writing a file' {
            $global:AegisLayoutProfile=New-AegisProfile -Rules @() -Options (New-AegisOptions) -TopologySignature 'synthetic:empty'
            $global:AegisPendingMoves=@()
            $path=Join-Path $temporaryDirectory 'preview-save.xml'
            $result=& $ProductPath -Action SaveProfile -ProfilePath $path -Preview -PassThru
            Assert-EntryV4 ($result.Status -eq 'Aborted' -and $result.Detail -like '*Preview*') 'Unsupported Preview was not explicitly rejected.'
            Assert-EntryV4 (-not (Test-Path -LiteralPath $path)) 'SaveProfile wrote despite Preview.'
        }
        Invoke-EntryV4Case 'EP06' 'LoadProfile rejects Preview without replacing current layout state' {
            $path=Join-Path $temporaryDirectory 'preview-load.xml'
            $fileLayout=New-AegisProfile -Rules @() -Options (New-AegisOptions) -TopologySignature 'synthetic:empty' -Revision 1
            Save-AegisProfile -LayoutProfile $fileLayout -Path $path
            $global:AegisLayoutProfile=New-AegisProfile -Rules @() -Options (New-AegisOptions) -TopologySignature 'synthetic:current' -Revision 3
            $result=& $ProductPath -Action LoadProfile -ProfilePath $path -Preview -PassThru
            Assert-EntryV4 ($result.Status -eq 'Aborted' -and $result.Detail -like '*Preview*') 'Unsupported load Preview was not explicitly rejected.'
            Assert-EntryV4 ($global:AegisLayoutProfile.Revision -eq 3 -and $global:AegisLayoutProfile.TopologySignature -eq 'synthetic:current') 'Load Preview replaced current layout state.'
        }
        $selfTestDirectory=Join-Path $temporaryDirectory 'tests';[void][IO.Directory]::CreateDirectory($selfTestDirectory)
        $selfTestPath=Join-Path $selfTestDirectory 'Test-AegisV4.ps1'
        $syntheticSource=Join-Path $temporaryDirectory 'Aegis.ps1'
        Invoke-EntryV4Case 'EP07' 'Successful SelfTest resets a stale prior failure exit code' {
            [IO.File]::WriteAllText($selfTestPath,"param([string]`$ScriptPath)`r`n'Fixture success'`r`n",[Text.Encoding]::UTF8)
            $global:AegisLastExitCode=9
            [void](Invoke-AegisMain -Arguments @{Action='SelfTest'} -BoundParameters @{} -SourcePath $syntheticSource)
            Assert-EntryV4 ($global:AegisLastExitCode -eq 0) 'SelfTest success reused a stale failure code.'
        }
        Invoke-EntryV4Case 'EP08' 'Failed SelfTest cannot reuse a stale prior success exit code' {
            [IO.File]::WriteAllText($selfTestPath,"param([string]`$ScriptPath)`r`nthrow 'Fixture failure'`r`n",[Text.Encoding]::UTF8)
            $global:AegisLastExitCode=0;$caught=$false
            try {[void](Invoke-AegisMain -Arguments @{Action='SelfTest'} -BoundParameters @{} -SourcePath $syntheticSource)} catch {$caught=$true}
            Assert-EntryV4 ($caught -and $global:AegisLastExitCode -ne 0) 'SelfTest failure retained a success exit code.'
        }
        & {
            # Stub the public orchestration boundary; no real native window
            # adapter is reachable in these cleanup-precedence cases.
            function Test-AegisNativeWindows { return $true }
            function Enter-AegisDpiContext { return @{Mode='Synthetic';Changed=$true;Previous=[IntPtr]1} }
            function Exit-AegisDpiContext { param($Context) return @{Accepted=$false;Reason='SyntheticDpiExitFailure'} }
            function Invoke-AegisController {
                param($Action,$Options,$Rules,$RuleIds,$Tier,$GroupId,$KeepSize,$ReleaseAbsent,$Preview)
                $outcome=New-AegisReport $Action $false
                $outcome.Status=$probeStatus;$outcome.ExitCode=$probeExit
                if ($probeExit -eq 3) { $outcome.PendingCount=1 }
                return $outcome
            }
            $global:AegisLayoutProfile=$null
            foreach ($probe in @(@('EP09','Complete',0,'Partial',1),@('EP10','Aborted',2,'Aborted',2),@('EP11','BlockedPending',3,'BlockedPending',3))) {
                $probeStatus=[string]$probe[1];$probeExit=[int]$probe[2]
                $expectedStatus=[string]$probe[3];$expectedExit=[int]$probe[4]
                Invoke-EntryV4Case ([string]$probe[0]) ('DPI cleanup preserves failure precedence for '+$probeStatus) {
                    $arguments=@{Action='Arrange';Options=@{};Rules=@();ConfigPath='';ProfilePath='';RuleIds=@();Tier=0;GroupId='';KeepSize=$false;ReleaseAbsent=$false;Preview=$false;PassThru=$true}
                    $result=Invoke-AegisMain -Arguments $arguments -BoundParameters @{} -SourcePath $ProductPath
                    Assert-EntryV4 ($result.Status -eq $expectedStatus -and $result.ExitCode -eq $expectedExit) 'Cleanup changed primary failure severity.'
                    Assert-EntryV4 (@($result.Warnings) -contains 'SyntheticDpiExitFailure') 'Cleanup failure diagnostic was lost.'
                    if ($probeExit -eq 3) { Assert-EntryV4 ($result.PendingCount -eq 1) 'Unresolved request count was lost.' }
                }
            }
        }
        $failed=@($results | Where-Object {$_.Status -eq 'FAIL'}).Count
        $passed=@($results | Where-Object {$_.Status -eq 'PASS'}).Count
        $skipped=@($results | Where-Object {$_.Status -eq 'SKIP'}).Count
        $summary=New-Object PSObject -Property @{
            ProductSha256=$sourceHash;EngineVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[string][Environment]::Version
            Scope='Actual entry point and data-file paths, synthetic SelfTest fixture; no native window mutations.'
            PowerShell2Runtime=$(if ($PSVersionTable.PSVersion.Major -eq 2) {'RUN'} else {'NOT_RUN'});WindowsIntegration='NOT_RUN'
            Total=$results.Count;Passed=$passed;Skipped=$skipped;Failed=$failed;Cases=@($results.ToArray())
        }
        if (-not [string]::IsNullOrEmpty($ReportPath)) {$summary | Export-Clixml -Path $ReportPath}
        Write-Host ('Entry-point tests: '+$passed+'/'+$results.Count+' passed; '+$skipped+' skipped.')
        if ($failed -gt 0) {throw ('Entry-point failures: '+$failed)}
        $summary
    } finally {
        foreach ($variableName in @('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult','AegisLastExitCode')) {
            if ($savedGlobals[$variableName].Exists) {Set-Variable -Name $variableName -Scope Global -Value $savedGlobals[$variableName].Value}
            else {Remove-Variable -Name $variableName -Scope Global -ErrorAction SilentlyContinue}
        }
        if (Test-Path -LiteralPath $temporaryDirectory) {Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force}
        $ErrorActionPreference=$previousPreference
    }
}
