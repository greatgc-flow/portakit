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

    def mark_managed(self, identifier, *, create_directory=True, wrong_pin=False):
        """Simulate only an installed directory and receipt, never run vendors."""
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        pin = catalog[identifier]
        if create_directory:
            target = self.root / pin["dest"]
            target.mkdir(parents=True, exist_ok=True)
            # Synthetic test payload only: exercise managed-directory presence
            # without executing or copying any third-party vendor binary.
            (target / "fixture-payload.txt").write_text("synthetic")
        state = toolsets.core.read_state(self.root)
        state[identifier] = {
            "version": pin["version"],
            "sha256": ("f" * 64 if wrong_pin else pin["sha256"]),
            "dest": pin["dest"],
        }
        toolsets.core.write_state(self.root, state)

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
        self.assertEqual(len(ids), 19)

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
        (self.root / "notepad++" / "fixture-payload.txt").write_text("synthetic")
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

    def test_empty_managed_directory_reports_blocked_empty_without_writes(self):
        """Receipts plus empty folders are not healthy installed applications."""
        self.root.mkdir()
        (self.root / "jq").mkdir()
        pin = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)["jq"]
        state = {"jq": {"version": pin["version"], "sha256": pin["sha256"],
                        "dest": pin["dest"]}}
        path = self.root / ".portakit-state.json"
        path.write_text(json.dumps(state), encoding="utf-8")
        before = path.read_bytes()
        plan = self.plan(["data"])
        self.assertEqual(plan["tools"][0]["status"], "blocked-empty")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list((self.root / "jq").iterdir()))
        plan.update(include=[], exclude=[], manifest=self.manifest)
        runner = mock.Mock(side_effect=AssertionError("unexpected child"))
        log = self.root.parent / "empty-plan.log"
        with self.assertRaisesRegex(toolsets.ToolsetError, "blocked plan"):
            toolsets.apply(plan, False, log, runner=runner)
        self.assertFalse(log.exists())
        runner.assert_not_called()

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
        data["categories"][0]["tools"][-1] = "winmerge"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "duplicate member"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_duplicate_manifest_schema_claim_is_rejected(self):
        source = self.manifest.read_text(encoding="utf-8")
        p = self.root.parent / "duplicate-v2.json"
        p.write_text(source.replace('"schemaVersion": 2',
                                    '"schemaVersion": 1, "schemaVersion": 2', 1),
                     encoding="utf-8")
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        with self.assertRaisesRegex(toolsets.ToolsetError, "Duplicate JSON key"):
            toolsets.load_manifest(p, catalog)

    def test_duplicate_nested_toolset_field_is_rejected(self):
        source = self.manifest.read_text(encoding="utf-8")
        p = self.root.parent / "duplicate-category.json"
        p.write_text(source.replace('"tools":', '"tools": [], "tools":', 1),
                     encoding="utf-8")
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        with self.assertRaisesRegex(toolsets.ToolsetError, "Duplicate JSON key"):
            toolsets.load_manifest(p, catalog)

    def test_nonfinite_manifest_extra_field_is_rejected(self):
        source = self.manifest.read_text(encoding="utf-8")
        p = self.root.parent / "nonfinite-manifest.json"
        p.write_text(source.replace('"schemaVersion": 2',
                                    '"unused": Infinity, "schemaVersion": 2', 1),
                     encoding="utf-8")
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        with self.assertRaisesRegex(toolsets.ToolsetError,
                                    "Nonstandard JSON numeric"):
            toolsets.load_manifest(p, catalog)

    def test_unsupported_manifest_version_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["schemaVersion"] = 999
        path = self.root.parent / "future.json"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(toolsets.ToolsetError, "schemaVersion"):
            toolsets.load_manifest(path, toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG))

    def test_schema_version_requires_real_integer_not_bool_or_float(self):
        """True == 1 and 2.0 == 2 must not pass a declarative schema gate."""
        original = json.loads(self.manifest.read_text(encoding="utf-8"))
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        path = self.root.parent / "invalid-schema-version.json"
        for version in (True, False, 1.0, 2.0, "1", "2", None, [], {}):
            with self.subTest(version=repr(version)):
                data = dict(original, schemaVersion=version)
                path.write_text(json.dumps(data), encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaisesRegex(
                        toolsets.ToolsetError, "schemaVersion=1 or 2"):
                    toolsets.load_manifest(path, catalog)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(self.root.exists())
        # The unchanged v2 source remains valid after all bad inputs.
        categories, profiles = toolsets.load_manifest(self.manifest, catalog)
        self.assertEqual(set(categories), {
            "files", "text", "structured-data", "system", "network",
            "security", "development", "automation", "documents", "transfer"})
        self.assertIn("minimal", profiles)

    def test_mutating_apply_rejects_log_under_managed_root_before_writes(self):
        """No batch, lock, root mkdir or installer may run with deletable evidence."""
        plan = self.plan(["data"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        runner = mock.Mock(side_effect=AssertionError("child started"))
        invalid = (
            self.root / "jq" / "audit.log",
            self.root / "jq.old" / "audit.log",
            self.root / ".portakit-stage-abc.tmp" / "audit.log",
            self.root / "other" / "audit.log",
            self.root / "audit.log",
        )
        for log in invalid:
            with self.subTest(path=log):
                with self.assertRaisesRegex(toolsets.core.PortakitError,
                                            ".portakit-evidence"):
                    toolsets.apply(plan, False, log, runner=runner)
                self.assertFalse(self.root.exists())
                self.assertFalse(log.exists())
        runner.assert_not_called()

    def test_mutating_apply_allows_explicit_reserved_evidence(self):
        """Existing dedicated evidence path survives the simulated tool install."""
        plan = self.plan(["data"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        folder = self.root / ".portakit-evidence"
        folder.mkdir(parents=True)
        log = folder / "apply.log"
        calls = []

        def success(cmd, **kwargs):
            name = cmd[cmd.index("install") + 1]
            calls.append(name)
            self.mark_managed(name)
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": name}, "error": None}), "")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = toolsets.apply(plan, False, log, runner=success)
        self.assertIsNone(result["failed"])
        self.assertEqual(result["installed"], ["jq"])
        self.assertEqual(calls, ["jq"])
        self.assertEqual(log.read_text(encoding="utf-8"), output.getvalue())
        self.assertTrue((self.root / "jq").exists())

    def test_apply_rejects_changed_selection_before_child_or_evidence(self):
        """A valid edited manifest cannot silently add, remove, or reorder tools.

        The first plan represents operator consent. The replan under batch
        lock can change installed status, not tool membership or pinned order.
        Only local JSON test data is changed; no vendor is launched.
        """
        source = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest = self.root.parent / "mutable-toolsets.json"
        for variation in ("added", "removed", "reordered"):
            with self.subTest(variation=variation):
                manifest.write_text(json.dumps(source), encoding="utf-8")
                plan = toolsets.create_plan(
                    ["minimal"], (), (), self.root, manifest)
                plan.update(include=[], exclude=[], manifest=manifest)
                self.assertEqual([item["id"] for item in plan["tools"]],
                                 ["notepad++", "winmerge"])
                edited = json.loads(manifest.read_text(encoding="utf-8"))
                profile = next(x for x in edited["profiles"]
                               if x["id"] == "minimal")
                if variation == "added":
                    profile["tools"].append("jq")
                elif variation == "removed":
                    profile["tools"].pop()
                else:
                    profile["tools"].reverse()
                manifest.write_text(json.dumps(edited), encoding="utf-8")
                log = self.root.parent / ("drift-" + variation + ".log")
                runner = mock.Mock(
                    side_effect=AssertionError("unexpected child execution"))
                with self.assertRaisesRegex(toolsets.ToolsetError,
                                            "selection or catalog pin changed"):
                    toolsets.apply(plan, False, log, runner=runner)
                runner.assert_not_called()
                self.assertFalse(log.exists())
                self.assertFalse((self.root / "notepad++").exists())
                self.assertFalse((self.root / "winmerge").exists())
                self.assertFalse((self.root / "jq").exists())

    def test_apply_allows_status_change_without_selection_or_pin_drift(self):
        """An independent matching install between plan and lock is skipped."""
        plan = self.plan(["data"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        self.mark_managed("jq")
        runner = mock.Mock(
            side_effect=AssertionError("already-installed must be skipped"))
        log = self.root.parent / "status-changed.log"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = toolsets.apply(plan, False, log, runner=runner)
        self.assertEqual(result, {"installed": [], "skipped": ["jq"],
                                  "failed": None})
        runner.assert_not_called()
        self.assertEqual(log.read_text(encoding="utf-8"), output.getvalue())
        self.assertIn("SKIP: jq", output.getvalue())

    def test_core_install_envelope_parser_without_running_installer(self):
        """A successful process exit must not replace strict envelope checks."""
        good = {"ok": True, "command": "install",
                "data": {"id": "jq"}, "error": None}
        payload = json.dumps(good)
        self.assertEqual(
            toolsets.parse_core_install_result(payload, "jq"), good)
        # Extra metadata has historically been allowed: keep compatibility.
        self.assertEqual(
            toolsets.parse_core_install_result(
                json.dumps(dict(good, extra="future")), "jq")["extra"],
            "future")
        invalid = (
            "",
            "null",
            "[]",
            "NaN",
            '{"ok":false,"ok":true,"command":"install",'
            '"data":{"id":"jq"},"error":null}',
            json.dumps(dict(good, error={"code": "blocked"})),
            json.dumps(dict(good, data={"id": "other"})),
            json.dumps(dict(good, command="update")),
        )
        for item in invalid:
            with self.subTest(payload=item):
                with self.assertRaises((ValueError, TypeError)):
                    toolsets.parse_core_install_result(item, "jq")

    def test_managed_postcheck_is_separate_from_core_json(self):
        """A valid child envelope never substitutes for persisted state."""
        catalog = toolsets.core.load_catalog(toolsets.core.DEFAULT_CATALOG)
        row = self.plan(["data"])["tools"][0]
        with self.assertRaisesRegex(toolsets.ToolsetError,
                                    "managed install not confirmed: install"):
            toolsets.verify_managed_install(row, catalog, self.root)
        self.mark_managed("jq")
        self.assertIsNone(
            toolsets.verify_managed_install(row, catalog, self.root))
        changed_pin = dict(row, sha256="f" * 64)
        with self.assertRaisesRegex(toolsets.ToolsetError,
                                    "catalog pin changed since preflight"):
            toolsets.verify_managed_install(changed_pin, catalog, self.root)
        # A receipt without a populated folder cannot pass the check.
        target = self.root / catalog["jq"]["dest"] / "fixture-payload.txt"
        target.unlink()
        with self.assertRaisesRegex(toolsets.ToolsetError, "blocked-empty"):
            toolsets.verify_managed_install(row, catalog, self.root)

    def test_apply_installs_each_unique_id_once_and_logs_verbatim(self):
        p = self.plan(["mes-support", "developer"])
        p.update(include=[], exclude=[], manifest=self.manifest)
        calls = []

        def runner(cmd, **kwargs):
            calls.append(list(cmd))
            app = cmd[cmd.index("install") + 1]
            self.mark_managed(app)
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": app}, "error": None}), "")
        log = self.root.parent / "test-result.log"
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
            self.mark_managed(app)
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": app}}), "")
        log = self.root.parent / "evidence.log"
        with contextlib.redirect_stdout(io.StringIO()):
            result = toolsets.apply(p, False, log, runner=runner)
        self.assertEqual(calls, ["notepad++", "winmerge"])
        self.assertEqual(result["installed"], ["notepad++"])
        self.assertEqual(result["failed"], "winmerge")
        self.assertIn("PARTIAL:", log.read_text(encoding="utf-8"))

    def test_success_json_without_written_state_fails_closed_and_stops_batch(self):
        plan = self.plan(["mes-support"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        calls = []

        def fake_success(cmd, **kwargs):
            name = cmd[cmd.index("install") + 1]
            calls.append(name)
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"ok": True, "command": "install",
                                    "data": {"id": name}, "error": None}), "")

        log = self.root.parent / "missing-receipt.log"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = toolsets.apply(plan, False, log, runner=fake_success)
        self.assertEqual(calls, ["notepad++"])
        self.assertEqual(result["installed"], [])
        self.assertEqual(result["failed"], "notepad++")
        self.assertIn("managed install not confirmed: install", output.getvalue())
        self.assertEqual(log.read_text(encoding="utf-8"), output.getvalue())

    def test_success_json_with_mismatched_or_missing_managed_target_fails(self):
        for kind in ("missing-directory", "wrong-pin", "empty-directory"):
            with self.subTest(kind=kind):
                # Per-case disposable install root avoids carrying state between runs.
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "portable"
                    plan = toolsets.create_plan(
                        ["data"], (), (), root, self.manifest)
                    plan.update(include=[], exclude=[], manifest=self.manifest)

                    def fake_success(cmd, **kwargs):
                        pin = toolsets.core.load_catalog(
                            toolsets.core.DEFAULT_CATALOG)["jq"]
                        root.mkdir(parents=True, exist_ok=True)
                        if kind in ("wrong-pin", "empty-directory"):
                            (root / pin["dest"]).mkdir()
                        toolsets.core.write_state(root, {"jq": {
                            "version": pin["version"], "dest": pin["dest"],
                            "sha256": ("f" * 64 if kind == "wrong-pin"
                                       else pin["sha256"]),
                        }})
                        return subprocess.CompletedProcess(
                            cmd, 0, json.dumps({"ok": True, "command": "install",
                                                "data": {"id": "jq"},
                                                "error": None}), "")

                    log = root.parent / "post-check.log"
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = toolsets.apply(
                            plan, False, log, runner=fake_success)
                    self.assertEqual(result["installed"], [])
                    self.assertEqual(result["failed"], "jq")
                    self.assertIn("post-install check:", log.read_text("utf-8"))

    def test_unbounded_old_core_response_is_now_rejected(self):
        plan = self.plan(["minimal"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        # A zero-exit fake installer cannot forge overlapping success fields.
        def duplicate_json(cmd, **kwargs):
            name = cmd[cmd.index("install") + 1]
            fake = ('{"ok": false, "ok": true, "command": "install", '
                    '"data": {"id": "' + name + '"}, "error": null}')
            return subprocess.CompletedProcess(cmd, 0, fake, "")
        log = self.root.parent / "duplicate-installer-result.log"
        with contextlib.redirect_stdout(io.StringIO()):
            result = toolsets.apply(plan, False, log, runner=duplicate_json)
        self.assertEqual(result["failed"], "notepad++")
        self.assertEqual(result["installed"], [])
        self.assertIn("invalid core result", log.read_text("utf-8"))
        self.assertIn("Duplicate JSON key", log.read_text("utf-8"))

    def test_core_child_envelope_error_with_zero_exit_blocks(self):
        plan = self.plan(["minimal"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        def fake_error(cmd, **kwargs):
            name = cmd[cmd.index("install") + 1]
            payload = {"ok": True, "command": "install",
                       "data": {"id": name}, "error": {"code": "unverified"}}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        log = self.root.parent / "failed-envelope.log"
        with contextlib.redirect_stdout(io.StringIO()):
            result = toolsets.apply(plan, False, log, runner=fake_error)
        self.assertEqual(result["failed"], "notepad++")
        self.assertEqual(result["installed"], [])
        self.assertIn("invalid core result", log.read_text("utf-8"))

    def test_bounded_process_failure_aborts_without_next_tool(self):
        plan = self.plan(["minimal"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        invocations = []
        def blocked(cmd, *, timeout_seconds):
            invocations.append((cmd, timeout_seconds))
            raise toolsets.bounded.BoundedProcessError("OUTPUT_LIMIT")
        log = self.root.parent / "bounded-error.log"
        with mock.patch.object(toolsets.bounded, "run_bounded", side_effect=blocked):
            with contextlib.redirect_stdout(io.StringIO()):
                result = toolsets.apply(plan, False, log, child_timeout=7)
        self.assertEqual(result["installed"], [])
        self.assertEqual(result["failed"], "notepad++")
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0][1], 7)
        self.assertIn("OUTPUT_LIMIT", log.read_text("utf-8"))
        self.assertIn("PARTIAL:", log.read_text("utf-8"))
        self.assertIn("CHILD_TIMEOUT_SECONDS: 7", log.read_text("utf-8"))

    def test_invalid_apply_timeout_rejected_before_writes(self):
        plan = self.plan(["minimal"])
        plan.update(include=[], exclude=[], manifest=self.manifest)
        for invalid in (None, 0, -1, 3601, True, 5.0, "6"):
            with self.subTest(timeout=invalid):
                with self.assertRaisesRegex(toolsets.ToolsetError, "child_timeout"):
                    toolsets.apply(plan, False, self.root / "no.log",
                                   runner=mock.Mock(), child_timeout=invalid)
                self.assertFalse(self.root.exists())

    def test_cli_timeout_restricted_to_apply_and_must_be_valid(self):
        for args in (["list", "--child-timeout", "1"],
                     ["plan", "minimal", "--child-timeout", "1"]):
            with self.subTest(args=args):
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(toolsets.main(args + ["--root", str(self.root)]), 1)
                self.assertFalse(self.root.exists())
        for value in ("0", "-1", "3601"):
            with self.subTest(value=value):
                args = ["apply", "minimal", "--yes", "--child-timeout", value,
                        "--root", str(self.root)]
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(toolsets.main(args), 1)
                self.assertIn("child_timeout", error.getvalue())
                self.assertFalse(self.root.exists())

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
