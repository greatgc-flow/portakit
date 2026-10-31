"""No vendor binary or network is executed in these isolated Windows tests."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

import support as fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_csv_operator_smoke", ROOT / "scripts" / "csv_operator_smoke.py")
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def selected_output():
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for row in smoke.EDGE_ROWS:
        writer.writerow(row[:2])
    return stream.getvalue().encode("utf-8")


class CSVOperatorTests(fixtures.Workspace):
    def setUp(self):
        super().setUp()
        self.miller = self.base / "mlr.exe"
        self.xan = self.base / "xan.exe"
        self.miller.write_bytes(b"SIMULATED miller do not execute")
        self.xan.write_bytes(b"SIMULATED xan do not execute")
        self.output = self.base / "evidence-1"

    @staticmethod
    def fake_runner(args, folder, timeout):
        """Simulate exact 4 CLI command outputs, never spawn processes."""
        name = Path(args[0]).name.casefold()
        case = "count" if "count" in args else "select"
        if case == "count":
            with (folder / "bulk.csv").open(
                    "r", encoding="utf-8", newline="") as stream:
                expected = len(list(csv.reader(stream))) - 1
            output = (b"count\r\n" + str(expected).encode("ascii") + b"\r\n"
                      if name == "mlr.exe"
                      else str(expected).encode("ascii") + b"\n")
        else:
            output = selected_output()
        return (0, output, b"", 1.23, None)

    def exec_ok(self, **kwargs):
        params = dict(miller_path=self.miller, xan_path=self.xan,
                      evidence_dir=self.output, rows=17, timeout=10,
                      approved_offline=True, yes=True,
                      runner=self.fake_runner, windows=True)
        params.update(kwargs)
        return smoke.execute(**params)

    def test_plan_is_read_only_and_never_calls_vendor(self):
        before = list(self.base.iterdir())
        out = io.StringIO()
        with mock.patch.object(subprocess, "run",
                               side_effect=AssertionError("must not execute")):
            with contextlib.redirect_stdout(out):
                self.assertEqual(smoke.run([]), 2)
        self.assertIn("PLAN ONLY", out.getvalue())
        self.assertIn("--approved-offline", out.getvalue())
        self.assertEqual(before, list(self.base.iterdir()))

    def test_plan_arg_boundaries_and_unknown_flag(self):
        for value in (-1, 0, 100001):
            with self.subTest(value=value):
                with self.assertRaisesRegex(smoke.SmokeError, "rows outside"):
                    smoke.plan(value)
        with self.assertRaisesRegex(smoke.SmokeError, "rows outside"):
            smoke.plan(True)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(smoke.run(["plan", "--rows", "0"]), 1)

    def test_one_run_contract_four_checks_fixture_sha_and_no_install(self):
        folder, result = self.exec_ok()
        self.assertEqual(folder, self.output)
        self.assertEqual(result["outcome"], "FUNCTIONAL_PASS_ONLY")
        self.assertEqual(len(result["checks"]), 4)
        self.assertEqual([(x["tool"], x["case"]) for x in result["checks"]],
                         [("miller", "count"), ("xan", "count"),
                          ("miller", "select"), ("xan", "select")])
        self.assertEqual({x["status"] for x in result["checks"]}, {"PASS"})
        self.assertTrue(result["inputsUnchanged"])
        self.assertTrue(result["executablesUnchanged"])
        self.assertEqual(result["unexpectedWorkspaceEntries"], [])
        self.assertEqual(result["vendorArchiveProvenance"], "NOT_VERIFIED")
        self.assertEqual(result["companyUseEDRRedistribution"], "NOT_VERIFIED")
        self.assertEqual(result["performanceRanking"], "NOT_ASSESSED_SINGLE_RUN")
        with (folder / "edge.csv").open("r", encoding="utf-8", newline="") as f:
            self.assertEqual(list(csv.reader(f)), smoke.EDGE_ROWS)
        self.assertFalse((folder / "xan").exists())
        self.assertFalse((folder / "miller").exists())

    def test_evidence_console_exact_and_json_only_new(self):
        folder, result = self.exec_ok()
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            smoke.emit(folder, result)
        transcript = (folder / "console.log").read_text(encoding="utf-8")
        self.assertEqual(text.getvalue(), transcript)
        record = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["exeSha256Local"], result["exeSha256Local"])
        self.assertEqual(record["checks"], result["checks"])
        previous = ((folder / "result.json").read_bytes(),
                    (folder / "console.log").read_bytes())
        with self.assertRaisesRegex(smoke.SmokeError, "already exist"):
            smoke.emit(folder, result)
        self.assertEqual(previous, ((folder / "result.json").read_bytes(),
                                    (folder / "console.log").read_bytes()))

    def test_dual_consent_offline_os_and_new_only_before_execution(self):
        def no_calls(*args, **kwargs):
            raise AssertionError("must not call executable")
        invalid = [
            dict(yes=False),
            dict(approved_offline=False),
            dict(yes=1),
            dict(windows=False),
            dict(evidence_dir=None),
            dict(evidence_dir=""),
            dict(rows=0),
            dict(rows=100001),
            dict(timeout=0),
            dict(timeout=121),
        ]
        for index, overrides in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(smoke.SmokeError):
                    self.exec_ok(runner=no_calls, **overrides)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        with self.assertRaisesRegex(smoke.SmokeError, "already exists"):
            self.exec_ok(runner=no_calls)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_executables_reject_links_wrong_names_missing_paths(self):
        with self.assertRaisesRegex(smoke.SmokeError, "mlr.exe"):
            smoke.validate_executable(self.xan, "mlr.exe")
        with self.assertRaisesRegex(smoke.SmokeError, "absolute"):
            smoke.validate_executable("mlr.exe", "mlr.exe")
        with self.assertRaisesRegex(smoke.SmokeError, "not found"):
            smoke.validate_executable(self.base / "missing" / "mlr.exe", "mlr.exe")
        with self.assertRaisesRegex(smoke.SmokeError, "absolute"):
            smoke.validate_executable(None, "mlr.exe")
        self.assertFalse(self.output.exists())

    def test_functional_output_parser_rejects_wrong_counts_and_encoding(self):
        cases = [
            ("xan", "count", b"17\n", 17, "PASS"),
            ("miller", "count", b"count\r\n17\r\n", 17, "PASS"),
            ("xan", "count", b"16\n", 17, "FAIL"),
            ("miller", "count", b"count\nbad\n", 17, "FAIL"),
            ("xan", "select", selected_output(), 17, "PASS"),
            ("miller", "select", b"id,name\nwrong,name\n", 17, "FAIL"),
            ("xan", "select", b"\xff", 17, "FAIL"),
        ]
        for tool, case, payload, rows, expected in cases:
            with self.subTest(tool=tool, case=case, payload=payload[:12]):
                self.assertEqual(smoke.check_output(tool, case, payload, rows),
                                 expected)

    def test_executable_error_timeout_and_output_limit_not_pass(self):
        cases = [
            ((1, b"", b"not available", 11.0, None), "COMMAND_FAILED"),
            ((None, b"", b"", 100.0, "TIMEOUT"), "TIMEOUT"),
            ((None, b"", b"x", 12.0, "RUNTIME_ERROR"), "RUNTIME_ERROR"),
            ((0, b"x" * (smoke.MAX_CAPTURE + 1), b"", 0.1, None),
             "OUTPUT_LIMIT"),
            ((0, b"0", b"a" * (smoke.MAX_CAPTURE + 1), 0.1, None),
             "OUTPUT_LIMIT"),
        ]
        for response, expected in cases:
            self.assertEqual(smoke.evaluate("xan", "count", response, 1)["status"],
                             expected)
        with self.assertRaisesRegex(smoke.SmokeError, "non-byte"):
            smoke.evaluate("xan", "count", (0, "1", b"", 0.0, None), 1)

    def test_semantic_failure_returns_blocked_but_keeps_other_cases(self):
        called = []
        def bad(args, folder, timeout):
            called.append(args)
            if len(called) == 2:
                return (0, b"bad count", b"", 1, None)
            return self.fake_runner(args, folder, timeout)
        _, result = self.exec_ok(runner=bad)
        self.assertEqual(len(called), 4)
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual([x["status"] for x in result["checks"]],
                         ["PASS", "FAIL", "PASS", "PASS"])
        self.assertEqual(result["performanceRanking"], "NOT_ASSESSED_SINGLE_RUN")

    def test_modified_input_and_exec_are_rejected_after_run(self):
        def sabotage_input(args, folder, timeout):
            response = self.fake_runner(args, folder, timeout)
            if "count" in args:
                (folder / "edge.csv").write_bytes(b"tampered")
            return response
        _, result = self.exec_ok(runner=sabotage_input)
        self.assertFalse(result["inputsUnchanged"])
        self.assertEqual(result["outcome"], "BLOCKED")
        self.output = self.base / "evidence-2"
        def sabotage_exe(args, folder, timeout):
            response = self.fake_runner(args, folder, timeout)
            self.xan.write_bytes(b"changed while running")
            return response
        _, result = self.exec_ok(runner=sabotage_exe)
        self.assertFalse(result["executablesUnchanged"])
        self.assertEqual(result["outcome"], "BLOCKED")

    def test_deleted_fixture_not_ignored_or_marked_pass(self):
        def erase(args, folder, timeout):
            output = self.fake_runner(args, folder, timeout)
            (folder / "edge.csv").unlink(missing_ok=True)
            return output
        _, result = self.exec_ok(runner=erase)
        self.assertFalse(result["inputsUnchanged"])
        self.assertEqual(result["outcome"], "BLOCKED")

    def test_unexpected_workspace_write_prevents_pass(self):
        def extra(args, folder, timeout):
            (folder / "unexpected.tmp").write_text("not authorized", encoding="utf-8")
            return self.fake_runner(args, folder, timeout)
        _, result = self.exec_ok(runner=extra)
        self.assertEqual(result["unexpectedWorkspaceEntries"], ["unexpected.tmp"])
        self.assertEqual(result["outcome"], "BLOCKED")

    def test_runner_exception_is_recorded_as_error_not_success(self):
        def crash(args, folder, timeout):
            raise RuntimeError("synthetic runtime exception")
        _, report = self.exec_ok(runner=crash)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual([x["status"] for x in report["checks"]], ["ERROR"] * 4)
        self.assertTrue(all(x["errorType"] == "RuntimeError"
                            for x in report["checks"]))

    def test_cli_run_without_approvals_does_not_execute_anything(self):
        command = ["run", "--miller-exe", str(self.miller),
                   "--xan-exe", str(self.xan), "--evidence-dir", str(self.output)]
        with mock.patch.object(smoke.subprocess, "run",
                               side_effect=AssertionError("vendor process")):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                value = smoke.run(command)
        self.assertEqual(value, 1)
        self.assertIn("BOTH", err.getvalue())
        self.assertFalse(self.output.exists())

    def test_vendor_cmds_from_current_upstream_documented_usage(self):
        commands = smoke.build_cases(self.miller, self.xan, self.base)
        self.assertEqual(commands[0][2][1:3], ["--csv", "count"])
        self.assertEqual(commands[1][2][1:3],
                         ["count", "--check-alignment"])
        self.assertEqual(commands[2][2][1:5],
                         ["--csv", "cut", "-f", "id,name"])
        self.assertEqual(commands[3][2][1:3], ["select", "id,name"])
        for _, _, argv in commands:
            self.assertEqual(Path(argv[0]).suffix.lower(), ".exe")
            self.assertTrue(Path(argv[-1]).is_absolute())


if __name__ == "__main__":
    unittest.main()
