# Personal toolkit GUI manual acceptance (2026-10-30)

## Read-only overview window (additional human acceptance)

- [ ] Open GUI, select some pinned/research/OS and editor plugins, open **Read-only overview…**. The main selection must not be saved or altered.
- [ ] Input managed root, optionally original vendor archive folder, optionally whole-number MiB limit; click **Inspect only**. Validate explicitly visible `READY`/`READY_APPROVED_SUBSET`/`NO_OP`/`BLOCKED` statuses and source-missing blockers; no EXE/download/install process.
- [ ] With no pinned entries, see `(no pinned tools selected)`; when pinned not installed, logical size must be `UNKNOWN`, not `0`. Already-managed matching pins may show measured logical bytes; never confuse logical size with physical disk allocation or full kit footprint.
- [ ] Check `skip pending` checkbox; research tools/editor plugins remain excluded even when source checks become green. Original corporate transfer/EDR/license approvals remain independent.
- [ ] Bad path/invalid budget must show a non-destructive error; no new files from overview scan. For filed JSON/log evidence use existing separate explicit CLI `--out`.
- [ ] Windows 100%, 150%, 200% DPI: overview scroll, controls, contrast, Unicode and keyboard Tab navigation. Tests do not create a real Tk window; keep HUMAN_NOT_VERIFIED until operator screenshots and evidence.


## Individual editor plugin display — manual acceptance still required

The picker now displays both the chosen plugin's host and verification stage and a separate visible **selected editor plugins** summary. Check all six plugin families (2 pinned-source metadata, 4 research-only). The summary must update immediately when a plugin is added, removed, a host application is de-selected, or an existing personal kit is imported. A previously research-only choice must not quietly become pinned after import. Resize to 850px and use 100/150/200% Windows DPI; confirm wrapping, contrast, Korean IME and keyboard navigation without clipping. These are **manual acceptance gates**, not proven by headless CI tests. All plugin installation remains a separate explicit offline workflow, never a GUI action.

## Keyboard UX follow-up (2026-10-30)

Source change: validation of all highlighted IDs before any modification; keyboard hints and a focusable search field; persistent highlighted rows and tree focus after search/filter/selection refresh. Bind **Ctrl+F** to focus search, **Space/Enter** to toggle highlighted records, **Ctrl+A** to highlight visible filtered rows (tree only), **Delete** to remove highlighted from kit (tree only), **Escape** to clear highlight (tree only), **Ctrl+O** to import, **Ctrl+S** to create a new kit. Existing no-overwrite JSON + exact evidence log, v1/v2 plugin selection and original separated install-only CLI are unchanged.

### Additional human-only checks
- [ ] 100%/150%/200% display scales: keyboard help, filtered result count, buttons and save area not clipped.
- [ ] Search Korean/ASCII/mixed case, Ctrl+F, Tab focus and full keyboard traversal.
- [ ] Filter list, Ctrl+A visible and Space toggle, then change filter: selected kit items survive while hidden. Confirm original highlighted items persist when still visible.
- [ ] Import a kit, Ctrl+S then attempt same output path: no overwrite; error dialog reachable by keyboard.
- [ ] Contrast and screen-reader announcement of rows/selection/counts. CI **cannot** prove screen-reader correctness or real focus behavior; keep HUMAN_NOT_VERIFIED.
- [ ] Esc/Del never remove a saved kit file or software install; they affect UI highlights/selection metadata only.



**Status: NOT_VERIFIED — workstation-only interactive acceptance pending.** This is separate from the Python headless model tests and Windows Actions CI. Do not mark GUI visually accepted without a real approved Windows desktop session.

## Preconditions and non-production boundary

