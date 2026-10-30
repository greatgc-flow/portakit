# Offline toolkit asset handoff (2026-10-30)

## One-command offline readiness (2026-10-30)

The preceding `list/export/verify` workflow remains supported. For a **single read-only preflight** that combines a personal kit's installation-state plan, the required *original* approved vendor filenames and the existing per-artifact SHA-256 verifier, run:

```cmd
:: No files created. Exit 2 if source files or consent are still missing.
scripts\OfflineCheck.cmd --kit MyKit.json --root D:\MyPortableApps

:: After separately obtaining approved original vendor files, validate only
:: the archives needed for missing pinned tools (already-installed pins skipped).
scripts\OfflineCheck.cmd --kit MyKit.json --root D:\MyPortableApps --archive-dir D:\ApprovedVendorArchives --skip-pending

:: Optional NEW JSON+exact console transcript log; never overwrite prior evidence.
scripts\OfflineCheck.cmd --kit MyKit.json --root D:\MyPortableApps --archive-dir D:\ApprovedVendorArchives --skip-pending --out MyKit.readiness.json
```

`--skip-pending` explicitly excludes *all* research-only tools and individually chosen editor plugins; it does not install them. The status is `READY`, `READY_APPROVED_SUBSET`, `NO_OP`, or `BLOCKED`. Exit **0** for ready/no-op, **2** for blockers (including missing/wrong SHA files, unapproved selections without explicit subset consent, prerequisites or blocked managed paths), **1** for invalid input/security errors. The command reports each pinned item's `already-installed` / `install` / `blocked-*` state, original filename, catalog hash, official URL and source readiness.

Only missing pinned applications require a local vendor archive; already managed matching installations are not re-downloaded. If **all** approved pinned applications are already installed (or there are none), an optional nonexistent archive folder is not a blocker because no vendor archive needs to be read. In a mixed kit, a missing folder still blocks the uninstalled applications. This reflects only managed state metadata, not a fresh installed-byte integrity or real GUI check. Exact hash comparisons reuse `toolsets.verify_offline_assets`; reparse/junction paths are refused. `--out` creates a new report JSON and exact console-mirrored .log *locally only*, with no overwrite. Default invocation has no writes. `READY` means **only a point-in-time local preflight** for approved pinned tools, never legal/company/EDR approval, installed-byte integrity, live desktop acceptance, or a guarantee that a subsequent state change will not block install. An actual build remains a **separate deliberate** `MyToolkit.cmd build ... --offline-dir ... --yes` operation, which rechecks all missing sources again under the install lock.


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
