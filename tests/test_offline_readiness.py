"""No-network/no-install Windows regression for one-command offline readiness."""
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
    "portakit_offline_ready", REPO / "scripts" / "offline_ready.py")
ready = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ready)


class OfflineReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp) / "not-created"
        self.archives = Path(self.tmp) / "vendor-originals"
        self.archives.mkdir()
        self.saved_file = Path(self.tmp) / "kit.json"
        self.out = Path(self.tmp) / "check.json"
        self.pins, _, _, self.known = ready.kit.inventory()
        self.kit = ready.kit.make_kit(
            "support", ["jq", "duckdb-cli", "cmd"], self.pins, self.known)

    def assess(self, *, saved=None, folder=None, consent=False):
        return ready.assess(saved or self.kit, self.pins, self.root,
                            folder, consent)

    def write_kit(self, data=None):
        with contextlib.redirect_stdout(io.StringIO()):
            ready.kit.save_new(data or self.kit, self.saved_file)

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ready.run(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_without_archive_dir_lists_missing_originals_and_no_writes(self):
        report = self.assess()
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["needInstall"], 1)
        self.assertEqual(report["tools"][0]["sourceStatus"], "NOT_PROVIDED")
        self.assertEqual(report["researchOnlyExcluded"], ["duckdb-cli"])
        self.assertEqual(report["osBuiltinsInformational"], ["cmd"])
        self.assertFalse(self.root.exists())
        self.assertFalse(self.saved_file.exists())

    def test_missing_archive_and_real_sha_verifier_never_called(self):
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               side_effect=AssertionError("not needed")) as verifier:
            report = self.assess(folder=self.archives, consent=True)
        verifier.assert_not_called()
        self.assertEqual(report["tools"][0]["sourceStatus"], "MISSING")
        self.assertTrue(any("SOURCE_MISSING" in x for x in report["blockers"]))
        self.assertEqual(report["outcome"], "BLOCKED")

    def test_existing_archive_directory_absent_reports_blocker(self):
        path = Path(self.tmp) / "missing"
        report = self.assess(folder=path, consent=True)
        self.assertEqual(report["tools"][0]["sourceStatus"], "MISSING_DIRECTORY")
        self.assertIn("SOURCE_DIRECTORY_MISSING", report["blockers"][0])
        self.assertFalse(path.exists())

    def test_verified_source_still_requires_explicit_pending_consent(self):
        filename = ready.assets.original_filename(self.pins["jq"]["url"])
        (self.archives / filename).write_bytes(b"synthetic-not-vendor")
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               return_value={"jq": self.archives / filename}):
            report = self.assess(folder=self.archives)
        self.assertEqual(report["tools"][0]["sourceStatus"], "SHA256_PASS")
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertTrue(any("RESEARCH_ONLY selected" in x for x in report["blockers"]))
        self.assertFalse(self.root.exists())

    def test_explicit_approved_subset_after_source_verification(self):
        filename = ready.assets.original_filename(self.pins["jq"]["url"])
        (self.archives / filename).write_bytes(b"synthetic-test-only")
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               return_value={"jq": self.archives / filename}) as verify:
            report = self.assess(folder=self.archives, consent=True)
        self.assertEqual(report["outcome"], "READY_APPROVED_SUBSET")
        self.assertTrue(report["skipPendingConsent"])
        self.assertEqual([r["id"] for r in verify.call_args.args[0]], ["jq"])
        self.assertEqual(report["pinnedTotal"], 1)
        self.assertEqual(report["alreadyInstalled"], 0)
        self.assertFalse(self.root.exists())

    def test_wrong_hash_from_pinned_verifier_is_blocked(self):
        filename = ready.assets.original_filename(self.pins["jq"]["url"])
        (self.archives / filename).write_bytes(b"invalid")
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               side_effect=ready.kit.sets.ToolsetError("SHA mismatch")):
            report = self.assess(folder=self.archives, consent=True)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["tools"][0]["sourceStatus"], "BLOCKED_SOURCE")
        self.assertTrue(any("SHA mismatch" in x for x in report["blockers"]))

    def test_verifier_incomplete_result_is_blocked(self):
        filename = ready.assets.original_filename(self.pins["jq"]["url"])
        (self.archives / filename).write_bytes(b"fake")
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               return_value={}):
            report = self.assess(folder=self.archives, consent=True)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["tools"][0]["sourceStatus"], "BLOCKED_SOURCE")

    def test_already_installed_needs_no_archive_directory_or_hash(self):
        item = {"id": "jq", "status": "already-installed"}
        existing = {"root": str(self.root), "tools": [item]}
        with mock.patch.object(ready.kit, "create_plan", return_value=existing):
            with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                                   side_effect=AssertionError("verify not needed")):
                report = self.assess(consent=True)
        self.assertEqual(report["outcome"], "NO_OP")
        self.assertEqual(report["needInstall"], 0)
        self.assertEqual(report["alreadyInstalled"], 1)
        self.assertEqual(report["tools"][0]["sourceStatus"], "NOT_REQUIRED")

    def test_install_blocked_status_never_validates_archives(self):
        item = {"id": "jq", "status": "blocked-backup"}
        mocked_plan = {"root": str(self.root), "tools": [item]}
        with mock.patch.object(ready.kit, "create_plan", return_value=mocked_plan):
            with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                                   side_effect=AssertionError("unexpected")):
                report = self.assess(folder=self.archives, consent=True)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertIn("INSTALL_BLOCKED", " ".join(report["blockers"]))
        self.assertEqual(report["tools"][0]["sourceStatus"], "NOT_REQUIRED")

    def test_prerequisite_7zip_missing_separate_7zr_is_blocked(self):
        saved = ready.kit.make_kit("seven", ["7zip"], self.pins, self.known)
        report = self.assess(saved=saved)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertTrue(any("PREREQUISITE: " in x for x in report["blockers"]))
        self.assertFalse(self.root.exists())

    def test_metadata_only_os_and_research_is_no_op_with_consent(self):
        saved = ready.kit.make_kit("metadata", ["cmd", "duckdb-cli"],
                                   self.pins, self.known)
        report = self.assess(saved=saved, consent=True)
        self.assertEqual(report["outcome"], "NO_OP")
        self.assertEqual(report["tools"], [])
        self.assertEqual(report["pinnedTotal"], 0)
        self.assertEqual(report["researchOnlyExcluded"], ["duckdb-cli"])
        self.assertFalse(self.root.exists())

    def test_v2_plugin_selection_requires_explicit_subset_consent(self):
        saved = ready.kit.make_kit("plugins", ["notepad++"], self.pins,
                                   self.known, plugins=["compareplus"])
        a = self.assess(saved=saved)
        self.assertEqual(a["outcome"], "BLOCKED")
        self.assertEqual(a["editorPluginsExcluded"], ["compareplus"])
        self.assertTrue(any("EDITOR_PLUGINS" in note for note in a["blockers"]))
        filename = ready.assets.original_filename(self.pins["notepad++"]["url"])
        (self.archives / filename).write_bytes(b"fake")
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               return_value={"notepad++": self.archives / filename}):
            b = self.assess(saved=saved, folder=self.archives, consent=True)
        self.assertEqual(b["outcome"], "READY_APPROVED_SUBSET")
        self.assertEqual(b["editorPluginsExcluded"], ["compareplus"])

    def test_no_write_default_cli_and_exit_2_when_incomplete(self):
        self.write_kit()
        rc, stdout, stderr = self.call("--kit", str(self.saved_file),
                                       "--root", str(self.root))
        self.assertEqual((rc, stderr), (2, ""))
        self.assertIn("RESULT: BLOCKED", stdout)
        self.assertIn("SHA256:", stdout)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.root.exists())

    def test_explicit_report_and_log_are_new_only_and_byte_mirrored(self):
        self.write_kit()
        rc, stdout, stderr = self.call("--kit", str(self.saved_file),
                                       "--root", str(self.root), "--out", str(self.out))
        self.assertEqual((rc, stderr), (2, ""))
        self.assertEqual(stdout, self.out.with_suffix(".log").read_text("utf-8"))
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(report["outcome"], "BLOCKED")
        old_bytes = self.out.read_bytes()
        rc2, out2, err2 = self.call("--kit", str(self.saved_file),
                                    "--root", str(self.root), "--out", str(self.out))
        self.assertEqual(rc2, 1)
        self.assertIn("refusing overwrite", err2)
        self.assertEqual(old_bytes, self.out.read_bytes())

    def test_unsupported_report_extension_and_invalid_consent_rejected(self):
        with self.assertRaisesRegex(ready.ReadinessError, ".json"):
            ready.emit(self.assess(), Path(self.tmp) / "bad.log")
        with self.assertRaisesRegex(ready.ReadinessError, "boolean"):
            self.assess(consent=None)

    def test_tampered_saved_pin_is_rejected_before_any_archive_read(self):
        self.write_kit()
        saved = json.loads(self.saved_file.read_text("utf-8"))
        saved["lockedPins"]["jq"]["sha256"] = "f" * 64
        self.saved_file.write_text(json.dumps(saved), encoding="utf-8")
        rc, stdout, stderr = self.call("--kit", str(self.saved_file),
                                       "--archive-dir", str(self.archives))
        self.assertEqual(rc, 1)
        self.assertIn("PIN_CHANGED", stderr)
        self.assertEqual(stdout, "")
        self.assertFalse(self.root.exists())

    def test_no_installer_network_or_execute_path_in_source(self):
        script = (REPO / "scripts" / "offline_ready.py").read_text("utf-8")
        import ast
        ast.parse(script)
        for forbidden in ("subprocess.run(", ".apply(", "urlopen(", "requests.get("):
            self.assertNotIn(forbidden, script)
        self.assertIn("verify_offline_assets", script)

    def test_real_managed_state_with_missing_archives_is_noop(self):
        """Exercise actual on-disk managed pin state, not a mocked planner."""
        pin = self.pins["jq"]
        self.root.mkdir()
        install_dir = self.root / pin["dest"]
        install_dir.mkdir()
        # Synthetic installed payload marker: do not fake a healthy install
        # with an empty directory, and never execute any vendor binary.
        (install_dir / "synthetic-contents.txt").write_text("fixture", encoding="utf-8")
        (self.root / ".portakit-state.json").write_text(
            json.dumps({"jq": {"version": pin["version"],
                                "sha256": pin["sha256"],
                                "dest": pin["dest"]}}),
            encoding="utf-8")
        saved = ready.kit.make_kit("already", ["jq"], self.pins, self.known)
        nonexistent = Path(self.tmp) / "no_vendor_archives_needed"
        with mock.patch.object(ready.kit.sets, "verify_offline_assets",
                               side_effect=AssertionError("unexpected SHA read")):
            report = self.assess(saved=saved, folder=nonexistent)
        self.assertEqual(report["outcome"], "NO_OP")
        self.assertEqual(report["needInstall"], 0)
        self.assertEqual(report["alreadyInstalled"], 1)
        self.assertEqual(report["tools"][0]["sourceStatus"], "NOT_REQUIRED")
        self.assertEqual(report["blockers"], [])
        self.assertFalse(nonexistent.exists())

    def test_real_empty_managed_folder_blocks_instead_of_false_noop(self):
        """Offline readiness must inherit the same empty-directory diagnosis."""
        pin = self.pins["jq"]
        self.root.mkdir()
        (self.root / pin["dest"]).mkdir()
        (self.root / ".portakit-state.json").write_text(
            json.dumps({"jq": {"version": pin["version"],
                                "sha256": pin["sha256"],
                                "dest": pin["dest"]}}),
            encoding="utf-8")
        saved = ready.kit.make_kit("empty-installed", ["jq"], self.pins, self.known)
        report = self.assess(saved=saved, folder=Path(self.tmp) / "missing-archives")
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["alreadyInstalled"], 0)
        self.assertEqual(report["needInstall"], 0)
        self.assertEqual(report["tools"][0]["installStatus"], "blocked-empty")
        self.assertTrue(any("INSTALL_BLOCKED: jq / blocked-empty" in blocker
                            for blocker in report["blockers"]))

    def test_mixed_real_managed_and_missing_app_requires_originals(self):
        pin = self.pins["jq"]
        self.root.mkdir()
        install_dir = self.root / pin["dest"]
        install_dir.mkdir()
        # Synthetic installed payload marker: do not fake a healthy install
        # with an empty directory, and never execute any vendor binary.
        (install_dir / "synthetic-contents.txt").write_text("fixture", encoding="utf-8")
        (self.root / ".portakit-state.json").write_text(
            json.dumps({"jq": {"version": pin["version"],
                                "sha256": pin["sha256"],
                                "dest": pin["dest"]}}),
            encoding="utf-8")
        saved = ready.kit.make_kit("partial", ["jq", "ripgrep"],
                                   self.pins, self.known)
        nonexistent = Path(self.tmp) / "no_vendor_archives"
        report = self.assess(saved=saved, folder=nonexistent)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["alreadyInstalled"], 1)
        self.assertEqual(report["needInstall"], 1)
        self.assertEqual([x["id"] for x in report["tools"]], ["jq", "ripgrep"])
        self.assertEqual(report["tools"][0]["sourceStatus"], "NOT_REQUIRED")
        self.assertEqual(report["tools"][1]["sourceStatus"], "MISSING_DIRECTORY")
        self.assertTrue(any("SOURCE_DIRECTORY_MISSING" in x for x in report["blockers"]))


if __name__ == "__main__":
    unittest.main()
