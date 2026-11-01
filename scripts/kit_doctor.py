"""One-command, read-only assessment of a saved personal PortaKit.

Composes the existing offline source, managed footprint, and optional plugin
integrity engines. No vendor executable, installer, downloader or GUI starts.
A local SHA match never establishes corporate EULA/EDR/legal approval.
"""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import offline_ready as sources  # noqa: E402
import kit_footprint as sizes  # noqa: E402
import plugin_health as plugins  # noqa: E402
import report_evidence as evidence_io  # noqa: E402

SCHEMA_VERSION = 1
NOTICE = ("LOCAL CHECKS ONLY: NOT company approval, vendor authenticity, "
          "redistribution permission, EDR clearance or GUI acceptance")


class DoctorError(Exception):
    pass


def inspect(saved, pins, root, *, archive_dir=None, skip_pending=False,
            max_mib=None):
    """Inspect without modifying a saved kit, a vendor archive, or managed files.

    Each subsystem independently enforces current SHA pins and link protections.
    Missing/pending items are NOT silently treated as available or zero-size.
    """
    if not isinstance(saved, dict):
        raise DoctorError("Invalid saved toolkit")
    if type(skip_pending) is not bool:
        raise DoctorError("skip_pending must be boolean")
    if max_mib is not None and (type(max_mib) is not int or max_mib < 0):
        raise DoctorError("max_mib must be a nonnegative integer")
    ready = sources.assess(saved, pins, root, archive_dir, skip_pending)
    measured = sizes.audit(saved, root, budget_mib=max_mib)
    if [r["id"] for r in ready["tools"]] != [r["id"] for r in measured["tools"]]:
        raise DoctorError("Readiness/footprint tool ID mismatch")
    health = (plugins.inspect(saved, pins, root)
              if saved.get("pluginSelections") else None)
    plugin_state = health["outcome"] if health is not None else "NOT_SELECTED"

    if (ready["outcome"] == "BLOCKED" or plugin_state == "BLOCKED" or
            measured["budgetResult"] == "OVER_BUDGET"):
        outcome = "BLOCKED"
    elif (ready["needInstall"] or not measured["complete"] or
          ready["researchOnlyExcluded"] or ready["osBuiltinsInformational"] or
          ready["editorPluginsExcluded"] or
          plugin_state not in ("NOT_SELECTED", "LOCAL_HASH_PASS") or
          measured["budgetResult"] == "UNKNOWN_INCOMPLETE"):
        outcome = "INCOMPLETE"
    else:
        # Only pinned managed applications already installed, no pending,
        # plugin or unmeasured size; not a statement about legal rights.
        outcome = "LOCAL_CHECKS_PASS"
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kitName": saved["name"],
        "outcome": outcome,
        "offlineReadiness": ready,
        "installedFootprint": measured,
        "pluginHealth": health,
        "notice": NOTICE,
    }


def report_lines(report):
    """One deterministic text projection for stdout and the evidence log."""
    ready = report["offlineReadiness"]
    sizes_report = report["installedFootprint"]
    result = [
        "PORTAKIT PERSONAL KIT DOCTOR (READ ONLY)",
        "KIT: " + report["kitName"],
        "OFFLINE: " + ready["outcome"] +
        " / missing pinned installs=" + str(ready["needInstall"]),
        "FOOTPRINT: " + str(sizes_report["totalMeasuredLogicalBytes"]) +
        " measured logical bytes; complete=" + str(sizes_report["complete"]) +
        "; budget=" + sizes_report["budgetResult"],
        "PLUGINS: " + (report["pluginHealth"]["outcome"]
                       if report["pluginHealth"] else "NOT_SELECTED"),
        "",
        "---- OFFLINE SOURCES ----",
    ]
    result.extend(sources.display_lines(ready))
    result.extend(["", "---- MANAGED INSTALLED SIZE ----"])
    result.extend(sizes.lines(sizes_report))
    if report["pluginHealth"] is not None:
        result.extend(["", "---- EDITOR PLUGIN HASHES ----"])
        result.extend(plugins.report_lines(report["pluginHealth"]))
    result.extend([
        "",
        "OVERALL RESULT: " + report["outcome"],
        NOTICE,
        "NO DOWNLOAD / NO INSTALL / NO VENDOR EXECUTION / NO SYSTEM CHANGES",
    ])
    return result


def emit(report, output=None):
    """Default zero writes; optional create-only JSON and stdout-mirrored log."""
    content = report_lines(report)
    if output is None:
        for line in content:
            print(line)
        return
    evidence_io.emit_json_report(
        report, content, output, error_type=DoctorError,
        collision_message="Report/log already exists; no overwrite")


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--kit", required=True, help="saved and validated personal kit JSON")
    parser.add_argument("--root", default="portable", help="managed install root")
    parser.add_argument("--archive-dir", help="optional original vendor archive directory")
    parser.add_argument("--skip-pending", action="store_true",
                        help="inspect approved subset, never approve pending tools/plugins")
    parser.add_argument("--max-mib", type=int,
                        help="optional installed logical-byte budget (whole MiB)")
    parser.add_argument("--out", help="optional NEW JSON and exactly mirrored .log")
    args = parser.parse_args(argv)
    try:
        pins, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, pins, known)
        report = inspect(saved, pins, args.root, archive_dir=args.archive_dir,
                         skip_pending=args.skip_pending, max_mib=args.max_mib)
        emit(report, args.out)
        # 0: complete local observations; 2: blocked/incomplete, 1: error.
        return 0 if report["outcome"] == "LOCAL_CHECKS_PASS" else 2
    except (DoctorError, sources.ReadinessError, sizes.FootprintError,
            plugins.HealthError, kit.KitError, kit.sets.ToolsetError,
            kit.core.PortakitError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
