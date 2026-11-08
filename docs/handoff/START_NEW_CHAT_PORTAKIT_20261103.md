# PortaKit — Session handoff (2026-11-03 KST)

## Active verification rule

> Public-safe developer handoff, not an enterprise/site acceptance report.
> LIVE REMOTE GitHub main, PRs, Issues and Actions always supersede this dated snapshot. Do not trust a recorded SHA as current until rechecked.
> Do not reproduce private workstation paths, credentials, internal MES/PLC data, identities or unpublished organization policy in this public repository.

## 1. Verified checkpoint before this handoff documentation

Repository: https://github.com/greatgc-flow/portakit
Last verified functional main SHA: eed1fde7ba04326d7c2f0941ad923ef1a970791f (squash PR #125).
Independent main Actions run: https://github.com/greatgc-flow/portakit/actions/runs/41602791918 — completed SUCCESS, Windows Python 3.11 and Python 3.14, 820/820 PASS each. Job IDs: 125805275392 (3.11), 125805275191 (3.14); both logs individually inspected for new tests plus GUI/source/Sysinternals pin gates.
At this snapshot: 0 open PR; 5 open issues #25, #27, #36, #51 and #87. Main branch was not protected. Branch rules were not changed.
The documentation PR that introduces this file will have a later main SHA and a separate CI run; ALWAYS fetch live GitHub state first.

## 2. Engineering results preserved from successive sessions

- #119: identity-aware cleanup of owned evidence outputs when inode identity is unknown; main caea261df64862dfc6848af63c94984a9005aa4e, 805 tests per Windows version.
- #120: optional CSV crosscheck report may not be written inside source smoke evidence tree; main 98b27f93355c7cd212a60d61d2bb945cfb683403, 807 tests per version.
- #121: CSV synthetic fixture input and captured output directory trees must be disjoint, including nested and dot-dot alias paths; main c055c49a7af049c344a2bd1cbf326b3acc826b23, 809 tests per version.
- #122: bound personal kit/declarative JSON reads to 1 MiB; normalize deep/invalid input to controlled errors; preserve GUI selection on bad import; main b1dea231445251c3c51b2029354a7f3cae01680f, 812 tests per version. An initial failing test assumed the same parser error wording across Python versions; only the corrected final green PR was merged.
- #123: reject nonregular personal-kit JSON file types before opening and check the opened handle type; main 6b081de24417ae784ab9041cc01366ceee73d562, 814 tests per version.
- #124: show controlled GUI errors for core reparse/path violations during import/save, including start-up; no selection/kit evidence mutation on failure; main 23fb9ae0b272a7014ac91e55c38e3040c7255787, 818 tests per version.
- #125: saved-kit GUI confirmation now shows a quoted ABSOLUTE MyToolkit.cmd launcher and quoted ABSOLUTE JSON path, so copy/paste plan guidance works from other working directories; main eed1fde7ba04326d7c2f0941ad923ef1a970791f, 820 tests per version. PR-head CI: https://github.com/greatgc-flow/portakit/actions/runs/41602592462. Independent postmerge main CI: https://github.com/greatgc-flow/portakit/actions/runs/41602791918. Two new tests use foreign CWD, Unicode/space paths and a real synthetic kit/evidence pair. Comment evidence: https://github.com/greatgc-flow/portakit/issues/27#issuecomment-6598837587 and https://github.com/greatgc-flow/portakit/issues/87#issuecomment-6598838950.

The PR-head + independently rerun merged-main Windows Python 3.11/3.14 job logs were checked for all completed merges above. No site or vendor runtime is certified by those tests.

## 3. Single source of truth / key code and docs

- catalog.json: currently pinned install-capable versions/source hashes only; approval to install on a company endpoint is NOT established by this metadata.
- research/TOOLS_CANDIDATES_20261020.json and research/INTAKE_ENTERPRISE_PORTABLE_20261025.json: 151 selectable software IDs at checkpoint = 19 pinned + 27 OS-only + 105 RESEARCH_ONLY, plus 6 separately selectable editor-plugin families. These counts may change; reload source.
- scripts/my_toolkit.py: one authoritative v1/v2 personal kit schema and CLI create/list/plan/build flow; installer runs ONLY under separate build --yes with all applicable gates. Do not bypass pending selection/host/pin safeguards.
- scripts/toolkit_picker.py: optional headless-testable PickerModel and Tk selection, filtering, JSON preview, readiness and save/import UI. No GUI installer.
- scripts/offline_ready.py, scripts/kit_footprint.py: point-in-time read-only archive/managed-size checks. Unknown bytes are NOT zero.
- scripts/toolsets.py and portakit.py: existing SHA-pinned install core, path checks, receipts and rollback. Preserve installer and evidence safety.
- tests/test_my_toolkit.py and tests/test_toolkit_picker.py: negative and compatibility coverage; tests run headlessly, NOT a live GUI session.
- docs/PERSONAL_KITS.md and docs/GUI_PICKER_ACCEPTANCE_20261030.md: usage and final-user GUI acceptance.
- docs/END_USER_ACCEPTANCE.md: boundary between source-engineering tests and corporate/operator acceptance.
- docs/PORTAKIT_ACTIVE_WORK_20261102.md: historical planning matrix; earlier "next" steps may already be complete; trust GitHub history/comments.
- https://github.com/greatgc-flow/VerySimpleGuide: review for Very Simple, independent functionality, MECE decomposition, concrete negative tests, traceable evidence and efficient CLI learning. Do not refactor on stylistic grounds alone.

## 4. Live issue ownership / state at checkpoint

- #25: actual third-party candidate research and acceptance, xan vs Miller, DuckDB, Tailviewer and isolated industrial simulator roles. Source-only research may continue. DuckDB, xan, qsv, xsv and Tailviewer are NOT catalog-admitted by default. Actual original binary SHA, Windows runtime, corporate license/EULA/OSS/EDR, transfer/airgap, CPU/RAM/GUI performance and deployment remain end-user / organization decisions.
- #27: optional GUI picker functionality substantially implemented; human keyboard/focus/850px/100%-200% DPI, Korean IME, actual accessibility and original workstation acceptance still NOT_VERIFIED. Do not close solely for synthetic green CI.
- #36: six independent editor-plugin choices, pinned-metadata versus research-only distinction; standalone offline plugin application is separately consented. No unapproved plugin admission or silent deployment. Actual host/vendor/license validation final-user-owned.
- #51: optional main protection/ruleset remains DEFERRED. Do NOT change settings without a separate specific approval. Current branch protected flag was false.
- #87: evidence-led and measurable refactors only; identify a REAL reproduced defect or substantial simplification. Avoid speculative small defensive PRs and repeated broad refactors. Keep issue open for substantive future defects.

## 5. Operating and merge rules

- Use GitHub connector to fetch live main SHA, open PRs/issues and Actions FIRST; do not treat this handoff snapshot as higher priority than main.
- Separate independent unit-testable behavior; prefer narrow functions and minimal dependency footprint. Windows Python 3.11 and 3.14 are CI versions. Do not assume all consumers have a live Tk desktop.
- Work on new dedicated branch. Create targeted negative/positive tests and documentation only when an actual issue is demonstrated.
- After exact final PR-head CI completes green, inspect both actual Windows job logs and match PR HEAD against CI SHA, base against unchanged main, mergeability true; then squash merge if authorized. Independently verify postmerge main CI logs and leave concise evidence in relevant open issues. Do not quietly change branch ruleset, public release, PyPI, catalog admission or actual vendor install.
- All site approvals, EULA/EDR/OSS/redistribution, genuine original vendor ZIP/EXE, actual Windows GUI and industrial network/production testing remain FINAL USER / ORGANIZATION owned. Green CI is source assurance only, not a company approval.
- There was no local repository clone to clean in the connector-only sessions: updates and commits were performed remotely through GitHub. For any later local workspace, show status and remove ONLY assistant-created disposable files/branches after safe remote preservation; never delete unknown user work.

## 6. Next engineering turn: start-of-turn deliverables

1. Recheck live main HEAD, PRs/issues/Actions and read this handoff plus newest comments in #25/#27/#36/#87.
2. Prefer a broad operator-flow walkthrough using the existing code and tests: browse -> select -> preview -> save -> verify CLI plan -> readiness/size -> separate consented build. Do not run a real build. Identify whether current CLI/GUI behaves inconsistently. As an initial candidate, inspect whether success, failure, empty selection and save collision workflows offer actionable user feedback when launched from arbitrary CWD, but do NOT predeclare a bug.
3. If no real defect is reproduced, record the exact no-change review and prioritize a concrete remaining issue rather than inventing a new PR. If there is a defect, make one small PR with focused test and operator documentation, apply the exact-head and independent postmerge CI gates above.
4. Distinguish source-only PASS from real-world human NOT_VERIFIED; do not close the open issues without the appropriate owner approval.
5. At genuine context limit or session end, update a dated handoff and relevant issue comment with current HEAD, test counts and any remaining blockers; write a detailed new-chat prompt. No secret/private context in a public repo.

## 7. Copyable next-chat instructions

Continue greatgc-flow/portakit from the latest live GitHub main. Read docs/handoff/START_NEW_CHAT_PORTAKIT_20261103.md in full, then verify main SHA, open PRs, issues #25/#27/#36/#51/#87 and latest Windows CI (https://github.com/greatgc-flow/portakit/actions/workflows/windows-tests.yml). Restore source responsibilities, pending final-user acceptance and 151 software ID / 6 editor-plugin snapshot without treating pins as corporate approvals. Review practical CLI/GUI kit creation, import, preview, saved-path command, read-only readiness and explicit-install boundaries; find one REPRODUCED operator-facing defect or meaningful maintenance simplification, otherwise report a no-change evaluation. If fixing, use an isolated branch, narrowly scoped code, independent synthetic negative/positive tests, Windows Python 3.11+3.14 exact PR-head CI log inspection, squash merge only on verified green, independent postmerge main CI and detailed issue evidence. Preserve Very Simple and no vendor execution/license/EDR/real industrial testing. Do not edit main branch protection or publish releases. At session end persist technical handoff remotely and report current truth.
