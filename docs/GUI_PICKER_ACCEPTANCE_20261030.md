# Personal toolkit GUI manual acceptance (2026-10-30)

## 2026-10-31 — selected filter and frozen-stage acceptance addition

The picker adds a **Selected only** checkbox and arranges text search and filter controls into two rows. Check `Selected only` with zero choices, mixed pinned/research/OS choices, combined search/category/stage filters, and multi-highlight across filter changes. Changing filters must never delete a hidden selected item, change `KIT.json`, or launch binaries. Confirm scroll/focus readability at 850 px and 100/150/200% DPI on a real approved interactive Windows workstation.

**Historical stage guard:** import a synthetic older JSON that saved a research-only tool; if a later reviewed test catalog promotes that tool, the previously saved choice must still display `PENDING (locked)` and appear under `RESEARCH_ONLY`, **not `READY`**. The user may opt in again by explicitly removing/reselecting and creating a new kit with the current pin snapshot. Do not modify the production catalog just to perform this test. Headless CI exercises a synthetic in-memory future catalog; human GUI evidence stays **NOT_VERIFIED** until actually reviewed.


## Prospective KIT.json preview — supplemental GUI acceptance (2026-11-01)

On an approved nonproduction desktop, choose Notepad++, jq, a research-only candidate and an OS built-in, optionally choose ComparePlus with its selected Notepad++ host. Enter a valid kit name and click **Preview KIT.json (read-only)** before saving. The scrolling view must show the selected ordered tool IDs, pinned version and SHA under `lockedPins`, research-only/OS-only arrays and plugin metadata (v2 when a plugin is chosen). Verify keyboard and horizontal/vertical scroll, 850 px and 100/150/200% DPI, Korean IME, readable output and no hidden/mutated selections. Confirm no output JSON/log is written and no vendor process/network/installer starts merely by opening the preview. Invalid name and empty selection must produce a controlled error without creating files. After a change to the name/selection, the old preview is a point-in-time snapshot; reopening it reflects current values. Then explicitly save to a new path and verify saved JSON matches unchanged preview bytes and console transcript matches its log; second save must refuse overwrite.

These are **HUMAN_NOT_VERIFIED** until an actual approved Windows operator records them. Headless CI tests serialization and source wiring only; neither preview nor SHA pin proves company EULA/EDR/redistribution/vendor authenticity.

## Optional pinned-profile filter — supplemental human GUI check (2026-11-01)

On an approved nonproduction desktop, select **Profile (pinned) = essentials**. The visible table should contain only the preset's current pinned IDs (for this checkpoint Notepad++, WinMerge and jq); combining the profile with search/category/READY/Selected only must return their intersection. `all` should restore the complete list without modifying saved choices; changing the profile must not auto-add any tool, download or install anything. The independent **Add preset** action still adds the whole preset, whereas **Add filtered** adds only the visible rows after all filters. Check clear/empty results and that hidden selected tools and selected editor plugins remain intact. Check the filter row and tool table for 850px width, 100/150/200% scaling, focus navigation and Korean IME. This is **HUMAN_NOT_VERIFIED** until an actual operator records results; GitHub CI verifies only headless projection and parser behavior.

## One-command local operator evidence — optional helper (2026-10-30)

Run the recorder from an **approved, nonproduction interactive Windows workstation**. This is separate from vendor-app GUI acceptance (`GuiAcceptance.cmd`) and tests only the **personal-kit picker**.

```cmd
:: Read-only check: Python, Tk module presence, GUI source SHA/syntax.
:: No desktop launched, no files written, always NOT_VERIFIED for GUI itself.
scripts\PickerAcceptance.cmd

:: Operator manually starts the picker in a separate window:
scripts\MyToolkitGUI.cmd

:: Then, in the original command window, interactively record observations:
scripts\PickerAcceptance.cmd --review --out D:\LocalEvidence\PickerReview.json
```

The guided run records 14 independent cases: basic launch/no elevation; Windows 100/150/200% scaling; Korean IME; keyboard/focus; filtering; editor plugin host and status; new-only save and protected import; read-only offline source check; installed-size UNKNOWN vs actual managed logical bytes; screen reader; and no unintended OS/network effects. Answer `P` (observed pass), `F` (observed fail), or `S` (skip or cannot verify) for **each**. There is no default PASS. The recorder **does not open Tk or any vendor program**; the operator performs actions in the already-open picker and reports outcomes.

`--review --out` creates *only* a new local JSON report and exactly mirrored **program-generated console transcript** `.log`. Existing JSON/log paths are never overwritten; if interrupted, a partial log remains and **no final pass report** is generated. Exit **0** means only that the operator reported all cases PASS; **1** means failure/input error; **2** means one or more cases SKIP/NOT_VERIFIED. A PASS is a **human self-report**, not automatically verified UI behavior. Neither CLI nor the operator answers establish EULA/EDR, source-transfer permission, vendor authenticity, or independent accessibility certification.

Do not enter enterprise identities, credentials, internal production paths, system inventory, network traffic or real equipment data in public issues. Screenshots are **not captured automatically**; if needed, keep sanitized screenshots and local report in organization-approved private storage. For issue escalation, share only sanitized reproduction steps and statuses; never publish the evidence folder from a company workstation in this PUBLIC repository. This automation cannot itself certify 100/150/200% DPI or screen-reader operation without the operator testing it.


## Per-tool size display (manual checks still outstanding)

- [ ] Select an uninstalled pinned item; inspect and verify its row says `size=UNKNOWN`, not `0`. With a valid managed installed pinned item, verify that row reports its **actual logical bytes**, rather than compressed archive size or NTFS allocation.
- [ ] A missing footprint row must produce an error, never a silent default of zero. Test scroll/horizontal layout under 850px and Windows 100/150/200% DPI in a live approved Tk desktop. Unit CI is not visual acceptance.
- [ ] Do not treat pending, OS built-ins or plugins as zero-size or fully installed; no total future footprint claim.


## GUI readiness / missing-source / size dialog — human acceptance needed

The picker has a **read-only** `Inspect readiness / size…` button. Verify on authorized nonproduction Windows desktop only: selection before save, empty selection error, already-installed managed tools, missing vendor original, wrong SHA, no vendor source directory, pending research/plugin host consent, 7zip/7zr prerequisite, and same selected kit after inspection (no mutation). Confirm optional budget values 0, a positive integer, negative/decimal/bool input. Visually verify that unknown future tool sizes are **never displayed as 0-byte final kit size or PASS**, and that `READY` does not appear as corporate EULA/EDR acceptance. The text area must scroll for the full 151-tool selection, and the window should remain usable at 850 px wide, 100/150/200% DPI and Korean UI input.

No live Tk GUI acceptance or source/EDR/legal evidence has been executed by automated CI; status remains **HUMAN_NOT_VERIFIED**. Headless unit tests exercise safe model state/formatting and no-op/missing/verified synthetic source checks only.


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
