# Personal toolkit footprint audit (read-only)

Use `python -I scripts/kit_footprint.py --kit MyKit.json --root D:\\MyPortableApps` to scan only existing PortaKit-managed pinned application directories.

Optional `--max-mib 100` checks an integer logical-file-byte budget in MiB; it reports `UNKNOWN_INCOMPLETE` if any selected tool is not measured or is research-only / OS built-in. Exit status: `0` when no budget was requested or all selected assets were measured and within budget; `2` for `UNKNOWN_INCOMPLETE` with a requested budget; `3` for `OVER_BUDGET`; `1` for errors. A measured total is a lower bound when any tool is missing; compressed size, NTFS allocated size, RAM, and temporary extraction headroom are **not** measured.

Optional `--out MyKit.footprint.json` creates a new-only JSON file and an exact console-matched local .log. Read-only calls without `--out` create no files. Filesystem scan refuses symlinks, junctions and special files, is limited to 100000 entries / 64 levels, and does not follow external folders. Concurrent filesystem modifications can invalidate the measurement; repeat when needed.

No vendor binaries are launched or downloaded; no installs, registry/service/driver writes, network probes, removal or redistribution are performed. This is independent from actual workstation GUI acceptance and enterprise licensing approvals. See `docs/PERSONAL_KITS.md`, `docs/OFFLINE_ASSETS.md` and the latest dated handoff.
