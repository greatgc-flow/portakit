import importlib.util
import contextlib
import io
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.error
import zipfile
import stat
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("portakit", Path(__file__).resolve().parents[1] / "portakit.py")
pk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pk)

# Real implementations captured before any test patches them.
REAL_RENAME = os.rename
REAL_REPLACE = os.replace


def entry(**changes):
    value = dict(id="demo", version="1",
                 url="https://github.com/owner/project/releases/download/v1/demo.zip",
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

    def write_catalog(self, tools):
        self.catalog.write_text(json.dumps({"tools": tools}), encoding="utf-8")

    def run_main(self, *args, json_mode=True, downloader=None):
        out, err = io.StringIO(), io.StringIO()
        argv = (["--json"] if json_mode else []) + ["--root", str(self.root), *args]
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = pk.main(argv, downloader=downloader)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def call(self, *args, downloader=None):
        code, out, _ = self.run_main(*args, downloader=downloader)
        return code, json.loads(out)

    def patch_rename(self, hook):
        """Call hook(src, dst) before every os.rename, then rename for real."""
        def rename(src, dst, *args, **kwargs):
            hook(Path(src), Path(dst))
            return REAL_RENAME(src, dst, *args, **kwargs)
        return mock.patch.object(os, "rename", rename)

    def junction(self, link, target):
        Path(target).mkdir(parents=True, exist_ok=True)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
        self.addCleanup(self.drop_junction, link)

    @staticmethod
    def drop_junction(link):
        try:
            os.rmdir(link)
        except OSError:
            pass


class CatalogTests(Workspace):
    def load(self, tools):
        self.write_catalog(tools)
        return pk.load_catalog(self.catalog)

    def test_shipped_catalog_is_plain_url_sha_entries(self):
        path = Path(pk.__file__).with_name("catalog.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        catalog = pk.load_catalog(path)
        self.assertEqual(set(catalog), {"notepad++", "winmerge", "jq"})
        for tool in raw["tools"]:
            with self.subTest(id=tool["id"]):
                for removed in ("kind", "repo", "tag", "asset", "github_url", "defaultConfig"):
                    self.assertNotIn(removed, tool)
                self.assertRegex(tool["sha256"], r"\A[a-f0-9]{64}\Z")
                self.assertEqual(pk.urllib.parse.urlsplit(tool["url"]).scheme, "https")
                self.assertTrue(pk.urllib.parse.urlsplit(tool["url"]).hostname)

    def test_valid_catalog(self):
        self.assertEqual(self.load([entry()])["demo"]["version"], "1")

    def test_mutable_latest_urls_are_catalog_errors(self):
        for path in ("latest/demo.zip", "releases/latest/download/demo.zip",
                     "releases/LATEST/demo.zip", "%6catest/demo.zip"):
            with self.subTest(path=path):
                self.write_catalog([entry(url="https://example.com/" + path)])
                code, result = self.call("list")
                self.assertEqual(code, 2)
                self.assertEqual(result["error"]["code"], "catalog")
                self.assertIn("url", result["error"]["message"])

    def test_latest_substring_in_pinned_filename_is_allowed(self):
        tool = entry(url="https://example.com/v1/latest-demo.zip")
        self.assertEqual(self.load([tool])["demo"]["url"], tool["url"])

    def test_bad_fields_are_named(self):
        for field, value in [("id", ""), ("id", "."), ("version", 1), ("version", ""),
                             ("url", "https://"), ("url", "file:///tmp/x"),
                             ("url", "http://example.com/demo.zip"),
                             ("url", "https://example.com/a b.zip"),
                             ("sha256", "bad"), ("artifact", "tar"),
                             ("preserveOnUpdate", ["../outside"]), ("preserveOnUpdate", "x")]:
            with self.subTest(field=field, value=value), self.assertRaisesRegex(pk.PortakitError, field):
                self.load([entry(**{field: value})])

    def test_each_required_field_is_named_when_missing(self):
        for field in ("id", "version", "url", "sha256", "artifact", "dest"):
            tool = entry()
            del tool[field]
            with self.subTest(field=field), self.assertRaisesRegex(pk.PortakitError, field):
                self.load([tool])

    def test_duplicate_id(self):
        with self.assertRaisesRegex(pk.PortakitError, "id"):
            self.load([entry(), entry()])

    def test_removed_and_unknown_fields_are_ignored(self):
        tool = self.load([entry(kind="github", repo="x/y", tag="t", asset="a.zip",
                                defaultConfig={"a.ini": "x"}, whatever=1)])["demo"]
        self.assertEqual(tool["id"], "demo")

    def test_todo_hash_is_rejected_at_load(self):
        for value in ("TODO", "todo"):
            with self.subTest(value=value), self.assertRaisesRegex(pk.PortakitError, "sha256"):
                self.load([entry(sha256=value)])

    def test_sha256_is_normalized_to_lowercase(self):
        self.assertEqual(self.load([entry(sha256="A" * 64)])["demo"]["sha256"], "a" * 64)

    def test_dest_must_be_one_safe_unreserved_segment(self):
        for dest in ["../outside", "/absolute", "C:\\escape", "..\\outside", ".",
                     ".portakit-cache", ".portakit-state.json", ".portakit-x", "x.old",
                     "a/b", "a\\b", "con", "NUL.txt", "bad:name", "trail.", "trail "]:
            with self.subTest(dest=dest), self.assertRaisesRegex(pk.PortakitError, "dest"):
                self.load([entry(dest=dest)])

    def test_id_exe_must_pass_path_rule(self):
        for identifier in ("con", "nul", "aux", "com1", "lpt9"):
            with self.subTest(id=identifier), self.assertRaisesRegex(pk.PortakitError, "id"):
                self.load([entry(id=identifier, dest="ok")])

    def test_dest_unique_case_insensitively(self):
        with self.assertRaisesRegex(pk.PortakitError, "dest"):
            self.load([entry(id="a", dest="Tool"), entry(id="b", dest="tool")])

    def test_malformed_json_names_catalog(self):
        self.catalog.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(pk.PortakitError, "catalog"):
            pk.load_catalog(self.catalog)

    def test_tools_must_be_a_list(self):
        self.catalog.write_text('{"tools": false}', encoding="utf-8")
        with self.assertRaisesRegex(pk.PortakitError, "tools"):
            pk.load_catalog(self.catalog)


class EnvelopeTests(Workspace):
    def test_help_explains_commands_flags_and_data_loss(self):
        code, out, err = self.run_main("--help")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        for text in ("list", "install ID", "update ID", "remove ID",
                     "require ID", "current directory", "portable", "--root",
                     "--json", "JSON", "user data", "catalog"):
            with self.subTest(text=text):
                self.assertIn(text, " ".join(out.split()))

    def test_exit_codes_are_stable(self):
        self.assertEqual(pk.EXIT_CODES, dict(ok=0, usage=1, catalog=2, fetch=3,
                                             archive=4, state=5, busy=6))

    def test_abbreviated_options_are_usage_errors(self):
        self.write_catalog([entry()])
        for option in ["--j", "--roo"]:
            with self.subTest(option=option):
                code, result = self.call(option, "list")
                self.assertEqual(code, 1)
                self.assertEqual(result["error"]["code"], "usage")

    def test_http_exception_is_fetch_and_oserror_is_state(self):
        self.write_catalog([entry()])
        for error, expected in [(http.client.HTTPException("broken response"), "fetch"),
                                (OSError("disk full"), "state")]:
            with self.subTest(error=type(error).__name__), mock.patch.object(pk, "install", side_effect=error):
                code, result = self.call("install", "demo")
                self.assertEqual(code, pk.EXIT_CODES[expected])
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], expected)
                self.assertIn(str(error), result["error"]["message"])

    def test_urlerror_from_download_is_fetch(self):
        self.write_catalog([entry()])
        with mock.patch.object(pk.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            code, result = self.call("install", "demo")
        self.assertEqual(code, 3)
        self.assertEqual(result["error"]["code"], "fetch")

    def test_list_json_envelope_has_data_items(self):
        self.write_catalog([entry()])
        code, result = self.call("list")
        self.assertEqual(code, 0)
        self.assertEqual(set(result), {"ok", "command", "data", "error"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "list")
        self.assertIsNone(result["error"])
        self.assertEqual(set(result["data"]), {"items"})
        self.assertEqual(result["data"]["items"][0]["id"], "demo")

    def test_list_human_output_is_id_tab_version(self):
        self.write_catalog([entry()])
        code, out, _ = self.run_main("list", json_mode=False)
        self.assertEqual((code, out), (0, "demo\t1\n"))

    def test_catalog_error_json(self):
        self.catalog.write_text('{"tools":false}')
        code, result = self.call("list")
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "catalog")
        self.assertIn("tools", result["error"]["message"])

    def test_usage_error_is_json(self):
        code, result = self.call("install")
        self.assertEqual(code, 1)
        self.assertEqual(result["error"]["code"], "usage")

    def test_usage_error_under_json_is_exactly_one_envelope(self):
        code, out, err = self.run_main("--bogus")
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual((result["ok"], result["command"], result["data"]), (False, None, None))
        self.assertEqual(result["error"]["code"], "usage")
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_help_exits_zero_with_human_text_and_no_envelope(self):
        for argv in (["-h"], ["--json", "-h"], ["--help", "--json"]):
            out, err = io.StringIO(), io.StringIO()
            with self.subTest(argv=argv), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = pk.main(argv)
                except SystemExit as exc:
                    code = exc.code
            self.assertEqual(code, 0)
            self.assertIn("usage", out.getvalue().lower())
            with self.assertRaises(ValueError):
                json.loads(out.getvalue())

    def test_errors_go_to_stderr_without_json(self):
        self.root.mkdir()
        code, out, err = self.run_main("remove", "demo", json_mode=False)
        self.assertEqual(code, 5)
        self.assertEqual(out, "")
        self.assertIn("not installed", err)


class DownloadTests(Workspace):
    def setUp(self):
        super().setUp()
        self.root.mkdir()

    def payload_tool(self, payload):
        return entry(sha256=hashlib.sha256(payload).hexdigest())

    def test_mismatch_aborts_deletes_temp_and_installs_nothing(self):
        with self.assertRaisesRegex(pk.PortakitError, "SHA256") as caught:
            pk.install(entry(), self.root, lambda url, dest: dest.write_bytes(b"bad"))
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
        with self.assertRaisesRegex(pk.PortakitError, "zip") as caught:
            pk.extract(source, entry(), self.root)
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse(self.root.exists())


class InstallWorkspace(Workspace):
    def setUp(self):
        super().setUp()
        self.root.mkdir()

    def package(self, version="1", members=None, **changes):
        payload = zip_bytes(members if members is not None else [("demo.exe", version.encode())])
        tool = entry(version=version, sha256=hashlib.sha256(payload).hexdigest(), **changes)
        return tool, lambda url, dest: dest.write_bytes(payload)

    def installed(self):
        tool, download = self.package()
        pk.install(tool, self.root, download)
        return (self.root / ".portakit-state.json").read_bytes()

    def state_bytes(self):
        return (self.root / ".portakit-state.json").read_bytes()


class InstallTests(InstallWorkspace):
    def test_install_refuses_installed_tool_and_points_to_update(self):
        previous = self.installed()
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "update") as caught:
            pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        download.assert_not_called()
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_locked_old_delete_is_success_with_one_stderr_warning(self):
        self.installed()
        tool, download = self.package("2")
        real = pk.remove_tree
        def locked_old(path, *args, **kwargs):
            if Path(path).name == "demo.old":
                raise PermissionError("locked backup")
            return real(path, *args, **kwargs)
        err = io.StringIO()
        with mock.patch.object(pk, "remove_tree", locked_old), contextlib.redirect_stderr(err):
            result = pk.update(tool, self.root, download)
        self.assertNotIn("cleanupPending", result)
        self.assertTrue(result["changed"])
        warnings = [line for line in err.getvalue().splitlines() if line.startswith("warning:")]
        self.assertEqual(len(warnings), 1)
        self.assertIn("could not delete", warnings[0])
        self.assertIn("demo.old", warnings[0])
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")

    def test_install_stages_and_records_state_with_sha256(self):
        tool, download = self.package()
        result = pk.install(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(pk.read_state(self.root)["demo"],
                         dict(version="1", sha256=tool["sha256"], dest="demo"))
        self.assertEqual(set(result), {"id", "version", "dest", "changed"})
        self.assertEqual((result["id"], result["version"], result["changed"]), ("demo", "1", True))
        self.assertTrue(Path(result["dest"]).is_absolute())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_update_swaps_then_deletes_old(self):
        self.installed()
        tool, download = self.package("2")
        pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")
        self.assertFalse((self.root / "demo.old").exists())

    def test_permission_error_on_stage_rename_is_busy_and_restores(self):
        previous = self.installed()
        tool, download = self.package("2")
        def locked(src, dst):
            if src.name.startswith(".portakit-stage-"):
                raise PermissionError("locked")
        with self.patch_rename(locked), self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "busy")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_state_write_failure_restores_previous_install(self):
        previous = self.installed()
        tool, download = self.package("2")
        with mock.patch.object(pk, "write_state", side_effect=OSError("state locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_initial_install_state_failure_leaves_nothing_installed(self):
        tool, download = self.package()
        with mock.patch.object(pk, "write_state", side_effect=OSError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.install(tool, self.root, download)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_unmanaged_directory_is_not_overwritten(self):
        (self.root / "demo").mkdir()
        (self.root / "demo/keep").write_text("mine")
        tool, download = self.package()
        with self.assertRaisesRegex(pk.PortakitError, "unmanaged") as caught:
            pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
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
        with self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "archive")
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertFalse((self.base / "escape").exists())

    def test_cli_install_uses_injected_downloader(self):
        tool, download = self.package(artifact="exe", id="jq", dest="jq")
        self.write_catalog([tool])
        code, result = self.call("install", "jq", downloader=download)
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertTrue((self.root / "jq/jq.exe").exists())


class UpdateTests(InstallWorkspace):
    def test_failed_old_restore_is_recovered_on_next_update(self):
        previous = self.installed()
        tool, download = self.package("2")
        def locked_restore(src, dst):
            if src == self.root / "demo.old":
                raise PermissionError("backup locked")
        with self.patch_rename(locked_restore), mock.patch.object(
                pk, "write_state", side_effect=OSError("state failed")):
            with self.assertRaisesRegex(pk.PortakitError, "demo.old") as caught:
                pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertTrue((self.root / "demo.old/demo.exe").exists())
        self.assertFalse((self.root / "demo").exists())
        # Recovery renames demo.old back before anything else; fail afterwards.
        with mock.patch.object(pk, "extract", side_effect=OSError("extract failed")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)

    def test_rollback_that_cannot_delete_new_dest_leaves_both_and_next_op_aborts(self):
        previous = self.installed()
        tool, download = self.package("2")
        real = pk.remove_tree
        def locked_new(path, *args, **kwargs):
            if Path(path) == self.root / "demo":
                raise PermissionError("new dest locked")
            return real(path, *args, **kwargs)
        with mock.patch.object(pk, "remove_tree", locked_new), mock.patch.object(
                pk, "write_state", side_effect=OSError("state failed")):
            with self.assertRaisesRegex(pk.PortakitError, "demo.old") as caught:
                pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertTrue((self.root / "demo").exists())
        self.assertTrue((self.root / "demo.old").exists())
        self.assertEqual(self.state_bytes(), previous)
        with self.assertRaisesRegex(pk.PortakitError, "both exist"):
            pk.update(tool, self.root, download)

    def test_keyboard_interrupt_rolls_back_swap(self):
        previous = self.installed()
        tool, download = self.package("2")
        with mock.patch.object(pk, "write_state", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_install_never_recovers_a_stray_old(self):
        previous = self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "update"):
            pk.install(tool, self.root, download)
        self.assertFalse((self.root / "demo").exists())
        self.assertTrue((self.root / "demo.old/demo.exe").exists())
        self.assertEqual(self.state_bytes(), previous)
        download.assert_not_called()

    def test_install_refuses_stray_old_as_unmanaged(self):
        (self.root / "demo.old").mkdir()
        (self.root / "demo.old/keep").write_text("mine")
        tool, _ = self.package()
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "delete or rename") as caught:
            pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual((self.root / "demo.old/keep").read_text(), "mine")
        self.assertFalse((self.root / "demo").exists())

    def test_stale_old_is_recovered_before_update_download_failure(self):
        previous = self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        tool, _ = self.package("2")
        with self.assertRaisesRegex(pk.PortakitError, "offline") as caught:
            pk.update(tool, self.root, mock.Mock(side_effect=urllib.error.URLError("offline")))
        self.assertEqual(caught.exception.code, "fetch")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_both_present_aborts_with_manual_fix_message(self):
        previous = self.installed()
        (self.root / "demo.old").mkdir()
        (self.root / "demo.old/marker").write_text("old")
        tool, _ = self.package("2")
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "both exist") as caught:
            pk.update(tool, self.root, download)
        message = str(caught.exception)
        self.assertEqual(caught.exception.code, "state")
        self.assertIn("demo.old", message)
        self.assertIn("delete", message)
        self.assertIn("rename", message)
        download.assert_not_called()
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo.old/marker").read_text(), "old")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

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

    def test_state_write_permission_error_rolls_back_settings_binary_and_state(self):
        previous = self.installed()
        (self.root / "demo/config.ini").write_text("custom")
        tool, download = self.package("2", preserveOnUpdate=["config.ini"])
        with mock.patch.object(pk, "write_state", side_effect=PermissionError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual((self.root / "demo/config.ini").read_text(), "custom")
        self.assertEqual(self.state_bytes(), previous)

    def test_preserve_copy_failure_leaves_previous_install(self):
        previous = self.installed()
        (self.root / "demo/config.ini").write_text("custom")
        tool, download = self.package("2", preserveOnUpdate=["config.ini"])
        with mock.patch.object(pk.shutil, "copy2", side_effect=PermissionError("locked")):
            with self.assertRaises(pk.PortakitError):
                pk.update(tool, self.root, download)
        self.assertEqual((self.root / "demo/config.ini").read_text(), "custom")
        self.assertEqual(self.state_bytes(), previous)

    def test_update_requires_installed_tool_and_changes_nothing(self):
        (self.root / "demo.old").mkdir()
        tool, _ = self.package()
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.assertRaisesRegex(pk.PortakitError, "not installed") as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertTrue((self.root / "demo.old").exists())
        self.assertFalse((self.root / "demo").exists())
        download.assert_not_called()

    def test_update_rejects_changed_destination(self):
        previous = self.installed()
        tool, download = self.package("2", dest="other")
        with self.assertRaisesRegex(pk.PortakitError, "dest changed; remove demo and install again") as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "other").exists())


