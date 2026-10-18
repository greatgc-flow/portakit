"""Small, standard-library portable app manager for Windows."""

import argparse
import hashlib
import http.client
import json
import msvcrt
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import zlib


DEFAULT_CATALOG = Path(__file__).with_name("catalog.json")
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
EXIT_CODES = dict(ok=0, usage=1, catalog=2, fetch=3, archive=4, state=5, busy=6)
DEVICE_NAME = re.compile(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?")


class PortakitError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_reparse(path):
    try:
        info = Path(path).lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


def check_links(path):
    """Check every component before resolution or access; retain '..' components."""
    absolute = Path.cwd() / path
    for component in (*reversed(absolute.parents), absolute):
        if is_reparse(component):
            raise PortakitError("state", f"Reparse path rejected: {component}")


def path_parts(value, field, code="catalog"):
    """Path rule (syntax only): returns the segments of a safe relative path."""
    if not isinstance(value, str) or not value:
        raise PortakitError(code, f"{field}: expected a relative path")
    parts = value.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") or p.endswith((".", " "))
           or re.search(r'[<>:"|?*\x00-\x1f]', p) or DEVICE_NAME.fullmatch(p)
           for p in parts):
        raise PortakitError(code, f"{field}: unsafe relative path")
    return parts


def safe_path(root, value, field, code="catalog"):
    """Path rule plus link rule: no existing component may be a reparse point."""
    parts = path_parts(value, field, code)
    check_links(root)
    root = Path(root).resolve()
    target = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if is_reparse(current):
            raise PortakitError(code, f"{field}: reparse path rejected")
    if not target.resolve().is_relative_to(root):
        raise PortakitError(code, f"{field}: path escapes root")
    return target


def check_dest(value, field="dest", code="catalog"):
    parts = path_parts(value, field, code)
    if len(parts) != 1:
        raise PortakitError(code, f"{field}: expected a single path segment")
    name = parts[0]
    if name.lower().startswith(".portakit") or name.lower().endswith(".old"):
        raise PortakitError(code, f"{field}: reserved name")
    return name


def load_catalog(path, root=None):
    check_links(path)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PortakitError("state", f"catalog: {exc}") from exc
    except ValueError as exc:
        raise PortakitError("catalog", f"catalog: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        raise PortakitError("catalog", "catalog.tools: expected a list")
    result = {}
    destinations = set()
    for tool in data["tools"]:
        if not isinstance(tool, dict):
            raise PortakitError("catalog", "catalog.tools: expected objects")
        for field in ("id", "version", "url", "sha256", "artifact", "dest"):
            if not isinstance(tool.get(field), str) or not tool[field]:
                raise PortakitError("catalog", f"{field}: expected a nonempty string")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_+.-]*", tool["id"]) or tool["id"] in result:
            raise PortakitError("catalog", "id: invalid or duplicate")
        path_parts(tool["id"] + ".exe", "id")
        try:
            url = urllib.parse.urlsplit(tool["url"])
            if url.scheme != "https" or not url.hostname or any(c.isspace() for c in tool["url"]):
                raise ValueError("expected HTTPS URL with a host")
        except ValueError as exc:
            raise PortakitError("catalog", f"url: {exc}") from exc
        if not re.fullmatch(r"[a-fA-F0-9]{64}", tool["sha256"]):
            raise PortakitError("catalog", "sha256: expected 64 hex digits (placeholders are rejected)")
        if tool["artifact"] not in ("zip", "exe"):
            raise PortakitError("catalog", "artifact: expected zip or exe")
        dest = check_dest(tool["dest"])
        if dest.lower() in destinations:
            raise PortakitError("catalog", "dest: duplicate")
        preserve = tool.get("preserveOnUpdate", [])
        if not isinstance(preserve, list):
            raise PortakitError("catalog", "preserveOnUpdate: expected a list")
        for item in preserve:
            path_parts(item, "preserveOnUpdate")
        destinations.add(dest.lower())
        result[tool["id"]] = dict(tool, sha256=tool["sha256"].lower(), preserveOnUpdate=preserve)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PortakitError("usage", message)


def check_download_size(size):
    if size > MAX_DOWNLOAD_BYTES:
        raise PortakitError("fetch", f"Download size exceeds {MAX_DOWNLOAD_BYTES} bytes")


