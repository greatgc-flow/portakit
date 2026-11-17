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
