# CSV tools: one-command synthetic Windows smoke (2026-10-31)

**Goal:** Let an authorized operator compare an existing Miller executable and a separately acquired xan executable using the same tiny, deterministic CSV correctness checks. Do not run either vendor program from CI. No installation or vendor file is bundled.

This design follows [VerySimpleGuide](https://github.com/greatgc-flow/VerySimpleGuide) at main commit 0aef4e93cbd9b746c4927f08ce9bfda685e897e4: [decision rules](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/01_METHOD/DECISION_RULES.md), [CLI contracts](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/02_STANDARD/CLI_STANDARD.md), [observation/evidence](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/02_STANDARD/OBSERVABILITY_EVIDENCE_STANDARD.md), [real-world gates](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/04_ASSURANCE/REALITY_GATES.md) and [feedback closure](https://github.com/greatgc-flow/VerySimpleGuide/blob/main/01_METHOD/OPERATIONAL_FEEDBACK_LOOP.md). It uses those principles without importing a framework, copying an entire policy package, or claiming certified conformance.

## Usage (Windows, Python 3.11+)

**1. Free and read-only discovery:**

~~~cmd
python -I scripts/csv_operator_smoke.py
python -I scripts/csv_operator_smoke.py plan --rows 10000
~~~

Exit code 2 = PLAN_ONLY / not executed. No files created and **no vendor process started**.

**2. Only if company policy and an isolated offline test machine explicitly allow running the two exact local executables:**

~~~cmd
python -I scripts/csv_operator_smoke.py run --miller-exe D:\ApprovedTools\miller\mlr.exe --xan-exe D:\ApprovedTools\xan\xan.exe --evidence-dir D:\LocalEvidence\CSV-001 --rows 10000 --timeout-sec 20 --yes --approved-offline
~~~

The evidence directory **must not already exist**. This is a new scratch location, not a production data directory or a PortaKit managed tool directory. Neither binary is downloaded, copied into the repo, installed, or added to PATH by the script. The program rejects absent/misnamed executables and reparse/symlink paths before launching. Flag --approved-offline is the **operator's assertion**, not proof of physical isolation, process sandboxing, network blocking or a valid company license. Third-party executables can still create processes, write outside the evidence directory, access the network when available and be intercepted by EDR. Only use a genuinely isolated, nonproduction, authorized host.

## Exactly four executable checks

| Tool | Command semantics | Expected result |
| --- | --- | --- |
| Existing Miller | mlr --csv count bulk.csv | Header count plus exact requested number of synthetic data rows |
| Research-only xan | xan count --check-alignment bulk.csv | Exact number of synthetic data rows (no header) |
| Existing Miller | mlr --csv cut -f id,name edge.csv | Header and five rows with the two selected columns |
| Research-only xan | xan select id,name edge.csv | Same semantic CSV content, irrespective of newline/quote representation |

Upstream references: [Miller manpage](https://github.com/johnkerl/miller/blob/main/docs/src/manpage.md), [xan count](https://github.com/medialab/xan/blob/master/docs/cmd/count.md) and [xan select](https://github.com/medialab/xan/blob/master/docs/cmd/select.md).

Only synthetic UTF-8 CSV is generated. The small file includes Korean, accented Latin, emoji, commas, double quotes, empty values, CRLF and a multiline field; the separate bulk file contains the configured 1–100,000 rows (default 10,000). Each call has a bounded timeout (1–120 seconds), with no shell, no user-supplied expressions and no real MES/PLC data. Vendor stdout is interpreted as **semantic CSV or integer output**, not a platform-specific raw byte-for-byte match. Nonzero exits, wrong data, invalid encoding, timeouts, unexpectedly large captured output, mutated source CSV or EXE, and unexpected files **inside the evidence workspace** block the result. The script cannot detect or prevent files the vendor writes outside that workspace, or child-process/network effects.

A successful run is **FUNCTIONAL_PASS_ONLY**, with operator-local EXE SHA-256 fingerprints and exact console-mirrored evidence in result.json and console.log. Exit codes: **0 = just these four functional checks passed**, **2 = one or more observed checks blocked/failed, or read-only plan pending**, **1 = invalid usage/preconditions/local evidence I/O**. None of these values admits xan into the tool catalog or establishes a vendor binary's provenance.

The report explicitly retains vendor archive provenance, corporate EULA/OSS/EDR/transfer rights and performance ranking as **NOT_VERIFIED / NOT_ASSESSED**. The command records individual elapsed milliseconds but **one pass is not a representative benchmark**, nor CPU/RAM measurement. Manual side effects outside its local scratch directory and network isolation remain unmeasured.

## Boundaries and follow-up

- **In scope, verified by isolated headless CI:** consent and Windows gates, direct-path validation, 4-case command contract, Unicode/quoted CSV parsing, output and timeouts, drift and workspace checks, no overwrite, deterministic local evidence. CI uses **fake vendor responses and synthetic EXE placeholders**, never real vendor programs.
- **Separate reality gates, not yet verified:** original xan 0.61.0 Windows x64 ZIP SHA from locally obtained original; expanded size; real Miller/xan exe identity and version; actual Windows offline console correctness; 100k+ rows, BOM, UTF-16, deliberately malformed CSV, numerically typed sorting/grouping, concurrent/memory-heavy operations; CPU/RAM/disk and repeated cold/warm run metrics; unapproved network writes; all bundled OSS notices, company approval, EDR and transfer/redistribution rights.
- **Acceptance/feedback:** [PortaKit Issue #25](https://github.com/greatgc-flow/portakit/issues/25) stays OPEN until **independent real original + enterprise acceptance evidence**. This source-only PR is implementation and headless test evidence, not a field pass or Issue closure. If a real test differs, record the exact binary SHA, scope, host, result, and next action there without posting enterprise-sensitive data.
- **Very Simple decision:** One optional module; read-only plan as the default; one explicitly authorized run path; fixed, well-sourced commands instead of generic user-defined shell execution, benchmarking DSL, new provider layer or catalog promotions. External binary execution is a stronger reality gate than structural checks, never conflated with them.

No automatic download, installation, network connection, privileged driver, registry mutation, scheduled task or default listener is introduced.
