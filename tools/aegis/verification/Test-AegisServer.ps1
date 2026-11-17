#requires -version 2.0
<#
.SYNOPSIS
Collects actual-server evidence without arranging, restoring or resizing windows.
.DESCRIPTION
Run in an existing Windows PowerShell 2.0 session. No execution-policy changes,
elevation, network access, installations or background loop are requested.
OutputDirectory authorizes creation of one new, unique evidence subdirectory.
Other runtimes write environment/hash evidence and mark target tests NOT_RUN.

The public runner has no injected runtime or backend option. Its semantic tests
use synthetic boundaries; Windows preflight only permits Context and Observe.
EntryPoint tests are intentionally excluded: their invalid Arrange test must not
become a native mutation if the guard being tested regresses.

Summary.txt contains counters, hashes and versions, but no machine/user names,
window titles or absolute paths. Raw preflight/error evidence can contain machine
names, local paths, process metadata and window titles. Review before sharing.
Read-only samples never establish real-app, RDP/tray/DPI or performance acceptance.
.EXAMPLE
powershell.exe -Version 2.0 -NoProfile -File .\verification\Test-AegisServer.ps1 -OutputDirectory C:\AegisEvidence
#>
[CmdletBinding()]
param(
    [string]$ProductPath='',
    [string]$ConfigPath='',
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$OutputDirectory,
    [ValidateRange(1,10)][int]$Iterations=3
)

function Get-AegisServerValue {
    param($Value,[string]$Name)
    if ($null -eq $Value) { return $null }
    if ($Value -is [System.Collections.IDictionary]) {
        if ($Value.Contains($Name)) { return $Value[$Name] }
        return $null
    }
    $serverProperty=$Value.PSObject.Properties[$Name]
    if ($null -ne $serverProperty) { return $serverProperty.Value }
    return $null
}

function ConvertTo-AegisServerCount {
    param($Value)
    [int]$serverCount=0
    if ($null -eq $Value -or [string]$Value -notmatch '^[0-9]+$' -or
        -not [int]::TryParse([string]$Value,[ref]$serverCount)) { throw 'InvalidEvidenceCount' }
    return $serverCount
}

function Resolve-AegisServerLocalPath {
    param([string]$Path,[bool]$MustExist=$false,[long]$MaximumBytes=2097152)
    if ([string]::IsNullOrEmpty($Path) -or $Path.Trim().Length -eq 0) { throw 'EmptyLocalPath' }
    if ($Path -match '[*?\[\]]' -or $Path -match '^[\\/]{2}' -or $Path.IndexOf([char]0) -ge 0) { throw 'NonLiteralOrNetworkPathRejected' }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        if ($Path -match ':' -and $Path -notmatch '^[A-Za-z]:[\\/][^:]*$') { throw 'ProviderOrDevicePathRejected' }
    } elseif ($Path -match ':') { throw 'ProviderPathRejected' }
    if (-not [IO.Path]::IsPathRooted($Path)) {
        $serverLocation=Get-Location
        if ($serverLocation.Provider.Name -ne 'FileSystem') { throw 'FileSystemLocationRequired' }
        $Path=Join-Path $serverLocation.Path $Path
    }
    $serverFull=[IO.Path]::GetFullPath($Path)
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        if ($serverFull -notmatch '^[A-Za-z]:\\') { throw 'LocalDrivePathRequired' }
        $serverDrive=New-Object System.IO.DriveInfo ([IO.Path]::GetPathRoot($serverFull))
        if ($serverDrive.DriveType -eq [IO.DriveType]::Network -or $serverDrive.DriveType -eq [IO.DriveType]::Unknown) { throw 'NetworkOrUnknownDriveRejected' }
    }
    # Reject existing reparse ancestors so a local-looking path cannot redirect
    # this collector to a share, device path or a different output tree.
    $serverAncestor=$serverFull
    while (-not [string]::IsNullOrEmpty($serverAncestor)) {
        if ([IO.File]::Exists($serverAncestor) -or [IO.Directory]::Exists($serverAncestor)) {
            if (([IO.File]::GetAttributes($serverAncestor) -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'ReparsePathRejected' }
        }
        $serverParent=[IO.Path]::GetDirectoryName($serverAncestor)
        if ($serverParent -eq $serverAncestor) { break }
        $serverAncestor=$serverParent
    }
    if ($MustExist) {
        if (-not [IO.File]::Exists($serverFull)) { throw 'RequiredLocalFileMissing' }
        $serverFile=New-Object System.IO.FileInfo $serverFull
        if ($serverFile.Length -gt $MaximumBytes) { throw 'LocalFileSizeLimitExceeded' }
    }
    return $serverFull
}

function Get-AegisServerFileEvidence {
    param([string]$Path,[string]$Id)
    $serverCrypto=$null;$serverStream=$null
    try {
        $serverCrypto=[Security.Cryptography.SHA256]::Create()
        if ($null -eq $serverCrypto) { throw 'HashProviderUnavailable' }
        $serverStream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $serverLength=$serverStream.Length
        $serverDigest=[BitConverter]::ToString($serverCrypto.ComputeHash($serverStream)).Replace('-','').ToLowerInvariant()
        return @{Id=$Id;Sha256=$serverDigest;Bytes=$serverLength}
    } finally {
        if ($null -ne $serverStream) { $serverStream.Close() }
        if ($null -ne $serverCrypto) { $serverCrypto.Clear() }
    }
}