- Use an authorized interactive Windows x64 workstation with standard Python 3.11+ and available `tkinter`. Do not install Tk, Python, drivers, services, plugins or tool binaries merely to run the acceptance.
- Check exact Git main commit and CI first. Back up any existing personal kits and work in a new disposable directory, e.g. `%TEMP%\portakit-picker-acceptance`. No real plant network, EAP/CIM/MES process, industrial PLC or production log.
- Run `scripts\MyToolkitGUI.cmd` or `python -I scripts/toolkit_picker.py`; it should require **no administrator access**. Use `scripts\MyToolkit.cmd` as CLI fallback if Tk missing.
- Capture operator observations and approved synthetic screenshots *locally only*; do not publish enterprise locations, device identity, credentials or corporate policy notes to this PUBLIC repository.

## Keyboard-first improvements — implementation versus human validation

The selection-only Tk GUI now has `Ctrl+F` to focus/select the current search text, `Ctrl+O` to import, and `Ctrl+S` to save. **In the tool table only**, `Space` or `Enter` toggles highlighted IDs, `Ctrl+A` highlights visible rows, `Delete` removes highlighted IDs from the kit, and `Escape` clears the highlight. Arrow keys navigate the table. Filter changes retain highlight/focus for still-visible IDs; the display reports visible/highlighted counts. Invalid multi-item operations must fail without partially changing selection.

These interactions are backed by deterministic headless source/model regression tests, **not** a real Windows Tk keyboard or assistive technology session. The on-site operator must still verify native widget behavior, selection/focus preservation, Korean IME, 100/150/200% scaling, high-contrast accessibility and errors with an actual mouse/keyboard and capture approved screenshots locally. A keyboard shortcut is not evidence of screen-reader accessibility.

## Execute / observe / retain result

| # | User action | Expected behavior |
| --- | --- | --- |
| 1 | Open selector | Clear light/dark readable window, all known tools loaded, **no install/download/registry change** |
| 2 | Search `DuckDB`, `jq`, mixed case and Korean term | Case-insensitive Unicode name/ID/domain filtering; no crashes |
| 3 | Change domain to `network`, state READY | Only pinned network candidates shown; no network sockets opened |
| 4 | Multi-highlight, add filtered, remove, clear | Correct selected count, no duplicates; empty selection remains safe |
| 5 | Add `essentials` twice, and individual `jq` | Exactly one `jq` in the eventual kit |
| 6 | Select `7zip` and `7zr` | Saved selection places `7zr` ahead of full `7zip` |
| 7 | Select `duckdb-cli` and `jq`, Save as a **new** JSON | New schema-v1 JSON and matching console evidence LOG; pending remains pending |
| 8 | Save again at same output path | Refuse overwrite without touching prior JSON/log; show clear error |
| 9 | Import valid saved kit; attempt tampered SHA import | Valid selection restored; bad SHA refused, prior selection retained |
| 10 | Close GUI, run `scripts\MyToolkit.cmd plan --kit <file>` | Plan read-only, no installed directory or vendor process |
| 11 | Try missing Tk interpreter/headless machine | GUI exits with clear fallback instruction; CLI still works |
| 12 | Test 100%, 150%, 200% DPI scaling / keyboard navigation / contrast | Record layout, clipped text, focus and screen reader accessibility findings without pretending green CI tests visual quality |

Any defect: record local file hashes, exact command and console text, expected vs actual behavior, Windows/Python/Tk versions, reproducible synthetic steps, and (approved) screenshots. Use new GitHub issue **only with sanitized results**; do not upload real paths or private binaries.

## Gates

- GUI Save is intentionally the **only mutation**: it creates a user-directed new JSON and local log. There is no direct Install/Apply button. Building requires a separate deliberate `MyToolkit.cmd build ... --yes` command after plan, license/EDR checks and optional offline SHA preflight.
- No approved vendor binary or simulator is shipped with this UI. Research-only can be selected but **not installed**. Historical research saved as pending must stay pending even after catalog promotion until a human reselects it.
- Until an approved operator has executed all checks with evidence, retain **HUMAN_NOT_VERIFIED** and do not declare the entire GUI/enterprise kit Release gate complete.
