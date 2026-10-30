"""Headless, offline tests of optional picker overview; NO Tk or vendor execution."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_gui_overview", ROOT / "scripts" / "kit_overview.py")
overview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overview)


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp) / "managed_not_created"
        self.archive_dir = Path(self.tmp) / "vendor_sources"
        self.pins, _, _, self.known = overview.ready.kit.inventory()
        self.saved = overview.ready.kit.make_kit(
            "my-kit", ["jq", "duckdb-cli", "cmd"], self.pins, self.known)

    def inspect(self, saved=None, **options):
        return overview.inspect(saved or self.saved, self.pins, self.root, **options)

    def test_missing_original_and_pending_are_visible_without_writing(self):
        result = self.inspect(budget_mib=200)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual((result["pinnedTotal"], result["needInstall"],
                          result["researchCount"], result["osCount"]),
                         (1, 1, 1, 1))
        self.assertEqual(result["tools"][0]["sourceStatus"], "NOT_PROVIDED")
        self.assertIsNone(result["tools"][0]["logicalBytes"])
        self.assertFalse(result["sizeComplete"])
        self.assertEqual(result["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertTrue(any("SOURCE_NOT_PROVIDED" in x for x in result["blockers"]))
        self.assertFalse(self.root.exists())
        self.assertFalse(self.archive_dir.exists())

    def test_unverified_research_never_becomes_ready_from_skip_alone(self):
        result = self.inspect(skip_pending=True, budget_mib=100)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual(result["researchCount"], 1)
        self.assertEqual(result["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertIn("UNKNOWN", "\n".join(overview.format_lines(result)))

    def test_official_original_verified_can_enable_approved_subset(self):
        self.archive_dir.mkdir()
        original = self.archive_dir / overview.ready.assets.original_filename(
            self.pins["jq"]["url"])
        original.write_bytes(b"synthetic-data-only")
        with mock.patch.object(overview.ready.kit.sets, "verify_offline_assets",
                               return_value={"jq": original}) as called:
            result = self.inspect(archive_dir=self.archive_dir, skip_pending=True)
        self.assertEqual(result["outcome"], "READY_APPROVED_SUBSET")
        self.assertEqual(result["tools"][0]["sourceStatus"], "SHA256_PASS")
        self.assertIsNone(result["tools"][0]["logicalBytes"])
        called.assert_called_once()
        self.assertFalse(self.root.exists())

    def test_malformed_or_negative_inputs_fail_before_filesystem(self):
        for options in ({"budget_mib": -1}, {"budget_mib": True},
                        {"skip_pending": None}, {"archive_dir": ""},
                        {"archive_dir": 42}):
            with self.subTest(options=options):
                with self.assertRaises(overview.OverviewError):
                    self.inspect(**options)
        with self.assertRaises(overview.OverviewError):
            overview.inspect([], self.pins, self.root)
        with self.assertRaises(overview.OverviewError):
            overview.inspect(self.saved, None, self.root)
        with self.assertRaises(overview.OverviewError):
            overview.inspect(self.saved, self.pins, "")
        self.assertFalse(self.root.exists())

    def test_v2_plugin_selection_is_excluded_and_never_installed(self):
        saved = overview.ready.kit.make_kit(
            "editor", ["notepad++"], self.pins, self.known,
            plugins=["compareplus"])
        with mock.patch.object(overview.ready.kit.sets, "apply",
                               side_effect=AssertionError("installer invoked")):
            result = self.inspect(saved=saved, skip_pending=True)
        self.assertEqual(result["pluginCount"], 1)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertFalse(result["sizeComplete"])

    def test_only_informational_items_is_noop_when_explicitly_excluded(self):
        saved = overview.ready.kit.make_kit(
            "note", ["cmd", "duckdb-cli"], self.pins, self.known)
        result = self.inspect(saved=saved, skip_pending=True, budget_mib=0)
        self.assertEqual(result["outcome"], "NO_OP")
        self.assertEqual(result["pinnedTotal"], 0)
        self.assertEqual(result["tools"], [])
        self.assertFalse(result["sizeComplete"])
        self.assertEqual(result["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertIn("no pinned tools selected", "\n".join(overview.format_lines(result)))

    def test_existing_managed_pin_is_measured_without_original_archives(self):
        pin = self.pins["jq"]
        self.root.mkdir()
        folder = self.root / pin["dest"]
        folder.mkdir()
        (folder / "synthetic.txt").write_bytes(b"1234567")
        (self.root / ".portakit-state.json").write_text(
            json.dumps({"jq": {"version": pin["version"],
                               "sha256": pin["sha256"], "dest": pin["dest"]}}),
            encoding="utf-8")
        selected = overview.ready.kit.make_kit(
            "installed", ["jq"], self.pins, self.known)
        result = self.inspect(saved=selected, archive_dir=self.archive_dir,
                              budget_mib=10)
        self.assertEqual(result["outcome"], "NO_OP")
        self.assertEqual(result["alreadyInstalled"], 1)
        self.assertEqual(result["needInstall"], 0)
        self.assertEqual(result["measuredLogicalBytes"], 7)
        self.assertEqual(result["budgetResult"], "PASS")
        self.assertEqual(result["tools"][0]["logicalBytes"], 7)
        self.assertFalse(self.archive_dir.exists())

    def test_over_budget_is_diagnostic_not_install_permission(self):
        pin = self.pins["jq"]
        self.root.mkdir()
        folder = self.root / pin["dest"]
        folder.mkdir()
        (folder / "one-byte.txt").write_bytes(b"1")
        (self.root / ".portakit-state.json").write_text(
            json.dumps({"jq": {"version": pin["version"],
                               "sha256": pin["sha256"], "dest": pin["dest"]}}),
            encoding="utf-8")
        saved = overview.ready.kit.make_kit(
            "tiny", ["jq"], self.pins, self.known)
        data = self.inspect(saved=saved, budget_mib=0)
        self.assertEqual(data["budgetResult"], "OVER_BUDGET")
        self.assertEqual(data["outcome"], "NO_OP")

    def test_format_lists_blockers_and_immutable_source_notes(self):
        report = self.inspect()
        lines = overview.format_lines(report)
        self.assertTrue(any("BLOCKERS / STILL REQUIRED" in x for x in lines))
        self.assertTrue(any("ORIGINAL FILE" in x for x in lines))
        self.assertTrue(any("corporate" in x for x in lines))
        self.assertTrue(any("No downloads" in x for x in lines))
        with self.assertRaises(overview.OverviewError):
            overview.format_lines(None)

    def test_source_boundary_gui_requires_explicit_click(self):
        path = ROOT / "scripts" / "toolkit_picker.py"
        gui = path.read_text("utf-8")
        impl = (ROOT / "scripts" / "kit_overview.py").read_text("utf-8")
        ast.parse(gui)
        ast.parse(impl)
        self.assertIn("def open_readonly_overview():", gui)
        self.assertIn("def inspect_current():", gui)
        self.assertIn("command=inspect_current", gui)
        self.assertIn("import kit_overview as overview", gui)
        self.assertIn("overview.inspect(", gui)
        self.assertNotIn(".apply(", gui)
        self.assertNotIn("subprocess.run(", gui)
        self.assertNotIn(".apply(", impl)
        self.assertNotIn("subprocess.run(", impl)


if __name__ == "__main__":
    unittest.main()
