# Independent controller regressions, with an explicit synthetic desktop.
function Copy-AegisV4TestRect {
    param($Value)
    return @{Left=[int]$Value.Left;Top=[int]$Value.Top;Width=[int]$Value.Width;Height=[int]$Value.Height}
}
function Test-AegisV4TestRect {
    param($Left,$Right)
    return ($null -ne $Left -and $null -ne $Right -and $Left.Left -eq $Right.Left -and $Left.Top -eq $Right.Top -and $Left.Width -eq $Right.Width -and $Left.Height -eq $Right.Height)
}
function New-AegisV4TestWindow {
    param([string]$Id='101',[string]$ProcessName='editor',[int]$Index=0)
    $left=91+($Index*61);$top=73+($Index*47)
    return @{
        Id=$Id;Handle=[IntPtr][int]$Id;ProcessName=$ProcessName;ClassName='FixtureWindow';Title=('Synthetic '+$Id)
        ProcessId=(1001+$Index);ThreadId=(2001+$Index);ProcessStart=('{0:x16}' -f (1001+$Index))
        Exists=$true;Visible=$true;Enabled=$true;Hung=$false;Cloaked=$false;CloakReady=$true;IsSelf=$false
        Owned=$false;ToolWindow=$false;NoActivate=$false;Topmost=$false
        Minimized=$false;Maximized=$false;Resizable=$true
        IdentityReady=$true;SnapshotReady=$true;RectReady=$true;StyleReady=$true;MinMaxReady=$true;PlacementReady=$true
        Left=$left;Top=$top;Width=400;Height=300;Order=$Index;LayoutOrder=$Index
        MinWidth=100;MinHeight=80;MaxWidth=0;MaxHeight=0;ConstraintReason='Measured'
        Monitor=@{Id='M1';Left=0;Top=0;Width=1600;Height=1000}
        Placement=@{length=44;flags=0;showCmd=1;minX=0;minY=0;maxX=0;maxY=0;nLeft=$left;nTop=$top;nRight=($left+400);nBottom=($top+300)}
        NativeWarnings=@()
    }
}
function New-AegisV4Fixture {
    $rules=@(
        @{Id='editor';ProcessName='editor';Tier=2;GroupId='primary';Priority=100;GroupPriority=100;GroupWeight=2;SizeMode='Exact';Width=500;Height=340;Include=$true},
        @{Id='monitor';ProcessName='monitor';Tier=2;GroupId='secondary';Priority=50;GroupPriority=50;GroupWeight=1;SizeMode='Exact';Width=400;Height=280;Include=$true}
    )
    $state=@{
        Windows=@{'101'=(New-AegisV4TestWindow '101' 'editor' 0);'102'=(New-AegisV4TestWindow '102' 'monitor' 1)}
        Order=@('101','102');Calls=(New-Object System.Collections.ArrayList)
        Complete=$true;DesktopSafe=$true;TopologySignature='M1:0,0,1600,1000'
        ContextTopology='M1:0,0,1600,1000';InventoryCalls=0
        DelayMoves=$false;RejectMoves=$false;PendingTargets=@{}
        HideOnObserveId='';HideOnMoveId='';ReplaceOnObserveId='';MoveOnObserveId='';ChangeMonitorOnObserveId='';ThrowAfterDispatchId=''
        ContextCalls=0;ChangeTopologyAfterContext=0;InventoryThrows=$false
    }
    $script:AegisV4Mock=$state
    $options=New-AegisOptions -Overrides @{MoveTimeoutMs=30;PollMs=20;TotalTimeoutMs=5000}
    return @{Rules=$rules;Options=$options;State=$state}
}
function Get-AegisV4MockInventory {
    param($Options,$Rules)
    $state=$script:AegisV4Mock;$state.InventoryCalls++
    if ($state.InventoryThrows) {throw 'Inventory must not run.'}
    $records=New-Object System.Collections.ArrayList
    foreach ($id in $state.Order) {
        $current=$state.Windows[$id]
        if ($null -eq $current -or -not $current.Exists) {continue}
        $record=$current.Clone();$record.Monitor=$current.Monitor.Clone();$record.Placement=$current.Placement.Clone()
        [void]$records.Add($record)
    }
    return @{
        Complete=$state.Complete;DesktopSafe=$state.DesktopSafe;TopologySignature=$state.TopologySignature
        Warnings=@();Windows=@($records.ToArray());Foreground=$null
        CursorMonitor=@{Id='M1';Left=0;Top=0;Width=1600;Height=1000}
        Monitors=@(@{Id='M1';Left=0;Top=0;Width=1600;Height=1000})
        ElapsedMs=0;Reason='SyntheticInventory'
    }
}
$script:AegisV4InventoryProvider={param($Options,$Rules) Get-AegisV4MockInventory $Options $Rules}
$script:AegisV4Backend={
    param($Operation,$Window,$Target)
    $state=$script:AegisV4Mock
    $id='';if ($null -ne $Window) {$id=[string]$Window.Id}
    $call=@{Operation=$Operation;Id=$id;Target=$Target}
    [void]$state.Calls.Add($call)
    if ($Operation -eq 'Context') {
        $state.ContextCalls++
        if ($state.ChangeTopologyAfterContext -gt 0 -and $state.ContextCalls -gt $state.ChangeTopologyAfterContext) {$state.ContextTopology='M1:0,0,800,600'}
        return @{DesktopSafe=$state.DesktopSafe;Complete=$true;TopologySignature=$state.ContextTopology;Reason='SyntheticContext';ErrorCode=0}
    }
    $current=$state.Windows[$id]
    if ($Operation -eq 'Observe') {
        if ($id -eq $state.HideOnObserveId) {$current.Visible=$false;$state.HideOnObserveId=''}
        if ($id -eq $state.ReplaceOnObserveId) {$current.ProcessStart='ffffffffffffffff';$state.ReplaceOnObserveId=''}
        if ($id -eq $state.MoveOnObserveId) {$current.Left+=37;$state.MoveOnObserveId=''}
        if ($id -eq $state.ChangeMonitorOnObserveId) {$current.Monitor.Id='M2';$state.ChangeMonitorOnObserveId=''}
        if ($null -eq $current -or -not $current.Exists) {return @{Exists=$false;SameIdentity=$false;Reason='WindowMissing';ErrorCode=1400}}
        $same=($current.ProcessId -eq $Window.ProcessId -and $current.ThreadId -eq $Window.ThreadId -and $current.ProcessStart -eq $Window.ProcessStart -and $current.ClassName -eq $Window.ClassName)
        return @{
            Exists=$true;SameIdentity=$same;Reason='Observed';ErrorCode=0
            Visible=$current.Visible;Minimized=$current.Minimized;Maximized=$current.Maximized
            Enabled=$current.Enabled;Hung=$current.Hung;Cloaked=$current.Cloaked;CloakReady=$current.CloakReady;Resizable=$current.Resizable
            IdentityReady=$true;RectReady=$true;StyleReady=$true;PlacementReady=$true;SnapshotReady=$true;MinMaxReady=$current.MinMaxReady
            Left=$current.Left;Top=$current.Top;Width=$current.Width;Height=$current.Height
            Placement=$current.Placement.Clone();Monitor=$current.Monitor.Clone()
        }
    }
    if ($Operation -eq 'Move') {
        if ($id -eq $state.ThrowAfterDispatchId) {$state.PendingTargets[$id]=$Target.Clone();$state.ThrowAfterDispatchId='';throw 'Synthetic backend exception after possible async dispatch.'}
        if ($id -eq $state.HideOnMoveId) {$current.Visible=$false;$state.HideOnMoveId=''}
        if ($state.RejectMoves) {return @{Accepted=$false;ErrorCode=5;Reason='SyntheticRejected'}}
        if ($state.DelayMoves) {$state.PendingTargets[$id]=$Target.Clone();return @{Accepted=$true;ErrorCode=0;Reason='SyntheticQueued'}}
        $current.Left=$Target.Left;$current.Top=$Target.Top
        if ($Target.Resize) {$current.Width=$Target.Width;$current.Height=$Target.Height}
        $current.Placement.nLeft=$current.Left;$current.Placement.nTop=$current.Top
        $current.Placement.nRight=$current.Left+$current.Width;$current.Placement.nBottom=$current.Top+$current.Height
        return @{Accepted=$true;ErrorCode=0;Reason='SyntheticAccepted'}
    }
    throw ('Unsafe or unsupported native operation requested: '+$Operation)
}
function Get-AegisV4Calls {
    param([string]$Operation,[string]$Id='')
    $selectedCalls=New-Object System.Collections.ArrayList
    foreach ($call in $script:AegisV4Mock.Calls) {
        if ($call.Operation -eq $Operation -and ([string]::IsNullOrEmpty($Id) -or $call.Id -eq $Id)) {[void]$selectedCalls.Add($call)}
    }
    return ,@($selectedCalls.ToArray())
}
function Invoke-AegisV4TestController {
    param($Fixture,[string]$Action='Arrange',[string[]]$RuleIds=@(),[int]$Tier=0,[string]$GroupId='',[switch]$KeepSize,[switch]$Preview)
    return (Invoke-AegisController -Action $Action -Options $Fixture.Options -Rules $Fixture.Rules -Backend $script:AegisV4Backend -InventoryProvider $script:AegisV4InventoryProvider -RuleIds $RuleIds -Tier $Tier -GroupId $GroupId -KeepSize:$KeepSize -Preview:$Preview)
}
function Invoke-AegisV4Fixture {
    param([scriptblock]$Body)
    $saved=@{}
    foreach ($name in @('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult')) {
        $existing=Get-Variable -Scope Global -Name $name -ErrorAction SilentlyContinue
        $saved[$name]=@{Exists=($null -ne $existing);Value=$null}
        if ($null -ne $existing) {$saved[$name].Value=$existing.Value}
        Set-Variable -Scope Global -Name $name -Value $null
    }
    try {$fixture=New-AegisV4Fixture;& $Body $fixture}
    finally {
        foreach ($name in @('AegisLayoutProfile','AegisUndoState','AegisPendingMoves','AegisLastResult')) {
            if ($saved[$name].Exists) {Set-Variable -Scope Global -Name $name -Value $saved[$name].Value}
            else {Remove-Variable -Scope Global -Name $name -ErrorAction SilentlyContinue}
        }
    }
}
function Assert-AegisV4NoShowOrZ {
    foreach ($call in $script:AegisV4Mock.Calls) {
        Assert-AegisV4 (@('Context','Observe','Move') -contains $call.Operation) ('Show/focus/Z mutation: '+$call.Operation)
    }
}

