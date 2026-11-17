#requires -version 2.0
<#
Aegis v4 read-only Windows preflight. Windows PowerShell 2.x source target.

Runs the actual Inspect path with an explicit CSV allowlist. Inspect does not
move, resize, restore, show, hide, activate, or change window Z order. It can
query selected applications with WM_GETMINMAXINFO; it is not a zero-impact scan.
No recurring task, privilege change, or service/process modification is made.

Examples, from the package directory:
  .\verification\Test-WindowsPreflight.ps1 -ConfigPath .\Aegis.Processes.csv
  .\verification\Test-WindowsPreflight.ps1 -ConfigPath .\Aegis.Processes.csv -ReportPath .\preflight.clixml -Iterations 3

Only an explicit ReportPath writes a file. No directory is created. The report
contains window/process metadata and paths; review it before sharing.
Memory figures are before/after snapshots, NOT peak memory. Three or even ten
runs do not establish P95/P99. No application mutation acceptance is executed.
PowerShell process launch is outside measured scope. Setup/load/native/DPI time
is reported separately from per-Inspect time.
#>
[CmdletBinding()]
param(
    [string]$ScriptPath='',
    [string]$ConfigPath='',
    [string]$ReportPath='',
    [ValidateRange(1,10)][int]$Iterations=3
)

$preflightHarnessPath=$MyInvocation.MyCommand.Path
$preflightPackageRoot=Split-Path -Parent (Split-Path -Parent $preflightHarnessPath)
. (Join-Path (Join-Path $preflightPackageRoot 'tests') 'ReportPathSafety.ps1')
$preflightProtectedProduct=$ScriptPath
if ([string]::IsNullOrEmpty($preflightProtectedProduct)) { $preflightProtectedProduct=Join-Path $preflightPackageRoot 'Aegis.ps1' }
$ReportPath=Resolve-AegisHarnessReportPath -Path $ReportPath -ProductPath $preflightProtectedProduct -HarnessPath $preflightHarnessPath -PackageRoot $preflightPackageRoot -AdditionalProtectedPaths @($ConfigPath)

function Get-AegisPreflightFileHash {
    param([string]$Path)
    $algorithm=[Security.Cryptography.SHA256]::Create()
    $stream=$null
    try {
        $stream=[IO.File]::OpenRead($Path)
        return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant()
    } finally {
        if ($null -ne $stream) { $stream.Close() }
        $algorithm.Clear()
    }
}

function Get-AegisPreflightProcessSnapshot {
    param($Process)
    $Process.Refresh()
    return @{
        CpuTicks=[long]$Process.TotalProcessorTime.Ticks
        PrivateMemoryBytes=[long]$Process.PrivateMemorySize64
        WorkingSetBytes=[long]$Process.WorkingSet64
        HandleCount=[int]$Process.HandleCount
    }
}

