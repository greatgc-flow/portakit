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

## Verified report-evidence follow-up (Issue #87, PR #89)

- [PR #89](https://github.com/greatgc-flow/portakit/pull/89) head `72f5e5bc38e53f6da0aacd49291c9aa3d3cae64a`: [Windows CI #41262818996](https://github.com/greatgc-flow/portakit/actions/runs/41262818996) 718/718 PASS on each Python 3.11 and 3.14, both job logs checked.
- Squash merged source `b7e0cee2ee35f181c93558f3b759b82f2aea59c2`: independent [main Windows CI #41262904434](https://github.com/greatgc-flow/portakit/actions/runs/41262904434) 718/718 PASS each, both job logs checked.
- Archive smoke **not triggered** for these read-only report sources; no validation claim beyond actually executed checks. Defect and negative fixtures documented above. Operator/company approval and original vendor execution **NOT_EVALUATED**.

## Candidate #2/#3 — cross-diagnostic alignment at GUI and KitDoctor boundary (in review)

**Observed source gap:** `PickerModel.inspect_readiness` independently computed offline readiness and installed footprint and returned both without reconciling their observed install statuses or root. `overview_lines` only checked for missing tool IDs; it could combine an `install` status with a stale `already-installed` footprint if managed state changed between reads. `KitDoctor.inspect` checked ordered IDs but not statuses/roots.

**Narrow correction:** `kit_footprint.confirm_readiness_alignment(readiness, measured)` enforces matching normalized root, ordered tool IDs and each `installStatus` / `status` pair (including empty selection). This pure cross-report check is called by both GUI preview and direct GUI projection, and by KitDoctor; KitDoctor translates its error into its existing `DoctorError` boundary. No changes to selection model, Tk controls, saved kit schema, catalogs, read-only command flags, output message format for matching snapshots, or vendor execution.

**Negative evidence:** new headless tests inject status/root/ID drift, empty selections, and null/malformed rows and verify no kit/output writes or selection mutation. Existing Windows CI must confirm all legacy tests unchanged on both Python 3.11 and 3.14. This detects discrepancies between two reads; it is not an atomic snapshot or protection against changes after the check. Operators still own real GUI/company acceptance.

## Verified GUI/Doctor report alignment — PR #91

- [PR #91](https://github.com/greatgc-flow/portakit/pull/91), final exact head `73b490951fd119ebd431ac9400f29c9538409099`: [Windows CI #41263772358](https://github.com/greatgc-flow/portakit/actions/runs/41263772358) **723/723 PASS** on each of Python 3.11 and 3.14; separate job logs examined.
- Source squash merged `acbd6e97838347130ebf798bebec95a563c153b8`: independent [source-main Windows CI #41263859072](https://github.com/greatgc-flow/portakit/actions/runs/41263859072) **723/723 PASS** each; individual logs checked.
- **Regression red-to-green evidence:** an earlier candidate [Windows CI #41263655133](https://github.com/greatgc-flow/portakit/actions/runs/41263655133) exposed legacy `test_gui_readiness` missing-row error wording regression. Existing error behavior restored; full CI passed on exact revised head. This is not a release certification or actual live Tk GUI verification.
- Remaining issue #87 topics are opt-in and only justified by reproduced defects or measurable cost improvements.

## Candidate #3 — direct kit creation and pure picker input boundaries (in review)

**Existing SSOT remains unchanged:** `portakit.strict_json_loads` already rejects duplicate JSON members and nonfinite values. `my_toolkit.read_kit` validates saved v1/v2 partitions, version/SHA locks and plugin host decisions. `plugin_offline` has separate plugin receipt provenance rules. Do **not** unify them into a permissive generic schema or rewrite known-good state readers.

**Observed source-level failure boundary:** `my_toolkit.make_kit`, when directly called with an unknown or unhashable selected ID, indexed `known[ident]` and could throw raw `KeyError`/`TypeError`; duplicate direct selections could create a kit rejected by its own `read_kit` later. The GUI's pure `PickerModel.remove`, `add_plugin`, `remove_plugin`, `add_preset` and `rows(category=...)` also lacked type checks before dict membership, so unexpected list/dict values could escape as raw `TypeError` rather than a domain `KitError`. Direct API consumers merit the same fail-closed policy as the CLI.

**Minimal behavior-preserving boundary:** validate direct `make_kit` selected input as a list/tuple of at most 256 unique known string IDs, then construct canonical JSON list data. Preserve intentionally allowed empty in-memory selections for read-only diagnostic fixtures; persisted kit readers still reject empty saved kits. Explicitly check selector types before membership for the five named picker functions. The normal CLI, presets, approved/research status, pin checks, saved schema, error messages for already-invalid **string** IDs, external execution and all valid selections remain unchanged.

**Regression cases:** malformed selectors include `None`, scalar values, dictionaries, nested/unhashable lists, unknown IDs, duplicates and length beyond the saved-kit limit; ensure deterministic `KitError`, no mutation, no JSON/log creation or vendor execution. Valid tuple inputs produce ordinary JSON lists, and empty in-memory previews still work. The required proof remains full exact-PR-head Windows Python 3.11/3.14 CI followed by independent merged-main CI. No real vendor/GUI/company approval is claimed.

## Direct plugin-choice input validation follow-up (in review)

The existing `my_toolkit.plugin_choices` deduplicated requested IDs using `dict.fromkeys(requested)` **before** checking the ID type; an unhashable nested list/dict therefore raised a raw `TypeError`. Direct callers could also pass malformed selected-host values to `set(selected)`, bypassing the caller's expected `KitError` boundary.

The small fix retains original ordering, duplicate collapse, plugin metadata and host/pin checks while validating host selection types and checking plugin IDs **before inserting them into a seen set**. One synthetic regression test covers null/nonstring/unhashable plugin IDs, invalid host selection collections, valid duplicate deduplication and absence of output files. No JSON schema, pin state or installer logic changes; no new abstraction, no vendor execution.

## Verified direct kit and plugin input boundary results (PRs #93/#94)

- [PR #93](https://github.com/greatgc-flow/portakit/pull/93) exact head `c5a6acfa92d00421a09a1e3070a7ca66137b35f5`: [Windows CI #41265234612](https://github.com/greatgc-flow/portakit/actions/runs/41265234612) **726/726 PASS** each on 3.11/3.14. Squash source `e0abe0829df5b5915c5e9f2bcfa68df73844a01f`: independent [main CI #41265304539](https://github.com/greatgc-flow/portakit/actions/runs/41265304539) **726/726 PASS** each. All four logs inspected.
- [PR #94](https://github.com/greatgc-flow/portakit/pull/94) exact head `02a9ff54c6147a2e1c2fa7049b9f65c6190d0df3`: [Windows CI #41265472711](https://github.com/greatgc-flow/portakit/actions/runs/41265472711) **727/727 PASS** each. Squash source `67da8b7e52144d8c61b2301d035e3a716300b1a3`: independent [main CI #41265563813](https://github.com/greatgc-flow/portakit/actions/runs/41265563813) **727/727 PASS** each. All four logs inspected.
- Negative test evidence applies to synthetic API inputs and headless model state only. No original vendor binaries, permission gates, download/install network path, Tk GUI field use, licensed distribution or end-user organization approval was carried out. Remaining refactor candidates optional under Issue #87.

## Final candidate — strict manifest schema and documentation SSOT (verified)

**Actual source defect:** `toolsets.load_manifest` used `data.get("schemaVersion") in (1, 2)`, so Python accepted `true` as schema version 1 and accepted `1.0`/`2.0` as integer versions. This was inconsistent with saved personal-kit `read_kit` which already requires `type(schemaVersion) is int`. The minimal fix reuses the existing strict declarative JSON reader, requires an actual JSON integer of exactly 1 or 2 and preserves the existing `ToolsetError` message. One no-vendor negative test covers booleans, floats, strings, null and collection values while verifying a valid v2 manifest and no side effects.

**Documentation navigation defect:** The historical `docs/HANDOFF.md` called its 2026-10-23 R2 pointer "Latest" and its 2026-10-22 handoff "CURRENT"; the 2026-11-01 handoff's reusable **new-chat prompt still asserted an old 706/706 and PR #82-era SHA**, while README repeated PR #84's 708-test checkpoint under a "Latest" heading. These source-correct historical checkpoints could be mistaken for current validation by the next session.

**Narrow fix:** declare the actual GitHub `main`/Windows Actions/PRs/Issues as current authority; make `docs/handoff/START_NEW_CHAT_PORTAKIT_20261101.md` the single dated handoff and updated next-chat entrypoint; label all prior sections as archive; remove fixed SHA/count from the copyable prompt only. Preserve links, recorded PR SHAs, historical counts and business approval limitations. Add two small documentation navigation regressions: archived pointers route to the one handoff; copyable prompt cannot hard-code stale SHA or PASS count. Do not generate a new framework, rewrite history or infer real vendor/enterprise approval from CI.

### Verified source evidence — PR #96

- Exact PR head `eb911e3d5ad0895ec8c49730f6ff278a009c9276`: [Windows CI #41271532294](https://github.com/greatgc-flow/portakit/actions/runs/41271532294) **730/730 PASS each** on Python 3.11/3.14, both job logs checked; [live Windows archive smoke #41271532127](https://github.com/greatgc-flow/portakit/actions/runs/41271532127) success.
- Squash source `b7e0bce301897189ecaadf128b54b6394f256749`: independent [merged-main Windows #41271622068](https://github.com/greatgc-flow/portakit/actions/runs/41271622068) **730/730 PASS each**, both logs examined.
- 727→730 total tests per version (one manifest type check + two documentation-navigation checks). All tests are source/synthetic assurance; a live archive smoke does not certify vendor execution in company environments. This closes source-verified #87 P3 documentation/manifest scope, not final-user acceptance.

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
