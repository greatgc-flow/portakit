"""Headless regression for optional GUI picker; never creates a Tk window.

Works on Windows CI with no display, network, real vendor tools or registry.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_picker", REPO / "scripts" / "toolkit_picker.py")
picker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(picker)


class PickerTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.saved = Path(self.temp) / "personal.json"
        self.model = picker.PickerModel()

    def test_union_and_mece_partition_is_current_not_hardcoded(self):
        rows = self.model.rows()
        self.assertEqual(len(rows), 151)
        self.assertEqual(len({x["id"] for x in rows}), len(rows))
        by_stage = {status: len(self.model.rows(status=status)) for status in
                    ("READY", "OS_ONLY", "RESEARCH_ONLY")}
        self.assertEqual(by_stage, {"READY": 19, "OS_ONLY": 27,
                                    "RESEARCH_ONLY": 105})
        self.assertEqual(set(r["primary"] for r in rows),
                         set(self.model.categories))

    def test_casefold_search_and_domain_search(self):
        found = self.model.rows(search="DuckDB")
        self.assertEqual([x["id"] for x in found], ["duckdb-cli"])
        found = self.model.rows(search="TCP", category="network")
        self.assertIn("tcpview", [x["id"] for x in found])
        self.assertEqual(self.model.rows(search="missing___tool"), [])
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown category"):
            self.model.rows(category="fake")
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown status"):
            self.model.rows(status="INSTALL_ME")

    def test_multiselect_dedup_and_noninstalled_research(self):
        self.model.add(["jq", "jq", "duckdb-cli", "cmd"])
        self.model.add(["jq", "ripgrep"])
        self.assertEqual(self.model.selected, ["jq", "duckdb-cli", "cmd", "ripgrep"])
        self.assertEqual(self.model.summary(),
                         {"selected": 4, "approved": 2, "pending": 1, "os": 1})

    def test_add_preset_and_approved_only(self):
        self.model.add_preset("essentials")
        self.assertEqual(self.model.selected, ["notepad++", "winmerge", "jq"])
        self.model.add_preset("essentials")
        self.assertEqual(len(self.model.selected), 3)
        self.model.set_approved_only()
        self.assertEqual(len(self.model.selected), 19)
        self.assertEqual(self.model.summary()["pending"], 0)
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown preset"):
            self.model.add_preset("no-such-profile")

    def test_remove_clear_empty_and_unknown_rejected(self):
        self.model.add(["jq", "duckdb-cli"])
        self.model.remove(["jq"])
        self.assertEqual(self.model.selected, ["duckdb-cli"])
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.add(["bogus"])
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.remove(["bogus"])
        self.model.clear()
        self.assertEqual(self.model.selected, [])
        with self.assertRaisesRegex(picker.kit.KitError, "Select at least one"):
            self.model.draft("empty")

    def test_7zip_order_and_existing_builder_inheritance(self):
        self.model.add(["7zip", "7zr"])
        self.assertEqual(self.model.selected, ["7zr", "7zip"])
        data = self.model.draft("zip")
        self.assertEqual(list(data["lockedPins"]), ["7zr", "7zip"])

    def test_save_creates_json_and_exact_local_console_evidence(self):
        self.model.add(["jq", "duckdb-cli", "cmd"])
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            created = self.model.save("my-kit", self.saved)
        self.assertEqual(created["tools"], ["jq", "duckdb-cli", "cmd"])
        self.assertEqual(stdout.getvalue(),
                         self.saved.with_suffix(".log").read_text(encoding="utf-8"))
        read_back = picker.kit.read_kit(self.saved, self.model.pins,
                                        self.model.known)
        self.assertEqual(read_back, created)
        with self.assertRaisesRegex(picker.kit.KitError, "already exists"):
            self.model.save("my-kit", self.saved)

    def test_import_tampered_pin_does_not_replace_current_selection(self):
        self.model.add(["jq"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.model.save("my-kit", self.saved)
        self.model.clear()
        self.model.add(["ripgrep"])
        data = json.loads(self.saved.read_text("utf-8"))
        data["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.saved.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(picker.kit.KitError, "PIN_CHANGED"):
            self.model.load_existing(self.saved)
        self.assertEqual(self.model.selected, ["ripgrep"])

    def test_import_pending_frozen_even_if_vendor_later_approved(self):
        self.model.add(["duckdb-cli", "jq"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.model.save("before", self.saved)
        changed = dict(self.model.pins)
        changed["duckdb-cli"] = {"version": "9.9", "sha256": "f" * 64,
                                 "dest": "duckdb-cli"}
        new_known = dict(self.model.known)
        new_known["duckdb-cli"] = {
            "id": "duckdb-cli", "name": "DuckDB CLI",
            "primary": "structured-data", "admission": "PINNED_CATALOG"}
        later = picker.PickerModel(inventories=(
            changed, self.model.categories, self.model.profiles, new_known))
        later.load_existing(self.saved)
        self.assertIn("duckdb-cli", later.frozen_pending)
        self.assertIn("duckdb-cli", later.draft("still-pending")["researchOnly"])
        self.assertNotIn("duckdb-cli", later.draft("still-pending")["lockedPins"])
        later.remove(["duckdb-cli"])
        later.add(["duckdb-cli"])
        self.assertIn("duckdb-cli", later.draft("reselected")["lockedPins"])

    def test_read_only_filter_and_load_have_no_fs_side_effects(self):
        self.model.add(["jq"])
        data = self.model.draft("read-only")
        self.assertEqual(data["lockedPins"]["jq"]["version"],
                         self.model.pins["jq"]["version"])
        self.assertFalse(self.saved.exists())
        self.assertEqual([x["id"] for x in self.model.rows(status="READY")
                          if x["selected"]], ["jq"])

    def test_ui_never_calls_installer_and_does_not_import_tk_until_launch(self):
        import sys
        self.assertNotIn("tkinter", picker.__dict__)
        with mock.patch.object(picker.kit.sets, "apply",
                               side_effect=AssertionError("install unexpectedly invoked")):
            self.model.add(["jq", "duckdb-cli"])
            self.model.draft("safe")
            self.model.rows(status="READY")

    def test_batch_add_fails_without_partial_mutation(self):
        self.model.add(["jq"])
        before = list(self.model.selected)
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.add(["ripgrep", "not-existing"])
        self.assertEqual(self.model.selected, before)

    def test_batch_toggle_preserves_unique_selection(self):
        self.model.add(["jq", "cmd"])
        self.assertEqual(self.model.toggle(["jq", "ripgrep", "ripgrep"]),
                         ["cmd", "ripgrep"])
        self.assertEqual(self.model.toggle(["cmd", "jq"]), ["ripgrep", "jq"])

    def test_batch_toggle_rejects_invalid_ids_atomically(self):
        self.model.add(["jq", "cmd"])
        original = self.model.draft("untouched")
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.toggle(["jq", "not-an-id"])
        self.assertEqual(self.model.draft("untouched"), original)
        with self.assertRaisesRegex(picker.kit.KitError, "Selections must be a list"):
            self.model.toggle(None)

    def test_keyboard_shortcuts_are_ui_only_and_table_local(self):
        script = (REPO / "scripts" / "toolkit_picker.py").read_text(encoding="utf-8")
        import ast
        ast.parse(script)
        for key in ("<Control-f>", "<Control-s>", "<Control-o>",
                    "<Control-a>", "<space>", "<Return>", "<Delete>", "<Escape>"):
            self.assertIn(key, script)
        self.assertIn('table.bind("<Control-a>"', script)
        self.assertIn('table.bind("<Delete>"', script)
        self.assertIn('root.bind("<Control-f>"', script)
        self.assertIn("focused = table.focus()", script)
        self.assertIn("table.selection_set(*kept)", script)
        self.assertNotIn(".apply(", script)

    def test_wizard_source_has_no_executable_install_branch(self):
        import ast
        script = (REPO / "scripts" / "toolkit_picker.py").read_text(encoding="utf-8")
        ast.parse(script)
        self.assertNotIn("subprocess.run(", script)
        self.assertNotIn("shell=True", script)
        self.assertNotIn(".apply(", script)

    def test_keyboard_toggle_preserves_deterministic_membership(self):
        self.model.add(["jq", "ripgrep"])
        self.assertEqual(self.model.toggle(["jq", "duckdb-cli", "jq"]),
                         ["ripgrep", "duckdb-cli"])
        self.assertEqual(self.model.toggle(["duckdb-cli", "jq"]),
                         ["ripgrep", "jq"])
        self.assertEqual(self.model.toggle([]), ["ripgrep", "jq"])

    def test_invalid_multi_add_is_atomic(self):
        self.model.add(["jq"])
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.add(["ripgrep", "nonexistent-tool"])
        self.assertEqual(self.model.selected, ["jq"])

    def test_invalid_keyboard_toggle_is_atomic(self):
        self.model.add(["jq", "duckdb-cli"])
        with self.assertRaisesRegex(picker.kit.KitError, "Unknown tool"):
            self.model.toggle(["jq", "bogus"])
        self.assertEqual(self.model.selected, ["jq", "duckdb-cli"])
        with self.assertRaisesRegex(picker.kit.KitError, "Selections must be"):
            self.model.toggle(None)
        self.assertEqual(self.model.selected, ["jq", "duckdb-cli"])

    def test_keyboard_toggle_host_removes_dependent_plugin_choice(self):
        self.model.add(["notepad++", "jq"])
        self.model.add_plugin("compareplus")
        self.assertIn("compareplus", self.model.selected_plugins)
        self.model.toggle(["notepad++"])
        self.assertNotIn("notepad++", self.model.selected)
        self.assertNotIn("compareplus", self.model.selected_plugins)
        self.model.toggle(["notepad++"])
        self.assertIn("notepad++", self.model.selected)
        self.assertNotIn("compareplus", self.model.selected_plugins)

    def test_keyboard_bindings_and_no_ui_install_path(self):
        script = (REPO / "scripts" / "toolkit_picker.py").read_text(encoding="utf-8")
        for binding in ('table.bind("<space>"', 'table.bind("<Return>"',
                        'table.bind("<Control-a>"', 'table.bind("<Delete>"',
                        'table.bind("<Escape>"', 'root.bind("<Control-f>"',
                        'root.bind("<Control-s>"', 'root.bind("<Control-o>"'):
            self.assertIn(binding, script)
        self.assertIn("root.after_idle(search_entry.focus_set)", script)
        self.assertIn("table.selection_set(*kept)", script)
        self.assertIn("table.focus(focused)", script)
        self.assertNotIn("subprocess.run(", script)
        self.assertNotIn(".apply(", script)


if __name__ == "__main__":
    unittest.main()
