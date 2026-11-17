#requires -version 2.0
<#
Aegis 4.1.0-ps2 | Interactive, allowlisted, geometry-only window arrangement.
Default Inspect is read-only. Edit Aegis.Processes.csv, then Arrange explicitly.
Arrange establishes homes once, then returns to them. Reflow changes the layout.
Hidden/minimized/maximized windows keep their display state. No Z-order changes.
Profiles and Undo are separate. SaveProfile/LoadProfile perform explicit data I/O.
Windows PowerShell 2.x source target; see release evidence for runtime limits.
#>
[CmdletBinding()]
param(
    [ValidateSet('Inspect','Arrange','Return','Reflow','Undo','SaveProfile','LoadProfile','SelfTest','Library')][string]$Action='Inspect',
    [hashtable]$Options=@{},[object[]]$Rules=@(),[string]$ConfigPath='',
    [string]$ProfilePath='',[string[]]$RuleIds=@(),
    [ValidateRange(0,3)][int]$Tier=0,[string]$GroupId='',
    [switch]$KeepSize,[switch]$ReleaseAbsent,[switch]$Preview,
    [switch]$PassThru,[switch]$ExitWithCode
)

function Get-AegisVersion { return '4.1.0-ps2' }

# Operational policy. Data-only configuration, Windows PowerShell 2.0 syntax.
function Get-AegisValue {
    param($Object, [string]$Name, $Default=$null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
    } else {
        $property=$Object.PSObject.Properties[$Name]
        if ($null -ne $property) { return $property.Value }
    }
    return $Default
}

function Test-AegisIntegerValue {
    param($Value, [double]$Minimum=-2147483648, [double]$Maximum=2147483647)
    if ($null -eq $Value -or $Value -is [bool]) { return $false }
    if ($Value -is [string] -and [string]::IsNullOrEmpty($Value.Trim())) { return $false }
    try { $n=[double]$Value } catch { return $false }
    return (-not [double]::IsNaN($n) -and -not [double]::IsInfinity($n) -and $n -eq [Math]::Floor($n) -and $n -ge $Minimum -and $n -le $Maximum)
}

function Copy-AegisData {
    param($Value)
    if ($Value -is [System.Collections.IDictionary]) {
        $copy=@{}
        foreach ($key in $Value.Keys) { $copy[$key]=Copy-AegisData $Value[$key] }
        return $copy
    }
    if ($Value -is [array] -or $Value -is [System.Collections.ArrayList]) {
        $copy=New-Object System.Collections.ArrayList
        foreach ($element in $Value) { [void]$copy.Add((Copy-AegisData $element)) }
        return ,$copy.ToArray()
    }
    return $Value
}

function New-AegisOptions {
    param([hashtable]$Overrides=@{})
    if ($null -eq $Overrides) { $Overrides=@{} }
    $o=@{
        Mode='Grid'; MonitorScope='EachMonitor'; Margin=8; Gap=8
        Weights=@{3=50;2=32;1=18}
        QueryTimeoutMs=50; MoveTimeoutMs=800; PollMs=80; TotalTimeoutMs=10000
        PlanningTimeoutMs=1500; Tolerance=2; MaxWindows=64; MaxEnumeratedWindows=2048
        MaxCandidates=12; MaxObservations=256; MaxMutations=64
    }
    foreach ($key in $Overrides.Keys) {
        if (-not $o.ContainsKey($key)) { throw ('Unknown option: '+$key) }
        $o[$key]=$Overrides[$key]
    }
    if ($o.Mode -ne 'Grid') { throw 'Operational v4 supports nonoverlapping Grid only.' }
    if (@('EachMonitor','CurrentMonitor') -notcontains $o.MonitorScope) { throw 'Invalid MonitorScope.' }
    $ranges=@{
        Margin=@(0,128);Gap=@(0,128)
        QueryTimeoutMs=@(1,250);MoveTimeoutMs=@(1,10000);PollMs=@(20,1000)
        TotalTimeoutMs=@(100,60000);PlanningTimeoutMs=@(10,10000);Tolerance=@(0,8)
        MaxWindows=@(1,128);MaxEnumeratedWindows=@(1,8192);MaxCandidates=@(1,32)
        MaxObservations=@(1,2048);MaxMutations=@(1,128)
    }
    foreach ($key in $ranges.Keys) {
        if (-not (Test-AegisIntegerValue $o[$key] $ranges[$key][0] $ranges[$key][1])) { throw ('Invalid option: '+$key) }
        $o[$key]=[int][double]$o[$key]
    }
    if ($o.Weights -isnot [hashtable]) { throw 'Weights must be a hashtable.' }
    $weights=@{}
    foreach ($tier in @(3,2,1)) {
        $value=Get-AegisValue $o.Weights ([string]$tier) $null
        if ($o.Weights.ContainsKey($tier)) { $value=$o.Weights[$tier] }
        if (-not (Test-AegisIntegerValue $value 1 1000000)) { throw 'All three tier weights are required.' }
        $weights[$tier]=[int][double]$value
    }
    $o.Weights=$weights
    return $o
}

