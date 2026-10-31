"""Read-only cross-check of existing xan source and CSV smoke evidence.

This is internal evidence consistency, NOT publisher authentication,
corporate permission, physical isolation, or a vendor execution test.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xan_zip_preflight as source  # noqa: E402
import csv_operator_smoke as smoke  # noqa: E402

MAX_REPORT_BYTES = 1024 * 1024
MAX_FIXTURE_BYTES = 32 * 1024 * 1024
SHA = re.compile(r"[a-f0-9]{64}\Z")
EXPECTED_CASES = (("miller", "count"), ("xan", "count"),
                  ("miller", "select"), ("xan", "select"))
STATUSES = {"PASS", "FAIL", "ERROR", "OUTPUT_LIMIT", "TIMEOUT",
            "RUNTIME_ERROR", "COMMAND_FAILED"}
NOTICE = ("EVIDENCE CONSISTENCY ONLY: NOT publisher authenticity, "
          "company license/EDR/transfer approval, physical offline isolation "
          "or performance certification")


class EvidenceError(Exception):
    """Missing, contradictory, changed or unsupported evidence."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def require_fields(obj, fields, label):
    """Schema-v1 reports have closed field sets; additions need a new version.

    Unknown keys can otherwise smuggle a forged approval assertion into a
    self-consistent JSON/log pair without appearing in its console transcript.
    """
    require(isinstance(obj, dict) and set(obj) == set(fields),
            "Unexpected " + label + " evidence fields")


def file_signature(info):
    """Portable cross-source identity: path stat vs handle fstat on Windows.

    Windows can expose different st_ctime_ns semantics for Path.stat and
    os.fstat even for the SAME unchanged file. Compare ctime only within
    one stat source, never across path-vs-handle boundaries.
    """
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns)


def created_identity(info):
    """Minimal identity for cautious cleanup of OUR newly created outputs."""
    return (info.st_dev, info.st_ino)


def cleanup_created(path, identity):
    """Only unlink our own new regular file, never a later/foreign replacement."""
    if identity is None:
        return
    try:
        source.kit.core.check_links(path)
        info = path.stat()
        if stat.S_ISREG(info.st_mode) and created_identity(info) == identity:
            path.unlink()
    except (OSError, source.kit.core.PortakitError):
        pass


