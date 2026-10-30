# PortaKit — current next-chat continuation (2026-10-30)

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