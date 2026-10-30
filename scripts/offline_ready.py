"""Read-only one-command personal-kit offline readiness and source checklist.

Uses existing pinned plan, exact SHA verifier and source manifest; does not
install, download, package, redistribute, or execute any vendor program.
Default invocation has *zero filesystem writes*. --out creates only a new JSON
report and a verbatim console transcript .log on the user's local machine.
Windows / Python 3.11+ stdlib, no administrative privileges required.
"""
import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import offline_assets as assets  # noqa: E402

SCHEMA_VERSION = 1
NOTICE = ("READ-ONLY OFFLINE CHECK: local hashes are not vendor signatures, "
          "corporate-use approval, transfer rights, EDR clearance, or installation.")


class ReadinessError(Exception):
    pass


def assess(saved, pins, root, archive_dir=None, skip_pending=False):
    """No writes, network, downloads, or tool execution.

    The source paths and install-status decisions are taken only from the
    current SHA-pinned catalog and validated personal kit, not from filenames
    or URLs supplied in arbitrary user JSON.
    """
    if not isinstance(skip_pending, bool):
        raise ReadinessError("skip_pending must be boolean")
    manifest = assets.make_manifest(saved, pins)
    plan = kit.create_plan(saved, root)
    blockers = []
    try:
        kit.check_prerequisite(saved, plan)
    except kit.KitError as exc:
        blockers.append("PREREQUISITE: " + str(exc))
    excluded = list(saved["researchOnly"])
    plugins = [row["id"] for row in saved.get("pluginSelections", [])]
    if excluded and not skip_pending:
        blockers.append("RESEARCH_ONLY selected: add --skip-pending for approved subset")
    if plugins and not skip_pending:
        blockers.append("EDITOR_PLUGINS selected: add --skip-pending for host-only subset")

    folder = None
    directory_exists = False
    # Already-installed tools never require original archives. Do not mark a
    # missing optional archive directory as a blocker when no source is needed.
    needs_originals = any(row["status"] == "install" for row in plan["tools"])
    if archive_dir is not None:
        folder = Path(os.path.abspath(str(archive_dir)))
        if needs_originals:
            kit.core.check_links(folder)
            directory_exists = folder.is_dir()
            if not directory_exists:
                blockers.append("SOURCE_DIRECTORY_MISSING: " + str(folder))
    by_id = {row["id"]: row for row in manifest["assets"]}
    result_rows = []
    for operation in plan["tools"]:
        ident, status = operation["id"], operation["status"]
        source = by_id[ident]
        item = {
            "id": ident,
            "version": source["version"],
            "installStatus": status,
            "originalFilename": source["originalFilename"],
            "url": source["url"],
            "sha256": source["sha256"],
            "sourceStatus": "NOT_REQUIRED",
        }
        if status.startswith("blocked-"):
            blockers.append("INSTALL_BLOCKED: " + ident + " / " + status)
        elif status == "install":
            if folder is None:
                item["sourceStatus"] = "NOT_PROVIDED"
                blockers.append("SOURCE_NOT_PROVIDED: " + ident)
            elif not directory_exists:
                item["sourceStatus"] = "MISSING_DIRECTORY"
            else:
                original = folder / source["originalFilename"]
                # Reject symlinks/reparse points before following filesystem data.
                kit.core.check_links(original)
                if not original.is_file():
                    item["sourceStatus"] = "MISSING"
                    blockers.append("SOURCE_MISSING: " + ident + " / " +
                                    source["originalFilename"])
                else:
                    try:
                        valid = kit.sets.verify_offline_assets([operation], folder)
                        if ident not in valid:
                            raise ReadinessError("Incomplete source verification")
                        item["sourceStatus"] = "SHA256_PASS"
                    except (ReadinessError, kit.sets.ToolsetError,
                            kit.core.PortakitError, OSError, ValueError) as exc:
                        item["sourceStatus"] = "BLOCKED_SOURCE"
                        blockers.append("SOURCE_BLOCKED: " + ident + " / " +
                                        str(exc))
        elif status != "already-installed":
            raise ReadinessError("Unexpected install plan status: " + str(status))
        result_rows.append(item)

    new_count = sum(row["installStatus"] == "install" for row in result_rows)
    if blockers:
        outcome = "BLOCKED"
    elif not new_count:
        outcome = "NO_OP"
    elif (excluded or plugins) and skip_pending:
        outcome = "READY_APPROVED_SUBSET"
    else:
        outcome = "READY"
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kitName": saved["name"],
        "root": plan["root"],
        "archiveDirectory": str(folder) if folder is not None else None,
        "skipPendingConsent": skip_pending,
        "outcome": outcome,
        "pinnedTotal": len(result_rows),
        "needInstall": new_count,
        "alreadyInstalled": len(result_rows) - new_count -
                            sum(x["installStatus"].startswith("blocked-")
                                for x in result_rows),
        "researchOnlyExcluded": excluded,
        "osBuiltinsInformational": list(saved["osBuiltins"]),
        "editorPluginsExcluded": plugins,
        "tools": result_rows,
        "blockers": blockers,
        "notice": NOTICE,
    }


