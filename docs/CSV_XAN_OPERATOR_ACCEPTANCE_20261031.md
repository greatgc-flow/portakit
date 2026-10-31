# PortaKit — xan/Miller operator acceptance package (2026-10-31)

**Status: READY TO USE AS A PLAN ONLY; REAL-WORLD EVIDENCE NOT COLLECTED.**

This is a small, optional **human-in-the-loop** checklist that connects the already merged, independently tested source-only xan ZIP preflight and synthetic CSV smoke. It adds no new software dependency, executable invocation, download, installer promotion, GitHub Action, service, network listener, process sandbox or registry/PATH change. xan remains RESEARCH_ONLY, and the existing Miller pin is unchanged.

## 1. Gates, owner and independent evidence

Complete each row independently on an approved **nonproduction, genuinely isolated Windows** workstation. Do not substitute an operator flag, a GitHub Actions run, or a checksum for a corporate policy decision. Leave a gate PENDING rather than inferring approval.

| Gate | Minimum local evidence | Initial status | Decision authority |
| --- | --- | --- | --- |
| G1. Source file | Exact approved xan 0.61.0 Windows x64 MSVC original filename, compressed byte count, SHA-256, ZIP CRC and safe member structure | NOT_VERIFIED | Operator/source reviewer |
| G2. Binary identity | Source ZIP member xan.exe SHA/size = separately supplied local xan.exe; preserve exact original reports | NOT_VERIFIED | Operator/source reviewer |
| G3. Execution authorization | Approved specific host, isolation, software EULA/OSS and included notices, antivirus/EDR review, separate vendor transfer/redistribution rights | NOT_VERIFIED | Enterprise legal/security/host owner |
| G4. Physical Windows behavior | On approved host only, four deterministic Miller/xan synthetic CSV count/select cases and no unexplained workspace changes | NOT_VERIFIED | Operator/application owner |
| G5. Compatibility negatives | BOM, UTF-16, malformed CSV, Unicode/quotes/multiline and expected error behavior; report supported vs unsupported separately | NOT_VERIFIED | Operator/application owner |
| G6. Footprint/performance | Repeatable warm/cold runs, compressed and expanded bytes, CPU/RAM/disk use, startup and comparison against existing Miller with the same dataset | NOT_VERIFIED | Operator/performance owner |
| G7. Release decision | Explicit per-candidate reviewed acceptance after G1–G6, with evidence reviewed and portability impact understood | NOT_VERIFIED | Repository/release owner |

A real approved original may satisfy G1 and G2 without satisfying G3–G7. Passing G4 alone does not make xan safe, faster or enterprise-approved. Public GitHub issue #25 must contain **sanitized metadata and outcome only**, never vendor binaries, personal/enterprise paths, raw logs, host identifiers or corporate internal approval records.

## 2. Stage A — read-only plan (safe without vendor execution)

From the repository root, with Python 3.11+:

    python -I scripts/csv_operator_smoke.py plan --rows 10000

Exit 2 means PLAN_ONLY, not failure or PASS. No vendor executable runs and no files are written. Keep G1–G7 NOT_VERIFIED.

The expected official-source **metadata snapshot only** is xan 0.61.0 ZIP filename xan-x86_64-pc-windows-msvc.zip, 6,473,075 compressed bytes, SHA-256:

    5f7bef4dcffbfb3a3a937ac180ed76cdf966cb13647251beffddb84d01c1ae54

This snapshot was not a physically obtained archive in the previous session. A release digest is **not a publisher signature or legal/EDR clearance**.

## 3. Stage B — existing local original, never vendor execution

**Only when the exact original ZIP was separately acquired and retained under the operator's own permissions**:

    python -I scripts/xan_zip_preflight.py --original D:\ApprovedVendorArchives\xan-x86_64-pc-windows-msvc.zip

Optional explicit local source-to-EXE SHA identity check and new-only evidence:

    python -I scripts/xan_zip_preflight.py --original D:\ApprovedVendorArchives\xan-x86_64-pc-windows-msvc.zip --exe D:\ApprovedTools\xan\xan.exe --out D:\LocalEvidence\xan-source-001.json

Verify the exit is 0, source report outcome LOCAL_ORIGINAL_STRUCTURE_PASS, and localExeComparison.status is LOCAL_EXE_MATCHES_ZIP_MEMBER **only when the --exe flag was used**. The JSON reports sourceSHA256, compressedBytes, structure.expandedLogicalBytes, structure.xanExeMember, structure.xanExeSha256, structure.xanExeBytes and localExeComparison.sha256/bytes.

