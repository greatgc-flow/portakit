import contextlib
import hashlib
import io
from pathlib import Path
import stat
import struct
import unittest
from unittest import mock
import warnings
import zipfile
import zlib

import test_portakit as fixtures


pk = fixtures.pk


class ArchiveEdges(fixtures.InstallWorkspace):
    def check_archive_error(self, payload):
        tool = fixtures.entry(sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaises(pk.PortakitError) as caught:
            pk.install(tool, self.root, lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_symlink_and_reparse_entries(self):
        for attribute in [(stat.S_IFLNK | 0o777) << 16, 0x400]:
            link = zipfile.ZipInfo("package/link")
            link.create_system = 3
            link.external_attr = attribute
            with self.subTest(attribute=attribute):
                self.check_archive_error(fixtures.zip_bytes([("package/good", b"ok"), (link, b"../outside")]))

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


class FilesystemEdges(fixtures.InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.clear_readonly_for_fixture_cleanup)

    def clear_readonly_for_fixture_cleanup(self):
        for path in self.base.rglob("*"):
            if path.is_file():
                path.chmod(path.stat().st_mode | stat.S_IWRITE)

    def test_locked_existing_directory_during_swap_is_busy(self):
        previous = self.installed()
        tool, download = self.package("2")
        def locked(src, dst):
            if src == self.root / "demo":
                raise PermissionError("running executable")
        with self.patch_rename(locked):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "busy")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_corrupt_state_rejected_without_touching_managed_files(self):
        self.installed()
        path = self.root / ".portakit-state.json"
        for content in [b"{", b"[]", b"\xff", b'{"demo":{"dest":"demo"}}']:
            path.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(pk.PortakitError) as caught:
                pk.remove("demo", self.root)
            self.assertEqual(caught.exception.code, "state")
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_unicode_root_members_update_and_remove(self):
        self.root = self.base / "도구 日本語"
        self.root.mkdir()
        tool, download = self.package(members=[("패키지/실행.exe", b"exe")], dest="편집기")
        pk.install(tool, self.root, download)
        self.assertEqual((self.root / "편집기/실행.exe").read_bytes(), b"exe")
        (self.root / "편집기/설정").mkdir()
        (self.root / "편집기/설정/사용자.ini").write_text("안녕하세요\n", encoding="utf-8")
        tool, download = self.package("2", dest="편집기", preserveOnUpdate=["설정"])
        pk.update(tool, self.root, download)
        self.assertEqual((self.root / "편집기/설정/사용자.ini").read_text(encoding="utf-8"), "안녕하세요\n")
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "편집기").exists())
        self.assertEqual(pk.read_state(self.root), {})

    def test_readonly_old_files_are_deleted_after_update(self):
        self.installed()
        (self.root / "demo/demo.exe").chmod(stat.S_IREAD)
        tool, download = self.package("2")
        result = pk.update(tool, self.root, download)
        self.assertEqual(set(result), {"id", "version", "dest", "changed"})
        self.assertFalse((self.root / "demo.old").exists())

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

    def test_remove_with_orphan_old_deletes_it_even_when_state_write_fails(self):
        previous = self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        with mock.patch.object(pk, "write_state", side_effect=OSError("locked state")):
            with self.assertRaises(pk.PortakitError):
                pk.remove("demo", self.root)
        # The entry is kept (state written last); a retry finishes.
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})


class LocalFilesystemClassificationTests(fixtures.InstallWorkspace):
    def test_catalog_filesystem_errors_are_state_5(self):
        for command in (("list",), ("install", "demo")):
            for error in (FileNotFoundError("missing catalog"),
                          PermissionError("catalog access denied"), OSError("catalog disk error")):
                with self.subTest(command=command, error=error), \
                        mock.patch.object(Path, "read_text", side_effect=error):
                    code, result = self.call(*command)
                    self.assertEqual((code, result["error"]["code"]), (5, "state"))
                    self.assertIn(str(error), result["error"]["message"])
        self.assertFalse((self.root / ".portakit-lock").exists())

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


class DestinationOwnershipTests(fixtures.InstallWorkspace):
    def assert_owned_destination_rejected(self, cli):
        for index, dest in enumerate(("demo", "DEMO")):
            with self.subTest(dest=dest):
                self.root = self.base / f"owned-{index}"
                self.root.mkdir()
                # The owner's directory is missing and the owner is absent from the catalog.
                pk.write_state(self.root, {"owner": {"version": "1", "dest": "demo"}})
                previous = self.state_bytes()
                tool, download = self.package(dest=dest)
                download = mock.Mock(wraps=download)
                if cli:
                    self.write_catalog([tool])
                    code, result = self.call("install", "demo", downloader=download)
                    self.assertEqual((code, result["error"]["code"] if result["error"] else None),
                                     (5, "state"))
                else:
                    with self.assertRaises(pk.PortakitError) as caught:
                        pk.install(tool, self.root, download)
                    self.assertEqual(caught.exception.code, "state")
                download.assert_not_called()
                self.assertEqual(self.state_bytes(), previous)
                self.assertFalse((self.root / dest).exists())
                self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_install_rejects_destination_owned_by_another_state_entry(self):
        self.assert_owned_destination_rejected(cli=False)

    def test_cli_install_rejects_destination_owned_by_another_state_entry(self):
        self.assert_owned_destination_rejected(cli=True)


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
