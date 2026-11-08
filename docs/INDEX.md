# Documentation index (MECE)

Every file under `docs/` and `research/` appears here exactly once, either as an explicit row or inside one directory row (an explicit row wins over its directory row). The test `tests/test_doc_index_mece.py` enforces this and also checks that every relative Markdown link in the repository resolves. Only the **current handoff** row is present-tense; everything dated is history.

| Category | Document | Purpose |
| --- | --- | --- |
| Navigation and status | [README](../README.md) | User reference, current-handoff pointer, commands, exit codes, catalog rules |
| Navigation and status | [INDEX](INDEX.md) | This index |
| Navigation and status | [HISTORY](HISTORY.md) | Dated README checkpoints moved out of README (append-only) |
| Navigation and status | [BACKLOG](BACKLOG.md) | Dated ledger of completed and open work; live Issues are the status authority |
| Navigation and status | [HANDOFF](HANDOFF.md) | Archived 2026-10 open-work notes; historical, not the active handoff |
| Navigation and status | [PORTAKIT_ACTIVE_WORK_20261102](PORTAKIT_ACTIVE_WORK_20261102.md) | Historical 2026-11-02 planning matrix |
| Contract | [SPEC](SPEC.md) | Behavioral contract for the core CLI |
| Contract | [DECISIONS](DECISIONS.md) | Ratified decisions, including 2026-11-08 retrospective ratification of merged post-2026-10-30 features |
| User guides | [TOOLSETS](TOOLSETS.md) | Optional categorized toolsets, profiles, offline apply |
| User guides | [PERSONAL_KITS](PERSONAL_KITS.md) | Personal kit CLI and optional Tk picker |
| User guides | [OFFLINE_ASSETS](OFFLINE_ASSETS.md) | Metadata-only offline asset list/export/verify |
| User guides | [FOOTPRINT_AUDIT](FOOTPRINT_AUDIT.md) | Read-only installed logical-size audit |
| User guides | [KIT_DOCTOR](KIT_DOCTOR.md) | One-command read-only personal-kit check |
| User guides | [INDIVIDUAL_EDITOR_PLUGINS](INDIVIDUAL_EDITOR_PLUGINS.md) | Individually selectable editor plugins (kit v2) |
| User guides | [PLUGIN_OFFLINE_APPLY](PLUGIN_OFFLINE_APPLY.md) | Offline plan/verify/apply of pinned editor plugins |
| User guides | [PLUGIN_HEALTH](PLUGIN_HEALTH.md) | Read-only managed plugin hash health check |
| User guides | [XAN_ZIP_LOCAL_PREFLIGHT](XAN_ZIP_LOCAL_PREFLIGHT.md) | Local original xan ZIP structure/SHA preflight |
| User guides | [DUCKDB_TARGZ_CSV_ALTERNATIVES](DUCKDB_TARGZ_CSV_ALTERNATIVES.md) | DuckDB tar.gz preflight and CSV CLI alternatives |
| User guides | [LIGHTWEIGHT_CANDIDATES](LIGHTWEIGHT_CANDIDATES.md) | Research-only lightweight candidate gate |
| Acceptance and evidence | [END_USER_ACCEPTANCE](END_USER_ACCEPTANCE.md) | Developer vs final-user responsibility boundary |
| Acceptance and evidence | [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md) | Manual release acceptance checklist |
| Acceptance and evidence | [GUI_ACCEPTANCE_20261021](GUI_ACCEPTANCE_20261021.md) | Human GUI acceptance harness for Everything/grepWin/7-Zip |
| Acceptance and evidence | [GUI_PICKER_ACCEPTANCE_20261030](GUI_PICKER_ACCEPTANCE_20261030.md) | Operator checklist for the personal-kit picker GUI |
| Acceptance and evidence | [WINMERGE_OFFICE_ACCEPTANCE](WINMERGE_OFFICE_ACCEPTANCE.md) | WinMerge runtime and Office 4 acceptance |
| Acceptance and evidence | [CSV_XAN_OPERATOR_ACCEPTANCE_20261031](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md) | Operator-local xan/Miller acceptance package |
| CSV research | [CSV_OPERATOR_SMOKE](CSV_OPERATOR_SMOKE.md) | One-command synthetic CSV smoke (opt-in run) |
| CSV research | [CSV_BENCHMARK_PROTOCOL](CSV_BENCHMARK_PROTOCOL.md) | Read-only review of operator-entered benchmark records |
| CSV research | [CSV_COMPAT_MATRIX](CSV_COMPAT_MATRIX.md) | Synthetic compatibility fixtures (BOM, UTF-16, malformed, sort, group) |
| CSV research | [CSV_COMPAT_RESULTS](CSV_COMPAT_RESULTS.md) | Read-only semantic check of retained compatibility outputs |
| CSV research | [CSV_EVIDENCE_CROSSCHECK](CSV_EVIDENCE_CROSSCHECK.md) | Source-to-smoke evidence cross-check |
| CSV research | [CSV_CANDIDATE_DECISION_20261104](CSV_CANDIDATE_DECISION_20261104.md) | Evidence-led decision: retain Miller, keep alternatives research-only |
| Component research | [COMPONENT_REVIEW_20261020](COMPONENT_REVIEW_20261020.md) | Tool-by-tool component review |
| Component research | [RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md) | Original enterprise offline TOP 30 survey |
| Research data | [TOOLS_CANDIDATES_20261020.json](../research/TOOLS_CANDIDATES_20261020.json) | Canonical candidate register (pinned / built-in / research-only) |
| Research data | [INTAKE_ENTERPRISE_PORTABLE_20261025.json](../research/INTAKE_ENTERPRISE_PORTABLE_20261025.json) | 53-family enterprise intake crosswalk |
| Research data | [ENTERPRISE_PORTABLE_REVIEW_20261025.md](../research/ENTERPRISE_PORTABLE_REVIEW_20261025.md) | Review and correction notes for the enterprise intake |
| Research data | [SYSINTERNALS_NETWORK_REVIEW_20261021.json](../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json) | TCPView/PsPing license and deployment intake |
| Research data | [CSV_ALTERNATIVES_20261031.json](../research/CSV_ALTERNATIVES_20261031.json) | DuckDB/qsv/xan release metadata ledger |
| Research data | [LIGHTWEIGHT_CANDIDATES_20261031.json](../research/LIGHTWEIGHT_CANDIDATES_20261031.json) | DuckDB CLI/xsv/Tailviewer research ledger |
| Research data | [CSV_BENCHMARK_TEMPLATE.json](../research/CSV_BENCHMARK_TEMPLATE.json) | Empty public benchmark record template |
| Research data | [INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md](../research/INDUSTRIAL_PROTOCOL_ROLE_MATRIX_20261101.md) | Industrial protocol client/server/simulator role matrix |
| Reviews | [review/](review/) | Dated MECE, refactor and closure audits |
| Handoff (current) | [START_NEW_CHAT_PORTAKIT_20261108](handoff/START_NEW_CHAT_PORTAKIT_20261108.md) | The single current handoff and new-chat prompt |
| Handoff (archive) | [handoff/](handoff/) | All earlier dated handoffs, closeouts and the 2026-10-22 source map |
