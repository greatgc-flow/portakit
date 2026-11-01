"""Read-only logical-byte footprint audit for a saved PortaKit.

No downloads, execution, installs, deletions or network activity. Traverses
only currently managed, exact catalog-pinned folders and refuses symlink/junction
trees. Report values are logical file bytes, NOT physical allocated disk usage.
"""
import argparse
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import report_evidence as evidence_io  # noqa: E402

SCHEMA = 1
MAX_ENTRIES = 100000
MAX_DEPTH = 64


class FootprintError(Exception):
    pass


def tree_usage(directory):
    """Count logical bytes, files and folders, never following reparse paths.

    Bounds protect diagnostics on unexpectedly enormous trees. This is not a
    snapshot: concurrent filesystem modifications can invalidate the result.
    """
    root = Path(directory)
    kit.core.check_links(root)
    if not root.is_dir():
        raise FootprintError("Managed directory unavailable: " + str(root))
    total, files, folders, visited = 0, 0, 0, 0
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise FootprintError("Directory depth limit exceeded")
        kit.core.check_links(current)
        with os.scandir(current) as entries:
            for entry in entries:
                visited += 1
                if visited > MAX_ENTRIES:
                    raise FootprintError("Entry count limit exceeded")
                path = Path(entry.path)
                # Reparse-points can include non-symlink junctions on Windows.
                if kit.core.is_reparse(path):
                    raise FootprintError("Reparse path encountered: " + str(path))
                details = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(details.st_mode):
                    raise FootprintError("Link encountered: " + str(path))
                if stat.S_ISDIR(details.st_mode):
                    folders += 1
                    stack.append((path, depth + 1))
                elif stat.S_ISREG(details.st_mode):
                    files += 1
                    total += details.st_size
                else:
                    raise FootprintError("Unexpected special file: " + str(path))
    return {"logicalBytes": total, "files": files, "directories": folders}


def audit(saved, root, *, budget_mib=None):
    """Use the exact kit pin locks and core managed state, without mutation."""
    if budget_mib is not None and (
            type(budget_mib) is not int or budget_mib < 0):
        raise FootprintError("Budget must be a nonnegative whole MiB value")
    pins, _, _, known = kit.inventory()
    # Validate saved snapshot also when called directly from unit tests.
    if not isinstance(saved, dict) or not isinstance(saved.get("tools"), list):
        raise FootprintError("Invalid saved kit")
    if not isinstance(saved.get("lockedPins"), dict):
        raise FootprintError("Invalid kit pin locks")
    root = Path(os.path.abspath(str(root)))
    kit.core.check_links(root)
    state = kit.core.read_state(root)
    rows = []
    total = 0
    # Budget cannot certify a complete toolkit when OS-only or research
    # selections have no measured managed files.
    complete = not (saved["researchOnly"] or saved["osBuiltins"]
                    or saved.get("pluginSelections"))
    for ident in saved["tools"]:
        if ident not in saved["lockedPins"]:
            continue
        if ident not in pins or saved["lockedPins"][ident] != {
                k: pins[ident][k] for k in ("version", "sha256", "dest")}:
            raise FootprintError("PIN_CHANGED or invalid saved lock: " + ident)
        pin = pins[ident]
        status = kit.sets.status_of(dict(pin, id=ident), root, state)
        record = {"id": ident, "version": pin["version"], "status": status,
                  "logicalBytes": None, "files": None, "directories": None}
        if status == "already-installed":
            installed = kit.core.safe_path(root, pin["dest"], "managed tool directory")
            metrics = tree_usage(installed)
            record.update(metrics)
            total += metrics["logicalBytes"]
        else:
            complete = False
        rows.append(record)

    limit = budget_mib * 1024 * 1024 if budget_mib is not None else None
    budget_state = "NOT_REQUESTED"
    if limit is not None:
        budget_state = "OVER_BUDGET" if total > limit else (
            "PASS" if complete else "UNKNOWN_INCOMPLETE")
    return {
        "schemaVersion": SCHEMA, "kitName": saved["name"],
        "measurement": "LOGICAL_FILE_BYTES_NOT_ALLOCATED_DISK_BYTES",
        "root": str(root), "tools": rows,
        "selectedPinned": len(rows),
        "measuredPinned": sum(1 for row in rows if row["logicalBytes"] is not None),
        "totalMeasuredLogicalBytes": total,
        "complete": complete,
        "budgetMiB": budget_mib, "budgetResult": budget_state,
        "researchOnlyNotMeasured": list(saved["researchOnly"]),
        "osBuiltinsNotMeasured": list(saved["osBuiltins"]),
        "editorPluginsNotMeasured": [
            x["id"] for x in saved.get("pluginSelections", [])],
        "notice": "Read-only, no software launched. A concurrent write can change these values.",
    }