function Invoke-AegisWindowsPreflight {
    param([hashtable]$Settings)
    # Function scope preserves the caller's strict/error preferences.
    Set-StrictMode -Off
    $ErrorActionPreference='Stop'
    $diagResults=New-Object Collections.ArrayList
    $diagWarnings=New-Object Collections.ArrayList
    $diagSavedGlobals=@{}
    $diagGlobalNames=@('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult','AegisLastExitCode')
    $diagIsolated=$false; $diagDpi=$null; $diagProcess=$null; $diagMutex=$null; $diagOwnsMutex=$false
    $diagReport=@{
        SchemaVersion=1; Suite='AegisWindowsReadOnlyPreflight'; Status='NotStarted'; Reason=''
        StartedUtc=[DateTime]::UtcNow.ToString('o'); CompletedUtc=''
        Environment=@{MachineName=[Environment]::MachineName;Platform=[Environment]::OSVersion.Platform.ToString();OSVersion=[Environment]::OSVersion.VersionString;PowerShellVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[Environment]::Version.ToString();ProcessBitness=([IntPtr]::Size*8)}
        ProductPath='';ProductSha256='';ConfigPath='';ConfigSha256='';NormalizedRuleCount=0;AllowedRuleCount=0
        NativeContextExecuted=$false;InspectExecuted=$false;WindowsPowerShell2Executed=$false
        AppMutationAcceptanceExecuted=$false;RequestedIterations=$Settings.Iterations;CompletedIterations=0
        SetupDurationMs=0;SetupBefore=$null;SetupAfter=$null;Context=$null;DpiEntry=$null;DpiExit=$null
        Results=@();Warnings=@();Summary=$null;GlobalsRestored=$true;SavedReportPath=''
        MeasurementScope=@{
            Action='Inspect only; native backend permits Context/Observe only.'
            Timing='Per-run stopwatch around actual Inspect; PowerShell process launch excluded; setup reported separately.'
            Cpu='Current PowerShell process TotalProcessorTime delta; not system or target-app CPU.'
            Memory='PrivateMemorySize64 and WorkingSet64 before/after snapshots; not peak or retained-only allocation.'
            Handles='Current PowerShell process HandleCount before/after; not app handles.'
            Statistics='Small sequential sample; no P95/P99 or production stability claim.'
            State='Layout/Undo/pending/result globals are isolated then restored; existing pending requests are not reconciled by this diagnostic.'
        }
    }
    $diagSetup=[Diagnostics.Stopwatch]::StartNew()
    try {
        $diagProduct=$Settings.ScriptPath
        if ([string]::IsNullOrEmpty($diagProduct)) { $diagProduct=$Settings.DefaultProductPath }
        $diagProduct=(Resolve-Path -LiteralPath $diagProduct).ProviderPath
        if (-not (Test-Path -LiteralPath $diagProduct -PathType Leaf)) { throw 'Product script is not a file.' }
        $diagReport.ProductPath=$diagProduct; $diagReport.ProductSha256=Get-AegisPreflightFileHash $diagProduct
        if (-not [string]::IsNullOrEmpty($Settings.ConfigPath)) {
            $diagConfig=(Resolve-Path -LiteralPath $Settings.ConfigPath).ProviderPath
            if (-not (Test-Path -LiteralPath $diagConfig -PathType Leaf)) { throw 'Configuration is not a file.' }
            $diagReport.ConfigPath=$diagConfig; $diagReport.ConfigSha256=Get-AegisPreflightFileHash $diagConfig
        }
        # No product/native initialization or window API on unsupported systems.
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
            $diagReport.Status='NotRun'; $diagReport.Reason='UnsupportedPlatform'; return $diagReport
        }
        foreach ($diagName in $diagGlobalNames) {
            $diagVariable=Get-Variable -Name $diagName -Scope Global -ErrorAction SilentlyContinue
            $diagSavedGlobals[$diagName]=@{Exists=($null -ne $diagVariable);Value=$null}
            if ($null -ne $diagVariable) { $diagSavedGlobals[$diagName].Value=$diagVariable.Value }
        }
        # Snapshot references remain untouched: the controller sees fresh state.
        $diagIsolated=$true
        foreach ($diagName in $diagGlobalNames) { Set-Variable -Name $diagName -Scope Global -Value $null }
        $global:AegisPendingMoves=@()
        . $diagProduct -Action Library
        $diagRules=@()
        if ($diagReport.ConfigPath -ne '') { $diagRules=@(Import-AegisProcessRules -Path $diagReport.ConfigPath) }
        $diagRules=@(ConvertTo-AegisRules $diagRules)
        $diagOptions=New-AegisOptions
        $diagReport.NormalizedRuleCount=$diagRules.Count
        $diagReport.AllowedRuleCount=@($diagRules | Where-Object {$_.Include}).Count
        if ($diagReport.AllowedRuleCount -eq 0) { [void]$diagWarnings.Add('Empty allowlist: native context/enumeration can be measured, but no configured app snapshot or minmax query is covered.') }
        $diagOldPending=$diagSavedGlobals['AegisPendingMoves'].Value
        if ($null -ne $diagOldPending -and @($diagOldPending).Count -gt 0) { [void]$diagWarnings.Add('Existing pending requests were preserved without diagnostic reconciliation. Their OS-side completion can still occur independently.') }
        $diagMutex=New-Object Threading.Mutex ($false,'Local\Aegis_WindowLayout_v3')
        try { $diagOwnsMutex=$diagMutex.WaitOne(0,$false) } catch [Threading.AbandonedMutexException] { $diagOwnsMutex=$true }
        if (-not $diagOwnsMutex) { $diagReport.Status='Blocked';$diagReport.Reason='AnotherAegisOperationIsActive';return $diagReport }
        $diagProcess=[Diagnostics.Process]::GetCurrentProcess()
        $diagReport.SetupBefore=Get-AegisPreflightProcessSnapshot $diagProcess
        $diagDpi=Enter-AegisDpiContext; $diagReport.DpiEntry=$diagDpi
        $diagReport.NativeContextExecuted=$true
        $diagContext=Invoke-AegisNative 'Context' $null $null
        $diagReport.Context=$diagContext
        if (-not $diagContext.Complete -or -not $diagContext.DesktopSafe -or -not $diagContext.Ready) { $diagReport.Status='Blocked';$diagReport.Reason=$diagContext.Reason;return $diagReport }
        $diagReport.SetupAfter=Get-AegisPreflightProcessSnapshot $diagProcess
        $diagSetup.Stop(); $diagReport.SetupDurationMs=[long]$diagSetup.ElapsedMilliseconds
        $diagBackend={
            param($Operation,$Window,$Target)
            if (@('Context','Observe') -notcontains $Operation) { throw 'PreflightRejectedMutationOperation' }
            return (Invoke-AegisNative $Operation $Window $Target)
        }
        for ($diagIndex=1;$diagIndex -le $Settings.Iterations;$diagIndex++) {
            # Reset only diagnostic state; preserve the user's original references.
            $global:AegisLayoutProfile=$null;$global:AegisUndoState=$null;$global:AegisPendingMoves=@()
            $diagBefore=Get-AegisPreflightProcessSnapshot $diagProcess
            $diagRunWatch=[Diagnostics.Stopwatch]::StartNew()
            $diagActual=Invoke-AegisController -Action Inspect -Options $diagOptions -Rules $diagRules -Backend $diagBackend
            $diagRunWatch.Stop()
            $diagAfter=Get-AegisPreflightProcessSnapshot $diagProcess
            $diagCpuMs=([double]($diagAfter.CpuTicks-$diagBefore.CpuTicks)/[TimeSpan]::TicksPerMillisecond)
            $diagRow=@{
                Iteration=$diagIndex;ElapsedMs=[long]$diagRunWatch.ElapsedMilliseconds;CpuMs=$diagCpuMs
                Before=$diagBefore;After=$diagAfter
                PrivateMemoryDeltaBytes=([long]$diagAfter.PrivateMemoryBytes-$diagBefore.PrivateMemoryBytes)
                WorkingSetDeltaBytes=([long]$diagAfter.WorkingSetBytes-$diagBefore.WorkingSetBytes)
                HandleDelta=($diagAfter.HandleCount-$diagBefore.HandleCount)
                InspectResult=$diagActual
            }
            [void]$diagResults.Add($diagRow)
            $diagReport.InspectExecuted=$true
            $diagReport.WindowsPowerShell2Executed=($PSVersionTable.PSVersion.Major -eq 2)
            $diagReport.CompletedIterations=$diagResults.Count
            if ($diagActual.Counters.Mutations -ne 0) { throw 'InspectAttemptedMutation: diagnostic backend rejected all write operations.' }
            if ($diagActual.Status -ne 'Complete' -and $diagActual.Status -ne 'Partial') {
                $diagReport.Status='Blocked';$diagReport.Reason=('Inspect:'+ $diagActual.Status+':'+$diagActual.Detail);break
            }
        }
        if ($diagReport.Status -eq 'NotStarted') { $diagReport.Status='Complete';$diagReport.Reason='ReadOnlySamplesCollected' }
        foreach ($diagRow in $diagResults) {
            if ($diagRow.InspectResult.Status -ne 'Complete' -and $diagReport.Status -eq 'Complete') { $diagReport.Status='Partial';$diagReport.Reason='InspectReportedPartialCoverage' }
        }
        if ($diagResults.Count -gt 0) {
            [double]$diagTimeSum=0;[double]$diagCpuSum=0;[long]$diagMin=[long]::MaxValue;[long]$diagMax=0
            foreach ($diagRow in $diagResults) { $diagTimeSum+=$diagRow.ElapsedMs;$diagCpuSum+=$diagRow.CpuMs;$diagMin=[Math]::Min($diagMin,$diagRow.ElapsedMs);$diagMax=[Math]::Max($diagMax,$diagRow.ElapsedMs) }
            $diagReport.Summary=@{Count=$diagResults.Count;ElapsedMeanMs=($diagTimeSum/$diagResults.Count);ElapsedMinMs=$diagMin;ElapsedMaxMs=$diagMax;CpuMeanMs=($diagCpuSum/$diagResults.Count);PeakMemoryMeasured=$false;P95Measured=$false;AppMutationAcceptanceExecuted=$false}
        }
        return $diagReport
    } catch { $diagReport.Status='Failed';$diagReport.Reason=$_.Exception.Message; return $diagReport }
    finally {
        if ($diagSetup.IsRunning) { $diagSetup.Stop();$diagReport.SetupDurationMs=[long]$diagSetup.ElapsedMilliseconds }
        if ($null -ne $diagDpi) {
            try {
                $diagLeave=Exit-AegisDpiContext $diagDpi; $diagReport.DpiExit=$diagLeave
                if (-not $diagLeave.Accepted) { [void]$diagWarnings.Add(('DpiRestore:'+ $diagLeave.Reason));$diagReport.Status='Partial' }
            } catch { [void]$diagWarnings.Add(('DpiRestoreException:'+ $_.Exception.Message));$diagReport.Status='Partial' }
        }
        if ($null -ne $diagProcess) { $diagProcess.Dispose() }
        if ($diagOwnsMutex -and $null -ne $diagMutex) { try { [void]$diagMutex.ReleaseMutex() } catch { [void]$diagWarnings.Add('MutexReleaseFailed');$diagReport.Status='Partial' } }
        if ($null -ne $diagMutex) { $diagMutex.Close() }
        if ($diagIsolated) {
            foreach ($diagName in $diagGlobalNames) {
                try {
                    if ($diagSavedGlobals[$diagName].Exists) { Set-Variable -Name $diagName -Scope Global -Value $diagSavedGlobals[$diagName].Value }
                    else { Remove-Variable -Name $diagName -Scope Global -ErrorAction SilentlyContinue }
                } catch { $diagReport.GlobalsRestored=$false;[void]$diagWarnings.Add(('GlobalRestoreFailed:'+ $diagName));$diagReport.Status='Partial' }
            }
        }
        $diagReport.Results=$diagResults.ToArray();$diagReport.Warnings=$diagWarnings.ToArray();$diagReport.CompletedUtc=[DateTime]::UtcNow.ToString('o')
    }
}

