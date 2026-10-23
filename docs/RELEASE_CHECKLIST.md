# Release acceptance checklist

## R2 ZIP extraction acceptance addition (2026-10-23)

The general ZIP importer has a proposed explicit **4,096-member / 512 MiB expanded-data** bounded preflight and actual-byte verification independent of the 100 MiB downloaded-asset cap. Before accepting the change, verify the five corresponding `tests/test_zip_bounds.py` cases on Windows Python **3.11 and 3.14**, including update rollback and no unapproved local changes. For real vendor archives, use the separately opt-in Windows live smoke; passing synthetic tests alone is not GUI/licensed-Office/corporate-security acceptance. Never publish a release without the existing human Gate D.

> **2026-10-22 evidence boundary:** [current comprehensive handoff](handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md). At that point 17 official immutable source pins, 282 passing unit tests each on Python 3.11 and 3.14, **but workstation GUI, WinMerge Office4 semantic GUI and Sysinternals licensing gates remain NOT_VERIFIED**. No default automated Release or company security approval is implied.

This is a **manual gate**, not an automated publish workflow. A green unit-test run is necessary but not enough to advertise a release.

## Scope and policy

- Windows only; Python 3.11+; standard library only.
- Preserve the one-file implementation plus adjacent `catalog.json` and the four-command MVP.
- Use GitHub releases with a source archive first if a release is approved; PyPI packaging needs a separate decision (the script depends on a sibling catalog).
- Do **not** tag, publish, or auto-release while any gate below is unverified.
- Never run destructive smoke tests against a real user's `portable` directory.

## Gate A: deterministic regression suite (required)

1. The [Windows tests workflow](../.github/workflows/windows-tests.yml) must pass for both Python 3.11 and Python 3.14 at the **actual candidate commit**.
2. The job runs `python -I -m unittest discover -s tests -v`, using synthetic archives and injected downloaders. No real downloads are performed in CI.
3. Confirm the test runner's final success summary (the test count may grow); do not infer success from the presence of a workflow or 173 test methods alone.
4. Confirm the CLI `--json list` output and `--help` contract from the workflow.
5. If a gate fails, fix it via a new commit and rerun. Do not bypass failing checks.

## Gate B: live Windows integration (required before a release)

On a Windows test machine with internet access, create a **clean, disposable** directory and run the following in PowerShell from the repository root. Do not use your real program directory.

```powershell
$root = Join-Path $env:TEMP ("portakit-smoke-" + [guid]::NewGuid().ToString("N"))
python -I -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }
python -I portakit.py --json list
if ($LASTEXITCODE -ne 0) { throw "Catalog read failed" }

python -I portakit.py --root "$root" install jq
if ($LASTEXITCODE -ne 0) { throw "jq installation failed" }
& (Join-Path $root "jq\jq.exe") --version
if ($LASTEXITCODE -ne 0) { throw "jq execution failed" }

$updateResult = python -I portakit.py --json --root "$root" update jq | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $updateResult.ok -or $updateResult.data.changed) {
    throw "Identical-pin update was not a no-op"
}
python -I portakit.py --root "$root" remove jq
if ($LASTEXITCODE -ne 0) { throw "jq removal failed" }
if (Test-Path -LiteralPath (Join-Path $root "jq")) { throw "jq folder remains" }
Write-Host "Smoke root (disposable): $root"
```

Review the printed `$root` carefully before deleting it; removal destroys anything inside that directory. Confirm state and temporary files are consistent after the run. Separately exercise Notepad++ and WinMerge installation, executable launch, no-op update, and removal in a **fresh disposable root** each (no production configs). Confirm catalog URLs still download and all three published SHA-256 pins match the assets. These live tests require network and are **not** included in CI.

