# portakit specification
Windows CLI, Python 3.11+ stdlib only, single module `portakit.py` + `catalog.json`. No JSON schemas.
Commands: `list | install ID | update ID | configure ID | remove ID`; global `--json`, `--root DIR`.
MVP tools: notepad++, winmerge, jq (single exe). Limits: 100 MiB download cap, reserved names (`.portakit*`, `*.old`), single-root zip flatten.
Out of scope: download cache, automatic or silent configuration, offline bundles, doctor, pip tools, shims, general nested/plugin destinations, installed status in `list`, and force reinstall flags. Exception: `install ID --recommended` for new installs and explicit `configure ID` for existing managed installations.

## Optional category/profile composition contract

- Add a separate file `toolsets.json` (`schemaVersion=1`), whose `categories` list maps validated names to zero or more existing **catalog tool IDs** and whose `profiles` map names to valid category IDs. The same catalog ID can appear in multiple categories; selection resolves in order and deduplicates. No download URL, arbitrary command or shell-configuration action is ever read from this manifest.
- Separate `scripts/toolsets.py` and `scripts/Toolsets.cmd`, not core `portakit.py` command changes. `list` displays available categories/profiles; `plan CATEGORY/PROFILE...` evaluates managed state **without creating directories, locks or logs**. `--include ID` and `--exclude ID` must name tools in the validated pinned catalog; unknown names and duplicates within each group are rejected. `--manifest` optionally supplies a validated custom selection manifest.
- `apply CATEGORY/PROFILE... --yes` requires explicit consent and delegates to original `portakit.py --json install ID` subprocess per newly missing catalog ID, in deterministic order, using its SHA-pinned downloads and root lock. Already installed exact pins are skipped (including no silent `configure`); stale pins, unmanaged/broken destinations, backup leftovers, and reparse paths block the entire plan **before downloading**. Apply is also serialized via a separate batch lock.
- `--recommended` on `apply` adds the existing opt-in recommended editor configuration **only when installing new editors**, never silently modifying existing ones. Nothing invokes Explorer shell integration. `plan`/ordinary core commands do not apply recommended settings.
- Batch apply has **per-tool atomicity** and no cross-tool rollback: stop after a failure, preserve already successfully installed tools, report partial results and let rerun skip completed IDs. Removing entire categories is unsupported because `portakit.py remove` deletes the app and its local user data.
- Displayed apply output is copied verbatim into an exclusively created UTF-8 file under `ROOT\.portakit-evidence\` (or `--log-file`). All toolset operations use the existing Windows/Python 3.11+ compatibility baseline.
- An empty curated category such as the initially unpinned NW category must be reported transparently and never trigger an unauthorized download, implicit network scan, Npcap driver install, or placeholder binary.

## Optional Explorer context menu (separate script contract)

- Implementation: `scripts/context_menu.py`, Windows / Python 3.11+ standard library (`winreg`). The PortaKit core CLI and its JSON contract, state format, install/configure/update/remove semantics and no-registry default **do not change**.
- `python -I scripts/context_menu.py install|status|remove {notepad++,winmerge} [--root DIR] [--log-file PATH]` or `scripts/ContextMenu.cmd`. Only explicit `install`/`remove` mutate registry. Status reads registry and records a local console log.
- Restrict all registry writes to `HKCU\Software\Classes\*\shell\PortaKit.NotepadPlusPlus.File`, `HKCU\Software\Classes\*\shell\PortaKit.WinMerge.File`, and `HKCU\Software\Classes\Directory\shell\PortaKit.WinMerge.Folder`, plus fixed `command` child; never write HKLM, HKCR, file associations or COM DLL registration.
- The installation target must be a non-symlink executable inside an existing, managed root whose `dest` equals the catalog tool destination; construct quoted `"EXE" "%1"` shell command. File/folder WinMerge menu handles *one* Explorer selection; user specifies the second path in WinMerge. Multi-select and Compare To COM behavior are out of scope and tracked separately.
- Each key uses a unique PortaKit namespaced name and exact `PortaKitOwner` value. Status reports `absent`, `owned`, `foreign` or `modified`. Install refuses any foreign/modified key and never overwrites it; repeat install with matching command is no-op. Remove deletes only matching owned keys (also when EXE no longer exists); refuses modified or foreign keys. Preflight all applicable keys before writes. A create failure triggers best-effort cleanup of only keys originally absent.
- Console output is duplicated into a unique UTF-8 log under `ROOT\.portakit-evidence\` or the explicit `--log-file`. The log is created exclusively and never overwritten. No automatic menu action occurs on regular app installation or removal.
- Windows 11 classic menu may need Show More Options / Shift+F10. A moved portable root invalidates hard-coded absolute menu paths; unregister before moving/re-register afterward. User must opt in and can reverse any time.

## 0. Opt-in recommended installation

- Optional global `--recommended` is valid only for `install ID`; all other commands return usage 1. `configure ID` explicitly applies recommendations without the flag. When absent, all original behavior remains unchanged; state schema and result envelopes are unchanged.
- `recommended` is an optional catalog object: `{ "settings": "notepad++-dev"|"winmerge-dev", "plugins": [{ "id", "version", "url", "sha256", "dest", "requiredFile" }] }`. Validate all entries at catalog load. Plugins require pinned HTTPS URL, 64-hex SHA, destination `plugins/<name>`, and a top-level DLL file name, with at most 8 unique plugin destinations. Settings profile must match tool ID. Only shipped Notepad++ x64 profile requests external plugins; WinMerge profile seeds local INI and requires bundled vendor Office scripts. Optional `bundledPlugins` (WinMerge only) must be a list of up to 20 unique single-segment `.sct`/`.dll` filenames within `MergePlugins`, validated at catalog load and checked in the freshly extracted stage before commit. Generic package installation is not a supported feature.
- On an opted-in `install`, download and safely unpack the normal application to a private stage. Apply recommended settings to this stage (Notepad++ portable marker, XML TabSetting 4/yes; WinMerge portable INI `[WinMerge]` section with `Settings/ViewLineNumbers=1`, `Settings/PluginsEnabled=1`, and `Settings/UnpackerMode=1` (verified against upstream 2.16.46 OptionsDef.h / IniOptionsMgr.cpp)), then download each pinned plugin to a private temp, enforce existing 100 MiB SHA-256 and safe ZIP rules, extract under the plugin's destination and assert `requiredFile` exists. Refuse pre-existing plugin destination; never overwrite packaged files. Commit the stage with the original two-phase rename/state process **only when all steps succeed**. Network, integrity, archive, config, or missing DLL errors abort with no managed install and temps cleaned.
- After install, updates preserve user configuration and third-party files through the original `preserveOnUpdate` and `preserveMissingOnUpdate` semantics. No additional auto-download of third-party plugin updates. No global PATH, registry modifications or automatic plugin execution by PortaKit; the editor may load plugins on launch.

## 0a. Configuring an existing managed installation

- `configure ID` requires an existing PortaKit-managed installation with the same destination, version, SHA-256 and a supported recommended profile as the current catalog. Otherwise abort; if pins differ, `update ID` must run first. It never downloads the main application.
- Refuse any reparse point, junction or symlink anywhere in the source installation. Make a private full staged copy, seed only selected recommended settings, check WinMerge bundled Office plugin scripts and download only missing SHA-pinned Notepad++ plugin archives. If an existing plugin directory is incomplete, refuse rather than overwrite its contents.
- Compare configuration bytes and plugin installation results. If there are no effective changes, discard the stage and return `changed:false`. Otherwise commit with the same reversible rename, state-write and rollback sequence as update, leaving the persisted state values unchanged.
- Existing unrelated files and settings are kept. Selected recommended settings can change by explicit user request. `configure` does not change the OS registry, PATH or Windows file associations; the target editor must be closed. Standard `update` never implicitly invokes configure.
- JSON result keys for `configure` are `id`, `version`, `dest`, `changed`. A second configure normally performs no downloads or modifications.

## 1. Root, layout, lock
- `--root` default `portable`, relative to the cwd. No PATH edits, no shims. install/update/remove mkdir ROOT (parents) before locking; `list` never does.
- Under ROOT: `<dest>\` (one path segment), `<dest>.old` (the only backup name), `.portakit-state.json`, `.portakit-lock`, and temps matching `.portakit-*.tmp`: `.portakit-stage-<id>.tmp` (dir), `.portakit-dl-<id>.tmp` (download), `.portakit-state.<hex>.tmp`.
- Lock: open (create) `.portakit-lock`, seek 0, `msvcrt.locking(fd, LK_NBLCK, 1)`; held for the whole op, released by Windows on process death. File stays empty. Held elsewhere -> exit 6, nothing touched. `list` takes no lock, reads only the catalog, and does not clean temporary files.
- After locking, delete every `ROOT\.portakit-*.tmp` (links inside are unlinked, never followed). A stage is never reused; `dest` only ever appears by one rename of a fully built stage.
- Only the state file is overwritten in place: written to a `.tmp`, then `os.replace`d (no partial files). The swap renames below never overwrite.

## 2. State
`{"<id>":{"version":"1.7.1","sha256":"<64 hex>","dest":"jq"}}`. Missing file = empty. Bad shape, invalid dest, or case-insensitive duplicate dests -> exit 5. An entry without `sha256` (v0.1.0 state) is accepted and compares as changed. No other migration.

## 3. Catalog
`{"tools":[...]}` beside `portakit.py`, fully validated on every load (so `list` also exits 2 on a bad catalog). Unknown fields ignored; the first invalid field is named.
| field | rule |
| --- | --- |
| id | `[a-z0-9][a-z0-9_+.-]*`, unique; `<id>.exe` must pass the path rule |
| version | nonempty string |
| url | required, `https://` with a host, no whitespace; a pinned release asset; reject any case-insensitive `latest` path segment after URL decoding |
| sha256 | 64 hex, normalized lowercase. `TODO`/placeholders rejected at load. README states published vs locally computed |
| artifact | `zip` or `exe` (exe installs as `<id>.exe`) |
| dest | one path segment; path rule; not `.portakit*`/`*.old`; unique case-insensitively |
| preserveOnUpdate | optional list (default `[]`) of paths under dest; path rule |
| preserveMissingOnUpdate | optional list (default `[]`) of existing plugin-directory paths under dest; path rule, each must be a directory at use time |

