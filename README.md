# portakit

Small Windows portable app manager. Python 3.11+, standard library only.

```powershell
python -I portakit.py list
python -I portakit.py --root portable install jq
.\portable\jq\jq.exe --version
python -I portakit.py --root portable update jq
python -I portakit.py --root portable remove jq
python -I portakit.py --json list
```

`catalog.json` pins GitHub release assets and SHA256 digests. The asset URLs
were checked against GitHub release metadata. Hash sources:
[Notepad++ release notes](https://github.com/notepad-plus-plus/notepad-plus-plus/releases/tag/v8.7.5),
[WinMerge manifest](https://github.com/ScoopInstaller/Extras/blob/777b50f8467b011b55f20a8790f2d8712b839663/bucket/winmerge.json),
[jq manifest](https://github.com/ScoopInstaller/Main/blob/da6f69ed0016a805c16d9d3d78386068a409da3a/bucket/jq.json).
Local asset downloads and `jq.exe --version` verification remain blocked by
the sandbox's unavailable proxy; these are published hashes, not locally
computed hashes. TODO hashes, if added, block downloads.

Downloads are capped at 100 MiB, including cache hits and injected downloaders,
and verified before extraction. ZIPs reject
unsafe paths and links; a single enclosing folder is flattened. EXE artifacts
become `ID.exe`. Updates replace the managed folder and preserve the exact
files or directories in `preserveOnUpdate` (directories replace packaged copies).
Installing an already installed ID is refused; use `update ID` instead.

The `github` plugin uses `kind: "github"`, `repo: "owner/repository"`, `tag`,
and `asset` to build the pinned download URL without an API request. An optional
`url` must match. Every catalog record must declare `kind: "github"`.
Edit the version, tag, asset, URL (if present), and digest together to update a pin.

`defaultConfig` maps relative file paths to UTF-8 text. Missing files are seeded
in staging after extraction and preservation; packaged and preserved files stay
intact. Notepad++ gets its `doLocalConf.xml` marker. WinMerge gets an empty
`WinMerge.ini`; use it with `WinMergeU.exe /inifile PATH\TO\WinMerge.ini`
([WinMerge manual](https://manual.winmerge.org/en/Command_line.html)).

State and cache live inside `--root` (default: `portable`). Failed swaps or
state writes restore the previous install. Close running apps before changing
them. After a successful commit, a locked `.old` backup may remain; JSON
`data.cleanupPending` names it. Inspect and delete it before retrying.
If a managed folder is missing, its `.old` backup is restored at the next
install/update/remove attempt. If both folders exist, inspect them before retrying.
Run one portakit command at a time.

`--json` returns `{ok, command, data, error}`; errors contain `code` and `message`.

| Exit | Meaning |
| --- | --- |
| 0 | Success |
| 2 | Usage |
| 3 | Catalog |
| 4 | Download |
| 5 | Integrity |
| 6 | Archive |
| 7 | Filesystem |
| 8 | State |
| 9 | Unknown or uninstalled ID |

```powershell
python -I -m unittest discover -s tests
```

Tests use temporary folders, mock ZIPs, and injected downloaders; no network.
SPEC steps 1–8 are implemented. Shims and offline bundles are deferred.