Check the manually dispatched [Windows live archive smoke](../.github/workflows/live-windows-smoke.yml) result for pinned asset downloads, SHA verification through PortaKit, bundled plugin directories, no-op update and removal. Also verify `install notepad++ --recommended` with both external pinned plugin DLLs, seed of Notepad++ tab setting, and `install winmerge --recommended` with its WinMerge-format INI settings and all four Office unpacker scriptlets in `MergePlugins`. Real Excel/Word/PowerPoint/Visio document comparisons require licensed desktop Microsoft Office apps and separate manual GUI verification (including a case with Office absent). It does **not** start the two GUI editors and does **not** verify preservation across a real release change. Do not represent it as GUI or plugin-compatibility validation.

## Gate C: fault and rollback review (required)

- Validate the mocked failure cases in `tests/test_lifecycle.py`, `test_archive.py`, and `test_links.py`: hash mismatch, unsafe ZIP entries, junction/symlink denial, stage failure, state-write rollback, stale backup restoration, both-present/manual recovery, locked binaries, and data-destructive remove.
- For a candidate release, explicitly inspect changes since the previous candidate for newly introduced paths, persistence changes, pin changes, and data-loss risks.
- No auto-upgrades, PATH edits, unpinned URLs, remote scripts, or global side effects.

## Gate C1: Office four-app static filters and safe prerequisite probe

- In live Windows CI verify the original SHA-pinned vendor `CompareMSExcelFiles.sct`, `CompareMSWordFiles.sct`, `CompareMSPowerPointFiles.sct` and `CompareMSVisioFiles.sct` contain matching extension filters and automatic selection declarations.
- Check the `portakit-winmerge-office-prerequisites` artifact contains four CSV rows (Excel/Word/PowerPoint/Visio), a console transcript and `NOT_VERIFIED` in each result. COM registration is informational only and does not establish Office readiness. Exit 2 is an expected probe result, never a test pass.
- An Office installed/licensed on the final workstation still requires actual document generation, plugin processing and human GUI inspection.

## Gate C1b: complete local evidence ZIP and semantic proof

- CI runs the one-command four-app `-ProbeOnly` entry point under Windows PowerShell, requires exit 2 and a local evidence ZIP/sidecar with matching SHA-256 and a manifest explicitly reporting NOT_VERIFIED. Upload is CI-only synthetic evidence, never user data.
- The licensed desktop acceptance run must verify distinct `BASELINE`/`DIFFERENT` markers **inside the generated HTML diff**, in addition to report existence and 0/1 exit codes. Comparing raw Office ZIP bytes is insufficient proof of plugin execution.
- After local execution, retain the ZIP, `.sha256.txt` and outputs for all four programs. Missing Office COM or an execution error is not PASS. Keep original business documents entirely out of test scope.

## Gate C1c: independent ZIP/CSV/semantic verification

- On each candidate Office4 ZIP, run `python -I scripts/verify_office_evidence.py --zip <path> --require-pass`. Only **exit 0** with verified four-app PASS is a pass gate. Exit 2 is verifiable evidence but insufficient Office integration; exit 1 means tampered/inconsistent evidence.
- Check sidecar SHA-256, all ZIP files/manifest entries, four-app CSV, full Office fixture sets, HTML reports and BASELINE/DIFFERENT markers for every PASS.
- This is an independent evidence consistency check, not proof that unattended COM runs are safe on live end-user Office sessions. Manual GUI acceptance is still mandatory.

## Gate C2: WinMerge executable + Office COM acceptance

- Record the successful real Windows WinMergeU.exe noninteractive text comparison with both HTML reports, exit codes 0 (same) and 1 (different), and the console transcript artifact. The test runs on disposable synthetic files, never user documents.
- Independently run scripts/WinMerge-OfficeAcceptance.ps1 on a licensed interactive Windows workstation for Excel (.xlsx), Word (.docx), PowerPoint (.pptx) and Visio (.vsdx), as applicable. See [WinMerge Office acceptance](WINMERGE_OFFICE_ACCEPTANCE.md). Retain console.log, results.csv, synthetic fixtures and HTML reports; use actual GUI inspection to confirm plugin selection/semantic results.
- Missing Microsoft Office COM is NOT VERIFIED (exit 2), not success. Any GUI or plugin limitation must appear in release notes. Do not infer Office support from basic archive/file installation or text comparison only.

