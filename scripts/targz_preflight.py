"""Read-only, bounded SHA-256 and tar.gz member audit for a local original.

This is a pre-admission diagnostic, NOT a general extractor or a release gate.
It never writes extracted files, executes a binary, downloads, or grants company
permission. The existing PortaKit installer still rejects tar.gz catalog pins.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import lightweight_review as research  # noqa: E402

CHUNK = 1024 * 1024
MAX_ARCHIVE_BYTES = kit.core.MAX_DOWNLOAD_BYTES
MAX_MEMBERS = kit.core.MAX_ZIP_MEMBERS
MAX_EXPANDED_BYTES = kit.core.MAX_ZIP_EXPANDED_BYTES
MAX_DEPTH = 32
# Count gzip output INCLUDING TAR headers/padding; do not trust member sizes alone.
MAX_GZIP_OUTPUT = MAX_EXPANDED_BYTES + MAX_MEMBERS * 4096 + 10240
NOTICE = ("LOCAL ORIGINAL SHA/STRUCTURE ONLY; not publisher authentication, "
          "safe DuckDB execution, company EULA/EDR/transfer approval or install permission")


class TarAuditError(Exception):
    pass


class BoundedReader:
    """Reject a gzip bomb while tarfile consumes its uncompressed stream."""

    def __init__(self, source, limit=MAX_GZIP_OUTPUT):
        self.source = source
        self.limit = limit
        self.used = 0

    def read(self, count=-1):
        if count is None or count < 0:
            count = self.limit - self.used + 1
        data = self.source.read(min(count, self.limit - self.used + 1))
        self.used += len(data)
        if self.used > self.limit:
            raise TarAuditError("gzip uncompressed stream exceeds safe bound")
        return data


def official_pin():
    """Load only the unchanged RESEARCH_ONLY DuckDB official release metadata."""
    doc = research.load_ledger()
    rows = [r for r in doc["candidates"] if r["id"] == "duckdb-cli"]
    if len(rows) != 1:
        raise TarAuditError("DuckDB CLI research record missing or duplicated")
    rec = rows[0]
    if (rec["stage"] != "RESEARCH_ONLY" or rec["artifactType"] != "tar.gz" or
            not rec["sha256FromReleaseMetadata"]):
        raise TarAuditError("DuckDB research pin unsupported or incomplete")
    return rec


def hash_stream(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    total = 0
    while True:
        block = stream.read(CHUNK)
        if not block:
            break
        total += len(block)
        if total > MAX_ARCHIVE_BYTES:
            raise TarAuditError("Original archive exceeds compressed size limit")
        digest.update(block)
    return digest.hexdigest(), total


def read_structure(stream):
    """Stream every member and verify content without materializing any file.

    Do not call extract/extractall. No filesystem writes occur here.
    Reject PAX metadata, link types, special files, Windows collisions,
    traversal, unexpectedly large streams, duplicate paths and empty TARs.
    """
    entries = {}
    parents = set()
    roots = set()
    files = directories = expanded = 0
    with gzip.GzipFile(fileobj=stream, mode="rb") as gz:
        limited = BoundedReader(gz, limit=MAX_GZIP_OUTPUT)
        with tarfile.open(fileobj=limited, mode="r|") as archive:
            for member in archive:
                if len(entries) >= MAX_MEMBERS:
                    raise TarAuditError("TAR member count limit exceeded")
                if member.pax_headers:
                    raise TarAuditError("TAR PAX metadata unsupported; manual review needed")
                if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE,
                                       tarfile.DIRTYPE):
                    raise TarAuditError("TAR link, sparse, or special member refused")
                is_dir = member.isdir()
                name = member.name[:-1] if member.name.endswith("/") else member.name
                try:
                    parts = kit.core.path_parts(name, "TAR member", "archive")
                except kit.core.PortakitError as exc:
                    raise TarAuditError("Unsafe TAR member path: " + str(exc)) from exc
                if len(parts) > MAX_DEPTH:
                    raise TarAuditError("TAR path depth limit exceeded")
                key = "/".join(parts).casefold()
                if key in entries:
                    raise TarAuditError("TAR duplicate/case-colliding path")
                entries[key] = "dir" if is_dir else "file"
                roots.add(parts[0].casefold())
                for index in range(1, len(parts)):
                    parents.add("/".join(parts[:index]).casefold())
                if is_dir:
                    directories += 1
                    if member.size:
                        raise TarAuditError("TAR directory declares file bytes")
                    continue
                if member.size < 0 or member.size > MAX_EXPANDED_BYTES - expanded:
                    raise TarAuditError("TAR expanded bytes limit exceeded")
                expanded += member.size
                files += 1
                data = archive.extractfile(member)
                if data is None:
                    raise TarAuditError("TAR regular file body unavailable")
                count = 0
                with data:
                    while True:
                        block = data.read(CHUNK)
                        if not block:
                            break
                        count += len(block)
                        if count > member.size:
                            raise TarAuditError("TAR file exceeds declared bytes")
                if count != member.size:
                    raise TarAuditError("TAR body shorter than declared bytes")
        # Drain through EOF to force gzip CRC/truncation and output-limit checks.
        while limited.read(CHUNK):
            pass
    if not files:
        raise TarAuditError("TAR has no regular files")
    if any(kind == "file" and key in parents
           for key, kind in entries.items()):
        raise TarAuditError("TAR file used as parent directory")
    return {"members": len(entries), "regularFiles": files,
            "directories": directories, "expandedLogicalBytes": expanded,
            "rootNames": sorted(roots)}


def inspect(original, expected_sha):
    """Check the exact local source against an independently pinned digest.

    Hash the SAME open handle both before and after streaming the gzip data.
    A modified file during inspection is denied; this is still a point-in-time
    snapshot rather than a signature or protection from a privileged adversary.
    """
    if not isinstance(expected_sha, str) or len(expected_sha) != 64 or (
            any(c not in "0123456789abcdefABCDEF" for c in expected_sha)):
        raise TarAuditError("Expected SHA-256 must contain 64 hex digits")
    path = Path(original).absolute()
    kit.core.check_links(path)
    if not path.is_file():
        raise TarAuditError("Original archive not found")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise TarAuditError("Original archive exceeds compressed size limit")
    try:
        with path.open("rb") as stream:
            before, compressed = hash_stream(stream)
            if before != expected_sha.lower():
                raise TarAuditError("Original SHA-256 mismatch")
            stream.seek(0)
            structure = read_structure(stream)
            after, final_size = hash_stream(stream)
            if after != before or final_size != compressed:
                raise TarAuditError("Original changed during structural audit")
    except (gzip.BadGzipFile, tarfile.TarError, EOFError, OSError, ValueError,
            OverflowError) as exc:
        raise TarAuditError("Unsafe or unreadable TAR/gzip original: " + str(exc)) from exc
    return {"schemaVersion": 1, "candidateId": "duckdb-cli",
            "outcome": "LOCAL_ORIGINAL_STRUCTURE_PASS",
            "sourceSHA256": before, "compressedBytes": compressed,
            "structure": structure, "notice": NOTICE}


def display_lines(result):
    meta = result["structure"]
    return [
        "PORTAKIT DUCKDB TAR.GZ ORIGINAL AUDIT (READ ONLY)",
        "CANDIDATE: " + result["candidateId"],
        "SOURCE SHA256 PASS: " + result["sourceSHA256"],
        "COMPRESSED BYTES: " + str(result["compressedBytes"]),
        "MEMBERS: " + str(meta["members"]) + "; regular=" +
        str(meta["regularFiles"]) + "; directories=" + str(meta["directories"]),
        "EXPANDED LOGICAL BYTES: " + str(meta["expandedLogicalBytes"]),
        "ROOT NAMES: " + ", ".join(meta["rootNames"]),
        "RESULT: " + result["outcome"],
        NOTICE,
        "NO EXTRACTION / NO VENDOR EXECUTION / NO DOWNLOAD / NO INSTALL",
    ]


def emit(report, output=None):
    """No writes by default; optional new-only JSON and exact console log."""
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
        raise TarAuditError("Report/log already exists; no overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(transcript) as evidence:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        for line in lines:
            evidence.emit(line)
        evidence.emit("REPORT: " + str(target))


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--original", required=True,
                        help="previously authorized LOCAL DuckDB release tar.gz")
    parser.add_argument("--out", help="optional NEW JSON plus mirrored local log")
    args = parser.parse_args(argv)
    try:
        record = official_pin()
        result = inspect(args.original, record["sha256FromReleaseMetadata"])
        emit(result, args.out)
        return 0  # local SHA and structure only; not a deployment approval.
    except (TarAuditError, research.ResearchError, kit.KitError,
            kit.core.PortakitError, kit.sets.ToolsetError,
            OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
