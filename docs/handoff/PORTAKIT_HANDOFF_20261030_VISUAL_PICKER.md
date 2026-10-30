# PortaKit — 2026-10-30 visual personal toolkit continuation

**Source repository:** https://github.com/greatgc-flow/portakit (PUBLIC).
**Baseline checked before change:** `d729b0553429b4baddaae5d5cdcf2678ed4c498a` on `main`, Windows CI successful. **Always fetch actual latest main HEAD, PRs, issues, Actions before proceeding.** Previous TCPView/PsPing PR #29 had already merged; baseline included 19 SHA-pinned catalog entries, 27 Windows built-in metadata and 105 research-only candidates, total 151 selectable; exact counts must be re-read if updated.

## Scope and files

Branch `feat/personal-kit-visual-picker-20261030`: new optional `scripts/toolkit_picker.py`, `scripts/MyToolkitGUI.cmd`, `tests/test_toolkit_picker.py`, [GUI acceptance](../GUI_PICKER_ACCEPTANCE_20261030.md), [personal kits usage](../PERSONAL_KITS.md), README/backlog, Windows headless parser gate. **Do not confuse candidate branch with merged main**; confirm PR CI and post-merge main CI separately. Existing `catalog.json`, `toolsets.json`, `portakit.py`, `scripts/my_toolkit.py`, `scripts/toolsets.py` and approved download hashes are UNMODIFIED by this branch.

## Technical design

- Standard-library Tk GUI is an **optional visual picker**; imports Tk lazily and has a pure `PickerModel` testable without graphics or a running desktop.
- Search across 151 known IDs with casefold, primary-category and READY / OS_ONLY / RESEARCH_ONLY status filters; multi selection; add/remove visible; existing presets; import original JSON; save NEW personal JSON + exact console-mirrored local log. GUI never downloads/installs or changes registry/services/drivers/PATH. Existing CLI performs separate plan/build.
- When loading an older kit, previously research-only items stay inert even if they were subsequently admitted to the catalog. Explicit de-selection and new selection is required to promote the tool in a new kit; original JSON never overwritten.
- `tests/test_toolkit_picker.py` checks dynamic selection partitions, safe UI model, Unicode/casefold, dedup, pinned state, verified import and missing/unknown/null selections, no install code path, future promotion opt-in.
- **Important unresolved:** real Tk window appearance/keyboard/accessibility/first-run remains HUMAN_NOT_VERIFIED. Windows CI syntax/model checks are not proof of actual GUI desktop acceptance. 6 editor plugin mentions still separately reviewed; vendor-rights compliant offline bundle/size budget/global single-tool command evidence are separate scope.

## Next milestones

1. Confirm GitHub PR #, Windows Python 3.11 and 3.14 test counts and current SHA; fix failing cases; squash-merge green PR only.
2. Reconfirm post-merge main SHA and successful CI; leave GUI manual acceptance open and link guide.
3. Follow [GUI acceptance procedure](../GUI_PICKER_ACCEPTANCE_20261030.md) on approved nonproduction desktop, bring back sanitized evidence.
4. Optionally review plugins individually and create license/manifest-only bundle planner before any redistribution or downloader changes, with clear tests/docs.
5. Protect main branch via repo settings only with separate explicit governance approval; never silently turn on auto Release.
