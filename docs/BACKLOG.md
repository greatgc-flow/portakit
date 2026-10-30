# PortaKit backlog (prioritized, evidence-based)

## R2 reconciliation (2026-10-23; review before changing latest main)

- **Focused remediation (PR validation required):** baseline ZIP extractor lacked expanded-size and member-count guards. The [R2 code/audit change](review/2026-10-23_RECURSIVE_MECE_AUDIT.md) adds bounded ZIP preflight, streamed member-length checks and rollback regressions. Consider DONE only once Windows PR CI passes, change is merged, and main CI rechecked.
- **Open human/licensing gates:** Everything / grepWin / full 7-Zip GUI remain `HUMAN_NOT_VERIFIED`; four Office semantic comparisons `NOT_VERIFIED`; TCPView/PsPing `RESEARCH_ONLY` pending vendor redistribution/internal transfer determination. Do not upgrade to PASS or add binaries because CI is green.
- **Next optional robustness:** consider an opt-in console-to-file evidence mode for the single-tool core CLI; toolset apply and GUI/Office harnesses already write local evidence. Confirm exact stdout/stderr semantics and sensitive-data handling before generalizing.
- **Usability:** explicit standalone `7zip` requires previously managed `7zr`; document prerequisite rather than silently installing it. Historical candidate lines below are intentionally not current installation status.

> **Active handoff as of 2026-10-22:** [Verified cross-chat status and ordered P0–P2 gaps](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md) · [new chat prompt](handoff/START_NEW_CHAT_PORTAKIT_20261022.md). The chronological sections below intentionally preserve older planning assumptions, some superseded by PRs #14–#18. Do not treat a past "candidate" or "not implemented" entry as current without checking main.

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

- **P1 sd upstream version anomaly:** Official v1.1.0 Windows ZIP at pinned SHA executes but `sd --version` prints 1.0.0 on Windows CI. Record explicit warning/exception (no hidden PASS as same version), compare vendor build metadata/source, open upstream issue if necessary and reassess pin/functional testing before future release claims. **2026-10-30 status:** still OPEN; upstream asset digest and tag `Cargo.toml` not yet re-verified (see [TOOLSETS](TOOLSETS.md#upstream-sd-embedded-version-discrepancy-not-hidden)).
- **P2 small-footprint research candidates (2026-10-30, no install, no vendor binaries):** recommend at most three for future admission, each needing exact official asset URL, SHA-256, compressed size, license notice, and a Windows download/hash/`--version` smoke before any catalog entry: (1) `b3sum` (CC0/Apache-2.0, `security`, fills the empty security domain for offline hashing; `certutil` remains the built-in fallback); (2) `sqlite-cli` (Public Domain, `structured-data`, local SQL/CSV export for log analysis); (3) `dust` (Apache-2.0, `files`, disk-usage tree). Rejected for now: `csvtk` (overlaps Miller), `just` / `taskfile` (overlap PowerShell/cmd), and `pandoc` / `imagemagick` (large, outside the small-footprint goal). All research sizes remain `NOT_MEASURED`.

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

## Current gate: GUI evidence and TCPView/PsPing corporate intake (2026-10-21)

- **Everything GUI — HUMAN_NOT_VERIFIED:** New `scripts/gui_acceptance.py` and `GuiAcceptance.cmd` provide read-only-by-default pin/executable SHA probe and **separate explicit** GUI/first-run consent. Test only a synthetic local folder, never launch under CI or on MES servers; no automatic service, whole-NTFS indexing, HTTP/ETP or elevation. A actual human-reviewed `result.json` + screenshot (if permitted) is still required for release.
- **grepWin GUI — HUMAN_NOT_VERIFIED:** Guided synthetic UTF-8/UTF-16 search and deliberately disabled production replace; no GUI auto-launch in CI. Earlier binary existence checks are not manual GUI success.
- **Full 7-Zip GUI — HUMAN_NOT_VERIFIED:** Native `7z.exe` ZIP create/test CI passed, but interactive `7zFM.exe` add/extract and no-registry-association confirmation is still a human gate.
- **TCPView + PsPing — LICENSE/REDISTRIBUTION_GATE:** Official [Microsoft FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq) explicitly declines third-party distribution and [license terms](https://learn.microsoft.com/en-us/sysinternals/license-terms) prohibit publishing to others. [Metadata review](../research/SYSINTERNALS_NETWORK_REVIEW_20261021.json) documents current upstream versions, download page links, risk, company legal approval/EDR gates; no executables or download URLs added to installable catalog.
- **Next non-production validation:** run manual GUI acceptance on locally approved PC; perform TCPView read-only endpoint/CSV smoke with name resolution disabled; explicit network owner approval for PsPing target/rate and avoid suite-wide privileged tools. Keep release gated.
