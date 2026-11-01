# PortaKit — 2026-11-01 verified handoff and new-chat start

> **Public-safe source-of-truth checkpoint.** A newer GitHub `main` HEAD/CI/PR always supersedes the listed snapshot. No company network addresses, credentials, privately collected vendor files, legal attestations, host inventory or customer data are contained here.

## 0c. Latest verified GUI/Doctor consistency checkpoint — PR #91 (supersedes PR #89 source)

- Source-only `main` squash SHA: `acbd6e97838347130ebf798bebec95a563c153b8`, [PR #91](https://github.com/greatgc-flow/portakit/pull/91) merged. Exact [PR-head Windows CI #41263772358](https://github.com/greatgc-flow/portakit/actions/runs/41263772358) **723/723 PASS each** on Python 3.11/3.14, two job logs checked. Independent [source-main CI #41263859072](https://github.com/greatgc-flow/portakit/actions/runs/41263859072) **723/723 PASS each**, both job logs checked.
- Pure `kit_footprint.confirm_readiness_alignment` checks matching read-only diagnostic roots, ordered pinned IDs and per-tool install statuses. Invoked by `PickerModel.inspect_readiness`, direct GUI `overview_lines`, `KitDoctor.inspect`. This rejects contradictory snapshots without GUI/CLI installation, core catalog or kit-schema changes; genuine empty pinned selections remain valid.
- **Compatibility regression handled:** early candidate [CI #41263655133](https://github.com/greatgc-flow/portakit/actions/runs/41263655133) failed an existing GUI missing-row error-contract test; the old error was restored and final CI rerun before merge. New negative tests address null/malformed/empty inputs, stale status, different root/ID, no selection mutation or output writes. The test count increased from 718 to 723 per version.
- [Scoped review](../review/2026-11-01_TARGETED_REFACTOR.md) and [Issue #87](https://github.com/greatgc-flow/portakit/issues/87) hold remaining optional proposals. Never claim atomic point-in-time filesystem snapshots or real user-site GUI, vendor, company EULA/EDR/OSS approvals based solely on CI; final user owns those. A later documentation-only `main` SHA must pass independent CI.

## 0b. Latest source and evidence-safety checkpoint — PR #89 (supersedes PR #86 source)

- Source-only `main` squash HEAD: `b7e0cee2ee35f181c93558f3b759b82f2aea59c2`; [PR #89](https://github.com/greatgc-flow/portakit/pull/89) merged. Exact [PR-head Windows CI #41262818996](https://github.com/greatgc-flow/portakit/actions/runs/41262818996) **718/718 PASS each** on Python 3.11/3.14 (logs checked). Independent [merged-main Windows CI #41262904434](https://github.com/greatgc-flow/portakit/actions/runs/41262904434) **718/718 PASS each**, both job logs inspected. No archive smoke for this report-only source change (not triggered).
- Proven defect: `offline_ready`, `kit_footprint` and `kit_doctor` could remove foreign JSON path on exclusive-open race or retain partial paired reports on subsequent log failure. Existing `plugin_health` used identity-guarded cleanup. All four now use focused `scripts/report_evidence.py` for *new-only JSON + verbatim console/.log* and owner-identifiable best-effort rollback. Command-specific schema/outputs/errors/consent and zero-write no-out modes unchanged.
- New synthetic `tests/test_report_evidence.py` covers four callers, disk/log failures, foreign collisions, path replacement, symlink guard and exact transcript mirroring. Changes recorded in [scoped review](../review/2026-11-01_TARGETED_REFACTOR.md), with progress comment in [Issue #87](https://github.com/greatgc-flow/portakit/issues/87). Remaining issue #87 candidates are optional and require evidence of actual benefit. No new generic abstraction.
- **Limits:** not an atomic multi-file commit or proof against process crash or adversarial concurrent writes. Windows CI cannot certify live vendor binaries, end-user GUI behavior, corporate EULA/EDR or operational deployment; these remain with the final user. A later docs-only `main` SHA must be verified independently.

## 0a. Latest targeted-refactor source checkpoint — PR #86 (supersedes PR #84 code)

- Functional-source `main` squash HEAD: `1888db2dc2c98fb00a57a7e22555e0217aee0962`; [PR #86](https://github.com/greatgc-flow/portakit/pull/86) merged. Exact [PR-head CI #41261968622](https://github.com/greatgc-flow/portakit/actions/runs/41261968622): **710/710 PASS** on Windows Python 3.11 and 3.14, each job log examined. [Windows archive smoke #41261968600](https://github.com/greatgc-flow/portakit/actions/runs/41261968600): **SUCCESS**. Independent [merged-main CI #41262060770](https://github.com/greatgc-flow/portakit/actions/runs/41262060770): **710/710 PASS** each, both job logs examined.
- Refactored existing `scripts/toolsets.py apply` into the minimal named seams `run_core_child`, `parse_core_install_result`, `verify_managed_install`; kept commands, console/evidence, pins and failure semantics unchanged. Added two synthetic no-vendor test methods, not new installation features.
- [Scoped recursive-MECE review](../review/2026-11-01_TARGETED_REFACTOR.md) and [follow-up Issue #87](https://github.com/greatgc-flow/portakit/issues/87) distinguish verified refactor from optional future candidates. No general-purpose framework or rewriting of unrelated modules.
- A documentation-only closeout merge has a **different `main` SHA and new CI**; verify independently. No vendor binaries, live equipment network tests or enterprise runtime/EULA/OSS/EDR approval were performed. Final user owns operational acceptance. Existing Issues #25/#27/#36/#51 remain independently tracked.

## 0. Later verified engineering checkpoint — PR #84 (supersedes older source SHA below)

- Functional-source `main` squash HEAD: `01c7559b31cb1d9dd88fe83e0b2e43a4826cb060`; [PR #84](https://github.com/greatgc-flow/portakit/pull/84) merged. **Windows Python 3.11 and 3.14: 708/708 PASS each**, independently verified from the [merged-main run #41260317503](https://github.com/greatgc-flow/portakit/actions/runs/41260317503) job logs. [PR-head run #41260210938](https://github.com/greatgc-flow/portakit/actions/runs/41260210938) also returned **708/708 PASS** per version; [archive smoke #41260210900](https://github.com/greatgc-flow/portakit/actions/runs/41260210900) **SUCCESS**.
- Engineering change: `scripts/toolsets.py apply` rejects changed tool IDs, order, version or SHA pins between initial planning and the locked replan, **before child launch and evidence creation**. Matching installed-status-only changes are safely skipped. Two new test methods cover three manifest-drift variants and status-only drift.
- The PR #84 source checkpoint supersedes historical PR #82 706-test code and PR #83 docs-only SHA below. This handoff refresh, once merged, has its **own different main SHA and independent CI**; always check current GitHub.
- No third-party binaries, live industrial connections, services, registry edits, automatic release or enterprise approval claims. Final-user acceptance ownership and open Issues #25/#27/#36/#51 remain unchanged.

## 1. Verified remote state at handoff

- Repository: https://github.com/greatgc-flow/portakit
- Latest independently verified **functional-source `main` before this docs-only refresh**: `a4ef03a5569ed289187e9bfce2c08b7645e30b74`. A docs-only PR merged after that SHA creates a newer `main` and must pass its own independent CI.
- Latest source [merged-main Windows CI #41225137743](https://github.com/greatgc-flow/portakit/actions/runs/41225137743): **SUCCESS**, **706/706 PASS** on **Python 3.11 and 3.14**; each job log independently checked. PR #82 head [CI #41224955787](https://github.com/greatgc-flow/portakit/actions/runs/41224955787) was **706/706 PASS** per version; archive smoke [#41224955832](https://github.com/greatgc-flow/portakit/actions/runs/41224955832) **SUCCESS**.
- Historical [PR #73](https://github.com/greatgc-flow/portakit/pull/73) research docs head `7425e5b04d12994f053302d965b0b981a8c0d2a9`, [PR CI #41218083490](https://github.com/greatgc-flow/portakit/actions/runs/41218083490) **686/686 each**; squash merged. See newer tested PRs below.
- **Open PRs: zero** at last check. Open Issues: [#25](https://github.com/greatgc-flow/portakit/issues/25), [#27](https://github.com/greatgc-flow/portakit/issues/27), [#36](https://github.com/greatgc-flow/portakit/issues/36), [#51](https://github.com/greatgc-flow/portakit/issues/51).
- Public repository rulesets `[]`, `main.protected=false` as last verified; **no branch protection change** was made. Issue #51 contains an optional minimal policy proposal only.

### Recent merged PR timeline (source CI and actual main CI checked)

| PR | Main squash commit | Purpose | Windows tests per Python version |
| --- | --- | --- | --- |
| [#67](https://github.com/greatgc-flow/portakit/pull/67) | `6cd5ae06f02d291e9a916043f401e2dfd05899d7` | Strict CSV evidence-v1 schema, empty-stream hashes | 634 |
| [#68](https://github.com/greatgc-flow/portakit/pull/68) | `853ffe86f735ab30ac4afc7531f7603c55ba7fa3` | Invocation-owned JSON/log failure cleanup for ZIP and CSV evidence | 643 |
| [#69](https://github.com/greatgc-flow/portakit/pull/69) | `fe2d9dddc08f8931433bc038a5cb30a306153c18` | Editor-plugin receipt duplicate key/health evidence hardening | 653 |
| [#70](https://github.com/greatgc-flow/portakit/pull/70) | `1647fe182c461b8370c1d01edec20ab3bf6a054b` | Final-user approval ownership + personal kit JSON safe writes | 662 |
| [#71](https://github.com/greatgc-flow/portakit/pull/71) | `b35f20d52131c367eddbd5e78dcf5f91fed71c68` | One strict JSON parser shared across catalog, state, toolsets, kits | 671 |
| [#72](https://github.com/greatgc-flow/portakit/pull/72) | `93474402bad5456d0bb9cf5f42cb3f76775e7776` | Toolset core installer per-child timeout, live stdout/stderr caps, strict success | 686 |
| [#73](https://github.com/greatgc-flow/portakit/pull/73) | `769860bf9042ff1c0e09fbf0febf7701b9507e2a` | Research-only industrial CLIENT/SERVER/SIMULATOR role matrix | 686 |
| [#76](https://github.com/greatgc-flow/portakit/pull/76) | `02ea77df0212b38468cbb423177ad34786027acf` | Verify managed receipt and dest after successful toolset child | 689 |
| [#77](https://github.com/greatgc-flow/portakit/pull/77) | `a84a07aa407ab31a43e8cc66178ebd6ffbcd6a5c` | Explorer stale-menu read-only classification | 691 |
| [#78](https://github.com/greatgc-flow/portakit/pull/78) | `d4d8530a0f18a64a8923dc0e9550eae0c88b4e46` | Optional exclusive-create single-tool stdout/stderr evidence | 696 |
| [#79](https://github.com/greatgc-flow/portakit/pull/79) | `f5682a0cddc96c42c1b7f34600076d546363015c` | Share strict core catalog/state receipt checks for Explorer menu | 698 |
| [#80](https://github.com/greatgc-flow/portakit/pull/80) | `d00edf9692fdee49b42504e68ad833a9ec4f8316` | Protect core CLI evidence from tool/backup/tmp deletion paths | 702 |
| [#81](https://github.com/greatgc-flow/portakit/pull/81) | `3ffedd710354cce955c8ffc35d087a3648c52a72` | Share core safe evidence path rule in batch toolset apply | 704 |
| [#82](https://github.com/greatgc-flow/portakit/pull/82) | `a4ef03a5569ed289187e9bfce2c08b7645e30b74` | Empty managed folders blocked in plan, postcheck, offline readiness | 706 |

The PR #76–#82 history above contains independently verified **PR-head and merged-main** Windows CI for each source checkpoint; successful exact links are recorded in each PR conversation. Earlier red CI runs during test-fixture alignment were corrected **before** merges, and their root causes are documented in PR comments. A new docs-only closeout has a **different SHA and CI**; inspect them independently rather than claiming this checkpoint covers future commits.

## 2. Governing invariants and product scope

- Philosophy: **Very Simple**, unit-testable independent functions, minimal effort/tokens for humans and AI, recursively MECE responsibilities, optional composition, explicit error handling, local exact console-evidence logs.
- Canonical personal software options (last source inspection): **151 software entries = 19 SHA-pinned install-capable + 27 OS built-ins + 105 RESEARCH_ONLY**, plus **six independent editor-plugin choices** (two existing SHA-pinned metadata/opt-in offline deployment candidates, four research-only). Verify latest source before repeating counts.
- Older legacy snapshots of 17 pins, 53 report families, or 108 research items are **historical**, not current catalog authority.
- `catalog.json`, research ledgers, `toolsets.json` and the source code are the authority; import/runtime metadata is never implicit company approval or source provenance.
- Separate [final-user acceptance responsibilities](../END_USER_ACCEPTANCE.md): the **final user/organization** owns actual workstations, GUI/IME/DPI, source authenticity, vendor licenses, company use, redistribution/transfer, EDR/OSS policy, runtime compatibility, performance and local deployment/release go/no-go. **Do not block unrelated source-only work or safe PR merges** on missing human acceptance. But **do not promote unknown vendors**, enable services/drivers or silently install and call them approved.
- No industrial default listeners, active equipment probes, PLC/OPC writes, production logs, elevated registry/system changes or binary bundle redistribution. If a lab server is ever implemented, default to source-only strict frame parsing; live binding must be separately configured/approved by the final user.
- `xan`, `DuckDB` and unpinned industrial protocol candidates remain **RESEARCH_ONLY**. A green synthetic test or local SHA match is not authority to admit them.
- Python project runtime uses **Windows Python 3.11+**, verified GitHub Actions matrix 3.11/3.14. Legacy enterprise Java JDK 8, Visual Studio 2015/.NET Framework, and PowerShell 2.0/5.x are **compatibility constraints for *separate* tools**, not evidence the current Python scripts run natively on those runtimes.

## 3. Documents to read (latest main first)

1. `README.md` — current entrypoint and source CI.
2. `docs/END_USER_ACCEPTANCE.md` — final-user versus developer gate and enterprise responsibility.
3. `docs/BACKLOG.md` — implemented history and source-level priorities.
4. `docs/PERSONAL_KITS.md`, `docs/PLUGIN_OFFLINE_APPLY.md` — v1/v2 selected kits, safe plugin workflows.
5. `docs/TOOLSETS.md` — optional MECE profiles and [PR #72](https://github.com/greatgc-flow/portakit/pull/72) bounded core installer: default 600s per tool, optional 1..3600, 256 KiB per stdout/stderr, process-only kill; **not** an OS sandbox.
6. `research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md` — [PR #73](https://github.com/greatgc-flow/portakit/pull/73) eight public-source-evidenced candidates; never mistake `pymcprotocol`, `PyXGT` or `QModMaster` clients for server-side virtual PLCs.
7. `docs/GUI_PICKER_ACCEPTANCE_20261030.md`, `docs/CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md` — final-user optional lab checklists, **not green CI proof**.
8. `https://github.com/greatgc-flow/VerySimpleGuide` — general architecture/design/testing preference reference.

## 4. Remaining work, kept MECE

- **Engineering / source-only:** continue targeted feature gaps and negative tests with discrete branch/PR, not repeated speculative hardening. Core and batch opt-in evidence paths are now preflight protected, and an **empty** managed directory is blocked rather than falsely marked installed. A **nonempty** directory alone does not prove contents, signature, compatibility or vendor functionality; any stronger verification must remain source-only, optional and precisely scoped. High-value next options: bounded real CPU/memory-independent child coordination, optional interface/unit tests, or one protocol-specific parser/TDD issue chosen with clear device SERVER role. The industrial matrix classifies only; it does **not** create a simulator.
- **Issue #25:** technical vendor capability/future individual admission. The eight-role **source matrix is done**; actual installed compatibility/legal/company acceptance is final-user-owned. Avoid converting the research issue into an automatic vendor promotion.
- **Issues #27 and #36:** selectable GUI and independent editor plugins are substantially implemented and synthetic-tested; live desktop/real DLL permission are final-user-owned. Do not replace the GUI with a new framework or reimplement existing features.
- **Issue #51:** optional minimal main-branch governance is **NOT implemented**; no ruleset change without explicit separate user approval. Existing single-maintainer fast PR/squash workflow must remain usable.
- **Real operations:** final user alone validates actual company EULA/EDR, transferred originals, legal and GUI acceptance, performance and production safety. Never claim they occurred because a synthetic GitHub job passed.

## 5. New-chat continuation prompt (copy everything below into a new chat)

> **PortaKit — full handoff restoration and source development continuation**  
> My GitHub repository is `https://github.com/greatgc-flow/portakit`. Start from the **actual latest** remote `main` HEAD, open PRs, Issues #25/#27/#36/#51 and Actions, rather than trusting historical SHA. The latest verified functional-source checkpoint before this documentation refresh was `a4ef03a5569ed289187e9bfce2c08b7645e30b74`, with merged-main Windows CI #41225137743 **706/706 PASS** on Python 3.11/3.14. A newer docs-only commit requires its own exact-head/main CI verification. Read `docs/handoff/START_NEW_CHAT_PORTAKIT_20261101.md` and its listed current documents before work; confirm any newer docs-only closeout commit and CI.  
> **You may create branches/Issues/PRs, commit, and squash-merge to main after exact-head Windows Python 3.11+3.14 full green CI; independently verify post-merge main CI.** This explicitly supersedes the older do-not-merge instruction.  
> **Real operator tests and all enterprise company-use, EULA, OSS/EDR, file transfer/redistribution, runtime compatibility, real GUI and deployment approvals are the final user's/organization's responsibility**, not a blocker to unrelated developer source work. Do not fabricate/claim such approval, run industrial protocols on production networks, install drivers/services, redistribute unapproved binaries or promote RESEARCH_ONLY tools.  
> Prioritize **Very Simple**, optional independent modules, null/empty/duplicate/error cases, no unsafe defaults, exact console-to-local evidence logs, MECE classification, a short regression-driven PR, and updated public-safe docs/Issues. Avoid speculative redundant implementation. The latest industrial role matrix is under `research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md`; `pymcprotocol` and `PyXGT` are client-focused, not drop-in virtual PLC servers. Continue actual engineering and report tested commit/CI facts, not progress promises. If a conversation becomes genuinely too long, commit/update GitHub handoff context and provide one new-chat prompt.

**No local user repository was cloned or modified during this handoff.** All current work was carried out with GitHub APIs on source/docs, and third-party vendor archives were never acquired or executed by the assistant.
