# portakit — SPEC v12 (FINAL RULING applied; design only; supersedes v1-v11)
Windows CLI, Python 3.11+ stdlib only, single module `portakit.py` + `catalog.json`. No JSON schemas.
Commands: `list | install ID | update ID | remove ID`; global `--json`, `--root DIR`.
MVP tools: notepad++, winmerge, jq (single exe). Kept from v1: 100 MiB download cap, reserved names (`.portakit*`, `*.old`), single-root zip flatten.
Cut: `kind`/github fields (every tool is a plain `url`+`sha256` entry; a GitHub asset is just its pinned release URL), state `schema`, download cache, `cleanupPending`, `defaultConfig`, `--force`, envelope `warnings`. Kept: `.old` recovery (update only), `preserveOnUpdate`, byte-0 lock, exit codes 0-6. Deferred: defaultConfig seeding (so no `doLocalConf.xml`/`WinMerge.ini` seeding in MVP), offline bundle, doctor, pip tools, shims, nested/plugin dests, installed status in `list`.

## 1. Root, layout, lock
- `--root` default `portable`, relative to the cwd. No PATH edits, no shims. install/update/remove mkdir ROOT (parents) before locking; `list` never does.
- Under ROOT: `<dest>\` (one path segment), `<dest>.old` (the only backup name), `.portakit-state.json`, `.portakit-lock`, and temps matching `.portakit-*.tmp`: `.portakit-stage-<id>.tmp` (dir), `.portakit-dl-<id>.tmp` (download), `.portakit-state.<hex>.tmp`.
- Lock: open (create) `.portakit-lock`, seek 0, `msvcrt.locking(fd, LK_NBLCK, 1)`; held for the whole op, released by Windows on process death. File stays empty. Held elsewhere -> exit 6, nothing touched. `list` takes no lock and reads only the catalog.
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
| url | required, `https://` with a host, no whitespace; a pinned release asset (never "latest") |
| sha256 | 64 hex, normalized lowercase. `TODO`/placeholders rejected at load. README states published vs locally computed |
| artifact | `zip` or `exe` (exe installs as `<id>.exe`) |
| dest | one path segment; path rule; not `.portakit*`/`*.old`; unique case-insensitively |
| preserveOnUpdate | optional list (default `[]`) of paths under dest; path rule |

**Path rule** (syntax only; dest, preserve paths, `<id>.exe`, zip members): nonempty; `/` or `\` separators; no empty/`.`/`..` segments; no absolute/UNC/drive; no `:<>"|?*` or control chars; no segment ending in `.` or space; no device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9, with or without extension); stays inside its base.
**Link rule** (use time): reparse points/junctions/symlinks are never followed. If any existing component of a path being read, written or copied is one, the op aborts (exit 5; zip members: exit 4). Deletion never recurses through a link: a link is removed with `os.rmdir`/`os.unlink` only (read-only bits cleared first).
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
- **Recovery** (update only; target dest only; other `*.old` untouched; install never recovers, it refuses any existing `dest`/`dest.old`, see below), at most:
  - `dest` missing, `dest.old` present -> `os.rename` it back (crash between the swap renames).
  - both present -> abort 5: `<dest> and <dest>.old both exist; if <dest> is good delete <dest>.old, else delete <dest> and rename <dest>.old to <dest>` (also after a committed op whose `dest.old` delete failed).
- **Dest-kind check** (install/update): dest exists and is not a real directory (file or link) -> exit 5, nothing touched. install also refuses any existing `dest` or `dest.old` (unmanaged, exit 5, "delete or rename it"); this includes a complete dest left by a crash after the stage rename but before the state write: delete it and retry.
- **Fetch/extract**: download to `.portakit-dl-<id>.tmp` (size-capped), verify SHA256 BEFORE extract (mismatch -> exit 3, temp deleted, nothing installed); no cache, every install/update downloads. Safe extract into `.portakit-stage-<id>.tmp`: zip-slip/absolute/link/special/duplicates rejected; single-root flatten; exe copied as `<id>.exe`.
- **Preserve (update)**: after extract, each `preserveOnUpdate` path is copied from the OLD dir (the current `dest`, still in place; never from `dest.old`) into the stage, replacing the packaged copy; absent paths skipped.
- **Swap** (install/update), using `os.rename` only (never `os.replace`/`shutil.move`, so an existing target makes it fail instead of being overwritten): (1) `dest` -> `dest.old` (skipped if dest absent); (2) stage -> `dest`; (3) write state (the commit point); (4) delete `dest.old`. Rollback applies only to failures before (3) completes, including (3) itself raising: if step 2 ran, delete the new `dest`; then `os.rename` `dest.old` back; state stays as it was. If rollback fails: leave both, exit 5 naming them (next op hits the both-present rule). PermissionError at step 1 or 2 -> exit 6, nothing changed. After (3) there is no rollback; if only (4) fails: success plus the stderr line `warning: could not delete <dest>.old; delete it before the next operation on <id>`.
- **update ID**: the catalog entry is the pin. Compare installed (`version`, `sha256`) with the catalog's: any difference (version up or down, or a changed digest at the same version) triggers the update, so pin changes always reach users; never "latest". Identical and dest present -> no-op, exit 0, `changed:false`. Dest absent -> repair: reinstall, `changed:true`. To force a reinstall of an identical pin, `remove` then `install` (preserveOnUpdate does not apply to that). The new state entry stores the catalog's `version` and `sha256`.
- **remove ID**: no recovery step. Delete `dest` (missing is fine; a link is unlinked, never followed; a regular file -> exit 5), then delete `dest.old` if present (both present is fine here), then **delete the state entry LAST** (state write). Any failure, including the state write, aborts with the entry kept (PermissionError -> 6, else 5); retry finishes. A crash leaves an entry without dest (retry `remove`, or `update` repairs), never a dest without an entry. Uses the state entry's dest. Removes everything in dest incl. user data; never touches other dirs or ROOT.

