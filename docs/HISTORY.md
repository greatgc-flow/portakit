# PortaKit history — dated README sections (append-only)

> Moved verbatim from `README.md` on 2026-11-08 by the recursive MECE closure audit (`review/2026-11-08_RECURSIVE_MECE_CLOSURE_AUDIT.md`); only relative links were rewritten for this folder. Every section below is a dated historical checkpoint: words such as "latest", "current" or "now" refer to the date shown, never to today. Present-tense authority is the live GitHub main/Actions plus the single current handoff named in the documentation index. Newest first. Append future README history here instead of README.

## Latest verified handoff — 2026-11-01

[**Resume PortaKit source development**](handoff/START_NEW_CHAT_PORTAKIT_20261101.md): latest merged-code/doc checkpoint, full PR/CI evidence, public-safe remaining backlog, **final-user acceptance ownership**, and a copyable new-chat prompt. Use current GitHub `main` over historic SHAs.

## Preview personal-kit JSON before create-only save (source-only, 2026-11-01)

The optional picker now exposes **Preview KIT.json (read-only)** to inspect the proposed name, ordered tool IDs, immutable version/SHA locks, research-only and OS-only choices, and optional plugin metadata before saving. It reuses `PickerModel.draft`; no disk writes, network or installer actions occur when previewing. An unchanged selection produces identical JSON text when explicitly saved later. The preview can become stale after edits; reopen it before final save. Actual GUI usability and enterprise/vendor acceptance remain final-user-only. See [personal-kit guide](PERSONAL_KITS.md) and [operator GUI checklist](GUI_PICKER_ACCEPTANCE_20261030.md).

## Optional pinned-profile finder (source-only feature, 2026-11-01)

The personal-toolkit picker now offers a **Profile (pinned)** view filter in addition to search, category, approval state and Selected only. Changing it **never edits the kit**; **Add filtered** explicitly adds visible pinned IDs, whereas **Add preset** explicitly adds the whole preset. Existing CLI, saved v1/v2 schema and vendor-installation gates remain unchanged. See [personal-kit guide](PERSONAL_KITS.md) and [human GUI acceptance](GUI_PICKER_ACCEPTANCE_20261030.md). Verify the latest live main/CI for this feature's merge status; source tests do not establish actual desktop behavior or corporate approval.

## Final-user enterprise acceptance boundary (2026-11-01)

**Actual operator tests, company-use and transfer/redistribution licenses, EDR approval, isolated vendor execution, local GUI acceptance and deployment go/no-go are the responsibility of the final user or its organization.** PortaKit development supplies code, independent synthetic tests, SHA-pinned selection, read-only diagnostics and optional user-attested installation. **CI pass and catalog READY never grant corporate permission.** Real-world acceptance is **not required to complete unrelated source-only PRs**; research-only vendor binaries remain inert and there is no automatic admission, installation or release. [Responsibility matrix and final-user checklist](END_USER_ACCEPTANCE.md).

## Historical checkpoint — direct selection input guards (PRs #93/#94)

