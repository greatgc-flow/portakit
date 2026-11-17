# Home geometry is separate from the current native window and one-batch Undo.
function New-AegisProfile {
    param([object[]]$Rules,[hashtable]$Options,[string]$TopologySignature,[int]$Revision=1)
    return @{SchemaVersion=4;Revision=$Revision;CreatedUtc=[DateTime]::UtcNow.ToString('o');TopologySignature=$TopologySignature;PolicyFingerprint=(Get-AegisPolicyFingerprint $Rules $Options);Rules=(Copy-AegisData $Rules);Options=(Copy-AegisData $Options);Slots=@();Zones=@()}
}

function Test-AegisRectsOverlap {
    param($A,$B)
    return ([long]$A.Left -lt ([long]$B.Left+$B.Width) -and [long]$B.Left -lt ([long]$A.Left+$A.Width) -and [long]$A.Top -lt ([long]$B.Top+$B.Height) -and [long]$B.Top -lt ([long]$A.Top+$A.Height))
}

function Assert-AegisProfileRectangle {
    param($Rectangle,[string]$Name)
    if ($Rectangle -isnot [hashtable]) { throw ($Name+' must be a rectangle hashtable.') }
    foreach ($key in @('Left','Top','Width','Height')) {
        $minimum=[int]::MinValue
        if ($key -eq 'Width' -or $key -eq 'Height') { $minimum=1 }
        if (-not (Test-AegisIntegerValue (Get-AegisValue $Rectangle $key $null) $minimum ([int]::MaxValue))) { throw ('Invalid '+$Name+'.'+$key+'.') }
    }
    if (([long]$Rectangle.Left+[long]$Rectangle.Width) -gt [int]::MaxValue -or ([long]$Rectangle.Top+[long]$Rectangle.Height) -gt [int]::MaxValue) { throw ($Name+' exceeds the coordinate range.') }
}

function Assert-AegisProfileText {
    param($Value,[string]$Name,[int]$Maximum=256,[bool]$AllowEmpty=$false)
    if ($Value -isnot [string] -or $Value.Length -gt $Maximum -or (-not $AllowEmpty -and [string]::IsNullOrEmpty($Value))) { throw ('Invalid '+$Name+'.') }
}

