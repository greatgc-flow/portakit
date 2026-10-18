"""Tests for archive behavior."""

import contextlib
import hashlib
import io
from pathlib import Path
import stat
import struct
import unittest
from unittest import mock
import urllib.error
import warnings
import zipfile
import zlib

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes


class DownloadTests(fixtures.Workspace):
    def setUp(self):
        super().setUp()
        self.root.mkdir()

    def payload_tool(self, payload):
        return entry(sha256=hashlib.sha256(payload).hexdigest())

    def test_mismatch_aborts_deletes_temp_and_installs_nothing(self):
        with mock.patch.object(pk, "extract") as extract, \
                self.assertRaisesRegex(pk.PortakitError, "SHA256") as caught:
            pk.install(entry(), self.root, lambda url, dest: dest.write_bytes(b"bad"))
        extract.assert_not_called()
        self.assertEqual(caught.exception.code, "fetch")
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_download_failure_deletes_partial(self):
        def fail(url, dest):
            dest.write_bytes(b"partial")
            raise urllib.error.URLError("offline")
        with self.assertRaisesRegex(pk.PortakitError, "offline") as caught:
            pk.install(entry(), self.root, fail)
        self.assertEqual(caught.exception.code, "fetch")
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_download_goes_to_the_dl_temp(self):
        names = []
        payload = zip_bytes([("demo.exe", b"1")])
        def downloader(url, dest):
            names.append(Path(dest).name)
            Path(dest).write_bytes(payload)
        pk.install(self.payload_tool(payload), self.root, downloader)
        self.assertEqual(names, [".portakit-dl-demo.tmp"])
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_no_download_cache_every_install_downloads(self):
        payload = zip_bytes([("demo.exe", b"1")])
        tool = self.payload_tool(payload)
        downloader = mock.Mock(side_effect=lambda url, dest: dest.write_bytes(payload))
        pk.install(tool, self.root, downloader)
        pk.remove("demo", self.root)
        pk.install(tool, self.root, downloader)
        self.assertEqual(downloader.call_count, 2)
        self.assertFalse((self.root / ".portakit-cache").exists())
        self.assertFalse(hasattr(pk, "fetch"))


class ExtractTests(fixtures.ExtractWorkspace):
    def test_single_root_is_flattened(self):
        self.extract([("package/", b""), ("package/bin/demo.exe", b"exe"),
                      ("package/readme.txt", b"readme")])
        self.assertEqual((self.root / "bin/demo.exe").read_bytes(), b"exe")
        self.assertFalse((self.root / "package").exists())

    def test_multiple_roots_are_kept(self):
        self.extract([("bin/demo.exe", b"exe"), ("readme.txt", b"readme")])
        self.assertTrue((self.root / "bin/demo.exe").exists())
        self.assertTrue((self.root / "readme.txt").exists())

    def test_unsafe_members_leave_zero_files(self):
        for name in ["../escape", "/absolute", "C:/escape", "\\\\host\\share\\x",
                     "x/../../escape", "..\\escape", "x:stream", "CON", "x. "]:
            with self.subTest(name=name), self.assertRaises(pk.PortakitError):
                self.extract([("good.txt", b"safe"), (name, b"bad")])
            self.assertFalse(self.root.exists())
            self.assertFalse((self.base / "escape").exists())

    def test_duplicate_windows_paths_and_file_parent_rejected(self):
        for members in [[("A.exe", b"a"), ("a.exe", b"b")],
                        [("x", b"file"), ("x/child", b"child")]]:
            with self.assertRaises(pk.PortakitError):
                self.extract(members)
            self.assertFalse(self.root.exists())

    def test_exe_artifact_is_copied_as_id_exe(self):
        source = self.base / "input.exe"
        source.write_bytes(b"MZ mock exe")
        pk.extract(source, entry(id="jq", artifact="exe"), self.root)
        self.assertEqual((self.root / "jq.exe").read_bytes(), b"MZ mock exe")

    def test_malformed_zip_has_archive_error(self):
        source = self.base / "bad.zip"
        source.write_bytes(b"bad")
        with self.assertRaisesRegex(pk.PortakitError, "zip") as caught:
            pk.extract(source, entry(), self.root)
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse(self.root.exists())


class InstallTests(fixtures.InstallWorkspace):
    def test_bad_zip_leaves_previous_install_and_state(self):
        previous = self.installed()
        tool, download = self.package("2", [("fine", b"yes"), ("../escape", b"no")])
        with self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "archive")
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertFalse((self.base / "escape").exists())


class ArchiveEdges(fixtures.ArchiveWorkspace):
    def test_absolute_and_drive_letter_paths(self):
        for name in ["/absolute", "C:/absolute", "C:relative", "\\absolute", "\\\\host\\share\\file"]:
            with self.subTest(name=name):
                self.check_archive_error(fixtures.zip_bytes([("good", b"ok"), (name, b"no")]))

    def test_duplicate_members(self):
        for name in ["good", "GOOD"]:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.check_archive_error(fixtures.zip_bytes([("good", b"one"), (name, b"two")]))

    def test_empty_and_truncated_zip(self):
        for payload in [fixtures.zip_bytes([]), b"PK\x03\x04", b"not a zip"]:
            with self.subTest(payload=payload):
                self.check_archive_error(payload)

    def test_invalid_deflate_stream_maps_zlib_error_to_archive(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("demo.exe", b"payload" * 20)
        damaged = bytearray(output.getvalue())
        name_length, extra_length = struct.unpack_from("<HH", damaged, 26)
        # BTYPE=3 is invalid, giving a real zlib.error during extraction.
        damaged[30 + name_length + extra_length] = 0x07
        with zipfile.ZipFile(io.BytesIO(damaged)) as archive, self.assertRaises(zlib.error):
            archive.read("demo.exe")
        self.check_archive_error(bytes(damaged))

    def test_eoferror_from_member_read_maps_to_archive(self):
        with mock.patch.object(pk.zipfile.ZipExtFile, "read", side_effect=EOFError("truncated member")):
            self.check_archive_error(fixtures.zip_bytes([("demo.exe", b"payload")]))


class FilesystemEdges(fixtures.FilesystemWorkspace):
    def test_readonly_stage_is_deleted_after_extraction_failure(self):
        tool, download = self.package()
        def fail(artifact, tool, stage):
            path = stage / "readonly"
            path.write_bytes(b"partial")
            path.chmod(stat.S_IREAD)
            raise pk.PortakitError("archive", "broken zip")
        with mock.patch.object(pk, "extract", fail):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "archive")
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])


