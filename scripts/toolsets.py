"""Optional, declarative Windows PortaKit toolsets (Python 3.11+ stdlib).

The existing single-tool CLI is untouched. A category/profile is only a named
selection of IDs in the SHA-pinned catalog, never a source of executable code.
'plan' is read-only; 'apply --yes' installs missing pinned tools only (no update,
remove, PATH, registry, profiles, or unreviewed executable downloads).
"""
import argparse
import hashlib
from urllib.parse import urlsplit, unquote
from datetime import datetime
import msvcrt
import os
from pathlib import Path
import re
import stat
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "toolsets.json"
TOOL = REPO / "portakit.py"
ID = re.compile(r"[a-z0-9][a-z0-9._+-]*\Z")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bounded_process as bounded  # noqa: E402 (no vendor execution in helper)
import portakit as core  # noqa: E402  (reuse catalog, state, reparse checks)


class ToolsetError(Exception):
    pass


def _validate_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ToolsetError("Invalid category/profile or tool ID: " + str(value))
    return value


def load_manifest(path, catalog):
    """Strict declarative v1/v2 manifest, with non-breaking v2 legacy aliases.

    Canonical v2 categories are mutually exclusive by *primary* tool function.
    Profiles compose categories and/or pinned individual tools; aliases lock old
    named selector behaviour to the original pinned IDs. Nothing is executable.
    """
    core.check_links(Path(path))
    try:
        data = core.strict_json_loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolsetError("Cannot read toolsets manifest: " + str(exc)) from exc
    if not isinstance(data, dict) or data.get("schemaVersion") not in (1, 2):
        raise ToolsetError("toolsets.json must have schemaVersion=1 or 2")
    version = data["schemaVersion"]
    categories, profiles = {}, {}
    legacy = {}
    for field in ("categories", "profiles", "aliases") if version == 2 else ("categories", "profiles"):
        output = categories if field == "categories" else (legacy if field == "aliases" else profiles)
        entries = data.get(field, [])
        if not isinstance(entries, list) or len(entries) > 32:
            raise ToolsetError(field + ": expected a list with at most 32 entries")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ToolsetError(field + ": expected objects")
            name = _validate_id(entry.get("id"))
            if name in output:
                raise ToolsetError(field + ": duplicate ID " + name)
            if not isinstance(entry.get("label"), str) or not entry["label"].strip():
                raise ToolsetError(field + ": missing label for " + name)
            members = "tools" if field == "categories" else "categories"
            selected = entry.get(members)
            if not isinstance(selected, list) or len(selected) > 64:
                raise ToolsetError(field + "." + name + ": invalid members")
            seen = set()
            for value in selected:
                _validate_id(value)
                if value in seen:
                    raise ToolsetError(field + "." + name + ": duplicate member " + value)
                seen.add(value)
            if field == "categories":
                if (not isinstance(entry.get("description"), str)
                        or len(entry["description"]) > 512):
                    raise ToolsetError("categories." + name + ": invalid description")
                if any(t not in catalog for t in selected):
                    raise ToolsetError("categories." + name + ": unknown pinned tool ID")
            else:
                if version == 2:
                    direct = entry.get("tools", [])
                    if (not isinstance(direct, list) or len(direct) > 64
                            or any(not isinstance(t, str) for t in direct)):
                        raise ToolsetError(field + "." + name + ": invalid tools")
                    for tool in direct:
                        _validate_id(tool)
                    if len(set(direct)) != len(direct) or any(t not in catalog for t in direct):
                        raise ToolsetError(field + "." + name + ": duplicate/unknown pinned tool")
                else:
                    direct = []
                entry = dict(entry, tools=direct)
            output[name] = entry

    if set(categories) & set(profiles) or set(categories) & set(legacy) or set(profiles) & set(legacy):
        raise ToolsetError("Category/profile/alias IDs overlap")
    if version == 2:
        if data.get("classification") != "exactly-one-primary-domain-per-installable-tool":
            raise ToolsetError("v2 requires explicit classification contract")
        owned = {}
        for name, entry in categories.items():
            for tool in entry["tools"]:
                if tool in owned:
                    raise ToolsetError("MECE: " + tool + " assigned multiple primary domains")
                owned[tool] = name
        if set(owned) != set(catalog):
            raise ToolsetError("MECE: every pinned catalog ID must have exactly one primary domain")
    for field, group in (("profiles", profiles), ("aliases", legacy)):
        for name, entry in group.items():
            if any(c not in categories for c in entry["categories"]):
                raise ToolsetError(field + "." + name + ": unknown category")
    # Aliases resolve via the same selector code, but remain visibly separated
    # from canonical profiles when listing the taxonomy.
    for name, entry in legacy.items():
        profiles[name] = dict(entry, legacy=True)
    return categories, profiles