function Test-AegisProfile {
    param([Alias('Profile')]$LayoutProfile)
    if ($LayoutProfile -isnot [hashtable] -or -not (Test-AegisIntegerValue (Get-AegisValue $LayoutProfile 'SchemaVersion' $null) 4 4)) { throw 'Invalid profile schema.' }
    foreach ($key in $LayoutProfile.Keys) {
        if (@('SchemaVersion','Revision','CreatedUtc','TopologySignature','PolicyFingerprint','Rules','Options','Slots','Zones') -notcontains $key) { throw ('Unknown profile field: '+$key) }
    }
    if (-not (Test-AegisIntegerValue (Get-AegisValue $LayoutProfile 'Revision' $null) 1 2147483647)) { throw 'Invalid profile revision.' }
    Assert-AegisProfileText (Get-AegisValue $LayoutProfile 'CreatedUtc' $null) 'profile creation time' 64
    [DateTime]$created=[DateTime]::MinValue
    if (-not [DateTime]::TryParse($LayoutProfile.CreatedUtc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind,[ref]$created)) { throw 'Invalid profile creation time.' }
    Assert-AegisProfileText (Get-AegisValue $LayoutProfile 'TopologySignature' $null) 'profile topology' 16384
    Assert-AegisProfileText (Get-AegisValue $LayoutProfile 'PolicyFingerprint' $null) 'profile policy checksum' 64
    if ($LayoutProfile.PolicyFingerprint -cnotmatch '^[0-9a-f]{64}$') { throw 'Invalid profile policy checksum.' }
    if ($LayoutProfile.Options -isnot [hashtable]) { throw 'Invalid profile options.' }
    if ($null -eq $LayoutProfile.Rules -or ($LayoutProfile.Rules -isnot [array] -and $LayoutProfile.Rules -isnot [System.Collections.ArrayList])) { throw 'Profile rules must be an array.' }
    $rules=@(ConvertTo-AegisRules $LayoutProfile.Rules); $options=New-AegisOptions $LayoutProfile.Options
    if ((Get-AegisPolicyFingerprint $rules $options) -cne $LayoutProfile.PolicyFingerprint) { throw 'Profile policy checksum mismatch.' }
    foreach ($collectionKey in @('Slots','Zones')) {
        # Access through the dictionary preserves a one-element array's shape.
        if (-not $LayoutProfile.ContainsKey($collectionKey) -or $null -eq $LayoutProfile[$collectionKey] -or ($LayoutProfile[$collectionKey] -isnot [array] -and $LayoutProfile[$collectionKey] -isnot [System.Collections.ArrayList])) { throw ('Profile '+$collectionKey+' must be an array.') }
    }
    $slots=@($LayoutProfile.Slots); $zones=@($LayoutProfile.Zones)
    if ($slots.Count -gt 128 -or $zones.Count -gt 512) { throw 'Profile exceeds bounded capacity.' }
    if ($slots.Count -eq 0 -and $zones.Count -gt 0) { throw 'Empty profile cannot contain unbound monitor zones.' }
    $byRule=@{}; $allowedGroups=@{}; $allowedTiers=@{}
    foreach ($rule in $rules) {
        $byRule[$rule.Id]=$rule
        if ($rule.Include) { $allowedGroups[([string]$rule.Tier+'/'+$rule.GroupId)]=$true; $allowedTiers[[string]$rule.Tier]=$true }
    }
    $ids=@{}; $identityKeys=@{}; $monitors=@{}
    foreach ($slot in $slots) {
        if ($slot -isnot [hashtable]) { throw 'Saved slot must be a hashtable.' }
        foreach ($key in $slot.Keys) {
            if (@('SlotId','RuleId','Order','Identity','Monitor','HomeRect','ZoneRect','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','HomeConfirmed') -notcontains $key) { throw ('Unknown saved slot field: '+$key) }
        }
        Assert-AegisProfileText (Get-AegisValue $slot 'SlotId' $null) 'slot identity' 68
        if ($slot.SlotId -cnotmatch '\A[A-Za-z0-9_.-]{1,64}:[0-9]{3}\z' -or $ids.ContainsKey($slot.SlotId)) { throw 'Invalid or duplicate slot identity.' }
        $ids[$slot.SlotId]=$true
        Assert-AegisProfileText (Get-AegisValue $slot 'RuleId' $null) 'slot rule identity' 64
        if (-not $byRule.ContainsKey($slot.RuleId) -or -not $byRule[$slot.RuleId].Include) { throw 'Slot references an unknown or excluded rule.' }
        $rule=$byRule[$slot.RuleId]
        if (-not $slot.SlotId.StartsWith(($rule.Id+':'),[StringComparison]::Ordinal) -or $slot.RuleId -cne $rule.Id) { throw 'Slot identity does not correspond to its rule.' }
        if (-not (Test-AegisIntegerValue (Get-AegisValue $slot 'Order' $null) 0 1000000)) { throw 'Invalid slot order.' }
        foreach ($key in @('Tier','Priority','GroupPriority','GroupWeight','Width','Height')) {
            $minimum=0; $maximum=16384
            if ($key -eq 'Tier') { $minimum=1; $maximum=3 }
            elseif ($key -eq 'Priority' -or $key -eq 'GroupPriority') { $minimum=-1000000; $maximum=1000000 }
            elseif ($key -eq 'GroupWeight') { $minimum=1; $maximum=1000000 }
            if (-not (Test-AegisIntegerValue (Get-AegisValue $slot $key $null) $minimum $maximum) -or [int]$slot[$key] -ne [int]$rule[$key]) { throw ('Saved slot '+$key+' differs from its rule.') }
        }
        foreach ($key in @('GroupId','SizeMode')) {
            Assert-AegisProfileText (Get-AegisValue $slot $key $null) ('slot '+$key) 64
            if ($slot[$key] -cne $rule[$key]) { throw ('Saved slot '+$key+' differs from its rule.') }
        }
        if ($slot.ContainsKey('HomeConfirmed') -and $slot.HomeConfirmed -isnot [bool]) { throw 'HomeConfirmed must be Boolean.' }
        Assert-AegisProfileRectangle $slot.HomeRect 'slot home rectangle'
        Assert-AegisProfileRectangle $slot.ZoneRect 'slot group rectangle'
        Assert-AegisProfileRectangle $slot.Monitor 'slot monitor rectangle'
        Assert-AegisProfileText (Get-AegisValue $slot.Monitor 'Id' $null) 'monitor identity' 128
        foreach ($key in $slot.Monitor.Keys) { if (@('Id','Left','Top','Width','Height') -notcontains $key) { throw ('Unknown monitor field: '+$key) } }
        foreach ($rectangleKey in @('HomeRect','ZoneRect')) {
            foreach ($key in $slot[$rectangleKey].Keys) { if (@('Left','Top','Width','Height') -notcontains $key) { throw ('Unknown rectangle field: '+$key) } }
        }
        if (-not (Test-AegisRectInside $slot.HomeRect $slot.ZoneRect) -or -not (Test-AegisRectInside $slot.ZoneRect $slot.Monitor)) { throw 'Slot geometry is outside its group or monitor.' }
        if ($monitors.ContainsKey($slot.Monitor.Id)) {
            if (-not (Test-AegisRectMatch $monitors[$slot.Monitor.Id] $slot.Monitor 0)) { throw 'One monitor identity has inconsistent saved work areas.' }
        } else { $monitors[$slot.Monitor.Id]=$slot.Monitor }
        if ($slot.Identity -isnot [hashtable]) { throw 'Saved binding hint must be a hashtable.' }
        foreach ($key in $slot.Identity.Keys) { if (@('Id','ProcessId','ThreadId','ProcessStart','ClassName') -notcontains $key) { throw ('Unknown binding field: '+$key) } }
        foreach ($key in @('Id','ProcessId','ThreadId','ProcessStart','ClassName')) { Assert-AegisProfileText (Get-AegisValue $slot.Identity $key $null) ('saved binding '+$key) 256 }
        [long]$handleValue=0
        if (-not [long]::TryParse($slot.Identity.Id,[ref]$handleValue) -or $handleValue -eq 0) { throw 'Invalid saved window handle hint.' }
        foreach ($key in @('ProcessId','ThreadId')) {
            [uint32]$ownerValue=0
            if (-not [uint32]::TryParse($slot.Identity[$key],[ref]$ownerValue) -or $ownerValue -eq 0) { throw 'Invalid saved process or thread hint.' }
        }
        if ($slot.Identity.ProcessStart -notmatch '^[0-9A-Fa-f]{16}$') { throw 'Invalid saved process creation time.' }
        $identityKey=''
        foreach ($key in @('Id','ProcessId','ThreadId','ProcessStart','ClassName')) { $text=[string]$slot.Identity[$key]; $identityKey+=$text.Length.ToString()+':'+$text+';' }
        if ($identityKeys.ContainsKey($identityKey)) { throw 'Two saved slots reference the same window identity.' }
        $identityKeys[$identityKey]=$true
    }
    $tierZones=@{}; $groupZones=@{}
    foreach ($zone in $zones) {
        if ($zone -isnot [hashtable]) { throw 'Saved zone must be a hashtable.' }
        foreach ($key in $zone.Keys) { if (@('Level','Tier','GroupId','Left','Top','Width','Height','MonitorId') -notcontains $key) { throw ('Unknown zone field: '+$key) } }
        Assert-AegisProfileText (Get-AegisValue $zone 'Level' $null) 'zone level' 5
        if (@('Tier','Group') -notcontains $zone.Level -or -not (Test-AegisIntegerValue (Get-AegisValue $zone 'Tier' $null) 1 3)) { throw 'Invalid saved zone level or tier.' }
        Assert-AegisProfileRectangle $zone 'saved zone rectangle'
        Assert-AegisProfileText (Get-AegisValue $zone 'MonitorId' $null) 'zone monitor identity' 128
        if (-not $monitors.ContainsKey($zone.MonitorId) -or -not (Test-AegisRectInside $zone $monitors[$zone.MonitorId])) { throw 'Saved zone lies outside a known monitor work area.' }
        $tierKey=$zone.MonitorId+'/'+[string]$zone.Tier
        if ($zone.Level -eq 'Tier') {
            if (-not $allowedTiers.ContainsKey([string]$zone.Tier) -or $tierZones.ContainsKey($tierKey)) { throw 'Unknown or duplicate saved tier zone.' }
            if ($zone.ContainsKey('GroupId')) { Assert-AegisProfileText $zone.GroupId 'tier group marker' 0 $true }
            $tierZones[$tierKey]=$zone
        } else {
            Assert-AegisProfileText (Get-AegisValue $zone 'GroupId' $null) 'zone group identity' 64
            if ($zone.GroupId -cnotmatch '\A[A-Za-z0-9_.-]{1,64}\z' -or -not $allowedGroups.ContainsKey(([string]$zone.Tier+'/'+$zone.GroupId))) { throw 'Saved zone references an unknown group.' }
            $groupKey=$tierKey+'/'+$zone.GroupId
            if ($groupZones.ContainsKey($groupKey)) { throw 'Duplicate saved group zone.' }
            $groupZones[$groupKey]=$zone
        }
    }
    foreach ($zone in $zones) {
        if ($zone.Level -ne 'Group') { continue }
        $tierKey=$zone.MonitorId+'/'+[string]$zone.Tier
        if (-not $tierZones.ContainsKey($tierKey) -or -not (Test-AegisRectInside $zone $tierZones[$tierKey])) { throw 'Saved group lies outside its matching tier zone.' }
    }
    foreach ($slot in $slots) {
        $groupKey=$slot.Monitor.Id+'/'+[string]$slot.Tier+'/'+$slot.GroupId
        if (-not $groupZones.ContainsKey($groupKey) -or -not (Test-AegisRectMatch $slot.ZoneRect $groupZones[$groupKey] 0)) { throw 'Saved slot group rectangle does not match its group zone.' }
    }
    for ($i=0;$i -lt $slots.Count;$i++) {
        for ($j=$i+1;$j -lt $slots.Count;$j++) {
            if ($slots[$i].Monitor.Id -eq $slots[$j].Monitor.Id -and (Test-AegisRectsOverlap $slots[$i].HomeRect $slots[$j].HomeRect)) { throw 'Saved home rectangles overlap.' }
        }
    }
    for ($i=0;$i -lt $zones.Count;$i++) {
        for ($j=$i+1;$j -lt $zones.Count;$j++) {
            if ($zones[$i].MonitorId -ne $zones[$j].MonitorId -or $zones[$i].Level -ne $zones[$j].Level) { continue }
            if ($zones[$i].Level -eq 'Group' -and $zones[$i].Tier -ne $zones[$j].Tier) { continue }
            if (Test-AegisRectsOverlap $zones[$i] $zones[$j]) { throw 'Saved sibling zones overlap.' }
        }
    }
}

