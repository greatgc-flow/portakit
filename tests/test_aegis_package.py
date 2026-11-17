"""Offline release-boundary tests; no PowerShell or real windows are launched."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("aegis_package", REPO / "scripts/build_aegis_package.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


class AegisPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        for name in package.RUNTIME_FILES:
            if name.endswith(".ps1"):
                text = "#requires -version 2.0\r\n# fixture\r\n"
                if name == "Aegis.ps1":
                    text += ("<#\r\nAegis 4.1.0-ps2 | Test fixture.\r\n#>\r\n"
                             "function Get-AegisVersion { return '4.1.0-ps2' }\r\n")
                data = b"\xef\xbb\xbf" + text.encode("utf-8")
            else:
                data = b"fixture\r\n"
            (self.source / name).write_bytes(data)
        self.output = self.root / "assets" / "Aegis-4.1.0-ps2.zip"

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = package.main(["--source-dir", str(self.source), "--output", str(self.output), *args])
        return code, out.getvalue(), err.getvalue()

    def test_runtime_allowlist_and_manifest_exclude_user_and_developer_files(self):
        (self.source / "profiles").mkdir()
        (self.source / "profiles" / "private.xml").write_text("private settings")
        (self.source / "tests").mkdir()
        (self.source / "tests" / "test.ps1").write_text("developer only")
        (self.source / "private.log").write_text("never package this")
        version, data = package.build_package(self.source)
        prefix = "Aegis-" + version + "/"
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()),
                             {prefix + name for name in (*package.RUNTIME_FILES, "SHA256SUMS.txt")})
            for row in archive.read(prefix + "SHA256SUMS.txt").decode("ascii").splitlines():
                digest, name = row.split("  ", 1)
                self.assertEqual(digest, hashlib.sha256(archive.read(prefix + name)).hexdigest())
                self.assertEqual(archive.read(prefix + name), (self.source / name).read_bytes())

    def test_archive_is_identical_after_filesystem_timestamp_changes(self):
        _, first = package.build_package(self.source)
        for index, path in enumerate(reversed(list(self.source.iterdir()))):
            os.utime(path, (1_600_000_000 + index, 1_700_000_000 + index))
        _, second = package.build_package(self.source)
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in archive.infolist()))

    def test_build_and_check_return_same_hash_without_modifying_asset(self):
        code, text, error = self.invoke()
        self.assertEqual((code, error), (0, ""))
        before = self.output.read_bytes()
        result = json.loads(text)
        self.assertEqual(result["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(result["file_count"], 7)
        code, text, error = self.invoke("--check")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(text)["status"], "verified")
        self.assertEqual(self.output.read_bytes(), before)

    def test_stale_asset_fails_check_and_is_not_overwritten(self):
        self.assertEqual(self.invoke()[0], 0)
        before = self.output.read_bytes()
        with (self.source / "README_ko.txt").open("ab") as stream:
            stream.write(b"updated source\r\n")
        code, _, error = self.invoke("--check")
        self.assertEqual(code, 1)
        self.assertIn("stale", error.lower())
        self.assertEqual(self.output.read_bytes(), before)

    def test_missing_asset_check_creates_no_output_directory(self):
        self.assertEqual(self.invoke("--check")[0], 1)
        self.assertFalse(self.output.parent.exists())

    def test_missing_runtime_file_aborts_before_creating_output(self):
        (self.source / "Aegis.Menu.ps1").unlink()
        self.assertEqual(self.invoke()[0], 1)
        self.assertFalse(self.output.parent.exists())

    def test_version_function_and_banner_must_match(self):
        path = self.source / "Aegis.ps1"
        path.write_bytes(path.read_bytes().replace(b"Aegis 4.1.0-ps2 |", b"Aegis 4.1.1-ps2 |"))
        with self.assertRaisesRegex(package.PackageError, "version"):
            package.build_package(self.source)

    def test_ps2_script_encoding_and_line_endings_are_enforced(self):
        path = self.source / "Aegis.Menu.ps1"
        original = path.read_bytes()
        for invalid in (original[3:], original.replace(b"\r\n", b"\n")):
            with self.subTest(invalid=invalid):
                path.write_bytes(invalid)
                with self.assertRaises(package.PackageError):
                    package.build_package(self.source)

    def test_source_symlink_is_rejected(self):
        target = self.root / "private.txt"
        target.write_bytes(b"must not be included")
        link = self.source / "README_ko.txt"
        link.unlink()
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest("Symlink creation unavailable: " + str(exc))
        with self.assertRaisesRegex(package.PackageError, "Link/reparse"):
            package.build_package(self.source)

    def test_output_inside_source_is_rejected_without_changes(self):
        self.output = self.source / "runtime.zip"
        self.assertEqual(self.invoke()[0], 1)
        self.assertFalse(self.output.exists())


class RepositoryAegisPackageTests(unittest.TestCase):
    def test_committed_asset_matches_runtime_source_exactly(self):
        version, data = package.build_package(REPO / "tools" / "aegis")
        package.check_archive(REPO / "assets" / "aegis" / ("Aegis-" + version + ".zip"), data)


if __name__ == "__main__":
    unittest.main()
