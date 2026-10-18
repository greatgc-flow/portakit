"""Tests for links behavior."""

import contextlib
import hashlib
import io
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes


class ExtractTests(fixtures.ExtractWorkspace):
    def test_symlink_and_reparse_are_rejected_before_any_write(self):
        for attr in [(stat.S_IFLNK | 0o777) << 16, 0x400]:
            link = zipfile.ZipInfo("link")
            link.create_system = 3
            link.external_attr = attr
            with self.subTest(attr=attr), self.assertRaises(pk.PortakitError):
                self.extract([("good.txt", b"safe"), (link, b"outside")])
            self.assertFalse(self.root.exists())


class PathSafetyTests(fixtures.Workspace):
    def test_existing_reparse_parent_rejected_even_inside_root(self):
        parent = self.root / "alias"
        parent.mkdir(parents=True)
        lstat = Path.lstat
        def reparse(path, *args, **kwargs):
            if path == parent:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return lstat(path, *args, **kwargs)
        with mock.patch.object(Path, "lstat", reparse):
            with self.assertRaisesRegex(pk.PortakitError, "reparse"):
                pk.safe_path(self.root, "alias/child", "dest")


class TempFileTests(fixtures.InstallWorkspace):
    def test_stale_temps_are_wiped_not_reused_and_links_not_followed(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("precious")
        stage = self.root / ".portakit-stage-demo.tmp"
        (stage / "inner").mkdir(parents=True)
        (stage / "inner/stale.txt").write_text("stale")
        self.junction(stage / "link", outside)
        (self.root / ".portakit-dl-demo.tmp").write_bytes(b"partial")
        (self.root / ".portakit-state.abc123.tmp").write_text("{")
        (self.root / ".portakit-other.tmp").mkdir()
        (self.root / "notes.tmp").write_text("not ours")
        payload = zip_bytes([("demo.exe", b"1")])
        self.write_catalog([entry(sha256=hashlib.sha256(payload).hexdigest())])
        code, _ = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(code, 0)
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])
        self.assertEqual((outside / "keep.txt").read_text(), "precious")
        self.assertEqual((self.root / "notes.tmp").read_text(), "not ours")
        self.assertFalse((self.root / "demo/inner").exists())
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")


