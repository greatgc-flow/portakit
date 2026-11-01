# PortaKit — targeted refactor review (2026-11-01)

> Evidence-based, source-only review of GitHub `main` `7524ade1f9d3eb4666740a7131bfa196a32979a9`. Review is **not** a claim of exhaustive line-by-line verification, user-site acceptance, or real vendor execution.

## Fitness and constraints

- **Outcome:** lower maintenance and debugging cost without changing public commands, pinned catalog, install behavior, evidence text, trust boundaries, or runtime requirements.
- **Authority:** the current catalog and core `portakit.py` remain the source of truth for installable pins, receipts, safe paths and installation transactions. User kits and research candidate metadata never grant enterprise approval.
- **Compatibility:** Windows Python 3.11+ standard library; existing CLI selectors, exit codes, root/evidence paths, offline behavior and JSON envelopes retained. Company EULA/OSS/EDR, vendor GUI and deployment acceptance remain with the final user or organization.
- **VerySimpleGuide principles:** [fitness](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/01_METHOD/OBJECTIVE_AND_FITNESS.md), [recursive MECE](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/01_METHOD/RECURSIVE_MECE.md), [component boundaries](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/02_STANDARD/COMPONENT_BOUNDARY.md), [assurance](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/04_ASSURANCE/ASSURANCE_CASE_AND_NEGATIVE_TEST.md). In particular, **avoid a new framework solely to deduplicate code**.

## Existing responsibility map — preserve, do not recreate

| Primary owner | Existing implementation | Rule to keep |
|---|---|---|
| Authoritative pinned catalog and install lifecycle | `portakit.py`, `catalog.json` | One authority for SHA locks, managed state, path safety, rollback |
| Optional batch selection and orchestration | `scripts/toolsets.py` | Read-only plan, explicit apply, bounded core-child invocation |
| Personal selection and saved kit schema | `scripts/my_toolkit.py` | Pinned versus research-only/OS-native separation |
| Optional picker | `scripts/toolkit_picker.py` | Pure model can run without Tk; UI must not launch vendor installers |
| Installed editor plugin lifecycle | `scripts/plugin_offline.py` | Independent approval and exact host/plugin receipt boundary |
| Read-only composed diagnosis | `scripts/kit_doctor.py` | Reuse offline readiness, footprint and plugin health rather than repeat checks |
| CI and operator evidence | `.github/workflows/*`, `scripts/*` report emitters | Exact observed evidence; no synthetic CI = real-world authorization |

## This PR: narrow orchestration refactor (COMPACT source-only)

**Observed seam:** `toolsets.apply` handled child launching, strict JSON validation, and persisted receipt/destination postchecks inline within the orchestration loop. These stages have different failure causes but were entangled in one function.

**Refactor:** extract three small, testable unit functions in the same module:
1. `run_core_child(cmd, runner, child_timeout)`: bounded production child or synthetic test runner.
2. `parse_core_install_result(stdout, name)`: strict success envelope, no filesystem mutation.
3. `verify_managed_install(row, catalog, root)`: reload current state and confirm pinned nonempty managed destination after child.

**Explicitly unchanged:** tool selection, ordering, child command flags, default timeout/output cap, process isolation limits, handling of stderr, error text and evidence placement, partial batch semantics, failure/exit codes, catalog pins, GUI, downloader and license gates. No new dependency or general-purpose plugin/evidence framework.

**Regression contract:** original Windows 3.11/3.14 full suite plus isolated tests for valid/invalid/duplicate-key/nonstandard core JSON, ID mismatch, missing/empty destination, matching installed receipt and pin changes. Existing failure/timeout/partial/evidence-mirror tests must still pass. CI results will be recorded by exact commit before merge; merged-main CI is independent.

## Verified implementation evidence (later source checkpoint)

