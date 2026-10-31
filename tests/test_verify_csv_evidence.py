"""Fabricated ZIP/dummy exe evidence only; zero vendor execution/network."""
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import csv_operator_smoke as smoke
import verify_csv_evidence as chain
import xan_zip_preflight as source


class EvidenceChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.xan = self.base / "xan.exe"
        self.miller = self.base / "mlr.exe"
        self.xan.write_bytes(b"SYNTHETIC-XAN-NOT-AN-EXECUTABLE")
        self.miller.write_bytes(b"SYNTHETIC-MILLER-NOT-AN-EXECUTABLE")
        self.archive = self.base / "xan-x86_64-pc-windows-msvc.zip"
        with zipfile.ZipFile(self.archive, "w") as z:
            z.writestr("xan.exe", self.xan.read_bytes())
            z.writestr("LICENSE", "synthetic not an actual license")
        data = self.archive.read_bytes()
        self.frozen = {
            "assetName": self.archive.name,
            "expectedBytes": len(data),
            "expectedSha256": hashlib.sha256(data).hexdigest(),
            "version": "SYNTHETIC",
        }
        self.source_json = self.base / "zip-source.json"
        self.folder = self.base / "smoke-evidence"

    @staticmethod
    def fake_runner(argv, folder, timeout):
        if "count" in argv:
            with (folder / "bulk.csv").open("r", encoding="utf-8", newline="") as f:
                count = sum(1 for _ in csv.reader(f)) - 1
            output = (("count\r\n%d\r\n" % count) if
                      Path(argv[0]).name == "mlr.exe" else
                      ("%d\n" % count)).encode("utf-8")
        else:
            string = io.StringIO(newline="")
            writer = csv.writer(string, lineterminator="\n")
            writer.writerows([row[:2] for row in smoke.EDGE_ROWS])
            output = string.getvalue().encode("utf-8")
        return 0, output, b"", 1.5, None

    def build(self, bind=True):
        report = source.inspect(self.archive, self.frozen,
                                exe=self.xan if bind else None)
        with contextlib.redirect_stdout(io.StringIO()):
            source.emit(report, self.source_json)
        folder, result = smoke.execute(
            self.miller, self.xan, self.folder, 17, 10,
            approved_offline=True, yes=True,
            runner=self.fake_runner, windows=True)
        with contextlib.redirect_stdout(io.StringIO()):
            smoke.emit(folder, result)
        return report, result

    def verify(self):
        return chain.verify(self.source_json, self.folder, self.frozen)

    def rewrite_smoke(self, mutate):
        p = self.folder / "result.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        mutate(doc)
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        (self.folder / "console.log").write_text(
            "\n".join(smoke.report_lines(doc)) + "\n", encoding="utf-8", newline="\n")

    def test_chain_success_only_synthetic_not_enterprise_pass(self):
        self.build()
        output = self.verify()
        self.assertEqual(output["outcome"], "EVIDENCE_CROSSCHECK_ONLY")
        self.assertTrue(output["sourceExecutableMatched"])
        self.assertEqual(output["companyUseEDRTransfer"], "NOT_VERIFIED")
        self.assertEqual(output["hostIsolation"], "NOT_VERIFIED_BY_SCRIPT")

    def test_missing_optional_exe_is_incomplete(self):
        self.build(bind=False)
        output = self.verify()
        self.assertEqual(output["outcome"], "INCOMPLETE_OR_BLOCKED")
        self.assertFalse(output["sourceExecutableMatched"])

    def test_mismatched_source_to_executed_sha_fails(self):
        self.build()
        self.rewrite_smoke(lambda doc: doc["exeSha256Local"].update(
            {"xan": "0" * 64}))
        with self.assertRaisesRegex(chain.EvidenceError, "Executed xan SHA"):
            self.verify()

    def test_changed_fixture_fails_even_with_unchanged_json(self):
        self.build()
        with (self.folder / "edge.csv").open("ab") as f:
            f.write(b"unexpected")
        with self.assertRaisesRegex(chain.EvidenceError, "CSV has changed"):
            self.verify()

    def test_missing_json_or_log_rejected(self):
        self.build()
        (self.folder / "console.log").unlink()
        with self.assertRaisesRegex(chain.EvidenceError, "Missing evidence"):
            self.verify()

    def test_tampered_source_console_rejected(self):
        self.build()
        self.source_json.with_suffix(".log").write_text(
            "RESULT: LOCAL_ORIGINAL_STRUCTURE_PASS\n", encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Console transcript|footer"):
            self.verify()

    def test_tampered_smoke_console_rejected(self):
        self.build()
        (self.folder / "console.log").write_text(
            "RESULT: FUNCTIONAL_PASS_ONLY\n", encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Console transcript"):
            self.verify()

    def test_false_functional_pass_rejected(self):
        self.build()
        self.rewrite_smoke(lambda doc: doc["checks"][0].update(
            {"status": "FAIL"}))
        with self.assertRaisesRegex(chain.EvidenceError, "outcome contradicts"):
            self.verify()

    def test_consistently_blocked_result_remains_blocked(self):
        self.build()
        def edit(doc):
            doc["checks"][0]["status"] = "FAIL"
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        self.assertEqual(self.verify()["outcome"], "INCOMPLETE_OR_BLOCKED")

    def test_unknown_case_status_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0]["status"] = "ENTERPRISE_APPROVED"
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "case list"):
            self.verify()

    def test_frozen_version_or_sha_mismatch_rejected(self):
        self.build()
        fake = dict(self.frozen, expectedSha256="0" * 64)
        with self.assertRaisesRegex(chain.EvidenceError, "Source report mismatches"):
            chain.verify(self.source_json, self.folder, fake)

    def test_evidence_out_mirrored_and_new_only(self):
        self.build()
        target = self.base / "chain.json"
        out = io.StringIO()
        report = self.verify()
        with contextlib.redirect_stdout(out):
            chain.emit(report, target)
        self.assertEqual(
            target.with_suffix(".log").read_text(encoding="utf-8").splitlines(),
            out.getvalue().splitlines())
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
        with self.assertRaisesRegex(chain.EvidenceError, "NEW JSON"):
            chain.emit(report, target)

    def test_default_stdout_only_and_no_file_write(self):
        self.build()
        before = set(self.base.iterdir())
        with contextlib.redirect_stdout(io.StringIO()):
            chain.emit(self.verify())
        self.assertEqual(set(self.base.iterdir()), before)

    def test_cli_missing_evidence_and_no_vendor_runner(self):
        with mock.patch.object(source, "official_record", return_value=self.frozen), \
             mock.patch.object(smoke, "call_vendor", side_effect=AssertionError("vendor")):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(chain.run(["--source-json", str(self.source_json),
                                            "--smoke-dir", str(self.folder)]), 1)

    def test_cli_success_and_incomplete_return_codes(self):
        self.build(bind=False)
        with mock.patch.object(source, "official_record", return_value=self.frozen):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(chain.run(["--source-json", str(self.source_json),
                                            "--smoke-dir", str(self.folder)]), 2)


    def test_source_console_rejects_crlf_normalization(self):
        """Visible lines alone are not byte-identical evidence."""
        self.build()
        path = self.source_json.with_suffix(".log")
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(chain.EvidenceError, "Console transcript"):
            self.verify()

    def test_smoke_console_rejects_crlf_normalization(self):
        self.build()
        path = self.folder / "console.log"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(chain.EvidenceError, "Console transcript"):
            self.verify()

    def test_smoke_console_requires_final_newline(self):
        self.build()
        path = self.folder / "console.log"
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        with self.assertRaisesRegex(chain.EvidenceError, "Console transcript"):
            self.verify()

    def test_source_console_rejects_extra_footer_lines(self):
        self.build()
        path = self.source_json.with_suffix(".log")
        with path.open("ab") as out:
            out.write(b"SECOND FOOTER: untrusted\n")
        with self.assertRaisesRegex(chain.EvidenceError, "footer"):
            self.verify()

    def test_duplicate_top_level_json_keys_rejected(self):
        self.build()
        path = self.source_json
        contents = path.read_text(encoding="utf-8")
        contents = contents.replace(
            '"schemaVersion": 1,', '"schemaVersion": 1, "schemaVersion": 1,', 1)
        path.write_text(contents, encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Duplicate JSON"):
            self.verify()

    def test_duplicate_nested_json_keys_rejected(self):
        self.build()
        path = self.folder / "result.json"
        contents = path.read_text(encoding="utf-8")
        contents = contents.replace(
            '"tool": "miller",', '"tool": "miller", "tool": "miller",', 1)
        path.write_text(contents, encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Duplicate JSON"):
            self.verify()

    def test_nonstandard_json_nan_rejected(self):
        self.build()
        path = self.source_json
        contents = path.read_text(encoding="utf-8")
        contents = contents.replace(
            '"schemaVersion": 1,', '"schemaVersion": 1, "untrusted": NaN,', 1)
        path.write_text(contents, encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Non-finite JSON"):
            self.verify()

    def test_pass_case_with_nonzero_exit_is_invalid(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["checks"][0].update({"returnCode": 1}))
        with self.assertRaisesRegex(chain.EvidenceError, "process/capture|Process record"):
            self.verify()

    def test_pass_case_with_claimed_truncated_output_is_invalid(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["checks"][1].update(
                {"capturedOutputTruncated": True}))
        with self.assertRaisesRegex(chain.EvidenceError, "process/capture|Process record"):
            self.verify()

    def test_pass_case_with_missing_digest_is_invalid(self):
        self.build()
        self.rewrite_smoke(lambda doc: doc["checks"][2].pop("stdoutSha256"))
        with self.assertRaisesRegex(
                chain.EvidenceError,
                "Unexpected smoke process record|process/capture|Process record"):
            self.verify()

    def test_pass_case_with_oversized_capture_is_invalid(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["checks"][3].update(
                {"stdoutBytes": smoke.MAX_CAPTURE + 1}))
        with self.assertRaisesRegex(chain.EvidenceError, "process/capture|Process record"):
            self.verify()

    def test_null_json_report_rejected(self):
        self.build()
        self.source_json.write_text("null\n", encoding="utf-8")
        with self.assertRaisesRegex(chain.EvidenceError, "Source report mismatches"):
            self.verify()

    def test_oversized_json_rejected_before_parse(self):
        self.build()
        with mock.patch.object(chain, "MAX_REPORT_BYTES", 64):
            with self.assertRaisesRegex(chain.EvidenceError, "byte limit"):
                self.verify()


    def test_deterministic_fixtures_match_smoke_generator_at_bounds(self):
        for rows in (1, 17, smoke.MAX_ROWS):
            with self.subTest(rows=rows):
                folder = self.base / ("fixtures-" + str(rows))
                folder.mkdir()
                generated = smoke.prepare_fixtures(folder, rows)
                self.assertEqual(chain.expected_fixture_sha256(rows), generated)

    def test_edge_content_and_report_hash_rewritten_together_rejected(self):
        self.build()
        path = self.folder / "edge.csv"
        original = path.read_bytes()
        path.write_bytes(original.replace("한글".encode("utf-8"),
                                          "변조".encode("utf-8"), 1))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.rewrite_smoke(lambda report:
                           report["syntheticInputSha256"].update({"edge": digest}))
        with self.assertRaisesRegex(chain.EvidenceError, "deterministic fixture: edge"):
            self.verify()

    def test_bulk_content_and_report_hash_rewritten_together_rejected(self):
        self.build()
        path = self.folder / "bulk.csv"
        original = path.read_bytes()
        path.write_bytes(original.replace(b"name1,", b"nameX,", 1))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.rewrite_smoke(lambda report:
                           report["syntheticInputSha256"].update({"bulk": digest}))
        with self.assertRaisesRegex(chain.EvidenceError, "deterministic fixture: bulk"):
            self.verify()

    def test_report_row_count_changed_with_consistent_log_rejected(self):
        self.build()
        self.rewrite_smoke(lambda report: report.update({"rowsCounted": 18}))
        with self.assertRaisesRegex(chain.EvidenceError, "deterministic fixture: bulk"):
            self.verify()

    def test_invalid_fixture_row_count_is_not_coerced(self):
        for value in (None, 0, smoke.MAX_ROWS + 1, True, "17", []):
            with self.subTest(value=value):
                with self.assertRaisesRegex(chain.EvidenceError, "row count"):
                    chain.expected_fixture_sha256(value)


    def rewrite_source(self, mutate):
        """Edit source JSON together with its canonical recorded console."""
        path = self.source_json
        report = json.loads(path.read_text(encoding="utf-8"))
        mutate(report)
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        lines = source.display_lines(report)
        footer = "REPORT: " + str(path)
        path.with_suffix(".log").write_text(
            "\n".join(lines + [footer]) + "\n",
            encoding="utf-8", newline="\n")

    def test_source_provenance_and_notice_overclaims_rejected(self):
        baseline, _ = self.build()
        for field, claimed in (("provenance", "PUBLISHER_VERIFIED"),
                               ("notice", "ENTERPRISE_APPROVED"),
                               ("candidateId", "not-xan")):
            with self.subTest(field=field):
                self.rewrite_source(
                    lambda report: report.update({field: claimed}))
                with self.assertRaisesRegex(chain.EvidenceError, "metadata"):
                    self.verify()
                self.rewrite_source(
                    lambda report: report.update({field: baseline[field]}))

    def test_source_zip_member_counters_rejected(self):
        self.build()
        self.rewrite_source(
            lambda report: report["structure"].update({"members": 1}))
        with self.assertRaisesRegex(chain.EvidenceError, "structure counters"):
            self.verify()

    def test_source_zip_expanded_bytes_below_executable_rejected(self):
        self.build()
        self.rewrite_source(lambda report:
                            report["structure"].update({"expandedLogicalBytes": 0}))
        with self.assertRaisesRegex(chain.EvidenceError, "structure counters"):
            self.verify()

    def test_smoke_host_attestation_overclaim_rejected(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc.update({"host": "CERTIFIED_AIRGAPPED"}))
        with self.assertRaisesRegex(chain.EvidenceError, "overclaims"):
            self.verify()

    def test_smoke_notice_overclaim_rejected(self):
        self.build()
        self.rewrite_smoke(lambda doc: doc.update({"notice": "RELEASE_APPROVED"}))
        with self.assertRaisesRegex(chain.EvidenceError, "overclaims"):
            self.verify()

    def test_valid_raised_runner_error_is_blocked_not_parse_error(self):
        self.build()
        def edit(doc):
            doc["checks"][0] = {"tool": "miller", "case": "count",
                                "status": "ERROR", "errorType": "ValueError"}
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        self.assertEqual(self.verify()["outcome"], "INCOMPLETE_OR_BLOCKED")

    def test_invalid_runner_error_missing_error_type_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0] = {"tool": "miller", "case": "count",
                                "status": "ERROR"}
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "ERROR record"):
            self.verify()

    def test_valid_nonzero_command_failure_remains_blocked(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({"status": "COMMAND_FAILED",
                                     "returnCode": 9})
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        self.assertEqual(self.verify()["outcome"], "INCOMPLETE_OR_BLOCKED")

    def test_command_failed_with_zero_return_code_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({"status": "COMMAND_FAILED",
                                     "returnCode": 0})
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "COMMAND_FAILED verdict"):
            self.verify()

    def test_failed_semantic_output_with_nonzero_return_code_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({"status": "FAIL", "returnCode": 1})
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "PASS/FAIL verdict"):
            self.verify()

    def test_output_limit_without_overflow_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0]["status"] = "OUTPUT_LIMIT"
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "OUTPUT_LIMIT verdict"):
            self.verify()

    def test_negative_duration_rejected_even_when_log_matches(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({"durationMilliseconds": -1})
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "Process record"):
            self.verify()

    def test_forged_truncation_flag_without_excess_bytes_rejected(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({"capturedOutputTruncated": True})
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "Process record"):
            self.verify()

    def test_source_unchecked_note_contradiction_rejected(self):
        self.build(bind=False)
        self.rewrite_source(
            lambda report: report["localExeComparison"].update(
                {"note": "CONTENT_MATCH_ONLY_NOT_EXECUTION_OR_PUBLISHER_APPROVAL"}))
        with self.assertRaisesRegex(chain.EvidenceError, "Unchecked source EXE"):
            self.verify()


    def test_member_parent_traversal_rejected_even_with_matching_log(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"xanExeMember": "../xan.exe"}))
        with self.assertRaisesRegex(chain.EvidenceError, "member/root path unsafe"):
            self.verify()

    def test_member_suffix_spoof_rejected(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"xanExeMember": "notxan.exe"}))
        with self.assertRaisesRegex(chain.EvidenceError, "member path does not match"):
            self.verify()

    def test_member_backslash_rejected(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"xanExeMember": "folder\\xan.exe"}))
        with self.assertRaisesRegex(chain.EvidenceError, "member path does not match"):
            self.verify()

    def test_member_control_character_rejected(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"xanExeMember": "forged\n/xan.exe"}))
        with self.assertRaisesRegex(chain.EvidenceError, "member/root path unsafe"):
            self.verify()

    def test_member_root_must_be_in_original_root_names(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"xanExeMember": "invented/xan.exe"}))
        with self.assertRaisesRegex(chain.EvidenceError, "member path does not match"):
            self.verify()

    def test_invalid_source_root_device_name_rejected(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update(
                {"rootNames": ["con"]}))
        with self.assertRaisesRegex(chain.EvidenceError, "member/root path unsafe"):
            self.verify()

    def test_blocked_workspace_with_safe_relative_path_allowed(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["extra/output.txt"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        self.assertEqual(self.verify()["outcome"], "INCOMPLETE_OR_BLOCKED")

    def test_blocked_workspace_with_parent_escape_rejected(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["../escaped.txt"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "Unsafe unexpected"):
            self.verify()

    def test_blocked_workspace_log_injection_rejected(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["report\nRESULT: PASS"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError, "Unsafe unexpected"):
            self.verify()

    def test_scan_error_sentinel_stays_blocked(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["UNKNOWN_SCAN_ERROR"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        self.assertEqual(self.verify()["outcome"], "INCOMPLETE_OR_BLOCKED")

    def test_source_log_footer_control_code_rejected(self):
        self.build()
        path = self.source_json.with_suffix(".log")
        path.write_bytes(path.read_bytes().replace(
            b"REPORT: ", b"REPORT: \x1b", 1))
        with self.assertRaisesRegex(chain.EvidenceError, "control characters"):
            self.verify()

    def test_copied_source_footer_original_path_still_allowed(self):
        self.build()
        path = self.source_json.with_suffix(".log")
        raw = path.read_bytes()
        suffix = b"REPORT: " + str(self.source_json).encode("utf-8") + b"\n"
        self.assertTrue(raw.endswith(suffix))
        path.write_bytes(raw[:-len(suffix)] +
                         b"REPORT: X:/PreviouslyApproved/source.json\n")
        self.assertEqual(self.verify()["outcome"], "EVIDENCE_CROSSCHECK_ONLY")


    def test_input_changed_between_stat_and_open_is_rejected(self):
        self.build()
        self.assert_read_fingerprint_change_detected(2, "before open")

    def test_input_changed_during_read_is_rejected(self):
        self.build()
        self.assert_read_fingerprint_change_detected(3, "during read")

    def test_input_replaced_after_read_is_rejected(self):
        self.build()
        self.assert_read_fingerprint_change_detected(5, "replaced after read")

    def assert_read_fingerprint_change_detected(self, changed_call, message):
        original = chain.file_signature
        call_number = [0]
        def simulate_mutation(info):
            call_number[0] += 1
            signature = original(info)
            if call_number[0] == changed_call:
                return signature[:-1] + (signature[-1] + 1,)
            return signature
        with mock.patch.object(chain, "file_signature",
                               side_effect=simulate_mutation):
            with self.assertRaisesRegex(chain.EvidenceError, message):
                chain.read_file(self.source_json, chain.MAX_REPORT_BYTES)

    def test_input_is_not_rewritten_on_successful_verification(self):
        self.build()
        files = [self.source_json, self.source_json.with_suffix(".log"),
                 self.folder / "result.json", self.folder / "console.log",
                 self.folder / "edge.csv", self.folder / "bulk.csv"]
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in files}
        self.verify()
        self.assertEqual(before,
                         {path: (path.read_bytes(), path.stat().st_mtime_ns)
                          for path in files})

    def test_json_dump_failure_removes_only_new_partial_json(self):
        self.build()
        out = self.base / "crosscheck-fail.json"
        with mock.patch.object(chain.json, "dump", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                chain.emit(self.verify(), out)
        self.assertFalse(out.exists())
        self.assertFalse(out.with_suffix(".log").exists())

    def test_console_log_failure_removes_new_json_and_partial_log(self):
        self.build()
        out = self.base / "crosscheck-emit-fail.json"
        def faulty_emit(evidence, line):
            evidence.stream.write("partial\n")
            evidence.stream.flush()
            raise OSError("simulated log failure")
        with mock.patch.object(source.kit.sets.Evidence, "emit", new=faulty_emit):
            with self.assertRaisesRegex(OSError, "simulated log failure"):
                chain.emit(self.verify(), out)
        self.assertFalse(out.exists())
        self.assertFalse(out.with_suffix(".log").exists())

    def test_concurrent_log_collision_preserves_foreign_file(self):
        self.build()
        out = self.base / "crosscheck-collision.json"
        log = out.with_suffix(".log")
        original_init = source.kit.sets.Evidence.__init__
        def intrude(evidence, path):
            Path(path).write_bytes(b"FOREIGN-USER-LOG\n")
            original_init(evidence, path)
        with mock.patch.object(source.kit.sets.Evidence,
                               "__init__", new=intrude):
            with self.assertRaises(FileExistsError):
                chain.emit(self.verify(), out)
        self.assertFalse(out.exists())
        self.assertEqual(log.read_bytes(), b"FOREIGN-USER-LOG\n")

    def test_preexisting_json_or_log_is_never_replaced(self):
        self.build()
        out = self.base / "crosscheck-existing.json"
        log = out.with_suffix(".log")
        for existing in (out, log):
            with self.subTest(existing=existing):
                existing.write_bytes(b"ORIGINAL-KEEP-ME\n")
                with self.assertRaisesRegex(chain.EvidenceError, "NEW JSON"):
                    chain.emit(self.verify(), out)
                self.assertEqual(existing.read_bytes(), b"ORIGINAL-KEEP-ME\n")
                existing.unlink()

    def test_cleanup_skips_replaced_output_file(self):
        self.build()
        path = self.base / "foreign-new.json"
        path.write_text("old", encoding="utf-8")
        original_identity = chain.created_identity(path.stat())
        path.unlink()
        path.mkdir()
        chain.cleanup_created(path, original_identity)
        self.assertTrue(path.is_dir())


    def test_source_extra_approval_field_is_not_trusted(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc.update({"publisherAuthenticated": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected source report"):
            self.verify()

    def test_source_extra_structure_field_is_not_trusted(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["structure"].update({"crcCertified": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected source structure"):
            self.verify()

    def test_source_extra_exe_field_is_not_trusted(self):
        self.build()
        self.rewrite_source(
            lambda doc: doc["localExeComparison"].update(
                {"executionApproved": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected source executable link"):
            self.verify()

    def test_smoke_extra_approval_field_is_not_trusted(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc.update({"companyApproved": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected smoke report"):
            self.verify()

    def test_smoke_extra_exe_digest_claim_is_not_trusted(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["exeSha256Local"].update(
                {"publisherSignature": "VALID"}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected smoke executable hashes"):
            self.verify()

    def test_smoke_extra_fixture_digest_claim_is_not_trusted(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["syntheticInputSha256"].update(
                {"realProductionData": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected smoke fixture hashes"):
            self.verify()

    def test_smoke_extra_process_claim_is_not_trusted(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["checks"][0].update(
                {"publisherVerified": True}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Unexpected smoke process record"):
            self.verify()

    def test_zero_byte_stderr_has_only_empty_digest(self):
        self.build()
        self.rewrite_smoke(
            lambda doc: doc["checks"][0].update(
                {"stderrSha256": "0" * 64}))
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Zero-byte process stream"):
            self.verify()

    def test_zero_byte_stdout_has_only_empty_digest(self):
        self.build()
        def edit(doc):
            doc["checks"][0].update({
                "status": "FAIL", "stdoutBytes": 0,
                "stdoutSha256": "f" * 64})
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "Zero-byte process stream"):
            self.verify()

    def test_workspace_entries_require_producer_sorted_order(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["z.txt", "a.txt"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "workspace entries contradict"):
            self.verify()

    def test_workspace_entries_cannot_be_duplicated(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["extra.txt", "extra.txt"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "workspace entries contradict"):
            self.verify()

    def test_scan_failure_sentinel_must_be_only_workspace_entry(self):
        self.build()
        def edit(doc):
            doc["unexpectedWorkspaceEntries"] = ["UNKNOWN_SCAN_ERROR", "z.txt"]
            doc["outcome"] = "BLOCKED"
        self.rewrite_smoke(edit)
        with self.assertRaisesRegex(chain.EvidenceError,
                                    "workspace entries contradict"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
