"""Deterministic no-network tests for optional toolsets on Windows."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import importlib.util

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portakit_toolsets", REPO / "scripts/toolsets.py")
toolsets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(toolsets)


class ToolsetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "my portable"
        self.manifest = REPO / "toolsets.json"

    def plan(self, names, include=(), exclude=()):
        return toolsets.create_plan(names, include, exclude, self.root, self.manifest)

    def test_curated_groups_and_profiles_resolve_to_catalog_only(self):
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        categories, profiles = toolsets.load_manifest(self.manifest, catalog)
        self.assertEqual(set(categories), {
            "files", "text", "structured-data", "system", "network",
            "security", "development", "automation", "documents", "transfer",
        })
        self.assertTrue({"minimal", "mes-support", "developer", "all-curated",
                         "essentials", "lightweight", "engineering", "incident-response"}.issubset(set(profiles)))
        self.assertTrue({"common", "os", "nw", "dev", "data", "diag"}.issubset(set(profiles)))
        self.assertEqual([r["id"] for r in self.plan(["minimal"])["tools"]],
                         ["notepad++", "winmerge"])
        self.assertEqual([r["id"] for r in self.plan(["mes-support"])["tools"]],
                         ["notepad++", "winmerge", "jq"])

    def test_v2_primary_mece_is_total_and_disjoint(self):
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        categories, _ = toolsets.load_manifest(self.manifest, catalog)
        ids = [item for group in categories.values() for item in group["tools"]]
        self.assertEqual(set(ids), set(catalog))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 11)

    def test_v2_legacy_names_remain_frozen_without_unintended_additions(self):
        expected = {"common": ["notepad++", "winmerge"],
                    "os": ["winmerge"], "nw": [],
                    "dev": ["notepad++", "jq"],
                    "data": ["jq"], "diag": ["winmerge", "jq"]}
        for alias, names in expected.items():
            self.assertEqual([r["id"] for r in self.plan([alias])["tools"]], names)

    def test_v2_lightweight_selection_eight_deduplicated_pins(self):
        tools = [r["id"] for r in self.plan(["lightweight"])["tools"]]
        self.assertEqual(tools, ["ripgrep", "fd", "fzf", "bat",
                                 "sd", "yq", "delta", "hyperfine"])
        self.assertEqual([r["id"] for r in self.plan(["lightweight", "lightweight"])["tools"]], tools)

    def test_v2_duplicate_primary_assignment_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["categories"][1]["tools"].append("winmerge")
        path = self.root.parent / "duplicate-primary.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "MECE"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_v2_missing_catalog_assignment_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["categories"][0]["tools"].remove("fd")
        path = self.root.parent / "missing-primary.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "MECE"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_v2_duplicate_profile_tools_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["profiles"][0]["tools"].append("notepad++")
        path = self.root.parent / "bad-profile.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "duplicate/unknown"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_nw_is_explicitly_empty_not_fake_install(self):
        p = self.plan(["nw"])
        self.assertEqual(p["tools"], [])
        self.assertFalse(self.root.exists())

    def test_overlap_deduplicates_and_preserves_order(self):
        self.assertEqual([r["id"] for r in self.plan(["dev", "common", "dev"])["tools"]],
                         ["notepad++", "jq", "winmerge"])

    def test_include_exclude_only_catalog_ids(self):
        selected = self.plan(["common"], ["jq"], ["winmerge"])
        self.assertEqual([t["id"] for t in selected["tools"]],
                         ["notepad++", "jq"])
        with self.assertRaisesRegex(toolsets.ToolsetError, "Unknown pinned"):
            self.plan(["nw"], ["curl-arbitrary"])
        with self.assertRaisesRegex(toolsets.ToolsetError, "exclude"):
            self.plan(["nw"], (), ["curl-arbitrary"])

    def test_unknown_toolset_and_empty_name_refuse(self):
        with self.assertRaisesRegex(toolsets.ToolsetError, "Unknown"):
            self.plan(["unknown"])
        with self.assertRaisesRegex(toolsets.ToolsetError, "Select one"):
            self.plan([])

    def test_plan_is_read_only_and_status_is_install(self):
        p = self.plan(["minimal"])
        self.assertEqual([x["status"] for x in p["tools"]], ["install", "install"])
        self.assertFalse(self.root.exists())

    def test_installed_pin_no_op_and_stale_pin_blocked(self):
        self.root.mkdir()
        (self.root / "notepad++").mkdir()
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        t = catalog["notepad++"]
        state = {"notepad++": {"version": t["version"], "sha256": t["sha256"],
                               "dest": t["dest"]}}
        (self.root / ".portakit-state.json").write_text(json.dumps(state))
        self.assertEqual(self.plan(["common"])["tools"][0]["status"], "already-installed")
        state["notepad++"]["sha256"] = "f" * 64
        (self.root / ".portakit-state.json").write_text(json.dumps(state))
        p = self.plan(["common"])
        self.assertEqual(p["tools"][0]["status"], "blocked-pin")
        p.update(include=[], exclude=[], manifest=self.manifest)
        with self.assertRaisesRegex(toolsets.ToolsetError, "blocked plan"):
            toolsets.apply(p, False, self.root / "evidence.log",
                           runner=mock.Mock())
        self.assertFalse((self.root / "evidence.log").exists())

    def test_existing_unmanaged_destination_and_backup_blocked(self):
        self.root.mkdir()
        (self.root / "jq").mkdir()
        self.assertEqual(self.plan(["data"])["tools"][0]["status"], "blocked-unmanaged")
        (self.root / "jq.old").mkdir()
        self.assertEqual(self.plan(["data"])["tools"][0]["status"], "blocked-backup")

    def test_manifest_unknown_tool_and_duplicate_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["categories"][0]["tools"].append("not-in-pins")
        path = self.root.parent / "custom.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "unknown pinned"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))
        data["categories"][0]["tools"][-1] = "notepad++"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "duplicate member"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_unsupported_manifest_version_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["schemaVersion"] = 999
        path = self.root.parent / "future.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "schemaVersion"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_apply_installs_each_unique_id_once_and_logs_verbatim(self):
        p = self.plan(["mes-support", "developer"])
        p.update(include=[], exclude=[], manifest=self.manifest)
        calls = []

        def runner(cmd, **kwargs):
            calls.append(list(cmd))
            app = cmd[cmd.index("install") + 1]
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": app}, "error": None}), "")
        log = self.root / "test-result.log"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = toolsets.apply(p, True, log, runner=runner)
        self.assertEqual(result["installed"], ["notepad++", "winmerge", "jq"])
        self.assertEqual(len(calls), 3)
        self.assertTrue("--recommended" in calls[0])
        self.assertTrue("--recommended" in calls[1])
        self.assertFalse("--recommended" in calls[2])
        self.assertEqual(output.getvalue(), log.read_text(encoding="utf-8"))

    def test_failure_stops_and_preserves_prior_tools(self):
        p = self.plan(["mes-support"])
        p.update(include=[], exclude=[], manifest=self.manifest)
        calls = []

        def runner(cmd, **kwargs):
            app = cmd[cmd.index("install") + 1]
            calls.append(app)
            if app == "winmerge":
                return subprocess.CompletedProcess(cmd, 3, "", "unreachable download")
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": app}}), "")
        log = self.root / "evidence.log"
        with contextlib.redirect_stdout(io.StringIO()):
            result = toolsets.apply(p, False, log, runner=runner)
        self.assertEqual(calls, ["notepad++", "winmerge"])
        self.assertEqual(result["installed"], ["notepad++"])
        self.assertEqual(result["failed"], "winmerge")
        self.assertIn("PARTIAL:", log.read_text(encoding="utf-8"))

    def test_empty_nw_apply_is_pure_no_op(self):
        p = self.plan(["nw"])
        p.update(include=[], exclude=[], manifest=self.manifest)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = toolsets.apply(p, False, self.root / "should-not-exist.log",
                                    runner=mock.Mock(side_effect=AssertionError("unexpected install")))
        self.assertEqual(result, {"installed": [], "skipped": [], "failed": None})
        self.assertFalse(self.root.exists())
        self.assertIn("NO_OP", out.getvalue())

    def test_command_list_plan_and_apply_consent(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(toolsets.main(["list"]), 0)
        self.assertIn("nw\t", output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(toolsets.main(["plan", "nw", "--root", str(self.root)]), 0)
        self.assertIn("EMPTY:", output.getvalue())
        self.assertFalse(self.root.exists())
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(toolsets.main(["apply", "minimal", "--root",
                                            str(self.root)]), 1)
        self.assertIn("--yes", errors.getvalue())
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