**Path rule** (syntax only; dest, preserve paths, `<id>.exe`, zip members): nonempty; `/` or `\` separators; no empty/`.`/`..` segments; no absolute/UNC/drive; no `:<>"|?*` or control chars; no segment ending in `.` or space; no device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9, with or without extension); stays inside its base.
**Link rule** (use time): reparse points/junctions/symlinks are never followed. If any existing component of a path being read, written or copied is one, the op aborts (exit 5; zip members: exit 4). Deletion never recurses through a link: a link is removed with `os.rmdir`/`os.unlink` only (read-only bits cleared first).
For every command, reject `--root` if it or any ancestor is a reparse point (exit 5), checking components before resolving links or `..` and before any other filesystem operation, including catalog/state reads, mkdir, lock creation, cleanup, or state writes.
**Precedence** (update): preserved > packaged.

## 4. Envelope and exit codes
`--json`: stdout is exactly one object `{"ok":bool,"command":str|null,"data":object|null,"error":null|{"code":str,"message":str}}`, incl. usage errors. Without `--json`, results go to stdout and errors to stderr. The only warning (a `dest.old` that could not be deleted) is one `warning: ...` line on stderr in both modes; it is not in the envelope. `-h/--help` is the sole exception: human text, exit 0, no envelope, even with `--json`.
`data`: `list` -> `{"items":[catalog entries]}` (human: `id<TAB>version`); install/update -> `{"id","version","dest":<abs path>,"changed":bool}` (no-op update: `changed:false`); remove -> `{"id"}`.
| exit | error.code | meaning |
| --- | --- | --- |
| 0 | - | success (incl. no-op update) |
| 1 | usage | bad args/flags/arity; unknown ID for install |
| 2 | catalog | invalid catalog |
| 3 | fetch | network/HTTP/size cap/SHA256 mismatch |
| 4 | archive | corrupt zip, zip-slip, links, duplicates |
| 5 | state | bad state; ID already installed/not installed/not in catalog; dest changed; dest is a file/link or an unmanaged dir; `dest` and `dest.old` both present; any other filesystem failure (message carries the OS error) |
| 6 | busy | lock held by another portakit, or PermissionError/sharing violation when renaming or deleting `dest` (target in use by a running app) |

