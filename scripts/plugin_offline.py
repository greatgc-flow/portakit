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
import re
import stat
import sys
import uuid

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import offline_assets as source_assets  # noqa: E402

STATE_NAME = ".portakit-plugin-state.json"
MAX_PINNED = 8
MAX_PLUGIN_FILES = 4096
MAX_PLUGIN_LEVELS = 32
MAX_PLUGIN_BYTES = 512 * 1024 * 1024
MAX_RECEIPT_BYTES = 2 * 1024 * 1024
BASE_RECEIPT_FIELDS = frozenset(
    ("hostSha256", "sha256", "version", "dest", "requiredFile"))


class PluginDeployError(Exception):
    pass


def receipt_path(root):
    return Path(root) / STATE_NAME


def validate_hashes(hashes):
    """Do not trust persisted file paths or digests read from local receipts."""
    if not isinstance(hashes, dict) or not hashes or len(hashes) > MAX_PLUGIN_FILES:
        raise PluginDeployError("Invalid plugin file hash inventory")
    seen = set()
    for name, digest in hashes.items():
        try:
            segments = kit.core.path_parts(name, "receipt relative file", "state")
        except kit.core.PortakitError as exc:
            raise PluginDeployError("Invalid plugin receipt file path") from exc
        if ("/".join(segments) != name or
                name.casefold() in seen or
                not isinstance(digest, str) or
                re.fullmatch(r"[a-f0-9]{64}", digest) is None):
            raise PluginDeployError("Unsafe/duplicate plugin file digest")
        seen.add(name.casefold())


def unique_receipt_pairs(pairs):
    """Reject duplicate JSON object keys at every nesting depth.

    json.loads otherwise keeps the last value, allowing a locally edited
    receipt to hide a conflicting SHA, version or file-hash assertion.
    """
    result = {}
    for name, value in pairs:
        if name in result:
            raise PluginDeployError("Duplicate plugin receipt JSON key: " + name)
        result[name] = value
    return result


def reject_receipt_constant(value):
    """A receipt must be strict JSON, not Python's NaN/Infinity extensions."""
    raise PluginDeployError("Invalid non-finite plugin receipt value: " + value)


def read_receipts(root):
    path = receipt_path(root)
    kit.core.check_links(path)
    if not path.exists():
        return {}
    try:
        if path.stat().st_size > MAX_RECEIPT_BYTES:
            raise PluginDeployError("Plugin receipt state too large")
        value = json.loads(path.read_text(encoding="utf-8"),
                           object_pairs_hook=unique_receipt_pairs,
                           parse_constant=reject_receipt_constant)
    except (OSError, ValueError, UnicodeError) as exc:
        raise PluginDeployError("Cannot read plugin receipt state: " + str(exc)) from exc
    if not isinstance(value, dict):
        raise PluginDeployError("Plugin receipts must be a JSON object")
    for ident, record in value.items():
        # Exact two-part normalized ID; never accept control/path tokens or
        # hidden/unbounded selectors in a persisted receipt key.
        if (not isinstance(ident, str) or
                re.fullmatch(r"[a-z0-9][a-z0-9._+-]*:[a-z0-9][a-z0-9._+-]*",
                             ident) is None or
                not isinstance(record, dict) or
                set(record) not in (BASE_RECEIPT_FIELDS,
                                   BASE_RECEIPT_FIELDS | {"fileHashes"}) or
                any(not isinstance(record.get(k), str)
                    for k in BASE_RECEIPT_FIELDS)):
            raise PluginDeployError("Invalid saved plugin receipt: " + str(ident))
        # Historical receipts are accepted for diagnosis, but NOT trusted
        # as proof of currently installed DLL integrity.
        if "fileHashes" in record:
            validate_hashes(record["fileHashes"])
    return value


