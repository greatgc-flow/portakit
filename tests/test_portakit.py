import importlib.util
import contextlib
import io
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
import stat
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("portakit", Path(__file__).resolve().parents[1] / "portakit.py")
pk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pk)


def entry(**changes):
    value = dict(id="demo", version="1", kind="github", repo="owner/project", tag="v1",
                 asset="demo.zip", url="https://github.com/owner/project/releases/download/v1/demo.zip",
                 sha256="a" * 64, artifact="zip", dest="demo", preserveOnUpdate=[])
    value.update(changes)
    return value


def zip_bytes(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return output.getvalue()


class Workspace(unittest.TestCase):
    def setUp(self):
        # On Windows, inherit workspace ACLs instead of tempfile's mode=0o700.
        mkdir = os.mkdir
        with mock.patch("tempfile._os.mkdir", side_effect=lambda path, mode: mkdir(path, 0o777)):
            temporary = self.enterContext(tempfile.TemporaryDirectory(
                dir=Path(__file__).resolve().parent, prefix="tmp-"))
        self.base = Path(temporary)
        self.root = self.base / "root"
        self.catalog = self.base / "catalog.json"


class CatalogTests(Workspace):
    def test_missing_kind_is_rejected(self):
        tool = entry()
        del tool["kind"]
        with self.assertRaisesRegex(pk.PortakitError, "kind"):
            self.load([tool])

    def test_shipped_catalog_is_valid_and_has_verified_hash_fields(self):
        catalog = pk.load_catalog(Path(pk.__file__).with_name("catalog.json"), self.root)
        self.assertEqual(set(catalog), {"notepad++", "winmerge", "jq"})
        for identifier, tool in catalog.items():
            with self.subTest(id=identifier):
                self.assertEqual(tool["kind"], "github")
                self.assertRegex(tool["sha256"], r"\A[a-fA-F0-9]{64}\Z")
                self.assertEqual(pk.urllib.parse.urlsplit(tool["url"]).scheme, "https")
                self.assertTrue(pk.urllib.parse.urlsplit(tool["url"]).hostname)

    def load(self, tools):
        self.catalog.write_text(json.dumps({"tools": tools}), encoding="utf-8")
        return pk.load_catalog(self.catalog, self.root)

    def test_valid_catalog(self):
        self.assertEqual(self.load([entry()])["demo"]["version"], "1")

    def test_bad_fields_are_named(self):
        for field, value in [("id", ""), ("id", "."), ("version", 1),
                             ("url", "https://"), ("url", "file:///tmp/x"),
                             ("sha256", "bad"), ("artifact", "tar"),
                             ("preserveOnUpdate", ["../outside"])]:
            with self.subTest(field=field), self.assertRaisesRegex(pk.PortakitError, field):
                self.load([entry(**{field: value})])

    def test_missing_and_duplicate_fields(self):
        tool = entry()
        del tool["version"]
        with self.assertRaisesRegex(pk.PortakitError, "version"):
            self.load([tool])
        with self.assertRaisesRegex(pk.PortakitError, "id"):
            self.load([entry(), entry()])

    def test_dest_cannot_escape_or_occupy_internal_paths(self):
        for dest in ["../outside", "/absolute", "C:\\escape", "..\\outside", ".",
                     ".portakit-cache", ".portakit-state.json"]:
            with self.subTest(dest=dest), self.assertRaisesRegex(pk.PortakitError, "dest"):
                self.load([entry(dest=dest)])

    def test_malformed_json_names_catalog(self):
        self.catalog.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(pk.PortakitError, "catalog"):
            pk.load_catalog(self.catalog, self.root)

    def test_todo_hash_is_explicitly_allowed_in_catalog(self):
        self.assertEqual(self.load([entry(sha256="TODO")])["demo"]["sha256"], "TODO")


class EnvelopeTests(Workspace):
    def test_abbreviated_options_are_usage_errors(self):
        self.catalog.write_text(json.dumps({"tools": [entry()]}))
        for option in ["--j", "--roo"]:
            with self.subTest(option=option):
                code, result = self.call(option, "list")
                self.assertEqual(code, pk.EXIT_CODES["usage"])
                self.assertEqual(result["error"]["code"], "usage")

    def test_http_and_unexpected_exceptions_use_json_envelope(self):
        self.catalog.write_text(json.dumps({"tools": [entry()]}))
        for error, expected in [(http.client.HTTPException("broken response"), "download"),
                                (RuntimeError("unexpected"), "filesystem")]:
            with self.subTest(error=type(error).__name__), mock.patch.object(pk, "install", side_effect=error):
                code, result = self.call("install", "demo")
                self.assertEqual(code, pk.EXIT_CODES[expected])
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], expected)
                self.assertIn(str(error), result["error"]["message"])

    def call(self, *args):
        output = io.StringIO()
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog), contextlib.redirect_stdout(output):
            code = pk.main(["--json", "--root", str(self.root), *args])
        return code, json.loads(output.getvalue())

    def test_list_json_envelope(self):
        self.catalog.write_text(json.dumps({"tools": [entry()]}))
        code, result = self.call("list")
        self.assertEqual(code, 0)
        self.assertEqual(set(result), {"ok", "command", "data", "error"})
        self.assertTrue(result["ok"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["data"][0]["id"], "demo")

    def test_catalog_error_json(self):
        self.catalog.write_text('{"tools":false}')
        code, result = self.call("list")
        self.assertEqual(code, pk.EXIT_CODES["catalog"])
        self.assertFalse(result["ok"])
        self.assertIn("tools", result["error"]["message"])

    def test_usage_error_is_json(self):
        code, result = self.call("install")
        self.assertEqual(code, 2)
        self.assertEqual(result["error"]["code"], "usage")

    def test_exit_codes_are_stable(self):
        self.assertEqual(pk.EXIT_CODES, dict(ok=0, usage=2, catalog=3, download=4,
                         integrity=5, archive=6, filesystem=7, state=8, not_found=9))


class DownloadTests(Workspace):
    def tool(self, payload=b"download"):
        return entry(sha256=hashlib.sha256(payload).hexdigest())

    def test_verified_cache_uses_same_key_and_no_network_on_hit(self):
        download = mock.Mock(side_effect=lambda url, dest: dest.write_bytes(b"download"))
        first = pk.fetch(self.tool(), self.root, download)
        second = pk.fetch(self.tool(), self.root, download)
        self.assertEqual(first, second)
        self.assertEqual(first.read_bytes(), b"download")
        self.assertEqual(download.call_count, 1)

    def test_mismatch_aborts_and_removes_partial(self):
        with self.assertRaisesRegex(pk.PortakitError, "SHA256"):
            pk.fetch(self.tool(), self.root, lambda url, dest: dest.write_bytes(b"bad"))
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse(any(p.is_file() for p in self.root.rglob("*")))

    def test_cache_is_reverified(self):
        path = pk.fetch(self.tool(), self.root, lambda url, dest: dest.write_bytes(b"download"))
        path.write_bytes(b"tampered")
        with self.assertRaisesRegex(pk.PortakitError, "SHA256"):
            pk.fetch(self.tool(), self.root, mock.Mock(side_effect=AssertionError("network")))
        self.assertFalse(path.exists())

    def test_todo_hash_fails_before_downloader(self):
        download = mock.Mock()
        with self.assertRaisesRegex(pk.PortakitError, "sha256.*TODO"):
            pk.fetch(entry(sha256="TODO"), self.root, download)
        download.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_download_failure_cleans_partial(self):
        def fail(url, dest):
            dest.write_bytes(b"partial")
            raise OSError("offline")
        with self.assertRaisesRegex(pk.PortakitError, "offline"):
            pk.fetch(self.tool(), self.root, fail)
        self.assertFalse(any(p.is_file() for p in self.root.rglob("*")))


class ExtractTests(Workspace):
    def extract(self, members):
        artifact = self.base / "input.zip"
        artifact.write_bytes(zip_bytes(members))
        pk.extract(artifact, entry(), self.root)

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

    def test_symlink_and_reparse_are_rejected_before_any_write(self):
        for attr in [(stat.S_IFLNK | 0o777) << 16, 0x400]:
            link = zipfile.ZipInfo("link")
            link.create_system = 3
            link.external_attr = attr
            with self.subTest(attr=attr), self.assertRaises(pk.PortakitError):
                self.extract([("good.txt", b"safe"), (link, b"outside")])
            self.assertFalse(self.root.exists())

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
        with self.assertRaisesRegex(pk.PortakitError, "zip"):
            pk.extract(source, entry(), self.root)
        self.assertFalse(self.root.exists())


class InstallWorkspace(Workspace):
    def package(self, version="1", members=None, **changes):
        payload = zip_bytes(members if members is not None else [("demo.exe", version.encode())])
        tool = entry(version=version, sha256=hashlib.sha256(payload).hexdigest(), **changes)
        return tool, lambda url, dest: dest.write_bytes(payload)

    def installed(self):
        tool, download = self.package()
        pk.install(tool, self.root, download)
        return (self.root / ".portakit-state.json").read_bytes()


class InstallTests(InstallWorkspace):
    def test_install_refuses_installed_tool_and_points_to_update(self):
        previous = self.installed()
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "update"):
            pk.install(tool, self.root, download)
        download.assert_not_called()
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_locked_backup_cleanup_reports_committed_success(self):
        self.installed()
        tool, download = self.package("2")
        rmtree = shutil.rmtree
        def locked_old(path, *args, **kwargs):
            if Path(path).name == "demo.old":
                raise PermissionError("locked backup")
            return rmtree(path, *args, **kwargs)
        with mock.patch.object(pk.shutil, "rmtree", locked_old):
            result = pk.update(tool, self.root, download)
        self.assertEqual(result["cleanupPending"], str(self.root / "demo.old"))
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")

    def test_install_stages_and_records_state(self):
        tool, download = self.package()
        result = pk.install(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(pk.read_state(self.root)["demo"], dict(version="1", dest="demo"))
        self.assertEqual(result["id"], "demo")
        self.assertEqual(list(self.root.glob(".portakit-stage-*")), [])

    def test_update_swaps_then_deletes_old(self):
        self.installed()
        tool, download = self.package("2")
        pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")
        self.assertFalse((self.root / "demo.old").exists())

    def test_permission_error_during_swap_restores_previous_state(self):
        previous = self.installed()
        tool, download = self.package("2")
        rename = Path.rename
        def locked(path, target):
            if path.name.startswith(".portakit-stage-"):
                raise PermissionError("locked")
            return rename(path, target)
        with mock.patch.object(Path, "rename", locked), self.assertRaisesRegex(pk.PortakitError, "[Cc]lose"):
            pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_state_write_failure_restores_previous_install(self):
        previous = self.installed()
        tool, download = self.package("2")
        with mock.patch.object(pk, "write_state", side_effect=OSError("state locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_initial_install_state_failure_leaves_nothing_installed(self):
        tool, download = self.package()
        with mock.patch.object(pk, "write_state", side_effect=OSError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.install(tool, self.root, download)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_unmanaged_directory_is_not_overwritten(self):
        (self.root / "demo").mkdir(parents=True)
        (self.root / "demo/keep").write_text("mine")
        tool, download = self.package()
        with self.assertRaisesRegex(pk.PortakitError, "unmanaged"):
            pk.install(tool, self.root, download)
        self.assertEqual((self.root / "demo/keep").read_text(), "mine")

    def test_bad_sha_never_reaches_extract(self):
        with mock.patch.object(pk, "extract") as extract:
            with self.assertRaises(pk.PortakitError):
                pk.install(entry(), self.root, lambda url, dest: dest.write_bytes(b"wrong"))
            extract.assert_not_called()
        self.assertFalse((self.root / "demo").exists())

    def test_bad_zip_leaves_previous_install_and_state(self):
        previous = self.installed()
        tool, download = self.package("2", [("fine", b"yes"), ("../escape", b"no")])
        with self.assertRaises(pk.PortakitError):
            pk.update(tool, self.root, download)
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertFalse((self.base / "escape").exists())

    def test_cli_install_uses_injected_downloader(self):
        tool, download = self.package(artifact="exe", id="jq", dest="jq")
        self.catalog.write_text(json.dumps({"tools": [tool]}))
        output = io.StringIO()
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog), contextlib.redirect_stdout(output):
            code = pk.main(["install", "jq", "--json", "--root", str(self.root)], downloader=download)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        self.assertTrue((self.root / "jq/jq.exe").exists())


class UpdateTests(InstallWorkspace):
    def test_failed_old_restore_is_recovered_on_next_update(self):
        previous = self.installed()
        tool, download = self.package("2")
        rename = Path.rename
        def locked_restore(path, target):
            if path == self.root / "demo.old":
                raise PermissionError("backup locked")
            return rename(path, target)
        with mock.patch.object(Path, "rename", locked_restore), mock.patch.object(
                pk, "write_state", side_effect=OSError("state failed")):
            with self.assertRaisesRegex(pk.PortakitError, "demo.old"):
                pk.update(tool, self.root, download)
        self.assertTrue((self.root / "demo.old/demo.exe").exists())
        self.assertFalse((self.root / "demo").exists())
        # Cache is verified, so fail extraction after recovery instead of download.
        with mock.patch.object(pk, "extract", side_effect=OSError("extract failed")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_old_is_restored_even_when_renaming_failed_new_install_fails(self):
        previous = self.installed()
        tool, download = self.package("2")
        rename = Path.rename
        restored = []
        def fail_first_rollback(path, target):
            if path == self.root / "demo" and Path(target).name.startswith(".portakit-stage-"):
                raise PermissionError("cannot rename failed new install")
            if path == self.root / "demo.old":
                restored.append(path)
            return rename(path, target)
        with mock.patch.object(Path, "rename", fail_first_rollback), mock.patch.object(
                pk, "write_state", side_effect=OSError("state failed")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertTrue(restored)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_keyboard_interrupt_rolls_back_swap(self):
        previous = self.installed()
        tool, download = self.package("2")
        with mock.patch.object(pk, "write_state", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-stage-*")), [])

    def test_stale_old_is_recovered_before_install_refuses_existing_tool(self):
        previous = self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "update"):
            pk.install(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        download.assert_not_called()

    def test_stale_old_is_recovered_before_update_download_failure(self):
        previous = self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        tool, _ = self.package("2")
        with self.assertRaisesRegex(pk.PortakitError, "offline"):
            pk.update(tool, self.root, mock.Mock(side_effect=OSError("offline")))
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_update_preserves_files_and_directories(self):
        self.installed()
        (self.root / "demo/settings").mkdir()
        (self.root / "demo/settings/user.ini").write_text("custom")
        (self.root / "demo/config.ini").write_text("mine")
        tool, download = self.package("2", [("demo.exe", b"2"), ("config.ini", b"default"),
                                            ("settings/new.ini", b"default")],
                                      preserveOnUpdate=["config.ini", "settings", "absent.ini"])
        pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")
        self.assertEqual((self.root / "demo/config.ini").read_text(), "mine")
        self.assertEqual((self.root / "demo/settings/user.ini").read_text(), "custom")
        self.assertFalse((self.root / "demo/settings/new.ini").exists())
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")

    def test_forced_update_failure_rolls_back_settings_binary_and_state(self):
        previous = self.installed()
        (self.root / "demo/config.ini").write_text("custom")
        tool, download = self.package("2", preserveOnUpdate=["config.ini"])
        with mock.patch.object(pk, "write_state", side_effect=PermissionError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / "demo/config.ini").read_text(), "custom")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_preserve_copy_failure_leaves_previous_install(self):
        previous = self.installed()
        (self.root / "demo/config.ini").write_text("custom")
        tool, download = self.package("2", preserveOnUpdate=["config.ini"])
        with mock.patch.object(pk.shutil, "copy2", side_effect=PermissionError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/config.ini").read_text(), "custom")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_update_requires_installed_tool(self):
        tool, download = self.package()
        with self.assertRaisesRegex(pk.PortakitError, "installed"):
            pk.update(tool, self.root, download)
        self.assertFalse(self.root.exists())

    def test_update_rejects_changed_destination(self):
        previous = self.installed()
        tool, download = self.package("2", dest="other")
        with self.assertRaisesRegex(pk.PortakitError, "dest"):
            pk.update(tool, self.root, download)
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertFalse((self.root / "other").exists())


class RemoveTests(InstallWorkspace):
    def test_keyboard_interrupt_restores_removed_directory(self):
        previous = self.installed()
        with mock.patch.object(pk, "write_state", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pk.remove("demo", self.root)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_remove_only_managed_directory_and_its_state_entry(self):
        self.installed()
        tool, download = self.package(id="other", dest="other")
        pk.install(tool, self.root, download)
        (self.root / "unmanaged").mkdir()
        (self.root / "unmanaged/keep").write_text("mine")
        cache_before = sorted(p.name for p in (self.root / ".portakit-cache").iterdir())
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assertEqual(set(pk.read_state(self.root)), {"other"})
        self.assertTrue((self.root / "other/demo.exe").exists())
        self.assertEqual((self.root / "unmanaged/keep").read_text(), "mine")
        self.assertEqual(sorted(p.name for p in (self.root / ".portakit-cache").iterdir()), cache_before)

    def test_remove_unmanaged_is_rejected(self):
        (self.root / "demo").mkdir(parents=True)
        with self.assertRaisesRegex(pk.PortakitError, "installed"):
            pk.remove("demo", self.root)
        self.assertTrue((self.root / "demo").exists())

    def test_remove_state_failure_restores_directory_and_state(self):
        previous = self.installed()
        with mock.patch.object(pk, "write_state", side_effect=PermissionError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.remove("demo", self.root)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)

    def test_remove_works_without_catalog(self):
        self.installed()
        output = io.StringIO()
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog), contextlib.redirect_stdout(output):
            code = pk.main(["--json", "--root", str(self.root), "remove", "demo"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_missing_managed_directory_can_be_forgotten(self):
        self.installed()
        shutil.rmtree(self.root / "demo")
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})

    def test_corrupt_state_cannot_target_outside_or_internal_paths(self):
        self.root.mkdir()
        for dest in ["../outside", ".portakit-cache", ".portakit-state.json", "."]:
            state = {"demo": dict(version="1", dest=dest)}
            path = self.root / ".portakit-state.json"
            content = json.dumps(state)
            path.write_text(content)
            with self.subTest(dest=dest), self.assertRaises(pk.PortakitError):
                pk.remove("demo", self.root)
            self.assertEqual(path.read_text(), content)

    def test_state_destinations_cannot_overlap(self):
        self.root.mkdir()
        state = {"demo": dict(version="1", dest="demo"),
                 "other": dict(version="1", dest="demo/nested")}
        (self.root / ".portakit-state.json").write_text(json.dumps(state))
        with self.assertRaisesRegex(pk.PortakitError, "dest"):
            pk.remove("demo", self.root)


class PathSafetyTests(Workspace):
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

    def test_cache_file_reparse_rejected_before_open(self):
        payload = b"download"
        tool = entry(sha256=hashlib.sha256(payload).hexdigest())
        cache = self.root / ".portakit-cache"
        cache.mkdir(parents=True)
        target = cache / tool["sha256"]
        target.write_bytes(payload)
        lstat = Path.lstat
        def reparse(path, *args, **kwargs):
            if path == target:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return lstat(path, *args, **kwargs)
        with mock.patch.object(Path, "lstat", reparse):
            with self.assertRaisesRegex(pk.PortakitError, "reparse"):
                pk.fetch(tool, self.root, mock.Mock(side_effect=AssertionError("network")))


class GithubTests(InstallWorkspace):
    def load(self, tool):
        self.catalog.write_text(json.dumps({"tools": [tool]}), encoding="utf-8")
        return pk.load_catalog(self.catalog, self.root)["demo"]

    def github(self, **changes):
        tool = entry(kind="github", repo="owner/project", tag="v1.0", asset="demo x64.zip")
        del tool["url"]
        tool.update(changes)
        return tool

    def test_github_resolves_pinned_asset_without_network(self):
        with mock.patch.object(pk.urllib.request, "urlopen", side_effect=AssertionError("network")):
            tool = self.load(self.github(tag="release/1.0"))
        self.assertEqual(tool["url"],
                         "https://github.com/owner/project/releases/download/release%2F1.0/demo%20x64.zip")

    def test_github_install_downloads_exact_asset_and_verifies_sha(self):
        package, _ = self.package()
        tool = self.load(self.github(sha256=package["sha256"]))
        payload = zip_bytes([("demo.exe", b"1")])
        downloader = mock.Mock(side_effect=lambda url, dest: dest.write_bytes(payload))
        with mock.patch.object(pk.urllib.request, "urlopen", side_effect=AssertionError("network")):
            pk.install(tool, self.root, downloader)
            pk.update(tool, self.root, downloader)
        self.assertEqual(downloader.call_count, 1)
        self.assertEqual(downloader.call_args.args[0], tool["url"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_github_fields_are_validated_by_name(self):
        for field, value in [("kind", "url"), ("kind", None), ("repo", "owner"),
                             ("repo", "../project"), ("repo", "owner/project/extra"),
                             ("repo", 42), ("tag", ""), ("tag", ".."),
                             ("asset", "../demo.zip"), ("asset", "demo\\x.zip"),
                             ("asset", ""), ("asset", 42)]:
            with self.subTest(field=field, value=value), self.assertRaisesRegex(pk.PortakitError, field):
                self.load(self.github(**{field: value}))

    def test_missing_github_field_is_named(self):
        tool = self.github()
        del tool["repo"]
        with self.assertRaisesRegex(pk.PortakitError, "repo"):
            self.load(tool)

    def test_conflicting_explicit_url_is_rejected(self):
        with self.assertRaisesRegex(pk.PortakitError, "url"):
            self.load(self.github(url="https://example.invalid/wrong.zip"))


class DefaultConfigTests(InstallWorkspace):
    def test_install_seeds_missing_files_without_overwriting_packaged_config(self):
        tool, download = self.package(members=[("demo.exe", b"exe"), ("config.ini", b"packaged")],
                                      defaultConfig={"config.ini": "preset", "settings/user.ini": "한글\n"})
        pk.install(tool, self.root, download)
        self.assertEqual((self.root / "demo/config.ini").read_bytes(), b"packaged")
        self.assertEqual((self.root / "demo/settings/user.ini").read_bytes(), "한글\n".encode("utf-8"))

    def test_update_preserves_custom_config_and_seeds_new_presets(self):
        self.installed()
        (self.root / "demo/config.ini").write_text("custom")
        tool, download = self.package("2", preserveOnUpdate=["config.ini"],
                                      defaultConfig={"config.ini": "preset", "new.ini": "new"})
        pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/config.ini").read_text(), "custom")
        self.assertEqual((self.root / "demo/new.ini").read_text(), "new")

    def test_bad_presets_are_rejected_before_downloading(self):
        for config in [[], {"../outside": "bad"}, {"C:/outside": "bad"},
                       {"config.ini": 1}, {"A.ini": "a", "a.ini": "b"},
                       {"config": "file", "config/nested": "child"}]:
            tool = entry(defaultConfig=config)
            self.catalog.write_text(json.dumps({"tools": [tool]}))
            with self.subTest(config=config), self.assertRaisesRegex(pk.PortakitError, "defaultConfig"):
                pk.load_catalog(self.catalog, self.root)
        self.assertFalse(self.root.exists())

    def test_preset_failure_leaves_old_install_and_state(self):
        previous = self.installed()
        tool, download = self.package("2", defaultConfig={"config.ini": "preset"})
        write_text = Path.write_text
        def locked(path, *args, **kwargs):
            if path.name == "config.ini":
                raise PermissionError("preset locked")
            return write_text(path, *args, **kwargs)
        with mock.patch.object(Path, "write_text", locked), self.assertRaises(pk.PortakitError):
            pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), previous)
        self.assertEqual(list(self.root.glob(".portakit-stage-*")), [])


if __name__ == "__main__":
    unittest.main()
