"""Regression checks for bounded ZIP extraction and atomic failure handling.

The tiny limits used here simulate hostile archive metadata without allocating
hundreds of MiB. These tests do not download vendor files or touch Windows settings.
"""

import io
import unittest
from unittest import mock

import support as fixtures


pk = fixtures.pk


class ZipBoundsTests(fixtures.ExtractWorkspace):
    def test_member_count_rejected_before_creating_destination(self):
        members = [("a.txt", b"a"), ("b.txt", b"b"), ("c.txt", b"c")]
        with mock.patch.object(pk, "MAX_ZIP_MEMBERS", 2):
            with self.assertRaisesRegex(pk.PortakitError, "member count") as caught:
                self.extract(members)
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse(self.root.exists())

    def test_total_expanded_size_rejected_before_creating_destination(self):
        members = [("a.txt", b"abcde"), ("b.txt", b"12345")]
        with mock.patch.object(pk, "MAX_ZIP_EXPANDED_BYTES", 9):
            with self.assertRaisesRegex(pk.PortakitError, "expanded size") as caught:
                self.extract(members)
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse(self.root.exists())

    def test_exact_expanded_size_limit_is_allowed(self):
        members = [("a.txt", b"abcde"), ("b.txt", b"12345")]
        with mock.patch.object(pk, "MAX_ZIP_EXPANDED_BYTES", 10):
            self.extract(members)
        self.assertEqual((self.root / "a.txt").read_bytes(), b"abcde")
        self.assertEqual((self.root / "b.txt").read_bytes(), b"12345")

    def test_stream_overrun_rejected_even_if_header_understates_size(self):
        archive = self.base / "forged.zip"
        archive.write_bytes(fixtures.zip_bytes([("demo.exe", b"x")]))
        # Simulate a ZIP reader returning more decompressed bytes than the
        # immutable member-size metadata declared during the preflight.
        with mock.patch.object(pk.zipfile.ZipFile, "open",
                               return_value=io.BytesIO(b"malicious expansion")):
            with self.assertRaisesRegex(pk.PortakitError, "exceeds declared size") as caught:
                pk.extract(archive, fixtures.entry(), self.root)
        self.assertEqual(caught.exception.code, "archive")
        self.assertEqual((self.root / "demo.exe").stat().st_size, 0)


class ZipBoundsRollbackTests(fixtures.InstallWorkspace):
    def test_size_limit_update_leaves_installed_pin_and_data_intact(self):
        original_state = self.installed()
        new_tool, downloader = self.package("2", [("demo.exe", b"x" * 20)])
        with mock.patch.object(pk, "MAX_ZIP_EXPANDED_BYTES", 8):
            with self.assertRaisesRegex(pk.PortakitError, "expanded size") as caught:
                pk.update(new_tool, self.root, downloader)
        self.assertEqual(caught.exception.code, "archive")
        self.assertEqual(self.state_bytes(), original_state)
        self.assertEqual((self.root / "demo" / "demo.exe").read_bytes(), b"1")
        self.assertFalse(list(self.root.glob(".portakit-*.tmp")))


if __name__ == "__main__":
    unittest.main()
