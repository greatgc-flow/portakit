# PortaKit — cross-component recursive MECE review (2026-10-23)

## Authority, scope, and evidence

Live repository checked at start: `greatgc-flow/portakit`, PUBLIC, `main=af6103ffd81c86e61b42e067da1c8c572dc803f4`, no open PR/issue, Windows test run [39883144654](https://github.com/greatgc-flow/portakit/actions/runs/39883144654) successful on Windows Python 3.11 and 3.14. The snapshot is NOT a claim that later commits were audited: always re-query live `main`, PRs, Issues, Actions, catalog and manifests. Repository `main` was not branch-protected at baseline; use PR and verified checks for changes.

Checked full file/tree inventory, both 2026-10-22/23 handoffs, original 48-file source map, actual root/catalog/toolsets JSON, specifications/decisions/backlog/release documents, research metadata, Python/PowerShell/CMD source, all test files, and workflow contents. Baseline main contains **53 tracked files** (48 historical files plus five newer handoff files; five historical files also changed). The `2026-10-22_REPO_SOURCE_MAP.json` is an intentionally dated 48-file provenance snapshot, NOT current full inventory.

## Vertical MECE: catalog -> categories -> profiles -> local operations

- `catalog.json`: 17 installable SHA-256 immutable pins. No duplicate tool IDs or target directories observed. No auto-update/release.
- `toolsets.json`: 10 primary categories, 12 reusable profiles, six frozen legacy aliases. Every one of 17 pinned tools is owned by exactly one primary category; none are orphaned or multiply owned. Empty domains are intentional; absence of network/system pins must never be misreported as a bug or silently filled with binaries.
- Research register: 108 distinct IDs. `admission` values partition exactly into 17 `PINNED_CATALOG`, 27 `OS_BUILTIN`, 64 `RESEARCH_ONLY`. The 17 admitted IDs equal the 17 `catalog.json` IDs. Every research item has one primary domain; the profile overlap is a composition feature, not duplicated installs.
- Selector composition de-duplicates IDs. `plan` does not install; `apply --yes` installs missing pinned items only. Already-installed and blocked state are separate; partial batch installation is explicitly NOT a whole-batch rollback.
- Offline assets require vendor original filename plus exact SHA-256; all missing archives are checked before any batch modification and each tool verifies again at deploy. `--recommended` offline intentionally fails closed.
- `7zip` needs an already installed, byte-verified `7zr` prerequisite. Profiles grouping both include that prerequisite in current order; standalone `7zip` selection does not silently install it.
- Local evidence is not uploaded to this PUBLIC repository. Historical source map is intentionally not overwritten as though it were fresh.

## Horizontal MECE: lifecycle, test, security, license, UX, feedback

| Dimension | Present safeguard | Residual limitation / objective gate |
| --- | --- | --- |
| Source/intake | Explicit upstream immutable HTTPS URL + SHA-256 | A pin is not legal/EDR/OSS approval; independent local approval required |
| Air gap | Exact original vendor archive and independent SHA recheck | Transfer/approval record, signature, retained notices remain P1 |
| ZIP | Existing path/reparse/duplicate validations | **Gap found:** no general ZIP member/expanded-byte cap on baseline; candidate fix in this review adds bounded preflight and runtime size validation with rollback regression tests |
| 7z SFX | Pinned 7zr as tool; SFX parsed/validated as DATA, never execute installer | Manual Windows File Manager GUI acceptance pending |
| State | Per-app staging, atomic swap, rollback and tested lock | Whole-batch atomicity not promised; malicious external file races not absolutely preventable |
| CLI evidence | Opt-in apply and GUI flows write local transcripts | Plain single-tool core CLI and error paths do not universally write mirrored logs; preserve simple default and review optional universal evidence separately |
| GUI | Synthetic fixtures and explicit human attestation | Everything, grepWin, 7zFM remain **HUMAN_NOT_VERIFIED** until approved nonproduction test |
| Office | Static WinMerge filters and self-verified evidence ZIP | Real licensed Excel/Word/PowerPoint/Visio semantic COM + GUI **NOT_VERIFIED** |
| Network | Native tools preferred; TCPView/PsPing metadata only | Vendor use ≠ redistribution permission; active PsPing probes need authorization |
| CI | Windows Python 3.11/3.14 and live vendor smoke | Offline unit CI does not prove all GUI behavior or enterprise approval |
| Release | Explicit human gate, no automatic publishing | **RELEASE_BLOCKED** until workstation/license/security gates and approval |

## Safe focused remedy in the associated change

The general ZIP importer now proposes these fixed *safety limits*:
- `MAX_ZIP_MEMBERS=4096`, counting directory entries.
- `MAX_ZIP_EXPANDED_BYTES=512 MiB`, counting declared expanded file sizes across the whole ZIP.
- Fail before extraction if either cap is exceeded; verify actual streamed bytes equal declared file size. Reject even a forged ZIP reader that returns extra uncompressed bytes.
- Keep the independent 100 MiB *downloaded-asset* cap and the separate stricter SFX 7z cap unchanged.
- Add tests for count violation, total expanded violation, exact-boundary admission, hostile stream overrun, and preserving existing install/state on failure.
- Do not alter download pins or auto-install flags. Larger future official ZIPs require explicit reviewed limit change, never silent fallback.

Until Windows PR CI and any required live archive verification succeed, treat this remedy as a **proposed code change** rather than an accepted main-branch fact. The original upstream 17 pinned vendor archive hashes remain the immutable source of truth.

## Licensing fact check (2026-10-23)

Official Microsoft [Sysinternals FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq) permits broad use on the user's own/supported devices, but explicitly says Microsoft does not grant third-party redistribution licenses; [license terms](https://learn.microsoft.com/en-us/sysinternals/license-terms) also restrict transfers. An [archived Microsoft statement](https://learn.microsoft.com/en-us/sysinternals/resources/archive/v02n05) specifically warned against corporate internal shares. Therefore TCPView/PsPing stay **RESEARCH_ONLY**, no vendor binaries, no internal bundles, and no implied permission to transfer to air-gapped computers without separate legal determination. Avoid active probes without owner approval.

## Prioritized state register

- **DONE (baseline code)**: 17 pins, 10 domains, deterministic optional toolset composition, SHA-checked online/offline per-tool installs, safe 7-Zip SFX DATA-only extraction, classic HKCU context menu opt-in, evidence harness, pinned Actions.
- **IN VALIDATION (this change)**: general ZIP extraction bound and five regression checks; status determined only by new PR CI/live results.
- **NOT VERIFIED**: Everything/grepWin/7zFM interactive GUI, Office4 semantic comparisons, local authorized corporate workstation, offline intake policy/legal approval, actual installed footprint of every tool, newer `sd` binary version reconciliation.
- **DEFERRED**: Windows 11 modern context-menu extensions, extra Sysinternals downloads, auto-updates, optional runtime profiles, unapproved remote probing, public releases.
- **CONTINUE**: synthetic local human acceptance and independent ZIP/CSV/JSON/log review, measured disk footprint, verified vendor licensing, `sd` upstream anomaly investigation, compact highest-value candidate evaluation.

## Closed-loop change rule

1. Recheck live HEAD/visibility/PRs/Issues/CI and manifest count invariants.
2. One risk or feature, one safe atomic change with negative/edge tests.
3. Windows Python 3.11+3.14 CI success; for changed vendor extraction also use appropriate opt-in live release smoke before publishing claims.
4. Review PR diff, avoid sensitive log/binary upload, merge only green required checks.
5. Recheck post-merge main and CI; refresh handoff/backlog and leave the unfinished human/legal gates honestly open.
