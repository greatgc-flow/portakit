# PortaKit — personal portable toolkit handoff (2026-10-25)

> PUBLIC-safe handoff. Always inspect remote latest `main`, PRs, issues and Actions first; starting baseline before this development: `8146cf0de062a20dc4f9de3563d282f2ffb5380e`. Branch at authoring: `feat/personal-portable-kits-20261025`; do not assume merged until PR and post-merge CI confirm.

## Goals & safe contracts

All 151 currently known software IDs may be selected into a **user-owned declarative portable toolkit**; only 17 immutable SHA-pinned installable entries may actually be installed. 27 Windows OS built-ins are informational and 107 unapproved research tools are inert, including 43 industrial/enterprise extras from the DOCX intake. No mutation to `catalog.json`, `toolsets.json`, `research/TOOLS_CANDIDATES_20261020.json` or original registry/service/driver/network defaults.

Read in order: `docs/PERSONAL_KITS.md`, `scripts/my_toolkit.py`, `tests/test_my_toolkit.py`, `docs/handoff/PORTAKIT_HANDOFF_20261025_ENTERPRISE_RESEARCH.md`, `research/ENTERPRISE_PORTABLE_REVIEW_20261025.md`, existing 2026-10-23 R2 handoff, README, toolsets, core and workflows.

## Architecture & key decisions

- One simple new CLI `scripts/MyToolkit.cmd` uses Python 3.11+ stdlib and delegates real installs to `scripts/toolsets.py` (no duplicated install engine). `list [--all]`, `create --name --out --tool/--preset/--category/--exclude`, `plan --kit` and `build --kit --yes [--offline-dir] [--skip-pending]`.
- `create`: exactly one personal JSON + console-mirroring local log, new files only, reparse checked, no installation. JSON schema v1 saves selected IDs, exact approved pin versions/SHA/dest and OS/research partitions. Existing prior report candidates cannot become installable just because upstream changes; recreate personal kit after human approval.
- `plan` is read-only and reports installed/pending/built-in/blocked. `build --yes` defaults to fail closed if any research-only selection is present. `--skip-pending` explicitly builds ONLY approved subset; `toolsets.apply` rechecks SHA and preflights all offline missing vendor archives before writes, keeps per-tool rollback and transcript. No batch-wide rollback guarantee; no auto install of approved dependencies beyond explicit 7zr selection.
- Handles 7-Zip SFX requirement by sorting selected `7zr` before `7zip` when both selected, otherwise requiring preexisting state-matched 7zr. No automatic publisher, network listener, registry service or config change.
- Test isolation: `tests/test_my_toolkit.py` (14 cases), existing full suite, new Windows CI `python -I` command smoke. PR green then squash merge, verify main success and preserve next-chat handoff.

## Remaining gates

- Optional minimal selection GUI/wizard (only if justified) and package/footprint reporting; no unapproved embedded runtime or default global Windows integration.
- Real GUI acceptance (Everything/grepWin/full 7-Zip), Office4 semantic comparison, commercial redistribution/EDR/vendor binary import restrictions, and industrial simulator correctness remain open.
- Next-chat action: check the latest HEAD/PR/Actions, re-run exact catalog counts, inspect this implementation and future staged tool promotion behavior, validate Windows tests; only then describe completed features.