The tool streams source and member bytes and checks CRC/paths, but never extracts or launches a vendor binary. The new JSON and same-name .log are written only when --out is explicitly provided, and neither existing file may be overwritten. Check the local console and .log match. Exit 0 is **only** local SHA/ZIP structure/optional byte identity; set G1/G2 to independently reviewed only after confirming actual output.

**Stop here if G3 is not separately approved.** Do not use --approved-offline as a substitute for a physical airgap, permission or sandbox.

## 4. Stage C — separately authorized Windows functional smoke

Only after G3 authorization for the **exact binary hashes and specific isolated nonproduction host**, invoke the existing opt-in script:

    python -I scripts/csv_operator_smoke.py run --miller-exe D:\ApprovedTools\miller\mlr.exe --xan-exe D:\ApprovedTools\xan\xan.exe --evidence-dir D:\LocalEvidence\CSV-001 --rows 10000 --timeout-sec 20 --yes --approved-offline

Use a **new, empty path not yet created** for each run. The script writes generated synthetic edge.csv/bulk.csv, result.json and screen-identical console.log; it does not use real MES/PLC data. It runs the four explicitly documented count/select cases. For a local consistency review, compare the following **without publishing the source files**:

- Stage B localExeComparison.sha256 == Stage B structure.xanExeSha256 == Stage C exeSha256Local.xan.
- Stage C outcome FUNCTIONAL_PASS_ONLY requires four checks PASS, inputsUnchanged true, executablesUnchanged true and unexpectedWorkspaceEntries empty.
- Stage C syntheticInputSha256.edge/bulk should match the retained synthetic CSV files. Review local console.log alongside result.json.
- Stage C vendorArchiveProvenance and companyUseEDRRedistribution remain NOT_VERIFIED **even when its four commands pass**. Neither a previous source JSON nor a synthetic smoke automatically upgrades corporate authority.

Exit 0 from the smoke is FUNCTIONAL_PASS_ONLY, exit 2 means BLOCKED, exit 1 means invalid preconditions/evidence I/O. Do not equate CLI timeout or output bounds with Windows Job Object isolation, complete process-tree termination, CPU/RAM/disk quotas or network isolation.

## 5. Stage D — manual compatibility/performance evidence (no automatic vendor launcher)

If stages B–C pass and separate authorization continues, keep additional test cases independent from PortaKit's four-case smoke. Use entirely synthetic data and the **same** input bytes and configuration for Miller and xan. Suggested coverage: BOM/no BOM, Korean/Unicode and emoji, delimiter and quote escapes, CRLF/multiline, null/empty/missing columns, UTF-16 with supported/unsupported verdict, malformed records, aggregation/sort/group/filter, 100k rows where feasible, and reproducible failure exits.

Record the following for **each** case privately: exact commands, version and EXE hashes, approved host/OS/architecture, iteration count, input rows/bytes/hash, cold/warm method, elapsed time distribution (minimum/median/maximum), peak process-tree RSS/working set, CPU time, added disk bytes, exit/semantic verdict, and any observable network/child-process activity. If a metric cannot be reliably measured, label it NOT_MEASURED. A one-off elapsedMilliseconds field from Stage C **does not prove a speed or memory advantage**.

Do not introduce unapproved process monitors, network probes, drivers, services, new installations, or production connectivity just to collect performance observations.

## 6. Decision / feedback closure

**Keep Issue #25 open.** After a human gate owner reviews the real authorized local evidence, record a sanitized summary, the independently observed failures or limitations, the explicitly accepted residual risks, the next owner and action, and whether to **retain Miller**, **continue xan research**, or **start a separate catalog-admission PR**.

- Any missing/failed G1–G3: **STOP / not executable for PortaKit acceptance**.
- Any missing/failed G4–G6: **continue RESEARCH_ONLY**, do not rank or admit.
- All gates observed and approved: **propose a separate reviewed PR**, still no automatic admission.
- If real vendor behavior contradicts headless synthetic CI, record the discrepancy and add a small failing regression test before changing the source contract.

References: [source-only xan preflight](XAN_ZIP_LOCAL_PREFLIGHT.md), [synthetic CSV smoke](CSV_OPERATOR_SMOKE.md), [CSV candidates research](../research/CSV_ALTERNATIVES_20261031.json), [open acceptance Issue #25](https://github.com/greatgc-flow/portakit/issues/25).

This document is an **operator execution plan, not a completed acceptance report**. No actual original/executable or enterprise authorization was supplied or exercised while preparing it.