def download(url, destination):
    check_links(destination)
    try:
        response = urllib.request.urlopen(url, timeout=60)
    except OSError as exc:
        raise urllib.error.URLError(exc) from exc
    with response:
        length = response.headers.get("Content-Length", "")
        if length.isdigit():
            check_download_size(int(length))
        total = 0
        check_links(destination)
        with Path(destination).open("wb") as out:
            while True:
                try:
                    chunk = response.read(min(64 * 1024, MAX_DOWNLOAD_BYTES - total + 1))
                except OSError as exc:
                    raise urllib.error.URLError(exc) from exc
                if not chunk:
                    break
                total += len(chunk)
                check_download_size(total)
                out.write(chunk)


def fetch_archive(tool, target, downloader=None):
    """Download straight to the dl temp and verify its SHA256 before anything is extracted."""
    try:
        check_links(target)
        (downloader or download)(tool["url"], target)
        check_links(target)
        check_download_size(target.stat().st_size)
        with target.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
    except PortakitError:
        raise
    except (urllib.error.URLError, http.client.HTTPException) as exc:
        raise PortakitError("fetch", f"download: {exc}") from exc
    except OSError as exc:
        raise PortakitError("state", f"download: {exc}") from exc
    if actual != tool["sha256"].lower():
        raise PortakitError("fetch", "SHA256 mismatch; nothing installed")


def extract(artifact, tool, destination):
    check_links(artifact)
    check_links(destination)
    destination = Path(destination)
    if tool["artifact"] == "exe":
        target = safe_path(destination, tool["id"] + ".exe", "id")
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, target)
        return
    try:
        with zipfile.ZipFile(artifact) as archive:
            members = []
            paths = {}
            for info in archive.infolist():
                name = info.filename.replace("\\", "/")
                directory = name.endswith("/")
                name = name[:-1] if directory else name
                safe_path(destination, name, "zip member")
                mode = info.external_attr >> 16
                if (info.external_attr & 0x400 or stat.S_ISLNK(mode)
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise PortakitError("archive", "zip member: reparse or special file")
                key = name.lower()
                if key in paths:
                    raise PortakitError("archive", "zip member: duplicate path")
                paths[key] = directory
                members.append((info, name, directory))
            for key in paths:
                parts = key.split("/")
                if any(paths.get("/".join(parts[:i])) is False for i in range(1, len(parts))):
                    raise PortakitError("archive", "zip member: file used as directory")
            if not any(not directory for _, _, directory in members):
                raise PortakitError("archive", "zip: no files")
            roots = {name.split("/")[0] for _, name, _ in members}
            flatten = len(roots) == 1 and all(directory or "/" in name
                                             for _, name, directory in members)
            plan = []
            for info, name, directory in members:
                if flatten:
                    name = name.partition("/")[2]
                if name:
                    plan.append((info, safe_path(destination, name, "zip member"), directory))
            for info, target, directory in plan:
                if directory:
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open("wb") as out:
                        shutil.copyfileobj(source, out)
    except PortakitError as exc:
        raise PortakitError("archive", str(exc)) from exc
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError) as exc:
        raise PortakitError("archive", f"zip: {exc}") from exc


