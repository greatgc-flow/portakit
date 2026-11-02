"""Read-only semantic cross-check of separately captured xan/Miller CSV outputs.

The four CSV results are operator-supplied bytes; this script NEVER launches
Miller/xan, verifies process exit/stderr, authenticates binaries, or grants
software approval. Missing files are explicitly INCOMPLETE, not a PASS.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import csv_compat_fixtures as matrix  # noqa: E402
import verify_csv_evidence as evidence  # noqa: E402
import report_evidence as evidence_io  # noqa: E402

MAX_OUTPUT_BYTES = 16 * 1024
NUMBER = re.compile(r"(?:0|[1-9][0-9]{0,5})(?:\.0{1,6})?\Z")
CASES = (
    ("miller-sort.csv", "sort"),
    ("xan-sort.csv", "sort"),
    ("miller-group.csv", "group"),
    ("xan-group.csv", "group"),
)
NOTICE = (
    "OUTPUT SEMANTICS ONLY; vendor execution, exit/stderr, original binary, "
    "company EULA/EDR/transfer, offline host and performance NOT VERIFIED"
)


class ComparisonError(Exception):
    pass


def lexical_path(value):
    """Collapse dot components for comparisons without following reparse links.

    File access still uses the original path and existing check_links guards.
    """
    return Path(os.path.normpath(str(Path(value).absolute())))


def checked_directory(folder, label):
    """Require an existing non-reparse directory; never create any input."""
    if not isinstance(folder, (str, os.PathLike)) or not str(folder).strip():
        raise ComparisonError(label + " requires a nonempty directory path")
    path = Path(folder).absolute()
    matrix.kit.core.check_links(path)
    if not path.is_dir():
        raise ComparisonError(label + " directory not found")
    return path


def verify_fixtures(folder):
    """Require exactly the original deterministic byte corpus and manifest.

    Do not trust self-reported hashes alone: both manifest and five fixtures
    are independently recomputed from source, not vendor output.
    """
    cases = matrix.fixtures()
    expected = matrix.manifest(cases)
    canonical = (json.dumps(expected, indent=2, ensure_ascii=False) +
                 "\n").encode("utf-8")
    actual = evidence.read_file(folder / "matrix.json", evidence.MAX_REPORT_BYTES)
    if actual != canonical:
        raise ComparisonError("Compatibility manifest differs from source")
    evidence.same_console(
        folder / "matrix.log", matrix.report_lines(expected), source_log=True)
    for name, known in cases.items():
        observed = evidence.read_file(folder / name, matrix.MAX_TOTAL_BYTES)
        if observed != known:
            raise ComparisonError("Compatibility source fixture changed: " + name)
    return expected


def records(data, columns):
    """Strict bounded CSV parse, independent of column order and CRLF style."""
    try:
        content = data.decode("utf-8-sig", errors="strict")
        if "\x00" in content:
            return None  # UTF-16 is not silently treated as UTF-8.
        lines = list(csv.reader(io.StringIO(content, newline=""), strict=True))
    except (UnicodeError, csv.Error, ValueError):
        return None
    if (len(lines) < 2 or len(lines[0]) != len(columns) or
            len(set(lines[0])) != len(columns) or
            set(lines[0]) != set(columns) or
            any(len(row) != len(columns) for row in lines[1:])):
        return None
    return [dict(zip(lines[0], row)) for row in lines[1:]]


def integral(value):
    """Accept an exact nonnegative integer, optionally printed as 14.0."""
    if not isinstance(value, str) or not NUMBER.fullmatch(value):
        return None
    return Decimal(value)


def check_sort(data):
    """Check all fields and ascending *numeric* order, not lexical order."""
    rows = records(data, ("category", "qty", "id"))
    if rows is None or len(rows) != len(matrix.GROUP_ROWS) - 1:
        return False
    expected = {row[2]: row for row in matrix.GROUP_ROWS[1:]}
    if [r["id"] for r in rows] != matrix.reference()["sortQtyAscendingIds"]:
        return False
    return all(
        r["id"] in expected and r["category"] == expected[r["id"]][0] and
        integral(r["qty"]) == Decimal(expected[r["id"]][1])
        for r in rows
    )


def check_group(data):
    """Compare grouped sums as values; allow different output row ordering."""
    rows = records(data, ("category", "qty_sum"))
    if rows is None or len(rows) != 2:
        return False
    expected = matrix.reference()["groupQtySumByCategory"]
    if set(r["category"] for r in rows) != set(expected):
        return False
    return (len(set(r["category"] for r in rows)) == len(rows) and
            all(integral(r["qty_sum"]) == Decimal(expected[r["category"]])
                for r in rows))


def inspect(fixtures_dir, results_dir):
    """Recheck source provenance, then inspect bounded external CSV outputs.

    Success means only matching *captured* CSV semantics; the caller must not
    infer process exit, stderr, origin of the files or real vendor approval.
    """
    source = checked_directory(fixtures_dir, "Fixture")
    outputs = checked_directory(results_dir, "Results")
    if lexical_path(source) == lexical_path(outputs):
        raise ComparisonError("Fixture and results directories must differ")
    verify_fixtures(source)
    rows = []
    for name, operation in CASES:
        path = outputs / name
        matrix.kit.core.check_links(path)
        if not os.path.lexists(path):
            rows.append({"name": name, "status": "MISSING",
                         "bytes": None, "sha256": None})
            continue
        data = evidence.read_file(path, MAX_OUTPUT_BYTES)
        matches = (check_sort(data) if operation == "sort" else
                   check_group(data))
        rows.append({
            "name": name,
            "status": "MATCH" if matches else "MISMATCH",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "schemaVersion": 1,
        "outcome": ("SEMANTIC_MATCH_ONLY" if all(
            case["status"] == "MATCH" for case in rows)
            else "INCOMPLETE_OR_MISMATCH"),
        "syntheticInputVerified": True,
        "results": rows,
        "vendorExecution": "NOT_OBSERVED",
        "vendorExitAndStderr": "NOT_OBSERVED",
        "companyApproval": "NOT_VERIFIED",
        "performanceRanking": "NOT_ASSESSED",
        "notice": NOTICE,
    }


def lines(report):
    output = [
        "PORTAKIT CSV COMPATIBILITY OUTPUT CHECK (READ ONLY)",
        "RESULT: " + report["outcome"],
        "SOURCE FIXTURES: VERIFIED EXACT BYTES",
    ]
    for row in report["results"]:
        output.append(
            row["name"] + " / " + row["status"] + " / bytes=" +
            ("NOT_PRESENT" if row["bytes"] is None else str(row["bytes"])) +
            " / sha256=" + (row["sha256"] or "NOT_PRESENT"))
    output.extend(["VENDOR PROCESS / EXIT / STDERR: NOT_OBSERVED",
                   "COMPANY APPROVAL / PERFORMANCE: NOT_VERIFIED", NOTICE])
    return output


def emit(report, output=None, inputs=()):
    """Read-only by default; optional new-only mirrored JSON/log elsewhere."""
    if output is None:
        for line in lines(report):
            print(line)
        return
    target = Path(output).absolute()
    if target.suffix.casefold() != ".json":
        raise ComparisonError("--out must end in .json")
    # The raw path may contain `other/../fixtures`: compare normalized
    # locations, but preserve original paths for the reparse safety checks.
    normalized_target = lexical_path(target)
    for folder in inputs:
        normalized_folder = lexical_path(folder)
        if (normalized_target == normalized_folder or
                normalized_folder in normalized_target.parents):
            raise ComparisonError("--out must be outside input directories")
    evidence_io.emit_json_report(
        report, lines(report), target,
        error_type=ComparisonError,
        collision_message="Comparison report/log already exists; no overwrite")


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--fixtures-dir", help="existing source-only fixture directory")
    parser.add_argument("--results-dir", help="existing local CSV result directory")
    parser.add_argument("--out", help="optional NEW JSON and exact console .log")
    args = parser.parse_args(argv)
    if args.fixtures_dir is None and args.results_dir is None and args.out is None:
        print("PLAN_ONLY: provide --fixtures-dir and --results-dir; no files "
              "will be created or vendor processes executed")
        return 2
    try:
        if args.fixtures_dir is None or args.results_dir is None:
            raise ComparisonError("Both --fixtures-dir and --results-dir required")
        report = inspect(args.fixtures_dir, args.results_dir)
        emit(report, args.out, inputs=(
            Path(args.fixtures_dir).absolute(), Path(args.results_dir).absolute()))
        return 0 if report["outcome"] == "SEMANTIC_MATCH_ONLY" else 2
    except (ComparisonError, evidence.EvidenceError,
            matrix.kit.core.PortakitError, matrix.kit.KitError,
            matrix.kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
