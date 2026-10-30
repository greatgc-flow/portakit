# PortaKit — read-only plugin health audit handoff (2026-10-30)

Public repository `greatgc-flow/portakit`. **Verify actual latest `main` HEAD, PRs, Actions, docs and remaining Issues before resuming**; initial baseline before this branch: `24b7f2a95affc6405d26fc1cffa8654fc80fab86`. Do not assume a candidate PR is merged until checks pass and main CI confirms.

Candidate branch `feat/plugin-health-audit-20261030` adds `scripts/plugin_health.py`, `tests/test_plugin_health.py`, `docs/PLUGIN_HEALTH.md`, README/backlog updates and isolated nonmutating Windows CI smoke. Existing catalog SHA/version pins, software inventory 151 (19 pinned, 27 OS built-in, 105 research-only), 6 plugin choices, personal v1/v2 schemas and installer engine unchanged.

Operator goal: read-only classification of individually-selected editor-plugin local state:
- `LOCAL_HASH_PASS` / exit 0: every selected pinned plugin has matching per-file local receipt hashes, no pending plugin choices.
- `INCOMPLETE` / exit 2: uninstalled or research-only choices.
- `BLOCKED` / exit 2: mismatched/missing/altered/legacy state.
- `ERROR` / exit 1: invalid kit/receipt, unsafe path or OS read failure.

Default prints no-write terminal result. Explicit `--out` creates a new-only JSON file + exact console-matched log locally (no overwrite). Include UTC observation time. Reuse `plugin_offline.make_plan` instead of a parallel integrity engine; do not auto-download, install, execute a vendor DLL, edit system settings or treat local hashes as security/EDR/legal compliance.

Tests require Windows Python 3.11 and 3.14 positive and negative fixture paths (clean synthetic source, altered DLL, unmanaged/legacy/unknown, research-only, evidence, nonzero return); post-merge CI confirmation. Real Notepad++ plugin menu/human test and EULA+EDR approvals are **separate HUMAN_NOT_VERIFIED gates**; never claim this diagnostic resolves them or authorize a public Release.

Next steps after merge: human desktop acceptance on a permitted Windows PC with synthetic data, separate corporate vendor/legal review, safe remediation of historical receipts only after operator consent, and branch protection governance separately. Update Issue #36 but keep open.
