# Ratified decisions

- Name: `portakit`. Windows only, Python 3.11+ standard library, one module and a catalog beside it. Initial build: 83 tests; static reviews passed; scope and specification approved unanimously by cc, cx and ag. Final v0.2.1 approval: cc, cx and ag; tests since restructured (173).
- [SPEC](SPEC.md) is the behavioral contract. README summarizes user operation; HANDOFF contains open work.
- Catalog pins use HTTPS URLs and SHA256. Updates follow both version and digest, including downgrades; identical pins skip downloading while the destination exists.
- Destinations are single folders, uniquely owned by state IDs. Never adopt unmanaged folders or follow reparse points, junctions or symlinks.
- Mutating operations hold a root lock, discard stale temps, verify downloads before extraction, and stage before swapping. State write commits the swap; pre-commit failures roll back. Update alone recovers a lone backup; both folders require manual resolution.
- Explicitly preserved paths override packaged files during updates. Opt-in `preserveMissingOnUpdate` merges only missing user/plugin files into the stage, leaving shipped binaries and updated plugin lists intact. Remove deletes all managed data and the backup before forgetting state; it works without a catalog.
- JSON uses one result envelope and exit codes 0–6; help stays human text. No cache, shims, silent/global config seeding or force flag in the MVP; optional per-install recommended profiles require `--recommended`.
- Behavior changes use tests first, red then green; validation is `python -I -m unittest discover -s tests`.

- 2026-10-20: New opt-in `install --recommended` profile seeds minimal editor settings, validates/verifies pinned third-party Notepad++ plugin assets and stages them before atomic commit. No silent plugin install, no automatic plugin upgrades, and no external WinMerge plugin duplication. Strongly prefer catalog SHA pins over mutable/latest URLs.

- 2026-10-20: WinMerge recommended setup reuses the shipped Office unpackers (Excel/Word/PowerPoint/Visio) rather than fetching duplicate/unverified third-party packages. Require those files in the verified vendor ZIP before commit. Enable automatic unpacking using WinMerge's actual `[WinMerge]` INI format and `Settings/PluginsEnabled=1`, `Settings/UnpackerMode=1`. Office COM prerequisites are not installed or guaranteed; these unpackers compare extracted contents, not rendered document formatting.
