#requires -version 2.0
<#
Focused collector regressions. Development harness only; no Windows API calls.
Private function-scope stubs exercise target orchestration without changing the
public runner's runtime gates or adding a public backend/runtime bypass switch.
Synthetic PASS results here do not establish Windows, PS2 or CLR2 execution.
#>
param([string]$RunnerPath='',[string]$ProductPath='',[string]$ReportPath='')
if ($WhatIfPreference) { throw 'InheritedWhatIfMustBeDisabledBeforeCollectorCases' }
$serverCaseOldPreference=$ErrorActionPreference
$ErrorActionPreference='Stop'
if ([string]::IsNullOrEmpty($RunnerPath)) { $RunnerPath=Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'Test-AegisServer.ps1' }
$serverCaseHarnessPath=$MyInvocation.MyCommand.Path
$serverCasePackage=Split-Path -Parent (Split-Path -Parent $serverCaseHarnessPath)
if ([string]::IsNullOrEmpty($ProductPath)) { $ProductPath=Join-Path $serverCasePackage 'Aegis.ps1' }
. (Join-Path $serverCasePackage 'tests\ReportPathSafety.ps1')
$ReportPath=Resolve-AegisHarnessReportPath $ReportPath $ProductPath $serverCaseHarnessPath $serverCasePackage @($RunnerPath)
$serverCaseSource=[IO.File]::ReadAllText($RunnerPath)
$serverCaseStart=$serverCaseSource.IndexOf('function Get-AegisServerValue {',[StringComparison]::Ordinal)
$serverCaseEnd=$serverCaseSource.IndexOf('# AEGIS_SERVER_ENTRY_POINT',[StringComparison]::Ordinal)
if ($serverCaseStart -lt 0 -or $serverCaseEnd -le $serverCaseStart) { throw 'Collector function boundary missing.' }
. ([scriptblock]::Create($serverCaseSource.Substring($serverCaseStart,$serverCaseEnd-$serverCaseStart)))
$serverCaseRoot=Join-Path ([IO.Path]::GetTempPath()) ('aegis-collector-cases-'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($serverCaseRoot)
$serverCaseResults=New-Object Collections.ArrayList
$serverCaseOriginalGlobals=Get-AegisServerGlobalSnapshot
$serverCaseOriginalGlobals.IsolationAttempted=$true
$script:ServerCaseStubCalls=New-Object Collections.ArrayList

function Assert-ServerCase {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-ServerCaseThrows {
    param([scriptblock]$Body)
    $serverDidThrow=$false
    try { & $Body | Out-Null } catch { $serverDidThrow=$true }
    if (-not $serverDidThrow) { throw 'Expected collector rejection.' }
}
function Invoke-ServerCase {
    param([string]$Id,[string]$Name,[scriptblock]$Body)
    $serverStatus='PASS';$serverDetail=''
    try { & $Body | Out-Null } catch { $serverStatus='FAIL';$serverDetail=$_.Exception.Message }
    [void]$serverCaseResults.Add(@{Id=$Id;Name=$Name;Status=$serverStatus;Detail=$serverDetail})
    Write-Host ($serverStatus+' '+$Id+' '+$Name)
    if ($serverDetail -ne '') { Write-Host $serverDetail }
}
function New-ServerCaseEnvironment {
    param([bool]$Target=$true,[bool]$Clr2=$true)
    $serverEngine='2.0';$serverClr='2.0.50727.9999'
    if (-not $Target) { $serverEngine='7.4.20';$serverClr='8.0.31' }
    elseif (-not $Clr2) { $serverClr='4.0.30319.42000' }
    return @{Platform='Win32NT';OSVersion='TEST HARNESS ONLY';PowerShellVersion=$serverEngine;ClrVersion=$serverClr;ProcessBitness=32;ActualWindows=$true;ActualPowerShell2=$Target;ActualClr2=$Clr2;TargetRuntime=$Target}
}
function New-ServerCaseSemantic {
    param([string]$Kind,[string]$Sha256,$Environment)
    $serverSemantic=@{Total=2;Passed=2;Failed=0;Cases=@(@{Status='PASS';Id='a'},@{Status='PASS';Id='b'})}
    if ($Kind -eq 'Planner') { $serverSemantic.SourceSha256=$Sha256;$serverSemantic.PowerShellVersion=$Environment.PowerShellVersion;$serverSemantic.ActualPowerShell2='RUN' }
    else {
        $serverSemantic.ProductSha256=$Sha256;$serverSemantic.EngineVersion=$Environment.PowerShellVersion
        if ($Kind -eq 'Storage') { $serverSemantic.ActualPS2Execution='RUN' } else { $serverSemantic.PowerShell2Runtime='RUN' }
    }
    return $serverSemantic
}
function New-ServerCasePreflight {
    param([string]$ProductSha,[string]$ConfigSha,[int]$Iterations,$Environment)
    $serverRows=New-Object Collections.ArrayList
    for ($serverIndex=1;$serverIndex -le $Iterations;$serverIndex++) {
        [void]$serverRows.Add(@{Iteration=$serverIndex;InspectResult=@{Action='Inspect';Status='Complete';Version='4.0.1-ps2';Counters=@{Mutations=0};Items=@(@{Title='PRIVATE-WINDOW-SENTINEL';ProcessName='fixture'})}})
    }
    return @{
        ProductSha256=$ProductSha;ConfigSha256=$ConfigSha;Status='Complete'
        Environment=@{MachineName='PRIVATE-MACHINE-SENTINEL';PowerShellVersion=$Environment.PowerShellVersion;ClrVersion=$Environment.ClrVersion;Platform='Win32NT'}
        ProductPath='C:\PRIVATE-USER-SENTINEL\Aegis.ps1'
        NativeContextExecuted=$true;InspectExecuted=$true;WindowsPowerShell2Executed=$true;GlobalsRestored=$true;AppMutationAcceptanceExecuted=$false
        RequestedIterations=$Iterations;CompletedIterations=$Iterations;AllowedRuleCount=1
        Context=@{Complete=$true;DesktopSafe=$true;Ready=$true};Results=$serverRows.ToArray()
        Summary=@{Count=$Iterations;ElapsedMeanMs=2.5;ElapsedMinMs=1;ElapsedMaxMs=4;CpuMeanMs=0.5}
    }
}
function New-ServerCasePackage {
    $serverFixtureRoot=Join-Path $serverCaseRoot ([Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($serverFixtureRoot)
    [void][IO.Directory]::CreateDirectory((Join-Path $serverFixtureRoot 'tests'))
    [void][IO.Directory]::CreateDirectory((Join-Path $serverFixtureRoot 'verification'))
    foreach ($serverRelative in @('Aegis.ps1','tests\Test-AegisV4.ps1','tests\Controller-V4-Cases.ps1','tests\ReportPathSafety.ps1','tests\Test-StorageV4.ps1','verification\Test-LayoutV4.ps1','verification\Test-WindowsPreflight.ps1')) {
        [IO.File]::WriteAllText((Join-Path $serverFixtureRoot $serverRelative),'throw ''FixtureScriptMustNeverExecute''',[Text.Encoding]::UTF8)
    }
    [IO.File]::WriteAllText((Join-Path $serverFixtureRoot 'Aegis.Processes.csv'),"Id,ProcessName`r`nfixture,fixture`r`n",[Text.Encoding]::UTF8)
    return @{ProductPath=(Join-Path $serverFixtureRoot 'Aegis.ps1');ConfigPath=(Join-Path $serverFixtureRoot 'Aegis.Processes.csv');OutputDirectory=(Join-Path $serverFixtureRoot 'evidence');Iterations=3;RunnerPath=$RunnerPath}
}
function Get-ServerCaseGate {
    param($Report,[string]$Id)
    return @($Report.Gates | Where-Object {$_.Id -eq $Id})[0]
}
function Invoke-ServerCasePrivateCollector {
    param($Settings,[string]$Mode='Good')
    # Only this harness scope shadows environment/suite functions. Public script
    # invocation never receives these definitions or a fake-runtime parameter.
    return (& {
        param($ServerFixtureSettings,$ServerFixtureMode)
        function Get-AegisServerEnvironment { return (New-ServerCaseEnvironment $true ($ServerFixtureMode -ne 'Clr4')) }
        function Invoke-AegisServerSuite {
            param([string]$ScriptFile,[hashtable]$Arguments,[string]$RawReportPath)
            $serverKind='Behavior'
            if ($ScriptFile -match 'Storage') { $serverKind='Storage' }
            elseif ($ScriptFile -match 'LayoutV4') { $serverKind='Planner' }
            elseif ($ScriptFile -match 'WindowsPreflight') { $serverKind='Preflight' }
            [void]$script:ServerCaseStubCalls.Add($serverKind)
            $global:AegisServerHarnessNew=@{Marker='Temporary state'}
            $global:AegisLayoutProfile=@{Marker='Temporary profile'}
            $serverSourceHash=(Get-AegisServerFileEvidence $ServerFixtureSettings.ProductPath 'Product').Sha256
            $serverConfigHash=(Get-AegisServerFileEvidence $ServerFixtureSettings.ConfigPath 'Config').Sha256
            $serverFixtureEnvironment=Get-AegisServerEnvironment
            if ($serverKind -eq 'Preflight') {
                $serverEvidence=New-ServerCasePreflight $serverSourceHash $serverConfigHash $ServerFixtureSettings.Iterations $serverFixtureEnvironment
                if ($ServerFixtureMode -eq 'Mutation') { $serverEvidence.Results[0].InspectResult.Counters.Mutations=1 }
            } else {
                $serverEvidence=New-ServerCaseSemantic $serverKind $serverSourceHash $serverFixtureEnvironment
                if ($ServerFixtureMode -eq 'SemanticFail' -and $serverKind -eq 'Behavior') { $serverEvidence.Passed=1;$serverEvidence.Failed=1;$serverEvidence.Cases[0].Status='FAIL' }
                if ($ServerFixtureMode -eq 'Malformed' -and $serverKind -eq 'Storage') { [void]$serverEvidence.Remove('Total') }
                if ($ServerFixtureMode -eq 'SourceChanged' -and $serverKind -eq 'Behavior') { [IO.File]::AppendAllText($ServerFixtureSettings.ConfigPath,'#changed') }
            }
            $serverEvidence | Export-Clixml -Path $RawReportPath -Depth 16
            return @{Evidence=(Import-Clixml -Path $RawReportPath);InvocationError=$null}
        }
        if ($ServerFixtureMode -eq 'HashUnavailable') {
            function Get-AegisServerFileEvidence { param($Path,$Id) throw 'PRIVATE-HASH-POLICY-SENTINEL' }
        }
        Invoke-AegisServerCheck $ServerFixtureSettings
    } $Settings $Mode)
}

try {
    Invoke-ServerCase 'SC01' 'Reject network, wildcard, provider and oversized paths' {
        Assert-ServerCaseThrows { Resolve-AegisServerLocalPath '\\server\share\evidence' }
        Assert-ServerCaseThrows { Resolve-AegisServerLocalPath 'Registry::HKEY_LOCAL_MACHINE' }
        Assert-ServerCaseThrows { Resolve-AegisServerLocalPath 'some[glob]' }
        $serverLarge=Join-Path $serverCaseRoot 'large';[IO.File]::WriteAllText($serverLarge,('x'*10))
        Assert-ServerCaseThrows { Resolve-AegisServerLocalPath $serverLarge $true 9 }
    }
    Invoke-ServerCase 'SC02' 'Modern runtime cannot pass a PS2 semantic gate' {
        $serverEnvironment=New-ServerCaseEnvironment $false
        $serverRaw=New-ServerCaseSemantic 'Behavior' 'aaa' (New-ServerCaseEnvironment)
        $serverDecision=Test-AegisServerSuiteEvidence $serverRaw 'Behavior' 'aaa' $serverEnvironment
        Assert-ServerCase ($serverDecision.Status -eq 'NOT_RUN') 'Non-target runtime accepted a PS2 assertion.'
    }
    Invoke-ServerCase 'SC03' 'Semantic evidence requires source, runtime and exact case counts' {
        $serverEnvironment=New-ServerCaseEnvironment
        foreach ($serverKind in @('Behavior','Storage','Planner')) {
            $serverRaw=New-ServerCaseSemantic $serverKind 'aaa' $serverEnvironment
            Assert-ServerCase ((Test-AegisServerSuiteEvidence $serverRaw $serverKind 'aaa' $serverEnvironment).Status -eq 'PASS') 'Valid private evidence rejected.'
            Assert-ServerCase ((Test-AegisServerSuiteEvidence $serverRaw $serverKind 'bbb' $serverEnvironment).Status -eq 'FAIL') 'Stale hash accepted.'
            $serverRaw.Cases=@(@{Status='PASS'})
            Assert-ServerCase ((Test-AegisServerSuiteEvidence $serverRaw $serverKind 'aaa' $serverEnvironment).Status -eq 'FAIL') 'Case-count mismatch accepted.'
        }
    }
    Invoke-ServerCase 'SC04' 'Read-only evidence requires actual target runtime and matching iterations' {
        $serverEnvironment=New-ServerCaseEnvironment
        $serverRaw=New-ServerCasePreflight 'aaa' 'bbb' 3 $serverEnvironment
        Assert-ServerCase ((Test-AegisServerPreflightEvidence $serverRaw 'aaa' 'bbb' 3 $serverEnvironment).Status -eq 'PASS') 'Valid private evidence rejected.'
        Assert-ServerCase ((Test-AegisServerPreflightEvidence $serverRaw 'aaa' 'bbb' 3 (New-ServerCaseEnvironment $false)).Status -eq 'NOT_RUN') 'Modern runtime was promoted to Windows PS2.'
        Assert-ServerCase ((Test-AegisServerPreflightEvidence $serverRaw 'aaa' 'bbb' 2 $serverEnvironment).Status -eq 'FAIL') 'Iteration mismatch accepted.'
    }
    Invoke-ServerCase 'SC05' 'Mutation counters, partial results and missing cleanup reject read-only PASS' {
        $serverEnvironment=New-ServerCaseEnvironment
        foreach ($serverVariant in @('Mutation','Partial','Cleanup','FlagString','MissingMetric')) {
            $serverRaw=New-ServerCasePreflight 'aaa' 'bbb' 3 $serverEnvironment
            switch ($serverVariant) {
                'Mutation' { $serverRaw.Results[0].InspectResult.Counters.Mutations=1 }
                'Partial' { $serverRaw.Status='Partial' }
                'Cleanup' { $serverRaw.GlobalsRestored=$false }
                'FlagString' { $serverRaw.NativeContextExecuted='true' }
                'MissingMetric' { [void]$serverRaw.Summary.Remove('CpuMeanMs') }
            }
            Assert-ServerCase ((Test-AegisServerPreflightEvidence $serverRaw 'aaa' 'bbb' 3 $serverEnvironment).Status -eq 'FAIL') ('Accepted invalid variant: '+$serverVariant)
        }
    }
    Invoke-ServerCase 'SC06' 'All Aegis globals restore original references and remove new variables' {
        $global:AegisLayoutProfile=@{Marker='Original reference'};$serverOriginal=$global:AegisLayoutProfile
        $serverSaved=Get-AegisServerGlobalSnapshot
        try { Clear-AegisServerGlobals $serverSaved;$global:AegisLayoutProfile=@{};$global:AegisServerHarnessNew=1 }
        finally { $serverRestored=Restore-AegisServerGlobals $serverSaved }
        Assert-ServerCase ($serverRestored -and [object]::ReferenceEquals($serverOriginal,$global:AegisLayoutProfile)) 'Original reference not restored.'
        Assert-ServerCase ($null -eq (Get-Variable AegisServerHarnessNew -Scope Global -ErrorAction SilentlyContinue)) 'New Aegis variable leaked.'
    }
    Invoke-ServerCase 'SC07' 'Read-only caller globals block isolation without forced changes' {
        Set-Variable -Name AegisServerHarnessReadOnly -Value 'Original' -Scope Global -Option ReadOnly
        try {
            Assert-ServerCaseThrows { Get-AegisServerGlobalSnapshot }
            Assert-ServerCase ($global:AegisServerHarnessReadOnly -eq 'Original') 'Read-only value changed.'
        } finally { Remove-Variable -Name AegisServerHarnessReadOnly -Scope Global -Force }
    }
    Invoke-ServerCase 'SC08' 'Public unsupported-host run never loads fixture product or suite scripts' {
        if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT -and $PSVersionTable.PSVersion.Major -eq 2) { return }
        $serverSettings=New-ServerCasePackage
        $serverOriginal=$global:AegisLayoutProfile;$serverBeforePreference=$ErrorActionPreference
        $serverResult=& { param($serverPath,$serverArgs) function Write-Host {param($Object)};& $serverPath @serverArgs } $RunnerPath @{ProductPath=$serverSettings.ProductPath;ConfigPath=$serverSettings.ConfigPath;OutputDirectory=$serverSettings.OutputDirectory;Iterations=1}
        $serverEvidence=Import-Clixml (Join-Path (Join-Path $serverSettings.OutputDirectory $serverResult.RunId) 'Run-Evidence.clixml')
        Assert-ServerCase ($serverResult.AutomaticStatus -eq 'UNSUPPORTED' -and $serverResult.DeploymentGate -eq 'HOLD') 'Unsupported host misreported.'
        Assert-ServerCase ((Get-ServerCaseGate $serverEvidence 'NativeReadOnly').Status -eq 'NOT_RUN' -and -not $serverEvidence.NativeReadOnlyExecuted) 'Native operation unexpectedly ran.'
        Assert-ServerCase ([object]::ReferenceEquals($serverOriginal,$global:AegisLayoutProfile) -and $ErrorActionPreference -eq $serverBeforePreference) 'Public runner changed caller state.'
    }
    Invoke-ServerCase 'SC09' 'Private target orchestration produces evidence while deployment stays HOLD' {
        $serverSettings=New-ServerCasePackage;$script:ServerCaseStubCalls.Clear()
        $serverBeforePreference=$ErrorActionPreference;Set-StrictMode -Version 2
        $serverReport=Invoke-ServerCasePrivateCollector $serverSettings
        Assert-ServerCase ($serverReport.AutomaticStatus -eq 'COMPLETE_READ_ONLY' -and $serverReport.DeploymentGate -eq 'HOLD') 'Read-only aggregate incorrect.'
        Assert-ServerCase ($script:ServerCaseStubCalls.Count -eq 4) 'Expected three semantic plus one preflight stub.'
        Assert-ServerCase ($ErrorActionPreference -eq $serverBeforePreference) 'Caller preference leaked.'
        $serverStrictPreserved=$false;try {$null=$serverHarnessUndefinedPropertyProbe} catch {$serverStrictPreserved=$true}
        Assert-ServerCase $serverStrictPreserved 'Caller strict mode changed.'
        foreach ($serverId in @('EntryPoint','RealAppAcceptance','TrayAcceptance','SessionAcceptance','DpiAcceptance','PerformanceAcceptance')) {
            Assert-ServerCase ((Get-ServerCaseGate $serverReport $serverId).Status -eq 'NOT_RUN') ('Manual gate was promoted: '+$serverId)
        }
    }
    Invoke-ServerCase 'SC10' 'Unique folders preserve earlier evidence bytes across repeated runs' {
        $serverSettings=New-ServerCasePackage
        $serverFirst=Invoke-ServerCasePrivateCollector $serverSettings
        $serverFirstFile=Join-Path (Join-Path $serverSettings.OutputDirectory $serverFirst.RunId) 'Run-Evidence.clixml'
        $serverFirstBytes=[Convert]::ToBase64String([IO.File]::ReadAllBytes($serverFirstFile))
        $serverSecond=Invoke-ServerCasePrivateCollector $serverSettings
        Assert-ServerCase ($serverFirst.RunId -ne $serverSecond.RunId -and [IO.Directory]::GetDirectories($serverSettings.OutputDirectory).Length -eq 2) 'Evidence directory reused.'
        Assert-ServerCase ($serverFirstBytes -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($serverFirstFile))) 'Earlier evidence overwritten.'
    }
    Invoke-ServerCase 'SC11' 'Summary omits machine, user path and title fields from raw preflight' {
        $serverSettings=New-ServerCasePackage;$serverReport=Invoke-ServerCasePrivateCollector $serverSettings
        $serverDirectory=Join-Path $serverSettings.OutputDirectory $serverReport.RunId
        foreach ($serverSummaryName in @('Summary.txt','Run-Evidence.clixml')) {
            $serverText=[IO.File]::ReadAllText((Join-Path $serverDirectory $serverSummaryName))
            Assert-ServerCase ($serverText -notmatch 'PRIVATE-(MACHINE|USER|WINDOW)-SENTINEL') 'Private metadata leaked to summary.'
        }
        Assert-ServerCase ([IO.File]::ReadAllText((Join-Path $serverDirectory 'Raw-Preflight.clixml')) -match 'PRIVATE-WINDOW-SENTINEL') 'Raw evidence fixture did not exercise privacy boundary.'
    }
    Invoke-ServerCase 'SC12' 'Semantic failure prevents native preflight and restores caller state' {
        $serverSettings=New-ServerCasePackage;$script:ServerCaseStubCalls.Clear();$serverOriginal=$global:AegisLayoutProfile
        $serverReport=Invoke-ServerCasePrivateCollector $serverSettings 'SemanticFail'
        Assert-ServerCase ($serverReport.AutomaticStatus -eq 'FAIL' -and (Get-ServerCaseGate $serverReport 'NativeReadOnly').Status -eq 'NOT_RUN') 'Failed prerequisites allowed native stage.'
        Assert-ServerCase ($script:ServerCaseStubCalls -notcontains 'Preflight') 'Preflight was invoked after semantic failure.'
        Assert-ServerCase ([object]::ReferenceEquals($serverOriginal,$global:AegisLayoutProfile) -and $serverReport.GlobalsRestored) 'Failure failed to restore caller state.'
    }
    Invoke-ServerCase 'SC13' 'Nonzero mutation report fails collection and restores caller state' {
        $serverSettings=New-ServerCasePackage;$serverOriginal=$global:AegisLayoutProfile
        $serverReport=Invoke-ServerCasePrivateCollector $serverSettings 'Mutation'
        Assert-ServerCase ($serverReport.AutomaticStatus -eq 'FAIL' -and (Get-ServerCaseGate $serverReport 'NativeReadOnly').Status -eq 'FAIL') 'Mutation report passed.'
        Assert-ServerCase ([object]::ReferenceEquals($serverOriginal,$global:AegisLayoutProfile) -and $serverReport.GlobalsRestored) 'Preflight failure leaked globals.'
    }
    Invoke-ServerCase 'SC14' 'Source changes are detected before further invocation and at completion' {
        $serverSettings=New-ServerCasePackage;$script:ServerCaseStubCalls.Clear()
        $serverReport=Invoke-ServerCasePrivateCollector $serverSettings 'SourceChanged'
        Assert-ServerCase ((Get-ServerCaseGate $serverReport 'SourceStable').Status -eq 'FAIL' -and $script:ServerCaseStubCalls.Count -eq 1) 'Changed source was not blocked before next stage.'
    }
    Invoke-ServerCase 'SC15' 'Hash-provider failures persist explicit failure evidence without policy changes' {
        $serverSettings=New-ServerCasePackage;$script:ServerCaseStubCalls.Clear()
        $serverReport=Invoke-ServerCasePrivateCollector $serverSettings 'HashUnavailable'
        Assert-ServerCase ((Get-ServerCaseGate $serverReport 'SourceHashes').Status -eq 'FAIL' -and $serverReport.AutomaticStatus -eq 'FAIL') 'Hash failure hidden.'
        Assert-ServerCase ($script:ServerCaseStubCalls.Count -eq 0 -and -not $serverReport.NativeReadOnlyExecuted) 'Hash failure allowed execution.'
        $serverDirectory=Join-Path $serverSettings.OutputDirectory $serverReport.RunId
        Assert-ServerCase ([IO.File]::Exists((Join-Path $serverDirectory 'Raw-Errors.clixml'))) 'Hash failure evidence missing.'
        Assert-ServerCase ([IO.File]::ReadAllText((Join-Path $serverDirectory 'Summary.txt')) -notmatch 'PRIVATE-HASH-POLICY-SENTINEL') 'Raw exception text leaked to summary.'
    }
    Invoke-ServerCase 'SC16' 'PS2 on CLR4 does not establish the CLR2 runtime gate' {
        $serverReport=Invoke-ServerCasePrivateCollector (New-ServerCasePackage) 'Clr4'
        Assert-ServerCase ((Get-ServerCaseGate $serverReport 'WindowsPS2').Status -eq 'PASS' -and (Get-ServerCaseGate $serverReport 'Clr2').Status -eq 'NOT_RUN') 'CLR4 was conflated with CLR2.'
        Assert-ServerCase ($serverReport.AutomaticStatus -eq 'INCOMPLETE' -and $serverReport.DeploymentGate -eq 'HOLD') 'CLR2 gap did not keep incomplete status.'
    }
    Invoke-ServerCase 'SC17' 'Malformed semantic reports cannot become successful zero-test runs' {
        $serverReport=Invoke-ServerCasePrivateCollector (New-ServerCasePackage) 'Malformed'
        Assert-ServerCase ((Get-ServerCaseGate $serverReport 'Storage').Status -eq 'FAIL' -and (Get-ServerCaseGate $serverReport 'NativeReadOnly').Status -eq 'NOT_RUN') 'Malformed evidence accepted.'
    }
    Invoke-ServerCase 'SC18' 'Production runtime fields come from the public environment function' {
        $serverActual=Get-AegisServerEnvironment
        Assert-ServerCase ($serverActual.PowerShellVersion -ceq [string]$PSVersionTable.PSVersion -and $serverActual.ClrVersion -ceq [Environment]::Version.ToString()) 'Private harness runtime leaked into public function.'
        Assert-ServerCase ($serverActual.TargetRuntime -eq ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT -and $PSVersionTable.PSVersion.Major -eq 2)) 'Runtime gate differs from actual process.'
    }
    Invoke-ServerCase 'SC19' 'Inherited WhatIf rejects before output or global changes' {
        $serverSettings=New-ServerCasePackage;$serverOriginal=$global:AegisLayoutProfile
        & {
            param($ServerWhatIfSettings)
            $WhatIfPreference=$true
            Assert-ServerCaseThrows { Invoke-AegisServerCheck $ServerWhatIfSettings }
            Assert-ServerCase ($WhatIfPreference) 'Caller WhatIf preference changed.'
        } $serverSettings
        Assert-ServerCase (-not [IO.Directory]::Exists($serverSettings.OutputDirectory)) 'WhatIf created an evidence directory.'
        Assert-ServerCase ([object]::ReferenceEquals($serverOriginal,$global:AegisLayoutProfile)) 'WhatIf changed caller globals.'
    }
    Invoke-ServerCase 'SC20' 'Low confirmation preference cannot hang internal changes and remains unchanged' {
        & {
            $ConfirmPreference='Low'
            $serverSettings=New-ServerCasePackage
            $serverReport=Invoke-ServerCasePrivateCollector $serverSettings
            Assert-ServerCase ($serverReport.GlobalsRestored -and $serverReport.AutomaticStatus -eq 'COMPLETE_READ_ONLY') 'Confirmation preference interrupted collection.'
            Assert-ServerCase ($ConfirmPreference -eq 'Low') 'Caller confirmation preference changed.'
        }
    }
    $serverFailed=@($serverCaseResults | Where-Object {$_.Status -eq 'FAIL'}).Count
    $serverCaseReport=@{
        Suite='Aegis server collector development harness';Scope='Private stub orchestration and unsupported-host public branch; no Windows API calls.'
        RunnerSha256=(Get-AegisServerFileEvidence $RunnerPath 'Collector').Sha256
        CollectorSha256=(Get-AegisServerFileEvidence $RunnerPath 'Collector').Sha256
        ProductSha256=(Get-AegisServerFileEvidence $ProductPath 'Product').Sha256
        EngineVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[Environment]::Version.ToString()
        ActualWindowsIntegration='NOT_RUN';ActualPS2ServerAcceptance='NOT_RUN'
        Total=$serverCaseResults.Count;Passed=($serverCaseResults.Count-$serverFailed);Failed=$serverFailed;Cases=$serverCaseResults.ToArray()
    }
    if (-not [string]::IsNullOrEmpty($ReportPath)) { $serverCaseReport | Export-Clixml -Path $ReportPath -Depth 10 }
    $serverCaseReport
    if ($serverFailed -gt 0) { throw ('Server collector development failures: '+$serverFailed) }
} finally {
    [void](Restore-AegisServerGlobals $serverCaseOriginalGlobals)
    if ([IO.Directory]::Exists($serverCaseRoot)) { [IO.Directory]::Delete($serverCaseRoot,$true) }
    $ErrorActionPreference=$serverCaseOldPreference
}
