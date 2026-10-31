# Optional toolsets — generic MECE primary taxonomy and composable work profiles

> **Current state 2026-10-30:** 19 SHA-pinned installable tools in the current catalog, with 151 selectable software entries overall (19 pinned / 27 OS built-ins / 105 research-only), plus six independently selectable editor-plugin metadata options. See the [2026-10-22 handoff and evidence map](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md). Historical phase-specific counts below are not current catalog totals.

**2026-10-20 — schema v2.** This is a **Windows x64 air-gapped corporate** tool selection, intentionally not a platform/industry-specific scheme. It separates **what software fundamentally does** from **which task/role combines it**, and from **how it is packaged or approved**.

## Bounded core child execution — 2026-11-01

An explicitly consented `apply --yes` now invokes **only PortaKit's own `portakit.py --json install ID`** via an argument array (`shell=False`). For optional `--log-file FILE`, a mutating toolset run accepts evidence only **outside `--root`** or under `ROOT/.portakit-evidence/`, where default logs are already placed. Other in-root paths are rejected before creating the root, locking it or running installers: managed tool folders, `.old` backups and cleanup temp folders may be moved/deleted during the batch. The evidence directory may be created by the existing opt-in toolset logger; files remain exclusive-create and cannot overwrite prior evidence. This preflight reuses the core CLI location validator rather than inventing a second policy. The immediate child has **600 seconds per install** by default, with an optional `--child-timeout SECONDS` (1–3600) for slow/offline equipment. Its stdout and stderr are drained **concurrently** and held to **256 KiB per stream**; exceeding the cap terminates the direct child and records `OUTPUT_LIMIT`. A stalled child records `TIMEOUT`. Launch/read failure is a separate failed status. On any failure, the batch stops at that tool; previously installed items remain managed rather than silently rolled back.

```cmd
:: Source-only planning, no vendor process or download
python -I scripts/toolsets.py plan minimal --root D:\PortableApps

:: Existing opt-in install flow, configurable per-child runtime limit
python -I scripts/toolsets.py apply minimal --root D:\PortableApps --yes --child-timeout 900
```

**Bounds are not an OS sandbox.** The direct child is killed on overflow or timeout; descendants that independently inherit handles may survive. CPU, RAM, network and disk writes by authorized installer code are not sandboxed, and the 256 KiB bounds apply to captured text rather than all child allocations. Run only after the **final user/organization** approves the target environment and tool licenses, and do not connect to live manufacturing equipment as part of synthetic tests. The child JSON success result must be valid, unique-key strict JSON with `ok: true`, matching `command/id` and no error object; invalid, contradictory or truncated output is a failed install result. The console-to-local evidence log reports the selected timeout and output cap and stops on the first failing item.

This is a **source-level reliability improvement**; no vendor binaries are executed by CI. It does not change default approved pins, existing v1/v2 toolset selection, EULA/EDR checks or the separate final-user approval boundary in [END_USER_ACCEPTANCE.md](END_USER_ACCEPTANCE.md).

## Three independent axes (MECE within each axis, intentionally many-to-many across axes)

1. **Primary functional domain** (exclusive): each installable catalog ID has exactly one domain. This is validated at load time: missing or repeated assignments fail before any download. Research candidates use the same one-primary-domain taxonomy in [108-tool inventory](../research/TOOLS_CANDIDATES_20261020.json).
2. **Work profile** (composable): user-purpose and optional profile IDs can span many domains. A tool can appear in many profiles, but resolution deduplicates by its unique pinned tool ID; no repeated download. No business-only category or hard-coded industry.
3. **Deployment and risk** (orthogonal): pinned download versus built-in versus research-only, exact archive bytes only when attested, license evidence, offline driver/elevation/active-network/cloud/PII risk. Small/portable is NOT the same as safe, legally redistributable or approved.

## 10 mutually exclusive primary domains

| Canonical ID | Coverage | Current SHA-pinned IDs |
| --- | --- | --- |
| `files` | File location, navigation, diff, archive, storage | `winmerge`, `fd`, `fzf`, `7zr`, `everything`, `7zip` |
| `text` | Text editing, log finding/reading, string transformation | `notepad++`, `ripgrep`, `bat`, `sd`, `grepwin` |
| `structured-data` | JSON/YAML/XML/CSV/DB manipulation | `jq`, `yq`, `miller`, `dasel` |
| `system` | OS process, performance, memory and event diagnostics | Empty until pin admission |
| `network` | Connection, latency, protocol and packet diagnostics | `tcpview`, `psping` (direct vendor source, separate legal gate) |
| `security` | Software signatures, digests, permissions and encryption | Empty until pin admission |
| `development` | Versioning, compilers, runtimes and developer inspections | `delta` |
| `automation` | Repeatable operations and command benchmarking | `hyperfine` |
| `documents` | PDF/images/screenshots and report review | Empty until pin admission |
| `transfer` | Approved file transport and remote terminal | Empty until pin admission |