## Gate D: publication (human approval only)

- Record: candidate commit SHA, both CI job links and conclusions, the three live test results, the catalog asset hash evidence, and remaining caveats.
- Update documentation and release notes; decide version/tag only once all checks are green.
- Publish a GitHub Release manually if desired. Do not set up automatic publishing as part of CI.
- Post-release: verify source archive contains `portakit.py` and `catalog.json` together and that `list` works from the extracted archive.

## Open scope

Future features (doctor, offline bundles, config seeding, pip tools, shims, nested destinations, installed-state listing) are deliberately deferred pending new requirements and their own test-first changes.

## Existing-install profile gate

In a disposable test root, install each editor *without* `--recommended`, add a private marker file, execute `configure ID`, then run it again. Confirm the marker and state remain unchanged, first configure installs/activates the profile, and second returns `changed:false` with no external asset downloads. Verify failure injection for invalid plugin SHA, incomplete plugin folder, symlink/junction and write-state rollback. Running Office comparison inside WinMerge GUI with licensed desktop Office apps remains a separate release blocker.


## Optional per-user classic Explorer menu gate

- In Windows CI, confirm mock-owned registry lifecycle, foreign/collision refusal, repeated install/remove no-op, partial-create rollback, and verbatim console log evidence.
- Run ephemeral HKCU smoke on a disposable hosted Windows identity; verify Notepad++ file and WinMerge file/folder key values and command path quoting; uninstall all owned keys in `finally`.
- For human acceptance, explicitly opt in, inspect Windows Explorer file and folder right-click classic menu, launch each app, and exercise removal. On Windows 11, use **Show more options / Shift+F10**. Advanced two-selected-item WinMerge extension and native modern menu are excluded.
- Never imply regular PortaKit `install`, `configure`, `update`, or `remove` implicitly adds/removes shell integration. The menu points to an absolute path and must be manually unregistered before moving or removing its target app.

## Optional toolset selection and lifecycle gate

- `python -I scripts/toolsets.py list` exposes six named categories and four composed profiles sourced exclusively from `toolsets.json`. All tool IDs must exist in the separately SHA-validated catalog. Overlapping memberships resolve once.
- `plan` must not download, write files or create ROOT/lock; verify the initially unpinned NW group reports **EMPTY** and a mixed `mes-support` selection enumerates only the three existing catalog IDs.
- `apply` requires explicit `--yes`, installs **missing** items only, refuses pin mismatch, unmanaged folders, backups and reparse links before download; `--recommended` is separately opt-in for **new** editor installs only. Do not permit silent update, remove, registry menu changes or Windows driver/service installation.
- Run the Windows **real pinned jq** category smoke, then reapply and verify the SHA of the managed state did not change. Check `ROOT\.portakit-evidence\toolsets-*.log` captures the complete displayed action lines. Cleanup solely test root. Partial group failure must preserve earlier successful installs.
- Any future OS/NW candidate requires official fixed release and independent SHA-256, archive validation, privilege/driver/licence review, and new category-specific tests. Do not claim Wireshark live capture works from a portable binary without Npcap.

## MECE taxonomy v2 and compact CLI acceptance gate

- Validate catalog **11 IDs**, toolsets.json schema v2's exactly-one primary domain, deterministic profile union and frozen backward compatibility aliases. No unapproved ZIP/EXE from the 107-tool research inventory may become installable.
- Check the official release asset metadata SHA-256 digest and compressed size for all eight newly admitted utilities; in Windows CI perform real HTTPS download → SHA-256 compare → safe extract → exactly one expected executable → `--version` invocation; reapply profile and confirm no state mutation; remove only the disposable managed test root. Keep extracted sizes distinct from release ZIP sizes.
- Legacy `common/os/nw/dev/data/diag` selectors and `minimal/mes-support/developer` profiles must keep prior pinned-ID results even after future catalog expansion. V1 user manifest is supported; unknown category/tool or overlapping canonical tool primary assignments must fail closed. No implicit registry, driver installation or profile auto-activation.
- Small-first candidate admission requires license evidence for *internal use and distribution separately*, corporate EDR/security and privilege review, official immutable package and checksum, source/vendor provenance, offline acceptance and dependency footprint.

