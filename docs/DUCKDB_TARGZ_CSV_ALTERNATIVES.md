# DuckDB tar.gz preflight and CSV CLI alternatives (2026-10-31)

**RESEARCH ONLY / NOT ADMITTED.** The checked-in catalog and canonical 151 software selections / 19 SHA-pinned installable tools are unchanged. This is source-and-structure evidence, not a vendor runtime installer, publisher signature or corporate EULA/EDR approval.

## 1. DuckDB 2.0.0 Windows x64 original: read-only preflight

Official [DuckDB installation docs](https://duckdb.org/docs/2.0/installation) publish the Windows CLI asset **duckdb-cli-windows-amd64.tar.gz** and its SHA-256: **91663c2f36c2a334b0e5e639006d8c29c29e013af0c477d80bb931df68870312**. GitHub release metadata records **19,663,611 compressed bytes**, not extracted size. Windows requires the Microsoft Visual C++ Redistributable. DuckDB extensions, SQL access to local files, and network use need separate sandbox review.

The current PortaKit core accepts ZIP, EXE and verified SFX7z, **not tar.gz**. Do not rename TAR as ZIP, run a remote install script, or bypass current installer guards.

Run only when separately authorized to obtain the original file:

~~~cmd
rem SHA and structure audit: does not write or extract anything.
python -I scripts/targz_preflight.py --original D:\ApprovedVendorArchives\duckdb-cli-windows-amd64.tar.gz

rem Optional new-only local JSON plus byte-mirrored console .log.
python -I scripts/targz_preflight.py --original D:\ApprovedVendorArchives\duckdb-cli-windows-amd64.tar.gz --out D:\LocalEvidence\DuckDbTarAudit.json
~~~

The auditor reuses the explicitly RESEARCH_ONLY DuckDB source record's SHA and verifies the exact local original. It then streams TAR/gzip **without extracting anything to disk**; checks the gzip checksum, all regular-file bodies, case-insensitive Windows path collisions, traversal/device names, file-as-parent, special/link members, unsupported PAX, total member count (maximum 4,096), depth (maximum 32), expanded logical bytes (maximum 512 MiB), and decompressed TAR stream headers/padding budget. It computes the original SHA again after streaming. It never uses TAR extract/extractall, runs vendor executables, downloads, installs, changes PATH/registry/services/drivers or opens network listeners.

Exit 0 means **LOCAL ORIGINAL SHA AND STRUCTURE PASSED AT THAT TIME ONLY**; failure/unsafe input is exit 2. A green audit is not installer approval, corporate EULA/EDR, source authenticity attestation or proof DuckDB can run safely. The real official archive member layout has **NOT** been tested here; CI uses synthetic safe/hostile TAR fixtures. If actual TAR metadata exceeds the strict supported subset, preserve the original and review manually rather than weakening safety by default. New-only JSON and exact console logs remain local; never commit real corporate workstation paths or files to this PUBLIC repo.

Remaining gates: independent original SHA on authorized Windows host, actual expanded size, bounded extraction design, physical Windows runtime and VC++ availability, disabled extension autoinstall/autoload, no unsolicited network, synthetic CSV/Parquet, CPU/RAM/disk measurement, publisher/software provenance, OSS/license notices, EDR, separate redistribution/airgap transfer approval and explicit Release decision.

## 2. qsv and xan versus archived xsv / current Miller

Supplemental structured evidence: [CSV alternatives release metadata](../research/CSV_ALTERNATIVES_20261031.json). All values are **compressed GitHub release asset sizes**, not expanded footprint or actual operator tests.

| Tool | Official Windows x64 asset | Compressed bytes | Maintenance and license note | Assessment |
| --- | --- | ---: | --- | --- |
| Miller 6.22.0 | Existing pinned ZIP in catalog | Not newly measured | Existing independent pinned baseline | Retain as current baseline |
| xsv 0.13.0 | Old Windows x64 MSVC ZIP | 792,499 | Upstream archived in 2025, GitHub release API lacks SHA | Deprioritize |
| [qsv 27.0.1](https://github.com/dathere/qsv/releases/tag/27.0.1) | x64 MSVC ZIP | **402,543,109** | [MIT since version after 21.1.1](https://github.com/dathere/qsv/blob/master/COPYING) | Over current 100 MiB compressed archive cap |
| qsv 27.0.1 | x64 GNU ZIP | **129,287,020** | Same upstream | Also over cap; do not weaken guard merely to admit |
| [xan 0.61.0](https://github.com/medialab/xan/releases/tag/0.61.0) | x64 MSVC ZIP | **6,473,075** | [MIT or Unlicense](https://github.com/medialab/xan/blob/master/COPYING) | Most promising next compact CLI **research** candidate |

The latest GitHub release metadata includes SHA-256 values for qsv and xan, saved in the supplementary JSON. They **are not original-file hashes independently verified in this task**. An upstream license summary never certifies downstream dependencies, corporate permission or transfer/redistribution. No qsv/xan were added to the canonical catalog or the selectable 151-item inventory.

Next independent xan-versus-Miller synthetic Windows tests: BOM/Unicode/UTF-16, CRLF and quoting, commas and escaped quote records, missing/null/empty values, malformed records and clean error, unique/sort/filter/group/join results, large CSV (100k+ rows), RAM/CPU/cold startup and unintentional network/file writes. Benchmark without running against real MES/PLC data. Retain Miller unless xan proves measurable efficiency in actual operator workflows and passes original SHA, footprint, license/EDR and offline acceptance.

## 3. Tailviewer independent GUI verification

[Official Tailviewer](https://github.com/Kittyfisto/Tailviewer) documents .NET Framework 4.7.1+ and multi-file timestamp merge. Keep 2022 portable ZIP **RESEARCH_ONLY** until independently hashed, actual portable config writes, GUI Unicode/IME, multiline/rotation/timestamp correctness, accessibility and corporate approval are observed on an authorized nonproduction Windows workstation.

## CI / acceptance boundary

A green headless Python Windows 3.11/3.14 matrix proves the new algorithm's synthetic bounded parsing and unchanged research/admission boundaries, **not** actual vendor-original bytes, Windows CLI performance, GUI or legal rights. Leave [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) open and require a distinct reviewed PR for any eventual promotion.
