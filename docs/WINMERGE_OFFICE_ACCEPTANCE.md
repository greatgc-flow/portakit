# WinMerge runtime and Microsoft Office acceptance

This project separates three independent gates. Do not claim an Office integration PASS from the CI-only checks.

| Gate | Validation | Required environment |
| --- | --- | --- |
| A: bundle | SHA-pinned ZIP, Excel/Word/PowerPoint/Visio plugin scriptlets, portable WinMerge.ini | Hosted Windows CI |
| B: executable | Real WinMergeU.exe compares identical/different text (exit 0/1), produces two HTML reports | Hosted Windows CI |
| C: Office COM | Real Excel/Word/PowerPoint/Visio content comparison via installed plugin + Office COM, with HTML report evidence | Interactive licensed Windows desktop |
| D: GUI | Human checks document rendering, automatic selection, dialogs, negative cases, semantic correctness | Target user PC |

Official references: [WinMerge command line](https://manual.winmerge.org/en/Command_line.html) and [WinMerge plugins and Office dependencies](https://manual.winmerge.org/en/Plugins.html).

## Gate B — automated

The live Windows PR workflow installs the SHA-verified WinMerge archive in a temporary root and invokes scripts/WinMerge-RuntimeSmoke.ps1. The script checks:
- Same UTF-8 text on both sides -> exit 0, nonempty HTML report.
- Different UTF-8 text on each side -> exit 1, nonempty HTML report.
- A bounded per-comparison timeout; no unbounded GUI hangs.
- A complete console transcript, synthetic source files and HTML report files saved together.

The workflow uploads the artifact **portakit-winmerge-runtime-evidence** for 7 days. Gate B uses the /noprefs option and changes no global user settings.

Reproduce locally with Windows PowerShell 2.0 or 5.x (use a disposable root and a new evidence folder):

    python -I portakit.py install winmerge --recommended
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\WinMerge-RuntimeSmoke.ps1 -WinMergeExe ".\portable\winmerge\WinMergeU.exe" -EvidenceDir "C:\Temp\portakit-wm-smoke-001"

The EvidenceDir must **not exist** before running; the script refuses to overwrite existing data.

## One-command four-app acceptance and self-contained ZIP

From a checkout of this repository on a dedicated Windows test desktop (PowerShell 2.x or 5.x, Python 3.11+):

    scripts\Run-WinMerge-Office4.cmd -ProbeOnly
    scripts\Run-WinMerge-Office4.cmd

The first command is safe prerequisite-only inspection and returns `2` = NOT VERIFIED even if all COM ProgIDs are registered. The second runs real synthetic comparisons for **Excel, Word, PowerPoint and Visio** where installed. Close all open Office documents first because some COM servers may reuse a running Office process. Do **not** use this on production MES servers. Lack of a corresponding licensed Office app remains NOT VERIFIED, not a test pass.

The runner automatically performs a pinned recommended WinMerge install if no managed installation exists, otherwise `configure winmerge` for current catalog pins; it refuses to auto-update a mismatched existing version. It never removes the installation. Optional `-Root`, `-EvidenceDir`, `-Python` and `-TimeoutSeconds` parameters are passed through the launcher. It does not alter PATH/registry or publish anything.

Outputs are created only under a **new** evidence folder and adjacent files:

- `office4-evidence-<unique>/` - all synthetic documents, report HTML, `results.csv`, child `console.log`, parent `runner-console.log`.
- `office4-evidence-<unique>.zip` - self-contained copy of the above plus `manifest.json` with SHA-256 of every included file and the real exit status.
- `office4-evidence-<unique>.zip.sha256.txt` - independent hash of the ZIP.
- `office4-evidence-<unique>.runner.log` - additional plain-text runner transcript.

The packager uses Python standard library only, refuses to overwrite existing files, and rejects evidence symlinks/junctions. Do not upload any locally generated Office files or logs publicly without inspection.

**Release gate**: `0` only if both actual WinMerge comparisons (same/different) succeed and the HTML report includes distinct `BASELINE`/`DIFFERENT` content markers, not merely ZIP binary differences. Exit `1` = FAIL; exit `2` = NOT VERIFIED. Hosted CI verifies the one-run `-ProbeOnly` path with an actual ZIP/hash/manifest but cannot certify Office integration.

## Independent evidence verification and final PASS gate

After running `scripts\Run-WinMerge-Office4.cmd`, verify the local ZIP and sidecar independently, with no Office installation required:

    python -I scripts/verify_office_evidence.py --zip "office4-evidence-....zip"
    python -I scripts/verify_office_evidence.py --zip "office4-evidence-....zip" --require-pass

The first command returns zero if the ZIP, SHA-256 sidecar, manifest entries, every included file checksum, four-app CSV and every claimed successful application's synthetic semantic HTML markers are internally consistent. A result `"verified": true, "office_runtime": "NOT_VERIFIED"` **does not** mean actual Office integration passed. The second command is the strict release gate: **exit 0** for verified **four-app PASS only**, **exit 2** for valid but incomplete/failed results, **exit 1** for invalid/tampered evidence. Both scripts are read-only and Python standard-library-only. The launcher itself automatically runs the first verifier after creating the ZIP.

Verification detects corrupted data, a false PASS manifest with fewer than four PASS rows, absent synthetic fixtures, missing HTML reports, or diff HTML without BASELINE/DIFFERENT evidence. It cannot prove that all embedded content was generated honestly by Office; for that, retain the original CI process logs and complete local human-in-loop GUI inspection. Do not publish any business documents or private workstation logs.

## Gate C0 — safe four-application prerequisite inventory

Run this before Office automation on a target PC, or use the CI-hosted run's `portakit-winmerge-office-prerequisites` artifact:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\WinMerge-OfficeAcceptance.ps1 -WinMergeExe ".\portable\winmerge\WinMergeU.exe" -EvidenceDir "C:\Temp\portakit-office-probe-001" -ProbeOnly

`-ProbeOnly` checks whether the four Office COM ProgIDs (Excel, Word, PowerPoint, Visio) are **registered** without starting an Office application or opening documents. It writes a console transcript and four rows in `results.csv` and **always returns exit code 2 (NOT_VERIFIED)** after a successful probe. Even a registered ProgID does not prove Office activation, licensing or WinMerge comparison correctness. An invalid input or filesystem error returns 1 instead.

In the CI workflow, the four original SHA-pinned vendor scriptlets are also inspected to assert their respective `.xlsx`, `.docx`, `.pptx` and `.vsdx` extension filters and `get_PluginIsAutomatic() == true` declarations, in addition to the existing plugin presence and INI checks. This is static package validation, **not** Office runtime certification.

## Gate C — Office COM integration on the target desktop

**Office applications are not present or licensed by default in the hosted CI.** These plugins invoke desktop Office COM automation and require the matching Excel, Word, PowerPoint or Visio application. They extract textual data and are not full formatting comparison engines. Use only disposable test documents, never actual MES or confidential customer files.

Prerequisites: interactive Windows desktop, installed and activated Office, PortaKit-managed recommended WinMerge (or run configure winmerge), Windows PowerShell 2.0/5.x and sufficient rights to start the relevant Office COM application.

Excel-only execution:

    python -I portakit.py configure winmerge
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\WinMerge-OfficeAcceptance.ps1 -WinMergeExe ".\portable\winmerge\WinMergeU.exe" -EvidenceDir "C:\Temp\portakit-office-001" -Applications Excel

All four applications (when licensed and installed):

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\WinMerge-OfficeAcceptance.ps1 -WinMergeExe ".\portable\winmerge\WinMergeU.exe" -EvidenceDir "C:\Temp\portakit-office-002" -Applications Excel,Word,PowerPoint,Visio

The script creates synthetic left/right files and an identical copy for each selected Office type; the actual WinMerge process runs with /noninteractive /enableexitcode /or and its portable /inifile. It checks identical exit 0, different exit 1 and HTML report creation.

Evidence output resides in the newly created directory: console.log is a transcript of screen output; results.csv has per-program statuses; each app folder has the generated fixtures and HTML reports.

Exit codes:
- **0**: all requested Office comparisons and reports passed.
- **1**: one or more generated documents/comparisons failed; diagnose from transcript.
- **2**: at least one prerequisite unavailable (NOT VERIFIED). This is not success.

Activation dialogs, Office versions, 32/64-bit mismatches, and COM SaveAs method differences may affect real results. Capture the evidence and evaluate on the actual workstation. The script does not install Microsoft Office.

## Gate D — manual GUI inspection

Open WinMerge normally and compare the synthetic pairs created by Gate C. Check that automatic unpacking and correct plugin selection work, semantic content differences appear, formatting-only differences behave as documented, and no unexpected dialogs or Office processes remain. Note WinMerge and Office versions. Record missing dependencies as NOT VERIFIED rather than PASS.

**Release gate:** If Gate C and D have not been executed successfully, state only that Office scriptlets are installed and enabled; real Office integration remains unverified. A successful Gate B does not justify a release claim for Office support.
