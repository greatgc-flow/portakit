# PortaKit — 2026-10-23 R2 safe continuation handoff

**Public-safe handoff only.** Never paste raw private chats, memories, machine/enterprise identifiers, credentials, production logs, unpublished third-party binaries or other sensitive material into this PUBLIC repository.

## Latest authority
- Starting main HEAD verified 2026-10-23: `af6103ffd81c86e61b42e067da1c8c572dc803f4` (same as earlier reference); working branch `fix/zip-extraction-bounds-20261023`. **This is a pre-change baseline, not a substitute for retrieving newer live main.**
- Baseline open PRs/issues: 0/0. Baseline Windows test run [39883144654](https://github.com/greatgc-flow/portakit/actions/runs/39883144654) SUCCESS, Windows Python 3.11 and 3.14.
- Start from [R2 audit](../review/2026-10-23_RECURSIVE_MECE_AUDIT.md), then [2026-10-23 prior handoff](PORTAKIT_HANDOFF_20261023.md), [full 2026-10-22 handoff](PORTAKIT_COMPLETE_HANDOFF_20261022.md), source map, `README.md`, `catalog.json`, `toolsets.json`, `portakit.py`, scripts, tests, workflows, governance and research.
- Baseline counts: 17 installable; 108 research items (17 pinned, 27 native, 64 review-only); 10 primary domains, 12 profiles, 6 legacy aliases; 53 main tracked files BEFORE this R2 branch. Research candidate is not installable.
- R2 scoped code change: constrain ordinary ZIP extraction file-count and expanded size, stream-verify member length, preserve rollback; unit regressions. Confirm PR checks and post-merge run before declaring these completed on main.

## Immutable decisions
Windows-only Python 3.11+ standard library. The user's older enterprise compatibility constraints apply when producing Java/C#/PowerShell examples: JDK 1.8, VS2015 C#, PS 2.x/5.x (or version-gated exceptions). Preserve read-only planning and explicit `apply --yes`; SHA-pinned offline installs; one primary owner per tool; profile dedup; no silently installed recommended plugins, GUI, services, indexers, drivers, registry entries, auto-update or network scans. Never execute original 7-Zip installer SFX. No auto Release.

## Pending external gates
1. Everything/grepWin/full 7-Zip actual GUI: approved **non-production workstation** only, local synthetic fixtures, `scripts/GuiAcceptance.cmd`. No true PASS without human evidence; review `result.json`, `results.csv`, exact `console.log` and approved screenshots independently. Everything requires separate first-run approval.
2. WinMerge Office4: actual licensed interactive Microsoft Office and semantic proof for Excel/Word/PPT/Visio; unattended or headless prerequisites are NOT_VERIFIED. See `docs/WINMERGE_OFFICE_ACCEPTANCE.md`.
3. TCPView/PsPing are research metadata only; official Microsoft free company use DOES NOT establish redistribution/air-gap copying rights. Separate legal/EDR/security approval. PsPing needs a specific approved active destination and rate.
4. `sd` v1.1.0 official archive vs embedded executable v1.0.0 mismatch; separate vendor-source investigation, no hidden PASS.
5. Measured installed disk space/dependencies/new small tools and standalone `7zip` prerequisite UX review; no speculative new pins.

## Repeatable next step
Read [copy-ready R2 prompt](START_NEW_CHAT_PORTAKIT_20261023_R2.md); fetch *actual latest main HEAD* + PR/issues and Windows run statuses; compare candidate PR and results; update source-to-test-to-doc evidence; only merge successful verified changes. Restore human/legal gates as open even if CI passes. Record public-safe evidence links rather than uploading enterprise files.
