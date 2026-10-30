"""Explicit, offline-only installation of SHA-pinned editor plugins.

This is NOT a license grant or vendor-binary distributor. The operator must
separately approve company use, transfer, EDR and original vendor archives.
Never downloads or executes vendor DLLs. Research-only choices are inert.
Host must already be a matching managed PortaKit installation. Existing
unmanaged plugin folders are NEVER overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import offline_assets as source_assets  # noqa: E402

STATE_NAME = ".portakit-plugin-state.json"
MAX_PINNED = 8


class PluginDeployError(Exception):
    pass


def receipt_path(root):
    return Path(root) / STATE_NAME


def read_receipts(root):
    path = receipt_path(root)
    kit.core.check_links(path)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise PluginDeployError("Cannot read plugin receipt state: " + str(exc)) from exc
    if not isinstance(value, dict):
        raise PluginDeployError("Plugin receipts must be a JSON object")
    for ident, record in value.items():
        if (not isinstance(ident, str) or ":" not in ident
                or not isinstance(record, dict)
                or set(record) != {"hostSha256", "sha256", "version", "dest", "requiredFile"}
                or any(not isinstance(v, str) for v in record.values())):
            raise PluginDeployError("Invalid saved plugin receipt: " + str(ident))
    return value


def write_receipts(root, receipts):
    root = Path(root)
    target = receipt_path(root)
    temp = root / (STATE_NAME + "." + uuid.uuid4().hex + ".tmp")
    kit.core.check_links(target)
    kit.core.check_links(temp)
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(receipts, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
        kit.core.check_links(target)
        os.replace(temp, target)
    finally:
        if os.path.lexists(temp):
            temp.unlink()


def vendor_pin(plugin, host):
    """Resolve nested immutable catalog pin, not user-supplied file metadata."""
    internal = kit.PLUGIN_PIN_ALIASES.get(plugin["id"], plugin["id"])
    for rec in host.get("recommended", {}).get("plugins", []):
        if rec["id"] == internal:
            return rec
    raise PluginDeployError("No approved SHA-pinned vendor metadata for " + plugin["id"])


def receipt_record(host, pin):
    return {"hostSha256": host["sha256"], "sha256": pin["sha256"],
            "version": pin["version"], "dest": pin["dest"],
            "requiredFile": pin["requiredFile"]}


def select_plugins(saved, pins):
    if saved.get("schemaVersion") != 2:
        raise PluginDeployError("Individual plugin install requires saved v2 kit")
    chosen, pending = [], []
    for item in saved["pluginSelections"]:
        if item["status"] != "PINNED_METADATA_ONLY":
            pending.append(item["id"])
            continue
        host = pins[item["host"]]
        pin = vendor_pin(item, host)
        if item["lockedPin"] != {key: pin[key]
                                for key in ("version", "sha256", "dest")}:
            raise PluginDeployError("Plugin pin changed: " + item["id"])
        chosen.append((item, host, pin))
    if len(chosen) > MAX_PINNED:
        raise PluginDeployError("Too many pinned plugins")
    return chosen, pending


def make_plan(saved, pins, root):
    """Pure read-only plan. Rejects unmanaged and stale plugin installations."""
    root = Path(os.path.abspath(str(root)))
    kit.core.check_links(root)
    managed = kit.core.read_state(root)
    receipts = read_receipts(root)
    selected, pending = select_plugins(saved, pins)
    result = []
    for selection, host, pin in selected:
        host_status = kit.sets.status_of(
            dict(host, id=selection["host"]), root, managed)
        dest = kit.core.safe_path(root, host["dest"] + "/" + pin["dest"],
                                  "editor plugin destination", "state")
        needed = kit.core.safe_path(dest, pin["requiredFile"],
                                    "editor plugin DLL", "state")
        key = selection["host"] + ":" + selection["id"]
        record = receipts.get(key)
        status = "install"
        if host_status != "already-installed":
            status = "blocked-host-" + host_status
        elif record is not None and record != receipt_record(host, pin):
            status = "blocked-plugin-pin"
        elif os.path.lexists(dest):
            if record is None:
                status = "blocked-unmanaged"
            elif not dest.is_dir() or not needed.is_file():
                status = "blocked-missing"
            else:
                status = "already-installed"
        elif record is not None:
            status = "blocked-missing"
        result.append({"id": selection["id"], "host": selection["host"],
                       "status": status, "destination": str(dest),
                       "filename": source_assets.original_filename(pin["url"]),
                       "version": pin["version"], "sha256": pin["sha256"]})
    return result, pending


def verify_vendor_archive(path, sha256):
    kit.core.check_links(path)
    if not path.is_file():
        raise PluginDeployError("Missing original vendor archive: " + str(path))
    if path.stat().st_size > kit.core.MAX_DOWNLOAD_BYTES:
        raise PluginDeployError("Vendor archive size exceeds allowed bound")
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != sha256.lower():
        raise PluginDeployError("Vendor SHA-256 mismatch: " + str(path))


def verify_all(selected, archive_dir):
    """Preflight every selected pinned original before any plugin is staged."""
    folder = Path(os.path.abspath(str(archive_dir)))
    kit.core.check_links(folder)
    if not folder.is_dir():
        raise PluginDeployError("Offline vendor archive directory not found")
    assets = {}
    for item, host, pin in selected:
        name = source_assets.original_filename(pin["url"])
        original = folder / name
        verify_vendor_archive(original, pin["sha256"])
        assets[item["id"]] = original
    return assets


def verified_local_snapshot(original, target, expected_sha):
    """Copy locally and hash the exact bytes that will be extracted.

    Guards against a swapped or mutated source after the preflight hash.
    Source bytes are never uploaded or executed.
    """
    kit.core.check_links(original)
    kit.core.check_links(target)
    digest = hashlib.sha256()
    amount = 0
    with original.open("rb") as stream, target.open("xb") as out:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            amount += len(block)
            if amount > kit.core.MAX_DOWNLOAD_BYTES:
                raise PluginDeployError("Original plugin archive exceeds safe bound")
            out.write(block)
            digest.update(block)
    if digest.hexdigest() != expected_sha.lower():
        raise PluginDeployError("Source changed after preflight: " + str(original))


def apply(saved, pins, root, archive_dir, *, skip_pending=False, evidence):
    """Install only approved-pinned subset. Per-plugin rollback, not batch atomic."""
    selected, pending = select_plugins(saved, pins)
    if pending and not skip_pending:
        raise PluginDeployError("Research-only plugin selections: " + ", ".join(pending) +
                                " (use --skip-pending to install approved pinned subset)")
    root = Path(os.path.abspath(str(root)))
    items, _ = make_plan(saved, pins, root)
    blocked = [row["id"] + "=" + row["status"] for row in items
               if row["status"].startswith("blocked-")]
    if blocked:
        raise PluginDeployError("Host/plugin state blocked: " + ", ".join(blocked))
    archives = verify_all(selected, archive_dir)
    if not selected:
        evidence.emit("NO_OP: no SHA-pinned plugins selected")
        return
    # Both locks avoid interleaving with either category apply or core direct installs.
    with kit.sets.BatchLock(root), kit.core.RootLock(root):
        refreshed, _ = make_plan(saved, pins, root)
        if [(r["id"], r["status"]) for r in items] != [
                (r["id"], r["status"]) for r in refreshed]:
            raise PluginDeployError("Plugin/host state changed during preflight")
        receipts = read_receipts(root)
        for item, host, pin in selected:
            row = next(x for x in refreshed if x["id"] == item["id"])
            if row["status"] == "already-installed":
                evidence.emit("SKIP: " + item["id"] + " already managed")
                continue
            nonce = uuid.uuid4().hex
            staging = root / (".portakit-plugin-stage-" + nonce)
            local_archive = root / (".portakit-plugin-archive-" + nonce + ".tmp")
            kit.core.check_links(staging)
            kit.core.check_links(local_archive)
            destination = kit.core.safe_path(root, host["dest"] + "/" + pin["dest"],
                                             "plugin dest", "state")
            key = item["host"] + ":" + item["id"]
            moved = False
            try:
                verified_local_snapshot(archives[item["id"]], local_archive,
                                        pin["sha256"])
                kit.core.extract(local_archive,
                                 {"id": item["id"], "artifact": "zip"}, staging)
                dll = kit.core.safe_path(staging, pin["requiredFile"],
                                         "required plugin DLL", "archive")
                if not dll.is_file():
                    raise PluginDeployError("Required plugin DLL missing: " + item["id"])
                kit.core.check_links(destination)
                if os.path.lexists(destination):
                    raise PluginDeployError("Plugin destination exists, refusing overwrite")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.rename(staging, destination)
                moved = True
                write_receipts(root, dict(receipts, **{
                    key: receipt_record(host, pin)}))
                receipts[key] = receipt_record(host, pin)
                evidence.emit("INSTALLED: " + item["id"] + " version=" + pin["version"] +
                              " SHA256=" + pin["sha256"] + " (host restart may be needed)")
            except BaseException:
                if moved:
                    kit.core.remove_tree(destination)
                raise
            finally:
                for temporary in (staging, local_archive):
                    if os.path.lexists(temporary):
                        kit.core.remove_tree(temporary)


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "verify", "apply"):
        p = sub.add_parser(command)
        p.add_argument("--kit", required=True)
        p.add_argument("--root", default="portable")
        if command in ("verify", "apply"):
            p.add_argument("--offline-dir", required=True)
        if command == "apply":
            p.add_argument("--yes", action="store_true")
            p.add_argument("--policy-approved", action="store_true",
                           help="operator confirms enterprise license/EDR/source-transfer approval")
            p.add_argument("--skip-pending", action="store_true",
                           help="exclude research-only plugins explicitly")
            p.add_argument("--log-file", help="new-only console-mirrored local evidence")
    args = parser.parse_args(argv)
    try:
        pins, _, _, known = kit.inventory()
        saved = kit.read_kit(args.kit, pins, known)
        selected, pending = select_plugins(saved, pins)
        if args.command == "plan":
            rows, pending = make_plan(saved, pins, args.root)
            for row in rows:
                print("PLUGIN: " + row["id"] + " / " + row["status"] +
                      " / " + row["filename"])
            for ident in pending:
                print("PLUGIN: " + ident + " / RESEARCH_ONLY / NOT INSTALLABLE")
            print("NO DOWNLOAD / NO CHANGES")
            return 0
        if args.command == "verify":
            found = verify_all(selected, args.offline_dir)
            for ident in found:
                print("SHA256 PASS: " + ident)
            for ident in pending:
                print("RESEARCH_ONLY: " + ident + " / SKIPPED")
            print("NO INSTALL / NO CHANGES")
            return 0
        if not args.yes or not args.policy_approved:
            raise PluginDeployError("apply requires --yes AND --policy-approved")
        path = (args.log_file or str(Path(args.root) / ".portakit-evidence" /
                ("editor-plugins-" + uuid.uuid4().hex + ".log")))
        with kit.sets.Evidence(path) as log:
            log.emit("OPERATION: offline pinned editor plugins")
            log.emit("POLICY APPROVAL: operator attested (not independently verified)")
            log.emit("SOURCE: original local vendor archives with SHA-256 preflight")
            try:
                apply(saved, pins, args.root, args.offline_dir,
                      skip_pending=args.skip_pending, evidence=log)
                log.emit("RESULT: COMPLETE")
                return 0
            except (PluginDeployError, kit.core.PortakitError,
                    kit.sets.ToolsetError, OSError, ValueError) as exc:
                log.emit("RESULT: FAILED / " + str(exc))
                log.emit("NOTE: prior successfully-installed plugins are not batch-rolled-back")
                return 1
    except (PluginDeployError, kit.KitError, kit.core.PortakitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
