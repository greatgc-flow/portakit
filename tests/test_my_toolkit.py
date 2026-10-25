"""Windows/offline regression for personal kit creation and safe composition.

No network access, vendor executables, UAC, registry, services or drivers.
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
SPEC = importlib.util.spec_from_file_location("portakit_my_toolkit",
                                              REPO / "scripts" / "my_toolkit.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


class KitTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(folder) / "apps"
        self.saved = Path(folder) / "personal.json"
        self.pins, self.categories, self.profiles, self.known = kit.inventory()

    def make(self, *ids):
        return kit.make_kit("my-kit", list(ids), self.pins, self.known)

    def save(self, data):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            kit.save_new(data, self.saved)
        self.assertEqual(output.getvalue(), self.saved.with_suffix(".log").read_text("utf-8"))
        return output.getvalue()

    def run_command(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = kit.run(argv)
        return result, out.getvalue(), err.getvalue()

    def test_all_tools_available_for_selection_but_not_for_install(self):
        self.assertEqual(len(self.known), 151)
        statuses = [x["admission"] for x in self.known.values()]
        self.assertEqual(statuses.count("PINNED_CATALOG"), 17)
        self.assertEqual(statuses.count("OS_BUILTIN"), 27)
        self.assertEqual(statuses.count("RESEARCH_ONLY"), 107)
        self.assertIn("secs4net", self.known)
        self.assertIn("duckdb-cli", self.known)
        self.assertIn("nats-server", self.known)

    def test_profile_category_and_individual_candidate_dedup(self):
        ids = kit.requested_ids(["duckdb-cli", "jq", "duckdb-cli", "cmd"],
                                ["essentials", "essentials"], [], ["winmerge"],
                                self.pins, self.categories, self.profiles, self.known)
        self.assertEqual(ids, ["notepad++", "jq", "duckdb-cli", "cmd"])
        k = kit.make_kit("portable01", ids, self.pins, self.known)
        self.assertEqual(list(k["lockedPins"]), ["notepad++", "jq"])
        self.assertEqual(k["researchOnly"], ["duckdb-cli"])
        self.assertEqual(k["osBuiltins"], ["cmd"])

    def test_category_selects_only_pinned_tools(self):
        ids = kit.requested_ids([], [], ["network", "text"], [],
                                self.pins, self.categories, self.profiles, self.known)
        self.assertEqual(ids, ["notepad++", "ripgrep", "bat", "sd", "grepwin"])
        self.assertNotIn("tcping", ids)

    def test_7zip_prerequisite_order_corrected_when_both_selected(self):
        ids = kit.requested_ids(["7zip", "7zr"], [], [], [],
                                self.pins, self.categories, self.profiles, self.known)
        self.assertEqual(ids, ["7zr", "7zip"])
        p = kit.create_plan(kit.make_kit("sample", ids, self.pins, self.known), self.root)
        kit.check_prerequisite(self.make("7zr", "7zip"), p)

    def test_7zip_alone_requires_managed_prerequisite(self):
        k = self.make("7zip")
        plan = kit.create_plan(k, self.root)
        with self.assertRaisesRegex(kit.KitError, "7zr"):
            kit.check_prerequisite(k, plan)
        self.assertFalse(self.root.exists())

    def test_create_save_and_read_without_touching_install_root(self):
        data = self.make("jq", "duckdb-cli", "cmd")
        output = self.save(data)
        self.assertIn("NO INSTALL / NO NETWORK", output)
        self.assertEqual(kit.read_kit(self.saved, self.pins, self.known), data)
        self.assertFalse(self.root.exists())

    def test_no_overwrite_and_bad_file_refused(self):
        data = self.make("jq")
        self.save(data)
        with self.assertRaisesRegex(kit.KitError, "already exists"):
            kit.save_new(data, self.saved)
        contents = json.loads(self.saved.read_text(encoding="utf-8"))
        contents["unexpected"] = "install-me"
        self.saved.write_text(json.dumps(contents), encoding="utf-8")
        with self.assertRaisesRegex(kit.KitError, "schema"):
            kit.read_kit(self.saved, self.pins, self.known)

    def test_locked_pin_drift_denied_even_when_current_catalog_has_pin(self):
        data = self.make("jq")
        data["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.saved.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(kit.KitError, "PIN_CHANGED"):
            kit.read_kit(self.saved, self.pins, self.known)

    def test_stale_or_fake_tool_id_and_duplicate_rejected(self):
        with self.assertRaisesRegex(kit.KitError, "Unknown tool"):
            kit.requested_ids(["fake-tool"], [], [], [], self.pins,
                              self.categories, self.profiles, self.known)
        with self.assertRaisesRegex(kit.KitError, "Empty selection"):
            kit.requested_ids([], [], [], [], self.pins,
                              self.categories, self.profiles, self.known)
        with self.assertRaisesRegex(kit.KitError, "name"):
            kit.make_kit("../escape", ["jq"], self.pins, self.known)
        data = self.make("jq")
        data["tools"].append("jq")
        self.saved.write_text(json.dumps(data))
        with self.assertRaisesRegex(kit.KitError, "duplicated"):
            kit.read_kit(self.saved, self.pins, self.known)

    def test_plan_with_pending_and_builtin_is_read_only(self):
        self.save(self.make("jq", "duckdb-cli", "cmd"))
        code, out, err = self.run_command(["plan", "--kit", str(self.saved),
                                           "--root", str(self.root)])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("jq\tinstall", out)
        self.assertIn("duckdb-cli\tRESEARCH_ONLY", out)
        self.assertIn("cmd\tOS_BUILTIN", out)
        self.assertFalse(self.root.exists())

    def test_build_requires_consent_and_rejects_pending_before_install(self):
        self.save(self.make("jq", "duckdb-cli"))
        base = ["build", "--kit", str(self.saved), "--root", str(self.root)]
        with mock.patch.object(kit.sets, "apply") as installer:
            no, _, error = self.run_command(base)
            self.assertEqual(no, 1)
            self.assertIn("--yes", error)
            blocked, _, error = self.run_command(base + ["--yes"])
            self.assertEqual(blocked, 1)
            self.assertIn("Research-only", error)
            installer.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_partial_explicit_build_only_installable_pin_and_offline_pass_through(self):
        self.save(self.make("jq", "duckdb-cli", "cmd"))
        arguments = ["build", "--kit", str(self.saved), "--root", str(self.root),
                     "--yes", "--skip-pending", "--offline-dir", str(self.root / "source")]
        with mock.patch.object(kit.sets, "apply",
                               return_value={"failed": None, "installed": [], "skipped": []}) as install:
            code, stdout, stderr = self.run_command(arguments)
        self.assertEqual((code, stderr), (0, ""))
        plan, recommended, evidence = install.call_args.args
        self.assertEqual([x["id"] for x in plan["tools"]], ["jq"])
        self.assertEqual(plan["include"], ["jq"])
        self.assertFalse(recommended)
        self.assertEqual(install.call_args.kwargs["offline_dir"], str(self.root / "source"))
        self.assertFalse(self.root.exists())

    def test_builtin_only_is_no_op_with_matching_evidence(self):
        self.save(self.make("cmd"))
        evidence = self.saved.parent / "noop.log"
        code, out, err = self.run_command(["build", "--kit", str(self.saved),
                                            "--root", str(self.root), "--yes",
                                            "--log-file", str(evidence)])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("NO_OP", out)
        self.assertEqual(out, evidence.read_text(encoding="utf-8"))
        self.assertFalse(self.root.exists())

    def test_create_cli_and_inventory_default_filter(self):
        code, output, error = self.run_command(["list"])
        self.assertEqual((code, error), (0, ""))
        self.assertIn("TOTAL: 17", output)
        code, output, error = self.run_command(["list", "--all", "--category", "network"])
        self.assertEqual((code, error), (0, ""))
        self.assertIn("tcping\tRESEARCH_ONLY", output)
        code, output, error = self.run_command(
            ["create", "--name", "my-team", "--out", str(self.saved),
             "--tool", "jq", "--tool", "duckdb-cli", "--preset", "minimal"])
        self.assertEqual((code, error), (0, ""))
        self.assertIn("CREATED:", output)
        saved = kit.read_kit(self.saved, self.pins, self.known)
        self.assertEqual(saved["tools"], ["notepad++", "winmerge", "jq", "duckdb-cli"])


if __name__ == "__main__":
    unittest.main()
