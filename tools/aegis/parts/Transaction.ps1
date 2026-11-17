# Geometry-only operations: never show, restore, activate, raise, or terminate an app.
function New-AegisOutcome {
    param($Window,[string]$Status,[string]$Reason,$Plan=$null)
    return @{Id=(Get-AegisValue $Window 'Id' '');SlotId=(Get-AegisValue $Window 'SlotId' '');RuleId=(Get-AegisValue $Window 'RuleId' '');ProcessName=(Get-AegisValue $Window 'ProcessName' '');Title=(Get-AegisValue $Window 'Title' '');Tier=(Get-AegisValue $Window 'Tier' 0);GroupId=(Get-AegisValue $Window 'GroupId' '');SizeMode=(Get-AegisValue $Window 'SizeMode' '');Status=$Status;Reason=$Reason;ErrorCode=0;Plan=$Plan;Actual=$null;Attempted=$false;Recovery='NotRequested';ZOrder='Unchanged'}
}

function Get-AegisObservationFailure {
    param($Observation)
    if ($Observation -isnot [hashtable]) { return @{Status='Deferred';Reason='NoObservation';ErrorCode=0} }
    $reason=[string](Get-AegisValue $Observation 'Reason' '')
    if (-not (Get-AegisValue $Observation 'Exists' $false)) {
        if (@('WindowMissing','WindowClosed') -contains $reason) { return @{Status='Disappeared';Reason='WindowClosed';ErrorCode=0} }
        return @{Status='Deferred';Reason=('IdentityUnavailable:'+ $reason);ErrorCode=0}
    }
    if (-not (Get-AegisValue $Observation 'SameIdentity' $false)) {
        if ($reason -eq 'IdentityMismatch') { return @{Status='Disappeared';Reason='IdentityChanged';ErrorCode=0} }
        return @{Status='Deferred';Reason=('IdentityUnavailable:'+ $reason);ErrorCode=0}
    }
    foreach ($key in @('Visible','Minimized','Maximized','Enabled','Hung','Cloaked','CloakReady','RectReady','StyleReady','Resizable')) {
        if ((Get-AegisValue $Observation $key $null) -isnot [bool]) { return @{Status='Deferred';Reason=('StateUnavailable:'+ $key);ErrorCode=0} }
    }
    if ($Observation.ErrorCode -ne 0 -or -not $Observation.RectReady -or -not $Observation.StyleReady -or -not $Observation.CloakReady -or -not (Test-AegisRectMatch $Observation $Observation 0)) { return @{Status='Deferred';Reason='ObservationUnavailable';ErrorCode=$Observation.ErrorCode} }
    if (-not $Observation.Visible) { return @{Status='Deferred';Reason='HiddenStatePreserved';ErrorCode=0} }
    if ($Observation.Minimized) { return @{Status='Deferred';Reason='MinimizedStatePreserved';ErrorCode=0} }
    if ($Observation.Maximized) { return @{Status='Deferred';Reason='MaximizedStatePreserved';ErrorCode=0} }
    if (-not $Observation.Enabled -or $Observation.Hung -or $Observation.Cloaked) { return @{Status='Deferred';Reason='CurrentWindowStateProtected';ErrorCode=0} }
    return $null
}

function Invoke-AegisBoundedBackend {
    param([scriptblock]$Backend,[string]$Operation,$Window,$Target,$Run)
    $Run.LastDispatchStarted=$false
    if ($Run.Timer.ElapsedMilliseconds -ge $Run.Options.TotalTimeoutMs) { throw 'RunTimeBudgetExceeded' }
    if ($Operation -eq 'Move') {
        if ($Run.Mutations -ge $Run.Options.MaxMutations) { throw 'MutationBudgetExceeded' }
        $Run.Mutations++
    } else {
        if ($Run.Observations -ge $Run.Options.MaxObservations) { throw 'ObservationBudgetExceeded' }
        $Run.Observations++
    }
    if ($Operation -eq 'Move') { $Run.LastDispatchStarted=$true }
    return (& $Backend $Operation $Window $Target)
}

function Test-AegisConfirmationContext {
    param($Context,[string]$ExpectedTopology)
    if ($Context -isnot [hashtable] -or [string]::IsNullOrEmpty($ExpectedTopology)) { return $false }
    return ((Get-AegisValue $Context 'Complete' $null) -is [bool] -and $Context.Complete -and
        (Get-AegisValue $Context 'DesktopSafe' $null) -is [bool] -and $Context.DesktopSafe -and
        [string](Get-AegisValue $Context 'TopologySignature' '') -ceq $ExpectedTopology)
}

function Wait-AegisObservation {
    param($Window,$Target,[scriptblock]$Backend,$Run)
    $watch=[Diagnostics.Stopwatch]::StartNew(); $last=$null
    while ($true) {
        try { $last=Invoke-AegisBoundedBackend $Backend 'Observe' $Window $null $Run }
        catch { return @{Status='Uncertain';Reason=$_.Exception.Message;Actual=$last} }
        $failure=Get-AegisObservationFailure $last
        if ($null -ne $failure) { $failure.Actual=$last; return $failure }
        if (Test-AegisRectMatch $last $Target $Run.Options.Tolerance) {
            # Equality is meaningful only under the coordinate/desktop context of
            # this request. A change after dispatch must retain async uncertainty.
            try { $context=Invoke-AegisBoundedBackend $Backend 'Context' $null $null $Run }
            catch { return @{Status='Uncertain';Reason=$_.Exception.Message;Actual=$last} }
            if (-not (Test-AegisConfirmationContext $context $Run.TopologySignature)) { return @{Status='Uncertain';Reason='ConfirmationContextChangedOrUnavailable';Actual=$last} }
            return @{Status='Matched';Reason='TargetObserved';Actual=$last}
        }
        $remaining=[Math]::Min(($Run.Options.MoveTimeoutMs-$watch.ElapsedMilliseconds),($Run.Options.TotalTimeoutMs-$Run.Timer.ElapsedMilliseconds))
        if ($remaining -le 0) { return @{Status='Uncertain';Reason='AcceptedRequestNotConfirmed';Actual=$last} }
        Start-Sleep -Milliseconds ([int][Math]::Min($Run.Options.PollMs,$remaining))
    }
}

