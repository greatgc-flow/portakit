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
