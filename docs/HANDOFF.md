# Open work

> **CURRENT PORTAKIT HANDOFF — 2026-10-22:** [Complete chat-to-Git handoff](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md) and [START NEW CHAT](handoff/START_NEW_CHAT_PORTAKIT_20261022.md). This original document retains historical rounds, some stale counts, and earlier decisions. Do **not** treat older snapshots as the latest source of truth. Check live main/code/pins/tests first.

Status checked 2026-10-20. The MVP contract remains [SPEC](SPEC.md). The optional recommended profile adds new behavior without changing ordinary install/update/remove semantics.

## Verification and release

- A minimal Windows CI workflow has been proposed: Python 3.11 and 3.14, regression tests plus catalog/CLI smoke, no download, no secrets, no auto-publish. **Verify actual check results at the candidate commit**; the test count alone is not a pass.
- Follow [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md) before a GitHub Release: live isolated Windows test for jq, Notepad++, and WinMerge (including actual pinned assets), failure/recovery audit, recorded evidence, and human release approval.
- The repository is public and has no published GitHub Release at the time of this handoff. PyPI packaging is not planned for this gate; choose separately if needed.

## WinMerge runtime and Office acceptance (2026-10-20)

- Added scripts/WinMerge-RuntimeSmoke.ps1: real WinMergeU.exe process compares disposable identical/different synthetic text, checks 0/1 exit codes and HTML report generation, with a Windows PowerShell 2.x/5.x-compatible transcript. CI uploads the seven-day synthetic artifact. This is an executable runtime test, not Office COM certification.
- Added scripts/WinMerge-OfficeAcceptance.ps1 + docs/WINMERGE_OFFICE_ACCEPTANCE.md for separate manual desktop COM comparison of Excel, Word, PowerPoint and Visio. Exit 2 means Office COM missing/NOT VERIFIED; reports, source fixtures, CSV and transcript are retained locally. Human GUI selection/semantic acceptance remains outstanding until actual workstation run.
- Avoid auto-publishing releases on this evidence alone. User-specific Office COM/GUI prerequisites are unavailable on ordinary hosted CI.

## Four-Office prerequisite preflight (2026-10-20)

- Office acceptance script `-ProbeOnly` checks only COM registration for Excel, Word, PowerPoint and Visio without spawning Office processes or touching production documents; emits four `NOT_VERIFIED` statuses to CSV and console transcript, exits 2.
- Live Windows CI inspects bundled `.sct` extension filters and automatic selection declarations and publishes separate seven-day Office prerequisite evidence. These gates must never be mistaken for a successful COM runtime test. Separate licensed desktop and manual GUI tests are still outstanding.

## Office 4 one-command local verification handoff (2026-10-20)

- `scripts/Run-WinMerge-Office4.cmd` + PowerShell runner provide one-operation opt-in Office4 acceptance, with `-ProbeOnly` for non-executing COM registration. Automatically install pinned WinMerge if no managed install exists or safely configure exact-pin existing; never silently update or remove anything. Requires Python 3.11+ and Windows PowerShell 2/5 syntax.
- `scripts/package_office_evidence.py` packages local synthetic fixtures, CSV statuses, HTML reports and transcripts into new ZIP, includes SHA-256 manifest, writes separate ZIP digest, refuses overwrites and symlinks.
- Office comparison acceptance requires original semantic markers in HTML diff as proof of actual extracted content, besides WinMerge exit 0/1. This prevents fake passes on raw ZIP byte comparisons; only a dedicated licensed Office workstation can verify 4 actual COM integrations. Hosted CI only runs probe-only and checks NOT_VERIFIED plus ZIP checksums.
- Results stay local; do not automatically upload or publish Office files, and do not consider missing licensed Office a pass.

## Independent Office evidence verification (2026-10-20)

- The one-run Office4 launcher now verifies its sealed ZIP using `scripts/verify_office_evidence.py`. The verifier is read-only, Python 3.11+ standard library, and does not need Office or WinMerge.
- For each ZIP, check SHA-256 sidecar, ZIP members, manifest file ledger, `results.csv` four-program statuses, and synthetic BASELINE/DIFFERENT content in every claimed PASS HTML diff. The `--require-pass` option returns 0 only for a fully validated four-app PASS; returns 2 for a valid but incomplete/not-passed result, and 1 for corrupt/inconsistent evidence.
- Tested negative cases: forged PASS status without four results, mismatched SHA-256, untracked ZIP members, unsafe paths, and missing extracted content. Hosted CI's real result is NOT_VERIFIED due to no Office COM registrations; it must not be mislabeled as a successful Office integration.
- Gate C/D requires a licensed interactive Windows desktop and human GUI verification. No automatic release is authorized.

## PeerHub cross-project status