@unittest.skipUnless(os.name == 'nt', 'Windows junctions')
class RootLinkTests(fixtures.Workspace):
    def setUp(self):
        super().setUp()
        self.write_catalog([entry()])
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.outside / ".portakit-state.json").write_text("{}")
        (self.outside / ".portakit-keep.tmp").write_text("precious")

    def assert_root_rejected(self):
        before = {p.relative_to(self.outside): p.read_bytes()
                  for p in self.outside.rglob("*") if p.is_file()}
        for command in ("list", "install", "update", "remove"):
            with self.subTest(command=command), \
                    mock.patch.object(pk, "RootLock", wraps=pk.RootLock) as lock, \
                    mock.patch.object(pk, "read_state", wraps=pk.read_state) as state, \
                    mock.patch.object(pk, "load_catalog", wraps=pk.load_catalog) as catalog, \
                    mock.patch.object(Path, "mkdir", autospec=True) as mkdir:
                args = (command,) if command == "list" else (command, "demo")
                code, result = self.call(*args, downloader=mock.Mock())
                self.assertEqual((code, result["error"]["code"] if result["error"] else None),
                                 (5, "state"))
                self.assertIn("reparse", result["error"]["message"].lower())
                mkdir.assert_not_called()
                lock.assert_not_called()
                state.assert_not_called()
                catalog.assert_not_called()
        after = {p.relative_to(self.outside): p.read_bytes()
                 for p in self.outside.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_root_junction_rejected_before_filesystem_work(self):
        self.junction(self.root, self.outside)
        self.assert_root_rejected()

    def test_ancestor_junction_rejected_for_existing_and_missing_root(self):
        self.junction(self.root, self.outside)
        (self.outside / "existing").mkdir()
        for suffix in ("existing", "missing/nested"):
            with self.subTest(suffix=suffix):
                self.root = self.base / "root" / suffix
                self.assert_root_rejected()
        self.assertFalse((self.outside / "missing").exists())

    def test_relative_root_with_junction_before_dotdot_is_rejected(self):
        self.junction(self.root, self.outside)
        self.root = Path(os.path.relpath(self.root)) / ".." / "safe"
        self.assert_root_rejected()

    def test_root_directory_symlink_rejected(self):
        try:
            self.root.symlink_to(self.outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")
        self.addCleanup(self.drop_junction, self.root)
        self.assert_root_rejected()


@unittest.skipUnless(os.name == 'nt', 'Windows junctions')
class LinkRuleTests(fixtures.InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("precious")

    def assert_outside_intact(self):
        self.assertEqual((self.outside / "secret.txt").read_text(), "precious")

    def link_at_dest(self):
        previous = self.installed()
        shutil.rmtree(self.root / "demo")
        self.junction(self.root / "demo", self.outside)
        return previous

    def assert_reparse_backup_rejected_before_recovery(self, cli):
        previous = self.installed()
        dest, old = self.root / "demo", self.root / "demo.old"
        shutil.rmtree(dest)
        self.junction(old, self.outside)
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with mock.patch.object(pk, "rename", wraps=pk.rename) as renamed:
            if cli:
                self.write_catalog([tool])
                code, result = self.call("update", "demo", downloader=download)
                self.assertEqual((code, result["error"]["code"]), (5, "state"))
            else:
                with self.assertRaises(pk.PortakitError) as caught:
                    pk.update(tool, self.root, download)
                self.assertEqual(caught.exception.code, "state")
            renamed.assert_not_called()
        download.assert_not_called()
        self.assertTrue(pk.is_reparse(old))
        self.assertFalse(os.path.lexists(dest))
        self.assertEqual(self.state_bytes(), previous)
        self.assert_outside_intact()
        self.assertEqual(list(self.outside.iterdir()), [self.outside / "secret.txt"])

    def test_update_rejects_reparse_backup_before_recovery(self):
        self.assert_reparse_backup_rejected_before_recovery(cli=False)

    def test_cli_update_rejects_reparse_backup_before_recovery(self):
        self.assert_reparse_backup_rejected_before_recovery(cli=True)

    def test_update_with_junction_at_dest_aborts_state(self):
        previous = self.link_at_dest()
        tool, download = self.package("2")
        with self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assert_outside_intact()
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual(list(self.outside.iterdir()), [self.outside / "secret.txt"])

    def test_install_with_junction_at_dest_is_refused(self):
        self.junction(self.root / "demo", self.outside)
        tool, download = self.package()
        with self.assertRaises(pk.PortakitError) as caught:
            pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assert_outside_intact()
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_remove_with_junction_at_dest_unlinks_without_following(self):
        self.link_at_dest()
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assert_outside_intact()
        self.assertEqual(pk.read_state(self.root), {})

    def test_remove_with_junction_inside_dest_does_not_follow(self):
        self.installed()
        self.junction(self.root / "demo/linked", self.outside)
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assert_outside_intact()

    def test_update_old_dir_with_junction_inside_is_deleted_without_following(self):
        self.installed()
        self.junction(self.root / "demo/linked", self.outside)
        tool, download = self.package("2")
        pk.update(tool, self.root, download)
        self.assertFalse((self.root / "demo.old").exists())
        self.assert_outside_intact()

    def test_remove_tree_unlinks_a_junction_and_nested_junctions(self):
        tree = self.base / "tree"
        (tree / "sub").mkdir(parents=True)
        self.junction(tree / "sub/linked", self.outside)
        pk.remove_tree(tree)
        self.assertFalse(tree.exists())
        self.assert_outside_intact()
        top = self.base / "toplink"
        self.junction(top, self.outside)
        pk.remove_tree(top)
        self.assertFalse(top.exists())
        self.assert_outside_intact()

    def test_preserved_path_containing_a_junction_aborts_update(self):
        previous = self.installed()
        (self.root / "demo/settings").mkdir()
        self.junction(self.root / "demo/settings/linked", self.outside)
        tool, download = self.package("2", preserveOnUpdate=["settings"])
        with self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assert_outside_intact()
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_list_ignores_links_under_root(self):
        self.write_catalog([entry()])
        self.junction(self.root / "demo", self.outside)
        code, _ = self.call("list")
        self.assertEqual(code, 0)


class ArchiveEdges(fixtures.ArchiveWorkspace):
    def test_symlink_and_reparse_entries(self):
        for attribute in [(stat.S_IFLNK | 0o777) << 16, 0x400]:
            link = zipfile.ZipInfo("package/link")
            link.create_system = 3
            link.external_attr = attribute
            with self.subTest(attribute=attribute):
                self.check_archive_error(fixtures.zip_bytes([("package/good", b"ok"), (link, b"../outside")]))


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


if __name__ == "__main__":
    unittest.main()