function Get-AegisServerEnvironment {
    $serverWindows=([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
    $serverPS2=($PSVersionTable.PSVersion.Major -eq 2)
    return @{
        Platform=[Environment]::OSVersion.Platform.ToString()
        OSVersion=[Environment]::OSVersion.VersionString
        PowerShellVersion=[string]$PSVersionTable.PSVersion
        ClrVersion=[Environment]::Version.ToString()
        ProcessBitness=([IntPtr]::Size*8)
        ActualWindows=$serverWindows;ActualPowerShell2=$serverPS2
        ActualClr2=([Environment]::Version.Major -eq 2)
        TargetRuntime=($serverWindows -and $serverPS2)
    }
}

function New-AegisServerGate {
    param([string]$Id,[string]$Label,[string]$Status='NOT_RUN',[string]$Reason='PrerequisiteNotRun')
    return @{Id=$Id;Label=$Label;Status=$Status;Reason=$Reason;Passed=0;Failed=0;Total=0}
}

function Set-AegisServerGate {
    param($Report,[string]$Id,[string]$Status,[string]$Reason)
    foreach ($serverGate in $Report.Gates) {
        if ($serverGate.Id -eq $Id) { $serverGate.Status=$Status;$serverGate.Reason=$Reason;return }
    }
    throw 'UnknownServerGate'
}

function Test-AegisServerSuiteEvidence {
    param($Evidence,[string]$Kind,[string]$ExpectedSha256,$Environment)
    $serverDecision=@{Status='FAIL';Reason='InvalidSemanticEvidence';Passed=0;Failed=0;Total=0}
    if (-not $Environment.TargetRuntime) { $serverDecision.Status='NOT_RUN';$serverDecision.Reason='ActualWindowsPowerShell2Required';return $serverDecision }
    try {
        $serverHashField='ProductSha256';$serverVersionField='EngineVersion';$serverRuntimeField='PowerShell2Runtime'
        if ($Kind -eq 'Storage') { $serverRuntimeField='ActualPS2Execution' }
        elseif ($Kind -eq 'Planner') { $serverHashField='SourceSha256';$serverVersionField='PowerShellVersion';$serverRuntimeField='ActualPowerShell2' }
        elseif ($Kind -ne 'Behavior') { throw 'UnknownSemanticSuite' }
        if ((Get-AegisServerValue $Evidence $serverHashField) -cne $ExpectedSha256) { throw 'SemanticSourceMismatch' }
        if ((Get-AegisServerValue $Evidence $serverVersionField) -cne $Environment.PowerShellVersion -or
            (Get-AegisServerValue $Evidence $serverRuntimeField) -cne 'RUN') { throw 'SemanticRuntimeMismatch' }
        $serverDecision.Total=ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'Total')
        $serverDecision.Passed=ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'Passed')
        $serverDecision.Failed=ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'Failed')
        if ($serverDecision.Total -eq 0 -or $serverDecision.Total -gt 10000 -or
            $serverDecision.Passed+$serverDecision.Failed -ne $serverDecision.Total) { throw 'SemanticCountMismatch' }
        $serverCases=@(Get-AegisServerValue $Evidence 'Cases')
        if ($serverCases.Count -ne $serverDecision.Total) { throw 'SemanticCaseCountMismatch' }
        $serverPassCount=0;$serverFailCount=0
        foreach ($serverCase in $serverCases) {
            $serverCaseStatus=Get-AegisServerValue $serverCase 'Status'
            if ($serverCaseStatus -ceq 'PASS') { $serverPassCount++ }
            elseif ($serverCaseStatus -ceq 'FAIL') { $serverFailCount++ }
            else { throw 'UnknownSemanticCaseStatus' }
        }
        if ($serverPassCount -ne $serverDecision.Passed -or $serverFailCount -ne $serverDecision.Failed) { throw 'SemanticCaseStatusMismatch' }
        if ($serverDecision.Failed -ne 0) { $serverDecision.Reason='SemanticAssertionsFailed';return $serverDecision }
        $serverDecision.Status='PASS';$serverDecision.Reason='ActualPS2SyntheticBoundaryPassed'
    } catch { $serverDecision.Reason='SemanticEvidenceRejected' }
    return $serverDecision
}