- [PeerHub #180](https://github.com/greatgc-flow/peerhub/issues/180) was closed 2026-10-19; it concerned in-place `pip install --target --upgrade` during an active ask on Windows and is not a PortaKit CLI failure.
- [#169](https://github.com/greatgc-flow/peerhub/issues/169) and [#174](https://github.com/greatgc-flow/peerhub/issues/174) are also closed. Closure is **not** independent evidence of end-to-end resolution; check PeerHub itself before asserting so.
- Previous direct ag review of PortaKit: spot checks reported 7/7 nonempty on PeerHub 0.21.1 (recorded in the earlier handoff). This is not equivalent to a full Windows integration test.

## Plugin preservation work (2026-10-20)

- Additional Notepad++ and WinMerge plugins are **not** downloaded or installed by PortaKit. Only the plugins bundled in the pinned archives install by default.
- The proposed opt-in `preserveMissingOnUpdate` retains user-added plugin files on updates without replacing files shipped by the new application version; Notepad++ `plugins/Config` is no longer blindly copied wholesale, to prevent overwriting the vendor plugin list DLL.
- Verify this behavior in Windows CI and on a real version-change update before treating it as release-ready. The automatic live-smoke PR check tests pinned archives, not a real version change.

## Optional future scope (not required for this gate)

- Expand the catalog after verifying every new pin and source.
- Deferred: offline bundles, doctor, pip tools, shims, nested/plugin destinations and installed-state listing in `list`.

## Recommended setup track (2026-10-20)

- Proposed `install ID --recommended` for Notepad++ and WinMerge; existing install/update/remove unchanged without flag.
- ComparePlus 3.0.0 and JSON Tools 8.5 SHA-256 values taken from the official Notepad++ x64 Plugin List. Windows CI must confirm external archives, DLL destinations, NPP configuration and WinMerge INI before the feature is merged.
- Live GUI plugin load and compatibility after real editor version transitions remain **manual release gates**, not implied by CLI smoke. Never advertise them as verified by file-only tests.

## WinMerge bundled Office comparison setup (2026-10-20)

- `install winmerge --recommended` ensures vendor `MergePlugins/CompareMSExcelFiles.sct`, `CompareMSWordFiles.sct`, `CompareMSPowerPointFiles.sct`, and `CompareMSVisioFiles.sct` are present. The SHA-verified WinMerge 2.16.46 ZIP already distributes them; no duplicate downloads.
- WinMerge 2.16.46 source (`Src/Common/IniOptionsMgr.cpp`, `Src/Merge.cpp`, `Src/OptionsDef.h`) proves portable `WinMerge.ini` must contain `[WinMerge]` keys `Settings/ViewLineNumbers`, `Settings/PluginsEnabled`, `Settings/UnpackerMode`. Previous `[Settings]` formatting was ineffective; corrected here. CLI's `/inifile` is not required when an INI is alongside `WinMergeU.exe`.
- Excel, Word, PowerPoint, and Visio Office COM automation dependencies are external and not installed. CLI smoke checks packaged scripts/INI; actual GUI and Office comparisons require a separately provisioned Windows desktop for release acceptance.

## Existing-install recommended configuration — 2026-10-20

- Explicit `configure notepad++` or `configure winmerge` on an already managed current-pin installation. Reuses the original binaries, validates user tree contains no links/junctions, stages a full copy, applies selected recommended settings, fills only missing SHA-verified third-party plugins, preserves unrelated data, and rolls back on failure. Second invocation is no-op.
- Windows Python 3.11/3.14 regression tests and live Windows installed-base-then-configure verification are mandatory. No Office COM GUI acceptance is implied; licensed Office integration still needs a separate Windows desktop test.


## Component-wide audit and optional Explorer shell entries (2026-10-20)

- See [component review](COMPONENT_REVIEW_20261020.md) for tool-by-tool decisions and [backlog](BACKLOG.md) for Office4 real COM/GUI verification and optional native Windows 11/WinMerge advanced shell integration.
- New optional `scripts/context_menu.py` and `scripts/ContextMenu.cmd`: reversible per-user **classic** Explorer file menu for Notepad++, file/folder compare starter for WinMerge. Distinct owned HKCU keys, no admin, no shell COM DLLs, and no changes to default install/configure/update/remove.
- `status`, `install`, `remove` are independent from application configuration, and every call writes a console-mirrored evidence log. Registry unit mocks plus actual Windows hosted runner HKCU self-cleaning smoke are the required gates.
- WinMerge simple one-selection menu is **not** WinMerge ShellExtension's native 2-file selection/Compare To feature. On Windows 11 classic menu, use Show more options / Shift+F10. No release until actual Windows GUI context-click acceptance where requested.

## Optional toolsets and categories (2026-10-20)

- `toolsets.json` is the single declarative source for **Common / OS / NW / Dev / Data / Diagnostics** membership and profile composition; no new tool URLs/pins are claimed. `scripts/toolsets.py` and `scripts/Toolsets.cmd` provide read-only `list/plan` plus explicit `apply --yes`, optional include/exclude and new-install-only `--recommended`.
- Existing single-tool CLI and defaults remain unchanged. No automatic Npcap/driver, Explorer shell registration, global PATH, silent update, delete or bulk rollback; cross-category repeated tool IDs are installed once.
- Dedicated `docs/TOOLSETS.md` includes current category map, sample plans, official reference links for TCPView/PsPing/Everything/Sysinternals/Wireshark and backlog gates. NW specialized tools remain pending verified immutable hashes.

## 2026-10-20 small-first MECE taxonomy handoff

- The new `toolsets.json` schema v2 has ten **exclusive primary functional domains** with 11 pinned catalog tools; task profiles are separate composable views. Legacy v1 custom manifests and historical `common/os/nw/dev/data/diag` selections survive (frozen); old profile selections also survive.
- Eight small official Windows release ZIPs with GitHub SHA-256 digests now appear in `catalog.json`: ripgrep, fd, fzf, bat, sd, yq, delta, hyperfine. Their combined compressed bytes are 20,282,483, with independently checked hashes required on real Windows runner. See `docs/TOOLSETS.md`; don't confuse compressed size with extracted footprint.
- `research/TOOLS_CANDIDATES_20261020.json` contains 107 unique tool names (11 pinned, 27 OS-builtin, 69 candidates) with primary owner, official reference, license claims, priority, risk and evidence boundary. No research-only URL can be installed by toolset commands until separately admitted to pinned catalog.
- TODO: future user workstation Explorer GUI acceptance, licensed Office4 comparisons, Sysinternals distribution/legal evaluation, privileged capture preflight and ongoing pin review remain separate.

## 2026-10-21 — second-wave compact tools and air-gapped install

- Core CLI `--archive FILE` for `install/update` and `scripts/toolsets.py --offline-dir DIR` for `apply --yes`. Local files are read-only inputs reverified against catalog SHA and never downloaded over the Internet during apply. Offline recommended plugins deliberately unsupported; flags fail closed rather than contacting GitHub.
- Five new pins: 7zr 26.04 (7z **only**, not complete 7-Zip), Everything Desktop 1.4.1.1032, grepWin 2.1.12, Miller 6.22.0, dasel 3.11.2. `portable-productivity` and `files-and-logs` profiles. Catalog 16; research 108 (16 pinned, 27 Windows built-ins, 65 research-only), all tools remain exactly one primary domain.
- Important: Everything index/service settings have NOT been exercised/approved on a real workstation; it must not be auto-launched on CI/production. grepWin GUI also only gets binary presence check until manual acceptance. Full 7-Zip vendor SFX-as-DATA extraction is now implemented behind pin verification; manual interactive GUI acceptance remains open. Follow-on privileged OS/NW tools require EULA redistribution and approval.

## 2026-10-21 — official full 7-Zip 26.04 integrated after Windows SFX probe

- PR #16: pinned official 7z2604-x64.exe (SHA `d54bf805f9f3704d1e8db2fa3498ae7ef2df0312b40b558e7c71c734430a665d`) is a 7z SFX carrying 107 members/5.92 MB, containing full File Manager, GUI helper, 7z.exe and 7z.dll. Installer EXE never executed.
- SFX parser and hardened unpack via separately pinned, state-matched, byte-reverified managed 7zr.exe; fails for malicious paths, links, encrypted archives, duplicates, caps; verifies extracted members and rolls back on error. `7zip` additionally registered as primary `files` domain pin; profile prereq first. Catalog 17, research 108 (17/27/64).
- CI gates: full ZIP creation and test with portable 7z.exe; GUI only binary presence. Manual full 7zFM GUI, Win11 context menu and Everything indexing still require workstation acceptance. No release/publish.

## 2026-10-21 GUI human test and Sysinternals licensing review

- New `scripts/gui_acceptance.py` and `scripts/GuiAcceptance.cmd`: safe default probe (NOT_VERIFIED), explicit `--review`, separate `--launch`, and extra `--allow-everything-first-run`; only local fixtures/evidence, no auto-registration, service, network call or GUI automation. PASS requires human typing `pass`; verified artifact status remains honest. See `docs/GUI_ACCEPTANCE_20261021.md`.
- `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json` documents TCPView 4.19 and PsPing 2.13 official pages, PsTools suite concern, Microsoft free-company-use vs non-redistribution conditions, legal/EDR/operation gates. **No Sysinternals binaries or Pins added**; 17 installable apps retained.
- Real GUI acceptance not possible on hosted headless CI; wait for approved human workstation evidence, do not mark user-visible GUI or license gate PASS.
