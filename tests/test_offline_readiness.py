"""Windows-only regression for single-command offline personal-kit readiness.

Source collection is user-managed. These tests do not access the Internet,
execute an installer, run vendor binaries or create a production installation.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_offline_readiness", HERE / "scripts" / "offline_assets.py")
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp) / "portable"
        self.saved_path = Path(self.temp) / "kit.json"
        self.out = Path(self.temp) / "ready.json"
        self.sources = Path(self.temp) / "original_sources"
        self.pins, _, _, self.known = assets.kit.inventory()

    def personal(self, *ids, plugins=()):
        return assets.kit.make_kit("my-kit", list(ids), self.pins, self.known,
                                   plugins=list(plugins))

    def check(self, saved, *, archive_dir=None, skip_pending=False):
        return assets.make_readiness(saved, self.pins, self.root,
                                     archive_dir=archive_dir,
                                     skip_pending=skip_pending)

    def save(self, obj):
        with contextlib.redirect_stdout(io.StringIO()):
            assets.kit.save_new(obj, self.saved_path)

    def run(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = assets.run(["check", "--kit", str(self.saved_path),
                             "--root", str(self.root), *args])
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_missing_only_report_and_no_install_root(self):
        report = self.check(self.personal("jq", "duckdb-cli", "cmd"),
                            skip_pending=True)
        self.assertEqual(report["status"], "NEEDS_ARCHIVES")
        self.assertEqual(report["selectedApproved"], 1)
        self.assertEqual(report["alreadyInstalled"], 0)
        self.assertEqual(report["missingApproved"], 1)
        self.assertEqual([x["id"] for x in report["requiredAssets"]], ["jq"])
        self.assertEqual(report["researchOnlyExcluded"], ["duckdb-cli"])
        self.assertEqual(report["osBuiltinsInformational"], ["cmd"])
        self.assertFalse(self.root.exists())
        self.assertFalse(self.sources.exists())

    def test_pending_default_fail_closed_and_explicit_subset(self):
        saved = self.personal("jq", "duckdb-cli")
        self.assertEqual(self.check(saved)["status"], "BLOCKED_PENDING")
        self.assertEqual(self.check(saved, skip_pending=True)["status"],
                         "NEEDS_ARCHIVES")
        self.assertFalse(self.root.exists())

    def test_v2_plugin_choice_remains_excluded_without_implicit_install(self):
        saved = self.personal("notepad++", plugins=["compareplus"])
        denied = self.check(saved)
        self.assertEqual(denied["status"], "BLOCKED_PENDING")
        self.assertEqual(denied["editorPluginsExcluded"], ["compareplus"])
        allowed = self.check(saved, skip_pending=True)
        self.assertEqual(allowed["status"], "NEEDS_ARCHIVES")
        self.assertEqual([x["id"] for x in allowed["requiredAssets"]],
                         ["notepad++"])
        self.assertFalse(self.root.exists())

    def test_managed_matching_install_skips_unneeded_original_archive(self):
        installed = "jq"
        entry = self.pins[installed]
        self.root.mkdir()
        (self.root / entry["dest"]).mkdir()
        (self.root / ".portakit-state.json").write_text(json.dumps({
            installed: {"version": entry["version"],
                        "sha256": entry["sha256"], "dest": entry["dest"]}
        }), encoding="utf-8")
        saved = self.personal("jq", "ripgrep")
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               return_value={"ripgrep": self.sources / "ripgrep.zip"}) as verifier:
            result = self.check(saved, archive_dir=self.sources)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["alreadyInstalled"], 1)
        self.assertEqual(result["missingApproved"], 1)
        self.assertEqual([x["id"] for x in result["requiredAssets"]], ["ripgrep"])
        self.assertEqual([r["id"] for r in verifier.call_args.args[0]], ["ripgrep"])
        self.assertTrue(result["offlineArchivesVerified"])

    def test_all_installed_requires_no_archives_or_source_directory(self):
        entry = self.pins["jq"]
        self.root.mkdir()
        (self.root / entry["dest"]).mkdir()
        (self.root / ".portakit-state.json").write_text(json.dumps({
            "jq": {"version": entry["version"], "sha256": entry["sha256"],
                   "dest": entry["dest"]}
        }), encoding="utf-8")
        with mock.patch.object(assets.kit.sets, "verify_offline_assets") as verifier:
            out = self.check(self.personal("jq"), archive_dir=self.sources)
            verifier.assert_not_called()
        self.assertEqual(out["status"], "READY")
        self.assertEqual(out["missingApproved"], 0)
        self.assertEqual(out["requiredAssets"], [])
        self.assertFalse(self.sources.exists())

    def test_wrong_hash_blocks_and_never_invokes_installer(self):
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               side_effect=assets.kit.sets.ToolsetError(
                                   "SHA mismatch for approved original")):
            with mock.patch.object(assets.kit.sets, "apply",
                                   side_effect=AssertionError("installer invoked")):
                report = self.check(self.personal("jq"),
                                    archive_dir=self.sources)
        self.assertEqual(report["status"], "BLOCKED_ARCHIVES")
        self.assertIn("SHA mismatch", report["archiveError"])
        self.assertFalse(report["offlineArchivesVerified"])
        self.assertFalse(self.root.exists())

    def test_unmanaged_destination_and_separate_prerequisite_block(self):
        self.root.mkdir()
        (self.root / "jq").mkdir()
        blocked = self.check(self.personal("jq"), archive_dir=None)
        self.assertEqual(blocked["status"], "BLOCKED_STATE")
        self.assertIn("jq=blocked-unmanaged", blocked["blockedState"])
        self.assertEqual(self.check(self.personal("7zip"))["status"],
                         "BLOCKED_STATE")

    def test_os_builtin_only_noop_without_archive(self):
        saved = self.personal("cmd")
        with mock.patch.object(assets.kit.sets, "verify_offline_assets") as verifier:
            report = self.check(saved)
            verifier.assert_not_called()
        self.assertEqual(report["status"], "NO_OP")
        self.assertEqual(report["requiredAssets"], [])
        self.assertEqual(report["osBuiltinsInformational"], ["cmd"])
        self.assertFalse(self.root.exists())

    def test_new_only_json_with_byte_identical_console(self):
        report = self.check(self.personal("jq"))
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            assets.output_readiness(report, self.out)
        self.assertEqual(json.loads(self.out.read_text(encoding="utf-8")), report)
        self.assertEqual(buf.getvalue(),
                         self.out.with_suffix(".log").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(assets.AssetError, "exists"):
            assets.output_readiness(report, self.out)
        self.assertFalse(self.root.exists())

    def test_cli_status_exit_and_optional_evidence(self):
        self.save(self.personal("jq", "duckdb-cli"))
        code, printed, errors = self.run()
        self.assertEqual((code, errors), (2, ""))
        self.assertIn("RESULT: BLOCKED_PENDING", printed)
        self.assertFalse(self.out.exists())
        code, printed, errors = self.run("--skip-pending", "--out", str(self.out))
        self.assertEqual((code, errors), (2, ""))
        self.assertIn("RESULT: NEEDS_ARCHIVES", printed)
        self.assertEqual(printed, self.out.with_suffix(".log").read_text("utf-8"))
        self.assertFalse(self.root.exists())
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               return_value={"jq": self.sources / "jq.zip"}):
            code, printed, errors = self.run("--skip-pending",
                                             "--archive-dir", str(self.sources))
        self.assertEqual((code, errors), (0, ""))
        self.assertIn("RESULT: READY", printed)

    def test_tampered_pin_prevents_check_before_archive(self):
        self.save(self.personal("jq"))
        data = json.loads(self.saved_path.read_text("utf-8"))
        data["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.saved_path.write_text(json.dumps(data), encoding="utf-8")
        with mock.patch.object(assets.kit.sets, "verify_offline_assets") as verify:
            code, out, err = self.run("--archive-dir", str(self.sources))
            verify.assert_not_called()
        self.assertEqual(code, 1)
        self.assertIn("PIN_CHANGED", err)
        self.assertFalse(self.root.exists())

    def test_pending_cannot_become_ready_with_verified_hash_without_consent(self):
        saved = self.personal("jq", "duckdb-cli")
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               return_value={"jq": self.sources / "jq.zip"}) as verifier:
            report = self.check(saved, archive_dir=self.sources)
        self.assertEqual(report["status"], "BLOCKED_PENDING")
        self.assertTrue(report["offlineArchivesVerified"])
        self.assertEqual(len(verifier.call_args.args[0]), 1)


if __name__ == "__main__":
    unittest.main()
