# Build your own PortaKit — 개인 포터블 툴킷 (2026-10-25)

## Optional approved-host offline plugin application

For plugin-containing v2 kits, host-only `MyToolkit.cmd build --skip-pending --yes` still never installs plugin DLLs. A separate controlled `python -I scripts/plugin_offline.py plan|verify|apply` is available **only** for individually selected ComparePlus/JsonTools pinned metadata, only when operator-supplied original ZIP hashes match, a managed pinned Notepad++ host is present, and separate `--yes --policy-approved` are supplied. All other plugins remain unapproved. The GUI remains selection-only. See [complete security, rollback and enterprise permission procedure](PLUGIN_OFFLINE_APPLY.md).

## Individually selected editor add-ons (metadata-only)

Use `scripts\MyToolkit.cmd plugins` for 6 separately named choices; during create, add `--plugin compareplus` and select its `--tool notepad++` host. The GUI now has a separate editor-plugin dropdown and Add/Remove controls. New plugin-containing files are schema v2 (version/SHA locked if vendor pinned as recommended, research-only otherwise); old no-plugin schema v1 remains unchanged. **No selected plugin is deployed by v2**: use `--skip-pending --yes` only to install pinned host tools, and do not combine v2 with `--recommended`. [Details](INDIVIDUAL_EDITOR_PLUGINS.md).

## Read-only footprint and size budget

After installing explicitly authorized pinned tools, run `python -I scripts/kit_footprint.py --kit MyKit.json --root D:\\MyPortableApps --max-mib 100`; add `--out MyKit.footprint.json` for a new-only JSON + exact console evidence log. This is **logical bytes measured only for existing managed pinned directories**, not a promise that pending/OS-only tools occupy zero space, nor physical NTFS allocation. [Full guide](FOOTPRINT_AUDIT.md). Unknown selections are not treated as a passing size budget.

> **Updated 2026-10-30:** 151 selectable IDs = 19 currently SHA-pinned + 27 OS built-ins + 105 research-only; installable *software choices* are only the current pinned subset. This does not certify corporate approval or vendor binary redistribution. For current authority use `catalog.json` and the research ledgers, not older historical handoffs.


## Metadata-only offline source checklist

For an existing user kit: `python -I scripts/offline_assets.py list --kit MyKit.json` displays the selected pinned original asset filename, URL and hash; `export --kit MyKit.json --out MyKit.assets.json` writes the new JSON metadata + mirrored log; `verify --kit MyKit.json --archive-dir D:\ApprovedVendorArchives` checks separately acquired, approved original files and logs the result before an explicit separate `build --yes`. Never confuse metadata/checksum validation with vendor redistribution permission. See [offline guide](OFFLINE_ASSETS.md).


## Optional mouse-based personal kit picker (2026-10-30)

On an approved interactive Windows PC with the **standard** Python 3.11+ distribution and optional Tkinter runtime, use:

```cmd
scripts\MyToolkitGUI.cmd
:: or
python -I scripts/toolkit_picker.py
```

The GUI is **optional**. Some embedded Python runtimes do not ship Tk; if it is unavailable or the desktop is headless, fall back to the fully supported `scripts\MyToolkit.cmd` commands below. GUI filters on all known IDs (current union 151, dynamic), on primary domain, and on explicit state **READY** (immutable catalog pins only), **OS_ONLY** (Windows built-in, informational) or **RESEARCH_ONLY** (unverified, never installed). Search supports Unicode and casefold. Multi-select highlighted, add all filtered, remove, approved-only, clear, add an existing *pinned-only* preset. Save a *new* `KIT.json` and exact console-mirrored `KIT.log` with no overwrite; optionally import existing `KIT.json`, with full schema/hash/pin verification. Old research candidates remain locked as research even if later promoted in the current catalog until the user deliberately deselects and reselects them.

