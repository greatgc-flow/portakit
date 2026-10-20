<#
.SYNOPSIS
  Verify WinMerge's Office COM unpacker plugins with disposable documents.

.DESCRIPTION
  Windows PowerShell 2.0/5.x-compatible acceptance harness.
  Requires an interactive Windows desktop, PortaKit recommended WinMerge and
  the corresponding Microsoft Office applications. No installation or registry
  edits are performed. All generated Office documents contain synthetic values.

  The terminal text is copied verbatim to console.log by Start-Transcript.
  Results are also saved in results.csv, alongside HTML reports and fixtures.

  Exit: 0 = every requested Office comparison verified; 1 = failed test;
        2 = one or more prerequisites unavailable (NOT VERIFIED).
.PARAMETER WinMergeExe
  WinMergeU.exe installed by PortaKit, usually portable\winmerge\WinMergeU.exe.
.PARAMETER EvidenceDir
  NEW directory for all output; refuse existing directories to avoid data loss.
.PARAMETER Applications
  Optional Office apps: Excel, Word, PowerPoint, Visio.
.PARAMETER TimeoutSeconds
  Per-comparison timeout (default 120 seconds).
.PARAMETER ProbeOnly
  Inspect Office COM registration only. Does not create COM objects or open Office.
  Returns exit 2 (NOT_VERIFIED) even when all four registrations exist.
.NOTES
  Only use with disposable documents. Do not test untrusted Office files or run
  this on servers. Requires actual Office COM and an interactive session.
#>
param(
    [Parameter(Mandatory=$true)][string]$WinMergeExe,
    [Parameter(Mandatory=$true)][string]$EvidenceDir,
    [string[]]$Applications=@("Excel","Word","PowerPoint","Visio"),
    [int]$TimeoutSeconds=120,
    [switch]$ProbeOnly
)
$ErrorActionPreference = "Stop"
$transcript = $false
$rows = @()
$fail = $false
$skipped = $false

