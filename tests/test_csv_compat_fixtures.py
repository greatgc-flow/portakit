"""Source-only matrix fixtures; no vendor binaries, network or approvals."""
import codecs
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "csv_compat_fixtures", ROOT / "scripts" / "csv_compat_fixtures.py")
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


class CSVCompatibilityFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.base = Path(self.temp)
        self.dest = self.base / "new-matrix"

    def test_default_is_read_only_plan_without_vendor_processes(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(subprocess, "Popen",
                               side_effect=AssertionError("vendor execution")):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = matrix.run([])
        self.assertEqual((code, err.getvalue()), (2, ""))
        self.assertIn("PLAN_ONLY", out.getvalue())
        self.assertIn("NOT_VENDOR_TESTED", out.getvalue())
        self.assertFalse(list(self.base.iterdir()))

    def test_exact_bom_unicode_and_malformed_bytes_are_synthetic(self):
        items = matrix.fixtures()
        self.assertEqual(set(items), set(matrix.CASE_NOTES))
        self.assertLess(sum(map(len, items.values())), matrix.MAX_TOTAL_BYTES)
        self.assertEqual(items["edge-utf8-bom.csv"],
                         codecs.BOM_UTF8 + items["edge-utf8.csv"])
        self.assertEqual(items["edge-utf16le.csv"][:2],
                         codecs.BOM_UTF16_LE)
        self.assertEqual(items["edge-utf16le.csv"][2:].decode("utf-16le"),
                         items["edge-utf8.csv"].decode("utf-8"))
        self.assertIn("한글".encode("utf-8"), items["edge-utf8.csv"])
        self.assertIn(b'"unterminated\r\n', items["malformed-quote.csv"])
        self.assertEqual(
            list(csv.reader(io.StringIO(items["edge-utf8.csv"].decode("utf-8")))),
            matrix.smoke.EDGE_ROWS)
        self.assertEqual(matrix.manifest(items)["vendorExecution"], "NOT_RUN")

    def test_numeric_sort_is_not_lexical_and_group_sum_is_exact(self):
        reference = matrix.reference()
        self.assertEqual(reference["sortQtyAscendingIds"],
                         ["r4", "r2", "r5", "r3", "r1"])
        self.assertEqual(reference["groupQtySumByCategory"], {"A": 14, "B": 11})
        records = list(csv.DictReader(io.StringIO(
            matrix.fixtures()["sort-group.csv"].decode("utf-8"))))
        self.assertEqual([r["id"] for r in sorted(
            records, key=lambda r: int(r["qty"]))],
            reference["sortQtyAscendingIds"])
        self.assertEqual([r["qty"] for r in sorted(
            records, key=lambda r: r["qty"])],
            ["1", "10", "2", "3", "9"])
        self.assertEqual(reference["otherCases"],
                         "OBSERVE_VENDOR_BEHAVIOR_NO_PREDECLARED_PASS")

    def test_new_only_outputs_retain_exact_console_evidence_and_sha(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = matrix.run(["--out-dir", str(self.dest)])
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertEqual(out.getvalue(),
                         (self.dest / "matrix.log").read_text("utf-8"))
        report = json.loads((self.dest / "matrix.json").read_text("utf-8"))
        self.assertEqual(report["outcome"], "PREPARED_ONLY_NOT_VENDOR_TESTED")
        self.assertEqual(len(report["files"]), 5)
        for rec in report["files"]:
            data = (self.dest / rec["name"]).read_bytes()
            self.assertEqual((rec["bytes"], rec["sha256"]),
                             (len(data), matrix.hashlib.sha256(data).hexdigest()))
        self.assertEqual(set(p.name for p in self.dest.iterdir()),
                         set(matrix.CASE_NOTES) | {"matrix.json", "matrix.log"})
        self.assertIn("REPORT: " + str(self.dest / "matrix.json"), out.getvalue())

    def test_existing_directory_is_never_modified_or_used(self):
        self.dest.mkdir()
        protected = self.dest / "notes.txt"
        protected.write_bytes(b"PRESERVE-EXISTING-CONTENTS")
        with self.assertRaisesRegex(matrix.FixtureError, "already exists"):
            matrix.prepare(self.dest)
        self.assertEqual(list(self.dest.iterdir()), [protected])
        self.assertEqual(protected.read_bytes(), b"PRESERVE-EXISTING-CONTENTS")
        with self.assertRaisesRegex(matrix.FixtureError, "nonempty"):
            matrix.prepare("")
        with self.assertRaisesRegex(matrix.FixtureError, "nonempty"):
            matrix.prepare(None)

    def test_late_evidence_error_leaves_partial_files_for_manual_review(self):
        """Never claim completion or automatically erase generated directories."""
        with mock.patch.object(matrix.evidence_io, "emit_json_report",
                               side_effect=OSError("synthetic report write error")):
            with self.assertRaisesRegex(OSError, "report write error"):
                matrix.prepare(self.dest)
        self.assertTrue(self.dest.is_dir())
        self.assertFalse((self.dest / "matrix.json").exists())
        self.assertFalse((self.dest / "matrix.log").exists())
        self.assertEqual(set(p.name for p in self.dest.iterdir()),
                         set(matrix.CASE_NOTES))
        original = (self.dest / "edge-utf8.csv").read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(matrix.run(["--out-dir", str(self.dest)]), 1)
        self.assertIn("already exists", stderr.getvalue())
        self.assertEqual((self.dest / "edge-utf8.csv").read_bytes(), original)

    def test_injected_unsafe_output_link_rejected_before_creation(self):
        with mock.patch.object(matrix.kit.core, "check_links",
                               side_effect=matrix.kit.core.PortakitError(
                                   "state", "synthetic reparse boundary")):
            with self.assertRaisesRegex(
                    matrix.kit.core.PortakitError, "reparse"):
                matrix.prepare(self.dest)
        self.assertFalse(self.dest.exists())

    def test_documented_miller_sort_is_numeric_ascending(self):
        """Upstream Miller -n asc differs from -nr descending."""
        guide = (ROOT / "docs" / "CSV_COMPAT_MATRIX.md").read_text("utf-8")
        self.assertIn("mlr --csv sort -n qty sort-group.csv", guide)
        self.assertNotIn("mlr --csv sort -nr qty sort-group.csv", guide)
        self.assertIn("xan sort --numeric --select qty", guide)

    def test_no_vendor_download_or_default_candidate_admission(self):
        source = (ROOT / "scripts" / "csv_compat_fixtures.py").read_text("utf-8")
        for forbidden in ("subprocess.Popen(", "subprocess.run(", "urlopen(",
                          "download(", "os.system(", ".apply("):
            self.assertNotIn(forbidden, source)
        self.assertNotIn('"id": "xan"', (ROOT / "catalog.json").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