class RemoveTests(InstallWorkspace):
    def test_delete_order_is_dest_then_old_then_state_last(self):
        self.installed()
        (self.root / "demo.old").mkdir()
        (self.root / "demo.old/f").write_text("x")
        events = []
        real_remove, real_write = pk.remove_tree, pk.write_state
        def spy_remove(path, *args, **kwargs):
            events.append(("delete", Path(path).name, "demo" in pk.read_state(self.root)))
            return real_remove(path, *args, **kwargs)
        def spy_write(root, state):
            events.append(("state", sorted(state)))
            return real_write(root, state)
        with mock.patch.object(pk, "remove_tree", spy_remove), mock.patch.object(pk, "write_state", spy_write):
            result = pk.remove("demo", self.root)
        self.assertEqual(events, [("delete", "demo", True), ("delete", "demo.old", True), ("state", [])])
        self.assertEqual(result, {"id": "demo"})
        self.assertEqual(pk.read_state(self.root), {})

    def test_state_write_failure_keeps_entry_and_retry_finishes(self):
        previous = self.installed()
        for error, code in [(OSError("state locked"), "state"), (PermissionError("locked"), "busy")]:
            with self.subTest(error=type(error).__name__), mock.patch.object(pk, "write_state", side_effect=error):
                with self.assertRaises(pk.PortakitError) as caught:
                    pk.remove("demo", self.root)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo").exists())  # an entry without a dest is allowed
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})

    def test_keyboard_interrupt_keeps_entry(self):
        previous = self.installed()
        with mock.patch.object(pk, "write_state", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pk.remove("demo", self.root)
        self.assertEqual(self.state_bytes(), previous)
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})

    def test_locked_dest_is_busy_and_keeps_dest_and_entry(self):
        previous = self.installed()
        real = pk.remove_tree
        def locked(path, *args, **kwargs):
            if Path(path) == self.root / "demo":
                raise PermissionError("in use")
            return real(path, *args, **kwargs)
        with mock.patch.object(pk, "remove_tree", locked), self.assertRaises(pk.PortakitError) as caught:
            pk.remove("demo", self.root)
        self.assertEqual(caught.exception.code, "busy")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})

    def test_other_delete_failure_is_state_and_keeps_entry(self):
        previous = self.installed()
        with mock.patch.object(pk, "remove_tree", side_effect=OSError("disk")):
            with self.assertRaises(pk.PortakitError) as caught:
                pk.remove("demo", self.root)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual(self.state_bytes(), previous)

    def test_remove_only_managed_directory_and_its_state_entry(self):
        self.installed()
        tool, download = self.package(id="other", dest="other")
        pk.install(tool, self.root, download)
        (self.root / "unmanaged").mkdir()
        (self.root / "unmanaged/keep").write_text("mine")
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assertEqual(set(pk.read_state(self.root)), {"other"})
        self.assertTrue((self.root / "other/demo.exe").exists())
        self.assertEqual((self.root / "unmanaged/keep").read_text(), "mine")

    def test_remove_unmanaged_is_rejected(self):
        (self.root / "demo").mkdir()
        with self.assertRaisesRegex(pk.PortakitError, "not installed") as caught:
            pk.remove("demo", self.root)
        self.assertEqual(caught.exception.code, "state")
        self.assertTrue((self.root / "demo").exists())

    def test_remove_works_without_catalog(self):
        self.installed()
        code, result = self.call("remove", "demo")  # catalog file does not exist
        self.assertEqual(code, 0)
        self.assertEqual(result["data"], {"id": "demo"})

    def test_remove_works_with_broken_catalog(self):
        self.installed()
        self.catalog.write_text("{", encoding="utf-8")
        code, result = self.call("remove", "demo")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_missing_managed_directory_can_be_forgotten(self):
        self.installed()
        shutil.rmtree(self.root / "demo")
        pk.remove("demo", self.root)
        self.assertEqual(pk.read_state(self.root), {})

    def test_remove_with_only_old_deletes_it_without_recovery(self):
        self.installed()
        (self.root / "demo").rename(self.root / "demo.old")
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(pk.read_state(self.root), {})

    def test_remove_with_both_present_deletes_both(self):
        self.installed()
        (self.root / "demo.old").mkdir()
        pk.remove("demo", self.root)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(pk.read_state(self.root), {})

    def test_remove_regular_file_dest_is_state_error_and_keeps_entry(self):
        previous = self.installed()
        shutil.rmtree(self.root / "demo")
        (self.root / "demo").write_text("file")
        with self.assertRaises(pk.PortakitError) as caught:
            pk.remove("demo", self.root)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual((self.root / "demo").read_text(), "file")
        self.assertEqual(self.state_bytes(), previous)

    def test_corrupt_state_cannot_target_outside_or_internal_paths(self):
        for dest in ["../outside", ".portakit-cache", ".portakit-state.json", ".", "a/b"]:
            state = {"demo": dict(version="1", dest=dest)}
            path = self.root / ".portakit-state.json"
            content = json.dumps(state)
            path.write_text(content)
            with self.subTest(dest=dest), self.assertRaises(pk.PortakitError) as caught:
                pk.remove("demo", self.root)
            self.assertEqual(caught.exception.code, "state")
            self.assertEqual(path.read_text(), content)

    def test_state_destinations_cannot_collide_case_insensitively(self):
        state = {"demo": dict(version="1", dest="demo"),
                 "other": dict(version="1", dest="DEMO")}
        (self.root / ".portakit-state.json").write_text(json.dumps(state))
        with self.assertRaisesRegex(pk.PortakitError, "dest") as caught:
            pk.remove("demo", self.root)
        self.assertEqual(caught.exception.code, "state")


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


if __name__ == "__main__":
    unittest.main()
