# PortaKit v0.3.0

## Highlights

- **Portable apps and toolsets:** Optional categorized toolsets and profiles add pinned utilities, offline installation from verified original vendor assets, and full 7-Zip extraction without running its installer. TCPView and PsPing are available from Microsoft as pinned downloads.
- **Personal kits:** Compose locked kits, preview and save selections with an optional keyboard-first picker, and plan or explicitly build them. Read-only offline readiness, footprint, plugin health and KitDoctor reports help assess a kit before deployment.
- **Editors and Explorer:** Opt in to recommended editor settings, individually selected pinned plugins and offline plugin application. Separate current-user Explorer menus support managed Notepad++ and WinMerge; status reports stale owned menus.
- **Evidence and research:** Optional create-only console evidence, Office acceptance workflows, and CSV source preflights, synthetic fixtures, captured-result checks and benchmark review support local assessment. Miller remains the pinned CSV baseline; alternatives remain research-only.

## Fixes

- Hardened archive extraction, strict JSON parsing, destination ownership, toolset child execution and post-install verification. Single-root ZIP flattening now handles case differences.
- Protected foreign files and evidence from cleanup or overwrite, refused modified Explorer menu payloads, and preserved GUI evidence on EOF.
- Corrected picker plan paths and input handling, offline readiness, plugin integrity checks, and CSV evidence boundaries and validation.

## Safety / Compatibility

PortaKit targets Windows and Python 3.11+ and uses only the Python standard library. Windows CI covers Python 3.11 and 3.14. Installs verify pinned SHA-256 hashes; toolset apply and plugin changes require explicit consent. Run one operation at a time.

## Known limitations / NOT_VERIFIED

Human GUI acceptance remains pending. Office4 comparison requires the corresponding licensed desktop Office applications and local acceptance; CI does not establish that acceptance. Sysinternals use and redistribution are subject to Microsoft's licensing terms. Site, legal, security, network and EDR approvals are owned by the end user or organization.

## Upgrade notes

Review the current catalog and toolset plans before applying changes. Existing managed installations can use explicit `configure` for recommended settings; plugin application has separate consent and offline asset requirements. Back up personal data before removal: `remove` deletes the managed folder, including settings and plugins. Review preserved third-party plugins for compatibility after updates.

## Release caveats (Gate C review)

- **Pins:** the catalog grew from 3 to 19 tools; the original Notepad++, WinMerge and jq pins are unchanged. TCPView and PsPing use mutable Microsoft URLs with a fixed SHA-256, so a vendor update fails closed until re-pinned. sd 1.1.0 reports 1.0.0 internally.
- **Vendor execution:** full 7-Zip is unpacked by running the managed, SHA-rechecked `7zr.exe`; this is the only vendor binary the core executes.
- **Persistence:** the state schema is unchanged but parsing is strict; hand-edited state with duplicate keys or NaN now fails closed. New files under ROOT: `.portakit-plugin-state.json` (plugin receipts) and `.portakit-evidence/` (logs).
- **Stale receipts:** `remove` does not delete plugin receipts; a reinstalled host reports blocked plugins until the receipt is cleared.
- **Update behaviour:** Notepad++ `plugins/Config` is no longer copied whole; vendor files win at the same path and user-added files are preserved.
- **Global side effects:** only the opt-in Explorer menu writes to `HKCU\Software\Classes`; no PATH edits, auto-upgrade or remote scripts. Unregister menus before moving the root.
- **Data loss:** `remove` deletes the managed folder and its `.old` backup, including settings and plugins.
- **Offline sources:** `--archive` and `--offline-dir` keep the SHA check, the 100 MiB cap and link refusal; an empty `--offline-dir` is rejected.
