# Synthetic CSV compatibility matrix — xan vs existing Miller (2026-11-02)

> **Source-only preparation.** This adds *no* third-party executable, GUI acceptance, installer, network listener, catalog admission, Windows permission or runtime performance claim. It complements, but never modifies, the four fixed checks and existing evidence-v1 format in [CSV_OPERATOR_SMOKE](CSV_OPERATOR_SMOKE.md). The xan tool remains RESEARCH_ONLY.

## Simple commands

From the repository root using Python 3.11+:

```cmd
rem No files, no vendor execution; exit 2 means PLAN_ONLY.
python -I scripts/csv_compat_fixtures.py

rem Create ONLY synthetic files and matrix.json + identical matrix.log.
rem Directory MUST NOT exist already. Exit 0 means PREPARED_ONLY.
python -I scripts/csv_compat_fixtures.py --out-dir D:\LocalEvidence\CSV-Compat-001
```

Generated five bounded files (total less than 16 KiB), with SHA-256/byte counts in `matrix.json` and console text mirrored byte-for-byte in `matrix.log`:

| File | Purpose | Permitted conclusion before vendor tests |
| --- | --- | --- |
| `edge-utf8.csv` | Korean, emoji, quotes, CRLF and multiline fields, no BOM | Known synthetic reference only |
| `edge-utf8-bom.csv` | Same bytes with UTF-8 BOM | Vendor interpretation **NOT_VERIFIED** |
| `edge-utf16le.csv` | Same semantic data encoded UTF-16 little-endian with BOM | Vendor interpretation **NOT_VERIFIED** |
| `malformed-quote.csv` | Unterminated quoted field, invalid CSV fixture | Observe behavior and error, no automatic PASS |
| `sort-group.csv` | Five rows with distinct numerical qty values and A/B categories | Numeric sort and sum references are deterministic |

### Two precise baseline semantics

For `sort-group.csv`, expected ascending **numeric** order of `id`: `r4,r2,r5,r3,r1` (qty 1,2,3,9,10). Lexicographic sorting would place 10 between 1 and 2 and is **not** equivalent. Expected group sum of `qty`: `A=14, B=11`. Compare parsed CSV **values** and group keys, not byte-for-byte row order (group output ordering may vary).

The following are **reference commands for a human on a separately authorized, isolated Windows nonproduction workstation**. They are not invoked by the fixture generator. Source syntax was checked against upstream [Miller verbs](https://github.com/johnkerl/miller/blob/main/docs/src/manpage.md), [xan sort](https://github.com/medialab/xan/blob/master/docs/cmd/sort.md) and [xan groupby](https://github.com/medialab/xan/blob/master/docs/cmd/groupby.md). Test the exact approved versions before relying on their output:

```cmd
rem With working directory set to the created synthetic fixture directory:
mlr --csv sort -nr qty sort-group.csv
xan sort --numeric --select qty sort-group.csv

mlr --csv stats1 -a sum -f qty -g category sort-group.csv
xan groupby category "sum(qty) as qty_sum" sort-group.csv
```

These examples do not assert identical column order, quoting, or numeric formatting. For the BOM/UTF-16/malformed/quoted files, use operator-approved vendor commands to observe exact parsing/error behavior, with independently recorded exit, stderr, output and original SHA. In particular, do not mark UTF-16 as supported solely because Python could generate a UTF-16 fixture.

## Safety, errors and evidence

- The **default mode** prints a plan and leaves the filesystem unchanged (exit 2). `--out-dir` is explicitly opt-in and **refuses any existing directory** rather than overwriting or deleting it. Its filenames and input byte lengths are fixed and bounded; it performs no vendor calls. Exit 0 means **files prepared**, NOT a functional compatibility PASS.
- On an I/O failure, a **partial new directory may remain**. Do not re-use or automatically remove it; review locally and use another clean destination. The JSON and console transcript use shared identity-aware best-effort output cleanup; this is not an atomic multi-file crash-safe transaction.
- The generated synthetic fixtures and manifest can be reviewed and hashed locally but prove only *what this source generated*. They do **not** prove xan/Miller will parse BOM/UTF-16/malformed data, correctly sort/group or outperform the existing Miller.
- Real operator tests, approved original SHA, complete dependency/license notices, security/EDR and airgap-transfer authorization, actual Windows runtime, performance and deployment remain **final-user/organization owned**. Never commit locally recorded workstation, network, EULA or proprietary equipment evidence to this public repo; do not use production MES/PLC data.

Leave [#25](https://github.com/greatgc-flow/portakit/issues/25) open and retain the four-case [existing opt-in smoke](CSV_OPERATOR_SMOKE.md) plus independent [source ↔ runtime evidence crosscheck](CSV_EVIDENCE_CROSSCHECK.md) unchanged.
