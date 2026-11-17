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
    foreach ($tier in @(3,2,1)) {
        $tierEntries=@($eligible | Where-Object {$_.Tier -eq $tier} | Sort-Object @{Expression='GroupPriority';Descending=$true},GroupId,@{Expression='Priority';Descending=$true},LayoutOrder,Id)
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
            $orderedGroups=@($groupList.ToArray() | Sort-Object @{Expression='Priority';Descending=$true},Id)
            $activeGroups=New-Object System.Collections.ArrayList; [long]$groupMinimumSum=0
            foreach ($group in $orderedGroups) {
                $group.Entries=@($group.Entries.ToArray() | Sort-Object @{Expression='Priority';Descending=$true},LayoutOrder,Id)
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
