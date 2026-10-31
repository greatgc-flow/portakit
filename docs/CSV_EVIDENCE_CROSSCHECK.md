# xan / Miller evidence cross-check (read-only)

**Research only, not a vendor execution test or company approval.** This optional, standalone helper checks whether the output from the already-existing xan original ZIP preflight agrees with the separate, already-existing four-command CSV smoke evidence. It runs **no vendor executables**, downloads nothing, creates no files by default, and cannot validate publisher signatures, legal permissions, EDR clearance or physical network isolation.

## Inputs and preconditions

Only use existing evidence created by the two scripts documented in:
- [xan original ZIP preflight](XAN_ZIP_LOCAL_PREFLIGHT.md)
- [CSV operator smoke](CSV_OPERATOR_SMOKE.md)
- [seven independent acceptance gates](CSV_XAN_OPERATOR_ACCEPTANCE_20261031.md)

The source stage must have produced a local source JSON + exact console .log with optional --exe (without --exe, source-to-exe identity is NOT_CHECKED). The separately authorized isolated Windows smoke stage must have its result.json, console.log and retained edge.csv/bulk.csv. **Do not start either executable merely to use this verifier.** Both source reports are operator-controlled and independently editable; internal consistency does not make them cryptographically authentic.

## Usage (Python 3.11+, no vendor execution)

From the PortaKit repository root, substitute actual **existing local** evidence paths:

~~~cmd
rem Pure read-only inspection; no output files.
python -I scripts/verify_csv_evidence.py --source-json D:\LocalEvidence\xan-source-001.json --smoke-dir D:\LocalEvidence\CSV-001

rem Optional: creates only a NEW JSON plus identical console .log.
python -I scripts/verify_csv_evidence.py --source-json D:\LocalEvidence\xan-source-001.json --smoke-dir D:\LocalEvidence\CSV-001 --out D:\LocalEvidence\CSV-crosscheck-001.json
~~~

The first command prints a compact result only. The second fails rather than replacing existing evidence, and uses the same console text in the new .log file. No original asset, executable, registry, service, PATH, network interface, installer, file association or production MES/PLC system is modified.

## Checks and exact meaning

1. Validate the source report schema/version and that original ZIP SHA + byte size match the pinned **research-only** official-release metadata. Check the source still reports runtime/enterprise approval as NOT_VERIFIED.
2. Check the unique ZIP xan.exe member digest and byte count, and verify its optional local EXE comparison matches both fields. NOT_CHECKED remains incomplete, even if downstream smoke reported passing results.
3. Check the smoke report has exactly four known cases in the fixed order: Miller count, xan count, Miller select and xan select; reject missing/duplicate/unsupported statuses, impossible pass results, missing integrity fields and contradictory input/executable mutation reports.
4. Independently recompute SHA-256 of retained synthetic edge.csv and bulk.csv (bounded local reads; no changes to CSV files). Validate both against their original reported SHA values **and independently regenerate the exact deterministic CSV content hash** from the fixed synthetic row grammar and recorded row count. Changing the CSV and its JSON hash together cannot pass this consistency check unless the original synthetic content is preserved.
5. Reconstruct each console transcript from the existing source/smoke display functions and compare **exact canonical UTF-8 text bytes**, including **LF line endings and final newline**, against the companion .log. The source preflight .log includes one REPORT: path footer with its historical path (may differ from a copied evidence file's new location). Changed CRLF, missing terminator, or appended footer lines are rejected.
6. When the source was explicitly bound to a local xan.exe, compare that digest to the executable SHA recorded by the smoke. Mismatch blocks the chain.
7. Preserve publisher, company license/EDR/transfer, physical host isolation and performance certification as NOT_VERIFIED, regardless of the internal result.

| Process exit | Result | Meaning |
| --- | --- | --- |
| 0 | EVIDENCE_CROSSCHECK_ONLY | Both reports/fixtures/transcripts internally consistent, source EXE identity linked and all four existing smoke cases recorded as PASS. **NOT** vendor authenticity, runtime safety or enterprise approval. |
| 2 | INCOMPLETE_OR_BLOCKED | Evidence is internally consistent but the source EXE was NOT_CHECKED or one/more smoke cases are blocked. |
| 1 | ERROR | Missing/modified source or fixture, mismatched SHA, invalid JSON/schema/log, unsupported statuses, contradictory verdict, unsafe local file or output collision. |

**Strict distinction:** Exit 0 does not independently rerun xan or Miller and does not prove the prior runner's host was genuinely offline or approved. Rewriting both JSON and .log could fabricate consistent evidence; only an independent authorized gate owner can attest to provenance/permissions and observe real Windows behavior.

## Security, bounds and acceptance

- Only local pre-existing JSON/log and synthetic CSV are read. JSON and log read caps are 1 MiB each; each fixture is capped at 32 MiB. Existing source path reparse/symlink checks are reused.
- Synthetic CI uses dummy files whose names end in .exe and a fake Python runner; **no vendor binary is ever launched** in the new tests.
- A source metadata snapshot is not a publisher signature, SHA equality is not approval, and the CLI's --approved-offline flag is an assertion, not a sandbox.
- Do not commit private enterprise paths, local operator evidence files, binary archives/executables, host identities, credentials or unredacted logs to the public repository.
- Keep [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) open until the seven independent human/enterprise acceptance gates are actually completed, including real compatibility and repeatable performance. xan remains RESEARCH_ONLY.

## Strict evidence format (source-only hardening)

- Reports use UTF-8 JSON. **Duplicate object keys at any depth** and nonstandard NaN/Infinity numeric tokens are invalid rather than using a JSON parser's last-wins interpretation.
- A case recorded as PASS must also have process returnCode 0, capturedOutputTruncated false, bounded nonempty stdout, bounded stderr and syntactically valid captured-prefix SHA fields. This catches **contradictory recorded claims**, but raw vendor stdout is not retained and cannot be independently reproduced by this checker.
- Console verification checks exact expected LF bytes, not `splitlines()` equivalence; Windows CRLF conversion is flagged as a changed file. The original log emitter writes LF on both Windows and Linux.
- Cross-check outcome **does not authenticate** a local JSON+log pair. A coordinated rewrite can still be self-consistent; independent source provenance, corporate signoff, approved host and real vendor testing remain distinct gates.

## Deterministic fixture replay (source-only)

- The verifier regenerates only the expected **hashes**, in memory, using the existing fixed UTF-8/CRLF CSV generator contract. No temporary CSV files or vendor processes are created.
- `edge.csv`: the original fixed header, Unicode/quoted/multiline/blank test records. `bulk.csv`: the original header plus the exact `rowsCounted` generated rows using the fixed name sequence.
- This detects edited CSV content even when the recorded SHA fields and matching log are edited together. Bounded row generation supports the existing 1–100,000-row smoke range without building a large in-memory row list.
- It does **not** prove the operator ran a real vendor process or authenticate a coordinated rewrite of unrelated fields. Enterprise/legal/EDR, offline host, executable provenance and performance gates remain separate and NOT_VERIFIED.