def read_state(root):
    path = Path(root) / ".portakit-state.json"
    check_links(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        destinations = set()
        for identifier, item in data.items():
            if not isinstance(item, dict) or not isinstance(item.get("version"), str):
                raise ValueError(f"{identifier}.version: expected a string")
            if "sha256" in item and not (isinstance(item["sha256"], str)
                                         and re.fullmatch(r"[a-fA-F0-9]{64}", item["sha256"])):
                raise ValueError(f"{identifier}.sha256: expected 64 hex digits")
            dest = check_dest(item.get("dest"), "dest", "state")
            if dest.lower() in destinations:
                raise ValueError("dest: duplicate")
            destinations.add(dest.lower())
        return data
    except (OSError, ValueError, PortakitError) as exc:
        raise PortakitError("state", f"state: {exc}") from exc


def write_state(root, state):
    target = Path(root) / ".portakit-state.json"
    temporary = target.with_name(f".portakit-state.{uuid.uuid4().hex}.tmp")
    check_links(target)
    check_links(temporary)
    try:
        with temporary.open("x", encoding="utf-8") as out:
            json.dump(state, out, indent=2)
            out.write("\n")
        check_links(target)
        check_links(temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def reject_links(path):
    if is_reparse(path):
        raise PortakitError("state", f"Reparse path rejected: {path}")
    if path.is_dir():
        for child in path.iterdir():
            reject_links(child)


def unlink_file(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except PermissionError:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        os.unlink(path)


def unlink_link(path):
    """Remove a link itself; never touches what it points at."""
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE, follow_symlinks=False)
    except (OSError, NotImplementedError):
        pass
    try:
        os.rmdir(path)  # junctions and directory symlinks
    except OSError:
        os.unlink(path)  # file symlinks


def _delete(path):
    path = Path(path)
    if is_reparse(path):
        unlink_link(path)
    elif path.is_dir():
        with os.scandir(path) as entries:
            children = [entry.path for entry in entries]
        for child in children:
            _delete(child)
        try:
            os.rmdir(path)
        except PermissionError:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            os.rmdir(path)
    else:
        unlink_file(path)


def remove_tree(path):
    check_links(Path(path).parent)  # The leaf itself may be a link to unlink.
    _delete(path)


def preserve_paths(tool, source, stage):
    for relative in tool.get("preserveOnUpdate", []):
        original = safe_path(source, relative, "preserveOnUpdate", "state")
        if not os.path.lexists(original):
            continue
        reject_links(original)
        target = safe_path(stage, relative, "preserveOnUpdate", "state")
        if os.path.lexists(target):
            remove_tree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if original.is_dir():
            shutil.copytree(original, target)
        else:
            shutil.copy2(original, target)


def rename(source, target):
    """os.rename only: an existing target makes it fail instead of being replaced."""
    try:
        os.rename(source, target)
    except PermissionError as exc:
        raise PortakitError("busy", f"cannot rename {source} to {target}: {exc}. "
                            "Close running applications and retry.") from exc


def rollback(dest, old, staged, moved_old):
    try:
        if staged:
            remove_tree(dest)
        if moved_old:
            os.rename(old, dest)
    except OSError as exc:
        raise PortakitError("state", f"Rollback failed; {dest} and {old} left in place "
                            f"(see the both-exist rule): {exc}") from exc


def dest_paths(root, name):
    return safe_path(root, name, "dest", "state"), Path(root) / (name + ".old")


def check_dest_kind(dest):
    if os.path.lexists(dest) and (is_reparse(dest) or not dest.is_dir()):
        raise PortakitError("state", f"{dest} is a file or link, not a directory")


def deploy(tool, root, state, downloader, update_mode):
    identifier = tool["id"]
    name = tool["dest"]
    dest, old = dest_paths(root, name)
    dl = root / f".portakit-dl-{identifier}.tmp"
    stage = root / f".portakit-stage-{identifier}.tmp"
    entry = dict(version=tool["version"], sha256=tool["sha256"].lower(), dest=name)
    moved_old = staged = False
    for temporary in (dl, stage):
        check_links(temporary)
    try:
        for leftover in (dl, stage):
            if os.path.lexists(leftover):
                remove_tree(leftover)
        fetch_archive(tool, dl, downloader)
        stage.mkdir()
        extract(dl, tool, stage)
        if update_mode:
            preserve_paths(tool, dest, stage)
        if os.path.lexists(dest):
            rename(dest, old)
            moved_old = True
        rename(stage, dest)
        staged = True
        write_state(root, dict(state, **{identifier: entry}))
    except BaseException as exc:
        rollback(dest, old, staged, moved_old)
        if isinstance(exc, PortakitError) or not isinstance(exc, Exception):
            raise
        raise PortakitError("state", f"{'update' if update_mode else 'install'}: {exc}") from exc
    finally:
        for leftover in (dl, stage):
            try:
                if os.path.lexists(leftover):
                    remove_tree(leftover)
            except OSError:
                pass
    if moved_old:
        try:
            remove_tree(old)
        except OSError:
            print(f"warning: could not delete {old}; delete it before the next operation on {identifier}",
                  file=sys.stderr)
    return dict(id=identifier, version=tool["version"], dest=str(dest), changed=True)


def install(tool, root, downloader=None):
    check_links(root)
    root = Path(root).resolve()
    state = read_state(root)
    identifier = tool["id"]
    if identifier in state:
        raise PortakitError("state", f"{identifier}: already installed; use update {identifier}")
    for owner, installed in state.items():
        if installed["dest"].lower() == tool["dest"].lower():
            raise PortakitError("state", f"{tool['dest']}: destination already owned by {owner}")
    dest, old = dest_paths(root, tool["dest"])
    check_dest_kind(dest)
    for path in (dest, old):
        if os.path.lexists(path):
            raise PortakitError("state", f"{path} exists and is unmanaged; delete or rename it")
    return deploy(tool, root, state, downloader, update_mode=False)


def update(tool, root, downloader=None):
    check_links(root)
    root = Path(root).resolve()
    state = read_state(root)
    identifier = tool["id"]
    if identifier not in state:
        raise PortakitError("state", f"{identifier}: not installed")
    installed = state[identifier]
    if installed["dest"] != tool["dest"]:
        raise PortakitError("state", f"{identifier}: dest changed; remove {identifier} and install again")
    dest, old = dest_paths(root, installed["dest"])
    has_dest, has_old = os.path.lexists(dest), os.path.lexists(old)
    if has_dest and has_old:
        raise PortakitError("state", f"{dest} and {old} both exist; if {dest} is good delete {old}, "
                            f"else delete {dest} and rename {old} to {dest}")
    if has_old:
        check_links(old)
        rename(old, dest)
    check_dest_kind(dest)
    sha256 = tool["sha256"].lower()
    if (os.path.lexists(dest) and installed.get("version") == tool["version"]
            and installed.get("sha256") == sha256):
        return dict(id=identifier, version=tool["version"], dest=str(dest), changed=False)
    return deploy(tool, root, state, downloader, update_mode=True)


def remove(identifier, root):
    check_links(root)
    root = Path(root).resolve()
    state = read_state(root)
    if identifier not in state:
        raise PortakitError("state", f"{identifier}: not installed")
    name = check_dest(state[identifier]["dest"], "dest", "state")
    dest, old = root / name, root / (name + ".old")  # no link check: a link dest is unlinked
    try:
        if os.path.lexists(dest):
            if not is_reparse(dest) and not dest.is_dir():
                raise PortakitError("state", f"{dest} is a file, not a directory")
            remove_tree(dest)
        if os.path.lexists(old):
            remove_tree(old)
        remaining = dict(state)
        del remaining[identifier]
        write_state(root, remaining)
    except PortakitError:
        raise
    except PermissionError as exc:
        raise PortakitError("busy", f"remove: {exc}. Close running applications and retry.") from exc
    except OSError as exc:
        raise PortakitError("state", f"remove: {exc}") from exc
    return dict(id=identifier)


class RootLock:
    """Byte-0 lock on ROOT\\.portakit-lock; Windows releases it if the process dies."""

    def __init__(self, root):
        self.path = Path(root) / ".portakit-lock"
        self.fd = None

    def __enter__(self):
        check_links(self.path)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_BINARY)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            os.close(fd)
            raise PortakitError("busy", f"another portakit holds {self.path}") from exc
        self.fd = fd
        return self

    def __exit__(self, *exc_info):
        try:
            os.lseek(self.fd, 0, 0)
            msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(self.fd)


def cleanup_temps(root):
    check_links(root)
    with os.scandir(root) as entries:
        names = [entry.path for entry in entries
                 if entry.name.startswith(".portakit-") and entry.name.endswith(".tmp")]
    for path in names:
        remove_tree(path)


def execute(args, downloader):
    command, root, identifier = args.command, args.root, args.id
    check_links(root)
    if command == "list":
        return {"items": list(load_catalog(DEFAULT_CATALOG, root).values())}
    catalog = None if command == "remove" else load_catalog(DEFAULT_CATALOG, root)
    root.mkdir(parents=True, exist_ok=True)
    with RootLock(root):
        cleanup_temps(root)
        state = read_state(root)
        if command == "install":
            if identifier not in catalog:
                raise PortakitError("usage", f"Unknown ID: {identifier}")
            return install(catalog[identifier], root, downloader)
        if command == "update":
            if identifier not in state:
                raise PortakitError("state", f"{identifier}: not installed")
            if identifier not in catalog:
                raise PortakitError("state", f"{identifier}: not in catalog; run remove {identifier}")
            return update(catalog[identifier], root, downloader)
        return remove(identifier, root)


def main(argv=None, downloader=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = None
    args = None
    try:
        parser = Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--root", type=Path, default=Path("portable"))
        parser.add_argument("command", choices=("list", "install", "update", "remove"))
        parser.add_argument("id", nargs="?")
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:  # -h/--help: human text, no envelope
            return exc.code if isinstance(exc.code, int) else 0
        command = args.command
        if (command == "list") != (args.id is None):
            raise PortakitError("usage", "list takes no ID; install/update/remove require ID")
        data = execute(args, downloader)
        result = dict(ok=True, command=command, data=data, error=None)
        code = 0
    except Exception as exc:
        name = (exc.code if isinstance(exc, PortakitError) else
                "fetch" if isinstance(exc, http.client.HTTPException) else "state")
        result = dict(ok=False, command=command, data=None,
                      error=dict(code=name, message=str(exc)))
        code = EXIT_CODES[name]
    if "--json" in argv:
        print(json.dumps(result))
    elif result["ok"]:
        if command == "list":
            for tool in result["data"]["items"]:
                print(f'{tool["id"]}\t{tool["version"]}')
        else:
            print(f"{command}: {args.id}")
    else:
        print(result["error"]["message"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
