# Personal Kit Doctor — one read-only check

**Scope:** inspect a saved personal kit in one command without a GUI. This
reuses the existing official-source SHA readiness, managed-install logical-byte
measurement and (only when selected) editor-plugin installed-file receipt
verification. It neither modifies the kit nor performs installs, downloads,
updates, Windows setting changes or vendor execution.

```cmd
scripts\KitDoctor.cmd --kit MyPortableKit.json --root D:\PortableApps
scripts\KitDoctor.cmd --kit MyPortableKit.json --root D:\PortableApps --archive-dir D:\ApprovedOriginals --skip-pending --max-mib 200
scripts\KitDoctor.cmd --kit MyPortableKit.json --root D:\PortableApps --out D:\LocalEvidence\Doctor.json
```

- Without `--out`: **no report/evidence file** is written.
- With `--out`: creates **only new** JSON and a same-basename UTF-8 `.log`
  whose bytes match the program-generated console stdout (including REPORT).
  Existing files and symlinks/junction destinations are rejected; keep the
  report private because it contains local paths and file inventory.
- `--archive-dir`: optional user-acquired **original official vendor files**;
  each still-missing pinned archive is hash-checked by the existing engine.
  Already-installed managed apps do not require vendor archives.
- `--skip-pending`: narrows *offline source inspection* to already-approved
  pins. Research-only, OS built-ins and individually selected editor plugins
  still cause the **whole-kit** aggregate result to stay INCOMPLETE. This flag
  does not install or authorize anything.
- `--max-mib`: optional nonnegative integer logical MiB limit; UNKNOWN sizes
  cannot produce a false budget PASS. Logical bytes are not physical allocated
  disk bytes or future download/unpacked estimates.

## Interpretation

| Outcome | Exit | Meaning |
| --- | --- | --- |
| `LOCAL_CHECKS_PASS` | 0 | Selected pinned managed apps already installed and measured; no pending/OS/plugin items, no budget failure. **Not enterprise approval.** |
| `INCOMPLETE` | 2 | Missing install, research-only, OS-only, plugin selection, unknown footprint or otherwise incomplete local evidence. |
| `BLOCKED` | 2 | Missing/wrong vendor sources, bad managed state/plugin receipt, prerequisite blocker or measured budget exceeded. |
| `ERROR` (stderr) | 1 | Invalid schema/pin, bad input/path or inability to inspect; never silently treated as PASS. |

A chosen editor plugin may independently show `LOCAL_HASH_PASS`, which only
means the local per-file receipt matches. Plugin size is still excluded from
the complete footprint; thus selected plugins do not automatically turn the
whole kit PASS. A real Windows GUI/Tk, licensed Office integration, EULA, OSS
policy, source transfer/redistribution permission, publisher signature and EDR
approval all remain **HUMAN/LEGAL_NOT_VERIFIED**.

No actions operate on industrial equipment, plant networks, or production
systems. Use only organization-approved synthetic or nonproduction inputs.
