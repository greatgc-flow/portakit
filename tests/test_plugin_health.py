"""Headless, no-network field-health diagnostics for synthetic plugin installs."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portakit_plugin_health",
                                              ROOT / "scripts" / "plugin_health.py")
health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health)


def zip_bytes(rows):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name, payload in rows:
            z.writestr(name, payload)
    return stream.getvalue()


class PluginHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.tmp / "managed-root"
        self.archives = self.tmp / "vendor-archives"
        self.archives.mkdir()
        self.kit_file = self.tmp / "selected-kit.json"
        self.report_file = self.tmp / "health.json"
        pins, _, _, self.known = health.kit.inventory()
        self.pins = copy.deepcopy(pins)
        self.plugin_pin = self.pins["notepad++"]["recommended"]["plugins"][0]
        archive = zip_bytes([("ComparePlus.dll", b"synthetic-only"),
                             ("libs/sqlite.dll", b"synthetic-library")])
        self.plugin_pin["sha256"] = hashlib.sha256(archive).hexdigest()
        name = health.offline.source_assets.original_filename(
            self.plugin_pin["url"])
        (self.archives / name).write_bytes(archive)
        self.saved = health.kit.make_kit(
            "operator-kit", ["notepad++"], self.pins, self.known,
            plugins=["compareplus"])

    def create_host(self):
        host = self.root / "notepad++"
        host.mkdir(parents=True)
        (host / "notepad++.exe").write_bytes(b"synthetic-host")
        p = self.pins["notepad++"]
        health.kit.core.write_state(self.root, {
            "notepad++": {k: p[k] for k in ("version", "sha256", "dest")}})
        return host

    def apply_fixture(self):
        self.create_host()
        with contextlib.redirect_stdout(io.StringIO()):
            with health.kit.sets.Evidence(self.tmp / "install-synthetic.log") as evidence:
                health.offline.apply(self.saved, self.pins, self.root, self.archives,
                                     evidence=evidence)

    def test_no_host_is_blocked_and_does_not_create_root(self):
        result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual(result["plugins"][0]["sourceState"], "blocked-host-install")
        self.assertEqual(result["blocked"], 1)
        self.assertFalse(self.root.exists())

    def test_managed_host_without_selected_plugin_is_incomplete(self):
        self.create_host()
        result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["outcome"], "INCOMPLETE")
        self.assertEqual(result["plugins"][0]["sourceState"], "install")
        self.assertEqual(result["unverifiedOrUninstalled"], 1)

    def test_cli_clean_synthetic_install_exits_zero_without_changes(self):
        self.apply_fixture()
        with contextlib.redirect_stdout(io.StringIO()):
            health.kit.save_new(self.saved, self.kit_file)
        before = health.offline.receipt_path(self.root).read_bytes()
        with mock.patch.object(health.kit, "inventory",
                               return_value=(self.pins, {}, {}, self.known)):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                result = health.run(["--kit", str(self.kit_file),
                                     "--root", str(self.root)])
        self.assertEqual(result, 0)
        self.assertIn("RESULT: LOCAL_HASH_PASS", stdout.getvalue())
        self.assertEqual(health.offline.receipt_path(self.root).read_bytes(), before)

    def test_valid_synthetic_files_pass_only_local_hash_check(self):
        self.apply_fixture()
        result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["outcome"], "LOCAL_HASH_PASS")
        self.assertEqual(result["locallyHashMatched"], 1)
        self.assertEqual(result["blocked"], 0)
        self.assertIn("NOT vendor signature", result["notice"])

    def test_mutated_main_dll_is_blocked_and_unchanged(self):
        self.apply_fixture()
        file = self.root / "notepad++/plugins/ComparePlus/ComparePlus.dll"
        file.write_bytes(b"modified-by-other-program")
        result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual(result["plugins"][0]["sourceState"], "blocked-content-drift")
        self.assertEqual(file.read_bytes(), b"modified-by-other-program")

    def test_old_receipt_blocked_without_automatic_migration(self):
        self.apply_fixture()
        receipts = health.offline.read_receipts(self.root)
        del receipts["notepad++:compareplus"]["fileHashes"]
        health.offline.write_receipts(self.root, receipts)
        before = health.offline.receipt_path(self.root).read_bytes()
        result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["plugins"][0]["sourceState"],
                         "blocked-legacy-unverified")
        self.assertEqual(health.offline.receipt_path(self.root).read_bytes(), before)

    def test_research_only_selection_is_incomplete_without_vendor_download(self):
        pending = health.kit.make_kit(
            "waiting", ["notepad++"], self.pins, self.known,
            plugins=["csvlint-npp"])
        result = health.inspect(pending, self.pins, self.root)
        self.assertEqual(result["outcome"], "INCOMPLETE")
        self.assertEqual(result["plugins"][0]["assessment"],
                         "NOT_APPROVED_FOR_INSTALL")
        self.assertEqual(result["locallyHashMatched"], 0)
        self.assertFalse(self.root.exists())

    def test_mixed_valid_and_research_is_not_global_pass(self):
        self.apply_fixture()
        mixed = health.kit.make_kit(
            "mixed", ["notepad++"], self.pins, self.known,
            plugins=["compareplus", "csvlint-npp"])
        result = health.inspect(mixed, self.pins, self.root)
        self.assertEqual(result["outcome"], "INCOMPLETE")
        self.assertEqual((result["locallyHashMatched"], result["unverifiedOrUninstalled"]),
                         (1, 1))

    def test_bad_receipt_returns_error_and_does_not_modify_file(self):
        self.apply_fixture()
        receipts_file = health.offline.receipt_path(self.root)
        receipts_file.write_text('{"broken": "unsupported"}', "utf-8")
        before = receipts_file.read_bytes()
        with self.assertRaises(health.offline.PluginDeployError):
            health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(receipts_file.read_bytes(), before)

    def test_report_json_and_stdout_are_byte_mirrored(self):
        self.apply_fixture()
        report = health.inspect(self.saved, self.pins, self.root)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            health.emit(report, self.report_file)
        self.assertEqual(stdout.getvalue(),
                         self.report_file.with_suffix(".log").read_text("utf-8"))
        self.assertEqual(json.loads(self.report_file.read_text("utf-8")), report)
        self.assertIn("RESULT: LOCAL_HASH_PASS", stdout.getvalue())

    def test_report_refuses_existing_path_without_overwrite(self):
        report = health.inspect(self.saved, self.pins, self.root)
        self.report_file.write_text("ORIGINAL", "utf-8")
        with self.assertRaisesRegex(health.HealthError, "already exists"):
            health.emit(report, self.report_file)
        self.assertEqual(self.report_file.read_text("utf-8"), "ORIGINAL")
        self.assertFalse(self.report_file.with_suffix(".log").exists())

    def test_report_json_error_rolls_back_only_owned_files(self):
        report = health.inspect(self.saved, self.pins, self.root)
        with mock.patch.object(health.json, "dump",
                               side_effect=OSError("simulated full disk")):
            with self.assertRaisesRegex(OSError, "full disk"):
                health.emit(report, self.report_file)
        self.assertFalse(self.report_file.exists())
        self.assertFalse(self.report_file.with_suffix(".log").exists())

    def test_report_log_error_rolls_back_only_owned_files(self):
        report = health.inspect(self.saved, self.pins, self.root)
        def failed_log(evidence, line):
            evidence.stream.write("partial\n")
            evidence.stream.flush()
            raise OSError("simulated log failure")
        with mock.patch.object(health.kit.sets.Evidence, "emit", new=failed_log):
            with self.assertRaisesRegex(OSError, "log failure"):
                health.emit(report, self.report_file)
        self.assertFalse(self.report_file.exists())
        self.assertFalse(self.report_file.with_suffix(".log").exists())

    def test_concurrent_json_collision_keeps_foreign_evidence(self):
        report = health.inspect(self.saved, self.pins, self.root)
        target = self.report_file
        init = health.kit.sets.Evidence.__init__
        def collided(evidence, path):
            target.write_bytes(b"FOREIGN-REPORT\n")
            init(evidence, path)
        with mock.patch.object(health.kit.sets.Evidence,
                               "__init__", new=collided):
            with self.assertRaises(FileExistsError):
                health.emit(report, target)
        self.assertEqual(target.read_bytes(), b"FOREIGN-REPORT\n")
        self.assertFalse(target.with_suffix(".log").exists())

    def test_replaced_json_during_log_error_is_not_deleted(self):
        report = health.inspect(self.saved, self.pins, self.root)
        target = self.report_file
        def replace_then_fail(evidence, line):
            target.unlink()
            target.write_bytes(b"NEW-OWNER\n")
            raise OSError("simulated output interruption")
        with mock.patch.object(health.kit.sets.Evidence,
                               "emit", new=replace_then_fail):
            with self.assertRaisesRegex(OSError, "output interruption"):
                health.emit(report, target)
        self.assertEqual(target.read_bytes(), b"NEW-OWNER\n")
        self.assertFalse(target.with_suffix(".log").exists())

    def test_existing_health_log_survives_preflight_rejection(self):
        report = health.inspect(self.saved, self.pins, self.root)
        log = self.report_file.with_suffix(".log")
        log.write_bytes(b"PREEXISTING-LOG\n")
        with self.assertRaisesRegex(health.HealthError, "already exists"):
            health.emit(report, self.report_file)
        self.assertEqual(log.read_bytes(), b"PREEXISTING-LOG\n")
        self.assertFalse(self.report_file.exists())

    def test_cli_incomplete_exit_2_and_read_only(self):
        original_pins, _, _, original_known = health.kit.inventory()
        v2 = health.kit.make_kit("public-safe", ["notepad++"], original_pins,
                                 original_known, plugins=["compareplus"])
        with contextlib.redirect_stdout(io.StringIO()):
            health.kit.save_new(v2, self.kit_file)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = health.run(["--kit", str(self.kit_file), "--root", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("RESULT: BLOCKED", stdout.getvalue())
        self.assertFalse(self.root.exists())

    def test_cli_invalid_v1_rejected_with_exit_1(self):
        v1 = health.kit.make_kit("legacy", ["notepad++"], self.pins, self.known)
        with contextlib.redirect_stdout(io.StringIO()):
            health.kit.save_new(v1, self.kit_file)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = health.run(["--kit", str(self.kit_file)])
        self.assertEqual(code, 1)
        self.assertIn("v2", err.getvalue())

    def test_no_vendor_execution_or_installer_actions(self):
        self.apply_fixture()
        with mock.patch.object(health.offline, "apply",
                               side_effect=AssertionError("installation was called")):
            with mock.patch.object(health.kit.core, "download",
                                   side_effect=AssertionError("network was called")):
                result = health.inspect(self.saved, self.pins, self.root)
        self.assertEqual(result["outcome"], "LOCAL_HASH_PASS")


if __name__ == "__main__":
    unittest.main()
