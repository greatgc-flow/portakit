# CSV benchmark evidence — operator data, source-only review (2026-11-02)

**Scope:** reproducible metadata consistency, not automatic benchmark execution, speed ranking, release admission, host isolation, or corporate EULA/OSS/EDR approval. [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) remains open. Existing Miller pin and xan RESEARCH_ONLY are unchanged.

## Very Simple workflow

1. Follow [existing acceptance stages G1–G7](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md) and [CSV input matrix](CSV_COMPAT_MATRIX.md). Only after the final user separately approves a genuinely isolated nonproduction Windows workstation and genuine source originals, collect results privately. Never use MES/PLC or corporate production data.
2. Copy [the **empty** JSON template](../research/CSV_BENCHMARK_TEMPLATE.json) to a private local path, and fill **actual observations**, not demo/synthetic timing values. Use one dataset, one workload, same exact input SHA/bytes and one stable host/architecture and comparable tool versions. Record exact commands, executable SHA, source files and run logs privately. This script checks the supplied records and supplied CSV original; it **cannot** prove executables actually used that file.
3. For each workload (count/select/sort/group), keep separate measurements. Cold vs warm requires a documented local cache/startup method. At least **5 and at most 20** trials per tool and phase, same count for all four tool/phase groups. Within each phase alternate pairs: odd trials Miller→xan; even trials xan→Miller. This reduces ordering bias but **does not** establish a genuinely cold OS cache.
4. Each observed run needs tool, phase, trial, elapsedMs, cpuMs (or null), peakRssBytes (or null), diskWrittenBytes (or null), exitCode, stderrBytes and semanticStatus (MATCH, MISMATCH, NOT_VERIFIED). Do not label nonzero exit, stderr warnings, wrong CSV or unreviewed output a successful benchmark. Record original stdout/stderr privately; for sort/group the [independent output semantic checker](CSV_COMPAT_RESULTS.md) can help, but cannot independently validate process exit.
5. Interpret only the **descriptive distribution** (min/median/max *per tool and cold/warm separately*) and explicitly note unavailable CPU/RSS/disk measurements. Never infer a universal winner, speed percent, future deployment suitability or security approval from one small dataset. Repeat on useful representative synthetic datasets after operator authorization if needed.

## Commands

Run from repository root, Python 3.11+:

```cmd
rem Plan only: exit 2, no files written or vendor executions.
python -I scripts/csv_benchmark_review.py

rem Inspect existing local observations and original synthetic dataset, read-only.
python -I scripts/csv_benchmark_review.py --input D:\LocalEvidence\benchmark.json --dataset D:\LocalEvidence\bulk.csv

rem Optional new-only JSON plus an exactly mirrored local .log.
python -I scripts/csv_benchmark_review.py --input D:\LocalEvidence\benchmark.json --dataset D:\LocalEvidence\bulk.csv --out D:\LocalEvidence\benchmark-review-001.json
```

**Exit 0 = DESCRIPTIVE_TIMING_ONLY:** recorded tool/phase/trial slots balanced 5–20 each, declared exit 0/stderr=0/semantics=MATCH, and dataset original SHA/byte count/CSV rows independently checked against the supplied file. The checked source must have nonempty, unique CSV column names; matching SHA and row count alone cannot validate ambiguous duplicate headers. The *run observations remain operator self-report*. No actual vendor execution, cold-cache enforcement, publisher authenticity or corporate authorization is verified.

**Exit 2 = INCOMPLETE_OR_BLOCKED:** not enough/unequal trials, operator-declared error/warning or semantic status unverified; no timing summary is output. The default PLAN also returns 2. Invalid schema, repeated trial, altered/unsafe dataset or invalid numbers and evidence I/O fail with exit 1.

CPU/RSS/disk coverage labels are independently RECORDED_ALL or NOT_MEASURED_OR_PARTIAL. A missing metric is **null**, not zero; no values are invented. Output always states performanceRanking=NOT_ASSESSED, publisherAuthenticity=NOT_VERIFIED, companyApproval=NOT_VERIFIED and that observed vendor runtime and cold-cache method remain **not machine verified**.

## JSON schema and ownership

The checked-in [template](../research/CSV_BENCHMARK_TEMPLATE.json) deliberately contains *null* provenance and *zero* timing observations. Keep it that way in this PUBLIC repo. Copy it locally and fill `inputSha256` (64 lower-hex characters), `inputBytes`, `inputRows` (excluding CSV header), the two `toolSha256` digests, nonempty ASCII `environmentNote` and `coldMethod` (max 300 chars, no private path or secret in public issues). Supported workload names: `count`, `select`, `sort`, `group`; `datasetClass` stays `SYNTHETIC_OPERATOR_DECLARED`. A real source ID is validated locally but **no host-specific note is echoed or written to summary output**.

One run has this **structure only** (the null elapsed is **not** allowed for a recorded run; fill with a real positive finite number only after actual observation):

```json
{
  "tool": "miller",
  "phase": "cold",
  "trial": 1,
  "elapsedMs": null,
  "cpuMs": null,
  "peakRssBytes": null,
  "diskWrittenBytes": null,
  "exitCode": null,
  "stderrBytes": null,
  "semanticStatus": "NOT_VERIFIED"
}
```

Do not paste invented measurements into GitHub. Source-only CI uses temporary CSV, dummy SHA and artificially simulated timing records strictly to test parser behavior. It never invokes Miller, xan or publisher downloads. Optional summary output is exclusive-create JSON with an exact console transcript, reusing the project's best-effort identity-aware cleanup. It is **not an atomic crash-safe two-file commit**.

Independent enterprise stakeholders retain all authority for publisher/source originals, Windows/EDR/OSS/EULA, network isolation, measurement accuracy, transfer permissions, deployment decisions and any catalog promotion. A green developer CI remains distinct from those gates.
