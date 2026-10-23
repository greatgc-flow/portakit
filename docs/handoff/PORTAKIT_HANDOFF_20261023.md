# PortaKit — 2026-10-23 verified continuation checkpoint

> **Purpose:** public-safe incremental handoff, not a transcript or private-memory export. **Source of truth:** latest live `main` and Git tree, validated `catalog.json` and `toolsets.json`, tests and CI. **Baseline BEFORE this handoff:** `8e1d1250edef433a96392815bbe9b6c689218c75`; later commits supersede it. Repository visibility: **PUBLIC**. Do NOT upload internal employer data, server IP/credentials, chat transcripts, personal memories or third-party vendor binaries.

## Start here — authority and reading order

1. [Latest new-chat prompt](START_NEW_CHAT_PORTAKIT_20261023.md).
2. [2026-10-22 comprehensive conversation handoff](PORTAKIT_COMPLETE_HANDOFF_20261022.md) — deep context and historical work through PR #18.
3. [2026-10-22 source provenance](2026-10-22_REPO_SOURCE_MAP.json) — **48 tracked files at an earlier checkpoint only**, not the current full tree.
4. `README.md`, `catalog.json`, `toolsets.json`, `portakit.py`, `scripts/toolsets.py`, `scripts/gui_acceptance.py`, `scripts/context_menu.py`.
5. `docs/SPEC.md`, `docs/DECISIONS.md`, `docs/TOOLSETS.md`, `docs/BACKLOG.md`, `docs/RELEASE_CHECKLIST.md`, `docs/GUI_ACCEPTANCE_20261021.md`, `docs/WINMERGE_OFFICE_ACCEPTANCE.md`.
6. `research/TOOLS_CANDIDATES_20261020.json`, `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json`, `docs/RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md`.
7. `tests/test_*.py`, `tests/support.py` and `.github/workflows/windows-tests.yml`, `.github/workflows/live-windows-smoke.yml`, live GitHub PR/Actions.

## Verified state (actual GitHub queries 2026-10-23, Asia/Seoul)