function Test-AegisServerPreflightEvidence {
    param($Evidence,[string]$ProductSha256,[string]$ConfigSha256,[int]$Iterations,$Environment)
    $serverDecision=@{Status='FAIL';Reason='InvalidReadOnlyEvidence';Iterations=0;AllowedRules=0;ObservedItems=0;Mutations=0;ResourceSamples=$null;ProductVersion=''}
    if (-not $Environment.TargetRuntime) { $serverDecision.Status='NOT_RUN';$serverDecision.Reason='ActualWindowsPowerShell2Required';return $serverDecision }
    try {
        if ((Get-AegisServerValue $Evidence 'ProductSha256') -cne $ProductSha256 -or
            (Get-AegisServerValue $Evidence 'ConfigSha256') -cne $ConfigSha256) { throw 'PreflightSourceMismatch' }
        $serverEvidenceEnvironment=Get-AegisServerValue $Evidence 'Environment'
        if ((Get-AegisServerValue $serverEvidenceEnvironment 'PowerShellVersion') -cne $Environment.PowerShellVersion -or
            (Get-AegisServerValue $serverEvidenceEnvironment 'ClrVersion') -cne $Environment.ClrVersion -or
            (Get-AegisServerValue $serverEvidenceEnvironment 'Platform') -cne 'Win32NT') { throw 'PreflightRuntimeMismatch' }
        foreach ($serverRequiredTrue in @('NativeContextExecuted','InspectExecuted','WindowsPowerShell2Executed','GlobalsRestored')) {
            $serverFlag=Get-AegisServerValue $Evidence $serverRequiredTrue
            if ($serverFlag -isnot [bool] -or -not $serverFlag) { throw 'PreflightRequiredExecutionMissing' }
        }
        if ((Get-AegisServerValue $Evidence 'AppMutationAcceptanceExecuted') -ne $false) { throw 'UnexpectedMutationEvidence' }
        if ((Get-AegisServerValue $Evidence 'Status') -cne 'Complete') { throw 'ReadOnlyPreflightIncomplete' }
        $serverContext=Get-AegisServerValue $Evidence 'Context'
        foreach ($serverRequiredTrue in @('Complete','DesktopSafe','Ready')) {
            $serverFlag=Get-AegisServerValue $serverContext $serverRequiredTrue
            if ($serverFlag -isnot [bool] -or -not $serverFlag) { throw 'ReadOnlyContextNotReady' }
        }
        $serverDecision.Iterations=ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'CompletedIterations')
        if ($serverDecision.Iterations -ne $Iterations -or (ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'RequestedIterations')) -ne $Iterations) { throw 'PreflightIterationMismatch' }
        $serverRows=@(Get-AegisServerValue $Evidence 'Results')
        if ($serverRows.Count -ne $Iterations) { throw 'PreflightRowCountMismatch' }
        $serverDecision.AllowedRules=ConvertTo-AegisServerCount (Get-AegisServerValue $Evidence 'AllowedRuleCount')
        $serverItemCount=0;$serverExpectedIteration=1
        foreach ($serverRow in $serverRows) {
            if ((ConvertTo-AegisServerCount (Get-AegisServerValue $serverRow 'Iteration')) -ne $serverExpectedIteration) { throw 'PreflightIterationOrderMismatch' }
            $serverExpectedIteration++
            $serverInspect=Get-AegisServerValue $serverRow 'InspectResult'
            if ((Get-AegisServerValue $serverInspect 'Action') -cne 'Inspect' -or
                (Get-AegisServerValue $serverInspect 'Status') -cne 'Complete') { throw 'UnexpectedPreflightActionOrStatus' }
            $serverMutationCount=ConvertTo-AegisServerCount (Get-AegisServerValue (Get-AegisServerValue $serverInspect 'Counters') 'Mutations')
            $serverDecision.Mutations+=$serverMutationCount
            if ($serverMutationCount -ne 0) { throw 'PreflightMutationCounterNotZero' }
            $serverItems=Get-AegisServerValue $serverInspect 'Items'
            if ($null -ne $serverItems) { $serverItemCount=[Math]::Max($serverItemCount,@($serverItems).Count) }
            $serverVersion=[string](Get-AegisServerValue $serverInspect 'Version')
            if ($serverVersion -match '^[0-9]+\.[0-9]+\.[0-9]+[-a-zA-Z0-9.]*$') { $serverDecision.ProductVersion=$serverVersion }
        }
        $serverDecision.ObservedItems=$serverItemCount
        # Copy only known numeric measures. Never propagate a raw title/path/reason.
        $serverSummary=Get-AegisServerValue $Evidence 'Summary'
        $serverSamples=@{Count=$Iterations;PeakMemoryMeasured=$false;P95Measured=$false;P99Measured=$false;Acceptance='NOT_RUN'}
        foreach ($serverMeasure in @('ElapsedMeanMs','ElapsedMinMs','ElapsedMaxMs','CpuMeanMs')) {
            $serverNumeric=Get-AegisServerValue $serverSummary $serverMeasure
            if ($null -eq $serverNumeric) { throw 'MissingResourceMeasure' }
            [double]$serverNumber=$serverNumeric
            if ([double]::IsNaN($serverNumber) -or [double]::IsInfinity($serverNumber) -or $serverNumber -lt 0) { throw 'InvalidResourceMeasure' }
            $serverSamples[$serverMeasure]=$serverNumber
        }
        if ((ConvertTo-AegisServerCount (Get-AegisServerValue $serverSummary 'Count')) -ne $Iterations) { throw 'ResourceSampleCountMismatch' }
        $serverDecision.ResourceSamples=$serverSamples
        $serverDecision.Status='PASS';$serverDecision.Reason='ReadOnlyInspectCompleteZeroMutations'
    } catch { $serverDecision.Reason='ReadOnlyEvidenceRejected' }
    return $serverDecision
}

function Get-AegisServerGlobalSnapshot {
    $serverSaved=@{}
    foreach ($serverVariable in @(Get-Variable -Scope Global -Name 'Aegis*' -ErrorAction SilentlyContinue)) {
        if (($serverVariable.Options -band [Management.Automation.ScopedItemOptions]::ReadOnly) -ne 0 -or
            ($serverVariable.Options -band [Management.Automation.ScopedItemOptions]::Constant) -ne 0) { throw 'ReadOnlyAegisGlobalCannotBeIsolated' }
        $serverSaved[$serverVariable.Name]=@{Value=$serverVariable.Value;Options=$serverVariable.Options}
    }
    return @{Variables=$serverSaved;IsolationAttempted=$false}
}

