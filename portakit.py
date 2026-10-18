"""Small, standard-library portable app manager for Windows."""

import argparse
import hashlib
import http.client
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import shutil
import stat
import urllib.request
import urllib.parse
import uuid
import zipfile
import zlib


DEFAULT_CATALOG = Path(__file__).with_name("catalog.json")
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
EXIT_CODES = dict(ok=0, usage=2, catalog=3, download=4, integrity=5,
                  archive=6, filesystem=7, state=8, not_found=9)


class PortakitError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_reparse(path):
    try:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


def safe_path(root, value, field):
    if not isinstance(value, str) or not value:
        raise PortakitError("catalog", f"{field}: expected a relative path")
    parts = value.replace("\\", "/").split("/")
    if (PureWindowsPath(value).drive or any(
            p in ("", ".", "..") or p.endswith((".", " "))
            or re.search(r'[<>:"|?*\x00-\x1f]', p)
            or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", p)
            for p in parts)):
        raise PortakitError("catalog", f"{field}: unsafe relative path")
    root = Path(root).resolve()
    target = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if is_reparse(current):
            raise PortakitError("catalog", f"{field}: reparse path rejected")
    if not target.resolve().is_relative_to(root):
        raise PortakitError("catalog", f"{field}: path escapes root")
    return target


def managed_dest(root, value, others=()):
    dest = safe_path(root, value, "dest")
    if (any(part.lower().startswith(".portakit") or part.lower().endswith(".old")
            for part in dest.relative_to(Path(root).resolve()).parts)
            or any(dest == old or dest in old.parents or old in dest.parents for old in others)):
        raise PortakitError("catalog", "dest: reserved or overlapping path")
    return dest


def github_url(tool):
    if tool.get("kind") != "github":
        raise PortakitError("catalog", "kind: expected github")
    repo = tool.get("repo")
    if (not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo, flags=re.ASCII)
            or any(part in (".", "..") for part in repo.split("/"))):
        raise PortakitError("catalog", "repo: expected owner/repository")
    tag = tool.get("tag")
    if (not isinstance(tag, str) or not tag or tag in (".", "..")
            or any(c.isspace() or ord(c) < 32 for c in tag)):
        raise PortakitError("catalog", "tag: expected a pinned release tag")
    asset = tool.get("asset")
    if not isinstance(asset, str) or not asset or "/" in asset or "\\" in asset:
        raise PortakitError("catalog", "asset: expected a release filename")
    safe_path(Path.cwd(), asset, "asset")
    quote = urllib.parse.quote
    url = f"https://github.com/{repo}/releases/download/{quote(tag, safe='')}/{quote(asset, safe='')}"
    if "url" in tool and tool["url"] != url:
        raise PortakitError("catalog", "url: conflicts with github repo/tag/asset")
    return url


def load_catalog(path, root):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PortakitError("catalog", f"catalog: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        raise PortakitError("catalog", "catalog.tools: expected a list")
    result = {}
    destinations = []
    for tool in data["tools"]:
        if not isinstance(tool, dict):
            raise PortakitError("catalog", "catalog.tools: expected objects")
        tool = dict(tool, url=github_url(tool))
        for field in ("id", "version", "url", "sha256", "artifact", "dest"):
            if not isinstance(tool.get(field), str) or not tool[field]:
                raise PortakitError("catalog", f"{field}: expected a nonempty string")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_+.-]*", tool["id"]) or tool["id"] in result:
            raise PortakitError("catalog", "id: invalid or duplicate")
        try:
            url = urllib.parse.urlsplit(tool["url"])
            if url.scheme != "https" or not url.hostname or any(c.isspace() for c in tool["url"]):
                raise ValueError("expected HTTPS URL with a host")
        except ValueError as exc:
            raise PortakitError("catalog", f"url: {exc}") from exc
        if not re.fullmatch(r"[a-fA-F0-9]{64}|TODO", tool["sha256"]):
            raise PortakitError("catalog", "sha256: expected 64 hex digits or TODO")
        if tool["artifact"] not in ("zip", "exe"):
            raise PortakitError("catalog", "artifact: expected zip or exe")
        dest = managed_dest(root, tool["dest"], destinations)
        preserve = tool.get("preserveOnUpdate", [])
        if not isinstance(preserve, list):
            raise PortakitError("catalog", "preserveOnUpdate: expected a list")
        for item in preserve:
            safe_path(dest, item, "preserveOnUpdate")
        config = tool.get("defaultConfig", {})
        if not isinstance(config, dict):
            raise PortakitError("catalog", "defaultConfig: expected relative paths mapped to text")
        config_paths = []
        for relative, content in config.items():
            path = safe_path(dest, relative, "defaultConfig")
            key = path.as_posix().casefold()
            if (not isinstance(content, str) or any(key == old or key.startswith(old + "/")
                    or old.startswith(key + "/") for old in config_paths)):
                raise PortakitError("catalog", "defaultConfig: expected text and nonoverlapping file paths")
            config_paths.append(key)
        destinations.append(dest)
        result[tool["id"]] = dict(tool, preserveOnUpdate=preserve)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PortakitError("usage", message)


