"""Tests for read-only logical footprint and fail-closed size budgets."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("kit_footprint",
                                              ROOT / "scripts" / "kit_footprint.py")
foot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(foot)


class FootprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp) / "portable"
        self.saved_path = Path(self.tmp) / "kit.json"
        self.report = Path(self.tmp) / "my-audit.json"
        self.pins, _, _, self.known = foot.kit.inventory()

    def saved(self, *ids):
        return foot.kit.make_kit("my-kit", list(ids), self.pins, self.known)

    def install_fixture(self, ident="jq", size=8):
        self.root.mkdir(parents=True, exist_ok=True)
        pin = self.pins[ident]
        dest = self.root / pin["dest"]
        (dest / "sub").mkdir(parents=True)
        (dest / "a.bin").write_bytes(b"a" * size)
        (dest / "sub" / "b.txt").write_bytes(b"bc")
        foot.kit.core.write_state(self.root, {
            ident: {k: pin[k] for k in ("version", "sha256", "dest")}
        })
        return dest

    def test_missing_root_read_only_and_unknown_budget(self):
        data = foot.audit(self.saved("jq"), self.root, budget_mib=1)
        self.assertEqual(data["tools"][0]["status"], "install")
        self.assertIsNone(data["tools"][0]["logicalBytes"])
        self.assertEqual(data["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertFalse(data["complete"])
        self.assertFalse(self.root.exists())

    def test_measured_nested_tree_exact_file_bytes(self):
        self.install_fixture(size=10)
        d = foot.audit(self.saved("jq"), self.root, budget_mib=1)
        self.assertEqual(d["totalMeasuredLogicalBytes"], 12)
        self.assertEqual((d["tools"][0]["files"], d["tools"][0]["directories"]),
                         (2, 1))
        self.assertEqual(d["measurement"], "LOGICAL_FILE_BYTES_NOT_ALLOCATED_DISK_BYTES")
        self.assertTrue(d["complete"])
        self.assertEqual(d["budgetResult"], "PASS")

    def test_budget_exact_zero_over_and_negative(self):
        self.install_fixture(size=0)
        equal = foot.audit(self.saved("jq"), self.root, budget_mib=0)
        self.assertEqual(equal["budgetResult"], "OVER_BUDGET")
        with self.assertRaisesRegex(foot.FootprintError, "nonnegative"):
            foot.audit(self.saved("jq"), self.root, budget_mib=-1)
        with self.assertRaisesRegex(foot.FootprintError, "nonnegative"):
            foot.audit(self.saved("jq"), self.root, budget_mib=True)

    def test_oversize_and_depth_bounds(self):
        self.install_fixture(size=1)
        with mock.patch.object(foot, "MAX_ENTRIES", 2):
            with self.assertRaisesRegex(foot.FootprintError, "Entry count limit"):
                foot.audit(self.saved("jq"), self.root)
        with mock.patch.object(foot, "MAX_DEPTH", 0):
            with self.assertRaisesRegex(foot.FootprintError, "depth limit"):
                foot.audit(self.saved("jq"), self.root)

    def test_reparse_inside_installed_tree_rejected(self):
        dest = self.install_fixture()
        target = Path(self.tmp) / "sensitive"
        target.mkdir()
        (target / "private.txt").write_text("secret")
        link = dest / "external"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Test environment does not permit symlink creation")
        with self.assertRaisesRegex(foot.FootprintError, "Reparse path"):
            foot.audit(self.saved("jq"), self.root)
        self.assertTrue((target / "private.txt").is_file())

    def test_stale_pin_and_unmanaged_install_are_not_measured(self):
        dest = self.root / self.pins["jq"]["dest"]
        dest.mkdir(parents=True)
        (dest / "not-managed.txt").write_text("data")
        data = foot.audit(self.saved("jq"), self.root)
        self.assertEqual(data["tools"][0]["status"], "blocked-unmanaged")
        self.assertEqual(data["measuredPinned"], 0)
        self.assertEqual(data["totalMeasuredLogicalBytes"], 0)
        self.assertFalse(data["complete"])

    def test_missing_builtins_and_research_cannot_prove_budget(self):
        self.install_fixture()
        d = foot.audit(self.saved("jq", "duckdb-cli", "cmd"),
                       self.root, budget_mib=1024)
        self.assertEqual(d["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertEqual(d["researchOnlyNotMeasured"], ["duckdb-cli"])
        self.assertEqual(d["osBuiltinsNotMeasured"], ["cmd"])
        self.assertEqual(d["measuredPinned"], 1)

    def test_create_new_json_and_exact_console_log(self):
        self.install_fixture()
        data = foot.audit(self.saved("jq"), self.root)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            foot.create_report(data, self.report)
        self.assertEqual(output.getvalue(),
                         self.report.with_suffix(".log").read_text("utf-8"))
        self.assertEqual(json.loads(self.report.read_text("utf-8")), data)
        with self.assertRaisesRegex(foot.FootprintError, "already exists"):
            foot.create_report(data, self.report)

    def test_cli_read_only_no_out_and_invalid_saved_pin(self):
        self.install_fixture()
        with contextlib.redirect_stdout(io.StringIO()):
            foot.kit.save_new(self.saved("jq"), self.saved_path)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(foot.run(["--kit", str(self.saved_path),
                                       "--root", str(self.root), "--max-mib", "1"]), 0)
        self.assertIn("BUDGET RESULT: PASS", output.getvalue())
        self.assertFalse(self.report.exists())
        data = json.loads(self.saved_path.read_text("utf-8"))
        data["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.saved_path.write_text(json.dumps(data), "utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(foot.run(["--kit", str(self.saved_path),
                                       "--root", str(self.root)]), 1)
        self.assertIn("PIN_CHANGED", error.getvalue())

    def test_empty_selected_research_case_returns_unmeasured(self):
        data = foot.audit(self.saved("cmd", "duckdb-cli"),
                          self.root, budget_mib=1)
        self.assertEqual(data["selectedPinned"], 0)
        self.assertEqual(data["measuredPinned"], 0)
        self.assertEqual(data["budgetResult"], "UNKNOWN_INCOMPLETE")
        self.assertEqual(data["tools"], [])

    def test_no_network_or_installer_called(self):
        self.install_fixture()
        with mock.patch.object(foot.kit.sets, "apply",
                               side_effect=AssertionError("install invoked")):
            with mock.patch.object(foot.kit.core, "download",
                                   side_effect=AssertionError("download invoked")):
                self.assertTrue(foot.audit(self.saved("jq"), self.root)["complete"])


if __name__ == "__main__":
    unittest.main()
