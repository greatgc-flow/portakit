# Development verification. Actual product planner, no Windows API calls.
# PS2-compatible cases with optional CLIXML evidence.
param([string]$SourcePath='', [string]$OutputPath='')
$layoutHarnessPath=$MyInvocation.MyCommand.Path
$layoutPackageRoot=Split-Path -Parent (Split-Path -Parent $layoutHarnessPath)
. (Join-Path (Join-Path $layoutPackageRoot 'tests') 'ReportPathSafety.ps1')
if ($SourcePath -eq '') { $SourcePath=Join-Path $layoutPackageRoot 'Aegis.ps1' }
$OutputPath=Resolve-AegisHarnessReportPath -Path $OutputPath -ProductPath $SourcePath -HarnessPath $layoutHarnessPath -PackageRoot $layoutPackageRoot
$ErrorActionPreference='Stop'
. $SourcePath -Action Library
$script:layoutResults=New-Object System.Collections.ArrayList
function Assert-LV($Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
function Window-LV([string]$Id,[int]$Width=200,[int]$Height=100) {
    return @{Id=$Id;Tier=2;GroupId='default';Priority=0;GroupPriority=0;GroupWeight=100;LayoutOrder=0;Width=$Width;Height=$Height;Resizable=$true;MinMaxReady=$true;MinWidth=80;MinHeight=50;MaxWidth=0;MaxHeight=0;SizeMode='Preserve';Reserved=$false}
}
function Options-LV { return @{Margin=0;Gap=0;MaxCandidates=12;MaxWindows=64;PlanningTimeoutMs=10000;Mode='Grid';Weights=@{3=50;2=32;1=18}} }
function Case-LV([string]$Id,[string]$Name,[scriptblock]$Body) {
    try { & $Body; [void]$script:layoutResults.Add(@{Id=$Id;Name=$Name;Status='PASS';Detail=''}) }
    catch { [void]$script:layoutResults.Add(@{Id=$Id;Name=$Name;Status='FAIL';Detail=$_.Exception.Message}) }
}
function CheckGeometry-LV($Plan,$Area,[int]$Expected) {
    Assert-LV ($Plan.Complete) 'Plan incomplete'
    Assert-LV (@($Plan.Items).Count -eq $Expected) 'Result count mismatch'
    $placed=@($Plan.Items | Where-Object {$_.Status -eq 'Planned'})
    foreach ($item in $placed) {
        Assert-LV ($item.Width -gt 0 -and $item.Height -gt 0) 'Nonpositive size'
        Assert-LV ($item.Left -ge $Area.Left -and $item.Top -ge $Area.Top -and [long]$item.Left+$item.Width -le [long]$Area.Left+$Area.Width -and [long]$item.Top+$item.Height -le [long]$Area.Top+$Area.Height) 'Outside work area'
        $z=$item.ZoneRect
        Assert-LV ($z.Level -eq 'Group' -and $item.Left -ge $z.Left -and $item.Top -ge $z.Top -and [long]$item.Left+$item.Width -le [long]$z.Left+$z.Width -and [long]$item.Top+$item.Height -le [long]$z.Top+$z.Height) 'Outside assigned group'
    }
    for ($i=0;$i -lt $placed.Count;$i++) {
        for ($j=$i+1;$j -lt $placed.Count;$j++) {
            $a=$placed[$i];$b=$placed[$j]
            $overlap=($a.Left -lt [long]$b.Left+$b.Width -and $b.Left -lt [long]$a.Left+$a.Width -and $a.Top -lt [long]$b.Top+$b.Height -and $b.Top -lt [long]$a.Top+$a.Height)
            Assert-LV (-not $overlap) ('Overlapping windows '+$a.Id+' / '+$b.Id)
        }
    }
}
$area=@{Left=0;Top=0;Width=1200;Height=800}

Case-LV 'LV01' 'Null and empty collections' {
    $p=New-AegisLayoutPlan $null $area (Options-LV)
    Assert-LV ($p.Complete -and @($p.Items).Count -eq 0 -and @($p.Zones).Count -eq 0) 'Empty input changed semantics'
}
Case-LV 'LV02' 'Small fixed windows receive movable slots' {
    $a=Window-LV 'a' 8 8;$b=Window-LV 'b' 8 8;$b.LayoutOrder=1
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV)
    CheckGeometry-LV $p $area 2
    Assert-LV ($p.Counters.PlannedCount -eq 2 -and -not $p.Items[0].Resize -and -not $p.Items[1].Resize) 'Tiny preserve windows were excluded or resized'
    Assert-LV ($p.Items[0].Left -ne $p.Items[1].Left -or $p.Items[0].Top -ne $p.Items[1].Top) 'Shared origin'
}
Case-LV 'LV03' 'Exact size outside application minimum is deferred' {
    $a=Window-LV 'a';$a.SizeMode='Exact';$a.DesiredWidth=40;$a.DesiredHeight=100
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Status -eq 'Deferred' -and $p.Items[0].Reason -match 'ExactSizeOutsideApplicationBounds') 'Exact minimum silently changed'
}
Case-LV 'LV04' 'Exact size outside work area is deferred' {
    $a=Window-LV 'a';$a.SizeMode='Exact';$a.DesiredWidth=1400;$a.DesiredHeight=900
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Status -eq 'Deferred' -and $p.Items[0].Reason -match 'WindowLargerThanWorkArea') 'Exact screen overflow silently shrunk'
}
Case-LV 'LV05' 'Preferred size clamps to application and available area' {
    $a=Window-LV 'a';$a.SizeMode='Preferred';$a.DesiredWidth=1500;$a.DesiredHeight=900;$a.MaxWidth=1000;$a.MaxHeight=700
    $small=@{Left=0;Top=0;Width=600;Height=500}
    $p=New-AegisLayoutPlan @($a) $small (Options-LV)
    CheckGeometry-LV $p $small 1
    Assert-LV ($p.Items[0].Width -eq 600 -and $p.Items[0].Height -eq 500 -and $p.Items[0].Reason -eq 'PreferredSizeAdjusted') 'Preferred clamp or explanation missing'
}
Case-LV 'LV06' 'Unknown constraints cause Fill to preserve current dimensions' {
    $a=Window-LV 'a' 320 240;$a.SizeMode='Fill';$a.MinMaxReady=$false
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Width -eq 320 -and $p.Items[0].Height -eq 240 -and -not $p.Items[0].Resize -and $p.Items[0].Reason -eq 'UnknownConstraintsSizePreserved') 'Unknown constraints caused resize'
}
Case-LV 'LV07' 'Unknown constraints block Exact size change' {
    $a=Window-LV 'a';$a.SizeMode='Exact';$a.DesiredWidth=500;$a.DesiredHeight=400;$a.MinMaxReady=$false
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Status -eq 'Deferred' -and $p.Items[0].Reason -match 'ExactSizeConstraintsUnavailable') 'Unknown constraints did not block Exact'
}
Case-LV 'LV08' 'Exact already sized unknown window permits position-only placement' {
    $a=Window-LV 'a' 320 240;$a.SizeMode='Exact';$a.DesiredWidth=320;$a.DesiredHeight=240;$a.MinMaxReady=$false
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Status -eq 'Planned' -and -not $p.Items[0].Resize -and $p.Items[0].Width -eq 320) 'Safe position-only Exact rejected'
}
Case-LV 'LV09' 'Business priority beats input ordering under space shortage' {
    $lo=Window-LV 'low' 400 250;$hi=Window-LV 'high' 400 250;$hi.Priority=100
    $small=@{Left=0;Top=0;Width=400;Height=300}
    $p=New-AegisLayoutPlan @($lo,$hi) $small (Options-LV)
    Assert-LV ($p.Items[1].Status -eq 'Planned' -and $p.Items[0].Status -eq 'Deferred') 'Lower priority evicted higher'
}
Case-LV 'LV10' 'High-priority counts precede lower-priority capacity' {
    $a=Window-LV 'a' 400 200;$a.Priority=100
    $b=Window-LV 'b' 200 200;$b.Priority=100;$b.LayoutOrder=1
    $c=Window-LV 'c' 200 100;$c.LayoutOrder=2
    $small=@{Left=0;Top=0;Width=600;Height=400}
    $p=New-AegisLayoutPlan @($c,$b,$a) $small (Options-LV)
    CheckGeometry-LV $p $small 3
    Assert-LV ($p.Items[1].Status -eq 'Planned' -and $p.Items[2].Status -eq 'Planned' -and $p.Counters.PlannedCount -eq 3) 'Priority-aware grid missed feasible set'
}
Case-LV 'LV11' 'Stable explicit order survives enumeration reversal' {
    $a=Window-LV 'a';$a.LayoutOrder=9;$b=Window-LV 'b';$b.LayoutOrder=2
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV);$q=New-AegisLayoutPlan @($b,$a) $area (Options-LV)
    foreach ($x in $p.Items) {
        $y=@($q.Items | Where-Object {$_.Id -eq $x.Id})[0]
        Assert-LV ($x.Left -eq $y.Left -and $x.Top -eq $y.Top -and $x.Width -eq $y.Width -and $x.Height -eq $y.Height) 'Enumeration changed stable slot'
    }
}
Case-LV 'LV12' 'Group weight divides surplus after minimums' {
    $a=Window-LV 'a';$a.GroupId='A';$a.GroupWeight=3
    $b=Window-LV 'b';$b.GroupId='B';$b.GroupWeight=1
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV)
    $za=@($p.Zones | Where-Object {$_.Level -eq 'Group' -and $_.GroupId -eq 'A'})[0]
    $zb=@($p.Zones | Where-Object {$_.Level -eq 'Group' -and $_.GroupId -eq 'B'})[0]
    Assert-LV ($za.Height -eq 550 -and $zb.Height -eq 250) 'Weighted surplus is incorrect'
}
Case-LV 'LV13' 'Group priority admits critical group when minimums cannot coexist' {
    $a=Window-LV 'a' 200 600;$a.GroupId='low';$a.GroupPriority=0
    $b=Window-LV 'b' 200 600;$b.GroupId='critical';$b.GroupPriority=100
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV)
    Assert-LV ($p.Items[1].Status -eq 'Planned' -and $p.Items[0].Reason -eq 'GroupSpaceExhausted') 'Group admission ignored priority'
}
Case-LV 'LV14' 'Tier shortage preserves higher tier instead of deferring everything' {
    $a=Window-LV 'a' 800 200;$a.Tier=3
    $b=Window-LV 'b' 800 200;$b.Tier=1
    $p=New-AegisLayoutPlan @($b,$a) $area (Options-LV)
    Assert-LV ($p.Items[1].Status -eq 'Planned' -and $p.Items[0].Reason -eq 'TierSpaceExhausted') 'Tier shortage deferred high tier'
}
Case-LV 'LV15' 'Low-priority wide demand does not block higher tier participants' {
    $a=Window-LV 'a' 300 100;$a.Tier=3;$a.Priority=100
    $b=Window-LV 'b' 1100 100;$b.Tier=3;$b.Priority=0
    $c=Window-LV 'c' 300 100;$c.Tier=2
    $p=New-AegisLayoutPlan @($b,$c,$a) $area (Options-LV)
    Assert-LV ($p.Items[2].Status -eq 'Planned' -and $p.Items[1].Status -eq 'Planned') 'Low demand inflated tier minimum'
}
Case-LV 'LV16' 'Hidden reservation occupies a genuine nonoverlapping slot' {
    $a=Window-LV 'reserved' 400 300;$a.Reserved=$true;$a.LayoutOrder=0
    $b=Window-LV 'live' 400 300;$b.LayoutOrder=1
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV)
    CheckGeometry-LV $p $area 2
    Assert-LV ($p.Items[0].Reserved -and $p.Counters.PlannedCount -eq 2) 'Reservation was dropped'
}
Case-LV 'LV17' 'Scoped group coordinates preserve supplied parent boundary' {
    $a=Window-LV 'a';$a.Tier=3;$a.GroupId='ops'
    $b=Window-LV 'b';$b.Tier=3;$b.GroupId='ops';$b.LayoutOrder=1
    $scope=@{Left=-1500;Top=300;Width=700;Height=400}
    $p=New-AegisLayoutPlan @($a,$b) $scope (Options-LV)
    CheckGeometry-LV $p $scope 2
    Assert-LV ($p.Zones[0].Left -eq -1500 -and $p.Zones[0].Top -eq 300 -and $p.Zones[0].Width -eq 700 -and $p.Zones[0].Height -eq 400) 'Scope boundary drifted'
}
Case-LV 'LV18' 'Maximum window count fails closed for the whole plan' {
    $a=Window-LV 'a';$b=Window-LV 'b';$o=Options-LV;$o.MaxWindows=1
    $p=New-AegisLayoutPlan @($a,$b) $area $o
    Assert-LV (-not $p.Complete -and $p.Counters.PlannedCount -eq 0 -and @($p.Items).Count -eq 2 -and $p.Items[0].Reason -eq 'MaxWindowsExceeded') 'Count cap produced partial apply plan'
}
Case-LV 'LV19' 'Candidate count bounded for 64 tiny windows' {
    $ws=New-Object System.Collections.ArrayList
    for ($i=0;$i -lt 64;$i++) { $w=Window-LV ('w'+$i) 8 8;$w.LayoutOrder=$i;[void]$ws.Add($w) }
    $o=Options-LV;$o.MaxCandidates=3
    $p=New-AegisLayoutPlan $ws.ToArray() $area $o
    CheckGeometry-LV $p $area 64
    Assert-LV ($p.Counters.CandidateCount -le 3 -and $p.Counters.PlannedCount -eq 64) 'Candidate budget exceeded or tiny windows lost'
}
Case-LV 'LV20' 'Time budget produces no applicable partial result' {
    $ws=New-Object System.Collections.ArrayList
    for ($i=0;$i -lt 64;$i++) { $w=Window-LV ('w'+$i) 8 8;$w.LayoutOrder=$i;[void]$ws.Add($w) }
    $o=Options-LV;$o.PlanningTimeoutMs=1
    $p=New-AegisLayoutPlan $ws.ToArray() $area $o
    Assert-LV (-not $p.Complete -and $p.Counters.PlannedCount -eq 0 -and $p.Warnings -contains 'PlanningTimeBudgetExceeded') 'Deadline did not fail closed'
}
Case-LV 'LV21' 'Input hashtables are not mutated' {
    $a=Window-LV 'a';$b=Window-LV 'b';$b.GroupId='other'
    $keysA=@($a.Keys | Sort-Object);$keysB=@($b.Keys | Sort-Object)
    $p=New-AegisLayoutPlan @($a,$b) $area (Options-LV)
    Assert-LV ([string]::Join(',', [string[]]$keysA) -eq [string]::Join(',', [string[]]@($a.Keys | Sort-Object)) -and [string]::Join(',', [string[]]$keysB) -eq [string]::Join(',', [string[]]@($b.Keys | Sort-Object))) 'Input fields were modified'
    Assert-LV ($a.Width -eq 200 -and $b.Height -eq 100 -and -not $a.ContainsKey('PriorityIndex')) 'Input sizing was mutated'
}
Case-LV 'LV22' 'Unsafe shape and duplicate IDs reject before application' {
    $a=Window-LV 'a';$duplicate=$false;$overflow=$false;$badMode=$false
    try { $null=New-AegisLayoutPlan @($a,$a) $area (Options-LV) } catch { $duplicate=$true }
    try { $null=New-AegisLayoutPlan @($a) @{Left=2147483640;Top=0;Width=100;Height=100} (Options-LV) } catch { $overflow=$true }
    $o=Options-LV;$o.Mode='Cascade'
    try { $null=New-AegisLayoutPlan @($a) $area $o } catch { $badMode=$true }
    Assert-LV ($duplicate -and $overflow -and $badMode) 'Malformed geometry accepted'
}
Case-LV 'LV23' 'Mixed tiers and groups maintain geometry across 75 seeded cases' {
    $rng=New-Object System.Random 31011
    for ($case=0;$case -lt 75;$case++) {
        $ws=New-Object System.Collections.ArrayList;$count=1+($case%24)
        for ($i=0;$i -lt $count;$i++) {
            $w=Window-LV ('w'+$i) ($rng.Next(80,550)) ($rng.Next(50,350))
            $w.Tier=1+($i%3);$w.GroupId='g'+($i%2);$w.Priority=($i%4)*10;$w.LayoutOrder=$i
            $w.GroupPriority=($i%2)*10;$w.GroupWeight=1+($i%2)
            if (($i%4) -eq 0) { $w.SizeMode='Fill' }
            [void]$ws.Add($w)
        }
        $bounds=@{Left=-1920;Top=-50;Width=1920;Height=1080};$o=Options-LV;$o.Margin=8;$o.Gap=8
        $p=New-AegisLayoutPlan $ws.ToArray() $bounds $o
        CheckGeometry-LV $p $bounds $count
        $groups=@($p.Zones | Where-Object {$_.Level -eq 'Group'}).Count
        Assert-LV ($p.Counters.CandidateCount -le $groups*$o.MaxCandidates) 'Candidate work bound violated'
    }
}
Case-LV 'LV24' 'Nonresizable preferred size is reported as preserved' {
    $a=Window-LV 'a' 320 240;$a.Resizable=$false;$a.SizeMode='Preferred';$a.DesiredWidth=500;$a.DesiredHeight=400
    $p=New-AegisLayoutPlan @($a) $area (Options-LV)
    Assert-LV ($p.Items[0].Status -eq 'Planned' -and $p.Items[0].Width -eq 320 -and $p.Items[0].Height -eq 240 -and -not $p.Items[0].Resize -and $p.Items[0].Reason -eq 'NonResizableSizePreserved') 'Nonresizable resize attempted'
}

