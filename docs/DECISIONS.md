# Ratified decisions

- Name: `portakit`. Windows only, Python 3.11+ standard library, one module and a catalog beside it. Initial build: 83 tests; static reviews passed; scope and specification approved unanimously by cc, cx and ag. Final v0.2.1 approval: cc, cx and ag; 166 tests.
- [SPEC](SPEC.md) is the behavioral contract. README summarizes user operation; HANDOFF contains open work.
- Catalog pins use HTTPS URLs and SHA256. Updates follow both version and digest, including downgrades; identical pins skip downloading while the destination exists.
- Destinations are single folders, uniquely owned by state IDs. Never adopt unmanaged folders or follow reparse points, junctions or symlinks.
- Mutating operations hold a root lock, discard stale temps, verify downloads before extraction, and stage before swapping. State write commits the swap; pre-commit failures roll back. Update alone recovers a lone backup; both folders require manual resolution.
- Preserve paths override packaged files during updates. Remove deletes all managed data and the backup before forgetting state; it works without a catalog.
- JSON uses one result envelope and exit codes 0–6; help stays human text. No cache, shims, config seeding or force flag in the MVP.
- Behavior changes use tests first, red then green; validation is `python -I -m unittest discover -s tests`.