def display_lines(report):
    lines = ["KIT: " + report["kitName"],
             "ROOT: " + report["root"],
             "OFFLINE SOURCES: " +
             (report["archiveDirectory"] or "NOT PROVIDED (list missing requirements)")]
    for row in report["tools"]:
        line = ("TOOL: " + row["id"] + " / " + row["installStatus"] +
                " / " + row["sourceStatus"] + " / " + row["originalFilename"])
        lines.append(line)
        if row["installStatus"] == "install":
            lines.append("  SHA256: " + row["sha256"])
            lines.append("  OFFICIAL SOURCE (manual approved acquisition only): " +
                         row["url"])
    lines.append("APPROVED PINNED: " + str(report["pinnedTotal"]) +
                 " / TO INSTALL: " + str(report["needInstall"]) +
                 " / ALREADY INSTALLED: " + str(report["alreadyInstalled"]))
    lines.append("EXCLUDED RESEARCH: " + str(len(report["researchOnlyExcluded"])))
    lines.append("EXCLUDED EDITOR PLUGINS: " + str(len(report["editorPluginsExcluded"])))
    lines.append("OS BUILT-INS INFORMATIONAL: " +
                 str(len(report["osBuiltinsInformational"])))
    for note in report["blockers"]:
        lines.append("BLOCKER: " + note)
    lines.extend(["RESULT: " + report["outcome"], NOTICE,
                  "NO DOWNLOAD / NO INSTALL / NO SYSTEM CHANGES"])
    return lines


def emit(report, out=None):
    lines = display_lines(report)
    if out is None:
        for line in lines:
            print(line)
        return
    target = Path(out).absolute()
    if target.suffix.lower() != ".json":
        raise ReadinessError("--out must end in .json")
    logfile = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(logfile)
    if target == logfile or os.path.lexists(target) or os.path.lexists(logfile):
        raise ReadinessError("Report or matching evidence log exists; refusing overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(logfile) as ev:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        for line in lines:
            ev.emit(line)
        ev.emit("REPORT: " + str(target))


def run(argv=None):
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("--kit", required=True, help="validated v1/v2 personal-kit JSON")
    p.add_argument("--root", default="portable", help="planned managed install root")
    p.add_argument("--archive-dir", help="optional user-provided original vendor files")
    p.add_argument("--skip-pending", action="store_true",
                   help="explicit approved-pins-only consent; excludes all plugins/research")
    p.add_argument("--out", help="optional NEW .json report and exactly mirrored .log")
    args = p.parse_args(argv)
    try:
        pins, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, pins, known)
        report = assess(saved, pins, args.root, args.archive_dir, args.skip_pending)
        emit(report, args.out)
        return 0 if report["outcome"] != "BLOCKED" else 2
    except (ReadinessError, assets.AssetError, kit.KitError,
            kit.sets.ToolsetError, kit.core.PortakitError,
            OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