function Clear-AegisServerGlobals {
    param($Snapshot)
    if ($WhatIfPreference) { throw 'InheritedWhatIfMustBeDisabledBeforeCollection' }
    $ConfirmPreference='None'
    $Snapshot.IsolationAttempted=$true
    foreach ($serverName in $Snapshot.Variables.Keys) {
        Set-Variable -Name $serverName -Scope Global -Value $null -ErrorAction Stop
        $serverActual=Get-Variable -Name $serverName -Scope Global -ErrorAction Stop
        if ($null -ne $serverActual.Value) { throw 'AegisGlobalIsolationNotApplied' }
    }
}

function Restore-AegisServerGlobals {
    param($Snapshot)
    $serverRestored=$true
    if ($null -eq $Snapshot -or -not $Snapshot.IsolationAttempted) { return $serverRestored }
    if ($WhatIfPreference) { return $false }
    $ConfirmPreference='None'
    foreach ($serverVariable in @(Get-Variable -Scope Global -Name 'Aegis*' -ErrorAction SilentlyContinue)) {
        if (-not $Snapshot.Variables.ContainsKey($serverVariable.Name)) {
            try {
                Remove-Variable -Name $serverVariable.Name -Scope Global -ErrorAction Stop
                if ($null -ne (Get-Variable -Name $serverVariable.Name -Scope Global -ErrorAction SilentlyContinue)) { $serverRestored=$false }
            }
            catch { $serverRestored=$false }
        }
    }
    foreach ($serverName in $Snapshot.Variables.Keys) {
        try {
            $serverExpected=$Snapshot.Variables[$serverName]
            Set-Variable -Name $serverName -Scope Global -Value $serverExpected.Value -Option $serverExpected.Options -ErrorAction Stop
            $serverActual=Get-Variable -Name $serverName -Scope Global -ErrorAction Stop
            $serverSame=[object]::ReferenceEquals($serverActual.Value,$serverExpected.Value)
            if (-not $serverSame -and $null -ne $serverActual.Value -and $serverActual.Value -is [ValueType]) { $serverSame=$serverActual.Value.Equals($serverExpected.Value) }
            if (-not $serverSame -or $serverActual.Options -ne $serverExpected.Options) { $serverRestored=$false }
        }
        catch { $serverRestored=$false }
    }
    return $serverRestored
}

function Invoke-AegisServerSuite {
    param([string]$ScriptFile,[hashtable]$Arguments,[string]$RawReportPath)
    $serverInvocationError=$null
    try {
        # Child scope also contains each suite's strict-mode/preference changes.
        # Suppress its per-case host chatter; retain the raw report and failures.
        & {
            param($ServerChildFile,$ServerChildArguments)
            function Write-Host { param($Object) }
            & $ServerChildFile @ServerChildArguments | Out-Null
        } $ScriptFile $Arguments
    } catch { $serverInvocationError=$_.Exception.ToString() }
    $serverRaw=$null
    if ([IO.File]::Exists($RawReportPath)) {
        $serverRawInfo=New-Object System.IO.FileInfo $RawReportPath
        if ($serverRawInfo.Length -gt 16777216) { throw 'RawEvidenceSizeLimitExceeded' }
        $serverRaw=Import-Clixml -Path $RawReportPath -ErrorAction Stop
    }
    return @{Evidence=$serverRaw;InvocationError=$serverInvocationError}
}