Invoke-AegisV4Case 'V01' 'Inspect plans without mutating windows or creating home/undo state' {
    Invoke-AegisV4Fixture {param($f)
        $before=Copy-AegisV4TestRect $f.State.Windows['101']
        $report=Invoke-AegisV4TestController $f Inspect
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Inspect moved a window.'
        Assert-AegisV4 (Test-AegisV4TestRect $before $f.State.Windows['101']) 'Inspect changed geometry.'
        Assert-AegisV4 ($null -eq $global:AegisLayoutProfile -and $null -eq $global:AegisUndoState) 'Inspect created persistent layout state.'
        Assert-AegisV4 (@($report.Items).Count -ge 2) 'Inspect omitted windows.'
    }
}
Invoke-AegisV4Case 'V02' 'Empty allowlist never writes to arbitrary visible applications' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules=@();$report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Unlisted process was moved.'
    }
}
Invoke-AegisV4Case 'V03' 'Process size settings apply exact outer width and height' {
    Invoke-AegisV4Fixture {param($f)
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($f.State.Windows['101'].Width -eq 500 -and $f.State.Windows['101'].Height -eq 340) 'Editor exact size was not applied.'
        Assert-AegisV4 ($f.State.Windows['102'].Width -eq 400 -and $f.State.Windows['102'].Height -eq 280) 'Monitor exact size was not applied.'
        Assert-AegisV4 ($null -ne $global:AegisLayoutProfile) 'Normal home profile was not recorded.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V04' 'Repeated Arrange restores saved size after manual working resize' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$savedHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $f.State.Windows['101'].Width=650;$f.State.Windows['101'].Height=420;$f.State.Windows['101'].Left=300
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 (Test-AegisV4TestRect $savedHome $f.State.Windows['101']) 'Manual working size replaced the home profile.'
    }
}
Invoke-AegisV4Case 'V05' 'Selected Return moves only that process and restores its normal size' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$aHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $f.State.Windows['101'].Left=350;$f.State.Windows['101'].Top=150;$f.State.Windows['101'].Width=620
        $f.State.Windows['102'].Left=720;$bWorking=Copy-AegisV4TestRect $f.State.Windows['102']
        $f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 (Test-AegisV4TestRect $aHome $f.State.Windows['101']) 'Selected return did not restore editor home.'
        Assert-AegisV4 (Test-AegisV4TestRect $bWorking $f.State.Windows['102']) 'Selected return changed a different process.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0) 'Unselected process received a move request.'
    }
}
Invoke-AegisV4Case 'V06' 'KeepSize returns only the position while retaining a fitting work size' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$savedHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $f.State.Windows['101'].Left=350;$f.State.Windows['101'].Top=150;$f.State.Windows['101'].Width=550;$f.State.Windows['101'].Height=350
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor') -KeepSize)
        $actual=$f.State.Windows['101']
        Assert-AegisV4 ($actual.Left -eq $savedHome.Left -and $actual.Top -eq $savedHome.Top) 'Position was not restored.'
        Assert-AegisV4 ($actual.Width -eq 550 -and $actual.Height -eq 350) 'KeepSize resized the window.'
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 (Test-AegisV4TestRect $savedHome $actual) 'KeepSize overwrote normal saved dimensions.'
    }
}
Invoke-AegisV4Case 'V07' 'Oversized KeepSize is deferred without moving neighbors' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Width=4000;$before=Copy-AegisV4TestRect $f.State.Windows['101'];$other=Copy-AegisV4TestRect $f.State.Windows['102'];$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor') -KeepSize)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Oversized return attempted a move.'
        Assert-AegisV4 (Test-AegisV4TestRect $before $f.State.Windows['101']) 'Oversized current geometry was overwritten.'
        Assert-AegisV4 (Test-AegisV4TestRect $other $f.State.Windows['102']) 'Neighbor was reflowed by KeepSize.'
    }
}
Invoke-AegisV4Case 'V08' 'Home profile survives independent Undo journal removal' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$savedHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $global:AegisUndoState=$null;$f.State.Windows['101'].Left=700;$f.State.Windows['101'].Width=600
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 (Test-AegisV4TestRect $savedHome $f.State.Windows['101']) 'Home depended on Undo history.'
    }
}
Invoke-AegisV4Case 'V09' 'Initially hidden and minimized windows are never restored or moved' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].Visible=$false;$f.State.Windows['102'].Minimized=$true
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Hidden or minimized window moved.'
        Assert-AegisV4 (-not $f.State.Windows['101'].Visible -and $f.State.Windows['102'].Minimized) 'Display state changed.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V10' 'Undo preserves a window hidden after the prior arrangement' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$f.State.Windows['101'].Visible=$false;$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController $f Undo)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Undo moved a hidden window.'
        Assert-AegisV4 (-not $f.State.Windows['101'].Visible) 'Undo showed a hidden window.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V11' 'Hide between enumeration and first observation prevents a move' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.HideOnObserveId='101';[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Window hidden after inventory was moved.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V12' 'Rejected move while app hides never triggers show-state recovery' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.HideOnMoveId='101';$f.State.RejectMoves=$true
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 (-not $f.State.Windows['101'].Visible) 'Failure recovery revealed the window.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V13' 'Hidden slot retains its home while visible peers are arranged' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$savedHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $f.State.Windows['101'].Visible=$false;$f.State.Windows['102'].Left=700
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Visible=$true;$f.State.Windows['101'].Left=600
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 (Test-AegisV4TestRect $savedHome $f.State.Windows['101']) 'Hidden slot lost its normal place.'
    }
}
Invoke-AegisV4Case 'V14' 'Unique replacement HWND can rebind a saved process slot safely' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$savedHome=Copy-AegisV4TestRect $f.State.Windows['101']
        $f.State.Windows['101'].Exists=$false
        $f.State.Windows['201']=New-AegisV4TestWindow '201' 'editor' 8;$f.State.Order=@('201','102');$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 (Test-AegisV4TestRect $savedHome $f.State.Windows['201']) 'Unique replacement did not reconnect to home.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Old HWND was mutated.'
    }
}
Invoke-AegisV4Case 'V15' 'Two indistinguishable replacement windows do not guess one saved slot' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$f.State.Windows['101'].Exists=$false
        $f.State.Windows['201']=New-AegisV4TestWindow '201' 'editor' 8
        $f.State.Windows['202']=New-AegisV4TestWindow '202' 'editor' 9
        $f.State.Order=@('201','202','102');$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 ((Get-AegisV4Calls Move '201').Count -eq 0 -and (Get-AegisV4Calls Move '202').Count -eq 0) 'Ambiguous reattachment moved one arbitrary replacement.'
    }
}
Invoke-AegisV4Case 'V16' 'Undo never applies a previous process identity to a reused HWND' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].ProcessStart='ffffffffffffffff';$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController $f Undo)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Undo moved reused HWND.'
    }
}
Invoke-AegisV4Case 'V17' 'Undo preserves external manual changes after the managed operation' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Left=725;$before=Copy-AegisV4TestRect $f.State.Windows['101'];$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController $f Undo)
        Assert-AegisV4 (Test-AegisV4TestRect $before $f.State.Windows['101']) 'Undo overwrote a later manual move.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Undo issued a request over external geometry.'
    }
}
Invoke-AegisV4Case 'V18' 'Confirmed geometry Undo restores original rectangle without display-state calls' {
    Invoke-AegisV4Fixture {param($f)
        $a=Copy-AegisV4TestRect $f.State.Windows['101'];$b=Copy-AegisV4TestRect $f.State.Windows['102']
        [void](Invoke-AegisV4TestController $f Arrange);[void](Invoke-AegisV4TestController $f Undo)
        Assert-AegisV4 (Test-AegisV4TestRect $a $f.State.Windows['101']) 'Editor original rectangle not restored.'
        Assert-AegisV4 (Test-AegisV4TestRect $b $f.State.Windows['102']) 'Monitor original rectangle not restored.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V19' 'Accepted async timeout does not enqueue rollback or a competing retry' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.DelayMoves=$true;[void](Invoke-AegisV4TestController $f Arrange)
        $initial=(Get-AegisV4Calls Move '101').Count
        Assert-AegisV4 ($initial -eq 1) 'Expected exactly one accepted editor request.'
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq $initial) 'Timeout was followed by a competing move.'
        Assert-AegisV4 ($null -ne $global:AegisPendingMoves) 'Unconfirmed async request lost its pending state.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V20' 'Observing the original rectangle does not prove a queued move cancelled' {
    Invoke-AegisV4Fixture {param($f)
        $before=Copy-AegisV4TestRect $f.State.Windows['101'];$f.State.DelayMoves=$true
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 (Test-AegisV4TestRect $before $f.State.Windows['101']) 'Synthetic queued move unexpectedly applied.'
        $count=(Get-AegisV4Calls Move '101').Count
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq $count) 'Original observed geometry cleared pending uncertainty.'
    }
}
Invoke-AegisV4Case 'V21' 'Incomplete inventory never applies a partial plan' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Complete=$false;[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Incomplete inventory produced writes.'
    }
}
Invoke-AegisV4Case 'V22' 'Unsafe input desktop prevents all mutations' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.DesktopSafe=$false;[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Unsafe or locked desktop was modified.'
    }
}
Invoke-AegisV4Case 'V23' 'Topology changed since planning prevents geometry writes' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.ContextTopology='M1:0,0,800,600';[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Stale monitor plan was applied.'
    }
}
Invoke-AegisV4Case 'V24' 'Identity replaced after inventory is not moved' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.ReplaceOnObserveId='101';[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Changed identity received a write.'
    }
}
Invoke-AegisV4Case 'V25' 'Unknown resize constraints defer an exact size change' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].MinMaxReady=$false;$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Exact resize attempted with unknown app constraints.'
    }
}
Invoke-AegisV4Case 'V26' 'Non-resizable tiny windows remain movable under Preserve size mode' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules[0].SizeMode='Preserve';$f.Rules[0].Remove('Width');$f.Rules[0].Remove('Height')
        $f.State.Windows['101'].Resizable=$false;$f.State.Windows['101'].Width=160;$f.State.Windows['101'].Height=90
        $before=Copy-AegisV4TestRect $f.State.Windows['101'];[void](Invoke-AegisV4TestController $f Arrange)
        $after=$f.State.Windows['101']
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1) 'Tiny non-resizable window was not moved.'
        Assert-AegisV4 ($after.Width -eq 160 -and $after.Height -eq 90) 'Tiny window was resized.'
        Assert-AegisV4 (-not (Test-AegisV4TestRect $before $after)) 'Tiny window remained at its arbitrary original position.'
    }
}
Invoke-AegisV4Case 'V27' 'Reflow of one saved group leaves the other group untouched' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Left=700;$b=Copy-AegisV4TestRect $f.State.Windows['102'];$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Reflow -Tier 2 -GroupId primary)
        Assert-AegisV4 (Test-AegisV4TestRect $b $f.State.Windows['102']) 'Scoped reflow changed outside group.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0) 'Outside group received request.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1) 'Target group did not reflow.'
    }
}
Invoke-AegisV4Case 'V28' 'Maximum managed-window budget blocks unsafe truncation' {
    Invoke-AegisV4Fixture {param($f)
        $f.Options.MaxWindows=1;[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Managed-window limit silently truncated a writable plan.'
    }
}
Invoke-AegisV4Case 'V29' 'Maximized display state is preserved without automatic normalization' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].Maximized=$true;[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Maximized window was moved.'
        Assert-AegisV4 $f.State.Windows['101'].Maximized 'Maximized state was cleared.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V30' 'Process matching is exact rather than a process-name substring' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].ProcessName='editor-helper';[void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Substring process name matched an explicit rule.'
    }
}

