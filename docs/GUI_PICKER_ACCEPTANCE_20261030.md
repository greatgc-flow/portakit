# Personal toolkit GUI manual acceptance (2026-10-30)

**Status: NOT_VERIFIED — workstation-only interactive acceptance pending.** This is separate from the Python headless model tests and Windows Actions CI. Do not mark GUI visually accepted without a real approved Windows desktop session.

## Preconditions and non-production boundary

- Use an authorized interactive Windows x64 workstation with standard Python 3.11+ and available `tkinter`. Do not install Tk, Python, drivers, services, plugins or tool binaries merely to run the acceptance.
- Check exact Git main commit and CI first. Back up any existing personal kits and work in a new disposable directory, e.g. `%TEMP%\portakit-picker-acceptance`. No real plant network, EAP/CIM/MES process, industrial PLC or production log.
- Run `scripts\MyToolkitGUI.cmd` or `python -I scripts/toolkit_picker.py`; it should require **no administrator access**. Use `scripts\MyToolkit.cmd` as CLI fallback if Tk missing.
- Capture operator observations and approved synthetic screenshots *locally only*; do not publish enterprise locations, device identity, credentials or corporate policy notes to this PUBLIC repository.

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