function ConvertTo-AegisServerSummary {
    param($Report)
    $serverLines=New-Object System.Collections.ArrayList
    [void]$serverLines.Add('Aegis 실서버 읽기 전용 검증')
    [void]$serverLines.Add(('실행 ID: '+$Report.RunId))
    [void]$serverLines.Add(('시작/완료 UTC: '+$Report.StartedUtc+' / '+$Report.CompletedUtc))
    [void]$serverLines.Add(('자동 수집: '+$Report.AutomaticStatus+' | 운영 투입 판정: HOLD'))
    [void]$serverLines.Add(('PowerShell '+$Report.Environment.PowerShellVersion+' | CLR '+$Report.Environment.ClrVersion+' | '+$Report.Environment.ProcessBitness+' bit'))
    [void]$serverLines.Add(('OS: '+$Report.Environment.OSVersion))
    if ($Report.ProductVersion -ne '') { [void]$serverLines.Add(('제품 응답 버전: '+$Report.ProductVersion)) }
    [void]$serverLines.Add(('제품 SHA256: '+$Report.ProductSha256))
    [void]$serverLines.Add(('설정 SHA256: '+$Report.ConfigSha256))
    [void]$serverLines.Add(('허용 규칙: '+$Report.ConfiguredRuleCount+'개 | Inspect 보고 항목 최대: '+$Report.ObservedItemCount+'개'))
    [void]$serverLines.Add('')
    foreach ($serverGate in $Report.Gates) {
        $serverCounts=''
        if ($serverGate.Total -gt 0) { $serverCounts=(' ['+$serverGate.Passed+'/'+$serverGate.Total+'; 실패 '+$serverGate.Failed+']') }
        [void]$serverLines.Add(($serverGate.Status+' | '+$serverGate.Label+$serverCounts+' | '+$serverGate.Reason))
    }
    if ($null -ne $Report.ResourceSamples) {
        $serverCulture=[Globalization.CultureInfo]::InvariantCulture
        [void]$serverLines.Add('')
        [void]$serverLines.Add(('Inspect 표본: '+$Report.ResourceSamples.Count+'회, 평균 '+$Report.ResourceSamples.ElapsedMeanMs.ToString('F2',$serverCulture)+' ms, 최대 '+$Report.ResourceSamples.ElapsedMaxMs.ToString('F2',$serverCulture)+' ms, 평균 CPU '+$Report.ResourceSamples.CpuMeanMs.ToString('F2',$serverCulture)+' ms'))
    }
    [void]$serverLines.Add('')
    [void]$serverLines.Add('이 명령은 창 이동·크기 변경·복원·트레이 열기를 요청하지 않습니다. 실행 전부터 진행 중인 OS 요청은 별개입니다.')
    [void]$serverLines.Add('의미 테스트는 실제 제품 함수와 가상 창 경계를 사용합니다. 실제 앱 변경 성공을 증명하지 않습니다.')
    [void]$serverLines.Add('허용 규칙 또는 대상 창이 없으면 해당 앱의 관찰 범위도 확보되지 않습니다. 보고 항목 수에는 제외된 창이 포함될 수 있습니다.')
    [void]$serverLines.Add('Inspect 자원 표본은 현재 PowerShell 프로세스의 일부 구간입니다. 앱/서버 전체 부하, 최대 메모리, P95/P99, 장시간 누수 합격 판정은 없습니다.')
    [void]$serverLines.Add('미완료: 앱별 크기 변경·제자리 복귀·Undo, 트레이 수명주기, RDP/잠금, 혼합 DPI/다중 모니터, 운영 부하 승인.')
    [void]$serverLines.Add('공유 검토: Summary.txt 및 Run-Evidence.clixml은 요약 자료입니다. Raw-*.clixml에는 컴퓨터 이름·로컬 경로·프로세스 정보·창 제목 등이 포함될 수 있습니다.')
    [void]$serverLines.Add('동일 실행 폴더의 자료를 함께 보관하세요. 100점 또는 운영 승인으로 자동 환산하지 않습니다.')
    return [string]::Join([Environment]::NewLine,[string[]]$serverLines.ToArray())
}