$failed=@($script:layoutResults.ToArray() | Where-Object {$_.Status -eq 'FAIL'}).Count
$sha=[System.Security.Cryptography.SHA256]::Create()
try { $sourceHash=[BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes((Resolve-Path $SourcePath).Path))).Replace('-','').ToLowerInvariant() }
finally { $sha.Clear() }
$report=@{SourceSha256=$sourceHash;SourceFile=(Split-Path -Leaf $SourcePath);Suite='Aegis v4 actual pure planner';Passed=$script:layoutResults.Count-$failed;Failed=$failed;Total=$script:layoutResults.Count;PowerShellVersion=$PSVersionTable.PSVersion.ToString();ActualWindowsIntegration='NOT_RUN';ActualPowerShell2=$(if($PSVersionTable.PSVersion.Major -eq 2){'RUN'}else{'NOT_RUN'});Cases=$script:layoutResults.ToArray()}
if ($OutputPath -ne '') { $report | Export-Clixml -Path $OutputPath }
foreach ($result in $script:layoutResults) { Write-Host ($result.Id+' '+$result.Status+' '+$result.Name+' '+$result.Detail) }
Write-Host ('Layout: '+$report.Passed+'/'+$report.Total+' passed')
if ($failed -ne 0) { throw 'Layout verification failed' }
