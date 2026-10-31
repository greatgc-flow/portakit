"""Read-only, bounded local-original ZIP preflight for research-only xan.

Only local originals already acquired under the operator's own permissions.
No download, unzip/extract, execution, installation or catalog promotion.
An upstream release-API digest is not a publisher signature or license grant.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402

LEDGER = HERE / "research" / "CSV_ALTERNATIVES_20261031.json"
CHUNK = 1024 * 1024
MAX_ARCHIVE_BYTES = kit.core.MAX_DOWNLOAD_BYTES
MAX_MEMBERS = kit.core.MAX_ZIP_MEMBERS
MAX_EXPANDED = kit.core.MAX_ZIP_EXPANDED_BYTES
MAX_DEPTH = 32
NOTICE = ("LOCAL SOURCE SHA AND ZIP CONTENT STRUCTURE ONLY; NO VENDOR EXECUTION, "
          "PUBLISHER AUTHENTICATION, COMPANY LICENSE/EDR/TRANSFER APPROVAL, "
          "OR INSTALL PERMISSION")


class XanPreflightError(Exception):
    pass


def official_record(path=LEDGER):
    """Accept one exact RESEARCH_ONLY release record from supplemental evidence."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise XanPreflightError("Research source metadata unreadable: " + str(exc)) from exc
    if not isinstance(doc, dict) or type(doc.get("schemaVersion")) is not int or doc["schemaVersion"] != 1:
        raise XanPreflightError("Research ledger schema unsupported")
    rows = doc.get("alternatives")
    if not isinstance(rows, list):
        raise XanPreflightError("Research alternatives must be an array")
    matches = [r for r in rows if isinstance(r, dict) and r.get("id") == "xan"]
    if len(matches) != 1:
        raise XanPreflightError("Unique xan research record not found")
    xan = matches[0]
    options = xan.get("windowsX64")
    if (not isinstance(options, list) or len(options) != 1 or
            not isinstance(options[0], dict)):
        raise XanPreflightError("Unique Windows x64 original archive required")
    original = options[0]
    version = xan.get("release")
    if (xan.get("sourceRepo") != "https://github.com/medialab/xan" or
            not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version) or
            original.get("asset") != "xan-x86_64-pc-windows-msvc.zip" or
            type(original.get("size")) is not int or not 0 < original["size"] <= MAX_ARCHIVE_BYTES or
            not isinstance(original.get("sha256"), str) or
            not re.fullmatch(r"[a-f0-9]{64}", original["sha256"])):
        raise XanPreflightError("Incomplete/invalid Windows x64 xan release metadata")
    return {"candidateId": "xan", "version": version,
            "sourceRepo": xan["sourceRepo"], "assetName": original["asset"],
            "expectedBytes": original["size"], "expectedSha256": original["sha256"]}


def hash_original(stream):
    """Hash the open file handle without loading it into RAM."""
    stream.seek(0)
    digest = hashlib.sha256()
    size = 0
    while True:
        block = stream.read(CHUNK)
        if not block:
            return digest.hexdigest(), size
        size += len(block)
        if size > MAX_ARCHIVE_BYTES:
            raise XanPreflightError("Compressed original exceeds archive size limit")
        digest.update(block)


