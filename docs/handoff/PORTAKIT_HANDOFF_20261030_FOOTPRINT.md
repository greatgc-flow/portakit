# PortaKit 2026-10-30 footprint implementation handoff

Check live main HEAD, open PR/issues, and Windows CI before continuing. Initial base SHA: `2ec91a1131797b4a52aae1146ca5df045827312a`.

Branch `feat/readonly-toolkit-footprint-audit-20261030` contains read-only `scripts/kit_footprint.py`, regression cases in `tests/test_kit_footprint.py`, and `docs/FOOTPRINT_AUDIT.md`. Existing 19 approved SHA pins, total 151 selectable IDs, core installer, catalog, research lists and toolset profiles remain unchanged.

The command measures only existing managed pinned directories with matching saved locks. Logical bytes are not NTFS allocated size or future download footprint. Missing/pending/OS items cannot pass a complete budget. It rejects junctions/symlinks/special files and caps scan depth/entries. Optional JSON report and exact mirrored local log are new-only; no downloads, execution, installs, OS changes or third-party bundling.

Recheck current PR Windows CI 3.11 and 3.14 and review diff before merging. Verify post-merge main CI. Actual GUI acceptance (issue #27), simulator candidate research (issue #25), legal rights and Office/Everything/7-Zip GUI real runs remain separate open gates. Prior general current handoff is `docs/handoff/START_NEW_CHAT_PORTAKIT_20261030_CURRENT.md`.
