# Individually selected editor plugins — offline apply (2026-10-30)

## Optional read-only health report

Use `python -I scripts/plugin_health.py --kit Editor.json --root D:\PortableApps` to classify each selected editor plugin's existing managed state and keep explicit optional local JSON+console evidence with `--out Editor.health.json`. This does **not** install, alter or launch plugins. See [field procedure](PLUGIN_HEALTH.md). `LOCAL_HASH_PASS` proves only matching local per-file receipt hashes at the time inspected; do not confuse it with independent publisher/EDR/legal checks.

## Persisted receipt and health-report integrity (2026-11-01)

- Existing `.portakit-plugin-state.json` is **untrusted local input**, not an approval record. The reader now rejects duplicate JSON keys at **all nesting levels** (plugin ID, version/source pin and individual file-hash inventory); previously a duplicate could be interpreted as the *last* value by a standard JSON parser. Nonstandard `NaN`/`Infinity` and invalid/noncanonical `host:plugin-id` keys fail closed. A rejected receipt is **not modified, migrated, accepted as installed or silently deleted**; back up and investigate it before taking an operator-approved remediation action.
- The separate read-only `plugin_health.py --out NEW.json` now attempts to clean up only its **own** partially created JSON/log files if serialization or console-mirror writing fails. It preserves any pre-existing or concurrently replaced file. A write error is **not** a successful health observation; choose a fresh evidence path and verify the exact log before relying on it.
- Like other evidence writers, cleanup is *best effort*, not an atomic filesystem transaction: power loss, file-ID reuse, or post-scan edits remain possible. The receipt parser is not a cryptographic signature, and `LOCAL_HASH_PASS` still means only matching local bytes, never corporate licensing/EDR or real desktop approval.

## Installed-file integrity audit (2026-10-30)

New installs record a bounded SHA-256 inventory for **every extracted file**, including the required DLL and nested libraries, in the plugin receipt state. The no-write `plan` rehashes the installed plugin directory before saying `already-installed`; changed, added or missing files return `blocked-content-drift`. A pre-existing **older receipt without file hashes is accepted for inspection but is blocked as `blocked-legacy-unverified`**, never silently elevated to trusted. Do not delete, replace or regenerate these receipts automatically: reconcile manually with backups, original source archives and separately approved remediation. An unauthorized plugin change is not silently overwritten; the evidence remains available for investigation.

The audit limits plugin tree traversal to 4,096 directory entries, depth 32 and 512 MiB of logical file bytes; links, junctions and special files are refused. The per-file hash receipt is **integrity evidence, not a publisher signature, malware clearance or forensic guarantee**: an attacker with permission to rewrite both installed files and receipts, or concurrent filesystem writes, may defeat a snapshot check. Keep host applications closed when applying plugins. No license/EDR or GUI acceptance is inferred.

This feature is **opt-in** and uses only the two existing SHA-pinned Notepad++ plugins (ComparePlus and JsonTools). It never downloads vendor ZIPs, bundles them into PortaKit, executes a DLL, or adjusts registry/services/driver/Windows PATH. No WinMerge add-on or research-only editor plugin is installable. **The operator must independently verify company-use, transfer, OSS notices and EDR policy before using --policy-approved.** A repository license permits certain uses subject to license terms; it does not prove that your organization has approved this deployment.