function ConvertTo-AegisRules {
    param([object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    if ($Rules.Count -gt 128) { throw 'At most 128 process rules are supported.' }
    $answer=New-Object System.Collections.ArrayList
    $ids=@{}; $groups=@{}
    foreach ($inputRule in $Rules) {
        if ($inputRule -isnot [hashtable]) { throw 'Each rule must be a hashtable.' }
        $r=@{Id='';ProcessName='';ClassName='';Title='';Tier=2;GroupId='default';Priority=0;GroupPriority=0;GroupWeight=100;SizeMode='Preserve';Width=0;Height=0;Include=$true}
        foreach ($key in $inputRule.Keys) {
            if (-not $r.ContainsKey($key)) { throw ('Unknown rule field: '+$key) }
            $r[$key]=$inputRule[$key]
        }
        foreach ($key in @('Id','ProcessName','ClassName','Title','GroupId','SizeMode')) {
            if ($r[$key] -isnot [string]) { throw ('Rule field requires text: '+$key) }
        }
        if ($r.Id -cnotmatch '\A[A-Za-z0-9_.-]{1,64}\z' -or $ids.ContainsKey($r.Id)) { throw 'Rule Id must be unique and use 1-64 ASCII letters, digits, dot, underscore or hyphen.' }
        $ids[$r.Id]=$true
        $r.ProcessName=$r.ProcessName.Trim()
        if ($r.ProcessName.EndsWith('.exe',[StringComparison]::OrdinalIgnoreCase)) { $r.ProcessName=$r.ProcessName.Substring(0,$r.ProcessName.Length-4) }
        if ([string]::IsNullOrEmpty($r.ProcessName) -or $r.ProcessName.Length -gt 128 -or $r.ProcessName -match '[\\/:*?\[\]]') { throw ('ProcessName must be an exact executable name without a path: '+$r.Id) }
        if ($r.GroupId -cnotmatch '\A[A-Za-z0-9_.-]{1,64}\z') { throw 'Invalid GroupId.' }
        if ($r.ClassName.Length -gt 256 -or $r.Title.Length -gt 512) { throw 'ClassName or Title is too long.' }
        foreach ($key in @('Tier','Priority','GroupPriority','GroupWeight','Width','Height')) {
            $minimum=0; $maximum=16384
            if ($key -eq 'Tier') { $minimum=1; $maximum=3 }
            elseif ($key -eq 'Priority' -or $key -eq 'GroupPriority') { $minimum=-1000000; $maximum=1000000 }
            elseif ($key -eq 'GroupWeight') { $minimum=1; $maximum=1000000 }
            if (-not (Test-AegisIntegerValue $r[$key] $minimum $maximum)) { throw ('Invalid '+$key+' in rule '+$r.Id) }
            $r[$key]=[int][double]$r[$key]
        }
        if ($r.Include -isnot [bool]) { throw 'Rule Include must be Boolean.' }
        if (@('Preserve','Exact','Preferred','Fill') -notcontains $r.SizeMode) { throw 'SizeMode must be Preserve, Exact, Preferred, or Fill.' }
        if (@('Exact','Preferred') -contains $r.SizeMode) {
            if ($r.Width -lt 1 -or $r.Height -lt 1) { throw 'Exact and Preferred require both Width and Height.' }
        } elseif ($r.Width -ne 0 -or $r.Height -ne 0) { throw 'Width and Height apply only to Exact or Preferred.' }
        $groupKey=([string]$r.Tier)+'/'+$r.GroupId
        if ($r.Include) {
            if ($groups.ContainsKey($groupKey)) {
                if ($groups[$groupKey].Priority -ne $r.GroupPriority -or $groups[$groupKey].Weight -ne $r.GroupWeight) { throw ('Rules in one tier/group must agree on GroupPriority and GroupWeight: '+$groupKey) }
            } else { $groups[$groupKey]=@{Priority=$r.GroupPriority;Weight=$r.GroupWeight} }
        }
        [void]$answer.Add($r)
    }
    return $answer.ToArray()
}

function Test-AegisRules { param([object[]]$Rules=@()) [void]@(ConvertTo-AegisRules $Rules) }

function Resolve-AegisRole {
    param([hashtable]$Window,[object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    foreach ($rule in $Rules) {
        # Match the native selector exactly. Culture-aware PowerShell comparison
        # can equate distinct Unicode sequences and choose a different tier/rule.
        if (-not [string]::Equals([string]$Window.ProcessName,[string]$rule.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        if (-not [string]::IsNullOrEmpty([string]$rule.ClassName) -and -not [string]::Equals([string]$Window.ClassName,[string]$rule.ClassName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        if (-not [string]::IsNullOrEmpty([string]$rule.Title) -and -not [string]::Equals([string]$Window.Title,[string]$rule.Title,[StringComparison]::Ordinal)) { continue }
        return @{Tier=$rule.Tier;RuleId=$rule.Id;Reason='ExplicitRule';IncludeOverride=$rule.Include;Rule=$rule}
    }
    return @{Tier=0;RuleId='';Reason='NotAllowlisted';IncludeOverride=$false;Rule=$null}
}

function Get-AegisEligibility {
    param([hashtable]$Window,[hashtable]$Options)
    $reason=''
    if (-not (Get-AegisValue $Window 'Exists' $false)) { $reason='MissingWindow' }
    elseif (-not (Get-AegisValue $Window 'Visible' $false)) { $reason='HiddenWindow' }
    elseif (Get-AegisValue $Window 'Minimized' $false) { $reason='MinimizedPreserved' }
    elseif (Get-AegisValue $Window 'Maximized' $false) { $reason='MaximizedPreserved' }
    elseif (Get-AegisValue $Window 'Cloaked' $false) { $reason='CloakedWindow' }
    elseif (Get-AegisValue $Window 'Hung' $false) { $reason='UnresponsiveWindow' }
    elseif (Get-AegisValue $Window 'IsSelf' $false) { $reason='OwnHostWindow' }
    elseif (-not (Get-AegisValue $Window 'Enabled' $false)) { $reason='DisabledWindow' }
    elseif (@('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd','tooltips_class32','#32768','SysShadow') -contains [string]$Window.ClassName) { $reason='SystemWindowClass' }
    elseif (-not (Get-AegisValue $Window 'IncludeOverride' $false)) { $reason='NotAllowlisted' }
    elseif (-not (Get-AegisValue $Window 'IdentityReady' $false)) { $reason='IdentityUnavailable' }
    elseif (-not (Get-AegisValue $Window 'SnapshotReady' $false)) { $reason='SnapshotUnavailable' }
    if ($reason -ne '') { return @{Eligible=$false;Reason=$reason} }
    return @{Eligible=$true;Reason='ExplicitIncludeRule'}
}

function Test-AegisRectMatch {
    param($Actual,$Target,[int]$Tolerance=2,[bool]$CheckSize=$true)
    if ($null -eq $Actual -or $null -eq $Target -or $Tolerance -lt 0 -or $Tolerance -gt 8) { return $false }
    $keys=@('Left','Top'); if ($CheckSize) { $keys+=@('Width','Height') }
    foreach ($key in $keys) {
        $a=Get-AegisValue $Actual $key $null; $b=Get-AegisValue $Target $key $null
        if (-not (Test-AegisIntegerValue $a) -or -not (Test-AegisIntegerValue $b)) { return $false }
        if (($key -eq 'Width' -or $key -eq 'Height') -and ($a -lt 1 -or $b -lt 1)) { return $false }
        if ([Math]::Abs([double]$a-[double]$b) -gt $Tolerance) { return $false }
    }
    return $true
}

function Get-AegisRect {
    param($Object)
    $r=@{}
    foreach ($key in @('Left','Top','Width','Height')) { $r[$key]=[int](Get-AegisValue $Object $key 0) }
    return $r
}

function Test-AegisRectInside {
    param($Rect,$Area)
    if (-not (Test-AegisRectMatch $Rect $Rect 0) -or -not (Test-AegisRectMatch $Area $Area 0)) { return $false }
    return ([long]$Rect.Left -ge [long]$Area.Left -and [long]$Rect.Top -ge [long]$Area.Top -and ([long]$Rect.Left+$Rect.Width) -le ([long]$Area.Left+$Area.Width) -and ([long]$Rect.Top+$Rect.Height) -le ([long]$Area.Top+$Area.Height))
}

function Get-AegisIdentity {
    param($Window)
    $r=@{}
    foreach ($key in @('Id','ProcessId','ThreadId','ProcessStart','ClassName')) { $r[$key]=[string](Get-AegisValue $Window $key '') }
    return $r
}

function Test-AegisIdentityEqual {
    param($First,$Second)
    if ($null -eq $First -or $null -eq $Second) { return $false }
    foreach ($key in @('Id','ProcessId','ThreadId','ProcessStart','ClassName')) {
        $a=[string](Get-AegisValue $First $key ''); $b=[string](Get-AegisValue $Second $key '')
        if ([string]::IsNullOrEmpty($a) -or -not [string]::Equals($a,$b,[StringComparison]::Ordinal)) { return $false }
    }
    return $true
}

function Get-AegisPolicyFingerprint {
    param([object[]]$Rules,[hashtable]$Options)
    $builder=New-Object System.Text.StringBuilder
    foreach ($rule in $Rules) {
        foreach ($key in @('Id','ProcessName','ClassName','Title','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','Include')) {
            $s=[string]$rule[$key]; [void]$builder.Append($key+':'+$s.Length+':'+$s+';')
        }
    }
    foreach ($key in @('MonitorScope','Margin','Gap')) { [void]$builder.Append($key+':'+[string]$Options[$key]+';') }
    foreach ($tier in @(3,2,1)) { [void]$builder.Append('Tier'+$tier+':'+$Options.Weights[$tier]+';') }
    $hash=[System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($builder.ToString())))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Clear() }
}

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

# Bounded, side-effect-free layout planning. Windows PowerShell 2.0 / .NET 2.
# Outer-window pixel coordinates in the caller's DPI context.
# Horizontal tiers, vertical groups, nonoverlapping grids; greedy, not optimal packing.

function Get-AegisLayoutValue {
    param($Object, [string]$Name, $Default)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
    } else {
        $property=$Object.PSObject.Properties[$Name]
        if ($null -ne $property) { return $property.Value }
    }
    return $Default
}

function ConvertTo-AegisLayoutInteger {
    param($Value, [string]$Name, [int]$Minimum, [int]$Maximum)
    [int]$number=0
    if ($null -eq $Value -or $Value -is [bool] -or -not [int]::TryParse([string]$Value,[ref]$number)) { throw ('InvalidInteger: '+$Name) }
    if ($number -lt $Minimum -or $number -gt $Maximum) { throw ('OutOfRange: '+$Name) }
    return $number
}

function New-AegisLayoutItem {
    param($Entry, [string]$Status, [string]$Reason, $Rectangle, [bool]$Resize, $Zone)
    $left=0; $top=0; $width=0; $height=0
    if ($null -ne $Rectangle) {
        $left=[int]$Rectangle.Left; $top=[int]$Rectangle.Top
        $width=[int]$Rectangle.Width; $height=[int]$Rectangle.Height
    }
    return @{
        Id=$Entry.Id; Window=$Entry.Window; Tier=$Entry.Tier; GroupId=$Entry.GroupId
        Priority=$Entry.Priority; Status=$Status; Reason=$Reason; Left=$left; Top=$top
        Width=$width; Height=$height; Resize=$Resize; Mode='Grid'; ZoneRect=$Zone
        Adjustment=[string]$Entry.Adjustment; Reserved=[bool]$Entry.Reserved
    }
}

function Get-AegisWeightedTracks {
    param($Tracks, [int]$Length, [int]$Gap)
    [long]$used=[long]$Gap*[Math]::Max(0,$Tracks.Count-1); [long]$weightSum=0
    foreach ($track in $Tracks) { $used+=[int]$track.Minimum; $weightSum+=[int]$track.Weight }
    if ($Tracks.Count -eq 0 -or $used -gt $Length -or $weightSum -le 0) { throw 'InvalidTrackBudget' }
    [long]$extra=[long]$Length-$used; [long]$assigned=0
    [int[]]$sizes=New-Object 'int[]' $Tracks.Count
    for ($i=0; $i -lt $Tracks.Count; $i++) {
        $sizes[$i]=[int]([int]$Tracks[$i].Minimum+[Math]::Floor($extra*([double]$Tracks[$i].Weight/$weightSum)))
        $assigned+=$sizes[$i]
    }
    [int]$remainder=[long]$Length-([long]$Gap*($Tracks.Count-1))-$assigned
    for ($i=0; $i -lt $remainder; $i++) { $sizes[$i]++ }
    return @{Values=$sizes}
}

function Get-AegisGridColumns {
    param($Entries, $Zone, [int]$Gap, [int]$Limit)
    [int]$minimum=[int]::MaxValue
    foreach ($entry in $Entries) { $minimum=[Math]::Min($minimum,$entry.RequiredWidth) }
    [int]$maximum=[Math]::Min($Entries.Count,[Math]::Floor(([long]$Zone.Width+$Gap)/[double]([long]$minimum+$Gap)))
    $maximum=[Math]::Max(1,$maximum)
    $values=New-Object System.Collections.ArrayList; $seen=@{}
    $suggestions=New-Object System.Collections.ArrayList; [void]$suggestions.Add(1)
    if ($maximum -le $Limit) {
        for ($i=2; $i -le $maximum; $i++) { [void]$suggestions.Add($i) }
    } else {
        [void]$suggestions.Add($maximum)
        [int]$ideal=[Math]::Max(1,[Math]::Min($maximum,[Math]::Round([Math]::Sqrt($Entries.Count*([double]$Zone.Width/$Zone.Height)))))
        foreach ($delta in @(0,-1,1,-2,2)) { [void]$suggestions.Add([Math]::Max(1,[Math]::Min($maximum,$ideal+$delta))) }
        for ($i=1; $i -le $Limit; $i++) { [void]$suggestions.Add([Math]::Max(1,[Math]::Min($maximum,1+[Math]::Floor(($maximum-1)*($i/[double]$Limit))))) }
    }
    foreach ($column in $suggestions) {
        if (-not $seen.ContainsKey([int]$column)) { $seen[[int]$column]=$true; [void]$values.Add([int]$column) }
        if ($values.Count -ge $Limit) { break }
    }
    return @{Values=@($values.ToArray() | Sort-Object)}
}

function New-AegisGridSummary {
    param($Entries, $Zone, [int]$Gap, [int]$Columns, $Timer, [int]$TimeoutMs)
    [int[]]$columnMinimums=New-Object 'int[]' $Columns
    [int[]]$rowMinimums=New-Object 'int[]' $Entries.Count
    [int[]]$accepted=New-Object 'int[]' $Entries.Count
    [int[]]$priorityCounts=New-Object 'int[]' $Entries.Count
    [bool[]]$bits=New-Object 'bool[]' $Entries.Count
    [long]$widthSum=0; [long]$heightSum=0; [int]$count=0; [int]$usedColumns=0; [int]$rows=0
    for ($i=0; $i -lt $Entries.Count; $i++) {
        if (($i%16) -eq 0 -and $Timer.ElapsedMilliseconds -ge $TimeoutMs) { return @{Expired=$true} }
        $entry=$Entries[$i]
        [int]$row=[Math]::Floor($count/[double]$Columns); [int]$column=$count%$Columns
        [int]$newWidth=[Math]::Max($columnMinimums[$column],$entry.RequiredWidth)
        [int]$newHeight=[Math]::Max($rowMinimums[$row],$entry.RequiredHeight)
        [int]$nextColumns=[Math]::Min($Columns,$count+1)
        [long]$nextWidth=$widthSum+$newWidth-$columnMinimums[$column]
        [long]$nextHeight=$heightSum+$newHeight-$rowMinimums[$row]
        if (($nextWidth+[long]$Gap*($nextColumns-1)) -gt $Zone.Width -or ($nextHeight+[long]$Gap*$row) -gt $Zone.Height) { continue }
        $columnMinimums[$column]=$newWidth; $rowMinimums[$row]=$newHeight
        $widthSum=$nextWidth; $heightSum=$nextHeight; $usedColumns=$nextColumns; $rows=$row+1
        $accepted[$count]=$i; $count++; $bits[$i]=$true; $priorityCounts[$entry.PriorityIndex]++
    }
    [double]$cost=[double]::MaxValue
    if ($count -gt 0) {
        [double]$averageWidth=($Zone.Width-$Gap*($usedColumns-1))/[double]$usedColumns
        [double]$averageHeight=($Zone.Height-$Gap*($rows-1))/[double]$rows
        $cost=[Math]::Abs([Math]::Log(($averageWidth/$averageHeight)/1.6))
    }
    return @{
        Expired=$false; Columns=$Columns; UsedColumns=$usedColumns; Rows=$rows
        Count=$count; Accepted=$accepted; Bits=$bits; PriorityCounts=$priorityCounts
        ColumnMinimums=$columnMinimums; RowMinimums=$rowMinimums; Cost=$cost
    }
}

function Test-AegisGridBetter {
    param($Candidate, $Best, [int]$PriorityCount, [int]$EntryCount)
    if ($null -eq $Best) { return $true }
    # Lexicographic admitted counts by business priority; then stable identity order.
    for ($i=0; $i -lt $PriorityCount; $i++) {
        if ($Candidate.PriorityCounts[$i] -gt $Best.PriorityCounts[$i]) { return $true }
        if ($Candidate.PriorityCounts[$i] -lt $Best.PriorityCounts[$i]) { return $false }
    }
    for ($i=0; $i -lt $EntryCount; $i++) {
        if ($Candidate.Bits[$i] -and -not $Best.Bits[$i]) { return $true }
        if ($Best.Bits[$i] -and -not $Candidate.Bits[$i]) { return $false }
    }
    if ($Candidate.Cost -lt ($Best.Cost-0.0000001)) { return $true }
    return $false
}

function Expand-AegisGridSummary {
    param($Entries, $Summary, $Zone, [int]$Gap)
    $items=New-Object System.Collections.ArrayList
    if ($null -eq $Summary -or $Summary.Count -eq 0) {
        foreach ($entry in $Entries) { [void]$items.Add((New-AegisLayoutItem $entry 'Deferred' 'GridSpaceExhausted' $null $false $Zone)) }
        return @{Items=$items.ToArray()}
    }
    $columns=New-Object System.Collections.ArrayList; $rows=New-Object System.Collections.ArrayList
    for ($i=0; $i -lt $Summary.UsedColumns; $i++) { [void]$columns.Add(@{Minimum=$Summary.ColumnMinimums[$i];Weight=1}) }
    for ($i=0; $i -lt $Summary.Rows; $i++) { [void]$rows.Add(@{Minimum=$Summary.RowMinimums[$i];Weight=1}) }
    [int[]]$widths=(Get-AegisWeightedTracks $columns $Zone.Width $Gap).Values
    [int[]]$heights=(Get-AegisWeightedTracks $rows $Zone.Height $Gap).Values
    [int[]]$lefts=New-Object 'int[]' $widths.Length; [int[]]$tops=New-Object 'int[]' $heights.Length
    [long]$cursor=$Zone.Left
    for ($i=0; $i -lt $widths.Length; $i++) { $lefts[$i]=[int]$cursor; $cursor+=[long]$widths[$i]+$Gap }
    $cursor=$Zone.Top
    for ($i=0; $i -lt $heights.Length; $i++) { $tops[$i]=[int]$cursor; $cursor+=[long]$heights[$i]+$Gap }
    [int]$slot=0
    for ($i=0; $i -lt $Entries.Count; $i++) {
        $entry=$Entries[$i]
        if (-not $Summary.Bits[$i]) { [void]$items.Add((New-AegisLayoutItem $entry 'Deferred' 'GridSpaceExhausted' $null $false $Zone)); continue }
        [int]$row=[Math]::Floor($slot/[double]$Summary.Columns); [int]$column=$slot%$Summary.Columns; $slot++
        [int]$width=$entry.RequiredWidth; [int]$height=$entry.RequiredHeight
        $reason='GridSlot'; $adjustment=[string]$entry.Adjustment
        if ($entry.EffectiveMode -eq 'Fill') {
            $width=[Math]::Min($widths[$column],$entry.MaximumWidth); $height=[Math]::Min($heights[$row],$entry.MaximumHeight)
        } elseif ($entry.EffectiveMode -eq 'Preferred') {
            $width=[Math]::Min($widths[$column],$entry.DesiredWidth); $height=[Math]::Min($heights[$row],$entry.DesiredHeight)
            if ($width -ne $entry.RequestedWidth -or $height -ne $entry.RequestedHeight) { $reason='PreferredSizeAdjusted'; $adjustment='PreferredClampedToApplicationOrSpace' }
        }
        if ($adjustment -ne '' -and $reason -eq 'GridSlot') { $reason=$adjustment }
        $rectangle=@{Left=$lefts[$column];Top=$tops[$row];Width=$width;Height=$height}
        $item=New-AegisLayoutItem $entry 'Planned' $reason $rectangle $entry.Resize $Zone
        $item.Adjustment=$adjustment; [void]$items.Add($item)
    }
    return @{Items=$items.ToArray()}
}

function New-AegisLayoutPlan {
    param($Windows, [hashtable]$WorkArea, [hashtable]$Options)
    if ($null -eq $Options) { $Options=@{} }
    if ($null -eq $WorkArea) { throw 'WorkAreaRequired' }
    $timer=[System.Diagnostics.Stopwatch]::StartNew()
    [int]$areaLeft=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $WorkArea 'Left' $null) 'WorkArea.Left' ([int]::MinValue) ([int]::MaxValue)
    [int]$areaTop=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $WorkArea 'Top' $null) 'WorkArea.Top' ([int]::MinValue) ([int]::MaxValue)
    [int]$areaWidth=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $WorkArea 'Width' $null) 'WorkArea.Width' 1 ([int]::MaxValue)
    [int]$areaHeight=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $WorkArea 'Height' $null) 'WorkArea.Height' 1 ([int]::MaxValue)
    if (([long]$areaLeft+$areaWidth) -gt [int]::MaxValue -or ([long]$areaTop+$areaHeight) -gt [int]::MaxValue) { throw 'WorkAreaCoordinateOverflow' }
    [int]$margin=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $Options 'Margin' 8) 'Margin' 0 128
    [int]$gap=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $Options 'Gap' 8) 'Gap' 0 128
    [int]$maxCandidates=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $Options 'MaxCandidates' 12) 'MaxCandidates' 1 32
    [int]$maxWindows=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $Options 'MaxWindows' 64) 'MaxWindows' 1 256
    [int]$timeout=ConvertTo-AegisLayoutInteger (Get-AegisLayoutValue $Options 'PlanningTimeoutMs' 1500) 'PlanningTimeoutMs' 1 120000
    $mode=[string](Get-AegisLayoutValue $Options 'Mode' 'Grid')
    if ($mode -ine 'Grid') { throw 'OnlyGridModeSupported' }
    $weightInput=Get-AegisLayoutValue $Options 'Weights' @{3=50;2=32;1=18}
    if ($weightInput -isnot [System.Collections.IDictionary]) { throw 'InvalidTierWeights' }
    $weights=@{}
    foreach ($tier in @(3,2,1)) {
        $value=$null
        if ($weightInput.Contains($tier)) { $value=$weightInput[$tier] }
        elseif ($weightInput.Contains([string]$tier)) { $value=$weightInput[[string]$tier] }
        $weights[$tier]=ConvertTo-AegisLayoutInteger $value ('Weight.Tier'+$tier) 1 1000000
    }
    $inputs=@(); if ($null -ne $Windows) { $inputs=@($Windows) }
    $entries=New-Object System.Collections.ArrayList; $eligible=New-Object System.Collections.ArrayList
    $results=@{}; $seen=@{}; $groupMetadata=@{}
    $zones=New-Object System.Collections.ArrayList; $warnings=New-Object System.Collections.ArrayList
    [long]$innerWidth=[long]$areaWidth-2*[long]$margin; [long]$innerHeight=[long]$areaHeight-2*[long]$margin
    [int]$candidateCount=0; $complete=($inputs.Count -le $maxWindows)
    if (-not $complete) { [void]$warnings.Add('MaxWindowsExceeded') }
    [int]$inputIndex=0
    foreach ($window in $inputs) {
        if ($null -eq $window) { throw 'NullWindowInput' }
        # Normalize fields once. Repeated PowerShell helper calls per field are
        # disproportionately expensive on the legacy engine and allocate heavily.
        $data=@{Id='';Tier=2;GroupId='default';Priority=0;GroupPriority=0;GroupWeight=100;LayoutOrder=$inputIndex;Reserved=$false;Width=$null;Height=$null;SizeMode='Preserve';Resizable=$false;MinMaxReady=$false;DesiredWidth=$null;DesiredHeight=$null;MinWidth=0;MinHeight=0;MaxWidth=0;MaxHeight=0}
        if ($window -is [System.Collections.IDictionary]) {
            foreach ($key in $window.Keys) { if ($data.ContainsKey([string]$key)) { $data[[string]$key]=$window[$key] } }
        } else {
            foreach ($property in $window.PSObject.Properties) { if ($data.ContainsKey($property.Name)) { $data[$property.Name]=$property.Value } }
        }
        $id=[string]$data.Id
        if ([string]::IsNullOrEmpty($id.Trim())) { throw 'WindowIdRequired' }
        if ($seen.ContainsKey($id)) { throw ('DuplicateWindowId: '+$id) }; $seen[$id]=$true
        $entry=@{Id=$id;Window=$window;Tier=2;GroupId='default';Priority=0;LayoutOrder=$inputIndex;Reserved=$false;Adjustment=''}
        [void]$entries.Add($entry); $inputIndex++
        if (-not $complete) { $results[$id]=New-AegisLayoutItem $entry 'Deferred' 'MaxWindowsExceeded' $null $false $null; continue }
        try {
            $entry.Tier=ConvertTo-AegisLayoutInteger $data.Tier 'Window.Tier' 1 3
            $entry.GroupId=[string]$data.GroupId
            if ([string]::IsNullOrEmpty($entry.GroupId.Trim()) -or $entry.GroupId.Length -gt 128) { throw 'InvalidGroupId' }
            $entry.Priority=ConvertTo-AegisLayoutInteger $data.Priority 'Window.Priority' -1000000 1000000
            $entry.GroupPriority=ConvertTo-AegisLayoutInteger $data.GroupPriority 'Window.GroupPriority' -1000000 1000000
            $entry.GroupWeight=ConvertTo-AegisLayoutInteger $data.GroupWeight 'Window.GroupWeight' 1 1000000
            $entry.LayoutOrder=ConvertTo-AegisLayoutInteger $data.LayoutOrder 'Window.LayoutOrder' 0 ([int]::MaxValue)
            $reservedValue=$data.Reserved
            if ($reservedValue -isnot [bool]) { throw 'InvalidReservedFlag' }; $entry.Reserved=[bool]$reservedValue
            [int]$actualWidth=ConvertTo-AegisLayoutInteger $data.Width 'Window.Width' 1 ([int]::MaxValue)
            [int]$actualHeight=ConvertTo-AegisLayoutInteger $data.Height 'Window.Height' 1 ([int]::MaxValue)
            $sizeMode=[string]$data.SizeMode
            if (@('Preserve','Exact','Preferred','Fill') -notcontains $sizeMode) { throw 'InvalidSizeMode' }
            $resizable=$data.Resizable; $constraints=$data.MinMaxReady
            if ($resizable -isnot [bool] -or $constraints -isnot [bool]) { throw 'InvalidConstraintReadiness' }
            $entry.RequiredWidth=$actualWidth; $entry.RequiredHeight=$actualHeight
            $entry.MaximumWidth=$actualWidth; $entry.MaximumHeight=$actualHeight
            $entry.DesiredWidth=$actualWidth; $entry.DesiredHeight=$actualHeight
            $entry.RequestedWidth=$actualWidth; $entry.RequestedHeight=$actualHeight
            $entry.Resize=$false; $entry.EffectiveMode='Preserve'
            if ($sizeMode -eq 'Exact' -or $sizeMode -eq 'Preferred') {
                $entry.RequestedWidth=ConvertTo-AegisLayoutInteger $data.DesiredWidth 'Window.DesiredWidth' 1 ([int]::MaxValue)
                $entry.RequestedHeight=ConvertTo-AegisLayoutInteger $data.DesiredHeight 'Window.DesiredHeight' 1 ([int]::MaxValue)
            }
            if ($sizeMode -ne 'Preserve') {
                if (-not $resizable -or -not $constraints) {
                    if ($sizeMode -eq 'Exact' -and ($entry.RequestedWidth -ne $actualWidth -or $entry.RequestedHeight -ne $actualHeight)) {
                        if (-not $resizable) { throw 'ExactSizeRequiresResizableWindow' }; throw 'ExactSizeConstraintsUnavailable'
                    }
                    if (-not $resizable) { $entry.Adjustment='NonResizableSizePreserved' } else { $entry.Adjustment='UnknownConstraintsSizePreserved' }
                } else {
                    [int]$minWidth=ConvertTo-AegisLayoutInteger $data.MinWidth 'Window.MinWidth' 0 ([int]::MaxValue)
                    [int]$minHeight=ConvertTo-AegisLayoutInteger $data.MinHeight 'Window.MinHeight' 0 ([int]::MaxValue)
                    [int]$maxWidth=ConvertTo-AegisLayoutInteger $data.MaxWidth 'Window.MaxWidth' 0 ([int]::MaxValue)
                    [int]$maxHeight=ConvertTo-AegisLayoutInteger $data.MaxHeight 'Window.MaxHeight' 0 ([int]::MaxValue)
                    $minWidth=[Math]::Max(1,$minWidth); $minHeight=[Math]::Max(1,$minHeight)
                    if ($maxWidth -eq 0) { $maxWidth=[int]::MaxValue }; if ($maxHeight -eq 0) { $maxHeight=[int]::MaxValue }
                    if ($maxWidth -lt $minWidth -or $maxHeight -lt $minHeight) { throw 'ContradictorySizeBounds' }
                    if ($sizeMode -eq 'Exact') {
                        if ($entry.RequestedWidth -lt $minWidth -or $entry.RequestedHeight -lt $minHeight -or $entry.RequestedWidth -gt $maxWidth -or $entry.RequestedHeight -gt $maxHeight) { throw 'ExactSizeOutsideApplicationBounds' }
                        $entry.RequiredWidth=$entry.RequestedWidth; $entry.RequiredHeight=$entry.RequestedHeight
                        $entry.MaximumWidth=$entry.RequestedWidth; $entry.MaximumHeight=$entry.RequestedHeight
                    } else {
                        $entry.RequiredWidth=$minWidth; $entry.RequiredHeight=$minHeight
                        $entry.MaximumWidth=$maxWidth; $entry.MaximumHeight=$maxHeight
                        $entry.DesiredWidth=[Math]::Min($maxWidth,[Math]::Max($minWidth,$entry.RequestedWidth))
                        $entry.DesiredHeight=[Math]::Min($maxHeight,[Math]::Max($minHeight,$entry.RequestedHeight))
                    }
                    $entry.Resize=$true; $entry.EffectiveMode=$sizeMode
                }
            }
            if ($innerWidth -le 0 -or $innerHeight -le 0) { throw 'WorkAreaTooSmall' }
            if ($entry.RequiredWidth -gt $innerWidth -or $entry.RequiredHeight -gt $innerHeight) { throw 'WindowLargerThanWorkArea' }
            $groupKey=[string]$entry.Tier+'|'+$entry.GroupId
            if ($groupMetadata.ContainsKey($groupKey)) {
                if ($groupMetadata[$groupKey].Priority -ne $entry.GroupPriority -or $groupMetadata[$groupKey].Weight -ne $entry.GroupWeight) { throw 'ConflictingGroupMetadata' }
            } else { $groupMetadata[$groupKey]=@{Priority=$entry.GroupPriority;Weight=$entry.GroupWeight} }
            [void]$eligible.Add($entry)
        } catch { $results[$id]=New-AegisLayoutItem $entry 'Deferred' ('InvalidOrUnfitWindow: '+$_.Exception.Message) $null $false $null }
    }

    $activeTiers=New-Object System.Collections.ArrayList; [long]$tierMinimumSum=0
    # Explicit key expressions avoid legacy Sort-Object property adaptation of hashtables.
    foreach ($tier in @(3,2,1)) {
        $tierEntries=@($eligible | Where-Object {$_.Tier -eq $tier} | Sort-Object @{Expression={[int]$_['GroupPriority']};Descending=$true},@{Expression={[string]$_['GroupId']}},@{Expression={[int]$_['Priority']};Descending=$true},@{Expression={[int]$_['LayoutOrder']}},@{Expression={[string]$_['Id']}})
        if ($tierEntries.Count -eq 0) { continue }
        # Leading business group/window establishes a floor; a lower demand cannot
        # inflate the floor and evict a more important tier.
        [int]$minimum=$tierEntries[0].RequiredWidth
        [long]$next=$tierMinimumSum+$minimum+[long]$gap*$activeTiers.Count
        if ($next -gt $innerWidth) {
            foreach ($entry in $tierEntries) { $results[$entry.Id]=New-AegisLayoutItem $entry 'Deferred' 'TierSpaceExhausted' $null $false $null }; continue
        }
        [void]$activeTiers.Add(@{Tier=$tier;Entries=$tierEntries;Minimum=$minimum;Weight=$weights[$tier]}); $tierMinimumSum+=$minimum
    }
    if ($activeTiers.Count -gt 0) {
        [int[]]$tierWidths=(Get-AegisWeightedTracks $activeTiers ([int]$innerWidth) $gap).Values
        [long]$tierLeft=[long]$areaLeft+$margin
        for ($ti=0; $ti -lt $activeTiers.Count; $ti++) {
            $tierData=$activeTiers[$ti]
            $tierZone=@{Level='Tier';Tier=$tierData.Tier;GroupId='';Left=[int]$tierLeft;Top=[int]([long]$areaTop+$margin);Width=$tierWidths[$ti];Height=[int]$innerHeight}
            [void]$zones.Add($tierZone); $tierLeft+=[long]$tierWidths[$ti]+$gap
            $groupMap=@{}; $groupList=New-Object System.Collections.ArrayList
            foreach ($entry in $tierData.Entries) {
                if ($entry.RequiredWidth -gt $tierZone.Width) { $results[$entry.Id]=New-AegisLayoutItem $entry 'Deferred' 'WindowWiderThanTier' $null $false $tierZone; continue }
                if (-not $groupMap.ContainsKey($entry.GroupId)) {
                    $group=@{Id=$entry.GroupId;Priority=$entry.GroupPriority;Weight=$entry.GroupWeight;Entries=(New-Object System.Collections.ArrayList);Minimum=0}
                    $groupMap[$entry.GroupId]=$group; [void]$groupList.Add($group)
                }
                [void]$groupMap[$entry.GroupId].Entries.Add($entry)
            }
            $orderedGroups=@($groupList.ToArray() | Sort-Object @{Expression={[int]$_['Priority']};Descending=$true},@{Expression={[string]$_['Id']}})
            $activeGroups=New-Object System.Collections.ArrayList; [long]$groupMinimumSum=0
            foreach ($group in $orderedGroups) {
                $group.Entries=@($group.Entries.ToArray() | Sort-Object @{Expression={[int]$_['Priority']};Descending=$true},@{Expression={[int]$_['LayoutOrder']}},@{Expression={[string]$_['Id']}})
                $group.Minimum=[int]$group.Entries[0].RequiredHeight
                [long]$next=$groupMinimumSum+$group.Minimum+[long]$gap*$activeGroups.Count
                if ($next -gt $tierZone.Height) {
                    foreach ($entry in $group.Entries) { $results[$entry.Id]=New-AegisLayoutItem $entry 'Deferred' 'GroupSpaceExhausted' $null $false $tierZone }; continue
                }
                [void]$activeGroups.Add($group); $groupMinimumSum+=$group.Minimum
            }
            if ($activeGroups.Count -eq 0) { continue }
            [int[]]$groupHeights=(Get-AegisWeightedTracks $activeGroups $tierZone.Height $gap).Values
            [long]$groupTop=$tierZone.Top
            for ($gi=0; $gi -lt $activeGroups.Count; $gi++) {
                $group=$activeGroups[$gi]
                $zone=@{Level='Group';Tier=$tierData.Tier;GroupId=$group.Id;Left=$tierZone.Left;Top=[int]$groupTop;Width=$tierZone.Width;Height=$groupHeights[$gi]}
                [void]$zones.Add($zone); $groupTop+=[long]$groupHeights[$gi]+$gap
                [int]$priorityIndex=-1; $lastPriority=$null
                foreach ($entry in $group.Entries) {
                    if ($null -eq $lastPriority -or $lastPriority -ne $entry.Priority) { $priorityIndex++; $lastPriority=$entry.Priority }
                    $entry.PriorityIndex=$priorityIndex
                }
                $best=$null
                foreach ($columns in (Get-AegisGridColumns $group.Entries $zone $gap $maxCandidates).Values) {
                    if ($timer.ElapsedMilliseconds -ge $timeout) { $complete=$false; break }
                    $candidate=New-AegisGridSummary $group.Entries $zone $gap $columns $timer $timeout; $candidateCount++
                    if ($candidate.Expired) { $complete=$false; break }
                    if (Test-AegisGridBetter $candidate $best ($priorityIndex+1) $group.Entries.Count) { $best=$candidate }
                }
                foreach ($item in (Expand-AegisGridSummary $group.Entries $best $zone $gap).Items) { $results[$item.Id]=$item }
            }
        }
    }
    if ($timer.ElapsedMilliseconds -ge $timeout) { $complete=$false }
    if (-not $complete -and $inputs.Count -le $maxWindows) { [void]$warnings.Add('PlanningTimeBudgetExceeded') }
    $output=New-Object System.Collections.ArrayList; [int]$plannedCount=0
    foreach ($entry in $entries) {
        if (-not $complete -and $inputs.Count -le $maxWindows) { $results[$entry.Id]=New-AegisLayoutItem $entry 'Deferred' 'PlanningTimeBudgetExceeded' $null $false $null }
        if (-not $results.ContainsKey($entry.Id)) { $results[$entry.Id]=New-AegisLayoutItem $entry 'Deferred' 'NoLayoutSlot' $null $false $null }
        if ($results[$entry.Id].Status -eq 'Planned') { $plannedCount++ }; [void]$output.Add($results[$entry.Id])
    }
    return @{
        Items=$output.ToArray(); Zones=$zones.ToArray(); Warnings=$warnings.ToArray(); Complete=$complete
        Counters=@{InputCount=$inputs.Count;EligibleCount=$eligible.Count;PlannedCount=$plannedCount;CandidateCount=$candidateCount;CandidateLimitPerGroup=$maxCandidates;ElapsedMs=$timer.ElapsedMilliseconds}
    }
}

