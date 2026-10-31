# PortaKit backlog (prioritized, evidence-based)

## 2026-11-01 — safe read-only Explorer stale-link diagnosis

- [x] Extend existing `scripts/context_menu.py status` only: exact PortaKit-owned menu keys are `STALE` when the target executable moved/vanished, the saved root no longer matches `--root`, or the managed receipt is absent. Keep `OWNED`, `FOREIGN`, `MODIFIED`, `ABSENT` distinct and preserve exact file-mirrored console messages.
- [x] Regression-test removed executable, missing receipt and moved managed root with mock registry; verify `status` makes no registry changes and explicit `remove` remains reversible. No Windows 11 shell COM, services, admin, registry mutation during source-only CI.
- [ ] Verify exact PR-head Windows Python 3.11/3.14 CI and independent post-squash `main` CI. Real Explorer GUI/EDR/enterprise approval remains final-user-owned.

## 2026-11-01 — toolset post-install state verification (source-only)

- [x] Inspect `scripts/toolsets.py` batch apply: a zero-exit core JSON success had been counted as installed without reopening the managed state receipt and verifying the destination exists under the pinned catalog. Close the false-complete evidence path with `status_of` and `core.read_state` **after each child response**; stop on missing/mismatched receipt or directory; preserve previously completed tools and exact mirrored evidence.
- [x] Add synthetic tests for success JSON with absent receipt, missing directory, and wrong SHA receipt; update approved-fixture runners to write simulated managed receipts. No vendor binaries, process-tree/OS sandbox, or enterprise approval claim.
- [ ] Complete final PR exact-head Windows 3.11/3.14 CI, squash merge and independently verify merged-main push CI before closing.

## 2026-11-01 — fail-closed core child pipe reader (source-only regression)

- [x] Close a specific failure path in `scripts/bounded_process.py`: an unexpected exception in an output reader thread could otherwise be printed only as a background thread traceback while the installer receives an incomplete but apparently successful capture. Treat **all ordinary reader/pipe-close exceptions** as `RUNTIME_ERROR` and terminate the direct child on reader failure.
- [x] Add a deterministic synthetic test injecting `RuntimeError` into the capture reader without patching `subprocess` globally; existing exact-limit, overflow, timeout and nonzero-return behavior must remain unchanged.
- [ ] This does **not** add CPU/RAM/disk limits or process-tree termination. Operator-approved vendor execution and enterprise acceptance remain the final user's responsibility. Verify exact-head Windows 3.11/3.14 CI, squash merge and independent post-merge `main` CI before declaring completion.

## 2026-11-01 — handoff / session closure SSOT

