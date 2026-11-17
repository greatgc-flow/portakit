function Show-AegisReport {
    param([hashtable]$Report)
    Write-Host ''
    Write-Host ('Aegis '+$Report.Version+' | '+$Report.Action+' | '+$Report.Status+' | exit='+$Report.ExitCode)
    if ($Report.Preview) { Write-Host '미리보기: 창 위치·크기와 저장된 홈은 변경하지 않았습니다.' }
    if (-not [string]::IsNullOrEmpty([string]$Report.Detail)) { Write-Host $Report.Detail }
    Write-Host ('프로필 revision='+$Report.ProfileRevision+' | Undo='+$Report.UndoAvailable+' | 미확인 요청='+$Report.PendingCount+' | '+$Report.DurationMs+' ms')
    $rows=New-Object System.Collections.ArrayList
    foreach ($item in @($Report.Items)) {
        if ($item.Status -eq 'Skipped' -and @('HiddenWindow','SystemWindowClass','OwnHostWindow') -contains $item.Reason) { continue }
        [void]$rows.Add((New-Object PSObject -Property @{Rule=$item.RuleId;Tier=$item.Tier;Group=$item.GroupId;Process=$item.ProcessName;Result=$item.Status;Reason=$item.Reason;Win32=$item.ErrorCode}))
    }
    if ($rows.Count -gt 0) { Write-Host ($rows | Select-Object -First 40 | Format-Table Rule,Tier,Group,Process,Result,Reason,Win32 -AutoSize | Out-String -Width 220) }
    if ($rows.Count -gt 40) { Write-Host '전체 창별 결과: $global:AegisLastResult.Items' }
    foreach ($warning in @($Report.Warnings)) { Write-Warning ([string]$warning) }
    if ($Report.Status -eq 'BlockedPending') { Write-Host '이동 요청의 완료가 확인되지 않아 후속 변경을 보류했습니다. Inspect로 다시 확인하세요. 취소·자동 롤백은 수행하지 않습니다.' }
    if ($Report.ProfileRevision -eq 0 -and @($Report.Items | Where-Object {$_.Status -eq 'Planned'}).Count -eq 0) { Write-Host '설정 예: -ConfigPath .\Aegis.Processes.csv. 허용한 프로세스의 보이는 일반 창만 대상입니다.' }
}

