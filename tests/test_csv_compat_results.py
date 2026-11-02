"""Read-only semantic checker tests: all output data simulated in Python."""
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
    "portakit_csv_compat_checker", ROOT / "scripts" /
    "csv_compat_results.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


def csv_bytes(header, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


class CSVCompatibilityResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        self.source = self.root / "matrix"
        self.outputs = self.root / "captured"
        with contextlib.redirect_stdout(io.StringIO()):
            check.matrix.prepare(self.source)
        self.outputs.mkdir()

    def write_results(self):
        rows = check.matrix.GROUP_ROWS[1:]
        ordered = sorted(rows, key=lambda row: int(row[1]))
        self.result("miller-sort.csv", csv_bytes(
            ["category", "qty", "id"], ordered))
        self.result("xan-sort.csv", csv_bytes(
            ["id", "qty", "category"],
            [[r[2], r[1] + ".0", r[0]] for r in ordered]))
        self.result("miller-group.csv", csv_bytes(
            ["category", "qty_sum"], [["A", "14"], ["B", "11"]]))
        self.result("xan-group.csv", csv_bytes(
            ["qty_sum", "category"], [["11.0", "B"], ["14.00", "A"]]))

    def result(self, name, content):
        (self.outputs / name).write_bytes(content)

    def test_plan_only_no_files_or_vendor_process(self):
        out, err = io.StringIO(), io.StringIO()
        before = sorted(self.root.rglob("*"))
        with mock.patch.object(subprocess, "Popen",
                               side_effect=AssertionError("vendor invoked")):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = check.run([])
        self.assertEqual((code, err.getvalue()), (2, ""))
        self.assertIn("PLAN_ONLY", out.getvalue())
        self.assertEqual(before, sorted(self.root.rglob("*")))

    def test_four_simulated_result_files_match_semantics_only(self):
        self.write_results()
        result = check.inspect(self.source, self.outputs)
        self.assertEqual(result["outcome"], "SEMANTIC_MATCH_ONLY")
        self.assertTrue(result["syntheticInputVerified"])
        self.assertEqual([r["status"] for r in result["results"]],
                         ["MATCH"] * 4)
        self.assertEqual(result["vendorExecution"], "NOT_OBSERVED")
        self.assertEqual(result["vendorExitAndStderr"], "NOT_OBSERVED")
        self.assertEqual(result["companyApproval"], "NOT_VERIFIED")
        self.assertEqual(result["performanceRanking"], "NOT_ASSESSED")

    def test_missing_result_is_incomplete_and_never_inferred_pass(self):
        self.write_results()
        (self.outputs / "xan-group.csv").unlink()
        result = check.inspect(self.source, self.outputs)
        self.assertEqual(result["outcome"], "INCOMPLETE_OR_MISMATCH")
        self.assertEqual(result["results"][-1]["status"], "MISSING")
        self.assertIsNone(result["results"][-1]["sha256"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check.run(["--fixtures-dir", str(self.source),
                                        "--results-dir", str(self.outputs)]), 2)

    def test_numeric_lexical_wrong_order_and_duplicates_refused(self):
        self.write_results()
        original = check.matrix.GROUP_ROWS[1:]
        lexical = sorted(original, key=lambda row: row[1])
        self.result("xan-sort.csv", csv_bytes(
            ["category", "qty", "id"], lexical))
        self.assertEqual(check.inspect(self.source, self.outputs)["results"][1]
                         ["status"], "MISMATCH")
        self.result("xan-sort.csv", csv_bytes(
            ["category", "qty", "id"], [original[3]] * 5))
        self.assertEqual(check.inspect(self.source, self.outputs)["results"][1]
                         ["status"], "MISMATCH")

    def test_group_extra_missing_duplicate_or_wrong_total_refused(self):
        self.write_results()
        bad_rows = (
            [["A", "13"], ["B", "11"]],
            [["A", "14"]],
            [["A", "14"], ["A", "11"]],
            [["A", "14"], ["B", "11"], ["Z", "1"]],
            [["A", "-14"], ["B", "11"]],
            [["A", "NaN"], ["B", "11"]],
        )
        for rows in bad_rows:
            with self.subTest(rows=rows):
                self.result("miller-group.csv", csv_bytes(
                    ["category", "qty_sum"], rows))
                self.assertEqual(
                    check.inspect(self.source, self.outputs)["results"][2]
                    ["status"], "MISMATCH")

    def test_wrong_header_encoding_or_unclosed_csv_refused(self):
        self.write_results()
        for bad in (b"\xff", b"id,qty,category\nr4,1,A\n",
                    b'category,qty,id\nA,"unterminated\n',
                    'category,qty,id\nA,1,r4\n'.encode("utf-16le"),
                    csv_bytes(["category", "category", "id"], [
                        ["A", "1", "r4"]] * 5)):
            with self.subTest(size=len(bad), body=bad[:16]):
                self.result("miller-sort.csv", bad)
                self.assertEqual(check.inspect(self.source, self.outputs)
                                 ["results"][0]["status"], "MISMATCH")

    def test_tampered_source_bytes_and_manifest_never_verified(self):
        self.write_results()
        p = self.source / "sort-group.csv"
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaisesRegex(check.ComparisonError, "fixture changed"):
            check.inspect(self.source, self.outputs)
        p.write_bytes(check.matrix.fixtures()["sort-group.csv"])
        manifest = self.source / "matrix.json"
        manifest.write_bytes(manifest.read_bytes().replace(
            b'"vendorExecution": "NOT_RUN"',
            b'"vendorExecution": "CLAIMED_RUN"'))
        with self.assertRaisesRegex(check.ComparisonError, "manifest differs"):
            check.inspect(self.source, self.outputs)

    def test_corrupted_transcript_is_refused(self):
        self.write_results()
        log = self.source / "matrix.log"
        log.write_bytes(b"FORGED CONSOLE\n")
        with self.assertRaisesRegex(check.evidence.EvidenceError,
                                    "Console transcript"):
            check.inspect(self.source, self.outputs)

    def test_console_and_optional_exact_create_only_evidence(self):
        self.write_results()
        path = self.root / "output.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = check.run(["--fixtures-dir", str(self.source),
                            "--results-dir", str(self.outputs),
                            "--out", str(path)])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), path.with_suffix(".log").read_text(
            encoding="utf-8"))
        self.assertEqual(json.loads(path.read_text("utf-8"))["outcome"],
                         "SEMANTIC_MATCH_ONLY")
        before = (path.read_bytes(), path.with_suffix(".log").read_bytes())
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(check.run([
                "--fixtures-dir", str(self.source),
                "--results-dir", str(self.outputs), "--out", str(path)]), 1)
        self.assertIn("already exists", err.getvalue())
        self.assertEqual(before, (path.read_bytes(),
                                 path.with_suffix(".log").read_bytes()))

    def test_outside_only_output_and_invalid_usage(self):
        self.write_results()
        for inside in (self.source / "oops.json",
                       self.outputs / "oops.json"):
            with self.subTest(inside=inside):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc = check.run(["--fixtures-dir", str(self.source),
                                    "--results-dir", str(self.outputs),
                                    "--out", str(inside)])
                self.assertEqual(rc, 1)
                self.assertIn("outside input", err.getvalue())
                self.assertFalse(inside.exists())
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(check.run(["--fixtures-dir", str(self.source)]), 1)
        self.assertIn("Both", err.getvalue())

    def test_no_vendor_execution_or_mutations_when_verifying(self):
        self.write_results()
        before = [(str(p), p.read_bytes()) for p in self.root.rglob("*")
                  if p.is_file()]
        with mock.patch.object(subprocess, "Popen",
                               side_effect=AssertionError("vendor execution")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check.run([
                    "--fixtures-dir", str(self.source),
                    "--results-dir", str(self.outputs)]), 0)
        after = [(str(p), p.read_bytes()) for p in self.root.rglob("*")
                 if p.is_file()]
        self.assertEqual(before, after)
        source = (ROOT / "scripts" / "csv_compat_results.py").read_text("utf-8")
        for forbidden in ("subprocess.Popen(", "subprocess.run(", "download(",
                          "urlopen(", "os.system(", ".apply("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