- [x] [Current handoff and copyable new-chat prompt](handoff/START_NEW_CHAT_PORTAKIT_20261101.md) records exact last code/doc `main` `769860bf9042ff1c0e09fbf0febf7701b9507e2a`, [Windows CI #41218229391](https://github.com/greatgc-flow/portakit/actions/runs/41218229391) **686/686 PASS** per Python 3.11/3.14, reviewed PRs #67–#73, unchanged four open Issues and distinct final-user/site acceptance ownership.
- [ ] Final docs-only handoff PR and merged-main CI must be independently reverified before claiming any newer SHA is a validated latest SSOT. Never publish private host or third-party vendor assets.

## 2026-11-01 — industrial protocol client/server research source matrix (merged PR #73)

- [x] Review eight report candidates (**Secs4Net, secsgem, pymcprotocol, python-snap7/Snap7 Server, cpppo, PyXGT, QModMaster and open62541**) against upstream evidence in [role matrix](../research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md). Disambiguate GEM host/equipment vs HSMS active/passive, PC PLC client vs virtual PLC server, and SDK vs runnable simulator.
- [x] Provide safe role-based candidate guidance and fail-closed framing/timeout/memory/concurrency test criteria. **No active listener, probe, vendor download, real I/O, new pin, simulator binary, or release**. Preserve distinct final-user enterprise and live lab acceptance.
- [x] [PR #73](https://github.com/greatgc-flow/portakit/pull/73) squash merged `769860bf9042ff1c0e09fbf0febf7701b9507e2a`. [Exact PR-head CI #41218083490](https://github.com/greatgc-flow/portakit/actions/runs/41218083490) and [post-merge main CI #41218229391](https://github.com/greatgc-flow/portakit/actions/runs/41218229391) both **686/686 PASS** per Windows Python 3.11/3.14, actual job logs inspected. Research is a source capability matrix only; exact runtime, legal and operator tests remain final-user responsibilities.

## 2026-11-01 — bounded core install subprocess in optional toolset apply (merged PR #72)

- [x] Replace default unbounded `subprocess.run(capture_output=True)` in `scripts/toolsets.py apply` with a small Windows-compatible independent `scripts/bounded_process.py`: **600s per child** (CLI `--child-timeout 1..3600`), concurrent stdout/stderr drains, **256 KiB per stream**, prompt direct-child stop on timeout/output overflow, no shell/inherited stdin.
- [x] Fail-closed batch on launch error, TIMEOUT, OUTPUT_LIMIT, failed/invalid core result JSON (duplicate success keys or non-null error), with exact locally mirrored console failure evidence; previously managed tools never silently rolled back. The injected fake runner remains available solely to synthetic regression tests.
- [x] Add **10 bounded-process synthetic Python child tests** + **5 batch integration negative tests**, no vendors/network/reg/driver/industrial listener. Describe that this is **not** an OS process-tree sandbox (descendants, CPU/RAM/disk/network not contained).
- [x] [PR #72](https://github.com/greatgc-flow/portakit/pull/72) squash merged `93474402bad5456d0bb9cf5f42cb3f76775e7776`. [Exact PR-head Windows CI #41217453966](https://github.com/greatgc-flow/portakit/actions/runs/41217453966) and [merged-main CI #41217743395](https://github.com/greatgc-flow/portakit/actions/runs/41217743395) each **686/686 PASS** on Python 3.11/3.14 (individual job logs verified), [pinned archives #41217453967](https://github.com/greatgc-flow/portakit/actions/runs/41217453967) SUCCESS. Real-world acceptance is final-user responsibility.

## 2026-11-01 — shared strict JSON boundary for catalog, installed state and toolsets (merged PR #71)

- [x] Establish **one** source-level JSON parser in `portakit.py`, rejecting duplicate object keys at all depths and nonstandard NaN/Infinity. Use it for `catalog.json` installable SHA locks, local `.portakit-state.json` receipts, `scripts/toolsets.py` declarative categories/profiles/aliases, and `scripts/my_toolkit.py` v1/v2 personal kits. Invalid input fails closed; do not rewrite existing files.
- [x] Add 9 vendor-free negative tests: top-level/nested catalog duplicate SHA; invalid numeric constant, installed-state duplicate IDs/lock/NaN, toolset schema/category duplicated keys and nonfinite metadata. Existing v1/v2 kit-reader negative tests remain intact after parser deduplication.
- [x] [PR #71](https://github.com/greatgc-flow/portakit/pull/71) squash merged as `b35f20d52131c367eddbd5e78dcf5f91fed71c68`; [exact PR-head CI #41216187278](https://github.com/greatgc-flow/portakit/actions/runs/41216187278) and independently [post-merge main CI #41216414526](https://github.com/greatgc-flow/portakit/actions/runs/41216414526) **671/671 PASS** each for Windows Python 3.11/3.14, individual logs confirmed; pinned archives run #41216187363 SUCCESS. This is source-level proof, not final-user enterprise acceptance.

## 2026-11-01 — final-user acceptance ownership; personal-kit input/output hardening (merged PR #70)

- [x] Formalize developer vs final-user responsibility in [END_USER_ACCEPTANCE.md](END_USER_ACCEPTANCE.md): actual vendor GUI/runtime/portability, EULA/OSS/EDR/transfer, local performance and deployment decisions are the end-user/organization's. Source-only CI, review and implementation are independent; a green CI never impersonates legal/operational approval.
- [x] Personal-kit `scripts/my_toolkit.py` JSON reader rejects duplicate keys at any level and NaN/Infinity, including nested pin and plugin assertions, with no install or automatic rewrite. Create-only JSON/console-log save uses guarded **best-effort** failure rollback that leaves foreign/replaced files untouched. Optional GUI import remains all-or-nothing.
- [x] Add 9 synthetic, vendor-free negative tests covering duplicate v1/v2 assertions, nonstandard values, errors/collisions on save and UI selection preservation. Live desktop acceptance is not performed by CI and remains final-user responsibility.
- [x] [PR #70](https://github.com/greatgc-flow/portakit/pull/70) squash merged as `1647fe182c461b8370c1d01edec20ab3bf6a054b`. [Final PR-head CI #41215662333](https://github.com/greatgc-flow/portakit/actions/runs/41215662333) and [post-merge main CI #41215781088](https://github.com/greatgc-flow/portakit/actions/runs/41215781088) both **662/662 PASS** per Windows Python 3.11 and 3.14, checked job logs. Issue #25/#27/#36 bodies now distinguish developer technical work from final-user enterprise acceptance; no false certification.
- [ ] Product source gaps (e.g. unsupported archives / industrial CLIENT vs SERVER matrix) remain project backlog; end-user approval ownership is **not** blanket permission to ship unknown vendor software.

## 2026-11-01 — independent editor-plugin receipt and health-evidence hardening (merged PR #69)

- [x] Make `scripts/plugin_offline.py` **fail closed on duplicate JSON keys** at every nesting level in persistent plugin receipts; reject NaN/Infinity and malformed/noncanonical host:plugin receipt identifiers. Do not silently trust last-wins source/hash fields or rewrite affected evidence.
- [x] Align `scripts/plugin_health.py` with invocation-owned, guarded best-effort JSON/console-log rollback; respect existing or replaced output files. No plugin installation, vendor process, download, network listener, registry or default behavior change.
- [x] Add **10 source-only negative tests** (duplicated receipt ID/lock/file hash, NaN, unsafe keys; JSON/log failures, competing/replaced output and existing log), plus explicit operator guidance and limitations.
- [x] [PR #69](https://github.com/greatgc-flow/portakit/pull/69) squash merged `fe2d9dddc08f8931433bc038a5cb30a306153c18`. [Final-head Windows CI #41214761613](https://github.com/greatgc-flow/portakit/actions/runs/41214761613) and [post-merge main CI #41214866286](https://github.com/greatgc-flow/portakit/actions/runs/41214866286) each **653/653 PASS** per Python 3.11 and 3.14; results recorded in Issue #36.
- [ ] Actual company-use/EULA/EDR/transfer approval, local real original plugin archives, Notepad++ desktop load/compatibility, negative GUI tests and final release signoff remain **NOT_VERIFIED**. Keep issue #36 open.


## 2026-11-01 — original ZIP and CSV smoke producer output I/O (merged PR #68)

- [x] Harden both **independent** report producers (`scripts/xan_zip_preflight.py` and `scripts/csv_operator_smoke.py`) against partial JSON/log writes. Reuse one identity-guarded best-effort helper in `scripts/toolsets.py`: cleanup only regular output files still matching IDs captured from this invocation's open handles; preserve any foreign/existing/replaced file on collision/failure.
- [x] Add 9 synthetic, vendor-free regression tests covering JSON serialization failure, log emission failure, concurrent JSON collision, replaced foreign JSON preservation, and a directory replacement guard. Both producers must preserve exact console-mirrored log on success, with no implicit vendor execution.
- [x] [PR #68](https://github.com/greatgc-flow/portakit/pull/68) Windows PR CI [#41213874077](https://github.com/greatgc-flow/portakit/actions/runs/41213874077), tested code HEAD `1d198dd2647eb8b29ed107b5b4c6c3ca341891ac`, **643/643 PASS** per Python 3.11 and 3.14 (both job logs inspected). Final docs-inclusive PR CI #41214000258 and post-merge main CI #41214103529 both independently SUCCESS, 643/643 per Windows Python version; squash-merged as `853ffe86f735ab30ac4afc7531f7603c55ba7fa3`.
- [ ] Real original publisher identity, corporate EULA/EDR/transfer approval, isolated Windows CSV behavior, negative compatibility, performance and release signoff remain **NOT_VERIFIED**. Keep xan RESEARCH_ONLY and Issue #25 open.
- **Limit:** best-effort failure cleanup is not an atomic filesystem transaction, a guarantee across power loss/process kill, or authenticated evidence; failed output must never be interpreted as a completed record.

## 2026-10-31 — CSV evidence schema-v1 claim boundary (merged PR #67)

- [x] Source-only fix in [Draft PR #67](https://github.com/greatgc-flow/portakit/pull/67): reject unknown keys in the exact version-1 source/smoke report contracts, including nested member/EXE/hash maps and evaluated process records. This blocks silent, unrecognized approval claims in coordinated JSON/log rewrites.
- [x] Verify the SHA-256 of an exactly zero-byte stdout/stderr record and align blocked-workspace arrays with the producer's sorted/unique and isolated scan-error sentinel rule. Add 12 negative synthetic regression tests and document compatible version evolution.
- [x] **PR-head Windows Python 3.11 and 3.14 full CI:** [run #41212654463](https://github.com/greatgc-flow/portakit/actions/runs/41212654463), tested commit `1510b2610ef550402ccb96270a9a0a7547e35bc3`, both Windows versions **634/634 PASS**, individual job logs reviewed. Earlier red runs reflect a corrected outdated test diagnostic assertion. Final docs-inclusive PR CI #41212878514 and merged-main CI #41213461562 SUCCESS, 634/634 per version; squash-merged as `6cd5ae06f02d291e9a916043f401e2dfd05899d7`. Historical main 622/622 PASS is separate.
- [x] Superseded former session-only no-merge instruction: user subsequently explicitly authorized merging. PR #67 merged as verified above; subsequent PRs #68/#69 also merged after green Windows CI.
- [ ] Real vendor ZIP/exe provenance, corporate legal/EDR/transfer, genuinely isolated Windows smoke, compatibility, performance and release acceptance remain NOT_VERIFIED. Keep Issue #25 OPEN and xan RESEARCH_ONLY.

## 2026-10-31 — session-closeout SSOT

- [x] Preserve merged #57–#59 code / docs, original-source security test failures and fixes, exact main/PR Windows 554-test evidence, VSG goals and independent enterprise reality gates in [final closeout](handoff/PORTAKIT_20261031_FINAL_CLOSEOUT.md).
- [x] Provide [single new-chat prompt](handoff/START_NEW_CHAT_PORTAKIT_20261031.md) and update older handoff pointer; do not copy personal chat content/vendor binaries into a public repository.
- [x] Independently verified the exact closeout/docs-only main commit 2289e4f1f71c3fc2b5f2211d398be1179e694e11 on [Windows CI #41185778538](https://github.com/greatgc-flow/portakit/actions/runs/41185778538): Python 3.11 554/554 PASS and Python 3.14 554/554 PASS, both logs checked.
- [ ] Keep issue #25, #27, #36, #51 gates open until specific real-world proof/owner approvals.


## 2026-10-31 — read integrity and safe partial-output cleanup

- [x] Strengthen the existing read-only CSV evidence checker: bounded regular file read with reparse checks plus path/handle metadata comparisons before, during, and after read (file identity, size, timestamps, mode). Distinguish detected mutations without claiming an atomic snapshot.
- [x] Protect output evidence from collision and rollback errors: exclusive-create JSON/log, cleanup only invocation-created files whose identity still matches, do not unlink a foreign log or target on an intervening collision, handle JSON serialization / log emission exceptions. Unit tests cover each mutation/failure boundary and input non-modification.
- [ ] Genuine Windows physical vendor/enterprise/airgap approval is still NOT_VERIFIED; human acceptance gate #25 remains open, and xan stays RESEARCH_ONLY.

## 2026-10-31 — original ZIP member path and evidence log safety

- [x] Reject path-traversing, spoofed-suffix, Windows-device, backslash and control-character member/root names in xan source reports using the shared core ZIP path validator. Also validate blocked-case unexpected workspace paths and bound historical REPORT console-footer text; preserve the authentic scan-error sentinel and legitimate copied evidence. New synthetic-only positive/negative regression tests.
- [ ] Source metadata and cross-reports are still mutable text; authentic original ZIP, enterprise legal/EDR/transfer, physical nonproduction Windows approval, vendor runtime and repeatable performance remain NOT_VERIFIED. Keep xan RESEARCH_ONLY and Issue #25 open.

## 2026-10-31 — source and failed-case evidence consistency

- [x] Cross-check original ZIP report's candidate/provenance/unverified labels, normalized roots and accounting counters, bound executable note and smoke attestation labels. Independently enforce original CSV evaluator's per-case process/timing/output schema for both PASS and BLOCKED statuses, separating valid runner exceptions, actual command failures and output-limit conditions. Synthetic-only negative/positive regression tests; no vendor process, executable download or change to default read-only operation.
- [ ] Physical original release provenance, corporate EULA/EDR/transfer, authorized host isolation, vendor compatibility, and repeatable CPU/RAM/disk benchmarks still require human evidence. Keep Issue #25 OPEN and xan RESEARCH_ONLY.

## 2026-10-31 — deterministic synthetic fixture consistency

- [x] Independently derive synthetic `edge.csv` and `bulk.csv` expected UTF-8/CRLF SHA-256 hashes from the existing fixed fixture grammar and recorded row count without generating files. Reject coordinated CSV+recorded-hash mutation or unsupported row count; include lower/upper boundary and negative tests, preserve default read-only behavior.
- [ ] Actual approved vendor original, execution, enterprise EULA/EDR/transfer, offline host, compatibility and measured performance remain NOT_VERIFIED. Keep Issue #25 open and xan RESEARCH_ONLY.

## 2026-10-31 — strict local evidence format / contradiction regression

- [x] Harden the existing read-only xan↔CSV evidence cross-check: canonical UTF-8/LF/final newline and single footer verification instead of splitlines() equivalence; reject duplicate nested JSON keys and NaN/Infinity; reject impossible PASS process-exit, truncation, size and digest claims. Independent synthetic-only negative tests, unchanged CLI and source-only scope.
- [ ] Actual original-file publisher, enterprise EULA/EDR/transfer/host and isolated vendor runtime evidence remain NOT_VERIFIED; retain xan RESEARCH_ONLY and Issue #25 OPEN. Internally consistent reports do not imply authenticity.

## 2026-10-31 — read-only cross-evidence chain follow-up

- [x] Add [independent source ↔ CSV evidence verifier](CSV_EVIDENCE_CROSSCHECK.md) and negative tests: pinned xan release ZIP SHA/bytes, optional ZIP-member ↔ local EXE match, recorded smoke EXE SHA, four semantic test verdicts, synthetic fixture hashes and original console log/JSON correspondence. Default read-only, optional create-new JSON + identical log, no vendor execution.
- [ ] Obtain separately approved physical Windows originals, test and security/legal evidence before treating any chained result as real-world admission proof. Mock-only CI means only script behavior is verified; keep Issue #25 OPEN and xan RESEARCH_ONLY.

## 2026-10-31 — next-session operator acceptance handoff

- [x] Provide an [operator-local xan/Miller acceptance package](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md) with seven independent reality gates, verified exact-head 554/554 latest Windows CI, existing safe commands, evidence-key cross-checks, and fail-closed STOP rules. The document itself is NOT real vendor/legal/host acceptance.
- [ ] Obtain separate approved original and enterprise security/legal/EDR/transfer clearance, then perform physical offline Windows testing and repeated benchmark evidence. Issue #25 stays OPEN; no catalog promotion.

## 2026-10-31 — xan original ZIP ↔ local EXE read-only identity (merged PR #59)

- [x] Keep the preceding [xan ZIP structural preflight](XAN_ZIP_LOCAL_PREFLIGHT.md) isolated and source-only. Stream-hash the unique `xan.exe` ZIP member during existing CRC reading (no extraction or extra decompression), report member path, bytes and SHA-256.
- [x] Optional `--exe ABSOLUTE\\xan.exe` hashes an explicitly provided local executable twice and fails closed on byte/size mismatch, zero-size exe, missing/renamed/reparse path or mutation; re-hash the original ZIP on its same unbuffered handle after comparison. No vendor execution or automatic operator action.
- [x] Add mock/synthetic-only positive/negative tests for wrapped ZIP, exact identity, mismatch, mutation, invalid/empty/oversized paths and bytes, command error codes, optional evidence JSON and exactly mirrored local console transcript.
- [x] [PR #59](https://github.com/greatgc-flow/portakit/pull/59) merged as `8e1d87050f14d77b14b14188fd67d0c3d330d712` after [exact-head PR CI #41182344874](https://github.com/greatgc-flow/portakit/actions/runs/41182344874) **Windows Python 3.11/3.14: 554 tests each PASS**. Independently confirmed [post-merge code main CI #41182417335](https://github.com/greatgc-flow/portakit/actions/runs/41182417335) both Windows versions SUCCESS. [Issue #25](https://github.com/greatgc-flow/portakit/issues/25#issuecomment-6540847570) documents local byte identity versus remaining real-world gates. Final docs-only main CI requires separate verification.
- [ ] **Real** official xan ZIP → approved local executable equality, corporate EULA/EDR/transfer, offline Windows CSV behavior and Miller comparative memory/performance remain **NOT_VERIFIED**; do not promote research-only xan to catalog.


## 2026-10-31 — xan read-only local original ZIP SHA and CRC preflight (merged PR #58)

- [x] Added `scripts/xan_zip_preflight.py` as independent supplemental *RESEARCH_ONLY* tool using locked official-release snapshot's xan 0.61.0 Win x64 ZIP original size and digest. It **never downloads/executes/extracts/installs**, and does not change the catalog.
- [x] Original SHA+bytes precheck, streaming ZIP CRC and declared sizes, 4,096-member/512MiB expanded bounds, 32-level path depth, Windows path/ADS/device/link/case collision/file-as-parent checks, exact one xan.exe requirement, postcheck SHA on same open original handle.
- [x] Synthetic SHA mismatch/CRC/truncated/escape/symlink/special/case/expanded-budget/duplicate/no-exe/metadata drift/changed-source/no-overwrite and exact console-mirror regression tests. Real official xan ZIP was **NOT** downloaded or examined, so original/hash/Windows acceptance remains OPEN.
- [x] [PR #58](https://github.com/greatgc-flow/portakit/pull/58) squash merged as `b9efb8d4f523ed98b91aa7bcc4a6afbf5f724b46` only after [latest-head Windows 3.11 + 3.14 CI](https://github.com/greatgc-flow/portakit/actions/runs/41174372211) **543 tests each PASS**. Fixed two real Windows-only test defects identified by earlier failing CI: stale same-handle buffered SHA after mutation; normalized backslash name in test ZIP writer. [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) includes exact verification evidence and explicit pending real vendor/enterprise gates. **Post-merge code main CI** [run 41174684490](https://github.com/greatgc-flow/portakit/actions/runs/41174684490) remained queued at handoff update; latest docs-only main CI also requires independent checking.
- [ ] Approved actual local original ZIP SHA and physical Windows runtime tests, pathological CSV, benchmark, company license/EDR/redistribution remain **NOT_VERIFIED**.

 
## 2026-10-31 — bounded live stdout/stderr capture for operator CSV smoke (merged PR #57)

- [x] Audited prior CSV smoke implementation against VerySimpleGuide safety/evidence claims: `subprocess.run(..., stdout=PIPE, stderr=PIPE)` collected output without limit until termination, despite a stated 256 KiB post-run threshold.
- [x] Isolated `call_vendor` now uses direct `Popen` and concurrent bounded pipe readers, retaining at most 256 KiB + 1 byte on **each** stdout/stderr stream and terminating the direct process when either crosses limit; per-call timeout likewise terminates the direct child. Stronger **actual output-memory limit**, not a vendor RAM/disk/network sandbox or process-tree kill.
- [x] Add synthetic Python subprocess tests for normal separate pipes, stdout/stderr overflow, real timeout, launch failure and explicit prefix digest semantics; no third-party executables run in CI. Keep existing vendor mock tests and all existing catalog/license/EDR/research gates.
- [x] [PR #57](https://github.com/greatgc-flow/portakit/pull/57) merged as `0c52c929506078fed84ba1ac491c58c6f6ada560` after [PR Windows Python 3.11 and 3.14 each 520/520 tests PASS](https://github.com/greatgc-flow/portakit/actions/runs/41172474618). [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) records evidence and open real-world gates. **Post-merge main CI** [run 41173199779](https://github.com/greatgc-flow/portakit/actions/runs/41173199779) was queued at handoff update; DO NOT treat as success before confirming exact final HEAD. Document-only follow-up commit also requires its own CI.
- [ ] Real approved xan/Miller Windows original archives, corporate permission and standalone offline runtime behavior remain **NOT_VERIFIED**.


## 2026-10-31 — VSG-guided Miller/xan opt-in Windows CSV smoke (merged PR #56)

- [x] Reviewed [VerySimpleGuide](https://github.com/greatgc-flow/VerySimpleGuide) main `0aef4e93cbd9b746c4927f08ce9bfda685e897e4`: Very Simple fitness, separate real-world gates, no inferred observations, explicit consent, bounded operation, exact console evidence, ongoing feedback. **Guidance applied, no mandatory imported framework or claim of full conformance.**
- [x] New independent `scripts/csv_operator_smoke.py`: default read-only `plan`, optional Windows-only `run` requires `--yes --approved-offline`, explicit local `mlr.exe/xan.exe`, new evidence directory. Fixed documented commands count/CSV select, synthetic UTF-8 Korean/comma/quotes/CRLF/multiline plus bounded bulk count, per-call timeout, output correctness, file/EXE SHA and unexpected workspace writes, new-only JSON plus exact console `.log`.
- [x] Headless synthetic/mock-only tests for opt-in consent, function/parse errors, changed files, unexpected writes, timeouts, no overwrite, null/empty/invalid inputs and no accidental vendor calls. No real vendor downloads/launches by CI, no registry/PATH/OS changes or new pin.
- [x] [PR #56](https://github.com/greatgc-flow/portakit/pull/56) squash-merged as `572d6f4c8832ecdb9fe49c777930e157a1b5a9c1`; [PR Windows CI](https://github.com/greatgc-flow/portakit/actions/runs/41170746060) and [post-merge code main CI](https://github.com/greatgc-flow/portakit/actions/runs/41170884529) both **514 tests PASS on Python 3.11 and 3.14**. [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) comment records exact safety/acceptance gaps; issue stays OPEN.
- [ ] Actual locally verified official xan ZIP SHA, live authorized offline Windows CSV/BOM/UTF-16/invalid-data/large-file smoke, repeated CPU/RAM/disk benchmarks, legal/EDR/redistribution approvals and GUI gates remain **NOT_VERIFIED**. CLI's 256 KiB output threshold is evaluated **after** process completion and cannot bound malicious vendor memory/disk/network usage; test only on an approved isolated host, propose stronger bounds after observing need. Do not equate passing mocked CI or a single live count with admission.


## 2026-10-31 — DuckDB read-only TAR structure audit and qsv/xan investigation (merged PR #55)

- [x] Independent `scripts/targz_preflight.py` verifies separately authorized **local original** DuckDB 2.0.0 x64 TAR SHA-256 against existing research metadata. Bounded gzip/TAR scan, Windows-safe relative paths, no links/special/PAX, case collision, parent-file conflicts, file/member/depth/expanded-stream limits, second SHA after scan. **No extraction, vendor execution, download or installation**; core `zip/exe/sfx7z` behavior unchanged.
- [x] Optional new-only JSON plus byte-identical console log; synthetic negative/positive TAR regressions. Exit 0 means local structure only, **not** compliance, runtime or installation acceptance.
- [x] Official GitHub release metadata: qsv 27.0.1 current Windows x64 MSVC/GNU ZIPs **402,543,109 / 129,287,020 compressed bytes**, both exceed the current 100MiB compressed limit; no automatic raising. xan 0.61.0 Windows x64 MSVC ZIP **6,473,075 compressed bytes**, compact candidate. Respect qsv's current MIT COPYING; xan MIT/Unlicense COPYING; neither company-redistribution/EDR approved. Research-only supplemental ledger and tests, no catalog or 151 selectable ID change.
- [x] [PR #55](https://github.com/greatgc-flow/portakit/pull/55) merged as `570e198630e3dc71bc075f115d26ae9878cabe23`. Both Windows Python 3.11/3.14 full suites **499 tests each PASS** and [post-merge main CI](https://github.com/greatgc-flow/portakit/actions/runs/41169678506) **PASS**. [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) updated with source evidence and open human gates; no candidate admitted.
- [ ] Real DuckDB official TAR physical SHA + file layout, actual expanded footprint and safe runtime/extension/no-network policy; xan source/version Windows functional and corporate license/EDR/transfer authorization; Tailviewer real GUI remain **HUMAN_NOT_VERIFIED**.


## 2026-10-31 — evidence-only three-tool lightweight research (merged PR #54)

- [x] Check official GitHub 2026-10-31 release API and vendor docs for DuckDB CLI v2.0.0, xsv 0.13.0 and Tailviewer v1.0.0-rc1; record actual asset filenames, official compressed byte counts and **metadata-only** SHA availability without downloading any binary.
- [x] Distinguish DuckDB `tar.gz` (not accepted by current `zip/exe/sfx7z` installer), Windows VC++ runtime, automatic extension/network permissions from approved offline smoke. xsv upstream archived in 2025; author recommends qsv/xan. Tailviewer has 2022 portable ZIP and .NET Framework 4.7.1+ prerequisite.
- [x] Add machine-readable supplemental research ledger and optional read-only `lightweight_review.py` audit with eight open enterprise/runtime/size gates, no auto-promotion, new-only local JSON+console evidence and headless regressions. Three IDs stay `RESEARCH_ONLY`; no actual binary downloaded or used.
- [x] [PR #54](https://github.com/greatgc-flow/portakit/pull/54) squash-merged as `3aa83daf478f797b6407052d590ea8762024ed20`. Windows Python 3.11 and 3.14 PR runs each **482/482 PASS**, and [post-merge code `main` CI](https://github.com/greatgc-flow/portakit/actions/runs/41168279537) both PASS. Findings recorded in [Issue #25](https://github.com/greatgc-flow/portakit/issues/25); no software was promoted.
- [ ] Independent live vendor-original SHA, safe extraction, expanded bytes, Windows execution/performance, corporate EULA/OSS/EDR/redistribution approvals remain unverified. Never claim automatic admission or public Release.


## 2026-10-31 — idempotent offline editor-plugin apply (merged PR #53)

- [x] Reuse `plugin_offline.make_plan` state to SHA-check original ZIPs only for missing pinned plugins. Installed plugins are still fully rehashed against receipts, and changed/unknown/legacy entries block before any install.
- [x] Make `--offline-dir` optional **only** for fully managed/no-op `apply`; `verify` continues requiring originals for every pinned choice. Missing items without a source folder fail closed. Dual operator consent, per-plugin rollback, locks and console-evidence behavior remain unchanged.
- [x] Six independent synthetic regressions: installed no-source no-op, mixed missing-only preflight, missing archive non-mutation, no-directory blocking, CLI consent and research-only no-op.
- [x] [PR #53](https://github.com/greatgc-flow/portakit/pull/53) merged as `ff2af0ce76f1157d7398d5c0b65a1992c4e8ca0e`; Windows Python 3.11/3.14 PR full suite **471/471 each PASS**, and [post-merge `main` CI](https://github.com/greatgc-flow/portakit/actions/runs/41161224819) **PASS**. Separate live plugin/GUI compatibility, EULA/OSS/EDR, source-transfer and public Release human gates remain open (Issue #36).


## 2026-10-31 — selected-only GUI and frozen research-stage safety (merged PR #52)

- [x] Optional `Selected only` model/UI filter combines with search, primary domain and effective approval stage; empty selection stays valid and filters do not mutate saved kit or launch vendor apps.
- [x] Imported former `RESEARCH_ONLY` items remain visibly `PENDING (locked)` and excluded from GUI `READY` filter after their catalog pin is later added. They are installable only after explicit remove/reselect and a newly saved validated snapshot.
- [x] Split the crowded GUI filter line into two compact rows to improve minimum-width usability; **actual 850px/100-200% DPI, keyboard screen reader and Korean IME acceptance remains HUMAN_NOT_VERIFIED.**
- [x] [PR #52](https://github.com/greatgc-flow/portakit/pull/52) squash-merged as `1f14b505`; PR Windows Python 3.11/3.14 **465 tests each PASS**. [Post-merge main Windows CI](https://github.com/greatgc-flow/portakit/actions/runs/41159957752) is independently tracked. Pinned metadata does not imply corporate legal/EDR approval.


## 2026-10-31 — one-command personal-kit doctor (merged PR #50)

- [x] Implement independent source-only `kit_doctor.py` + Windows CMD: compose the **existing** offline readiness, managed logical size, and optional editor-plugin health engines without modifying them or adding vendor binaries. No automatic install, live GUI, registry or network calls.
- [x] Reject input errors and mismatched per-pin assessment IDs. Separate `BLOCKED`, `INCOMPLETE`, `LOCAL_CHECKS_PASS` and documented exit 2/1; pending research, OS-only or editor selections never imply whole-kit PASS. Optional new-only JSON plus stdout-mirrored evidence.
- [x] [PR #50](https://github.com/greatgc-flow/portakit/pull/50) merged as `3d486ea`; full Windows Python 3.11 and 3.14 matrices **461/461 tests each PASS**, including [post-merge main CI](https://github.com/greatgc-flow/portakit/actions/runs/41083220122). Remaining enterprise/legal/human gates stay open.
- [ ] **Human/legal still open:** company EULA/OSS/EDR and source transfer approvals, GUI DPI/IME/accessibility, WinMerge Office4, on-site vendor executables and final Release authorization. Local checksum status is not enterprise release acceptance.


## 2026-10-30 — personal-kit GUI operator acceptance workflow

- Optional `scripts/PickerAcceptance.cmd` / `scripts/picker_acceptance.py`: safe static preflight (Python/Tk availability, source hash and syntax) reports `NOT_VERIFIED` without files/desktop. Explicit `--review --out` asks 14 independent operator PASS/FAIL/SKIP checks for DPI 100/150/200, IME, keyboard, filters, plugin status, save/import, readiness, size, a11y and no OS actions. New-only private JSON plus exactly program-mirrored local console log; interrupted sessions cannot silently produce PASS. No vendor executables, GUI automation, screenshot capture or new runtime dependency.
- **Still open**: actual company-approved workstation review/evidence for the 14 cases, independent screenshots where permissible, real screen-reader use, enterprise EULA/EDR/legal transfer verification. An operator's self-attestation is not independent acceptance or a public Release approval. Keep GUI Issue #27 open.


## 2026-10-30 — avoiding duplicate GUI overview implementations

- PR #46 delivered the user-triggered readiness/size GUI. PR #47 covered overlapping implementation and was closed unmerged to preserve a **single SSOT**, avoiding a second `kit_overview.py` and duplicate Tk dialog.
- This follow-up adds **per-pinned-tool** installed logical byte display or explicit `UNKNOWN`; a mismatch between source and footprint rows must fail closed. Existing install and SHA preflight engines untouched. Real desktop/DPI, operator file approval and full future size measurement remain outstanding.


## 2026-10-30 — GUI offline readiness and installed-size overview

- **Code feature:** optional GUI read-only `Inspect readiness / size…` dialog from the current selected user kit (without forcing save), showing present pinned installs, missing/wrong original sources, research/plugin exclusions, OS-only informational items, explicit pinned-subset consent, SHA verification via existing offline engine, blockers and logical bytes of already installed managed pins. No guessed future kit total, no downloads or install/apply code.
- **Verification:** new isolated headless Tk-independent tests; full Windows Python 3.11/3.14 regression and post-merge CI required. Manual DPI, GUI text layout, scroll performance for 151 items, accessibility, Korean IME, and real approved nonproduction vendor archives remain **HUMAN_NOT_VERIFIED**.


## 2026-10-30 — simpler offline personal-kit readiness

- New one-command **read-only** `scripts/OfflineCheck.cmd` + `scripts/offline_ready.py`: validate saved personal kit locks, reuse `my_toolkit.create_plan`, existing 7zr prerequisite and per-artifact SHA verifier; report exact missing original filenames, local installation status, pending/editor plugin exclusions and blockers. No network/binaries/install/registry/driver/service actions. `--skip-pending` allows readiness for pinned-only subset; `--out` creates a new local JSON+verbatim console log. Default no-write, error exit 2 for incomplete.
- Remain open: approved physical airgap transfer, vendor corporate EULA/EDR/redistribution rights, live GUI/Office4, source executables and first-run effects, full legal-binary ZIP packaging. No automatic release or admission of research-only tools.


## 2026-10-30 — GUI plugin choice visibility

- Add a selected-plugin summary with host and pinned-metadata/research-only labels, source-approved host precondition, retained historical research-only status, dynamic window width wrapping and four new headless regressions. Keep old CLI and plugin offline installation untouched. Human approved Windows GUI 850px/100-200% DPI, Korean IME and keyboard reading remain pending. This is selection-only display, not vendor binary or company-license approval.

## 2026-10-30 picker keyboard follow-up

- [x] Implement keyboard-only search/import/save, Treeview visible-list highlight/toggle/remove and clear; persist focus/highlights across row refresh; describe selected/visible counts.
- [x] Validate group addition before any mutation; unit-test malformed/duplicate batches and source shortcut bindings.
- [ ] Windows Python 3.11/3.14 CI and post-merge main verification must be checked for this commit.
- [ ] Human Tk desktop assessment: keyboard traversal, contrast, scaling, Korean accessibility and screen readers. Until signed off leave Issue #27 open and **HUMAN_NOT_VERIFIED**.



## 2026-10-30 — field plugin-health evidence

- **Candidate PR/CI gate:** optional read-only `scripts/plugin_health.py` for 3-way operator triage `LOCAL_HASH_PASS`/`INCOMPLETE`/`BLOCKED`, explicit error exit, UTC observation, optional new-only local JSON and exactly mirrored console evidence. Reuses existing managed per-file SHA validation, keeps vendor binaries and receipt state untouched; 12 unit regressions and Windows 3.11/3.14 isolated CI. [Health guide](PLUGIN_HEALTH.md).
- **Still open:** real approved Windows desktop plugin GUI/menu and Office-related human acceptance; enterprise license/EDR/source-transfer evidence and legacy receipt remediation. SHA snapshot cannot certify a trusted publisher or source.

## 2026-10-30 — installed editor plugin integrity follow-up

- **Candidate reviewed PR:** extend SHA-pinned offline plugin receipts with per-file SHA-256 (required DLL **and** nested dependencies), inspect all managed files on read-only `plan` and re-application, fail closed on content drift or legacy receipts without digests; bounded path traversal and malformed receipt denial. Preserve user data and avoid automatic overwrite/cleanup. Regression includes tampered main DLL, altered nested lib, extra/deleted file, symlink, metadata tamper and idempotent clean state. Require Windows 3.11/3.14 PASS, then post-merge CI.
- **Still human/legal gated:** real Windows host plugin behavior, vendor dependency compliance, corporate OSS/security approval, licensed source transfer. Hash integrity cannot prove the full enterprise security state.

## 2026-10-30 — individually approved offline editor plugin capability

- **Candidate PR / Windows CI gate:** new opt-in, source-only `scripts/plugin_offline.py`: plan, verify and separately consented policy-approved apply of existing pinned ComparePlus/JsonTools original offline ZIPs into an existing managed Notepad++ host. Host/version/SHA, all-source preflight, second SHA snapshot, bounded ZIP extraction, no overwrite, per-plugin receipt and rollback; Windows synthetic tests and console-mirrored evidence. No unapproved vendor archive in GitHub, no default auto-install or elevated changes.
- **Still open:** actual corporate permission, source transfer/redistribution obligations for ComparePlus GPL-3.0 and JsonTools Apache-2.0, third-party dependencies, EDR review, real GUI validation on approved workstation; four other plugin families research-only and entirely excluded. Full media ZIP and global GUI acceptance remain blocked pending legal/human evidence.

## Editor plugins — 2026-10-30 metadata-only individual choice

- **Candidate PR, CI/merge gate:** six individually selectable Notepad++/WinMerge editor plugin choices in CLI and optional Tk GUI, host prerequisite, v1 compatible v2 JSON, pinned/research distinction, no installation and no implicit download; offline manifest excludes chosen plugin binaries and footprint budget treats them as unknown. See [plugin selection guide](INDIVIDUAL_EDITOR_PLUGINS.md).
- **Remaining P1**: independently approved vendor EULAs, transfer/redistribution, host compatibility, checked vendor packages, exact per-plugin hash and rollback/GUI acceptance *before* enabling **any** actual v2 plugin deployment. Leave existing legacy `--recommended` behavior unchanged but prohibit it for v2.

## 2026-10-30 — footprint diagnostics

- **Candidate PR / CI gate:** read-only logical-byte and file-count measurement for installed, matching pinned personal-kit tools (`scripts/kit_footprint.py`, independent tests, [guide](FOOTPRINT_AUDIT.md)); symlink/junction and excessive size-tree denial; optional explicit local JSON + exact console evidence; do not infer uninstalled size or licensing from installed bytes.
- **Still deferred:** true allocated NTFS disk bytes, official compressed/archive footprint for non-installed candidates, temporary installation headroom, automatic licensed distribution bundles, individual plugin controls, full desktop GUI/operator evidence.

> **Verified milestones (2026-10-30):** personal-kit CLI PR #26, optional selection-only GUI PR #31, and source-only offline manifest PR #32 are merged and Windows post-merge matrix CI is green. Actual desktop GUI/Office4 acceptance, vendor transfer rights, and full ZIP bundling are still open. [Current handoff](handoff/START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md) records exact scope and remaining gates. Dated older work items remain as history below.


## 2026-10-30 — offline handoff refinement

- **MERGED #32 (post-merge CI PASS):** metadata-only personal asset inventory/export/verify (`scripts/offline_assets.py`) backed by source catalog SHA pins and existing `toolsets.verify_offline_assets` before tool installation; `docs/OFFLINE_ASSETS.md`. New-only JSON+mirrored log, missing/wrong/duplicate filename and hash guards, no download or vendor bundling; Windows 3.11/3.14 tests.
- **Still NOT implemented:** universal vendor-binary redistributable ZIP builder, license/EDR approval workflow, automated safe runtime launcher for every unverified tool, installed disk footprint measurement and GUI vendor acceptance. Keep these separate: legal authorization cannot be inferred from official download URLs or SHA.


## 2026-10-30 — personal-toolkit picker follow-up

- **MERGED #31 (post-merge CI PASS):** optional Python standard-library Tkinter **mouse-based, zero-install selection-only GUI** `scripts/toolkit_picker.py` and `scripts/MyToolkitGUI.cmd`. Dynamic 151-ID browse/search/category and approval filters, multi-select, pin-only presets, imported saved kits, new schema-v1 JSON and mirrored log, research-only consent preservation. Independent headless tests, Windows CI parser gate. No code path installs binaries or changes OS settings.
- **Still unverified:** real human GUI acceptance on approved Windows desktop (Tk availability, scaling at 100/150/200%, Korean text, keyboard-only operation, screen-reader behavior, window responsiveness with larger inventories, screenshot evidence). CLI remains authoritative fallback.
- **Still deferred:** individually-selectable optional editor plugins beyond existing approved recommended plugins, vendor-rights-compliant offline redistribution/package build, measured size budgets, full single-tool CLI read-only/error evidence mirroring, real Office4/Everything/grepWin/7-Zip GUI acceptance. Keep #25 legal/protocol gates independent; no new service, driver, live network scan or release.


## Personal portable toolkit composition (2026-10-25)

- **MERGED #26 (post-merge CI PASS)**: `scripts/my_toolkit.py`, `scripts/MyToolkit.cmd`, and [guide](PERSONAL_KITS.md) allow selecting any of the current 151 tool IDs into a personal JSON toolkit, with immutable approved-version SHA locks, category/preset composition, research-only and OS built-in partitions, zero-write planning, explicit safe install and offline SHA preflight via existing `toolsets.apply`. No changes to catalog or canonical taxonomy. Confirm Windows Python 3.11/3.14 tests and post-merge CI before labeling as released.
- **P1 human acceptance**: optional Tk picker/search/import/export is now implemented (#31); real GUI display, keyboard/accessibility, scaling and corporate permission checks remain HUMAN_NOT_VERIFIED. No mandatory GUI runtime or auto-download of research-only tools.
- **P1 intake**: 43 additional research-only software families from [2026-10-25 report](../research/INTAKE_ENTERPRISE_PORTABLE_20261025.json) remain *selectable but non-installable* until independently approved. Safe partial build requires explicit `--skip-pending`.
- **P2**: license-compliant optional offline media packaging and installed-footprint budgeting, reversible portable launcher session (never system PATH), and metadata-only tool discovery/filter by role. Must revalidate redistribution rights; do not bundle closed vendor binaries by default.


## Enterprise/industrial research intake (2026-10-25, opt-in and metadata only)

- **Acquired source**: one 31-page research DOCX (private, never upload to PUBLIC repo); [53 matrix-family crosswalk](../research/INTAKE_ENTERPRISE_PORTABLE_20261025.json) and [technical/license fact review](../research/ENTERPRISE_PORTABLE_REVIEW_20261025.md), including six related editor plugin mentions. Keep current 17 catalog pins and 108 canonical research entries unchanged; 43 newly discovered research-only IDs are *staged*, not installed/approved.
- **P1 research candidates**: DuckDB CLI, xsv, Tailviewer: independently verify official versions, SHA, archive/unpacked sizes, Windows compatibility, runtime dependencies, corporate-use and redistribution license, offline behavior, and synthetic functional tests; retain RESEARCH_ONLY until all admission gates pass.
- **P1 safety corrections**: `pymcprotocol` is PLC client, not a proven simulator server; report's 0.0.0.0 server sketch untrusted and never run; PowerShell 7 legacy OS compatibility, Everything auto-service, Secs4Net modern .NET runtime, GlazeWM MSI portability, com0com driver, NSSM service and Sysinternals redistribution each require explicit policy check.
- **P2 optional domain profiles**: industrial-secs-gem, industrial-plc-fieldbus, industrial-telemetry, ergonomics, legacy-cli (cross-domain, no installable memberships unless independently pinned and tested). Production ports/real PLC scans or raw socket listeners forbidden by default. Apply the report via candidate metadata and reviewed branches, never a wholesale taxonomy migration.


## R2 reconciliation (2026-10-23; review before changing latest main)

- **Focused remediation (PR validation required):** baseline ZIP extractor lacked expanded-size and member-count guards. The [R2 code/audit change](review/2026-10-23_RECURSIVE_MECE_AUDIT.md) adds bounded ZIP preflight, streamed member-length checks and rollback regressions. Consider DONE only once Windows PR CI passes, change is merged, and main CI rechecked.
- **Open human/licensing gates:** Everything / grepWin / full 7-Zip GUI remain `HUMAN_NOT_VERIFIED`; four Office semantic comparisons `NOT_VERIFIED`; TCPView/PsPing `RESEARCH_ONLY` pending vendor redistribution/internal transfer determination. Do not upgrade to PASS or add binaries because CI is green.
- **Next optional robustness:** consider an opt-in console-to-file evidence mode for the single-tool core CLI; toolset apply and GUI/Office harnesses already write local evidence. Confirm exact stdout/stderr semantics and sensitive-data handling before generalizing.
- **Usability:** explicit standalone `7zip` requires previously managed `7zr`; document prerequisite rather than silently installing it. Historical candidate lines below are intentionally not current installation status.

> **Active handoff as of 2026-10-22:** [Verified cross-chat status and ordered P0–P2 gaps](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md) · [new chat prompt](handoff/START_NEW_CHAT_PORTAKIT_20261022.md). The chronological sections below intentionally preserve older planning assumptions, some superseded by PRs #14–#18. Do not treat a past "candidate" or "not implemented" entry as current without checking main.

The [corporate/offline 30-software survey](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md) identifies **research-only** candidates and per-vendor redistribution gates. Do not silently add them to installable catalog or republish proprietary vendor binaries.


The items below are **not implemented/certified** merely by their appearance in this document. Keep explicit consent for side effects, and maintain minimal vendor defaults where a configuration change offers no verified benefit.

| Priority | Area | Task | Gate / next action | State |
| --- | --- | --- | --- | --- |
| P1 | WinMerge Office 4 | Execute **real** Excel, Word, PowerPoint and Visio document comparisons on a licensed, interactive Windows PC; inspect Explorer/WinMerge GUI plugin selection, SaveAs variants and evidence ZIP results; review `--require-pass` on the resulting archive | All four real Office app comparisons and human GUI check. No false PASS from absent COM | **BLOCKED — licensed Office desktop / actual evidence not provided** |
| P2 | WinMerge Explorer integration | Advanced two-selection Compare / Compare To via vendor WinMerge shell extension, including Windows 11 native menu. Current lightweight classic menu only opens a selected file/folder and WinMerge can prompt for the other target | Upstream shell-extension compatibility/security testing and reversible installer, admin/COM approval if needed | Backlog (optional, do not default) |
| P2 | Notepad++ Explorer integration | Windows 11 **modern** primary context menu, as opposed to the classic per-user registry action shipped by PortaKit | Verify NppShell signed COM/sparse package deployment and admin permissions; no registry hijacks | Backlog (optional) |
| P2 | Shell-menu lifecycle | Detect/report stale registered shell links when a managed application is moved/removed. Do not silently remove global/user shell keys during a regular PortaKit remove command | Cross-command UX tests and consent contract | Backlog |
| P3 | Catalog pins | Periodically review new upstream versions of Notepad++, WinMerge and jq, plugin compatibility and verified hashes. Don't silently use 'latest' or change an approved pin | Explicit reviewed pin update PR with SHA evidence and Windows live tests | Backlog |
| P3 | Performance | Optional offline cache, bundle portability, and CLI JSON status for diagnostics if justified by user demand | Add only with tests / no behavioral regression | Deferred |

## Release scope and evidence boundary

- Existing WinMerge Office vendor plugin file checks, automatic plugin settings, real plain text comparison, prereq-only COM tests and ZIP SHA evidence have passed on hosted Windows CI. That **does not mean Excel/Word/PowerPoint/Visio GUI comparisons passed**.
- Do not publish a GitHub Release claiming Office compatibility until the P1 gate is satisfied.
- The classic Explorer menus are an **explicit current-user opt-in**; the two-argument vendor ShellExtension behavior is intentionally not represented as implemented.

## Category toolset roadmap (P2, optional)

- **Common**: evaluate 7-Zip and Everything stable portable ZIP; pin exact official assets, SHA, verify extraction, license and indexing/privilege behavior before adding to `catalog.json`.
- **OS**: Process Explorer, Process Monitor, Autoruns candidates; avoid full Sysinternals Suite until >100 MiB download cap and bundle policy reviewed.
- **NW**: prioritize TCPView and PsPing, then evaluate protocols/packet-capture viewers. Test non-elevated operation and explicit optional elevation where required; no automatic packet capture or network probing. Wireshark live capture requires Npcap (driver) and is **not** a pure portable/no-side-effect default.
- **Dev/Data/Diagnostics**: reuse existing verified Notepad++ / WinMerge / jq until new tool delivers a clear benefit. Ripgrep and format analyzers are optional candidates, not promised installations.
- **Governance**: add one candidate at a time, with official provenance, immutable version and SHA, EULA/licensing, safety classification, CI acceptance, and optional membership of any number of categories. Never treat a plan selection as consent for new drivers/services/system-wide changes.

Details and official reference links: [TOOLSETS](TOOLSETS.md).

## MECE small-first candidate admission (2026-10-20)

- [107 unique screened research entries](../research/TOOLS_CANDIDATES_20261020.json) are categorized once by primary purpose. **11 are SHA-pinned**, **27 are existing/optional Windows built-ins**, **69 are research-only**. The candidate register is not an install authorization and does not certify all free-use or redistribution claims.
- **Accepted small-first pins for live CI:** ripgrep, fd, fzf, bat, sd, yq, delta and hyperfine; release metadata SHA-256 + compressed sizes are recorded in the immutable `catalog.json` and `TOOLSETS.md`. Gate: real Windows download/hash/extract/`--version` smoke and reapply no-op. No auto-update.
- **Next P0 research admission:** 7-Zip, Everything portable, compact log viewers (klogg/grepWin), dasel/Miller/SQLite tools; compare incremental practical value against built-ins and already pinned tools.
- **Network/OS conditional:** Microsoft Sysinternals licensing permits company use but restricts redistribution; no unrestricted vendor binary bundling. Prioritize metadata-only sourcing, IT approval, safe non-privileged observation. Wireshark Npcap and live network/packet testing are elevated/change-impact opt-ins.
- **Footprint honesty:** unknown compressed sizes are `null`, not treated as small; exact official bytes only for 8 newly pinned assets. Capture installed disk footprint (all DLL/doc files), prerequisites, first-launch writes, network activity, built-in alternatives, license notice, runtime compatibility and rollback before future admission.
- **Legacy names:** keep `common/os/nw/dev/data/diag` as backward compatible frozen selectors, not primary categories. `minimal/mes-support/developer` preserved as profile names. Future releases should use `files/text/structured-data/system/network/security/development/automation/documents/transfer`.

- **P1 sd upstream version anomaly:** Official v1.1.0 Windows ZIP at pinned SHA executes but `sd --version` prints 1.0.0 on Windows CI. Record explicit warning/exception (no hidden PASS as same version), compare vendor build metadata/source, open upstream issue if necessary and reassess pin/functional testing before future release claims. **2026-10-30 status:** still OPEN; upstream asset digest and tag `Cargo.toml` not yet re-verified (see [TOOLSETS](TOOLSETS.md#upstream-sd-embedded-version-discrepancy-not-hidden)).
- **P2 small-footprint research candidates (2026-10-30, no install, no vendor binaries):** recommend at most three for future admission, each needing exact official asset URL, SHA-256, compressed size, license notice, and a Windows download/hash/`--version` smoke before any catalog entry: (1) `b3sum` (CC0/Apache-2.0, `security`, fills the empty security domain for offline hashing; `certutil` remains the built-in fallback); (2) `sqlite-cli` (Public Domain, `structured-data`, local SQL/CSV export for log analysis); (3) `dust` (Apache-2.0, `files`, disk-usage tree). Rejected for now: `csvtk` (overlaps Miller), `just` / `taskfile` (overlap PowerShell/cmd), and `pandoc` / `imagemagick` (large, outside the small-footprint goal). All research sizes remain `NOT_MEASURED`.

## Closed-network second-wave outstanding items — 2026-10-21

- **Full 7-Zip GUI user-workstation acceptance** (P1): the **complete official 7-Zip 26.04 is now pinned** and uses validated SFX-as-DATA extraction via the trusted managed 7zr, never launches installer. Remaining: manual 7zFM GUI Add/Extract/Open, Unicode paths, HKCU context-menu *opt-in only*, no unintended default file associations or registry writes.
- **Everything service/index and privacy** (P1): officially permissive desktop software, portable ZIP installed without registry; actual first launch may offer NTFS service, indexing via admin, update checks, HTTP/ETP configuration, index-file user permissions. Never auto-launch in CI. Validate on non-production client with *service disabled + folder-only indexing* profile and document performance/privilege trade-off; no default service or full drive index on MES servers.
- **grepWin** (P1): real Windows Explorer GUI search and replace *read-only search first*, case/encoding/large log and portable settings write footprint. Add optional shell integration only after owned-HKCU collision-safe test (not default).
- **Miller / dasel** (P1): fixture-based real transformations and log encoding tests, check NUL/malformed CSV/YAML/JSON and no in-place source modifications. 
- **Offline vendor intake** (P1): review manifest-driven export with exact official URLs, local SHA, file size, signature, EDR/OSS approval evidence. Validate source archives without network on disconnected worker; currently user must obtain original vendor files on an approved connected machine. Offline recommended Notepad++ plugin installer is not implemented; reject instead of network fallback.
- **License review** (P1): original vendor binaries are downloaded by the user from official sources; source-only Git repo contains no vendor binaries. Everything desktop license includes notice conditions. Run internal corporate OSS/EULA/security approval before deployment; no automatic release.
- **Prior unchanged:** actual Office4 Word/Excel/PowerPoint/Visio COM GUI comparisons on licensed Windows, advanced WinMerge two-item native ShellExtension, and `sd` pinned v1.1.0 archive containing executable self-report v1.0.0 remain blocked/backlog.

## Next cross-component verification

- Validate real full 7-Zip SFX extraction under an approved offline workstation (not only hosted CI). Verify `7zFM.exe` opens without admin, actually adds/extracts ZIP/7z, configuration stays local, Win11 classic right-click remains unchanged until separate optional HKCU integration approved.
- Everything desktop: first-run folder-only indexing without service/UAC as **option**, metadata/file path privacy and manual UI. Do not autoenable NTFS service.
- grepWin portable: read-only regex search against UTF-8/UTF-16 and log-volume fixture, verify application UI and replace operation opt-in, no shell association by default.

## Current gate: GUI evidence and TCPView/PsPing corporate intake (2026-10-21)

- **Everything GUI — HUMAN_NOT_VERIFIED:** New `scripts/gui_acceptance.py` and `GuiAcceptance.cmd` provide read-only-by-default pin/executable SHA probe and **separate explicit** GUI/first-run consent. Test only a synthetic local folder, never launch under CI or on MES servers; no automatic service, whole-NTFS indexing, HTTP/ETP or elevation. A actual human-reviewed `result.json` + screenshot (if permitted) is still required for release.
- **grepWin GUI — HUMAN_NOT_VERIFIED:** Guided synthetic UTF-8/UTF-16 search and deliberately disabled production replace; no GUI auto-launch in CI. Earlier binary existence checks are not manual GUI success.
- **Full 7-Zip GUI — HUMAN_NOT_VERIFIED:** Native `7z.exe` ZIP create/test CI passed, but interactive `7zFM.exe` add/extract and no-registry-association confirmation is still a human gate.
- **TCPView + PsPing — LICENSE/REDISTRIBUTION_GATE:** Official [Microsoft FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq) explicitly declines third-party distribution and [license terms](https://learn.microsoft.com/en-us/sysinternals/license-terms) prohibit publishing to others. [Metadata review](../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json) documents current upstream versions, download page links, risk, company legal approval/EDR gates; no executables or download URLs added to installable catalog.
- **Next non-production validation:** run manual GUI acceptance on locally approved PC; perform TCPView read-only endpoint/CSV smoke with name resolution disabled; explicit network owner approval for PsPing target/rate and avoid suite-wide privileged tools. Keep release gated.
