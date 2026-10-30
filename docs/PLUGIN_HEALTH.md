# Editor plugin local health check — read-only (2026-10-30)

This report checks **local managed-plugin file hashes** against a managed per-file receipt. It does not run vendor applications/DLLs, install packages, scan a production network or modify existing installation state. It is not vendor authentication, malware clearance, license approval, independent notarization or confirmation the GUI loads.

## Use in an approved nonproduction Windows environment

From the repository root with Python 3.11+:

```cmd
:: Default: read-only, no files created, no vendor archives required.
python -I scripts/plugin_health.py --kit Editor.json --root D:\PortableApps

:: Optional explicit new-only JSON plus identical local console evidence log.
python -I scripts/plugin_health.py --kit Editor.json --root D:\PortableApps --out Editor.health.json

:: Health should be reviewed BEFORE using any install/repair command.
python -I scripts/plugin_offline.py plan --kit Editor.json --root D:\PortableApps
```

`Editor.json` must be a validated **personal kit v2** with individually chosen plugins. No v1 kit is silently upgraded. By default the command creates **no files**. `--out` writes *only* a new JSON report and new console-mirrored `.log`; refusal to overwrite protects previous evidence. Keep locally captured paths/results private; this repository is PUBLIC.

## Results and exit codes

| Outcome | Meaning | Exit |
| --- | --- | --- |
| `LOCAL_HASH_PASS` | Every selected plugin already installed, matching managed per-file SHA-256 receipt at scan time | 0 |
| `INCOMPLETE` | At least one plugin is not installed or remains research-only; none is blocked | 2 |
| `BLOCKED` | At least one plugin is blocked due to missing/mismatched host, drift, legacy receipt or unmanaged files | 2 |
| `ERROR` (stderr) | Unreadable/corrupt receipt, unsafe path, unsupported kit, access failure or other scan problem | 1 |

Per-item `sourceState` is preserved from `plugin_offline.make_plan`: `already-installed`, `install`, `blocked-host-...`, `blocked-content-drift`, `blocked-legacy-unverified`, `blocked-unmanaged` and `RESEARCH_ONLY`. These categories are **not a corporate compliance verdict**. `LOCAL_HASH_PASS` is a temporary local comparison, not proof of publisher trust or absence of malicious edits if both files and receipts can be altered.

## Field checklist (operator signed/recorded locally only)

- Confirm an authorized non-production PC, actual user account privileges, isolated approved vendor sources and no MES/PLC production connections. Obtain EULA/EDR/company distribution/transfer approvals independently.
- Confirm Notepad++ is closed and the installed host version matches the current immutable catalog pin. Record checked hash only; do not paste workstation identities or internal paths into PUBLIC GitHub.
- Execute the read-only health command; retain JSON/log and local SHA of both files in your organization-approved evidence store. Compare with `plugin_offline.py plan` (also read-only).
- For `BLOCKED` or `ERROR`, preserve original plugin files and receipts; do not delete or automatically rewrite/migrate legacy state. Perform approved human triage before remediation.
- Separately perform manual GUI acceptance: launch approved Notepad++ *under local operator control*, verify expected plugin menu, one synthetic compare/JSON sample and no policy/EDR alert. This script **never** launches the editor.
- Record `HUMAN_NOT_VERIFIED` until all actual GUI cases and legal approval evidence exist. A green Windows CI run only covers synthetic unit tests.

## Design and audit limits

This uses current `scripts/plugin_offline.py` receipt validation and per-file SHA traversal, including limits of 4,096 entries, depth 32, 512MiB logical bytes and rejection of symlinks/reparse points. A filesystem can change after inspection; the report includes an observation UTC timestamp. It does not perform an installed binary code signature check, and no elevated Windows or service/driver/registry change occurs.

See [plugin offline apply](PLUGIN_OFFLINE_APPLY.md), [GUI manual acceptance](GUI_PICKER_ACCEPTANCE_20261030.md), [per-plugin choices](INDIVIDUAL_EDITOR_PLUGINS.md), [2026-10-30 current handoff](handoff/START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md).