**Taxonomy is a primary owner, not a claim of only one use.** A JSON viewer may also help development, but `structured-data` remains its primary category; an incident-response profile may select it. See [research inventory](../research/TOOLS_CANDIDATES_20261020.json) for **108 unique items: 19 pinned, 27 OS built-ins/optional built-ins, 62 research-only** (no runtime installation permissions implied).

## Generic profiles (optional; no default installation)

| Profile | Purpose | Behaviour |
| --- | --- | --- |
| `essentials` | Small minimum everyday set | Notepad++, WinMerge, jq |
| `lightweight` | **Compact CLI productivity add-ons** | ripgrep, fd, fzf, bat, sd, yq, delta, hyperfine |
| `workstation` | Text + files + data without unnecessary apps | 7 approved pins |
| `incident-response` | Restricted-network troubleshooting | Current category+direct composition selects 10 pins, including optional `tcpview` and `psping` (legal/active-probe gates remain) |
| `engineering` | Version control, text, data, file tools, command automation | Category union, deduplicated |
| `data-work` | Structured data + text workflows | Category union |
| `all-curated` | All 19 currently pinned programs | Category union |
| `minimal`, `mes-support`, `developer` | Historical profiles | Frozen original results for compatibility, not promoted as canonical new names |

**Legacy selectors:** `common` → Npp/WinMerge, `os` → WinMerge, `nw` → empty, `dev` → Npp/jq, `data` → jq, `diag` → WinMerge/jq. These are kept as **frozen aliases**, listed separately, not counted as new MECE categories. Existing scripts and scenarios keep their exact scope. New scripts should use the canonical category/profile names.

## Pinned ultra-small candidates admitted to catalog

The following sizes are **published GitHub Release asset compressed ZIP byte lengths**, confirmed with the official release's SHA-256 `digest` field. These are NOT uncompressed install sizes and they do not prove successful offline execution: a Windows runner's actual download/extraction/version smoke is the independent gate.

