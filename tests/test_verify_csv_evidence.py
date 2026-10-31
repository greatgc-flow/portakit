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
            "\n".join(smoke.report_lines(doc)) + "\n", encoding="utf-8")

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
        with self.assertRaisesRegex(chain.EvidenceError, "footer"):
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


if __name__ == "__main__":
    unittest.main()
