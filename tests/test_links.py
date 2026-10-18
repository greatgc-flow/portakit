"""Link-rule regressions; mocked lstat also covers file links without privileges."""

import contextlib
import hashlib
import io
import os
from pathlib import Path
import stat
from types import SimpleNamespace
from unittest import mock

import test_portakit as fixtures


pk = fixtures.pk


class LinkAccessTests(fixtures.InstallWorkspace):
    @contextlib.contextmanager
    def reparse(self, path, symlink=False):
        original = Path.lstat
        marked = Path.cwd() / path

        def lstat(candidate, *args, **kwargs):
            if Path.cwd() / candidate == marked:
                return SimpleNamespace(st_mode=stat.S_IFLNK if symlink else stat.S_IFREG,
                                       st_file_attributes=0 if symlink else 0x400)
            return original(candidate, *args, **kwargs)

        with mock.patch.object(Path, "lstat", lstat):
            yield

    @contextlib.contextmanager
    def rejected(self):
        with self.assertRaises(pk.PortakitError) as caught:
            yield
        self.assertEqual(caught.exception.code, "state")
        self.assertIn("reparse", str(caught.exception).lower())

    def test_read_state_rejects_file_links_even_when_dangling(self):
        path = self.root / ".portakit-state.json"
        for exists in (False, True):
            if exists:
                path.write_text("{}")
            for symlink in (False, True):
                with self.subTest(exists=exists, symlink=symlink), \
                        self.reparse(path, symlink), self.rejected():
                    pk.read_state(self.root)

    def test_write_state_rejects_target_link_without_replacing_it(self):
        path = self.root / ".portakit-state.json"
        path.write_bytes(b"precious")
        with self.reparse(path), self.rejected():
            pk.write_state(self.root, {})
        self.assertEqual(path.read_bytes(), b"precious")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_write_state_rejects_temporary_link_without_unlinking_it(self):
        temporary = self.root / ".portakit-state.fixed.tmp"
        temporary.write_bytes(b"precious")
        with mock.patch.object(pk.uuid, "uuid4", return_value=SimpleNamespace(hex="fixed")), \
                self.reparse(temporary), self.rejected():
            pk.write_state(self.root, {})
        self.assertEqual(temporary.read_bytes(), b"precious")
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_cli_rejects_lock_link_before_opening_it(self):
        self.write_catalog([fixtures.entry()])
        path = self.root / ".portakit-lock"
        path.write_bytes(b"precious")
        with self.reparse(path), mock.patch.object(pk.os, "open", wraps=os.open) as opened:
            code, result = self.call("remove", "demo")
            self.assertEqual((code, result["error"]["code"]), (5, "state"))
            self.assertIn("reparse", result["error"]["message"].lower())
            opened.assert_not_called()
        self.assertEqual(path.read_bytes(), b"precious")

    def test_cli_rejects_catalog_file_link(self):
        self.write_catalog([fixtures.entry()])
        with self.reparse(self.catalog):
            code, result = self.call("list")
        self.assertEqual((code, result["error"]["code"] if result["error"] else None),
                         (5, "state"))
        self.assertFalse((self.root / ".portakit-lock").exists())

    def test_cleanup_unlinks_top_level_temp_file_links(self):
        for name in (".portakit-state.fixed.tmp", ".portakit-dl-demo.tmp",
                     ".portakit-stage-demo.tmp"):
            path = self.root / name
            path.write_bytes(b"precious")
            with self.subTest(name=name), self.reparse(path):
                pk.cleanup_temps(self.root)
                self.assertFalse(path.exists())

    def test_download_rejects_target_link_before_network_or_write(self):
        path = self.root / "download.tmp"
        path.write_bytes(b"precious")
        response = io.BytesIO(b"new")
        response.headers = {}
        with self.reparse(path), \
                mock.patch.object(pk.urllib.request, "urlopen", return_value=response) as opened, \
                self.rejected():
            pk.download("https://example.com/file", path)
        opened.assert_not_called()
        self.assertEqual(path.read_bytes(), b"precious")

    def test_fetch_rejects_target_link_before_injected_downloader(self):
        path = self.root / "download.tmp"
        download = mock.Mock()
        with self.reparse(path), self.rejected():
            pk.fetch_archive(fixtures.entry(), path, download)
        download.assert_not_called()

    def test_fetch_rechecks_target_after_downloader(self):
        path = self.root / "download.tmp"
        path.write_bytes(b"precious")
        tool = fixtures.entry(sha256=hashlib.sha256(b"precious").hexdigest())
        def download(url, target):
            self.enterContext(self.reparse(target))
        with self.rejected():
            pk.fetch_archive(tool, path, download)

    def test_extract_rejects_artifact_link_for_zip_and_exe(self):
        path = self.base / "artifact"
        path.write_bytes(fixtures.zip_bytes([("demo.exe", b"payload")]))
        for artifact in ("zip", "exe"):
            with self.subTest(artifact=artifact), self.reparse(path), self.rejected():
                pk.extract(path, fixtures.entry(artifact=artifact), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_extract_rejects_stage_link_for_zip_and_exe(self):
        path = self.base / "artifact"
        path.write_bytes(fixtures.zip_bytes([("demo.exe", b"payload")]))
        for artifact in ("zip", "exe"):
            with self.subTest(artifact=artifact), self.reparse(self.root), self.rejected():
                pk.extract(path, fixtures.entry(artifact=artifact), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_deploy_rejects_link_temps_before_removal_or_download(self):
        tool, download = self.package()
        for name in (".portakit-dl-demo.tmp", ".portakit-stage-demo.tmp"):
            path = self.root / name
            path.write_bytes(b"precious")
            with self.subTest(name=name), self.reparse(path), self.rejected():
                pk.install(tool, self.root, download)
            self.assertEqual(path.read_bytes(), b"precious")
            path.unlink()


class AncestorLinkAccessTests(fixtures.InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.outside = self.base / "outside"
        self.outside.mkdir()
        self.alias = self.base / "alias"
        self.junction(self.alias, self.outside)

    def test_cleanup_unlinks_temp_junctions_without_touching_targets(self):
        precious = self.outside / "precious"
        precious.write_bytes(b"precious")
        untouched = self.root / "notes.tmp"
        untouched.write_bytes(b"keep")
        names = (".portakit-state.fixed.tmp", ".portakit-dl-demo.tmp",
                 ".portakit-stage-demo.tmp")
        for name in names:
            self.junction(self.root / name, self.outside)
        pk.cleanup_temps(self.root)
        for name in names:
            self.assertFalse(os.path.lexists(self.root / name))
        self.assertEqual(list(self.outside.iterdir()), [precious])
        self.assertEqual(precious.read_bytes(), b"precious")
        self.assertEqual(untouched.read_bytes(), b"keep")

    def test_catalog_rejects_linked_parent(self):
        (self.outside / "catalog.json").write_text('{"tools": []}')
        with self.assertRaises(pk.PortakitError) as caught:
            pk.load_catalog(self.alias / "catalog.json")
        self.assertEqual(caught.exception.code, "state")

    def test_direct_operations_reject_root_before_resolving_it(self):
        tool, download = self.package()
        for operation in (lambda: pk.install(tool, self.alias, download),
                          lambda: pk.update(tool, self.alias, download),
                          lambda: pk.remove("demo", self.alias),
                          lambda: pk.read_state(self.alias),
                          lambda: pk.write_state(self.alias, {}),
                          lambda: pk.safe_path(self.alias, "child", "dest", "state")):
            with self.subTest(operation=operation):
                with self.assertRaises(pk.PortakitError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, "state")
        self.assertEqual(list(self.outside.iterdir()), [])

    def test_delete_rejects_linked_parent_but_keeps_leaf_unlink_semantics(self):
        path = self.outside / "precious"
        path.write_bytes(b"precious")
        with self.assertRaises(pk.PortakitError) as caught:
            pk.remove_tree(self.alias / "precious")
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual(path.read_bytes(), b"precious")
