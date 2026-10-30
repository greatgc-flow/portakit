"""Read-only personal editor-plugin health report for field acceptance.

All results are observations, not certification of vendor legitimacy, legal
approval, EDR clearance, actual plugin load or future filesystem integrity.
No plugin binary, app, downloader, installer, registry or network is invoked.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import plugin_offline as offline  # noqa: E402

SCHEMA_VERSION = 1
NOTICE = ("READ_ONLY_INTEGRITY_SNAPSHOT: NOT vendor signature, EDR approval, "
          "license authorization or real GUI acceptance")


class HealthError(Exception):
    pass


def inspect(saved, pins, root):
    """Classify all explicitly chosen plugins using the existing safe plan.

    The plan validates receipts, SHA-pinned host state and every deployed file.
    Missing/unselected plugins are NEVER inferred as successfully installed.
    """
    rows, pending = offline.make_plan(saved, pins, root)
    results = []
    for row in rows:
        status = row["status"]
        if status == "already-installed":
            category = "VERIFIED_LOCAL_HASH"
        elif status == "install":
            category = "NOT_INSTALLED"
        elif status.startswith("blocked-"):
            category = "BLOCKED"
        else:
            raise HealthError("Unrecognized plugin state: " + status)
        results.append({"id": row["id"], "host": row["host"],
                        "sourceState": status, "assessment": category})
    for ident in pending:
        results.append({"id": ident, "host": None,
                        "sourceState": "RESEARCH_ONLY",
                        "assessment": "NOT_APPROVED_FOR_INSTALL"})
    blocked = sum(x["assessment"] == "BLOCKED" for x in results)
    verified = sum(x["assessment"] == "VERIFIED_LOCAL_HASH" for x in results)
    incomplete = len(results) - verified - blocked
    outcome = ("BLOCKED" if blocked else
               "INCOMPLETE" if incomplete or not results else "LOCAL_HASH_PASS")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "observedAtUtc": datetime.now(timezone.utc).isoformat(),
        "kitName": saved["name"],
        "outcome": outcome,
        "selectedPlugins": len(results),
        "locallyHashMatched": verified,
        "blocked": blocked,
        "unverifiedOrUninstalled": incomplete,
        "plugins": results,
        "notice": NOTICE,
    }


def report_lines(report):
    lines = [
        "KIT: " + report["kitName"],
        "OBSERVED UTC: " + report["observedAtUtc"],
    ]
    for record in report["plugins"]:
        lines.append("PLUGIN: " + record["id"] + " / " +
                     record["sourceState"] + " / " + record["assessment"])
    lines.extend([
        "LOCAL HASH MATCHED: " + str(report["locallyHashMatched"]) +
        "/" + str(report["selectedPlugins"]),
        "BLOCKED: " + str(report["blocked"]),
        "UNKNOWN_OR_NOT_INSTALLED: " + str(report["unverifiedOrUninstalled"]),
        "RESULT: " + report["outcome"],
        NOTICE,
        "NO INSTALL / NO DOWNLOAD / NO CHANGES TO MANAGED TOOLS",
    ])
    return lines


def emit(report, output=None):
    """Either print only or create new-only JSON and identical console log."""
    lines = report_lines(report)
    if output is None:
        for line in lines:
            print(line)
        return
    target = Path(output).absolute()
    log = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(log)
    if target == log or os.path.lexists(target) or os.path.lexists(log):
        raise HealthError("Report/log already exists; refusing overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(log) as transcript:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        for line in lines:
            transcript.emit(line)
        transcript.emit("REPORT: " + str(target))


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--kit", required=True, help="validated personal JSON v2")
    parser.add_argument("--root", default="portable", help="existing managed root")
    parser.add_argument("--out", help="new local JSON + mirrored .log (optional)")
    args = parser.parse_args(argv)
    try:
        pins, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, pins, known)
        report = inspect(saved, pins, args.root)
        emit(report, args.out)
        # 0=all chosen plugin files match local receipt, 2=unverified/blocked,
        # 1=invalid state, unreadable files or operational error.
        return 0 if report["outcome"] == "LOCAL_HASH_PASS" else 2
    except (HealthError, offline.PluginDeployError, kit.KitError,
            kit.sets.ToolsetError, kit.core.PortakitError,
            OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
