"""Offline four-Office evidence verification, including tamper/false-PASS gates."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


packer = module("package_office_evidence.py", "office_package")
verifier = module("verify_office_evidence.py", "office_verify")

APPS = {"Excel": ".xlsx", "Word": ".docx", "PowerPoint": ".pptx",
        "Visio": ".vsdx"}


class IndependentVerificationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.evidence = self.base / "source"
        self.evidence.mkdir()
        self.zip = self.base / "my office.zip"
        (self.evidence / "console.log").write_text("synthetic test only",
                                                    encoding="utf-8")

    def rows(self, statuses):
        with (self.evidence / "results.csv").open("w", encoding="utf-8") as out:
            out.write("Application,Status,Detail\n")
            for app, status in statuses.items():
                out.write(app + "," + status + ",Synthetic fixture\n")

    def documents(self, app):
        folder = self.evidence / app
        folder.mkdir()
        ext = APPS[app]
        for name in ("left", "right", "identical"):
            (folder / (name + ext)).write_bytes(b"fake sample " + name.encode("ascii"))
        (folder / "identical.html").write_text(
            "<html>" + "same" * 60 + "</html>", encoding="utf-8")
        (folder / "different.html").write_text(
            "<html>" + "BASELINE" + " line" * 60 + "DIFFERENT" + "</html>",
            encoding="utf-8")

    def pack(self, exit_code):
        packer.package_evidence(self.evidence, self.zip, exit_code)
        return verifier.verify(self.zip)

    def test_valid_not_verified_probe(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        verdict = self.pack(2)
        self.assertTrue(verdict["verified"])
        self.assertEqual(verdict["office_runtime"], "NOT_VERIFIED")
        self.assertEqual(set(verdict["applications"]), set(APPS))
        self.assertEqual(verifier.main(["--zip", str(self.zip), "--require-pass"]), 2)

    def test_valid_synthetic_four_pass_structure(self):
        for app in APPS:
            self.documents(app)
        self.rows({app: "PASS" for app in APPS})
        verdict = self.pack(0)
        self.assertEqual(verdict["office_runtime"], "PASS")
        self.assertEqual(verdict["file_count"], 22)
        self.assertEqual(verifier.main(["--zip", str(self.zip), "--require-pass"]), 0)

    def test_reject_false_pass_without_four_results(self):
        with self.assertRaisesRegex(verifier.EvidenceError, "four-app"):
            self.pack(0)

    def test_reject_false_pass_without_semantic_report(self):
        for app in APPS:
            self.documents(app)
        (self.evidence / "Word/different.html").write_text("<html>" + "raw ZIP" * 30 + "</html>")
        self.rows({app: "PASS" for app in APPS})
        with self.assertRaisesRegex(verifier.EvidenceError, "semantic"):
            self.pack(0)

    def test_reject_inconsistent_verdict_and_csv(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        with self.assertRaisesRegex(verifier.EvidenceError, "four successful"):
            self.pack(0)

    def test_reject_tampered_zip_checksum(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        self.pack(2)
        with self.zip.open("ab") as out:
            out.write(b"ADDED")
        with self.assertRaisesRegex(verifier.EvidenceError, "SHA-256"):
            verifier.verify(self.zip)

    def test_reject_changed_sidecar(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        self.pack(2)
        sha = self.zip.with_name(self.zip.name + ".sha256.txt")
        sha.write_text("0" * 64 + "  " + self.zip.name + "\n")
        with self.assertRaisesRegex(verifier.EvidenceError, "SHA-256"):
            verifier.verify(self.zip)

    def test_reject_untracked_entry_even_with_valid_sidecar(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        self.pack(2)
        with zipfile.ZipFile(self.zip, "a") as archive:
            archive.writestr("untracked-file.txt", "extra")
        sha = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        self.zip.with_name(self.zip.name + ".sha256.txt").write_text(
            sha + "  " + self.zip.name + "\n")
        with self.assertRaisesRegex(verifier.EvidenceError, "count mismatch|Untracked"):
            verifier.verify(self.zip)

    def test_reject_zip_path_traversal_with_valid_sidecar(self):
        self.rows({app: "NOT_VERIFIED" for app in APPS})
        self.pack(2)
        with zipfile.ZipFile(self.zip, "a") as archive:
            archive.writestr("../escape.txt", "bad")
        sha = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        self.zip.with_name(self.zip.name + ".sha256.txt").write_text(
            sha + "  " + self.zip.name + "\n")
        with self.assertRaisesRegex(verifier.EvidenceError, "Unsafe"):
            verifier.verify(self.zip)

    def test_valid_failure_with_only_console_log(self):
        verdict = self.pack(1)
        self.assertEqual(verdict["office_runtime"], "FAIL")
        self.assertEqual(verifier.main(["--zip", str(self.zip), "--require-pass"]), 2)


if __name__ == "__main__":
    unittest.main()
