"""Headless Tk-independent GUI readiness inspection regression.

Runs only local reads and synthetic catalog fixtures. No vendor execution or
installation, GUI window, downloader, service, registry, network probe.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_picker_readiness", REPO / "scripts" / "toolkit_picker.py")
picker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(picker)


class GuiReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp) / "notinstalled"
        self.sources = Path(self.temp) / "sources"
        self.sources.mkdir()
        self.model = picker.PickerModel()

    def inspect(self, folder=None, skip=False, budget=None):
        return self.model.inspect_readiness(
            self.root, folder, skip_pending=skip, budget_mib=budget)

    def test_empty_kit_fails_without_root_or_report_creation(self):
        with self.assertRaisesRegex(picker.kit.KitError, "Select at least one"):
            self.inspect()
        self.assertFalse(self.root.exists())

    def test_one_pinned_missing_source_is_blocked_with_unknown_size(self):
        self.model.add(["jq"])
        readiness, measured = self.inspect(budget=100)
        self.assertEqual(readiness["outcome"], "BLOCKED")
        self.assertEqual(readiness["needInstall"], 1)
        self.assertEqual(readiness["tools"][0]["sourceStatus"], "NOT_PROVIDED")
        self.assertEqual(measured["measuredPinned"], 0)
        self.assertEqual(measured["totalMeasuredLogicalBytes"], 0)
        self.assertEqual(measured["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertFalse(self.root.exists())
        lines = picker.overview_lines(readiness, measured)
        self.assertTrue(any("SOURCE_NOT_PROVIDED" in x for x in lines))
        self.assertTrue(any("NOT the total future kit size" in x for x in lines))

    def test_research_builtins_and_editor_plugins_are_separate(self):
        self.model.add(["notepad++", "duckdb-cli", "cmd"])
        self.model.add_plugin("compareplus")
        checked, measured = self.inspect(skip=True)
        self.assertEqual(checked["researchOnlyExcluded"], ["duckdb-cli"])
        self.assertEqual(checked["osBuiltinsInformational"], ["cmd"])
        self.assertEqual(checked["editorPluginsExcluded"], ["compareplus"])
        self.assertEqual(checked["outcome"], "BLOCKED")  # host archive missing
        self.assertFalse(measured["complete"])
        text = "\n".join(picker.overview_lines(checked, measured))
        self.assertIn("EDITOR PLUGINS (NOT INSTALLED HERE)", text)
        self.assertIn("RESEARCH (NOT INSTALLED)", text)
        self.assertIn("OS BUILT-INS (INFORMATION ONLY)", text)
        self.assertIn("APPROVED SUBSET ONLY: YES", text)
        self.assertFalse(self.root.exists())

    def test_metadata_only_kit_can_noop_with_subset_opt_in(self):
        self.model.add(["duckdb-cli", "cmd"])
        checked, measured = self.inspect(skip=True)
        self.assertEqual(checked["outcome"], "NO_OP")
        self.assertEqual(checked["tools"], [])
        self.assertEqual(measured["measuredPinned"], 0)
        self.assertFalse(measured["complete"])
        self.assertFalse(self.root.exists())

    def test_pending_without_subset_opt_in_is_blocked(self):
        self.model.add(["duckdb-cli", "cmd"])
        checked, _ = self.inspect()
        self.assertEqual(checked["outcome"], "BLOCKED")
        self.assertTrue(any("RESEARCH_ONLY selected" in x for x in checked["blockers"]))

    def test_bad_input_fails_before_inspection(self):
        self.model.add(["jq"])
        for kwargs in (
            {"root": ""},
            {"root": None},
            {"root": self.root, "archive_dir": ""},
            {"root": self.root, "skip_pending": None},
            {"root": self.root, "budget_mib": -1},
            {"root": self.root, "budget_mib": 1.2},
            {"root": self.root, "budget_mib": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(picker.kit.KitError):
                    self.model.inspect_readiness(**kwargs)
        self.assertFalse(self.root.exists())

    def test_sha_verified_original_source_delegates_existing_engine(self):
        self.model.add(["jq"])
        name = picker.readiness.assets.original_filename(self.model.pins["jq"]["url"])
        (self.sources / name).write_bytes(b"synthetic bytes")
        with mock.patch.object(picker.kit.sets, "verify_offline_assets",
                               return_value={"jq": self.sources / name}) as verify:
            checked, measured = self.inspect(folder=self.sources, budget=10)
        self.assertEqual(checked["outcome"], "READY")
        self.assertEqual(checked["tools"][0]["sourceStatus"], "SHA256_PASS")
        self.assertEqual(measured["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertEqual([r["id"] for r in verify.call_args.args[0]], ["jq"])
        self.assertFalse(self.root.exists())

    def test_no_implicit_vendor_or_os_actions(self):
        self.model.add(["jq"])
        with mock.patch.object(picker.kit.sets, "apply",
                               side_effect=AssertionError("unexpected installer call")):
            with mock.patch.object(picker.kit.core, "install",
                                   create=True,
                                   side_effect=AssertionError("unexpected core install")):
                checked, measured = self.inspect()
        self.assertEqual(checked["outcome"], "BLOCKED")
        self.assertFalse(self.root.exists())

    def test_summary_formatter_handles_no_blockers_and_measured_bytes(self):
        self.model.add(["jq"])
        checked, measured = self.inspect()
        checked["blockers"] = []
        checked["outcome"] = "NO_OP"
        checked["alreadyInstalled"] = 1
        checked["needInstall"] = 0
        measured["totalMeasuredLogicalBytes"] = 1234567
        measured["measuredPinned"] = 1
        measured["complete"] = True
        measured["budgetResult"] = "PASS"
        text = "\n".join(picker.overview_lines(checked, measured))
        self.assertIn("1,234,567", text)
        self.assertIn("None detected by this local preflight", text)
        self.assertIn("BUDGET: PASS", text)
        self.assertIn("READINESS IS NOT COMPANY", text)

    def test_inspection_does_not_save_draft_or_upgrade_research(self):
        self.model.add(["notepad++", "duckdb-cli"])
        self.model.add_plugin("compareplus")
        self.model.frozen_plugin_choices["compareplus"] = {
            "id": "compareplus", "host": "notepad++",
            "status": "RESEARCH_ONLY", "lockedPin": None}
        original = self.model.draft("preview")
        self.inspect(skip=True)
        self.assertEqual(self.model.draft("preview"), original)
        self.assertFalse(self.root.exists())

    def test_gui_does_not_include_any_install_button_or_subprocess(self):
        script = (REPO / "scripts" / "toolkit_picker.py").read_text(encoding="utf-8")
        self.assertIn('command=open_readiness', script)
        self.assertIn("model.inspect_readiness(", script)
        self.assertIn("footprint.audit(", script)
        self.assertIn("readiness.assess(", script)
        self.assertNotIn("subprocess.run(", script)
        self.assertNotIn(".apply(", script)
        import ast
        ast.parse(script)


if __name__ == "__main__":
    unittest.main()
