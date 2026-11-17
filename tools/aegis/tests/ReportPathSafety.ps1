# Windows PowerShell 2 / CLR2 report-path protection for development harnesses.
# Load this helper from the harness package, never from a supplied product path.
function Get-AegisHarnessFilePath {
    param([string]$Path)
    if ([string]::IsNullOrEmpty($Path) -or $Path -match '[*?\[\]]') { throw 'ReportPathMustBeLiteral: use a nonempty file path without wildcard characters.' }
    $leaf=Split-Path -Path $Path -Leaf
    $parent=Split-Path -Path $Path -Parent
    if ([string]::IsNullOrEmpty($leaf)) { throw 'ReportPathMustNameFile: a directory is not a report file.' }
    if ([string]::IsNullOrEmpty($parent)) { $parent='.' }
    # Resolve against PowerShell's location/drive, not the process working directory.
    $resolved=Resolve-Path -LiteralPath $parent -ErrorAction Stop
    if ($resolved.Provider.Name -ne 'FileSystem') { throw 'ReportPathMustBeFileSystem: only file-system paths are supported.' }
    return [IO.Path]::GetFullPath([IO.Path]::Combine($resolved.ProviderPath,$leaf))
}

function Test-AegisHarnessSameFileBytes {
    param([string]$First,[string]$Second)
    if (-not [IO.File]::Exists($First) -or -not [IO.File]::Exists($Second)) { return $false }
    if ((New-Object IO.FileInfo $First).Length -ne (New-Object IO.FileInfo $Second).Length) { return $false }
    $firstStream=$null;$secondStream=$null
    try {
        $firstStream=[IO.File]::Open($First,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $secondStream=[IO.File]::Open($Second,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ($firstStream.Length -ne $secondStream.Length) { return $false }
        [byte[]]$firstBuffer=New-Object 'byte[]' 4096
        [byte[]]$secondBuffer=New-Object 'byte[]' 4096
        [long]$remaining=$firstStream.Length
        while ($remaining -gt 0) {
            [int]$wanted=[Math]::Min([long]4096,$remaining)
            [int]$offset=0
            while ($offset -lt $wanted) {
                $read=$firstStream.Read($firstBuffer,$offset,$wanted-$offset)
                if ($read -le 0) { throw 'ReportPathInputChanged: a protected file changed during comparison.' }
                $offset+=$read
            }
            $offset=0
            while ($offset -lt $wanted) {
                $read=$secondStream.Read($secondBuffer,$offset,$wanted-$offset)
                if ($read -le 0) { throw 'ReportPathInputChanged: a protected file changed during comparison.' }
                $offset+=$read
            }
            if ([Convert]::ToBase64String($firstBuffer,0,$wanted) -cne [Convert]::ToBase64String($secondBuffer,0,$wanted)) { return $false }
            $remaining-=$wanted
        }
        return $true
    } finally {
        if ($null -ne $firstStream) { $firstStream.Close() }
        if ($null -ne $secondStream) { $secondStream.Close() }
    }
}

function Resolve-AegisHarnessReportPath {
    param([string]$Path,[string]$ProductPath,[string]$HarnessPath,[string]$PackageRoot,[string[]]$AdditionalProtectedPaths=@())
    if ([string]::IsNullOrEmpty($Path)) { return '' }
    $output=Get-AegisHarnessFilePath $Path
    if ([IO.Directory]::Exists($output)) { throw 'ReportPathMustNameFile: a directory is not a report file.' }
    $inputs=New-Object Collections.ArrayList
    foreach ($inputPath in @($ProductPath,$HarnessPath)) {
        if (-not [string]::IsNullOrEmpty($inputPath)) { [void]$inputs.Add((Get-AegisHarnessFilePath $inputPath)) }
    }
    if ($null -ne $AdditionalProtectedPaths) {
        foreach ($inputPath in $AdditionalProtectedPaths) {
            if (-not [string]::IsNullOrEmpty($inputPath)) { [void]$inputs.Add((Get-AegisHarnessFilePath $inputPath)) }
        }
    }
    $package=(Resolve-Path -LiteralPath $PackageRoot -ErrorAction Stop).ProviderPath
    $product=Get-AegisHarnessFilePath $ProductPath
    [void]$inputs.Add((Join-Path (Split-Path -Parent $product) 'Aegis.Processes.csv'))
    # These are bounded, nonrecursive package-directory inventories. No code is
    # loaded from ProductPath's directory; all auxiliary scripts are protected.
    foreach ($directory in @($package,(Join-Path $package 'tests'),(Join-Path $package 'verification'),(Join-Path $package 'parts'),(Join-Path (Join-Path $package 'verification') 'baseline'))) {
        if (-not [IO.Directory]::Exists($directory)) { continue }
        foreach ($pattern in @('*.ps1','*.csv')) {
            foreach ($inputPath in [IO.Directory]::GetFiles($directory,$pattern)) { [void]$inputs.Add($inputPath) }
        }
    }
    $seen=@{}
    foreach ($inputPath in $inputs) {
        if ($seen.ContainsKey($inputPath)) { continue }
        $seen[$inputPath]=$true
        if ([string]::Equals($output,$inputPath,[StringComparison]::OrdinalIgnoreCase)) { throw ('ReportPathProtectedInput: '+$inputPath) }
        # Existing identical bytes also protect hard-link/short-name aliases and
        # input copies without a native API or a FIPS-sensitive hash dependency.
        # This is a pre-run accident guard, not a concurrent filesystem lock.
        if (Test-AegisHarnessSameFileBytes $output $inputPath) { throw ('ReportPathProtectedInputBytes: '+$inputPath) }
    }
    return $output
}