## Acceptance
Under `python -I`: malformed catalog (TODO sha256, unsafe paths, device-name id, non-https url) -> exit 2 naming the field; zip-slip -> zero files; bad SHA -> nothing installed; failed install/update keeps previous dest and state (incl. a failing state write); swap never overwrites an existing target; kill after each swap step recovers or aborts per sec. 5; stale stage is wiped, not reused; remove never leaves a dest without an entry; junctions are never followed or deleted through; resolve errors change no dest or state (ROOT and the lock file may be created); a changed `sha256` at the same version, or a state entry without `sha256`, triggers update; `--json` always one envelope, `-h` exits 0; second process -> exit 6; locked dest -> exit 6 with state unchanged; identical-pin update is a no-op only while dest exists; first run creates ROOT. End to end with no PATH/shims: `python -I portakit.py install jq` then `portable\jq\jq.exe --version` works.

## README requirements
Quickstart (default root, `portable\jq\jq.exe`); commands/flags incl. `-h`; envelope, `data` shapes and exit table identical to sec. 4; layout, lock, state, `dest.old` semantics and the both-present manual fix; update-by-pin rule and reinstall = remove+install; remove semantics; per-tool sha256 provenance (no TODO); how to bump a pin (version, url, sha256); test command; Windows-only, one operation at a time; no config seeding (deferred).

## Code-vs-SPEC deltas (vs v0.1.0-pre-ratify)
1. Exit codes: replace `EXIT_CODES` (0,2-9) with 0-6 and codes usage/catalog/fetch/archive/state/busy; busy = lock held or PermissionError on rename/delete of dest; other `OSError` -> state (5).
2. Add the byte-0 lock + exit 6 and mkdir ROOT before locking (mutating ops only). Rename temps to `.portakit-stage-<id>.tmp`, `.portakit-dl-<id>.tmp`, `.portakit-state.<hex>.tmp` (today uuid names) and delete all `.portakit-*.tmp` after locking.
3. Catalog: drop `kind`, `repo`, `tag`, `asset`, `github_url`, `defaultConfig` (code: `apply_defaults` and its validation; `catalog.json`: keep `url`, remove the rest); reject `sha256: TODO` at load; dest = one segment; check `<id>.exe` at load.
4. State entries gain `sha256` (missing tolerated, compares as changed); `install`/`update` write it.
5. Remove the download cache (`fetch`, `.portakit-cache`): download straight to the dl temp, verify, extract. Remove `cleanupPending` from `data`; the single `dest.old` warning is one stderr line.
6. `update`: compare (version, sha256) instead of version (a missing state `sha256` counts as changed); no-op only if identical and dest present; repair for absent dest; `not in catalog` message (today "Unknown ID"); run resolve (state/catalog/dest-changed) before recovery or any download.
7. Swap: use `os.rename` (today `Path.rename` is fine; ensure no `replace`/`shutil.move` anywhere in the swap); make the state-write-failure rollback explicit and tested; replace the previous-entry restore and the "Backup already exists" errors with the sec. 5 recovery (update only; `install()` stops restoring and refuses); dest-kind check (file/link -> 5; install refuses existing `dest`/`dest.old`).
8. `remove`: today renames dest to `.old`, writes state, deletes; change to delete dest, delete `dest.old`, write state last; accept missing dest and both-present; no recovery.
9. Link rule: deletion helper must unlink/rmdir junctions and symlinks instead of recursing (verify `remove_tree` on a junction); keep `reject_links` for preserve.
10. Envelope: `list` -> `data.items`; `changed`/`dest` on all install/update results; one envelope for usage errors under `--json`; `-h` exits 0 with human text, no envelope (do not swallow argparse's SystemExit).
11. README: align with sec. 4-5; remove the cache, `kind`/github, `defaultConfig`, TODO-hash, `cleanupPending` and "inspect `.old`" text.
12. Tests (first): kill/failure after each swap and remove step; state write raising; swap onto an existing target fails; resolve-before-recovery (unknown ID with a stray `dest.old` changes nothing); both-present abort message; locked rename leaves state unchanged (6); junction at dest and inside dest; same version + new sha256 updates; second process -> 6; `list` mid-swap.
