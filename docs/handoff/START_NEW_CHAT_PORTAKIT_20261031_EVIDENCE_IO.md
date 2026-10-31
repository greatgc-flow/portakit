# PortaKit — source-only evidence I/O handoff (2026-10-31)

This handoff is written for continuation in a **new ChatGPT session**. The remote GitHub repository is the source of truth; confirm its latest `main` commit and PR/issue/Actions status **before** resuming work. This document may be older than a newly merged commit.

Repository: https://github.com/greatgc-flow/portakit
Design reference: https://github.com/greatgc-flow/VerySimpleGuide

## Mission and safety constraints

- PortaKit is a small, offline-first, enterprise-conscious, fully optionable personal Windows utility toolkit. Prefer Very Simple, independent single-responsibility modules and recursive MECE, explicitly safe-by-default CLI and testable changes.
- Avoid vendor downloads, unpacking, execution, installer/catalog promotion, production system calls, new credentials, or externally unapproved EULA/OSS/EDR/redistribution claims.
- `xan` remains `RESEARCH_ONLY`. The independent 7 operator acceptance gates remain `NOT_VERIFIED`; the approved local Windows host, vendor original, actual execution, compatibility and performance are not represented by synthetic CI.
- Default read-only; optional JSON evidence output must mirror the exact displayed console lines to a new UTF-8 LF log. No overwriting existing records.

## Confirmed pre-this-round status

- Pre-round `main` commit: `a03a0d65cd53dda9ae3a3f3c9a1881e6b69f1a13` (this is only a historical baseline; **latest remote main takes precedence**).
- PR #60–65 merged in prior rounds: source/original and smoke acceptance docs, source-only JSON/log linkage, duplicate key and canonical LF checks, deterministic synthetic CSV fixture replay, blocked-case/provenance checks and ZIP member/workspace path hardening.
- Before this round: latest main CI #41207415236 completed SUCCESS; Windows Python 3.11 and 3.14 each ran 613 tests, all OK.
- Before this round: 0 open PRs, 4 open Issues: #25 research original/vendor/acceptance, #27 GUI picker, #36 editor plugins, #51 optional branch protection. Keep #25 open until real evidence exists.

## This round — evidence I/O integrity (verify latest branch/PR/CI to confirm)

- Modified `scripts/verify_csv_evidence.py`:
  - A bounded read now compares path `stat` with opened-handle `fstat` and the final path `stat` (identity, file mode, size and mtime across sources; ctime only within the same path/handle stat domain on Windows), plus bytes read and non-reparse checks.
  - Optional `--out` JSON and log are exclusively created. If creation/serialization/log-mirror fails, best-effort rollback targets only files created by this operation, and only while their file identity remains the same. No collateral deletion of a competing writer's file.
  - Not a transactional filesystem, Windows file-locking facility or cryptographically authenticated snapshot; metadata spoofing and post-check edits cannot be ruled out.
- Expanded `tests/test_verify_csv_evidence.py` with simulated mutations before/during/after read; input non-modification; JSON serialization and partial-log failures; new/foreign output collision and replacement tests.
- Extended `docs/CSV_EVIDENCE_CROSSCHECK.md` and `docs/BACKLOG.md`.
- A separate source-only PR/CI should verify these changes before squash merge. If failed, inspect **exact job logs**, fix the cause, and run tests again; never claim green or merge a failing head.

## First actions in a new session

1. Inspect latest remote `main` HEAD and commit tree, all open PRs/issues, latest Actions run and Windows 3.11/3.14 job logs through the connected GitHub plugin.
2. Read this document, `docs/handoff/PORTAKIT_20261031_FINAL_CLOSEOUT.md`, `docs/handoff/START_NEW_CHAT_PORTAKIT_20261031.md`, `docs/BACKLOG.md`, `docs/CSV_EVIDENCE_CROSSCHECK.md`, `docs/CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md`, `scripts/verify_csv_evidence.py` and its tests.
3. Separate **confirmed historical** work from unresolved real-world verification and current work; use the latest authoritative repository state rather than this document's old SHA.
4. Continue with small independent source-only fixes and negative tests as necessary. Require PR-head Windows 3.11/3.14 full pass, squash merge and exact merged-`main` CI pass before declaring done.
5. Record changes/verified results on Issue #25 without prematurely closing it. Write a new next-chat prompt in conversation after a complete work round.

## Guiding principle

A report marked `EVIDENCE_CROSSCHECK_ONLY` is **only a consistency statement about existing files**. No code-level pass constitutes publisher authentication, corporate authorization, physical isolation or executable trust.