Invoke-AegisV4Case 'V31' 'Late completion resolves async uncertainty without replaying the same move' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.DelayMoves=$true;[void](Invoke-AegisV4TestController $f Arrange)
        $aCount=(Get-AegisV4Calls Move '101').Count
        foreach ($queuedId in @($f.State.PendingTargets.Keys)) {
            $target=$f.State.PendingTargets[$queuedId];$current=$f.State.Windows[$queuedId]
            $current.Left=$target.Left;$current.Top=$target.Top
            if ($target.Resize) {$current.Width=$target.Width;$current.Height=$target.Height}
            $current.Placement.nLeft=$current.Left;$current.Placement.nTop=$current.Top
            $current.Placement.nRight=$current.Left+$current.Width;$current.Placement.nBottom=$current.Top+$current.Height
        }
        $f.State.DelayMoves=$false
        $report=Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor')
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq $aCount) 'Confirmed late move was replayed.'
        Assert-AegisV4 ($report.PendingCount -eq 0) 'Late target confirmation did not clear pending uncertainty.'
    }
}
Invoke-AegisV4Case 'V32' 'A hidden original HWND prevents binding its home to a new visible instance' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange);$f.State.Windows['101'].Visible=$false
        $f.State.Windows['201']=New-AegisV4TestWindow '201' 'editor' 8;$f.State.Order=@('101','201','102');$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 ((Get-AegisV4Calls Move '201').Count -eq 0) 'Hidden original was treated as a released slot.'
    }
}
Invoke-AegisV4Case 'V33' 'Exact class and title restrictions refine the process allowlist' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules[0].ClassName='MainEditor';$f.Rules[1].Title='Approved monitor'
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Unmatched class/title restriction was ignored.'
    }
}
Invoke-AegisV4Case 'V34' 'Return without a saved profile does not silently arrange fresh windows' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor'))
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'No-profile Return performed a fresh arrangement.'
        Assert-AegisV4 ($null -eq $global:AegisLayoutProfile) 'No-profile Return created a replacement baseline.'
    }
}
Invoke-AegisV4Case 'V35' 'Each accepted mutation carries stale-rectangle and topology guards' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        foreach ($request in (Get-AegisV4Calls Move)) {
            Assert-AegisV4 ($null -ne $request.Target.ExpectedRect) 'Move lacks expected current rectangle.'
            Assert-AegisV4 ($null -ne $request.Target.ExpectedMonitor) 'Move lacks expected current monitor.'
            Assert-AegisV4 ($request.Target.ExpectedTopologySignature -eq $f.State.TopologySignature) 'Move lacks the planned topology signature.'
        }
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -gt 0) 'Guard test exercised no mutation.'
    }
}
Invoke-AegisV4Case 'V36' 'No-op repeated arrangement does not discard the useful Undo journal' {
    Invoke-AegisV4Fixture {param($f)
        $original=Copy-AegisV4TestRect $f.State.Windows['101']
        [void](Invoke-AegisV4TestController $f Arrange);$count=(Get-AegisV4Calls Move).Count
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Stable repeat performed redundant writes.'
        [void](Invoke-AegisV4TestController $f Undo)
        Assert-AegisV4 (Test-AegisV4TestRect $original $f.State.Windows['101']) 'No-op repeat discarded original Undo geometry.'
    }
}
Invoke-AegisV4Case 'V37' 'An unassigned new process window is not silently inserted by Arrange' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['201']=New-AegisV4TestWindow '201' 'editor' 8;$f.State.Order=@('101','201','102');$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '201').Count -eq 0) 'New window was inserted without explicit Reflow.'
    }
}
Invoke-AegisV4Case 'V38' 'Inspect during an uncertain request never sends a compensating mutation' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.DelayMoves=$true;[void](Invoke-AegisV4TestController $f Arrange)
        $count=(Get-AegisV4Calls Move).Count
        [void](Invoke-AegisV4TestController $f Inspect)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Inspect caused pending recovery writes.'
        Assert-AegisV4NoShowOrZ
    }
}
Invoke-AegisV4Case 'V39' 'A nonresponsive or disabled target remains untouched' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].Hung=$true;$f.State.Windows['102'].Enabled=$false
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Hung or disabled target was mutated.'
    }
}
Invoke-AegisV4Case 'V40' 'Tier-local Reflow never moves a window in another tier' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules[1].Tier=1
        [void](Invoke-AegisV4TestController $f Arrange)
        $other=Copy-AegisV4TestRect $f.State.Windows['102'];$f.State.Windows['101'].Left=800;$f.State.Calls.Clear()
        [void](Invoke-AegisV4TestController -Fixture $f -Action Reflow -Tier 2)
        Assert-AegisV4 (Test-AegisV4TestRect $other $f.State.Windows['102']) 'Tier-local Reflow changed another tier.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0) 'Other tier received a move request.'
    }
}