function Resolve-AegisBindings {
    param($layoutProfile,[object[]]$Windows,[object[]]$AllWindows)
    if ($null -eq $Windows) { $Windows=@() }; if ($null -eq $AllWindows) { $AllWindows=@() }
    $answer=@{ByWindow=@{};BySlot=@{};Unassigned=@();Ambiguous=@();Reserved=@();OldGone=@{}}
    if ($null -eq $layoutProfile) { $answer.Unassigned=$Windows; return $answer }
    $allById=@{}; foreach ($window in $AllWindows) { $allById[[string]$window.Id]=$window }
    $used=@{}; $openByRule=@{}
    foreach ($slot in $layoutProfile.Slots) {
        $matched=$null
        foreach ($window in $Windows) {
            if (-not $used.ContainsKey([string]$window.Id) -and $window.RuleId -eq $slot.RuleId -and (Test-AegisIdentityEqual (Get-AegisIdentity $window) $slot.Identity)) { $matched=$window; break }
        }
        if ($null -ne $matched) {
            $used[[string]$matched.Id]=$true; $answer.ByWindow[[string]$matched.Id]=$slot; $answer.BySlot[[string]$slot.SlotId]=$matched
            continue
        }
        $oldGone=$false
        if (-not $allById.ContainsKey([string]$slot.Identity.Id)) { $oldGone=$true }
        else {
            $observed=$allById[[string]$slot.Identity.Id]
            if ((Get-AegisValue $observed 'IdentityReady' $false) -and -not (Test-AegisIdentityEqual (Get-AegisIdentity $observed) $slot.Identity)) { $oldGone=$true }
        }
        $answer.OldGone[[string]$slot.SlotId]=$oldGone
        if (-not $openByRule.ContainsKey([string]$slot.RuleId)) { $openByRule[[string]$slot.RuleId]=New-Object System.Collections.ArrayList }
        [void]$openByRule[[string]$slot.RuleId].Add($slot)
    }
    $unmatchedByRule=@{}
    foreach ($window in $Windows) {
        if ($used.ContainsKey([string]$window.Id)) { continue }
        if (-not $unmatchedByRule.ContainsKey([string]$window.RuleId)) { $unmatchedByRule[[string]$window.RuleId]=New-Object System.Collections.ArrayList }
        [void]$unmatchedByRule[[string]$window.RuleId].Add($window)
    }
    $unassigned=New-Object System.Collections.ArrayList; $ambiguous=New-Object System.Collections.ArrayList
    foreach ($ruleId in $unmatchedByRule.Keys) {
        $newWindows=$unmatchedByRule[$ruleId]; $oldSlots=@(Get-AegisValue $openByRule $ruleId @())
        if ($newWindows.Count -eq 1 -and $oldSlots.Count -eq 1 -and $answer.OldGone[[string]$oldSlots[0].SlotId]) {
            $window=$newWindows[0]; $slot=$oldSlots[0]
            $answer.ByWindow[[string]$window.Id]=$slot; $answer.BySlot[[string]$slot.SlotId]=$window
        } elseif ($oldSlots.Count -gt 0) {
            foreach ($window in $newWindows) { [void]$ambiguous.Add($window) }
        } else { foreach ($window in $newWindows) { [void]$unassigned.Add($window) } }
    }
    $reserved=New-Object System.Collections.ArrayList
    foreach ($slot in $layoutProfile.Slots) { if (-not $answer.BySlot.ContainsKey([string]$slot.SlotId)) { [void]$reserved.Add($slot) } }
    $answer.Unassigned=$unassigned.ToArray(); $answer.Ambiguous=$ambiguous.ToArray(); $answer.Reserved=$reserved.ToArray()
    return $answer
}

