<#
.SYNOPSIS
  One-run four-Office WinMerge acceptance + SHA-256 evidence package.
.DESCRIPTION
  Windows PowerShell 2.0/5.x compatible. Does not uninstall/update applications
  or change global Windows settings. If WinMerge is not managed yet, install
  its pinned recommended profile. If managed, configure only (no base re-download).
  NEVER auto-update an existing version; report its pin mismatch instead.
  Invoke the Office acceptance using separate powershell.exe to isolate exit 2.
  Keeps all evidence locally; never uploads or publishes it.
.PARAMETER Root
  PortaKit-managed root. Default is ../portable relative to this script's repo.
.PARAMETER EvidenceDir
  Must not exist. Default: ../office4-evidence-<unique timestamp>.
.PARAMETER ProbeOnly
  Check COM registration without starting Office; always NOT_VERIFIED (exit 2).
.PARAMETER Python
  Command or path to Python 3.11+ (default python).
.PARAMETER TimeoutSeconds
  Per-Office comparison timeout in seconds, 10 through 600.
.NOTES
  Before real comparisons CLOSE all open Office documents. Office automation may
  attach to an existing desktop process, and the acceptance harness calls Quit.
  Run only on a disposable desktop, never a MES server.
#>
param(
    [string]$Root = "",
    [string]$EvidenceDir = "",
    [string]$Python = "python",
    [int]$TimeoutSeconds = 120,
    [switch]$ProbeOnly
)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $scriptDir
if ($Root -eq "") { $Root = Join-Path $repo "portable" }
if ($EvidenceDir -eq "") {
    $stamp = (Get-Date -Format "yyyyMMdd-HHmmss")
    $suffix = [Guid]::NewGuid().ToString("N").Substring(0,8)
    $EvidenceDir = Join-Path $repo ("office4-evidence-" + $stamp + "-" + $suffix)
}
$rootPath = [System.IO.Path]::GetFullPath($Root)
$evidencePath = [System.IO.Path]::GetFullPath($EvidenceDir)
$zipPath = $evidencePath + ".zip"
$transcriptPath = $evidencePath + ".runner.log"
$transcript = $false
$result = 1
$runStarted = $false
try {
    if ($TimeoutSeconds -lt 10 -or $TimeoutSeconds -gt 600) {
        throw "TimeoutSeconds must be between 10 and 600"
    }
    foreach ($item in @($evidencePath, $zipPath, $transcriptPath, ($zipPath + ".sha256.txt"))) {
        if (Test-Path -LiteralPath $item) {
            throw "Refusing to overwrite existing evidence: $item"
        }
    }
    Start-Transcript -Path $transcriptPath -Force | Out-Null
    $transcript = $true
    Write-Host "PORTAKIT OFFICE4 - local acceptance runner"
    Write-Host "REPO: $repo"
    Write-Host "ROOT: $rootPath"
    Write-Host "EVIDENCE: $evidencePath"
    Write-Host "REQUIREMENTS: Python 3.11+, licensed Office desktop, interactive Windows session"
    Write-Host "NOTICE: close all open Office documents before running actual integration"
    Write-Host "NO AUTO-UPDATE / NO UPLOAD / NO GLOBAL SYSTEM CHANGES"
    $toolPath = Join-Path $repo "portakit.py"
    if (-not (Test-Path -LiteralPath $toolPath -PathType Leaf)) {
        throw "portakit.py not found: $toolPath"
    }
    $exe = Join-Path (Join-Path $rootPath "winmerge") "WinMergeU.exe"
    $statePath = Join-Path $rootPath ".portakit-state.json"
    if ((Test-Path -LiteralPath $statePath) -or (Test-Path -LiteralPath $exe)) {
        Write-Host "CONFIGURE: managed WinMerge only; stale catalog pins require manual update"
        & $Python "-I" $toolPath "--root" $rootPath "configure" "winmerge"
    }
    else {
        Write-Host "INSTALL: pinned WinMerge recommended profile (first installation)"
        & $Python "-I" $toolPath "--root" $rootPath "install" "winmerge" "--recommended"
    }
    if ($LASTEXITCODE -ne 0) { throw "PortaKit installation/configuration failed: exit $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "WinMergeU.exe missing after configured installation"
    }
    $accept = Join-Path $scriptDir "WinMerge-OfficeAcceptance.ps1"
    $runStarted = $true
    if ($ProbeOnly) {
        Write-Host "MODE: prereq-only registration; all statuses NOT_VERIFIED"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $accept -WinMergeExe $exe -EvidenceDir $evidencePath -TimeoutSeconds $TimeoutSeconds -ProbeOnly
    }
    else {
        Write-Host "MODE: four real Office COM + WinMerge comparisons"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $accept -WinMergeExe $exe -EvidenceDir $evidencePath -TimeoutSeconds $TimeoutSeconds
    }
    $result = [int]$LASTEXITCODE
    Write-Host "ACCEPTANCE EXIT: $result (0 PASS, 1 FAIL, 2 NOT_VERIFIED)"
}
catch {
    Write-Host ("RUNNER FAIL: " + $_.Exception.Message)
    $result = 1
}
finally {
    if ($transcript) {
        try { Stop-Transcript | Out-Null } catch {}
    }
    if (Test-Path -LiteralPath $evidencePath -PathType Container) {
        try {
            Copy-Item -LiteralPath $transcriptPath -Destination (Join-Path $evidencePath "runner-console.log")
        } catch {
            Write-Host ("EVIDENCE WARNING: runner transcript copy failed: " + $_.Exception.Message)
            $result = 1
        }
    }
    else {
        # Even if the pre-check stops before Office runs, preserve error evidence.
        try {
            New-Item -ItemType Directory -Path $evidencePath -ErrorAction Stop | Out-Null
            if (Test-Path -LiteralPath $transcriptPath) {
                Copy-Item -LiteralPath $transcriptPath -Destination (Join-Path $evidencePath "runner-console.log")
            }
        } catch {
            Write-Host ("EVIDENCE WARNING: unable to prepare error evidence: " + $_.Exception.Message)
            $result = 1
        }
    }
}
try {
    Write-Host "PACKAGING: synthetic fixtures, CSV, reports and console transcripts"
    $packer = Join-Path $scriptDir "package_office_evidence.py"
    & $Python "-I" $packer "--evidence" $evidencePath "--zip" $zipPath "--exit-code" $result
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PACKAGING FAILED; source evidence remains at $evidencePath"
        exit 1
    }
    Write-Host "ZIP: $zipPath"
    Write-Host "SHA256: $zipPath.sha256.txt"
    # Validate the sealed ZIP independently, including manifest entries,
    # application results, and the extracted semantic HTML proof if PASS.
    $verifier = Join-Path $scriptDir "verify_office_evidence.py"
    & $Python "-I" $verifier "--zip" $zipPath
    if ($LASTEXITCODE -ne 0) {
        throw "INDEPENDENT_VERIFICATION_FAILED: packaged Office evidence is not valid"
    }
    Write-Host "EVIDENCE VALIDATION: PASS (archive integrity only; not Office status)"
}
catch {
    Write-Host ("PACKAGING FAILED: " + $_.Exception.Message)
    exit 1
}
Write-Host "FINAL EXIT: $result"
exit $result
