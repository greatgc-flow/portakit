"""Independently verify PortaKit Office evidence ZIP, SHA-256 ledger and verdict.

Python 3.11+ stdlib; read-only. Works without WinMerge or Microsoft Office.
Zero result means the archive is internally consistent, NOT that Office passed.
Use --require-pass if the caller needs a real four-application PASS gate.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

APPLICATIONS = {"Excel": ".xlsx", "Word": ".docx",
                "PowerPoint": ".pptx", "Visio": ".vsdx"}
MAX_FILES = 256
MAX_UNCOMPRESSED = 128 * 1024 * 1024
STATUSES = {0: "PASS", 1: "FAIL", 2: "NOT_VERIFIED"}


class EvidenceError(ValueError):
    """A package cannot be treated as verified evidence."""


def sha256_stream(source):
    sha = hashlib.sha256()
    size = 0
    while True:
        data = source.read(128 * 1024)
        if not data:
            break
        size += len(data)
        if size > MAX_UNCOMPRESSED:
            raise EvidenceError("Evidence file exceeds validation limit")
        sha.update(data)
    return sha.hexdigest(), size


def safe_member(name):
    if (not isinstance(name, str) or not name or "\\" in name
            or name.startswith("/") or "\x00" in name):
        raise EvidenceError("Unsafe ZIP member name")
    parts = PurePosixPath(name).parts
    if (not parts or any(p in (".", "..", "") or ":" in p for p in parts)
            or any(p.endswith((" ", ".")) for p in parts)):
        raise EvidenceError("Unsafe ZIP member path: " + name)


def parse_results(contents):
    try:
        with io.TextIOWrapper(io.BytesIO(contents), encoding="utf-8-sig",
                              errors="strict", newline="") as text:
            reader = csv.DictReader(text)
            if not reader.fieldnames or not {"Application", "Status", "Detail"}.issubset(
                    set(reader.fieldnames)):
                raise EvidenceError("results.csv missing required columns")
            rows = list(reader)
    except UnicodeError as exc:
        raise EvidenceError("Invalid CSV encoding") from exc
    names = {}
    for row in rows:
        name = row["Application"]
        status = row["Status"]
        if (name not in APPLICATIONS or name in names
                or status not in set(STATUSES.values())):
            raise EvidenceError("Unknown/duplicate application or status in results.csv")
        names[name] = status
    return names


def html_has_markers(contents):
    # Official report versions may write UTF-8 or UTF-16 text. Require
    # both distinct markers in the HTML, not just a binary ZIP difference.
    markers = (b"BASELINE", b"DIFFERENT")
    if all(x in contents for x in markers):
        return True
    if (contents.startswith(b"\xff\xfe") or contents.startswith(b"\xfe\xff")
            or b"\x00" in contents[:64]):
        for codec in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                text = contents.decode(codec)
                if all(x in text for x in ("BASELINE", "DIFFERENT")):
                    return True
            except UnicodeError:
                pass
    return False


def verify(archive_path, checksum_path=None):
    archive_path = Path(archive_path)
    sidecar = (Path(checksum_path) if checksum_path is not None
               else archive_path.with_name(archive_path.name + ".sha256.txt"))
    if not archive_path.is_file() or not sidecar.is_file():
        raise EvidenceError("Both evidence ZIP and its SHA256 sidecar are required")
    try:
        declared = sidecar.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError("Invalid checksum sidecar") from exc
    match = re.fullmatch(r"([a-fA-F0-9]{64})  ([^\r\n]+)", declared)
    if not match or match.group(2) != archive_path.name:
        raise EvidenceError("Checksum sidecar format/name mismatch")
    with archive_path.open("rb") as source:
        digest, _ = sha256_stream(source)
    if digest != match.group(1).lower():
        raise EvidenceError("ZIP SHA-256 does not match sidecar")

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            if len(infos) < 2 or len(infos) > MAX_FILES:
                raise EvidenceError("Unexpected ZIP member count")
            names = set()
            data = {}
            total = 0
            for item in infos:
                safe_member(item.filename)
                key = item.filename.casefold()
                if key in names:
                    raise EvidenceError("Duplicate/case-colliding ZIP member")
                names.add(key)
                if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16):
                    raise EvidenceError("Directory or symbolic link not permitted")
                total += item.file_size
                if item.file_size > MAX_UNCOMPRESSED or total > MAX_UNCOMPRESSED:
                    raise EvidenceError("ZIP uncompressed data exceeds limit")
                with archive.open(item, "r") as stream:
                    raw = stream.read(MAX_UNCOMPRESSED + 1)
                if len(raw) != item.file_size:
                    raise EvidenceError("ZIP size mismatch")
                data[item.filename] = raw
            if "manifest.json" not in data:
                raise EvidenceError("Evidence manifest.json missing")
    except (OSError, zipfile.BadZipFile, EOFError, RuntimeError) as exc:
        raise EvidenceError("Unreadable evidence ZIP") from exc

    try:
        manifest = json.loads(data["manifest.json"].decode("utf-8"))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise EvidenceError("Invalid manifest JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != "portakit-office-evidence-v1":
        raise EvidenceError("Unknown manifest format")
    exit_code = manifest.get("script_exit_code")
    if type(exit_code) is not int or exit_code not in STATUSES:
        raise EvidenceError("Invalid recorded acceptance exit")
    verdict = STATUSES[exit_code]
    if manifest.get("office_runtime") != verdict:
        raise EvidenceError("Manifest verdict and exit code disagree")
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != len(data) - 1:
        raise EvidenceError("Manifest file count mismatch")
    recorded = set()
    for row in records:
        if not isinstance(row, dict):
            raise EvidenceError("Invalid file record")
        name, size, sha = row.get("path"), row.get("size"), row.get("sha256")
        safe_member(name)
        if (name == "manifest.json" or name in recorded or name not in data
                or type(size) is not int or size < 0 or
                not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha)):
            raise EvidenceError("Invalid manifest file entry: " + str(name))
        recorded.add(name)
        contents = data[name]
        if len(contents) != size or hashlib.sha256(contents).hexdigest() != sha.lower():
            raise EvidenceError("Evidence contents mismatch: " + name)
    if recorded != set(data) - {"manifest.json"}:
        raise EvidenceError("Untracked or missing evidence member")
    statuses = parse_results(data["results.csv"]) if "results.csv" in data else {}
    if verdict in ("PASS", "NOT_VERIFIED") and set(statuses) != set(APPLICATIONS):
        raise EvidenceError("Complete four-app results.csv required for PASS/NOT_VERIFIED")
    if verdict == "PASS" and any(status != "PASS" for status in statuses.values()):
        raise EvidenceError("PASS requires four successful Office applications")
    if verdict == "NOT_VERIFIED" and (any(s == "FAIL" for s in statuses.values())
                                     or not any(s == "NOT_VERIFIED" for s in statuses.values())):
        raise EvidenceError("NOT_VERIFIED must contain at least one unavailable app and no FAIL")
    if verdict == "FAIL" and statuses and all(s == "PASS" for s in statuses.values()):
        raise EvidenceError("FAIL verdict conflicts with all application PASS rows")

    for app, status in statuses.items():
        if status != "PASS":
            continue
        ext = APPLICATIONS[app]
        required = [app + "/" + p for p in
                    ("left" + ext, "right" + ext, "identical" + ext,
                     "identical.html", "different.html")]
        if not all(name in data and len(data[name]) > 0 for name in required):
            raise EvidenceError(app + " PASS is missing Office fixtures or HTML reports")
        if (len(data[app + "/identical.html"]) < 100 or
                len(data[app + "/different.html"]) < 100 or
                not html_has_markers(data[app + "/different.html"])):
            raise EvidenceError(app + " PASS has no semantic Office text evidence")
    return {"verified": True, "archive_sha256": digest, "office_runtime": verdict,
            "script_exit_code": exit_code, "applications": statuses,
            "file_count": len(records)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, help="Office evidence ZIP")
    parser.add_argument("--sha256", help="SHA-256 sidecar; default ZIP.sha256.txt")
    parser.add_argument("--require-pass", action="store_true",
                        help="Exit 2 for a valid but non-PASS ZIP")
    args = parser.parse_args(argv)
    try:
        result = verify(args.zip, args.sha256)
    except (EvidenceError, OSError, ValueError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if args.require_pass and result["office_runtime"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
