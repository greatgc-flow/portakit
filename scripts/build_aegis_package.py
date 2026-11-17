"""Build/check the deterministic Aegis runtime ZIP; never execute Aegis.

Only the explicit runtime files are packaged. Developer tests, existing user
settings and saved profiles are excluded. ZIP_STORED keeps identical bytes
across Python/zlib versions. --check is read-only and rejects a stale asset.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import zipfile


REPO = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    "Aegis.ps1", "Aegis.Processes.csv", "Aegis.Menu.ps1",
    "Start-Aegis.cmd", "README_ko.txt", "LICENSE.txt",
)
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
VERSION = re.compile(
    r"function\s+Get-AegisVersion\s*\{\s*return\s+'"
    r"([0-9]+\.[0-9]+\.[0-9]+-ps2)'\s*\}")
BANNER = re.compile(r"^Aegis ([0-9]+\.[0-9]+\.[0-9]+-ps2) \|", re.M)


class PackageError(Exception):
    pass


def check_links(path):
    """Reject existing link/reparse ancestors without resolving through them."""
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & 0x400):
            raise PackageError("Link/reparse path is not allowed: " + str(item))


def runtime_bytes(path):
    check_links(path)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_FILE_BYTES:
            raise PackageError("Invalid runtime file or size: " + str(path))
        data = path.read_bytes()
    except OSError as exc:
        raise PackageError("Cannot read runtime file: " + str(path)) from exc
    if not 0 < len(data) <= MAX_FILE_BYTES:
        raise PackageError("Invalid runtime file size: " + str(path))
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PackageError("Runtime text must be UTF-8: " + path.name) from exc
    if path.suffix.lower() in (".ps1", ".cmd"):
        remaining = data.replace(b"\r\n", b"")
        if b"\n" in remaining or b"\r" in remaining:
            raise PackageError("Runtime scripts require CRLF: " + path.name)
        if path.suffix.lower() == ".ps1" and not data.startswith(b"\xef\xbb\xbf"):
            raise PackageError("PowerShell scripts require UTF-8 BOM: " + path.name)
        if path.suffix.lower() == ".cmd":
            try:
                data.decode("ascii")
            except UnicodeDecodeError as exc:
                raise PackageError("CMD launcher must use ASCII text: " + path.name) from exc
    return data


def build_package(source):
    source = Path(source).absolute()
    payload = {name: runtime_bytes(source / name) for name in RUNTIME_FILES}
    if sum(map(len, payload.values())) > MAX_TOTAL_BYTES:
        raise PackageError("Runtime payload exceeds the package size bound")
    engine = payload["Aegis.ps1"].decode("utf-8-sig")
    versions, banners = VERSION.findall(engine), BANNER.findall(engine)
    if len(versions) != 1 or banners != versions:
        raise PackageError("Engine version function and banner must agree exactly")
    version = versions[0]
    manifest = "".join(
        hashlib.sha256(payload[name]).hexdigest() + "  " + name + "\r\n"
        for name in sorted(payload)
    ).encode("ascii")
    payload["SHA256SUMS.txt"] = manifest
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo("Aegis-" + version + "/" + name,
                                   date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, payload[name])
    return version, buffer.getvalue()


def check_archive(output, expected):
    check_links(output)
    try:
        if not output.is_file() or output.stat().st_size != len(expected):
            raise PackageError("Missing or stale Aegis package: " + str(output))
        actual = output.read_bytes()
    except OSError as exc:
        raise PackageError("Cannot read Aegis package: " + str(output)) from exc
    if actual != expected:
        raise PackageError("Stale Aegis package; rebuild from the reviewed runtime source")


def write_archive(output, data):
    check_links(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=REPO / "tools" / "aegis")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true", help="compare only; never write")
    args = parser.parse_args(argv)
    try:
        version, data = build_package(args.source_dir)
        output = (args.output or REPO / "assets" / "aegis" /
                  ("Aegis-" + version + ".zip")).absolute()
        check_links(output)
        if output.suffix.lower() != ".zip" or output.resolve().is_relative_to(args.source_dir.resolve()):
            raise PackageError("Output must be a ZIP outside the runtime source directory")
        if args.check:
            check_archive(output, data)
        else:
            write_archive(output, data)
        print(json.dumps({"version": version, "archive": str(output),
                          "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                          "file_count": len(RUNTIME_FILES) + 1,
                          "status": "verified" if args.check else "built"}))
        return 0
    except (PackageError, OSError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
