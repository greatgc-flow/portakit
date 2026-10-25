"""Personal, user-owned, reproducible PortaKit configurations.

Every known tool can be selected and saved, but only SHA-pinned, catalog-approved
tools may be installed. All research-only tools are inert notes in the personal
kit. This script never installs services, drivers, registry keys or operating
system components. Windows / Python 3.11+ stdlib, consistent with PortaKit core.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import uuid
from datetime import datetime

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import portakit as core  # noqa: E402
import toolsets as sets  # noqa: E402

CANDIDATES = HERE / "research" / "TOOLS_CANDIDATES_20261020.json"
INTAKE = HERE / "research" / "INTAKE_ENTERPRISE_PORTABLE_20261025.json"
KIT_VERSION = 1
KIT_FIELDS = frozenset(("schemaVersion", "name", "tools", "lockedPins",
                        "researchOnly", "osBuiltins"))
ALLOWED_PIN_FIELDS = frozenset(("version", "sha256", "dest"))
NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")


class KitError(Exception):
    pass


def json_file(path):
    """Load data but never follow Windows junctions or symbolic links."""
    path = Path(path).absolute()
    core.check_links(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise KitError("Cannot read JSON " + str(path) + ": " + str(exc)) from exc


def inventory():
    """Keep installable and research inventories independent and deterministic."""
    pins = core.load_catalog(core.DEFAULT_CATALOG)
    categories, profiles = sets.load_manifest(sets.MANIFEST, pins)
    rows = json_file(CANDIDATES)
    incoming = json_file(INTAKE)
    if not isinstance(rows, dict) or not isinstance(rows.get("tools"), list):
        raise KitError("Canonical research inventory malformed")
    if not isinstance(incoming, dict) or not isinstance(incoming.get("records"), list):
        raise KitError("Research intake malformed")
    owners = {name: domain for domain, group in categories.items()
              for name in group["tools"]}
    known = {}
    for row in rows["tools"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise KitError("Malformed canonical research item")
        ident = sets._validate_id(row["id"])
        if ident in known or row.get("primary") not in categories:
            raise KitError("Duplicate or unclassified canonical tool: " + ident)
        adm = row.get("admission")
        if adm not in ("PINNED_CATALOG", "OS_BUILTIN", "RESEARCH_ONLY"):
            raise KitError("Unknown admission: " + ident)
        if (ident in pins) != (adm == "PINNED_CATALOG"):
            raise KitError("Catalog/research drift: " + ident)
        if ident in pins and owners.get(ident) != row["primary"]:
            raise KitError("Pin primary ownership mismatch: " + ident)
        known[ident] = {"id": ident, "name": row["name"],
                        "primary": row["primary"], "admission": adm}
    if set(pins) != {x for x in known if known[x]["admission"] == "PINNED_CATALOG"}:
        raise KitError("Research missing one or more pinned catalog tools")
    for row in incoming["records"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise KitError("Malformed additional research item")
        ident = sets._validate_id(row["id"])
        if row.get("stage") == "NEW_RESEARCH_ONLY":
            if ident in known or row.get("primary") not in categories:
                raise KitError("Intake collision or unclassified tool: " + ident)
            known[ident] = {"id": ident, "name": row["name"],
                            "primary": row["primary"], "admission": "RESEARCH_ONLY"}
        elif ident not in known:
            raise KitError("Unresolved existing intake tool: " + ident)
    return pins, categories, profiles, known


def requested_ids(tools, profiles_selected, domains, excluded, pins, categories,
                  profiles, known):
    """Select exact research IDs plus deduplicated pinned groups/presets."""
    requested = []
    selectors = list(profiles_selected) + list(domains)
    for domain in domains:
        if domain not in categories:
            raise KitError("Unknown primary category: " + domain)
    for profile in profiles_selected:
        if profile not in profiles:
            raise KitError("Unknown preset: " + profile)
    if selectors:
        requested.extend(sets.selection(selectors, [], [], categories, profiles, pins))
    for ident in tools:
        sets._validate_id(ident)
        if ident not in known:
            raise KitError("Unknown tool: " + ident)
        requested.append(ident)
    for ident in excluded:
        sets._validate_id(ident)
        if ident not in known:
            raise KitError("Unknown excluded tool: " + ident)
    denied = set(excluded)
    selected = [x for x in dict.fromkeys(requested) if x not in denied]
    if not selected:
        raise KitError("Empty selection. Supply --tool, --preset or --category")
    # 7-Zip full SFX is DATA and requires managed 7zr to be installed first.
    if "7zip" in selected and "7zr" in selected:
        selected.remove("7zr")
        selected.insert(selected.index("7zip"), "7zr")
    return selected


def make_kit(name, selected, pins, known):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise KitError("Kit name must be 1-64 lowercase letters/digits/._-")
    locks = {}
    pending = []
    builtin = []
    for ident in selected:
        row = known[ident]
        if row["admission"] == "PINNED_CATALOG":
            pin = pins[ident]
            locks[ident] = {k: pin[k] for k in ("version", "sha256", "dest")}
        elif row["admission"] == "OS_BUILTIN":
            builtin.append(ident)
        else:
            pending.append(ident)
    return {"schemaVersion": KIT_VERSION, "name": name, "tools": selected,
            "lockedPins": locks, "researchOnly": pending, "osBuiltins": builtin}


def read_kit(path, pins, known):
    data = json_file(path)
    if not isinstance(data, dict) or set(data) != KIT_FIELDS:
        raise KitError("Unknown/invalid kit file schema")
    if type(data["schemaVersion"]) is not int or data["schemaVersion"] != KIT_VERSION:
        raise KitError("Unsupported kit schema version")
    if not isinstance(data["name"], str) or not NAME.fullmatch(data["name"]):
        raise KitError("Invalid kit name")
    ids = data["tools"]
    if (not isinstance(ids, list) or not ids or len(ids) > 256
            or any(not isinstance(x, str) or x not in known for x in ids)
            or len(ids) != len(set(ids))):
        raise KitError("Unknown, empty or duplicated selected tools")
    locks, research, builtins = data["lockedPins"], data["researchOnly"], data["osBuiltins"]
    if (not isinstance(locks, dict) or not isinstance(research, list)
            or not isinstance(builtins, list)):
        raise KitError("Invalid saved statuses")
    for part in (list(locks), research, builtins):
        if (any(not isinstance(x, str) or x not in ids for x in part)
                or len(part) != len(set(part))):
            raise KitError("Invalid saved tool partition")
    if set(locks) & set(research) or set(locks) & set(builtins) or set(research) & set(builtins):
        raise KitError("Overlapping saved statuses")
    if set(ids) != (set(locks) | set(research) | set(builtins)):
        raise KitError("Incomplete saved tool partition")
    for ident, snapshot in locks.items():
        if (not isinstance(snapshot, dict) or set(snapshot) != ALLOWED_PIN_FIELDS
                or any(not isinstance(snapshot[k], str) for k in ALLOWED_PIN_FIELDS)):
            raise KitError("Malformed saved pinned tool: " + ident)
        if ident in pins:
            current = {k: pins[ident][k] for k in ALLOWED_PIN_FIELDS}
            if current != snapshot:
                raise KitError("PIN_CHANGED for " + ident +
                               " (recreate kit after reviewing update)")
        else:
            raise KitError("PIN_REMOVED for " + ident)
    for ident in builtins:
        if known[ident]["admission"] != "OS_BUILTIN":
            raise KitError("Built-in classification changed: " + ident)
    for ident in research:
        if known[ident]["admission"] == "OS_BUILTIN":
            raise KitError("Pending classification changed: " + ident)
        # A newly approved tool MUST stay inert in an older saved kit until
        # explicitly reselected/re-locked by creating a new kit file.
    return data


def print_inventory(known, category=None, show_all=False):
    available = [row for row in known.values()
                 if (category is None or row["primary"] == category)
                 and (show_all or row["admission"] == "PINNED_CATALOG")]
    for row in sorted(available, key=lambda r: (r["primary"], r["id"])):
        status = {"PINNED_CATALOG": "READY",
                  "OS_BUILTIN": "OS_ONLY",
                  "RESEARCH_ONLY": "RESEARCH_ONLY"}[row["admission"]]
        print(row["primary"] + "\t" + row["id"] + "\t" + status +
              "\t" + row["name"])
    print("TOTAL: " + str(len(available)))


def save_new(data, path, log_file=None):
    """Create an explicit new personal profile and a matching local transcript."""
    target = Path(path).absolute()
    logfile = Path(log_file).absolute() if log_file else target.with_suffix(".log")
    core.check_links(target)
    core.check_links(logfile)
    if target == logfile or os.path.lexists(target) or os.path.lexists(logfile):
        raise KitError("Output profile/log already exists; no overwrite allowed")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sets.Evidence(logfile) as log:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as out:
                json.dump(data, out, indent=2, ensure_ascii=False)
                out.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        log.emit("CREATED: " + str(target))
        log.emit("KIT: " + data["name"])
        log.emit("SELECTED: " + ", ".join(data["tools"]))
        log.emit("READY_PINNED: " + str(len(data["lockedPins"])))
        log.emit("RESEARCH_ONLY: " + str(len(data["researchOnly"])))
        log.emit("OS_BUILTIN: " + str(len(data["osBuiltins"])))
        log.emit("NO INSTALL / NO NETWORK / NO SYSTEM CHANGES")


def approved_selection(kit):
    return [ident for ident in kit["tools"] if ident in kit["lockedPins"]]


def create_plan(kit, root):
    approved = approved_selection(kit)
    # nw is the frozen empty legacy alias; preserve all install semantics by
    # delegating to existing toolset resolver instead of writing a new engine.
    plan = sets.create_plan(["nw"], approved, [], root)
    plan.update(include=approved, exclude=[], manifest=sets.MANIFEST)
    return plan


def check_prerequisite(kit, plan):
    approved = approved_selection(kit)
    if "7zip" not in approved:
        return
    if "7zr" in approved:
        if approved.index("7zr") > approved.index("7zip"):
            raise KitError("7zr must precede 7zip for first-time installs")
    else:
        installed = sets.core.read_state(Path(plan["root"]))
        pin = sets.core.load_catalog(sets.core.DEFAULT_CATALOG)["7zr"]
        record = installed.get("7zr")
        if (not isinstance(record, dict) or
                any(record.get(key) != pin[key] for key in ("version", "sha256", "dest")) or
                not (Path(plan["root"]) / pin["dest"] / "7zr.exe").is_file()):
            raise KitError("7zip requires separately installed, matching pinned 7zr; "
                           "include --tool 7zr and create a new kit")


def show_plan(kit, plan):
    print("KIT: " + kit["name"])
    for item in plan["tools"]:
        print(item["id"] + "\t" + item["status"] + "\t" + item["version"])
    for ident in kit["osBuiltins"]:
        print(ident + "\tOS_BUILTIN (informational; not installed)")
    for ident in kit["researchOnly"]:
        print(ident + "\tRESEARCH_ONLY (not installable)")
    print("SUMMARY: approved=" + str(len(kit["lockedPins"])) +
          " built_in=" + str(len(kit["osBuiltins"])) +
          " pending=" + str(len(kit["researchOnly"])))
    print("NO CHANGES / NO DOWNLOADS")


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    lst = sub.add_parser("list", help="browse approved tools or all 151 research candidates")
    lst.add_argument("--all", action="store_true", help="also show built-in and unverified candidates")
    lst.add_argument("--category", help="filter by one MECE primary domain")
    create = sub.add_parser("create", help="create new portable personal kit and matching evidence log")
    create.add_argument("--name", required=True)
    create.add_argument("--out", required=True, metavar="KIT.json")
    create.add_argument("--tool", action="append", default=[], metavar="ID",
                        help="any known ID; repeat as needed, pending items stay inert")
    create.add_argument("--preset", action="append", default=[], metavar="NAME",
                        help="built-in profile; repeat to compose and deduplicate")
    create.add_argument("--category", action="append", default=[], metavar="ID",
                        help="select only approved pins from a primary domain")
    create.add_argument("--exclude", action="append", default=[], metavar="ID")
    create.add_argument("--log-file", help="new evidence log path, default KIT.log")
    for cmd in ("plan", "build"):
        p = sub.add_parser(cmd, help=("read-only preview" if cmd == "plan" else
                                      "explicit opt-in apply using existing SHA-pinned engine"))
        p.add_argument("--kit", required=True)
        p.add_argument("--root", default="portable")
        if cmd == "build":
            p.add_argument("--yes", action="store_true", help="mandatory install consent")
            p.add_argument("--skip-pending", action="store_true",
                           help="explicitly build approved subset while keeping pending inert")
            p.add_argument("--offline-dir", help="original approved vendor archives, SHA preflight")
            p.add_argument("--recommended", action="store_true",
                           help="optional editor settings/plugins on NEW online installs only")
            p.add_argument("--log-file", help="new toolset evidence log (no overwrite)")
    args = parser.parse_args(argv)
    try:
        pins, categories, profiles, known = inventory()
        if args.command == "list":
            if args.category and args.category not in categories:
                raise KitError("Unknown category: " + args.category)
            print_inventory(known, args.category, args.all)
            return 0
        if args.command == "create":
            selected = requested_ids(args.tool, args.preset, args.category,
                                     args.exclude, pins, categories, profiles, known)
            data = make_kit(args.name, selected, pins, known)
            save_new(data, args.out, args.log_file)
            return 0
        kit = read_kit(args.kit, pins, known)
        plan = create_plan(kit, args.root)
        check_prerequisite(kit, plan)
        if args.command == "plan":
            show_plan(kit, plan)
            return 0
        if not args.yes:
            raise KitError("build requires explicit --yes (run plan first)")
        if kit["researchOnly"] and not args.skip_pending:
            raise KitError("Research-only candidates remain unapproved: " +
                           ", ".join(kit["researchOnly"]) +
                           "; no changes made. Use --skip-pending to build approved subset")
        if any(x["status"].startswith("blocked-") for x in plan["tools"]):
            raise KitError("Blocked installed state/pin/destination; no changes made")
        log = (args.log_file or
               str(Path(plan["root"]) / ".portakit-evidence" /
                   ("personal-" + datetime.now().strftime("%Y%m%d-%H%M%S") +
                    "-" + uuid.uuid4().hex[:8] + ".log")))
        if not plan["tools"]:
            with sets.Evidence(log) as evidence:
                evidence.emit("NO_OP: no approved installable tools; no changes")
                evidence.emit("OS_BUILTIN: " + str(len(kit["osBuiltins"])))
                evidence.emit("RESEARCH_ONLY: " + str(len(kit["researchOnly"])))
            return 0
        result = sets.apply(plan, args.recommended, log, offline_dir=args.offline_dir)
        return 1 if result["failed"] else 0
    except (KitError, sets.ToolsetError, core.PortakitError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
