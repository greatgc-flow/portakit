"""Optional, zero-download Tkinter personal toolkit picker (Windows Python 3.11+).

The pure PickerModel is independently unit-testable without Tk/display.
UI can browse, filter, select, inspect/import, and SAVE inert personal kit JSON.
It deliberately has NO installation, update, uninstall, driver, service, shell
or network actions: use existing my_toolkit.py build --yes separately.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402


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

    def rows(self, search="", category="all", status="all"):
        if not isinstance(search, str):
            raise kit.KitError("Search must be text")
        if category != "all" and category not in self.categories:
            raise kit.KitError("Unknown category: " + str(category))
        if status not in ("all", "READY", "OS_ONLY", "RESEARCH_ONLY"):
            raise kit.KitError("Unknown status: " + str(status))
        needle = search.casefold().strip()
        results = []
        for rec in self.known.values():
            state = STATES[rec["admission"]]
            if (category != "all" and rec["primary"] != category) or (
                    status != "all" and state != status):
                continue
            if needle and not any(needle in str(rec[k]).casefold()
                                  for k in ("id", "name", "primary")):
                continue
            results.append(dict(rec, status=state, selected=rec["id"] in self.selected,
                                locked_pending=rec["id"] in self.frozen_pending))
        return sorted(results, key=lambda x: (x["primary"], x["id"]))

    def add(self, ids):
        if not isinstance(ids, (list, tuple)):
            raise kit.KitError("Selections must be a list")
        if not ids:
            return list(self.selected)
        for ident in ids:
            if not isinstance(ident, str) or ident not in self.known:
                raise kit.KitError("Unknown tool: " + str(ident))
            if ident not in self.selected:
                self.selected.append(ident)
        # 7zr is the manually selected prerequisite for 7zip. Existing
        # builder is still responsible for validating installed state.
        self.selected = kit.requested_ids(self.selected, [], [], [],
                                          self.pins, self.categories,
                                          self.profiles, self.known)
        return list(self.selected)

    def remove(self, ids):
        if not isinstance(ids, (list, tuple)):
            raise kit.KitError("Selections must be a list")
        for ident in ids:
            if ident not in self.known:
                raise kit.KitError("Unknown tool: " + str(ident))
        removed = set(ids)
        self.selected = [x for x in self.selected if x not in removed]
        self.frozen_pending.difference_update(removed)
        return list(self.selected)

    def clear(self):
        self.selected = []
        self.frozen_pending.clear()

    def set_approved_only(self):
        self.clear()
        self.add([x["id"] for x in self.rows(status="READY")])

    def add_preset(self, profile):
        if profile not in self.profiles:
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
        return data

    def draft(self, name):
        if not self.selected:
            raise kit.KitError("Select at least one tool before saving")
        output = kit.make_kit(name, list(self.selected), self.pins, self.known)
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

    def save(self, name, path):
        # Create-only and mirrored evidence delegated to the source of truth.
        data = self.draft(name)
        kit.save_new(data, path)
        return data


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
    preset = tk.StringVar(value="essentials")
    name = tk.StringVar(value="my-portable-kit")
    output = tk.StringVar(value=str(Path.cwd() / "MyPortableKit.json"))
    summary_text = tk.StringVar()

    frame = tk.Frame(root, bg="#121e2b", padx=22, pady=16)
    frame.pack(fill="both", expand=True)
    title = tk.Label(frame, text="My Portable Toolkit",
                     font=("Segoe UI Semibold", 23), fg="#f1f7fc", bg="#121e2b")
    title.pack(anchor="w")
    subtitle = tk.Label(
        frame, text="Pick freely. Only verified SHA-pinned apps can be built; "
                    "research entries remain inert. No installations from this window.",
        fg="#abc1cf", bg="#121e2b", font=("Segoe UI", 10))
    subtitle.pack(anchor="w", pady=(3, 16))

    filters = tk.Frame(frame, bg="#121e2b")
    filters.pack(fill="x", pady=(0, 10))
    ttk.Entry(filters, textvariable=search, width=38).pack(side="left", padx=(0, 9))
    ttk.Combobox(filters, textvariable=domain, width=18, state="readonly",
                 values=["all"] + list(model.categories)).pack(side="left", padx=(0, 9))
    ttk.Combobox(filters, textvariable=status, width=17, state="readonly",
                 values=["all", "READY", "OS_ONLY", "RESEARCH_ONLY"]).pack(
                     side="left", padx=(0, 9))
    tk.Label(filters, text="Search name / ID / category", fg="#a9bdc9",
             bg="#121e2b").pack(side="left")

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

    def refresh(*_):
        table.delete(*table.get_children())
        for row in model.rows(search.get(), domain.get(), status.get()):
            chosen = "●" if row["selected"] else ""
            st = "PENDING (locked)" if row["locked_pending"] else row["status"]
            tag = ("ready" if row["status"] == "READY" else
                   "os" if row["status"] == "OS_ONLY" else "pending")
            table.insert("", "end", iid=row["id"],
                         values=(chosen, row["id"], row["name"], row["primary"], st),
                         tags=(tag,))
        counts = model.summary()
        summary_text.set("Selected {selected}   •   Ready {approved}   •   "
                         "Unverified {pending}   •   Windows built-in {os}"
                         .format(**counts))

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
        if not ids:
            return
        def mutation():
            off = [x for x in ids if x in model.selected]
            on = [x for x in ids if x not in model.selected]
            model.remove(off)
            model.add(on)
        action(mutation)

    table.bind("<Double-1>", toggle_row)
    table.bind("<space>", toggle_row)
    for var in (search, domain, status):
        var.trace_add("write", refresh)

    buttons = tk.Frame(frame, bg="#121e2b")
    buttons.pack(fill="x", pady=(12, 7))
    def command(text, callback):
        ttk.Button(buttons, text=text, command=callback).pack(side="left", padx=(0, 8))

    command("Add highlighted", lambda: action(lambda: model.add(picked())))
    command("Remove highlighted", lambda: action(lambda: model.remove(picked())))
    command("Add filtered", lambda: action(
        lambda: model.add([x["id"] for x in model.rows(search.get(), domain.get(),
                                                       status.get())])))
    command("Approved only", lambda: action(model.set_approved_only))
    command("Clear", lambda: action(model.clear))
    ttk.Combobox(buttons, textvariable=preset, width=17, state="readonly",
                 values=[k for k, v in model.profiles.items()
                         if not v.get("legacy")]).pack(side="left", padx=(8, 7))
    command("Add preset", lambda: action(lambda: model.add_preset(preset.get())))

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
    tk.Label(foot, text="No install, download or registry edits",
             bg="#121e2b", fg="#b2c1cc").pack(side="right")
    refresh()
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
