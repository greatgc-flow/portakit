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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import portakit as core  # noqa: E402
import toolsets as sets  # noqa: E402

CANDIDATES = HERE / "research" / "TOOLS_CANDIDATES_20261020.json"
INTAKE = HERE / "research" / "INTAKE_ENTERPRISE_PORTABLE_20261025.json"
KIT_VERSION = 1
KIT_FIELDS = frozenset(("schemaVersion", "name", "tools", "lockedPins",
                        "researchOnly", "osBuiltins"))
KIT_V2_FIELDS = KIT_FIELDS | {"pluginSelections"}
# The report's JsonTools ID differs from its vendor plugin ID.
PLUGIN_PIN_ALIASES = {"jsontools-npp": "jsontools"}
ALLOWED_PIN_FIELDS = frozenset(("version", "sha256", "dest"))
NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")


class KitError(Exception):
    pass


def json_file(path):
    """Load data but never follow Windows junctions or symbolic links."""
    path = Path(path).absolute()
    core.check_links(path)
    try:
        return core.strict_json_loads(path.read_text(encoding="utf-8"))
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
            if row.get("primary") not in categories:
                raise KitError("Unclassified intake tool: " + ident)
            # Once a candidate is promoted into the canonical inventory,
            # the dated sidecar stays valid without duplicating the entry.
            if ident in known:
                if known[ident]["primary"] != row["primary"]:
                    raise KitError("Intake primary ownership conflict: " + ident)
            else:
                known[ident] = {"id": ident, "name": row["name"],
                                "primary": row["primary"], "admission": "RESEARCH_ONLY"}
        elif ident not in known:
            raise KitError("Unresolved existing intake tool: " + ident)
    return pins, categories, profiles, known


def plugin_inventory(pins):
    """Six independently selectable editor plugin families, report sourced.

    SHA-pinned profile plugins are still NOT independently installable. Their
    status is metadata-only. Vendor copyright/licensing and transfer gate remain.
    """
    incoming = json_file(INTAKE)
    rows = incoming.get("relatedEditorPlugins")
    if not isinstance(rows, list) or len(rows) > 64:
        raise KitError("Malformed editor plugin inventory")
    known = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise KitError("Malformed editor plugin")
        ident = sets._validate_id(row["id"])
        host = row.get("host")
        if (ident in known or host not in ("notepad++", "winmerge")
                or host not in pins):
            raise KitError("Duplicate or unsupported editor plugin host")
        pin_id = PLUGIN_PIN_ALIASES.get(ident, ident)
        pinned = next((p for p in pins[host].get("recommended", {}).get("plugins", [])
                       if p["id"] == pin_id), None)
        status = "PINNED_METADATA_ONLY" if pinned is not None else "RESEARCH_ONLY"
        if row.get("stage") == "ALREADY_PINNED_PLUGIN_AS_OPTION" and pinned is None:
            raise KitError("Pinned plugin mapping missing: " + ident)
        if row.get("stage") == "REVIEW_ONLY_PLUGIN" and pinned is not None:
            raise KitError("Report plugin admission mismatch: " + ident)
        if row.get("stage") not in ("REVIEW_ONLY_PLUGIN", "ALREADY_PINNED_PLUGIN_AS_OPTION"):
            raise KitError("Unrecognized editor plugin stage: " + ident)
        known[ident] = {"id": ident, "name": row["name"], "host": host,
                        "status": status,
                        "pin": ({k: pinned[k] for k in ("version", "sha256", "dest")}
                                if pinned is not None else None)}
    return known


def plugin_choices(requested, selected, pins, inventory=None):
    """Validate host prerequisite, dedup and snapshot optional plugin intent."""
    if not isinstance(requested, (list, tuple)):
        raise KitError("Plugin choices must be a list")
    if not requested:
        return []
    known = inventory if inventory is not None else plugin_inventory(pins)
    selected_set = set(selected)
    items = []
    for ident in dict.fromkeys(requested):
        if not isinstance(ident, str) or ident not in known:
            raise KitError("Unknown editor plugin: " + str(ident))
        plugin = known[ident]
        if plugin["host"] not in selected_set:
            raise KitError("Plugin host must be selected: " + plugin["host"])
        if plugin["host"] not in pins:
            raise KitError("Plugin host is not approved catalog pin")
        items.append({"id": ident, "host": plugin["host"],
                      "status": plugin["status"],
                      "lockedPin": (dict(plugin["pin"]) if plugin["pin"] else None)})
    return items


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


def make_kit(name, selected, pins, known, *, plugins=()):
    """v1 if no plugins; v2 only when individually chosen plugins exist."""

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
    result = {"schemaVersion": KIT_VERSION, "name": name, "tools": selected,
              "lockedPins": locks, "researchOnly": pending, "osBuiltins": builtin}
    chosen = plugin_choices(plugins, selected, pins)
    if chosen:
        for item in chosen:
            if item["host"] not in locks:
                raise KitError("Plugin host must be pinned in the selected kit")
        result["schemaVersion"] = 2
        result["pluginSelections"] = chosen
    return result