$preflightDefaultProduct=Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) 'Aegis.ps1'
$preflightSettings=@{ScriptPath=$ScriptPath;ConfigPath=$ConfigPath;ReportPath=$ReportPath;Iterations=$Iterations;DefaultProductPath=$preflightDefaultProduct}
$preflightReport=Invoke-AegisWindowsPreflight $preflightSettings
if (-not [string]::IsNullOrEmpty($ReportPath)) {
    try {
        $preflightOutputPath=[IO.Path]::GetFullPath($ReportPath)
        if ($preflightOutputPath -match '[*?\[\]]') { throw 'ReportPath must be a literal path without wildcard characters.' }
        if ([string]::Equals($preflightOutputPath,[string]$preflightReport.ProductPath,[StringComparison]::OrdinalIgnoreCase) -or [string]::Equals($preflightOutputPath,[string]$preflightReport.ConfigPath,[StringComparison]::OrdinalIgnoreCase)) { throw 'ReportPath cannot overwrite the product or configuration.' }
        $preflightReport.SavedReportPath=$preflightOutputPath
        $preflightReport | Export-Clixml -Path $preflightOutputPath -Depth 32 -ErrorAction Stop
    } catch { $preflightReport.SavedReportPath='';$preflightReport.Warnings=@($preflightReport.Warnings)+@(('ReportSaveFailed:'+ $_.Exception.Message)) }
}
$preflightReport
