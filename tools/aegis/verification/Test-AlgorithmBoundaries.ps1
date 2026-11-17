#requires -version 2.0
# Focused pure-planner boundary checks. No Windows/native calls.
param([string]$ProductPath='', [string]$ReportPath='')
$boundaryHarnessPath=$MyInvocation.MyCommand.Path
$boundaryPackage=Split-Path -Parent (Split-Path -Parent $boundaryHarnessPath)
if ([string]::IsNullOrEmpty($ProductPath)) { $ProductPath=Join-Path $boundaryPackage 'Aegis.ps1' }
. (Join-Path (Join-Path $boundaryPackage 'tests') 'ReportPathSafety.ps1')
$ProductPath=Get-AegisHarnessFilePath $ProductPath
$ReportPath=Resolve-AegisHarnessReportPath $ReportPath $ProductPath $boundaryHarnessPath $boundaryPackage
$ErrorActionPreference='Stop'
. $ProductPath -Action Library
$closeoutResults=New-Object Collections.ArrayList
function Assert-Closeout {param([bool]$Value,[string]$Message) if (-not $Value) {throw $Message}}
function Case-Closeout {param([string]$Id,[string]$Name,[scriptblock]$Body)
    $status='PASS';$detail=''
    try { & $Body | Out-Null } catch {$status='FAIL';$detail=$_.Exception.Message}
    [void]$closeoutResults.Add((New-Object PSObject -Property @{Id=$Id;Name=$Name;Status=$status;Detail=$detail}))
    Write-Host ($Id+' '+$status+' '+$Name+' '+$detail)
}
function Window-Closeout {param([string]$Id,[int]$Width=8,[int]$Height=8)
    return @{Id=$Id;Tier=2;GroupId='g';Priority=0;GroupPriority=0;GroupWeight=100;LayoutOrder=0;Width=$Width;Height=$Height;Resizable=$true;MinMaxReady=$true;MinWidth=1;MinHeight=1;MaxWidth=0;MaxHeight=0;SizeMode='Preserve';Reserved=$false}
}
function Options-Closeout {
    return @{Mode='Grid';Margin=0;Gap=0;MaxCandidates=32;MaxWindows=128;PlanningTimeoutMs=10000;Weights=@{3=50;2=32;1=18}}
}
function Check-CloseoutGeometry {param($Plan,$Area,[int]$Count)
    Assert-Closeout $Plan.Complete 'Unexpected incomplete bounded calculation.'
    Assert-Closeout (@($Plan.Items).Count -eq $Count) 'Output/input cardinality differs.'
    $ids=@{};$placed=@($Plan.Items | Where-Object {$_.Status -eq 'Planned'})
    foreach ($item in $Plan.Items) {
        Assert-Closeout (-not $ids.ContainsKey([string]$item.Id)) 'Duplicate output identity.'
        $ids[[string]$item.Id]=$true
    }
    foreach ($item in $placed) {
        foreach ($field in @('Left','Top','Width','Height')) { Assert-Closeout ($item[$field] -is [int]) 'Non-integer output field.' }
        Assert-Closeout ($item.Width -gt 0 -and $item.Height -gt 0) 'Nonpositive placed geometry.'
        foreach ($bound in @($Area,$item.ZoneRect)) {
            Assert-Closeout ([long]$item.Left -ge [long]$bound.Left -and [long]$item.Top -ge [long]$bound.Top -and [long]$item.Left+[long]$item.Width -le [long]$bound.Left+[long]$bound.Width -and [long]$item.Top+[long]$item.Height -le [long]$bound.Top+[long]$bound.Height) 'Placed geometry crosses its supplied boundary.'
        }
    }
    for ($i=0;$i -lt $placed.Count;$i++) {
        for ($j=$i+1;$j -lt $placed.Count;$j++) {
            $a=$placed[$i];$b=$placed[$j]
            $separate=([long]$a.Left+[long]$a.Width -le [long]$b.Left -or [long]$b.Left+[long]$b.Width -le [long]$a.Left -or [long]$a.Top+[long]$a.Height -le [long]$b.Top -or [long]$b.Top+[long]$b.Height -le [long]$a.Top)
            Assert-Closeout $separate 'Two planned rectangles overlap.'
        }
    }
    return $placed.Count
}
function Signature-Closeout {param($Plan)
    $parts=New-Object Collections.ArrayList
    foreach ($item in @($Plan.Items | Sort-Object Id)) {
        [void]$parts.Add(($item.Id+'|'+$item.Status+'|'+$item.Left+','+$item.Top+','+$item.Width+','+$item.Height))
    }
    return [string]::Join(';',[string[]]$parts.ToArray())
}

