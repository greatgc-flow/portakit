# CSV compatibility outputs — read-only semantic check (2026-11-02)

**Source-only verifier; NO vendor executions or release approval.** [Create the five tiny input fixtures](CSV_COMPAT_MATRIX.md) separately using the existing `csv_compat_fixtures.py`. The resulting `matrix.json`, `matrix.log` and five fixed input CSV files must remain unchanged.

## Usage

From the repository root (Python 3.11+):

```cmd
rem Default PLAN ONLY; exit 2, no file writes and no vendor process.
python -I scripts/csv_compat_results.py

rem Read existing source fixtures and operator-provided outputs, no file writes.
python -I scripts/csv_compat_results.py --fixtures-dir D:\LocalEvidence\CSV-Compat-001 --results-dir D:\LocalEvidence\CSV-Compat-Results

rem Optional NEW JSON and exactly mirrored local log at a THIRD location.
python -I scripts/csv_compat_results.py --fixtures-dir D:\LocalEvidence\CSV-Compat-001 --results-dir D:\LocalEvidence\CSV-Compat-Results --out D:\LocalEvidence\CSV-Compat-Review-001.json
```

Both input directories must exist. The source directory must have the original `matrix.json`, `matrix.log` and five canonical CSV files. The verifier recomputes their **exact bytes independently** and refuses modified/fake evidence; this is a point-in-time source consistency check, not publisher authentication.

## Fixed result filenames and semantic expectations

| Existing results-dir file | Intended manual producer command (separately approved Windows only) | Expected CSV meaning |
| --- | --- | --- |
| `miller-sort.csv` | `mlr --csv sort -n qty sort-group.csv` | Numeric ascending IDs `r4,r2,r5,r3,r1` |
| `xan-sort.csv` | `xan sort --numeric --select qty sort-group.csv` | Same numeric sorted rows |
| `miller-group.csv` | `mlr --csv stats1 -a sum -f qty -g category sort-group.csv` | `category,qty_sum`: A=14, B=11 |
| `xan-group.csv` | `xan groupby category "sum(qty) as qty_sum" sort-group.csv` | Same group sums |

**The verifier NEVER executes these commands.** The operator saves their **stdout CSV** at the indicated fixed filenames in a separate existing local directory. The operator must independently record original binary provenance, exact command exit code and stderr; simple stdout capture cannot prove execution occurred or that the vendor emitted no warning. A different column order, CSV quoting or CRLF/LF representation is accepted if the parsed rows/keys/numbers agree; numerical order is mandatory for sort, group row order is not. Extra/missing/duplicate data, incorrect numeric results, malformed CSV and UTF-16 masquerading as UTF-8 are mismatches. BOM and deliberately malformed *input* compatibility remain separate human test cases, **not automatically passed here**.

## Outcome and safety boundary

- `SEMANTIC_MATCH_ONLY` (exit `0`) means all **four supplied file contents** match the expected CSV values; **not** proof that xan or Miller actually ran, exited 0, produced empty stderr, or met the user's security/license policy.
- `INCOMPLETE_OR_MISMATCH` (exit `2`) means one or more result files are **MISSING** or **MISMATCH**; no full semantic-match claim. Source-only plan without arguments also returns 2.
- Exit `1` means missing/modified source fixtures, invalid or unsafe path, over-limit/unreadable result file, invalid arguments or optional evidence write failure. It never returns a successful conclusion on errors.
- Input reads are size-bounded and use the existing reparse/regular-file and detectable replacement protections. No file is created by default. `--out` creates only an **exclusive, new** JSON and byte-identical `.log` outside both input trees, using existing identity-aware best-effort cleanup. Dot-dot (`..`) aliases are normalized **for location comparisons** so an alternate spelling cannot write into an input tree or treat one directory as two; existing reparse checks still apply to the original paths. This is not an atomic multi-file commit. The verifier never rewrites result files, the fixture matrix or any operator file.
- No real vendor, installer, tool admission, environment probe, shell execution, download, network listener, process isolation or performance score is introduced. Any approved real execution, version and publisher SHA, local Windows/EDR/OSS/EULA/airgap verification and deployment decision remain entirely **final-user/organization owned**.

Cross-reference: [four-case operator smoke](CSV_OPERATOR_SMOKE.md), [source ZIP ↔ smoke evidence chain](CSV_EVIDENCE_CROSSCHECK.md), [Issue #25](https://github.com/greatgc-flow/portakit/issues/25). Neither existing schema nor execution path is changed.