**Safety-first interface:** the GUI only selects and saves. It deliberately has **no install/build/auto-download** button. Then inspect `scripts\MyToolkit.cmd plan --kit KIT.json` and separately authorize `scripts\MyToolkit.cmd build --kit KIT.json --yes`; any research-only item blocks building unless `--skip-pending` explicitly opts into an approved subset. Offline `--offline-dir` still requires original separately legally acquired, locally SHA-verified vendor archives. No program is automatically elevated, executed, redistributed or modified by the GUI.

**Validation boundary:** `tests/test_toolkit_picker.py` tests the GUI's pure model with no Tk or display; Windows CI parses the GUI source and verifies the CLI import path. **Live Tk window, appearance, accessibility, keyboard navigation, actual first run, and packaged Python/Tk availability require a separate human GUI acceptance on a non-production Windows PC.** No vendor binaries are bundled and there is no independent deployment engine.


> **Working implementation**, Windows/Python 3.11+ stdlib, no web UI, no new third-party packages. Built on the existing `scripts/toolsets.py` SHA-pinned installer. Personal selections are inert **JSON files** until explicit `build --yes`. No automatic service/driver, registry, PATH, shell, auto-update or Release change.

## A. One model, every tool selectable, each in exactly one primary domain

`scripts/MyToolkit.cmd` / `python -I scripts/my_toolkit.py` covers the *union* of the 108-entry canonical research register and the 43 unique research-only new software families from the supplied enterprise report: **151 unique selectable IDs** at this checkpoint, with 10 primary functional domains and cross-domain presets. Four statuses matter:
- `READY`: **19** current immutable SHA-pinned `catalog.json` installable tools; only these can be installed by PortaKit after explicit consent.
- `RESEARCH_ONLY`: **105** candidates (62 existing research-only, 43 newly inventoried); selectable/savable but **never downloaded or installed** until independent vendor/license/EDR/Windows approval and reviewed catalogue promotion.
- `OS_ONLY`: **27** Windows built-ins (some depend on OS optional features); selectable as notes; **never copied/installed** by PortaKit. They may not be present on every Windows image.
- **Category / preset**: compose only current 19 SHA-pinned entries, de-duplicate by ID, no scope creep if candidates appear later. Every ID belongs to exactly one primary domain; optional personal profiles are intentionally many-to-many.

All 151 selectable *IDs* do not imply all 151 are ready-made portable EXEs or that a family (e.g. a simulator SDK) is a complete runnable product.

## B. Commands (copy/paste from repository root in an approved nonproduction Windows workstation)

```cmd
rem Explore current SHA-pinned installable entries (19 as of 2026-10-30) (does not create files)
scripts\MyToolkit.cmd list

rem Browse all 151 candidates, filter by exactly one domain
scripts\MyToolkit.cmd list --all
scripts\MyToolkit.cmd list --all --category network

rem Create personal JSON kit + exact console transcript .log (no installation)
scripts\MyToolkit.cmd create --name my-support --preset essentials --tool ripgrep --tool duckdb-cli --tool tcping --out MySupport.json

rem Read-only plan (no downloads, files, registry or services touched)
scripts\MyToolkit.cmd plan --kit MySupport.json --root D:\MyPortableApps

rem This intentionally FAILS CLOSED because duckdb-cli/tcping remain research only.
scripts\MyToolkit.cmd build --kit MySupport.json --root D:\MyPortableApps --yes

rem Explicit safe partial installation from preapproved vendor archives only;
rem all selected original archives preflight SHA-256 before any install
scripts\MyToolkit.cmd build --kit MySupport.json --root D:\MyPortableApps --offline-dir D:\ApprovedArchives --skip-pending --yes

rem Or define a fully approved pinned kit (recommended before offline transfer).
scripts\MyToolkit.cmd create --name compact-ops --tool notepad++ --tool jq --tool ripgrep --tool 7zr --tool 7zip --out CompactOps.json
scripts\MyToolkit.cmd plan --kit CompactOps.json --root D:\MyPortableApps
scripts\MyToolkit.cmd build --kit CompactOps.json --root D:\MyPortableApps --offline-dir D:\ApprovedArchives --yes
```

