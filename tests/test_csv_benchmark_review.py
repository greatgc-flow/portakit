"""Source-only paired benchmark record checks: never execute real vendors."""
import contextlib
import hashlib
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
    "portakit_csv_benchmark_review", ROOT / "scripts" / "csv_benchmark_review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class CSVBenchmarkEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.base = Path(self.tmp)
        self.csv = self.base / "synthetic.csv"
        self.csv.write_bytes(b"category,qty\r\nA,2\r\nB,10\r\nA,9\r\n")
        self.input = self.base / "observations.json"
        self.template = json.loads(
            (ROOT / "research" / "CSV_BENCHMARK_TEMPLATE.json").read_text("utf-8"))

    def full_record(self, n=5):
        data = self.csv.read_bytes()
        doc = dict(self.template)
        doc.update({
            "inputSha256": hashlib.sha256(data).hexdigest(),
            "inputBytes": len(data),
            "inputRows": 3,
            "toolSha256": {"miller": "a" * 64, "xan": "b" * 64},
            "environmentNote": "operator-private-same-host",
            "coldMethod": "operator-described reset; NOT OS-verified",
            "runs": [],
        })
        for phase in review.PHASES:
            for trial in range(1, n + 1):
                tools = review.TOOLS if trial % 2 else tuple(
                    reversed(review.TOOLS))
                for tool in tools:
                    doc["runs"].append({
                        "tool": tool, "phase": phase, "trial": trial,
                        "elapsedMs": (20 if phase == "cold" else 10) +
                                     (2 if tool == "miller" else 0) + trial,
                        "cpuMs": None, "peakRssBytes": None,
                        "diskWrittenBytes": None,
                        "exitCode": 0, "stderrBytes": 0,
                        "semanticStatus": "MATCH",
                    })
        return doc

    def write_record(self, record):
        self.input.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    def test_default_plan_only_no_files_and_no_vendor_process(self):
        before = list(self.base.iterdir())
        stdout = io.StringIO()
        with mock.patch.object(subprocess, "Popen",
                               side_effect=AssertionError("vendor execution")):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(review.run([]), 2)
        self.assertIn("PLAN_ONLY", stdout.getvalue())
        self.assertEqual(before, list(self.base.iterdir()))

    def test_empty_public_template_is_incomplete_not_approved(self):
        self.write_record(self.template)
        output = review.inspect(self.template, self.csv)
        self.assertEqual(output["outcome"], "INCOMPLETE_OR_BLOCKED")
        self.assertFalse(output["sourceBytesAndRowsVerified"])
        self.assertEqual(output["groups"], [])
        self.assertEqual(output["performanceRanking"], "NOT_ASSESSED")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.run(["--input", str(self.input),
                                         "--dataset", str(self.csv)]), 2)

    def test_five_paired_cold_and_warm_trials_only_describe_times(self):
        doc = self.full_record()
        result = review.inspect(doc, self.csv)
        self.assertEqual(result["outcome"], "DESCRIPTIVE_TIMING_ONLY")
        self.assertTrue(result["sourceBytesAndRowsVerified"])
        self.assertEqual(result["trialsPerToolPhase"], 5)
        self.assertEqual(len(result["groups"]), 4)
        group = next(x for x in result["groups"]
                     if x["phase"] == "warm" and x["tool"] == "miller")
        self.assertEqual((group["minMs"], group["medianMs"], group["maxMs"]),
                         (13, 15, 17))
        self.assertEqual(group["cpuMetric"], "NOT_MEASURED_OR_PARTIAL")
        self.assertEqual(result["vendorRuntime"],
                         "OPERATOR_DECLARED_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["publisherAuthenticity"], "NOT_VERIFIED")
        self.assertEqual(result["companyApproval"], "NOT_VERIFIED")

    def test_partial_or_unbalanced_runs_never_have_performance_summary(self):
        for record in (self.full_record(4), self.full_record(5)):
            if len(record["runs"]) == 20:
                record["runs"].pop()
            with self.subTest(count=len(record["runs"])):
                result = review.inspect(record, self.csv)
                self.assertEqual(result["outcome"], "INCOMPLETE_OR_BLOCKED")
                self.assertEqual(result["groups"], [])

    def test_wrong_execution_order_cannot_be_mislabeled_balanced(self):
        record = self.full_record()
        record["runs"][0], record["runs"][1] = (
            record["runs"][1], record["runs"][0])
        self.assertEqual(review.inspect(record, self.csv)["outcome"],
                         "INCOMPLETE_OR_BLOCKED")

    def test_error_warning_or_semantics_unverified_prevents_summary(self):
        for changes in (
            {"exitCode": 2},
            {"stderrBytes": 6},
            {"semanticStatus": "MISMATCH"},
            {"semanticStatus": "NOT_VERIFIED"},
            {"exitCode": None},
        ):
            doc = self.full_record()
            doc["runs"][0].update(changes)
            with self.subTest(changes=changes):
                result = review.inspect(doc, self.csv)
                self.assertEqual(result["outcome"], "INCOMPLETE_OR_BLOCKED")
                self.assertEqual(result["groups"], [])

    def test_invalid_measurement_schema_duplicates_booleans_and_nan_refused(self):
        changes = (
            lambda d: d["runs"].append(dict(d["runs"][0])),
            lambda d: d["runs"][0].update({"elapsedMs": True}),
            lambda d: d["runs"][0].update({"elapsedMs": float("nan")}),
            lambda d: d["runs"][0].update({"cpuMs": -1}),
            lambda d: d["runs"][0].update({"peakRssBytes": False}),
            lambda d: d["runs"][0].update({"extraApproval": "YES"}),
            lambda d: d.update({"performanceWinner": "xan"}),
            lambda d: d.update({"inputBytes": True}),
        )
        for action in changes:
            doc = self.full_record()
            action(doc)
            with self.subTest(case=str(action)):
                with self.assertRaises(review.BenchmarkError):
                    review.inspect(doc, self.csv)

    def test_wrong_actual_sha_bytes_or_row_count_rejected(self):
        for field, value, expected in (
            ("inputSha256", "0" * 64, "Actual dataset"),
            ("inputBytes", 10, "Actual dataset"),
            ("inputRows", 99, "row count"),
        ):
            doc = self.full_record()
            doc[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(review.BenchmarkError, expected):
                    review.inspect(doc, self.csv)
        doc = self.full_record()
        self.csv.write_bytes(self.csv.read_bytes() + b"changed")
        with self.assertRaisesRegex(review.BenchmarkError, "Actual dataset"):
            review.inspect(doc, self.csv)

    def test_duplicate_csv_header_names_fail_closed_even_with_matching_hash(self):
        """A self-consistent SHA/row count must not bless ambiguous column names."""
        self.csv.write_bytes(
            b"category,category,qty\r\nA,Z,2\r\nB,Y,10\r\nA,X,9\r\n")
        doc = self.full_record()
        self.assertEqual(doc["inputRows"], 3)
        with self.assertRaisesRegex(review.BenchmarkError, "duplicate columns"):
            review.inspect(doc, self.csv)
        self.write_record(doc)
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(review.run([
                "--input", str(self.input), "--dataset", str(self.csv)]), 1)
        self.assertIn("duplicate columns", stderr.getvalue())

    def test_whitespace_only_header_rejected_despite_valid_hash_and_rows(self):
        """Blank-but-truthy header fields must not receive source verification."""
        for blank in (b" ", b"\t", b"  \t"):
            with self.subTest(blank=blank):
                self.csv.write_bytes(
                    b"category," + blank + b"\r\n"
                    b"A,2\r\nB,10\r\nA,9\r\n")
                doc = self.full_record()
                with self.assertRaisesRegex(review.BenchmarkError, "header invalid"):
                    review.inspect(doc, self.csv)
                self.write_record(doc)
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    rc = review.run(["--input", str(self.input),
                                     "--dataset", str(self.csv)])
                self.assertEqual(rc, 1)
                self.assertIn("header invalid", stderr.getvalue())

    def test_space_only_operator_notes_fail_even_with_complete_trials(self):
        """A blank environment or cold-cache method is not documented evidence."""
        for field in ("environmentNote", "coldMethod"):
            for blank in (" ", "     "):
                with self.subTest(field=field, blank=blank):
                    doc = self.full_record()
                    doc[field] = blank
                    with self.assertRaisesRegex(
                            review.BenchmarkError, "Invalid local method note"):
                        review.inspect(doc, self.csv)
                    self.write_record(doc)
                    with contextlib.redirect_stderr(io.StringIO()) as stderr:
                        rc = review.run(["--input", str(self.input),
                                         "--dataset", str(self.csv)])
                    self.assertEqual(rc, 1)
                    self.assertIn("Invalid local method note",
                                  stderr.getvalue())

            # An intentionally unset note still belongs to the existing
            # INCOMPLETE_OR_BLOCKED (not malformed schema) state.
            doc = self.full_record()
            doc[field] = None
            self.assertEqual(review.inspect(doc, self.csv)["outcome"],
                             "INCOMPLETE_OR_BLOCKED")

    def test_optional_cpu_rss_disk_are_not_fabricated(self):
        doc = self.full_record()
        for row in doc["runs"]:
            row.update({"cpuMs": 4.5, "peakRssBytes": 1024,
                        "diskWrittenBytes": 0})
        doc["runs"][0]["peakRssBytes"] = None
        result = review.inspect(doc, self.csv)
        self.assertEqual(result["outcome"], "DESCRIPTIVE_TIMING_ONLY")
        one = result["groups"][0]
        self.assertEqual(one["cpuMetric"], "RECORDED_ALL")
        self.assertEqual(one["rssMetric"], "NOT_MEASURED_OR_PARTIAL")
        self.assertEqual(one["diskMetric"], "RECORDED_ALL")

    def test_exact_console_transcript_new_only_and_no_input_mutation(self):
        doc = self.full_record()
        self.write_record(doc)
        out_path = self.base / "summary.json"
        before = (self.input.read_bytes(), self.csv.read_bytes())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(review.run([
                "--input", str(self.input), "--dataset", str(self.csv),
                "--out", str(out_path)]), 0)
        self.assertEqual(stdout.getvalue(),
                         out_path.with_suffix(".log").read_text("utf-8"))
        result = json.loads(out_path.read_text("utf-8"))
        self.assertEqual(result["outcome"], "DESCRIPTIVE_TIMING_ONLY")
        archived = (out_path.read_bytes(), out_path.with_suffix(".log").read_bytes())
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(review.run([
                "--input", str(self.input), "--dataset", str(self.csv),
                "--out", str(out_path)]), 1)
        self.assertIn("already exists", stderr.getvalue())
        self.assertEqual((out_path.read_bytes(), out_path.with_suffix(".log").read_bytes()),
                         archived)
        self.assertEqual((self.input.read_bytes(), self.csv.read_bytes()), before)

    def test_output_may_not_replace_input_or_dataset(self):
        doc = self.full_record()
        self.write_record(doc)
        for filename in (self.input, self.csv):
            with self.subTest(filename=filename):
                original = filename.read_bytes()
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = review.run(["--input", str(self.input),
                                     "--dataset", str(self.csv),
                                     "--out", str(filename)])
                self.assertEqual(rc, 1)
                self.assertEqual(filename.read_bytes(), original)

    def test_duplicate_json_keys_and_nonfinite_json_are_rejected(self):
        self.input.write_text(
            '{"schemaVersion":1,"schemaVersion":1}\n', encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(review.run([
                "--input", str(self.input), "--dataset", str(self.csv)]), 1)
        self.assertIn("Duplicate", stderr.getvalue())
        self.input.write_text(
            '{"schemaVersion":NaN}\n', encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(review.run([
                "--input", str(self.input), "--dataset", str(self.csv)]), 1)
        self.assertIn("Non-finite", stderr.getvalue())

    def test_source_does_not_launch_vendor_or_admit_xan(self):
        code = (ROOT / "scripts" / "csv_benchmark_review.py").read_text("utf-8")
        for forbidden in ("subprocess.Popen(", "subprocess.run(", "urlopen(",
                          "download(", "os.system(", ".apply("):
            self.assertNotIn(forbidden, code)
        self.assertNotIn('"id": "xan"', (ROOT / "catalog.json").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
