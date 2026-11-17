#requires -version 2.0
# Focused harness regression: disposable package inputs, no native window API.
param([string]$PackageRoot='', [string]$ReportPath='')
$auditPath=$MyInvocation.MyCommand.Path
$auditDirectory=Split-Path -Parent $auditPath
if ($PackageRoot -eq '') { $PackageRoot=Split-Path -Parent $auditDirectory }
$PackageRoot=(Resolve-Path -LiteralPath $PackageRoot -ErrorAction Stop).ProviderPath
. (Join-Path (Join-Path $PackageRoot 'tests') 'ReportPathSafety.ps1')
if ($ReportPath -eq '') { $ReportPath=Join-Path $auditDirectory 'report-path-safety.clixml' }
$ReportPath=Resolve-AegisHarnessReportPath -Path $ReportPath -ProductPath (Join-Path $PackageRoot 'Aegis.ps1') -HarnessPath $auditPath -PackageRoot $PackageRoot
$previousPreference=$ErrorActionPreference;$ErrorActionPreference='Stop'
$results=New-Object Collections.ArrayList
$fixture=[IO.Path]::Combine([IO.Path]::GetTempPath(),('aegis-report-safety-'+[Guid]::NewGuid().ToString('N')))
[void][IO.Directory]::CreateDirectory($fixture)
function Assert-RPS { param([bool]$Condition,[string]$Message) if (-not $Condition) { throw $Message } }
function Case-RPS {
    param([string]$Id,[string]$Name,[scriptblock]$Body)
    $status='PASS';$detail=''
    try { & $Body | Out-Null } catch { $status='FAIL';$detail=$_.Exception.Message }
    [void]$results.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
    Write-Host ($status+' '+$Id+' '+$Name+' '+$detail)
}
function Reject-RPS {
    param([scriptblock]$Body,[string]$Reason='ReportPathProtectedInput')
    $caught=$false
    try { & $Body | Out-Null }
    catch { if ($_.Exception.Message -like ($Reason+'*')) { $caught=$true } else { throw } }
    Assert-RPS $caught ('Expected pre-run rejection: '+$Reason)
}
function Hash-RPS {
    param([string]$Path)
    $provider=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($provider.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace('-','').ToLowerInvariant() }
    finally { $provider.Clear() }
}
try {
    $fixtureTests=Join-Path $fixture 'tests';$fixtureVerification=Join-Path $fixture 'verification'
    $fixtureReports=Join-Path $fixture 'reports';$fixtureExternal=Join-Path $fixture 'external'
    foreach ($directory in @($fixtureTests,$fixtureVerification,$fixtureReports,$fixtureExternal)) { [void][IO.Directory]::CreateDirectory($directory) }
    $fixtureProduct=Join-Path $fixture 'Aegis.ps1'
    $fixtureConfig=Join-Path $fixture 'Aegis.Processes.csv'
    $fixtureHelper=Join-Path $fixtureTests 'ReportPathSafety.ps1'
    $fixtureAuxiliary=Join-Path $fixtureTests 'Controller-V4-Cases.ps1'
    [IO.File]::WriteAllText($fixtureProduct,"throw 'UnexpectedProductExecution'`r`n",[Text.Encoding]::UTF8)
    [IO.File]::WriteAllText($fixtureConfig,"Id,ProcessName`r`na,fixture`r`n",[Text.Encoding]::UTF8)
    [IO.File]::WriteAllText($fixtureAuxiliary,"throw 'UnexpectedAuxiliaryExecution'`r`n",[Text.Encoding]::UTF8)
    [IO.File]::Copy((Join-Path (Join-Path $PackageRoot 'tests') 'ReportPathSafety.ps1'),$fixtureHelper)
    $harnesses=@(
        @{Directory='tests';File='Test-AegisV4.ps1';ProductParameter='ScriptPath';OutputParameter='ReportPath'},
        @{Directory='tests';File='Test-StorageV4.ps1';ProductParameter='ScriptPath';OutputParameter='ReportPath'},
        @{Directory='tests';File='Test-EntryPointV4.ps1';ProductParameter='ProductPath';OutputParameter='ReportPath'},
        @{Directory='verification';File='Test-LayoutV4.ps1';ProductParameter='SourcePath';OutputParameter='OutputPath'},
        @{Directory='verification';File='Test-WindowsPreflight.ps1';ProductParameter='ScriptPath';OutputParameter='ReportPath'}
    )
    [int]$caseNumber=0
    foreach ($harness in $harnesses) {
        $source=Join-Path (Join-Path $PackageRoot $harness.Directory) $harness.File
        $destination=Join-Path (Join-Path $fixture $harness.Directory) $harness.File
        [IO.File]::Copy($source,$destination)
    }
    foreach ($harness in $harnesses) {
        $harnessPath=Join-Path (Join-Path $fixture $harness.Directory) $harness.File
        foreach ($protected in @(@{Name='product';Path=$fixtureProduct},@{Name='configuration';Path=$fixtureConfig},@{Name='own harness';Path=$harnessPath},@{Name='shared helper';Path=$fixtureHelper},@{Name='auxiliary harness';Path=$fixtureAuxiliary})) {
            $caseNumber++
            Case-RPS ('RP'+$caseNumber.ToString('00')) ($harness.File+' protects '+$protected.Name) {
                $before=[Convert]::ToBase64String([IO.File]::ReadAllBytes($protected.Path))
                $invocation=@{};$invocation[$harness.ProductParameter]=$fixtureProduct;$invocation[$harness.OutputParameter]=$protected.Path
                Reject-RPS { & $harnessPath @invocation }
                Assert-RPS ($before -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($protected.Path))) 'A protected input changed.'
            }
        }
    }
    Case-RPS 'RP26' 'Preflight protects its explicit external ConfigPath' {
        $externalConfig=Join-Path $fixtureExternal 'customer-settings.dat'
        [IO.File]::WriteAllText($externalConfig,'external configuration',[Text.Encoding]::UTF8)
        $preflight=Join-Path $fixtureVerification 'Test-WindowsPreflight.ps1'
        Reject-RPS { & $preflight -ScriptPath $fixtureProduct -ConfigPath $externalConfig -ReportPath $externalConfig }
        Assert-RPS ([IO.File]::ReadAllText($externalConfig) -ceq 'external configuration') 'External configuration changed.'
    }
    Case-RPS 'RP27' 'Parent-directory traversal still resolves to protected product' {
        $candidate=Join-Path $fixtureReports '../Aegis.ps1'
        Reject-RPS { Resolve-AegisHarnessReportPath -Path $candidate -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture }
    }
    Case-RPS 'RP28' 'Windows case-insensitive collision is rejected' {
        $candidate=Join-Path $fixture 'AEGIS.PS1'
        Reject-RPS { Resolve-AegisHarnessReportPath -Path $candidate -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture }
    }
    Case-RPS 'RP29' 'Identical input bytes under another name cannot be overwritten' {
        $candidate=Join-Path $fixtureReports 'copied-input.clixml'
        [IO.File]::Copy($fixtureProduct,$candidate)
        Reject-RPS { Resolve-AegisHarnessReportPath -Path $candidate -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture }
        Assert-RPS ([IO.File]::ReadAllText($candidate) -ceq [IO.File]::ReadAllText($fixtureProduct)) 'Input copy changed.'
    }
    Case-RPS 'RP30' 'New report and normal replacement remain supported' {
        $candidate=Join-Path $fixtureReports 'repeat.clixml'
        $first=Resolve-AegisHarnessReportPath -Path $candidate -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture
        New-Object PSObject -Property @{Revision=1} | Export-Clixml -Path $first
        $second=Resolve-AegisHarnessReportPath -Path $candidate -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture
        New-Object PSObject -Property @{Revision=2} | Export-Clixml -Path $second
        Assert-RPS ((Import-Clixml -Path $candidate).Revision -eq 2) 'Existing normal report could not be replaced.'
    }
    Case-RPS 'RP31' 'Relative report paths use the PowerShell current location' {
        Push-Location $fixtureReports
        try {
            $candidate=Resolve-AegisHarnessReportPath -Path 'relative.clixml' -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture
            Assert-RPS ([string]::Equals($candidate,(Join-Path $fixtureReports 'relative.clixml'),[StringComparison]::OrdinalIgnoreCase)) 'Relative report used the process working directory.'
        } finally { Pop-Location }
    }
    Case-RPS 'RP32' 'Wildcard report paths are rejected before export' {
        Reject-RPS { Resolve-AegisHarnessReportPath -Path (Join-Path $fixtureReports '*.clixml') -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture } 'ReportPathMustBeLiteral'
    }
    Case-RPS 'RP33' 'A directory is not accepted as an output file' {
        Reject-RPS { Resolve-AegisHarnessReportPath -Path $fixtureReports -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture } 'ReportPathMustNameFile'
    }
    Case-RPS 'RP34' 'An omitted report still performs no path or file work' {
        Assert-RPS ((Resolve-AegisHarnessReportPath -Path '' -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture) -ceq '') 'Empty report path changed.'
    }
    Case-RPS 'RP35' 'External product directory cannot inject a helper' {
        $externalProduct=Join-Path $fixtureExternal 'Aegis.ps1'
        $externalHelper=Join-Path $fixtureExternal 'ReportPathSafety.ps1'
        $marker=Join-Path $fixtureExternal 'helper-executed.txt'
        [IO.File]::Copy($fixtureProduct,$externalProduct)
        [IO.File]::WriteAllText($externalHelper,"[IO.File]::WriteAllText('"+$marker.Replace("'","''")+"','unexpected')",[Text.Encoding]::UTF8)
        $entry=Join-Path $fixtureTests 'Test-EntryPointV4.ps1'
        Reject-RPS { & $entry -ProductPath $externalProduct -ReportPath $externalProduct }
        Assert-RPS (-not [IO.File]::Exists($marker)) 'Helper code was loaded from the supplied product directory.'
    }
    Case-RPS 'RP36' 'File-system PSDrive aliases resolve to protected input' {
        $driveName='AegisReportPathFixture'
        [void](New-PSDrive -Name $driveName -PSProvider FileSystem -Root $fixture)
        try {
            Reject-RPS { Resolve-AegisHarnessReportPath -Path ($driveName+':/Aegis.ps1') -ProductPath $fixtureProduct -HarnessPath $fixtureAuxiliary -PackageRoot $fixture }
        } finally { Remove-PSDrive -Name $driveName }
    }
    Case-RPS 'RP37' 'This regression harness protects itself in a disposable package' {
        $fixtureAudit=Join-Path $fixtureVerification 'Test-ReportPathSafety.ps1'
        [IO.File]::Copy($auditPath,$fixtureAudit)
        $before=[Convert]::ToBase64String([IO.File]::ReadAllBytes($fixtureAudit))
        Reject-RPS { & $fixtureAudit -PackageRoot $fixture -ReportPath $fixtureAudit }
        Assert-RPS ($before -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($fixtureAudit))) 'Regression harness overwrote its own copy.'
    }
    $failed=@($results | Where-Object {$_.Status -eq 'FAIL'}).Count
    $productHash='';$helperHash='';$harnessHash='';$hashError=''
    try {
        $productHash=Hash-RPS (Join-Path $PackageRoot 'Aegis.ps1')
        $helperHash=Hash-RPS (Join-Path (Join-Path $PackageRoot 'tests') 'ReportPathSafety.ps1')
        $harnessHash=Hash-RPS $auditPath
    } catch { $hashError=$_.Exception.Message }
    $summary=New-Object PSObject -Property @{
        Suite='Aegis harness report path protection';Total=$results.Count;Passed=($results.Count-$failed);Failed=$failed
        ProductSha256=$productHash;HelperSha256=$helperHash;HarnessSha256=$harnessHash;HashReady=($hashError -eq '');HashError=$hashError
        PowerShellVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[string][Environment]::Version
        ActualPS2Execution=$(if($PSVersionTable.PSVersion.Major -eq 2){'RUN'}else{'NOT_RUN'})
        ActualPS2Clr2Execution=$(if($PSVersionTable.PSVersion.Major -eq 2 -and [Environment]::Version.Major -eq 2){'RUN'}else{'NOT_RUN'})
        WindowsIntegration='NOT_RUN';Scope='Disposable inputs and report files; no native window API or real application changes.'
        FipsCondition='Default SHA256.Create used elsewhere can fail under FIPS policy on .NET Framework 4.6.1 or earlier; this path guard uses byte comparison and does not change policy.'
        FilesystemRaceLimitation='Pre-run accident prevention, not a concurrent filesystem lock or hostile-race guarantee.'
        Cases=$results.ToArray()
    }
    $summary | Export-Clixml -Path $ReportPath -Depth 12
    $summary
    if ($failed -ne 0) { throw ('Report-path safety regressions failed: '+$failed) }
} finally {
    if ([IO.Directory]::Exists($fixture)) { [IO.Directory]::Delete($fixture,$true) }
    $ErrorActionPreference=$previousPreference
}