[PR #93](https://github.com/greatgc-flow/portakit/pull/93) and [PR #94](https://github.com/greatgc-flow/portakit/pull/94) harden direct personal-kit and optional picker/plugin choice APIs against null, unhashable, duplicate and unknown IDs before state changes. Strict saved v1/v2 JSON/pin/receipt rules remain authoritative; no new parser or installation behavior. Source `main` `67da8b7e52144d8c61b2301d035e3a716300b1a3`: [PR #94 Windows CI #41265472711](https://github.com/greatgc-flow/portakit/actions/runs/41265472711) and independently [merged-main CI #41265563813](https://github.com/greatgc-flow/portakit/actions/runs/41265563813) **727/727 PASS each** on Python 3.11 and 3.14. Earlier PR #93 [head CI](https://github.com/greatgc-flow/portakit/actions/runs/41265234612) and [main CI](https://github.com/greatgc-flow/portakit/actions/runs/41265304539) **726/726 PASS each**. No vendor program, GUI field or company approval was tested. See [scoped review](review/2026-11-01_TARGETED_REFACTOR.md) and [Issue #87](https://github.com/greatgc-flow/portakit/issues/87).

## Historical checkpoint — GUI/KitDoctor report alignment (PR #91)

[PR #91](https://github.com/greatgc-flow/portakit/pull/91) source squash `acbd6e97838347130ebf798bebec95a563c153b8`: before composing independently sampled readiness/footprint reports, reject mismatched managed root, pinned-tool ID order or install status. Existing GUI missing-row error and headless no-write behavior preserved. [Exact PR-head Windows CI #41263772358](https://github.com/greatgc-flow/portakit/actions/runs/41263772358) and [independent merged-main CI #41263859072](https://github.com/greatgc-flow/portakit/actions/runs/41263859072): **723/723 PASS each** on Python 3.11 and 3.14; individual logs inspected. This does not establish atomic filesystem snapshots or real Tk/operator/vendor/EULA/EDR acceptance. Details: [MECE refactor review](review/2026-11-01_TARGETED_REFACTOR.md), [Issue #87](https://github.com/greatgc-flow/portakit/issues/87).

## Historical checkpoint — evidence write safety (PR #89)

[PR #89](https://github.com/greatgc-flow/portakit/pull/89) squash merged `b7e0cee2ee35f181c93558f3b759b82f2aea59c2`: read-only diagnostics now share one narrow create-only JSON + verbatim console/.log writer with best-effort ownership-guarded failure cleanup. No changed report formats or default filesystem writes. [Exact PR-head Windows CI #41262818996](https://github.com/greatgc-flow/portakit/actions/runs/41262818996) and [independent merged-main CI #41262904434](https://github.com/greatgc-flow/portakit/actions/runs/41262904434): **718/718 PASS each** on Windows Python 3.11/3.14. Archive smoke did not run for this change. Follow-up scope and limits: [targeted refactor review](review/2026-11-01_TARGETED_REFACTOR.md), [Issue #87](https://github.com/greatgc-flow/portakit/issues/87). Not an atomic filesystem transaction, vendor execution or corporate acceptance.

## Historical checkpoint — batch apply refactor (PR #86)

[PR #86](https://github.com/greatgc-flow/portakit/pull/86) squash merged `1888db2dc2c98fb00a57a7e22555e0217aee0962`: keep the batch installer behavior while separating child launch, strict JSON response validation and managed destination/receipt postcheck into unit-testable functions. [PR CI #41261968622](https://github.com/greatgc-flow/portakit/actions/runs/41261968622) and [independent post-merge main CI #41262060770](https://github.com/greatgc-flow/portakit/actions/runs/41262060770) both **710/710 PASS per Windows Python 3.11 and 3.14**; [archive smoke #41261968600](https://github.com/greatgc-flow/portakit/actions/runs/41261968600) **SUCCESS**. See [targeted VerySimpleGuide review](review/2026-11-01_TARGETED_REFACTOR.md) and [optional follow-up backlog](https://github.com/greatgc-flow/portakit/issues/87). No real vendor or company approval was tested; docs-only newer main commits need their own CI.

## Historical checkpoint — PR #84 source CI (708 tests)

At PR #84, functional-source `main` checkpoint `01c7559b31cb1d9dd88fe83e0b2e43a4826cb060` passed [independent merged-main Windows CI #41260317503](https://github.com/greatgc-flow/portakit/actions/runs/41260317503), **708/708 tests each on Python 3.11 and 3.14** (both individual job logs checked). [PR #84](https://github.com/greatgc-flow/portakit/pull/84) blocks changed ordered toolset selections/catalog pins between initial planning and locked apply while allowing matching status-only skips. Earlier [PRs #76–#82](handoff/START_NEW_CHAT_PORTAKIT_20261101.md) covered receipt checks, Explorer diagnostics, protected evidence logs and empty managed-folder detection. These are synthetic/code CI proofs only, not real vendor execution or enterprise approval. Any **newer docs-only `main` SHA** requires its own CI; always prefer current GitHub Actions.

## Industrial protocol role research (2026-11-01)

[Eight-candidate client/server/simulator role matrix](../research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md) distinguishes **requesting PLC clients** from **actual virtual-device listeners**, HSMS active/passive from host/equipment, and **protocol SDKs** from complete simulators. This research-only comparison enables informed *optional future* development; it installs or enables **no** industrial listener, binary, driver or company-approved vendor tool. Any real execution and enterprise signoff remain the final user's responsibility.

## Bounded optional toolset installation (2026-11-01)

`scripts/toolsets.py apply --yes` now runs its own core child using bounded **stdout and stderr** capture (**256 KiB per stream**) and an explicit **600s per-tool timeout**, adjustable with `--child-timeout 1..3600`. On overflow/timeout/invalid or contradictory core JSON, the batch **stops and logs failure**, retaining previously completed tools rather than implying a successful all-or-nothing transaction. This is **not** child-tree sandboxing or local legal/EDR approval. The plan/list commands remain read-only and do not accept apply-only timeout flags. [Examples, limitations and responsibility boundary](TOOLSETS.md).

## Declarative JSON safety (2026-11-01)

Personal-kit JSON, installation receipts, and immutable catalog/toolset metadata are treated as **untrusted local input**, not as approval certificates. Readers reject contradictory duplicate keys and nonstandard NaN/Infinity claims instead of silently keeping the final value. Create-only evidence output failures remain **invalid** and subject to best-effort cleanup; no user data or vendor programs are launched merely by these checks. See [final-user responsibilities](END_USER_ACCEPTANCE.md).

## Historical prior handoff — 2026-10-31

[Final session context and verification](handoff/PORTAKIT_20261031_FINAL_CLOSEOUT.md) ·
[Start a new chat](handoff/START_NEW_CHAT_PORTAKIT_20261031.md).
Historical 2026-10-31 baseline: Windows Python 3.11/3.14 **554/554 PASS**. See the 2026-11-01 handoff above for actual newer verified code/CI. Real xan runtime and company approval remain **final-user-owned and NOT_VERIFIED**.


## Selected-only picker and consent-safe pending status (2026-10-31)

The optional personal-kit GUI now offers a **Selected only** filter alongside category, search and approval state. Imported choices that were `RESEARCH_ONLY` when saved remain visibly pending even if a newer catalog has pinned them; they do **not** appear under `READY` until a person explicitly removes and reselects the item. Filters never change kit contents, install tools or approve vendor/legal/EDR use. Live Windows Tk display, Korean IME, scaling and accessibility still require the approved workstation checks in [GUI acceptance](GUI_PICKER_ACCEPTANCE_20261030.md).

## One-command personal kit doctor (2026-10-31)

Run `scripts\KitDoctor.cmd --kit MyKit.json --root D:\PortableApps` to combine existing read-only offline source/SHA readiness, installed logical-byte footprint and selected editor-plugin file integrity checks. Optional `--archive-dir`, `--skip-pending`, `--max-mib`, `--out` remain explicit. Overall `LOCAL_CHECKS_PASS` applies **only** to fully measured, already-installed pinned apps with no pending/OS/plugin selections; it **never certifies company license, EDR, vendor authenticity, GUI or source-transfer rights**. Output is either console-only (no files) or new JSON plus byte-identical console log. [Guide](KIT_DOCTOR.md).


## xan local-original ZIP source audit (2026-10-31)

Optional `python -I scripts/xan_zip_preflight.py --original LOCAL.zip` verifies
an already authorized local **xan 0.61.0** Win x64 original ZIP's release
metadata SHA/size, ZIP CRC, bounded contents and Windows-safe paths without
extracting or running vendor programs. Default is **read-only** (no writes);
optional `--out NEW.json` creates an exact console-mirrored `.log`.
Exit 0 is **local source/structure only**, not publisher authentication,
company use/license/EDR approval, GUI/CPU benchmark or installer permission.
An optional `--exe ABSOLUTE\\xan.exe` additionally compares the SHA-256
of that **operator-supplied local executable** with the single ZIP member's
streamed SHA-256, without extracting or starting the program. A match means
**file-byte identity only**, not publisher authentication, execution safety,
or corporate approval. Default remains read-only and vendor-free.
The canonical catalog and installable IDs are unchanged.
[One-command operator guide](XAN_ZIP_LOCAL_PREFLIGHT.md).

## One-command synthetic CSV smoke (2026-10-31)

Following [VerySimpleGuide](https://github.com/greatgc-flow/VerySimpleGuide),
an optional `python -I scripts/csv_operator_smoke.py` **plans only**
(read-only, no vendor execution). Explicit `run --yes --approved-offline` with
local `mlr.exe` and `xan.exe` paths, a **new** local evidence directory,
and an approved offline Windows workstation tests only documented CSV count
and column-selection semantics on generated synthetic files. It records local
EXE SHA, SHA drift, individual results and exactly mirrored console evidence.
Headless CI only executes short synthetic Python subprocess fixtures, **never vendor executables**. Vendor stdout and stderr are now consumed as two bounded streams, with the direct child terminated if either exceeds 256 KiB. This is **not** a Windows Job Object, RAM/disk/network sandbox or descendant-process kill. A passing smoke is **not** a xan catalog
promotion, company EULA/EDR/transfer approval or performance ranking.
[Operator guide and safety gates](CSV_OPERATOR_SMOKE.md).
For reproducible *operator-entered* cold/warm Miller–xan timing metadata,
the optional [read-only benchmark record reviewer](CSV_BENCHMARK_PROTOCOL.md)
checks source CSV identity, paired trial balance, missing resource metrics
and failure states without launching either executable or ranking products.

For optional **BOM, UTF-16, malformed CSV, numeric sort and group-sum** comparison
fixtures without running either vendor executable, use
`python -I scripts/csv_compat_fixtures.py` (read-only plan), or explicitly
`--out-dir NEW_DIRECTORY` to create only five tiny deterministic CSVs plus
SHA-256 manifest and a byte-mirrored local transcript. Files prepared do not
prove vendor compatibility or admission. [CSV compatibility matrix](CSV_COMPAT_MATRIX.md).
The [read-only compatibility output checker](CSV_COMPAT_RESULTS.md)
compares already retained Miller/xan sort/group CSV outputs against those exact
synthetic inputs and flags missing/mismatched results. It **does not execute**
either vendor or infer process exit/stderr, EDR approval or performance.

## DuckDB TAR safety preflight / CSV alternatives (2026-10-31)

Optional `python -I scripts/targz_preflight.py --original LOCAL.tar.gz` reads
an operator-supplied, separately authorized DuckDB 2.0.0 x64 original and
checks the official research SHA, bounded TAR/gzip contents, path collisions
and links **without extracting a file**. Optional `--out` writes only a new
JSON and exactly mirrored console transcript. Exit 0 is a local SHA/structure
result **only**, not permission to install, run vendor code, or transfer it.
The core installer still rejects `tar.gz`; DuckDB remains research-only.
The same [guide](DUCKDB_TARGZ_CSV_ALTERNATIVES.md) compares GitHub
release metadata for qsv and xan against existing pinned Miller. qsv current
Windows x64 assets exceed the existing 100 MiB archive cap; xan is a more
compact **research** candidate, not silently added to canonical selections.

## Lightweight candidate research gate (2026-10-31)

The optional `python -I scripts/lightweight_review.py` command displays the
**research-only** source/compatibility blockers for DuckDB CLI, archived xsv,
and Tailviewer. It makes **no downloads, installs or runtime claims**, and
always exits 2 when valid candidates are not admitted. Optional `--id` and
`--out` select a subset and create new-only JSON plus an exact console log.
Pinned catalog entries, software counts and default toolkits are unchanged.
[Source ledger and operator checklist](LIGHTWEIGHT_CANDIDATES.md).

## Idempotent offline editor-plugin apply (2026-10-31)

For validated v2 personal kits, `scripts/plugin_offline.py apply` now checks
original vendor ZIP SHA-256 only for **missing** pinned editor plugins. Already
managed plugins must match their full local file-hash receipt and do not require
the old ZIP again. Fully installed kits can omit `--offline-dir` for a no-op;
missing tools still require it. `--yes --policy-approved` remains mandatory
for every apply, with new-only console evidence. `verify` still checks **all**
selected pinned original archives. No new vendor binaries, privileges or
license approvals are implied. [Guide](PLUGIN_OFFLINE_APPLY.md).

## Read-only plugin health evidence (2026-10-30)

Run `python -I scripts/plugin_health.py --kit Editor.json --root D:\PortableApps` to compare **already installed, managed** plugin DLL and nested-file SHA-256 against a local per-file receipt without changing tools or executing vendor binaries. Result is `LOCAL_HASH_PASS`, `INCOMPLETE`, or `BLOCKED`; invalid state is an error. Optional `--out Editor.health.json` writes a new-only JSON plus byte-identical local console evidence log. Results **do not certify** publisher authenticity, corporate license/EDR or real GUI operation. See [operator health guide](PLUGIN_HEALTH.md).

## Managed editor-plugin integrity check (2026-10-30)

`python -I scripts/plugin_offline.py plan --kit Editor.json --root D:\\PortableApps` is read-only and rechecks SHA-256 for each file of an already-managed individual Notepad++ plugin. A changed, missing or additional DLL/library is `blocked-content-drift` rather than silently skipped; old receipts without per-file hashes are `blocked-legacy-unverified` until reviewed outside the installer. No automatic overwrite, upgrade or deletion. Per-file hashes do not replace EDR, publisher signatures or corporate licensing. [Operator guide](PLUGIN_OFFLINE_APPLY.md).

## Offline-only individually selected editor plugin application (2026-10-30)

New optional `python -I scripts/plugin_offline.py plan|verify|apply` provides separate **original vendor archive SHA preflight and opt-in Notepad++ plugin deployment** for the two existing nested catalog pins, ComparePlus and JsonTools. `apply` requires a schema-v2 personal kit, an already-managed exact-pinned host, all original local plugin ZIPs, `--yes --policy-approved`, dual stage+snapshot SHA validation, no existing unmanaged plugin folder, and new-only local evidence. No third-party assets are downloaded/bundled; research-only plugins remain inert. Corporate OSS/EDR and source-transfer permission plus live GUI acceptance are **separate unverified gates**. See [offline plugin procedure](PLUGIN_OFFLINE_APPLY.md).

## Individually selectable editor plugins (2026-10-30)

List six source-researched plugins with `scripts\MyToolkit.cmd plugins`; add `--plugin compareplus` or `--plugin csvlint-npp` to personal kit `create` while explicitly selecting the Notepad++ host. Optional GUI picker supports separate plugin choices. **Plugin selections are metadata-only**: a kit with plugins uses v2 JSON, old v1 remains compatible; no plugin DLL is downloaded or installed by individual choice. Building v2 blocks by default; `--skip-pending --yes` builds only pinned host apps, and `--recommended` is rejected for v2 to avoid implicit bundled plugins. [Plugin guide](INDIVIDUAL_EDITOR_PLUGINS.md). Enterprise license/redistribution and live GUI proof remain separate.

## Read-only installed-size audit (2026-10-30)

For a saved personal toolkit, `python -I scripts/kit_footprint.py --kit MyKit.json --root D:\\MyPortableApps` reports logical file bytes of **currently managed and matching** pinned folders. `--max-mib 100` optionally checks a logical-byte budget; any missing/research/OS selections produce UNKNOWN rather than fake PASS. `--out MyKit.footprint.json` creates a new-only local JSON and matching console-evidence log. No vendor binaries, network, OS changes or downloads. See [footprint guide](FOOTPRINT_AUDIT.md). Real NTFS disk allocation and compressed package sizes are separate measurements.

> **Current SSOT (2026-10-30):** Catalog 19 SHA-pinned, 108 canonical research (19/27/62), plus 43 additional research candidates; 151 selectable IDs (19 pinned / 27 built-in / 105 unverified). Historical counts in dated sections below explain past phases, not today's installation status. Start continuation at [2026-10-30 current handoff](handoff/START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md). Actual current source files always override snapshots.


## Metadata-only offline asset checklist (2026-10-30)

After creating a personal kit, use `python -I scripts/offline_assets.py list --kit MyKit.json` to see official original filenames and exact catalog SHA-256; `export --kit MyKit.json --out MyKit.assets.json` creates new-only metadata plus matching local log; `verify --kit MyKit.json --archive-dir D:\ApprovedVendorArchives` checks **all** selected pinned original files using the unchanged offline SHA preflight before any installation. [Offline guide](OFFLINE_ASSETS.md). **No download, vendor binary bundling, third-party redistribution, service/driver, or automatic installation** is performed. Research-only and OS-native tools are listed as exclusions; vendor/legal/EDR approvals remain independent.


## Optional visual personal-toolkit picker (2026-10-30)

Run `scripts\MyToolkitGUI.cmd` on an **authorized non-production Windows desktop with Python 3.11+ and Tkinter available**, or `python -I scripts/toolkit_picker.py`. The optional zero-dependency (beyond standard-library Tk) UI searches the entire current **151-ID** research/catalog union, filters by one-of-ten primary domains and approval state, multi-selects, imports a *validated* existing personal JSON, and saves a **new** pinned JSON + exactly mirrored local console evidence. **The window never installs/downloads/updates software or modifies services, drivers, shell, registry or PATH.** Install only with the separate existing CLI `scripts\MyToolkit.cmd build --kit ... --yes` after plan and permission checks. Python distributions without Tk can keep using the CLI without changes. [UI guide](PERSONAL_KITS.md). Real visual/UI workstation acceptance and screenshots are NOT_VERIFIED by headless CI.


## Build your own portable toolkit (2026-10-25)

Every known tool is now *selectable* into your own reusable JSON toolkit, but only the **19 verified SHA-pinned** tools are installable. Use [Personal Kits guide](PERSONAL_KITS.md), `scripts/MyToolkit.cmd` or `python -I scripts/my_toolkit.py`. The separate inventory union has **151 IDs = 19 pinned + 27 Windows native + 105 unverified research items**. Unverified items can be saved and planned, never silently installed.

```cmd
scripts\MyToolkit.cmd list --all
scripts\MyToolkit.cmd create --name my-support --preset essentials --tool ripgrep --tool duckdb-cli --out MySupport.json
scripts\MyToolkit.cmd plan --kit MySupport.json --root D:\MyPortableApps
scripts\MyToolkit.cmd build --kit MySupport.json --root D:\MyPortableApps --offline-dir D:\ApprovedVendorArchives --skip-pending --yes
```

`create` writes a new profile plus exact matching local console evidence; `plan` never mutates disk; `build --yes` reuses the existing validated per-tool installer. Research-only items block the whole build unless the user explicitly supplies `--skip-pending`. No new tool binaries, auto updates, services, drivers, registry/OS path edits, active network probes or releases are enabled. All archives must be separately approved and acquired by the user. This is the initial Very Simple CLI; optional GUI tooling remains deferred.


## New enterprise/industrial portable-tool intake (2026-10-25)

A [53-family DOCX research crosswalk](../research/INTAKE_ENTERPRISE_PORTABLE_20261025.json) is now kept **separately** from the 17-item approved install catalog and the existing 108-record canonical candidate ledger. [Review and correction notes](../research/ENTERPRISE_PORTABLE_REVIEW_20261025.md) explain 5 already-pinned items, 5 existing research items and 43 *new research-only* suggestions, including industrial protocols, large logs, ergonomics and IIoT. This is metadata only; no new vendor binary, service/driver, internet access, industrial listener or automatic settings change is approved. See [the 2026-10-25 handoff](handoff/PORTAKIT_HANDOFF_20261025_ENTERPRISE_RESEARCH.md).

## 2026-10-23 R2 quality and ZIP safety review

The [R2 MECE/code/security audit](review/2026-10-23_RECURSIVE_MECE_AUDIT.md) and [current public-safe handoff](handoff/PORTAKIT_HANDOFF_20261023_R2.md) describe the bounded ordinary-ZIP extraction hardening, independent regression tests and remaining **human/not-verified** release gates. The older handoff links below remain historical evidence, not the current Git main SHA. **Do not use this project as permission to redistribute vendor packages or to operate on production systems.**

> **Latest verified conversation handoff (2026-10-22):** [Complete source/decision/evidence map](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md) · [One copy-ready next-chat prompt](handoff/START_NEW_CHAT_PORTAKIT_20261022.md) · [48-file baseline source map](handoff/2026-10-22_REPO_SOURCE_MAP.json). The most recent live main plus `catalog.json` and `toolsets.json` supersedes dated historical counts. Company GUI/Office/licensing acceptance remains NOT_VERIFIED.
