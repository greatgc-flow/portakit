"""Create tiny CSV compatibility fixtures for separate operator review.

Default is a read-only PLAN.  Explicit --out-dir creates a NEW local directory
containing bounded synthetic CSVs and a JSON/console evidence pair.  This never
runs or acquires Miller/xan, grants admission or makes an enterprise verdict.
"""
import argparse
import codecs
import csv
import hashlib
import io
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import csv_operator_smoke as smoke  # noqa: E402
import report_evidence as evidence_io  # noqa: E402

MAX_TOTAL_BYTES = 16 * 1024
NOTICE = ("SYNTHETIC FILES ONLY; no vendor execution, compatibility result, "
          "license/EDR/transfer approval, network-isolation or performance claim.")
GROUP_ROWS = [
    ["category", "qty", "id"],
    ["B", "10", "r1"],
    ["A", "2", "r2"],
    ["A", "9", "r3"],
    ["B", "1", "r4"],
    ["A", "3", "r5"],
]
CASE_NOTES = {
    "edge-utf8.csv": "UTF8_WITHOUT_BOM_QUOTED_MULTILINE_CRLF",
    "edge-utf8-bom.csv": "UTF8_BOM_VENDOR_BEHAVIOR_NOT_VERIFIED",
    "edge-utf16le.csv": "UTF16LE_BOM_VENDOR_BEHAVIOR_NOT_VERIFIED",
    "malformed-quote.csv": "INVALID_UNTERMINATED_QUOTE_OBSERVE_ERROR",
    "sort-group.csv": "NUMERIC_SORT_AND_GROUP_SUM_REFERENCE_ONLY",
}


class FixtureError(Exception):
    pass


def csv_bytes(rows):
    """Canonical CRLF CSV, preserving embedded newline and quoted fields."""
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def fixtures():
    """No files or vendor processes; values are small deterministic bytes."""
    edge = csv_bytes(smoke.EDGE_ROWS)
    cases = {
        "edge-utf8.csv": edge,
        "edge-utf8-bom.csv": codecs.BOM_UTF8 + edge,
        "edge-utf16le.csv": (
            codecs.BOM_UTF16_LE + edge.decode("utf-8").encode("utf-16le")),
        "malformed-quote.csv": b'id,name\r\n1,"unterminated\r\n',
        "sort-group.csv": csv_bytes(GROUP_ROWS),
    }
    if (set(cases) != set(CASE_NOTES) or
            sum(len(v) for v in cases.values()) > MAX_TOTAL_BYTES or
            any(not v for v in cases.values())):
        raise FixtureError("Synthetic compatibility fixture contract changed")
    return cases


def reference():
    """Compute expectations from source rows, not output of a vendor tool."""
    data = GROUP_ROWS[1:]
    groups = {}
    for category, quantity, _ in data:
        groups[category] = groups.get(category, 0) + int(quantity)
    return {
        "sortQtyAscendingIds": [
            rec[2] for rec in sorted(data, key=lambda r: int(r[1]))],
        "groupQtySumByCategory": {key: groups[key] for key in sorted(groups)},
        "sortNumericNotLexical": True,
        "otherCases": "OBSERVE_VENDOR_BEHAVIOR_NO_PREDECLARED_PASS",
    }


def manifest(cases):
    """Declare only immutable synthetic input identity; no runtime verdict."""
    return {
        "schemaVersion": 1,
        "outcome": "PREPARED_ONLY_NOT_VENDOR_TESTED",
        "files": [{
            "name": name,
            "bytes": len(cases[name]),
            "sha256": hashlib.sha256(cases[name]).hexdigest(),
            "case": CASE_NOTES[name],
        } for name in sorted(cases)],
        "reference": reference(),
        "vendorExecution": "NOT_RUN",
        "licenseEDRTransfer": "NOT_VERIFIED",
        "notice": NOTICE,
    }


def report_lines(report):
    """Compact console transcript, byte-identical to new matrix.log on write."""
    lines = ["PORTAKIT CSV COMPATIBILITY FIXTURES (SOURCE ONLY)",
             "RESULT: " + report["outcome"]]
    for file in report["files"]:
        lines.append(file["name"] + " / bytes=" + str(file["bytes"]) +
                     " / sha256=" + file["sha256"] + " / " + file["case"])
    lines.extend([
        "NUMERIC SORT IDS: " + ",".join(report["reference"]["sortQtyAscendingIds"]),
        "GROUP SUM: " + ", ".join(
            k + "=" + str(v) for k, v in
            report["reference"]["groupQtySumByCategory"].items()),
        "VENDOR: NOT_RUN / ENTERPRISE: NOT_VERIFIED", NOTICE,
    ])
    return lines


def prepare(out_dir, cases=None):
    """Create a new directory and fixtures, never replace existing evidence.

    On failure, the partially created directory may remain for local review.
    Never automatically remove a folder, its contents or another writer's file.
    A successful matrix.json/.log pair is the source-only completion evidence.
    """
    if not isinstance(out_dir, (str, os.PathLike)) or not str(out_dir).strip():
        raise FixtureError("Explicit nonempty --out-dir required")
    folder = Path(out_dir).absolute()
    kit.core.check_links(folder)
    if os.path.lexists(folder):
        raise FixtureError("Output directory already exists; choose a NEW path")
    if cases is None:
        cases = fixtures()
    report = manifest(cases)
    folder.mkdir(parents=True, exist_ok=False)
    kit.core.check_links(folder)
    for name, data in cases.items():
        dest = folder / name
        kit.core.check_links(dest)
        with dest.open("xb") as stream:
            stream.write(data)
        kit.core.check_links(dest)
        if dest.read_bytes() != data:
            raise FixtureError("New synthetic fixture changed: " + name)
    evidence_io.emit_json_report(
        report, report_lines(report), folder / "matrix.json",
        error_type=FixtureError,
        collision_message="Compatibility report/log already exists; no overwrite")
    return report


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--out-dir", help="explicit NEW local directory; omit for no-write plan")
    args = parser.parse_args(argv)
    try:
        if args.out_dir is None:
            for line in report_lines(manifest(fixtures())):
                print(line)
            print("STATUS: PLAN_ONLY / NO FILES / NO VENDOR EXECUTION")
            return 2
        prepare(args.out_dir)
        return 0  # FIxture creation only; NEVER a vendor compatibility PASS.
    except (FixtureError, kit.core.PortakitError, kit.KitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
