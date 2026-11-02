"""Review operator-entered paired CSV timing evidence WITHOUT executing tools.

This is not a benchmark runner, a publisher-verification tool or an enterprise
acceptance decision. Even a complete result only proves *internal consistency*
of locally declared observations, not that Miller/xan actually ran.
"""
import argparse
import csv
import hashlib
import io
import math
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_csv_evidence as evidence  # noqa: E402
import report_evidence as evidence_io  # noqa: E402

MAX_DATASET_BYTES = 32 * 1024 * 1024
MIN_TRIALS = 5
MAX_TRIALS = 20
TOOLS = ("miller", "xan")
PHASES = ("cold", "warm")
WORKLOADS = ("count", "select", "sort", "group")
HASH = re.compile(r"[a-f0-9]{64}\Z")
ROOT_FIELDS = (
    "schemaVersion", "datasetClass", "workload", "inputSha256",
    "inputBytes", "inputRows", "toolSha256", "environmentNote",
    "coldMethod", "runs",
)
RUN_FIELDS = (
    "tool", "phase", "trial", "elapsedMs", "cpuMs", "peakRssBytes",
    "diskWrittenBytes", "exitCode", "stderrBytes", "semanticStatus",
)
NOTICE = (
    "OPERATOR-DECLARED METRICS ONLY: no vendor execution verification, "
    "cold-cache enforcement, performance ranking, license, EDR or approval"
)


class BenchmarkError(Exception):
    pass


def require(condition, detail):
    """Fail closed for incorrect source schema; never coerce a value."""
    if not condition:
        raise BenchmarkError(detail)


def number(value, *, positive=False):
    return (type(value) in (float, int) and
            (value > 0 if positive else value >= 0) and
            value <= 1000000000 and math.isfinite(value))