def read_kit(path, pins, known):
    data = json_file(path)
    if not isinstance(data, dict):
        raise KitError("Unknown/invalid kit file schema")
    if (type(data.get("schemaVersion")) is not int
            or data["schemaVersion"] not in (1, 2)):
        raise KitError("Unsupported kit schema version")
    expected = KIT_FIELDS if data["schemaVersion"] == 1 else KIT_V2_FIELDS
    if set(data) != expected:
        raise KitError("Unknown/invalid kit file schema")
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
    if data["schemaVersion"] == 2:
        choices = data["pluginSelections"]
        if (not isinstance(choices, list) or not choices or len(choices) > 64):
            raise KitError("Invalid individual plugin selections")
        inventory_plugins = plugin_inventory(pins)
        seen = set()
        for item in choices:
            if not isinstance(item, dict) or set(item) != {
                    "id", "host", "status", "lockedPin"}:
                raise KitError("Malformed individual plugin selection")
            ident = item["id"]
            if not isinstance(ident, str) or ident in seen or ident not in inventory_plugins:
                raise KitError("Unknown or duplicated editor plugin")
            seen.add(ident)
            current = inventory_plugins[ident]
            if item["host"] != current["host"] or item["host"] not in locks:
                raise KitError("Plugin host missing or mismatched for " + ident)
            if item["status"] not in ("PINNED_METADATA_ONLY", "RESEARCH_ONLY"):
                raise KitError("Invalid editor plugin status")
            if item["status"] == "RESEARCH_ONLY":
                if item["lockedPin"] is not None:
                    raise KitError("Research plugin must not have executable lock")
            elif item["lockedPin"] != current["pin"] or current["pin"] is None:
                raise KitError("Plugin PIN_CHANGED for " + ident)
            # Both states are selection metadata only, never installed by v2.
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
    core.check_links(target)
    core.check_links(logfile)
    # A failed save cannot be a valid kit/evidence record. On output error
    # attempt to remove only our own unchanged files, not other writers'.
    kit_identity = log_identity = None
    try:
        with sets.Evidence(logfile) as log:
            log_identity = sets.created_output_identity(
                os.fstat(log.stream.fileno()))
            with target.open("x", encoding="utf-8", newline="\n") as out:
                kit_identity = sets.created_output_identity(
                    os.fstat(out.fileno()))
                json.dump(data, out, indent=2, ensure_ascii=False)
                out.write("\n")
            log.emit("CREATED: " + str(target))
            log.emit("KIT: " + data["name"])
            log.emit("SELECTED: " + ", ".join(data["tools"]))
            log.emit("READY_PINNED: " + str(len(data["lockedPins"])))
            log.emit("RESEARCH_ONLY: " + str(len(data["researchOnly"])))
            log.emit("OS_BUILTIN: " + str(len(data["osBuiltins"])))
            if data["schemaVersion"] == 2:
                log.emit("EDITOR_PLUGINS_METADATA_ONLY: " +
                         ", ".join(x["id"] for x in data["pluginSelections"]))
            log.emit("NO INSTALL / NO NETWORK / NO SYSTEM CHANGES")
    except BaseException:
        sets.cleanup_own_output(logfile, log_identity)
        sets.cleanup_own_output(target, kit_identity)
        raise


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
    if kit["schemaVersion"] == 2:
        for item in kit["pluginSelections"]:
            print("PLUGIN: " + item["id"] + " (" + item["host"] +
                  ") " + item["status"] + " / NOT INSTALLED")
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
    create.add_argument("--plugin", action="append", default=[], metavar="ID",
                        help="select an editor plugin separately; research/metadata only")
    plug = sub.add_parser("plugins", help="browse six editor plugin choices (no install)")
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
        if args.command == "plugins":
            for item in plugin_inventory(pins).values():
                print(item["host"] + "\t" + item["id"] + "\t" +
                      item["status"] + "\t" + item["name"])
            return 0
        if args.command == "create":
            selected = requested_ids(args.tool, args.preset, args.category,
                                     args.exclude, pins, categories, profiles, known)
            data = make_kit(args.name, selected, pins, known, plugins=args.plugin)
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
        if kit["schemaVersion"] == 2 and args.recommended:
            raise KitError("--recommended conflicts with explicit plugin choices; "
                           "no editor plugins were installed")
        if kit["schemaVersion"] == 2 and not args.skip_pending:
            raise KitError("Individual editor plugins are metadata-only and "
                           "cannot be deployed by build; use --skip-pending "
                           "to build only pinned host applications")
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
