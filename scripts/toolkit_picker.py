"""Optional, zero-download Tkinter personal toolkit picker (Windows Python 3.11+).

The pure PickerModel is independently unit-testable without Tk/display.
UI can browse, filter, select, inspect/import, and SAVE inert personal kit JSON.
It deliberately has NO installation, update, uninstall, driver, service, shell
or network actions: use existing my_toolkit.py build --yes separately.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402
import offline_ready as readiness  # noqa: E402
import kit_footprint as footprint  # noqa: E402


STATES = {
    "PINNED_CATALOG": "READY",
    "OS_BUILTIN": "OS_ONLY",
    "RESEARCH_ONLY": "RESEARCH_ONLY",
}


class PickerModel:
    """Selection model for any number of tools; never evaluates tool code."""

    def __init__(self, *, inventories=None):
        if inventories is None:
            inventories = kit.inventory()
        self.pins, self.categories, self.profiles, self.known = inventories
        self.selected = []
        # Previously pending items that later gained a pin must remain inert
        # until a person explicitly deselects and reselects them.
        self.frozen_pending = set()
        self.plugin_catalog = kit.plugin_inventory(self.pins)
        self.selected_plugins = []
        self.frozen_plugin_choices = {}

    def rows(self, search="", category="all", status="all", selected_only=False,
             profile="all"):
        """Display effective saved-kit approval, never just current catalog pins.

        A formerly research-only ID that was later pinned remains inert in an
        imported kit until explicitly removed and reselected by the operator.
        """
        if not isinstance(search, str):
            raise kit.KitError("Search must be text")
        if type(selected_only) is not bool:
            raise kit.KitError("selected_only must be a boolean")
        if not isinstance(category, str) or (
                category != "all" and category not in self.categories):
            raise kit.KitError("Unknown category: " + str(category))
        if status not in ("all", "READY", "OS_ONLY", "RESEARCH_ONLY"):
            raise kit.KitError("Unknown status: " + str(status))
        if not isinstance(profile, str) or (
                profile != "all" and profile not in self.profiles):
            raise kit.KitError("Unknown preset filter: " + str(profile))
        # Profiles are pinned, named read-only projections of the same toolset
        # taxonomy. An empty legacy profile is a legitimate empty filter.
        # Reuse the authoritative selector; never add a profile to the kit.
        profile_ids = (None if profile == "all" else set(
            kit.sets.selection([profile], [], [], self.categories,
                               self.profiles, self.pins)))
        needle = search.casefold().strip()
        results = []
        selected = set(self.selected)
        for rec in self.known.values():
            is_chosen = rec["id"] in selected
            is_frozen = is_chosen and rec["id"] in self.frozen_pending
            # An imported RESEARCH_ONLY item is not READY merely because the
            # current catalog now pins it. Never silently upgrade consent.
            state = "RESEARCH_ONLY" if is_frozen else STATES[rec["admission"]]
            if (selected_only and not is_chosen) or (
                    profile_ids is not None and rec["id"] not in profile_ids) or (
                    category != "all" and rec["primary"] != category) or (
                    status != "all" and state != status):
                continue
            if needle and not any(needle in str(rec[k]).casefold()
                                  for k in ("id", "name", "primary")):
                continue
            results.append(dict(rec, status=state, selected=is_chosen,
                                locked_pending=is_frozen))
        return sorted(results, key=lambda x: (x["primary"], x["id"]))

    def _checked_selection(self, ids):
        """Validate a prospective selection before changing the picker state.

        Reuse the saved-kit builder's 256-tool limit and pin checks instead of
        maintaining a second GUI-only limit. Empty in-memory selection is valid.
        """
        if not ids:
            return []
        ordered = kit.requested_ids(ids, [], [], [], self.pins,
                                    self.categories, self.profiles, self.known)
        kit.make_kit("preview", ordered, self.pins, self.known)
        return ordered

    def add(self, ids):
        if not isinstance(ids, (list, tuple)):
            raise kit.KitError("Selections must be a list")
        # Validate all IDs before modifying the selected set.
        for ident in ids:
            if not isinstance(ident, str) or ident not in self.known:
                raise kit.KitError("Unknown tool: " + str(ident))
        if not ids:
            return list(self.selected)
        candidate = list(self.selected)
        for ident in ids:
            if ident not in candidate:
                candidate.append(ident)
        self.selected = self._checked_selection(candidate)
        return list(self.selected)

    def remove(self, ids):
        if not isinstance(ids, (list, tuple)):
            raise kit.KitError("Selections must be a list")
        for ident in ids:
            if not isinstance(ident, str) or ident not in self.known:
                raise kit.KitError("Unknown tool: " + str(ident))
        removed = set(ids)
        self.selected = [x for x in self.selected if x not in removed]
        self.frozen_pending.difference_update(removed)
        self.selected_plugins = [
            p for p in self.selected_plugins
            if self.plugin_catalog[p]["host"] not in removed]
        self.frozen_plugin_choices = {
            k: v for k, v in self.frozen_plugin_choices.items()
            if k in self.selected_plugins}
        return list(self.selected)

    def toggle(self, ids):
        """Toggle one fully validated group, without installer side effects."""
        if not isinstance(ids, (list, tuple)):
            raise kit.KitError("Selections must be a list")
        if any(not isinstance(x, str) or x not in self.known for x in ids):
            raise kit.KitError("Unknown tool in toggle selection")
        unique = list(dict.fromkeys(ids))
        previous = set(self.selected)
        removed = [x for x in unique if x in previous]
        candidate = [x for x in self.selected if x not in removed]
        candidate.extend(x for x in unique if x not in previous)
        # Fail before removing frozen consent or host-dependent plugin choices.
        checked = self._checked_selection(candidate)
        if removed:
            self.remove(removed)
        self.selected = checked
        return list(self.selected)

    def clear(self):
        self.selected = []

        self.frozen_pending.clear()
        self.selected_plugins = []
        self.frozen_plugin_choices.clear()

    def plugin_rows(self, host="all", selected_only=False):
        """Pure UI metadata; never equate a pinned plugin with permission to install.

        Existing imported RESEARCH_ONLY plugin intent remains inert even after
        a newer catalog pins that plugin. This is a display of user selections,
        not an installation plan or enterprise licensing verdict.
        """
        if host != "all" and host not in ("notepad++", "winmerge"):
            raise kit.KitError("Unknown plugin host: " + str(host))
        if not isinstance(selected_only, bool):
            raise kit.KitError("selected_only must be a boolean")
        rows = []
        for ident, info in self.plugin_catalog.items():
            if host != "all" and info["host"] != host:
                continue
            selected = ident in self.selected_plugins
            if selected_only and not selected:
                continue
            status = ("RESEARCH_ONLY" if ident in self.frozen_plugin_choices
                      else info["status"])
            rows.append({
                "id": ident, "name": info["name"], "host": info["host"],
                "status": status, "selected": selected,
                "hostSelected": info["host"] in self.selected,
            })
        return rows

    def add_plugin(self, ident):
        if not isinstance(ident, str) or ident not in self.plugin_catalog:
            raise kit.KitError("Unknown editor plugin: " + str(ident))
        host = self.plugin_catalog[ident]["host"]
        if host not in self.selected or host not in self.pins:
            raise kit.KitError("Select pinned plugin host first: " + host)
        # Imported research-only hosts must not silently gain plugin consent
        # when the current catalog later pins them.
        if host in self.frozen_pending:
            raise kit.KitError("Remove and reselect pending plugin host first: " + host)
        if ident not in self.selected_plugins:
            self.selected_plugins.append(ident)
            # Only a true remove/reselect clears historical research status.
            self.frozen_plugin_choices.pop(ident, None)

    def remove_plugin(self, ident):
        if not isinstance(ident, str) or ident not in self.plugin_catalog:
            raise kit.KitError("Unknown editor plugin: " + str(ident))
        self.selected_plugins = [x for x in self.selected_plugins if x != ident]
        self.frozen_plugin_choices.pop(ident, None)

    def set_approved_only(self):
        # An oversized future catalog must not erase the existing kit first.
        checked = self._checked_selection(
            [x["id"] for x in self.rows(status="READY")])
        self.clear()
        self.selected = checked

    def add_preset(self, profile):
        if not isinstance(profile, str) or profile not in self.profiles:
            raise kit.KitError("Unknown preset: " + str(profile))
        ids = kit.requested_ids([], [profile], [], [], self.pins,
                                self.categories, self.profiles, self.known)
        return self.add(ids)

    def load_existing(self, path):
        # Validate schema, pin locks and user consent boundary first; if it
        # fails, do not replace current selection.
        data = kit.read_kit(path, self.pins, self.known)
        self.selected = list(data["tools"])
        self.frozen_pending = {x for x in data["researchOnly"]
                               if x in self.pins}
        self.selected_plugins = [
            x["id"] for x in data.get("pluginSelections", [])]
        self.frozen_plugin_choices = {
            x["id"]: dict(x) for x in data.get("pluginSelections", [])
            if x["status"] == "RESEARCH_ONLY"}
        return data

    def draft(self, name):
        if not self.selected:
            raise kit.KitError("Select at least one tool before saving")
        output = kit.make_kit(name, list(self.selected), self.pins, self.known,
                              plugins=self.selected_plugins)
        for i, item in enumerate(output.get("pluginSelections", [])):
            previous = self.frozen_plugin_choices.get(item["id"])
            if previous is not None:
                output["pluginSelections"][i] = dict(previous)
        for ident in self.frozen_pending:
            if ident in output["lockedPins"]:
                del output["lockedPins"][ident]
                output["researchOnly"].append(ident)
        # Preserve visual user-selected order even after research stage drift.
        output["researchOnly"] = [x for x in self.selected
                                  if x in output["researchOnly"]]
        return output

    def summary(self):
        temp = self.draft("preview") if self.selected else None
        if temp is None:
            return {"selected": 0, "approved": 0, "pending": 0, "os": 0}
        return {"selected": len(temp["tools"]),
                "approved": len(temp["lockedPins"]),
                "pending": len(temp["researchOnly"]),
                "os": len(temp["osBuiltins"])}

    def inspect_readiness(self, root, archive_dir=None, *, skip_pending=False,
                          budget_mib=None):
        """Inspect the CURRENT unsaved selection with existing read-only engines.

        No save, download, vendor execution or installation. The footprint
        report measures only already-installed managed pinned tool directories,
        never inferred compressed sizes for missing tools or plugins.
        """
        if not isinstance(root, (str, Path)) or not str(root).strip():
            raise kit.KitError("Provide an install root to inspect")
        if archive_dir is not None and (
                not isinstance(archive_dir, (str, Path)) or
                not str(archive_dir).strip()):
            raise kit.KitError("Archive directory must be a path or omitted")
        if type(skip_pending) is not bool:
            raise kit.KitError("skip_pending must be boolean")
        if budget_mib is not None and (type(budget_mib) is not int or budget_mib < 0):
            raise kit.KitError("Budget must be a nonnegative integer MiB")
        saved = self.draft("preview")
        checked = readiness.assess(saved, self.pins, root, archive_dir, skip_pending)
        measured = footprint.audit(saved, root, budget_mib=budget_mib)
        # Both reports inspect managed state at different instants; never
        # combine contradictory snapshots into an apparently valid preview.
        footprint.confirm_readiness_alignment(checked, measured)
        return checked, measured

    def preview_json(self, name):
        """Exact prospective KIT.json text; never create a file or run a tool.

        Save still validates and rebuilds the draft at the moment the user
        explicitly saves. A changed selection after preview changes the output.
        """
        return json.dumps(self.draft(name), indent=2, ensure_ascii=False) + "\n"

    def save(self, name, path):
        # Create-only and mirrored evidence delegated to the source of truth.
        data = self.draft(name)
        kit.save_new(data, path)
        return data


def overview_lines(checked, measured):
    """Explain readiness and *known* installed bytes without guessing sizes."""
    # Preserve the existing GUI missing-footprint error contract first;
    # then verify the full set, ordered IDs, status and root consistently.
    measured_by_id = {row["id"]: row for row in measured["tools"]}
    for item in checked["tools"]:
        if item["id"] not in measured_by_id:
            raise kit.KitError("Missing footprint row for selected pin: " + item["id"])
    footprint.confirm_readiness_alignment(checked, measured)
    selected = (checked["pinnedTotal"] +
                len(checked["researchOnlyExcluded"]) +
                len(checked["osBuiltinsInformational"]))
    lines = [
        "PERSONAL TOOLKIT: " + checked["kitName"],
        "SELECTED TOOLS: " + str(selected),
        "PINNED / INSTALLED / NEED INSTALL: {} / {} / {}".format(
            checked["pinnedTotal"], checked["alreadyInstalled"],
            checked["needInstall"]),
        "RESEARCH ONLY: {}  |  OS BUILT-INS: {}  |  PLUGINS: {}".format(
            len(checked["researchOnlyExcluded"]),
            len(checked["osBuiltinsInformational"]),
            len(checked["editorPluginsExcluded"])),
        "",
        "OFFLINE READINESS: " + checked["outcome"],
        "APPROVED SUBSET ONLY: " + ("YES" if checked["skipPendingConsent"] else "NO"),
        "SOURCE DIRECTORY: " + (checked["archiveDirectory"] or "NOT PROVIDED"),
        "",
        "INSTALLED LOGICAL BYTES (MEASURED ONLY): {:,}".format(
            measured["totalMeasuredLogicalBytes"]),
        "MEASURED PINNED: {}/{}".format(measured["measuredPinned"],
                                       measured["selectedPinned"]),
        "COMPLETE KIT FOOTPRINT: " + ("YES" if measured["complete"] else "NO / UNKNOWN"),
        "BUDGET: " + measured["budgetResult"],
        "NOTICE: This is NOT the total future kit size or NTFS allocated bytes.",
        "",
        "TOOL STATUS / ORIGINAL SOURCE FILE:",
    ]
    for item in checked["tools"]:
        # A partial or mismatched measurement must not be shown as zero bytes.
        count = measured_by_id[item["id"]]["logicalBytes"]
        size = "UNKNOWN" if count is None else "{:,} logical bytes".format(count)
        lines.append("  {}  |  {}  |  {}  |  {}  |  size={}".format(
            item["id"], item["installStatus"], item["sourceStatus"],
            item["originalFilename"], size))
    if checked["researchOnlyExcluded"]:
        lines.append("RESEARCH (NOT INSTALLED): " +
                     ", ".join(checked["researchOnlyExcluded"]))
    if checked["editorPluginsExcluded"]:
        lines.append("EDITOR PLUGINS (NOT INSTALLED HERE): " +
                     ", ".join(checked["editorPluginsExcluded"]))
    if checked["osBuiltinsInformational"]:
        lines.append("OS BUILT-INS (INFORMATION ONLY): " +
                     ", ".join(checked["osBuiltinsInformational"]))
    lines.append("")
    lines.append("BLOCKERS:")
    lines.extend(("  - " + msg) for msg in checked["blockers"])
    if not checked["blockers"]:
        lines.append("  None detected by this local preflight")
    lines.extend([
        "",
        "READINESS IS NOT COMPANY/EDR/LICENSE/REDISTRIBUTION APPROVAL.",
        "READINESS DOES NOT INSTALL OR CERTIFY VENDOR BINARIES.",
        "No downloads, installation, Windows configuration or files written.",
        "Actual installation remains separate: MyToolkit.cmd build --yes.",
    ])
    return lines


def launch():
    """Import Tk lazily: the CLI/tested model works on headless Windows too."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise kit.KitError(
            "Tkinter unavailable; use scripts/MyToolkit.cmd CLI instead") from exc

    model = PickerModel()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise kit.KitError("No interactive desktop/Tk display; use CLI instead") from exc
    root.title("PortaKit  •  Build your personal toolkit")
    root.geometry("1080x740")
    root.minsize(850, 620)
    root.configure(bg="#121e2b")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("PK.Treeview", background="#1b2937", foreground="#f2f6fa",
                    fieldbackground="#1b2937", rowheight=28,
                    font=("Segoe UI", 10), borderwidth=0)
    style.configure("PK.Treeview.Heading", background="#223449",
                    foreground="#edf3f8", font=("Segoe UI Semibold", 10),
                    padding=(6, 8))
    style.map("PK.Treeview", background=[("selected", "#296178")],
              foreground=[("selected", "white")])
    style.configure("PK.TCombobox", padding=5)
    root.option_add("*Font", "Segoe UI 10")

    search = tk.StringVar()
    domain = tk.StringVar(value="all")
    status = tk.StringVar(value="all")
    selected_filter = tk.BooleanVar(value=False)
    profile_filter = tk.StringVar(value="all")
    preset = tk.StringVar(value="essentials")
    name = tk.StringVar(value="my-portable-kit")
    output = tk.StringVar(value=str(Path.cwd() / "MyPortableKit.json"))
    summary_text = tk.StringVar()
    plugin_choice = tk.StringVar(value="compareplus")
    plugin_selected_text = tk.StringVar(value="")
    plugin_choice_text = tk.StringVar(value="")

    frame = tk.Frame(root, bg="#121e2b", padx=22, pady=16)
    frame.pack(fill="both", expand=True)
    title = tk.Label(frame, text="My Portable Toolkit",
                     font=("Segoe UI Semibold", 23), fg="#f1f7fc", bg="#121e2b")
    title.pack(anchor="w")
    subtitle = tk.Label(
        frame, text="Pinned does not mean corporate approval. "
                    "Research remains inert; this window never installs.",
        fg="#abc1cf", bg="#121e2b", font=("Segoe UI", 10))
    subtitle.pack(anchor="w", pady=(3, 8))
    tk.Label(frame, text=("Keyboard: Ctrl+F search | arrows navigate | "
                          "Space/Enter toggle | Ctrl+A highlight visible | "
                          "Delete remove | Ctrl+O import | Ctrl+S save"),
             fg="#d5dfe9", bg="#121e2b", font=("Segoe UI", 9),
             anchor="w").pack(fill="x", pady=(0, 12))

    # Two filter rows avoid the prior single-line crowding at 850px / high DPI.
    filters = tk.Frame(frame, bg="#121e2b")
    filters.pack(fill="x", pady=(0, 10))
    search_row = tk.Frame(filters, bg="#121e2b")
    search_row.pack(fill="x", pady=(0, 5))
    tk.Label(search_row, text="Search name / ID / category", fg="#a9bdc9",
             bg="#121e2b").pack(side="left", padx=(0, 9))
    search_entry = ttk.Entry(search_row, textvariable=search)
    search_entry.pack(side="left", fill="x", expand=True)
    filter_row = tk.Frame(filters, bg="#121e2b")
    filter_row.pack(fill="x")
    ttk.Combobox(filter_row, textvariable=domain, width=24, state="readonly",
                 values=["all"] + list(model.categories)).pack(side="left", padx=(0, 9))
    ttk.Combobox(filter_row, textvariable=status, width=18, state="readonly",
                 values=["all", "READY", "OS_ONLY", "RESEARCH_ONLY"]).pack(
                     side="left", padx=(0, 12))
    ttk.Checkbutton(filter_row, text="Selected only",
                    variable=selected_filter).pack(side="left", padx=(0, 11))
    # This is a VIEW filter only; adding a whole preset remains a separate,
    # explicit button below. Legacy empty aliases are deliberately omitted.
    tk.Label(filter_row, text="Profile (pinned)", fg="#a9bdc9",
             bg="#121e2b").pack(side="left", padx=(0, 5))
    ttk.Combobox(filter_row, textvariable=profile_filter, width=20,
                 state="readonly", values=["all"] + [
                     k for k, v in model.profiles.items() if not v.get("legacy")
                 ]).pack(side="left")

    holder = tk.Frame(frame, bg="#121e2b")
    holder.pack(fill="both", expand=True)
    cols = ("chosen", "id", "name", "category", "status")
    table = ttk.Treeview(holder, columns=cols, show="headings", selectmode="extended",
                         style="PK.Treeview", height=15)
    headings = {"chosen": "✓", "id": "Tool ID", "name": "Tool",
                "category": "Primary domain", "status": "Approval state"}
    widths = {"chosen": 46, "id": 160, "name": 240, "category": 155,
              "status": 165}
    for key in cols:
        table.heading(key, text=headings[key])
        table.column(key, width=widths[key], stretch=key in ("name", "category"),
                     anchor="center" if key == "chosen" else "w")
    table.tag_configure("pending", foreground="#e6ba7b")
    table.tag_configure("ready", foreground="#d8f0e7")
    table.tag_configure("os", foreground="#b9caed")
    bar = ttk.Scrollbar(holder, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=bar.set)
    table.pack(fill="both", expand=True, side="left")
    bar.pack(fill="y", side="right")
    results_text = tk.StringVar(value="")
    tk.Label(frame, textvariable=results_text, fg="#c8d6e2", bg="#121e2b",
             anchor="w", font=("Segoe UI", 9)).pack(fill="x", pady=(5, 0))

    def refresh_plugin_details(*_):
        current = next((row for row in model.plugin_rows()
                        if row["id"] == plugin_choice.get()), None)
        if current:
            state = ("Pinned source metadata only" if current["status"] ==
                     "PINNED_METADATA_ONLY" else "Research only - not approved")
            host = ("remove/reselect pending host"
                    if current["host"] in model.frozen_pending else
                    "host selected" if current["hostSelected"] else
                    "select host first")
            plugin_choice_text.set(
                "{} | {} | {} | {} | no automatic plugin install".format(
                    current["name"], current["host"], state, host))
        else:
            plugin_choice_text.set("Choose an editor plugin. No plugin is installed by this window.")

        chosen = model.plugin_rows(selected_only=True)
        if not chosen:
            plugin_selected_text.set("Selected editor plugins (0): none")
            return
        labels = []
        for row in chosen:
            state = ("PINNED METADATA" if row["status"] ==
                     "PINNED_METADATA_ONLY" else "RESEARCH ONLY")
            labels.append("{} [{}; {}]".format(row["name"], row["host"], state))
        plugin_selected_text.set(
            "Selected editor plugins ({}): {}".format(len(chosen), "  |  ".join(labels)))

    def refresh(*_):
        # Preserve keyboard highlight and focus after selecting tools.
        highlighted = set(table.selection())
        focused = table.focus()
        old_rows = table.get_children()
        if old_rows:
            table.delete(*old_rows)
        visible = model.rows(search.get(), domain.get(), status.get(),
                             selected_only=selected_filter.get(),
                             profile=profile_filter.get())
        for row in visible:
            chosen = "●" if row["selected"] else ""
            st = "PENDING (locked)" if row["locked_pending"] else row["status"]
            tag = ("ready" if row["status"] == "READY" else
                   "os" if row["status"] == "OS_ONLY" else "pending")
            table.insert("", "end", iid=row["id"],
                         values=(chosen, row["id"], row["name"], row["primary"], st),
                         tags=(tag,))
        shown_ids = {row["id"] for row in visible}
        kept = [ident for ident in highlighted if ident in shown_ids]
        if kept:
            table.selection_set(*kept)
        if focused in shown_ids:
            table.focus(focused)
        scope = (str(len(model.selected)) + " selected" if selected_filter.get()
                 else str(len(model.known)) + " known")
        profile_notice = ("" if profile_filter.get() == "all" else
                          " Profile: " + profile_filter.get() + " (pinned only).")
        results_text.set("Showing {} of {} tools; highlighted {}. Filters do not change your kit.{}".format(
            len(visible), scope, len(kept), profile_notice))
        counts = model.summary()
        summary_text.set(("Selected {selected}  •  Pinned {approved}  •  "
                          "Research {pending}  •  OS {os}  •  Plugins {plugins} "
                          "(selection only)").format(
                              **dict(counts, plugins=len(model.selected_plugins))))
        refresh_plugin_details()

    def action(fn):
        try:
            fn()
            refresh()
        except (kit.KitError, kit.sets.ToolsetError, OSError, ValueError) as exc:
            messagebox.showerror("PortaKit", str(exc), parent=root)

    def picked():
        return list(table.selection())

    def toggle_row(_event=None):
        ids = picked()
        if ids:
            action(lambda: model.toggle(ids))
        return "break"

    def highlight_all(_event=None):
        ids = table.get_children()
        if ids:
            table.selection_set(*ids)
            table.focus(ids[0])
        return "break"

    def remove_highlighted(_event=None):
        ids = picked()
        if ids:
            action(lambda: model.remove(ids))
        return "break"

    def clear_highlight(_event=None):
        if table.selection():
            table.selection_remove(*table.selection())
        return "break"

    table.bind("<Double-1>", toggle_row)
    table.bind("<space>", toggle_row)
    table.bind("<Return>", toggle_row)
    table.bind("<Control-a>", highlight_all)
    table.bind("<Delete>", remove_highlighted)
    table.bind("<Escape>", clear_highlight)
    for var in (search, domain, status, selected_filter, profile_filter):
        var.trace_add("write", refresh)
    plugin_choice.trace_add("write", refresh_plugin_details)

    buttons = tk.Frame(frame, bg="#121e2b")
    buttons.pack(fill="x", pady=(12, 7))
    def command(text, callback):
        ttk.Button(buttons, text=text, command=callback).pack(side="left", padx=(0, 8))

    command("Add highlighted", lambda: action(lambda: model.add(picked())))
    command("Remove highlighted", lambda: action(lambda: model.remove(picked())))
    command("Add filtered", lambda: action(
        lambda: model.add([x["id"] for x in model.rows(
            search.get(), domain.get(), status.get(),
            selected_only=selected_filter.get(),
            profile=profile_filter.get())])))
    command("Pinned only", lambda: action(model.set_approved_only))
    command("Clear", lambda: action(model.clear))
    ttk.Combobox(buttons, textvariable=preset, width=17, state="readonly",
                 values=[k for k, v in model.profiles.items()
                         if not v.get("legacy")]).pack(side="left", padx=(8, 7))
    command("Add preset", lambda: action(lambda: model.add_preset(preset.get())))

    plugin_bar = tk.Frame(frame, bg="#121e2b")
    plugin_bar.pack(fill="x", pady=(4, 8))
    tk.Label(plugin_bar, text="Optional editor plugins (not installed):",
             fg="#d2e1ee", bg="#121e2b").pack(side="left", padx=(0, 8))
    plugin_ids = list(model.plugin_catalog)
    ttk.Combobox(plugin_bar, textvariable=plugin_choice, values=plugin_ids,
                 state="readonly", width=21).pack(side="left", padx=(0, 8))
    ttk.Button(plugin_bar, text="Add plugin", command=lambda: action(
        lambda: model.add_plugin(plugin_choice.get()))).pack(side="left", padx=(0, 7))
    ttk.Button(plugin_bar, text="Remove plugin", command=lambda: action(
        lambda: model.remove_plugin(plugin_choice.get()))).pack(side="left", padx=(0, 8))
    tk.Label(plugin_bar, text="Host required; no GUI plugin install",
             fg="#c6aa77", bg="#121e2b").pack(side="left")
    plugin_details = tk.Frame(frame, bg="#121e2b")
    plugin_details.pack(fill="x", pady=(0, 7))
    tk.Label(plugin_details, textvariable=plugin_choice_text,
             fg="#c4d8e8", bg="#121e2b", font=("Segoe UI", 9),
             anchor="w", justify="left").pack(fill="x")
    selected_plugin_label = tk.Label(
        plugin_details, textvariable=plugin_selected_text,
        fg="#a8dfcd", bg="#121e2b", font=("Segoe UI", 9),
        anchor="w", justify="left", wraplength=760)
    selected_plugin_label.pack(fill="x")
    # Responsive wrap for narrow Windows and high DPI, with a safe lower bound.
    plugin_details.bind(
        "<Configure>", lambda event: selected_plugin_label.configure(
            wraplength=max(200, event.width - 24)))

    status_label = tk.Label(frame, textvariable=summary_text, bg="#121e2b",
                            fg="#a8dfcd", font=("Segoe UI Semibold", 11))
    status_label.pack(anchor="w", pady=(7, 12))

    save_row = tk.Frame(frame, bg="#121e2b")
    save_row.pack(fill="x")
    tk.Label(save_row, text="Kit name", bg="#121e2b", fg="#e9f3fa").pack(side="left")
    ttk.Entry(save_row, textvariable=name, width=23).pack(side="left", padx=(7, 13))
    tk.Label(save_row, text="Output JSON", bg="#121e2b",
             fg="#e9f3fa").pack(side="left")
    ttk.Entry(save_row, textvariable=output).pack(side="left", fill="x",
                                                   expand=True, padx=(7, 8))
    ttk.Button(save_row, text="Browse…",
               command=lambda: output.set(
                   filedialog.asksaveasfilename(parent=root, defaultextension=".json",
                                               filetypes=[("JSON kit", "*.json")]) or
                   output.get())).pack(side="left")

    foot = tk.Frame(frame, bg="#121e2b")
    foot.pack(fill="x", pady=(12, 0))
    def save_kit():
        def op():
            saved = model.save(name.get().strip(), output.get())
            messagebox.showinfo("Toolkit saved",
                                "Saved selected IDs: " + str(len(saved["tools"])) +
                                "\n\nPreview without changes:\n"
                                "scripts\\MyToolkit.cmd plan --kit \"" +
                                str(Path(output.get()).absolute()) +
                                "\"\n\nInstallation requires a separate CLI build --yes.",
                                parent=root)
        action(op)

    def import_kit():
        path = filedialog.askopenfilename(parent=root,
                                          filetypes=[("JSON kit", "*.json")])
        if path:
            def op():
                data = model.load_existing(path)
                name.set(data["name"])
            action(op)

    ttk.Button(foot, text="Import existing kit…", command=import_kit).pack(
        side="left", padx=(0, 9))
    ttk.Button(foot, text="Save personal kit + evidence",
               command=save_kit).pack(side="left")

    def preview_kit():
        """Preview current consent and pin snapshot, without any filesystem write."""
        def op():
            payload = model.preview_json(name.get().strip())
            dialog = tk.Toplevel(root)
            dialog.title("PortaKit  •  Proposed KIT.json (read-only)")
            dialog.geometry("820x560")
            dialog.minsize(620, 380)
            dialog.configure(bg="#121e2b")
            panel = tk.Frame(dialog, bg="#121e2b", padx=14, pady=12)
            panel.pack(fill="both", expand=True)
            tk.Label(
                panel,
                text=("Current selection only: no file saved or vendor executed. "
                      "Edit selection/name and preview again before saving."),
                bg="#121e2b", fg="#c8d6e2", anchor="w",
                justify="left", wraplength=760).pack(fill="x", pady=(0, 8))
            frame_json = tk.Frame(panel, bg="#121e2b")
            frame_json.pack(fill="both", expand=True)
            viewer = tk.Text(frame_json, wrap="none", relief="flat",
                             bg="#1b2937", fg="#edf3f8",
                             font=("Consolas", 10), padx=10, pady=10)
            scroll_y = ttk.Scrollbar(frame_json, orient="vertical",
                                     command=viewer.yview)
            scroll_x = ttk.Scrollbar(frame_json, orient="horizontal",
                                     command=viewer.xview)
            viewer.configure(yscrollcommand=scroll_y.set,
                             xscrollcommand=scroll_x.set)
            viewer.grid(row=0, column=0, sticky="nsew")
            scroll_y.grid(row=0, column=1, sticky="ns")
            scroll_x.grid(row=1, column=0, sticky="ew")
            frame_json.grid_rowconfigure(0, weight=1)
            frame_json.grid_columnconfigure(0, weight=1)
            viewer.insert("1.0", payload)
            viewer.configure(state="disabled")
        action(op)

    def open_readiness():
        """User-triggered, read-only dialog; NEVER call any apply or installer."""
        dialog = tk.Toplevel(root)
        dialog.title("PortaKit  •  Readiness / Missing / Size")
        dialog.geometry("900x590")
        dialog.minsize(700, 440)
        dialog.configure(bg="#121e2b")
        panel = tk.Frame(dialog, bg="#121e2b", padx=14, pady=12)
        panel.pack(fill="both", expand=True)
        inspect_root = tk.StringVar(value=str(Path.cwd() / "portable"))
        inspect_archive = tk.StringVar(value="")
        inspect_budget = tk.StringVar(value="")
        inspect_skip = tk.BooleanVar(value=False)
        line = tk.Frame(panel, bg="#121e2b")
        line.pack(fill="x", pady=(0, 6))
        tk.Label(line, text="Install root", bg="#121e2b",
                 fg="#e9f3fa", width=14, anchor="w").pack(side="left")
        ttk.Entry(line, textvariable=inspect_root).pack(side="left", fill="x", expand=True)
        line = tk.Frame(panel, bg="#121e2b")
        line.pack(fill="x", pady=(0, 6))
        tk.Label(line, text="Original archives", bg="#121e2b",
                 fg="#e9f3fa", width=14, anchor="w").pack(side="left")
        ttk.Entry(line, textvariable=inspect_archive).pack(
            side="left", fill="x", expand=True)
        ttk.Button(line, text="Browse…",
                   command=lambda: inspect_archive.set(
                       filedialog.askdirectory(parent=dialog) or inspect_archive.get())).pack(
                           side="left", padx=(5, 0))
        line = tk.Frame(panel, bg="#121e2b")
        line.pack(fill="x", pady=(0, 7))
        tk.Label(line, text="Budget MiB", bg="#121e2b",
                 fg="#e9f3fa", width=14, anchor="w").pack(side="left")
        ttk.Entry(line, textvariable=inspect_budget, width=9).pack(
            side="left", padx=(0, 12))
        ttk.Checkbutton(line, text="Inspect pinned subset (exclude pending)",
                        variable=inspect_skip).pack(side="left")
        content = tk.Frame(panel, bg="#121e2b")
        content.pack(fill="both", expand=True)
        viewer = tk.Text(content, wrap="word", relief="flat",
                         bg="#1b2937", fg="#edf3f8",
                         font=("Consolas", 10), padx=10, pady=10)
        scroll = ttk.Scrollbar(content, orient="vertical", command=viewer.yview)
        viewer.configure(yscrollcommand=scroll.set, state="disabled")
        viewer.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def inspect_now():
            try:
                budget = inspect_budget.get().strip()
                if budget and (not budget.isdecimal()):
                    raise kit.KitError("Budget MiB must be a nonnegative whole number")
                checked, measured = model.inspect_readiness(
                    inspect_root.get(),
                    inspect_archive.get().strip() or None,
                    skip_pending=bool(inspect_skip.get()),
                    budget_mib=int(budget) if budget else None)
                lines = overview_lines(checked, measured)
                viewer.configure(state="normal")
                viewer.delete("1.0", "end")
                viewer.insert("1.0", "\n".join(lines) + "\n")
                viewer.configure(state="disabled")
            except (kit.KitError, kit.sets.ToolsetError,
                    kit.core.PortakitError, readiness.ReadinessError,
                    readiness.assets.AssetError, footprint.FootprintError,
                    OSError, ValueError) as exc:
                messagebox.showerror("Read-only inspection", str(exc), parent=dialog)

        ttk.Button(panel, text="Inspect current selection (read-only)",
                   command=inspect_now).pack(anchor="w", pady=(8, 4))
        tk.Label(panel, text=("No write / download / install. Source SHA and size "
                              "are point-in-time checks; pending items not deployable."),
                 fg="#aec5d2", bg="#121e2b", anchor="w").pack(fill="x")
    ttk.Button(foot, text="Inspect readiness / size…",
               command=open_readiness).pack(side="left", padx=(9, 0))
    # Keep the original footer buttons reachable on a narrow Windows desktop.
    # The extra read-only preview stays in a separate, compact footer row.
    preview_row = tk.Frame(frame, bg="#121e2b")
    preview_row.pack(fill="x", pady=(5, 0))
    ttk.Button(preview_row, text="Preview KIT.json (read-only)",
               command=preview_kit).pack(side="left")
    tk.Label(preview_row, text="No install, download or registry edits",
             bg="#121e2b", fg="#b2c1cc").pack(side="right")
    def focus_search(_event=None):
        search_entry.focus_set()
        search_entry.selection_range(0, "end")
        return "break"

    def save_shortcut(_event=None):
        save_kit()
        return "break"

    def import_shortcut(_event=None):
        import_kit()
        return "break"

    # Global shortcuts do not modify the OS. Ctrl+A/Delete apply to the table only.
    root.bind("<Control-f>", focus_search)
    root.bind("<Control-s>", save_shortcut)
    root.bind("<Control-o>", import_shortcut)
    refresh()
    root.after_idle(search_entry.focus_set)
    root.mainloop()


def main():
    try:
        launch()
        return 0
    except (kit.KitError, kit.sets.ToolsetError, OSError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
