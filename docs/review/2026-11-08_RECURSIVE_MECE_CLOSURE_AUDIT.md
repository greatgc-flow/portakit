# Recursive MECE / vertical-horizontal closure audit (2026-11-08)

Scope: whole repo (docs + code + tests) at main f0e3ddc. Baseline: 823 tests OK (6 skipped), local Windows.
Method: scripted traceability inventory (script -> test -> doc -> launcher; doc -> inbound links; current-pointer chain), then peer review.

Axes:
- Vertical (V): requirement/SPEC -> code -> test -> user doc -> handoff; every layer must point down/up consistently.
- Horizontal (H): siblings in one layer are mutually exclusive (no duplicate/competing truth) and collectively exhaustive (every sibling indexed/covered).
- Recursive: the same rule applies inside each doc/category, and the check itself is enforced by a test so it stays closed.

## Findings (evidence)

| ID | Axis | Finding | Evidence |
|---|---|---|---|
| F1 | V | Current-handoff pointer is stale: README, docs/HANDOFF.md, docs/BACKLOG.md and tests/test_doc_navigation_ssot.py all name START_NEW_CHAT_PORTAKIT_20261101.md, but a newer START_NEW_CHAT_PORTAKIT_20261103.md (PR #126) exists. The SSOT test hardcodes the date, so every handoff silently forks truth unless 4 places are edited. | grep CURRENT |
| F2 | H | No MECE doc index. README "Docs" section lists only SPEC/DECISIONS/HANDOFF and still calls HANDOFF "open work" although HANDOFF.md declares itself historical. 32 docs + 8 research files are not classified. | README.md:419 |
| F3 | H | 12 handoff docs are orphans (no inbound link from any .md). | inventory |
| F4 | H/V | README (438 lines) is a chronological changelog: ~30 dated "Historical checkpoint"/feature sections precede Quickstart/Commands. History duplicates BACKLOG/handoffs; reference and history are not mutually exclusive. | README headings |
| F5 | V | Launchers lack a closure test: MyToolkitGUI.cmd, OfflineCheck.cmd, PickerAcceptance.cmd, Toolsets.cmd, Run-WinMerge-Office4.cmd have no test asserting their target script exists. | inventory |
| F6 | hygiene | 96 non-main remote branches (mostly merged squash PR heads). | git branch -r |
| F7 (added R1) | V | DECISIONS is stale on the same axis as F2: line 4 said "HANDOFF contains open work", and nothing is ratified after 2026-10-30 although personal kits, picker, evidence logs, offline plugin apply and the 2026-11-04 CSV decision have code, tests and guides. The audit did not check DECISIONS vs code. | docs/DECISIONS.md |

Non-findings (checked, closed): no broken relative md links; every scripts/*.py is imported by >=1 test (report_evidence.py via its callers); CI matrix 3.11/3.14 documented.

## Proposed changes (minimal, Very Simple)

P1 (F1, recursive closure): tests/test_doc_navigation_ssot.py derives CURRENT = newest docs/handoff/START_NEW_CHAT_PORTAKIT_*.md by name sort; asserts README/HANDOFF/BACKLOG all point to it and no other START_NEW_CHAT file is called "latest/current". Required sections relaxed to what every handoff must contain: live-verification rule + new-chat prompt without 40-hex SHA or "N/N PASS". Update the 3 pointers to 20261103; add the required headings to 20261103 if missing (content preserved).
P2 (F2+F3): add docs/INDEX.md — one MECE table: Contract (SPEC, DECISIONS) / User guides / Acceptance & evidence / CSV research / Research data / Reviews / Handoff (current + archive list). Test: every docs/**/*.md and research/* file appears exactly once in INDEX.md (CE + ME). README "Docs" -> link INDEX.md.
P3 (F4): move README dated sections (between "Current status" and "Quickstart") verbatim into docs/HISTORY.md (append-only, linked from INDEX); README keeps overview, current-status pointer, Quickstart..License. Keep all strings asserted by tests/test_cli.py (README assertions) — verify by running tests.
P4 (F5): test that each scripts/*.cmd references only files that exist in scripts/ and every .cmd is listed in README Commands or a guide doc.
P5 (F6): delete merged remote branches only after user approval (irreversible-ish; listed to user).

Explicitly NOT doing: code refactors without reproduced defect (#87 rule); catalog/toolset changes; branch protection (#51).

## Decision log

### Round 1 — peer findings (ag, fable)

Closed by verification: SPEC exit table, README table and `EXIT_CODES` agree and are test-enforced; all five CLI commands plus `--archive`/`--recommended`/`--log-file` appear in SPEC; 19 pinned / 108 canonical / 151 selectable agree across DECISIONS, TOOLSETS.md, README and tests.

Gaps raised against the audit itself:

1. DECISIONS stale and unchecked against code → new finding F7.
2. P1 and P3 are coupled: "no other handoff called latest/current" fails on README lines 3, 58, 171, 206 and on the filename `START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md` until P3 moves those sections. P1 runs after P3.
3. P1 understated the test changes: the 20261103 handoff lacks `docs/BACKLOG.md` and the `Issues #25/...` string in its prompt and its last section is "7. Copyable next-chat instructions". Dropped assertions must be listed.
4. P3 "verbatim" breaks 47 root-relative links unless rewritten; `tests/test_doc_navigation_ssot.py` also asserts the PR #84 heading in README.
5. Link checking was a one-off script, not a test, violating the audit's own recursive rule.
6. F6 unverified: `git branch -r --merged main` finds 2 of 98 because squash merges hide ancestry.
7. P2 scope holes: `docs/**/*.md` misses `docs/handoff/2026-10-22_REPO_SOURCE_MAP.json`; "exactly once" breaks on paths quoted in note cells; INDEX becomes a fifth current pointer unless P1 covers it.
8. P4 as written fails: `Run-WinMerge-Office4.cmd` references `powershell.exe` and a `.ps1`; `PickerAcceptance.cmd` names `MyToolkitGUI.cmd` in a comment. ag additionally flagged suffix ambiguity (`_R2`) for name-sorted CURRENT.

### Round 2 — synthesis and votes (unanimous APPROVE)

- **P1 APPROVE.** CURRENT = the `START_NEW_CHAT_PORTAKIT_<YYYYMMDD>*.md` with the greatest 8-digit date; the test fails if two files share that date (no second manifest). Pointer set = README, docs/HANDOFF.md, docs/BACKLOG.md, docs/INDEX.md. README top heading carries no date; no README line labels another handoff latest/current. CURRENT needs a heading containing "verification rule" and a last `## ` section containing `windows-tests.yml` with no 40-hex SHA or N/N PASS. Dropped asserts: `docs/BACKLOG.md` and Issues string inside the prompt, `## 1. Archived PR #82-era remote state`, `## 5. New-chat continuation prompt`, PR #84 README heading (now asserted in HISTORY.md). Caveat accepted: README line 3 heading reworded, not redated. Applied after P3.
- **P2 APPROVE** with one rule: a file matched by an explicit path entry and its directory row counts as one match (explicit wins). Entries are file paths (top-level docs/*.md, README, research/* singly) or directory rows (`docs/handoff/`, `docs/review/`). Permanent test: every relative .md link resolves.
- **P3 APPROVE.** Dated README sections → `docs/HISTORY.md` with link rewrite (`docs/` prefix stripped, `../` prefixed for root files); README keeps overview, current pointer, Quickstart..License; full suite run before and after.
- **P4 APPROVE, amended per ag:** match `%~dp0([^"\r\n]+)` with quotes stripped, resolve relative to `scripts/` including `..`, assert the target exists; comments and system executables ignored; the "listed in README/guide" clause dropped.
- **P5 APPROVE.** merged = `gh pr list --state merged --json headRefName` (94 merged, 2 unmerged kept); delete only after user approval naming the 2 unmerged branches separately. Not executed in this change.
- **F7 APPROVE.** DECISIONS gets an honest scope note (ratified through 2026-10-30; later features are specified by their indexed guides) and the stale "HANDOFF contains open work" line is fixed. No retroactive fake ratification.

Sequence agreed and executed: P2 link test → P3 → P1 → P4 → F7. P5 remains approval-gated.

### Implementation record (2026-11-08, uncommitted working tree)

- New: `docs/INDEX.md`, `docs/HISTORY.md`, `tests/test_doc_index_mece.py`, `tests/test_launcher_targets.py`.
- Rewritten: `README.md` (dated sections moved; Air-gapped and Complete 7-Zip reference sections kept and placed after Quickstart; Docs section points to INDEX), `tests/test_doc_navigation_ssot.py` (derived CURRENT).
- Edited: `docs/HANDOFF.md`, `docs/BACKLOG.md` (pointer → 20261103), `docs/DECISIONS.md` (scope note, line 4), `docs/handoff/START_NEW_CHAT_PORTAKIT_20261103.md` (added `## Active verification rule` heading above the existing rule; the copyable prompt now names the `windows-tests.yml` workflow URL; no content removed).

### Follow-up after PR #130 (main 73bddf1, branch docs/ratify-post-1030-decisions)

- G1 (F7 full close): `docs/DECISIONS.md` scope note replaced by one line; eight 2026-11-08 entries ratify merged PR families retrospectively (personal kits + picker; opt-in evidence logs; offline editor-plugin apply; read-only kit diagnostics; bounded toolset apply; strict declarative JSON; research-only CSV tooling + 2026-11-04 decision; final-user acceptance boundary). Each cites PRs, the test files enforcing the invariant, and the guide.
- G2: `tests/test_launcher_targets.py` also parses `scripts/*.ps1` for literal `Join-Path $scriptDir "<name>"` (scripts/) and `Join-Path $repo "<name>.py"` (repo root) targets and asserts they exist; computed names, logs, directories and managed-root executables are ignored.

### Re-audit after #133-#136 (branch docs/close-gaps-after-133-135)

Fixes #133-#135 changed behaviour without updating the contract docs; the SPEC -> code -> doc axis is re-closed by one-clause additions:

- G1: `docs/SPEC.md` toolset status line names `blocked-destination` (another state ID owns the destination, case-insensitive; blocks the batch before any download) plus the already-coded `blocked-backup`, `blocked-unmanaged`, `blocked-pin`.
- G2: `docs/SPEC.md` single-root flatten states roots are compared case-insensitively (#133).
- G3: `docs/TOOLSETS.md` and `docs/PERSONAL_KITS.md` state that an empty `--offline-dir` is rejected, no implicit current directory (#134).
- G4: `docs/SPEC.md` context menu: a saved exe that is not absolute or contains a quote/newline counts as modified and is refused by install and remove (#135).
- G5: `docs/GUI_ACCEPTANCE_20261021.md`: EOF/`OSError`/`ValueError` during operator review records FAIL while keeping `gui_launched`, pin and SHA-256 evidence (#135).
- R1 (recursive closure): `tests/test_toolsets.py` collects every `"blocked-*"` literal in `scripts/toolsets.py` and asserts each appears in `docs/SPEC.md`, so new statuses cannot ship undocumented.