function Resolve-AegisPendingMoves {
    param([scriptblock]$Backend,$Run)
    $remaining=New-Object System.Collections.ArrayList; $outcomes=New-Object System.Collections.ArrayList
    foreach ($entry in @($global:AegisPendingMoves)) {
        $resolved=$false; $observation=$null
        try {
            $observation=Invoke-AegisBoundedBackend $Backend 'Observe' $entry.Window $null $Run
            $failure=Get-AegisObservationFailure $observation
            if ($null -ne $failure -and $failure.Status -eq 'Disappeared') { $entry.Unavailable=$true; $resolved=$true }
            elseif ($null -eq $failure -and (Test-AegisRectMatch $observation $entry.Target $Run.Options.Tolerance)) {
                $context=Invoke-AegisBoundedBackend $Backend 'Context' $null $null $Run
                if (Test-AegisConfirmationContext $context $entry.TopologySignature) {
                    $entry.After=Get-AegisRect $observation; $entry.Confirmed=$true; $entry.Pending=$false
                    if ($entry.Operation -eq 'Undo') { $entry.Restored=$true }
                    $resolved=$true
                }
            }
        } catch { }
        if ($resolved) {
            $reason='LateTargetObserved'; if ($entry.Unavailable) { $reason='OriginalIdentityRetired' }
            [void]$outcomes.Add((New-AegisOutcome $entry.Window 'Resolved' $reason))
        } else {
            [void]$remaining.Add($entry)
            $item=New-AegisOutcome $entry.Window 'Uncertain' 'PendingAsyncRequest'; $item.Actual=$observation
            [void]$outcomes.Add($item)
        }
    }
    $global:AegisPendingMoves=$remaining.ToArray()
    return $outcomes.ToArray()
}

