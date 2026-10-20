# PortaKit backlog (prioritized, evidence-based)

The [corporate/offline 30-software survey](RESEARCH_CORPORATE_OFFLINE_FREE_TOP30_20261020.md) identifies **research-only** candidates and per-vendor redistribution gates. Do not silently add them to installable catalog or republish proprietary vendor binaries.


The items below are **not implemented/certified** merely by their appearance in this document. Keep explicit consent for side effects, and maintain minimal vendor defaults where a configuration change offers no verified benefit.

| Priority | Area | Task | Gate / next action | State |
| --- | --- | --- | --- | --- |
| P1 | WinMerge Office 4 | Execute **real** Excel, Word, PowerPoint and Visio document comparisons on a licensed, interactive Windows PC; inspect Explorer/WinMerge GUI plugin selection, SaveAs variants and evidence ZIP results; review `--require-pass` on the resulting archive | All four real Office app comparisons and human GUI check. No false PASS from absent COM | **BLOCKED — licensed Office desktop / actual evidence not provided** |
| P2 | WinMerge Explorer integration | Advanced two-selection Compare / Compare To via vendor WinMerge shell extension, including Windows 11 native menu. Current lightweight classic menu only opens a selected file/folder and WinMerge can prompt for the other target | Upstream shell-extension compatibility/security testing and reversible installer, admin/COM approval if needed | Backlog (optional, do not default) |
| P2 | Notepad++ Explorer integration | Windows 11 **modern** primary context menu, as opposed to the classic per-user registry action shipped by PortaKit | Verify NppShell signed COM/sparse package deployment and admin permissions; no registry hijacks | Backlog (optional) |
| P2 | Shell-menu lifecycle | Detect/report stale registered shell links when a managed application is moved/removed. Do not silently remove global/user shell keys during a regular PortaKit remove command | Cross-command UX tests and consent contract | Backlog |
| P3 | Catalog pins | Periodically review new upstream versions of Notepad++, WinMerge and jq, plugin compatibility and verified hashes. Don't silently use 'latest' or change an approved pin | Explicit reviewed pin update PR with SHA evidence and Windows live tests | Backlog |
| P3 | Performance | Optional offline cache, bundle portability, and CLI JSON status for diagnostics if justified by user demand | Add only with tests / no behavioral regression | Deferred |

## Release scope and evidence boundary

- Existing WinMerge Office vendor plugin file checks, automatic plugin settings, real plain text comparison, prereq-only COM tests and ZIP SHA evidence have passed on hosted Windows CI. That **does not mean Excel/Word/PowerPoint/Visio GUI comparisons passed**.
- Do not publish a GitHub Release claiming Office compatibility until the P1 gate is satisfied.
- The classic Explorer menus are an **explicit current-user opt-in**; the two-argument vendor ShellExtension behavior is intentionally not represented as implemented.

## Category toolset roadmap (P2, optional)

- **Common**: evaluate 7-Zip and Everything stable portable ZIP; pin exact official assets, SHA, verify extraction, license and indexing/privilege behavior before adding to `catalog.json`.
- **OS**: Process Explorer, Process Monitor, Autoruns candidates; avoid full Sysinternals Suite until >100 MiB download cap and bundle policy reviewed.
- **NW**: prioritize TCPView and PsPing, then evaluate protocols/packet-capture viewers. Test non-elevated operation and explicit optional elevation where required; no automatic packet capture or network probing. Wireshark live capture requires Npcap (driver) and is **not** a pure portable/no-side-effect default.
- **Dev/Data/Diagnostics**: reuse existing verified Notepad++ / WinMerge / jq until new tool delivers a clear benefit. Ripgrep and format analyzers are optional candidates, not promised installations.
- **Governance**: add one candidate at a time, with official provenance, immutable version and SHA, EULA/licensing, safety classification, CI acceptance, and optional membership of any number of categories. Never treat a plan selection as consent for new drivers/services/system-wide changes.

Details and official reference links: [TOOLSETS](TOOLSETS.md).

## MECE small-first candidate admission (2026-10-20)