| Tool | Version | Official ZIP size | License (repository metadata) | Value |
| --- | --- | ---: | --- | --- |
| [hyperfine](https://github.com/sharkdp/hyperfine) | 2.0.0 | 632,670 B | Apache-2.0 | Repeatable command-time comparison |
| [sd](https://github.com/chmln/sd) | 1.1.0 | 888,027 B | MIT | Regex substitution |
| [fd](https://github.com/sharkdp/fd) | 10.5.0 | 1,535,063 B | Apache-2.0 | Fast files/paths |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | 15.2.0 | 1,789,611 B | MIT/Unlicense | Fast recursive log regex |
| [fzf](https://github.com/junegunn/fzf) | 0.74.5 | 2,544,236 B | MIT | Interactive fuzzy filtering |
| [delta](https://github.com/dandavison/delta) | 0.20.1 | 3,450,186 B | MIT | Readable Git diff |
| [bat](https://github.com/sharkdp/bat) | 0.26.1 | 3,613,318 B | Apache-2.0 | Source/log previews |
| [yq](https://github.com/mikefarah/yq) | 4.54.1 | 5,829,372 B | MIT | YAML/JSON/XML config |
| **All eight** | | **20,282,483 B (~19.34 MiB)** | | All eight combined compressed; each individually SHA-pinned |

**Management model:** base catalog still retains Notepad++ / WinMerge / jq pinned original versions; 8 additions are independent opt-in IDs. Install only after preview. No auto-update, no right-click menu registration, no plugin preference change by a toolset.

## Usage from the repository root

```powershell
# Read-only, no downloads, no directory/lock/log creation:
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan essentials
.\scripts\Toolsets.cmd plan lightweight
.\scripts\Toolsets.cmd plan incident-response
.\scripts\Toolsets.cmd plan files network --exclude winmerge
.\scripts\Toolsets.cmd plan lightweight --root "D:\Portable"

# Download *only* approved pinned programs, after explicit acknowledgement:
.\scripts\Toolsets.cmd apply lightweight --yes
.\scripts\Toolsets.cmd apply workstation --yes --recommended
# One-tool override, requires pinned catalog ID:
.\scripts\Toolsets.cmd plan essentials --include hyperfine --exclude jq

# Older commands still work with the same selections as before:
.\scripts\Toolsets.cmd plan mes-support
.\scripts\Toolsets.cmd plan nw
```

The config is versioned `toolsets.json`. `scripts/toolsets.py` remains standard-library-only Python 3.11+ on Windows; `scripts/Toolsets.cmd` wraps it. V1 user-supplied manifests remain supported; V2 requires `classification` and exactly one primary group per pinned tool. Profiles may select categories and/or direct pins; aliases cannot collide with category/profile IDs.

## No-side-effects and release gates

- Core `portakit.py install|configure|update|remove` is untouched. `list`/`plan` are read-only; `apply` needs `--yes`, uses a batch lock and invokes existing per-tool SHA-256 protected installer. Existing exact-pin installs are skipped, stale/unmanaged/backup/reparse paths block the group.
- The batch is **not globally transactional**. A failure stops new installs but retains earlier successful ones, with full console-mirrored local evidence logs. No automatic registry PATH, drivers, packet capture, telemetry or uploads.
- **Research is not installation:** [108 candidate register](../research/TOOLS_CANDIDATES_20261020.json) includes Windows built-ins and conditional Sysinternals/Wireshark items. Programs without pinned release URL+digest are excluded from catalog. Company's OSS/EDR/license approval remains mandatory for all.
- For Microsoft Sysinternals, free commercial *use* does not imply general third-party redistribution; [licensing FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq). For Wireshark, live Windows capture may require Npcap driver with [independent commercial-use conditions](https://npcap.com/oem/internal). Do not run active network tests on production equipment without explicit target/time/cadence approval.
- Windows CI must validate catalog hashes, exact-one primary domains, frozen legacy selection, idempotence/empty-plan/unknown-ID failures and **real ZIP download → SHA-256 → extraction → version** for the new pinned subset. Offline client end-to-end approval remains separate from CI.

For 30 historically assessed desktop-oriented tools see [corporate closed-network TOP 30](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md). For future release gates see [BACKLOG](BACKLOG.md) and [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md).

### Upstream sd embedded-version discrepancy (not hidden)

During the genuine Windows x64 CI run, the official GitHub **sd v1.1.0 ZIP** (pinned archive SHA-256 `59837c2e...`) executed successfully, but `sd.exe --version` printed **sd 1.0.0**. This is **not** evidence that the binary belongs to a different download—the archive digest matched the recorded vendor release—but it does mean self-reported version parity is unproven. The Windows CI explicitly checks `1.0.0` for this particular pinned artifact and warns on the mismatch; all 7 other new tools must match their released version. Investigate vendor packaging before calling the embedded version verified or upgrading this pin.

**Status review 2026-10-30 (docs only, no pin change):**
- **Fact (repo):** `catalog.json` pins `v1.1.0` `sd-v1.1.0-x86_64-pc-windows-msvc.zip` with SHA-256 `59837c2e…71007c`; `live-windows-smoke.yml` expects `1.0.0` and emits a warning, not a pass.
- **Fact (verified 2026-10-30 via `gh release view v1.1.0 -R chmln/sd`):** the upstream asset digest equals the pinned SHA-256. Still unverified: the `Cargo.toml` version at tag `v1.1.0`.
- **Inference (not established):** the 1.0.0 string may come from an unbumped version in upstream source/packaging. Confirm the tag's `Cargo.toml`, then either file an upstream issue or keep the documented exception.

## Phase 2 — 2026-10-21 small verified pins and true disconnected installation

**Five fixed-version packages** appended without changing the original 11 pins. At that historical phase directly installable IDs = **16**. After full 7-Zip admission (2026-10-21): **17 pinned**. Research register = **108 unique entries (17 pinned / 27 Windows built-ins / 64 research-only)**.

| Tool | Official vendor asset and size metadata | Pinned SHA provenance | Practical guardrail |
| --- | --- | --- | --- |
| [7zr](https://github.com/ip7z/7zip/releases/download/26.04/7zr.exe) | standalone 7zr.exe ~603 KB | Official GitHub release `digest` | **7z format only**; not full GUI 7-Zip or ZIP support. Use `7zr` as compact .7z reader |
| [Everything](https://www.voidtools.com/downloads/) | 1.4.1.1032 x64 ZIP ~1.86 MB | Scoop Extras maintained manifest points to exact official vendor ZIP and SHA; validated by real Windows download/hash gate | **Installation only**. Starting GUI can request UAC, create service/index, reveal indexed filenames to other local users; no service or indexing enabled by PortaKit |
| [grepWin](https://github.com/stefankueng/grepWin/releases/tag/2.1.12) | x64 portable ZIP 691,960 B | Official GitHub release `digest` | GUI executable presence/PE only in hosted CI, not click/interactive acceptance; replace mode can modify documents |
| [Miller](https://github.com/johnkerl/miller/releases/tag/v6.22.0) | windows-amd64 ZIP 6,227,745 B | Official GitHub release `digest` | CSV/TSV/JSON CLI, `mlr.exe --version` verified on hosted Windows |
| [dasel](https://github.com/TomWright/dasel/releases/tag/v3.11.2) | windows-amd64 EXE 10,756,608 B | Official GitHub release `digest` | JSON/YAML/XML/TOML/CSV operations; CLI `--version` verified on hosted Windows |

**Offline mode:**

```powershell
# On a connected, company-approved staging PC: collect exact original assets,
# record official download URL and SHA, scan them, and copy unchanged to D:\Approved.

# On a CLOSED-NETWORK company PC (Internet not required):
python -I portakit.py --archive "D:\Approved\dasel_windows_amd64.exe" install dasel
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan portable-productivity
.\scripts\Toolsets.cmd apply portable-productivity --yes --offline-dir "D:\Approved"

# One-time file integrity is automatically validated for each missing pin.
# Already installed exact versions are skipped; no auto-updates or user data deletion.
```

For a group of missing tools, `--offline-dir` expects the **original URL basename** of each pinned vendor archive in the local folder; it preflights all required hashes **before** starting any installation, then delegates to the ordinary atomic per-tool stage pipeline with another SHA verification. **No Internet is used in the installation phase.** File files with incorrect digest, wrong name, missing entries, symlinks, oversize binaries or unapproved ID fail closed. The source archive remains untouched. The local evidence log still mirrors console lines from installation; early preflight failures print errors without a full batch log (follow-up hardening candidate).

`--archive` is supported for the core `install` and `update` verbs, never for `list/configure/remove`. `--recommended` cannot be combined with `--archive` and group `--offline-dir` because Notepad++ optional plugin assets are separate downloads; no hidden network fallback. **No default menu/registry, PATH or Windows services changes.** For Everything only, subsequent *human GUI launch* needs special review: manual folder indexing can avoid installing the NTFS service but uses different performance characteristics; never default to service/HTTP/FTP features.

**Update 2026-10-21:** Full official 7-Zip GUI is now installed as a separate **optional** `7zip` ID using the verified upstream x64 SFX *without executing the installer*. Its `7zFM.exe` was statically checked; interactive GUI acceptance is still outstanding. 7zr.exe only supports 7z archives. Microsoft Sysinternals and packet capture drivers remain separate permissions and license review items. Release gate includes Windows CI and company workstation manual acceptance, not publication automatically.

## 2026-10-21 full official 7-Zip opt-in admission

- **Official x64 vendor asset:** `https://github.com/ip7z/7zip/releases/download/26.04/7z2604-x64.exe`, **1,664,082 bytes**, vendor-published SHA-256 `d54bf805f9f3704d1e8db2fa3498ae7ef2df0312b40b558e7c71c734430a665d`.
- **Proven from real Windows inspection:** file is a self-extracting 7z archive with 107 entries (~5.92 MB unpacked), includes `7zFM.exe`, `7zG.exe`, `7z.exe`, `7z.dll` and `License.txt`. **Never launch this executable**; only `7zr.exe l -slt` and `7zr.exe x` read its archive DATA.
- **Prerequisite:** a separately PortaKit-managed `7zr` 26.04 with exact *state pin and executable SHA-256*; reject missing, modified or downgraded prereq **before downloading** installer. `portable-productivity` profile and `files` primary domain order `7zr` before `7zip`. Installing `7zip` as a single tool without `7zr` must fail closed.
- **Extraction safety:** only pinned `id=7zip` may use artifact type `sfx7z`; parse listing and limit 512 members / 64 MiB expanded data; reject traversal, absolute/ADS/device names, path collisions, links/reparse, encryption and special types. After extraction recursively verify every exact declared file size and type, then use original atomic move/rollback. No EXE installer or `Uninstall.exe` is executed.
- **Run:** `python -I portakit.py install 7zr`, then `python -I portakit.py install 7zip`. For offline imports, pass the two exact original assets through `--archive` or select the approved `portable-productivity` profile with `--offline-dir`.
- **GUI acceptance caveat:** existence/PE verification of `7zFM.exe` is NOT evidence of interactive GUI success. Hosted Windows CI additionally exercises **full 7z.exe ZIP create/test** (7zr-only is different), no actual user-window UI, no registry or service changes. User workstation manual review remains a release gate.
- **Status:** catalog **17 pinned**, research ledger **108 unique (17 pinned, 27 Windows built-ins, 64 research-only)**. Complete desktop 7-Zip replaces the old *research candidate*, while small 7zr remains a separate lightweight program.
