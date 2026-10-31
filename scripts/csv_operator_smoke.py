"""Small, opt-in Windows CSV smoke for xan versus the existing Miller baseline.

No vendor commands run by default. 'run' requires explicit dual consent,
pre-existing local exe paths and a NEW evidence directory on an approved,
physically offline nonproduction Windows host. This is NOT a sandbox, a
software provenance check, a speed ranking, or a catalog admission.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402

MAX_ROWS = 100000
MAX_TIMEOUT = 120
MAX_CAPTURE = 256 * 1024
SCHEMA_VERSION = 1
NOTICE = ("SYNTHETIC FUNCTIONAL SMOKE ONLY; no network isolation, publisher "
          "provenance, company EULA/EDR/transfer approval or performance ranking.")
EDGE_ROWS = [
    ["id", "name", "note"],
    ["1", "한글", "comma, retained as data"],
    ["2", "a,b", "quote \"inside\""],
    ["3", "", ""],
    ["4", "Élodie", "line 1\nline 2"],
    ["5", "😀", "trailing blank"],
]
class SmokeError(Exception):
    pass


def build_cases(miller_exe, xan_exe, folder):
    """Only documented CLI operations; never shell strings or untrusted SQL."""
    edge = str(folder / "edge.csv")
    bulk = str(folder / "bulk.csv")
    return [
        ("miller", "count", [str(miller_exe), "--csv", "count", bulk]),
        ("xan", "count", [str(xan_exe), "count", "--check-alignment", bulk]),
        ("miller", "select",
         [str(miller_exe), "--csv", "cut", "-f", "id,name", edge]),
        ("xan", "select", [str(xan_exe), "select", "id,name", edge]),
    ]


def sample_lines(rows):
    """Show a short, copyable plan without resolving vendor paths or writing."""
    return [
        "PORTAKIT CSV COMPARISON / PLAN ONLY",
        "TOOLS: existing SHA-pinned Miller; unapproved research-only xan 0.61.0",
        "FIXTURES: deterministic synthetic CSV only; edge quoting/Unicode/CRLF",
        "OPERATIONS: count on " + str(rows) +
        " generated records; select id,name on 5 edge records",
        "RUN: python -I scripts/csv_operator_smoke.py run "
        "--miller-exe D:\\ApprovedTools\\miller\\mlr.exe "
        "--xan-exe D:\\ApprovedTools\\xan\\xan.exe "
        "--evidence-dir D:\\LocalEvidence\\CSV-001 "
        "--yes --approved-offline",
        "CONDITIONS: approved nonproduction offline Windows, "
        "approved local executables, new evidence directory",
        "NO VENDOR EXECUTION / NO FILE WRITES IN PLAN",
        NOTICE,
    ]


def validate_executable(path, basename):
    """Check local path and expected filename, never resolve a PATH alias."""
    if path is None or not isinstance(path, (str, Path)) or not str(path):
        raise SmokeError("Both absolute executable paths are required")
    source = Path(path)
    if not source.is_absolute() or source.name.casefold() != basename:
        raise SmokeError("Expected absolute path to " + basename)
    kit.core.check_links(source)
    if not source.is_file():
        raise SmokeError("Approved local executable not found: " + basename)
    return source


def file_hash(path):
    kit.core.check_links(path)
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_fixtures(folder, rows):
    """Two bounded deterministic fixtures inside the explicitly new directory."""
    if type(rows) is not int or not (1 <= rows <= MAX_ROWS):
        raise SmokeError("rows must be an integer between 1 and " + str(MAX_ROWS))
    edge = folder / "edge.csv"
    bulk = folder / "bulk.csv"
    with edge.open("x", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\r\n")
        writer.writerows(EDGE_ROWS)
    with bulk.open("x", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\r\n")
        writer.writerow(EDGE_ROWS[0])
        for n in range(1, rows + 1):
            writer.writerow([str(n), "name" + str(n % 17), "synthetic"])
    return {"edge": file_hash(edge), "bulk": file_hash(bulk)}


def call_vendor(argv, folder, timeout):
    """Run an approved CLI with bounded *live* stdout/stderr pipe consumption.

    Each reader retains at most MAX_CAPTURE+1 bytes. Overflow terminates the
    direct process rather than allowing subprocess.run to accumulate unlimited
    output in RAM. Separate pipes must be drained concurrently to avoid the
    classic stdout/stderr deadlock. This is NOT OS sandboxing, a process-tree
    kill, or a CPU/RAM/disk/network quota for the vendor process.
    """
    start = time.perf_counter()
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=str(folder), shell=False)
    except OSError as exc:
        return (None, b"", str(exc).encode("utf-8", errors="replace"),
                round((time.perf_counter() - start) * 1000, 3), "RUNTIME_ERROR")

    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()
    read_failure = threading.Event()

    def drain(pipe, buffer):
        try:
            while True:
                chunk = os.read(pipe.fileno(), 8192)
                if not chunk:
                    break
                available = MAX_CAPTURE + 1 - len(buffer)
                if available > 0:
                    buffer.extend(chunk[:available])
                if len(buffer) > MAX_CAPTURE:
                    overflow.set()
                    # Stop generation as soon as the byte cap is observed.
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break
        except OSError:
            read_failure.set()
        finally:
            pipe.close()

    readers = [
        threading.Thread(target=drain, args=(process.stdout, buffers[0]),
                         daemon=True),
        threading.Thread(target=drain, args=(process.stderr, buffers[1]),
                         daemon=True),
    ]
    try:
        for thread in readers:
            thread.start()
    except RuntimeError as exc:
        # Failing to start a reader must not orphan a just-launched vendor.
        try:
            process.kill()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
        for thread in readers:
            if thread.ident is not None:
                thread.join(timeout=2)
        for pipe in (process.stdout, process.stderr):
            try:
                pipe.close()
            except OSError:
                pass
        return (process.returncode, b"",
                str(exc).encode("utf-8", errors="replace"),
                round((time.perf_counter() - start) * 1000, 3),
                "RUNTIME_ERROR")
    error = None
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        error = "TIMEOUT"
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            error = "RUNTIME_ERROR"
    except OSError:
        error = "RUNTIME_ERROR"
        try:
            process.kill()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    for thread in readers:
        thread.join(timeout=2)
    if any(thread.is_alive() for thread in readers):
        # E.g. an untrusted child process inherited a pipe. Do not call PASS.
        read_failure.set()
        for pipe in (process.stdout, process.stderr):
            try:
                pipe.close()
            except OSError:
                pass
    if overflow.is_set():
        error = "OUTPUT_LIMIT"
    elif read_failure.is_set():
        error = "RUNTIME_ERROR"
    return (process.returncode, bytes(buffers[0]), bytes(buffers[1]),
            round((time.perf_counter() - start) * 1000, 3), error)


def check_output(tool, case, payload, rows):
    """Validate semantics, not line endings, CSV quoting style or timings."""
    try:
        text = payload.decode("utf-8-sig", errors="strict")
        if case == "count":
            if tool == "xan":
                if text.strip() != str(rows):
                    return "FAIL"
            elif list(csv.reader(io.StringIO(text, newline=""), strict=True)) != [
                    ["count"], [str(rows)]]:
                return "FAIL"
        elif case == "select":
            actual = list(csv.reader(io.StringIO(text, newline=""), strict=True))
            expected = [record[:2] for record in EDGE_ROWS]
            if actual != expected:
                return "FAIL"
        else:
            raise SmokeError("Unknown comparison operation")
        return "PASS"
    except (UnicodeError, csv.Error, ValueError):
        return "FAIL"


def evaluate(tool, case, response, rows):
    """Bound and classify vendor output; never infer missing values as PASS."""
    rc, stdout, stderr, millis, error = response
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise SmokeError("Runner returned non-byte stdout/stderr")
    result = {
        "tool": tool, "case": case, "status": "ERROR",
        "returnCode": rc, "durationMilliseconds": millis,
        "stdoutBytes": len(stdout), "stderrBytes": len(stderr),
        # Hashes cover the CAPTURED prefix, never claim a digest for data
        # that was intentionally rejected and not retained.
        "stdoutSha256": hashlib.sha256(stdout).hexdigest(),
        "stderrSha256": hashlib.sha256(stderr).hexdigest(),
        "capturedOutputTruncated": (len(stdout) > MAX_CAPTURE or
                                    len(stderr) > MAX_CAPTURE),
    }
    if len(stdout) > MAX_CAPTURE or len(stderr) > MAX_CAPTURE:
        result["status"] = "OUTPUT_LIMIT"
    elif error is not None:
        result["status"] = error
    elif rc != 0:
        result["status"] = "COMMAND_FAILED"
    else:
        result["status"] = check_output(tool, case, stdout, rows)
    return result


def execute(miller_path, xan_path, evidence_dir, rows, timeout,
            approved_offline, yes, runner=None, windows=None):
    """Explicit opt-in; source fingerprint != vendor archive authenticity."""
    if type(yes) is not bool or type(approved_offline) is not bool or (
            not yes or not approved_offline):
        raise SmokeError("run requires BOTH --yes AND --approved-offline")
    if windows is None:
        windows = os.name == "nt"
    if windows is not True:
        raise SmokeError("Real vendor execution requires an approved Windows host")
    if type(rows) is not int or not 1 <= rows <= MAX_ROWS:
        raise SmokeError("rows outside allowed 1..100000")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT:
        raise SmokeError("timeout outside allowed 1..120 seconds")
    miller = validate_executable(miller_path, "mlr.exe")
    xan = validate_executable(xan_path, "xan.exe")
    if evidence_dir is None or not str(evidence_dir).strip():
        raise SmokeError("run requires --evidence-dir")
    folder = Path(evidence_dir).absolute()
    kit.core.check_links(folder)
    if os.path.lexists(folder):
        raise SmokeError("Evidence directory already exists; choose a NEW path")
    before_executables = {"miller": file_hash(miller), "xan": file_hash(xan)}
    # Do not create an evidence tree until approval, both binaries, paths and
    # all resource bounds have been verified.
    folder.mkdir(parents=True, exist_ok=False)
    hashes = prepare_fixtures(folder, rows)
    calls = build_cases(miller, xan, folder)
    invoker = runner if runner is not None else call_vendor
    results = []
    for tool, case, argv in calls:
        try:
            response = invoker(argv, folder, timeout)
            item = evaluate(tool, case, response, rows)
        except Exception as exc:
            # A mocked runner or vendor adapter failure is NOT evidence of PASS.
            item = {"tool": tool, "case": case, "status": "ERROR",
                    "errorType": type(exc).__name__}
        results.append(item)
    # Vendor processes might modify or delete fixtures, binaries or current
    # working directory files. Report the divergence, never fabricate PASS.
    try:
        unchanged_inputs = hashes == {
            "edge": file_hash(folder / "edge.csv"),
            "bulk": file_hash(folder / "bulk.csv"),
        }
    except (OSError, kit.core.PortakitError):
        unchanged_inputs = False
    try:
        unchanged_exes = before_executables == {
            "miller": file_hash(miller), "xan": file_hash(xan),
        }
    except (OSError, kit.core.PortakitError):
        unchanged_exes = False
    try:
        unexpected_entries = [
            p.relative_to(folder).as_posix() for p in folder.rglob("*")
            if p.relative_to(folder).as_posix() not in ("edge.csv", "bulk.csv")
        ]
    except (OSError, kit.core.PortakitError):
        unexpected_entries = ["UNKNOWN_SCAN_ERROR"]
    outcome = ("FUNCTIONAL_PASS_ONLY"
               if all(r["status"] == "PASS" for r in results)
               and unchanged_inputs and unchanged_exes and not unexpected_entries
               else "BLOCKED")
    return folder, {
        "schemaVersion": SCHEMA_VERSION,
        "outcome": outcome,
        "rowsCounted": rows,
        "timeoutSeconds": timeout,
        "host": "OPERATOR_ATTESTED_WINDOWS_OFFLINE_NOT_VERIFIED_BY_SCRIPT",
        "exeSha256Local": before_executables,
        "syntheticInputSha256": hashes,
        "inputsUnchanged": unchanged_inputs,
        "executablesUnchanged": unchanged_exes,
        "unexpectedWorkspaceEntries": sorted(unexpected_entries),
        "checks": results,
        "companyUseEDRRedistribution": "NOT_VERIFIED",
        "vendorArchiveProvenance": "NOT_VERIFIED",
        "performanceRanking": "NOT_ASSESSED_SINGLE_RUN",
        "notice": NOTICE,
    }


def report_lines(result):
    lines = [
        "PORTAKIT CSV OPERATOR SMOKE (SYNTHETIC; OPT-IN)",
        "RESULT: " + result["outcome"],
        "ROWS: " + str(result["rowsCounted"]),
        "TIMEOUT PER CALL (SECONDS): " + str(result["timeoutSeconds"]),
        "MILLER LOCAL EXE SHA256: " + result["exeSha256Local"]["miller"],
        "XAN LOCAL EXE SHA256: " + result["exeSha256Local"]["xan"],
    ]
    for case in result["checks"]:
        lines.append(
            case["tool"] + " / " + case["case"] + " / " + case["status"] +
            " / ms=" + str(case.get("durationMilliseconds", "UNKNOWN")))
    lines.extend([
        "INPUT HASHES INTACT: " + str(result["inputsUnchanged"]),
        "EXECUTABLE HASHES INTACT: " + str(result["executablesUnchanged"]),
        "UNEXPECTED WORKSPACE ENTRIES: " + ", ".join(
            result["unexpectedWorkspaceEntries"]) if result["unexpectedWorkspaceEntries"]
            else "UNEXPECTED WORKSPACE ENTRIES: none",
        "VENDOR ARCHIVE PROVENANCE: " + result["vendorArchiveProvenance"],
        "LEGAL/EDR/TRANSFER: " + result["companyUseEDRRedistribution"],
        "PERFORMANCE RANKING: " + result["performanceRanking"],
        NOTICE,
    ])
    return lines


def emit(folder, result):
    """Create JSON plus stdout-mirrored console log, never overwrite evidence."""
    target = folder / "result.json"
    log = folder / "console.log"
    kit.core.check_links(target)
    kit.core.check_links(log)
    if os.path.lexists(target) or os.path.lexists(log):
        raise SmokeError("Evidence files already exist; no overwrite")
    with kit.sets.Evidence(log) as evidence:
        with target.open("x", encoding="utf-8", newline="\n") as out:
            json.dump(result, out, indent=2, ensure_ascii=False)
            out.write("\n")
        for line in report_lines(result):
            evidence.emit(line)


def plan(rows=10000):
    if type(rows) is not int or not 1 <= rows <= MAX_ROWS:
        raise SmokeError("rows outside allowed 1..100000")
    for line in sample_lines(rows):
        print(line)
    return 2  # Not yet executed; never imply successful live validation.


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command")
    inspect = commands.add_parser("plan", help="read-only plan (default)")
    inspect.add_argument("--rows", type=int, default=10000)
    command = commands.add_parser("run", help="explicit real vendor executable smoke")
    command.add_argument("--miller-exe", required=True)
    command.add_argument("--xan-exe", required=True)
    command.add_argument("--evidence-dir", required=True)
    command.add_argument("--rows", type=int, default=10000)
    command.add_argument("--timeout-sec", type=int, default=20)
    command.add_argument("--yes", action="store_true")
    command.add_argument("--approved-offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "plan"):
            return plan(getattr(args, "rows", 10000))
        folder, result = execute(
            args.miller_exe, args.xan_exe, args.evidence_dir,
            args.rows, args.timeout_sec, args.approved_offline, args.yes)
        emit(folder, result)
        return 0 if result["outcome"] == "FUNCTIONAL_PASS_ONLY" else 2
    except (SmokeError, kit.KitError, kit.core.PortakitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