def read_file(path, bound):
    """Read one bounded regular file; fail closed on detectable replacement."""
    target = Path(path).absolute()
    source.kit.core.check_links(target)
    require(target.is_file(), "Missing evidence file: " + target.name)
    before = target.stat()
    require(stat.S_ISREG(before.st_mode), "Evidence input is not a regular file")
    require(0 < before.st_size <= bound,
            "Evidence file byte limit: " + target.name)
    with target.open("rb", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        require(file_signature(before) == file_signature(opened),
                "Evidence file changed before open: " + target.name)
        data = handle.read(bound + 1)
        after = os.fstat(handle.fileno())
        require(file_signature(opened) == file_signature(after) and
                opened.st_ctime_ns == after.st_ctime_ns,
                "Evidence file changed during read: " + target.name)
    require(len(data) == opened.st_size,
            "Evidence file changed while reading: " + target.name)
    source.kit.core.check_links(target)
    final = target.stat()
    require(file_signature(after) == file_signature(final) and
            before.st_ctime_ns == final.st_ctime_ns,
            "Evidence file replaced after read: " + target.name)
    return data


def unique_json_pairs(pairs):
    """Reject ambiguous duplicate keys at every JSON object depth."""
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON evidence key: " + key)
        result[key] = value
    return result


def reject_json_constant(value):
    """Python's JSON decoder otherwise accepts non-standard NaN/Infinity."""
    raise EvidenceError("Non-finite JSON evidence value: " + value)


def read_json(path):
    try:
        return json.loads(
            read_file(path, MAX_REPORT_BYTES).decode("utf-8"),
            object_pairs_hook=unique_json_pairs,
            parse_constant=reject_json_constant)
    except (UnicodeError, ValueError) as exc:
        raise EvidenceError("Invalid UTF-8 JSON evidence: " + str(exc)) from exc


def same_console(path, expected, source_log=False):
    """Require canonical UTF-8 bytes, not merely equal splitlines().

    Both original emitters use Evidence.emit: one '\\n' after every console
    line. Their logs must retain exact LF bytes and final newline. The source
    preflight adds one REPORT: footer with the original operator path; accept
    its location as historical text, never as a local file locator.
    """
    try:
        observed = read_file(path, MAX_REPORT_BYTES).decode("utf-8")
    except UnicodeError as exc:
        raise EvidenceError("Non UTF-8 evidence console transcript") from exc
    canonical = "\n".join(expected) + "\n"
    if source_log:
        require(observed.startswith(canonical),
                "Console transcript contradicts evidence JSON")
        footer = observed[len(canonical):]
        require(footer.startswith("REPORT: ") and
                footer.endswith("\n") and footer.count("\n") == 1 and
                "\r" not in footer and len(footer) > len("REPORT: \n"),
                "Source console report footer absent or invalid")
        # The report footer is an archival label, not a filesystem lookup.
        # No terminal-control characters may hide or spoof evidence lines.
        historical_path = footer[len("REPORT: "):-1]
        require(len(historical_path) <= 4096 and
                all(ord(character) >= 32 and ord(character) != 127
                    for character in historical_path),
                "Source console report footer contains control characters")
    else:
        require(observed == canonical,
                "Console transcript contradicts evidence JSON")


def sha_file(path):
    return hashlib.sha256(read_file(path, MAX_FIXTURE_BYTES)).hexdigest()


def expected_fixture_sha256(rows):
    """Recompute exact UTF-8 CRLF fixture hashes without writing files."""
    require(type(rows) is int and 1 <= rows <= smoke.MAX_ROWS,
            "Invalid synthetic CSV row count")
    def digest_rows(records):
        digest = hashlib.sha256()
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        for record in records:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow(record)
            digest.update(buffer.getvalue().encode("utf-8"))
        return digest.hexdigest()
    def bulk_rows():
        yield smoke.EDGE_ROWS[0]
        for number in range(1, rows + 1):
            yield [str(number), "name" + str(number % 17), "synthetic"]
    return {"edge": digest_rows(smoke.EDGE_ROWS),
            "bulk": digest_rows(bulk_rows())}

def check_source(doc, frozen):
    """Match frozen xan release metadata and the local member identity."""
    require(isinstance(doc, dict) and type(doc.get("schemaVersion")) is int and
            doc["schemaVersion"] == 1 and
            doc.get("outcome") == "LOCAL_ORIGINAL_STRUCTURE_PASS" and
            doc.get("release") == frozen["version"] and
            doc.get("sourceSHA256") == frozen["expectedSha256"] and
            doc.get("compressedBytes") == frozen["expectedBytes"] and
            doc.get("runtimeWindows") == "NOT_VERIFIED" and
            doc.get("enterprisePermission") == "NOT_VERIFIED" and
            doc.get("candidateId") == "xan" and
            doc.get("provenance") ==
            "GITHUB_RELEASE_METADATA_SHA_NOT_PUBLISHER_SIGNATURE" and
            doc.get("notice") == source.NOTICE,
            "Source report mismatches release metadata or unverified gates")
    require_fields(doc, (
        "schemaVersion", "candidateId", "release", "outcome", "sourceSHA256",
        "compressedBytes", "structure", "localExeComparison", "provenance",
        "runtimeWindows", "enterprisePermission", "notice"), "source report")
    structure = doc.get("structure")
    link = doc.get("localExeComparison")
    require(isinstance(structure, dict) and isinstance(link, dict) and
            type(structure.get("xanExeCount")) is int and
            structure["xanExeCount"] == 1 and
            type(structure.get("xanExeBytes")) is int and
            0 < structure["xanExeBytes"] <= source.MAX_EXPANDED and
            isinstance(structure.get("xanExeSha256"), str) and
            SHA.fullmatch(structure["xanExeSha256"]) is not None,
            "Source ZIP member digest/size invalid")
    require_fields(structure, (
        "members", "regularFiles", "directories", "expandedLogicalBytes",
        "xanExeCount", "rootNames", "xanExeMember", "xanExeBytes",
        "xanExeSha256"), "source structure")
    require_fields(link, ("status", "sha256", "bytes", "note"),
                   "source executable link")
    # These counts are reported by the original ZIP inspector. Check that
    # numbers, roots, bytes and members do not contradict each other.
    members = structure.get("members")
    regular = structure.get("regularFiles")
    directories = structure.get("directories")
    expanded = structure.get("expandedLogicalBytes")
    roots = structure.get("rootNames")
    require(type(members) is int and 1 <= members <= source.MAX_MEMBERS and
            type(regular) is int and 1 <= regular <= members and
            type(directories) is int and 0 <= directories < members and
            regular + directories == members and
            type(expanded) is int and
            structure["xanExeBytes"] <= expanded <= source.MAX_EXPANDED and
            isinstance(roots, list) and 1 <= len(roots) <= members and
            all(isinstance(root, str) and root and root == root.casefold()
                for root in roots) and roots == sorted(set(roots)) and
            isinstance(structure.get("xanExeMember"), str) and
            structure["xanExeMember"].casefold().endswith("xan.exe"),
            "Source ZIP structure counters/roots are inconsistent")
    # The producer has already checked each ZIP path with the shared
    # archive path rules. Verify those rules against the stored member text:
    # a string merely ending in 'xan.exe' is not a safe ZIP member path.
    member = structure["xanExeMember"]
    try:
        segments = source.kit.core.path_parts(
            member, "xan ZIP executable member", "archive")
        for root in roots:
            root_segments = source.kit.core.path_parts(
                root, "ZIP root name", "archive")
            require(len(root_segments) == 1,
                    "Source ZIP root is not one path component")
    except source.kit.core.PortakitError as exc:
        raise EvidenceError("Source ZIP member/root path unsafe") from exc
    require("\\" not in member and
            1 <= len(segments) <= source.MAX_DEPTH and
            segments[-1].casefold() == "xan.exe" and
            segments[0].casefold() in roots,
            "Source ZIP member path does not match archive structure")
    status = link.get("status")
    require(status in ("NOT_CHECKED", "LOCAL_EXE_MATCHES_ZIP_MEMBER"),
            "Unsupported source-to-executable comparison")
    if status == "NOT_CHECKED":
        require(link.get("sha256") is None and link.get("bytes") is None and
                link.get("note") == "NO_EXECUTABLE_PROVIDED",
                "Unchecked source EXE cannot claim a digest")
        return None
    require(link.get("sha256") == structure["xanExeSha256"] and
            type(link.get("bytes")) is int and
            link["bytes"] == structure["xanExeBytes"] and
            link.get("note") ==
            "CONTENT_MATCH_ONLY_NOT_EXECUTION_OR_PUBLISHER_APPROVAL",
            "ZIP member and local executable evidence differ")
    return link["sha256"]


def check_smoke(doc, folder):
    """Verify original smoke result logic and the retained fixture hashes."""
    require(isinstance(doc, dict) and type(doc.get("schemaVersion")) is int and
            doc["schemaVersion"] == smoke.SCHEMA_VERSION and
            doc.get("outcome") in ("BLOCKED", "FUNCTIONAL_PASS_ONLY") and
            type(doc.get("rowsCounted")) is int and
            1 <= doc["rowsCounted"] <= smoke.MAX_ROWS and
            type(doc.get("timeoutSeconds")) is int and
            1 <= doc["timeoutSeconds"] <= smoke.MAX_TIMEOUT and
            doc.get("vendorArchiveProvenance") == "NOT_VERIFIED" and
            doc.get("companyUseEDRRedistribution") == "NOT_VERIFIED" and
            doc.get("performanceRanking") == "NOT_ASSESSED_SINGLE_RUN" and
            doc.get("host") ==
            "OPERATOR_ATTESTED_WINDOWS_OFFLINE_NOT_VERIFIED_BY_SCRIPT" and
            doc.get("notice") == smoke.NOTICE,
            "Smoke report invalid or overclaims verification")
    require_fields(doc, (
        "schemaVersion", "outcome", "rowsCounted", "timeoutSeconds", "host",
        "exeSha256Local", "syntheticInputSha256", "inputsUnchanged",
        "executablesUnchanged", "unexpectedWorkspaceEntries", "checks",
        "companyUseEDRRedistribution", "vendorArchiveProvenance",
        "performanceRanking", "notice"), "smoke report")
    checks = doc.get("checks")
    require(isinstance(checks, list) and len(checks) == len(EXPECTED_CASES) and
            all(isinstance(row, dict) and
                (row.get("tool"), row.get("case")) == key and
                row.get("status") in STATUSES
                for key, row in zip(EXPECTED_CASES, checks)),
            "Smoke case list/order/status invalid")
    # Record-level invariants are checked for BOTH passing and blocked
    # commands. Error records produced by a raised runner exception carry
    # only errorType; evaluated process records carry bounded size/timing.
    for row in checks:
        status = row["status"]
        if status == "ERROR":
            require(set(row) == {"tool", "case", "status", "errorType"} and
                    isinstance(row.get("errorType"), str) and
                    0 < len(row["errorType"]) <= 128 and
                    row["errorType"].isidentifier(),
                    "Raised-runner ERROR record has invalid fields")
            continue
        require_fields(row, (
            "tool", "case", "status", "returnCode", "durationMilliseconds",
            "stdoutBytes", "stderrBytes", "stdoutSha256", "stderrSha256",
            "capturedOutputTruncated"), "smoke process record")
        rc = row.get("returnCode")
        elapsed = row.get("durationMilliseconds")
        out_count = row.get("stdoutBytes")
        err_count = row.get("stderrBytes")
        truncated = row.get("capturedOutputTruncated")
        require((rc is None or type(rc) is int) and
                type(elapsed) in (int, float) and
                math.isfinite(elapsed) and elapsed >= 0 and
                type(out_count) is int and
                0 <= out_count <= smoke.MAX_CAPTURE + 1 and
                type(err_count) is int and
                0 <= err_count <= smoke.MAX_CAPTURE + 1 and
                type(truncated) is bool and
                truncated == (out_count > smoke.MAX_CAPTURE or
                              err_count > smoke.MAX_CAPTURE) and
                all(isinstance(row.get(k), str) and SHA.fullmatch(row[k])
                    for k in ("stdoutSha256", "stderrSha256")),
                "Process record has invalid exit/timing/capture metadata")
        # The actual captured stream is not preserved. However, a stream
        # recorded as EMPTY has exactly one independently checkable digest.
        empty_sha = hashlib.sha256(b"").hexdigest()
        require((out_count != 0 or row["stdoutSha256"] == empty_sha) and
                (err_count != 0 or row["stderrSha256"] == empty_sha),
                "Zero-byte process stream has inconsistent SHA256")
        if status in ("PASS", "FAIL"):
            require(rc == 0 and not truncated and
                    (status != "PASS" or out_count > 0),
                    "PASS/FAIL verdict contradicts process/capture data")
        elif status == "COMMAND_FAILED":
            require(rc is not None and rc != 0 and not truncated,
                    "COMMAND_FAILED verdict contradicts return code")
        elif status == "OUTPUT_LIMIT":
            require(truncated,
                    "OUTPUT_LIMIT verdict lacks overflowed capture")
        else:
            require(status in ("TIMEOUT", "RUNTIME_ERROR"),
                    "Unsupported process status")
    require(type(doc.get("inputsUnchanged")) is bool and
            type(doc.get("executablesUnchanged")) is bool and
            isinstance(doc.get("unexpectedWorkspaceEntries"), list) and
            all(isinstance(x, str) for x in doc["unexpectedWorkspaceEntries"]),
            "Smoke consistency flags absent")
    entries = doc["unexpectedWorkspaceEntries"]
    require(entries == sorted(set(entries)) and
            ("UNKNOWN_SCAN_ERROR" not in entries or
             entries == ["UNKNOWN_SCAN_ERROR"]),
            "Smoke workspace entries contradict producer ordering/scan state")
    # Workspace names are rendered in the original operator console log.
    # Prevent a forged JSON/log pair from smuggling control characters,
    # parent traversal or Windows-unsafe path segments into that transcript.
    for workspace_name in doc["unexpectedWorkspaceEntries"]:
        if workspace_name == "UNKNOWN_SCAN_ERROR":
            continue  # Original producer's scan-error sentinel, BLOCKED only.
        try:
            parts = source.kit.core.path_parts(
                workspace_name, "unexpected smoke workspace entry", "archive")
        except source.kit.core.PortakitError as exc:
            raise EvidenceError("Unsafe unexpected workspace entry path") from exc
        require("\\" not in workspace_name and
                1 <= len(parts) <= source.MAX_DEPTH,
                "Unsafe unexpected workspace entry path")
    hashes = doc.get("exeSha256Local")
    fixtures = doc.get("syntheticInputSha256")
    require(isinstance(hashes, dict) and isinstance(fixtures, dict) and
            all(isinstance(hashes.get(k), str) and
                SHA.fullmatch(hashes[k]) for k in ("miller", "xan")) and
            all(isinstance(fixtures.get(k), str) and
                SHA.fullmatch(fixtures[k]) for k in ("edge", "bulk")),
            "EXE/fixture SHA fields absent or malformed")
    require_fields(hashes, ("miller", "xan"), "smoke executable hashes")
    require_fields(fixtures, ("edge", "bulk"), "smoke fixture hashes")
    for key in ("edge", "bulk"):
        require(sha_file(folder / (key + ".csv")) == fixtures[key],
                "Retained synthetic CSV has changed: " + key)
    expected = expected_fixture_sha256(doc["rowsCounted"])
    for key in ("edge", "bulk"):
        require(fixtures[key] == expected[key],
                "Synthetic CSV differs from deterministic fixture: " + key)
    clean = (all(row["status"] == "PASS" for row in checks) and
             doc["inputsUnchanged"] and doc["executablesUnchanged"] and
             not doc["unexpectedWorkspaceEntries"])
    require((doc["outcome"] == "FUNCTIONAL_PASS_ONLY") == clean,
            "Smoke outcome contradicts its detailed evidence")
    return hashes["xan"], clean


def verify(source_json, smoke_dir, frozen=None):
    """No file writes and no vendor processes; cross-check existing evidence."""
    source_path = Path(source_json).absolute()
    folder = Path(smoke_dir).absolute()
    require(source_path.suffix.lower() == ".json", "Source report needs .json")
    source.kit.core.check_links(folder)
    require(folder.is_dir(), "Missing existing smoke evidence directory")
    reference = source.official_record() if frozen is None else frozen
    source_doc = read_json(source_path)
    smoke_doc = read_json(folder / "result.json")
    source_exe = check_source(source_doc, reference)
    smoke_exe, functional = check_smoke(smoke_doc, folder)
    # Existing evidence emitters are the only authority for console format.
    same_console(source_path.with_suffix(".log"),
                 source.display_lines(source_doc), source_log=True)
    same_console(folder / "console.log", smoke.report_lines(smoke_doc))
    if source_exe is not None:
        require(source_exe == smoke_exe,
                "Executed xan SHA differs from source ZIP executable identity")
    complete = source_exe is not None and functional
    return {
        "schemaVersion": 1,
        "outcome": "EVIDENCE_CROSSCHECK_ONLY" if complete else "INCOMPLETE_OR_BLOCKED",
        "sourceArchiveSha256": source_doc["sourceSHA256"],
        "xanExeSha256": smoke_exe,
        "sourceExecutableMatched": source_exe is not None,
        "csvFunctionalSmokePassed": functional,
        "publisherAuthentication": "NOT_VERIFIED",
        "companyUseEDRTransfer": "NOT_VERIFIED",
        "hostIsolation": "NOT_VERIFIED_BY_SCRIPT",
        "notice": NOTICE,
    }


def display_lines(result):
    return [
        "PORTAKIT XAN/CSV EVIDENCE CROSSCHECK (READ ONLY)",
        "RESULT: " + result["outcome"],
        "SOURCE ZIP SHA256: " + result["sourceArchiveSha256"],
        "XAN EXE SHA256: " + result["xanExeSha256"],
        "SOURCE EXE MATCH: " + str(result["sourceExecutableMatched"]),
        "CSV FUNCTIONAL PASS: " + str(result["csvFunctionalSmokePassed"]),
        "PUBLISHER/ENTERPRISE/HOST APPROVAL: NOT_VERIFIED",
        NOTICE,
        "NO VENDOR EXECUTION / NO DOWNLOAD / NO INSTALL",
    ]


def emit(result, out=None):
    """No writes by default; optional NEW JSON and identical console log."""
    lines = display_lines(result)
    if out is None:
        for line in lines:
            print(line)
        return
    target = Path(out).absolute()
    log = target.with_suffix(".log")
    source.kit.core.check_links(target)
    source.kit.core.check_links(log)
    require(target.suffix.lower() == ".json" and
            target != log and not os.path.lexists(target) and
            not os.path.lexists(log), "Choose a NEW JSON/log output pair")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.kit.core.check_links(target)
    source.kit.core.check_links(log)
    # Exclusive file creation followed by conservative cleanup if a write fails.
    # In particular, a log collision must NEVER unlink that other writer's log.
    json_identity = log_identity = None
    try:
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            json_identity = created_identity(os.fstat(handle.fileno()))
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with source.kit.sets.Evidence(log) as evidence:
            log_identity = created_identity(os.fstat(evidence.stream.fileno()))
            for line in lines:
                evidence.emit(line)
    except BaseException:
        cleanup_created(log, log_identity)
        cleanup_created(target, json_identity)
        raise


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source-json", required=True,
                        help="existing xan ZIP preflight JSON (and .log)")
    parser.add_argument("--smoke-dir", required=True,
                        help="existing CSV smoke evidence directory")
    parser.add_argument("--out", help="optional NEW result JSON + matching log")
    args = parser.parse_args(argv)
    try:
        result = verify(args.source_json, args.smoke_dir)
        emit(result, args.out)
        return 0 if result["outcome"] == "EVIDENCE_CROSSCHECK_ONLY" else 2
    except (EvidenceError, source.XanPreflightError, source.kit.KitError,
            source.kit.core.PortakitError, source.kit.sets.ToolsetError,
            smoke.SmokeError, OSError, TypeError, KeyError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