class LocalFilesystemClassificationTests(fixtures.InstallWorkspace):
    def test_download_filesystem_errors_are_state_5(self):
        real_open, real_stat = Path.open, Path.stat
        for index, phase in enumerate(("open", "write", "stat", "read", "hash", "injected")):
            with self.subTest(phase=phase), contextlib.ExitStack() as patches:
                self.root = self.base / f"local-{index}"
                self.root.mkdir()
                tool, _ = self.package()
                self.write_catalog([tool])
                pk.write_state(self.root, {})
                previous = self.state_bytes()
                target = self.root / ".portakit-dl-demo.tmp"
                failure = PermissionError("local disk failure")
                writer = mock.mock_open()
                writer.return_value.write.side_effect = failure

                def opened(path, mode="r", *args, **kwargs):
                    if path == target:
                        if (phase == "open" and mode == "wb") or (phase == "read" and mode == "rb"):
                            raise failure
                        if phase == "write" and mode == "wb":
                            return writer()
                    return real_open(path, mode, *args, **kwargs)

                stat_failures = [failure] if phase == "stat" else []
                def stated(path, *args, **kwargs):
                    if path == target and stat_failures:
                        raise stat_failures.pop()
                    return real_stat(path, *args, **kwargs)

                patches.enter_context(mock.patch.object(Path, "open", opened))
                patches.enter_context(mock.patch.object(Path, "stat", stated))
                if phase == "hash":
                    patches.enter_context(mock.patch.object(pk.hashlib, "file_digest", side_effect=failure))
                response = io.BytesIO(b"downloaded")
                response.headers = {}
                patches.enter_context(mock.patch.object(pk.urllib.request, "urlopen", return_value=response))
                downloader = mock.Mock(side_effect=failure) if phase == "injected" else None
                code, result = self.call("install", "demo", downloader=downloader)
                self.assertEqual((code, result["error"]["code"]), (5, "state"))
                self.assertIn(str(failure), result["error"]["message"])
                self.assertEqual(self.state_bytes(), previous)
                self.assertFalse((self.root / "demo").exists())
                self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_network_oserrors_remain_fetch_3(self):
        self.write_catalog([fixtures.entry()])
        for phase in ("connect", "read"):
            with self.subTest(phase=phase), contextlib.ExitStack() as patches:
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.headers = {}
                response.read.side_effect = ConnectionResetError("network disconnected")
                patches.enter_context(mock.patch.object(
                    pk.urllib.request, "urlopen", return_value=response,
                    side_effect=ConnectionResetError("network disconnected") if phase == "connect" else None))
                code, result = self.call("install", "demo")
                self.assertEqual((code, result["error"]["code"]), (3, "fetch"))
                self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])


class DownloadEdges(fixtures.InstallWorkspace):
    def response(self, body, length=None):
        response = io.BytesIO(body)
        response.headers = {} if length is None else {"Content-Length": str(length)}
        return response

    def test_streamed_download_cap_without_content_length(self):
        with mock.patch.object(pk, "MAX_DOWNLOAD_BYTES", 8), mock.patch.object(
                pk.urllib.request, "urlopen", return_value=self.response(b"123456789")):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.download("https://example.com/x", self.base / "dl.tmp")
        self.assertEqual(caught.exception.code, "fetch")
        self.assertIn("size", str(caught.exception).lower())

    def test_oversized_content_length_rejected_before_read(self):
        response = self.response(b"123456789", length=9)
        with mock.patch.object(pk, "MAX_DOWNLOAD_BYTES", 8), mock.patch.object(
                pk.urllib.request, "urlopen", return_value=response), mock.patch.object(
                response, "read", side_effect=AssertionError("body must not be read")):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.download("https://example.com/x", self.base / "dl.tmp")
        self.assertEqual(caught.exception.code, "fetch")

    def test_injected_downloader_cannot_bypass_cap(self):
        payload = b"123456789"
        tool = fixtures.entry(sha256=hashlib.sha256(payload).hexdigest())
        with mock.patch.object(pk, "MAX_DOWNLOAD_BYTES", 8):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.install(tool, self.root, lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(caught.exception.code, "fetch")
        self.assertIn("size", str(caught.exception).lower())
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_exact_size_limit_is_allowed(self):
        target = self.base / "dl.tmp"
        with mock.patch.object(pk, "MAX_DOWNLOAD_BYTES", 8), mock.patch.object(
                pk.urllib.request, "urlopen", return_value=self.response(b"12345678", length=8)):
            pk.download("https://example.com/x", target)
        self.assertEqual(target.read_bytes(), b"12345678")


if __name__ == "__main__":
    unittest.main()
