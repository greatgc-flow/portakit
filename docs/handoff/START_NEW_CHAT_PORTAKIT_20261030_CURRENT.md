# PortaKit — current next-chat continuation (2026-10-30)

## 2026-10-31 — DuckDB TAR + CSV alternatives source-only work (merged PR #55)

[PR #55](https://github.com/greatgc-flow/portakit/pull/55), merged as `570e198630e3dc71bc075f115d26ae9878cabe23`, includes `scripts/targz_preflight.py` as an independent optional original SHA + bounded TAR/gzip read-only verifier (no extracted file and **no change to the current core installer**), synthetic path/link/PAX/size/sha/collision/CRC/evidence tests, [operator guide](../DUCKDB_TARGZ_CSV_ALTERNATIVES.md) and supplemental qsv/xan metadata. DuckDB official 2.0.0 Win x64 tar.gz SHA is in previously published research ledger; original physical file was not fetched or run by ChatGPT. Current qsv x64 MSVC/GNU 402,543,109/129,287,020 compressed bytes > 100 MiB core cap; xan 0.61.0 Windows x64 ZIP 6,473,075 bytes from official GitHub release metadata, potential next lightweight research. All candidates remain noninstallable research-only; enterprise EULA/EDR, redistribution, real vendor Windows smoke, actual extraction and releases are **NOT VERIFIED**. Windows Python 3.11 and 3.14 PR full suites **499 tests each PASS** and [post-merge code main CI](https://github.com/greatgc-flow/portakit/actions/runs/41169678506) **PASS**. The original official DuckDB binary/archive was **not** downloaded or run and no catalog approval was granted. Preserve actual latest main as SSOT.


## 2026-10-31 — lightweight 3-tool research snapshot (merged PR #54)

[PR #54](https://github.com/greatgc-flow/portakit/pull/54) merged as `3aa83daf478f797b6407052d590ea8762024ed20`; reviewed [source-cited review](../../docs/LIGHTWEIGHT_CANDIDATES.md) for DuckDB CLI v2.0.0 (official Windows x64 `tar.gz` / GitHub release SHA metadata; current core supports only zip/exe/sfx7z), xsv 0.13.0 (upstream archived 2025; Windows MSVC ZIP without GitHub API digest), and Tailviewer portable 1.0.0.39 (2022 ZIP / .NET Framework 4.7.1+, no GitHub API digest). Creates a supplemental machine-readable release-metadata snapshot and read-only optional `scripts/lightweight_review.py` with eight independent missing admission gates, new-only local JSON and exact console evidence, zero downloads/install/vendor execution. All three remain `RESEARCH_ONLY`; **vendor assets, Windows smoke, expansion size and enterprise legal/EDR/redistribution have not been verified**. PR full Windows Python 3.11/3.14 each **482 tests PASS**, and [post-merge main CI](https://github.com/greatgc-flow/portakit/actions/runs/41168279537) both **PASS**. A previously flaky ZIP timestamp-dependent lifecycle test was stabilized without changing the installer; latest live main overrides dated handoff.


## 2026-10-31 — offline plugin missing-only source follow-up (merged #53)

[PR #53](https://github.com/greatgc-flow/portakit/pull/53), merged as `ff2af0ce76f1157d7398d5c0b65a1992c4e8ca0e`, updates `scripts/plugin_offline.py` to require approved original ZIPs only for **missing** pinned editor plugins at apply time. Previously managed plugins must still pass full per-file SHA receipt/host-state checks and are skipped without ZIP re-acquisition. `verify` still checks all selected originals; `apply --yes --policy-approved` remains mandatory and cannot auto-install unapproved research choices. Existing/unknown/modified or legacy receipt entries fail closed. Six synthetic negative/positive tests plus docs; PR Windows Python 3.11 and 3.14 **471 tests each PASS**, and [post-merge main CI](https://github.com/greatgc-flow/portakit/actions/runs/41161224819) **PASS**. No claim of corporate EULA, OSS, EDR, redistribution, interactive GUI or Release approval. Latest GitHub main always supersedes dated SHA notes.


## 2026-10-31 — selected-only GUI and historical research-stage guard

[PR #52](https://github.com/greatgc-flow/portakit/pull/52) merged as `1f14b505af63e10c6ce784d14d7dc5cf0fed442a` after Windows Python 3.11/3.14 PR matrices each ran **465 passing tests**. The optional Tk personal-kit picker now provides a `Selected only` search/category/status filter and divides crowded filter controls into two rows. Saved historical `RESEARCH_ONLY` selections remain `PENDING (locked)` and are excluded from `READY` filters after future catalog pin promotion, until explicitly removed/reselected. No install, update, download, catalog pin, GUI build button, privilege, registry or network changes. This is **headless regression proof**, not real desktop contrast/IME/DPI/screen-reader or enterprise acceptance. [Post-merge main CI](https://github.com/greatgc-flow/portakit/actions/runs/41159957752). [Issue #27](https://github.com/greatgc-flow/portakit/issues/27) stays open for human GUI evidence, #36 for license/plugin approval, #25 for research and #51 for optional branch protection. Use the current GitHub `main` SHA as SSOT over all dated notes.


## 2026-10-31 continuation — source-only KitDoctor integrated

[PR #50](https://github.com/greatgc-flow/portakit/pull/50) merged as `3d486ea491f2893528f1ec128a9ae72573921767` and introduces `scripts/kit_doctor.py`, `scripts/KitDoctor.cmd`, `docs/KIT_DOCTOR.md` and isolated offline regressions. It **reuses** the local readiness / managed footprint / plugin health engines. PR and post-merge Windows Python 3.11/3.14 [main CI](https://github.com/greatgc-flow/portakit/actions/runs/41083220122) both report **461/461 PASS**. This proves only headless/offline tests, NOT a real enterprise Windows human session. Its overall result never certifies corporate EULA/EDR, vendor authenticity, UI, redistribution or future physical capacity. The current next backlog includes [#51 optional main governance](https://github.com/greatgc-flow/portakit/issues/51), alongside #25 research, #27 human GUI, #36 editor plugin enterprise licensing. Prefer live main SHA and GitHub state to this historical snapshot.


> **2026-10-30 append-only update candidate (verify PR and latest main before treating as merged):** independent editor plugin choice schema-v2, six records from report, host prerequisite, UI checkbox-like add/remove, offline/footprint exclusion, full v1 compatibility. See `docs/INDIVIDUAL_EDITOR_PLUGINS.md`. v2 never installs plugins. Prior 151 software IDs exclude six editor plugin choices. The live main SHA supersedes any historical SHA in this handoff.

Continue https://github.com/greatgc-flow/portakit from the **actual latest remote main**, not from this dated commit. Public repository: do not publish private chat text, enterprise identifiers/logs/keys, third-party vendor executables or unapproved licenses. Check latest SHA, visibility, open PR/issues, Actions, branch protections, releases and source tree first.

## Last verified pre-docs baseline

`main=884951e6674320a23cba0a2d4a62e87b5f36ea09` after:
- [#24](https://github.com/greatgc-flow/portakit/pull/24): report intake, 53 families (5 already pinned +5 existing research +43 additional research-only), 6 editor plugin mentions (separately reviewed);
- [#26](https://github.com/greatgc-flow/portakit/pull/26): personal JSON kit selection, stored SHA/version snapshots, `create/plan/build --yes`, offline, research gate and evidence;
- [#29](https://github.com/greatgc-flow/portakit/pull/29): direct-official-source Sysinternals TCPView/PsPing SHA-pinned on main, no implicit third-party redistribution or legal approval;
- [#31](https://github.com/greatgc-flow/portakit/pull/31): optional Tkinter personal-kit GUI picker, *selection/import/save ONLY*, no install/network/OS writes;
- [#32](https://github.com/greatgc-flow/portakit/pull/32): metadata-only vendor source manifest/export/verify using SHA checks; no vendor binary packaging.

Windows post-merge tests at baseline: [325/325 Python 3.11 and Python 3.14 PASS](https://github.com/greatgc-flow/portakit/actions/runs/41021024931). This proves core/headless behavior, **not** live Tk GUI or actual approved-airgap acceptance.

## Authority and counts (as of this baseline)

- `catalog.json`: 19 SHA-pinned vendor items, official URLs/hashes; executable use and corporate permission are separate.
- `research/TOOLS_CANDIDATES_20261020.json`: 108 current canonical research rows = 19 pinned + 27 Windows built-in + 62 older RESEARCH_ONLY.
- `research/INTAKE_ENTERPRISE_PORTABLE_20261025.json`: 53 original report family mentions, 43 new distinct research-only IDs. **Union is 151 selectable IDs = 19 pinned + 27 OS + 105 research-only**, but this is not 151 actually portable/installable binaries.
- `toolsets.json`: 10 exclusive primary domains, 12 preset profiles, six legacy aliases; duplicates are removed on selection.
- `scripts/my_toolkit.py`: source of truth for personal JSON schema v1 and pin consent validation, `scripts/toolkit_picker.py` optional GUI, `scripts/offline_assets.py` source-only handoff.
- No automatic install, update, removal, service, driver, global PATH, registry changes, active industrial network listener/probe or release. Explicit `--yes` only for existing per-tool SHA-checked install; GUI never has build button.
- Read-only metadata may be used locally, but no vendor archive redistribution is authorized by its hash alone.

## Read in order

1. `README.md`
2. `docs/PERSONAL_KITS.md`
3. `docs/OFFLINE_ASSETS.md`
4. `docs/GUI_PICKER_ACCEPTANCE_20261030.md`
5. `docs/TOOLSETS.md`, `toolsets.json`, `catalog.json`
6. `research/TOOLS_CANDIDATES_20261020.json`, `research/INTAKE_ENTERPRISE_PORTABLE_20261025.json`, `research/ENTERPRISE_PORTABLE_REVIEW_20261025.md`
7. `docs/BACKLOG.md`, `docs/RELEASE_CHECKLIST.md`, `docs/DECISIONS.md`
8. `scripts/my_toolkit.py`, `scripts/toolkit_picker.py`, `scripts/offline_assets.py`, `scripts/toolsets.py`, `portakit.py`, all tests/workflows
9. Dated 2026-10-22/23/25/30 handoff documents as historical references (do not overwrite with an assertion that their old SHAs/counts are current)

## Open gates, prioritized

1. **HUMAN_NOT_VERIFIED**: actual desktop Tk picker contrast, Korean, DPI, accessibility and keyboard use; Everything/grepWin/full 7-Zip GUI; WinMerge Office4 semantic Excel/Word/PPT/Visio on licensed Office.
2. **LEGAL/SECURITY_NOT_VERIFIED**: exact vendor corporate use vs internal transfer/redistribution, signed build, EULA/privacy/EDR, first run. Official Microsoft direct URL is not internal redistribution approval.
3. **RESEARCH_ONLY**: new DuckDB CLI, xsv, Tailviewer evaluation and the rest of candidates; industrial protocol client/server distinction, no execution of report's unsafe 0.0.0.0 simulator code, test-only loopback and separate existing VirtualPLC project.
4. **Deferred**: individual optional Notepad++/WinMerge plugin selection, legal-rights-compliant actual ZIP bundling/media packing, measured installed footprints, universal core CLI stdout/error evidence, main branch governance protection, legacy OS/PS2.x testing for corporate script examples, and eventual human-approved Release.
5. **Issues**: [#25 industrial/tool research](https://github.com/greatgc-flow/portakit/issues/25), [#27 personal-kit GUI human acceptance](https://github.com/greatgc-flow/portakit/issues/27). Only close when all conditions verified; past green CI is not a substitute for field tests.

Continue smallest high-value independent change with negative/empty/null tests, reviewed PR, both Windows matrices green, and successful post-merge main CI; keep everything else explicitly OPEN. A final conclusion should distinguish **implementation / unit CI / live integration / legal evidence / human acceptance**.