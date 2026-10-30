# PortaKit — offline personal-kit readiness handoff (2026-10-30)

Current baseline before branch: `abc33be70ea0397d3c1e02543a5c64ae4c37940a` on PUBLIC `greatgc-flow/portakit`. **Always verify latest remote main, PRs, CI and source before assuming merge.** Working feature branch: `feat/offline-readiness-20261030`.

## Purpose

Reduce multi-command airgap checklist friction without creating a new installer, auto-downloader or vendor-binary packager. Read-only `scripts/offline_ready.py` + `scripts/OfflineCheck.cmd` shows exactly which selected pinned originals are needed for currently uninstalled tools, and independently checks every present source with the existing SHA-256 preflight. Users can save an explicit new-only local JSON + identical console evidence log via `--out`.

## Layering

- Source of truth: `scripts/my_toolkit.py` personal v1/v2 strict pin locks, `scripts/toolsets.py` managed installed-state plan and SHA verifier, `scripts/offline_assets.py` original vendor filenames and source-only manifest. No new trust roots or download/install code.
- READINESS only: selected `READY` pins and their local file readiness. Windows OS-only entries always informational. Research candidates/editor plugin choices are never installed by this command; presence blocks preflight by default unless `--skip-pending` explicitly opts into evaluating only the approved pinned subset.
- `check_prerequisite` catches original 7zip/7zr policy; invalid/blocked states prevent readiness. Already-installed matching pinned records require no original archive; installed-file integrity and real application startup remain separate acceptance gates.
- Exit statuses 0 = ready/no-op, 2 = incomplete/blocked, 1 = invalid input/errors. No writes by default; `--out REPORT.json` writes JSON + verbatim console transcript `REPORT.log` new-only.
- No change to catalog pins, 151 known tool choices, six editor plugin metadata choices, offline installer, registry/PATH/services/drivers or production networks. No vendor binaries or personal source documents uploaded to public repository.

## Validation

- `tests/test_offline_readiness.py`: missing/no source, SHA verifier delegation/failure, partial subset consent, installed/no-op, missing 7zr, v2 plugin exclusion, tamper, new-only local evidence, CLI no-write/exit codes; no real vendor archive needed.
- New Windows 3.11/3.14 CI isolated `python -I scripts/offline_ready.py` test: still BLOCKED without vendor-original source, no install directory created.
- Separate actual authorized offline workstation, original-source hash/permissions, EDR, GUI and packaging approval remain **HUMAN/LEGAL_NOT_VERIFIED**.

## Next chat

Read `docs/OFFLINE_ASSETS.md`, `docs/PERSONAL_KITS.md`, `scripts/offline_ready.py`, `tests/test_offline_readiness.py`, `scripts/toolsets.py`, `scripts/my_toolkit.py`, `scripts/offline_assets.py`, previous current handoff and source manifest. Review PR diff and run Windows 3.11/3.14 CI. Squash-merge if green, then verify main SHA/post-merge CI. Keep #25/#27/#36 open until their independent industrial/vendor/desktop plugin approval gates are actually satisfied. Do not publish release automatically.
