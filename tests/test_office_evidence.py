"""Offline, non-destructive Office acceptance evidence packager tests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_office_evidence.py"
spec = importlib.util.spec_from_file_location("office_evidence", SCRIPT)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class EvidencePackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.folder = base / "source evidence"
        self.folder.mkdir()
        (self.folder / "Excel").mkdir()
        (self.folder / "Excel" / "identical.html").write_text(
            "BASELINE", encoding="utf-8")
        (self.folder / "console.log").write_text("console matches\\n", encoding="utf-8")
        self.target = base / "result evidence.zip"

    def test_sha256_manifest_and_zip_are_consistent(self):
        result = packager.package_evidence(self.folder, self.target, 0)
        self.assertEqual(result["runtime"], "PASS")
        self.assertEqual(result["files"], 2)
        digest = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.assertEqual(result["sha256"], digest)
        self.assertEqual((self.target.parent / (self.target.name + ".sha256.txt"))
                         .read_text(encoding="utf-8"),
                         digest + "  " + self.target.name + "\n")
        with zipfile.ZipFile(self.target) as archive:
            self.assertEqual(set(archive.namelist()),
                             {"Excel/identical.html", "console.log", "manifest.json"})
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["office_runtime"], "PASS")
            self.assertEqual(manifest["script_exit_code"], 0)
            for record in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read(record["path"]))
                                 .hexdigest(), record["sha256"])

    def test_missing_office_exit_is_explicitly_not_verified(self):
        result = packager.package_evidence(self.folder, self.target, 2)
        self.assertEqual(result["runtime"], "NOT_VERIFIED")
        with zipfile.ZipFile(self.target) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["office_runtime"], "NOT_VERIFIED")
            self.assertEqual(manifest["script_exit_code"], 2)

    def test_failure_exit_is_not_reported_as_pass(self):
        result = packager.package_evidence(self.folder, self.target, 1)
        self.assertEqual(result["runtime"], "FAIL")

    def test_collision_does_not_overwrite_existing_package(self):
        self.target.write_bytes(b"keep-existing")
        with self.assertRaises(FileExistsError):
            packager.package_evidence(self.folder, self.target, 0)
        self.assertEqual(self.target.read_bytes(), b"keep-existing")

    def test_rejects_evidence_manifest_or_empty_folder(self):
        (self.folder / "manifest.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "manifest.json"):
            packager.package_evidence(self.folder, self.target, 0)
        self.assertFalse(self.target.exists())
        (self.folder / "manifest.json").unlink()
        (self.folder / "console.log").unlink()
        (self.folder / "Excel" / "identical.html").unlink()
        with self.assertRaisesRegex(ValueError, "no files"):
            packager.package_evidence(self.folder, self.target, 0)

    def test_rejects_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "0, 1 or 2"):
            packager.package_evidence(self.folder, self.target, 3)


if __name__ == "__main__":
    unittest.main()
