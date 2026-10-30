"""KitDoctor aggregate gates: no network, install or false full-kit PASS."""
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
    "portakit_kit_doctor", REPO / "scripts" / "kit_doctor.py")
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp) / "managed"
        self.path = Path(self.tmp) / "my-kit.json"
        self.output = Path(self.tmp) / "doctor.json"
        self.pins, _, _, self.known = doctor.kit.inventory()

    def saved(self, *ids, plugins=()):
        return doctor.kit.make_kit(
            "small-kit", list(ids), self.pins, self.known, plugins=plugins)

    def install(self, ident="jq", size=5):
        pin = self.pins[ident]
        folder = self.root / pin["dest"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "example.bin").write_bytes(b"x" * size)
        doctor.kit.core.write_state(
            self.root, {ident: {k: pin[k] for k in ("version", "sha256", "dest")}})
        return folder

    def save(self, value):
        with contextlib.redirect_stdout(io.StringIO()):
            doctor.kit.save_new(value, self.path)

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = doctor.run(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_uninstalled_pin_and_missing_originals_block_no_writes(self):
        report = doctor.inspect(self.saved("jq"), self.pins, self.root)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["offlineReadiness"]["needInstall"], 1)
        self.assertEqual(report["installedFootprint"]["measuredPinned"], 0)
        self.assertFalse(self.root.exists())
        self.assertFalse(self.output.exists())

    def test_installed_exact_pin_passes_without_source_folder(self):
        self.install()
        data = doctor.inspect(self.saved("jq"), self.pins, self.root,
                              archive_dir=Path(self.tmp) / "not-present", max_mib=1)
        self.assertEqual(data["outcome"], "LOCAL_CHECKS_PASS")
        self.assertEqual(data["offlineReadiness"]["outcome"], "NO_OP")
        self.assertEqual(data["installedFootprint"]["totalMeasuredLogicalBytes"], 5)
        self.assertEqual(data["installedFootprint"]["budgetResult"], "PASS")

    def test_unknown_research_and_os_stay_incomplete_despite_skip(self):
        self.install()
        data = doctor.inspect(
            self.saved("jq", "cmd", "duckdb-cli"), self.pins, self.root,
            skip_pending=True, max_mib=10)
        self.assertEqual(data["offlineReadiness"]["outcome"], "NO_OP")
        self.assertEqual(data["outcome"], "INCOMPLETE")
        self.assertEqual(data["installedFootprint"]["budgetResult"],
                         "UNKNOWN_INCOMPLETE")

    def test_pending_only_has_no_false_zero_size_pass(self):
        data = doctor.inspect(self.saved("duckdb-cli"), self.pins,
                              self.root, skip_pending=True, max_mib=0)
        self.assertEqual(data["outcome"], "INCOMPLETE")
        self.assertEqual(data["installedFootprint"]["selectedPinned"], 0)
        self.assertEqual(data["installedFootprint"]["budgetResult"],
                         "UNKNOWN_INCOMPLETE")

    def test_budget_over_limit_blocks_already_installed(self):
        self.install(size=20)
        data = doctor.inspect(self.saved("jq"), self.pins,
                              self.root, max_mib=0)
        self.assertEqual(data["outcome"], "BLOCKED")
        self.assertEqual(data["installedFootprint"]["budgetResult"], "OVER_BUDGET")

    def test_editor_plugin_status_is_separate_and_not_full_pass(self):
        data = self.saved("notepad++", plugins=("csvlint-npp",))
        report = doctor.inspect(data, self.pins, self.root, skip_pending=True)
        self.assertIsNotNone(report["pluginHealth"])
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertTrue(report["installedFootprint"]["editorPluginsNotMeasured"])
        self.assertEqual(report["pluginHealth"]["outcome"], "INCOMPLETE")

    def test_reject_invalid_input_types_and_readiness_mismatch(self):
        with self.assertRaises(doctor.DoctorError):
            doctor.inspect(None, self.pins, self.root)
        with self.assertRaises(doctor.DoctorError):
            doctor.inspect(self.saved("jq"), self.pins, self.root, max_mib=True)
        with self.assertRaises(doctor.DoctorError):
            doctor.inspect(self.saved("jq"), self.pins, self.root, skip_pending=1)
        self.install()
        with mock.patch.object(doctor.sizes, "audit", return_value={
                "tools": [{"id": "wrong"}]}):
            with self.assertRaisesRegex(doctor.DoctorError, "ID mismatch"):
                doctor.inspect(self.saved("jq"), self.pins, self.root)

    def test_report_writes_new_only_and_console_mirrors_log(self):
        self.install()
        report = doctor.inspect(self.saved("jq"), self.pins, self.root)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            doctor.emit(report, self.output)
        self.assertEqual(stream.getvalue(),
                         self.output.with_suffix(".log").read_text("utf-8"))
        self.assertEqual(json.loads(self.output.read_text("utf-8")), report)
        with self.assertRaisesRegex(doctor.DoctorError, "already exists"):
            doctor.emit(report, self.output)

    def test_missing_log_collision_has_no_overwrite(self):
        self.install()
        prior = self.output.with_suffix(".log")
        prior.write_text("private", "utf-8")
        report = doctor.inspect(self.saved("jq"), self.pins, self.root)
        with self.assertRaises(doctor.DoctorError):
            doctor.emit(report, self.output)
        self.assertEqual(prior.read_text("utf-8"), "private")
        self.assertFalse(self.output.exists())

    def test_cli_success_incomplete_and_tampered_pin(self):
        self.install()
        self.save(self.saved("jq"))
        code, out, err = self.call("--kit", str(self.path), "--root",
                                   str(self.root), "--max-mib", "1")
        self.assertEqual(code, 0)
        self.assertIn("OVERALL RESULT: LOCAL_CHECKS_PASS", out)
        self.assertEqual(err, "")
        code, out, _ = self.call("--kit", str(self.path), "--root",
                                 str(self.root), "--max-mib", "0")
        self.assertEqual(code, 2)
        self.assertIn("OVERALL RESULT: BLOCKED", out)
        record = json.loads(self.path.read_text("utf-8"))
        record["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.path.write_text(json.dumps(record), encoding="utf-8")
        code, _, err = self.call("--kit", str(self.path), "--root", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("PIN_CHANGED", err)

    def test_no_engine_install_download_vendor_execution_or_output_by_default(self):
        self.install()
        with mock.patch.object(doctor.kit.sets, "apply",
                               side_effect=AssertionError("install called")):
            with mock.patch.object(doctor.kit.core, "download",
                                   side_effect=AssertionError("download called")):
                with contextlib.redirect_stdout(io.StringIO()):
                    doctor.emit(doctor.inspect(self.saved("jq"), self.pins, self.root))
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
