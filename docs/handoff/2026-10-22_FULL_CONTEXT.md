# PortaKit — complete project-conversation handoff (2026-10-22)

> **Entry point for a new conversation.** Read this document and [START_NEW_CHAT_20261022.md](START_NEW_CHAT_20261022.md), then the LIVE repository files. This is a **project-relevant reconstruction**, with factual evidence links and unresolved items; it is **not** a verbatim export of the ChatGPT conversation, inaccessible internal scratchpad, personal memory store, or local corporate data. **This repository is PUBLIC** as verified by GitHub API on 2026-10-22. Do not publish employer-specific details, credentials, private network addresses, local screenshots, user identity, or proprietary operating data.

## 0. Snapshot: verified external truth versus prior-chat narrative

| Item | Verified 2026-10-22 | Evidence / distinction |
| --- | --- | --- |
| Repository | [greatgc-flow/portakit](https://github.com/greatgc-flow/portakit) | **Public**, default branch main, not archived |
| Baseline latest main | \`09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25\` | Github branch API when this checkpoint was created. **Re-read latest main next chat**; handoff commits will move it |
| PRs | #1 through #18 **merged**, no open PR at checkpoint | [Repository pull requests](https://github.com/greatgc-flow/portakit/pulls?q=is%3Apr) |
| Issues | No open issues at checkpoint | [Issues](https://github.com/greatgc-flow/portakit/issues); the document backlog remains open |
| Last main workflow before handoff | [Windows tests run 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982), success | Windows Python **3.11 and 3.14** each **282 tests PASS** (actual job logs); this is not GUI/Office acceptance |
| Recent live vendor smoke | [Run 39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046), success on prior security-PR branch; [run 39513889906](https://github.com/greatgc-flow/portakit/actions/runs/39513889906) verifies full portable 7-Zip | Different branch SHAs. After a new modification, check actual HEAD tests; a previous result is not proof for new commits |
| Published GitHub Release | **Not verified/published** in this work | Preserve explicit human release gate; check Releases live before any future claim |
| Current admissible application IDs | **17 immutable vendor SHA-256-pinned entries** in [catalog.json](../../catalog.json) | Count of catalog installers, **not** evidence all 17 are installed on any user's PC |
| Tool research | **108 unique entries**: 17 pinned, 27 Windows built-in/optional built-in, 64 research-only | [Canonical research register](../../research/TOOLS_CANDIDATES_20261020.json) |
| Functional taxonomy | **10 exclusive primary domains** in schema v2, composable opt-in profiles, frozen legacy selectors | [toolsets.json](../../toolsets.json) |
| Source files | **48 baseline tracked files**, exact blob SHAs/byte lengths recorded | [Repository source map](2026-10-22_REPO_SOURCE_MAP.json) captured at baseline SHA; *not* SHA-256 of archive downloads |

### What new chats must do first

1. Query actual GitHub \`main\` HEAD, repository public/private status, open PRs/issues, workflow runs, branch protections (if needed). **If main has advanced, latest main wins; this baseline is only a recovery checkpoint**.
2. Read [this document](2026-10-22_FULL_CONTEXT.md), [new-chat prompt](START_NEW_CHAT_20261022.md), [original handoff chronology](../HANDOFF.md), [SPEC](../SPEC.md), [DECISIONS](../DECISIONS.md), [TOOLSETS](../TOOLSETS.md), [BACKLOG](../BACKLOG.md), and [release checklist](../RELEASE_CHECKLIST.md). Then inspect real code/tests/catalog.
3. Preserve 17 exact pinned IDs, MECE one-primary-domain contract, older aliases and the no-implicit-side-effect safety promises. Confirm all future additions comply with offline corporate use, real SHA pin, licensing, download size and live Windows smoke.
4. Treat external links and prior assistant reports as **leads**, never substitute for actual file/CI evidence. Test on a non-production disposable directory only; never run a live disruptive diagnosis without explicit approval.

## 1. User goals and decisions accumulated in this conversation

The work started as a small **PortaKit** Windows portable application manager intended to make company workstation tasks convenient in **internet-restricted/air-gapped environments**, prioritizing **free-for-commercial-business-use, genuinely portable, low-storage-footprint, high productivity, operational safety** and an **optional**/simple configurable selection model.

Recorded explicit requests and resolutions, in order:

1. Review each original component and keep good vendor defaults. Add optional right-click integration for Notepad++ and WinMerge. Result: opt-in owned \`HKCU\` classic Explorer menu only; no admin/system-wide change and never automatically registered during normal app install.
2. Revisit previously researched tool lists. Historical Engram source \`greatgc-flow/Engram/_sys/defaults/runtimes.json\` (developer tools/runtime) and \`tool-catalog.v1.json\` were identified; no independently verified old organization-wide Common/OS/NW evaluation report. Prior Google Drive references were exploratory, **not mirrored into this public repository**, and should not be assumed accessible without checking.
3. Make categorized optional toolsets (\`Common/OS/NW/Dev/Data/Diagnostics\`) without changing the default three-tool setup. Initial schema v1 separated pinned software assets from category/profile selection; offline read-only plan and explicit \`apply --yes\`, installed pin skip and dedicated evidence.
4. Carry out a new survey of **30 free corporate/offline tools**, with official upstream references and license caveats, covering common, Windows/OS, network, developer and data. Explicitly separate **free company use** from **right to redistribute/host the vendor executable**, corporate OSS/EDR approval, administrator/driver requirements and no-network execution.
5. Improve genericity and **recursive MECE** coverage; prioritize tiny/high-value programs and many more candidates. Replaced overlapping v1 primary categories with **10 mutually exclusive *primary functionality* domains** and *cross-domain profiles*; retain frozen old names as aliases. Initial 11 pinned apps and 107-item research inventory.
6. Add lightweight practical tools one at a time with verified official release SHA-256 and real Windows tests: \`ripgrep\`, \`fd\`, \`fzf\`, \`bat\`, \`sd\`, \`yq\`, \`delta\`, \`hyperfine\` (8 new ZIPs, **20,282,483 bytes combined compressed**, not installed footprint). The \`sd\` v1.1.0 ZIP reportedly runs an executable self-reporting \`1.0.0\`; **record the mismatch** rather than claiming semantic version parity.
7. Extend into true offline import: user obtains vendor archives on approved connected staging PC and transfers them by approved company channel. \`portakit.py --archive FILE install ID\` or \`update ID\` and \`scripts/toolsets.py apply PROFILE --yes --offline-dir DIR\`; **all local assets for pending installs** checked for exact vendor basename, size, checksum and no reparse/symlink paths before beginning batch. Existing exact pins skipped. **No hidden Internet fallback**, no recommended plugin fetches with offline flags.
8. Add \`7zr\` (small **7z-only**, *not full ZIP-capable 7-Zip*), Everything desktop, grepWin, Miller, dasel. Add \`portable-productivity\` and \`files-and-logs\` profiles; actual Windows test covered SHA, local install/reapply/no-op. Be precise: Everything and grepWin binary presence is **not** GUI interaction acceptance.
9. Make **full 7-Zip** an independent optional pin. Vendor \`7z2604-x64.exe\` SHA verified as a **7z SFX data container**; **NEVER run the installer EXE**. Requires separately pinned and byte-reverified managed \`7zr\`; pre/post member and size validation, path traversal, links, duplicates, encrypted entries, zip-bomb limits. Actual Windows CLI **ZIP create/test** passed; \`7zFM.exe\` only statically present, human GUI acceptance remains outstanding. Catalog becomes 17, research 108.
10. User said continue: prepare **safe Everything/grepWin/full 7-Zip GUI acceptance**, and review **TCPView/PsPing licensing**. PR #17 merged: \`scripts/gui_acceptance.py\` + \`GuiAcceptance.cmd\`; read-only/default \`NOT_VERIFIED\` probe, **manual review** and explicit \`--launch\`, additional \`--allow-everything-first-run\` guard. Local synthetic fixtures, stdout-mirrored log, JSON/CSV evidence; no CI vendor GUI starts. Microsoft Sysinternals license caveat means TCPView/PsPing **metadata only** pending company's separate legal/EDR approval.
11. Most recent maintenance PR #18 pinned \`actions/checkout\` and \`actions/setup-python\` to verified immutable commits without changing test behavior. No auto-publish.
12. Finally user requested this **comprehensive handoff of conversation memory/context and necessary files**. Because GitHub repository is **public**, project-relevant technical decisions, code/source hashes and links are recorded but private user/company details, raw chat transcript, confidential server context and any private files are **not** added.

## 2. Code architecture and invariants

**Primary implementation:** [portakit.py](../../portakit.py) is a small Windows Python **3.11+ stdlib** CLI. [catalog.json](../../catalog.json) is a *single* validated asset source (ID, fixed version, vendor URL, SHA-256, archive format, destination, settings). \`scripts/toolsets.py\` is an independent selection/orchestration layer; \`toolsets.json\` is a no-executable-code declarative taxonomy. There are also independent \`context_menu.py\` and \`gui_acceptance.py\` modules and reproducible Windows CI.

- Unit-oriented, independently testable functions with explicit scope; deterministic input validation; null/empty lists and corrupt/unmanaged state must **fail closed**.
- **No automatic update, remove, service, driver, file association, PATH, Explorer registry, outbound scan, TCP disconnect or upload** when selecting or installing toolsets. Default vendor settings remain intact unless explicit \`--recommended\` or \`configure ID\`, with original rules.
- Profiles: \`essentials\`, \`lightweight\`, \`workstation\`, \`incident-response\`, \`engineering\`, \`data-work\`, \`all-curated\`, \`portable-productivity\`, \`files-and-logs\`. Legacy profiles \`minimal\`, \`mes-support\`, \`developer\`; legacy aliases \`common\`, \`os\`, \`nw\`, \`dev\`, \`data\`, \`diag\` **do not silently absorb newly pinned tools**.
- Exactly one *primary* category per pinned app: \`files\`, \`text\`, \`structured-data\`, \`system\`, \`network\`, \`security\`, \`development\`, \`automation\`, \`documents\`, \`transfer\`; profile membership may intentionally overlap. Catalog v2 loader checks complete coverage, no duplicate primary ownership.
- Managed exact current pin is **no-op** for installer selection. Stale pin, unmanaged path, backup remnants or symlink/junction are blocked. Batch operations use local locks and per-tool atomic stages; already completed tools are preserved after later batch failure (no unintended broad rollback).
- Mandatory SHA checks for approved downloads and offline originals, bounded archive parsing, path-traversal/reparse prevention; full 7-Zip \`sfx7z\` is restricted to exactly the audited \`7zip\` ID, requires managed 7zr, and must never run vendor setup/uninstall executables.
- Screen output is mirrored to dedicated **local evidence** for console scripts/harnesses; custom PowerShell samples must remain **Windows PowerShell 2.0 syntax compatible, also 5.x**, unless explicitly documented otherwise. The Python management tool itself uses Python 3.11+ and standard library.
- No vendor binaries, proprietary assets, credentials, end-user company data or real Office documents belong in the public Git repository. Office fixtures are synthetic.
- A green CI is not an approval to publish a release and not proof of GUI usability, legal entitlement, site EDR approval or no production impact.

### 17 SHA-pinned application IDs / versions — exact baseline

| Domain | IDs (version) | Important behavior |
| --- | --- | --- |
| files | \`winmerge\` 2.16.46, \`fd\` 10.5.0, \`fzf\` 0.74.5, \`7zr\` 26.04, \`everything\` 1.4.1.1032, \`7zip\` 26.04 | 7zip requires 7zr; Everything service/index/HTTP can have *runtime* side effects |
| text | \`notepad++\` 8.7.5, \`ripgrep\` 15.2.0, \`bat\` 0.26.1, \`sd\` 1.1.0, \`grepwin\` 2.1.12 | grepWin GUI real use still not witnessed; sd internal-version discrepancy |
| structured-data | \`jq\` 1.7.1, \`yq\` 4.54.1, \`miller\` 6.22.0, \`dasel\` 3.11.2 | CLI functional tests on real Windows |
| development | \`delta\` 0.20.1 | Terminal diff output |
| automation | \`hyperfine\` 2.0.0 | Timing comparisons |
| system/network/security/documents/transfer | **no pinned entries** | Legitimate research candidates; not fake installers |

### Approved operator commands (examples, not consent to run)

\`\`\`powershell
# No installation, download or directory creation:
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan essentials
.\scripts\Toolsets.cmd plan lightweight
.\scripts\Toolsets.cmd plan portable-productivity

# EXPLICIT local vendor originals on a closed-network PC:
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"
python -I portakit.py --archive "D:\Approved\7zr.exe" install 7zr
python -I portakit.py --archive "D:\Approved\7z2604-x64.exe" install 7zip

# Opt-in HKCU classic Explorer menu (file/directory launch, no two-item COM shell extension):
.\scripts\ContextMenu.cmd status notepad++
.\scripts\ContextMenu.cmd install winmerge
.\scripts\ContextMenu.cmd remove winmerge

# Default no-GUI read-only installed-pin probe (writes isolated synthetic evidence):
.\scripts\GuiAcceptance.cmd --tools everything grepwin 7zip

# Human-review only on approved, disposable workstation; no automatic PASS:
.\scripts\GuiAcceptance.cmd --review --launch --tools grepwin 7zip
.\scripts\GuiAcceptance.cmd --review --launch --allow-everything-first-run --tools everything

# Offline regression on Windows after changes:
python -I -m unittest discover -s tests -v
\`\`\`

**Offline details:** the \`--offline-dir\` folder must contain the ORIGINAL, unmodified vendor-named files of *every new pin needed*, including both 7zr and official 7-Zip vendor SFX if fresh. Independent hash and size checks run before any group installation; already-managed pins need no original files. Offline \`--recommended\` cannot fetch plugin ZIPs and is intentionally disallowed.

## 3. Chronological implementation provenance (all merged as of checkpoint)

| PR | Scope / decisive evidence |
| ---: | --- |
| [#1](https://github.com/greatgc-flow/portakit/pull/1) | Windows regression and release-readiness gates |
| [#2](https://github.com/greatgc-flow/portakit/pull/2) | Plugin preservation/update and live archive smoke |
| [#3](https://github.com/greatgc-flow/portakit/pull/3) | Opt-in Notepad++ ComparePlus/JSON Tools and recommended editor configuration |
| [#4](https://github.com/greatgc-flow/portakit/pull/4) | WinMerge bundled Office unpacker configuration |
| [#5](https://github.com/greatgc-flow/portakit/pull/5) | Restore WinMerge live smoke and Office filter checks |
| [#6](https://github.com/greatgc-flow/portakit/pull/6) | Safe idempotent \`configure\` for already installed managed editors |
| [#7](https://github.com/greatgc-flow/portakit/pull/7) | WinMerge real noninteractive text comparisons and HTML evidence |
| [#8](https://github.com/greatgc-flow/portakit/pull/8) | Office 4 plugin filter correctness and COM prereq-only checks |
| [#9](https://github.com/greatgc-flow/portakit/pull/9) | One-run Office4 acceptance and SHA-256-evidenced ZIP |
| [#10](https://github.com/greatgc-flow/portakit/pull/10) | Independent validation of Office4 evidence ZIP and false PASS prevention |
| [#11](https://github.com/greatgc-flow/portakit/pull/11) | Optional reversible per-user classic Explorer menus and component audit |
| [#12](https://github.com/greatgc-flow/portakit/pull/12) | First optional Common/OS/NW/Dev/Data/Diagnostics toolset selector |
| [#13](https://github.com/greatgc-flow/portakit/pull/13) | Corporate closed-network free-software TOP 30, licensing and priority research |
| [#14](https://github.com/greatgc-flow/portakit/pull/14) | Ten exclusive MECE primary domains, 107 research items, eight tiny pinned CLIs |
| [#15](https://github.com/greatgc-flow/portakit/pull/15) | Five more portable pins and true offline \`--archive\` / \`--offline-dir\` |
| [#16](https://github.com/greatgc-flow/portakit/pull/16) | Full 7-Zip official SFX-as-data, SHA and ZIP create/test CI |
| [#17](https://github.com/greatgc-flow/portakit/pull/17) | Human-guided Everything/grepWin/7-Zip GUI acceptance; Sysinternals metadata-only licensing intake |
| [#18](https://github.com/greatgc-flow/portakit/pull/18) | Pinned GitHub Actions action dependencies to immutable verified commits |

These PRs are the durable *actual code-change* trail. The conversation also contained “go ahead” approvals at each phase, but approval to continue implementation **is not** approval to launch software on production MES servers or publish proprietary/internal data.

## 4. Main documents and source of truth map

| File | Authority / reading reason |
| --- | --- |
| [README](../../README.md) | User-facing CLI and design summary. Historical sections may contain prior-phase counts; latest source/this checkpoint prevails |
| [SPEC](../SPEC.md) | Core behavioral requirements and security invariants |
| [DECISIONS](../DECISIONS.md) | Ratified designs and feature boundaries; historical chronological entries not overwritten |
| [Handoff history](../HANDOFF.md) | Original incremental reviews from MVP through GUI and license review |
| [Toolsets guide](../TOOLSETS.md) | MECE taxonomy, profile examples, package sizes and real archive acceptance |
| [TOP 30](../RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md) | Earlier wider freeware legal/portable/privilege assessment |
| [Component review](../COMPONENT_REVIEW_20261020.md) | Original Notepad++/WinMerge/jq per-component decisions |
| [Backlog](../BACKLOG.md) | Still-open human and licensing gates; **some old sections are historical** |
| [Release checklist](../RELEASE_CHECKLIST.md) | Explicit no-false-PASS/no-release requirements |
| [GUI acceptance](../GUI_ACCEPTANCE_20261021.md) | Consent-gated synthetic Everything/grepWin/7-Zip real desktop checks |
| [WinMerge Office](../WINMERGE_OFFICE_ACCEPTANCE.md) | Four licensed Office app evidence contract |
| [Candidate register](../../research/TOOLS_CANDIDATES_20261020.json) | 108 unique tool candidates with \`admission\`, license hints and category |
| [Sysinternals licensing register](../../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json) | TCPView/PsPing corporate EULA and risk notes, **not an installer** |
| [Pinned catalog](../../catalog.json) | Only authoritative approved asset SHA and URL |
| [Profile selection](../../toolsets.json) | Only authoritative domain/profile names and tool composition |
| [Core CLI](../../portakit.py) | Download hash/offline input/atomic file operations/full 7zip SFX |
| [GUI harness](../../scripts/gui_acceptance.py) | Safe default no-GUI probe and human-local evidence; no CI visual automation |
| [Office evidence verifier](../../scripts/verify_office_evidence.py) | Independent verification with NOT_VERIFIED distinct from PASS |
| [Snapshot source map](2026-10-22_REPO_SOURCE_MAP.json) | Baseline **all 48 files** with Git blob SHA, bytes, exact relative paths; references only, contents remain in Git history |

**No copies of entire source files inside this handoff** because the actual main Git tree is already the canonical exact file content; duplicating all 574,620 bytes risks inconsistent stale copies. The immutable source map provides every baseline file's path and Git blob hash; future chats must read current HEAD first.

## 5. Cross-component verification and completed acceptance — keep precise

- Latest check at baseline \`09bd9f...\`: [main CI 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982) success; Python 3.11/3.14 **282 unit tests each PASS** (inspected job log), no production machine used.
- Earlier Windows live asset smoke tested official SHA-fixed archives, real jq and eight CLI launch cases, the second wave's local vendor originals, functional \`miller\` CSV→JSON, \`dasel\` JSON select, and full 7-Zip \`7z.exe\` ZIP creation/validation. Vendor GUI **not launched** in that run.
- Important upstream discrepancy: pinned \`sd\` release ZIP 1.1.0 reports \`sd 1.0.0\` in the executable. Vendor archive checksum matched; internal version parity is not verified.
- Everything, grepWin and full 7-Zip GUI: hosted CI tests their **installed pinned file presence and safe console flags**, not operator-visible interaction. \`GUI_ACCEPTANCE\` human checklist exists, but **no user-produced PASS evidence** in this conversation.
- WinMerge Office4: bundled vendor scripts/INI syntactic and evidence ZIP checks passed; actual Excel/Word/PowerPoint/Visio COM **NOT_VERIFIED** without licensed desktop. CI emits a NOT_VERIFIED probe; do not misrepresent it as Office plugin runtime success.
- Native Win11 modern context menu and WinMerge two-selected-item COM ShellExtension **not implemented**; existing HKCU classic 1-item launcher is tested and reversible.
- TCPView/PsPing: official license research only, **no SHA-pinned vendor EXE included**, no auto-import, no active probing. Free company use and right to distribute/share portable software are separate. The PsTools package contains other privileged utilities, so do not download the whole suite by default.
- Security PR #18 pins existing GitHub checkout/setup-python action versions by upstream commit hashes; original CI workflow criteria remain.
- Toolset profiles do **not** all contain 17 by default. \`essentials\` remains only the original trio; \`all-curated\` is an explicit broader selection. Built-in and research-only programs are never installed from the candidate JSON.
- QA uses human-ready documentation and local-only evidence; no vendor asset ZIPs, user data or confidential chat exported to public Git.

## 6. Open work, ranked by user impact and risk

**P0 — first next-chat task:** Restore live state at new HEAD (after handoff PR) and run **reproducible tests on exact changed code**; verify source map/links and all public content has no employer-internal/private detail. Do not force-release merely because CI succeeds. Confirm no PR left unmerged unnecessarily.

**P1 — actual human GUI acceptance (requires separate local approved Windows desktop):**
- Everything first-run service/NTFS indexing and privacy safety: folder-only fixtures, reject UAC/service/HTTP/ETP unless explicitly approved.
- grepWin read-only regex search on synthetic UTF-8/UTF-16 data; no replace against business files.
- Full 7-Zip File Manager GUI add/extract and no unexpected file associations/registry writes.
- Office4 WinMerge semantic Excel/Word/PowerPoint/Visio plugin comparisons with licensed installed desktop; produce independent ZIP/CSV/HTML/sha evidence and manual inspect.
- Cannot be honestly marked COMPLETE from hosted headless CI. An automation may produce NOT_VERIFIED evidence but not counterfeit human PASS.

**P1 — Sysinternals corporate path:** Legal/OSS/EDR clarify how approved TCPView/PsPing originals may be transferred to internal air-gapped Windows PCs consistent with Microsoft terms; source official single-tool binaries, exact SHA/signatures and provenance; no binary redistribution via public Git and no uncontrolled network scans. Then evaluate optional read-only local \`Tcpvcon\` snapshot and approved \`PsPing\` target-port/rate tests with clear production-impact gates.

**P1 — application hardening:** prove live real-version update preserves user plugin data, config and no-op; close the \`sd\` version-anomaly trail; confirm actual extracted byte footprint + first-run disk/registry/service changes; avoid large/full suites with license/admin issues. Audit filesystem evidence/partial failure and PowerShell 2.x/5.x compatibility.

**P2 — experience:** optional modern Windows 11 context menus, WinMerge native two-selection comparison, safe owned-key cleanup status; no implicit admin/COM registration. Optional complete offline bundle intake/manifest with approved signatures and license notices, optional independent audit/doctor.
 
**P3 — monitoring:** manual safe upstream version review, not automatic pin updates; no auto GitHub Release; minimize footprint.

## 7. Verification recipes / resumability

\`\`\`powershell
# From freshly checked out main on Windows:
python -I -m unittest discover -s tests -v
python -I portakit.py --json list
python -I scripts/toolsets.py list
python -I scripts/toolsets.py plan essentials
python -I scripts/toolsets.py plan portable-productivity
python -I scripts/gui_acceptance.py --help
# No vendor install/launch or company data touched by the above.

# Only when an approved test PC has pinned vendor assets staged:
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"
.\scripts\GuiAcceptance.cmd --root ".\portable" --tools everything grepwin 7zip

# Manual GUI interaction requires explicit consent and a local interactive shell:
.\scripts\GuiAcceptance.cmd --review --launch --tools grepwin 7zip
.\scripts\GuiAcceptance.cmd --review --launch --allow-everything-first-run --tools everything

# Office4 standalone real acceptance is separate and must never run
# against real user documents or production COM Office sessions by default.
\`\`\`

GitHub Actions: [Windows tests](../../.github/workflows/windows-tests.yml) and [Live Windows archive smoke](../../.github/workflows/live-windows-smoke.yml). Continue reporting exact test count and run links. The source tree's full baseline manifest is [here](2026-10-22_REPO_SOURCE_MAP.json); if HEAD has moved do not reuse those Git blob SHA values as current.

## 8. Handoff publication, confidentiality and limitations

1. GitHub **Public** visibility verified on 2026-10-22. We have included only generic project/technology facts and links already suitable for publication. Do not upload any personal memory, full nonproject chat data, company private topology or data, raw EDR captures, screenshots, user paths containing identifiers, auth artifacts or local closed-network installation ZIPs.
2. This handoff is a **faithful project decisions/evidence synthesis**, not a lossless raw chat export. No system tool here can extract and commit hidden ChatGPT memory or export every previous message automatically. The original conversation remains in ChatGPT history unless the user separately exports it.
3. \`2026-10-22_REPO_SOURCE_MAP.json\` holds complete files **from the baseline main checkout**, identified by Git blob hashes. Git stores the actual byte contents and retains historical commits; avoid copying 48 files again merely for a handoff.
4. To avoid divergent history, new chats **always check latest main** and reconcile branches/PRs before editing. Prefer one reviewed PR to main and confirm post-merge CI. Treat tests and legal/GUI evidence gates independently.

**End of snapshot:** technical source continuity, historical user decisions, pinned tools, MECE model, integration validation, licence boundaries and every repository file are now linked in a traceable, restartable manner.