- [107 unique screened research entries](../research/TOOLS_CANDIDATES_20261020.json) are categorized once by primary purpose. **11 are SHA-pinned**, **27 are existing/optional Windows built-ins**, **69 are research-only**. The candidate register is not an install authorization and does not certify all free-use or redistribution claims.
- **Accepted small-first pins for live CI:** ripgrep, fd, fzf, bat, sd, yq, delta and hyperfine; release metadata SHA-256 + compressed sizes are recorded in the immutable `catalog.json` and `TOOLSETS.md`. Gate: real Windows download/hash/extract/`--version` smoke and reapply no-op. No auto-update.
- **Next P0 research admission:** 7-Zip, Everything portable, compact log viewers (klogg/grepWin), dasel/Miller/SQLite tools; compare incremental practical value against built-ins and already pinned tools.
- **Network/OS conditional:** Microsoft Sysinternals licensing permits company use but restricts redistribution; no unrestricted vendor binary bundling. Prioritize metadata-only sourcing, IT approval, safe non-privileged observation. Wireshark Npcap and live network/packet testing are elevated/change-impact opt-ins.
- **Footprint honesty:** unknown compressed sizes are `null`, not treated as small; exact official bytes only for 8 newly pinned assets. Capture installed disk footprint (all DLL/doc files), prerequisites, first-launch writes, network activity, built-in alternatives, license notice, runtime compatibility and rollback before future admission.
- **Legacy names:** keep `common/os/nw/dev/data/diag` as backward compatible frozen selectors, not primary categories. `minimal/mes-support/developer` preserved as profile names. Future releases should use `files/text/structured-data/system/network/security/development/automation/documents/transfer`.

- **P1 sd upstream version anomaly:** Official v1.1.0 Windows ZIP at pinned SHA executes but `sd --version` prints 1.0.0 on Windows CI. Record explicit warning/exception (no hidden PASS as same version), compare vendor build metadata/source, open upstream issue if necessary and reassess pin/functional testing before future release claims.

## Closed-network second-wave outstanding items — 2026-10-21

- **Full 7-Zip GUI user-workstation acceptance** (P1): the **complete official 7-Zip 26.04 is now pinned** and uses validated SFX-as-DATA extraction via the trusted managed 7zr, never launches installer. Remaining: manual 7zFM GUI Add/Extract/Open, Unicode paths, HKCU context-menu *opt-in only*, no unintended default file associations or registry writes.
- **Everything service/index and privacy** (P1): officially permissive desktop software, portable ZIP installed without registry; actual first launch may offer NTFS service, indexing via admin, update checks, HTTP/ETP configuration, index-file user permissions. Never auto-launch in CI. Validate on non-production client with *service disabled + folder-only indexing* profile and document performance/privilege trade-off; no default service or full drive index on MES servers.
- **grepWin** (P1): real Windows Explorer GUI search and replace *read-only search first*, case/encoding/large log and portable settings write footprint. Add optional shell integration only after owned-HKCU collision-safe test (not default).
- **Miller / dasel** (P1): fixture-based real transformations and log encoding tests, check NUL/malformed CSV/YAML/JSON and no in-place source modifications. 
- **Offline vendor intake** (P1): review manifest-driven export with exact official URLs, local SHA, file size, signature, EDR/OSS approval evidence. Validate source archives without network on disconnected worker; currently user must obtain original vendor files on an approved connected machine. Offline recommended Notepad++ plugin installer is not implemented; reject instead of network fallback.
- **License review** (P1): original vendor binaries are downloaded by the user from official sources; source-only Git repo contains no vendor binaries. Everything desktop license includes notice conditions. Run internal corporate OSS/EULA/security approval before deployment; no automatic release.
- **Prior unchanged:** actual Office4 Word/Excel/PowerPoint/Visio COM GUI comparisons on licensed Windows, advanced WinMerge two-item native ShellExtension, and `sd` pinned v1.1.0 archive containing executable self-report v1.0.0 remain blocked/backlog.

## Next cross-component verification

- Validate real full 7-Zip SFX extraction under an approved offline workstation (not only hosted CI). Verify `7zFM.exe` opens without admin, actually adds/extracts ZIP/7z, configuration stays local, Win11 classic right-click remains unchanged until separate optional HKCU integration approved.
- Everything desktop: first-run folder-only indexing without service/UAC as **option**, metadata/file path privacy and manual UI. Do not autoenable NTFS service.
- grepWin portable: read-only regex search against UTF-8/UTF-16 and log-volume fixture, verify application UI and replace operation opt-in, no shell association by default.
