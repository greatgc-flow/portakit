"""Small, standard-library portable app manager for Windows."""

import argparse
import configparser
import hashlib
import http.client
import json
import msvcrt
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import zlib
import xml.etree.ElementTree as ET


DEFAULT_CATALOG = Path(__file__).with_name("catalog.json")
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
# Guard against ZIP bombs independently of the compressed vendor-download cap.
# Review these limits when admitting unusually large new official packages.
MAX_ZIP_MEMBERS = 4096
MAX_ZIP_EXPANDED_BYTES = 512 * 1024 * 1024
EXIT_CODES = dict(ok=0, usage=1, catalog=2, fetch=3, archive=4, state=5, busy=6)
DEVICE_NAME = re.compile(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?")


class PortakitError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_reparse(path):
    try:
        info = Path(path).lstat()
        return stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
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
    return target


def check_dest(value, field="dest", code="catalog"):
    parts = path_parts(value, field, code)
    if len(parts) != 1:
        raise PortakitError(code, f"{field}: expected a single path segment")
    name = parts[0]
    if name.lower().startswith(".portakit") or name.lower().endswith(".old"):
        raise PortakitError(code, f"{field}: reserved name")
    return name


def validate_recommended(config):
    if config is None:
        return
    if not isinstance(config, dict):
        raise PortakitError("catalog", "recommended: expected an object")
    if config.get("settings") not in ("notepad++-dev", "winmerge-dev"):
        raise PortakitError("catalog", "recommended.settings: unknown profile")
    plugins = config.get("plugins")
    if not isinstance(plugins, list) or len(plugins) > 8:
        raise PortakitError("catalog", "recommended.plugins: expected at most 8 plugins")
    bundled = config.get("bundledPlugins", [])
    if not isinstance(bundled, list) or len(bundled) > 20:
        raise PortakitError("catalog", "recommended.bundledPlugins: expected at most 20 filenames")
    if bundled and config["settings"] != "winmerge-dev":
        raise PortakitError("catalog", "recommended.bundledPlugins: WinMerge-only")
    seen = set()
    for name in bundled:
        parts = path_parts(name, "recommended.bundledPlugins")
        if (len(parts) != 1 or not name.lower().endswith((".sct", ".dll"))
                or name.lower() in seen):
            raise PortakitError("catalog", "recommended.bundledPlugins: unsafe or duplicate name")
        seen.add(name.lower())
    destinations = set()
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise PortakitError("catalog", "recommended.plugins: expected objects")
        for field in ("id", "version", "url", "sha256", "dest", "requiredFile"):
            if not isinstance(plugin.get(field), str) or not plugin[field]:
                raise PortakitError("catalog", f"recommended.plugins.{field}: required string")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", plugin["id"]):
            raise PortakitError("catalog", "recommended.plugins.id: invalid")
        parsed = urllib.parse.urlsplit(plugin["url"])
        if (parsed.scheme != "https" or not parsed.hostname
                or any(ch.isspace() for ch in plugin["url"])
                or "latest" in urllib.parse.unquote(parsed.path).lower().split("/")):
            raise PortakitError("catalog", "recommended.plugins.url: expected pinned HTTPS asset")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", plugin["sha256"]):
            raise PortakitError("catalog", "recommended.plugins.sha256: expected 64 hex")
        parts = path_parts(plugin["dest"], "recommended.plugins.dest")
        if len(parts) != 2 or parts[0].lower() != "plugins":
            raise PortakitError("catalog", "recommended.plugins.dest: expected plugins/PluginName")
        required = path_parts(plugin["requiredFile"], "recommended.plugins.requiredFile")
        if len(required) != 1 or not required[0].lower().endswith(".dll"):
            raise PortakitError("catalog", "recommended.plugins.requiredFile: expected plugin DLL")
        if parts[1].lower() in destinations:
            raise PortakitError("catalog", "recommended.plugins.dest: duplicate destination")
        destinations.add(parts[1].lower())


def strict_json_pairs(pairs):
    """Reject duplicate members anywhere in trusted-selection JSON.

    Standard json.loads silently chooses the last value, allowing shadowed
    SHA pins, aliases and per-tool state to be interpreted differently.
    """
    values = {}
    for name, value in pairs:
        if name in values:
            raise ValueError("Duplicate JSON key: " + name)
        values[name] = value
    return values


def reject_nonfinite_json(value):
    """Python accepts NaN/Infinity by default; these are invalid JSON."""
    raise ValueError("Nonstandard JSON numeric token: " + value)


def strict_json_loads(text):
    """Single source of truth for fail-closed declarative JSON parsing."""
    return json.loads(text, object_pairs_hook=strict_json_pairs,
                      parse_constant=reject_nonfinite_json)


def load_catalog(path):
    check_links(path)
    try:
        data = strict_json_loads(Path(path).read_text(encoding="utf-8"))
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
            if "latest" in urllib.parse.unquote(url.path).lower().split("/"):
                raise ValueError("expected a pinned release URL; latest is mutable")
        except ValueError as exc:
            raise PortakitError("catalog", f"url: {exc}") from exc
        if not re.fullmatch(r"[a-fA-F0-9]{64}", tool["sha256"]):
            raise PortakitError("catalog", "sha256: expected 64 hex digits (placeholders are rejected)")
        if tool["artifact"] not in ("zip", "exe", "sfx7z"):
            raise PortakitError("catalog", "artifact: expected zip, exe or sfx7z")
        if tool["artifact"] == "sfx7z" and tool["id"] != "7zip":
            raise PortakitError("catalog", "sfx7z: restricted to verified 7zip catalog ID")
        dest = check_dest(tool["dest"])
        if dest.lower() in destinations:
            raise PortakitError("catalog", "dest: duplicate")
        extras = tool.get("preserveMissingOnUpdate", [])
        if not isinstance(extras, list):
            raise PortakitError("catalog", "preserveMissingOnUpdate: expected a list")
        for item in extras:
            path_parts(item, "preserveMissingOnUpdate")
        preserve = tool.get("preserveOnUpdate", [])
        if not isinstance(preserve, list):
            raise PortakitError("catalog", "preserveOnUpdate: expected a list")
        for item in preserve:
            path_parts(item, "preserveOnUpdate")
        validate_recommended(tool.get("recommended"))
        if tool.get("recommended"):
            setting = tool["recommended"]["settings"]
            if (setting == "notepad++-dev") != (tool["id"] == "notepad++"):
                raise PortakitError("catalog", "recommended.settings: incompatible tool")
            if setting == "winmerge-dev" and tool["id"] != "winmerge":
                raise PortakitError("catalog", "recommended.settings: incompatible tool")
        destinations.add(dest.lower())
        result[tool["id"]] = dict(tool, sha256=tool["sha256"].lower(),
                                  preserveOnUpdate=preserve, preserveMissingOnUpdate=extras)
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


def parse_sfx_listing(output, destination):
    """Fail-closed 7zr -slt listing parser, BEFORE touching the extraction root.

    This is intentionally NOT a general-purpose 7z extractor. The official,
    pinned Windows 7-Zip SFX archive uses a known, bounded listing grammar.
    """
    if not isinstance(output, str) or len(output) > 1024 * 1024:
        raise PortakitError("archive", "sfx7z: missing or oversize listing")
    header = re.search(r"(?m)^-{10,}\r?$", output)
    if not header or "Type = 7z" not in output[:header.start()]:
        raise PortakitError("archive", "sfx7z: expected SFX with embedded 7z archive")
    entries = {}
    total = 0
    for piece in re.split(r"\r?\n\s*\r?\n", output[header.end():]):
        part = dict(line.split(" = ", 1) for line in piece.splitlines()
                    if " = " in line)
        if not part:
            continue
        name, size_str = part.get("Path"), part.get("Size")
        if not name or not size_str or not size_str.isdigit():
            raise PortakitError("archive", "sfx7z: malformed member listing")
        if any(ord(ch) > 127 for ch in name):
            raise PortakitError("archive", "sfx7z: only ASCII vendor package paths supported")
        parts = path_parts(name, "sfx member", "archive")
        normalized = "/".join(parts)
        safe_path(destination, normalized, "sfx member", "archive")
        key = normalized.lower()
        if key in entries:
            raise PortakitError("archive", "sfx7z: duplicate case-insensitive path")
        attributes = part.get("Attributes", "")
        if (not attributes or "L" in attributes.upper() or
                part.get("Encrypted") != "-" or "Symbolic Link" in part or
                "Hard Link" in part or "Reparse" in part):
            raise PortakitError("archive", "sfx7z: unknown/encrypted/link entry")
        directory = "D" in attributes
        size = int(size_str)
        if directory and size != 0:
            raise PortakitError("archive", "sfx7z: directory has file content")
        total += size
        if total > 64 * 1024 * 1024 or len(entries) >= 512:
            raise PortakitError("archive", "sfx7z: expanded size/member limit")
        entries[key] = (normalized, size, directory)
    if not entries:
        raise PortakitError("archive", "sfx7z: no members")
    for key, (_name, _size, directory) in entries.items():
        if any(entries.get("/".join(key.split("/")[:i]), ("", 0, True))[2] is False
               for i in range(1, len(key.split("/")))):
            raise PortakitError("archive", "sfx7z: file used as folder")
    for expected in ("7z.exe", "7z.dll", "7zfm.exe", "7zg.exe", "license.txt"):
        if expected not in entries or entries[expected][2]:
            raise PortakitError("archive", "sfx7z: required full 7-Zip file missing: " + expected)
    return entries


def trusted_sfx_extractor(root):
    """Only execute a fully-pinned, byte-reverified, PortaKit-managed 7zr.exe."""
    root = Path(root)
    catalog = load_catalog(DEFAULT_CATALOG)
    if "7zr" not in catalog:
        raise PortakitError("archive", "sfx7z: no pinned 7zr tool available")
    pin = catalog["7zr"]
    installed = read_state(root).get("7zr")
    if (not isinstance(installed, dict) or
            installed.get("version") != pin["version"] or
            installed.get("sha256") != pin["sha256"] or
            installed.get("dest") != pin["dest"]):
        raise PortakitError("archive", "sfx7z: install the matching pinned 7zr first")
    exe = safe_path(root, pin["dest"] + "/7zr.exe", "7zr executable", "archive")
    if not exe.is_file():
        raise PortakitError("archive", "sfx7z: missing managed 7zr.exe")
    with exe.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != pin["sha256"]:
        raise PortakitError("archive", "sfx7z: installed 7zr executable SHA mismatch")
    return exe


def extract_sfx7z(archive, destination, *, runner=subprocess.run):
    """Unpack exact vendor Windows SFX as DATA; never launch the installer.

    7zr is separately pinned and installed. Validate listing before extraction,
    refuse special paths, verify all expanded files and total byte counts before
    original deploy() atomically promotes the stage. No registry or GUI commands.
    """
    destination = Path(destination)
    check_links(destination)
    unpacker = trusted_sfx_extractor(destination.parent)
    archive = Path(archive)
    check_links(archive)
    try:
        info = runner([str(unpacker), "l", "-slt", str(archive)],
                      capture_output=True, text=True, encoding="utf-8",
                      errors="replace", timeout=30, check=False)
        if info.returncode:
            raise PortakitError("archive", "sfx7z: vendor archive listing failed")
        expected = parse_sfx_listing(info.stdout, destination)
        extraction = runner([str(unpacker), "x", "-y", "-bd",
                             "-o" + str(destination), str(archive)],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, check=False)
        if extraction.returncode:
            raise PortakitError("archive", "sfx7z: vendor archive extraction failed")
        # 7zr lists archive FILE entries but materializes intermediate
        # directories which may not be explicit archive members (e.g. Lang/).
        # Permit only ancestor directories of validated file/member paths.
        implicit_dirs = set()
        for key in expected:
            segments = key.split("/")
            implicit_dirs.update("/".join(segments[:i])
                                 for i in range(1, len(segments)))
        observed = set()
        for root, dirs, files in os.walk(destination, followlinks=False):
            for entry in dirs + files:
                actual = Path(root) / entry
                if is_reparse(actual):
                    raise PortakitError("archive", "sfx7z: extracted junction/symlink")
                name = actual.relative_to(destination).as_posix()
                safe_path(destination, name, "sfx member", "archive")
                key = name.lower()
                if key in observed:
                    raise PortakitError("archive", "sfx7z: duplicate extracted member: " + name)
                if key not in expected:
                    if actual.is_dir() and key in implicit_dirs:
                        continue
                    raise PortakitError("archive", "sfx7z: unexpected extracted member: " + name)
                planned, length, directory = expected[key]
                if actual.is_dir() != directory or (not directory and actual.stat().st_size != length):
                    raise PortakitError("archive", "sfx7z: extracted member size/type mismatch")
                observed.add(key)
        if observed != set(expected):
            raise PortakitError("archive", "sfx7z: missing extracted file(s)")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PortakitError("archive", "sfx7z: subprocess or file validation failed: " + str(exc)) from exc


def extract(artifact, tool, destination):
    check_links(artifact)
    check_links(destination)
    destination = Path(destination)
    if tool["artifact"] == "sfx7z":
        extract_sfx7z(artifact, destination)
        return
    if tool["artifact"] == "exe":
        target = safe_path(destination, tool["id"] + ".exe", "id")
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, target)
        return
    try:
        with zipfile.ZipFile(artifact) as archive:
            members = []
            paths = {}
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise PortakitError("archive", "zip: member count limit exceeded")
            expanded = 0
            for info in infos:
                name = info.filename.replace("\\", "/")
                directory = name.endswith("/")
                name = name[:-1] if directory else name
                safe_path(destination, name, "zip member")
                if directory and info.file_size:
                    raise PortakitError("archive", "zip: directory contains file data")
                if info.file_size > MAX_ZIP_EXPANDED_BYTES - expanded:
                    raise PortakitError("archive", "zip: expanded size limit exceeded")
                expanded += info.file_size
                mode = info.external_attr >> 16
                if (info.external_attr & stat.FILE_ATTRIBUTE_REPARSE_POINT or stat.S_ISLNK(mode)
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
                        written = 0
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > info.file_size:
                                raise PortakitError("archive",
                                                    "zip: expanded member exceeds declared size")
                            out.write(chunk)
                        if written != info.file_size:
                            raise PortakitError("archive",
                                                "zip: expanded member size mismatch")
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
        data = strict_json_loads(path.read_text(encoding="utf-8"))
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


def preserve_missing_paths(tool, source, stage):
    """Keep user-added files under nominated directories; packaged paths take priority."""
    def merge_missing(old, new):
        for item in old.iterdir():
            target = new / item.name
            if os.path.lexists(target):
                if item.is_dir() and target.is_dir():
                    merge_missing(item, target)
                continue  # Never replace a packaged file, including bundled plugin binaries.
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

    for relative in tool.get("preserveMissingOnUpdate", []):
        original = safe_path(source, relative, "preserveMissingOnUpdate", "state")
        if not os.path.lexists(original):
            continue
        reject_links(original)
        if not original.is_dir():
            raise PortakitError("state", f"preserveMissingOnUpdate: {original} is not a directory")
        target = safe_path(stage, relative, "preserveMissingOnUpdate", "state")
        if os.path.lexists(target) and not target.is_dir():
            continue
        target.mkdir(parents=True, exist_ok=True)
        merge_missing(original, target)


def seed_recommended_settings(settings, stage):
    """Seed only a new staged install; never change existing user config."""
    if settings == "notepad++-dev":
        marker = safe_path(stage, "doLocalConf.xml", "recommended.settings", "state")
        if not marker.exists():
            marker.touch()
        config = safe_path(stage, "config.xml", "recommended.settings", "state")
        try:
            if config.exists():
                tree = ET.parse(config)
                root = tree.getroot()
                if root.tag != "NotepadPlus":
                    raise ValueError("expected NotepadPlus root")
            else:
                root = ET.Element("NotepadPlus")
                tree = ET.ElementTree(root)
            gui = root.find("GUIConfigs")
            if gui is None:
                gui = ET.SubElement(root, "GUIConfigs")
            tab = next((node for node in gui.findall("GUIConfig")
                        if node.get("name") == "TabSetting"), None)
            if tab is None:
                tab = ET.SubElement(gui, "GUIConfig", {"name": "TabSetting"})
            tab.set("size", "4")
            tab.set("replaceBySpace", "yes")
            tree.write(config, encoding="utf-8", xml_declaration=True)
        except (ET.ParseError, ValueError) as exc:
            raise PortakitError("state", f"recommended.settings: bad config.xml: {exc}") from exc
    elif settings == "winmerge-dev":
        config = safe_path(stage, "WinMerge.ini", "recommended.settings", "state")
        ini = configparser.ConfigParser(interpolation=None)
        ini.optionxform = str  # Preserve WinMerge setting key case.
        try:
            if config.exists():
                with config.open("r", encoding="utf-8-sig") as source:
                    ini.read_file(source)
        except (configparser.Error, UnicodeError) as exc:
            raise PortakitError("state", f"recommended.settings: bad WinMerge.ini: {exc}") from exc
        # WinMerge 2.16 reads [WinMerge] keys with the "Settings/" prefix.
        # [Settings] is not recognized by its CIniOptionsMgr implementation.
        if not ini.has_section("WinMerge"):
            ini.add_section("WinMerge")
        for name, value in (("ViewLineNumbers", "1"),
                            ("PluginsEnabled", "1"),
                            ("UnpackerMode", "1")):
            ini.set("WinMerge", "Settings/" + name, value)
        with config.open("w", encoding="utf-8") as out:
            ini.write(out)


def stage_recommended(tool, stage, root, downloader, *, existing=False):
    config = tool.get("recommended")
    if not config:
        raise PortakitError("catalog", f"{tool['id']}: no recommended profile")
    validate_recommended(config)
    config_name = "config.xml" if config["settings"] == "notepad++-dev" else "WinMerge.ini"
    settings_path = safe_path(stage, config_name, "recommended.settings", "state")
    marker_path = (safe_path(stage, "doLocalConf.xml", "recommended.settings", "state")
                   if config["settings"] == "notepad++-dev" else None)
    before = settings_path.read_bytes() if settings_path.exists() else None
    marker_before = marker_path.exists() if marker_path else False
    seed_recommended_settings(config["settings"], stage)
    changed = (before != settings_path.read_bytes() or
               (marker_path is not None and marker_before != marker_path.exists()))
    for name in config.get("bundledPlugins", []):
        plugin = safe_path(stage, "MergePlugins/" + name,
                           "recommended.bundledPlugins", "archive")
        if not plugin.is_file():
            raise PortakitError("archive",
                                f"recommended.bundledPlugins: {name} missing from vendor archive")
    for index, plugin in enumerate(config["plugins"]):
        destination = safe_path(stage, plugin["dest"], "recommended.plugins.dest", "state")
        if os.path.lexists(destination):
            if existing:
                required = safe_path(destination, plugin["requiredFile"],
                                     "recommended.plugins.requiredFile", "state")
                if destination.is_dir() and required.is_file():
                    continue
                raise PortakitError("state",
                                    f"recommended.plugins.requiredFile: {required} missing; "
                                    "refusing to overwrite an existing plugin folder")
            raise PortakitError("state", f"recommended.plugins.dest: {destination} exists")
        changed = True
        archive = root / f".portakit-dl-{tool['id']}-rec-{index}.tmp"
        try:
            fetch_archive(plugin, archive, downloader)
            extract(archive, dict(id=plugin["id"], artifact="zip"), destination)
            required = safe_path(destination, plugin["requiredFile"],
                                 "recommended.plugins.requiredFile", "state")
            if not required.is_file():
                raise PortakitError("archive", f"recommended.plugins.requiredFile: {required} missing")
        finally:
            if os.path.lexists(archive):
                remove_tree(archive)
    return changed


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


def deploy(tool, root, state, downloader, update_mode, recommended=False):
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
        if tool["artifact"] == "sfx7z":
            # Refuse absent or modified prerequisite BEFORE any network download.
            trusted_sfx_extractor(root)
        for leftover in (dl, stage):
            if os.path.lexists(leftover):
                remove_tree(leftover)
        fetch_archive(tool, dl, downloader)
        stage.mkdir()
        extract(dl, tool, stage)
        if recommended:
            stage_recommended(tool, stage, root, downloader)
        if update_mode:
            preserve_paths(tool, dest, stage)
            preserve_missing_paths(tool, dest, stage)
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


def install(tool, root, downloader=None, *, state=None, recommended=False):
    check_links(root)
    root = Path(root).resolve()
    if state is None:
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
    return deploy(tool, root, state, downloader, update_mode=False, recommended=recommended)


def update(tool, root, downloader=None, *, state=None):
    check_links(root)
    root = Path(root).resolve()
    if state is None:
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


def configure(tool, root, downloader=None, *, state=None):
    """Add recommended settings and plugins to an already managed installation.

    Work on a complete private copy; never download/reinstall the main app.
    Rollback restores the original directory on any precommit failure.
    """
    check_links(root)
    root = Path(root).resolve()
    if state is None:
        state = read_state(root)
    identifier = tool["id"]
    if not tool.get("recommended"):
        raise PortakitError("catalog", f"{identifier}: no recommended profile")
    if identifier not in state:
        raise PortakitError("state", f"{identifier}: not installed")
    installed = state[identifier]
    if installed["dest"] != tool["dest"]:
        raise PortakitError("state", f"{identifier}: dest changed; remove and install again")
    if (installed.get("version") != tool["version"]
            or installed.get("sha256") != tool["sha256"].lower()):
        raise PortakitError("state", f"{identifier}: catalog pin changed; update {identifier} first")
    dest, old = dest_paths(root, tool["dest"])
    has_dest, has_old = os.path.lexists(dest), os.path.lexists(old)
    if has_dest and has_old:
        raise PortakitError("state", f"{dest} and {old} both exist; recover manually before configure")
    if has_old:
        check_links(old)
        rename(old, dest)
    check_dest_kind(dest)
    if not dest.is_dir():
        raise PortakitError("state", f"{identifier}: installed folder missing; update to repair")
    reject_links(dest)
    stage = root / f".portakit-stage-{identifier}.tmp"
    check_links(stage)
    moved_old = staged = False
    try:
        if os.path.lexists(stage):
            remove_tree(stage)
        shutil.copytree(dest, stage)
        changed = stage_recommended(tool, stage, root, downloader, existing=True)
        if not changed:
            return dict(id=identifier, version=tool["version"], dest=str(dest), changed=False)
        rename(dest, old)
        moved_old = True
        rename(stage, dest)
        staged = True
        write_state(root, state)
    except BaseException as exc:
        rollback(dest, old, staged, moved_old)
        if isinstance(exc, PortakitError) or not isinstance(exc, Exception):
            raise
        raise PortakitError("state", f"configure: {exc}") from exc
    finally:
        if os.path.lexists(stage):
            remove_tree(stage)
    try:
        remove_tree(old)
    except OSError:
        print(f"warning: could not delete {old}; delete it before the next operation on {identifier}",
              file=sys.stderr)
    return dict(id=identifier, version=tool["version"], dest=str(dest), changed=True)


def remove(identifier, root, *, state=None):
    check_links(root)
    root = Path(root).resolve()
    if state is None:
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


def offline_downloader(archive):
    """Read an explicit locally staged vendor asset, retaining normal SHA checks.

    The caller selects an archive by path, not by a mutable URL or untrusted
    manifest. The original fetch_archive() still verifies the pinned digest
    and maximum size before extraction and atomic deployment.
    """
    path = Path(os.path.abspath(str(archive)))
    check_links(path)
    if not path.is_file():
        raise PortakitError("fetch", f"offline archive not found: {path}")

    def copy_archive(_vendor_url, destination):
        check_links(path)
        check_links(destination)
        try:
            total = 0
            with path.open("rb") as source, Path(destination).open("wb") as output:
                while True:
                    block = source.read(64 * 1024)
                    if not block:
                        break
                    total += len(block)
                    check_download_size(total)
                    output.write(block)
        except OSError as exc:
            raise PortakitError("fetch", f"offline archive read: {exc}") from exc

    return copy_archive


def execute(args, downloader):
    command, root, identifier = args.command, args.root, args.id
    if getattr(args, "archive", None) is not None:
        downloader = offline_downloader(args.archive)
    check_links(root)
    if command == "list":
        return {"items": list(load_catalog(DEFAULT_CATALOG).values())}
    catalog = None if command == "remove" else load_catalog(DEFAULT_CATALOG)
    root.mkdir(parents=True, exist_ok=True)
    with RootLock(root):
        cleanup_temps(root)
        state = read_state(root)
        if command == "install":
            if identifier not in catalog:
                raise PortakitError("usage", f"Unknown ID: {identifier}")
            if args.recommended:
                return install(catalog[identifier], root, downloader, state=state,
                               recommended=True)
            return install(catalog[identifier], root, downloader, state=state)
        if command == "configure":
            if identifier not in catalog:
                raise PortakitError("state", f"{identifier}: not in catalog")
            return configure(catalog[identifier], root, downloader, state=state)
        if command == "update":
            if identifier not in state:
                raise PortakitError("state", f"{identifier}: not installed")
            if identifier not in catalog:
                raise PortakitError("state", f"{identifier}: not in catalog; run remove {identifier}")
            return update(catalog[identifier], root, downloader, state=state)
        return remove(identifier, root, state=state)


class _ConsoleTee:
    """Mirror this Python invocation's stream writes to a local evidence log.

    Both streams use one exclusive-create file. This does not capture output
    written by native subprocesses to OS handles or survive process crashes.
    """

    def __init__(self, displayed, evidence):
        self.displayed = displayed
        self.evidence = evidence

    def write(self, value):
        self.displayed.write(value)
        self.evidence.write(value)
        self.evidence.flush()

    def flush(self):
        self.displayed.flush()
        self.evidence.flush()


def main(argv=None, downloader=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = None
    args = None
    original_stdout, original_stderr = sys.stdout, sys.stderr
    evidence = None
    try:
        parser = Parser(
            description=__doc__, allow_abbrev=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=("Commands:\n"
                    "  list        Show catalog pins; takes no ID.\n"
                    "  install ID  Download, verify and install a catalog pin.\n"
                    "  update ID   Apply the catalog pin; identical installs skip download.\n"
                    "  configure ID  Add recommended settings/plugins to a managed install.\n"
                    "  remove ID   Delete the installed folder, backup and all user data,\n"
                    "              then forget the state entry; no catalog needed.\n"
                    "install/update/configure/remove require ID."))
        parser.add_argument("--archive", type=Path, metavar="FILE",
                            help="for install/update: use this pre-staged vendor file offline, "
                                 "SHA-256 checked against pinned catalog; no download")
        parser.add_argument("--recommended", action="store_true",
                            help="opt in to pinned recommended settings and plugins (install only)")
        parser.add_argument("--json", action="store_true",
                            help="emit one JSON result envelope (help stays human text)")
        parser.add_argument("--log-file", type=Path, metavar="FILE",
                            help="optional new-only local console transcript (stdout and stderr)")
        parser.add_argument("--root", type=Path, default=Path("portable"), metavar="DIR",
                            help="install root (default: portable in the current directory)")
        parser.add_argument("command", choices=("list", "install", "update", "configure", "remove"),
                            help="operation to perform (see Commands below)")
        parser.add_argument("id", nargs="?", metavar="ID",
                            help="tool ID; required except for list")
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:  # -h/--help: human text, no envelope
            return exc.code if isinstance(exc.code, int) else 0
        command = args.command
        if args.log_file is not None:
            # Fail before any command side effect if evidence cannot be
            # created; no default log, no mkdir, no overwrite or reparse path.
            check_links(args.log_file)
            evidence = args.log_file.open("x", encoding="utf-8", newline="\n")
            sys.stdout = _ConsoleTee(original_stdout, evidence)
            sys.stderr = _ConsoleTee(original_stderr, evidence)
        if (command == "list") != (args.id is None):
            raise PortakitError("usage", "list takes no ID; other commands require ID")
        if args.recommended and command != "install":
            raise PortakitError("usage", "--recommended applies only to install")
        if args.archive is not None and command not in ("install", "update"):
            raise PortakitError("usage", "--archive applies only to install/update")
        if args.archive is not None and args.recommended:
            raise PortakitError("usage",
                                "--archive with --recommended is not supported: "
                                "offline plugin assets cannot be implicitly downloaded")
        data = execute(args, downloader)
        result = dict(ok=True, command=command, data=data, error=None)
        code = 0
    except Exception as exc:
        name = (exc.code if isinstance(exc, PortakitError) else
                "fetch" if isinstance(exc, http.client.HTTPException) else "state")
        result = dict(ok=False, command=command, data=None,
                      error=dict(code=name, message=str(exc)))
        code = EXIT_CODES[name]
    try:
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
    finally:
        # Restore callers\u0027 streams even when log writing fails. A partial
        # log after an I/O error is never authoritative evidence.
        sys.stdout, sys.stderr = original_stdout, original_stderr
        if evidence is not None:
            evidence.close()


if __name__ == "__main__":
    sys.exit(main())
