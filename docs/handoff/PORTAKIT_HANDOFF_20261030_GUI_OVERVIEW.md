# PortaKit — GUI read-only overview handoff (2026-10-30)

This work is in the PUBLIC repository https://github.com/greatgc-flow/portakit, based on main `b9f6d6e22f47998eebf89ce5163268a109c3c1fa` after merged offline-ready NO_OP fix #45. Always fetch latest remote main SHA, open PRs and Windows Actions before resuming.

## Scope
- Optional Tk window in `scripts/toolkit_picker.py` opens only on user click, using local root, optional user-held vendor original archive folder, optional logical MiB budget and opt-in pinned-only subset. No install/apply or network.
- Pure `scripts/kit_overview.py` combines `scripts/offline_ready.py` (saved pin/current installed-status and original SHA preflight) and `scripts/kit_footprint.py` (logical bytes of *existing managed* pinned tool folders). It runs on the current in-memory draft so GUI preview never writes user kit JSON.
- Missing original files, blocked managed state, 7zip/7zr prerequisites and research/plugin exclusion remain visible. Unknown physical disk and missing/pending tool sizes are NEVER estimated or treated as zero.
- No catalog, vendor binaries, file overwrite, service/driver/registry/PATH, core installer or public Release changes.

## Review and verification
- New 10 headless cases `tests/test_kit_overview.py`, Windows Python 3.11 and 3.14 matrix and AST smoke. No real GUI or vendor processes involved.
- `docs/PERSONAL_KITS.md`, `docs/GUI_PICKER_ACCEPTANCE_20261030.md` updated. **HUMAN_NOT_VERIFIED**: live Tk focus/layout/IME/screen reader/100-200% DPI, vendor legal/EDR, offline file transfer, production readiness.
- After green PR CI: squash merge, re-read main HEAD, confirm post-merge Windows CI. Keep open #27/#36/#25 gates. No release.