function Invoke-AegisWindowChange {
    param($Entry,$Plan,[string]$Operation,[scriptblock]$Backend,$Run,[switch]$Preview)
    # Preview executes the same observation/ownership/constraint gates but cannot
    # publish journal changes or enter the native mutation boundary.
    if ($Preview) { $Entry=Copy-AegisData $Entry }
    $window=$Entry.Window; $outcome=New-AegisOutcome $window 'Deferred' 'NotApplied' $Plan
    $issued=$false;$Run.LastDispatchStarted=$false
    try {
        $before=Invoke-AegisBoundedBackend $Backend 'Observe' $window $null $Run; $outcome.Actual=$before
        $failure=Get-AegisObservationFailure $before
        if ($null -ne $failure) {
            $outcome.Status=$failure.Status; $outcome.Reason=$failure.Reason; $outcome.ErrorCode=$failure.ErrorCode
            if ($failure.Status -eq 'Disappeared') { $Entry.Unavailable=$true }
            return $outcome
        }
        if ($Run.Options.MonitorScope -eq 'CurrentMonitor' -and $before.Monitor.Id -ne $Run.CursorMonitor.Id) {
            $outcome.Status='Skipped';$outcome.Reason='OutsideCurrentMonitor';return $outcome
        }
        if (-not (Test-AegisRectMatch $before $window $Run.Options.Tolerance) -or $before.Monitor.Id -ne $window.Monitor.Id -or -not (Test-AegisRectMatch $before.Monitor $window.Monitor 0)) {
            $outcome.Reason='WindowChangedSinceInventory';return $outcome
        }
        $target=Get-AegisRect $Plan; $target.Resize=[bool]$Plan.Resize
        if ($Operation -eq 'Undo') {
            if (Test-AegisRectMatch $before $Entry.Before $Run.Options.Tolerance) { $Entry.Restored=$true; $outcome.Status='AlreadyRestored';$outcome.Reason='OriginalGeometryObserved';return $outcome }
            if (-not $Entry.Confirmed -or -not (Test-AegisRectMatch $before $Entry.After $Run.Options.Tolerance)) { $outcome.Reason='ExternalChangePreserved';return $outcome }
        }
        if (Test-AegisRectMatch $before $target $Run.Options.Tolerance) { $outcome.Status='AlreadyPlaced';$outcome.Reason='TargetAlreadyObserved';return $outcome }
        if (-not $target.Resize -and ($before.Width -ne $target.Width -or $before.Height -ne $target.Height)) { $outcome.Reason='PreservedSizeChangedSincePlan'; return $outcome }
        if ($target.Resize -and ($before.Width -ne $target.Width -or $before.Height -ne $target.Height)) {
            if (-not $before.Resizable -or -not (Get-AegisValue $window 'MinMaxReady' $false)) { $outcome.Reason='ResizeConstraintsUnavailable';return $outcome }
            if ($target.Width -lt $window.MinWidth -or $target.Height -lt $window.MinHeight -or ($window.MaxWidth -gt 0 -and $target.Width -gt $window.MaxWidth) -or ($window.MaxHeight -gt 0 -and $target.Height -gt $window.MaxHeight)) { $outcome.Reason='CurrentSizeConstraintsRejectTarget';return $outcome }
        }
        if (-not (Test-AegisRectInside $target $Plan.ZoneRect)) { $outcome.Reason='TargetOutsideSavedZone';return $outcome }
        if ($Preview) {
            $outcome.Status='Planned';$outcome.Reason=[string](Get-AegisValue $Plan 'Reason' 'PlannedGeometryOnly')
            if ($Operation -eq 'Undo') { $outcome.Reason='UndoGeometryOnly' }
            return $outcome
        }
        $target.ExpectedRect=Get-AegisRect $before; $target.ExpectedMonitor=Copy-AegisData $before.Monitor
        $target.ExpectedTopologySignature=$Run.TopologySignature; $target.Tolerance=$Run.Options.Tolerance
        if ($Operation -ne 'Undo') { $Entry.Before=Get-AegisRect $before; $Entry.BeforeMonitor=Copy-AegisData $before.Monitor }
        $Entry.Target=Get-AegisRect $target; $Entry.Operation=$Operation;$Entry.TopologySignature=$Run.TopologySignature
        $outcome.Attempted=$true; $Entry.Attempted=$true
        $request=Invoke-AegisBoundedBackend $Backend 'Move' $window $target $Run
        $issued=[bool](Get-AegisValue $request 'Accepted' $false) -or [bool](Get-AegisValue $request 'MayBePending' $false)
        if (-not $issued) {
            $outcome.Status='Failed'; $outcome.Reason='MoveRequestRejected'
            if ($null -ne $request) { $outcome.ErrorCode=Get-AegisValue $request 'ErrorCode' 0; $outcome.Reason=[string](Get-AegisValue $request 'Reason' 'MoveRequestRejected') }
            return $outcome
        }
        $Entry.Pending=$true
        $check=Wait-AegisObservation $window $target $Backend $Run; $outcome.Actual=$check.Actual
        if ($check.Status -eq 'Matched') {
            $Entry.After=Get-AegisRect $check.Actual; $Entry.Confirmed=$true; $Entry.Pending=$false
            $outcome.Status='Moved'; $outcome.Reason='TargetObserved'
            if ($Operation -eq 'Undo') { $Entry.Restored=$true; $outcome.Status='Restored';$outcome.Reason='OriginalGeometryObserved' }
        } elseif ($check.Status -eq 'Disappeared') {
            $Entry.Unavailable=$true;$Entry.Pending=$false;$outcome.Status='Disappeared';$outcome.Reason=$check.Reason
        } else { $outcome.Status='Uncertain';$outcome.Reason=('Pending:'+ $check.Reason) }
    } catch {
        $outcome.Reason=$_.Exception.Message
        if ($issued -or $Run.LastDispatchStarted) { $Entry.Pending=$true; $outcome.Status='Uncertain' } else { $outcome.Status='Deferred' }
    }
    if ($Entry.Pending -and -not $Entry.Unavailable) { $global:AegisPendingMoves=@($global:AegisPendingMoves)+@($Entry) }
    return $outcome
}

function Get-AegisPlanningBatches {
    param([object[]]$Windows,$layoutProfile,[hashtable]$Options,[int]$Tier=0,[string]$GroupId='',$Run=$null)
    $byMonitor=@{}
    foreach ($window in $Windows) {
        $id=[string]$window.Monitor.Id
        if (-not $byMonitor.ContainsKey($id)) { $byMonitor[$id]=New-Object System.Collections.ArrayList }
        [void]$byMonitor[$id].Add($window)
    }
    $items=New-Object System.Collections.ArrayList; $zones=New-Object System.Collections.ArrayList; $warnings=New-Object System.Collections.ArrayList
    $complete=$true; $counters=New-Object System.Collections.ArrayList
    foreach ($monitorId in @($byMonitor.Keys | Sort-Object)) {
        $rows=$byMonitor[$monitorId]; $area=Get-AegisRect $rows[0].Monitor; $optionsCopy=Copy-AegisData $Options
        if ($null -ne $Run) {
            $remaining=$Run.Options.TotalTimeoutMs-$Run.Timer.ElapsedMilliseconds
            if ($remaining -le 0) { $complete=$false;[void]$warnings.Add('RunTimeBudgetExceededBeforePlanningBatch');break }
            $optionsCopy.PlanningTimeoutMs=[int][Math]::Min($optionsCopy.PlanningTimeoutMs,$remaining)
        }
        if ($Tier -ne 0) {
            $zoneMatches=@($layoutProfile.Zones | Where-Object { $_.MonitorId -eq $monitorId -and $_.Tier -eq $Tier -and (($_.Level -eq 'Tier' -and [string]::IsNullOrEmpty($GroupId)) -or ($_.Level -eq 'Group' -and $_.GroupId -eq $GroupId)) })
            if ($zoneMatches.Count -ne 1) { throw 'ScopedReflowRequiresOneSavedZonePerMonitor' }
            $area=Get-AegisRect $zoneMatches[0]; $optionsCopy.Margin=0
        }
        $plan=New-AegisLayoutPlan -Windows $rows.ToArray() -WorkArea $area -Options $optionsCopy
        if (-not $plan.Complete) { $complete=$false }
        foreach ($item in @($plan.Items)) { [void]$items.Add($item) }
        foreach ($zone in @($plan.Zones)) {
            # A group-only reflow must not replace its parent tier boundary.
            if (-not [string]::IsNullOrEmpty($GroupId) -and $zone.Level -eq 'Tier') { continue }
            $zone.MonitorId=$monitorId; [void]$zones.Add($zone)
        }
        foreach ($warning in @($plan.Warnings)) { [void]$warnings.Add($warning) }
        [void]$counters.Add($plan.Counters)
    }
    return @{Items=$items.ToArray();Zones=$zones.ToArray();Warnings=$warnings.ToArray();Complete=$complete;Counters=$counters.ToArray()}
}