Alternatively use `--category files`, `--category text`, `--preset lightweight`, or any combination, plus repeated `--tool` and `--exclude`. Duplicate IDs are removed deterministically and a selected `7zr` is moved before `7zip`, since official full 7-Zip SFX must be extracted as data by the verified prerequisite. Selecting `7zip` alone requires an already managed, matching `7zr`; there is no silent install.

## C. Three stages and recoverability

| Stage | Side effects | Validation |
| --- | --- | --- |
| `list [--all]` | Read-only | Known IDs, primary domains and strict install/research/OS boundary |
| `create` | Writes only **new** `KIT.json` plus same-basename `KIT.log`; refuses overwrite or junctions | Saved file includes exact selected IDs, `lockedPins` (version/SHA/dest), separate built-ins/pending snapshot |
| `plan --kit` | Read-only; prints installed/missing/blocked plus pending entries | Re-verifies saved pins against *current* catalog, version drift fails closed |
| `build --kit --yes` | Installs missing approved subset under `--root` only | Uses existing `toolsets.apply` locking, SHA, offline preflight, per-tool rollback, exact local console-evidence logs; no auto-update/removal |

**Default blocking rule:** If *any* research candidate is present in the kit, `build --yes` refuses to install anything. Use `--skip-pending` only when you explicitly accept a **partial toolkit**. Even if a research candidate is later promoted to an official pinned ID, old personal kit JSON keeps it noninstallable until recreated (fresh user consent). If an approved version/hash changes, a locked kit fails until newly reviewed/re-created; never silently upgrades.

Per-tool install is transactional; **whole-batch atomicity is not promised**. Already-installed matching tools are skipped. All original archives must be separately authorized to transfer and copied offline by the user; `--offline-dir` is **not** a source auto-downloader or general redistribution license. `--recommended` only affects new approved online editor installs and never happens by default; cannot combine it with `--offline-dir`.

`build` logs the actual toolset installer console at `ROOT\.portakit-evidence\personal-<timestamp>-<suffix>.log` (or explicit `--log-file`); `create` writes exact mirrored console text next to the JSON. `plan/list` default to read-only and intentionally do not write evidence files; for local read-only capture, redirect their console output to a locally approved file when needed. **No sensitive log is uploaded to the public GitHub repository**.

## D. Deliberate non-goals & acceptance gates

- Selection and export **do not grant** corporate-use/redistribution permission. Review the actual vendor EULA, release hash, signed binaries, runtime and offline dependencies, OS support, legal/EDR and package notices. Some 'portable' programs can still write settings or request privileges when launched; the catalog's GUI evidence gates remain open.
- No active probes, real SECS/GEM/PLC simulator listeners, service registration (NSSM), kernel drivers (com0com), non-default Everything indexing, clipboard persistence or unapproved outgoing links are enabled by building research-only selections.
- `PowerShell 2.x/5.x`, JDK 8 and Visual Studio 2015 constraints for enterprise scripts remain applicable; the PortaKit management tool itself already requires an approved Python 3.11+ runtime on Windows.
- **Not a graphical wizard yet.** This initial interface is a small documented CLI; a lightweight optional GUI/wizard can be designed separately if it materially improves adoption without creating heavyweight runtime dependencies.

## E. Regression and future growth

`tests/test_my_toolkit.py` validates 151 ID union, exact stage partition, profiles/categories selection and dedup, safe JSON evidence, no overwrite, pin locking, tampering, all-research block, explicit partial safe build, built-in-only no-op and 7-Zip prerequisite. Windows CI runs on Python 3.11 and 3.14 and checks isolated CLI `-I` imports.

Newly approved software should enter the canonical research and SHA-pinned install catalog only after independent review and separate PR; personal kits are not a shortcut into the trust boundary. Optional portable UI/wizard, device independent size budgeting and license-compliant export bundles can follow after verified user need.
