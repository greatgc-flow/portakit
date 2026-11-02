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
    # A newly created parent may alter path safety; check both output paths.
    kit.core.check_links(target)
    kit.core.check_links(evidence_path)
    manifest_identity = log_identity = None
    try:
        with kit.sets.Evidence(evidence_path) as ev:
            log_identity = kit.sets.created_output_identity(
                os.fstat(ev.stream.fileno()))
            with target.open("x", encoding="utf-8", newline="\n") as f:
                manifest_identity = kit.sets.created_output_identity(
                    os.fstat(f.fileno()))
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            ev.emit("MANIFEST: " + str(target))
            ev.emit("KIT: " + data["kitName"])
            ev.emit("PINNED ASSETS: " + str(len(data["assets"])))
            ev.emit("NOT INCLUDED RESEARCH: " + str(len(data["researchOnlyNotPackaged"])))
            ev.emit("NOT INCLUDED OS: " + str(len(data["osBuiltinsNotPackaged"])))
            ev.emit(DISCLAIMER)
    except BaseException:
        # Exclusive-create races must NEVER remove an unrelated manifest.
        # A late log/JSON failure discards only outputs owned by this call.
        kit.sets.cleanup_own_output(evidence_path, log_identity)
        kit.sets.cleanup_own_output(target, manifest_identity)
        raise


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


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "export", "verify"):
        p = subs.add_parser(command)
        p.add_argument("--kit", required=True, help="existing validated personal JSON kit")
        if command == "export":
            p.add_argument("--out", required=True, help="new metadata-only .json file")
            p.add_argument("--log-file", help="new exact local evidence log")
        if command == "verify":
            p.add_argument("--archive-dir", required=True,
                           help="user-acquired original official vendor filenames")
            p.add_argument("--log-file", help="new evidence log (default under cwd)")
    args = parser.parse_args(argv)
    try:
        catalog, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, catalog, known)
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
