"""Headless, source-only tests for lightweight research gate; no vendor binaries."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lightweight_review", ROOT / "scripts" / "lightweight_review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class LightweightReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.folder = Path(self.directory)
        self.data = review.load_ledger()
        self.by_id = {x["id"]: x for x in self.data["candidates"]}

    def write_ledger(self, value):
        path = self.folder / "staged.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_three_current_candidates_and_research_stage(self):
        self.assertEqual(set(self.by_id), {"duckdb-cli", "xsv", "tailviewer"})
        self.assertEqual(len(self.data["requiredIndependentGates"]), 8)
        pins, _, _, known = review.kit.inventory()
        for ident, rec in self.by_id.items():
            self.assertNotIn(ident, pins)
            self.assertEqual(known[ident]["admission"], "RESEARCH_ONLY")
            self.assertEqual(known[ident]["primary"], rec["primary"])
            self.assertEqual(rec["stage"], "RESEARCH_ONLY")
        self.assertEqual(review.load_ledger()["admissionDecision"],
                         "RESEARCH_ONLY_NOT_INSTALLABLE")

    def test_release_digest_is_only_metadata_not_original_verification(self):
        expected = ("91663c2f36c2a334b0e5e639006d8c29c29e013af0c477d80bb931df68870312")
        self.assertEqual(self.by_id["duckdb-cli"]["sha256FromReleaseMetadata"],
                         expected)
        self.assertEqual(self.by_id["duckdb-cli"]["assetBytesFromMetadata"],
                         19663611)
        for ident in ("xsv", "tailviewer"):
            self.assertIsNone(self.by_id[ident]["sha256FromReleaseMetadata"])
        results = review.assess(self.data)["tools"]
        self.assertTrue(all(t["status"] == "NOT_ADMITTED" for t in results))
        self.assertTrue(all("originalSha256LocallyVerified" in t["blockedBy"]
                            for t in results))
        self.assertEqual([x["id"] for x in results],
                         sorted(self.by_id))

    def test_format_and_maintenance_blocks_distinct(self):
        report = review.assess(self.data)
        statuses = {x["id"]: x["blockedBy"] for x in report["tools"]}
        self.assertIn("currentCoreDoesNotAcceptArchiveType", statuses["duckdb-cli"])
        self.assertNotIn("currentCoreDoesNotAcceptArchiveType", statuses["xsv"])
        self.assertIn("vendorReleaseDidNotPublishSHA256InAPI", statuses["xsv"])
        self.assertIn("vendorReleaseDidNotPublishSHA256InAPI",
                      statuses["tailviewer"])
        self.assertIn("upstreamArchivedMaintenanceDecision", statuses["xsv"])
        self.assertNotIn("upstreamArchivedMaintenanceDecision",
                         statuses["tailviewer"])
        self.assertIn('("zip", "exe", "sfx7z")',
                      (ROOT / "portakit.py").read_text(encoding="utf-8"))

    def test_subset_dedup_order_without_original_writes(self):
        selected = review.assess(self.data, ["tailviewer", "tailviewer", "xsv"])
        self.assertEqual([x["id"] for x in selected["tools"]],
                         ["tailviewer", "xsv"])
        self.assertEqual(selected["outcome"], "RESEARCH_ONLY_NOT_INSTALLABLE")
        self.assertFalse(list(self.folder.iterdir()))

    def test_empty_unknown_null_and_nonlist_choices_fail_closed(self):
        for invalid in ([], None if False else ["missing"], [None],
                        ["duckdb-cli", "bogus"], "xsv", {"xsv"}):
            with self.subTest(invalid=str(invalid)):
                with self.assertRaises(review.ResearchError):
                    review.assess(self.data, invalid)

    def test_reject_relabel_as_ready_or_catalog_collision(self):
        data = copy.deepcopy(self.data)
        data["candidates"][0]["stage"] = "READY"
        with self.assertRaisesRegex(review.ResearchError, "admission"):
            review.load_ledger(self.write_ledger(data))
        data = copy.deepcopy(self.data)
        data["candidates"][0]["id"] = "jq"
        with self.assertRaisesRegex(review.ResearchError, "admission"):
            review.load_ledger(self.write_ledger(data))
        data = copy.deepcopy(self.data)
        data["candidates"].append(copy.deepcopy(data["candidates"][0]))
        with self.assertRaisesRegex(review.ResearchError, "admission"):
            review.load_ledger(self.write_ledger(data))

    def test_reject_missing_or_invalid_release_details(self):
        changes = [
            ("sha256FromReleaseMetadata", "xyz", "SHA"),
            ("assetBytesFromMetadata", True, "size"),
            ("assetBytesFromMetadata", 0, "size"),
            ("artifactType", "rar", "type"),
            ("assetName", "../duckdb.zip", "mismatch"),
            ("assetURL", "http://evil.example/download", "mismatch"),
            ("repoArchived", "false", "archived"),
            ("sources", [], "source"),
            ("publishedAt", "", "field")
        ]
        for field, bad, message in changes:
            with self.subTest(field=field, bad=bad):
                data = copy.deepcopy(self.data)
                data["candidates"][0][field] = bad
                with self.assertRaisesRegex(review.ResearchError, message):
                    review.load_ledger(self.write_ledger(data))

    def test_invalid_schema_and_missing_gates_rejected(self):
        for mutation in ("version", "empty", "duplicate", "admitted"):
            data = copy.deepcopy(self.data)
            if mutation == "version":
                data["schemaVersion"] = 2
            elif mutation == "empty":
                data["requiredIndependentGates"] = []
            elif mutation == "duplicate":
                data["requiredIndependentGates"][0] = data["requiredIndependentGates"][1]
            elif mutation == "admitted":
                data["admissionDecision"] = "READY"
            with self.subTest(mutation=mutation):
                with self.assertRaises(review.ResearchError):
                    review.load_ledger(self.write_ledger(data))

    def test_cli_is_read_only_no_vendor_calls_or_output_file_default(self):
        import subprocess
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(review.kit.core, "download",
                               side_effect=AssertionError("vendor download")):
            with mock.patch.object(subprocess, "run",
                                   side_effect=AssertionError("vendor execution")):
                with mock.patch.object(review.kit.sets, "apply",
                                       side_effect=AssertionError("installation")):
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        rc = review.run(["--id", "xsv"])
        self.assertEqual(rc, 2)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("RESEARCH_ONLY_NOT_INSTALLABLE", stdout.getvalue())
        self.assertIn("upstreamArchivedMaintenanceDecision", stdout.getvalue())
        self.assertFalse(list(self.folder.iterdir()))

    def test_cli_report_new_only_and_exact_console_log(self):
        target = self.folder / "evidence.json"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = review.run(["--id", "duckdb-cli", "--out", str(target)])
        self.assertEqual(rc, 2)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(out.getvalue(), target.with_suffix(".log").read_text("utf-8"))
        data = json.loads(target.read_text("utf-8"))
        self.assertEqual(data["tools"][0]["id"], "duckdb-cli")
        self.assertIn("currentCoreDoesNotAcceptArchiveType",
                      data["tools"][0]["blockedBy"])
        before = (target.read_bytes(), target.with_suffix(".log").read_bytes())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = review.run(["--out", str(target)])
        self.assertEqual(rc, 1)
        self.assertIn("already exists", err.getvalue())
        self.assertEqual((target.read_bytes(), target.with_suffix(".log").read_bytes()),
                         before)

    def test_ledger_source_only_and_no_install_catalog_mutation(self):
        source = (ROOT / "scripts" / "lightweight_review.py").read_text("utf-8")
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("urlopen(", source)
        self.assertNotIn("download(", source)
        self.assertNotIn(".apply(", source)
        self.assertFalse((self.folder / "portable").exists())


if __name__ == "__main__":
    unittest.main()