Invoke-AegisV4Case 'V41' 'Imported profile rejects slot metadata inconsistent with its process rule' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile
        $changed.Slots[0].Tier=3;$changed.Slots[0].GroupId='unrelated'
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Inconsistent saved slot rule/tier/group was accepted.'
    }
}
Invoke-AegisV4Case 'V42' 'Imported profile rejects an off-monitor saved group boundary' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile
        foreach ($zone in $changed.Zones) {if ($zone.Level -eq 'Group') {$zone.Left=5000;$zone.Top=5000;break}}
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Off-monitor saved group boundary was accepted.'
    }
}

Invoke-AegisV4Case 'V43' 'Imported profile rejects two slots bound to one native identity' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile
        $changed.Slots[1].Identity=Copy-AegisData $changed.Slots[0].Identity
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Two slots bound to one native identity were accepted.'
    }
}
Invoke-AegisV4Case 'V44' 'Imported profile rejects a duplicated group zone key' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile
        foreach ($zone in $changed.Zones) {if ($zone.Level -eq 'Group') {$changed.Zones+=@(Copy-AegisData $zone);break}}
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Duplicate group boundary key was accepted.'
    }
}
Invoke-AegisV4Case 'V45' 'Imported profile rejects fractional saved rectangle coordinates' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile;$changed.Slots[0].HomeRect.Left=8.5
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Fractional stored geometry was accepted.'
    }
}
Invoke-AegisV4Case 'V46' 'Imported profile rejects an unexpected executable field without evaluating it' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile
        $script:AegisV4UnexpectedEvaluated=$false
        $changed.Slots[0].UnexpectedCode={$script:AegisV4UnexpectedEvaluated=$true}
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 ($rejected -and -not $script:AegisV4UnexpectedEvaluated) 'Unexpected executable field was accepted or evaluated.'
    }
}
Invoke-AegisV4Case 'V47' 'Imported profile rejects configuration changed without its checksum' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $changed=Copy-AegisData $global:AegisLayoutProfile;$changed.Rules[0].Width++
        $rejected=$false;try {Test-AegisProfile $changed} catch {$rejected=$true}
        Assert-AegisV4 $rejected 'Changed saved rules bypassed policy checksum validation.'
    }
}

Invoke-AegisV4Case 'V48' 'Repeated Reflow keeps a newly admitted window stable despite tied observed order' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['201']=New-AegisV4TestWindow '201' 'editor' 8
        $f.State.Windows['201'].Order=0;$f.State.Windows['101'].Order=0
        $f.State.Order=@('201','101','102')
        [void](Invoke-AegisV4TestController -Fixture $f -Action Reflow -Tier 2 -GroupId primary)
        $existing=Copy-AegisV4TestRect $f.State.Windows['101'];$added=Copy-AegisV4TestRect $f.State.Windows['201']
        Assert-AegisV4 ((Get-AegisV4Calls Move '201').Count -eq 1) 'New editor did not receive a group slot.'
        $count=(Get-AegisV4Calls Move).Count
        [void](Invoke-AegisV4TestController -Fixture $f -Action Reflow -Tier 2 -GroupId primary)
        Assert-AegisV4 (Test-AegisV4TestRect $existing $f.State.Windows['101']) 'Existing editor swapped slots on immediate repeated Reflow.'
        Assert-AegisV4 (Test-AegisV4TestRect $added $f.State.Windows['201']) 'New editor swapped slots on immediate repeated Reflow.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Stable repeated Reflow performed redundant moves.'
    }
}

Invoke-AegisV4Case 'V49' 'Unknown cloak state prevents a mutation' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['101'].CloakReady=$false
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Unknown cloak state was treated as safely visible.'
    }
}
Invoke-AegisV4Case 'V50' 'Manual geometry change after inventory is preserved by first observation' {
    Invoke-AegisV4Fixture {param($f)
        $starting=Copy-AegisV4TestRect $f.State.Windows['101'];$f.State.MoveOnObserveId='101'
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'User change during planning was overwritten.'
        Assert-AegisV4 ($f.State.Windows['101'].Left -eq ($starting.Left+37)) 'Concurrent user position was not preserved.'
    }
}
Invoke-AegisV4Case 'V51' 'Fresh monitor differs from inventory so the original plan is deferred' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.ChangeMonitorOnObserveId='101'
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 0) 'Plan crossed a newly changed window monitor.'
    }
}
Invoke-AegisV4Case 'V52' 'A one-mutation budget applies the high-priority group before enumeration order' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Order=@('102','101');$f.State.Windows['102'].Order=0;$f.State.Windows['101'].Order=1
        $f.Options.MaxMutations=1
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1) 'High-priority group did not receive the available mutation.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0) 'Low-priority enumeration row consumed the mutation budget.'
        Assert-AegisV4 ($report.PendingCount -eq 0) 'A pre-dispatch budget rejection created false async uncertainty.'
    }
}
Invoke-AegisV4Case 'V53' 'An existing home that cannot fit Reflow blocks profile replacement and all writes' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $oldRevision=$global:AegisLayoutProfile.Revision;$oldCount=@($global:AegisLayoutProfile.Slots).Count
        $f.State.Windows['101'].MinWidth=2000;$f.State.Calls.Clear()
        $report=Invoke-AegisV4TestController -Fixture $f -Action Reflow -Tier 2
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Reflow partially wrote before preserving an unplaceable saved home.'
        Assert-AegisV4 ($global:AegisLayoutProfile.Revision -eq $oldRevision -and @($global:AegisLayoutProfile.Slots).Count -eq $oldCount) 'Reflow erased or replaced the unplaceable saved home.'
        Assert-AegisV4 (@($global:AegisLayoutProfile.Slots | Where-Object {$_.RuleId -eq 'editor'}).Count -eq 1) 'Original editor home was lost.'
        Assert-AegisV4 ($report.Status -ne 'Complete') 'Blocked Reflow reported complete success.'
    }
}
Invoke-AegisV4Case 'V54' 'An exception after possible backend dispatch is retained as pending and stops the batch' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.ThrowAfterDispatchId='101'
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1) 'Expected one possibly dispatched request.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0) 'Batch continued after an uncertain backend failure.'
        Assert-AegisV4 ($report.PendingCount -eq 1) 'Potentially accepted request lost pending protection.'
        $count=(Get-AegisV4Calls Move).Count
        [void](Invoke-AegisV4TestController $f Arrange)
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Unconfirmed backend exception permitted a new write.'
    }
}

