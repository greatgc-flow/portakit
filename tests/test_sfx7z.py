"""Isolated tests for official 7-Zip SFX-as-DATA extraction (never launch installer)."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import support as fixtures

pk = fixtures.pk


def listing(extra=()):
    items = [
        ("7z.exe", 4, "A", "-"),
        ("7z.dll", 3, "A", "-"),
        ("7zFM.exe", 5, "A", "-"),
        ("7zG.exe", 5, "A", "-"),
        ("License.txt", 7, "A", "-"),
    ] + list(extra)
    blocks = []
    for path, size, attrs, encrypted in items:
        blocks.append("Path = {}\nSize = {}\nAttributes = {}\nEncrypted = -\n".format(
            path, size, attrs).replace("Encrypted = -", "Encrypted = " + encrypted))
    return ("7-Zip 26.04\n\n--\nType = 7z\nMethod = LZMA\n\n"
            "----------\n" + "\n".join("\n" + text for text in blocks))


class SfxListingTests(unittest.TestCase):
    def setUp(self):
        self.folder = self.enterContext(tempfile.TemporaryDirectory())
        self.target = Path(self.folder) / "stage"

    def test_minimal_safe_vendor_listing(self):
        result = pk.parse_sfx_listing(listing(), self.target)
        self.assertEqual(len(result), 5)
        self.assertEqual(result["7zfm.exe"][1], 5)
        self.assertFalse(result["7zfm.exe"][2])

    def test_reject_unsafe_paths_and_duplicate_case(self):
        for path in ("../outside.exe", "C:\\evil.exe", "Lang/../../bad.txt",
                     "\\absolute.exe", "NUL.txt", "with:colon.txt",
                     "Lang\\duplicate\\..\\b.txt"):
            with self.subTest(path=path):
                with self.assertRaises(pk.PortakitError):
                    pk.parse_sfx_listing(listing([(path, 1, "A", "-")]), self.target)
        with self.assertRaisesRegex(pk.PortakitError, "duplicate"):
            pk.parse_sfx_listing(listing([("7ZFM.exe", 8, "A", "-")]), self.target)

    def test_refuse_bad_encryption_or_link(self):
        for attrs, encrypted in (("A", "+"), ("L", "-"), ("AL", "-")):
            with self.subTest(attrs=attrs, encrypted=encrypted):
                with self.assertRaisesRegex(pk.PortakitError, "link|encrypted"):
                    pk.parse_sfx_listing(listing([("hijack", 4, attrs, encrypted)]),
                                         self.target)

    def test_reject_file_used_as_directory(self):
        with self.assertRaisesRegex(pk.PortakitError, "file used"):
            pk.parse_sfx_listing(listing([("7z.exe/child.exe", 1, "A", "-")]),
                                 self.target)

    def test_reject_missing_required_file_and_oversize(self):
        with self.assertRaisesRegex(pk.PortakitError, "required"):
            pk.parse_sfx_listing(listing().replace("7zG.exe", "other.exe"), self.target)
        with self.assertRaisesRegex(pk.PortakitError, "limit"):
            pk.parse_sfx_listing(listing([("huge.txt", 65 * 1024 * 1024, "A", "-")]),
                                 self.target)

    def test_reject_empty_or_non_7z_header(self):
        for value in ("", "not a listing", listing().replace("Type = 7z", "Type = Rar")):
            with self.subTest(value=value[:22]):
                with self.assertRaises(pk.PortakitError):
                    pk.parse_sfx_listing(value, self.target)


class SfxDependencyTests(fixtures.InstallWorkspace):
    def test_pin_type_restricted_to_full_7zip(self):
        tool = fixtures.entry(id="untrusted", artifact="sfx7z")
        self.write_catalog([tool])
        with self.assertRaisesRegex(pk.PortakitError, "restricted"):
            pk.load_catalog(self.catalog)

    def test_missing_prerequisite_fails_before_vendor_download(self):
        self.write_catalog([fixtures.entry(id="7zip", dest="7zip", artifact="sfx7z")])
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog):
            code, result = self.call("install", "7zip", downloader=mock.Mock(
                side_effect=AssertionError("must not download")))
        self.assertEqual(result["error"]["code"], "archive")
        self.assertIn("7zr", result["error"]["message"])
        self.assertFalse((self.root / "7zip").exists())

    def test_digest_recheck_blocks_tampered_7zr_before_sfx(self):
        official = {"id": "7zr", "dest": "7zr", "version": "26.04",
                    "sha256": hashlib.sha256(b"valid").hexdigest()}
        self.write_catalog([fixtures.entry(id="7zip", dest="7zip", artifact="sfx7z"),
                            fixtures.entry(**official)])
        (self.root / "7zr").mkdir()
        (self.root / "7zr/7zr.exe").write_bytes(b"tampered")
        pk.write_state(self.root, {"7zr": {"dest": "7zr", "version": "26.04",
                                           "sha256": official["sha256"]}})
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog):
            code, result = self.call("install", "7zip", downloader=mock.Mock(
                side_effect=AssertionError("must not download")))
        self.assertEqual(result["error"]["code"], "archive")
        self.assertIn("SHA mismatch", result["error"]["message"])

    def test_expected_implicit_parents_allowed_extra_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "stage"
            stage.mkdir()
            archive = Path(tmp) / "vendor.exe"
            archive.write_bytes(b"vendor")
            output = listing([("Lang\\ko.txt", 2, "A", "-")])
            records = {"7z.exe": 4, "7z.dll": 3, "7zFM.exe": 5,
                       "7zG.exe": 5, "License.txt": 7, "Lang/ko.txt": 2}

            def runner(cmd, **kwargs):
                if cmd[1] == "l":
                    return subprocess.CompletedProcess(cmd, 0, output, "")
                for name, length in records.items():
                    target = stage / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"x" * length)
                return subprocess.CompletedProcess(cmd, 0, "Everything is Ok", "")

            with mock.patch.object(pk, "trusted_sfx_extractor", return_value=archive):
                pk.extract_sfx7z(archive, stage, runner=runner)
                self.assertEqual((stage / "Lang/ko.txt").read_bytes(), b"xx")

            def rogue(cmd, **kwargs):
                response = runner(cmd, **kwargs)
                if cmd[1] == "x":
                    (stage / "unexpected.txt").write_text("rogue")
                return response

            with mock.patch.object(pk, "trusted_sfx_extractor", return_value=archive):
                with self.assertRaisesRegex(pk.PortakitError, "unexpected"):
                    pk.extract_sfx7z(archive, stage, runner=rogue)

    def test_extract_rejects_subprocess_errors_without_promoting(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "staged"
            stage.mkdir()
            archive = Path(tmp) / "vendor.exe"
            archive.write_bytes(b"dummy")
            # The executable is mock-pinned for unit tests only, and cannot
            # launch because injected runner returns a listing failure.
            with mock.patch.object(pk, "trusted_sfx_extractor", return_value=archive):
                runner = mock.Mock(return_value=subprocess.CompletedProcess(
                    [], 2, "", "not an SFX"))
                with self.assertRaisesRegex(pk.PortakitError, "listing failed"):
                    pk.extract_sfx7z(archive, stage, runner=runner)
                self.assertEqual(runner.call_count, 1)
                self.assertEqual(list(stage.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
