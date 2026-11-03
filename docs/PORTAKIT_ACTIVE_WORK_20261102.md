# PortaKit — active work and MECE disposition (2026-11-02)

> **Latest handoff (2026-11-03):** [START_NEW_CHAT_PORTAKIT_20261103.md](handoff/START_NEW_CHAT_PORTAKIT_20261103.md). This dated active-work matrix is historical; its old next-step bullets may already be implemented. Live main/PR/Actions take precedence.
>
> **Point-in-time engineering plan, not a second live SSOT.** The current GitHub [main](https://github.com/greatgc-flow/portakit/tree/main), [PRs](https://github.com/greatgc-flow/portakit/pulls), [Issues](https://github.com/greatgc-flow/portakit/issues) and [Windows CI](https://github.com/greatgc-flow/portakit/actions/workflows/windows-tests.yml) always override this dated snapshot. Preserve historical evidence rather than replacing it with guesses.

## Reconciled starting point (verified against remote, not an enterprise approval)

- Snapshot `main` `7b8e24428313035cd7752d2be284a4daca426012` (squash PR #107), [independent Windows CI #41381495864](https://github.com/greatgc-flow/portakit/actions/runs/41381495864): **753/753 PASS on each Python 3.11 and 3.14**. The next PR will produce a *different* exact head, test count and main CI; these numbers are historical checkpoints.
- Open PRs **0** and open Issues **#25, #27, #36, #51, #87** at this snapshot. `main.protected=false`; ruleset edits are **not** authorized by merely approving this development plan.
- Verified source responsibility: `catalog.json` controls 19 pinned install-capable entries, the consolidated selection taxonomy has 27 OS-builtins and 105 research-only (151 software IDs total); separate optional editor-plugin metadata counts six. Neither `PINNED_CATALOG` nor GitHub green checks means corporate use or publisher acceptance.
- **Developer owns** reproducible synthetic/source tests and documentation. **Final user/organization owns** actual vendor originals, licensing/OSS/EDR, approved-device GUI/runtime, offline transfer, performance and deployment decisions. Do not block unrelated source-only merges waiting for those site-owned activities.

## Exactly five issue workstreams — no duplicated ownership

| Issue | Implemented and verified in source | Remaining developer decision / action | Separate final-user gate | Disposition |
| --- | --- | --- | --- | --- |
| [#25 Tool intake](https://github.com/greatgc-flow/portakit/issues/25) | Research inventory, three-item `lightweight_review`, qsv/xan comparison ledger, bounded read-only ZIP/TAR and CSV smoke helpers, industrial CLIENT/SERVER role matrix | Fix research report evidence creation race in one small source PR; compare researched candidate *benefit* against pinned Miller, avoid a generic new extractor without need | Original source/publisher hash, host/runtime, license, transfer, EDR, performance | **P1 developer now**, vendor promotions held |
| [#36 Editor plugins](https://github.com/greatgc-flow/portakit/issues/36) | Six individual choices (two pinned metadata, four research); v2 saved kit, host consent guard, separate opt-in offline `apply`, local SHA receipts/health, rollback and evidence root guard | Only justified source regression or compatibility issue; no new unverified default plugin | Real Notepad++/WinMerge plugin load and EULA/OSS/EDR/host checks | Source substantially implemented; manual gate open |
| [#27 Optional picker](https://github.com/greatgc-flow/portakit/issues/27) | Tk + CLI, search/filter/role, multi-select, import, JSON preview, pending lock, readiness/size and headless tests | Fix reproduced UI defect only; keep no installer privilege in GUI | 850px + 100/150/200% DPI, Korean IME, keyboard, screen reader and real workstation UX | Source substantially implemented; manual gate open |
| [#87 Targeted refactor](https://github.com/greatgc-flow/portakit/issues/87) | Shared report ownership/evidence, strict schema, status alignment, child execution seams, plugin and Explorer evidence isolation (PRs #86–#107) | Only independently reproduced defect or measurable simplification; do not rewrite full source or duplicate domain-specific parsers | No enterprise approval implied | Evidence-led opportunistic P2 |
| [#51 Governance](https://github.com/greatgc-flow/portakit/issues/51) | Working two-version PR/push Windows CI and squash workflow | Document minimum ruleset, emergency rollback and stable check names; **do not apply** without distinct explicit approval | Repo owner authorizes ruleset scope | Deferred optional P2 |

## Candidate decision queue (research only, release API refreshed 2026-11-02)

1. **xan 0.61.0 — first comparative benchmark candidate.** [Upstream Windows MSVC ZIP](https://github.com/medialab/xan/releases/tag/0.61.0), 6,473,075 metadata bytes. Current `research/CSV_ALTERNATIVES_20261031.json` and `docs/CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md` already cover this; repeat no tool; compare with installed-admissible Miller only using operator-approved synthetic tests. No admission before separate gates.
2. **DuckDB CLI v2.0.0 — conditional analytical value.** [Upstream](https://github.com/duckdb/duckdb/releases/tag/v2.0.0), Windows AMD64 `tar.gz` 19,663,611 metadata bytes, release API SHA available. Current core supports `zip`/`exe`/`sfx7z` but **not `tar.gz`**. Do not silently rename, unpack unsafely or broaden the installer before evaluating a bounded extractor and no-network extensions policy separately.
3. **Tailviewer v1.0.0-rc1 — conditional GUI review.** [Upstream](https://github.com/Kittyfisto/Tailviewer/releases/tag/v1.0.0-rc1), 3,786,701 metadata bytes, no release API SHA at this checkpoint; .NET prerequisite and actual portable user-profile behavior remain unverified. Existing `grepwin`/`ripgrep` baseline can cover many use cases.
4. **qsv 27.0.1 / xsv 0.13.0 — defer.** [qsv Windows x64 MSVC/ GNU releases](https://github.com/dathere/qsv/releases/tag/27.0.1) are 402,543,109 / 129,287,020 metadata bytes (both above the default 100-MiB compressed cap); `xsv` was archived. Do not relax size limits or promote an older unmaintained binary without measured operator gain.

The release API SHA, size and version are **not locally verified original bytes**, enterprise approval, runtime functionality or a current upstream-security verdict. All candidate selection, previews, root/network restrictions, and `RESEARCH_ONLY` status stay unchanged. No production PLC/MES or industrial-protocol live traffic.

## Executed research-source follow-ups (live GitHub takes precedence)

- **PR #108 (2026-11-02):** `lightweight_review.py` now uses shared owned-output JSON/log writer; four negative tests. Exact PR CI #41395586064 and merged-main CI #41395730610 each passed **757/757** Python 3.11/3.14 at main `dbb82058b78c2441e5ee150059c87ba8cb23cb3a`. This supersedes items 1–3 below (which are archived execution plan, not still-open tasks).
- **Next targeted DuckDB candidate preflight:** `scripts/targz_preflight.py` already implements bounded, **read-only** `tar.gz` structural audit. No generic extractor needed for the existing research-only workflow. A separately reproduced JSON/log collision and late-error cleanup gap is the scoped source change; four negative tests reuse the same common owned-output helper. The core installer still rejects `tar.gz`; admission, actual archived bytes, genuine Windows runtime and license approvals remain deferred. PR/CI proof is attached to #25 after verification.

## Immediate implementation and acceptance loop

1. Apply exactly one **source-only #25** repair: move `scripts/lightweight_review.py --out` to existing `report_evidence.emit_json_report`, keep output JSON/transcript byte-identical. Reject foreign JSON create race and clean only owned partial outputs on dump/log failures.
2. Add four isolated Windows Python 3.11/3.14 regression cases: foreign collision, incomplete JSON, incomplete transcript, replaced output. Ensure no vendor code, network or installed-state changes.
3. Run exact PR-head Windows CI, inspect individual 3.11 and 3.14 test logs; squash merge only if HEAD/base unchanged and all checks pass; independently rerun and inspect merged-main CI. Attach exact run IDs and new SHA to #25 and #87; update PR gates.
4. **Next engineering iteration**, not bundled in this fix: review whether DuckDB `tar.gz` can be handled without unnecessary extractor complexity, or whether xan-vs-Miller functional difference justifies a reviewed optional path. No actual admission without final-user decisions.
5. Periodically reconcile this matrix against live issue comments; archived `docs/BACKLOG.md` records are history, not promises to redo the same implementations.

**End-user/operator evidence:** `docs/END_USER_ACCEPTANCE.md`, `docs/GUI_PICKER_ACCEPTANCE_20261030.md`, `docs/CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md`. Their `NOT_VERIFIED` status must remain distinct from source CI. No private approvals, vendor binaries, customer data or workstation fingerprints are included here.
