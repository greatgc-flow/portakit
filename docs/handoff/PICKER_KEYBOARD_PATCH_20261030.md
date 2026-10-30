# PortaKit keyboard-first GUI picker — 2026-10-30

PUBLIC repository: `greatgc-flow/portakit`. Verify latest `main` and PR CI before assuming merged. Starting main was `b6ec274b55a2c570f99d36154e472d79abb9fc03`.

## Scope
- Modify only the existing selection-only `scripts/toolkit_picker.py` for mouse/keyboard efficiency, *without* installing, downloading, running vendor binaries, modifying OS settings or creating new runtime dependencies.
- Retain existing `PickerModel` and `my_toolkit.py` as the authority, with **one source of truth** for JSON kit schema, frozen research status and plugin host dependency.
- Reject entire invalid add/toggle batches before mutation, deduplicate toggles, use `model.toggle(...)` for keyboard/mouse, retain Treeview highlight and focus after rebuilding search results.
- `Ctrl+F`: search focus/select text. `Ctrl+S`: save NEW kit only. `Ctrl+O`: import. Tree-local `Space/Enter`: toggle highlighted, `Ctrl+A`: highlight filtered, `Delete`: remove, `Escape`: clear highlight. Initial focus on search, small inline shortcut guide and result count.
- Keep current 151 research IDs and 6 plugin families metadata-only; pinned software and source approvals remain unchanged. Even if a research candidate becomes pinned later, previously saved pending status remains inert absent explicit re-selection.

## Verification
- Add 5 unit regressions to `tests/test_toolkit_picker.py` for dedup, atomic invalid batch, plugin-host cleanup, and exact shortcut bindings/absence of installer.
- Run complete Windows Python 3.11 and 3.14 suites and isolated `-I` CLI smoke via pull-request CI; verify actual results before merging.
- Human interactive Tk testing still **NOT_VERIFIED** for DPI 100/150/200%, contrast, Korean IME, screen reader, keyboard and user experience. See `docs/GUI_PICKER_ACCEPTANCE_20261030.md`.
- Do not publish a Release, enable service/driver/registry commands, or modify source catalog/toolset/industrial policies.

## Continuation
After CI green, squash merge feature PR to `main`, check main HEAD and post-merge Windows CI. Log any field GUI problems as sanitized reproductions and keep UX issue #27 open until real workstation acceptance completes.