Invoke-AegisV4Case 'V55' 'Undo does not reinterpret saved coordinates after a consistent topology change' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $current=Copy-AegisV4TestRect $f.State.Windows['101'];$f.State.Calls.Clear()
        $f.State.TopologySignature='coordinate-changed|M1:0,0,1600,1000';$f.State.ContextTopology=$f.State.TopologySignature
        $report=Invoke-AegisV4TestController $f Undo
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Undo applied old coordinates under a changed context.'
        Assert-AegisV4 (Test-AegisV4TestRect $current $f.State.Windows['101']) 'Changed-coordinate Undo altered geometry.'
        Assert-AegisV4 ($report.Status -ne 'Complete') 'Changed-coordinate Undo claimed complete success.'
    }
}
Invoke-AegisV4Case 'V56' 'A pending target rectangle under changed coordinates remains uncertain' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.DelayMoves=$true;[void](Invoke-AegisV4TestController $f Arrange)
        foreach ($queuedId in @($f.State.PendingTargets.Keys)) {
            $target=$f.State.PendingTargets[$queuedId];$current=$f.State.Windows[$queuedId]
            $current.Left=$target.Left;$current.Top=$target.Top
            if ($target.Resize) {$current.Width=$target.Width;$current.Height=$target.Height}
        }
        $count=(Get-AegisV4Calls Move).Count
        $f.State.TopologySignature='coordinate-changed|M1:0,0,1600,1000';$f.State.ContextTopology=$f.State.TopologySignature
        $report=Invoke-AegisV4TestController $f Inspect
        Assert-AegisV4 ($report.PendingCount -gt 0) 'Numeric rectangle equality discarded the old coordinate context.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Pending context change permitted another write.'
    }
}

