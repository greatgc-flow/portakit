# Offline toolkit asset handoff (2026-10-30)

## One-step readiness check — missing files only (2026-10-30)

Use the new optional `check` subcommand when preparing an individual kit for an approved offline workstation. It **combines** the personal install plan with original filename/SHA source metadata and checks only archives for tools that are **not already installed**. This fixes the former need to manually compare `list`, `plan` and `verify` output. The older commands remain backward compatible.

```cmd
:: From a permitted Windows console, Python 3.11+ required.
scripts\KitOffline.cmd check --kit MyKit.json --root D:\MyPortableApps

:: After separately obtaining the legally-authorized original archives:
scripts\KitOffline.cmd check --kit MyKit.json --root D:\MyPortableApps --archive-dir D:\ApprovedVendorArchives

:: For a kit with research-only software/editor plugin selections,
:: explicitly preflight ONLY the 19-or-fewer approved software subset:
scripts\KitOffline.cmd check --kit MyKit.json --root D:\MyPortableApps --archive-dir D:\ApprovedVendorArchives --skip-pending --out MyKit.check.json

:: Separate install consent — never performed by check:
scripts\MyToolkit.cmd build --kit MyKit.json --root D:\MyPortableApps --offline-dir D:\ApprovedVendorArchives --skip-pending --yes
```

`check` is **read-only by default**; it never creates `D:\MyPortableApps`, starts installers, executes or downloads vendor software, or changes Windows settings. `--out` explicitly creates a **new** `MyKit.check.json` and same-basename `MyKit.check.log` with console text mirrored exactly, refusing overwrite. The source originals are not included.

Outcomes: `READY` (0, required missing archives verified if supplied, or all approved tools already installed); `NO_OP` (0, no approved software to install); `NEEDS_ARCHIVES` (2, missing original vendor archives have not been supplied); `BLOCKED_PENDING` (2, research-only or schema-v2 editor plugins need explicit `--skip-pending` to check approved subset); `BLOCKED_ARCHIVES` (2, missing/mismatched/unsafe archive); `BLOCKED_STATE` (2, unmanaged destination, backup, changed managed pin, missing prerequisite); `ERROR` (1, malformed/tampered kit, inaccessible state/paths, unexpected read/argument errors). **READY is not legal or corporate permission approval.** The user must still separately approve original source rights, EDR/OS/runtime effects and execute `MyToolkit.cmd build ... --yes`, which *revalidates* hashes immediately before installation.

If **all approved tools are already installed**, the check does not require or hash their original vendor archives. A tool that needs installation still requires the correct original filename and exact catalog SHA. The six editor plugins are excluded from the application readiness list: their independent opt-in offline apply/health checks remain under `plugin_offline.py` and `plugin_health.py`. `--skip-pending` never installs plugins or unapproved software.

This is a **metadata-only** workflow for collecting separately authorized, original vendor files for a chosen personal kit. It intentionally never downloads, bundles, redistributes, runs vendor software or changes an OS installation. A SHA-pinned tool's use on a corporate machine and its redistribution/transfer rights are independent decisions; obtain EULA, OSS, EDR and import approvals before transferring any vendor archive.

## Three commands

From the source repository root on a permitted Windows machine with Python 3.11+:

```cmd
:: 1. Read-only list of exact original filenames and known upstream SHA hashes.
python -I scripts/offline_assets.py list --kit MyKit.json

:: 2. Save new metadata-only manifest plus mirrored console log locally.
python -I scripts/offline_assets.py export --kit MyKit.json --out MyKit.assets.json

:: 3. After separately acquiring approved vendor-original files, validate ALL hashes.
python -I scripts/offline_assets.py verify --kit MyKit.json --archive-dir D:\ApprovedVendorArchives

:: 4. Only then consider actual installation, after independently checking license and permissions.
scripts\MyToolkit.cmd plan --kit MyKit.json --root D:\MyPortableApps
scripts\MyToolkit.cmd build --kit MyKit.json --root D:\MyPortableApps --offline-dir D:\ApprovedVendorArchives --yes
```

If the kit contains unverified research-only selections, the default `build` refuses to run; use `--skip-pending` only to authorize the pinned subset. The manifest lists *only* the pinned subset; remaining items are recorded as excluded. `verify` refuses missing, oversized, wrong-name, bad-hash, or reparse-point vendor archive paths using the existing `scripts/toolsets.py` `verify_offline_assets` code; no network or tools are executed, and no partial install is attempted.

## Evidence and source trust

- `export` creates **new-only** `MyKit.assets.json` and `MyKit.assets.log`, recording the exact displayed console lines. `verify` creates a new evidence log under `.portakit-evidence` in the current local working directory unless `--log-file` is supplied; error and success outcome text are mirrored exactly. Private logs stay on the operator's workstation, never on PUBLIC GitHub.
- Contains per-tool official original source URL, exact filename, immutable catalog version, SHA-256 and archive type; never a tool executable, a license grant, or an artifact copied from the vendor. Mutable upstream URLs can cease to serve matching bytes, in which case verification **fails closed**.
- Rejects archive filename collisions where different SHA values would occupy one filename. Re-evaluates personal-kit locked versions/SHA against current `catalog.json`; changed pins are refused until the user regenerates and re-approves the kit.
- Metadata-only `list` does not create a log. Operators needing a read-only transcript can capture it with an explicit local redirection. The original packaged binaries are **not** attached to this project or automatically transferred.
- **Not a redistributable ZIP packager.** Do not mistake it for universal portable installation; official license notices and each tool's first-run effects/OS dependencies remain independent approval gates.

## Acceptance

`tests/test_offline_assets.py` verifies metadata isolation, Unicode-safe filenames, URL and collision gates, new-only manifest + exact logs, delegated SHA preflight, missing archive failures, pending/builtin no-ops, read-only list, changed pin denial. Windows Python 3.11/3.14 CI must be green. Real approved-offline workstation SHA check, manual airgap transfer procedure, and commercial redistribution rights remain HUMAN/LEGAL_NOT_VERIFIED; no automatic public Release.