def check_download_size(size):
    if size > MAX_DOWNLOAD_BYTES:
        raise PortakitError("download", f"Download size exceeds {MAX_DOWNLOAD_BYTES} bytes")


def download(url, destination):
    with urllib.request.urlopen(url, timeout=60) as response:
        length = response.headers.get("Content-Length", "")
        if length.isdigit():
            check_download_size(int(length))
        total = 0
        with destination.open("wb") as out:
            while chunk := response.read(min(64 * 1024, MAX_DOWNLOAD_BYTES - total + 1)):
                total += len(chunk)
                check_download_size(total)
                out.write(chunk)


def fetch(tool, root, downloader=None):
    expected = tool["sha256"].lower()
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise PortakitError("integrity", "sha256: TODO must be replaced with a verified digest")
    cache = safe_path(root, ".portakit-cache", "cache")
    cache.mkdir(parents=True, exist_ok=True)
    target = safe_path(cache, expected, "cache")
    partial = safe_path(cache, expected + ".part", "cache")
    try:
        if not target.exists():
            (downloader or download)(tool["url"], partial)
            candidate = partial
        else:
            candidate = target
        if candidate.stat().st_size > MAX_DOWNLOAD_BYTES:
            candidate.unlink()
            check_download_size(MAX_DOWNLOAD_BYTES + 1)
        with candidate.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            candidate.unlink()
            raise PortakitError("integrity", "SHA256 mismatch; nothing installed")
        if candidate == partial:
            partial.replace(target)
        return target
    except OSError as exc:
        raise PortakitError("download", f"download: {exc}") from exc
    finally:
        partial.unlink(missing_ok=True)


def extract(artifact, tool, destination):
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
    path = safe_path(root, ".portakit-state.json", "state")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        destinations = []
        for identifier, item in data.items():
            if not isinstance(item, dict) or not isinstance(item.get("version"), str):
                raise ValueError(f"{identifier}.version: expected a string")
            destinations.append(managed_dest(root, item.get("dest"), destinations))
        return data
    except (OSError, ValueError, PortakitError) as exc:
        raise PortakitError("state", f"state: {exc}") from exc


def write_state(root, state):
    target = safe_path(root, ".portakit-state.json", "state")
    temporary = target.with_name(".portakit-state-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as out:
            json.dump(state, out, indent=2)
            out.write("\n")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def reject_links(path):
    if is_reparse(path):
        raise PortakitError("filesystem", f"Reparse path rejected: {path}")
    if path.is_dir():
        for child in path.iterdir():
            reject_links(child)


def remove_tree(path):
    def onerror(function, filename, info):
        if not isinstance(info[1], PermissionError):
            raise info[1]
        target = Path(filename)
        target.chmod(target.stat().st_mode | stat.S_IWRITE)
        function(filename)
    shutil.rmtree(path, onerror=onerror)


def preserve_paths(tool, source, stage):
    for relative in tool.get("preserveOnUpdate", []):
        original = safe_path(source, relative, "preserveOnUpdate")
        if not original.exists():
            continue
        reject_links(original)
        target = safe_path(stage, relative, "preserveOnUpdate")
        if target.is_dir():
            remove_tree(target)
        elif target.exists():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        if original.is_dir():
            shutil.copytree(original, target)
        else:
            shutil.copy2(original, target)


def apply_defaults(tool, stage):
    for relative, content in tool.get("defaultConfig", {}).items():
        target = safe_path(stage, relative, "defaultConfig")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="")


def rollback_swap(dest, old, stage=None):
    # Infer completed renames from disk, including interruption before flag updates.
    if stage is not None and not stage.exists() and dest.exists():
        try:
            dest.rename(stage)
        except OSError:
            try:
                remove_tree(dest)
            except OSError:
                pass  # Still attempt backup restoration independently.
    if old.exists():
        try:
            old.rename(dest)
        except OSError as exc:
            raise PortakitError("filesystem", f"Rollback failed; backup retained at {old}: {exc}") from exc
    elif stage is not None and not stage.exists() and dest.exists():
        raise PortakitError("filesystem", f"Rollback could not remove failed install: {dest}")