Invoke-AegisV4Case 'V57' 'Saved-home Preview defers resizing when current app constraints are unknown' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Width=600;$f.State.Windows['101'].MinMaxReady=$false;$f.State.Calls.Clear()
        $preview=Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor') -Preview
        $apply=Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor')
        foreach ($report in @($preview,$apply)) {
            Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'ResizeConstraintsUnavailable'}).Count -eq 1) 'Preview and apply disagreed about unavailable current resize constraints.'
            Assert-AegisV4 ($report.ExitCode -eq 1) 'An unavailable saved-home resize was reported as successful.'
        }
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Constraint rejection dispatched a move.'
    }
}
Invoke-AegisV4Case 'V58' 'Saved-home Preview rejects dimensions outside current app bounds' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].Width=650;$f.State.Windows['101'].MinWidth=600;$f.State.Calls.Clear()
        $preview=Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor') -Preview
        $apply=Invoke-AegisV4TestController -Fixture $f -Action Return -RuleIds @('editor')
        foreach ($report in @($preview,$apply)) {
            Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'CurrentSizeConstraintsRejectTarget'}).Count -eq 1) 'Preview and apply disagreed about current app minimums.'
        }
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Out-of-bounds saved-home resize dispatched a move.'
    }
}
Invoke-AegisV4Case 'V59' 'Undo Preview preserves later manual edits and leaves the stored journal unchanged' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $entry=$global:AegisUndoState.Entries[0];$journalWindow=$entry.Window
        $f.State.Windows['101'].Left+=100;$f.State.Calls.Clear()
        $preview=Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor') -Preview
        Assert-AegisV4 (@($preview.Items | Where-Object {$_.Id -eq '101' -and $_.Reason -eq 'ExternalChangePreserved' -and $_.Status -eq 'Deferred'}).Count -eq 1) 'Undo Preview promised to overwrite a later manual edit.'
        Assert-AegisV4 ([object]::ReferenceEquals($journalWindow,$entry.Window) -and -not $entry.Restored) 'Undo Preview refreshed or retired the stored journal entry.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0 -and $preview.Counters.Mutations -eq 0) 'Undo Preview dispatched a mutation.'
    }
}
Invoke-AegisV4Case 'V60' 'Undo Preview preserves hidden minimized and maximized app states' {
    foreach ($stateName in @('Visible','Minimized','Maximized')) {
        Invoke-AegisV4Fixture {param($f)
            [void](Invoke-AegisV4TestController $f Arrange)
            $f.State.Windows['101'][$stateName]=($stateName -ne 'Visible');$f.State.Calls.Clear()
            $preview=Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor') -Preview
            Assert-AegisV4 (@($preview.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Planned'}).Count -eq 0) ('Protected app was marked Planned: '+$stateName)
            Assert-AegisV4 (@($preview.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Deferred'}).Count -eq 1) ('Protected app did not explain its deferred Undo: '+$stateName)
            Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Protected Undo Preview dispatched a move.'
        }
    }
}
Invoke-AegisV4Case 'V61' 'Undo Preview recognizes already restored geometry without retiring live Undo state' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $entry=$global:AegisUndoState.Entries[0];$journalWindow=$entry.Window
        foreach ($key in @('Left','Top','Width','Height')) {$f.State.Windows['101'][$key]=$entry.Before[$key]}
        $f.State.Calls.Clear()
        $preview=Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor') -Preview
        Assert-AegisV4 (@($preview.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'AlreadyRestored'}).Count -eq 1) 'Undo Preview failed to report an already restored window.'
        Assert-AegisV4 (-not $entry.Restored -and [object]::ReferenceEquals($journalWindow,$entry.Window)) 'Undo Preview retired or replaced live journal state.'
        [void](Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor'))
        Assert-AegisV4 ($entry.Restored -and (Get-AegisV4Calls Move).Count -eq 0) 'Actual no-op Undo failed to retire its entry without dispatch.'
    }
}
Invoke-AegisV4Case 'V62' 'CurrentMonitor Undo preserves outside-monitor windows even with intentionally incomplete native rows' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.Windows['102'].Monitor=@{Id='M2';Left=1600;Top=0;Width=1600;Height=1000};$f.State.Windows['102'].Left=1700
        $f.State.TopologySignature='M1:0,0,1600,1000|M2:1600,0,1600,1000';$f.State.ContextTopology=$f.State.TopologySignature
        $provider={param($Options,$Rules)
            $result=Get-AegisV4MockInventory $Options $Rules
            $result.Monitors=@(@{Id='M1';Left=0;Top=0;Width=1600;Height=1000},@{Id='M2';Left=1600;Top=0;Width=1600;Height=1000})
            if ($Options.MonitorScope -eq 'CurrentMonitor') {
                foreach ($row in $result.Windows) {
                    if ($row.Monitor.Id -eq 'M2') {$row.IdentityReady=$false;$row.SnapshotReady=$false;$row.ProcessStart='';$row.SelectionReason='OutsideCurrentMonitor'}
                }
            }
            return $result
        }
        [void](Invoke-AegisController -Action Arrange -Options $f.Options -Rules $f.Rules -Backend $script:AegisV4Backend -InventoryProvider $provider)
        $outside=Copy-AegisV4TestRect $f.State.Windows['102'];$f.Options.MonitorScope='CurrentMonitor';$f.State.Calls.Clear()
        $preview=Invoke-AegisController -Action Undo -Options $f.Options -Rules $f.Rules -Backend $script:AegisV4Backend -InventoryProvider $provider -Preview
        $apply=Invoke-AegisController -Action Undo -Options $f.Options -Rules $f.Rules -Backend $script:AegisV4Backend -InventoryProvider $provider
        foreach ($report in @($preview,$apply)) {
            $rows=@($report.Items | Where-Object {$_.Id -eq '102'})
            Assert-AegisV4 ($rows.Count -eq 1 -and $rows[0].Status -eq 'Skipped' -and $rows[0].Reason -eq 'OutsideCurrentMonitor') 'Outside-monitor Undo was not represented by one scope skip.'
        }
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1) 'Current-monitor Undo did not restore the scoped window.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '102').Count -eq 0 -and (Get-AegisV4Calls Observe '102').Count -eq 0) 'Outside-monitor Undo performed detailed observation or mutation.'
        Assert-AegisV4 (Test-AegisV4TestRect $outside $f.State.Windows['102']) 'Outside-monitor geometry changed.'
    }
}
Invoke-AegisV4Case 'V63' 'An unavailable cursor monitor blocks CurrentMonitor actions' {
    Invoke-AegisV4Fixture {param($f)
        $f.Options.MonitorScope='CurrentMonitor'
        $provider={param($Options,$Rules) $result=Get-AegisV4MockInventory $Options $Rules;$result.CursorMonitor=$null;return $result}
        $report=Invoke-AegisController -Action Arrange -Options $f.Options -Rules $f.Rules -Backend $script:AegisV4Backend -InventoryProvider $provider
        Assert-AegisV4 ($report.Status -eq 'BlockedContext' -and $report.ExitCode -eq 2) 'Unavailable CurrentMonitor was interpreted as an empty successful scope.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Unknown CurrentMonitor published a profile or moved a window.'
    }
}
Invoke-AegisV4Case 'V64' 'Coordinate context changing after dispatch prevents confirmation and stops later moves' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.ChangeTopologyAfterContext=1
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($report.Status -eq 'BlockedPending' -and $report.PendingCount -eq 1) 'Post-dispatch coordinate change was confirmed as success.'
        Assert-AegisV4 ((Get-AegisV4Calls Move '101').Count -eq 1 -and (Get-AegisV4Calls Move '102').Count -eq 0) 'Unconfirmed coordinate change did not stop later requests.'
        Assert-AegisV4 (-not $global:AegisUndoState.Entries[0].Confirmed -and -not $global:AegisLayoutProfile.Slots[0].HomeConfirmed) 'Post-dispatch coordinate change marked saved geometry confirmed.'
        Assert-AegisV4 (@($report.Items | Where-Object {$_.Reason -eq 'Pending:ConfirmationContextChangedOrUnavailable'}).Count -eq 1) 'Context uncertainty was not explained.'
    }
}
Invoke-AegisV4Case 'V65' 'Unsafe unavailable or malformed post-dispatch context keeps accepted requests pending' {
    foreach ($contextKind in @('Unsafe','Unavailable','Malformed')) {
        Invoke-AegisV4Fixture {param($f)
            $backend={param($Operation,$Window,$Target)
                $result=& $script:AegisV4Backend $Operation $Window $Target
                if ($Operation -eq 'Context' -and $script:AegisV4Mock.ContextCalls -gt 1) {
                    if ($contextKind -eq 'Unsafe') {$result.DesktopSafe=$false}
                    if ($contextKind -eq 'Unavailable') {return $null}
                    if ($contextKind -eq 'Malformed') {$result.Complete='true'}
                }
                return $result
            }
            $report=Invoke-AegisController -Action Arrange -Options $f.Options -Rules $f.Rules -Backend $backend -InventoryProvider $script:AegisV4InventoryProvider
            Assert-AegisV4 ($report.PendingCount -eq 1 -and $report.Status -eq 'BlockedPending') ('Invalid post-dispatch context lost pending protection: '+$contextKind)
            Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 1) 'Invalid confirmation context allowed a later mutation.'
        }
    }
}
Invoke-AegisV4Case 'V66' 'Observation budget exhaustion during context confirmation retains the accepted request' {
    Invoke-AegisV4Fixture {param($f)
        $f.Options.MaxObservations=3
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($report.Counters.Observations -eq 3 -and $report.PendingCount -eq 1 -and $report.Status -eq 'BlockedPending') 'Confirmation budget exhaustion either exceeded its cap or lost pending protection.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 1 -and @($report.Items | Where-Object {$_.Reason -eq 'Pending:ObservationBudgetExceeded'}).Count -eq 1) 'Confirmation budget exhaustion was not reported after one accepted request.'
    }
}
Invoke-AegisV4Case 'V67' 'An unconfirmed post-dispatch context can resolve later under the original context without another move' {
    Invoke-AegisV4Fixture {param($f)
        $originalTopology=$f.State.ContextTopology;$f.State.ChangeTopologyAfterContext=1
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.ChangeTopologyAfterContext=0;$f.State.ContextTopology=$originalTopology
        $count=(Get-AegisV4Calls Move).Count
        $report=Invoke-AegisV4TestController $f Inspect
        Assert-AegisV4 ($report.PendingCount -eq 0 -and @($report.Items | Where-Object {$_.Status -eq 'Resolved' -and $_.Reason -eq 'LateTargetObserved'}).Count -eq 1) 'Safe late context confirmation could not resolve the pending request.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq $count) 'Late context confirmation replayed a request.'
    }
}
Invoke-AegisV4Case 'V68' 'Preview observes a hide occurring after inventory and never dispatches geometry' {
    Invoke-AegisV4Fixture {param($f)
        $f.State.HideOnObserveId='101'
        $report=Invoke-AegisV4TestController $f Inspect
        Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'HiddenStatePreserved'}).Count -eq 1) 'Preview did not observe a state change after inventory.'
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0 -and $report.Counters.Mutations -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Preview dispatched a move or published a profile.'
    }
}
Invoke-AegisV4Case 'V69' 'Undo Preview rejects original dimensions outside newly changed app bounds' {
    Invoke-AegisV4Fixture {param($f)
        [void](Invoke-AegisV4TestController $f Arrange)
        $f.State.Windows['101'].MinWidth=450;$f.State.Calls.Clear()
        $preview=Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor') -Preview
        $apply=Invoke-AegisV4TestController -Fixture $f -Action Undo -RuleIds @('editor')
        foreach ($report in @($preview,$apply)) {
            Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq '101' -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'CurrentSizeConstraintsRejectTarget'}).Count -eq 1) 'Undo Preview and apply disagreed about current app minimums.'
        }
        Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0) 'Out-of-bounds Undo dispatched a mutation.'
    }
}

function Initialize-AegisV4KeepSizeCorner {
    param($Fixture)
    $Fixture.Rules=@(@{Id='editor';ProcessName='editor';Tier=2;GroupId='work';Priority=100;GroupPriority=100;GroupWeight=100;SizeMode='Exact';Width=400;Height=400;Include=$true})
    $Fixture.State.Windows=@{};$Fixture.State.Order=@('101','102','103')
    foreach ($id in $Fixture.State.Order) {
        $window=New-AegisV4TestWindow $id 'editor' ([int]$id-101)
        $window.Monitor=@{Id='M1';Left=0;Top=0;Width=1000;Height=1000}
        $Fixture.State.Windows[$id]=$window
    }
    $Fixture.State.TopologySignature='M1:0,0,1000,1000';$Fixture.State.ContextTopology=$Fixture.State.TopologySignature
    $initial=Invoke-AegisV4TestController $Fixture Arrange
    Assert-AegisV4 ($initial.ExitCode -eq 0) 'Initial corner layout failed.'
    $slots=@($global:AegisLayoutProfile.Slots)
    $right=@($slots | Sort-Object @{Expression={$_.HomeRect.Left};Descending=$true},@{Expression={$_.HomeRect.Top}})[0]
    $lower=@($slots | Sort-Object @{Expression={$_.HomeRect.Top};Descending=$true},@{Expression={$_.HomeRect.Left}})[0]
    Assert-AegisV4 ($right.SlotId -ne $lower.SlotId) 'Fixture has no empty diagonal cell.'
    $other=@($slots | Where-Object {$_.SlotId -ne $right.SlotId -and $_.SlotId -ne $lower.SlotId})[0]
    return @{RightId=$right.Identity.Id;LowerId=$lower.Identity.Id;OtherId=$other.Identity.Id;RightHome=(Copy-AegisV4TestRect $right.HomeRect);LowerHome=(Copy-AegisV4TestRect $lower.HomeRect)}
}
function Set-AegisV4CrossingWorkSizes {
    param($Fixture,$Corner)
    $Fixture.State.Windows[$Corner.RightId].Height=850
    $Fixture.State.Windows[$Corner.LowerId].Width=850
    # Working windows remain partly visible and do not overlap before Return.
    $Fixture.State.Windows[$Corner.RightId].Left=900
    $Fixture.State.Windows[$Corner.LowerId].Top=900
}