# Native adapter. Windows PowerShell 2.0 / .NET Framework 2.0 compatible.
# Reflection.Emit uses AssemblyBuilderAccess.Run: this adapter writes no files.
# All geometry is an OUTER rectangle in the current caller's DPI context.
# ProcessStart is the exact creation FILETIME, encoded as 16 uppercase hex digits.

function Get-AegisNativeField {
    param($Object, [string]$Name, $Default)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
    } else {
        $property = $Object.PSObject.Properties[$Name]
        if ($null -ne $property) { return $property.Value }
    }
    return $Default
}

function Test-AegisNativeWindows {
    return ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
}

function Initialize-AegisNative {
    # Change this version if any emitted method or field changes. The API's own
    # assembly resolves its structs, so an unrelated old dynamic assembly cannot
    # supply a struct with the same short name.
    $prefix = 'Aegis_PS2_20261113_Native6'
    $cached = Get-Variable -Name AegisNativeCacheV4 -Scope Global -ErrorAction SilentlyContinue
    if ($null -ne $cached -and $cached.Value -is [hashtable]) {
        $cache = $cached.Value
        if ($cache.ContainsKey('Prefix') -and $cache.Prefix -eq $prefix -and $cache.ContainsKey('Api') -and $cache.Api -is [type] -and $cache.ContainsKey('Types') -and $cache.Types -is [hashtable]) {
            $script:AegisNativeApiType = $cache.Api
            $script:AegisNativeTypes = $cache.Types
            return
        }
    }
    $api = ($prefix + '.Api') -as [type]
    if ($null -eq $api) {
        $assemblyName = New-Object System.Reflection.AssemblyName ($prefix + '_' + [Guid]::NewGuid().ToString('N'))
        $assemblyArguments = [object[]]@($assemblyName.PSObject.BaseObject, [System.Reflection.Emit.AssemblyBuilderAccess]::Run)
        $assemblySignature = [type[]]@([System.Reflection.AssemblyName], [System.Reflection.Emit.AssemblyBuilderAccess])
        $factory = [AppDomain].GetMethod('DefineDynamicAssembly', $assemblySignature)
        if ($null -ne $factory) {
            $assembly = $factory.Invoke([AppDomain]::CurrentDomain, $assemblyArguments)
        } else {
            # This branch permits metadata-only tests under current PowerShell.
            # Windows PowerShell 2.0 takes the AppDomain branch above.
            $factory = [System.Reflection.Emit.AssemblyBuilder].GetMethod('DefineDynamicAssembly', $assemblySignature)
            if ($null -eq $factory) { throw 'DynamicAssemblyFactoryUnavailable' }
            $assembly = $factory.Invoke($null, $assemblyArguments)
        }
        $module = $assembly.DefineDynamicModule($prefix + '.Module')
        $types = @{}
        $definitions = @(
            @('Rect', [int], @('Left','Top','Right','Bottom')),
            @('Point', [int], @('X','Y')),
            @('MinMaxInfo', [int], @('ReservedX','ReservedY','MaxSizeX','MaxSizeY','MaxPositionX','MaxPositionY','MinTrackX','MinTrackY','MaxTrackX','MaxTrackY')),
            @('Placement', [int], @('length','flags','showCmd','minX','minY','maxX','maxY','nLeft','nTop','nRight','nBottom')),
            @('MonitorInfo', [int], @('Size','MonitorLeft','MonitorTop','MonitorRight','MonitorBottom','WorkLeft','WorkTop','WorkRight','WorkBottom','Flags')),
            @('FileTime', [uint32], @('Low','High'))
        )
        foreach ($definition in $definitions) {
            $builder = $module.DefineType(($prefix + '.' + $definition[0]), [System.Reflection.TypeAttributes]'Public,SequentialLayout,Sealed', [ValueType])
            foreach ($field in $definition[2]) {
                [void]$builder.DefineField($field, $definition[1], [System.Reflection.FieldAttributes]::Public)
            }
            $types[$definition[0]] = $builder.CreateType()
        }

        $delegateBuilder = $module.DefineType(($prefix + '.EnumCallback'), [System.Reflection.TypeAttributes]'Public,Sealed', [MulticastDelegate])
        $constructor = $delegateBuilder.DefineConstructor([System.Reflection.MethodAttributes]'RTSpecialName,HideBySig,Public', [System.Reflection.CallingConventions]::Standard, [type[]]@([object],[IntPtr]))
        $constructor.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $invoke = $delegateBuilder.DefineMethod('Invoke', [System.Reflection.MethodAttributes]'Public,HideBySig,NewSlot,Virtual', [bool], [type[]]@([IntPtr],[IntPtr]))
        $invoke.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $unmanagedConstructor = [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute].GetConstructor([type[]]@([System.Runtime.InteropServices.CallingConvention]))
        $unmanagedAttribute = New-Object System.Reflection.Emit.CustomAttributeBuilder ($unmanagedConstructor, [object[]]@([System.Runtime.InteropServices.CallingConvention]::Winapi))
        $delegateBuilder.SetCustomAttribute($unmanagedAttribute)
        $types['EnumCallback'] = $delegateBuilder.CreateType()

        $monitorDelegate = $module.DefineType(($prefix + '.MonitorCallback'), [System.Reflection.TypeAttributes]'Public,Sealed', [MulticastDelegate])
        $monitorConstructor = $monitorDelegate.DefineConstructor([System.Reflection.MethodAttributes]'RTSpecialName,HideBySig,Public', [System.Reflection.CallingConventions]::Standard, [type[]]@([object],[IntPtr]))
        $monitorConstructor.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $monitorInvoke = $monitorDelegate.DefineMethod('Invoke', [System.Reflection.MethodAttributes]'Public,HideBySig,NewSlot,Virtual', [bool], [type[]]@([IntPtr],[IntPtr],[IntPtr],[IntPtr]))
        $monitorInvoke.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $monitorDelegate.SetCustomAttribute($unmanagedAttribute)
        $types['MonitorCallback'] = $monitorDelegate.CreateType()

        $apiBuilder = $module.DefineType(($prefix + '.Api'), [System.Reflection.TypeAttributes]'Public,Abstract,Sealed')
        $rectRef = $types.Rect.MakeByRefType()
        $placementRef = $types.Placement.MakeByRefType()
        $fileTimeRef = $types.FileTime.MakeByRefType()
        $methods = @(
            @('kernel32.dll','SetLastError',[void],[type[]]@([uint32]),$false),
            @('kernel32.dll','GetCurrentProcessId',[uint32],[type[]]@(),$false),
            @('kernel32.dll','GetCurrentThreadId',[uint32],[type[]]@(),$false),
            @('kernel32.dll','ProcessIdToSessionId',[bool],[type[]]@([uint32],[uint32].MakeByRefType()),$true),
            @('kernel32.dll','GetConsoleWindow',[IntPtr],[type[]]@(),$false),
            @('kernel32.dll','OpenProcess',[IntPtr],[type[]]@([uint32],[bool],[uint32]),$true),
            @('kernel32.dll','CloseHandle',[bool],[type[]]@([IntPtr]),$true),
            @('kernel32.dll','GetProcessTimes',[bool],[type[]]@([IntPtr],$fileTimeRef,$fileTimeRef,$fileTimeRef,$fileTimeRef),$true),
            @('kernel32.dll','QueryFullProcessImageNameW',[bool],[type[]]@([IntPtr],[uint32],[System.Text.StringBuilder],[uint32].MakeByRefType()),$true),
            @('user32.dll','SetThreadDpiAwarenessContext',[IntPtr],[type[]]@([IntPtr]),$true),
            @('user32.dll','GetThreadDpiAwarenessContext',[IntPtr],[type[]]@(),$false),
            @('user32.dll','GetAwarenessFromDpiAwarenessContext',[int],[type[]]@([IntPtr]),$false),
            @('user32.dll','AreDpiAwarenessContextsEqual',[bool],[type[]]@([IntPtr],[IntPtr]),$false),
            @('shcore.dll','GetProcessDpiAwareness',[int],[type[]]@([IntPtr],[int].MakeByRefType()),$false),
            @('user32.dll','IsProcessDPIAware',[bool],[type[]]@(),$false),
            @('user32.dll','GetDC',[IntPtr],[type[]]@([IntPtr]),$false),
            @('user32.dll','ReleaseDC',[int],[type[]]@([IntPtr],[IntPtr]),$false),
            @('gdi32.dll','GetDeviceCaps',[int],[type[]]@([IntPtr],[int]),$false),
            @('user32.dll','GetProcessWindowStation',[IntPtr],[type[]]@(),$true),
            @('user32.dll','GetThreadDesktop',[IntPtr],[type[]]@([uint32]),$true),
            @('user32.dll','OpenInputDesktop',[IntPtr],[type[]]@([uint32],[bool],[uint32]),$true),
            @('user32.dll','CloseDesktop',[bool],[type[]]@([IntPtr]),$true),
            @('user32.dll','GetUserObjectInformationW',[bool],[type[]]@([IntPtr],[int],[System.Text.StringBuilder],[uint32],[uint32].MakeByRefType()),$true),
            @('wtsapi32.dll','WTSQuerySessionInformationW',[bool],[type[]]@([IntPtr],[uint32],[int],[IntPtr].MakeByRefType(),[uint32].MakeByRefType()),$true),
            @('wtsapi32.dll','WTSFreeMemory',[void],[type[]]@([IntPtr]),$false),
            @('user32.dll','EnumDisplayMonitors',[bool],[type[]]@([IntPtr],[IntPtr],$types.MonitorCallback,[IntPtr]),$true),
            @('user32.dll','EnumWindows',[bool],[type[]]@($types.EnumCallback,[IntPtr]),$true),
            @('user32.dll','IsWindow',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsWindowVisible',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsWindowEnabled',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsIconic',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsZoomed',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsHungAppWindow',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','GetWindow',[IntPtr],[type[]]@([IntPtr],[uint32]),$true),
            @('user32.dll','GetWindowLongW',[int],[type[]]@([IntPtr],[int]),$true),
            @('user32.dll','GetWindowRect',[bool],[type[]]@([IntPtr],$rectRef),$true),
            @('user32.dll','GetWindowPlacement',[bool],[type[]]@([IntPtr],$placementRef),$true),
            @('user32.dll','GetWindowTextW',[int],[type[]]@([IntPtr],[System.Text.StringBuilder],[int]),$true),
            @('user32.dll','GetClassNameW',[int],[type[]]@([IntPtr],[System.Text.StringBuilder],[int]),$true),
            @('user32.dll','GetWindowThreadProcessId',[uint32],[type[]]@([IntPtr],[uint32].MakeByRefType()),$true),
            @('user32.dll','SetWindowPos',[bool],[type[]]@([IntPtr],[IntPtr],[int],[int],[int],[int],[uint32]),$true),
            @('user32.dll','SendMessageTimeoutW',[IntPtr],[type[]]@([IntPtr],[uint32],[UIntPtr],$types.MinMaxInfo.MakeByRefType(),[uint32],[uint32],[UIntPtr].MakeByRefType()),$true),
            @('user32.dll','GetCursorPos',[bool],[type[]]@($types.Point.MakeByRefType()),$true),
            @('user32.dll','MonitorFromPoint',[IntPtr],[type[]]@($types.Point,[uint32]),$false),
            @('user32.dll','MonitorFromWindow',[IntPtr],[type[]]@([IntPtr],[uint32]),$false),
            @('user32.dll','GetMonitorInfoW',[bool],[type[]]@([IntPtr],$types.MonitorInfo.MakeByRefType()),$true),
            @('user32.dll','GetSystemMetrics',[int],[type[]]@([int]),$false),
            @('dwmapi.dll','DwmGetWindowAttribute',[int],[type[]]@([IntPtr],[uint32],[int].MakeByRefType(),[uint32]),$false)
        )
        $dllConstructor = [System.Runtime.InteropServices.DllImportAttribute].GetConstructor([type[]]@([string]))
        $dllFields = [System.Reflection.FieldInfo[]]@(
            [System.Runtime.InteropServices.DllImportAttribute].GetField('EntryPoint'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('ExactSpelling'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('CallingConvention'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('CharSet'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('SetLastError'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('PreserveSig')
        )
        foreach ($definition in $methods) {
            $method = $apiBuilder.DefinePInvokeMethod($definition[1], $definition[0], $definition[1], [System.Reflection.MethodAttributes]'Public,Static,PinvokeImpl', [System.Reflection.CallingConventions]::Standard, $definition[2], $definition[3], [System.Runtime.InteropServices.CallingConvention]::Winapi, [System.Runtime.InteropServices.CharSet]::Unicode)
            # DefinePInvokeMethod has no SetLastError parameter. Emit the complete
            # DllImport pseudo attribute so the defaults do not replace our
            # explicit entry point / calling convention / character set.
            $dllValues = [object[]]@($definition[1],$true,[System.Runtime.InteropServices.CallingConvention]::Winapi,[System.Runtime.InteropServices.CharSet]::Unicode,[bool]$definition[4],$true)
            $dllAttribute = New-Object System.Reflection.Emit.CustomAttributeBuilder ($dllConstructor, [object[]]@($definition[0]), $dllFields, $dllValues)
            $method.SetCustomAttribute($dllAttribute)
            $method.SetImplementationFlags([System.Reflection.MethodImplAttributes]::PreserveSig)
        }
        $api = $apiBuilder.CreateType()
    }

    $script:AegisNativeApiType = $api
    $script:AegisNativeTypes = @{}
    foreach ($name in @('Rect','Point','MinMaxInfo','Placement','MonitorInfo','FileTime','EnumCallback','MonitorCallback')) {
        $script:AegisNativeTypes[$name] = $api.Assembly.GetType(($prefix + '.' + $name), $true)
    }
    $expectedSizes = @{ Rect = 16; Point = 8; MinMaxInfo = 40; Placement = 44; MonitorInfo = 40; FileTime = 8 }
    foreach ($name in $expectedSizes.Keys) {
        $sizeProbe = [Activator]::CreateInstance($script:AegisNativeTypes[$name])
        if ([System.Runtime.InteropServices.Marshal]::SizeOf($sizeProbe) -ne $expectedSizes[$name]) {
            throw ('NativeStructSizeMismatch:' + $name)
        }
    }
    $global:AegisNativeCacheV4 = @{ Prefix=$prefix; Api=$api; Types=$script:AegisNativeTypes }
}

function ConvertTo-AegisNativeHandle {
    param($Window)
    $handle = Get-AegisNativeField $Window 'Handle' $null
    if ($handle -is [IntPtr]) { return $handle }
    [long]$number = 0
    $id = Get-AegisNativeField $Window 'Id' ''
    if (-not [long]::TryParse([string]$id, [ref]$number)) { return [IntPtr]::Zero }
    try { return (New-Object IntPtr $number) }
    catch { return [IntPtr]::Zero }
}

function Get-AegisNativeProcess {
    param([uint32]$ProcessId, [bool]$ReadName)
    $api = $script:AegisNativeApiType
    $result = @{ ProcessStart = ''; ProcessName = ''; Ready = $false; ErrorCode = 0; Reason = 'ProcessIdentityUnavailable' }
    if ($ProcessId -eq 0) { return $result }
    $processHandle = [IntPtr]::Zero
    try {
        $processHandle = $api::OpenProcess(0x1000, $false, $ProcessId)
        $openError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($processHandle -eq [IntPtr]::Zero) {
            $processHandle = $api::OpenProcess(0x0400, $false, $ProcessId)
            $openError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        }
        if ($processHandle -eq [IntPtr]::Zero) {
            $result.ErrorCode = $openError
        } else {
            $creation = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $exitTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $kernelTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $userTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $timesOk = $api::GetProcessTimes($processHandle, [ref]$creation, [ref]$exitTime, [ref]$kernelTime, [ref]$userTime)
            $timesError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($timesOk -and ($creation.High -ne 0 -or $creation.Low -ne 0)) {
                $culture = [Globalization.CultureInfo]::InvariantCulture
                $result.ProcessStart = $creation.High.ToString('X8', $culture) + $creation.Low.ToString('X8', $culture)
                $result.Ready = $true; $result.Reason = 'IdentityRead'
            } else { $result.ErrorCode = $timesError }
            if ($ReadName) {
                [uint32]$capacity = 1024
                $buffer = New-Object System.Text.StringBuilder ([int]$capacity)
                $nameOk = $api::QueryFullProcessImageNameW($processHandle, 0, $buffer, [ref]$capacity)
                $nameError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
                if (-not $nameOk -and $nameError -eq 122) {
                    $capacity = 32768
                    $buffer = New-Object System.Text.StringBuilder ([int]$capacity)
                    $nameOk = $api::QueryFullProcessImageNameW($processHandle, 0, $buffer, [ref]$capacity)
                }
                if ($nameOk) { $result.ProcessName = [IO.Path]::GetFileNameWithoutExtension($buffer.ToString()) }
            }
        }
    } catch {
        $result.Reason = 'ProcessIdentityException'
        $result.Detail = $_.Exception.Message
    } finally {
        if ($processHandle -ne [IntPtr]::Zero) { [void]$api::CloseHandle($processHandle) }
    }
    if ($ReadName -and [string]::IsNullOrEmpty($result.ProcessName)) {
        $processObject = $null
        try {
            $processObject = [Diagnostics.Process]::GetProcessById([int]$ProcessId)
            $result.ProcessName = $processObject.ProcessName
        } catch { }
        finally { if ($null -ne $processObject) { $processObject.Dispose() } }
    }
    return $result
}

function Get-AegisNativeIdentity {
    param([IntPtr]$Handle, [bool]$ReadName = $false)
    $api = $script:AegisNativeApiType
    $result = @{
        Id = $Handle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture); Handle = $Handle
        Exists = $false; IdentityReady = $false; ProcessId = [uint32]0; ThreadId = [uint32]0
        ProcessStart = ''; ProcessName = ''; ClassName = ''; ErrorCode = 0; Reason = 'WindowMissing'
    }
    if ($Handle -eq [IntPtr]::Zero) { $result.Reason = 'WindowHandleInvalid'; return $result }
    if (-not $api::IsWindow($Handle)) { return $result }
    $result.Exists = $true
    [uint32]$windowProcessId = 0
    $threadId = $api::GetWindowThreadProcessId($Handle, [ref]$windowProcessId)
    $threadError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $result.ProcessId = $windowProcessId; $result.ThreadId = $threadId
    if ($threadId -eq 0 -or $windowProcessId -eq 0) {
        $result.ErrorCode = $threadError; $result.Reason = 'WindowOwnerUnreadable'; return $result
    }
    $classBuffer = New-Object System.Text.StringBuilder 256
    $classLength = $api::GetClassNameW($Handle, $classBuffer, $classBuffer.Capacity)
    $classError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if ($classLength -le 0) {
        $result.ErrorCode = $classError; $result.Reason = 'WindowClassUnreadable'; return $result
    }
    $result.ClassName = $classBuffer.ToString()
    $process = Get-AegisNativeProcess $windowProcessId $ReadName
    $result.ProcessStart = $process.ProcessStart; $result.ProcessName = $process.ProcessName
    if (-not $process.Ready) {
        $result.ErrorCode = $process.ErrorCode; $result.Reason = $process.Reason; return $result
    }
    # A window can disappear while the process handle is queried. Re-read the
    # cheap owner fields rather than publishing a known mixed identity.
    [uint32]$checkProcessId = 0
    $checkThreadId = $api::GetWindowThreadProcessId($Handle, [ref]$checkProcessId)
    $checkError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $result.Exists = $api::IsWindow($Handle)
    if (-not $result.Exists) { $result.Reason = 'WindowMissing'; return $result }
    if ($checkThreadId -eq 0 -or $checkProcessId -eq 0) { $result.ErrorCode = $checkError; $result.Reason = 'WindowOwnerUnreadable'; return $result }
    if ($checkThreadId -ne $threadId -or $checkProcessId -ne $windowProcessId) { $result.Reason = 'IdentityChangedDuringRead'; return $result }
    $result.IdentityReady = $true; $result.Reason = 'IdentityRead'
    return $result
}

function Test-AegisNativeIdentity {
    param($Window, $Identity)
    if (-not $Identity.Exists) { return @{ Same = $false; Reason = 'WindowMissing' } }
    if (-not $Identity.IdentityReady) { return @{ Same = $false; Reason = $Identity.Reason } }
    if (-not [bool](Get-AegisNativeField $Window 'IdentityReady' $true)) { return @{ Same = $false; Reason = 'OriginalIdentityUnreadable' } }
    $id = [string](Get-AegisNativeField $Window 'Id' '')
    $start = [string](Get-AegisNativeField $Window 'ProcessStart' '')
    $className = [string](Get-AegisNativeField $Window 'ClassName' '')
    [uint32]$expectedProcess = 0; [uint32]$expectedThread = 0
    $processValid = [uint32]::TryParse([string](Get-AegisNativeField $Window 'ProcessId' ''), [ref]$expectedProcess)
    $threadValid = [uint32]::TryParse([string](Get-AegisNativeField $Window 'ThreadId' ''), [ref]$expectedThread)
    if ([string]::IsNullOrEmpty($id) -or [string]::IsNullOrEmpty($start) -or [string]::IsNullOrEmpty($className) -or -not $processValid -or -not $threadValid -or $expectedProcess -eq 0 -or $expectedThread -eq 0) {
        return @{ Same = $false; Reason = 'OriginalIdentityIncomplete' }
    }
    # A corrupted Handle/Id pair is an invalid snapshot, not evidence that the
    # original window was closed or that Windows reused its handle.
    $expectedHandle = ConvertTo-AegisNativeHandle $Window
    if ($expectedHandle -eq [IntPtr]::Zero) { return @{ Same = $false; Reason = 'OriginalHandleInvalid' } }
    if (-not [string]::Equals($id, $expectedHandle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture), [StringComparison]::Ordinal)) {
        return @{ Same = $false; Reason = 'OriginalHandleIdMismatch' }
    }
    if (-not [string]::Equals($id, $Identity.Id, [StringComparison]::Ordinal) -or $expectedProcess -ne $Identity.ProcessId -or $expectedThread -ne $Identity.ThreadId -or -not [string]::Equals($start, $Identity.ProcessStart, [StringComparison]::Ordinal) -or -not [string]::Equals($className, $Identity.ClassName, [StringComparison]::Ordinal)) {
        return @{ Same = $false; Reason = 'IdentityMismatch' }
    }
    return @{ Same = $true; Reason = 'IdentityMatched' }
}

function Get-AegisNativePlacement {
    param([IntPtr]$Handle)
    $api = $script:AegisNativeApiType
    $placement = [Activator]::CreateInstance($script:AegisNativeTypes.Placement)
    $placement.length = 44
    $ok = $api::GetWindowPlacement($Handle, [ref]$placement)
    $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if (-not $ok) { return @{ Ready = $false; Value = $null; ErrorCode = $errorCode; Reason = 'PlacementUnavailable' } }
    $value = @{}
    foreach ($field in @('length','flags','showCmd','minX','minY','maxX','maxY','nLeft','nTop','nRight','nBottom')) {
        $value[$field] = [int]$placement.$field
    }
    [long]$normalWidth = [long]$value.nRight - $value.nLeft
    [long]$normalHeight = [long]$value.nBottom - $value.nTop
    if ($value.length -ne 44 -or $normalWidth -le 0 -or $normalHeight -le 0 -or $normalWidth -gt [int]::MaxValue -or $normalHeight -gt [int]::MaxValue) {
        return @{ Ready = $false; Value = $null; ErrorCode = 0; Reason = 'InvalidPlacement' }
    }
    return @{ Ready = $true; Value = $value; ErrorCode = 0; Reason = 'PlacementRead' }
}

function Get-AegisNativeMonitor {
    param([IntPtr]$Monitor)
    if ($Monitor -eq [IntPtr]::Zero) { return $null }
    $api = $script:AegisNativeApiType
    $info = [Activator]::CreateInstance($script:AegisNativeTypes.MonitorInfo)
    $info.Size = 40
    if (-not $api::GetMonitorInfoW($Monitor, [ref]$info)) { return $null }
    [long]$width = [long]$info.WorkRight - $info.WorkLeft
    [long]$height = [long]$info.WorkBottom - $info.WorkTop
    if ($width -le 0 -or $height -le 0 -or $width -gt [int]::MaxValue -or $height -gt [int]::MaxValue) { return $null }
    return @{
        Id = $Monitor.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture)
        Left = $info.WorkLeft; Top = $info.WorkTop; Width = [int]$width; Height = [int]$height
    }
}

function Enter-AegisDpiContext {
    Initialize-AegisNative
    $result = @{ Previous = [IntPtr]::Zero; Mode = 'CallerContext'; Changed = $false; ErrorCode = 0; Reason = 'ThreadDpiUnavailable' }
    if (-not (Test-AegisNativeWindows)) { $result.Reason = 'UnsupportedPlatform'; return $result }
    $api = $script:AegisNativeApiType
    foreach ($context in @(-4,-3)) {
        try {
            $previous = $api::SetThreadDpiAwarenessContext((New-Object IntPtr ([long]$context)))
            $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($previous -ne [IntPtr]::Zero) {
                $result.Previous = $previous; $result.Changed = $true; $result.Reason = 'ThreadDpiChanged'
                if ($context -eq -4) { $result.Mode = 'PerMonitorV2' } else { $result.Mode = 'PerMonitorV1' }
                return $result
            }
            $result.ErrorCode = $errorCode
        } catch { $result.Detail = $_.Exception.Message }
    }
    return $result
}

function Exit-AegisDpiContext {
    param($Context)
    if ($null -eq $Context -or -not [bool](Get-AegisNativeField $Context 'Changed' $false)) {
        return @{ Accepted = $true; ErrorCode = 0; Reason = 'NoDpiChange' }
    }
    if (-not (Test-AegisNativeWindows)) { return @{ Accepted = $false; ErrorCode = 0; Reason = 'UnsupportedPlatform' } }
    try {
        $api = $script:AegisNativeApiType
        $previous = Get-AegisNativeField $Context 'Previous' ([IntPtr]::Zero)
        if (-not ($previous -is [IntPtr]) -or $previous -eq [IntPtr]::Zero) { return @{ Accepted = $false; ErrorCode = 0; Reason = 'InvalidDpiContext' } }
        $restored = $api::SetThreadDpiAwarenessContext($previous)
        $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($restored -eq [IntPtr]::Zero) { return @{ Accepted = $false; ErrorCode = $errorCode; Reason = 'DpiRestoreRejected' } }
        return @{ Accepted = $true; ErrorCode = 0; Reason = 'DpiRestored' }
    } catch { return @{ Accepted = $false; ErrorCode = 0; Reason = 'DpiRestoreException'; Detail = $_.Exception.Message } }
}

# Desktop checks are observations, not a lock against a subsequent desktop
# switch. Every write rechecks; no API here switches desktops or sessions.
function Get-AegisNativeObjectName {
    param([IntPtr]$Handle)
    if ($Handle -eq [IntPtr]::Zero) { return '' }
    $api = $script:AegisNativeApiType
    $buffer = New-Object System.Text.StringBuilder 256
    [uint32]$required = 0
    if ($api::GetUserObjectInformationW($Handle, 2, $buffer, 512, [ref]$required)) { return $buffer.ToString() }
    return ''
}

function Get-AegisNativeDesktop {
    $result = @{ DesktopSafe=$false; DesktopKnown=$false; SessionId=[uint32]0; SessionState=-1; WindowStation=''; ThreadDesktop=''; InputDesktop=''; Reason='DesktopUnavailable'; ErrorCode=0 }
    $api = $script:AegisNativeApiType
    $inputDesktop = [IntPtr]::Zero
    $sessionBuffer = [IntPtr]::Zero
    try {
        [uint32]$sessionId = 0
        if (-not $api::ProcessIdToSessionId($api::GetCurrentProcessId(), [ref]$sessionId)) {
            $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='SessionIdUnavailable'; return $result
        }
        $result.SessionId=$sessionId
        if ($sessionId -eq 0) { $result.DesktopKnown=$true; $result.Reason='SessionZeroPreserved'; return $result }
        [uint32]$sessionBytes = 0
        if (-not $api::WTSQuerySessionInformationW([IntPtr]::Zero,$sessionId,8,[ref]$sessionBuffer,[ref]$sessionBytes) -or $sessionBuffer -eq [IntPtr]::Zero -or $sessionBytes -lt 4) {
            $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='SessionStateUnavailable'; return $result
        }
        $result.SessionState=[Runtime.InteropServices.Marshal]::ReadInt32($sessionBuffer)
        if ($result.SessionState -ne 0) { $result.DesktopKnown=$true; $result.Reason='SessionNotActive'; return $result }
        $result.WindowStation=Get-AegisNativeObjectName ($api::GetProcessWindowStation())
        if ([string]::IsNullOrEmpty($result.WindowStation)) { $result.Reason='WindowStationUnavailable'; return $result }
        if (-not [string]::Equals($result.WindowStation,'WinSta0',[StringComparison]::OrdinalIgnoreCase)) { $result.DesktopKnown=$true; $result.Reason='NonInteractiveWindowStation'; return $result }
        $result.ThreadDesktop=Get-AegisNativeObjectName ($api::GetThreadDesktop($api::GetCurrentThreadId()))
        # DESKTOP_READOBJECTS only. Never request switching or object-write rights.
        $inputDesktop=$api::OpenInputDesktop(0,$false,1)
        if ($inputDesktop -eq [IntPtr]::Zero) { $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='InputDesktopUnavailable'; return $result }
        $result.InputDesktop=Get-AegisNativeObjectName $inputDesktop
        if ([string]::IsNullOrEmpty($result.ThreadDesktop) -or [string]::IsNullOrEmpty($result.InputDesktop)) { $result.Reason='DesktopNameUnavailable'; return $result }
        $result.DesktopKnown=$true
        if (-not [string]::Equals($result.ThreadDesktop,'Default',[StringComparison]::OrdinalIgnoreCase) -or -not [string]::Equals($result.InputDesktop,'Default',[StringComparison]::OrdinalIgnoreCase)) { $result.Reason='InputDesktopChanged'; return $result }
        $result.DesktopSafe=$true; $result.Reason='InteractiveDesktopObserved'; return $result
    } catch { $result.Reason='DesktopCheckException'; $result.Detail=$_.Exception.Message; return $result }
    finally {
        if ($sessionBuffer -ne [IntPtr]::Zero) { $api::WTSFreeMemory($sessionBuffer) }
        if ($inputDesktop -ne [IntPtr]::Zero) { [void]$api::CloseDesktop($inputDesktop) }
    }
}

# This signature describes the observed caller coordinate context. System
# LOGPIXELS is not per-monitor DPI; app DPI transitions still require Windows
# integration testing. Unknown observations produce a stable diagnostic token
# but never authorize a write.
function Get-AegisNativeCoordinateContext {
    $api=$script:AegisNativeApiType
    $result=@{ Known=$false; Signature='CallerUnknown;SystemDpi=Unknown'; Awareness='CallerUnknown'; SystemDpiX=0; SystemDpiY=0; Reason='CoordinateContextUnavailable'; Limitation='System DPI is not a per-monitor DPI measurement.' }
    $awareness=''; $threadContext=[IntPtr]::Zero
    try {
        $threadContext=$api::GetThreadDpiAwarenessContext()
        if ($threadContext -ne [IntPtr]::Zero) {
            foreach ($candidate in @(@(-4,'PerMonitorV2'),@(-3,'PerMonitorV1'),@(-2,'SystemAware'),@(-5,'UnawareGdiScaled'),@(-1,'Unaware'))) {
                if ($api::AreDpiAwarenessContextsEqual($threadContext,(New-Object IntPtr ([long]$candidate[0])))) { $awareness=('Thread:'+ $candidate[1]); break }
            }
            if ($awareness -eq '') {
                $level=$api::GetAwarenessFromDpiAwarenessContext($threadContext)
                if ($level -ge 0 -and $level -le 2) { $awareness=('ThreadLevel:'+ $level) }
            }
        }
    } catch { }
    if ($awareness -eq '') {
        try {
            [int]$level=-1
            $status=$api::GetProcessDpiAwareness([IntPtr]::Zero,[ref]$level)
            if ($status -eq 0 -and $level -ge 0 -and $level -le 2) { $awareness=('ProcessLevel:'+ $level) }
        } catch { }
    }
    if ($awareness -eq '') {
        try { if ($api::IsProcessDPIAware()) { $awareness='LegacyProcess:Aware' } else { $awareness='LegacyProcess:Unaware' } }
        catch { }
    }
    $dc=[IntPtr]::Zero; $released=$true
    try {
        $dc=$api::GetDC([IntPtr]::Zero)
        if ($dc -ne [IntPtr]::Zero) {
            $dpiX=$api::GetDeviceCaps($dc,88); $dpiY=$api::GetDeviceCaps($dc,90)
            if ($dpiX -gt 0 -and $dpiX -le 9600 -and $dpiY -gt 0 -and $dpiY -le 9600) { $result.SystemDpiX=$dpiX; $result.SystemDpiY=$dpiY }
        }
    } catch { }
    finally { if ($dc -ne [IntPtr]::Zero) { try { $released=($api::ReleaseDC([IntPtr]::Zero,$dc) -ne 0) } catch { $released=$false } } }
    if ($awareness -ne '') { $result.Awareness=$awareness }
    $dpi='Unknown'
    if ($result.SystemDpiX -gt 0 -and $result.SystemDpiY -gt 0) { $dpi=([string]$result.SystemDpiX+','+$result.SystemDpiY) }
    $result.Signature=$result.Awareness+';SystemDpi='+$dpi
    $result.Known=($awareness -ne '' -and $dpi -ne 'Unknown' -and $released)
    if ($result.Known) { $result.Reason='CoordinateContextObserved' }
    elseif (-not $released) { $result.Reason='DeviceContextReleaseFailed' }
    elseif ($awareness -eq '') { $result.Reason='DpiAwarenessUnavailable' }
    else { $result.Reason='SystemDpiUnavailable' }
    return $result
}

function Get-AegisNativeContext {
    param([int]$TimeoutMs=1000)
    $result = @{ Complete=$false; Ready=$false; DesktopSafe=$false; DesktopReason='UnsupportedPlatform'; TopologyReady=$false; TopologySignature=''; CoordinateSignature=''; CoordinateKnown=$false; CoordinateReason='CoordinateContextUnavailable'; Monitors=@(); SessionId=[uint32]0; SessionState=-1; WindowStation=''; ThreadDesktop=''; InputDesktop=''; Reason='UnsupportedPlatform'; ErrorCode=0 }
    if (-not (Test-AegisNativeWindows)) { return $result }
    Initialize-AegisNative
    if ($TimeoutMs -lt 1 -or $TimeoutMs -gt 120000) { throw 'InvalidContextTimeout' }
    $api=$script:AegisNativeApiType
    $desktop=Get-AegisNativeDesktop
    foreach ($key in @('DesktopSafe','SessionId','SessionState','WindowStation','ThreadDesktop','InputDesktop')) { $result[$key]=$desktop[$key] }
    $result.DesktopReason=$desktop.Reason
    $coordinate=Get-AegisNativeCoordinateContext
    $result.CoordinateSignature=$coordinate.Signature; $result.CoordinateKnown=$coordinate.Known; $result.CoordinateReason=$coordinate.Reason
    $result.CoordinateLimitation=$coordinate.Limitation
    $contextState=@{ Handles=(New-Object System.Collections.ArrayList); Watch=[Diagnostics.Stopwatch]::StartNew(); TimedOut=$false; Error=''; Limit=$false; Timeout=$TimeoutMs }
    try {
        $body={
            param([IntPtr]$MonitorHandle,[IntPtr]$DeviceContext,[IntPtr]$Rectangle,[IntPtr]$Parameter)
            try {
                if ($contextState.Watch.ElapsedMilliseconds -ge $contextState.Timeout) { $contextState.TimedOut=$true; return $false }
                if ($contextState.Handles.Count -ge 64) { $contextState.Limit=$true; return $false }
                [void]$contextState.Handles.Add($MonitorHandle); return $true
            } catch { $contextState.Error=$_.Exception.Message; return $false }
        }.GetNewClosure()
        $callback=[Management.Automation.LanguagePrimitives]::ConvertTo($body,$script:AegisNativeTypes.MonitorCallback)
        $api::SetLastError(0)
        $ok=$api::EnumDisplayMonitors([IntPtr]::Zero,[IntPtr]::Zero,$callback,[IntPtr]::Zero)
        $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        [GC]::KeepAlive($callback)
        if (-not $ok -or $contextState.Handles.Count -eq 0 -or $contextState.Limit -or $contextState.TimedOut -or -not [string]::IsNullOrEmpty($contextState.Error)) { $result.Reason='MonitorEnumerationIncomplete'; return $result }
        $monitors=New-Object System.Collections.ArrayList
        $tokens=New-Object System.Collections.ArrayList
        foreach ($handle in $contextState.Handles) {
            if ($contextState.Watch.ElapsedMilliseconds -ge $TimeoutMs) { $result.Reason='ContextBudgetExceeded'; return $result }
            $monitor=Get-AegisNativeMonitor $handle
            if ($null -eq $monitor) { $result.Reason='MonitorWorkAreaUnavailable'; return $result }
            [void]$monitors.Add($monitor)
            [void]$tokens.Add(($monitor.Id+','+$monitor.Left+','+$monitor.Top+','+$monitor.Width+','+$monitor.Height))
        }
        $sorted=@($tokens.ToArray() | Sort-Object)
        $result.Monitors=$monitors.ToArray()
        $result.TopologySignature=$coordinate.Signature+'|'+[string]::Join(';',[string[]]$sorted)
        $result.TopologyReady=$true
        $result.Complete=([bool]$desktop.DesktopKnown -and [bool]$coordinate.Known)
        $result.Ready=($result.Complete -and $result.DesktopSafe)
        $result.Reason=$desktop.Reason
        $result.ErrorCode=$desktop.ErrorCode
        if (-not $coordinate.Known) { $result.Reason=$coordinate.Reason }
        return $result
    } catch { $result.Reason='ContextException'; $result.Detail=$_.Exception.Message; return $result }
    finally { $contextState.Watch.Stop() }
}

# Name lookup deliberately precedes process-creation identity, placement and
# WM_GETMINMAXINFO. Names are only selection hints; writes use full identity.
function Get-AegisNativeProcessName {
    param([uint32]$ProcessId)
    if ($ProcessId -eq 0) { return '' }
    $api=$script:AegisNativeApiType
    $handle=[IntPtr]::Zero; $name=''
    try {
        $handle=$api::OpenProcess(0x1000,$false,$ProcessId)
        if ($handle -ne [IntPtr]::Zero) {
            [uint32]$capacity=1024
            $buffer=New-Object Text.StringBuilder ([int]$capacity)
            if ($api::QueryFullProcessImageNameW($handle,0,$buffer,[ref]$capacity)) { $name=[IO.Path]::GetFileNameWithoutExtension($buffer.ToString()) }
        }
    } catch { }
    finally { if ($handle -ne [IntPtr]::Zero) { [void]$api::CloseHandle($handle) } }
    if ([string]::IsNullOrEmpty($name)) {
        $process=$null
        try { $process=[Diagnostics.Process]::GetProcessById([int]$ProcessId); $name=$process.ProcessName }
        catch { }
        finally { if ($null -ne $process) { $process.Dispose() } }
    }
    return $name
}

function Get-AegisNativeWindowState {
    param([IntPtr]$Handle,[bool]$ReadGeometry=$true)
    $api=$script:AegisNativeApiType
    $state=@{ Exists=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; StyleReady=$false; RectReady=$false; Left=0; Top=0; Width=0; Height=0; Monitor=$null; ErrorCode=0; Reason='WindowMissing' }
    if (-not $api::IsWindow($Handle)) { return $state }
    $state.Exists=$true
    $state.Visible=$api::IsWindowVisible($Handle); $state.Minimized=$api::IsIconic($Handle); $state.Maximized=$api::IsZoomed($Handle)
    $state.Enabled=$api::IsWindowEnabled($Handle); $state.Hung=$api::IsHungAppWindow($Handle)
    if (-not $ReadGeometry -and (-not $state.Visible -or $state.Minimized -or $state.Maximized -or -not $state.Enabled -or $state.Hung)) { $state.Reason='UserStatePreserved'; return $state }
    $state.Owned=($api::GetWindow($Handle,4) -ne [IntPtr]::Zero)
    $api::SetLastError(0); $style=$api::GetWindowLongW($Handle,-16); $styleError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $api::SetLastError(0); $extended=$api::GetWindowLongW($Handle,-20); $extendedError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $state.StyleReady=(($style -ne 0 -or $styleError -eq 0) -and ($extended -ne 0 -or $extendedError -eq 0))
    $state.Resizable=(($style -band 0x00040000) -ne 0); $state.ToolWindow=(($extended -band 0x80) -ne 0)
    $state.NoActivate=(($extended -band 0x08000000) -ne 0); $state.Topmost=(($extended -band 8) -ne 0)
    try {
        [int]$cloaked=0
        $status=$api::DwmGetWindowAttribute($Handle,14,[ref]$cloaked,4)
        if ($status -eq 0) { $state.Cloaked=($cloaked -ne 0); $state.CloakReady=$true }
    } catch { }
    # DWMWA_CLOAKED arrived in Windows 8; lack of that API on earlier Windows
    # is expected. On supporting systems an unreadable state cannot authorize.
    if (-not $state.CloakReady) {
        $version=[Environment]::OSVersion.Version
        if ($version.Major -lt 6 -or ($version.Major -eq 6 -and $version.Minor -lt 2)) { $state.CloakReady=$true }
    }
    if ($ReadGeometry) {
        $rect=[Activator]::CreateInstance($script:AegisNativeTypes.Rect)
        $api::SetLastError(0)
        $rectOk=$api::GetWindowRect($Handle,[ref]$rect)
        $rectError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($rectOk) {
            [long]$width=[long]$rect.Right-$rect.Left; [long]$height=[long]$rect.Bottom-$rect.Top
            if ($width -gt 0 -and $height -gt 0 -and $width -le [int]::MaxValue -and $height -le [int]::MaxValue) {
                $state.Left=$rect.Left; $state.Top=$rect.Top; $state.Width=[int]$width; $state.Height=[int]$height; $state.RectReady=$true
            }
        }
        $state.Monitor=Get-AegisNativeMonitor ($api::MonitorFromWindow($Handle,2))
        if (-not $state.RectReady) { $state.ErrorCode=$rectError; $state.Reason='WindowRectUnavailable'; return $state }
        if ($null -eq $state.Monitor) { $state.Reason='WindowMonitorUnavailable'; return $state }
    }
    if (-not $state.StyleReady) { $state.ErrorCode=[Math]::Max($styleError,$extendedError); $state.Reason='WindowStyleUnavailable' }
    elseif (-not $state.CloakReady) { $state.Reason='CloakStateUnavailable' }
    else { $state.Reason='WindowStateRead' }
    return $state
}

function Get-AegisNativePreserveReason {
    param($State)
    if (-not $State.Exists) { return 'WindowMissing' }
    if (-not $State.Visible) { return 'HiddenWindowPreserved' }
    if ($State.Minimized) { return 'MinimizedWindowPreserved' }
    if ($State.Maximized) { return 'MaximizedWindowPreserved' }
    if (-not $State.Enabled) { return 'DisabledWindowPreserved' }
    if ($State.Hung) { return 'UnresponsiveWindow' }
    if ($State.Cloaked) { return 'CloakedWindowPreserved' }
    if (-not $State.CloakReady) { return 'CloakStateUnavailable' }
    if (-not $State.StyleReady) { return 'WindowStyleUnavailable' }
    return ''
}

function Get-AegisNativeMatchingRule {
    param($Window,[object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    foreach ($rule in $Rules) {
        if ($rule -isnot [System.Collections.IDictionary]) { continue }
        $process=[string](Get-AegisNativeField $rule 'ProcessName' '')
        if ([string]::IsNullOrEmpty($process) -or -not [string]::Equals($process,[string]$Window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        $class=[string](Get-AegisNativeField $rule 'ClassName' '')
        if (-not [string]::IsNullOrEmpty($class) -and -not [string]::Equals($class,[string]$Window.ClassName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        $title=[string](Get-AegisNativeField $rule 'Title' '')
        if (-not [string]::IsNullOrEmpty($title) -and -not [string]::Equals($title,[string]$Window.Title,[StringComparison]::Ordinal)) { continue }
        return $rule
    }
    return $null
}

function Get-AegisInventory {
    param([hashtable]$Options=@{},[object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    $watch=[Diagnostics.Stopwatch]::StartNew()
    Initialize-AegisNative
    $windows=New-Object System.Collections.ArrayList; $warnings=New-Object System.Collections.ArrayList
    $result=@{ Windows=@(); Warnings=@(); Foreground=$null; CursorMonitor=$null; Complete=$true; ElapsedMs=0; DesktopSafe=$false; DesktopReason='UnsupportedPlatform'; TopologySignature=''; CoordinateSignature=''; CoordinateKnown=$false; CoordinateReason='CoordinateContextUnavailable'; Monitors=@(); Context=$null; SelectedCount=0 }
    if (-not (Test-AegisNativeWindows)) { $result.Complete=$false; $result.Warnings=@('UnsupportedPlatform'); return $result }
    $api=$script:AegisNativeApiType
    [int]$queryTimeout=0; [int]$totalTimeout=0; [int]$maxWindows=0; [int]$maxEnumerated=0
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'QueryTimeoutMs' 50),[ref]$queryTimeout) -or $queryTimeout -lt 1 -or $queryTimeout -gt 5000) { throw 'InvalidQueryTimeoutMs' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'TotalTimeoutMs' 10000),[ref]$totalTimeout) -or $totalTimeout -lt 1 -or $totalTimeout -gt 120000) { throw 'InvalidTotalTimeoutMs' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'MaxWindows' 64),[ref]$maxWindows) -or $maxWindows -lt 1 -or $maxWindows -gt 512) { throw 'InvalidMaxWindows' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'MaxEnumeratedWindows' 2048),[ref]$maxEnumerated) -or $maxEnumerated -lt 1 -or $maxEnumerated -gt 16384) { throw 'InvalidMaxEnumeratedWindows' }
    $context=Get-AegisNativeContext ([Math]::Min(1000,$totalTimeout))
    $result.Context=$context; $result.DesktopSafe=$context.DesktopSafe; $result.DesktopReason=$context.DesktopReason
    $result.TopologySignature=$context.TopologySignature; $result.Monitors=$context.Monitors
    $result.CoordinateSignature=$context.CoordinateSignature; $result.CoordinateKnown=$context.CoordinateKnown; $result.CoordinateReason=$context.CoordinateReason
    if (-not $context.CoordinateKnown) { $result.Complete=$false; [void]$warnings.Add($context.CoordinateReason) }
    if (-not $context.TopologyReady) { $result.Complete=$false; [void]$warnings.Add($context.Reason) }
    if (-not $context.DesktopSafe) { [void]$warnings.Add($context.DesktopReason) }
    [uint32]$ownProcessId=$api::GetCurrentProcessId(); $ownConsole=$api::GetConsoleWindow()
    $point=[Activator]::CreateInstance($script:AegisNativeTypes.Point)
    if ($api::GetCursorPos([ref]$point)) { $result.CursorMonitor=Get-AegisNativeMonitor ($api::MonitorFromPoint($point,2)) }
    $currentMonitorOnly=([string](Get-AegisNativeField $Options 'MonitorScope' 'EachMonitor') -eq 'CurrentMonitor')
    if ($currentMonitorOnly -and $null -eq $result.CursorMonitor) {
        $result.Complete=$false;[void]$warnings.Add('CurrentMonitorUnavailable')
        $watch.Stop();$result.ElapsedMs=$watch.ElapsedMilliseconds;$result.Warnings=$warnings.ToArray()
        return $result
    }
    $enumeration=@{ Handles=(New-Object System.Collections.ArrayList); Watch=$watch; Budget=$totalTimeout; Max=$maxEnumerated; TimedOut=$false; Limit=$false; Error='' }
    $body={
        param([IntPtr]$WindowHandle,[IntPtr]$Parameter)
        try {
            if ($enumeration.Watch.ElapsedMilliseconds -ge $enumeration.Budget) { $enumeration.TimedOut=$true; return $false }
            if ($enumeration.Handles.Count -ge $enumeration.Max) { $enumeration.Limit=$true; return $false }
            [void]$enumeration.Handles.Add($WindowHandle); return $true
        } catch { $enumeration.Error=$_.Exception.Message; return $false }
    }.GetNewClosure()
    $callback=[Management.Automation.LanguagePrimitives]::ConvertTo($body,$script:AegisNativeTypes.EnumCallback)
    $api::SetLastError(0); $ok=$api::EnumWindows($callback,[IntPtr]::Zero); $enumerationError=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); [GC]::KeepAlive($callback)
    if (-not $ok) { $result.Complete=$false; [void]$warnings.Add(('EnumerationIncomplete:'+ $enumerationError)) }
    if ($enumeration.Limit) { [void]$warnings.Add('EnumerationLimitExceeded'); $result.Complete=$false }
    if (-not [string]::IsNullOrEmpty($enumeration.Error)) { [void]$warnings.Add('EnumerationCallbackFailed'); $result.Complete=$false }
    $processNames=@{}
    [int]$baselineWidth=[Math]::Max(1,$api::GetSystemMetrics(34)); [int]$baselineHeight=[Math]::Max(1,$api::GetSystemMetrics(35))
    [int]$order=0
    foreach ($handle in $enumeration.Handles) {
        $window=@{ Id=$handle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture); Handle=$handle; Order=$order; ProcessId=[uint32]0; ThreadId=[uint32]0; ProcessStart=''; ProcessName=''; ClassName=''; Title=''; IsSelf=$false; Exists=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; Left=0; Top=0; Width=0; Height=0; MinWidth=$baselineWidth; MinHeight=$baselineHeight; MaxWidth=0; MaxHeight=0; Monitor=$null; Placement=$null; PlacementReady=$false; RectReady=$false; StyleReady=$false; IdentityReady=$false; SnapshotReady=$false; MinMaxReady=$false; ConstraintReason='NotQueried'; NativeWarnings=@(); Selected=$false; Allowed=$false; MatchedRuleId=''; SelectionTitle=''; SelectionReason='NotAllowlisted'; TopologySignature=$result.TopologySignature }
        $order++
        [void]$windows.Add($window)
        if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
        try {
            $state=Get-AegisNativeWindowState $handle $false
            foreach ($key in $state.Keys) { $window[$key]=$state[$key] }
            $preserve=Get-AegisNativePreserveReason $state
            if ($preserve -ne '') { $window.SelectionReason=$preserve; continue }
            [uint32]$owner=0; $window.ThreadId=$api::GetWindowThreadProcessId($handle,[ref]$owner); $window.ProcessId=$owner
            $window.IsSelf=($owner -eq $ownProcessId -or ($ownConsole -ne [IntPtr]::Zero -and $handle -eq $ownConsole))
            if ($window.IsSelf) { $window.SelectionReason='OwnHostWindow'; continue }
            if ($owner -eq 0 -or $window.ThreadId -eq 0) { $window.SelectionReason='WindowOwnerUnreadable'; continue }
            $classBuffer=New-Object Text.StringBuilder 256
            if ($api::GetClassNameW($handle,$classBuffer,$classBuffer.Capacity) -le 0) { $window.SelectionReason='WindowClassUnreadable'; continue }
            $window.ClassName=$classBuffer.ToString()
            if (@('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd','tooltips_class32','#32768','SysShadow') -contains $window.ClassName) { $window.SelectionReason='SystemWindowClass'; continue }
            $ownerKey=[string]$owner
            if (-not $processNames.ContainsKey($ownerKey)) { $processNames[$ownerKey]=Get-AegisNativeProcessName $owner }
            $window.ProcessName=[string]$processNames[$ownerKey]
            $possible=$false
            foreach ($rule in $Rules) {
                if ([string]::Equals([string](Get-AegisNativeField $rule 'ProcessName' ''),$window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { $possible=$true; break }
            }
            if (-not $possible) { continue }
            [int]$titleCapacity=1024 # Rule titles are limited to 512; truncation cannot equal a valid exact title.
            $titleBuffer=New-Object Text.StringBuilder $titleCapacity
            if ($api::GetWindowTextW($handle,$titleBuffer,$titleCapacity) -gt 0) { $window.Title=$titleBuffer.ToString() }
            $matched=Get-AegisNativeMatchingRule $window $Rules
            if ($null -eq $matched) { continue }
            $window.MatchedRuleId=[string](Get-AegisNativeField $matched 'Id' '')
            $window.SelectionTitle=[string](Get-AegisNativeField $matched 'Title' '')
            $include=Get-AegisNativeField $matched 'Include' $true
            if ($include -isnot [bool] -or -not $include) { $window.SelectionReason='ExplicitExcludeRule'; continue }
            $window.Allowed=$true
            # Scope is resolved before the detailed-query cap. Keep a cheap row
            # for reservation/identity uncertainty without querying another
            # monitor's process start time, rectangle, placement or min/max.
            if ($currentMonitorOnly) {
                $window.Monitor=Get-AegisNativeMonitor ($api::MonitorFromWindow($handle,2))
                if ($null -eq $window.Monitor) {
                    $window.SelectionReason='WindowMonitorUnavailable';$result.Complete=$false
                    [void]$warnings.Add('WindowMonitorUnavailable');continue
                }
                if ($window.Monitor.Id -ne $result.CursorMonitor.Id) { $window.SelectionReason='OutsideCurrentMonitor';continue }
            }
            if ($result.SelectedCount -ge $maxWindows) { $window.SelectionReason='TargetWindowLimitExceeded'; $result.Complete=$false; [void]$warnings.Add('TargetWindowLimitExceeded'); continue }
            $result.SelectedCount++
            if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
            $identity=Get-AegisNativeIdentity $handle $true
            $window.ProcessStart=$identity.ProcessStart
            if (-not [string]::Equals($identity.ProcessName,$window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { $window.SelectionReason='IdentitySelectionChanged'; continue }
            if (-not $identity.IdentityReady -or $identity.ProcessId -ne $window.ProcessId -or $identity.ThreadId -ne $window.ThreadId -or -not [string]::Equals($identity.ClassName,$window.ClassName,[StringComparison]::Ordinal)) { $window.SelectionReason=('Identity:'+ $identity.Reason); continue }
            $window.IdentityReady=$true
            $state=Get-AegisNativeWindowState $handle $true
            foreach ($key in $state.Keys) { $window[$key]=$state[$key] }
            $preserve=Get-AegisNativePreserveReason $state
            if ($preserve -ne '') { $window.SelectionReason=$preserve; continue }
            if (-not $window.RectReady -or $null -eq $window.Monitor) { $window.SelectionReason=$state.Reason; continue }
            if ($currentMonitorOnly -and $window.Monitor.Id -ne $result.CursorMonitor.Id) {
                $window.SelectionReason='WindowMonitorChangedDuringInventory';$result.Complete=$false
                [void]$warnings.Add('WindowMonitorChangedDuringInventory');continue
            }
            $placement=Get-AegisNativePlacement $handle
            $window.PlacementReady=$placement.Ready; $window.Placement=$placement.Value
            if ($window.Resizable) {
                if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
                $minmax=[Activator]::CreateInstance($script:AegisNativeTypes.MinMaxInfo)
                [UIntPtr]$messageResult=[UIntPtr]::Zero
                [uint32]$remaining=[Math]::Max(1,[Math]::Min([long]$queryTimeout,[long]$totalTimeout-$watch.ElapsedMilliseconds))
                $api::SetLastError(0)
                # ABORTIFHUNG | ERRORONEXIT; no NOTIMEOUTIFNOTHUNG.
                $query=$api::SendMessageTimeoutW($handle,0x0024,[UIntPtr]::Zero,[ref]$minmax,0x0022,$remaining,[ref]$messageResult)
                $queryError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
                if ($query -ne [IntPtr]::Zero) {
                    $window.MinMaxReady=$true; $window.ConstraintReason='MinMaxRead'
                    if ($minmax.MinTrackX -gt 0) { $window.MinWidth=$minmax.MinTrackX }
                    if ($minmax.MinTrackY -gt 0) { $window.MinHeight=$minmax.MinTrackY }
                    if ($minmax.MaxTrackX -gt 0) { $window.MaxWidth=$minmax.MaxTrackX }
                    if ($minmax.MaxTrackY -gt 0) { $window.MaxHeight=$minmax.MaxTrackY }
                    if (($window.MaxWidth -gt 0 -and $window.MaxWidth -lt $window.MinWidth) -or ($window.MaxHeight -gt 0 -and $window.MaxHeight -lt $window.MinHeight)) { $window.MinMaxReady=$false; $window.ConstraintReason='AppBoundsConflict' }
                } else { $window.ConstraintReason='MinMaxUnavailable'; $window.NativeWarnings=@(('MinMaxUnavailable:'+ $queryError)) }
            } else {
                $window.MinWidth=$window.Width; $window.MinHeight=$window.Height; $window.MaxWidth=$window.Width; $window.MaxHeight=$window.Height
                $window.MinMaxReady=$true; $window.ConstraintReason='FixedSize'
            }
            $window.SnapshotReady=($window.IdentityReady -and $window.RectReady -and $window.StyleReady -and $window.CloakReady -and $null -ne $window.Monitor)
            $window.Selected=$window.SnapshotReady
            $window.SelectionReason='Selected'
        } catch { $window.SnapshotReady=$false; $window.Selected=$false; $window.SelectionReason='InventoryException'; $window.NativeWarnings=@($_.Exception.Message) }
    }
    if ($enumeration.TimedOut -or $watch.ElapsedMilliseconds -ge $totalTimeout) { $result.Complete=$false; [void]$warnings.Add('InventoryBudgetExceeded') }
    $watch.Stop(); $result.ElapsedMs=$watch.ElapsedMilliseconds; $result.Windows=$windows.ToArray(); $result.Warnings=@($warnings.ToArray() | Select-Object -Unique)
    return $result
}

function Invoke-AegisNative {
    param([string]$Operation,$Window,$Target=$null)
    if ($Operation -eq 'Context') { return (Get-AegisNativeContext) }
    $observed=@{ Exists=$false; SameIdentity=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; StyleReady=$false; RectReady=$false; Left=0; Top=0; Width=0; Height=0; Monitor=$null; Placement=$null; PlacementReady=$false; ErrorCode=0; Reason='UnsupportedPlatform' }
    $isObserve=($Operation -eq 'Observe')
    $failure=@{ Accepted=$false; RequestIssued=$false; MayBePending=$false; ErrorCode=0; Reason='UnsupportedPlatform' }
    # The operational adapter has no show, restore, activation or Z-order write.
    if (-not $isObserve -and $Operation -ne 'Move') { $failure.Reason='UnsupportedOperation'; return $failure }
    if (-not (Test-AegisNativeWindows)) { if ($isObserve) { return $observed }; return $failure }
    $requestEntered=$false
    try {
        Initialize-AegisNative
        $api=$script:AegisNativeApiType
        if (-not $isObserve) {
            $context=Get-AegisNativeContext
            if (-not $context.Ready) { $failure.Reason=$context.Reason; $failure.ErrorCode=$context.ErrorCode; return $failure }
            $expectedTopology=[string](Get-AegisNativeField $Target 'ExpectedTopologySignature' (Get-AegisNativeField $Window 'TopologySignature' ''))
            if (-not [string]::IsNullOrEmpty($expectedTopology) -and -not [string]::Equals($expectedTopology,$context.TopologySignature,[StringComparison]::Ordinal)) { $failure.Reason='TopologyChanged'; return $failure }
        }
        $handle=ConvertTo-AegisNativeHandle $Window
        if ($handle -eq [IntPtr]::Zero) { if ($isObserve) { $observed.Reason='OriginalHandleInvalid'; return $observed }; $failure.Reason='OriginalHandleInvalid'; return $failure }
        $identity=Get-AegisNativeIdentity $handle
        $comparison=Test-AegisNativeIdentity $Window $identity
        $observed.Exists=$identity.Exists; $observed.SameIdentity=$comparison.Same; $observed.ErrorCode=$identity.ErrorCode; $observed.Reason=$comparison.Reason
        if (-not $comparison.Same) { if ($isObserve) { return $observed }; $failure.Reason=$comparison.Reason; $failure.ErrorCode=$identity.ErrorCode; return $failure }
        $state=Get-AegisNativeWindowState $handle $true
        foreach ($key in $state.Keys) { $observed[$key]=$state[$key] }
        if ($isObserve) { return $observed }
        $preserve=Get-AegisNativePreserveReason $state
        if ($preserve -ne '') { $failure.Reason=$preserve; return $failure }
        $requiredTitle=[string](Get-AegisNativeField $Window 'SelectionTitle' '')
        if (-not [string]::IsNullOrEmpty($requiredTitle)) {
            $currentTitle=New-Object Text.StringBuilder 1024
            [void]$api::GetWindowTextW($handle,$currentTitle,$currentTitle.Capacity)
            if (-not [string]::Equals($requiredTitle,$currentTitle.ToString(),[StringComparison]::Ordinal)) { $failure.Reason='WindowTitleChanged'; return $failure }
        }
        if (-not $state.RectReady -or $null -eq $state.Monitor) { $failure.Reason=$state.Reason; return $failure }
        $expectedMonitor=Get-AegisNativeField $Target 'ExpectedMonitor' (Get-AegisNativeField $Window 'Monitor' $null)
        if ($null -ne $expectedMonitor) {
            $expectedId=[string](Get-AegisNativeField $expectedMonitor 'Id' $expectedMonitor)
            if (-not [string]::Equals($expectedId,[string]$state.Monitor.Id,[StringComparison]::Ordinal)) { $failure.Reason='WindowMonitorChanged'; return $failure }
            if ($expectedMonitor -is [System.Collections.IDictionary]) {
                foreach ($key in @('Left','Top','Width','Height')) {
                    if ([string](Get-AegisNativeField $expectedMonitor $key '') -ne [string]$state.Monitor[$key]) { $failure.Reason='MonitorWorkAreaChanged'; return $failure }
                }
            }
        }
        [int]$tolerance=0
        if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Tolerance' 0),[ref]$tolerance) -or $tolerance -lt 0 -or $tolerance -gt 8) { $failure.Reason='InvalidTolerance'; return $failure }
        $expectedRect=Get-AegisNativeField $Target 'ExpectedRect' $null
        if ($null -ne $expectedRect) {
            foreach ($key in @('Left','Top','Width','Height')) {
                [int]$expectedValue=0
                if (-not [int]::TryParse([string](Get-AegisNativeField $expectedRect $key ''),[ref]$expectedValue) -or [Math]::Abs([long]$state[$key]-$expectedValue) -gt $tolerance) { $failure.Reason='WindowGeometryChanged'; return $failure }
            }
        }
        [int]$left=0; [int]$top=0; [int]$width=$state.Width; [int]$height=$state.Height
        if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Left' ''),[ref]$left) -or -not [int]::TryParse([string](Get-AegisNativeField $Target 'Top' ''),[ref]$top)) { $failure.Reason='InvalidMovePosition'; return $failure }
        $resize=Get-AegisNativeField $Target 'Resize' $null
        if ($resize -isnot [bool]) { $failure.Reason='InvalidResizeFlag'; return $failure }
        if ($resize) {
            if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Width' ''),[ref]$width) -or -not [int]::TryParse([string](Get-AegisNativeField $Target 'Height' ''),[ref]$height) -or $width -le 0 -or $height -le 0) { $failure.Reason='InvalidMoveSize'; return $failure }
            if ($width -eq $state.Width -and $height -eq $state.Height) { $resize=$false }
            elseif (-not $state.Resizable) { $failure.Reason='FixedWindowResizePreserved'; return $failure }
            elseif (-not [bool](Get-AegisNativeField $Window 'MinMaxReady' $false)) { $failure.Reason='ResizeConstraintsUnavailable'; return $failure }
            if ($resize) {
                foreach ($axis in @(@('Width','MinWidth','MaxWidth',$width),@('Height','MinHeight','MaxHeight',$height))) {
                    [int]$minimum=0; [int]$maximum=0
                    if (-not [int]::TryParse([string](Get-AegisNativeField $Window $axis[1] ''),[ref]$minimum) -or -not [int]::TryParse([string](Get-AegisNativeField $Window $axis[2] ''),[ref]$maximum) -or $minimum -lt 1 -or $maximum -lt 0 -or [int]$axis[3] -lt $minimum -or ($maximum -gt 0 -and [int]$axis[3] -gt $maximum)) { $failure.Reason='TargetViolatesAppBounds'; return $failure }
                }
            }
        }
        $inside=$false
        foreach ($monitor in $context.Monitors) {
            if ([long]$left -ge [long]$monitor.Left -and [long]$top -ge [long]$monitor.Top -and ([long]$left+$width) -le ([long]$monitor.Left+$monitor.Width) -and ([long]$top+$height) -le ([long]$monitor.Top+$monitor.Height)) { $inside=$true; break }
        }
        if (-not $inside) { $failure.Reason='TargetOutsideWorkArea'; return $failure }
        # Recheck cheap user-state flags immediately before the only write. A
        # transition can still race this read; crucially the write has NO SHOW,
        # HIDE, ACTIVATE or Z-order effect and recovery never changes show state.
        if (-not $api::IsWindowVisible($handle) -or $api::IsIconic($handle) -or $api::IsZoomed($handle) -or -not $api::IsWindowEnabled($handle) -or $api::IsHungAppWindow($handle)) { $failure.Reason='WindowStateChangedBeforeMove'; return $failure }
        [uint32]$flags=0x4214 # ASYNCWINDOWPOS | NOACTIVATE | NOZORDER | NOOWNERZORDER
        if (-not $resize) { $flags=$flags -bor 1 }
        $api::SetLastError(0); $requestEntered=$true
        $accepted=$api::SetWindowPos($handle,[IntPtr]::Zero,$left,$top,$width,$height,$flags)
        $errorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($accepted) { return @{ Accepted=$true; RequestIssued=$true; MayBePending=$true; ErrorCode=0; Reason='Accepted' } }
        return @{ Accepted=$false; RequestIssued=$true; MayBePending=$false; ErrorCode=$errorCode; Reason='MoveRejected' }
    } catch {
        if ($isObserve) { $observed.SameIdentity=$false; $observed.Reason='NativeException'; $observed.Detail=$_.Exception.Message; return $observed }
        return @{ Accepted=$false; RequestIssued=$requestEntered; MayBePending=$requestEntered; ErrorCode=0; Reason='NativeException'; Detail=$_.Exception.Message }
    }
}

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

# Explicit local data I/O. Configuration is never dot-sourced or evaluated.
function Get-AegisDataPath {
    param([string]$Path,[bool]$MustExist=$true)
    if ([string]::IsNullOrEmpty($Path) -or $Path.Length -gt 1024 -or $Path.StartsWith('\\') -or $Path.StartsWith('//')) { throw 'Use an explicit local file path; network/device paths are not supported.' }
    if ($Path -match ':' -and $Path -notmatch '^[A-Za-z]:[\\/][^:]*$') { throw 'Only filesystem paths are supported.' }
    $full=[IO.Path]::GetFullPath($Path)
    if ($MustExist) {
        $info=New-Object IO.FileInfo $full
        if (-not $info.Exists -or $info.Length -gt 262144) { throw 'Data file must exist and be at most 256 KiB.' }
    } elseif (-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($full))) { throw 'The destination directory must already exist.' }
    return $full
}

function Import-AegisProcessRules {
    param([string]$Path)
    $full=Get-AegisDataPath $Path $true
    $text=Read-AegisBoundedDataText $full
    $records=@($text | ConvertFrom-Csv -Delimiter ',')
    if ($records.Count -eq 0 -or $records.Count -gt 128) { throw 'CSV requires 1-128 process rules.' }
    $rules=New-Object System.Collections.ArrayList
    foreach ($record in $records) {
        $rule=@{}
        foreach ($property in $record.PSObject.Properties) {
            if (@('Id','ProcessName','ClassName','Title','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','Include') -notcontains $property.Name) { throw ('Unknown CSV column: '+$property.Name) }
            $value=[string]$property.Value
            if ([string]::IsNullOrEmpty($value)) { continue }
            if ($property.Name -eq 'Include') {
                [bool]$included=$false
                if (-not [bool]::TryParse($value,[ref]$included)) { throw 'CSV Include must be true or false.' }
                $rule[$property.Name]=$included
            } else { $rule[$property.Name]=$value }
        }
        [void]$rules.Add($rule)
    }
    return (ConvertTo-AegisRules $rules.ToArray())
}

function Read-AegisBoundedDataText {
    param([string]$FullPath)
    $stream=$null
    try {
        $stream=New-Object IO.FileStream ($FullPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ($stream.Length -gt 262144) { throw 'Data file exceeds 256 KiB.' }
        [byte[]]$buffer=New-Object 'byte[]' ([int]$stream.Length)
        $offset=0
        while ($offset -lt $buffer.Length) {
            $read=$stream.Read($buffer,$offset,($buffer.Length-$offset))
            if ($read -eq 0) { throw 'Data file changed while being read.' }
            $offset+=$read
        }
        if ($stream.ReadByte() -ne -1) { throw 'Data file grew while being read.' }
        $encoding=New-Object Text.UTF8Encoding ($false,$true)
        $text=$encoding.GetString($buffer)
        if ($text.Length -gt 0 -and $text[0] -eq [char]0xfeff) { $text=$text.Substring(1) }
        return $text
    } finally { if ($null -ne $stream) { $stream.Close() } }
}

function Write-AegisXmlAttributes {
    param($Writer,$Data,[string[]]$Names)
    foreach ($name in $Names) { $Writer.WriteAttributeString($name,[string](Get-AegisValue $Data $name '')) }
}

function Read-AegisXmlAttributes {
    param($Node,[string[]]$Names,[string[]]$Integers=@(),[string[]]$Booleans=@())
    if ($null -eq $Node) { throw 'Required profile element is missing.' }
    $result=@{}
    foreach ($attribute in $Node.Attributes) { if ($Names -notcontains $attribute.Name) { throw ('Unknown profile attribute: '+$attribute.Name) } }
    foreach ($name in $Names) {
        if (-not $Node.HasAttribute($name)) { throw ('Missing profile attribute: '+$name) }
        $value=$Node.GetAttribute($name)
        if ($Integers -contains $name) {
            [int]$number=0
            if (-not [int]::TryParse($value,[Globalization.NumberStyles]::Integer,[Globalization.CultureInfo]::InvariantCulture,[ref]$number)) { throw ('Invalid profile integer: '+$name) }
            $result[$name]=$number
        } elseif ($Booleans -contains $name) {
            [bool]$boolean=$false
            if (-not [bool]::TryParse($value,[ref]$boolean)) { throw ('Invalid profile Boolean: '+$name) }
            $result[$name]=$boolean
        } else { $result[$name]=[string]$value }
    }
    return $result
}

function Get-AegisXmlChildren {
    param($Node,[string[]]$Allowed)
    $byName=@{}
    foreach ($child in $Node.ChildNodes) {
        if ($child.NodeType -ne [Xml.XmlNodeType]::Element -or $Allowed -notcontains $child.Name) { throw 'Unexpected profile XML content.' }
        if ($byName.ContainsKey($child.Name)) { throw ('Duplicate profile element: '+$child.Name) }
        $byName[$child.Name]=$child
    }
    foreach ($name in $Allowed) { if (-not $byName.ContainsKey($name)) { throw ('Missing profile element: '+$name) } }
    return $byName
}

function Save-AegisProfile {
    param([hashtable]$LayoutProfile,[string]$Path)
    Test-AegisProfile $LayoutProfile
    $full=Get-AegisDataPath $Path $false
    $temporary=[IO.Path]::Combine([IO.Path]::GetDirectoryName($full),('.aegis-profile-'+[Guid]::NewGuid().ToString('N')+'.tmp'))
    $writer=$null;$stream=$null
    try {
        $stream=New-Object IO.FileStream ($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $settings=New-Object Xml.XmlWriterSettings;$settings.Encoding=New-Object Text.UTF8Encoding $true;$settings.Indent=$true;$settings.NewLineChars="`r`n"
        $writer=[Xml.XmlWriter]::Create($stream,$settings)
        $writer.WriteStartDocument();$writer.WriteStartElement('AegisProfile')
        Write-AegisXmlAttributes $writer $LayoutProfile @('SchemaVersion','Revision','CreatedUtc','TopologySignature','PolicyFingerprint')
        $writer.WriteStartElement('Options')
        foreach ($key in @($LayoutProfile.Options.Keys | Sort-Object)) {
            if ($key -eq 'Weights') { continue }
            $writer.WriteStartElement('Option');$writer.WriteAttributeString('Key',$key);$writer.WriteAttributeString('Value',[string]$LayoutProfile.Options[$key]);$writer.WriteEndElement()
        }
        foreach ($tier in @(3,2,1)) {
            $writer.WriteStartElement('Weight');$writer.WriteAttributeString('Tier',[string]$tier);$writer.WriteAttributeString('Value',[string]$LayoutProfile.Options.Weights[$tier]);$writer.WriteEndElement()
        }
        $writer.WriteEndElement();$writer.WriteStartElement('Rules')
        foreach ($rule in $LayoutProfile.Rules) {
            $writer.WriteStartElement('Rule');Write-AegisXmlAttributes $writer $rule @('Id','ProcessName','ClassName','Title','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','Include');$writer.WriteEndElement()
        }
        $writer.WriteEndElement();$writer.WriteStartElement('Slots')
        foreach ($slot in $LayoutProfile.Slots) {
            $writer.WriteStartElement('Slot');Write-AegisXmlAttributes $writer $slot @('SlotId','RuleId','Order','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height')
            $writer.WriteAttributeString('HomeConfirmed',[string][bool](Get-AegisValue $slot 'HomeConfirmed' $false))
            $writer.WriteStartElement('Identity');Write-AegisXmlAttributes $writer $slot.Identity @('Id','ProcessId','ThreadId','ProcessStart','ClassName');$writer.WriteEndElement()
            $writer.WriteStartElement('Monitor');Write-AegisXmlAttributes $writer $slot.Monitor @('Id','Left','Top','Width','Height');$writer.WriteEndElement()
            foreach ($name in @('HomeRect','ZoneRect')) { $writer.WriteStartElement($name);Write-AegisXmlAttributes $writer $slot[$name] @('Left','Top','Width','Height');$writer.WriteEndElement() }
            $writer.WriteEndElement()
        }
        $writer.WriteEndElement();$writer.WriteStartElement('Zones')
        foreach ($zone in $LayoutProfile.Zones) {
            $writer.WriteStartElement('Zone');Write-AegisXmlAttributes $writer $zone @('Level','Tier','GroupId','Left','Top','Width','Height','MonitorId');$writer.WriteEndElement()
        }
        $writer.WriteEndElement();$writer.WriteEndElement();$writer.WriteEndDocument();$writer.Flush();$writer.Close();$writer=$null;$stream.Close();$stream=$null
        if ((New-Object IO.FileInfo $temporary).Length -gt 262144) { throw 'Profile exceeds 256 KiB.' }
        # Check our serialized data before an atomic replacement. Never delete
        # the previous good file as a fallback for a failed replacement.
        [void](Import-AegisProfile $temporary)
        if ([IO.File]::Exists($full)) {
            # The PS2 method binder converts a null string argument to ''.
            # Reflection preserves the null backup-name accepted by File.Replace.
            $replaceMethod=[IO.File].GetMethod('Replace',[type[]]@([string],[string],[string]))
            [void]$replaceMethod.Invoke($null,[object[]]@($temporary,$full,$null))
        }
        else { [IO.File]::Move($temporary,$full) }
    } finally {
        if ($null -ne $writer) { $writer.Close() }
        if ($null -ne $stream) { $stream.Close() }
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
    }
}

function Import-AegisProfile {
    param([string]$Path)
    $full=Get-AegisDataPath $Path $true
    $reader=$null;$textReader=$null
    try {
        $settings=New-Object Xml.XmlReaderSettings
        $settings.ProhibitDtd=$true;$settings.XmlResolver=$null;$settings.IgnoreWhitespace=$true;$settings.IgnoreComments=$true
        $content=Read-AegisBoundedDataText $full
        $textReader=New-Object IO.StringReader $content
        $reader=[Xml.XmlReader]::Create($textReader,$settings)
        $document=New-Object Xml.XmlDocument;$document.XmlResolver=$null;$document.Load($reader)
    } finally { if ($null -ne $reader) { $reader.Close() };if ($null -ne $textReader) { $textReader.Close() } }
    $rootNode=$document.DocumentElement
    if ($null -eq $rootNode -or $rootNode.Name -cne 'AegisProfile' -or -not [string]::IsNullOrEmpty($rootNode.NamespaceURI)) { throw 'Invalid profile document root.' }
    $layoutProfile=Read-AegisXmlAttributes $rootNode @('SchemaVersion','Revision','CreatedUtc','TopologySignature','PolicyFingerprint') @('SchemaVersion','Revision')
    $sections=Get-AegisXmlChildren $rootNode @('Options','Rules','Slots','Zones')
    foreach ($section in $sections.Values) { if ($section.Attributes.Count -ne 0) { throw 'Unexpected profile section attributes.' } }
    $optionValues=@{};$weights=@{}
    foreach ($node in $sections.Options.ChildNodes) {
        if ($node.ChildNodes.Count -gt 0) { throw 'Profile option values must be attributes.' }
        if ($node.Name -eq 'Option') {
            $pair=Read-AegisXmlAttributes $node @('Key','Value')
            if ($pair.Key -eq 'Weights' -or $optionValues.ContainsKey($pair.Key)) { throw 'Invalid or duplicate profile option.' }
            $optionValues[$pair.Key]=$pair.Value
        } elseif ($node.Name -eq 'Weight') {
            $pair=Read-AegisXmlAttributes $node @('Tier','Value') @('Tier','Value')
            if (@(1,2,3) -notcontains $pair.Tier -or $weights.ContainsKey($pair.Tier)) { throw 'Invalid or duplicate tier weight.' }
            $weights[$pair.Tier]=$pair.Value
        } else { throw 'Unknown profile option element.' }
    }
    $optionValues.Weights=$weights;$layoutProfile.Options=New-AegisOptions $optionValues
    $rules=New-Object System.Collections.ArrayList
    foreach ($node in $sections.Rules.ChildNodes) {
        if ($node.Name -ne 'Rule' -or $node.ChildNodes.Count -gt 0) { throw 'Unexpected profile rule content.' }
        [void]$rules.Add((Read-AegisXmlAttributes $node @('Id','ProcessName','ClassName','Title','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','Include') @('Tier','Priority','GroupPriority','GroupWeight','Width','Height') @('Include')))
    }
    $layoutProfile.Rules=@(ConvertTo-AegisRules $rules.ToArray())
    $slots=New-Object System.Collections.ArrayList
    foreach ($node in $sections.Slots.ChildNodes) {
        if ($node.Name -ne 'Slot') { throw 'Unexpected profile slot content.' }
        $slot=Read-AegisXmlAttributes $node @('SlotId','RuleId','Order','Tier','GroupId','Priority','GroupPriority','GroupWeight','SizeMode','Width','Height','HomeConfirmed') @('Order','Tier','Priority','GroupPriority','GroupWeight','Width','Height') @('HomeConfirmed')
        $children=Get-AegisXmlChildren $node @('Identity','Monitor','HomeRect','ZoneRect')
        foreach ($child in $children.Values) { if ($child.ChildNodes.Count -gt 0) { throw 'Unexpected nested slot data.' } }
        $slot.Identity=Read-AegisXmlAttributes $children.Identity @('Id','ProcessId','ThreadId','ProcessStart','ClassName')
        $slot.Monitor=Read-AegisXmlAttributes $children.Monitor @('Id','Left','Top','Width','Height') @('Left','Top','Width','Height')
        foreach ($name in @('HomeRect','ZoneRect')) { $slot[$name]=Read-AegisXmlAttributes $children[$name] @('Left','Top','Width','Height') @('Left','Top','Width','Height') }
        [void]$slots.Add($slot)
    }
    $layoutProfile.Slots=$slots.ToArray();$zones=New-Object System.Collections.ArrayList
    foreach ($node in $sections.Zones.ChildNodes) {
        if ($node.Name -ne 'Zone' -or $node.ChildNodes.Count -gt 0) { throw 'Unexpected profile zone content.' }
        [void]$zones.Add((Read-AegisXmlAttributes $node @('Level','Tier','GroupId','Left','Top','Width','Height','MonitorId') @('Tier','Left','Top','Width','Height')))
    }
    $layoutProfile.Zones=$zones.ToArray();Test-AegisProfile $layoutProfile
    return $layoutProfile
}

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
