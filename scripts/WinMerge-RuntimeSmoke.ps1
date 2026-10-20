<#
.SYNOPSIS
  Real WinMergeU.exe comparison and report generation smoke test.
.DESCRIPTION
  Windows PowerShell 2.0 and 5.x compatible. Uses only disposable synthetic
  text files. Console output is mirrored to evidence console.log.
  Existing EvidenceDir is refused, preventing accidental overwrite.
.PARAMETER WinMergeExe
  Full path to the WinMergeU.exe binary.
.PARAMETER EvidenceDir
  Non-existing folder for synthetic fixtures, HTML reports and evidence.
.PARAMETER TimeoutSeconds
  Per-comparison upper bound in seconds (default 60).
.NOTES
  Does NOT test Office COM plugins. That requires licensed desktop Office.
#>
param(
    [Parameter(Mandatory=$true)][string]$WinMergeExe,
    [Parameter(Mandatory=$true)][string]$EvidenceDir,
    [int]$TimeoutSeconds=60
)
$ErrorActionPreference = "Stop"
$transcript = $false
$passed = $false
try {
    if ($TimeoutSeconds -lt 5 -or $TimeoutSeconds -gt 300) {
        throw "TimeoutSeconds must be between 5 and 300"
    }
    $exe = [System.IO.Path]::GetFullPath($WinMergeExe)
    if (-not [System.IO.File]::Exists($exe)) { throw "WinMerge executable not found: $exe" }
    if ([System.IO.Path]::GetFileName($exe).ToLowerInvariant() -ne "winmergeu.exe") {
        throw "Expected WinMergeU.exe, got: $exe"
    }
    $outDir = [System.IO.Path]::GetFullPath($EvidenceDir)
    if (Test-Path -LiteralPath $outDir) {
        throw "EvidenceDir exists, refuse to overwrite: $outDir"
    }
    New-Item -ItemType Directory -Path $outDir -ErrorAction Stop | Out-Null
    Start-Transcript -Path (Join-Path $outDir "console.log") -Force | Out-Null
    $transcript = $true
    Write-Host "TEST: real WinMergeU.exe executable, reports and exit codes"
    Write-Host "EXE: $exe"
    Write-Host "EVIDENCE: $outDir"
    Write-Host "OFFICE_COM: NOT_TESTED"

    $left = Join-Path $outDir "left.txt"
    $right = Join-Path $outDir "right.txt"
    $eol = [string][char]13 + [string][char]10
    $same = "PortaKit comparison acceptance" + $eol + "Common text" + $eol
    [System.IO.File]::WriteAllText($left, $same, [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText($right, $same, [System.Text.Encoding]::UTF8)
    $cases = @(
        @{ Name="identical"; Expected=0; Different=$false },
        @{ Name="different"; Expected=1; Different=$true }
    )
    foreach ($case in $cases) {
        if ($case.Different) {
            [System.IO.File]::WriteAllText(
                $right, ("PortaKit comparison acceptance" + $eol + "Changed text" + $eol),
                [System.Text.Encoding]::UTF8)
        }
        $report = Join-Path $outDir ($case.Name + ".html")
        # Start-Process joins ArgumentList array: explicitly quote all paths.
        $argv = @("/noninteractive", "/enableexitcode", "/noprefs", "/u",
                  ('"' + $left + '"'), ('"' + $right + '"'),
                  "/or", ('"' + $report + '"'))
        Write-Host ("RUN " + $case.Name + ": expecting " + $case.Expected)
        $proc = Start-Process -FilePath $exe -ArgumentList $argv -PassThru
        try {
            if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
                try { $proc.Kill() } catch {}
                throw "TIMEOUT: $($case.Name) exceeded $TimeoutSeconds seconds"
            }
            $proc.Refresh()
            $code = $proc.ExitCode
        }
        finally { $proc.Dispose() }
        Write-Host ("EXIT_CODE " + $case.Name + ": " + $code)
        if ($code -ne $case.Expected) {
            throw "FAILED: $($case.Name) expected $($case.Expected), got $code"
        }
        if (-not (Test-Path -LiteralPath $report -PathType Leaf)) {
            throw "FAILED: HTML report missing: $report"
        }
        $reportInfo = Get-Item -LiteralPath $report
        if ($reportInfo.Length -lt 100) {
            throw "FAILED: report unexpectedly short: $($reportInfo.Length)"
        }
        Write-Host ("PASS " + $case.Name + ": report bytes " + $reportInfo.Length)
    }
    $passed = $true
    Write-Host "RESULT: PASS (real text comparisons + HTML reports)"
}
catch {
    Write-Host ("RESULT: FAIL " + $_.Exception.Message)
}
finally {
    if ($transcript) { Stop-Transcript | Out-Null }
}
if ($passed) { exit 0 } else { exit 1 }