def selection(names, include, exclude, categories, profiles, catalog):
    if not names:
        raise ToolsetError("Select one or more categories/profiles")
    found = []
    for name in names:
        _validate_id(name)
        if name in categories:
            groups = (name,)
        elif name in profiles:
            groups = profiles[name]["categories"]
            for tool in profiles[name].get("tools", []):
                if tool not in found:
                    found.append(tool)
        else:
            raise ToolsetError("Unknown toolset/category: " + name)
        for group in groups:
            for tool in categories[group]["tools"]:
                if tool not in found:
                    found.append(tool)
    for tool in include:
        _validate_id(tool)
        if tool not in catalog:
            raise ToolsetError("Unknown pinned catalog tool: " + tool)
        if tool not in found:
            found.append(tool)
    for tool in exclude:
        _validate_id(tool)
        if tool not in catalog:
            raise ToolsetError("Unknown pinned catalog tool to exclude: " + tool)
    return [tool for tool in found if tool not in set(exclude)]


def status_of(tool, root, state):
    """Installed/stale/unmanaged; never change state during planning."""
    name, dest = tool["id"], tool["dest"]
    install = root / dest
    backup = root / (dest + ".old")
    core.check_links(install)
    core.check_links(backup)
    if os.path.lexists(backup):
        return "blocked-backup"
    if name not in state:
        return "blocked-unmanaged" if os.path.lexists(install) else "install"
    record = state[name]
    if record["dest"] != dest:
        return "blocked-destination"
    if (record.get("version") != tool["version"]
            or record.get("sha256") != tool["sha256"]):
        return "blocked-pin"
    if not install.is_dir():
        return "blocked-missing"
    return "already-installed"


def create_plan(names, include, exclude, root, manifest=MANIFEST, *,
                load_catalog=core.load_catalog, read_state=core.read_state):
    """Read-only deterministic plan; install only from validated pinned catalog."""
    catalog = load_catalog(core.DEFAULT_CATALOG)
    categories, profiles = load_manifest(manifest, catalog)
    picked = selection(names, include, exclude, categories, profiles, catalog)
    root = Path(os.path.abspath(str(root)))
    core.check_links(root)
    state = read_state(root)
    operations = []
    for ident in picked:
        tool = catalog[ident]
        operations.append({
            "id": ident, "version": tool["version"], "sha256": tool["sha256"],
            "status": status_of(tool, root, state),
            "recommended_available": bool(tool.get("recommended")),
        })
    return {"selected": list(names), "root": str(root), "tools": operations}


def created_output_identity(info):
    """Capture (device, file ID) while the output's own handle is open.

    Used only to recognize files created by the current evidence operation.
    This is a cautious best-effort cleanup guard, not an atomic Windows lock.
    """
    return info.st_dev, info.st_ino


def cleanup_own_output(path, identity):
    """Best-effort remove only a regular output with its original identity.

    A competing writer's existing or replaced file must remain untouched.
    Fail closed on reparse/link checks; never follow an unknown replacement.
    """
    if identity is None:
        return
    candidate = Path(path)
    try:
        core.check_links(candidate)
        current = candidate.stat()
        if (stat.S_ISREG(current.st_mode) and
                created_output_identity(current) == identity):
            candidate.unlink()
    except (OSError, core.PortakitError):
        pass


