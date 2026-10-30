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

    def test_idempotent_receipt_skips_without_replacing_plugin(self):
        host = self.make_host()
        self.evidence_apply()
        target = host / "plugins/ComparePlus/ComparePlus.dll"
        target.write_bytes(b"user-modification")
        out = self.evidence_apply()
        self.assertIn("SKIP: compareplus", out)
        self.assertEqual(target.read_bytes(), b"user-modification")

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


if __name__ == "__main__":
    unittest.main()