def inspect_members(stream):
    """Read every member to validate CRC and stream bounds. NO extraction."""
    entries = {}
    parents = set()
    roots = set()
    regular = directories = expanded = executables = 0
    executable_digest = None
    executable_size = None
    executable_member = None
    with zipfile.ZipFile(stream, mode="r") as archive:
        members = archive.infolist()
        if not members or len(members) > MAX_MEMBERS:
            raise XanPreflightError("Empty ZIP or excessive ZIP member count")
        for entry in members:
            filename = entry.filename
            directory = entry.is_dir()
            # ZipInfo.filename may be normalized by Python on Windows;
            # orig_filename retains the decoded pre-normalized ZIP name.
            raw_name = getattr(entry, "orig_filename", filename)
            if (not isinstance(raw_name, str) or raw_name != filename or
                    "\\" in raw_name or "\x00" in raw_name):
                raise XanPreflightError("Ambiguous or backslash ZIP member name")
            # The normal core archive path contract is intentionally reused.
            name = filename[:-1] if directory else filename
            try:
                parts = kit.core.path_parts(name, "ZIP member", "archive")
            except kit.core.PortakitError as exc:
                raise XanPreflightError("Unsafe ZIP member name: " + str(exc)) from exc
            if len(parts) > MAX_DEPTH:
                raise XanPreflightError("ZIP member path exceeds depth bound")
            key = "/".join(parts).casefold()
            if key in entries:
                raise XanPreflightError("Duplicate or Windows case-colliding ZIP member")
            entries[key] = "dir" if directory else "file"
            roots.add(parts[0].casefold())
            for idx in range(1, len(parts)):
                parents.add("/".join(parts[:idx]).casefold())
            mode = entry.external_attr >> 16
            if (entry.flag_bits & 0x1 or
                    entry.external_attr & stat.FILE_ATTRIBUTE_REPARSE_POINT or
                    stat.S_ISLNK(mode) or
                    stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise XanPreflightError("Encrypted/reparse/link/special ZIP member rejected")
            if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise XanPreflightError("Unsupported ZIP compression method")
            if entry.file_size > MAX_EXPANDED - expanded:
                raise XanPreflightError("ZIP expanded byte limit exceeded")
            expanded += entry.file_size
            if directory:
                if entry.file_size:
                    raise XanPreflightError("ZIP directory has unexpected file contents")
                directories += 1
                continue
            regular += 1
            is_executable = parts[-1].casefold() == "xan.exe"
            if is_executable:
                executables += 1
                if entry.file_size <= 0:
                    raise XanPreflightError("ZIP xan.exe member is empty")
            count = 0
            digest = hashlib.sha256() if is_executable else None
            with archive.open(entry, "r") as src:
                while True:
                    block = src.read(CHUNK)
                    if not block:
                        break
                    count += len(block)
                    if count > entry.file_size:
                        raise XanPreflightError("ZIP member exceeds declared expanded size")
                    if digest is not None:
                        digest.update(block)
            if count != entry.file_size:
                raise XanPreflightError("ZIP member shorter than declared expanded size")
            if digest is not None:
                executable_digest = digest.hexdigest()
                executable_size = count
                executable_member = name
            # zipfile verifies per-member CRC when its stream reaches EOF.
    if not regular or not executables:
        raise XanPreflightError("Archive has no regular files or no xan.exe")
    if executables != 1:
        raise XanPreflightError("Archive contains multiple xan.exe candidates")
    if any(kind == "file" and key in parents for key, kind in entries.items()):
        raise XanPreflightError("ZIP regular file used as parent directory")
    return {"members": len(entries), "regularFiles": regular,
            "directories": directories, "expandedLogicalBytes": expanded,
            "xanExeCount": executables, "rootNames": sorted(roots),
            "xanExeMember": executable_member,
            "xanExeBytes": executable_size,
            "xanExeSha256": executable_digest}


def hash_local_exe(path):
    """Hash one explicitly provided local EXE read-only; reject links and bounds.

    No PATH lookup, execution, extraction or auto-discovery. This deliberately
    does not imply the local executable is authorized by its publisher.
    """
    if path is None or not isinstance(path, (str, Path)) or not str(path).strip():
        raise XanPreflightError("Executable path must be a nonempty absolute path")
    source = Path(path)
    if not source.is_absolute() or source.name.casefold() != "xan.exe":
        raise XanPreflightError("Expected absolute path to local xan.exe")
    kit.core.check_links(source)
    if not source.is_file():
        raise XanPreflightError("Local xan.exe file not found")
    size = source.stat().st_size
    if not 0 < size <= MAX_EXPANDED:
        raise XanPreflightError("Local xan.exe size outside bounded source limit")
    with source.open("rb", buffering=0) as stream:
        digest = hashlib.sha256()
        count = 0
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            count += len(block)
            if count > MAX_EXPANDED:
                raise XanPreflightError("Local xan.exe exceeds byte limit")
            digest.update(block)
    if count != size:
        raise XanPreflightError("Local xan.exe changed during read")
    return digest.hexdigest(), count


def compare_local_executable(path, structure):
    """Bind a manually supplied local executable to the inspected ZIP member.

    Caller must inspect source structure FIRST and hash the original again
    AFTER this check. Matching bytes is not signing / enterprise approval.
    """
    expected_hash = structure.get("xanExeSha256")
    expected_size = structure.get("xanExeBytes")
    if (not isinstance(expected_hash, str) or
            not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or
            type(expected_size) is not int or expected_size <= 0 or
            expected_size > MAX_EXPANDED):
        raise XanPreflightError("ZIP's xan.exe digest or size invalid")
    before, before_size = hash_local_exe(path)
    if (before != expected_hash or before_size != expected_size):
        raise XanPreflightError("Local xan.exe does not match original ZIP member")
    after, after_size = hash_local_exe(path)
    if before != after or before_size != after_size:
        raise XanPreflightError("Local xan.exe changed during source comparison")
    return {"status": "LOCAL_EXE_MATCHES_ZIP_MEMBER",
            "sha256": before, "bytes": before_size,
            "note": "CONTENT_MATCH_ONLY_NOT_EXECUTION_OR_PUBLISHER_APPROVAL"}


def inspect(original, metadata, exe=None):
    """Audit the same original handle twice and optionally compare a local EXE."""
    if not isinstance(metadata, dict):
        raise XanPreflightError("Source metadata missing")
    expected_name = metadata.get("assetName")
    expected_size = metadata.get("expectedBytes")
    expected_hash = metadata.get("expectedSha256")
    if (not isinstance(expected_name, str) or
            expected_name != "xan-x86_64-pc-windows-msvc.zip" or
            type(expected_size) is not int or not 0 < expected_size <= MAX_ARCHIVE_BYTES or
            not isinstance(expected_hash, str) or
            not re.fullmatch(r"[a-f0-9]{64}", expected_hash)):
        raise XanPreflightError("Original release SHA, asset or byte count invalid")
    if original is None or not str(original).strip():
        raise XanPreflightError("Original source path is required")
    source = Path(original).absolute()
    kit.core.check_links(source)
    if source.name != expected_name:
        raise XanPreflightError("Expected original release asset filename")
    if not source.is_file():
        raise XanPreflightError("Local original archive missing")
    if source.stat().st_size != expected_size:
        raise XanPreflightError("Original compressed bytes disagree with release metadata")
    try:
        # An unbuffered handle is deliberate: a small ZIP can fit entirely
        # in Python's buffered-reader cache. Re-seeking that same buffered
        # handle would otherwise miss an external in-place mutation on Windows.
        with source.open("rb", buffering=0) as stream:
            before, count = hash_original(stream)
            if count != expected_size or before != expected_hash:
                raise XanPreflightError("Local original SHA-256 mismatch")
            stream.seek(0)
            structure = inspect_members(stream)
            bound_exe = (compare_local_executable(exe, structure)
                         if exe is not None else
                         {"status": "NOT_CHECKED", "sha256": None, "bytes": None,
                          "note": "NO_EXECUTABLE_PROVIDED"})
            after, final_size = hash_original(stream)
            if before != after or final_size != count:
                raise XanPreflightError("Local original changed during read-only audit")
    except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError,
            OSError, ValueError, OverflowError) as exc:
        raise XanPreflightError("ZIP/CRC/read error: " + str(exc)) from exc
    return {"schemaVersion": 1, "candidateId": "xan",
            "release": metadata.get("version", "UNKNOWN"),
            "outcome": "LOCAL_ORIGINAL_STRUCTURE_PASS",
            "sourceSHA256": before, "compressedBytes": count,
            "structure": structure, "localExeComparison": bound_exe,
            "provenance": "GITHUB_RELEASE_METADATA_SHA_NOT_PUBLISHER_SIGNATURE",
            "runtimeWindows": "NOT_VERIFIED",
            "enterprisePermission": "NOT_VERIFIED",
            "notice": NOTICE}