- [PR #86](https://github.com/greatgc-flow/portakit/pull/86), exact head `3d7cb8f6d6d40ac6f5cdf50a30c2cde1f0d995d1`: [Windows CI #41261968622](https://github.com/greatgc-flow/portakit/actions/runs/41261968622), 710/710 PASS each on Python 3.11/3.14; [archive smoke #41261968600](https://github.com/greatgc-flow/portakit/actions/runs/41261968600), SUCCESS.
- Source squash merge `1888db2dc2c98fb00a57a7e22555e0217aee0962`: independent [main Windows CI #41262060770](https://github.com/greatgc-flow/portakit/actions/runs/41262060770) 710/710 PASS each version; all four relevant test-job logs independently checked.
- This is **NEGATIVE_TESTED on synthetic Windows fixtures**, not actual end-user acceptance, vendor binary integrity, enterprise approval or a proof of every possible fault.
- Remaining candidates moved to [Issue #87](https://github.com/greatgc-flow/portakit/issues/87) for risk-driven opt-in consideration.

## Follow-up: create-only JSON and console-evidence ownership (Issue #87, PR in review)

**Reproduced source gap:** Three consumers (`offline_ready.emit`, `kit_footprint.create_report`, `kit_doctor.emit`) previously handled a JSON-write exception by deleting whatever occupied the target path, even if an unrelated file won the race between preflight and exclusive open. They also kept their JSON/log files when the later evidence emitter failed. `plugin_health.emit` already used safer opened-file identity guards and cleaned both owned outputs.

**Narrow remedy:** one reusable `scripts/report_evidence.py:emit_json_report` restricted to create-only JSON + verbatim UTF-8 console log. It reuses `toolsets.Evidence`, `created_output_identity`, `cleanup_own_output` and `core.check_links`. Its only policy inputs are the per-command exception type and existing collision message; no new schema, CLI, general-purpose abstraction or business-acceptance authority. All four existing callers retain their independent line projections, no-output behavior, exit semantics and special readiness `.json` suffix validation.

**New negative regressions:** for all four callers verify exact console/log and JSON bytes, collision without overwrite, injected JSON disk failure, injected log write failure, concurrent foreign JSON appearance, and replacing a JSON path after creation. Include a symlink replacement guard fixture where permitted. Existing report tests and full Windows matrix remain required.

**Guarantee boundary:** best-effort cleanup based on opened-file identity; it is **not** an atomic two-file commit, durable fsync guarantee, malicious-race containment or company/provider certification. A process crash and competing writer can still leave partial local evidence. Do not label successful source CI as a live-workstation acceptance.

## Candidate follow-ups — only when regression benefit is demonstrated

| Order | Area | Specific observation | Recommended next step / stop criterion |
|---|---|---|---|
| P1 | Evidence emitters | Similar `emit` flows in `offline_ready.py`, `kit_footprint.py`, `kit_doctor.py`, `plugin_health.py` | Compare output schema, exclusive-create and cleanup guarantees with golden-transcript tests **before** shared helper. Do not change output format or error cleanup for aesthetics |
| P2 | Optional picker | `toolkit_picker.py` already has a separate pure `PickerModel`; the Tk `launch` code is longer | Refactor only when a reproduced UI defect/test gap justifies a smaller handler boundary; no new GUI framework |
| P2 | State/schema readers | Core pin/state parser, kit v1/v2 validation and plugin receipt schema have intentionally distinct trust contracts | Prefer existing public contracts; extract only truly identical invariants, never erase explicit provenance checks |
| P3 | Documentation | `README.md` and `BACKLOG.md` preserve long historical checkpoints | Mark latest SSOT prominently; archive historical details only if links and reproducibility remain intact |
| HOLD | Vendor admission and live tests | Vendor EULA/EDR/original archive, real Windows GUI and industrial network testing | Final-user-owned, never inferred from source refactoring or synthetic CI |

**Revisit trigger:** a measured/reproduced regression, changed public contract, incorrect evidence, duplicated invariant requiring the same modification in multiple modules, or actual maintenance burden. Otherwise stop after the smallest verified change.

## Proof boundaries

- **Design and source review:** targeted files and the cited VerySimpleGuide contracts inspected.
- **Negative test proof:** only after exact-commit Windows CI and logs are inspected.
- **Operational acceptance:** not run or certified here; real corporate environment, original binary provenance and industrial connections remain outside the assistant's source-only actions.
