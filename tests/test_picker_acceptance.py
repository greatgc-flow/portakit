"""Headless regression: no Tk window, vendor binary, network or system edits."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_picker_human_accept", ROOT / "scripts" / "picker_acceptance.py")
rec = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rec)


class PickerHumanAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.output = Path(self.tmp) / "review.json"
        self.log = self.output.with_suffix(".log")

    def ask(self, letters):
        it = iter(letters)
        return it.__next__

    def review(self, choices):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = rec.review(self.output, read=self.ask(choices))
        return rc, output.getvalue()

    def test_default_probe_is_not_gui_acceptance_and_creates_no_files(self):
        probe = rec.probe()
        self.assertEqual(probe["outcome"], "NOT_VERIFIED")
        self.assertEqual(probe["mode"], "PREREQUISITES_ONLY")
        self.assertEqual(len(probe["pickerSha256"]), 64)
        self.assertIn("NOT_VERIFIED", "\n".join(rec.summary_lines(probe)))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rec.run([]), 0)
        self.assertIn("static prerequisites only", out.getvalue())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.log.exists())

    def test_review_all_pass_is_operator_report_only_and_exact_console_log(self):
        rc, console = self.review(["p"] * len(rec.CHECKS))
        self.assertEqual(rc, 0)
        self.assertEqual(console, self.log.read_text(encoding="utf-8"))
        report = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(report["outcome"], "OPERATOR_REPORTED_PASS")
        self.assertEqual(report["mode"], "HUMAN_SELF_REPORT")
        self.assertTrue(all(x["status"] == "PASS" for x in report["checks"]))
        self.assertIn("NOT automated GUI proof", console)
        self.assertEqual([x["id"] for x in report["checks"]],
                         [x[0] for x in rec.CHECKS])

    def test_one_fail_overrides_skipped_and_evidence_is_durable(self):
        choices = ["p"] * len(rec.CHECKS)
        choices[1] = "f"
        choices[2] = "s"
        rc, console = self.review(choices)
        self.assertEqual(rc, 1)
        self.assertIn("RESULT: OPERATOR_REPORTED_FAIL", console)
        self.assertIn("REPORTED FAIL: 1", console)
        self.assertIn("NOT VERIFIED: 1", console)
        self.assertEqual(console, self.log.read_text("utf-8"))

    def test_skipped_one_or_more_never_claims_pass(self):
        choices = ["p"] * len(rec.CHECKS)
        choices[-1] = "s"
        rc, console = self.review(choices)
        self.assertEqual(rc, 2)
        self.assertIn("RESULT: INCOMPLETE_NOT_VERIFIED", console)
        self.assertEqual(json.loads(self.output.read_text("utf-8"))["outcome"],
                         "INCOMPLETE_NOT_VERIFIED")

    def test_invalid_key_is_reprompted_without_implicit_pass(self):
        inputs = ["invalid", "", "P"] + ["s"] * (len(rec.CHECKS) - 1)
        rc, console = self.review(inputs)
        self.assertEqual(rc, 2)
        self.assertEqual(console.count("INVALID INPUT"), 2)
        report = json.loads(self.output.read_text("utf-8"))
        self.assertEqual(report["checks"][0]["status"], "PASS")
        self.assertEqual(report["checks"][1]["status"], "SKIP")

    def test_cannot_overwrite_json_or_log(self):
        self.output.write_text("existing", encoding="utf-8")
        with self.assertRaisesRegex(rec.AcceptanceError, "refusing overwrite"):
            rec.review(self.output, read=lambda: "p")
        self.assertEqual(self.output.read_text("utf-8"), "existing")
        self.output.unlink()
        self.log.write_text("existing-log", encoding="utf-8")
        with self.assertRaisesRegex(rec.AcceptanceError, "refusing overwrite"):
            rec.review(self.output, read=lambda: "p")
        self.assertEqual(self.log.read_text("utf-8"), "existing-log")

    def test_interrupted_checklist_leaves_unambiguous_partial_log_not_json(self):
        answers = iter(["p", "s"])
        def read():
            return next(answers)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(rec.AcceptanceError, "interrupted"):
                rec.review(self.output, read=read)
        self.assertFalse(self.output.exists())
        self.assertTrue(self.log.exists())
        self.assertIn("RECORDED: launch = PASS", self.log.read_text("utf-8"))
        self.assertNotIn("RESULT: OPERATOR_REPORTED_PASS", self.log.read_text("utf-8"))

    def test_review_has_no_duplicate_case_ids_and_three_dpi_gates(self):
        ids = [x[0] for x in rec.CHECKS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 12)
        self.assertEqual(set(ids) & {"dpi100", "dpi150", "dpi200"},
                         {"dpi100", "dpi150", "dpi200"})
        self.assertIn("a11y", ids)
        self.assertIn("ime", ids)

    def test_assessment_rejects_missing_duplicate_invalid_statuses(self):
        okay = [{"id": item[0], "status": "PASS"} for item in rec.CHECKS]
        self.assertEqual(rec.assess_results(okay), "OPERATOR_REPORTED_PASS")
        for broken in (okay[:-1],
                       [dict(item) for item in okay[:-1]] + [dict(okay[0])],
                       [dict(item) for item in okay[:-1]] +
                       [dict(okay[-1], status="UNREVIEWED")]):
            with self.subTest(broken=broken[-1]):
                with self.assertRaises(rec.AcceptanceError):
                    rec.assess_results(broken)

    def test_refuse_non_json_out_and_missing_review_opt_in(self):
        with self.assertRaisesRegex(rec.AcceptanceError, ".json"):
            rec.verify_output(self.output.with_suffix(".txt"))
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(rec.run(["--review"]), 1)
        self.assertIn("requires --out", error.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(rec.run(["--out", str(self.output)]), 1)
        self.assertIn("Use --review", error.getvalue())
        self.assertFalse(self.output.exists())

    def test_no_gui_execution_or_installer_in_recorder(self):
        code = (ROOT / "scripts" / "picker_acceptance.py").read_text("utf-8")
        ast.parse(code)
        for forbidden in ("subprocess.run(", "tk.Tk(", "urlopen(", ".apply(",
                          "shell=True", "os.system(", "exec("):
            self.assertNotIn(forbidden, code)
        self.assertIn("kit.sets.Evidence(", code)
        self.assertIn('input', code)


if __name__ == "__main__":
    unittest.main()