def display_lines(result):
    s = result["structure"]
    return [
        "PORTAKIT XAN OFFLINE ZIP PREFLIGHT (READ ONLY)",
        "CANDIDATE: xan / " + str(result["release"]),
        "ORIGINAL SHA-256 MATCH: " + result["sourceSHA256"],
        "COMPRESSED BYTES: " + str(result["compressedBytes"]),
        "MEMBERS: " + str(s["members"]) + "; regular=" + str(s["regularFiles"]) +
        "; directories=" + str(s["directories"]),
        "EXPANDED LOGICAL BYTES: " + str(s["expandedLogicalBytes"]),
        "ROOT NAMES: " + ", ".join(s["rootNames"]),
        "XAN.EXE MEMBERS: " + str(s["xanExeCount"]),
        "XAN.EXE ZIP MEMBER: " + s["xanExeMember"],
        "XAN.EXE MEMBER BYTES: " + str(s["xanExeBytes"]),
        "XAN.EXE MEMBER SHA256: " + s["xanExeSha256"],
        "LOCAL EXE COMPARISON: " + result["localExeComparison"]["status"],
        "RESULT: " + result["outcome"],
        "WINDOWS RUNTIME: " + result["runtimeWindows"],
        "ENTERPRISE APPROVAL: " + result["enterprisePermission"],
        NOTICE,
        "NO EXTRACTION / NO VENDOR EXECUTION / NO DOWNLOAD / NO INSTALL",
    ]


def emit(report, output=None):
    """No writes by default; optional create-only JSON and exact stdout log."""
    lines = display_lines(report)
    if output is None:
        for line in lines:
            print(line)
        return
    target = Path(output).absolute()
    transcript = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(transcript)
    if target == transcript or os.path.lexists(target) or os.path.lexists(transcript):
        raise XanPreflightError("Evidence JSON/log already exists; no overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    kit.core.check_links(target)
    kit.core.check_links(transcript)
    # No overwrite. On failure, remove only output paths still referencing
    # the same regular files created by this invocation, never foreign files.
    json_identity = log_identity = None
    try:
        with kit.sets.Evidence(transcript) as evidence:
            log_identity = kit.sets.created_output_identity(
                os.fstat(evidence.stream.fileno()))
            with target.open("x", encoding="utf-8", newline="\\n") as stream:
                json_identity = kit.sets.created_output_identity(
                    os.fstat(stream.fileno()))
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\\n")
            for line in lines:
                evidence.emit(line)
            evidence.emit("REPORT: " + str(target))
    except BaseException:
        kit.sets.cleanup_own_output(transcript, log_identity)
        kit.sets.cleanup_own_output(target, json_identity)
        raise


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--original", required=True,
                        help="previously authorized LOCAL xan 0.61.0 x64 MSVC ZIP")
    parser.add_argument("--exe", help="optional absolute LOCAL xan.exe to compare by SHA, never execute")
    parser.add_argument("--out", help="optional NEW JSON plus exact local console log")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.original, official_record(), exe=args.exe)
        emit(result, args.out)
        return 0  # SOURCE/STRUCTURE ONLY, not software release approval.
    except (XanPreflightError, kit.KitError, kit.core.PortakitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
