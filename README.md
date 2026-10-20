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

- Without `--recommended`, `install` behaves exactly as before. The flag is accepted **only by install**, not update/remove/list. Existing installations are not changed.
- Notepad++: local portable configuration, 4-space indentation; additionally download and SHA-256 verify the **x64 ComparePlus 3.0.0** and **JSON Tools 8.5** plugin ZIPs from their pinned upstream GitHub releases. Extract into `plugins/ComparePlus` and `plugins/JsonTools`. These are executable third-party DLLs; the flag is explicit consent to running third-party plugins when the editor starts. Upstream pins are checked against the official Notepad++ x64 plugin list; upgrades require explicit catalog review.
- WinMerge: verify that the pinned vendor ZIP contains **CompareMSExcelFiles.sct**, **CompareMSWordFiles.sct**, **CompareMSPowerPointFiles.sct**, and **CompareMSVisioFiles.sct** in `MergePlugins/`; never download duplicates. Seed `WinMerge.ini` in WinMerge's actual `[WinMerge]` format (`Settings/ViewLineNumbers=1`, `Settings/PluginsEnabled=1`, `Settings/UnpackerMode=1`) so its bundled Office unpackers are automatically selected by extension. These scripts require the corresponding desktop **Microsoft Excel, Word, PowerPoint, or Visio** application installed; they compare extracted text/content, not original visual formatting. Without Office installed, those comparisons cannot work. No Office programs are installed by PortaKit. WinMerge may still use some Windows registry data even with an INI; this setup does **not** change file associations or add Explorer shell integrations.
- Downloads are pinned and verified **before** staging is committed. Any plugin failure aborts the new installation, leaves no managed destination/state entry, and cleans temporary files. Existing files are not adopted or overwritten.
- Profiles seed new installations, or are applied explicitly with `configure ID` to an existing managed installation. Updates retain the config and extra plugin files per the existing preservation rules. `remove` deletes all managed data, including added plugins and settings. Stop the editor before updating.

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