- **Version mismatch exception:** sd v1.1.0 pinned ZIP reports sd.exe version 1.0.0 on live Windows. This exact mismatch must be surfaced to release reviewers; all seven other new tools require exact version-text match. SHA match authenticates archive bytes, not the executable's internal version field.

## Disconnected local vendor archive admission gate (2026-10-21)

- Assert pinned **17 software IDs**, exactly-one functional domain for each, 108 research entries (17 pinned, 27 built-ins, 64 research-only); old category aliases retain existing tool selection.
- `portakit.py --archive ORIGINAL install ID` reads only local source, disallows symlinks, enforces maximum archive size, compares SHA-256 to approved immutable catalog, uses the same safe ZIP and rollback staging; never contacts a vendor URL or silently opts into recommended plugin downloads.
- `toolsets.py apply portable-productivity --yes --offline-dir DIR` requires ALL missing source files to exist under their exact vendor basename, with all hashes valid BEFORE any installation or local state mutation; repeat install keeps byte-identical .portakit-state.json; untrusted/missing/symlink input has no installs. Errors must show a nonzero exit and no false PASS.
- Live Windows pinned vendor smoke must verify official SHA for 7zr/Everything/grepWin/Miller/dasel; test 7zr/Miller/dasel CLI version where meaningful, inspect Everything/grepWin executable metadata/signature **without GUI launch**, uninstall only disposable directories. No service, drivers, registry, PATH or installers.
- Human security acceptance for Everything indexes/admin/HTTP, grepWin replacements, and **full 7-Zip File Manager interactive GUI**; do not claim Microsoft Sysinternals redistribution or Office4 COM PASS based on hosted CI.

## Full 7-Zip SFX-only safety and acceptance

- Verify exact pinned official 26.04 x64 installer SHA and size; confirm installer EXE is **only opened as a 7z SFX archive** using exact separately managed `7zr.exe` (its SHA rechecked before invocation). Never execute vendor installer / uninstaller, no HKCU/HKLM file associations.
- Before extraction validate 7z listing: archive type, paths, duplicates, no link/encryption, <=512 entries, <=64 MiB expanded; validate all post-extraction members and lengths before atomic commit. Tampered prerequisite/missing prereq/unsafe listing must fail before download or state promotion.
- In Windows CI check static full `7zFM.exe`, `7zG.exe`, `7z.exe`, `7z.dll`; real ZIP creation plus integrity test with `7z.exe`; full profile reapply is byte-identical state and disposable test cleanup. **No interactive GUI assertion** unless tested on a user workstation with captured evidence.

## GUI/manual user acceptance and Microsoft redistribution gate (2026-10-21)

- CI must run `tests/test_gui_acceptance.py` with **no vendor processes launched**. The console-equal `console.log` + `results.csv` + `result.json` must distinguish machine `NOT_VERIFIED` from explicit **HUMAN_ATTESTED_PASS**; never report green CI as Everything/grepWin/7-Zip interactive UI PASS.
- On a disposable corporate-approved Windows test PC, separately run [manual GUI acceptance](GUI_ACCEPTANCE_20261021.md) for Everything folder-only indexing/HTTP-service exclusion, grepWin synthetic read-only regex and full 7-Zip archive GUI. Review any vendor first-run UAC, service, auto-index, registry or setting writes. Never accept on MES production servers by default.
- Store approved evidence folder with selected tools, actual version/pin, executable SHA, operator observations and statuses. The harness cannot prove screenshots or GUI navigation; manually compare recorded results to what was observed.
- TCPView/PsPing remain **uninstallable by PortaKit** pending company OSS/security/legal decision on Sysinternals redistribution/internal transport, actual vendor hashes and exact-binary verification. No assumed EULA consent; no active network tests or bandwidth stress in production.
