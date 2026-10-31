"""Offline editor-plugin install regression; all archives and hosts are synthetic.

Run only in Windows Actions. Never contacts a vendor, launches Notepad++,
loads plugin DLLs, uses admin rights, or mutates real workstation paths.
"""
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
SPEC = importlib.util.spec_from_file_location("portakit_plugin_offline",
                                              ROOT / "scripts" / "plugin_offline.py")
plugins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugins)


def synthetic_zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in rows:
            archive.writestr(name, data)
    return buf.getvalue()


class OfflinePluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.tmp / "portable"
        self.originals = self.tmp / "approved_originals"
        self.originals.mkdir()
        self.saved_path = self.tmp / "Kit.json"
        self.pins, _, _, self.known = plugins.kit.inventory()
        self.pins = copy.deepcopy(self.pins)
        self.archive_bytes = synthetic_zip([
            ("ComparePlus.dll", b"fake-dll-bytes-no-execution"),
            ("libs/sqlite.dll", b"fake-library")])
        self.sha = hashlib.sha256(self.archive_bytes).hexdigest()
        self.pin = self.pins["notepad++"]["recommended"]["plugins"][0]
        self.pin["sha256"] = self.sha
        self.source_path = self.originals / plugins.source_assets.original_filename(
            self.pin["url"])
        self.source_path.write_bytes(self.archive_bytes)
        self.saved = plugins.kit.make_kit(
            "editor", ["notepad++"], self.pins, self.known,
            plugins=["compareplus"])
        self.receipt = self.root / plugins.STATE_NAME

    def make_host(self):
        host = self.root / "notepad++"
        host.mkdir(parents=True)
        (host / "notepad++.exe").write_bytes(b"fake-host-only")
        p = self.pins["notepad++"]
        plugins.kit.core.write_state(self.root, {
            "notepad++": {key: p[key] for key in ("version", "sha256", "dest")}})
        return host

    def evidence_apply(self, *, approved=True, pending=False):
        log = self.tmp / ("trace-" + str(len(list(self.tmp.glob("trace-*")))) + ".log")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with plugins.kit.sets.Evidence(log) as evidence:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              skip_pending=approved, evidence=evidence)
        self.assertEqual(output.getvalue(), log.read_text("utf-8"))
        return output.getvalue()

    def save_kit(self):
        with contextlib.redirect_stdout(io.StringIO()):
            plugins.kit.save_new(self.saved, self.saved_path)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(plugins.kit, "inventory",
                               return_value=(self.pins, {}, {}, self.known)):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = plugins.run(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_plan_read_only_no_root(self):
        rows, pending = plugins.make_plan(self.saved, self.pins, self.root)
        self.assertEqual((rows[0]["status"], pending),
                         ("blocked-host-install", []))
        self.assertFalse(self.root.exists())

    def test_verify_original_zip_offline(self):
        selected, _ = plugins.select_plugins(self.saved, self.pins)
        found = plugins.verify_all(selected, self.originals)
        self.assertEqual(found["compareplus"], self.source_path)
        self.assertFalse(self.root.exists())

    def add_jsontools(self, *, complete=True):
        pin = self.pins["notepad++"]["recommended"]["plugins"][1]
        data = synthetic_zip([
            (("JsonTools.dll" if complete else "Different.dll"),
             b"synthetic plugin for local tests")])
        pin["sha256"] = hashlib.sha256(data).hexdigest()
        path = self.originals / plugins.source_assets.original_filename(pin["url"])
        path.write_bytes(data)
        self.saved = plugins.kit.make_kit(
            "two", ["notepad++"], self.pins, self.known,
            plugins=["compareplus", "jsontools-npp"])
        return path

    def test_both_pinned_plugins_apply_independently(self):
        host = self.make_host()
        self.add_jsontools()
        text = self.evidence_apply()
        self.assertIn("INSTALLED: compareplus", text)
        self.assertIn("INSTALLED: jsontools-npp", text)
        self.assertTrue((host / "plugins/JsonTools/JsonTools.dll").is_file())
        self.assertEqual(set(plugins.read_receipts(self.root)),
                         {"notepad++:compareplus", "notepad++:jsontools-npp"})

    def test_all_source_hashes_preflight_before_any_install(self):
        host = self.make_host()
        second = self.add_jsontools()
        second.write_bytes(b"changed second original")
        with self.assertRaisesRegex(plugins.PluginDeployError, "SHA-256"):
            with plugins.kit.sets.Evidence(self.tmp / "preflight.log") as ev:
                plugins.apply(self.saved, self.pins, self.root,
                              self.originals, evidence=ev)
        self.assertFalse((host / "plugins/ComparePlus").exists())
        self.assertFalse((host / "plugins/JsonTools").exists())

    def test_second_plugin_failure_retains_first_success_receipt(self):
        host = self.make_host()
        self.add_jsontools(complete=False)
        with self.assertRaisesRegex(plugins.PluginDeployError, "Required plugin DLL"):
            with plugins.kit.sets.Evidence(self.tmp / "batch.log") as ev:
                plugins.apply(self.saved, self.pins, self.root,
                              self.originals, evidence=ev)
        self.assertTrue((host / "plugins/ComparePlus/ComparePlus.dll").is_file())
        self.assertFalse((host / "plugins/JsonTools").exists())
        self.assertEqual(set(plugins.read_receipts(self.root)),
                         {"notepad++:compareplus"})

    def test_normal_installs_only_selected_plugin_in_existing_host(self):
        host = self.make_host()
        out = self.evidence_apply()
        self.assertIn("INSTALLED: compareplus", out)
        self.assertEqual((host / "plugins/ComparePlus/ComparePlus.dll").read_bytes(),
                         b"fake-dll-bytes-no-execution")
        self.assertEqual((host / "plugins/ComparePlus/libs/sqlite.dll").read_bytes(),
                         b"fake-library")
        self.assertEqual(plugins.read_receipts(self.root)["notepad++:compareplus"]["sha256"],
                         self.sha)
        self.assertEqual(list(self.root.glob(".portakit-plugin-*.tmp")), [])
        self.assertEqual(list(self.root.glob(".portakit-plugin-stage-*")), [])

    def test_idempotent_receipt_skips_only_intact_plugin(self):
        host = self.make_host()
        self.evidence_apply()
        target = host / "plugins/ComparePlus/ComparePlus.dll"
        original = target.read_bytes()
        out = self.evidence_apply()
        self.assertIn("SKIP: compareplus", out)
        self.assertEqual(target.read_bytes(), original)
        record = plugins.read_receipts(self.root)["notepad++:compareplus"]
        self.assertEqual(set(record["fileHashes"]),
                         {"ComparePlus.dll", "libs/sqlite.dll"})
        self.assertEqual(record["fileHashes"]["ComparePlus.dll"],
                         hashlib.sha256(original).hexdigest())

    def test_modified_plugin_main_DLL_is_blocked_without_replacement(self):
        host = self.make_host()
        self.evidence_apply()
        target = host / "plugins/ComparePlus/ComparePlus.dll"
        target.write_bytes(b"unknown mutation")
        row = plugins.make_plan(self.saved, self.pins, self.root)[0][0]
        self.assertEqual(row["status"], "blocked-content-drift")
        with self.assertRaisesRegex(plugins.PluginDeployError, "blocked"):
            self.evidence_apply()
        self.assertEqual(target.read_bytes(), b"unknown mutation")

    def test_modified_nested_dependency_blocks_readonly_plan(self):
        host = self.make_host()
        self.evidence_apply()
        library = host / "plugins/ComparePlus/libs/sqlite.dll"
        library.write_bytes(b"modified nested dependency")
        row = plugins.make_plan(self.saved, self.pins, self.root)[0][0]
        self.assertEqual(row["status"], "blocked-content-drift")

    def test_extra_or_missing_plugin_file_is_blocked(self):
        host = self.make_host()
        self.evidence_apply()
        dest = host / "plugins/ComparePlus"
        added = dest / "surprise.dat"
        added.write_bytes(b"unexpected")
        self.assertEqual(plugins.make_plan(self.saved, self.pins, self.root)[0][0]["status"],
                         "blocked-content-drift")
        added.unlink()
        (dest / "libs/sqlite.dll").unlink()
        self.assertEqual(plugins.make_plan(self.saved, self.pins, self.root)[0][0]["status"],
                         "blocked-content-drift")

    def test_legacy_receipts_are_not_trusted_or_autoreplaced(self):
        host = self.make_host()
        self.evidence_apply()
        data = plugins.read_receipts(self.root)
        del data["notepad++:compareplus"]["fileHashes"]
        plugins.write_receipts(self.root, data)
        result = plugins.make_plan(self.saved, self.pins, self.root)[0][0]
        self.assertEqual(result["status"], "blocked-legacy-unverified")
        with self.assertRaisesRegex(plugins.PluginDeployError, "blocked"):
            self.evidence_apply()
        self.assertTrue((host / "plugins/ComparePlus/ComparePlus.dll").exists())

    def test_unsafe_or_malformed_receipt_hash_inventory_fails_closed(self):
        self.make_host()
        self.evidence_apply()
        for bad in ({}, {"../unsafe": "a" * 64}, {"A.dll": "WRONG"},
                    {"valid.dll": None}, {"X.dll": "a" * 64, "x.dll": "b" * 64}):
            with self.subTest(bad=bad):
                record = plugins.read_receipts(self.root)
                record["notepad++:compareplus"]["fileHashes"] = bad
                self.receipt.write_text(json.dumps(record), "utf-8")
                with self.assertRaises(plugins.PluginDeployError):
                    plugins.make_plan(self.saved, self.pins, self.root)
                fresh = plugins.receipt_record(self.pins["notepad++"],
                                               self.pin, {"ComparePlus.dll": "a" * 64})
                fresh["fileHashes"]["libs/sqlite.dll"] = "b" * 64
                plugins.write_receipts(self.root, {
                    "notepad++:compareplus": fresh})

    def test_installed_plugin_symlink_refused(self):
        host = self.make_host()
        self.evidence_apply()
        link = host / "plugins/ComparePlus/extra.link"
        target = self.tmp / "outside.txt"
        target.write_text("external", "utf-8")
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink not permitted on Windows runner")
        with self.assertRaises(plugins.kit.core.PortakitError):
            plugins.make_plan(self.saved, self.pins, self.root)
        self.assertEqual(target.read_text("utf-8"), "external")

    def test_hash_inventory_member_limit_is_enforced(self):
        host = self.make_host()
        self.evidence_apply()
        with mock.patch.object(plugins, "MAX_PLUGIN_FILES", 1):
            # Stored receipt preflight is separately bounded before traversal.
            with self.assertRaisesRegex(plugins.PluginDeployError,
                                        "Invalid plugin file hash inventory"):
                plugins.make_plan(self.saved, self.pins, self.root)
            # The actual filesystem traversal has its own independent gate.
            with self.assertRaisesRegex(plugins.PluginDeployError, "member count"):
                plugins.installed_file_hashes(host / "plugins/ComparePlus")

    def test_wrong_hash_fails_before_writes(self):
        host = self.make_host()
        self.source_path.write_bytes(b"tampered source")
        with self.assertRaisesRegex(plugins.PluginDeployError, "SHA-256"):
            with plugins.kit.sets.Evidence(self.tmp / "bad-hash.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root,
                              self.originals, evidence=evidence)
        self.assertFalse((host / "plugins").exists())
        self.assertFalse(self.receipt.exists())

    def test_source_mutated_between_preflight_and_extract_denied(self):
        host = self.make_host()
        prior = plugins.verify_all
        def swap(selected, directory):
            found = prior(selected, directory)
            self.source_path.write_bytes(b"source replaced after check")
            return found
        with mock.patch.object(plugins, "verify_all", side_effect=swap):
            with self.assertRaisesRegex(plugins.PluginDeployError, "changed"):
                with plugins.kit.sets.Evidence(self.tmp / "swap.log") as evidence:
                    plugins.apply(self.saved, self.pins, self.root,
                                  self.originals, evidence=evidence)
        self.assertFalse((host / "plugins/ComparePlus").exists())
        self.assertFalse(self.receipt.exists())

    def test_archive_missing_required_DLL_rolls_back_stage(self):
        host = self.make_host()
        contents = synthetic_zip([("Other.dll", b"wrong")])
        self.source_path.write_bytes(contents)
        self.pin["sha256"] = hashlib.sha256(contents).hexdigest()
        self.saved["pluginSelections"][0]["lockedPin"]["sha256"] = self.pin["sha256"]
        with self.assertRaisesRegex(plugins.PluginDeployError, "Required plugin DLL"):
            with plugins.kit.sets.Evidence(self.tmp / "missing.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=evidence)
        self.assertFalse((host / "plugins/ComparePlus").exists())
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.glob(".portakit-plugin-stage-*")), [])
        self.assertEqual(list(self.root.glob(".portakit-plugin-archive-*")), [])

    def test_zip_traversal_archive_fails_closed(self):
        host = self.make_host()
        contents = synthetic_zip([("../escape.dll", b"malicious")])
        self.source_path.write_bytes(contents)
        self.pin["sha256"] = hashlib.sha256(contents).hexdigest()
        self.saved["pluginSelections"][0]["lockedPin"]["sha256"] = self.pin["sha256"]
        with self.assertRaises(plugins.kit.core.PortakitError):
            with plugins.kit.sets.Evidence(self.tmp / "traversal.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=evidence)
        self.assertFalse((self.root / "escape.dll").exists())
        self.assertFalse((host / "plugins/ComparePlus").exists())
        self.assertFalse(self.receipt.exists())

    def test_unknown_preexisting_plugin_folder_never_overwritten(self):
        host = self.make_host()
        current = host / "plugins/ComparePlus"
        current.mkdir(parents=True)
        (current / "ComparePlus.dll").write_bytes(b"unknown third party")
        self.assertEqual(plugins.make_plan(self.saved, self.pins, self.root)[0][0]["status"],
                         "blocked-unmanaged")
        with self.assertRaisesRegex(plugins.PluginDeployError, "blocked"):
            with plugins.kit.sets.Evidence(self.tmp / "blocked.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=evidence)
        self.assertEqual((current / "ComparePlus.dll").read_bytes(),
                         b"unknown third party")

    def test_wrong_host_version_blocks_before_writes(self):
        host = self.make_host()
        state = plugins.kit.core.read_state(self.root)
        state["notepad++"]["version"] = "not-approved-version"
        plugins.kit.core.write_state(self.root, state)
        self.assertTrue(plugins.make_plan(self.saved, self.pins, self.root)[0][0]["status"]
                        .startswith("blocked-host"))
        with self.assertRaisesRegex(plugins.PluginDeployError, "blocked"):
            with plugins.kit.sets.Evidence(self.tmp / "host.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=evidence)
        self.assertFalse((host / "plugins/ComparePlus").exists())

    def test_receipt_write_failure_removes_plugin_tree(self):
        host = self.make_host()
        with mock.patch.object(plugins, "write_receipts",
                               side_effect=OSError("state unavailable")):
            with self.assertRaisesRegex(OSError, "state unavailable"):
                with plugins.kit.sets.Evidence(self.tmp / "receipt.log") as evidence:
                    plugins.apply(self.saved, self.pins, self.root, self.originals,
                                  evidence=evidence)
        self.assertFalse((host / "plugins/ComparePlus").exists())
        self.assertFalse(self.receipt.exists())

    def test_bad_receipt_state_blocks(self):
        self.make_host()
        self.receipt.write_text('{"bad": "thing"}', "utf-8")
        with self.assertRaisesRegex(plugins.PluginDeployError, "Invalid"):
            plugins.make_plan(self.saved, self.pins, self.root)

    def test_pending_never_installs_without_explicit_exclusion(self):
        self.make_host()
        self.saved["pluginSelections"].append({
            "id": "csvlint-npp", "host": "notepad++",
            "status": "RESEARCH_ONLY", "lockedPin": None})
        with self.assertRaisesRegex(plugins.PluginDeployError, "Research-only"):
            with plugins.kit.sets.Evidence(self.tmp / "pending.log") as evidence:
                plugins.apply(self.saved, self.pins, self.root,
                              self.originals, evidence=evidence)
        self.assertFalse(self.receipt.exists())
        out = self.evidence_apply(approved=True)
        self.assertIn("INSTALLED: compareplus", out)
        self.assertFalse((self.root / "notepad++/plugins/CSVLint").exists())

    def test_cli_requires_dual_operator_consent(self):
        self.make_host()
        self.save_kit()
        base = ("apply", "--kit", str(self.saved_path), "--root", str(self.root),
                "--offline-dir", str(self.originals))
        rc, out, err = self.cli(*base)
        self.assertEqual(rc, 1)
        self.assertIn("--yes AND --policy-approved", err)
        rc, out, err = self.cli(*(base + ("--yes",)))
        self.assertEqual(rc, 1)
        self.assertFalse(self.receipt.exists())

    def test_cli_preflight_and_consented_installer_evidence(self):
        self.make_host()
        self.save_kit()
        base = ("--kit", str(self.saved_path), "--root", str(self.root))
        rc, out, err = self.cli("plan", *base)
        self.assertEqual((rc, err), (0, ""))
        self.assertIn("PLUGIN: compareplus / install", out)
        rc, out, err = self.cli("verify", *base, "--offline-dir", str(self.originals))
        self.assertEqual((rc, err), (0, ""))
        self.assertIn("SHA256 PASS: compareplus", out)
        file = self.tmp / "installed.log"
        rc, out, err = self.cli(
            "apply", *base, "--offline-dir", str(self.originals),
            "--yes", "--policy-approved", "--log-file", str(file))
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out, file.read_text("utf-8"))
        self.assertIn("RESULT: COMPLETE", out)

    def test_empty_v1_and_unapproved_only_stays_uninstallable(self):
        self.make_host()
        legacy = plugins.kit.make_kit("legacy", ["notepad++"], self.pins, self.known)
        with self.assertRaisesRegex(plugins.PluginDeployError, "v2"):
            plugins.select_plugins(legacy, self.pins)
        pending_only = plugins.kit.make_kit(
            "waiting", ["notepad++"], self.pins, self.known,
            plugins=["csvlint-npp"])
        with plugins.kit.sets.Evidence(self.tmp / "pending-only.log") as log:
            with self.assertRaisesRegex(plugins.PluginDeployError, "Research-only"):
                plugins.apply(pending_only, self.pins, self.root,
                              self.originals, evidence=log)
        self.assertFalse(self.receipt.exists())

    def test_no_vendor_executables_or_network_ever_invoked(self):
        self.make_host()
        with mock.patch.object(plugins.kit.core, "download",
                               side_effect=AssertionError("download")):
            with mock.patch.object(plugins.kit.sets, "apply",
                                   side_effect=AssertionError("toolset apply")):
                self.evidence_apply()
        self.assertFalse((self.root / "notepad++/gup.exe").exists())


    def test_apply_idempotent_without_archive_directory_or_originals(self):
        """Installed matching receipts never need the old vendor ZIP again."""
        host = self.make_host()
        self.evidence_apply()
        receipt_before = self.receipt.read_bytes()
        (self.root / "notepad++/plugins/ComparePlus/ComparePlus.dll").is_file()
        self.source_path.unlink()
        with mock.patch.object(plugins, "verify_all",
                               side_effect=AssertionError("unneeded original")):
            with plugins.kit.sets.Evidence(self.tmp / "no-original.log") as log:
                plugins.apply(self.saved, self.pins, self.root, None, evidence=log)
        self.assertEqual(self.receipt.read_bytes(), receipt_before)
        self.assertIn("SKIP: compareplus",
                      (self.tmp / "no-original.log").read_text("utf-8"))
        self.assertTrue((host / "plugins/ComparePlus/ComparePlus.dll").is_file())

    def test_mixed_existing_and_missing_checks_only_missing_archive(self):
        """A previously installed plugin never forces re-import of its old ZIP."""
        host = self.make_host()
        self.evidence_apply()
        self.add_jsontools()
        self.source_path.unlink()
        with mock.patch.object(plugins, "verify_all",
                               wraps=plugins.verify_all) as check:
            with plugins.kit.sets.Evidence(self.tmp / "mixed.log") as log:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=log)
        self.assertEqual(len(check.call_args.args[0]), 1)
        self.assertEqual(check.call_args.args[0][0][0]["id"], "jsontools-npp")
        self.assertTrue((host / "plugins/JsonTools/JsonTools.dll").is_file())
        self.assertEqual(set(plugins.read_receipts(self.root)), {
            "notepad++:compareplus", "notepad++:jsontools-npp"})
        self.assertIn("SKIP: compareplus",
                      (self.tmp / "mixed.log").read_text("utf-8"))

    def test_missing_mixed_original_fails_before_new_install(self):
        """Missing second ZIP blocks with no mutation of the first plugin."""
        host = self.make_host()
        self.evidence_apply()
        second = self.add_jsontools()
        second.unlink()
        self.source_path.unlink()
        before = self.receipt.read_bytes()
        with self.assertRaisesRegex(plugins.PluginDeployError,
                                    "Missing original vendor archive"):
            with plugins.kit.sets.Evidence(self.tmp / "mixed-missing.log") as log:
                plugins.apply(self.saved, self.pins, self.root, self.originals,
                              evidence=log)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertTrue((host / "plugins/ComparePlus/ComparePlus.dll").is_file())
        self.assertFalse((host / "plugins/JsonTools").exists())

    def test_apply_without_dir_fails_when_plugin_missing(self):
        """Omission must fail closed rather than silently skipping installation."""
        host = self.make_host()
        with self.assertRaisesRegex(plugins.PluginDeployError, "require --offline-dir"):
            with plugins.kit.sets.Evidence(self.tmp / "need-dir.log") as log:
                plugins.apply(self.saved, self.pins, self.root, None, evidence=log)
        self.assertFalse((host / "plugins").exists())
        self.assertFalse(self.receipt.exists())

    def test_cli_noop_no_offline_dir_still_requires_dual_consent(self):
        """No-op is permitted without archives, but never bypasses consent."""
        self.make_host()
        self.evidence_apply()
        self.source_path.unlink()
        self.save_kit()
        base = ("apply", "--kit", str(self.saved_path),
                "--root", str(self.root))
        rc, out, err = self.cli(*base)
        self.assertEqual(rc, 1)
        self.assertIn("--yes AND --policy-approved", err)
        rc, out, err = self.cli(*(base + ("--yes", "--policy-approved",
                                         "--log-file", str(self.tmp / "cli-noop.log"))))
        self.assertEqual((rc, err), (0, ""))
        self.assertIn("SKIP: compareplus", out)
        self.assertEqual(out, (self.tmp / "cli-noop.log").read_text("utf-8"))
        self.assertIn("RESULT: COMPLETE", out)

    def test_research_only_skip_noop_no_archive(self):
        """Pure research selections stay excluded even without vendor files."""
        self.make_host()
        saved = plugins.kit.make_kit("research", ["notepad++"],
                                     self.pins, self.known,
                                     plugins=["csvlint-npp"])
        with plugins.kit.sets.Evidence(self.tmp / "research-noop.log") as log:
            plugins.apply(saved, self.pins, self.root, None,
                          skip_pending=True, evidence=log)
        self.assertFalse(self.receipt.exists())
        self.assertIn("NO_OP: no SHA-pinned plugins selected",
                      (self.tmp / "research-noop.log").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
