# Lightweight candidates — evidence, not installation approval (2026-10-31)

**Source-only research snapshot. No candidate is deployable.** Issue [#25](https://github.com/greatgc-flow/portakit/issues/25) owns admission. The maintained software catalog and source integrity/installation code are unchanged. The new machine-readable [ledger](../research/LIGHTWEIGHT_CANDIDATES_20261031.json) is supplemental to the existing canonical research register and Oct 25 enterprise intake; it is not a new source of installable pins. Release API metadata can change: this document records a point-in-time observation as of 2026-10-31.

## Read-only command

From the PortaKit repository root, with Python 3.11+:

```cmd
rem Review all three candidates, without internet/vendor execution or file writes.
python -I scripts/lightweight_review.py

rem Narrow scope.
python -I scripts/lightweight_review.py --id duckdb-cli
python -I scripts/lightweight_review.py --id xsv --id tailviewer

rem Optional operator-local NEW JSON plus byte-mirrored console transcript.
python -I scripts/lightweight_review.py --out D:\LocalEvidence\Candidates.json
```

The command **always returns exit code 2** for valid research-only candidates; this is a deliberate *not-admitted* result, not a failed installation. Input/schema problems or existing output paths return 1. It never returns an install approval code 0. The optional `--out` refuses to overwrite either JSON or its same-basename `.log`; default is no-write. Do not put real company endpoint names, internal original ZIP paths, credentials, data, logs or review evidence in this PUBLIC repository.

The eight independent missing gates are: locally hash-verified vendor original, extracted logical bytes, Windows offline smoke, synthetic function smoke, enterprise-use license, redistribution/transfer authorization, EDR/security authorization and first-run side-effect review. The tool reports these as **outstanding regardless of official release metadata**. A published GitHub SHA does not mean PortaKit has downloaded or verified those bytes.

## Candidate comparison (source metadata only)

| ID | Official release / Windows asset | Compressed bytes from GitHub | GitHub API SHA-256 | Findings / next action |
| --- | --- | ---: | --- | --- |
| `duckdb-cli` | [DuckDB v2.0.0](https://github.com/duckdb/duckdb/releases/tag/v2.0.0), `duckdb-cli-windows-amd64.tar.gz` | 19,663,611 | published; in ledger | **P1 follow-up.** Official 2026-10-21 x64 asset; existing PortaKit core handles only `zip`, `exe`, `sfx7z`, NOT `tar.gz`. Do not mislabel it as ZIP or implement shell extraction without bounded traversal/link/size guards. Windows VC++ Redistributable required. |
| `xsv` | [xsv 0.13.0](https://github.com/BurntSushi/xsv/releases/tag/0.13.0), `xsv-0.13.0-x86_64-pc-windows-msvc.zip` | 792,499 | **not provided** for this old asset in GitHub API | **Deprioritize.** Upstream [archived 2025-04-24](https://github.com/BurntSushi/xsv), author now recommends qsv or xan. Compare with currently pinned Miller before considering a substitute, and measure BOM/UTF-16, malformed records and big CSV. |
| `tailviewer` | [Tailviewer v1.0.0-rc1](https://github.com/Kittyfisto/Tailviewer/releases/tag/v1.0.0-rc1), `Tailviewer-portable-1.0.0.39.zip` | 3,786,701 | **not provided** for this asset in GitHub API | **Conditional.** Official portable ZIP from 2022; reported .NET Framework 4.7.1+ dependency, not yet installed/tested. Human test multiline, UTF-16, multi-file timestamp sorting, memory, config writes and EDR. |

The upstream project metadata reports MIT for DuckDB and Tailviewer, and MIT/Unlicense options for xsv. These are **project-level license labels**, not a review of bundled dependencies, required notices, corporate-use conditions, EDR policy or separate redistribution/transfer rights. No additional SHA, signature, dependency, actual logical footprint or vendor binary smoke is claimed.

### DuckDB extension and filesystem safety

DuckDB's CLI can read local files and load/install extensions depending on configuration. Official [securing guide](https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview) and [safe-mode documentation](https://duckdb.org/docs/current/clients/cli/safe_mode) distinguish two different test lanes:

1. **Restricted in-memory SQL:** use CLI safe mode or explicit disabling of external access/extensions, without attempting CSV/Parquet file reads that safe mode intentionally blocks.
2. **Approved local CSV/Parquet performance:** on a nonproduction machine, use dedicated synthetic directories and explicit allowed paths, disable unapproved extensions/autoinstall/autoload, record CPU/RAM/disk and unexpected network effects. Do not assume a generic untrusted SQL string is safe.

No scripts in PortaKit download the vendor release, install extensions, start a server or run either lane. A green synthetic source-only unit test does not replace a real asset hash or workstation smoke.

## Independent next decision

- DuckDB: separately decide whether bounded `tar.gz` support is justified, or use an independently immutable, separately validated approved ZIP for a selected version; never rename a tarball to ZIP. Compare a minimal `zip` approach against expanding the core extractor's attack surface.
- xsv: investigate maintained qsv/xan as separate research IDs **only if** they outperform the existing pinned Miller for actual operator workflows. Do not silently transfer xsv's license or SHA assertions to a fork.
- Tailviewer: verify ZIP archive bytes locally before deriving SHA, compatibility of .NET prerequisites, and actual portable profile/user settings. Test ordered multi-file logs with synthetic timestamps and corrupted encodings on authorized interactive Windows.

Only after source provenance, actual SHA, dependencies, legal policy, EDR, size and functional evidence can a **separate reviewed PR** promote a single item. Existing `research/INTAKE_ENTERPRISE_PORTABLE_20261025.json`, `catalog.json`, `toolsets.json`, `scripts/my_toolkit.py`, installer and Release gates remain unchanged.

**NO PRODUCTION MES/PLC CONNECTIONS OR NEW DEFAULT NETWORK LISTENERS.**
