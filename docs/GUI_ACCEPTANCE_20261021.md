# Portable GUI user acceptance — safe manual test harness (2026-10-21)

This workflow addresses the **remaining real interactive UI acceptance**, not a replacement for the Windows GitHub Actions smoke. Use **only on a non-production, company-approved Windows workstation** with original pinned PortaKit apps already installed and Python 3.11+. The tester must interpret first-run dialogs and security prompts. It never uploads company files or performs an Internet request.

## Commands

```powershell
# Read-only evaluation of managed app directory/pin/EXE; writes a NEW,
# independent evidence folder and synthetic test files, but never opens a GUI.
.\scripts\GuiAcceptance.cmd --tools everything grepwin 7zip

# Interactive HUMAN test without automatically starting any executable:
# Manually open vendor apps only if authorized, then enter pass/fail/skip.
.\scripts\GuiAcceptance.cmd --review --tools grepwin 7zip

# Explicitly launch approved GUI apps, then enter pass/fail/skip in console:
.\scripts\GuiAcceptance.cmd --review --launch --tools grepwin 7zip

# EXTRA consent required for Everything: launch may request admin/service,
# perform local NTFS indexing, create app settings, or enable network features
# if user chooses vendor prompts. Do not accept any such prompts by default.
.\scripts\GuiAcceptance.cmd --review --launch --allow-everything-first-run --tools everything

# Customize locations; EVIDENCE must NOT exist and must remain outside ROOT.
.\scripts\GuiAcceptance.cmd --root "D:\Portable" --evidence "D:\Evidence\GuiQA-001" --tools grepwin
```

**Status truth contract:** ordinary probe **never PASS** even if all binaries exist; it returns **2 NOT_VERIFIED** and a local `results.csv`, `result.json`, and `console.log`. Manual review may return **0 HUMAN_ATTESTED_PASS** *only* when an operator explicitly enters `pass` for every requested GUI and has visually completed its checklist. Automated regression CI cannot claim the UI worked. **1 FAIL** for missing pin/EXE, bad state, human failure or actual GUI-launch error. `skip` produces 2. A human PASS is a signed-off observation, not machine GUI automation proof.

**Evidence & privacy:** all fixtures are synthetic and written exclusively to the new evidence folder. For every tool, record the exact managed pin/version and SHA-256 **of installed executable bytes** (different from SHA-256 of vendor ZIP) and Everything's named service presence before/after. Every displayed line from this Python harness is emitted unmodified to the local `console.log`. No screenshots, process lists, IP addresses or user documents are secretly uploaded; if screenshots are necessary, place reviewed/censored screenshots in the evidence directory manually. The harness neither kills launched GUI apps nor changes service/registry/permissions/index. The vendor app itself may have user-selected first-run effects: use a disposable workstation.

## Real GUI verification matrix

| Tool | Synthetic tasks to perform | Must NOT be claimed without confirmation |
| --- | --- | --- |
| Everything 1.4 portable | Confirm the user explicitly declines service/UAC; `Tools > Options > Indexes > Folders` select **only** the synthetic `fixtures` directory, check `PK-GUI-12345` appears, close and inspect vendor settings/database location | Automatic all-NTFS indexing, Everything Service install, system startup, HTTP/ETP listener, enterprise-wide exposure of filenames; default NTFS indexing may be enabled, so check before proceeding |
| grepWin 2.1 portable | Select evidence/fixtures folder only; search regex `PK-GUI-[0-9]+` in UTF-8 and UTF-16 fixture; confirm `nonmatching-utf8.txt` does not match, leave `Replace` untouched | File replacement against production logs, unapproved context-menu changes, unsolicited external connections |
| Full 7-Zip 26.04 | Open `7zFM.exe`; inspect synthetic fixture; create a ZIP **inside evidence folder** and reopen/test; optionally confirm a 7z archive | New .zip/.7z file associations, implicit registry writes, administrator launch or Explorer context menu success |

### Everything 1.4 caveats

Upstream [indexing guidance](https://www.voidtools.com/support/everything/everything_service/) explicitly states folder-only indexing can avoid the service but is slower than direct NTFS indexing. [Default NTFS index behavior](https://www.voidtools.com/support/everything/indexes/) may traverse entire local fixed NTFS volumes. Do **not** blindly accept first-run dialogs on production, even though its pinned ZIP installation itself does not launch the GUI. [HTTP server](https://www.voidtools.com/support/everything/http/) can expose indexed file names/downloads if enabled, so verify it is disabled. Everything Server 1.5 enterprise functionality has a distinct commercial license; **not included** here.

## Acceptance roles and gates

- **CI:** validates safe argument parsing, no-launch by default, root/pin checks, duplicate/symlink detection, no evidence overwrite, exact stdout log, and explicit human-only PASS. CI **must NOT** run GUI launches.
- **Corporate workstation operator:** with local IT approval, review vendor dialogs; manually verify search/archives using only synthetic evidence fixtures; enter result. If anything requires elevated access, additional service or whole-drive indexing, stop and record `skip` or `fail`.
- **Release manager:** require `result.json`, `results.csv`, and `console.log` plus human-reviewed screenshots (if policy allows), pinned app identity and environment notes. Do not infer actual GUI acceptance from a headless GitHub Actions job.

Use [research licensing intake](../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json) separately before selecting TCPView or PsPing; neither is included in GUI validation or the 17 SHA-pinned installable apps.