class Evidence:
    """Copy each displayed line exactly to a new local UTF-8 audit log."""
    def __init__(self, path):
        self.path = Path(path)
        core.check_links(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("x", encoding="utf-8", newline="\n")

    def emit(self, message):
        message = str(message)
        print(message, flush=True)
        self.stream.write(message + "\n")
        self.stream.flush()

    def close(self):
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class BatchLock:
    """Second byte-0 lock serializes entire category runs, not just individual tools."""
    def __init__(self, root):
        self.path = root / ".portakit-toolset-lock"
        self.fd = None

    def __enter__(self):
        core.check_links(self.path)
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR | os.O_BINARY)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            os.close(fd)
            raise ToolsetError("Another toolset operation is already in progress") from exc
        self.fd = fd
        return self

    def __exit__(self, *_):
        try:
            os.lseek(self.fd, 0, 0)
            msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(self.fd)


def verify_offline_assets(rows, archive_dir, *, load_catalog=core.load_catalog):
    """Preflight EVERY missing pinned artifact before any install is started.

    No network calls and no directory writes. SHA and max size are checked from
    vendor-named files, exactly as the core installer will re-check at stage.
    The user must bring the original archive untouched into this directory.
    """
    offline = Path(os.path.abspath(str(archive_dir)))
    core.check_links(offline)
    if not offline.is_dir():
        raise ToolsetError("Offline directory not found: " + str(offline))
    catalog = load_catalog(core.DEFAULT_CATALOG)
    plan = {}
    for row in rows:
        if row["status"] != "install":
            continue
        tool = catalog[row["id"]]
        filename = unquote(urlsplit(tool["url"]).path.split("/")[-1])
        if not filename or filename in (".", "..") or "/" in filename or "\\" in filename:
            raise ToolsetError("Unsafe offline vendor filename for " + row["id"])
        original = offline / filename
        core.check_links(original)
        if not original.is_file():
            raise ToolsetError("Missing offline pinned archive: " + str(original))
        if original.stat().st_size > core.MAX_DOWNLOAD_BYTES:
            raise ToolsetError("Oversize offline archive for " + row["id"])
        with original.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != tool["sha256"].lower():
            raise ToolsetError("Offline SHA-256 mismatch for " + row["id"])
        plan[row["id"]] = original
    return plan