function New-AegisReport {
    param([string]$Action,[bool]$Preview=$false)
    return @{Version=(Get-AegisVersion);Action=$Action;Preview=$Preview;Status='NotStarted';ExitCode=2;Detail='';Items=@();Warnings=@();DurationMs=0;UndoAvailable=$false;ProfileRevision=0;PendingCount=0;DpiMode='Unspecified';TopologySignature='';Counters=@{Observations=0;Mutations=0;Planning=@()}}
}

function Invoke-AegisController {
    param([string]$Action='Inspect',[hashtable]$Options=@{},[object[]]$Rules=@(),
        [scriptblock]$Backend={param($Operation,$Window,$Target) Invoke-AegisNative $Operation $Window $Target},
        [scriptblock]$InventoryProvider={param($Options,$Rules) Get-AegisInventory -Options $Options -Rules $Rules},
        [string[]]$RuleIds=@(),[int]$Tier=0,[string]$GroupId='',
        [switch]$KeepSize,[switch]$ReleaseAbsent,[switch]$Preview)
    # The caller's strict mode is restored automatically when this function exits.
    Set-StrictMode -Off
    $timer=[Diagnostics.Stopwatch]::StartNew()
    $isPreview=($Action -eq 'Inspect' -or [bool]$Preview)
    $report=New-AegisReport $Action $isPreview
    $items=New-Object System.Collections.ArrayList; $warnings=New-Object System.Collections.ArrayList
    $run=$null; $journal=$null; $publishJournal=$false
    try {
        if (@('Inspect','Arrange','Return','Reflow','Undo') -notcontains $Action) { throw 'Invalid controller action.' }
        if ($Tier -lt 0 -or $Tier -gt 3 -or (-not [string]::IsNullOrEmpty($GroupId) -and $Tier -eq 0)) { throw 'GroupId requires Tier 1, 2, or 3.' }
        if ($KeepSize -and @('Return','Inspect','Arrange') -notcontains $Action) { throw 'KeepSize applies only to Return or saved-home inspection/arrangement.' }
        if ($ReleaseAbsent -and $Action -ne 'Reflow') { throw 'ReleaseAbsent applies only to Reflow.' }
        if ($Action -eq 'Reflow' -and $null -ne $RuleIds -and $RuleIds.Count -gt 0) { throw 'Reflow scopes are whole tiers/groups; RuleIds applies to Return.' }
        if ($null -eq $global:AegisPendingMoves) { $global:AegisPendingMoves=@() }
        $layoutProfile=$global:AegisLayoutProfile
        if ($null -ne $layoutProfile) { Test-AegisProfile $layoutProfile }
        if (-not $PSBoundParameters.ContainsKey('Rules') -and $null -ne $layoutProfile) { $Rules=$layoutProfile.Rules }
        if (-not $PSBoundParameters.ContainsKey('Options') -and $null -ne $layoutProfile) { $Options=$layoutProfile.Options }
        $rules=@(ConvertTo-AegisRules $Rules); $options=New-AegisOptions $Options
        $configuredIds=@{};$configuredGroups=@{}
        foreach ($rule in $rules) { $configuredIds[[string]$rule.Id]=$true;$configuredGroups[([string]$rule.Tier+'/'+$rule.GroupId)]=$true }
        if ($null -ne $RuleIds) { foreach ($selectedId in $RuleIds) { if (-not $configuredIds.ContainsKey([string]$selectedId)) { throw ('Unknown RuleId selector: '+$selectedId) } } }
        if (-not [string]::IsNullOrEmpty($GroupId) -and -not $configuredGroups.ContainsKey(([string]$Tier+'/'+$GroupId))) { throw 'Unknown tier/group selector.' }
        $run=@{Timer=$timer;Options=$options;Observations=0;Mutations=0;TopologySignature=''}
        if ($Action -eq 'Return' -and $null -eq $layoutProfile) { $report.Status='NoProfile';$report.Detail='Arrange must establish a profile first.';return $report }
        if ($Action -eq 'Reflow' -and $null -eq $layoutProfile) { $report.Status='NoProfile';$report.Detail='Arrange must establish a profile first.';return $report }
        foreach ($resolved in @(Resolve-AegisPendingMoves $Backend $run)) { [void]$items.Add($resolved) }
        if (@($global:AegisPendingMoves).Count -gt 0) { $report.Status='BlockedPending';$report.Detail='An accepted asynchronous request is not yet confirmed. No new geometry request was sent.';return $report }
        if ($Action -eq 'Undo') {
            $undo=Get-AegisUndoSelection $global:AegisUndoState
            if ($undo.Status -ne 'Ready') { $report.Status=$undo.Status;if ($undo.Status -eq 'NoSnapshot') {$report.ExitCode=0};return $report }
        }
        $inventory=& $InventoryProvider $options $rules
        if ($inventory -isnot [hashtable] -or -not (Get-AegisValue $inventory 'Complete' $false)) { $report.Status='BlockedInventory';$report.Detail='Window enumeration or query budget was incomplete.';return $report }
        $allWindows=@(); if ($null -ne $inventory.Windows) { $allWindows=@($inventory.Windows) }
        if ($allWindows.Count -gt $options.MaxEnumeratedWindows) { $report.Status='BlockedLimit';$report.Detail='Enumeration count exceeds MaxEnumeratedWindows.';return $report }
        $run.TopologySignature=[string]$inventory.TopologySignature; $report.TopologySignature=$run.TopologySignature
        if ([string]::IsNullOrEmpty($run.TopologySignature)) { $report.Status='BlockedContext';$report.Detail='Monitor topology is unavailable.';return $report }
        foreach ($warning in @($inventory.Warnings)) { if ($null -ne $warning) { [void]$warnings.Add($warning) } }
        $context=Invoke-AegisBoundedBackend $Backend 'Context' $null $null $run
        if ($context -isnot [hashtable] -or -not $context.Complete -or $context.TopologySignature -cne $run.TopologySignature -or -not $context.DesktopSafe -or -not $inventory.DesktopSafe) {
            $report.Status='BlockedContext';$report.Detail='Interactive session, desktop, or monitor topology is unsafe or changed.';return $report
        }
        $run.CursorMonitor=Get-AegisValue $inventory 'CursorMonitor' $null
        if ($options.MonitorScope -eq 'CurrentMonitor' -and ([string]::IsNullOrEmpty([string](Get-AegisValue $run.CursorMonitor 'Id' '')) -or -not (Test-AegisRectMatch $run.CursorMonitor $run.CursorMonitor 0))) {
            $report.Status='BlockedContext';$report.Detail='Current monitor is unavailable.';return $report
        }
        if ($Action -eq 'Undo' -and (Get-AegisValue $global:AegisUndoState 'TopologySignature' '') -cne $run.TopologySignature) { $report.Status='ProfileChanged';$report.Detail='Undo coordinates belong to a different monitor/DPI context.';return $report }
        $eligible=New-Object System.Collections.ArrayList; $byId=@{}; $outsideScope=@{}
        foreach ($rawWindow in $allWindows) {
            $window=Copy-AegisData $rawWindow; $byId[[string]$window.Id]=$window
            $role=Resolve-AegisRole $window $rules; $window.RuleId=$role.RuleId;$window.Tier=$role.Tier;$window.IncludeOverride=$role.IncludeOverride
            if ($null -ne $role.Rule) {
                foreach ($key in @('GroupId','Priority','GroupPriority','GroupWeight','SizeMode')) { $window[$key]=$role.Rule[$key] }
                $window.DesiredWidth=$role.Rule.Width;$window.DesiredHeight=$role.Rule.Height
                $window.LayoutOrder=[int](Get-AegisValue $window 'Order' 0)
            }
            # Native inventory deliberately avoids detailed identity/snapshot
            # queries outside CurrentMonitor. Preserve that scope reason first.
            if ($options.MonitorScope -eq 'CurrentMonitor' -and $null -ne $window.Monitor -and $window.Monitor.Id -ne $run.CursorMonitor.Id) {
                $eligibility=@{Eligible=$false;Reason='OutsideCurrentMonitor'};$outsideScope[[string]$window.Id]=$true
            } else { $eligibility=Get-AegisEligibility $window $options }
            if ($eligibility.Eligible) { [void]$eligible.Add($window) }
            else { [void]$items.Add((New-AegisOutcome $window 'Skipped' $eligibility.Reason)) }
        }
        if ($eligible.Count -gt $options.MaxWindows) { $report.Status='BlockedLimit';$report.Detail='Selected window count exceeds MaxWindows.';return $report }
        if ($Action -eq 'Undo') {
            foreach ($entry in $undo.Entries) {
                if (-not (Test-AegisScope $entry.Window $RuleIds $Tier $GroupId)) { continue }
                if ($outsideScope.ContainsKey([string]$entry.Window.Id)) { continue }
                if ($isPreview) { $entry=Copy-AegisData $entry }
                if ($byId.ContainsKey([string]$entry.Window.Id) -and (Test-AegisIdentityEqual (Get-AegisIdentity $byId[[string]$entry.Window.Id]) (Get-AegisIdentity $entry.Window))) {
                    $old=$entry.Window; $entry.Window=Copy-AegisData $byId[[string]$old.Id]
                    foreach ($key in @('RuleId','SlotId','Tier','GroupId','SizeMode')) { $entry.Window[$key]=Get-AegisValue $old $key '' }
                }
                $plan=Get-AegisRect $entry.Before;$plan.Resize=$true;$plan.ZoneRect=$entry.BeforeMonitor;$plan.Status='Planned'
                [void]$items.Add((Invoke-AegisWindowChange $entry $plan 'Undo' $Backend $run -Preview:$isPreview))
                if (@($global:AegisPendingMoves).Count -gt 0) { break }
            }
        } else {
            $fingerprint=Get-AegisPolicyFingerprint $rules $options
            $isReflow=($Action -eq 'Reflow')
            if ($null -ne $layoutProfile -and ($layoutProfile.PolicyFingerprint -cne $fingerprint -or $layoutProfile.TopologySignature -cne $run.TopologySignature)) {
                if (-not $isReflow -or $Tier -ne 0 -or $options.MonitorScope -ne 'EachMonitor') { $report.Status='ProfileChanged';$report.Detail='Rules, layout options, or topology changed; a full Reflow is required.';return $report }
            }
            $bindings=Resolve-AegisBindings $layoutProfile $eligible.ToArray() $allWindows
            $plans=New-Object System.Collections.ArrayList
            $candidate=$null
            if ($null -eq $layoutProfile -or $isReflow) {
                if ($null -eq $layoutProfile -and ($Tier -ne 0 -or -not [string]::IsNullOrEmpty($GroupId) -or ($null -ne $RuleIds -and $RuleIds.Count -gt 0))) { throw 'Initial Arrange requires the full configured scope.' }
                $participants=New-Object System.Collections.ArrayList; $selectedOld=@{}; $ruleById=@{}
                foreach ($rule in $rules) { $ruleById[$rule.Id]=$rule }
                $ambiguousIds=@{}; foreach ($window in $bindings.Ambiguous) { $ambiguousIds[[string]$window.Id]=$true }
                if ($null -ne $layoutProfile) {
                    foreach ($slot in $layoutProfile.Slots) {
                        if (-not (Test-AegisScope $slot @() $Tier $GroupId)) { continue }
                        if ($options.MonitorScope -eq 'CurrentMonitor' -and $slot.Monitor.Id -ne $inventory.CursorMonitor.Id) { continue }
                        $selectedOld[[string]$slot.SlotId]=$true
                    }
                }
                foreach ($window in $eligible) {
                    if (-not (Test-AegisScope $window @() $Tier $GroupId)) { continue }
                    if ($ambiguousIds.ContainsKey([string]$window.Id) -and -not $ReleaseAbsent) { [void]$items.Add((New-AegisOutcome $window 'Deferred' 'AmbiguousProfileBinding')); continue }
                    if ($bindings.ByWindow.ContainsKey([string]$window.Id)) { $window.LayoutOrder=$bindings.ByWindow[[string]$window.Id].Order }
                    [void]$participants.Add($window)
                }
                # Assign stable new-slot order before planning; saving a different
                # order afterward would reshuffle identical consecutive Reflows.
                $nextOrder=0
                if ($null -ne $layoutProfile) { foreach ($old in $layoutProfile.Slots) { $nextOrder=[Math]::Max($nextOrder,([int]$old.Order+1)) } }
                $newParticipants=@($participants | Where-Object { -not $bindings.ByWindow.ContainsKey([string]$_.Id) } | Sort-Object @{Expression={[string]$_.RuleId}},@{Expression={[string]$_.Id}})
                foreach ($newParticipant in $newParticipants) { $newParticipant.LayoutOrder=$nextOrder;$nextOrder++ }
                if (-not $ReleaseAbsent) {
                    foreach ($slot in $bindings.Reserved) {
                        if (-not $selectedOld.ContainsKey([string]$slot.SlotId)) { continue }
                        if (-not $ruleById.ContainsKey([string]$slot.RuleId) -or -not $ruleById[[string]$slot.RuleId].Include) { throw 'RemovedRuleHasReservedSlot: use explicit Reflow -ReleaseAbsent.' }
                        if ($null -ne $layoutProfile -and $layoutProfile.PolicyFingerprint -cne $fingerprint) { throw 'ChangedRulesHaveReservedSlots: restore the app or use Reflow -ReleaseAbsent.' }
                        if ($layoutProfile.TopologySignature -cne $run.TopologySignature) { throw 'TopologyChangedWithReservedSlots: restore the app or use Reflow -ReleaseAbsent.' }
                        [void]$participants.Add((New-AegisReservedWindow $slot))
                    }
                }
                if ($participants.Count -gt $options.MaxWindows) { $report.Status='BlockedLimit';$report.Detail='Active plus reserved slots exceed MaxWindows.';return $report }
                $planned=Get-AegisPlanningBatches $participants.ToArray() $layoutProfile $options $Tier $GroupId $run
                $report.Counters.Planning=$planned.Counters
                foreach ($warning in @($planned.Warnings)) { [void]$warnings.Add($warning) }
                if (-not $planned.Complete) { $report.Status='BlockedPlanning';$report.Detail='Planning exceeded its bounded work/time budget.';return $report }
                $revision=1;if ($null -ne $layoutProfile) { $revision=$layoutProfile.Revision+1 }
                $candidate=New-AegisProfile $rules $options $run.TopologySignature $revision
                $newSlots=New-Object System.Collections.ArrayList; $newZones=New-Object System.Collections.ArrayList; $next=@{}
                if ($null -ne $layoutProfile) {
                    foreach ($slot in $layoutProfile.Slots) {
                        $number=[int]([string]$slot.SlotId).Substring(([string]$slot.SlotId).Length-3)
                        if (-not $next.ContainsKey([string]$slot.RuleId) -or $next[[string]$slot.RuleId] -le $number) { $next[[string]$slot.RuleId]=$number+1 }
                        if (-not $selectedOld.ContainsKey([string]$slot.SlotId)) { [void]$newSlots.Add((Copy-AegisData $slot)) }
                    }
                    foreach ($zone in $layoutProfile.Zones) {
                        $replace=($Tier -eq 0 -or $zone.Tier -eq $Tier)
                        if (-not [string]::IsNullOrEmpty($GroupId)) { $replace=($replace -and $zone.Level -eq 'Group' -and $zone.GroupId -eq $GroupId) }
                        if ($options.MonitorScope -eq 'CurrentMonitor' -and $zone.MonitorId -ne $inventory.CursorMonitor.Id) { $replace=$false }
                        if (-not $replace) { [void]$newZones.Add((Copy-AegisData $zone)) }
                    }
                }
                foreach ($plan in $planned.Items) {
                    $window=$plan.Window
                    if ($plan.Status -ne 'Planned') {
                        [void]$items.Add((New-AegisOutcome $window 'Deferred' $plan.Reason $plan))
                        if (Get-AegisValue $window 'Reserved' $false) { throw 'ReservedSlotWouldBeLost: the reflow was not applied.' }
                        if ($bindings.ByWindow.ContainsKey([string]$window.Id)) { throw 'ExistingSlotWouldBeLost: the reflow was not applied.' }
                        continue
                    }
                    if (Get-AegisValue $window 'Reserved' $false) {
                        $slot=Copy-AegisData $window.OriginalSlot;$slot.HomeRect=Get-AegisRect $plan;$slot.ZoneRect=Get-AegisRect $plan.ZoneRect;$slot.HomeConfirmed=$false
                        [void]$newSlots.Add($slot);[void]$items.Add((New-AegisOutcome $window 'Reserved' 'AbsentWindowSlotRetained' $plan));continue
                    }
                    $oldSlot=Get-AegisValue $bindings.ByWindow ([string]$window.Id) $null
                    if ($null -ne $oldSlot) { $slotId=$oldSlot.SlotId;$slotOrder=$oldSlot.Order }
                    else {
                        if (-not $next.ContainsKey([string]$window.RuleId)) { $next[[string]$window.RuleId]=1 }
                        if ($next[[string]$window.RuleId] -gt 999) { throw 'SlotSequenceExhausted' }
                        $slotId=$window.RuleId+':'+([int]$next[[string]$window.RuleId]).ToString('000');$next[[string]$window.RuleId]++
                        $slotOrder=$window.LayoutOrder
                    }
                    $window.SlotId=$slotId;$slot=New-AegisSlot $window $plan $slotId $slotOrder
                    [void]$newSlots.Add($slot);$plan.SavedSlot=$slot;[void]$plans.Add($plan)
                }
                foreach ($zone in $planned.Zones) { [void]$newZones.Add($zone) }
                # Planner may report an empty group/tier; retain only zones used by saved slots.
                $usedZones=New-Object System.Collections.ArrayList
                foreach ($zone in $newZones) {
                    foreach ($slot in $newSlots) {
                        if ($slot.Monitor.Id -eq $zone.MonitorId -and $slot.Tier -eq $zone.Tier -and ($zone.Level -eq 'Tier' -or $slot.GroupId -eq $zone.GroupId)) { [void]$usedZones.Add($zone);break }
                    }
                }
                $candidate.Slots=$newSlots.ToArray();$candidate.Zones=$usedZones.ToArray();Test-AegisProfile $candidate
            } else {
                $candidate=Copy-AegisData $layoutProfile
                $candidateSlots=@{};foreach ($slot in $candidate.Slots) { $candidateSlots[[string]$slot.SlotId]=$slot }
                foreach ($window in $bindings.Unassigned) { if (Test-AegisScope $window $RuleIds $Tier $GroupId) { [void]$items.Add((New-AegisOutcome $window 'Deferred' 'UnassignedWindowRequiresReflow')) } }
                foreach ($window in $bindings.Ambiguous) { if (Test-AegisScope $window $RuleIds $Tier $GroupId) { [void]$items.Add((New-AegisOutcome $window 'Deferred' 'AmbiguousProfileBinding')) } }
                foreach ($slot in $bindings.Reserved) {
                    if (Test-AegisScope $slot $RuleIds $Tier $GroupId) { [void]$items.Add((New-AegisOutcome (New-AegisReservedWindow $slot) 'Reserved' 'AbsentWindowSlotRetained')) }
                }
                foreach ($window in $eligible) {
                    if (-not (Test-AegisScope $window $RuleIds $Tier $GroupId) -or -not $bindings.ByWindow.ContainsKey([string]$window.Id)) { continue }
                    $slot=$candidateSlots[[string]$bindings.ByWindow[[string]$window.Id].SlotId]
                    $window.SlotId=$slot.SlotId;$window.LayoutOrder=$slot.Order
                    $plan=Get-AegisRect $slot.HomeRect;$plan.Window=$window;$plan.Id=$window.Id;$plan.ZoneRect=Copy-AegisData $slot.ZoneRect;$plan.SavedSlot=$slot;$plan.Status='Planned';$plan.Reason='SavedHome';$plan.Tier=$window.Tier;$plan.GroupId=$window.GroupId
                    if ($KeepSize) { $plan.Width=$window.Width;$plan.Height=$window.Height;$plan.Reason='SavedPositionCurrentSize' }
                    $plan.Resize=($plan.Width -ne $window.Width -or $plan.Height -ne $window.Height)
                    if (-not (Test-AegisRectInside $plan $slot.ZoneRect) -or -not (Test-AegisRectInside $plan $slot.Monitor)) { [void]$items.Add((New-AegisOutcome $window 'Deferred' 'CurrentSizeExceedsSavedZone' $plan));continue }
                    if ($KeepSize) {
                        $collision=$false
                        foreach ($other in $candidate.Slots) { if ($other.SlotId -ne $slot.SlotId -and $other.Monitor.Id -eq $slot.Monitor.Id -and (Test-AegisRectsOverlap $plan $other.HomeRect)) { $collision=$true;break } }
                        if ($collision) { [void]$items.Add((New-AegisOutcome $window 'Deferred' 'CurrentSizeOverlapsAnotherHome' $plan));continue }
                    }
                    $slot.Identity=Get-AegisIdentity $window; [void]$plans.Add($plan)
                }
            }
            if ($KeepSize -and $plans.Count -gt 1) {
                # Expanded targets can cross in an unused diagonal cell while
                # avoiding every original HomeRect. Reject all participants of
                # such a conflict before Preview or any Move, independently of
                # enumeration order. Existing saved-home checks still apply.
                $conflictedPlans=@{}
                for ($leftIndex=0;$leftIndex -lt $plans.Count;$leftIndex++) {
                    for ($rightIndex=$leftIndex+1;$rightIndex -lt $plans.Count;$rightIndex++) {
                        $leftPlan=$plans[$leftIndex];$rightPlan=$plans[$rightIndex]
                        if ($leftPlan.SavedSlot.Monitor.Id -eq $rightPlan.SavedSlot.Monitor.Id -and (Test-AegisRectsOverlap $leftPlan $rightPlan)) {
                            $conflictedPlans[$leftIndex]=$true;$conflictedPlans[$rightIndex]=$true
                        }
                    }
                }
                if ($conflictedPlans.Count -gt 0) {
                    $nonconflictingPlans=New-Object System.Collections.ArrayList
                    for ($planIndex=0;$planIndex -lt $plans.Count;$planIndex++) {
                        $currentPlan=$plans[$planIndex]
                        if ($conflictedPlans.ContainsKey($planIndex)) { [void]$items.Add((New-AegisOutcome $currentPlan.Window 'Deferred' 'CurrentSizesOverlapWithinBatch' $currentPlan)) }
                        else { [void]$nonconflictingPlans.Add($currentPlan) }
                    }
                    $plans=$nonconflictingPlans
                }
            }
            if ($isPreview) {
                foreach ($plan in $plans) {
                    $entry=@{Window=(Copy-AegisData $plan.Window);Before=$null;BeforeMonitor=$null;After=$null;Target=$null;Attempted=$false;Confirmed=$false;Pending=$false;Restored=$false;Unavailable=$false;Operation=$Action}
                    [void]$items.Add((Invoke-AegisWindowChange $entry $plan $Action $Backend $run -Preview))
                }
            } else {
                if ($timer.ElapsedMilliseconds -ge $options.TotalTimeoutMs) { $report.Status='BlockedBudget';return $report }
                $global:AegisLayoutProfile=$candidate
                $journal=@{SchemaVersion=4;Entries=@();CreatedUtc=[DateTime]::UtcNow.ToString('o');TopologySignature=$run.TopologySignature}
                $entries=New-Object System.Collections.ArrayList
                $applyPlans=@($plans | Sort-Object @{Expression={[int]$_.Window.Tier};Descending=$true},@{Expression={[int]$_.Window.GroupPriority};Descending=$true},@{Expression={[int]$_.Window.Priority};Descending=$true},@{Expression={[int]$_.Window.LayoutOrder}},@{Expression={[string]$_.Id}})
                $stopWriting=$false
                foreach ($plan in $applyPlans) {
                    if ($stopWriting) { [void]$items.Add((New-AegisOutcome $plan.Window 'Deferred' 'EarlierAsyncRequestPending' $plan));continue }
                    $entry=@{Window=(Copy-AegisData $plan.Window);Before=$null;BeforeMonitor=$null;After=$null;Target=$null;Attempted=$false;Confirmed=$false;Pending=$false;Restored=$false;Unavailable=$false;Operation=$Action}
                    [void]$entries.Add($entry);$journal.Entries=$entries.ToArray()
                    $outcome=Invoke-AegisWindowChange $entry $plan $Action $Backend $run;[void]$items.Add($outcome)
                    if ($entry.Confirmed -or $entry.Pending) { $publishJournal=$true;$global:AegisUndoState=$journal }
                    if (@('Moved','AlreadyPlaced') -contains $outcome.Status) { $plan.SavedSlot.HomeConfirmed=$true }
                    if (@($global:AegisPendingMoves).Count -gt 0) { $stopWriting=$true }
                }
            }
        }
        $report.Status='Complete';$report.ExitCode=0
        foreach ($item in $items) {
            if (@('Deferred','Failed','Uncertain','Disappeared') -contains $item.Status) { $report.Status='Partial';$report.ExitCode=1 }
        }
        if (@($global:AegisPendingMoves).Count -gt 0) { $report.Status='BlockedPending';$report.ExitCode=3 }
        return $report
    } catch {
        $report.Status='Aborted';$report.ExitCode=2;$report.Detail=$_.Exception.Message
        return $report
    } finally {
        if ($publishJournal -and $null -ne $journal) { $global:AegisUndoState=$journal }
        $report.Items=$items.ToArray();$report.Warnings=$warnings.ToArray();$report.DurationMs=[int]$timer.ElapsedMilliseconds
        $report.PendingCount=0;if ($null -ne $global:AegisPendingMoves) { $report.PendingCount=@($global:AegisPendingMoves).Count }
        if ($report.Status -eq 'BlockedPending') { $report.ExitCode=3 }
        $report.UndoAvailable=((Get-AegisUndoSelection $global:AegisUndoState).Status -eq 'Ready')
        if ($null -ne $global:AegisLayoutProfile) { $report.ProfileRevision=$global:AegisLayoutProfile.Revision }
        if ($null -ne $run) { $report.Counters.Observations=$run.Observations;$report.Counters.Mutations=$run.Mutations }
        $global:AegisLastResult=$report
    }
}
