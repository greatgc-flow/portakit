# PortaKit — 2026-10-30 personal offline asset manifest handoff

Check actual GitHub `greatgc-flow/portakit` **main latest SHA**, open PRs/issues and Actions first; baseline for this branch was `642570293ad98a1ea12db073bdd135a6b29169d0` including optional GUI picker PR #31. Never trust this historical baseline over newer main.

- New optional utility: `scripts/offline_assets.py` for list / export / verify original SHA-pinned vendor asset metadata for a user's existing personal kit. No downloader, no ZIP bundling or third-party binaries, no new install, no OS edits.
- New docs: `docs/OFFLINE_ASSETS.md`, 9 independent tests `tests/test_offline_assets.py`, Windows nonmutating CLI smoke; README/personal kit guide/backlog updated.
- `list` reads current catalog + kit; `export` creates an exactly mirrored new-only metadata JSON and log; `verify` invokes unchanged `sets.verify_offline_assets` for every pinned item (not research, not native built-ins) and emits exact local SHA PASS or failure evidence, no partial installs.
- Updated vendor package SHA, software license, distribution/airgap transfer, effective OS compatibility and independent approval remain gates. No `catalog.json`/core/toolset/personal-kit schema or pin changes in this branch.
- Start next chat with `docs/PERSONAL_KITS.md`, `docs/OFFLINE_ASSETS.md`, `docs/GUI_PICKER_ACCEPTANCE_20261030.md`, all 2026-10-25 and 2026-10-30 handoffs, read actual latest GitHub PR/Actions and rerun Python 3.11/3.14 full tests. Review PR diff and merge only after green; post-merge main CI required.
- Remaining work: physically approved vendor archives and SHA; true GUI/Office4 acceptance; individual optional editor plug-in selection; license-approved media-packaging/footprint evidence; comprehensive CLI audit logging and secure governance. Do not auto-release or silently activate network protocols.