def apply(plan, recommended, log, runner=None, *, offline_dir=None,
          child_timeout=bounded.DEFAULT_TIMEOUT):
    """Apply verified plan using bounded core-child capture by default.

    runner is a test-only injected subprocess.run-compatible callback.
    Per-child timeout is configurable for slow offline devices. stdout/stderr
    are each limited to 256KiB on the real execution path.
    """
    if type(child_timeout) is not int or not 1 <= child_timeout <= bounded.MAX_TIMEOUT:
        raise ToolsetError("child_timeout must be an integer in 1..3600 seconds")
    root = Path(plan["root"])
    if not plan["tools"]:
        print("NO_OP: selected toolsets contain no verified pinned tools")
        return {"installed": [], "skipped": [], "failed": None}
    # Share the single-tool CLI's fail-closed placement rule: a batch must
    # never remove or rename its own evidence while replacing a managed tool.
    # Validate before mkdir, lock, download or any child installer process.
    core.check_evidence_location(log, root, "install")
    if any(row["status"].startswith("blocked-") for row in plan["tools"]):
        raise ToolsetError("Cannot apply blocked plan; first resolve pins, backups or unmanaged paths")
    if offline_dir is not None and recommended:
        raise ToolsetError("Offline --recommended is unsupported: editor plugins may require extra downloads")
    if offline_dir is not None:
        verify_offline_assets(plan["tools"], offline_dir)
    root.mkdir(parents=True, exist_ok=True)
    with BatchLock(root):
        # Preflight again under batch lock, before downloading anything.
        current = create_plan(plan["selected"], plan["include"], plan["exclude"],
                              root, plan["manifest"])
        if any(row["status"].startswith("blocked-") for row in current["tools"]):
            raise ToolsetError("Blocked during apply preflight; no new tool downloaded")
        offline_assets = (verify_offline_assets(current["tools"], offline_dir)
                          if offline_dir is not None else {})
        # Keep the verified pin snapshot for each read-only post-install check.
        # A successful child JSON alone does not prove its receipt was persisted.
        verified_catalog = core.load_catalog(core.DEFAULT_CATALOG)
        with Evidence(log) as evidence:
            evidence.emit("OPERATION: apply toolsets (explicit --yes)")
            evidence.emit("CHILD_TIMEOUT_SECONDS: " + str(child_timeout))
            evidence.emit("CHILD_OUTPUT_LIMIT_PER_STREAM: " + str(bounded.MAX_CAPTURE))
            evidence.emit("ROOT: " + str(root))
            evidence.emit("SELECTED: " + ", ".join(plan["selected"]))
            evidence.emit("RECOMMENDED: " + ("YES (new installs only)" if recommended else "NO"))
            evidence.emit("SOURCE: " + ("OFFLINE LOCAL SHA VERIFIED" if offline_dir else "PINNED HTTPS"))
            evidence.emit("PLAN: " + ", ".join(row["id"] + "=" + row["status"]
                                              for row in current["tools"]))
            result = {"installed": [], "skipped": [], "failed": None}
            for row in current["tools"]:
                name = row["id"]
                if row["status"] == "already-installed":
                    result["skipped"].append(name)
                    evidence.emit("SKIP: " + name + " (already managed; no update/config change)")
                    continue
                cmd = [sys.executable, "-I", str(TOOL), "--json", "--root", str(root)]
                if name in offline_assets:
                    cmd.extend(["--archive", str(offline_assets[name])])
                cmd.extend(["install", name])
                if recommended and row["recommended_available"]:
                    cmd.append("--recommended")
                evidence.emit("INSTALL: " + name + " (catalog SHA-pinned)")
                try:
                    if runner is None:
                        completed = bounded.run_bounded(cmd, timeout_seconds=child_timeout)
                    else:
                        completed = runner(cmd, capture_output=True, text=True, encoding="utf-8",
                                           errors="replace", check=False)
                except (OSError, bounded.BoundedProcessError) as exc:
                    result["failed"] = name
                    evidence.emit("STOP: " + name + " launcher error: " + str(exc))
                    evidence.emit("PARTIAL: previously installed tools are NOT rolled back")
                    break
                for line in (completed.stdout or "").splitlines():
                    evidence.emit("CHILD STDOUT: " + line)
                for line in (completed.stderr or "").splitlines():
                    evidence.emit("CHILD STDERR: " + line)
                if completed.returncode != 0:
                    result["failed"] = name
                    evidence.emit("STOP: " + name + " exit=" + str(completed.returncode))
                    evidence.emit("PARTIAL: previously installed tools are NOT rolled back")
                    break
                try:
                    parsed = core.strict_json_loads(completed.stdout)
                    if (not isinstance(parsed, dict) or parsed.get("ok") is not True
                            or parsed.get("command") != "install"
                            or not isinstance(parsed.get("data"), dict)
                            or parsed["data"].get("id") != name
                            or parsed.get("error") is not None):
                        raise ValueError("Unexpected core installer result")
                except (ValueError, AttributeError, TypeError) as exc:
                    result["failed"] = name
                    evidence.emit("STOP: " + name + " invalid core result: " + str(exc))
                    break
                try:
                    pin = verified_catalog[name]
                    if (pin["version"] != row["version"]
                            or pin["sha256"] != row["sha256"]):
                        raise ToolsetError("catalog pin changed since preflight")
                    observed = status_of(pin, root, core.read_state(root))
                    if observed != "already-installed":
                        raise ToolsetError("managed install not confirmed: " + observed)
                except (KeyError, OSError, ValueError, core.PortakitError,
                        ToolsetError) as exc:
                    result["failed"] = name
                    evidence.emit("STOP: " + name + " post-install check: " + str(exc))
                    evidence.emit("PARTIAL: previously installed tools are NOT rolled back")
                    break
                result["installed"].append(name)
            evidence.emit("RESULT: " + ("FAILED" if result["failed"] else "COMPLETE"))
            evidence.emit("EVIDENCE: " + str(Path(log).absolute()))
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("command", choices=("list", "plan", "apply"))
    parser.add_argument("toolsets", nargs="*", help="category or profile IDs")
    parser.add_argument("--root", default="portable")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--include", action="append", default=[], metavar="ID")
    parser.add_argument("--exclude", action="append", default=[], metavar="ID")
    parser.add_argument("--offline-dir", metavar="DIR",
                        help="apply only; local original vendor files, all SHA preverified; no Internet")
    parser.add_argument("--recommended", action="store_true",
                        help="apply recommended settings/plugins on NEW installs only")
    parser.add_argument("--yes", action="store_true",
                        help="required acknowledgement for apply; never for plan/list")
    parser.add_argument("--log-file", help="new log path for apply; must not exist")
    parser.add_argument("--child-timeout", type=int, metavar="SECONDS",
                        help="apply only; per-tool core installer timeout 1..3600 (default: 600)")
    args = parser.parse_args(argv)
    try:
        catalog = core.load_catalog(core.DEFAULT_CATALOG)
        categories, profiles = load_manifest(args.manifest, catalog)
        if args.command == "list":
            if (args.toolsets or args.include or args.exclude or args.recommended
                    or args.yes or args.log_file or args.offline_dir or args.child_timeout is not None):
                raise ToolsetError("list takes no selections/installation options")
            print("CATEGORIES")
            for name, group in categories.items():
                print(name + "\t" + group["label"] + "\t" +
                      (", ".join(group["tools"]) if group["tools"] else "(no verified pins yet)"))
            print("PROFILES")
            for name, profile in profiles.items():
                if profile.get("legacy"):
                    continue
                sources = profile["categories"] + profile.get("tools", [])
                print(name + "\t" + profile["label"] + "\t" + ", ".join(sources))
            if any(v.get("legacy") for v in profiles.values()):
                print("LEGACY ALIASES (stable pinned selections)")
                for name, profile in profiles.items():
                    if profile.get("legacy"):
                        print(name + "\t" + ", ".join(profile.get("tools", [])))
            return 0
        if args.command == "plan" and (args.yes or args.log_file or args.recommended
                                        or args.offline_dir or args.child_timeout is not None):
            raise ToolsetError("plan is read-only; --yes/--recommended/--log-file apply only")
        if args.command == "apply" and not args.yes:
            raise ToolsetError("apply requires explicit --yes (plan first)")
        root = Path(os.path.abspath(args.root))
        plan = create_plan(args.toolsets, args.include, args.exclude, root, args.manifest)
        if args.command == "plan":
            print("PLAN: " + ", ".join(plan["selected"]))
            print("ROOT: " + plan["root"])
            for row in plan["tools"]:
                print(row["id"] + "\t" + row["version"] + "\t" + row["status"])
            if not plan["tools"]:
                print("EMPTY: no SHA-pinned tools in selection")
            if any(x["status"].startswith("blocked-") for x in plan["tools"]):
                print("BLOCKED: resolve previous state/pin before apply")
            print("NO CHANGES / NO DOWNLOADS")
            return 0
        plan.update(include=args.include, exclude=args.exclude, manifest=args.manifest)
        root = Path(plan["root"])
        log = args.log_file or str(root / ".portakit-evidence" /
                 ("toolsets-" + datetime.now().strftime("%Y%m%d-%H%M%S")
                  + "-" + uuid.uuid4().hex[:8] + ".log"))
        result = apply(plan, args.recommended, log, offline_dir=args.offline_dir,
                       child_timeout=(args.child_timeout if args.child_timeout is not None
                                      else bounded.DEFAULT_TIMEOUT))
        return 1 if result["failed"] else 0
    except (ToolsetError, core.PortakitError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
