#requires -version 2.0
<#
Aegis v4 behavioral regressions. Uses the actual product functions and an
in-memory Windows boundary; never changes real desktop windows.
A pass on PowerShell 7 / Linux does not establish PS2 or Win32 integration.
#>
param([string]$ScriptPath='', [string]$ReportPath='')
$testFolder=Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($ScriptPath)) {$ScriptPath=Join-Path (Split-Path -Parent $testFolder) 'Aegis.ps1'}
. (Join-Path $testFolder 'ReportPathSafety.ps1')
$ReportPath=Resolve-AegisHarnessReportPath -Path $ReportPath -ProductPath $ScriptPath -HarnessPath $MyInvocation.MyCommand.Path -PackageRoot (Split-Path -Parent $testFolder)
if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {throw ('Product not found: '+$ScriptPath)}
$sourceHashProvider=[System.Security.Cryptography.SHA256]::Create()
try {$sourceSha256=[BitConverter]::ToString($sourceHashProvider.ComputeHash([IO.File]::ReadAllBytes($ScriptPath))).Replace('-','').ToLowerInvariant()}
finally {$sourceHashProvider.Clear()}
$previousErrorPreference=$ErrorActionPreference
$ErrorActionPreference='Stop'
try {
    . $ScriptPath -Action Library
    $script:AegisV4Results=New-Object System.Collections.ArrayList
    function Assert-AegisV4 {
        param([bool]$Condition,[string]$Message)
        if (-not $Condition) {throw $Message}
    }
    function Invoke-AegisV4Case {
        param([string]$Id,[string]$Name,[scriptblock]$Body)
        $status='PASS';$detail=''
        try {& $Body | Out-Null}
        catch {$status='FAIL';$detail=$_.Exception.Message}
        [void]$script:AegisV4Results.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
        Write-Host ($status+' '+$Id+' '+$Name)
        if ($status -eq 'FAIL') {Write-Host ('  '+$detail)}
    }
    . (Join-Path $testFolder 'Controller-V4-Cases.ps1')
    $failed=@($script:AegisV4Results | Where-Object {$_.Status -eq 'FAIL'}).Count
    $summary=New-Object PSObject -Property @{
        ProductSha256=$sourceSha256
        EngineVersion=[string]$PSVersionTable.PSVersion
        ClrVersion=[string][Environment]::Version
        OS=[string][Environment]::OSVersion
        Scope='Actual product functions; synthetic desktop boundary. No real window mutation.'
        PowerShell2Runtime=$(if ($PSVersionTable.PSVersion.Major -eq 2) {'RUN'} else {'NOT_RUN'});WindowsIntegration='NOT_RUN'
        Total=$script:AegisV4Results.Count;Passed=($script:AegisV4Results.Count-$failed);Failed=$failed
        Cases=@($script:AegisV4Results.ToArray())
    }
    if (-not [string]::IsNullOrEmpty($ReportPath)) {$summary | Export-Clixml -Path $ReportPath}
    Write-Host ('Behavioral tests: '+$summary.Passed+'/'+$summary.Total+' passed.')
    if ($failed -gt 0) {throw ('Aegis v4 behavioral test failures: '+$failed)}
    $summary
} finally {$ErrorActionPreference=$previousErrorPreference}
