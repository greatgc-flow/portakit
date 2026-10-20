# Optional toolsets — generic MECE primary taxonomy and composable work profiles

**2026-10-20 — schema v2.** This is a **Windows x64 air-gapped corporate** tool selection, intentionally not a platform/industry-specific scheme. It separates **what software fundamentally does** from **which task/role combines it**, and from **how it is packaged or approved**.

## Three independent axes (MECE within each axis, intentionally many-to-many across axes)

1. **Primary functional domain** (exclusive): each installable catalog ID has exactly one domain. This is validated at load time: missing or repeated assignments fail before any download. Research candidates use the same one-primary-domain taxonomy in [107-tool inventory](../research/TOOLS_CANDIDATES_20261020.json).
2. **Work profile** (composable): user-purpose and optional profile IDs can span many domains. A tool can appear in many profiles, but resolution deduplicates by its unique pinned tool ID; no repeated download. No business-only category or hard-coded industry.
3. **Deployment and risk** (orthogonal): pinned download versus built-in versus research-only, exact archive bytes only when attested, license evidence, offline driver/elevation/active-network/cloud/PII risk. Small/portable is NOT the same as safe, legally redistributable or approved.

## 10 mutually exclusive primary domains

| Canonical ID | Coverage | Current SHA-pinned IDs |
| --- | --- | --- |
| `files` | File location, navigation, diff, archive, storage | `winmerge`, `fd`, `fzf` |
| `text` | Text editing, log finding/reading, string transformation | `notepad++`, `ripgrep`, `bat`, `sd` |
| `structured-data` | JSON/YAML/XML/CSV/DB manipulation | `jq`, `yq` |
| `system` | OS process, performance, memory and event diagnostics | Empty until pin admission |
| `network` | Connection, latency, protocol and packet diagnostics | Empty until pin admission |
| `security` | Software signatures, digests, permissions and encryption | Empty until pin admission |
| `development` | Versioning, compilers, runtimes and developer inspections | `delta` |
| `automation` | Repeatable operations and command benchmarking | `hyperfine` |
| `documents` | PDF/images/screenshots and report review | Empty until pin admission |
| `transfer` | Approved file transport and remote terminal | Empty until pin admission |

**Taxonomy is a primary owner, not a claim of only one use.** A JSON viewer may also help development, but `structured-data` remains its primary category; an incident-response profile may select it. See [research inventory](../research/TOOLS_CANDIDATES_20261020.json) for **107 unique items: 11 pinned, 27 OS built-ins/optional built-ins, 69 research-only** (no runtime installation permissions implied).

## Generic profiles (optional; no default installation)

| Profile | Purpose | Behaviour |
| --- | --- | --- |
| `essentials` | Small minimum everyday set | Notepad++, WinMerge, jq |
| `lightweight` | **Compact CLI productivity add-ons** | ripgrep, fd, fzf, bat, sd, yq, delta, hyperfine |
| `workstation` | Text + files + data without unnecessary apps | 7 approved pins |
| `incident-response` | Restricted-network troubleshooting | Currently 8 pinned tools; OS/NW/Security candidate tools are **not** installed |
| `engineering` | Version control, text, data, file tools, command automation | Category union, deduplicated |
| `data-work` | Structured data + text workflows | Category union |
| `all-curated` | All 11 actually pinned programs | Category union |
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
- **Research is not installation:** [107 candidate register](../research/TOOLS_CANDIDATES_20261020.json) includes Windows built-ins and conditional Sysinternals/Wireshark items. Programs without pinned release URL+digest are excluded from catalog. Company's OSS/EDR/license approval remains mandatory for all.
- For Microsoft Sysinternals, free commercial *use* does not imply general third-party redistribution; [licensing FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq). For Wireshark, live Windows capture may require Npcap driver with [independent commercial-use conditions](https://npcap.com/oem/internal). Do not run active network tests on production equipment without explicit target/time/cadence approval.
- Windows CI must validate catalog hashes, exact-one primary domains, frozen legacy selection, idempotence/empty-plan/unknown-ID failures and **real ZIP download → SHA-256 → extraction → version** for the new pinned subset. Offline client end-to-end approval remains separate from CI.

For 30 historically assessed desktop-oriented tools see [corporate closed-network TOP 30](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md). For future release gates see [BACKLOG](BACKLOG.md) and [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md).
