"""Optional per-user classic Explorer context menus for PortaKit portable editors.

No administrator access, shell-extension DLL, HKCR, PATH, default association,
or implicit installation. Registry modifications ONLY on explicit install/remove.
Usage: python -I scripts/context_menu.py install|remove|status notepad++|winmerge
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import stat
import sys
import uuid
import winreg

# One canonical catalog/state validator; no duplicate permissive JSON parser.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portakit as core  # noqa: E402


OWNER = "greatgc-flow/portakit:context-menu:v1"
BASE = r"Software\Classes"
ENTRIES = {
    "notepad++": (
        (r"*\shell\PortaKit.NotepadPlusPlus.File", "Edit with Notepad++ (PortaKit)"),
    ),
    "winmerge": (
        (r"*\shell\PortaKit.WinMerge.File", "Compare with WinMerge (PortaKit)"),
        (r"Directory\shell\PortaKit.WinMerge.Folder",
         "Compare folder with WinMerge (PortaKit)"),
    ),
}
EXES = {"notepad++": "notepad++.exe", "winmerge": "WinMergeU.exe"}


class MenuError(Exception):
    pass


def registry_path(relative):
    return BASE + "\\" + relative


def check_safe_path(path):
    """Refuse all reparse/symlink ancestors and leaf; no path resolution through links."""
    absolute = Path(os.path.abspath(str(path)))
    for part in (*reversed(absolute.parents), absolute):
        try:
            st = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) &
                                            stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise MenuError("Reparse/junction/symlink path refused: " + str(part))


def managed_executable(root, app, repo_dir):
    """Resolve executable ONLY from PortaKit-managed state and its current catalog."""
    root = Path(os.path.abspath(str(root)))
    check_safe_path(root)
    catalog_path = repo_dir / "catalog.json"
    state_path = root / ".portakit-state.json"
    for path in (catalog_path, state_path):
        check_safe_path(path)
    try:
        catalog = core.load_catalog(catalog_path)
        state = core.read_state(root)
        tool = catalog[app]
        installed = state[app]
        dest = tool["dest"]
        if (installed["dest"] != dest or dest != app
                or installed["version"] != tool["version"]
                or installed.get("sha256") != tool["sha256"]):
            raise MenuError(app + ": managed installation pin/destination mismatch")
    except (OSError, ValueError, KeyError, TypeError, core.PortakitError) as exc:
        raise MenuError(app + ": managed installation/catalog not available: " + str(exc))
    exe = root / dest / EXES[app]
    check_safe_path(exe)
    if not exe.is_file():
        raise MenuError(app + ": expected managed executable absent: " + str(exe))
    return str(exe)


def expectations(app, exe):
    """Small fixed set of narrowly namespaced owned registry keys."""
    if not isinstance(exe, str) or '"' in exe or "\n" in exe or "\r" in exe:
        raise MenuError("Unsafe executable path")
    result = []
    for suffix, label in ENTRIES[app]:
        result.append((registry_path(suffix), {
            "": label,
            "Icon": exe + ",0",
            "PortaKitOwner": OWNER,
            "command": '"' + exe + '" "%1"',
        }))
    return result


def read_menu(path, registry=winreg):
    """Read an exact menu or None. Extra keys/values make it a collision."""
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, path, 0,
                              registry.KEY_READ) as root:
            root_values = {}
            index = 0
            while True:
                try:
                    name, value, kind = registry.EnumValue(root, index)
                    root_values[name] = (value, kind)
                    index += 1
                except OSError:
                    break
            children = []
            index = 0
            while True:
                try:
                    children.append(registry.EnumKey(root, index))
                    index += 1
                except OSError:
                    break
        command = None
        if children == ["command"]:
            with registry.OpenKey(registry.HKEY_CURRENT_USER, path + r"\command",
                                  0, registry.KEY_READ) as child:
                vals = []
                i = 0
                while True:
                    try:
                        vals.append(registry.EnumValue(child, i))
                        i += 1
                    except OSError:
                        break
                command = vals
                if registry.QueryInfoKey(child)[0] != 0:
                    command = None
        return root_values, children, command
    except FileNotFoundError:
        return None


def equals_managed(record, expected, registry=winreg):
    if record is None:
        return False
    values, children, command = record
    required = {key: (value, registry.REG_SZ) for key, value
                in expected.items() if key != "command"}
    return (children == ["command"] and values == required and
            command == [("", expected["command"], registry.REG_SZ)])


def create_menu(path, expected, registry=winreg):
    """Create a new exact key and return once completed; caller tracks cleanup."""
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, path, 0,
                              registry.KEY_WRITE) as root:
        for name, value in expected.items():
            if name != "command":
                registry.SetValueEx(root, name, 0, registry.REG_SZ, value)
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, path + r"\command", 0,
                              registry.KEY_WRITE) as child:
        registry.SetValueEx(child, "", 0, registry.REG_SZ, expected["command"])


def delete_menu(path, registry=winreg):
    """Remove only this menu's two fixed keys, tolerating a partial create."""
    try:
        registry.DeleteKey(registry.HKEY_CURRENT_USER, path + r"\command")
    except FileNotFoundError:
        pass
    registry.DeleteKey(registry.HKEY_CURRENT_USER, path)