Invoke-AegisV4Case 'V70' 'KeepSize defers crossing batch targets while an independent target still returns' {
    Invoke-AegisV4Fixture {param($f)
        $corner=Initialize-AegisV4KeepSizeCorner $f
        Set-AegisV4CrossingWorkSizes $f $corner
        $rightBefore=Copy-AegisV4TestRect $f.State.Windows[$corner.RightId]
        $lowerBefore=Copy-AegisV4TestRect $f.State.Windows[$corner.LowerId]
        Assert-AegisV4 (-not (Test-AegisRectsOverlap $rightBefore $lowerBefore)) 'Working windows overlap before the command.'
        $otherHome=Copy-AegisV4TestRect $f.State.Windows[$corner.OtherId]
        $f.State.Windows[$corner.OtherId].Left+=17;$f.State.Calls.Clear()
        $report=Invoke-AegisV4TestController $f Return -KeepSize
        foreach ($id in @($corner.RightId,$corner.LowerId)) {
            Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq $id -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'CurrentSizesOverlapWithinBatch'}).Count -eq 1) 'A crossing target was not deferred.'
            Assert-AegisV4 ((Get-AegisV4Calls Move $id).Count -eq 0) 'A crossing target was moved.'
        }
        Assert-AegisV4 ((Test-AegisV4TestRect $rightBefore $f.State.Windows[$corner.RightId]) -and (Test-AegisV4TestRect $lowerBefore $f.State.Windows[$corner.LowerId])) 'Deferred work geometry was changed.'
        Assert-AegisV4 ((Get-AegisV4Calls Move $corner.OtherId).Count -eq 1 -and (Test-AegisV4TestRect $otherHome $f.State.Windows[$corner.OtherId])) 'Independent nonconflicting target did not return.'
        Assert-AegisV4 ($report.Status -eq 'Partial' -and $report.ExitCode -eq 1 -and $report.Counters.Mutations -eq 1) 'Conflicting targets were reported complete or used mutation budget.'
    }
}
Invoke-AegisV4Case 'V71' 'KeepSize previews and reversed enumeration make the same collision decision without publishing state' {
    foreach ($reverse in @($false,$true)) {
        foreach ($actionName in @('Return','Arrange','Inspect')) {
            Invoke-AegisV4Fixture {param($f)
                $corner=Initialize-AegisV4KeepSizeCorner $f
                Set-AegisV4CrossingWorkSizes $f $corner
                if ($reverse) { $f.State.Order=@('103','102','101') }
                $savedProfile=$global:AegisLayoutProfile;$savedUndo=$global:AegisUndoState
                $rightBefore=Copy-AegisV4TestRect $f.State.Windows[$corner.RightId]
                $lowerBefore=Copy-AegisV4TestRect $f.State.Windows[$corner.LowerId]
                $f.State.Calls.Clear()
                $report=Invoke-AegisV4TestController -Fixture $f -Action $actionName -KeepSize -Preview
                foreach ($id in @($corner.RightId,$corner.LowerId)) {
                    Assert-AegisV4 (@($report.Items | Where-Object {$_.Id -eq $id -and $_.Status -eq 'Deferred' -and $_.Reason -eq 'CurrentSizesOverlapWithinBatch'}).Count -eq 1) 'Preview or enumeration changed the collision decision.'
                }
                Assert-AegisV4 ((Get-AegisV4Calls Move).Count -eq 0 -and $report.Counters.Mutations -eq 0) 'Collision Preview dispatched a mutation.'
                Assert-AegisV4 ([object]::ReferenceEquals($savedProfile,$global:AegisLayoutProfile) -and [object]::ReferenceEquals($savedUndo,$global:AegisUndoState)) 'Collision Preview published profile or journal state.'
                Assert-AegisV4 ((Test-AegisV4TestRect $rightBefore $f.State.Windows[$corner.RightId]) -and (Test-AegisV4TestRect $lowerBefore $f.State.Windows[$corner.LowerId])) 'Collision Preview changed working geometry.'
            }
        }
    }
}
Invoke-AegisV4Case 'V72' 'Multiple nonconflicting KeepSize targets retain their working sizes and return normally' {
    Invoke-AegisV4Fixture {param($f)
        $corner=Initialize-AegisV4KeepSizeCorner $f
        $right=$f.State.Windows[$corner.RightId];$lower=$f.State.Windows[$corner.LowerId]
        $right.Height=450;$right.Left=900;$lower.Width=450;$lower.Top=900
        $f.State.Calls.Clear()
        $report=Invoke-AegisV4TestController $f Return -KeepSize
        Assert-AegisV4 ($report.ExitCode -eq 0 -and (Get-AegisV4Calls Move).Count -eq 2) 'Independent KeepSize targets were blocked.'
        Assert-AegisV4 ($right.Left -eq $corner.RightHome.Left -and $right.Top -eq $corner.RightHome.Top -and $right.Height -eq 450) 'Right target lost its working size or home position.'
        Assert-AegisV4 ($lower.Left -eq $corner.LowerHome.Left -and $lower.Top -eq $corner.LowerHome.Top -and $lower.Width -eq 450) 'Lower target lost its working size or home position.'
        $moveCalls=Get-AegisV4Calls Move
        foreach ($call in $moveCalls) { Assert-AegisV4 (-not $call.Target.Resize) 'KeepSize requested resizing.' }
        Assert-AegisV4 (-not (Test-AegisRectsOverlap $right $lower)) 'Independent targets unexpectedly overlap.'
    }
}
Invoke-AegisV4Case 'V73' 'KeepSize collision checks use target monitor identity instead of numeric coordinates alone' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules=@(@{Id='editor';ProcessName='editor';Tier=2;GroupId='work';SizeMode='Exact';Width=400;Height=400;Include=$true})
        foreach ($id in @('101','102')) {
            $f.State.Windows[$id].ProcessName='editor'
            $f.State.Windows[$id].Monitor=@{Id=$(if($id -eq '101'){'M1'}else{'M2'});Left=0;Top=0;Width=1000;Height=1000}
        }
        $f.State.TopologySignature='SyntheticIndependentMonitors:M1/M2';$f.State.ContextTopology=$f.State.TopologySignature
        $first=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($first.ExitCode -eq 0) 'Independent monitor fixture failed to arrange.'
        foreach ($id in @('101','102')) { $f.State.Windows[$id].Width=450;$f.State.Windows[$id].Height=450;$f.State.Windows[$id].Left+=37 }
        $f.State.Calls.Clear()
        $report=Invoke-AegisV4TestController $f Return -KeepSize
        Assert-AegisV4 ($report.ExitCode -eq 0 -and (Get-AegisV4Calls Move).Count -eq 2) 'Different monitor targets were treated as one collision domain.'
        Assert-AegisV4 (@($report.Items | Where-Object {$_.Reason -eq 'CurrentSizesOverlapWithinBatch'}).Count -eq 0) 'Numeric equality alone triggered a collision.'
    }
}
Invoke-AegisV4Case 'V74' 'Exact Unicode titles select the same rule at native and controller boundaries' {
    $composed='caf'+[char]0x00e9;$decomposed='cafe'+[char]0x0301
    $rules=@(ConvertTo-AegisRules @(@{Id='first';ProcessName='editor';Title=$composed;Tier=3},@{Id='exact';ProcessName='editor';Title=$decomposed;Tier=1}))
    $window=New-AegisV4TestWindow;$window.Title=$decomposed
    $nativeRule=Get-AegisNativeMatchingRule $window $rules
    $role=Resolve-AegisRole $window $rules
    Assert-AegisV4 ($nativeRule.Id -eq 'exact' -and $role.RuleId -eq 'exact' -and $role.Tier -eq 1) 'Culturally equivalent titles changed the selected rule or tier.'
}
Invoke-AegisV4Case 'V75' 'Process and class selectors agree on ordinal case-insensitive matching' {
    $composed='caf'+[char]0x00e9;$decomposed='cafe'+[char]0x0301
    foreach ($field in @('ProcessName','ClassName')) {
        $first=@{Id='first';ProcessName='editor';ClassName='FixtureWindow';Tier=3}
        $exact=@{Id='exact';ProcessName='editor';ClassName='FixtureWindow';Tier=1}
        $first[$field]=$composed;$exact[$field]=$decomposed
        $rules=@(ConvertTo-AegisRules @($first,$exact))
        $window=New-AegisV4TestWindow;$window[$field]=$decomposed
        $nativeRule=Get-AegisNativeMatchingRule $window $rules;$role=Resolve-AegisRole $window $rules
        Assert-AegisV4 ($nativeRule.Id -eq 'exact' -and $role.RuleId -eq 'exact' -and $role.Tier -eq 1) ('Unicode '+$field+' selection differs across boundaries.')
    }
    $rules=@(ConvertTo-AegisRules @(@{Id='ascii';ProcessName='editor';ClassName='FixtureWindow'}))
    $window=New-AegisV4TestWindow;$window.ProcessName='EDITOR';$window.ClassName='fixturewindow'
    Assert-AegisV4 ((Get-AegisNativeMatchingRule $window $rules).Id -eq 'ascii' -and (Resolve-AegisRole $window $rules).RuleId -eq 'ascii') 'ASCII case-insensitive selection regressed.'
}
Invoke-AegisV4Case 'V76' 'Full window identity retains ordinal class equality independently of rule matching' {
    $original=Get-AegisIdentity (New-AegisV4TestWindow)
    $original.ClassName='caf'+[char]0x00e9
    $different=Copy-AegisData $original;$different.ClassName='cafe'+[char]0x0301
    Assert-AegisV4 (-not (Test-AegisIdentityEqual $original $different)) 'Culturally equivalent class names matched distinct identities.'
    $different=Copy-AegisData $original;$different.ClassName=$original.ClassName.ToUpperInvariant()
    Assert-AegisV4 (-not (Test-AegisIdentityEqual $original $different)) 'Case-changed class matched full identity.'
    Assert-AegisV4 (Test-AegisIdentityEqual $original (Copy-AegisData $original)) 'Identical ordinal identity was rejected.'
}
Invoke-AegisV4Case 'V77' 'A Unicode case-fold equivalent is rejected as a rule Id before inventory or mutation' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules[0].Id=[string][char]0x212a
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($report.Status -eq 'Aborted' -and $report.Detail -like 'Rule Id must be unique*') 'Non-ASCII rule Id was not rejected by configuration validation.'
        Assert-AegisV4 ($f.State.InventoryCalls -eq 0 -and $f.State.Calls.Count -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Invalid rule Id reached inventory, backend, or profile publication.'
    }
}
Invoke-AegisV4Case 'V78' 'A Unicode case-fold equivalent is rejected as a GroupId before inventory or mutation' {
    Invoke-AegisV4Fixture {param($f)
        $f.Rules[0].GroupId=[string][char]0x212a
        $report=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($report.Status -eq 'Aborted' -and $report.Detail -eq 'Invalid GroupId.') 'Non-ASCII GroupId was not rejected by configuration validation.'
        Assert-AegisV4 ($f.State.InventoryCalls -eq 0 -and $f.State.Calls.Count -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Invalid GroupId reached inventory, backend, or profile publication.'
    }
}
Invoke-AegisV4Case 'V79' 'Rule Id and GroupId reject a trailing LF at configuration ingestion' {
    foreach ($field in @('Id','GroupId')) {
        Invoke-AegisV4Fixture {param($f)
            $f.Rules[0][$field]=[string]$f.Rules[0][$field]+"`n"
            $report=Invoke-AegisV4TestController $f Arrange
            $expectedReason='Invalid GroupId.'
            if ($field -eq 'Id') { $expectedReason='Rule Id must be unique and use 1-64 ASCII letters, digits, dot, underscore or hyphen.' }
            Assert-AegisV4 ($report.Status -eq 'Aborted' -and $report.Detail -eq $expectedReason) ('Trailing LF survived '+$field+' configuration validation.')
            Assert-AegisV4 ($f.State.InventoryCalls -eq 0 -and $f.State.Calls.Count -eq 0 -and $null -eq $global:AegisLayoutProfile) 'Trailing LF in an identifier reached inventory, backend, or profile publication.'
        }
    }
}
Invoke-AegisV4Case 'V80' 'Valid ASCII identifiers retain exact case and punctuation at the 1 and 64 character boundaries' {
    foreach ($identifier in @('Z',('Ab09._-'+('x'*57)))) {
        Invoke-AegisV4Fixture {param($f)
            $f.Rules=@(@{Id=$identifier;ProcessName='editor';Tier=2;GroupId=$identifier;SizeMode='Exact';Width=500;Height=340;Include=$true})
            $report=Invoke-AegisV4TestController $f Arrange
            Assert-AegisV4 ($report.ExitCode -eq 0 -and $global:AegisLayoutProfile.Slots.Count -eq 1) 'Valid boundary-length ASCII identifier was rejected.'
            $slot=$global:AegisLayoutProfile.Slots[0]
            Assert-AegisV4 ([string]::Equals($slot.RuleId,$identifier,[StringComparison]::Ordinal) -and [string]::Equals($slot.GroupId,$identifier,[StringComparison]::Ordinal)) 'Valid identifier case or punctuation was changed.'
            Assert-AegisV4 ([string]::Equals($slot.SlotId,($identifier+':001'),[StringComparison]::Ordinal)) 'Valid boundary identifier did not create its expected saved SlotId.'
            Test-AegisProfile $global:AegisLayoutProfile
        }
    }
}
Invoke-AegisV4Case 'V81' 'A saved SlotId with trailing LF is rejected before the corrupted profile can be used' {
    Invoke-AegisV4Fixture {param($f)
        $initial=Invoke-AegisV4TestController $f Arrange
        Assert-AegisV4 ($initial.ExitCode -eq 0) 'Valid profile fixture failed.'
        $original=$global:AegisLayoutProfile
        $corrupted=Copy-AegisData $original
        $corrupted.Slots[0].SlotId+="`n"
        $rejected=$false;$reason=''
        try { Test-AegisProfile $corrupted } catch { $rejected=$true;$reason=$_.Exception.Message }
        Assert-AegisV4 ($rejected -and $reason -eq 'Invalid or duplicate slot identity.') 'Trailing LF was accepted in a saved SlotId.'
        Assert-AegisV4 ([object]::ReferenceEquals($original,$global:AegisLayoutProfile) -and $original.Slots[0].SlotId.IndexOf([char]10) -lt 0) 'Validation changed the active profile while rejecting its corrupted copy.'
    }
}

Invoke-AegisV4Case 'V82' 'Reports use the declared product version' {
    Assert-AegisV4 ((Get-AegisVersion) -ceq '4.1.0-ps2') 'Unexpected declared product version.'
    foreach ($actionName in @('Inspect','Arrange','Return','Reflow','Undo','SaveProfile','LoadProfile')) {
        $versionReport=New-AegisReport $actionName $false
        Assert-AegisV4 ($versionReport.Version -ceq (Get-AegisVersion)) 'Report version differs from the product declaration.'
    }
}
