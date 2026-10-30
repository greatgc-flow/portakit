# PortaKit GUI readiness/missing/installed-size — 2026-10-30 handoff

**Repository PUBLIC** `greatgc-flow/portakit`. Branch `feat/gui-readiness-overview-20261030` starts after `main=b9f6d6e22f47998eebf89ce5163268a109c3c1fa` (after fixing fully managed offline NO_OP in #45). Always re-read latest main/PR/CI before claiming merge.

## Scope / SSOT
- GUI `scripts/toolkit_picker.py` adds a separate user-triggered read-only readiness / installed-size window. The current *unsaved* picker selection becomes an ephemeral validated personal kit snapshot; no automatic saved file is created, no tool is installed.
- Source-of-truth remains `my_toolkit.PickerModel.draft` for selected and historically frozen pending items; `offline_ready.assess` for pinned original source, SHA checks, 7zr and unapproved consent; `kit_footprint.audit` for bounded, managed, **installed logical file bytes only**. No duplicated downloader, installer or approval policy.
- Pure `overview_lines` displays select/pin/pending/OS/plugin counts, readiness state and source filenames, blockers, installed measured size and completeness/budget, clearly distinguishing `UNKNOWN` future size from known installed bytes. Optional MiB budget; negative/float input rejected. `--skip-pending` analogue is deliberately **user-set, default off**.
- UI inspection is **read only**. It reads managed installed folders and, only after explicit user action, optional vendor-original archives; no network, changes, executables, services, drivers, global PATH or registry. Reuse existing CLI `OfflineCheck.cmd --out` for requested persistent evidence (GUI does not silently write logs).
- Existing user-owned v1/v2 JSON, source pin locks, six plugin metadata records, 151 research IDs and 19 installable pins remain unchanged.

## Tests and work remaining
- `tests/test_gui_readiness.py`: 11 headless tests for empty kit, missing source, verified synthetic source, research/plugin/OS isolation, previously frozen consent, measurement unknown, no filesystem writes and no installer path.
- Windows Python 3.11 and 3.14 full test matrix, PR review, merge only if green; post-merge CI must be confirmed.
- **HUMAN_NOT_VERIFIED:** real Tk GUI at 850px and 100/150/200% DPI, keyboard, Korean IME, screen reader, actual licensed source archives, enterprise EULA/EDR authorization, correct operator use, network isolation. Do not claim desktop acceptance or product Release.

## Next-step workflow
Run GUI in an approved nonproduction Windows environment; choose pins and optional research/plugin metadata; click `Inspect readiness / size...` and enter an approved managed root and optional original archive directory. Evaluate status and evidence without installation. Actual installation still requires separate `MyToolkit.cmd build --yes --offline-dir ...` and legal approval.

Read `README.md`, `docs/PERSONAL_KITS.md`, `docs/OFFLINE_ASSETS.md`, `docs/GUI_PICKER_ACCEPTANCE_20261030.md`, `scripts/offline_ready.py`, `scripts/kit_footprint.py`, `scripts/toolkit_picker.py`, `tests/test_gui_readiness.py`, latest Actions and this handoff in successor chat. Keep existing open #25/#27/#36 independent, no automatic Release.
