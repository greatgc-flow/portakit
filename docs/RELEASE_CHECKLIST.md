# Release acceptance checklist

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