def installed_file_hashes(directory):
    """Hash *all* deployed files with bounded, no-reparse, read-only traversal.

    This is a best-effort snapshot. A privileged concurrent process can still
    alter files after verification; do not describe it as a signature or EDR gate.
    """
    root = Path(directory)
    kit.core.check_links(root)
    if not root.is_dir():
        raise PluginDeployError("Plugin folder does not exist")
    stack = [(root, "", 0)]
    found = {}
    names_lower = set()
    total = 0
    entries = 0
    while stack:
        current, prefix, depth = stack.pop()
        if depth > MAX_PLUGIN_LEVELS:
            raise PluginDeployError("Installed plugin depth limit exceeded")
        kit.core.check_links(current)
        with os.scandir(current) as directory_entries:
            for entry in directory_entries:
                entries += 1
                if entries > MAX_PLUGIN_FILES:
                    raise PluginDeployError("Installed plugin member count exceeded")
                path = Path(entry.path)
                kit.core.check_links(path)
                info = entry.stat(follow_symlinks=False)
                name = prefix + entry.name
                if stat.S_ISDIR(info.st_mode):
                    stack.append((path, name + "/", depth + 1))
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise PluginDeployError("Installed plugin contains special file")
                if name.casefold() in names_lower:
                    raise PluginDeployError("Installed plugin duplicate file case")
                if info.st_size > MAX_PLUGIN_BYTES - total:
                    raise PluginDeployError("Installed plugin logical size limit exceeded")
                digest = hashlib.sha256()
                counted = 0
                with path.open("rb") as stream:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        counted += len(chunk)
                        if counted > info.st_size or counted > MAX_PLUGIN_BYTES - total:
                            raise PluginDeployError("Installed plugin size changed during scan")
                        digest.update(chunk)
                if counted != info.st_size:
                    raise PluginDeployError("Installed plugin size changed during scan")
                total += counted
                found[name] = digest.hexdigest()
                names_lower.add(name.casefold())
    if not found:
        raise PluginDeployError("Installed plugin directory has no files")
    validate_hashes(found)
    return found


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


def receipt_record(host, pin, file_hashes=None):
    info = {"hostSha256": host["sha256"], "sha256": pin["sha256"],
            "version": pin["version"], "dest": pin["dest"],
            "requiredFile": pin["requiredFile"]}
    if file_hashes is not None:
        validate_hashes(file_hashes)
        info["fileHashes"] = file_hashes
    return info


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
        elif record is not None and {
                key: record.get(key) for key in BASE_RECEIPT_FIELDS
                } != receipt_record(host, pin):
            status = "blocked-plugin-pin"
        elif os.path.lexists(dest):
            if record is None:
                status = "blocked-unmanaged"
            elif not dest.is_dir() or not needed.is_file():
                status = "blocked-missing"
            elif "fileHashes" not in record:
                status = "blocked-legacy-unverified"
            elif installed_file_hashes(dest) != record["fileHashes"]:
                status = "blocked-content-drift"
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
    # Original vendor archives are needed only for plugins not yet installed.
    # Reused managed plugins have already been checked in make_plan against
    # their per-file SHA receipts; do not require re-acquisition of ZIP files.
    status_by_id = {row["id"]: row["status"] for row in items}
    to_install = [(item, host, pin) for item, host, pin in selected
                  if status_by_id[item["id"]] == "install"]
    if not selected:
        evidence.emit("NO_OP: no SHA-pinned plugins selected")
        return
    if to_install and archive_dir is None:
        raise PluginDeployError(
            "Missing plugins require --offline-dir with original vendor archives")
    archives = verify_all(to_install, archive_dir) if to_install else {}
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
            receipt_committed = False
            try:
                verified_local_snapshot(archives[item["id"]], local_archive,
                                        pin["sha256"])
                kit.core.extract(local_archive,
                                 {"id": item["id"], "artifact": "zip"}, staging)
                dll = kit.core.safe_path(staging, pin["requiredFile"],
                                         "required plugin DLL", "archive")
                if not dll.is_file():
                    raise PluginDeployError("Required plugin DLL missing: " + item["id"])
                deployed_hashes = installed_file_hashes(staging)
                kit.core.check_links(destination)
                if os.path.lexists(destination):
                    raise PluginDeployError("Plugin destination exists, refusing overwrite")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.rename(staging, destination)
                moved = True
                receipt = receipt_record(host, pin, deployed_hashes)
                write_receipts(root, dict(receipts, **{key: receipt}))
                # Receipt persistence is the commit point for this plugin.
                # A later evidence I/O failure must not strand a receipt by
                # deleting its corresponding managed directory.
                receipt_committed = True
                receipts[key] = receipt
                evidence.emit("INSTALLED: " + item["id"] + " version=" + pin["version"] +
                              " SHA256=" + pin["sha256"] + " (host restart may be needed)")
            except BaseException:
                # Roll back only uncommitted installs. After receipt commit,
                # incomplete evidence is an error, but managed state remains
                # consistent and can be verified again without vendor files.
                if moved and not receipt_committed:
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
            p.add_argument("--offline-dir", required=(command == "verify"),
                           help=("Original vendor ZIP directory: mandatory for "
                                 "verify and for apply when plugins are missing"))
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
        # Never let evidence creation alter a managed editor/plugin directory.
        # Reuse the core installer's pre-write guard: inside the install root,
        # only the dedicated .portakit-evidence folder is safe.
        kit.core.check_evidence_location(path, args.root, "install")
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