def perform(command, app, root, repo_dir=None, registry=winreg):
    """Plan all collisions before writing; never overwrite foreign/changed keys."""
    if repo_dir is None:
        repo_dir = Path(__file__).resolve().parents[1]
    if app not in ENTRIES:
        raise MenuError("Unsupported editor; jq requires no shell integration")
    # Removing stale entries is possible even after the executable moved.
    # Use the stored path only when the entry already belongs to us, and
    # accept only a safe, exact menu payload before touching it.
    exe = managed_executable(root, app, repo_dir) if command == "install" else None
    plan = expectations(app, exe) if exe is not None else []
    if command in ("status", "remove"):
        plan = []
        for suffix, label in ENTRIES[app]:
            path = registry_path(suffix)
            snapshot = read_menu(path, registry)
            if snapshot is None:
                plan.append((path, None, "absent"))
                continue
            values, children, child = snapshot
            owner = values.get("PortaKitOwner")
            icon = values.get("Icon")
            if owner != (OWNER, registry.REG_SZ) or not icon or not isinstance(icon[0], str):
                plan.append((path, None, "foreign"))
                continue
            saved_exe = icon[0][:-2] if icon[0].endswith(",0") else None
            if saved_exe is None:
                plan.append((path, None, "modified"))
                continue
            spec = {"": label, "Icon": icon[0], "PortaKitOwner": OWNER,
                    "command": '"' + saved_exe + '" "%1"'}
            state = "owned" if equals_managed(snapshot, spec, registry) else "modified"
            plan.append((path, spec, state))
        if command == "status":
            # Registration ownership and current usability are different.
            # A missing/moved executable or absent managed state is STALE;
            # still-owned keys remain removable through explicit 'remove'.
            active_exe = None
            if any(st == "owned" for _, _, st in plan):
                try:
                    active_exe = managed_executable(root, app, repo_dir)
                except MenuError:
                    pass
            items = []
            for path, expected, state in plan:
                if state == "owned":
                    saved_exe = expected["Icon"][:-2]
                    if (active_exe is None or
                            os.path.normcase(os.path.abspath(saved_exe)) !=
                            os.path.normcase(os.path.abspath(active_exe))):
                        state = "stale"
                items.append({"key": path, "state": state})
            return {"changed": False, "items": items}
        if any(st in ("foreign", "modified") for _, _, st in plan):
            raise MenuError("Refusing to remove foreign/modified Explorer key")
        changed = False
        for path, _, state in plan:
            if state == "owned":
                delete_menu(path, registry)
                changed = True
        return {"changed": changed, "items": [
            {"key": p, "state": "removed" if st == "owned" else "absent"}
            for p, _, st in plan]}
    if command != "install":
        raise MenuError("Unsupported command")
    new = []
    for path, expected in plan:
        current = read_menu(path, registry)
        if current is None:
            new.append((path, expected))
        elif not equals_managed(current, expected, registry):
            raise MenuError("Registry key already exists with different values: " + path)
    created = []
    try:
        for path, expected in new:
            created.append(path)
            create_menu(path, expected, registry)
    except Exception:
        # Only keys that were absent in our preflight may be rolled back.
        for path in reversed(created):
            try:
                delete_menu(path, registry)
            except OSError:
                pass  # Reportable partial cleanup; never delete nonowned keys.
        raise
    return {"changed": bool(new), "items": [
        {"key": p, "state": "installed" if any(n == p for n, _ in new)
         else "already-installed"} for p, _ in plan]}


class Echo:
    """Emit each console line byte-identically into an evidence file."""
    def __init__(self, filename):
        self.file = Path(filename)
        # The log is a separate evidence artifact, never an install payload.
        # Reject junction/symlink ancestors both before and after parent mkdir.
        core.check_links(self.file)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        core.check_links(self.file)
        self.stream = self.file.open("x", encoding="utf-8", newline="\n")

    def line(self, message):
        line = str(message)
        print(line, flush=True)
        self.stream.write(line + "\n")
        self.stream.flush()

    def close(self):
        self.stream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "install", "remove"))
    parser.add_argument("app", choices=("notepad++", "winmerge"))
    parser.add_argument("--root", default="portable")
    parser.add_argument("--log-file",
                        help="Evidence log path, default ROOT/.portakit-evidence/<unique>.log")
    args = parser.parse_args(argv)
    root = Path(os.path.abspath(args.root))
    log = args.log_file or str(root / ".portakit-evidence" /
          ("context-menu-" + datetime.now().strftime("%Y%m%d-%H%M%S")
           + "-" + uuid.uuid4().hex[:8] + ".log"))
    try:
        # The status command also writes a log. Keep every command's evidence
        # out of the managed app folders and transient install/backup paths.
        core.check_evidence_location(log, root, "install")
        sink = Echo(log)
    except (OSError, core.PortakitError) as exc:
        print("ERROR: could not create evidence log: " + str(exc), file=sys.stderr)
        return 1
    try:
        sink.line("OPERATION: " + args.command + " " + args.app)
        sink.line("REGISTRY: HKCU\\" + BASE + " (current user only)")
        sink.line("ROOT: " + str(root))
        value = perform(args.command, args.app, root)
        for row in value["items"]:
            sink.line(row["state"].upper() + ": HKCU\\" + row["key"])
        sink.line("RESULT: " + ("CHANGED" if value["changed"] else "NO_CHANGE"))
        sink.line("EVIDENCE: " + str(Path(log).absolute()))
        return 0
    except (MenuError, OSError, ValueError) as exc:
        sink.line("ERROR: " + str(exc))
        sink.line("RESULT: FAILED (no foreign key overwritten)")
        sink.line("EVIDENCE: " + str(Path(log).absolute()))
        return 1
    finally:
        sink.close()


if __name__ == "__main__":
    raise SystemExit(main())
