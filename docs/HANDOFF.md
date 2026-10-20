# Open work

Status checked 2026-10-20. The MVP contract remains [SPEC](SPEC.md); the implementation and original test suite have not been expanded by the release-readiness work.

## Verification and release

- A minimal Windows CI workflow has been proposed: Python 3.11 and 3.14, regression tests plus catalog/CLI smoke, no download, no secrets, no auto-publish. **Verify actual check results at the candidate commit**; the test count alone is not a pass.
- Follow [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md) before a GitHub Release: live isolated Windows test for jq, Notepad++, and WinMerge (including actual pinned assets), failure/recovery audit, recorded evidence, and human release approval.
- The repository is public and has no published GitHub Release at the time of this handoff. PyPI packaging is not planned for this gate; choose separately if needed.

## PeerHub cross-project status

- [PeerHub #180](https://github.com/greatgc-flow/peerhub/issues/180) was closed 2026-10-19; it concerned in-place `pip install --target --upgrade` during an active ask on Windows and is not a PortaKit CLI failure.
- [#169](https://github.com/greatgc-flow/peerhub/issues/169) and [#174](https://github.com/greatgc-flow/peerhub/issues/174) are also closed. Closure is **not** independent evidence of end-to-end resolution; check PeerHub itself before asserting so.
- Previous direct ag review of PortaKit: spot checks reported 7/7 nonempty on PeerHub 0.21.1 (recorded in the earlier handoff). This is not equivalent to a full Windows integration test.

## Optional future scope (not required for this gate)

- Expand the catalog after verifying every new pin and source.
- Deferred: config seeding, offline bundles, doctor, pip tools, shims, nested/plugin destinations and installed-state listing in `list`.
