# Independent editor plugin selection — safe personal kit v2

## GUI visibility and intent (2026-10-30)

The optional `MyToolkitGUI.cmd` selector shows the **currently chosen editor plugins** (up to six from this research report) with their required `notepad++` or `winmerge` host and a state that is not equivalent to corporate approval. The chosen dropdown also states whether its host is selected. `PINNED METADATA` means a vendor plugin has a known pin in the recommended profile, **not** that GUI automatically installs or has approved business use/redistribution. `RESEARCH ONLY` means no approved standalone plugin apply option exists.

An imported kit that recorded a plugin as research-only retains that pending state until explicitly removed and re-selected, even if newer source metadata becomes pinned. Removing its host from the personal kit removes associated selections; none of these UI operations writes plugin files or changes Windows configuration. Headless tests validate displayed mapping, host selection and frozen intent, but real Tk GUI/DPI and keyboard acceptance remain **HUMAN_NOT_VERIFIED**.

User-supplied 31-page research source lists 6 plugin families: ComparePlus, JsonTools, CSV Lint, NppExec (Notepad++), xdocdiff, Merge7z (WinMerge). Two currently have SHA/version pins nested under the Notepad++ **recommended** profile; the other four remain research-only. The source intake remains authoritative for all six IDs. **SHA-pinned metadata is not corporate license or redistribution approval**, and none of the six is independently installable through personal kit v2.

## CLI (no download/install)

```cmd
scripts\MyToolkit.cmd plugins
scripts\MyToolkit.cmd create --name log-ops --tool notepad++ --plugin compareplus --plugin csvlint-npp --out LogOps.json
scripts\MyToolkit.cmd plan --kit LogOps.json
scripts\MyToolkit.cmd build --kit LogOps.json --root D:\Portable --yes
:: Fails closed: plugin selection is metadata-only.
scripts\MyToolkit.cmd build --kit LogOps.json --root D:\Portable --skip-pending --yes
:: Only pinned HOST applications are eligible; selected plugins are still excluded.
```

Select the host application explicitly first (`--tool notepad++` or `--tool winmerge`). Mixed editor choices require both hosts. GUI `scripts\MyToolkitGUI.cmd` has an optional 'Editor plugins' dropdown with Add/Remove; it only saves a JSON kit. Plugins are **not included** in the existing 151 software ID count.

- Existing kits **v1** (no plugins) remain byte-compatible, valid and safely buildable with their prior opt-in behavior. Creating plugin selections automatically uses schema **v2** with `pluginSelections: [{id,host,status,lockedPin}]` and exact host version/SHA/dest locks.
- `PINNED_METADATA_ONLY` records ComparePlus and JsonTools nested catalog pins (JsonTools research ID `jsontools-npp` maps to upstream id `jsontools`). This does **not** authorize a download, apply operation or corporate distribution.
- `RESEARCH_ONLY` records CSV Lint, NppExec, xdocdiff and Merge7z with `lockedPin=null`, never allowing an arbitrary vendor URL/hash in user config.
- v2 `build --yes` **fails closed** on any plugin choice. `--skip-pending` explicitly permits only separately selected pinned HOST applications; not plugins. A v2 `--recommended` attempt is rejected because the existing legacy recommended bundle would bypass individual plugin consent. Legacy v1 `--recommended` remains unchanged but is not part of individual plugin selection.
- Saved v2 pending choices stay pending even if an upstream catalog pin is later introduced. Explicit remove/reselect into a newly saved kit is necessary; mismatching pinned plugin hashes fail before any installation action.
- `offline_assets.py` exports the original host files only; `editorPluginsNotPackaged` lists excluded selections. `kit_footprint.py` treats v2 plugin selections as unmeasured so a requested budget remains `UNKNOWN_INCOMPLETE` unless all selections, including plugin choices, are measured separately. Neither tool copies or executes plugin DLLs.
- Files and local logs are new-only. Personal kit GUI does not install any binaries, edit Windows services/registry, or run an industrial network listener. Existing tool GUI and WinMerge Office acceptance remain human-not-verified.

## Optional implementation progress — offline pinned plugin application (2026-10-30)

An **additional explicit** `scripts/plugin_offline.py` supports separately permissioned, already catalog SHA-pinned ComparePlus/JsonTools plugin deployment only from locally provided original ZIP files. It requires an installed, managed Notepad++ host, `--yes --policy-approved`, a verified offline source, stage re-verification, no unmanaged overwrite and per-plugin rollback. This is **not** performed by the normal v2 `MyToolkit.cmd build` path or selection-only GUI. Full procedure and operator gates: [PLUGIN_OFFLINE_APPLY.md](PLUGIN_OFFLINE_APPLY.md). Other four plugins remain research-only; corporate licensing/transfer and real GUI acceptance are still not verified.

## Remaining gated implementation

**Individual plugin deployment is NOT implemented.** It requires official vendor licenses (company use and separate transfer/redistribution), compatible host versions, exact individual vendor archive and SHA, safety/rollback preflight and explicit per-plugin permissions, new test fixtures, updated installer behavior, and actual approved Windows GUI acceptance. The previous `--recommended` legacy path has not been removed or modified. No Release is authorized by this work.
