# PortaKit — offline per-plugin delivery continuation (2026-10-30)

**PUBLIC repository** https://github.com/greatgc-flow/portakit. Before this branch, `main=3fe165b414bf70d5d6a25330b98f9b6eb76c558d`, Windows Python 3.11+3.14 CI both 352 PASS and Issue #36 open. **Always recheck live main, PR, issue, Actions, release gates** and prefer newer sources. This document is not proof of enterprise license or site acceptance.

## Work on branch

`feat/approved-offline-editor-plugins-20261030` introduces `scripts/plugin_offline.py`, `tests/test_plugin_offline.py`, `docs/PLUGIN_OFFLINE_APPLY.md`, revised README/personal-kit/backlog and Windows CI fail-closed smoke.

- Preserve original 19 software catalog pins and 151 software selectable IDs, plus six plugin choices in v2 personal kits. Only two nested catalog plugin pins, **ComparePlus 3.0.0 and JsonTools 8.5**, support independent **offline** apply. Four report-only plugins remain completely noninstallable. No files or binaries fetched/repackaged into PUBLIC GitHub.
- Permission-gated `plan` (read only) / `verify --offline-dir` (source SHA read only) / `apply --yes --policy-approved --offline-dir` with optional `--skip-pending` (only pins, never pending).
- Must already have a managed, correct-version/hash Notepad++ host. Refuse unmanaged existing plugin folders, bad receipt state, changed pin or host, absent/invalid SHA original, overly large/reparse/zip traversal, missing required DLL; no automatic setting, registry, network, driver or service changes.
- Under existing toolset+core lock hierarchy: snapshot source to local temp with **second SHA**, extract using existing ZIP security rules, stage on same volume, atomic rename into host plugins, write separate plugin receipts, rollback new plugin folder if receipt fails; partial success from prior selected plugins remains. Console operations mirror their local logs.
- Validate with exact Windows Python 3.11 and 3.14 CI, synthetic cases and no-write CLI gate, scoped reviewed PR before any merge. Recheck post-merge main and link evidence in Issue #36. **HUMAN_NOT_VERIFIED** for actual GUI usability, corporate EDR/OSS approval and vendor license/transfer obligations. Notepad++ application must be closed before installing plugins; the program is not launched.

References: `docs/INDIVIDUAL_EDITOR_PLUGINS.md`, `docs/PLUGIN_OFFLINE_APPLY.md`, `docs/PERSONAL_KITS.md`, `docs/GUI_PICKER_ACCEPTANCE_20261030.md`, core source `portakit.py` and `scripts/toolsets.py`. Next work may include explicit operator checklists for legal/GUI evidence and plugin receipts audit. No automatic Release or installer privilege expansion.
