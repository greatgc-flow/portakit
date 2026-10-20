# Full component review — 2026-10-20

Scope: `greatgc-flow/portakit`, latest main before this change `407a686dcfcc57e5192729fc59cf8606c7a46bc5`. Principle: **minimum change**, reviewed upstream defaults win unless a verified user benefit justifies explicit opt-in. Distinguish real tested behavior from manual acceptance.

| Area / feature | Actual current baseline | Decision | Rationale |
| --- | --- | --- | --- |
| Notepad++ core (portable x64) | SHA-pinned vendor ZIP, no shell integration | **KEEP DEFAULT** install | Avoid forced file associations/registry and unknown profile changes |
| Notepad++ recommended settings | On `install --recommended` or `configure`: local 4-space indentation + ComparePlus/JsonTools pinned plugins | **KEEP OPT-IN** | Plugins load executable third-party code; don't silently install |
| Notepad++ Explorer menu | Before change: not provided | **ADD OPTIONAL** | Simple per-user classic `Edit with Notepad++` action for file, no admin or COM-DLL installation; reversible |
| WinMerge core (portable x64) | SHA-pinned ZIP, vendor `MergePlugins` | **KEEP DEFAULT** install | Avoid vendor defaults override, shell registration, machine changes |
| WinMerge recommended Office scripts | Verify four bundled `.sct` and seed local [WinMerge] INI | **KEEP OPT-IN** | No extra downloads; licensed Office COM required for actual comparisons |
| WinMerge Explorer menu | Before change: not provided | **ADD OPTIONAL** | Per-user classic file/folder action, open chosen path in WinMerge to specify comparison partner; no claims of native two-file shell extension |
| jq | SHA-pinned single executable | **KEEP DEFAULT** | No plugin/config/shell menu is needed for a CLI filter; no PATH/shim by default |
| Catalog pins/validation | Three exact versions, HTTPS, SHA-256, safe destination paths, duplicates rejected | **KEEP** | Prevent mutable installs and unreviewed silent upgrades |
| Extract/download | Bounded size, SHA check, safe ZIP stage, symlinks/reparse rejected | **KEEP** | Tests cover zip slip, reparse, truncation, rollback |
| Install/configure/update | Mutex, temp stage, atomic directory swap with backup, config preservation | **KEEP** | Already tested; avoid forced settings/registry changes |
| Remove | Deliberately deletes managed destination and state; does not remove external registry data | **KEEP** | Explicit destructive operation. If optional shell integration was added, unregister it separately before removing apps |
| Console/JSON | Stable error codes, JSON envelope for PortaKit, log capture for shell commands | **KEEP** and add evidence for menu script | Shell script stdout is duplicated verbatim to timestamped local log |
| Windows integration | No PATH, COM registration, HKCR or admin requirement | **OPTION ONLY** | HKCU Classic context menu must never be installed by ordinary `install`, `configure` or `update` |
| Windows CI | Python 3.11/3.14 offline unit tests plus live asset smoke | **EXTEND REGISTRY COVERAGE** | Mock-owned collision cases and ephemeral real HKCU self-cleaning smoke |
| Excel/Word/PowerPoint/Visio | Office not installed/licensed in CI | **BACKLOG (P1)** | Real Office COM and GUI comparisons remain unverified (see BACKLOG) |

## Optional classic Explorer menu design

**Actions**: standalone `scripts/ContextMenu.cmd install|status|remove notepad++|winmerge` or Python equivalent. Default root is current working directory's `portable`, matching PortaKit. `--root DIR` supported. The menu integration cannot run automatically.

**Registry scope**: exclusively `HKEY_CURRENT_USER\Software\Classes\*\shell\PortaKit.NotepadPlusPlus.File`, `*\shell\PortaKit.WinMerge.File`, and `Directory\shell\PortaKit.WinMerge.Folder`. The corresponding `command` subkeys launch absolute managed executable path with quoted `"%1"`. Only HKCU current user; **no admin, HKCR, PATH, default association, global config or shell DLL registration**. The menu entries contain an exact ownership marker; foreign or modified keys are never overwritten/deleted. Registry writes occur only on explicit `install`/`remove`; `status` is read-only apart from its console evidence log. Relative paths, paths containing spaces, symlinks, unmanaged targets and key collisions are tested.

**Limitations**: This is the classic Explorer context menu. On Windows 11, choose **Show more options / Shift+F10** if the entry is absent from the main menu. A selected WinMerge file/folder opens the application with that path; the user chooses the comparison partner there. This is **not** the WinMerge vendor's COM ShellExtension capable of two selected paths or cross-window Compare To; that advanced function remains an optional backlog task. A newly moved PortaKit root makes recorded absolute shell commands stale; remove the old owned keys before installing at the new location, or run `status` and inspect.

**References**:
- [Notepad++ official user manual: portable edition and per-user classic shell menu](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/shell-extension.md).
- [WinMerge official manual: Explorer shell integration](https://manual.winmerge.org/en/Open_paths.html).
- [WinMerge official command-line manual](https://manual.winmerge.org/en/Command_line.html).

## Overall assessment

All three packaged tools and their surrounding lifecycle components have an explicit decision. No default preference is changed. The only newly introduced OS integration is the separate, removable, per-user opt-in classic Explorer menu. E2E context-click rendering on a desktop and Office4 COM verification still require user Windows workstation evidence; automated registry and command templates alone do not prove Windows 11 native shell UI behavior.
