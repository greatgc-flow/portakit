"""Fully offline source and SHA verification, no external sockets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import support as fixtures

CORE = fixtures.pk
REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("toolsets_offline_test", REPO / "scripts/toolsets.py")
toolsets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(toolsets)


class CoreArchiveTests(fixtures.InstallWorkspace):
    def test_offline_zip_install_and_no_http(self):
        payload = fixtures.zip_bytes([("demo.exe", b"offline")])
        incoming = self.base / "approved vendor.zip"
        incoming.write_bytes(payload)
        self.write_catalog([fixtures.entry(sha256=hashlib.sha256(payload).hexdigest())])
        with mock.patch.object(CORE.urllib.request, "urlopen", side_effect=AssertionError("network disallowed")):
            code, result = self.call("--archive", str(incoming), "install", "demo")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"offline")
        self.assertTrue(incoming.exists())
        self.assertFalse(list(self.root.glob(".portakit-*.tmp")))

    def test_offline_exe_install_and_no_http(self):
        incoming = self.base / "vendor.exe"
        incoming.write_bytes(b"not-a-real-binary-but-valid-for-SHA-pipeline")
        self.write_catalog([fixtures.entry(artifact="exe", sha256=hashlib.sha256(
            incoming.read_bytes()).hexdigest())])
        with mock.patch.object(CORE.urllib.request, "urlopen", side_effect=AssertionError("network disallowed")):
            code, result = self.call("--archive", str(incoming), "install", "demo")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), incoming.read_bytes())

    def test_offline_hash_mismatch_refuses_and_keeps_original(self):
        incoming = self.base / "untrusted.zip"
        incoming.write_bytes(fixtures.zip_bytes([("demo.exe", b"tampered")]))
        self.write_catalog([fixtures.entry(sha256="f" * 64)])
        code, result = self.call("--archive", str(incoming), "install", "demo")
        self.assertEqual((code, result["error"]["code"]), (3, "fetch"))
        self.assertIn("SHA256 mismatch", result["error"]["message"])
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_offline_missing_file_refuses_before_install(self):
        self.write_catalog([fixtures.entry()])
        code, result = self.call("--archive", str(self.base / "missing.zip"), "install", "demo")
        self.assertEqual((code, result["error"]["code"]), (3, "fetch"))
        self.assertFalse((self.root / "demo").exists())

    def test_reject_archive_for_list_configure_remove_and_recommended(self):
        self.write_catalog([fixtures.entry()])
        incoming = self.base / "vendor.zip"
        incoming.write_bytes(fixtures.zip_bytes([("demo.exe", b"x")]))
        for argv in (("--archive", str(incoming), "list"),
                     ("--archive", str(incoming), "configure", "demo"),
                     ("--archive", str(incoming), "remove", "demo"),
                     ("--archive", str(incoming), "--recommended", "install", "demo")):
            with self.subTest(argv=argv):
                code, result = self.call(*argv)
                self.assertEqual((code, result["error"]["code"]), (1, "usage"))

    def test_offline_archive_symlink_refuses(self):
        incoming = self.base / "vendor.zip"
        incoming.write_bytes(fixtures.zip_bytes([("demo.exe", b"x")]))
        link = self.base / "symbolic.zip"
        try:
            link.symlink_to(incoming)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks forbidden under current Windows test identity")
        self.write_catalog([fixtures.entry(sha256=hashlib.sha256(incoming.read_bytes()).hexdigest())])
        code, result = self.call("--archive", str(link), "install", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertFalse((self.root / "demo").exists())


class ProfileOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.offline = self.base / "approved"
        self.offline.mkdir()
        self.payload = b"offline-asset"
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.pin = {"id": "demo", "version": "1",
                    "url": "https://vendor.example/releases/v1/demo-v1.zip",
                    "sha256": self.digest}
        self.row = {"id": "demo", "status": "install"}

    def verify(self, rows=None):
        return toolsets.verify_offline_assets(
            [self.row] if rows is None else rows, self.offline,
            load_catalog=lambda path: {"demo": self.pin})

    def test_preflight_requires_exact_vendor_filename_and_correct_hash(self):
        with self.assertRaisesRegex(toolsets.ToolsetError, "Missing offline"):
            self.verify()
        archive = self.offline / "demo-v1.zip"
        archive.write_bytes(b"wrong")
        with self.assertRaisesRegex(toolsets.ToolsetError, "SHA-256 mismatch"):
            self.verify()
        archive.write_bytes(self.payload)
        self.assertEqual(self.verify()["demo"], archive)

    def test_existing_pin_requires_no_vendor_archive(self):
        already = {"id": "demo", "status": "already-installed"}
        self.assertEqual(self.verify([already]), {})

    def test_reject_symlink_local_archives(self):
        real = self.base / "vendor.zip"
        real.write_bytes(self.payload)
        link = self.offline / "demo-v1.zip"
        try:
            link.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation forbidden")
        with self.assertRaises(CORE.PortakitError):
            self.verify()

    def test_reject_oversize_file_using_limit_override(self):
        archive = self.offline / "demo-v1.zip"
        archive.write_bytes(self.payload)
        with mock.patch.object(toolsets.core, "MAX_DOWNLOAD_BYTES", 5):
            with self.assertRaisesRegex(toolsets.ToolsetError, "Oversize"):
                self.verify()


if __name__ == "__main__":
    unittest.main()
