"""Read-only cross-check of existing xan source and CSV smoke evidence.

This is internal evidence consistency, NOT publisher authentication,
corporate permission, physical isolation, or a vendor execution test.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
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


def read_file(path, bound):
    """Read one existing bounded regular file, rejecting links/reparse paths."""
    target = Path(path).absolute()
    source.kit.core.check_links(target)
    require(target.is_file(), "Missing evidence file: " + target.name)
    size = target.stat().st_size
    require(0 < size <= bound, "Evidence file byte limit: " + target.name)
    with target.open("rb", buffering=0) as handle:
        data = handle.read(bound + 1)
    require(len(data) == size, "Evidence file changed while reading: " + target.name)
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
            doc.get("enterprisePermission") == "NOT_VERIFIED",
            "Source report mismatches release metadata or unverified gates")
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
    status = link.get("status")
    require(status in ("NOT_CHECKED", "LOCAL_EXE_MATCHES_ZIP_MEMBER"),
            "Unsupported source-to-executable comparison")
    if status == "NOT_CHECKED":
        require(link.get("sha256") is None and link.get("bytes") is None,
                "Unchecked source EXE cannot claim a digest")
        return None
    require(link.get("sha256") == structure["xanExeSha256"] and
            type(link.get("bytes")) is int and
            link["bytes"] == structure["xanExeBytes"],
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
            doc.get("performanceRanking") == "NOT_ASSESSED_SINGLE_RUN",
            "Smoke report invalid or overclaims verification")
    checks = doc.get("checks")
    require(isinstance(checks, list) and len(checks) == len(EXPECTED_CASES) and
            all(isinstance(row, dict) and
                (row.get("tool"), row.get("case")) == key and
                row.get("status") in STATUSES
                for key, row in zip(EXPECTED_CASES, checks)),
            "Smoke case list/order/status invalid")
    # A case marked PASS by the original evaluator cannot also have a
    # nonzero process exit, overflowed capture, or missing digest metadata.
    # No raw stdout is retained, so this checks *record consistency only*.
    for row in checks:
        if row["status"] != "PASS":
            continue
        require(type(row.get("returnCode")) is int and
                row["returnCode"] == 0 and
                row.get("capturedOutputTruncated") is False and
                type(row.get("stdoutBytes")) is int and
                0 < row["stdoutBytes"] <= smoke.MAX_CAPTURE and
                type(row.get("stderrBytes")) is int and
                0 <= row["stderrBytes"] <= smoke.MAX_CAPTURE and
                isinstance(row.get("stdoutSha256"), str) and
                SHA.fullmatch(row["stdoutSha256"]) is not None and
                isinstance(row.get("stderrSha256"), str) and
                SHA.fullmatch(row["stderrSha256"]) is not None,
                "PASS check contradicts recorded process/capture data")
    require(type(doc.get("inputsUnchanged")) is bool and
            type(doc.get("executablesUnchanged")) is bool and
            isinstance(doc.get("unexpectedWorkspaceEntries"), list) and
            all(isinstance(x, str) for x in doc["unexpectedWorkspaceEntries"]),
            "Smoke consistency flags absent")
    hashes = doc.get("exeSha256Local")
    fixtures = doc.get("syntheticInputSha256")
    require(isinstance(hashes, dict) and isinstance(fixtures, dict) and
            all(isinstance(hashes.get(k), str) and
                SHA.fullmatch(hashes[k]) for k in ("miller", "xan")) and
            all(isinstance(fixtures.get(k), str) and
                SHA.fullmatch(fixtures[k]) for k in ("edge", "bulk")),
            "EXE/fixture SHA fields absent or malformed")
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
    with source.kit.sets.Evidence(log) as evidence:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        for line in lines:
            evidence.emit(line)


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