Case-Closeout 'AB01' 'Weighted tracks conserve maximum integer budgets and exact fractional remainders' {
    foreach ($weights in @(@(1,1000000),@(999999,1000000),@(999983,999979,1),@(1000000,1000000,1000000),@(1,1,1,1,1,1,1))) {
        foreach ($length in @(1001,1048573,2147483647)) {
            $tracks=New-Object Collections.ArrayList
            [long]$sum=0
            foreach ($weight in $weights) {[void]$tracks.Add(@{Minimum=1;Weight=$weight});$sum+=$weight}
            $gap=3;$actual=(Get-AegisWeightedTracks $tracks $length $gap).Values
            [long]$extra=[long]$length-$weights.Count-[long]$gap*($weights.Count-1)
            $expected=New-Object 'int[]' $weights.Count
            [long]$used=0
            for ($i=0;$i -lt $weights.Count;$i++) {$expected[$i]=1+[int][Math]::Floor(([decimal]$extra*[decimal]$weights[$i])/[decimal]$sum);$used+=$expected[$i]}
            [int]$remainder=[long]$length-[long]$gap*($weights.Count-1)-$used
            for ($i=0;$i -lt $remainder;$i++) {$expected[$i]++}
            [long]$actualTotal=[long]$gap*($weights.Count-1)
            for ($i=0;$i -lt $weights.Count;$i++) {Assert-Closeout ($actual[$i] -eq $expected[$i]) 'Weighted floor/remainder differs from exact decimal arithmetic.';$actualTotal+=$actual[$i]}
            Assert-Closeout ($actualTotal -eq $length) 'Weighted tracks lose or create budget.'
        }
    }
}
Case-Closeout 'AB02' 'Extreme negative coordinates remain integral contained and nonoverlapping' {
    $windows=New-Object Collections.ArrayList
    for ($i=0;$i -lt 12;$i++) {
        $w=Window-Closeout ([string]$i);$w.Tier=1+($i%3);$w.GroupId='g'+($i%2);$w.GroupWeight=1+999999*($i%2);$w.LayoutOrder=$i;$w.SizeMode='Fill'
        [void]$windows.Add($w)
    }
    $area=@{Left=[int]::MinValue;Top=[int]::MinValue;Width=[int]::MaxValue;Height=[int]::MaxValue}
    $options=Options-Closeout;$options.Weights=@{3=1000000;2=1;1=1000000};$options.Gap=128;$options.Margin=128
    $plan=New-AegisLayoutPlan $windows.ToArray() $area $options
    $count=Check-CloseoutGeometry $plan $area 12
    Assert-Closeout ($count -gt 0) 'Extreme valid work area produced no planned windows.'
}
Case-Closeout 'AB03' 'Near-maximum positive coordinates do not wrap after gaps and margins' {
    $windows=@((Window-Closeout 'a'),(Window-Closeout 'b'),(Window-Closeout 'c'))
    $area=@{Left=2147483447;Top=2147483447;Width=200;Height=200}
    $options=Options-Closeout;$options.Margin=8;$options.Gap=8
    $plan=New-AegisLayoutPlan $windows $area $options
    Assert-Closeout ((Check-CloseoutGeometry $plan $area 3) -eq 3) 'Valid near-maximum input unexpectedly lost windows.'
}
Case-Closeout 'AB04' 'A single grid candidate stays bounded for the public 128-window limit' {
    $windows=New-Object Collections.ArrayList
    for ($i=0;$i -lt 128;$i++) {$w=Window-Closeout ([string]$i) 1 1;$w.LayoutOrder=$i;[void]$windows.Add($w)}
    $area=@{Left=-20;Top=-20;Width=1;Height=128}
    $options=Options-Closeout;$options.MaxCandidates=1
    $plan=New-AegisLayoutPlan $windows.ToArray() $area $options
    Assert-Closeout ((Check-CloseoutGeometry $plan $area 128) -eq 128 -and $plan.Counters.CandidateCount -eq 1) 'Single-candidate bound or unit-window admission failed.'
}
Case-Closeout 'AB05' 'Explicit identity/order allocation is invariant under deterministic permutations' {
    $windows=New-Object Collections.ArrayList
    for ($i=0;$i -lt 24;$i++) {
        $w=Window-Closeout ([string]$i) (40+($i%3)*10) (30+($i%4)*10)
        $w.Tier=1+($i%3);$w.GroupId='g'+($i%2);$w.GroupWeight=1+($i%2);$w.Priority=($i%5)-2;$w.GroupPriority=$i%2;$w.LayoutOrder=$i
        [void]$windows.Add($w)
    }
    $area=@{Left=-1920;Top=-200;Width=1920;Height=1080};$options=Options-Closeout;$options.Gap=3
    $plan=New-AegisLayoutPlan $windows.ToArray() $area $options
    [void](Check-CloseoutGeometry $plan $area 24);$reference=Signature-Closeout $plan
    for ($shift=1;$shift -le 12;$shift++) {
        $permuted=New-Object Collections.ArrayList
        for ($i=0;$i -lt 24;$i++) {[void]$permuted.Add($windows[(23-$i+$shift)%24])}
        $candidate=New-AegisLayoutPlan $permuted.ToArray() $area $options
        Assert-Closeout ((Signature-Closeout $candidate) -ceq $reference) 'Input permutation changed allocation despite stable explicit order.'
    }
}
Case-Closeout 'AB06' 'All-reserved tier/group inputs occupy real stable geometry' {
    $windows=New-Object Collections.ArrayList
    for ($i=0;$i -lt 6;$i++) {$w=Window-Closeout ('reservation-'+$i) 40 30;$w.Reserved=$true;$w.Tier=1+($i%3);$w.GroupId='g'+($i%2);$w.LayoutOrder=$i;[void]$windows.Add($w)}
    $area=@{Left=-500;Top=0;Width=1000;Height=600};$options=Options-Closeout;$options.Gap=7
    $first=New-AegisLayoutPlan $windows.ToArray() $area $options;$second=New-AegisLayoutPlan $windows.ToArray() $area $options
    Assert-Closeout ((Check-CloseoutGeometry $first $area 6) -eq 6) 'Reserved geometry was silently omitted.'
    Assert-Closeout (@($first.Items | Where-Object {-not $_.Reserved}).Count -eq 0) 'Reserved identity marker lost.'
    Assert-Closeout ((Signature-Closeout $first) -ceq (Signature-Closeout $second)) 'Repeated reservation plan changed geometry.'
}
Case-Closeout 'AB07' 'Margins that consume the entire area defer without invalid applicable geometry' {
    $area=@{Left=-8;Top=-8;Width=16;Height=16};$options=Options-Closeout;$options.Margin=8
    $plan=New-AegisLayoutPlan @((Window-Closeout 'tiny' 1 1)) $area $options
    Assert-Closeout ($plan.Complete -and @($plan.Zones).Count -eq 0 -and $plan.Items[0].Status -eq 'Deferred' -and $plan.Items[0].Reason -like '*WorkAreaTooSmall*') 'Consumed inner area was reported as applicable.'
}
Case-Closeout 'AB08' 'Extreme signed group and window priority admits the feasible critical group first' {
    $low=Window-Closeout 'low' 30 70;$low.GroupId='a';$low.GroupPriority=-1000000;$low.Priority=1000000
    $high=Window-Closeout 'high' 30 70;$high.GroupId='z';$high.GroupPriority=1000000;$high.Priority=-1000000
    $area=@{Left=0;Top=0;Width=100;Height=100};$options=Options-Closeout
    $plan=New-AegisLayoutPlan @($low,$high) $area $options
    Assert-Closeout ((Check-CloseoutGeometry $plan $area 2) -eq 1 -and $plan.Items[0].Status -eq 'Deferred' -and $plan.Items[1].Status -eq 'Planned') 'Window priority escaped its group hierarchy.'
}
$failed=@($closeoutResults | Where-Object {$_.Status -eq 'FAIL'}).Count
$hashProvider=[Security.Cryptography.SHA256]::Create()
try {$productHash=[BitConverter]::ToString($hashProvider.ComputeHash([IO.File]::ReadAllBytes($ProductPath))).Replace('-','').ToLowerInvariant();$harnessHash=[BitConverter]::ToString($hashProvider.ComputeHash([IO.File]::ReadAllBytes($boundaryHarnessPath))).Replace('-','').ToLowerInvariant()}
finally {$hashProvider.Clear()}
$report=@{Suite='Algorithm boundary checks';Scope='Actual pure planner, synthetic geometry, no Windows API calls';ProductSha256=$productHash;HarnessSha256=$harnessHash;EngineVersion=[string]$PSVersionTable.PSVersion;ClrVersion=[string][Environment]::Version;ActualWindowsIntegration='NOT_RUN';ActualPS2Execution=$(if ($PSVersionTable.PSVersion.Major -eq 2) {'RUN'} else {'NOT_RUN'});Total=$closeoutResults.Count;Passed=$closeoutResults.Count-$failed;Failed=$failed;Cases=$closeoutResults.ToArray()}
if (-not [string]::IsNullOrEmpty($ReportPath)) { $report | Export-Clixml -Path $ReportPath -Depth 8 }
$report
if ($failed -gt 0) {throw 'Focused layout closeout failed.'}