Official project sources: [ComparePlus](https://github.com/pnedev/comparePlus) (GPL-3.0; Notepad++ >=8.4.2, use correct architecture, includes required libs) and [JsonTools](https://github.com/molsonkiko/JsonToolsNppPlugin) (Apache-2.0; check release and plugin-host architecture). Catalog locks currently target Notepad++ 8.7.5 x64, ComparePlus 3.0.0 and JsonTools 8.5. Check **exact catalog pin**; not a claim that latest versions are always safe.

## Safe workflow (nonproduction, controlled offline Windows)

First create a v2 kit and install the **Notepad++ host only**, without automatic recommended plugins:

```cmd
scripts\MyToolkit.cmd create --name editor --tool notepad++ --plugin compareplus --plugin jsontools-npp --out Editor.json
scripts\MyToolkit.cmd plan --kit Editor.json --root D:\PortableApps
scripts\MyToolkit.cmd build --kit Editor.json --root D:\PortableApps --skip-pending --yes
```

Manually and separately obtain permissioned, **unmodified original vendor archives** named exactly as their pinned GitHub release files. Use `scripts\MyToolkit.cmd plugins` and `catalog.json` to verify source URLs, versions and SHA-256. Transfer files into your approved **local** archive directory. **Do not upload third-party ZIPs or internal host paths to this public GitHub repository.**

```cmd
:: No changes: host/plugin state, dependencies and destination plan
python -I scripts/plugin_offline.py plan --kit Editor.json --root D:\PortableApps

:: No changes: verify every pinned original archive SHA-256
python -I scripts/plugin_offline.py verify --kit Editor.json --root D:\PortableApps --offline-dir D:\ApprovedVendorArchives

:: Only after corporate license/EDR/source-transfer authorization and closure of Notepad++:
python -I scripts/plugin_offline.py apply --kit Editor.json --root D:\PortableApps --offline-dir D:\ApprovedVendorArchives --yes --policy-approved

:: If a v2 kit also contains research-only plugin choices:
python -I scripts/plugin_offline.py apply --kit Editor.json --root D:\PortableApps --offline-dir D:\ApprovedVendorArchives --yes --policy-approved --skip-pending
```

All three subcommands require a validated personal **schema-v2** JSON kit. `--yes` and `--policy-approved` must be supplied together for apply. Neither flag supplies legal authorization on its own. `--skip-pending` explicitly suppresses only unapproved research plugins; missing pinned vendor archives or failed host validation always block. Existing old **schema-v1** kits and their legacy `--recommended` behavior are untouched.

## Missing-only original ZIP preflight (2026-10-31)

`apply` now requires original vendor ZIPs **only for selected pinned plugins whose
current managed status is `install`**. Already-managed plugins are rechecked
against their per-file SHA-256 receipt during planning and after acquiring the
existing locks, then skipped without re-requesting their original archive.
This is analogous to the main offline toolkit's missing-only readiness.

```cmd
:: Already-managed, SHA-matched selected plugins: local no-op, no source folder needed.
:: Both policy attestation flags and a new local evidence log remain mandatory.
python -I scripts/plugin_offline.py apply --kit Editor.json --root D:\PortableApps --yes --policy-approved

:: Mixed installed + missing: the source directory needs original ZIPs only
:: for the missing selected plugins. All missing ZIPs are verified before writes.
python -I scripts/plugin_offline.py apply --kit Editor.json --root D:\PortableApps --offline-dir D:\ApprovedVendorArchives --yes --policy-approved

:: Explicit original archive audit is unchanged: checks EVERY selected pinned ZIP.
python -I scripts/plugin_offline.py verify --kit Editor.json --root D:\PortableApps --offline-dir D:\ApprovedVendorArchives
```

A missing original for a still-uninstalled plugin, hash mismatch, modified
managed plugin, stale host, absent policy attestation or research-only selection
without `--skip-pending` **still fails closed**. An empty pinned subset with
explicit `--skip-pending` performs no installation. `apply` is not a repair
command for modified installed files. For a no-op, the CLI allows omission of
`--offline-dir`; `verify` still requires it. If any selected plugin needs
installation and `--offline-dir` is omitted, the command fails before writing
managed plugin files. Existing evidence logs are never overwritten.

## Strict scope and recovery

- Host must already be in a managed, exact catalog pinned state, with no backup lock or link. No app execution, full installation, silent host update or admin rights.
- All **missing selected pinned** original archives are SHA-256 checked before any change, then snapshotted locally with a **second SHA** before extraction; ZIP contents use the existing path traversal, reparse, maximum members and expanded-bytes guards.
- Extraction occurs in a new temporary stage on the same volume. The plugin is moved to its intended Notepad++ `plugins/PluginName` directory without overwriting an existing destination. A required DLL must exist. No editor user configuration is rewritten.
- Managed receipts live in `ROOT/.portakit-plugin-state.json` with plugin+host pin metadata; an unmanaged folder, stale receipt, absent host, modified pinned version, missing source or corrupt manifest **fails closed**. Previously managed plugins are reused **only when all local extracted-file hashes still match the managed receipt**; otherwise the operation is blocked without replacing the files. This is not a publisher-signature or anti-malware verdict.
- Each plugin is transactional **up to receipt commit**: stage or receipt write failure removes that plugin's new folder and leaves previous user files untouched. **After receipt commit**, a later console/evidence I/O error is reported but preserves both the installed directory and its matching receipt; deleting only the directory would leave stale managed state. The incomplete transcript is **invalid evidence**, not proof of a completed apply. Check the read-only `plan`, then explicitly retry using a fresh create-only evidence log; a matching managed plugin is skipped without reacquiring the original ZIP. **Whole batch is not atomic**: earlier committed plugins remain if a later plugin fails. Do not delete managed plugin folders manually; reconcile independently. Close Notepad++ before installing so it can reload plugins on next launch.
- `apply` mirrors console evidence into an operator-local new-only `.portakit-evidence/editor-plugins-*.log` (or explicit `--log-file`). An explicit log **inside ROOT** is accepted **only under ROOT/.portakit-evidence/**; logs inside managed editor/plugin directories, temporary install folders, backups, or other root subfolders are rejected **before creating any evidence file or installing a plugin**. A log file outside ROOT remains valid. This uses the same existing safety rule as core/toolset installation, preserving the installed plugin SHA file inventory and create-only evidence. `plan` and `verify` are read-only console commands. Never publish enterprise evidence or any vendor archive.

## Incomplete gates

The actual plugin UI (loaded correctly in Notepad++ and functioning with Office documents) remains **HUMAN_NOT_VERIFIED** until executed on an approved Windows workstation. Real vendor archive hash/SHA verification and corporate license/transfer approvals are **OPERATOR_NOT_VERIFIED** here. This code is a controlled, permission-gated capability, not an automatic company-wide deployment or redistributable plugin pack. No public Release.
