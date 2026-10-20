# Optional toolsets (Common / OS / NW / Dev / Data / Diagnostics)

**Research reference (not installed):** [2026-10-20 corporate air-gapped free-software TOP 30](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md). Includes business-use license/EULA, ZIP/portable feasibility, Windows privilege and driver risks, and role-based rollout gates. The current pinned catalog remains limited to 3 tools.


**Architecture:** `catalog.json` owns the actual pinned downloads, versions, SHA-256 digests and installation semantics. `toolsets.json` is a **pure selection manifest**: it never holds URLs, commands, installers, or permission to modify Windows. A tool can appear in several categories without being downloaded twice. A profile composes categories and the result is a stable, deduplicated list.

## Current catalogue and category mapping

| Category | Verified, actually installable IDs | Future additions (not installed) |
| --- | --- | --- |
| `common` — shared | `notepad++`, `winmerge` | 7-Zip, Everything portable |
| `os` — files/Windows | `winmerge` | Process Explorer, Process Monitor, Autoruns |
| `nw` — network | *(none yet)* | Microsoft TCPView, PsPing; packet-capable capture tools reviewed separately |
| `dev` — development | `notepad++`, `jq` | ripgrep, VS Code portable if worth complexity |
| `data` — JSON/logs | `jq` | additional format parsers only with real demand |
| `diag` — troubleshooting | `winmerge`, `jq` | ProcDump, TCPView, Process Explorer |

These categories represent **purposes**, not disjoint application ownership; multiple memberships are intentional. The resolver deduplicates by the single catalog tool ID. A category with zero verified tools is **empty and cannot install a placeholder**. New tools require explicit catalog pin/SHA review, security/dependency/license analysis and Windows acceptance; a label is not an authorization to download it.

Four composed profiles are supplied: `minimal` (Common), `mes-support` (Common + OS + NW + Data + Diagnostics), `developer` (Common + Dev + Data), and `all-curated` (every currently verified category).

## Usage

From the repository root on Windows with Python 3.11+:

```powershell
# Read-only; do not download or write to Windows, the registry or portable/.
python -I scripts/toolsets.py list
python -I scripts/toolsets.py plan mes-support
python -I scripts/toolsets.py plan common nw --include jq --exclude winmerge
python -I scripts/toolsets.py plan developer --root "D:\PortableTools"

# Explicit installation after reviewing the plan.
# Existing exact-pin managed tools are skipped; never updated/reconfigured.
python -I scripts/toolsets.py apply mes-support --yes
python -I scripts/toolsets.py apply developer --yes --recommended
python -I scripts/toolsets.py apply os nw --yes --root "D:\PortableTools"

# Equivalent double-click-friendly command-line entrypoint:
.\scripts\Toolsets.cmd list
.\scripts\Toolsets.cmd plan mes-support
.\scripts\Toolsets.cmd apply mes-support --yes
```

**Safety contract**

- **No default side effects**: ordinary PortaKit `install/update/configure/remove` continue working unchanged; merely adding toolsets.json never installs anything. `list` and `plan` are completely read-only, including no log/lock/directory creation.
- **Explicit consent**: `apply` refuses without `--yes`. Download/install is delegated to the existing Windows-only PortaKit core, with its pinned HTTPS URL, SHA-256 verification, path protections, atomic per-tool staging and root lock. Toolset manifests cannot add arbitrary URLs or shell commands.
- **Optional recommended profiles**: `--recommended` on `apply` affects **new installs only** and uses the existing pinned editor plugin rules; it never edits existing editor settings. Installing a category does not implicitly install Explorer right-click integration.
- **Idempotence**: an exact-pin managed app is skipped with no downloads or mutation. Stale pin, unmanaged path, broken/missing managed directory, backup remnants, or reparse/junction cause a blocked plan; `apply` refuses the whole selection until fixed. No silent update/downgrade/remove.
- **Selection control**: choose one or more categories/profiles, add individual pinned tools through `--include ID`, and remove IDs using `--exclude ID`. The empty NW group presently reports zero tools and does not install anything.
- **Failure isolation**: a profile is **not one atomic multi-tool transaction**. On a failure, processing stops; previously installed tools remain, and you can rerun safely. Do not automatically remove user data as rollback. A separate batch lock serializes other toolset runs; the PortaKit core keeps its own per-tool lock.
- **Evidence**: an `apply` with tools creates a unique `ROOT\.portakit-evidence\toolsets-*.log`, capturing the **same console lines** (including child CLI stdout/stderr). Optional `--log-file PATH` must not already exist. No external upload.
- **Custom categories**: edit a copy of `toolsets.json` and use `--manifest PATH`. IDs must exist in the validated core catalog; the manifest contains no executable downloads or registry settings. The default curated manifest is versioned in Git.
- **Uninstall**: intentionally excluded from group operations because `portakit.py remove ID` destroys managed app data. Remove only individually, and unregister any optional Explorer menu before moving/removing its app.

## Review of future candidate tools

- **NW first:** Microsoft [TCPView](https://learn.microsoft.com/en-us/sysinternals/downloads/tcpview) (TCP/UDP endpoints and owning processes) and [PsPing](https://learn.microsoft.com/en-us/sysinternals/downloads/psping) (ICMP, TCP connection latency/bandwidth). They are useful for application/OS/Network boundary diagnosis. Defer installation until exact individual artifact versions and SHA256 can be independently verified.
- **OS:** Microsoft [Sysinternals Suite](https://learn.microsoft.com/en-us/sysinternals/downloads/sysinternals-suite) includes Process Explorer, Process Monitor and TCPView, but the full 192 MB suite exceeds PortaKit's current **100 MiB download cap**. Favor individually verified smaller binaries, or separately review whether to raise the cap rather than silently bypass it.
- **Common:** [Everything portable ZIP](https://voidtools.com/support/everything/installing_everything/) supports portable execution without a conventional installer; evaluate file indexing and privilege implications before adding a catalog pin.
- **Packet capture:** [Wireshark for Windows](https://www.wireshark.org/docs/wsug_html_chunked/ChBuildInstallWinInstall.html) uses **Npcap** for live capture, which is a driver/system prerequisite, not a pure portable operation. Do not silently install a driver on production equipment or MES servers. Offline capture-file analysis is a separate candidate.
- **Production caution:** tools that can change or terminate network connections (e.g., TCPView Close Connections), deploy drivers, scan systems, or write Windows settings must be opt-in with permissions and impact recorded. PortaKit installs files only; it does not initiate scans or capture traffic.

## Next quality gates

1. Complete Windows CI with synthetic manifest tests, no-network plan, blocked/partial apply recovery, idempotent selector and full evidence output.
2. Review each new candidate: usage, licensing, privilege/driver requirements, official immutable URL + SHA256, archive structure, end-user launch validation.
3. Do not imply that an unpinned item shown under "future additions" was installed or has been fully verified.