function Invoke-AegisMain {
    param($Arguments,$BoundParameters,[string]$SourcePath)
    Set-StrictMode -Off
    $actionName=[string]$Arguments.Action
    if ($actionName -eq 'SelfTest') {
        $global:AegisLastExitCode=2
        $testPath=Join-Path (Join-Path (Split-Path -Parent $SourcePath) 'tests') 'Test-AegisV4.ps1'
        if (-not (Test-Path -LiteralPath $testPath -PathType Leaf)) { throw 'SelfTest requires the full package tests directory.' }
        & $testPath -ScriptPath $SourcePath
        $global:AegisLastExitCode=0
        return
    }
    $previousPreference=$ErrorActionPreference;$ErrorActionPreference='Stop'
    $mutex=$null;$ownsMutex=$false;$dpi=$null;$result=$null
    $totalTimer=[Diagnostics.Stopwatch]::StartNew()
    try {
        if ($actionName -eq 'SaveProfile' -or $actionName -eq 'LoadProfile') {
            if ($Arguments.Preview) { throw 'Preview applies only to window actions.' }
            if ([string]::IsNullOrEmpty([string]$Arguments.ProfilePath)) { throw 'ProfilePath is required.' }
            if ($null -ne $global:AegisPendingMoves -and @($global:AegisPendingMoves).Count -gt 0) { throw 'Pending requests must resolve before a profile can be saved or loaded.' }
            if ($actionName -eq 'SaveProfile') { Save-AegisProfile -LayoutProfile $global:AegisLayoutProfile -Path $Arguments.ProfilePath }
            else { $global:AegisLayoutProfile=Import-AegisProfile -Path $Arguments.ProfilePath }
            $result=New-AegisReport $actionName $false;$result.Status='Complete';$result.ExitCode=0;$result.ProfileRevision=$global:AegisLayoutProfile.Revision
        } else {
            if (-not [string]::IsNullOrEmpty([string]$Arguments.ProfilePath)) { throw 'ProfilePath applies only to SaveProfile or LoadProfile.' }
            if ($BoundParameters.ContainsKey('Rules') -and -not [string]::IsNullOrEmpty([string]$Arguments.ConfigPath)) { throw 'Use either Rules or ConfigPath, not both.' }
            $effectiveRules=@();$effectiveOptions=@{}
            if ($null -ne $global:AegisLayoutProfile) { Test-AegisProfile $global:AegisLayoutProfile;$effectiveRules=$global:AegisLayoutProfile.Rules;$effectiveOptions=Copy-AegisData $global:AegisLayoutProfile.Options }
            if (-not [string]::IsNullOrEmpty([string]$Arguments.ConfigPath)) { $effectiveRules=@(Import-AegisProcessRules $Arguments.ConfigPath) }
            elseif ($BoundParameters.ContainsKey('Rules')) { $effectiveRules=$Arguments.Rules }
            if ($null -ne $Arguments.Options) { foreach ($key in $Arguments.Options.Keys) { $effectiveOptions[$key]=$Arguments.Options[$key] } }
            $effectiveOptions=New-AegisOptions $effectiveOptions;$effectiveRules=@(ConvertTo-AegisRules $effectiveRules)
            if (-not (Test-AegisNativeWindows)) { throw 'Window actions require an interactive Windows desktop. SelfTest and data-file actions can run on another platform.' }
            # Retains the v3 mutex name so an old copy cannot run concurrently.
            $mutex=New-Object System.Threading.Mutex ($false,'Local\Aegis_WindowLayout_v3')
            try { $ownsMutex=$mutex.WaitOne(0,$false) } catch [Threading.AbandonedMutexException] { $ownsMutex=$true }
            if (-not $ownsMutex) { throw 'Another Aegis operation is active in this session.' }
            $dpi=Enter-AegisDpiContext
            $result=Invoke-AegisController -Action $actionName -Options $effectiveOptions -Rules $effectiveRules -RuleIds $Arguments.RuleIds -Tier $Arguments.Tier -GroupId $Arguments.GroupId -KeepSize:([bool]$Arguments.KeepSize) -ReleaseAbsent:([bool]$Arguments.ReleaseAbsent) -Preview:([bool]$Arguments.Preview)
            $result.DpiMode=$dpi.Mode
        }
    } catch {
        $result=New-AegisReport $actionName ([bool]$Arguments.Preview)
        $result.Status='Aborted';$result.ExitCode=2;$result.Detail=$_.Exception.Message
    } finally {
        if ($null -ne $dpi) {
            $leave=Exit-AegisDpiContext $dpi
            if (-not $leave.Accepted -and $null -ne $result) {
                $result.Warnings=@($result.Warnings)+@($leave.Reason)
                # Cleanup failure may raise a successful result to Partial, but
                # must not hide an abort or an unresolved asynchronous request.
                if ($result.ExitCode -eq 0) { $result.Status='Partial';$result.ExitCode=1 }
            }
        }
        if ($ownsMutex -and $null -ne $mutex) { [void]$mutex.ReleaseMutex() }
        if ($null -ne $mutex) { $mutex.Close() }
        $ErrorActionPreference=$previousPreference
    }
    $result.DurationMs=[int]$totalTimer.ElapsedMilliseconds
    $global:AegisLastResult=$result;$global:AegisLastExitCode=$result.ExitCode
    if ($Arguments.PassThru) { return $result }
    Show-AegisReport $result
}

if ($Action -eq 'Library') { return }
$aegisInvocation=@{Action=$Action;Options=$Options;Rules=$Rules;ConfigPath=$ConfigPath;ProfilePath=$ProfilePath;RuleIds=$RuleIds;Tier=$Tier;GroupId=$GroupId;KeepSize=[bool]$KeepSize;ReleaseAbsent=[bool]$ReleaseAbsent;Preview=[bool]$Preview;PassThru=[bool]$PassThru}
Invoke-AegisMain -Arguments $aegisInvocation -BoundParameters $PSBoundParameters -SourcePath $MyInvocation.MyCommand.Path
if ($ExitWithCode) { exit $global:AegisLastExitCode }