def has_hash(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def validate(doc):
    """Closed schema, bounded measurements and unique tool/phase/trial slots."""
    require(isinstance(doc, dict) and set(doc) == set(ROOT_FIELDS),
            "Benchmark root fields invalid")
    require(type(doc["schemaVersion"]) is int and doc["schemaVersion"] == 1,
            "Benchmark schema version unsupported")
    require(doc["datasetClass"] == "SYNTHETIC_OPERATOR_DECLARED" and
            doc["workload"] in WORKLOADS, "Dataset/workload not supported")
    require(isinstance(doc["toolSha256"], dict) and
            set(doc["toolSha256"]) == set(TOOLS),
            "Both tool digests must be declared")
    require(doc["inputSha256"] is None or has_hash(doc["inputSha256"]),
            "Invalid input SHA256")
    require(doc["inputBytes"] is None or
            (type(doc["inputBytes"]) is int and
             0 < doc["inputBytes"] <= MAX_DATASET_BYTES),
            "Invalid input byte count")
    require(doc["inputRows"] is None or
            (type(doc["inputRows"]) is int and
             1 <= doc["inputRows"] <= 1000000),
            "Invalid input row count")
    for name in TOOLS:
        require(doc["toolSha256"][name] is None or
                has_hash(doc["toolSha256"][name]),
                "Invalid tool SHA256: " + name)
    for name in ("environmentNote", "coldMethod"):
        value = doc[name]
        require(value is None or
                (isinstance(value, str) and 1 <= len(value) <= 300 and
                 all(32 <= ord(char) < 127 for char in value)),
                "Invalid local method note: " + name)
    entries = doc["runs"]
    require(isinstance(entries, list) and len(entries) <= 4 * MAX_TRIALS,
            "Run array exceeds fixed bound or is not an array")
    seen = set()
    for run in entries:
        require(isinstance(run, dict) and set(run) == set(RUN_FIELDS),
                "Run fields invalid or overclaiming")
        tool, phase, trial = (run["tool"], run["phase"], run["trial"])
        require(tool in TOOLS and phase in PHASES and
                type(trial) is int and 1 <= trial <= MAX_TRIALS,
                "Unknown tool/phase/trial")
        key = (tool, phase, trial)
        require(key not in seen, "Duplicate tool/phase/trial measurement")
        seen.add(key)
        require(number(run["elapsedMs"], positive=True),
                "Elapsed milliseconds missing or invalid")
        require(run["cpuMs"] is None or number(run["cpuMs"]),
                "Invalid optional CPU time")
        for field in ("peakRssBytes", "diskWrittenBytes"):
            require(run[field] is None or
                    (type(run[field]) is int and 0 <= run[field] <= 10**12),
                    "Invalid optional metric: " + field)
        require(run["exitCode"] is None or
                (type(run["exitCode"]) is int and -32768 <= run["exitCode"] <= 32767),
                "Invalid process exit code")
        require(run["stderrBytes"] is None or
                (type(run["stderrBytes"]) is int and
                 0 <= run["stderrBytes"] <= MAX_DATASET_BYTES),
                "Invalid stderr byte count")
        require(run["semanticStatus"] in
                ("MATCH", "MISMATCH", "NOT_VERIFIED"),
                "Invalid self-reported semantic status")
    return entries


def dataset_identity(path, doc):
    """Compare local source hash, bytes and CSV row count with claimed input."""
    raw = evidence.read_file(path, MAX_DATASET_BYTES)
    require(len(raw) == doc["inputBytes"] and
            hashlib.sha256(raw).hexdigest() == doc["inputSha256"],
            "Actual dataset bytes/SHA differ from declared source")
    try:
        content = raw.decode("utf-8-sig", errors="strict")
        require("\x00" not in content, "Dataset is not UTF-8 CSV")
        records = csv.reader(io.StringIO(content, newline=""), strict=True)
        header = next(records)
        require(len(header) > 0 and all(header), "Dataset header invalid")
        count = 0
        for row in records:
            require(len(row) == len(header), "Dataset columns not aligned")
            count += 1
        require(count == doc["inputRows"], "Dataset row count differs")
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise BenchmarkError("Invalid synthetic CSV dataset") from exc
    return True


def expected_order(n):
    """Counterbalance paired order by trial; this checks JSON order only."""
    result = []
    for phase in PHASES:
        for trial in range(1, n + 1):
            tools = TOOLS if trial % 2 else tuple(reversed(TOOLS))
            result.extend((tool, phase, trial) for tool in tools)
    return result


def inspect(doc, dataset=None):
    """Never rank vendors, even when descriptive source metadata is complete."""
    runs = validate(doc)
    fields_present = (
        doc["inputSha256"] is not None and
        doc["inputBytes"] is not None and
        doc["inputRows"] is not None and
        all(doc["toolSha256"][tool] is not None for tool in TOOLS) and
        doc["environmentNote"] is not None and
        doc["coldMethod"] is not None
    )
    if dataset is not None and fields_present:
        dataset_identity(dataset, doc)
        input_verified = True
    else:
        input_verified = False
    n = len(runs) // 4
    full = (fields_present and input_verified and
            MIN_TRIALS <= n <= MAX_TRIALS and len(runs) == 4 * n and
            [(r["tool"], r["phase"], r["trial"]) for r in runs] ==
            expected_order(n) and
            all(r["exitCode"] == 0 and r["stderrBytes"] == 0 and
                r["semanticStatus"] == "MATCH" for r in runs))
    groups = []
    if full:
        for phase in PHASES:
            for tool in TOOLS:
                current = [r for r in runs if r["phase"] == phase and
                           r["tool"] == tool]
                samples = [r["elapsedMs"] for r in current]
                groups.append({
                    "tool": tool, "phase": phase, "trials": n,
                    "minMs": min(samples),
                    "medianMs": statistics.median(samples),
                    "maxMs": max(samples),
                    "cpuMetric": "RECORDED_ALL" if all(
                        r["cpuMs"] is not None for r in current)
                        else "NOT_MEASURED_OR_PARTIAL",
                    "rssMetric": "RECORDED_ALL" if all(
                        r["peakRssBytes"] is not None for r in current)
                        else "NOT_MEASURED_OR_PARTIAL",
                    "diskMetric": "RECORDED_ALL" if all(
                        r["diskWrittenBytes"] is not None for r in current)
                        else "NOT_MEASURED_OR_PARTIAL",
                })
    return {
        "schemaVersion": 1,
        "outcome": ("DESCRIPTIVE_TIMING_ONLY" if full
                    else "INCOMPLETE_OR_BLOCKED"),
        "declaredWorkload": doc["workload"],
        "sourceBytesAndRowsVerified": input_verified,
        "trialsPerToolPhase": n if full else None,
        "groups": groups,
        "vendorRuntime": "OPERATOR_DECLARED_NOT_INDEPENDENTLY_VERIFIED",
        "coldCache": "OPERATOR_METHOD_NOT_MACHINE_VERIFIED",
        "publisherAuthenticity": "NOT_VERIFIED",
        "companyApproval": "NOT_VERIFIED",
        "performanceRanking": "NOT_ASSESSED",
        "notice": NOTICE,
    }


def lines(report):
    result = ["PORTAKIT CSV PERFORMANCE RECORD REVIEW (NO EXECUTION)",
              "RESULT: " + report["outcome"],
              "WORKLOAD: " + report["declaredWorkload"],
              "SOURCE BYTES/ROWS VERIFIED: " +
              str(report["sourceBytesAndRowsVerified"])]
    for row in report["groups"]:
        result.append(
            row["tool"] + " / " + row["phase"] +
            " / trials=" + str(row["trials"]) +
            " / min-ms=" + str(row["minMs"]) +
            " / median-ms=" + str(row["medianMs"]) +
            " / max-ms=" + str(row["maxMs"]) +
            " / cpu=" + row["cpuMetric"] +
            " / rss=" + row["rssMetric"] +
            " / disk=" + row["diskMetric"])
    result.extend(["VENDOR RUN / COLD CACHE: NOT INDEPENDENTLY VERIFIED",
                   "COMPANY APPROVAL / PERFORMANCE RANKING: NOT_VERIFIED",
                   NOTICE])
    return result


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", help="existing operator-entered JSON record")
    parser.add_argument("--dataset", help="existing local synthetic CSV original")
    parser.add_argument("--out", help="optional NEW JSON and exact local .log")
    args = parser.parse_args(argv)
    if args.input is None and args.dataset is None and args.out is None:
        print("PLAN_ONLY: populate research/CSV_BENCHMARK_TEMPLATE.json locally; "
              "run with --input EXISTING.json --dataset SYNTHETIC.csv. "
              "No tool execution or writes.")
        return 2
    try:
        require(args.input is not None, "--input is required")
        if args.out is not None:
            require(args.dataset is not None, "--dataset is required with --out")
            target = Path(args.out).absolute()
            require(target.suffix.lower() == ".json", "--out requires .json")
            for origin in (args.input, args.dataset):
                original = Path(origin).absolute()
                require(target != original and target.with_suffix(".log") != original,
                        "Output may not overwrite an input")
        record = evidence.read_json(args.input)
        report = inspect(record, args.dataset)
        if args.out is None:
            for entry in lines(report):
                print(entry)
        else:
            evidence_io.emit_json_report(
                report, lines(report), args.out, error_type=BenchmarkError,
                collision_message="Benchmark report/log already exists; no overwrite")
        return 0 if report["outcome"] == "DESCRIPTIVE_TIMING_ONLY" else 2
    except (BenchmarkError, evidence.EvidenceError,
            evidence.source.kit.core.PortakitError,
            evidence.source.kit.KitError,
            evidence.source.kit.sets.ToolsetError,
            OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
