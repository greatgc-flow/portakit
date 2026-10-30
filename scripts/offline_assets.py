"""Offline source-asset handoff for one user-defined PortaKit.

This utility only exports legal-review metadata and verifies user-provided
vendor-original SHA-256 bytes. It NEVER downloads, bundles, redistributes,
executes vendor programs or installs tools/services/drivers.
"""
import argparse
from datetime import datetime
from pathlib import Path
import json
import os
import sys
from urllib.parse import unquote, urlsplit
import uuid

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402

SCHEMA_VERSION = 1
DISCLAIMER = ("SOURCE METADATA ONLY: no vendor redistribution, download, "
              "install, network probe, EULA or corporate approval is implied.")


class AssetError(Exception):
    pass


def original_filename(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        raise AssetError("Official vendor URL must be HTTPS")
    path = urlsplit(url).path
    name = unquote(path.rsplit("/", 1)[-1])
    if (not name or name in (".", "..") or "/" in name or "\\" in name
            or name.endswith((".", " ")) or any(ord(x) < 32 for x in name)):
        raise AssetError("Unsafe vendor archive basename: " + repr(name))
    return name


def make_manifest(saved, catalog):
    """Compute metadata only; source read under exact personal kit pin locks."""
    rows = []
    by_filename = {}
    for ident in saved["tools"]:
        if ident not in saved["lockedPins"]:
            continue
        pin = catalog[ident]
        name = original_filename(pin["url"])
        if name.casefold() in by_filename:
            existing = by_filename[name.casefold()]
            if existing != pin["sha256"]:
                raise AssetError("Vendor filename collision with different SHA: " + name)
        by_filename[name.casefold()] = pin["sha256"]
        rows.append({"id": ident, "version": pin["version"], "artifact": pin["artifact"],
                     "originalFilename": name, "url": pin["url"],
                     "sha256": pin["sha256"]})
    return {
        "schemaVersion": SCHEMA_VERSION, "kitName": saved["name"],
        "policy": "METADATA_ONLY_NOT_LICENSED_FOR_REDISTRIBUTION",
        "notice": DISCLAIMER,
        "approvedCatalogPins": len(rows),
        "osBuiltinsNotPackaged": list(saved["osBuiltins"]),
        "researchOnlyNotPackaged": list(saved["researchOnly"]),
        "editorPluginsNotPackaged": [
            x["id"] for x in saved.get("pluginSelections", [])],
        "assets": rows,
    }


def create_manifest_file(data, path, log=None):
    target = Path(path).absolute()
    evidence_path = Path(log).absolute() if log else target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(evidence_path)
    if (target == evidence_path or os.path.lexists(target)
            or os.path.lexists(evidence_path)):
        raise AssetError("Output manifest/log exists; refuse overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(evidence_path) as ev:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        ev.emit("MANIFEST: " + str(target))
        ev.emit("KIT: " + data["kitName"])
        ev.emit("PINNED ASSETS: " + str(len(data["assets"])))
        ev.emit("NOT INCLUDED RESEARCH: " + str(len(data["researchOnlyNotPackaged"])))
        ev.emit("NOT INCLUDED OS: " + str(len(data["osBuiltinsNotPackaged"])))
        ev.emit(DISCLAIMER)


def show_assets(data):
    print("KIT: " + data["kitName"])
    for x in data["assets"]:
        print("ASSET: " + x["id"] + "\t" + x["originalFilename"] +
              "\tSHA256=" + x["sha256"])
        print("  OFFICIAL URL (manual acquisition only): " + x["url"])
    print("NOT INCLUDED RESEARCH: " + str(len(data["researchOnlyNotPackaged"])))
    print("NOT INCLUDED OS: " + str(len(data["osBuiltinsNotPackaged"])))
    print(DISCLAIMER)
    print("NO DOWNLOAD / NO CHANGES")


def verify_archives(data, archive_dir, evidence_path):
    """Verify every distinct pinned original file before user builds kit.

    Delegate actual file validation to the existing offline preflight engine.
    A failure never starts or partially installs any tool.
    """
    entries = [{"id": row["id"], "status": "install"} for row in data["assets"]]
    with kit.sets.Evidence(evidence_path) as ev:
        ev.emit("OPERATION: verify personal kit offline source assets")
        ev.emit("KIT: " + data["kitName"])
        ev.emit("ARCHIVE DIRECTORY: " + str(Path(archive_dir).absolute()))
        try:
            if entries:
                verified = kit.sets.verify_offline_assets(entries, archive_dir)
                for row in data["assets"]:
                    ev.emit("SHA256 PASS: " + row["id"] + " / " +
                            row["originalFilename"] + " / " + row["sha256"])
                if len(verified) != len(entries):
                    raise AssetError("Offline preflight incomplete")
            else:
                ev.emit("NO_OP: no approved pinned assets selected")
            ev.emit("RESULT: VERIFIED (files were NOT executed or installed)")
            ev.emit(DISCLAIMER)
            return True
        except (AssetError, kit.sets.ToolsetError, kit.core.PortakitError,
                OSError, ValueError) as exc:
            ev.emit("RESULT: FAILED / " + str(exc))
            ev.emit("NO INSTALL / NO DOWNLOAD / NO PARTIAL DEPLOYMENT")
            return False



def make_readiness(saved, catalog, root, archive_dir=None, skip_pending=False):
    """Read-only cross-check of kit pins, managed-state and ONLY missing archives.

    Source facts are delegated to the personal kit planner and the original
    offline SHA preflight. This routine does not create directories, install
    software, run downloads or change the saved user selection.
    """
    plan = kit.create_plan(saved, root)
    metadata = make_manifest(saved, catalog)
    by_id = {item["id"]: item for item in metadata["assets"]}
    missing = [row for row in plan["tools"] if row["status"] == "install"]
    blocked = [row["id"] + "=" + row["status"] for row in plan["tools"]
               if row["status"].startswith("blocked-")]
    # 7-Zip full archive requires a user-chosen verified 7zr prerequisite.
    try:
        kit.check_prerequisite(saved, plan)
    except kit.KitError as exc:
        blocked.append("PREREQUISITE: " + str(exc))
    pending = list(saved["researchOnly"])
    plugins = [item["id"] for item in saved.get("pluginSelections", [])]
    pending_blocked = bool((pending or saved["schemaVersion"] == 2)
                           and not skip_pending)

    required = [by_id[row["id"]] for row in missing]
    error = None
    verified = False
    if archive_dir is not None and missing and not blocked:
        try:
            result = kit.sets.verify_offline_assets(missing, archive_dir)
            if set(result) != {row["id"] for row in missing}:
                raise AssetError("Incomplete offline source preflight")
            verified = True
        except (kit.sets.ToolsetError, kit.core.PortakitError,
                AssetError, OSError, ValueError) as exc:
            error = str(exc)

    if blocked:
        outcome = "BLOCKED_STATE"
    elif pending_blocked:
        outcome = "BLOCKED_PENDING"
    elif error is not None:
        outcome = "BLOCKED_ARCHIVES"
    elif missing and archive_dir is None:
        outcome = "NEEDS_ARCHIVES"
    elif not plan["tools"]:
        outcome = "NO_OP"
    else:
        outcome = "READY"

    return {
        "schemaVersion": 1,
        "kitName": saved["name"],
        "root": plan["root"],
        "archiveDirectory": (str(Path(archive_dir).absolute())
                             if archive_dir is not None else None),
        "status": outcome,
        "skipPending": bool(skip_pending),
        "selectedApproved": len(plan["tools"]),
        "alreadyInstalled": sum(row["status"] == "already-installed"
                                for row in plan["tools"]),
        "missingApproved": len(missing),
        "offlineArchivesVerified": verified,
        "blockedState": blocked,
        "archiveError": error,
        "installPlan": [{"id": row["id"], "status": row["status"]}
                        for row in plan["tools"]],
        "requiredAssets": required,
        "researchOnlyExcluded": pending,
        "editorPluginsExcluded": plugins,
        "osBuiltinsInformational": list(saved["osBuiltins"]),
        "policy": "METADATA_ONLY_NOT_LICENSED_FOR_REDISTRIBUTION",
        "notice": DISCLAIMER,
    }


def readiness_lines(report):
    """Stable, human-readable text suitable for byte-identical local evidence."""
    lines = ["KIT: " + report["kitName"],
             "ROOT: " + report["root"],
             "INSTALL PLAN:"]
    for item in report["installPlan"]:
        lines.append("  " + item["id"] + " / " + item["status"])
    for item in report["requiredAssets"]:
        lines.append("REQUIRED ORIGINAL: " + item["id"] + " / " +
                     item["originalFilename"] + " / SHA256=" + item["sha256"])
        lines.append("  OFFICIAL URL (manual acquisition only): " + item["url"])
    lines.append("SELECTED APPROVED: " + str(report["selectedApproved"]) +
                 " / ALREADY INSTALLED: " + str(report["alreadyInstalled"]) +
                 " / ARCHIVES NEEDED: " + str(report["missingApproved"]))
    lines.append("RESEARCH EXCLUDED: " + str(len(report["researchOnlyExcluded"])) +
                 " / PLUGINS EXCLUDED: " + str(len(report["editorPluginsExcluded"])) +
                 " / OS ONLY: " + str(len(report["osBuiltinsInformational"])))
    lines.append("SKIP PENDING: " + ("YES" if report["skipPending"] else "NO"))
    if report["archiveDirectory"] is not None:
        lines.append("ARCHIVE DIRECTORY: " + report["archiveDirectory"])
        lines.append("REQUIRED ARCHIVES SHA: " +
                     ("PASS" if report["offlineArchivesVerified"] else
                      "NOT_VERIFIED" if report["missingApproved"] == 0 else "FAIL"))
    for reason in report["blockedState"]:
        lines.append("BLOCKED: " + reason)
    if report["archiveError"] is not None:
        lines.append("SOURCE ERROR: " + report["archiveError"])
    lines.extend(["RESULT: " + report["status"],
                  "NO INSTALL / NO DOWNLOAD / NO CHANGES TO MANAGED TOOLS",
                  DISCLAIMER,
                  "NEXT: review licenses/EDR/transfer authorization; then use "
                  "scripts\\MyToolkit.cmd build --kit ... "
                  "--offline-dir ... --yes (and --skip-pending if selected)"])
    return lines


def output_readiness(report, output=None):
    """No output path = read-only console; --out = new JSON + exact console log."""
    lines = readiness_lines(report)
    if output is None:
        for line in lines:
            print(line)
        return
    target = Path(output).absolute()
    evidence_path = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(evidence_path)
    if (target == evidence_path or os.path.lexists(target)
            or os.path.lexists(evidence_path)):
        raise AssetError("Readiness JSON/log already exists; refuse overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(evidence_path) as ev:
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

def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "export", "verify", "check"):
        p = subs.add_parser(command)
        p.add_argument("--kit", required=True, help="existing validated personal JSON kit")
        if command == "export":
            p.add_argument("--out", required=True, help="new metadata-only .json file")
            p.add_argument("--log-file", help="new exact local evidence log")
        if command == "verify":
            p.add_argument("--archive-dir", required=True,
                           help="user-acquired original official vendor filenames")
            p.add_argument("--log-file", help="new evidence log (default under cwd)")
        if command == "check":
            p.add_argument("--root", default="portable",
                           help="existing managed install destination")
            p.add_argument("--archive-dir",
                           help="optional local originals; verify only missing pins")
            p.add_argument("--skip-pending", action="store_true",
                           help="explicitly accept only approved subset; never plugins")
            p.add_argument("--out", help="optional new JSON + byte-mirrored .log")
    args = parser.parse_args(argv)
    try:
        catalog, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, catalog, known)
        if args.command == "check":
            report = make_readiness(saved, catalog, args.root,
                                    archive_dir=args.archive_dir,
                                    skip_pending=args.skip_pending)
            output_readiness(report, args.out)
            return 0 if report["status"] in ("READY", "NO_OP") else 2
        data = make_manifest(saved, catalog)
        if args.command == "list":
            show_assets(data)
            return 0
        if args.command == "export":
            create_manifest_file(data, args.out, args.log_file)
            return 0
        evidence = (args.log_file or str(Path.cwd() / ".portakit-evidence" /
                     ("assets-" + datetime.now().strftime("%Y%m%d-%H%M%S") +
                      "-" + uuid.uuid4().hex[:8] + ".log")))
        return 0 if verify_archives(data, args.archive_dir, evidence) else 1
    except (AssetError, kit.KitError, kit.sets.ToolsetError,
            kit.core.PortakitError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