function New-AegisSlot {
    param($Window,$Plan,[string]$SlotId,[int]$Order)
    return @{
        SlotId=$SlotId;RuleId=$Window.RuleId;Order=$Order;Identity=(Get-AegisIdentity $Window)
        Monitor=(Copy-AegisData $Window.Monitor);HomeRect=(Get-AegisRect $Plan);ZoneRect=(Get-AegisRect $Plan.ZoneRect)
        Tier=$Window.Tier;GroupId=$Window.GroupId;Priority=$Window.Priority
        GroupPriority=$Window.GroupPriority;GroupWeight=$Window.GroupWeight
        SizeMode=$Window.SizeMode;Width=$Window.DesiredWidth;Height=$Window.DesiredHeight;HomeConfirmed=$false
    }
}

function New-AegisReservedWindow {
    param($Slot)
    return @{
        Id=('reserved/'+$Slot.SlotId);SlotId=$Slot.SlotId;RuleId=$Slot.RuleId;Reserved=$true
        ProcessName='';Title='';Tier=$Slot.Tier;GroupId=$Slot.GroupId;Priority=$Slot.Priority
        GroupPriority=$Slot.GroupPriority;GroupWeight=$Slot.GroupWeight;LayoutOrder=$Slot.Order
        Width=$Slot.HomeRect.Width;Height=$Slot.HomeRect.Height;SizeMode='Exact'
        DesiredWidth=$Slot.HomeRect.Width;DesiredHeight=$Slot.HomeRect.Height;Resizable=$true;MinMaxReady=$true
        MinWidth=1;MinHeight=1;MaxWidth=0;MaxHeight=0;Monitor=(Copy-AegisData $Slot.Monitor)
        OriginalSlot=$Slot
    }
}

