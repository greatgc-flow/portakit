# PortaKit — final-user acceptance and enterprise permission boundary

**Policy effective 2026-11-01 · Source-level CI is separate from local deployment authorization**

PortaKit is a **selection and optional offline-tooling framework**, not a license auditor, compliance service, antivirus, desktop testing laboratory or industrial-network approval authority. The **final user or their organization's designated approver** owns real-workstation acceptance and every site-specific enterprise permission decision. PortaKit contributors own source design, bounded static/fixture checks, regression testing, reproducibility, documentation and correct safety behavior. **Neither side's evidence substitutes for the other.**

## Very Simple division of responsibilities

| Responsibility | PortaKit development / GitHub CI | Final user / organization |
| --- | --- | --- |
| Code correctness and regression tests | **Owns** implementation, source-only Windows Python 3.11/3.14 CI, synthetic positive/negative fixtures | May independently inspect |
| Tool and plugin selection / SHA locks | Owns metadata format, pin drift detection and explicit opt-in behavior | Chooses tools/plugins and supplies permissioned original assets |
| Actual vendor binary provenance / malware policy | Provides offline hash/structure utilities; **cannot attest independent authenticity** | Independently validates source, original archive, anti-malware/EDR controls and trust |
| Company-use license, OSS notices, redistribution/air-gap transfer | Clearly documents constraints and does not claim a grant | Secures and documents enterprise approval **under its own policy** |
| Real GUI, Unicode/IME, DPI, host compatibility and measured footprint/performance | Supplies human checklists, read-only diagnostics and synthetic CI tests | Performs and records tests on an **authorized nonproduction workstation** |
| Production network listeners, PLC/OPC writes, drivers, services | Keeps them disabled/excluded by default; no blanket permission from a green CI | Separately authorizes any such action; follow local safety/change controls |
| Deployment/release acceptance | Can publish only source-level/test status and release notes within authorized workflow | Makes local deployment and operational go/no-go decision |

## Interpretation of status (never combine these as a single green light)

- **PINNED_CATALOG / READY** = source/catalog metadata was admitted to the project's technical selection mechanism; **NOT** corporate authorization, vendor publisher verification or safe use on an arbitrary PC.
- **RESEARCH_ONLY** = notes / candidate only. Not installed, automatically promoted, downloaded or executed by normal approved-tool workflow; future admission requires explicit repository review and stable immutable pins.
- **SHA256 PASS / LOCAL_HASH_PASS** = observed local bytes matched specified hashes. It does not prove license rights, publisher identity, EDR clearance, interactive behavior or binary safety.
- **GitHub Actions PASS** = synthetic automated test suite passed in a known runner environment. It does not prove real customer/enterprise acceptance.
- **End-user acceptance** = a separate locally recorded decision, which **must never be inferred automatically** from any source-only result.

## Final-user checklist (local only, optional until that user intends to deploy)

1. Confirm use is permitted for the intended company, device, jurisdiction and distribution channel. Treat enterprise *use*, *redistribution*, and *offline transfer* as separate permissions; follow EDR/OSS security policy.
2. Independently fetch/verifiably source the exact approved vendor release (when needed); confirm architecture, version, SHA, OS/dependencies, licenses/notices, and network/proxy restrictions.
3. In a controlled nonproduction Windows workstation, run PortaKit's read-only `plan` / `verify` / `doctor` and applicable manual GUI/plugin/operator checklists **before** any explicit install. Use non-sensitive synthetic data and no live MES/PLC connections.
4. Capture test results and approvals in **organization-controlled local/private evidence**; do not publish binaries, internal paths, organization credentials, host fingerprints or private logs to this public GitHub repository.
5. Perform any install/apply **only after** final-user decision and explicit current command flags (`--yes`, `--policy-approved` where applicable); keep the existing no-overwrite, SHA-pin and rollback protections. On failure or uncertainty, stop and retain logs for local triage.
6. Maintain a local change/rollback plan and review any renewed version, SHA, host, license or security-policy change independently. A previous approval must not silently carry over to new binaries.

## Developer workflow and open issues

**Do not block ordinary source-level feature development, CI, PR review or safe code merge while a separate final user has not performed their site acceptance.** Keep the test reality boundary explicit in README/issues/release notes. A source-only change can be complete even when real GUI, vendor-runtime, enterprise policy and production acceptance are not known.

The developer can close a **code-complete** issue with a clear final-user handoff if its remaining criteria are solely site-specific. If an issue also contains unresolved **source-level work**, track that work independently; do not falsely claim its completion. In particular, industrial candidate **catalog promotion** or third-party binary redistribution still requires an approved, auditable decision—not merely a developer guessing what a user would approve.

- [Personal toolkit operator workflow](PERSONAL_KITS.md)
- [GUI manual acceptance](GUI_PICKER_ACCEPTANCE_20261030.md)
- [Editor plugin offline apply](PLUGIN_OFFLINE_APPLY.md)
- [CSV / xan operator reality gates](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md)
- [Technical and research backlog](BACKLOG.md)

**No credentials, signatures, organizational approvals, operator attestations, real vendor binaries or production equipment were gathered or implied by this policy.**