function Release-Com([object]$value) {
    if ($null -ne $value) {
        try {
            if ([System.Runtime.InteropServices.Marshal]::IsComObject($value)) {
                [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($value)
            }
        } catch {}
    }
}

function New-OfficePair([string]$name, [string]$folder) {
    $ext = switch ($name) {
        "Excel" { ".xlsx" }
        "Word" { ".docx" }
        "PowerPoint" { ".pptx" }
        "Visio" { ".vsdx" }
        default { throw "Unknown Office program: $name" }
    }
    $left = Join-Path $folder ("left" + $ext)
    $right = Join-Path $folder ("right" + $ext)
    $app = $null
    $doc = $null
    $part = $null
    try {
        $app = New-Object -ComObject ($name + ".Application") -ErrorAction Stop
        if ($name -eq "Excel") {
            $app.Visible = $false
            $app.DisplayAlerts = $false
            $doc = $app.Workbooks.Add()
            $part = $doc.Worksheets.Item(1)
            $part.Cells.Item(1,1).Value2 = "PortaKit QA"
            $part.Cells.Item(2,1).Value2 = "BASELINE"
            $doc.SaveAs($left,51)
            $part.Cells.Item(2,1).Value2 = "DIFFERENT"
            $doc.SaveAs($right,51)
            $doc.Close($false)
        } elseif ($name -eq "Word") {
            $app.Visible = $false
            $app.DisplayAlerts = 0
            $doc = $app.Documents.Add()
            $doc.Content.Text = "PortaKit QA BASELINE"
            $doc.SaveAs2($left,16)
            $doc.Content.Text = "PortaKit QA DIFFERENT"
            $doc.SaveAs2($right,16)
            $doc.Close(0)
        } elseif ($name -eq "PowerPoint") {
            $app.Visible = 1
            $doc = $app.Presentations.Add()
            $slide = $doc.Slides.Add(1,12)
            $part = $slide.Shapes.AddTextbox(1,30,30,430,60)
            $part.TextFrame.TextRange.Text = "PortaKit QA BASELINE"
            $doc.SaveAs($left,24)
            $part.TextFrame.TextRange.Text = "PortaKit QA DIFFERENT"
            $doc.SaveAs($right,24)
            $doc.Close()
        } elseif ($name -eq "Visio") {
            $doc = $app.Documents.Add("")
            $page = $doc.Pages.Item(1)
            $part = $page.DrawRectangle(1,1,5,4)
            $part.Text = "PortaKit QA BASELINE"
            $doc.SaveAs($left)
            $part.Text = "PortaKit QA DIFFERENT"
            $doc.SaveAs($right)
            $doc.Close()
        }
        if (-not (Test-Path -LiteralPath $left -PathType Leaf) -or
            -not (Test-Path -LiteralPath $right -PathType Leaf)) {
            throw "Office SaveAs did not produce both disposable documents"
        }
        Copy-Item -LiteralPath $left -Destination (Join-Path $folder ("identical" + $ext))
        return @{ Left=$left; Right=$right; Identical=(Join-Path $folder ("identical" + $ext)) }
    }
    finally {
        try { if ($null -ne $app) { $app.Quit() } } catch {}
        Release-Com $part
        Release-Com $doc
        Release-Com $app
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

function Invoke-OfficeCompare([string]$exe, [string]$left, [string]$right,
                              [string]$report, [int]$seconds, [int]$expected) {
    $ini = Join-Path (Split-Path -Parent $exe) "WinMerge.ini"
    if (-not (Test-Path -LiteralPath $ini -PathType Leaf)) {
        throw "Portable recommended WinMerge.ini missing"
    }
    $argv = @("/noninteractive", "/enableexitcode", "/u",
              "/inifile", ('"' + $ini + '"'),
              ('"' + $left + '"'), ('"' + $right + '"'),
              "/or", ('"' + $report + '"'))
    $proc = Start-Process -FilePath $exe -ArgumentList $argv -PassThru
    try {
        if (-not $proc.WaitForExit($seconds * 1000)) {
            try { $proc.Kill() } catch {}
            throw "TIMEOUT: WinMerge document comparison exceeded $seconds seconds"
        }
        $proc.Refresh()
        $code = $proc.ExitCode
    } finally { $proc.Dispose() }
    if ($code -ne $expected) {
        throw "WinMerge exit code $code (expected $expected)"
    }
    if (-not (Test-Path -LiteralPath $report -PathType Leaf)) {
        throw "WinMerge HTML report missing"
    }
    if ((Get-Item -LiteralPath $report).Length -lt 100) {
        throw "WinMerge HTML report unexpectedly small"
    }
    return $code
}

try {
    if ($TimeoutSeconds -lt 10 -or $TimeoutSeconds -gt 600) {
        throw "TimeoutSeconds must be between 10 and 600"
    }
    $exe = [System.IO.Path]::GetFullPath($WinMergeExe)
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "WinMergeU.exe missing: $exe"
    }
    $outDir = [System.IO.Path]::GetFullPath($EvidenceDir)
    if (Test-Path -LiteralPath $outDir) {
        throw "EvidenceDir already exists; refusing overwrite: $outDir"
    }
    New-Item -ItemType Directory -Path $outDir | Out-Null
    Start-Transcript -Path (Join-Path $outDir "console.log") -Force | Out-Null
    $transcript = $true
    Write-Host "OFFICE ACCEPTANCE: real COM-unpacker WinMerge comparison"
    Write-Host "WINMERGE: $exe"
    Write-Host "EVIDENCE: $outDir"
    Write-Host "WARNING: requires a desktop and installed/licensed Microsoft Office"
    if ($ProbeOnly) {
        Write-Host "MODE: PREREQUISITE PROBE ONLY — NO Office COM execution"
        foreach ($name in $Applications) {
            $progId = switch ($name) {
                "Excel" { "Excel.Application" }
                "Word" { "Word.Application" }
                "PowerPoint" { "PowerPoint.Application" }
                "Visio" { "Visio.Application" }
                default { "" }
            }
            if (-not $progId) { throw "Unknown Applications selection: $name" }
            $registered = $false
            try {
                $registered = ($null -ne [System.Type]::GetTypeFromProgID($progId, $false))
            } catch {
                Write-Host ("COM REGISTRY PROBE ERROR for " + $name + ": " +
                            $_.Exception.Message)
            }
            if ($registered) {
                $detail = "COM registration exists; runtime, activation and plugin NOT VERIFIED"
            } else {
                $detail = "COM registration not found; runtime and plugin NOT VERIFIED"
            }
            Write-Host ("NOT_VERIFIED " + $name + ": " + $detail)
            $rows += New-Object PSObject -Property @{
                Application=$name; Status="NOT_VERIFIED"; Detail=$detail }
        }
        $skipped = $true
    } else {
    foreach ($name in $Applications) {
        $folder = Join-Path $outDir $name
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host ("OFFICE: " + $name)
        $comApp = switch ($name) {
            "Excel" { "Excel.Application" }
            "Word" { "Word.Application" }
            "PowerPoint" { "PowerPoint.Application" }
            "Visio" { "Visio.Application" }
            default { "" }
        }
        if (-not $comApp) {
            throw "Unknown Applications selection: $name"
        }
        # Avoid claiming that missing Office or licensing is a successful test.
        $available = $null
        try { $available = New-Object -ComObject $comApp -ErrorAction Stop }
        catch {
            Write-Host ("NOT_VERIFIED " + $name + ": Office COM unavailable: " + $_.Exception.Message)
            $rows += New-Object PSObject -Property @{
                Application=$name; Status="NOT_VERIFIED"; Detail="Office COM unavailable" }
            $skipped = $true
            continue
        }
        try { $available.Quit() } catch {}
        Release-Com $available

        try {
            $pair = New-OfficePair $name $folder
            Write-Host ("GENERATED " + $pair.Left + " / " + $pair.Right)
            $sameReport = Join-Path $folder "identical.html"
            $diffReport = Join-Path $folder "different.html"
            [void](Invoke-OfficeCompare $exe $pair.Left $pair.Identical $sameReport $TimeoutSeconds 0)
            [void](Invoke-OfficeCompare $exe $pair.Left $pair.Right $diffReport $TimeoutSeconds 1)
            Write-Host ("PASS " + $name + ": identical=0 different=1; reports saved")
            $rows += New-Object PSObject -Property @{
                Application=$name; Status="PASS"; Detail="Actual WinMerge + Office COM comparisons" }
        }
        catch {
            Write-Host ("FAIL " + $name + ": " + $_.Exception.Message)
            $rows += New-Object PSObject -Property @{
                Application=$name; Status="FAIL"; Detail=$_.Exception.Message }
            $fail = $true
        }
    }
    }
}
catch {
    Write-Host ("FAIL PRECHECK: " + $_.Exception.Message)
    $fail = $true
}
finally {
    if ($transcript) {
        if ($rows.Count -gt 0) {
            $rows | Select-Object Application,Status,Detail |
                Export-Csv -Path (Join-Path $outDir "results.csv") -NoTypeInformation -Encoding UTF8
        }
        Stop-Transcript | Out-Null
    }
}
if ($fail) { exit 1 }
if ($skipped -or $rows.Count -eq 0) { exit 2 }
exit 0