function Test-AegisScope {
    param($Object,[string[]]$RuleIds=@(),[int]$Tier=0,[string]$GroupId='')
    if ($null -ne $RuleIds -and $RuleIds.Count -gt 0 -and $RuleIds -notcontains [string]$Object.RuleId) { return $false }
    if ($Tier -ne 0 -and [int]$Object.Tier -ne $Tier) { return $false }
    if (-not [string]::IsNullOrEmpty($GroupId) -and [string]$Object.GroupId -ine $GroupId) { return $false }
    return $true
}

function Get-AegisUndoSelection {
    param($State)
    if ($null -eq $State) { return @{Status='NoSnapshot';Entries=@()} }
    if ($State -isnot [hashtable] -or (Get-AegisValue $State 'SchemaVersion' 0) -ne 4) { return @{Status='InvalidSnapshot';Entries=@()} }
    $entries=New-Object System.Collections.ArrayList
    foreach ($entry in @($State.Entries)) {
        if ($entry -isnot [hashtable] -or $entry.Window -isnot [hashtable]) { return @{Status='InvalidSnapshot';Entries=@()} }
        if ($entry.Confirmed -and -not $entry.Restored -and -not $entry.Unavailable) { [void]$entries.Add($entry) }
    }
    if ($entries.Count -eq 0) { return @{Status='NoSnapshot';Entries=@()} }
    return @{Status='Ready';Entries=$entries.ToArray()}
}
