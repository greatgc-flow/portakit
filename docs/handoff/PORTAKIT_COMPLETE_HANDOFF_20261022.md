# PortaKit — complete conversation handoff & verified current state

> **Snapshot date:** 2026-10-22, Asia/Seoul. **Repository:** [greatgc-flow/portakit](https://github.com/greatgc-flow/portakit), **PUBLIC**. This handoff deliberately includes only PortaKit technical/project context; do **not** put user conversations, personal memory, confidential business information, passwords, third-party executables or corporate data into a public Git repository.
> **Snapshot baseline** (before this handoff commit): main `09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25`. **Always confirm latest live main HEAD, PRs and Actions before continuing**; this SHA is not an immutable future-current value.

## 0. Read order and authority

1. [START_NEW_CHAT_PORTAKIT_20261022.md](START_NEW_CHAT_PORTAKIT_20261022.md) — paste the self-contained user prompt into the new chat.
2. **This file** — complete conversation-specific facts, technical context and pending tasks.
3. [../../README.md](../../README.md) — top-level command examples and overall purpose.
4. [../../catalog.json](../../catalog.json), [../../toolsets.json](../../toolsets.json) — **authoritative** version/SHA/download pins, ten primary categories and profiles. If any prose disagrees, these validated files plus live tests win.
5. [../SPEC.md](../SPEC.md), [../DECISIONS.md](../DECISIONS.md), [../RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md), [../BACKLOG.md](../BACKLOG.md). Older historical sections may describe fewer tools; use current main + this dated handoff for the latest state.
6. [../TOOLSETS.md](../TOOLSETS.md), [../../research/TOOLS_CANDIDATES_20261020.json](../../research/TOOLS_CANDIDATES_20261020.json), [../RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md](../RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md).
7. [../GUI_ACCEPTANCE_20261021.md](../GUI_ACCEPTANCE_20261021.md), [../../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json](../../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json), [../WINMERGE_OFFICE_ACCEPTANCE.md](../WINMERGE_OFFICE_ACCEPTANCE.md).
8. Actual current code, scripts, tests, workflows and GitHub PR/Actions evidence described below. Do not infer a passed manual GUI test from green automated CI.

## 1. User goal, context and engineering requirements

**Goal:** PortaKit is a **Very Simple** modular, reproducible, Windows-focused manager for useful **small**, **free-to-use-in-business after legal review**, **offline/air-gapped-friendly**, optionally composable portable applications. Strong preference for productivity per megabyte, not installing all programs. Workflows cover general office utilities, Windows file/process tools, network diagnostics, text/logs, structured data, developer tooling, automation, security and approved remote transfer. The aim is MECE by primary functionality and a closed loop of catalog → optional selection → safe install → test → evidence → review/backlog. Do not promote a research candidate to installed status without its own gates.

**Relevant company workflow:** user manages Battery MES collection servers and equipment↔MES interfaces (CIM/EAS/EAP) including WCF/IIS and production diagnostics. Keep production-safe defaults: no unexpected network probes, DLL injection, service installation, packet capture, admin escalation, registry/association or file replacement. Official EULA, separate redistribution rights and company OSS/EDR approval matter even for free apps. Tools may be staged on an approved connected PC and used later with **no Internet**.

**Implementation constraints:** PortaKit itself uses Python **3.11+ stdlib only** on Windows x64; this does **not** mean Java/C# applications in the user's environment can be upgraded. Any proposed companion Java code must remain **JDK 1.8**, C# must remain **VS 2015 compatible**, and requested PowerShell scripts must run on **Windows PowerShell 2.0 and 5.x** (avoid pwsh-only syntax). Keep each feature independently testable; optionalize disputed settings; consider missing/null/empty inputs, links/junctions, permissions, existing state and partial failure. Console/script output must be preserved in a local evidence file wherever practical, with rich comments, explicit quoting and modular functions.

**Privacy/scope:** repository is PUBLIC. Commit sources, tests, synthetic fixtures, specifications, metadata-only vendor references and project handoff. **Never** commit copyrighted vendor binaries, local logs from actual company machines, credentials, license keys, private network endpoints, identifiable personal memory or raw conversation transcripts. All real workstation validations are Human-in-the-Loop.

## 2. Actual repository state verified on 2026-10-22

| Check | Verified snapshot | Evidence |
|---|---|---|
| Repo/main | Public; main baseline `09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25` | GitHub branches/main API |
| PRs | PR **#1–#18 merged**; **0 open PRs** at snapshot | [GitHub PR list](https://github.com/greatgc-flow/portakit/pulls?q=is%3Apr) |
| CI | [main Windows tests run 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982): SUCCESS; Python 3.11 = **282/282**, Python 3.14 = **282/282** | Real Actions logs |
| Vendor smoke | [PR #18 pinned live Windows archive smoke 39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046): SUCCESS; earlier [full 7-Zip run 39513889906](https://github.com/greatgc-flow/portakit/actions/runs/39513889906): SUCCESS | Actual Actions run conclusions |
| Installable catalog | **17 SHA-pinned IDs** (3 original + 8 compact CLIs + 5 follow-on + full 7-Zip) | catalog.json |
| Survey | **108 unique tools** = 17 installable, 27 Windows built-in/optional built-in, **64 research-only** | research/TOOLS_CANDIDATES_20261020.json |
| Classification | Schema v2 with **10 exclusive primary domains**; profiles compose domains; six historical selectors frozen | toolsets.json + unit tests |
| Releases | No approved/published product release is asserted; Release Gate intentionally BLOCKED by outstanding workstation/Office/security acceptance | docs/RELEASE_CHECKLIST.md |
| Sysinternals TCPView/PsPing | **Research-only, metadata-only**; no catalog pin/vendor binary packaged | research/SYSINTERNALS_NETWORK_REVIEW_20261021.json |
| Manual GUI | Everything, grepWin, full 7-Zip: **NOT VERIFIED on licensed/approved interactive end-user PC**; harness exists but cannot silently confer a PASS | docs/GUI_ACCEPTANCE_20261021.md |

**Important CI wording:** hosted Actions validates scripted regressions, real Windows downloads, SHA, extraction and CLI-only operations. The Office4 prerequisite ZIP can itself be verified while still reporting `NOT_VERIFIED` because actual Excel/Word/PowerPoint/Visio COM+WinMerge semantic GUI verification was never done in that runner. The synthetic prerequisite probe may intentionally exit 2 (NOT_VERIFIED). This is not a product Office PASS.

## 3. Complete work chronology (this conversation + prior project context)

| PR | Implemented / documented | Critical acceptance note |
|---|---|---|
| [#1](https://github.com/greatgc-flow/portakit/pull/1) | Core Windows stdlib portable manager: catalog, list/install/update/remove, pinned SHA, safe ZIP extraction, locks/state/rollback, JSON/error envelopes | No default admin/registry/PATH writes |
| [#2–#6](https://github.com/greatgc-flow/portakit/pulls?q=is%3Amerged) | Vendor live installation and reproducibility; optional recommended Notepad++ plugins and WinMerge settings/Office format plugin scripts; existing-install `configure` while preserving user state | Recommendations opt-in; not proof of Office GUI |
| [#7–#10](https://github.com/greatgc-flow/portakit/pulls?q=is%3Amerged) | Real WinMerge plain-text HTML diff, Office plugin static/COM prereq probe, Office4 one-run evidence ZIP and independent ZIP/SHA/results/marker verifier | Office Excel/Word/PPT/Visio semantic GUI still not verified |
| [#11](https://github.com/greatgc-flow/portakit/pull/11) | Explicit reversible **HKCU classic Explorer context menu** for Notepad++/WinMerge; component-by-component audit and backlog | Classic Windows 11 menu via More Options, not native modern-menu COM; no default registration |
| [#12](https://github.com/greatgc-flow/portakit/pull/12) | Opt-in categories/profiles, `list`, read-only `plan`, explicit `apply --yes`, de-duplication, side-effect and partial-batch evidence guards | Early overlapping Common/OS/NW/Dev names replaced by newer MECE taxonomy but retained as aliases |
| [#13](https://github.com/greatgc-flow/portakit/pull/13) | New corporate closed-network **TOP 30** research, official vendor/license/portable/privilege/driver documentation | Research findings ≠ OSS/security approval or permission to redistribute |
| [#14](https://github.com/greatgc-flow/portakit/pull/14) | **10 MECE functional primary domains**, 8 tiny immutable official Windows ZIP pins (`ripgrep`, `fd`, `fzf`, `bat`, `sd`, `yq`, `delta`, `hyperfine`), larger candidate register | Real release ZIP SHA/Windows smoke; `sd` vendor 1.1.0 ZIP reports executable 1.0.0 — documented exception |
| [#15](https://github.com/greatgc-flow/portakit/pull/15) | Five follow-on pins: `7zr`, `everything`, `grepwin`, `miller`, `dasel`; **offline** per-tool `--archive FILE` and group `--offline-dir DIR`; read-only all-assets SHA preflight | 7zr handles 7z only; no vendor GUI or services auto-launched |
| [#16](https://github.com/greatgc-flow/portakit/pull/16) | **Full 7-Zip 26.04** via SHA-verified official SFX read as DATA using pre-installed hash-checked 7zr; safe listing/extraction and actual ZIP create/test | Installer EXE **never executed**; user GUI/manual acceptance outstanding |
| [#17](https://github.com/greatgc-flow/portakit/pull/17) | GUI acceptance harness, synthetic fixtures, human consent & status evidence; TCPView/PsPing Microsoft Sysinternals metadata licensing review | Main already contains these features; never repeat as unmerged branch work |
| [#18](https://github.com/greatgc-flow/portakit/pull/18) | Windows workflow GitHub Actions references pinned to immutable commit SHAs | Preserve these security pins; updating workflow actions requires reviewed SHA |

**Current conversation's explicit decisions captured:** original Notepad++/WinMerge/jq baseline → optionally grouped tools → search for earlier tool research (Engram runtimes/catalog found but not a verified OS+NW comprehensive survey) → new corporate free/offline TOP 30 → expand to 108 unique screened entries favoring low-byte high-value utilities → correct overlapping names to ten MECE primary categories + profiles → pin 8 compact tools and vendor hashes → pin 5 more plus truly disconnected group import → full 7-Zip via data-only SFX → human GUI acceptance and Sysinternals license intake. Every implemented item above is already on main through PR #18.

## 4. Current 17 pinned applications, with role and key caveats

| Tool ID | Version | Meaning / constraints |
|---|---|---|
| `notepad++` | 8.7.5 | Text/config/log editor; ComparePlus and JSON Tools only opt-in recommended |
| `winmerge` | 2.16.46 | File/dir compare, Office unpacker scripts optional; Office4 GUI/semantic acceptance unverified |
| `jq` | 1.7.1 | JSON CLI |
| `ripgrep` | 15.2.0 | Fast recursive log regex |
| `fd` | 10.5.0 | Fast file/path find |
| `fzf` | 0.74.5 | Interactive fuzzy selection |
| `bat` | 0.26.1 | Pretty source/log viewer |
| `sd` | vendor 1.1.0 | **Binary prints 1.0.0** in Windows smoke; retain explicit anomaly |
| `yq` | 4.54.1 | YAML/JSON/XML structure CLI |
| `delta` | 0.20.1 | Readable Git diffs |
| `hyperfine` | 2.0.0 | Repeatable CLI benchmark |
| `7zr` | 26.04 | Minimal **7z-only** standalone binary; prerequisite for full 7-Zip |
| `everything` | 1.4.1.1032 | Desktop portable ZIP; GUI first-run may index NTFS, ask for service/admin; auto-launch forbidden |
| `grepwin` | 2.1.12 | GUI regular-expression file search/replace; never replace production files by default |
| `miller` | 6.22.0 | CSV/TSV/JSON CLI; Windows real CSV→JSON smoke passed |
| `dasel` | 3.11.2 | JSON/YAML/XML/CSV selector; Windows real JSON selector smoke passed |
| `7zip` | 26.04 | **Full** vendor File Manager `7zFM.exe` + `7z.exe`/DLL; original SFX never executed, prerequisite 7zr exact pin/hash required |

All 17 vendor asset URLs, archive artifact types and complete per-file SHA-256 pins are canonical in **catalog.json**. Avoid maintaining a second competing SHA list. For the 8 smallest new CLI ZIPs, the combined vendor-download bytes at review were **20,282,483 (~19.34 MiB)**, **compressed** only; no claim about installed footprint. For five later apps and 7-Zip, exact official release metadata/vendor hashes were checked by hosted Windows tests; not a substitute for a company's independent onboarding.

## 5. MECE category, selection and runtime model

Schema v2 canonical exclusive **primary owner** domains are `files`, `text`, `structured-data`, `system`, `network`, `security`, `development`, `automation`, `documents`, `transfer`. An individual installable tool belongs to exactly one; the v2 loader blocks duplicates/missing members. Intentionally empty domains are allowed. A task can span domains via **profiles**, not by duplicating ownership. `toolsets.json` is selection data only, never an arbitrary executable download instruction.

Canonical/composable profiles: `essentials`, `lightweight`, `workstation`, `incident-response`, `engineering`, `data-work`, `all-curated`, `portable-productivity`, `files-and-logs`. Historic profile names `minimal`, `mes-support`, `developer` are deliberately kept with **original frozen selections**. Historic categories `common`, `os`, `nw`, `dev`, `data`, `diag` are **legacy selector aliases**, not canonical MECE owners; `nw` remains an empty historic selector and DOES NOT magically install TCPView/PsPing. Old schema-v1 custom manifests remain supported.

**Install policy:** a read-only `plan` prints what will change; only `apply --yes` can perform selected pinned installs; includes/excludes require validated catalog IDs; overlapping selections de-duplicate. An exact-pin managed tool is skipped, with **no silent update or configuration change**. Unmanaged paths, stale pins, missing managed folders, backup artifacts, reparse links block batch apply. Batch is not one global transaction: on failure, earlier successfully installed tools remain and can be idempotently skipped on retry. Avoid a bulk remove; `remove ID` can delete managed local app data. Recommended editor settings/plugins apply **only by explicit user flag** for new installs; offline `--archive/--offline-dir` with `--recommended` is intentionally rejected to prevent hidden downloads.

**Offline intake:** on an approved Internet-connected staging machine, fetch *exact original* official vendor assets, capture license, version, source URL, digest/signature, EDR review, legal review and copy through authorized transfer channel. Then, on a disconnected Windows PC, use `portakit.py --archive PATH install ID` or `scripts/Toolsets.cmd apply PROFILE --yes --offline-dir PATH`. The group prevalidates all missing vendor basenames and all SHA-256 before installing anything; core independently rechecks on every tool. No Internet fallback. Do not package vendor binaries directly into the public Git repository.

**7-Zip SFX:** only catalog `id=7zip` can use `artifact=sfx7z`; requires already managed `7zr` with exact state and real executable SHA. Archive listing checked for traversal, encrypted/link/junction entries, case collisions, 512-member and 64-MiB expanded ceilings, validated implied parent directories and complete extracted member lengths. The original Windows installer EXE is treated ONLY as data; never executed. Synthetic Windows workflow successfully created/tested ZIP using installed full `7z.exe`. Human interactive File Manager still NOT_VERIFIED.

## 6. Exact command examples (do not silently run on production)

~~~powershell
# Safe read-only exploration
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan essentials
.\scripts\Toolsets.cmd plan lightweight
.\scripts\Toolsets.cmd plan portable-productivity
.\scripts\Toolsets.cmd plan files-and-logs

# Explicitly install approved SHA-pinned apps via vendor HTTPS:
.\scripts\Toolsets.cmd apply lightweight --yes

# Fully disconnected company Windows PC: first stage exact original vendor files
python -I portakit.py --archive "D:\Approved\7zr.exe" install 7zr
python -I portakit.py --archive "D:\Approved\7z2604-x64.exe" install 7zip
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"

# Current-user classic Explorer menu — explicit optional install/remove:
.\scripts\ContextMenu.cmd install notepad++
.\scripts\ContextMenu.cmd install winmerge
.\scripts\ContextMenu.cmd status winmerge
.\scripts\ContextMenu.cmd remove winmerge

# Default GUI acceptance is safe, does NOT launch vendor GUI; exit=2 is expected
.\scripts\GuiAcceptance.cmd --tools everything grepwin 7zip
# Human-led, explicit GUI consent, only disposable workstation
.\scripts\GuiAcceptance.cmd --review --launch --tools grepwin 7zip
.\scripts\GuiAcceptance.cmd --review --launch --allow-everything-first-run --tools everything

# Safe test suite locally on a compatible Windows workstation (no external network)
python -I -m unittest discover -s tests -v
~~~

**Evidence:** toolsets `apply` writes a unique local `.portakit-evidence/toolsets-*.log` with console-equivalent output. GUI harness creates a **new** local evidence folder **outside managed root** with `console.log`, `results.csv`, `result.json` and only synthetic fixtures; default GUI probe exits **2 NOT_VERIFIED**. Manual `pass` means **HUMAN_ATTESTED_PASS**, not visual automation. See `scripts/Run-WinMerge-Office4.ps1` and `docs/WINMERGE_OFFICE_ACCEPTANCE.md` for Office-specific evidence ZIPs (actual licensed Office apps needed).

## 7. Source/traceability map (file content resides in Git)

| Responsibility | Exact paths in main |
|---|---|
| Install/upgrade/remove state machine, reparse/archive/SFX safety, local vendor archive | `portakit.py`, `catalog.json` |
| Canonical MECE/aliases/profiles | `toolsets.json`, `scripts/toolsets.py`, `scripts/Toolsets.cmd` |
| Opt-in current-user classic right-click integration | `scripts/context_menu.py`, `scripts/ContextMenu.cmd` |
| Opt-in GUI probe and human acceptance with evidence | `scripts/gui_acceptance.py`, `scripts/GuiAcceptance.cmd`, `docs/GUI_ACCEPTANCE_20261021.md` |
| WinMerge Office4 COM acceptance and independent ZIP evidence | `scripts/WinMerge-OfficeAcceptance.ps1`, `scripts/Run-WinMerge-Office4.ps1`, `scripts/Run-WinMerge-Office4.cmd`, `scripts/package_office_evidence.py`, `scripts/verify_office_evidence.py`, `docs/WINMERGE_OFFICE_ACCEPTANCE.md` |
| Windows actual WinMerge plain-text report smoke | `scripts/WinMerge-RuntimeSmoke.ps1` |
| Core regression coverage | `tests/test_*.py` including catalog, archive, lifecycle, links, configure, recommended, menu, toolsets, offline, SFX, GUI, Office evidence/verify, research taxonomy |
| Hosted CI and live vendor/installer smoke | `.github/workflows/windows-tests.yml`, `.github/workflows/live-windows-smoke.yml` (actions SHA pinned in PR #18) |
| Original 30-product research and 108-entry screening | `docs/RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md`, `research/TOOLS_CANDIDATES_20261020.json` |
| Microsoft TCPView/PsPing legal/risk stage | `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json` |
| Architecture & governance | `docs/SPEC.md`, `docs/DECISIONS.md`, `docs/COMPONENT_REVIEW_20261020.md`, `docs/TOOLSETS.md`, `docs/RELEASE_CHECKLIST.md`, `docs/BACKLOG.md`, `README.md`, `docs/HANDOFF.md` |
| New cross-chat handoff | `docs/handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md`, `docs/handoff/START_NEW_CHAT_PORTAKIT_20261022.md` |

### Verification evidence map

- **Current main Windows regression:** [run 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982), Python 3.11 and 3.14 each **282 tests**, both success. This also tested GUI harness parser and verified no Sysinternals binary in catalog.
- **SHA-pinned workflow action follow-up PR #18:** [live archived assets run 39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046) SUCCESS and [Windows tests run 39714407837](https://github.com/greatgc-flow/portakit/actions/runs/39714407837) SUCCESS.
- **Actual full 7-Zip portable archive installation/ZIP creation + second-wave offline importer:** [live run 39513889906](https://github.com/greatgc-flow/portakit/actions/runs/39513889906) SUCCESS. Windows extractor handles implicit validated parent directories; vendor install EXE never executed.
- **GUI/manual status:** hosted Windows unit tests can verify acceptance harness **logic**, NOT GUI navigation. No supplied real corporate workstation human PASS artifacts.
- **Office4 status:** prerequisite/fixture ZIP hash integrity is checked, but no four-app licensed Office COM + visually examined semantic comparisons have been validated.

## 8. Outstanding risk register — NO silent PASS, no scope inflation

| Priority | Status | Gap / exact next gate |
|---|---|---|
| P0 | **RELEASE_BLOCKED** | No production/company approval or unambiguous general release GO. Secure legal/OSS/EDR policy, non-production acceptance, doc review and explicit human approval before tag/release. |
| P1 | **HUMAN_NOT_VERIFIED** | Everything first-run may offer service/UAC, whole-drive NTFS indexing, HTTP/ETP and reveal path metadata. Test only synthetic directory and decline all elevated/network features unless separately permitted. Run GUI harness only under operator consent. |
| P1 | **HUMAN_NOT_VERIFIED** | grepWin GUI: verify UTF-8/UTF-16 synthetic regex search; ensure no replacement of company data, report UI/results and settings footprint. |
| P1 | **HUMAN_NOT_VERIFIED** | Full 7-Zip `7zFM.exe` interactive open/create/extract ZIP/7z, Unicode path, local settings and no silent file associations. CLI ZIP smoke succeeded but GUI remains separate. |
| P1 | **NOT_VERIFIED_OFFICE4** | Real Excel/Word/PowerPoint/Visio Office COM+WinMerge plugin semantic comparison and generated HTML results on licensed interactive Windows PC; absent COM is NOT_VERIFIED, never mark PASS. |
| P1 | **LICENSE/EDR_GATE** | TCPView and PsPing official Microsoft free company-use differs from third-party redistribution. No binaries, download pins or auto-installs until a legal-approved closed-network intake workflow; PsPing sends active probes and belongs to PsTools (unrelated powerful commands). |
| P1 | **UPSTREAM_VERSION_ANOMALY** | Pinned `sd` release ZIP v1.1.0 prints executable v1.0.0 on Windows. Existing CI warns explicitly; investigate vendor build metadata before claim of internal version match. |
| P2 | **OPTIONAL** | Windows 11 modern context menu via COM/shell extension & WinMerge native multi-selection comparison. Existing current-user *classic* verbs work, modern shell does not claim parity. |
| P2 | **OPTIONAL** | Source/binary version/size refresh as separate reviewed immutable-pin PR; no automatic latest, arbitrary version upgrade, PATH or systemwide changes. |
| P2 | **OPTIONAL** | Improve offline intake audit with stored approved license receipt, signature/vendor hash evidence, EDR/OSS signoff; recommended editor plugins in offline mode intentionally unsupported (fail closed). |

**Production-specific network troubleshooting:** TCPView view socket/PID in read-only mode; consider hostname resolution as a variable in the previously reported WCF 3–4-second intermittent delay. PsPing requires target/port/rate/test window approval. Use native `netstat`, `typeperf`, `logman`, `netsh trace` etc where already present before expanding third-party redistribution obligations; never generate traffic/capture without permission. Note: prior WCF performance diagnosis is outside this repository and no real MES logs are included here.

## 9. Closed-loop continuation protocol

1. Fetch actual live `main` SHA, PRs, Issues, Actions and compare with this dated snapshot; never overwrite/rollback newer work. Confirm repository visibility PUBLIC before edits.
2. Read this handoff + actual SSOT files/code/tests; audit category/alias ownership, source-pin hashes, documented status vs actual CI and any security changes after the baseline.
3. Address the highest-value outstanding P1 **manual GUI acceptance** through an explicitly human-run, nonproduction, synthetic fixture test; provide **one** complete approved script/checklist and require true evidence; never claim to have clicked a GUI via GitHub Actions.
4. Separately resolve TCPView/PsPing **official use, internal transfer and third-party redistribution** policy. If unclear, leave metadata-only and create documented decision/issue rather than violating license or bundling.
5. For any new feature, follow RED → minimal independent implementation → GREEN offline tests → Windows real vendor smoke if applicable → documentation/spec → PR → CI → merge only after passing checks; preserve hard-fail thresholds and no-default-side-effects.
6. Before handoff or release, repeat MECE review in both directions: every pin one primary owner, research status never exposed as installed, every P1 gap has observable acceptance evidence or explicit NOT_VERIFIED, no closed-loop claims without independent verification.
7. Keep the source/trace links, pending gaps and next-chat prompt current. This handoff is an audited contextual snapshot, **not the complete original chat transcript**, because the entire chat (including private material) is not a safe/public-repo artifact.

### Complete 48-file Git blob provenance

- [2026-10-22_REPO_SOURCE_MAP.json](2026-10-22_REPO_SOURCE_MAP.json) is a read-only snapshot of **all 48 pre-handoff** tracked source/docs/tests/workflow files at the original baseline `main=09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25`, including each relative path, byte length, and **Git blob SHA**. The actual complete file contents remain stored by Git; this source map is an index, **not** vendor-download SHA-256 and **not** a copy of the full chat transcript. It intentionally does not include files created by PR #19 or this later source-map PR. Re-query the **current main tree** for any newest state, and do not confuse these baseline blob hashes with current HEAD.

## 10. Last verified provenance and handoff integrity

- The current repo state was verified live on **2026-10-22** with GitHub connected actions: branch/main SHA, PR list (none open; #1–#18 merged), root file tree, pinned catalog, schema v2, 108-item research register, core/workflow source paths and exact CI conclusions.
- At the baseline, `main` had **282 passing tests per Python version** and live pinned Windows smoke SUCCESS. Earlier provisional failures and retries during development were resolved; **do not** count intermediate failed runs as unresolved bugs if final green source/evidence superseded them.
- This document summarizes *material project context*. Original implementation, test fixtures and design notes remain in Git at the exact linked paths; no vendor binaries or user local files were copied into this public repository.