## 5. Operations
Order: parse -> (install/update) load catalog -> mkdir ROOT -> lock -> delete temps -> read state -> **resolve ID** -> recovery (update only) -> dest-kind check (install/update) -> operate.
- **Resolve** (before any recovery or disk change): install: ID not in catalog -> exit 1; ID already in state -> exit 5 (points to `update`). update: not in state -> 5 `not installed`; in state but not in catalog -> 5 `not in catalog` (hint: `remove ID`); installed dest != catalog dest -> 5 `dest changed; remove ID and install again`. remove: not in state -> 5 `not installed`; remove never loads the catalog. The target's dest is now known (catalog for install, state for update/remove).
- **Destination ownership**: install refuses a destination owned by another state ID, case-insensitively (exit 5), even if its directory is absent. It never adopts or overwrites another ID's destination.
- **Recovery** (update only; target dest only; other `*.old` untouched; install never recovers, it refuses any existing `dest`/`dest.old`, see below), at most:
  - `dest` missing, `dest.old` present -> `os.rename` it back (crash between the swap renames).
  - both present -> abort 5: `<dest> and <dest>.old both exist; if <dest> is good delete <dest>.old, else delete <dest> and rename <dest>.old to <dest>` (also after a committed op whose `dest.old` delete failed).
- **Dest-kind check** (install/update): dest exists and is not a real directory (file or link) -> exit 5, nothing touched. install also refuses any existing `dest` or `dest.old` (unmanaged, exit 5, "delete or rename it"); this includes a complete dest left by a crash after the stage rename but before the state write: delete it and retry.
- **Fetch/extract**: download to `.portakit-dl-<id>.tmp` (size-capped), verify SHA256 BEFORE extract (mismatch -> exit 3, temp deleted, nothing installed); no cache; every install and every changed or repair update downloads. An identical-pin update with dest present does not download. Safe extract into `.portakit-stage-<id>.tmp`: zip-slip/absolute/link/special/duplicates rejected; single-root flatten; exe copied as `<id>.exe`.
- **Preserve (update)**: after extract, each `preserveOnUpdate` path is copied from the OLD dir (the current `dest`, still in place; never from `dest.old`) into the stage, replacing the packaged copy; absent paths skipped.
- **Preserve missing extras (update)**: after explicit preservation, for each `preserveMissingOnUpdate` directory copy old files/directories missing under the extracted stage (recursively). Existing packaged files/dirs win on conflicts; for shared directories, recurse and copy only missing descendants. Source directories containing reparse points abort with exit 5, without committing any changes. Absent sources skip; an existing source that is not a directory fails. This is for third-party plugins, not a substitute for a versioned catalog. Any old plugin absent from a newly shipped archive may remain, and compatibility is not guaranteed.
- **Swap** (install/update), using `os.rename` only (never `os.replace`/`shutil.move`, so an existing target makes it fail instead of being overwritten): (1) `dest` -> `dest.old` (skipped if dest absent); (2) stage -> `dest`; (3) write state (the commit point); (4) delete `dest.old`. Rollback applies only to failures before (3) completes, including (3) itself raising: if step 2 ran, delete the new `dest`; then `os.rename` `dest.old` back; state stays as it was. If rollback fails: leave both, exit 5 naming them (next op hits the both-present rule). PermissionError at step 1 or 2 -> exit 6, nothing changed. After (3) there is no rollback; if only (4) fails: success plus the stderr line `warning: could not delete <dest>.old; delete it before the next operation on <id>`.
- **update ID**: the catalog entry is the pin. Compare installed (`version`, `sha256`) with the catalog's: any difference (version up or down, or a changed digest at the same version) triggers the update, so pin changes always reach users; never "latest". Identical and dest present -> no-op without downloading, exit 0, `changed:false`. Dest absent -> repair: reinstall, `changed:true`. To force a reinstall of an identical pin, `remove` then `install` (preserveOnUpdate does not apply to that). The new state entry stores the catalog's `version` and `sha256`.
- **remove ID**: no recovery step. Delete `dest` (missing is fine; a link is unlinked, never followed; a regular file -> exit 5), then delete `dest.old` if present (both present is fine here), then **delete the state entry LAST** (state write). Any failure, including the state write, aborts with the entry kept (PermissionError -> 6, else 5); retry finishes. A crash leaves an entry without dest (retry `remove`, or `update` repairs), never a dest without an entry. Uses the state entry's dest. Removes everything in dest incl. user data; never touches other dirs or ROOT.

## Acceptance
Under `python -I`: malformed catalog (TODO sha256, unsafe paths, device-name id, non-https url) -> exit 2 naming the field; zip-slip -> zero files; bad SHA -> nothing installed; failed install/update keeps previous dest and state (incl. a failing state write); swap never overwrites an existing target; kill after each swap step recovers or aborts per sec. 5; stale stage is wiped, not reused; remove never leaves a dest without an entry; junctions are never followed or deleted through; resolve errors change no dest or state (ROOT and the lock file may be created); a changed `sha256` at the same version, or a state entry without `sha256`, triggers update; `--json` always one envelope, `-h` exits 0; second process -> exit 6; locked dest -> exit 6 with state unchanged; identical-pin update is a no-op only while dest exists; first run creates ROOT. End to end with no PATH/shims: `python -I portakit.py install jq` then `portable\jq\jq.exe --version` works.
