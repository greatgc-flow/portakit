# CSV tooling — evidence-led admission decision (2026-11-04 KST)

> **Decision: RETAIN the existing Miller pin; keep xan, DuckDB, qsv, and xsv in research only.** This is a public-safe decision record, **not** a measured runtime benchmark, authorized installation, publisher attestation, license review or promotion. Live GitHub upstream and PortaKit main supersede this dated snapshot.

## User outcome and non-goals

PortaKit favors small, portable tools that demonstrably improve an operator's work. A release is not a reason to add another tool: compare **distinct daily use cases, correct output, usable resource footprint and maintenance/approval obligations** against the existing Miller baseline. No unratified speed threshold, company-use permission or field acceptance is invented here.

In particular, do **not** add a competing CSV binary only because it exposes the same count/select/sort/group functions, because a GitHub release exists, or because a published SHA matches a local downloaded file. Leave the actual vendor runtime, source authenticity, EULA/OSS/EDR, original-binary transfer and deployment acceptance with the final user/organization.

## Official release metadata rechecked on 2026-11-04

The following entries come from the official GitHub **releases/latest** API; sizes are compressed *asset* bytes, not installed disk usage, and GitHub's advertised asset digest is not independent publisher authentication.

| Option | Upstream release / target asset | Compressed bytes | Recorded SHA-256 / authority | Evaluation |
| --- | --- | ---: | --- | --- |
| **Miller (existing PINNED)** | [v6.22.0](https://github.com/johnkerl/miller/releases/tag/v6.22.0), `miller-6.22.0-windows-amd64.zip` | 6,227,745 | `a8b7f5fe321528d181c771948f631115b9c17a8ebdf1c5809de835349a9dd304`; also in current `catalog.json` | **RETAIN**; established CLI baseline; no proven replacement value |
| **xan (RESEARCH_ONLY)** | [0.61.0](https://github.com/medialab/xan/releases/tag/0.61.0), `xan-x86_64-pc-windows-msvc.zip` | 6,473,075 | `5f7bef4dcffbfb3a3a937ac180ed76cdf966cb13647251beffddb84d01c1ae54`; existing research ledger | **FIRST COMPARATIVE PILOT** only after operator gates; similar compressed size is *not* performance proof |
| **DuckDB CLI (RESEARCH_ONLY)** | [v2.0.0](https://github.com/duckdb/duckdb/releases/tag/v2.0.0), `duckdb-cli-windows-amd64.tar.gz` | 19,663,611 | `91663c2f36c2a334b0e5e639006d8c29c29e013af0c477d80bb931df68870312`; existing research ledger | **CONDITIONAL SQL/Parquet** use case, not general CSV replacement; no installer tar.gz support |
| **qsv (NOT ADMITTED)** | [28.0.0](https://github.com/dathere/qsv/releases/tag/28.0.0), `qsv-28.0.0-x86_64-pc-windows-gnu.zip` | 130,337,120 | GitHub asset metadata `e0fdcbb0ef83cd732d3407227893f7beff8206e222d20473e020317792dd63fc` | **DEFER**: above 100 MiB compressed limit |
| **qsv (same release)** | [28.0.0](https://github.com/dathere/qsv/releases/tag/28.0.0), `qsv-28.0.0-x86_64-pc-windows-msvc.zip` | 403,273,528 | GitHub asset metadata `f93d9cdfb769cb86ffb620808845586425c18a6b55bc902a74366628b9398216` | **DEFER**: above limit; do not weaken core size guard |
| **xsv (archived upstream)** | [0.13.0](https://github.com/BurntSushi/xsv/releases/tag/0.13.0), `xsv-0.13.0-x86_64-pc-windows-msvc.zip` | 792,499 | No GitHub release asset SHA in checked API; upstream archived | **DEFER**: maintenance/provenance cost despite small size |

**Architecture matters:** qsv 28.0.0 also has *Windows ARM64* ZIPs (45,056,566 and 51,957,089 metadata bytes). Those are **not** interchangeable with the listed Windows **x64** assets; their smaller size does not satisfy the x64 candidate's footprint goal. The older 2026-10-31 [CSV alternatives ledger](../research/CSV_ALTERNATIVES_20261031.json) accurately records the then-current qsv **27.0.1** snapshot and remains historical; do not rewrite its pinned test provenance to imply that 28.0.0 binaries were actually examined.

Upstream source of release observations: [Miller releases/latest](https://api.github.com/repos/johnkerl/miller/releases/latest) · [xan](https://api.github.com/repos/medialab/xan/releases/latest) · [DuckDB](https://api.github.com/repos/duckdb/duckdb/releases/latest) · [qsv](https://api.github.com/repos/dathere/qsv/releases/latest) · [xsv](https://api.github.com/repos/BurntSushi/xsv/releases/latest). These are dated observations; never auto-promote `latest`.

## MECE decision lanes (no redundant tooling)

| Operator need / differentiator | Current choice | What evidence would change the decision |
| --- | --- | --- |
| Small one-off CSV inspection, count, select, sort, aggregation | **Miller already pinned** | xan must show *correctness parity* and an independently observed, material operator value (performance, reduced manual steps, or uniquely needed operation) without losing portability |
| Repeated large CSV batch processing with resource limits | **xan benchmark candidate, not installed** | Real original+EXE hash, equal datasets/output, same host, balanced 5–20 paired cold/warm trials, CPU/RSS/disk and reproducible outcomes. No unmeasured "x% faster" claim |
| Multiple CSV/Parquet datasets needing SQL joins, aggregations or ad-hoc relational querying | **DuckDB conditional research** | Actual approved workload beyond Miller/xan, SQL and file-access containment, reproducible offline original and VC++ runtime, extension-autoinstall/network checks, and acceptable resource use |
| More command families without distinct local need | **Do not admit qsv** | Verified practical benefit and a separately justified size/packaging decision; no relaxation of the existing archive cap merely to fit it |
| Very small but archived upstream | **Do not admit xsv** | Maintained provenance and independently verified safety/operational benefit sufficient to outweigh existing Miller |

**Important semantics:** DuckDB's `read_csv` infers input dialect and types, and can query CSV with SQL. That is a *different* role from basic row-oriented CLI transformations, not proof of faster processing. See [upstream CSV docs](https://duckdb.org/docs/stable/data/csv/overview). Restrictive DuckDB SQL execution without local-file access and approved CSV/Parquet experiments are separate security lanes; do not infer that a single "safe mode" permits both. See [existing DuckDB review](DUCKDB_TARGZ_CSV_ALTERNATIVES.md).

## Reuse existing evidence instead of implementing a second benchmark

1. **No vendor execution by default:** `python -I scripts/csv_operator_smoke.py plan --rows 10000` (exit 2 = PLAN_ONLY). Source-only checks cannot rank performance.
2. **Original file identity before any separately authorized run:** xan [local ZIP preflight](XAN_ZIP_LOCAL_PREFLIGHT.md); DuckDB [bounded read-only tar.gz preflight](DUCKDB_TARGZ_CSV_ALTERNATIVES.md). The core installer deliberately still rejects `tar.gz`.
3. **Functional compatibility and numerical correctness:** [CSV synthetic input matrix](CSV_COMPAT_MATRIX.md), [read-only provided-output checker](CSV_COMPAT_RESULTS.md), [four-case operator smoke](CSV_OPERATOR_SMOKE.md). The checker verifies provided result semantics, not real execution or stderr.
4. **If the operator explicitly approves real performance observation:** [balanced benchmark protocol and empty template](CSV_BENCHMARK_PROTOCOL.md), with per-workload cold/warm trials, exact binary/data hashes, errors and separately recorded CPU/RSS/disk. Missing metrics remain **NOT_MEASURED**, never zero.
5. **Independent acceptance:** [G1–G7 operator checklist](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md) plus [enterprise acceptance owner](END_USER_ACCEPTANCE.md). Any later single-tool admission requires its own reviewed PR and fresh original/permissions; green synthetic Windows CI is not deployment permission.

### Recorded outcome and next decision owner

- **Engineering decision now:** Keep current Miller pin, 151 selectable IDs / 19 install-capable pins and all existing CLI/GUI behavior unchanged. No new exporter, generic benchmark harness, TAR extractor, installer extension, download or Release. No acceptance metrics have been measured by this review.
- **Next owner:** Final user / authorized operator supplies a concrete workload and approvals if there is a reason to compare real xan with Miller or to test DuckDB's distinct SQL value.
- **Backlog #25 remains OPEN:** If real evidence shows equivalent or worse capability, stop the corresponding candidate without a source PR. If benefit is independently demonstrated and gates are met, propose a **separate** minimal approval/admission change; never treat this dated memo as such approval.
