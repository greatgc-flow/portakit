"""One read-only, pure-Python overview for the optional personal-kit picker.

The overview REUSES offline readiness and managed-file logical-size audits;
it does not download, package, execute or install vendor binaries. A displayed
READY refers only to local SHA input readiness, not corporate permission.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import offline_ready as ready  # noqa: E402
import kit_footprint as footprint  # noqa: E402


class OverviewError(Exception):
    pass


def inspect(saved, pins, root, archive_dir=None, *, skip_pending=False, budget_mib=None):
    """Synchronous explicit user-invoked snapshot; no writes or network.

    Size is measured for ALREADY MANAGED pinned tools only; absent tools,
    research, OS builtins and editor plugins have UNKNOWN footprint.
    """
    if not isinstance(saved, dict) or not isinstance(saved.get("tools"), list):
        raise OverviewError("Invalid personal kit draft")
    if not isinstance(pins, dict):
        raise OverviewError("Invalid approved pin catalog")
    if not isinstance(root, (str, Path)) or not str(root).strip():
        raise OverviewError("Existing managed root path is required")
    if archive_dir is not None and (
            not isinstance(archive_dir, (str, Path)) or not str(archive_dir).strip()):
        raise OverviewError("Archive directory must be a nonempty path or omitted")
    if type(skip_pending) is not bool:
        raise OverviewError("skip_pending must be a boolean")
    if budget_mib is not None and (
            type(budget_mib) is not int or budget_mib < 0):
        raise OverviewError("Budget must be a nonnegative whole MiB number")

    r = ready.assess(saved, pins, root, archive_dir, skip_pending)
    f = footprint.audit(saved, root, budget_mib=budget_mib)
    sizes = {row["id"]: row for row in f["tools"]}
    rows = []
    for tool in r["tools"]:
        metrics = sizes[tool["id"]]
        rows.append({
            "id": tool["id"],
            "installStatus": tool["installStatus"],
            "sourceStatus": tool["sourceStatus"],
            "originalFilename": tool["originalFilename"],
            "logicalBytes": metrics["logicalBytes"],
        })
    return {
        "kitName": r["kitName"],
        "root": r["root"],
        "archiveDirectory": r["archiveDirectory"],
        "outcome": r["outcome"],
        "pinnedTotal": r["pinnedTotal"],
        "needInstall": r["needInstall"],
        "alreadyInstalled": r["alreadyInstalled"],
        "researchCount": len(r["researchOnlyExcluded"]),
        "osCount": len(r["osBuiltinsInformational"]),
        "pluginCount": len(r["editorPluginsExcluded"]),
        "measuredLogicalBytes": f["totalMeasuredLogicalBytes"],
        "measuredPinned": f["measuredPinned"],
        "sizeComplete": f["complete"],
        "budgetMiB": budget_mib,
        "budgetResult": f["budgetResult"],
        "tools": rows,
        "blockers": list(r["blockers"]),
        "notices": [
            "Source readiness is point-in-time and DOES NOT grant corporate or vendor transfer rights.",
            "Size is installed MANAGED LOGICAL BYTES only; unknown sizes never treated as zero.",
            "No downloads, installs, system changes, vendor execution, or publication.",
        ],
    }


def format_lines(result):
    """Single model-level text formatting shared by GUI and tests."""
    if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
        raise OverviewError("Invalid overview result")
    lines = [
        "PERSONAL KIT: " + result["kitName"],
        "MANAGED ROOT: " + result["root"],
        "ORIGINAL SOURCES: " + (result["archiveDirectory"] or "not supplied"),
        "OFFLINE READINESS: " + result["outcome"],
        "SELECTED: pinned={} | installed={} | need install={} | research={} | OS={} | plugins={}".format(
            result["pinnedTotal"], result["alreadyInstalled"], result["needInstall"],
            result["researchCount"], result["osCount"], result["pluginCount"]),
        "INSTALLED LOGICAL SIZE: {} bytes (measured {} of {} pinned)".format(
            result["measuredLogicalBytes"], result["measuredPinned"], result["pinnedTotal"]),
        "SIZE COVERAGE: " + ("COMPLETE" if result["sizeComplete"] else "UNKNOWN_INCOMPLETE"),
        "SIZE BUDGET: " + result["budgetResult"] +
        (" ({} MiB)".format(result["budgetMiB"])
         if result["budgetMiB"] is not None else ""),
        "",
        "PINNED TOOL DETAILS",
    ]
    if not result["tools"]:
        lines.append("  (no pinned tools selected)")
    for row in result["tools"]:
        size = ("UNKNOWN" if row["logicalBytes"] is None else
                "{} logical bytes".format(row["logicalBytes"]))
        lines.append("  {} | {} | archive={} | size={}".format(
            row["id"], row["installStatus"], row["sourceStatus"], size))
        if row["installStatus"] == "install":
            lines.append("    ORIGINAL FILE: " + row["originalFilename"])
    lines.append("")
    lines.append("BLOCKERS / STILL REQUIRED")
    if not result["blockers"]:
        lines.append("  (none in this point-in-time source check)")
    else:
        lines.extend("  " + message for message in result["blockers"])
    lines.append("")
    lines.extend(result["notices"])
    return lines