def install(tool, root, downloader=None, *, preserve=False):
    root = Path(root).resolve()
    state = read_state(root)
    identifier = tool["id"]
    dest = managed_dest(root, tool["dest"], [safe_path(root, item["dest"], "state.dest")
                        for key, item in state.items() if key != identifier])
    previous = state.get(identifier)
    if previous:
        installed_dest = managed_dest(root, previous["dest"])
        installed_old = safe_path(root, previous["dest"] + ".old", "backup")
        if installed_old.exists() and not installed_dest.exists():
            installed_old.rename(installed_dest)
        if not preserve:
            raise PortakitError("state", f"{identifier}: already installed; use update {identifier}")
    if previous and previous["dest"] != tool["dest"]:
        raise PortakitError("state", "dest changed; remove the installed tool first")
    if dest.exists() and not previous:
        raise PortakitError("state", f"Refusing to replace unmanaged directory: {dest}")
    old = safe_path(root, tool["dest"] + ".old", "backup")
    if old.exists():
        raise PortakitError("filesystem", f"Backup already exists: {old}; inspect it before retrying")
    artifact = fetch(tool, root, downloader)
    stage = root / (".portakit-stage-" + uuid.uuid4().hex)
    stage.mkdir()
    moved_old = False
    try:
        extract(artifact, tool, stage)
        if preserve:
            preserve_paths(tool, dest, stage)
        apply_defaults(tool, stage)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.rename(old)
            moved_old = True
        stage.rename(dest)
        write_state(root, dict(state, **{identifier: dict(version=tool["version"], dest=tool["dest"])}))
    except BaseException as exc:
        rollback_swap(dest, old, stage)
        if not isinstance(exc, Exception) or isinstance(exc, (PortakitError, http.client.HTTPException)):
            raise
        hint = " Close running applications and retry." if isinstance(exc, PermissionError) else ""
        raise PortakitError("filesystem", f"install: {exc}.{hint}") from exc
    finally:
        if stage.exists():
            remove_tree(stage)
    result = dict(id=identifier, version=tool["version"], dest=str(dest))
    if moved_old:
        try:
            remove_tree(old)
        except OSError:
            # Commit succeeded. Keep a locked backup for manual cleanup.
            result["cleanupPending"] = str(old)
    return result


def update(tool, root, downloader=None):
    if tool["id"] not in read_state(root):
        raise PortakitError("not_found", f'{tool["id"]}: not installed')
    return install(tool, root, downloader, preserve=True)


def remove(identifier, root):
    root = Path(root).resolve()
    state = read_state(root)
    if identifier not in state:
        raise PortakitError("not_found", f"{identifier}: not installed")
    dest = managed_dest(root, state[identifier]["dest"])
    old = safe_path(root, state[identifier]["dest"] + ".old", "backup")
    if old.exists() and not dest.exists():
        old.rename(dest)
    if old.exists():
        raise PortakitError("filesystem", f"Backup already exists: {old}; inspect it before retrying")
    moved = False
    try:
        if dest.exists():
            dest.rename(old)
            moved = True
        remaining = dict(state)
        del remaining[identifier]
        write_state(root, remaining)
    except BaseException as exc:
        rollback_swap(dest, old)
        if not isinstance(exc, Exception) or isinstance(exc, PortakitError):
            raise
        raise PortakitError("filesystem", f"remove: {exc}. Close running applications and retry.") from exc
    result = dict(id=identifier)
    if moved:
        try:
            remove_tree(old)
        except OSError:
            result["cleanupPending"] = str(old)
    return result


def main(argv=None, downloader=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = None
    try:
        parser = Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--root", type=Path, default=Path("portable"))
        parser.add_argument("command", choices=("list", "install", "update", "remove"))
        parser.add_argument("id", nargs="?")
        args = parser.parse_args(argv)
        command = args.command
        if (command == "list") != (args.id is None):
            raise PortakitError("usage", "list takes no ID; install/update/remove require ID")
        if command == "remove":
            data = remove(args.id, args.root)
        else:
            catalog = load_catalog(DEFAULT_CATALOG, args.root)
            if command == "list":
                data = list(catalog.values())
            else:
                if args.id not in catalog:
                    raise PortakitError("not_found", f"Unknown ID: {args.id}")
                action = install if command == "install" else update
                data = action(catalog[args.id], args.root, downloader)
        result = dict(ok=True, command=command, data=data, error=None)
        code = 0
    except Exception as exc:
        name = (exc.code if isinstance(exc, PortakitError) else
                "download" if isinstance(exc, http.client.HTTPException) else "filesystem")
        result = dict(ok=False, command=command, data=None,
                      error=dict(code=name, message=str(exc)))
        code = EXIT_CODES[name]
    if "--json" in argv:
        print(json.dumps(result))
    elif result["ok"]:
        if command == "list":
            for tool in result["data"]:
                print(f'{tool["id"]}\t{tool["version"]}')
        else:
            print(f"{command}: {args.id}")
    else:
        print(result["error"]["message"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
