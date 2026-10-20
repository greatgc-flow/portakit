# portakit

Small Windows portable app manager. Python 3.11+, standard library only. Windows only; run one operation at a time.

## Quickstart

```powershell
python -I portakit.py list
python -I portakit.py install jq
.\portable\jq\jq.exe --version
python -I portakit.py update jq
python -I portakit.py remove jq
```

The default root is `portable`, relative to the current directory. No PATH edits, no shims.

## Optional categorized toolsets

Toolsets are an **opt-in composition layer**, not a change to default installation. `toolsets.json` groups the existing SHA-pinned catalog into **Common, OS, NW, Development, Data and Diagnostics** and profiles including `minimal`, `mes-support` and `developer`. The same tool can belong to multiple categories but is only installed once. Network-specific binaries are currently **backlog candidates, not verified installs**.

```powershell
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan mes-support
.\scripts\Toolsets.cmd plan common nw --include jq --exclude winmerge
.\scripts\Toolsets.cmd apply mes-support --yes
# Optional recommended editor plugins/settings for NEW installs only:
.\scripts\Toolsets.cmd apply developer --yes --recommended
```

`plan` never writes or downloads. `apply --yes` installs missing catalog-pinned apps only, skips already installed ones, refuses stale/unmanaged destinations (no silent updates), never touches right-click registry menus, and records console-equivalent logs. Existing core commands remain unchanged. See the [toolset design, category review and backlog](docs/TOOLSETS.md).

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
