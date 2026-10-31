# PortaKit — 2026-11-01 verified handoff and new-chat start

> **Public-safe source-of-truth checkpoint.** A newer GitHub `main` HEAD/CI/PR always supersedes the listed snapshot. No company network addresses, credentials, privately collected vendor files, legal attestations, host inventory or customer data are contained here.

## 1. Verified remote state at handoff

- Repository: https://github.com/greatgc-flow/portakit
- Latest independently verified **main**: `769860bf9042ff1c0e09fbf0febf7701b9507e2a`
- Latest [merged-main Windows CI #41218229391](https://github.com/greatgc-flow/portakit/actions/runs/41218229391): **SUCCESS**, **686/686 PASS** on **Python 3.11 and 3.14**; independent job logs checked.
- Latest [PR #73](https://github.com/greatgc-flow/portakit/pull/73) docs-only head `7425e5b04d12994f053302d965b0b981a8c0d2a9`, [PR CI #41218083490](https://github.com/greatgc-flow/portakit/actions/runs/41218083490) **SUCCESS 686/686 each**; squash merged.
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

The docs-only handoff closeout (if this file was later squash merged) has its **own, newer** HEAD and GitHub Actions run: confirm them independently; this checkpoint is not evidence of future CI.

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

- **Engineering / source-only:** continue targeted feature gaps and negative tests with discrete branch/PR, not repeated speculative hardening. High-value options: safe new metadata-only research, bounded real CPU/memory-independent child coordination, optional interface/unit tests, or one protocol-specific parser/TDD issue chosen with clear device SERVER role. The industrial matrix classifies only; it does **not** create a simulator.
- **Issue #25:** technical vendor capability/future individual admission. The eight-role **source matrix is done**; actual installed compatibility/legal/company acceptance is final-user-owned. Avoid converting the research issue into an automatic vendor promotion.
- **Issues #27 and #36:** selectable GUI and independent editor plugins are substantially implemented and synthetic-tested; live desktop/real DLL permission are final-user-owned. Do not replace the GUI with a new framework or reimplement existing features.
- **Issue #51:** optional minimal main-branch governance is **NOT implemented**; no ruleset change without explicit separate user approval. Existing single-maintainer fast PR/squash workflow must remain usable.
- **Real operations:** final user alone validates actual company EULA/EDR, transferred originals, legal and GUI acceptance, performance and production safety. Never claim they occurred because a synthetic GitHub job passed.

## 5. New-chat continuation prompt (copy everything below into a new chat)

> **PortaKit — full handoff restoration and source development continuation**  
> My GitHub repository is `https://github.com/greatgc-flow/portakit`. Start from the **actual latest** remote `main` HEAD, open PRs, Issues #25/#27/#36/#51 and Actions, rather than trusting historical SHA. The last source-complete checkpoint before docs closeout was `769860bf9042ff1c0e09fbf0febf7701b9507e2a`, with merged-main Windows CI #41218229391 **686/686 PASS** on Python 3.11/3.14. Read `docs/handoff/START_NEW_CHAT_PORTAKIT_20261101.md` and its listed current documents before work; confirm any newer docs-only closeout commit and CI.  
> **You may create branches/Issues/PRs, commit, and squash-merge to main after exact-head Windows Python 3.11+3.14 full green CI; independently verify post-merge main CI.** This explicitly supersedes the older do-not-merge instruction.  
> **Real operator tests and all enterprise company-use, EULA, OSS/EDR, file transfer/redistribution, runtime compatibility, real GUI and deployment approvals are the final user's/organization's responsibility**, not a blocker to unrelated developer source work. Do not fabricate/claim such approval, run industrial protocols on production networks, install drivers/services, redistribute unapproved binaries or promote RESEARCH_ONLY tools.  
> Prioritize **Very Simple**, optional independent modules, null/empty/duplicate/error cases, no unsafe defaults, exact console-to-local evidence logs, MECE classification, a short regression-driven PR, and updated public-safe docs/Issues. Avoid speculative redundant implementation. The latest industrial role matrix is under `research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md`; `pymcprotocol` and `PyXGT` are client-focused, not drop-in virtual PLC servers. Continue actual engineering and report tested commit/CI facts, not progress promises. If a conversation becomes genuinely too long, commit/update GitHub handoff context and provide one new-chat prompt.

**No local user repository was cloned or modified during this handoff.** All current work was carried out with GitHub APIs on source/docs, and third-party vendor archives were never acquired or executed by the assistant.
