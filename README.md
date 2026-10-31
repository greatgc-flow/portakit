# portakit

## Final-user enterprise acceptance boundary (2026-11-01)

**Actual operator tests, company-use and transfer/redistribution licenses, EDR approval, isolated vendor execution, local GUI acceptance and deployment go/no-go are the responsibility of the final user or its organization.** PortaKit development supplies code, independent synthetic tests, SHA-pinned selection, read-only diagnostics and optional user-attested installation. **CI pass and catalog READY never grant corporate permission.** Real-world acceptance is **not required to complete unrelated source-only PRs**; research-only vendor binaries remain inert and there is no automatic admission, installation or release. [Responsibility matrix and final-user checklist](docs/END_USER_ACCEPTANCE.md).

## Latest verified source CI

Merged `main` `b35f20d52131c367eddbd5e78dcf5f91fed71c68` passed [Windows Python 3.11 and 3.14 CI #41216414526](https://github.com/greatgc-flow/portakit/actions/runs/41216414526), **671/671 tests each** (individual job logs verified). The later source-only PR must verify its own head and merged-main CI.

## Bounded optional toolset installation (2026-11-01)

`scripts/toolsets.py apply --yes` now runs its own core child using bounded **stdout and stderr** capture (**256 KiB per stream**) and an explicit **600s per-tool timeout**, adjustable with `--child-timeout 1..3600`. On overflow/timeout/invalid or contradictory core JSON, the batch **stops and logs failure**, retaining previously completed tools rather than implying a successful all-or-nothing transaction. This is **not** child-tree sandboxing or local legal/EDR approval. The plan/list commands remain read-only and do not accept apply-only timeout flags. [Examples, limitations and responsibility boundary](docs/TOOLSETS.md).

## Declarative JSON safety (2026-11-01)

Personal-kit JSON, installation receipts, and immutable catalog/toolset metadata are treated as **untrusted local input**, not as approval certificates. Readers reject contradictory duplicate keys and nonstandard NaN/Infinity claims instead of silently keeping the final value. Create-only evidence output failures remain **invalid** and subject to best-effort cleanup; no user data or vendor programs are launched merely by these checks. See [final-user responsibilities](docs/END_USER_ACCEPTANCE.md).

## Latest complete handoff — 2026-10-31

[Final session context and verification](docs/handoff/PORTAKIT_20261031_FINAL_CLOSEOUT.md) ·
[Start a new chat](docs/handoff/START_NEW_CHAT_PORTAKIT_20261031.md).
Latest pre-closeout verified main Windows 3.11/3.14 CI ran **554 tests each PASS**; confirm the closeout/docs-only commit's exact current main CI separately. Real xan original/runtime/corporate approval **NOT_VERIFIED**.


## Selected-only picker and consent-safe pending status (2026-10-31)

The optional personal-kit GUI now offers a **Selected only** filter alongside category, search and approval state. Imported choices that were `RESEARCH_ONLY` when saved remain visibly pending even if a newer catalog has pinned them; they do **not** appear under `READY` until a person explicitly removes and reselects the item. Filters never change kit contents, install tools or approve vendor/legal/EDR use. Live Windows Tk display, Korean IME, scaling and accessibility still require the approved workstation checks in [GUI acceptance](docs/GUI_PICKER_ACCEPTANCE_20261030.md).

## One-command personal kit doctor (2026-10-31)

Run `scripts\KitDoctor.cmd --kit MyKit.json --root D:\PortableApps` to combine existing read-only offline source/SHA readiness, installed logical-byte footprint and selected editor-plugin file integrity checks. Optional `--archive-dir`, `--skip-pending`, `--max-mib`, `--out` remain explicit. Overall `LOCAL_CHECKS_PASS` applies **only** to fully measured, already-installed pinned apps with no pending/OS/plugin selections; it **never certifies company license, EDR, vendor authenticity, GUI or source-transfer rights**. Output is either console-only (no files) or new JSON plus byte-identical console log. [Guide](docs/KIT_DOCTOR.md).


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
[One-command operator guide](docs/XAN_ZIP_LOCAL_PREFLIGHT.md).

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
[Operator guide and safety gates](docs/CSV_OPERATOR_SMOKE.md).

## DuckDB TAR safety preflight / CSV alternatives (2026-10-31)

Optional `python -I scripts/targz_preflight.py --original LOCAL.tar.gz` reads
an operator-supplied, separately authorized DuckDB 2.0.0 x64 original and
checks the official research SHA, bounded TAR/gzip contents, path collisions
and links **without extracting a file**. Optional `--out` writes only a new
JSON and exactly mirrored console transcript. Exit 0 is a local SHA/structure
result **only**, not permission to install, run vendor code, or transfer it.
The core installer still rejects `tar.gz`; DuckDB remains research-only.
The same [guide](docs/DUCKDB_TARGZ_CSV_ALTERNATIVES.md) compares GitHub
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
[Source ledger and operator checklist](docs/LIGHTWEIGHT_CANDIDATES.md).

## Idempotent offline editor-plugin apply (2026-10-31)

For validated v2 personal kits, `scripts/plugin_offline.py apply` now checks
original vendor ZIP SHA-256 only for **missing** pinned editor plugins. Already
managed plugins must match their full local file-hash receipt and do not require
the old ZIP again. Fully installed kits can omit `--offline-dir` for a no-op;
missing tools still require it. `--yes --policy-approved` remains mandatory
for every apply, with new-only console evidence. `verify` still checks **all**
selected pinned original archives. No new vendor binaries, privileges or
license approvals are implied. [Guide](docs/PLUGIN_OFFLINE_APPLY.md).

## Read-only plugin health evidence (2026-10-30)

Run `python -I scripts/plugin_health.py --kit Editor.json --root D:\PortableApps` to compare **already installed, managed** plugin DLL and nested-file SHA-256 against a local per-file receipt without changing tools or executing vendor binaries. Result is `LOCAL_HASH_PASS`, `INCOMPLETE`, or `BLOCKED`; invalid state is an error. Optional `--out Editor.health.json` writes a new-only JSON plus byte-identical local console evidence log. Results **do not certify** publisher authenticity, corporate license/EDR or real GUI operation. See [operator health guide](docs/PLUGIN_HEALTH.md).

## Managed editor-plugin integrity check (2026-10-30)

`python -I scripts/plugin_offline.py plan --kit Editor.json --root D:\\PortableApps` is read-only and rechecks SHA-256 for each file of an already-managed individual Notepad++ plugin. A changed, missing or additional DLL/library is `blocked-content-drift` rather than silently skipped; old receipts without per-file hashes are `blocked-legacy-unverified` until reviewed outside the installer. No automatic overwrite, upgrade or deletion. Per-file hashes do not replace EDR, publisher signatures or corporate licensing. [Operator guide](docs/PLUGIN_OFFLINE_APPLY.md).

## Offline-only individually selected editor plugin application (2026-10-30)

New optional `python -I scripts/plugin_offline.py plan|verify|apply` provides separate **original vendor archive SHA preflight and opt-in Notepad++ plugin deployment** for the two existing nested catalog pins, ComparePlus and JsonTools. `apply` requires a schema-v2 personal kit, an already-managed exact-pinned host, all original local plugin ZIPs, `--yes --policy-approved`, dual stage+snapshot SHA validation, no existing unmanaged plugin folder, and new-only local evidence. No third-party assets are downloaded/bundled; research-only plugins remain inert. Corporate OSS/EDR and source-transfer permission plus live GUI acceptance are **separate unverified gates**. See [offline plugin procedure](docs/PLUGIN_OFFLINE_APPLY.md).

## Individually selectable editor plugins (2026-10-30)

List six source-researched plugins with `scripts\MyToolkit.cmd plugins`; add `--plugin compareplus` or `--plugin csvlint-npp` to personal kit `create` while explicitly selecting the Notepad++ host. Optional GUI picker supports separate plugin choices. **Plugin selections are metadata-only**: a kit with plugins uses v2 JSON, old v1 remains compatible; no plugin DLL is downloaded or installed by individual choice. Building v2 blocks by default; `--skip-pending --yes` builds only pinned host apps, and `--recommended` is rejected for v2 to avoid implicit bundled plugins. [Plugin guide](docs/INDIVIDUAL_EDITOR_PLUGINS.md). Enterprise license/redistribution and live GUI proof remain separate.

## Read-only installed-size audit (2026-10-30)

For a saved personal toolkit, `python -I scripts/kit_footprint.py --kit MyKit.json --root D:\\MyPortableApps` reports logical file bytes of **currently managed and matching** pinned folders. `--max-mib 100` optionally checks a logical-byte budget; any missing/research/OS selections produce UNKNOWN rather than fake PASS. `--out MyKit.footprint.json` creates a new-only local JSON and matching console-evidence log. No vendor binaries, network, OS changes or downloads. See [footprint guide](docs/FOOTPRINT_AUDIT.md). Real NTFS disk allocation and compressed package sizes are separate measurements.

> **Current SSOT (2026-10-30):** Catalog 19 SHA-pinned, 108 canonical research (19/27/62), plus 43 additional research candidates; 151 selectable IDs (19 pinned / 27 built-in / 105 unverified). Historical counts in dated sections below explain past phases, not today's installation status. Start continuation at [2026-10-30 current handoff](docs/handoff/START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md). Actual current source files always override snapshots.


## Metadata-only offline asset checklist (2026-10-30)

After creating a personal kit, use `python -I scripts/offline_assets.py list --kit MyKit.json` to see official original filenames and exact catalog SHA-256; `export --kit MyKit.json --out MyKit.assets.json` creates new-only metadata plus matching local log; `verify --kit MyKit.json --archive-dir D:\ApprovedVendorArchives` checks **all** selected pinned original files using the unchanged offline SHA preflight before any installation. [Offline guide](docs/OFFLINE_ASSETS.md). **No download, vendor binary bundling, third-party redistribution, service/driver, or automatic installation** is performed. Research-only and OS-native tools are listed as exclusions; vendor/legal/EDR approvals remain independent.


## Optional visual personal-toolkit picker (2026-10-30)

Run `scripts\MyToolkitGUI.cmd` on an **authorized non-production Windows desktop with Python 3.11+ and Tkinter available**, or `python -I scripts/toolkit_picker.py`. The optional zero-dependency (beyond standard-library Tk) UI searches the entire current **151-ID** research/catalog union, filters by one-of-ten primary domains and approval state, multi-selects, imports a *validated* existing personal JSON, and saves a **new** pinned JSON + exactly mirrored local console evidence. **The window never installs/downloads/updates software or modifies services, drivers, shell, registry or PATH.** Install only with the separate existing CLI `scripts\MyToolkit.cmd build --kit ... --yes` after plan and permission checks. Python distributions without Tk can keep using the CLI without changes. [UI guide](docs/PERSONAL_KITS.md). Real visual/UI workstation acceptance and screenshots are NOT_VERIFIED by headless CI.


## Build your own portable toolkit (2026-10-25)

Every known tool is now *selectable* into your own reusable JSON toolkit, but only the **19 verified SHA-pinned** tools are installable. Use [Personal Kits guide](docs/PERSONAL_KITS.md), `scripts/MyToolkit.cmd` or `python -I scripts/my_toolkit.py`. The separate inventory union has **151 IDs = 19 pinned + 27 Windows native + 105 unverified research items**. Unverified items can be saved and planned, never silently installed.

```cmd
scripts\MyToolkit.cmd list --all
scripts\MyToolkit.cmd create --name my-support --preset essentials --tool ripgrep --tool duckdb-cli --out MySupport.json
scripts\MyToolkit.cmd plan --kit MySupport.json --root D:\MyPortableApps
scripts\MyToolkit.cmd build --kit MySupport.json --root D:\MyPortableApps --offline-dir D:\ApprovedVendorArchives --skip-pending --yes
```

`create` writes a new profile plus exact matching local console evidence; `plan` never mutates disk; `build --yes` reuses the existing validated per-tool installer. Research-only items block the whole build unless the user explicitly supplies `--skip-pending`. No new tool binaries, auto updates, services, drivers, registry/OS path edits, active network probes or releases are enabled. All archives must be separately approved and acquired by the user. This is the initial Very Simple CLI; optional GUI tooling remains deferred.


## New enterprise/industrial portable-tool intake (2026-10-25)

A [53-family DOCX research crosswalk](research/INTAKE_ENTERPRISE_PORTABLE_20261025.json) is now kept **separately** from the 17-item approved install catalog and the existing 108-record canonical candidate ledger. [Review and correction notes](research/ENTERPRISE_PORTABLE_REVIEW_20261025.md) explain 5 already-pinned items, 5 existing research items and 43 *new research-only* suggestions, including industrial protocols, large logs, ergonomics and IIoT. This is metadata only; no new vendor binary, service/driver, internet access, industrial listener or automatic settings change is approved. See [the 2026-10-25 handoff](docs/handoff/PORTAKIT_HANDOFF_20261025_ENTERPRISE_RESEARCH.md).

## 2026-10-23 R2 quality and ZIP safety review

The [R2 MECE/code/security audit](docs/review/2026-10-23_RECURSIVE_MECE_AUDIT.md) and [current public-safe handoff](docs/handoff/PORTAKIT_HANDOFF_20261023_R2.md) describe the bounded ordinary-ZIP extraction hardening, independent regression tests and remaining **human/not-verified** release gates. The older handoff links below remain historical evidence, not the current Git main SHA. **Do not use this project as permission to redistribute vendor packages or to operate on production systems.**

> **Latest verified conversation handoff (2026-10-22):** [Complete source/decision/evidence map](docs/handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md) · [One copy-ready next-chat prompt](docs/handoff/START_NEW_CHAT_PORTAKIT_20261022.md) · [48-file baseline source map](docs/handoff/2026-10-22_REPO_SOURCE_MAP.json). The most recent live main plus `catalog.json` and `toolsets.json` supersedes dated historical counts. Company GUI/Office/licensing acceptance remains NOT_VERIFIED.

Small Windows portable app manager. Python 3.11+, standard library only. Windows only; run one operation at a time.

## Air-gapped local vendor archive installation (explicit opt-in)

The normal `install` command still downloads a pinned HTTPS asset. On a **fully disconnected company PC**, stage the **original, byte-unchanged vendor .ZIP/.EXE files** from an approved external transfer first, then use **offline flags**. The existing independent SHA-256 catalog pin is verified again locally; no URL is contacted.

```powershell
# One exact vendor package (offline, no network):
python -I portakit.py --archive "D:\Approved\grepWin-x64-2.1.12_portable.zip" install grepwin

# Entire optional profile; folder must contain all five originals for fresh installs:
.\scripts\Toolsets.cmd plan portable-productivity
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"

# View the other compact GUI/data tools, unchanged defaults:
.\scripts\Toolsets.cmd plan files-and-logs
```

**Safety:** the group checks **all** missing packages and their SHA-256 before installing anything. A missing/tampered item aborts with no partial installation. Running it again skips matching installed pins. `--offline-dir` does not auto-configure recommended plugins (those may need more external assets), and `--archive` plus `--recommended` is refused. Use ordinary approved `update` only when explicitly requested; no per-user PATH/registry/service changes during file installation.

Five second-wave additions: **7zr** (very small **7z-only CLI**, *not* a substitute for 7-Zip's ZIP/GUI), **Everything Desktop** (file index/search; only install the ZIP, launching can prompt for privileged NTFS indexer service), **grepWin** (regex GUI search), **Miller** (CSV/TSV/JSON CLI), and **dasel** (cross-format structured data CLI). GUI launch and system indexing are **not** implied by installation and require separate user-workstation policy review.

See [offline toolset and licensing notes](docs/TOOLSETS.md). **Full 7-Zip 26.04 is now a separate opt-in `7zip` ID:** its official SHA-256-pinned x64 installer is **never run**, only extracted as verified 7z SFX data using the already installed/byte-verified `7zr`. The full GUI `7zFM.exe` and complete `7z.exe`+`7z.dll` are installed locally, without registering shell associations. Actual user-workstation GUI acceptance remains pending.


## Complete 7-Zip (optional, vendor installer never launched)

To get **full 7-Zip** GUI/CLI, not only the 7z-only `7zr`, install the exact official `7zr` prerequisite first. The independent `7zip` ID uses the official **26.04 x64 SFX executable as a verified archive**, not as an installer or process.

```powershell
# Installed from approved original files, fully offline:
python -I portakit.py --archive "D:\Approved\7zr.exe" install 7zr
python -I portakit.py --archive "D:\Approved\7z2604-x64.exe" install 7zip

# Optional group includes both prerequisite and full 7-Zip in safe order:
.\scripts\Toolsets.cmd plan portable-productivity
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"

# Manual launch (GUI user acceptance not automated):
.\portable\7zip\7zFM.exe
# Full ZIP format support:
.\portable\7zip\7z.exe
```

The 7zip installer is **never executed**: PortaKit checks vendor SHA-256, checks the separate managed 7zr.exe's own installed SHA-256, prevalidates archive member names, case collisions, encryption/symlinks and expanded size, and only then extracts to a private stage and promotes it atomically. Its x64 GUI is not started in CI; context-menu/registry options remain separate, disabled by default.

## Quickstart

```powershell
python -I portakit.py list
python -I portakit.py install jq
.\portable\jq\jq.exe --version
python -I portakit.py update jq
python -I portakit.py remove jq
```

The default root is `portable`, relative to the current directory. No PATH edits, no shims.

## Optional categorized toolsets — 10 MECE domains + reusable profiles

**Default installation remains unchanged.** Each SHA-256-pinned tool has exactly one **primary functional category**, verified by tests: `files`, `text`, `structured-data`, `system`, `network`, `security`, `development`, `automation`, `documents`, `transfer`. A **profile** composes tools across those boundaries without installing duplicate copies. Historical selector names continue working but are no longer canonical taxonomy categories.

There are **11 directly installable SHA-pinned tools**, including eight new lightweight ZIP binaries (together ~19.34 MiB compressed): `ripgrep`, `fd`, `fzf`, `bat`, `sd`, `yq`, `delta`, `hyperfine`. A separate [107-tool research register](research/TOOLS_CANDIDATES_20261020.json) includes Windows built-ins and unverified candidates; those are **not** automatically installable.

```powershell
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan essentials
.\scripts\Toolsets.cmd plan lightweight
.\scripts\Toolsets.cmd plan incident-response
.\scripts\Toolsets.cmd apply lightweight --yes
# Optional vendor-recommended settings and plugins for newly installed editors only:
.\scripts\Toolsets.cmd apply essentials --yes --recommended
# Legacy scripts continue to resolve their frozen original selections:
.\scripts\Toolsets.cmd plan common
.\scripts\Toolsets.cmd plan mes-support
```

`list` and `plan` do not modify any files or download software. `apply --yes` installs only missing SHA-pinned binaries, skips matching managed versions, never silently updates or overwrites user settings, never registers Explorer context menus, and produces console-mirrored evidence logs. [Detailed domain/profile contracts](docs/TOOLSETS.md) · [107 candidate entries](research/TOOLS_CANDIDATES_20261020.json) · [original enterprise TOP 30](docs/RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md).

## Commands

`list | install ID | update ID | configure ID | remove ID`. Global flags: `--json`, `--root DIR`, `-h/--help` (human text, exit 0, never an envelope).

- `install ID` downloads the pinned asset, verifies its SHA256, extracts it into a stage folder and renames the stage to `ROOT\<dest>`. An installed ID is refused (use `update`); an existing `dest` or `dest.old` is treated as unmanaged and refused (delete or rename it).
- `update ID` compares the installed `version` and `sha256` with the catalog pin. Any difference (up, down, or a new digest at the same version) updates; identical with the folder present is a no-op without downloading (`changed: false`); a missing folder is repaired. Files and folders listed in `preserveOnUpdate` are copied from the old folder over the packaged copies. To force a reinstall of an identical pin, `remove` then `install` (preserved paths are not kept).
- `configure ID` explicitly applies recommended settings and missing verified plugins to a **currently managed** installation, without re-downloading the application. Only an exact catalog-pin match is accepted; run `update ID` first if pins differ. The tool copies the existing directory into a private staging folder, checks for links/junctions, changes only the selected recommended settings and missing plugin paths, and swaps with rollback. Other files and settings are preserved; running it again is a no-op. **Close the editor first.**
- `remove ID` deletes `dest`, then `dest.old`, then the state entry last, and removes everything in `dest` including user data. It never loads the catalog and touches nothing else.

### Plugins and updates

Notepad++'s pinned **standard portable ZIP** includes its bundled plugins and Plugins Admin; WinMerge installs only the plugins shipped in its chosen archive. PortaKit installs additional pinned Notepad++ plugins **only** on `install --recommended` or `configure`; otherwise it leaves third-party plugin installation to each application.

For the shipped catalog, updated versions keep additional plugin files under `notepad++/plugins` and `winmerge/MergePlugins` using `preserveMissingOnUpdate`. Files included in the new vendor package always win at the same path (including the Notepad++ plugin list DLL); absent user-added files are copied to the staged version. This avoids forcing old bundled plugin binaries back over the updated distribution, but any extra plugin may still be incompatible with a newer application. If a plugin was removed by the vendor it can remain from the old installation; review third-party plugins after upgrades. Do not use `remove` followed by `install` to retain plugins: `remove` deletes them.


## Layout, lock, state

Under the root: `<dest>\`, `<dest>.old` (the only backup name), `.portakit-state.json` (`{"id":{"version","sha256","dest"}}`), `.portakit-lock` (held for the whole operation; a second portakit exits 6) and temporary `.portakit-*.tmp` files, wiped at the start of each install, update or remove. `list` reads only the catalog: it takes no lock and does not clean temporary files.

An update renames `dest` to `dest.old`, renames the stage to `dest`, writes the state, then deletes `dest.old`. If a crash leaves only `dest.old`, the next `update` renames it back. If both `dest` and `dest.old` exist, the operation stops with exit 5 and the message `... both exist; if <dest> is good delete <dest>.old, else delete <dest> and rename <dest>.old to <dest>`. Do that, then retry. A `dest.old` that could not be deleted after a successful update is reported as one `warning:` line on stderr.

## Envelope and exit codes

With `--json`, stdout is exactly one object `{"ok","command","data","error"}`; `error` is `null` or `{"code","message"}`. Without it, results go to stdout and errors to stderr.

`data`: `list` -> `{"items":[catalog entries]}` (human: `id<TAB>version`); install/update -> `{"id","version","dest","changed"}`; remove -> `{"id"}`.

| Exit | error.code | Meaning |
| --- | --- | --- |
| 0 | - | success (including a no-op update) |
| 1 | usage | bad args, flags or arity; unknown ID for install |
| 2 | catalog | invalid catalog |
| 3 | fetch | network, HTTP, size cap or SHA256 mismatch |
| 4 | archive | corrupt zip, zip-slip, links, duplicates |
| 5 | state | bad state; already installed / not installed / not in catalog; dest changed; dest is a file, link or unmanaged folder; `dest` and `dest.old` both exist; any other filesystem failure |
| 6 | busy | lock held by another portakit, or the target is in use by a running app |

## Catalog

`catalog.json`, beside `portakit.py`, holds `{"tools": [...]}`. Every entry is `id`, `version`, `url` (a pinned release asset), `sha256` (64 hex), `artifact` (`zip` or `exe`; an exe installs as `ID.exe`), `dest` (one folder name) and optional `preserveOnUpdate` and `preserveMissingOnUpdate`. Downloads are capped at 100 MiB and verified before extraction; each install or changed/repair update downloads again (no cache). Mutable URLs with a `latest` path segment are rejected.

Digests: the notepad++ digest comes from the [release notes](https://github.com/notepad-plus-plus/notepad-plus-plus/releases/tag/v8.7.5), winmerge from the [Scoop manifest](https://github.com/ScoopInstaller/Extras/blob/777b50f8467b011b55f20a8790f2d8712b839663/bucket/winmerge.json) and jq from the [Scoop manifest](https://github.com/ScoopInstaller/Main/blob/da6f69ed0016a805c16d9d3d78386068a409da3a/bucket/jq.json). These are published hashes, not locally computed ones.

To bump a pin, edit `version`, `url` and `sha256` together. Configuration seeding is **opt-in** through `install ID --recommended`; no profiles apply to ordinary installations.

## Recommended setup (opt-in)

```powershell
python -I portakit.py install notepad++ --recommended
python -I portakit.py install winmerge --recommended
# Already installed via PortaKit:
python -I portakit.py configure notepad++
python -I portakit.py configure winmerge
```

- Without `--recommended`, `install` behaves exactly as before. The flag is accepted **only by install**, not update/configure/remove/list. To opt in on an existing PortaKit-managed installation, run `configure ID`; ordinary install/update never silently adds third-party plugins.
- Notepad++: local portable configuration, 4-space indentation; additionally download and SHA-256 verify the **x64 ComparePlus 3.0.0** and **JSON Tools 8.5** plugin ZIPs from their pinned upstream GitHub releases. Extract into `plugins/ComparePlus` and `plugins/JsonTools`. These are executable third-party DLLs; the flag is explicit consent to running third-party plugins when the editor starts. Upstream pins are checked against the official Notepad++ x64 plugin list; upgrades require explicit catalog review.
- WinMerge: verify that the pinned vendor ZIP contains **CompareMSExcelFiles.sct**, **CompareMSWordFiles.sct**, **CompareMSPowerPointFiles.sct**, and **CompareMSVisioFiles.sct** in `MergePlugins/`; never download duplicates. Seed `WinMerge.ini` in WinMerge's actual `[WinMerge]` format (`Settings/ViewLineNumbers=1`, `Settings/PluginsEnabled=1`, `Settings/UnpackerMode=1`) so its bundled Office unpackers are automatically selected by extension. These scripts require the corresponding desktop **Microsoft Excel, Word, PowerPoint, or Visio** application installed; they compare extracted text/content, not original visual formatting. Without Office installed, those comparisons cannot work. No Office programs are installed by PortaKit. WinMerge may still use some Windows registry data even with an INI; this setup does **not** change file associations or add Explorer shell integrations.
- Downloads are pinned and verified **before** staging is committed. Any plugin failure aborts the new installation, leaves no managed destination/state entry, and cleans temporary files. Existing files are not adopted or overwritten.
- Profiles seed new installations, or are applied explicitly with `configure ID` to an existing managed installation. Updates retain the config and extra plugin files per the existing preservation rules. `remove` deletes all managed data, including added plugins and settings. Stop the editor before updating.

## Optional Windows Explorer right-click menus (current user only)

All application installations remain **portable and registry-free by default**. To add a **reversible, classic** Windows Explorer context menu, use explicit opt-in from the repository directory:

```powershell
# Must have already installed the corresponding tool via PortaKit.
python -I scripts/context_menu.py install notepad++
python -I scripts/context_menu.py install winmerge
# Inspect the exact HKCU menu entries before/after registration.
python -I scripts/context_menu.py status notepad++
python -I scripts/context_menu.py status winmerge
# Unregister before moving your portable root or removing the app.
python -I scripts/context_menu.py remove winmerge
python -I scripts/context_menu.py remove notepad++
```

The equivalent simple CMD entrypoint is `scripts\ContextMenu.cmd install|status|remove notepad++|winmerge`. If PortaKit was installed under a different root, add `--root "D:\My Portable Apps"`. The script creates a unique plain-text log for each run under `ROOT\.portakit-evidence\` with the **same lines as console output**; use `--log-file PATH` to override. Commands are idempotent and **do not require administrator privileges**.

Notepad++ adds **Edit with Notepad++ (PortaKit)** when right-clicking a file. WinMerge adds **Compare with WinMerge (PortaKit)** for one file or folder; WinMerge opens the selected path, and you choose the second comparison path in WinMerge. **These are not** the full vendor two-selected-items Explorer COM shell-extension commands. That advanced integration is optional backlog work, not installed here.

Only unique PortaKit-owned keys under `HKEY_CURRENT_USER\Software\Classes\...\shell\` are written. Foreign/modified keys are **never overwritten or removed**, nor are file associations, PATH, COM DLLs or global registry modified. On Windows 11, this classic action may require **Show more options / Shift+F10**. After moving the portable app folder, remove the old owned shell entries and register them again at the new path. Ordinary `install`, `configure`, `update` and `remove` do not change the registry.

Review: [all component decisions](docs/COMPONENT_REVIEW_20261020.md); [backlog](docs/BACKLOG.md); [official Notepad++ shell options](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/shell-extension.md); [official WinMerge Explorer integration](https://manual.winmerge.org/en/Open_paths.html).

## WinMerge executable and Office acceptance

The Windows live workflow now **actually launches WinMergeU.exe** on synthetic identical/different text files, checks exit codes 0/1 and HTML report generation, and uploads its console transcript and reports as an Actions artifact. This verifies the executable, not Microsoft Office integration.

For `.xlsx` / `.docx` / `.pptx` / `.vsdx` comparison, run the evidence-producing [WinMerge Office acceptance guide](docs/WINMERGE_OFFICE_ACCEPTANCE.md) on an interactive Windows PC with the corresponding licensed Office app. The PS2/5-compatible scripts accept a new isolated evidence directory and never install Office or touch real documents. Missing Office is recorded as **NOT VERIFIED**, not PASS. Actual GUI behavior needs a separate human check.

Office prerequisites can be inventoried on a Windows machine **without launching Office** by running `scripts/WinMerge-OfficeAcceptance.ps1 -ProbeOnly`. Results for Excel, Word, PowerPoint and Visio are saved as a transcript and CSV with status `NOT_VERIFIED`, regardless of whether their COM registrations exist. The live Windows CI also checks vendor-provided Office extension filters and automatic selection declarations; actual Office COM and GUI document comparison remain a separately required acceptance gate. See the [Office acceptance guide](docs/WINMERGE_OFFICE_ACCEPTANCE.md).

## One-run Office 4 acceptance and evidence

On an **interactive disposable Windows PC** with Python 3.11+, run `scripts\Run-WinMerge-Office4.cmd` to inspect all four Office comparison integrations in one pass. The launcher automatically performs a pinned `install winmerge --recommended` if no managed installation exists, or `configure winmerge` for an existing matching catalog pin. It never silently updates mismatched versions or removes user documents.

For a safe registration-only probe that **never launches Office**, run:

    scripts\Run-WinMerge-Office4.cmd -ProbeOnly

For actual four-app acceptance, first close all Office documents and run:

    scripts\Run-WinMerge-Office4.cmd

The script creates a uniquely named evidence folder plus a local ZIP and SHA-256 sidecar. The ZIP includes the exact console transcripts, CSV status per application, synthetic Office documents, HTML reports and a SHA-256 file manifest. **Nothing is uploaded.** Exit `0` means real Office integration passed, `1` failed, and `2` means prerequisites were unavailable / NOT VERIFIED (probe mode always returns 2). The real test checks that the HTML diff contains the synthetic `BASELINE` and `DIFFERENT` values; ZIP-only binary comparison cannot pass by accident.

See [step-by-step Office acceptance guide](docs/WINMERGE_OFFICE_ACCEPTANCE.md). Hosted GitHub runners lack licensed Office and can only test the `-ProbeOnly` flow.

## Independent verification of Office4 evidence

Any Windows/Linux machine with Python 3.11+ can validate an Office4 result ZIP **without running Office or WinMerge**:

    python -I scripts/verify_office_evidence.py --zip "office4-evidence-....zip"

The read-only verifier cross-checks the SHA-256 sidecar, ZIP entries, per-file manifest hashes, CSV statuses for all four Office applications, and the actual synthetic content markers in diff reports for every PASS. Its result JSON distinguishes `verified:true` (evidence internally sound) from `office_runtime:PASS` (Office 4 actually passed). To require full integration before moving to release use `--require-pass`: exit 0 only for four-app PASS, exit 2 for sound but incomplete/failed results, exit 1 for invalid or tampered evidence. The one-run launcher also invokes this verifier before returning.

## Verification and releases

Pull requests and `main` run the [Windows regression workflow](.github/workflows/windows-tests.yml) on Python 3.11 and 3.14. It uses mocks (no real app downloads). Before publishing, follow the [manual release acceptance checklist](docs/RELEASE_CHECKLIST.md), including isolated live downloads and full catalog verification. CI does not publish releases.

## Tests

```powershell
python -I -m unittest discover -s tests
```

Tests use temporary folders, mock ZIPs and injected downloaders; no network.

## Docs

See `docs/SPEC.md` (contract), `docs/DECISIONS.md` (ratified decisions), `docs/HANDOFF.md` (open work).

## License

[MIT](LICENSE), copyright 2026 greatgc-flow.

## Non-production GUI acceptance and Sysinternals network licensing

The portable installer never launches Everything, grepWin, or 7-Zip. A separate **user-invoked** [Windows GUI acceptance harness](docs/GUI_ACCEPTANCE_20261021.md) checks installed pins and local EXE SHA without opening windows, then (only with explicit consent) helps a human review the GUI on synthetic files while saving exact console lines to local evidence.

```powershell
.\scripts\GuiAcceptance.cmd --tools everything grepwin 7zip
.\scripts\GuiAcceptance.cmd --review --launch --tools grepwin 7zip
# Elevated/service/NTFS index first-run risks require a SECOND explicit flag:
.\scripts\GuiAcceptance.cmd --review --launch --allow-everything-first-run --tools everything
```

**TCPView/PsPing remain metadata-only** in [corporate license and deployment intake](research/SYSINTERNALS_NETWORK_REVIEW_20261021.json), not automatically installable. Microsoft allows free company-device use but restricts third-party redistribution; PsPing is inside PsTools (which contains powerful unrelated administrative commands). Do not package vendor binaries into PortaKit or a shared internal bundle without corporate legal approval. No active network probes run by default.