def confirm_readiness_alignment(readiness, measured):
    """Reject a contradictory pair of independent point-in-time diagnostics.

    Readiness and footprint read the same managed files independently, so a
    concurrent change could otherwise produce a misleading combined report.
    Require exact root, ordered pinned IDs, and per-tool install status.
    Empty pinned-tool selections are valid when both lists are empty; this
    check does not make the underlying filesystem snapshots atomic.
    """
    if not isinstance(readiness, dict) or not isinstance(measured, dict):
        raise FootprintError("Invalid readiness/footprint report")
    first, second = readiness.get("tools"), measured.get("tools")
    if not isinstance(first, list) or not isinstance(second, list):
        raise FootprintError("Invalid readiness/footprint rows")
    if (not isinstance(readiness.get("root"), str)
            or not isinstance(measured.get("root"), str)
            or readiness["root"] != measured["root"]):
        raise FootprintError("Readiness/footprint root mismatch")
    if len(first) != len(second):
        raise FootprintError("Readiness/footprint tool ID mismatch")
    for ready_row, size_row in zip(first, second):
        if not isinstance(ready_row, dict) or not isinstance(size_row, dict):
            raise FootprintError("Invalid readiness/footprint tool row")
        ident = ready_row.get("id")
        if (not isinstance(ident, str)
                or ident != size_row.get("id")):
            raise FootprintError("Readiness/footprint tool ID mismatch")
        if (not isinstance(ready_row.get("installStatus"), str)
                or not isinstance(size_row.get("status"), str)
                or ready_row["installStatus"] != size_row["status"]):
            raise FootprintError(
                "Readiness/footprint install status changed during inspection: "
                + ident)



def lines(data):
    """Single source for displayed text and matching stored evidence."""
    result = ["KIT: " + data["kitName"],
              "MEASUREMENT: " + data["measurement"]]
    for row in data["tools"]:
        size = str(row["logicalBytes"]) if row["logicalBytes"] is not None else "UNKNOWN"
        result.append("TOOL: " + row["id"] + " / " + row["status"] +
                      " / logicalBytes=" + size)
    result.extend([
        "MEASURED: " + str(data["measuredPinned"]) + "/" +
        str(data["selectedPinned"]),
        "TOTAL MEASURED LOGICAL BYTES: " + str(data["totalMeasuredLogicalBytes"]),
        "BUDGET RESULT: " + data["budgetResult"],
        "NOT MEASURED RESEARCH: " + str(len(data["researchOnlyNotMeasured"])),
        "NOT MEASURED OS: " + str(len(data["osBuiltinsNotMeasured"])),
        data["notice"], "NO INSTALL / NO DOWNLOAD / NO CHANGES",
    ])
    return result


def create_report(data, outfile):
    """New-only local JSON report + exact byte-mirrored console transcript."""
    evidence_io.emit_json_report(
        data, lines(data), outfile, error_type=FootprintError,
        collision_message="Report/evidence already exists; no overwrite")


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--kit", required=True, help="validated personal kit JSON")
    parser.add_argument("--root", default="portable", help="existing managed install root")
    parser.add_argument("--max-mib", type=int,
                        help="optional logical-byte threshold; unknown tools never PASS")
    parser.add_argument("--out", help="optional new report JSON + console-matched log")
    args = parser.parse_args(argv)
    try:
        pins, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, pins, known)
        data = audit(saved, args.root, budget_mib=args.max_mib)
        if args.out:
            create_report(data, args.out)
        else:
            for line in lines(data):
                print(line)
        # For automation: UNKNOWN cannot be interpreted as passing a budget.
        # 0 = fully measured PASS or no budget; 2 = incomplete; 3 = over budget.
        if data["budgetResult"] == "UNKNOWN_INCOMPLETE":
            return 2
        if data["budgetResult"] == "OVER_BUDGET":
            return 3
        return 0
    except (FootprintError, kit.KitError, kit.core.PortakitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
