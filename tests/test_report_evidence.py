"""Cross-consumer negative tests for the shared create-only report/evidence pair.

All reports use local synthetic/empty inventory. No vendor assets are loaded,
downloaded, installed, launched or accepted by this test.
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


def module(name):
    spec = importlib.util.spec_from_file_location(
        "report_fixture_" + name, REPO / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ready = module("offline_ready")
foot = module("kit_footprint")
doctor = module("kit_doctor")
health = module("plugin_health")
writer = ready.evidence_io


class ReportEvidenceCrossConsumerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.tmp / "managed-missing"
        pins, _, _, known = ready.kit.inventory()
        saved = ready.kit.make_kit("test-kit", [], pins, known)
        read_report = ready.assess(saved, pins, self.root)
        size_report = foot.audit(saved, self.root)
        doctor_report = doctor.inspect(saved, pins, self.root)
        plugin_report = {
            "kitName": "test-kit",
            "observedAtUtc": "2026-11-01T00:00:00+00:00",
            "plugins": [],
            "locallyHashMatched": 0,
            "selectedPlugins": 0,
            "blocked": 0,
            "unverifiedOrUninstalled": 0,
            "outcome": "INCOMPLETE",
        }
        self.cases = (
            ("readiness", ready.emit, read_report),
            ("footprint", foot.create_report, size_report),
            ("doctor", doctor.emit, doctor_report),
            ("plugin-health", health.emit, plugin_report),
        )

    def test_all_four_consumer_transcripts_are_byte_exact(self):
        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    write(report, dest)
                self.assertEqual(stdout.getvalue(),
                                 dest.with_suffix(".log").read_text("utf-8"))
                self.assertEqual(json.loads(dest.read_text("utf-8")), report)
                self.assertTrue(stdout.getvalue().endswith(
                    "REPORT: " + str(dest) + "\n"))
                self.assertEqual(dest.read_bytes()[-1:], b"\n")

    def test_json_write_error_rolls_back_only_owned_pair_for_all(self):
        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")
                with mock.patch.object(writer.json, "dump",
                                       side_effect=OSError("synthetic disk full")):
                    with self.assertRaisesRegex(OSError, "synthetic disk full"):
                        write(report, dest)
                self.assertFalse(dest.exists())
                self.assertFalse(dest.with_suffix(".log").exists())

    def test_log_write_error_removes_partial_json_and_log_for_all(self):
        def failing_emit(evidence, line):
            evidence.stream.write("partial\n")
            evidence.stream.flush()
            raise OSError("synthetic evidence failure")

        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")
                with mock.patch.object(ready.kit.sets.Evidence, "emit",
                                       new=failing_emit):
                    with self.assertRaisesRegex(OSError, "evidence failure"):
                        write(report, dest)
                self.assertFalse(dest.exists())
                self.assertFalse(dest.with_suffix(".log").exists())

    def test_concurrent_new_json_is_never_deleted_as_own(self):
        original_init = ready.kit.sets.Evidence.__init__
        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")

                def race(evidence, path):
                    dest.write_bytes(b"FOREIGN-REPORT\n")
                    original_init(evidence, path)

                with mock.patch.object(ready.kit.sets.Evidence, "__init__",
                                       new=race):
                    with self.assertRaises(FileExistsError):
                        write(report, dest)
                self.assertEqual(dest.read_bytes(), b"FOREIGN-REPORT\n")
                self.assertFalse(dest.with_suffix(".log").exists())

    def test_replaced_json_is_preserved_on_later_log_failure(self):
        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")

                def replace_then_fail(evidence, line):
                    dest.unlink()
                    dest.write_bytes(b"FOREIGN-REPLACEMENT\n")
                    raise OSError("synthetic replacement race")

                with mock.patch.object(ready.kit.sets.Evidence, "emit",
                                       new=replace_then_fail):
                    with self.assertRaisesRegex(OSError, "replacement race"):
                        write(report, dest)
                self.assertEqual(dest.read_bytes(), b"FOREIGN-REPLACEMENT\n")
                self.assertFalse(dest.with_suffix(".log").exists())

    def test_existing_log_collision_does_not_touch_any_evidence(self):
        for name, write, report in self.cases:
            with self.subTest(name=name):
                dest = self.tmp / (name + ".json")
                log = dest.with_suffix(".log")
                log.write_bytes(b"PRIVATE-DIAGNOSTIC\n")
                with self.assertRaises(Exception) as raised:
                    write(report, dest)
                self.assertIn("exist", str(raised.exception))
                self.assertFalse(dest.exists())
                self.assertEqual(log.read_bytes(), b"PRIVATE-DIAGNOSTIC\n")

    def test_readiness_extension_policy_remains_distinct(self):
        with self.assertRaisesRegex(ready.ReadinessError, "must end in .json"):
            ready.emit(self.cases[0][2], self.tmp / "not-json.txt")
        self.assertFalse((self.tmp / "not-json.txt").exists())

    def test_own_output_cleanup_never_follows_replaced_symlink(self):
        # Windows symlinks may be privilege-disabled. Existing link-protection
        # tests cover reparse/junction behavior; this fixture is optional.
        name, write, report = self.cases[0]
        dest = self.tmp / (name + ".json")
        private = self.tmp / "private.txt"
        private.write_bytes(b"KEEP-PRIVATE")
        def replace_then_fail(evidence, line):
            dest.unlink()
            try:
                dest.symlink_to(private)
            except (OSError, NotImplementedError):
                raise OSError("symlinks unavailable")
            raise OSError("synthetic replaced-link")

        with mock.patch.object(ready.kit.sets.Evidence, "emit",
                               new=replace_then_fail):
            with self.assertRaises(OSError):
                write(report, dest)
        self.assertEqual(private.read_bytes(), b"KEEP-PRIVATE")
        self.assertFalse(dest.with_suffix(".log").exists())


if __name__ == "__main__":
    unittest.main()