function Invoke-AegisServerCheck {
    param([hashtable]$Settings)
    # An inherited dry-run request must not produce partially written evidence or
    # pretend Set-Variable restored state. Reject before any directory is created.
    if ($WhatIfPreference) { throw 'InheritedWhatIfMustBeDisabledBeforeCollection' }
    Set-StrictMode -Off
    $ErrorActionPreference='Stop'
    $ConfirmPreference='None'
    $serverOutput=Resolve-AegisServerLocalPath $Settings.OutputDirectory
    if ([IO.File]::Exists($serverOutput)) { throw 'OutputDirectoryMustBeDirectory' }
    [void][IO.Directory]::CreateDirectory($serverOutput)
    $serverRunId='Aegis-ServerCheck-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[Guid]::NewGuid().ToString('N')
    $serverRunDirectory=Join-Path $serverOutput $serverRunId
    if ([IO.Directory]::Exists($serverRunDirectory) -or [IO.File]::Exists($serverRunDirectory)) { throw 'UniqueEvidenceDirectoryCollision' }
    [void][IO.Directory]::CreateDirectory($serverRunDirectory)
    $serverGates=@(
        (New-AegisServerGate 'InputFiles' '로컬 입력 파일'),
        (New-AegisServerGate 'SourceHashes' 'SHA256 환경/입력 해시'),
        (New-AegisServerGate 'WindowsPS2' '실제 Windows PowerShell 2.x'),
        (New-AegisServerGate 'Clr2' '실제 CLR 2.0'),
        (New-AegisServerGate 'GlobalIsolation' 'Aegis 전역 상태 격리/복원'),
        (New-AegisServerGate 'Behavior' 'PS2 의미 테스트: 제어/상태'),
        (New-AegisServerGate 'Storage' 'PS2 의미 테스트: 저장/설정'),
        (New-AegisServerGate 'Planner' 'PS2 의미 테스트: 배치 기하'),
        (New-AegisServerGate 'NativeReadOnly' '실제 Win32 읽기 전용 Inspect'),
        (New-AegisServerGate 'ResourceSamples' '읽기 전용 자원 표본 수집'),
        (New-AegisServerGate 'SourceStable' '검증 전후 소스/설정 동일'),
        (New-AegisServerGate 'EntryPoint' '전체 진입점 회귀 테스트' 'NOT_RUN' 'ExcludedArrangeGuardTestNeedsIsolatedDesktop'),
        (New-AegisServerGate 'RealAppAcceptance' '실제 앱 크기/복귀/Undo 승인' 'NOT_RUN' 'ManualAppMutationAcceptancePending'),
        (New-AegisServerGate 'TrayAcceptance' '트레이/숨김/재생성 승인' 'NOT_RUN' 'ManualTrayLifecycleAcceptancePending'),
        (New-AegisServerGate 'SessionAcceptance' 'RDP/잠금/세션 전환 승인' 'NOT_RUN' 'ManualSessionAcceptancePending'),
        (New-AegisServerGate 'DpiAcceptance' '혼합 DPI/다중 모니터 승인' 'NOT_RUN' 'ManualMixedDpiAcceptancePending'),
        (New-AegisServerGate 'PerformanceAcceptance' '운영 자원/장시간 안정성 승인' 'NOT_RUN' 'ManualPerformanceAcceptancePending')
    )
    $serverReport=@{
        SchemaVersion=1;Suite='AegisServerReadOnlyCollector';RunId=$serverRunId
        StartedUtc=[DateTime]::UtcNow.ToString('o');CompletedUtc=''
        AutomaticStatus='NOT_RUN';DeploymentGate='HOLD';Environment=(Get-AegisServerEnvironment)
        ProductVersion='';ProductSha256='UNAVAILABLE';ConfigSha256='UNAVAILABLE'
        Sources=@();Gates=$serverGates;RequestedIterations=$Settings.Iterations
        NativeReadOnlyExecuted=$false;AppMutationAcceptanceExecuted=$false
        ConfiguredRuleCount=0;ObservedItemCount=0;ResourceSamples=$null
        GlobalsRestored=$true;CallerPreferences='Child/function scopes only'
        RawFiles=@();SummaryFile='Summary.txt';EvidenceFile='Run-Evidence.clixml'
        RawEvidenceNotice='Raw files can contain machine names, paths, process metadata, window titles and exception details.'
    }
    $serverRawErrors=New-Object System.Collections.ArrayList
    $serverSources=New-Object System.Collections.ArrayList
    $serverPathMap=@{};$serverSnapshot=$null;$serverStage='InputFiles';$serverHashed=$false
    try {
        $serverProduct=Resolve-AegisServerLocalPath $Settings.ProductPath $true 2097152
        $serverConfig=Resolve-AegisServerLocalPath $Settings.ConfigPath $true 262144
        $serverPathMap['Product']=$serverProduct;$serverPathMap['Config']=$serverConfig
        $serverPathMap['Collector']=Resolve-AegisServerLocalPath $Settings.RunnerPath $true 2097152
        # Auxiliary code belongs to this collector's package, not an alternate
        # ProductPath directory. ProductPath only selects the product under test.
        $serverPackage=Split-Path -Parent (Split-Path -Parent $serverPathMap['Collector'])
        $serverPathMap['Behavior']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'tests\Test-AegisV4.ps1') $true 2097152
        $serverPathMap['BehaviorCases']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'tests\Controller-V4-Cases.ps1') $true 2097152
        $serverPathMap['ReportPathSafety']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'tests\ReportPathSafety.ps1') $true 2097152
        $serverPathMap['Storage']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'tests\Test-StorageV4.ps1') $true 2097152
        $serverPathMap['Planner']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'verification\Test-LayoutV4.ps1') $true 2097152
        $serverPathMap['Preflight']=Resolve-AegisServerLocalPath (Join-Path $serverPackage 'verification\Test-WindowsPreflight.ps1') $true 2097152
        Set-AegisServerGate $serverReport 'InputFiles' 'PASS' 'BoundedLiteralLocalFiles'
        $serverStage='SourceHashes'
        foreach ($serverId in @('Product','Config','Collector','Behavior','BehaviorCases','ReportPathSafety','Storage','Planner','Preflight')) {
            [void]$serverSources.Add((Get-AegisServerFileEvidence $serverPathMap[$serverId] $serverId))
        }
        $serverReport.Sources=$serverSources.ToArray();$serverReport.ProductSha256=$serverSources[0].Sha256;$serverReport.ConfigSha256=$serverSources[1].Sha256
        $serverHashed=$true
        Set-AegisServerGate $serverReport 'SourceHashes' 'PASS' 'SHA256Collected'
        if ($serverReport.Environment.TargetRuntime) { Set-AegisServerGate $serverReport 'WindowsPS2' 'PASS' 'ActualWindowsPowerShell2Observed' }
        else {
            $serverUnsupported='PowerShell2Required'
            if (-not $serverReport.Environment.ActualWindows) { $serverUnsupported='UnsupportedPlatform' }
            Set-AegisServerGate $serverReport 'WindowsPS2' 'NOT_RUN' $serverUnsupported
        }
        if ($serverReport.Environment.TargetRuntime -and $serverReport.Environment.ActualClr2) { Set-AegisServerGate $serverReport 'Clr2' 'PASS' 'ActualClr2Observed' }
        else { Set-AegisServerGate $serverReport 'Clr2' 'NOT_RUN' 'ActualWindowsPS2Clr2NotObserved' }
        if (-not $serverReport.Environment.TargetRuntime) {
            foreach ($serverId in @('Behavior','Storage','Planner','NativeReadOnly','ResourceSamples')) { Set-AegisServerGate $serverReport $serverId 'NOT_RUN' $serverUnsupported }
            Set-AegisServerGate $serverReport 'GlobalIsolation' 'NOT_RUN' 'NoProductCodeLoaded'
            return $serverReport
        }
        $serverStage='GlobalIsolation'
        $serverSnapshot=Get-AegisServerGlobalSnapshot
        Clear-AegisServerGlobals $serverSnapshot
        $serverSemanticPass=$true
        foreach ($serverKind in @('Behavior','Storage','Planner')) {
            $serverStage=$serverKind
            # Rehash immediately before each invocation as well as after the run.
            foreach ($serverSource in $serverReport.Sources) {
                $serverCurrent=Get-AegisServerFileEvidence $serverPathMap[$serverSource.Id] $serverSource.Id
                if ($serverCurrent.Sha256 -cne $serverSource.Sha256) { throw 'SourceChangedBeforeExecution' }
            }
            $serverRawName='Raw-'+$serverKind+'.clixml';$serverRawPath=Join-Path $serverRunDirectory $serverRawName
            $serverArguments=@{ScriptPath=$serverProduct;ReportPath=$serverRawPath}
            if ($serverKind -eq 'Planner') { $serverArguments=@{SourcePath=$serverProduct;OutputPath=$serverRawPath} }
            $serverSuite=Invoke-AegisServerSuite $serverPathMap[$serverKind] $serverArguments $serverRawPath
            if ([IO.File]::Exists($serverRawPath)) { $serverReport.RawFiles+=@($serverRawName) }
            $serverDecision=Test-AegisServerSuiteEvidence $serverSuite.Evidence $serverKind $serverReport.ProductSha256 $serverReport.Environment
            if ($null -ne $serverSuite.InvocationError) {
                [void]$serverRawErrors.Add(@{Stage=$serverKind;Detail=$serverSuite.InvocationError})
                $serverDecision.Status='FAIL';$serverDecision.Reason='SemanticInvocationFailed'
            }
            Set-AegisServerGate $serverReport $serverKind $serverDecision.Status $serverDecision.Reason
            foreach ($serverGate in $serverReport.Gates) {
                if ($serverGate.Id -eq $serverKind) { $serverGate.Total=$serverDecision.Total;$serverGate.Passed=$serverDecision.Passed;$serverGate.Failed=$serverDecision.Failed }
            }
            if ($serverDecision.Status -ne 'PASS') { $serverSemanticPass=$false }
        }
        if (-not $serverSemanticPass) {
            Set-AegisServerGate $serverReport 'NativeReadOnly' 'NOT_RUN' 'SemanticPrerequisiteFailed'
            Set-AegisServerGate $serverReport 'ResourceSamples' 'NOT_RUN' 'SemanticPrerequisiteFailed'
            return $serverReport
        }
        $serverStage='NativeReadOnly'
        foreach ($serverSource in $serverReport.Sources) {
            $serverCurrent=Get-AegisServerFileEvidence $serverPathMap[$serverSource.Id] $serverSource.Id
            if ($serverCurrent.Sha256 -cne $serverSource.Sha256) { throw 'SourceChangedBeforeExecution' }
        }
        $serverRawName='Raw-Preflight.clixml';$serverRawPath=Join-Path $serverRunDirectory $serverRawName
        $serverArguments=@{ScriptPath=$serverProduct;ConfigPath=$serverConfig;ReportPath=$serverRawPath;Iterations=$Settings.Iterations}
        $serverSuite=Invoke-AegisServerSuite $serverPathMap['Preflight'] $serverArguments $serverRawPath
        if ([IO.File]::Exists($serverRawPath)) { $serverReport.RawFiles+=@($serverRawName) }
        $serverDecision=Test-AegisServerPreflightEvidence $serverSuite.Evidence $serverReport.ProductSha256 $serverReport.ConfigSha256 $Settings.Iterations $serverReport.Environment
        if ($null -ne $serverSuite.InvocationError) {
            [void]$serverRawErrors.Add(@{Stage='NativeReadOnly';Detail=$serverSuite.InvocationError})
            $serverDecision.Status='FAIL';$serverDecision.Reason='PreflightInvocationFailed'
        }
        $serverReport.NativeReadOnlyExecuted=((Get-AegisServerValue $serverSuite.Evidence 'NativeContextExecuted') -eq $true)
        Set-AegisServerGate $serverReport 'NativeReadOnly' $serverDecision.Status $serverDecision.Reason
        $serverReport.ConfiguredRuleCount=$serverDecision.AllowedRules;$serverReport.ObservedItemCount=$serverDecision.ObservedItems
        $serverReport.ProductVersion=$serverDecision.ProductVersion
        if ($serverDecision.Status -eq 'PASS') {
            $serverReport.ResourceSamples=$serverDecision.ResourceSamples
            Set-AegisServerGate $serverReport 'ResourceSamples' 'PASS' 'SamplesOnlyNoPerformanceAcceptance'
        } else { Set-AegisServerGate $serverReport 'ResourceSamples' 'NOT_RUN' 'ReadOnlyPreflightIncomplete' }
    } catch {
        [void]$serverRawErrors.Add(@{Stage=$serverStage;Detail=$_.Exception.ToString()})
        $serverReason='CollectorStageFailed'
        if ($serverStage -eq 'SourceHashes') { $serverReason='HashCollectionFailedCheckCryptoPolicyAndFileAccess' }
        elseif ($serverStage -eq 'InputFiles') { $serverReason='LocalInputValidationFailed' }
        elseif ($serverStage -eq 'GlobalIsolation') { $serverReason='CallerStateCouldNotBeIsolated' }
        Set-AegisServerGate $serverReport $serverStage 'FAIL' $serverReason
    } finally {
        if ($serverHashed) {
            try {
                $serverUnchanged=$true
                foreach ($serverSource in $serverReport.Sources) {
                    $serverCurrent=Get-AegisServerFileEvidence $serverPathMap[$serverSource.Id] $serverSource.Id
                    if ($serverCurrent.Sha256 -cne $serverSource.Sha256 -or $serverCurrent.Bytes -ne $serverSource.Bytes) { $serverUnchanged=$false }
                }
                if ($serverUnchanged) { Set-AegisServerGate $serverReport 'SourceStable' 'PASS' 'AllRecordedInputBytesUnchanged' }
                else { Set-AegisServerGate $serverReport 'SourceStable' 'FAIL' 'InputBytesChangedDuringCollection' }
            } catch {
                [void]$serverRawErrors.Add(@{Stage='SourceStable';Detail=$_.Exception.ToString()})
                Set-AegisServerGate $serverReport 'SourceStable' 'FAIL' 'FinalSourceHashUnavailable'
            }
        }
        if ($null -ne $serverSnapshot -and $serverSnapshot.IsolationAttempted) {
            $serverReport.GlobalsRestored=Restore-AegisServerGlobals $serverSnapshot
            if ($serverReport.GlobalsRestored) { Set-AegisServerGate $serverReport 'GlobalIsolation' 'PASS' 'AllAegisGlobalsRestored' }
            else { Set-AegisServerGate $serverReport 'GlobalIsolation' 'FAIL' 'AegisGlobalRestoreFailed' }
        }
        $serverFailed=@($serverReport.Gates | Where-Object {$_.Status -eq 'FAIL'}).Count
        if ($serverFailed -gt 0) { $serverReport.AutomaticStatus='FAIL' }
        elseif (-not $serverReport.Environment.TargetRuntime) { $serverReport.AutomaticStatus='UNSUPPORTED' }
        else {
            $serverRequired=@('InputFiles','SourceHashes','WindowsPS2','Clr2','GlobalIsolation','Behavior','Storage','Planner','NativeReadOnly','ResourceSamples','SourceStable')
            $serverIncomplete=@($serverReport.Gates | Where-Object {$serverRequired -contains $_.Id -and $_.Status -ne 'PASS'}).Count
            if ($serverIncomplete -eq 0) { $serverReport.AutomaticStatus='COMPLETE_READ_ONLY' }
            else { $serverReport.AutomaticStatus='INCOMPLETE' }
        }
        $serverReport.CompletedUtc=[DateTime]::UtcNow.ToString('o')
        if ($serverRawErrors.Count -gt 0) {
            $serverRawErrors.ToArray() | Export-Clixml -Path (Join-Path $serverRunDirectory 'Raw-Errors.clixml') -Depth 8 -ErrorAction Stop
            $serverReport.RawFiles+=@('Raw-Errors.clixml')
        }
        $serverReport | Export-Clixml -Path (Join-Path $serverRunDirectory 'Run-Evidence.clixml') -Depth 12 -ErrorAction Stop
        $serverSavedEvidencePath=Join-Path $serverRunDirectory 'Run-Evidence.clixml'
        if (-not [IO.File]::Exists($serverSavedEvidencePath)) { throw 'FinalEvidenceFileNotCreated' }
        $serverSavedEvidence=Import-Clixml -Path $serverSavedEvidencePath -ErrorAction Stop
        if ((Get-AegisServerValue $serverSavedEvidence 'RunId') -cne $serverReport.RunId -or
            (Get-AegisServerValue $serverSavedEvidence 'AutomaticStatus') -cne $serverReport.AutomaticStatus -or
            (Get-AegisServerValue $serverSavedEvidence 'DeploymentGate') -cne 'HOLD' -or
            (Get-AegisServerValue $serverSavedEvidence 'ProductSha256') -cne $serverReport.ProductSha256 -or
            @(Get-AegisServerValue $serverSavedEvidence 'Gates').Count -ne $serverReport.Gates.Count) { throw 'FinalEvidenceRoundTripMismatch' }
        $serverSummary=ConvertTo-AegisServerSummary $serverReport
        $serverWriter=$null
        try {
            $serverOutputStream=[IO.File]::Open((Join-Path $serverRunDirectory 'Summary.txt'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
            $serverWriter=New-Object IO.StreamWriter ($serverOutputStream,[Text.Encoding]::UTF8)
            $serverWriter.Write($serverSummary)
        } finally { if ($null -ne $serverWriter) { $serverWriter.Close() } elseif ($null -ne $serverOutputStream) { $serverOutputStream.Close() } }
    }
    return $serverReport
}

# AEGIS_SERVER_ENTRY_POINT
$serverRunnerPath=$MyInvocation.MyCommand.Path
$serverDefaultRoot=Split-Path -Parent (Split-Path -Parent $serverRunnerPath)
if ([string]::IsNullOrEmpty($ProductPath)) { $ProductPath=Join-Path $serverDefaultRoot 'Aegis.ps1' }
if ([string]::IsNullOrEmpty($ConfigPath)) { $ConfigPath=Join-Path $serverDefaultRoot 'Aegis.Processes.csv' }
$serverSettings=@{ProductPath=$ProductPath;ConfigPath=$ConfigPath;OutputDirectory=$OutputDirectory;Iterations=$Iterations;RunnerPath=$serverRunnerPath}
$serverCollected=Invoke-AegisServerCheck $serverSettings
Write-Host (ConvertTo-AegisServerSummary $serverCollected)
New-Object PSObject -Property @{RunId=$serverCollected.RunId;AutomaticStatus=$serverCollected.AutomaticStatus;DeploymentGate='HOLD';SummaryFile='Summary.txt';EvidenceFile='Run-Evidence.clixml'}
