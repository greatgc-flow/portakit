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

## Plugin preservation work (2026-10-20)

- Additional Notepad++ and WinMerge plugins are **not** downloaded or installed by PortaKit. Only the plugins bundled in the pinned archives install by default.
- The proposed opt-in `preserveMissingOnUpdate` retains user-added plugin files on updates without replacing files shipped by the new application version; Notepad++ `plugins/Config` is no longer blindly copied wholesale, to prevent overwriting the vendor plugin list DLL.
- Verify this behavior in Windows CI and on a real version-change update before treating it as release-ready. The automatic live-smoke PR check tests pinned archives, not a real version change.

## Optional future scope (not required for this gate)

- Expand the catalog after verifying every new pin and source.
- Deferred: offline bundles, doctor, pip tools, shims, nested/plugin destinations and installed-state listing in `list`.

## Recommended setup track (2026-10-20)

- Proposed `install ID --recommended` for Notepad++ and WinMerge; existing install/update/remove unchanged without flag.
- ComparePlus 3.0.0 and JSON Tools 8.5 SHA-256 values taken from the official Notepad++ x64 Plugin List. Windows CI must confirm external archives, DLL destinations, NPP configuration and WinMerge INI before the feature is merged.
- Live GUI plugin load and compatibility after real editor version transitions remain **manual release gates**, not implied by CLI smoke. Never advertise them as verified by file-only tests.
