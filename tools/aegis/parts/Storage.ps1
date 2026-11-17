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