| Subject | Grounded fact |
| --- | --- |
| Repository | [greatgc-flow/portakit](https://github.com/greatgc-flow/portakit), **public**, baseline main `8e1d1250edef433a96392815bbe9b6c689218c75` |
| Open PRs / issues | **0 open PRs, 0 open issues** at checkpoint. PR #17 GUI acceptance merged; PR #18 security CI SHA pins merged; PR #19/#21 October 22 handoffs merged. PR #20 was shown **unmerged** in all-PR query; do not confuse it with the merged #19/#21 |
| Latest main Windows CI | [39767847308](https://github.com/greatgc-flow/portakit/actions/runs/39767847308), **success**. Earlier [39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982) reported **282 tests for each Python 3.11 and 3.14**. Verify actual new test count from the current run logs if quoting it. |
| Last verified real vendor ZIP execution | [39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046), success; this is **not evidence of real human GUI or Office COM integration** |
| Git file tree | **51 tracked blobs** before this handoff, versus earlier 48-file source-map. Build a new tree manifest if exact updated blob mapping is needed, never treat 10/22 map as current |
| Installable catalog | **17 pinned programs**, official immutable URL/SHA per `catalog.json` |
| Candidate ledger | **108 distinct records**: 17 pinned, 27 Windows built-in/optional, 64 research-only |
| Classification | Ten **MECE primary functional groups**: `files`, `text`, `structured-data`, `system`, `network`, `security`, `development`, `automation`, `documents`, `transfer`. Cross-domain task profiles are intentionally composable |
| Release | No approval or assertion of production corporate readiness. Verify current Releases/tags before publishing; **do not publish automatically** |

## User intent and immutable principles

- Small-footprint, high productivity-per-megabyte Windows utilities; purpose-based profiles without default bulk installation. Company **closed network** is a first-class deployment environment.
- User manages Battery MES collection interface applications (CIM/EAS/EAP and equipment↔MES, WCF/IIS), but keep source generic and reusable beyond that sector. No unnecessary network probing, service/driver installation, process termination, company credential handling or capture on production servers.
- PortaKit itself requires **Windows x64 and Python >=3.11 stdlib**. For related user deliverables, **Java JDK 1.8**, **C# VS2015**, **Windows PowerShell 2.x and 5.x compatibility** are required. Prefer independently testable small functions, explicit configurable options, safe null/empty handling, unambiguous quoting and no hard-coded local paths.
- Console programs should mirror user-visible logs in local evidence files. Any new output artifact is generated locally or Git-committed only if sanitized public-safe.
- Company free-use and **redistribution/packaging** permission differ. Microsoft Sysinternals is **metadata-only** pending company legal, OSS, EDR and approved internal intake workflow. Never check vendor executables into Git.

## Implemented — exact boundaries

### Managed applications (17)

Notepad++ 8.7.5; WinMerge 2.16.46; jq 1.7.1; ripgrep 15.2.0; fd 10.5.0; fzf 0.74.5; bat 0.26.1; sd vendor archive 1.1.0 (**self-reports sd 1.0.0; anomaly documented**); yq 4.54.1; delta 0.20.1; hyperfine 2.0.0; 7zr 26.04 (**7z-only CLI**); Everything Desktop 1.4.1.1032; grepWin 2.1.12; Miller 6.22.0; dasel 3.11.2; **full 7-Zip 26.04**. Full 7-Zip is distinct from 7zr: exact vendor x64 self-extracting installer is **read as archive data, never executed**, with a separately pinned and byte-rechecked 7zr, malicious path/link/encryption and expanded-byte checks; real ZIP creation/test passed in Windows CI. GUI acceptance remains manual.

### Optional install and evidence

```powershell
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan essentials
.\scripts\Toolsets.cmd plan lightweight
.\scripts\Toolsets.cmd plan portable-productivity
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"
python -I portakit.py --archive "D:\Approved\7zr.exe" install 7zr
python -I portakit.py --archive "D:\Approved\7z2604-x64.exe" install 7zip
```

- **`plan` is read-only**; `apply --yes` is the explicit action. Existing exact pins are skipped, no silent update, shell-menu registration, global PATH, driver, service, config rewrites or network scan. Group offline mode prechecks all missing original vendor files and SHA before changes. Distinguish per-tool atomicity from whole-batch atomicity (earlier successful tools remain on later failures).
- GUI acceptance `scripts/gui_acceptance.py` / `scripts/GuiAcceptance.cmd` defaults to **no GUI launch and NOT_VERIFIED**, with evidence `console.log`, CSV, JSON and synthetic fixtures. Explicit `--review --launch` is required for guided GUI; Everything additionally requires `--allow-everything-first-run` due to first-run UAC/service/index risks. Human "pass" is **attestation only**, not automated GUI proof. No employer data or direct production server testing.
- Classic Explorer right-click menus for Notepad++ and WinMerge are independent, opt-in, HKCU-only and rollback-oriented. Windows 11 native menu and 2-selected-item WinMerge ShellExtension are not implemented.
- WinMerge Office4 Excel/Word/PowerPoint/Visio filters/prerequisites and local ZIP proof tooling are present; **real licensed Office GUI semantic comparison remains NOT_VERIFIED**. No false success from headless runner.

### Network and licensing

- `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json`: TCPView and PsPing vendor EULA/FAQ evidence, operational risk and proposed intake. Both **excluded** from installable catalog until legal redistribution/intake determination and official binary hash/permission review. No silent PsPing probing or Wireshark/Npcap installation.
- Windows native utilities should take priority when suitable (netstat, Get-NetTCPConnection where available, ping, tracert, typeperf, logman, wevtutil, pktmon if OS supports). PowerShell examples for company work must remain PS2.x/PS5.x compatible or give an explicit version-gated alternative.

## Known outstanding and next tasks — do not falsely complete

1. **P1 interactive GUI operator evidence:** test Everything on an approved non-production workstation with **folder-only** test indexing and no HTTP/ETP/service/whole-drive indexing; grepWin synthetic read-only regex search (UTF-8/UTF-16) and safe replace UX; full 7-Zip `7zFM.exe` add/extract/Open with no file association changes. Import and independently validate actual `result.json`, `results.csv`, `console.log`, approved/screenshotted evidence. Status remains HUMAN_NOT_VERIFIED until this is done.
2. **P1 TCPView/PsPing legal + procurement workflow:** verify current official Microsoft license and redistribution FAQs, align security/OSS/legal approval and closed-network transfer with company rules; metadata-only until approval. Test TCPView read-only local endpoint mapping only on authorized test systems; PsPing requires an approved destination, port, count/rate and load impact.
3. **P1 WinMerge Office4 semantic GUI with real licensed desktop Office:** currently blocked. Do not run unattended COM tests on users' active Office sessions.
4. **P2 Windows11 modern right-click and multi-selection extension** and any optional enhancements; preserve existing registry safety.
5. Continue small-first MECE research (klogg, SQLite CLI, CSV tools, etc.) gated by exact official vendor pin, SHA, size, enterprise license/internal redistribution, offline dependency and real Windows tests.
6. Resolve/doc-version `sd` embedded-version discrepancy; fix stale duplicated historical prose/claims only after direct comparison to source-of-truth.
7. Review official binary release/update/checks; no automatic pin upgrades, OS changes or public release.

## Feedback loop, validation, handoff procedure

Before change: confirm latest GitHub main HEAD/visibility, issues, PRs, workflows, green/broken Actions and required paths. Work on a branch, commit modular implementation/tests/docs, use live Windows CI and real versioned installer/ZIP SHA acceptance. Never merge failed required checks. After successful merge verify resulting main and post-merge CI; update `docs/BACKLOG.md`, `docs/RELEASE_CHECKLIST.md`, `docs/HANDOFF.md` if scope shifts. All verification claims must distinguish fact vs assumption vs not-tested and include actual GitHub action links. Keep no proprietary binaries or private context in PUBLIC git history.

**Source coverage note:** This is a semantic handoff indexed to existing files, **not** an exact reproduction of the private chat or all generated/transient data. Those are not safely or necessarily available as exportable bytes. Prior October 22 source-map records 48 blobs; 10/23 Git tree returned 51 tracked blobs at baseline and later checkpoint files will add to that number. Verify/rebuild a current map when appropriate.
