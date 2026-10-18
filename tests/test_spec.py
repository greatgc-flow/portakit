"""Tests for the SPEC v12 deltas (see docs/DELTAS.md for the delta -> test map)."""

import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import test_portakit as fixtures


pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes

HOLD_LOCK = (
    "import os, msvcrt, sys\n"
    "fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT | os.O_BINARY)\n"
    "msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)\n"
    "print('ready', flush=True)\n"
    "sys.stdin.readline()\n"
)

# Runs one portakit command and hard-exits (os._exit(42)) right after the chosen
# step: rename1, rename2 (os.rename calls) or state (write_state).
KILL_SCRIPT = r'''
import importlib.util, os, sys
from pathlib import Path
module_path, root, catalog, payload, command, step = sys.argv[1:7]
spec = importlib.util.spec_from_file_location("portakit", module_path)
pk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pk)
pk.DEFAULT_CATALOG = Path(catalog)
real_rename, real_write = os.rename, pk.write_state
count = [0]
def rename(src, dst, *args, **kwargs):
    real_rename(src, dst, *args, **kwargs)
    count[0] += 1
    if step == "rename%d" % count[0]:
        os._exit(42)
def write_state(*args, **kwargs):
    real_write(*args, **kwargs)
    if step == "state":
        os._exit(42)
os.rename = rename
pk.write_state = write_state
def downloader(url, dest):
    Path(dest).write_bytes(Path(payload).read_bytes())
sys.exit(pk.main(["--json", "--root", root, command, "demo"], downloader=downloader))
'''


class LockMixin:
    @contextlib.contextmanager
    def held_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen([sys.executable, "-I", "-c", HOLD_LOCK, str(self.root / ".portakit-lock")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "ready")
            yield proc
        finally:
            proc.kill()
            proc.wait()
            proc.stdin.close()
            proc.stdout.close()


@unittest.skipUnless(os.name == "nt", "Windows only")
class LockAndRootTests(fixtures.Workspace, LockMixin):
    def test_install_with_lock_held_elsewhere_is_busy_and_touches_nothing(self):
        payload = zip_bytes([("demo.exe", b"1")])
        tool = entry(sha256=hashlib.sha256(payload).hexdigest())
        self.write_catalog([tool])
        download = mock.Mock(side_effect=AssertionError("download"))
        with self.held_lock():
            code, result = self.call("install", "demo", downloader=download)
        self.assertEqual(code, 6)
        self.assertEqual(result["error"]["code"], "busy")
        download.assert_not_called()
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [".portakit-lock"])

    def test_remove_with_lock_held_elsewhere_is_busy(self):
        self.root.mkdir()
        payload = zip_bytes([("demo.exe", b"1")])
        pk.install(entry(sha256=hashlib.sha256(payload).hexdigest()), self.root,
                   lambda url, dest: dest.write_bytes(payload))
        before = (self.root / ".portakit-state.json").read_bytes()
        with self.held_lock():
            code, result = self.call("remove", "demo")
        self.assertEqual((code, result["error"]["code"]), (6, "busy"))
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(), before)
        self.assertTrue((self.root / "demo/demo.exe").exists())

    def test_list_takes_no_lock_and_never_creates_root(self):
        self.write_catalog([entry()])
        code, result = self.call("list")
        self.assertEqual(code, 0)
        self.assertFalse(self.root.exists())
        with self.held_lock():
            code, result = self.call("list")
        self.assertEqual(code, 0)

    def test_lock_is_released_when_holder_dies(self):
        self.write_catalog([entry()])
        with self.held_lock() as proc:
            proc.kill()
            proc.wait()
            payload = zip_bytes([("demo.exe", b"1")])
            tool = entry(sha256=hashlib.sha256(payload).hexdigest())
            self.write_catalog([tool])
            code, result = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(code, 0)

    def test_lock_is_held_during_download_and_released_after(self):
        import msvcrt
        payload = zip_bytes([("demo.exe", b"1")])
        self.write_catalog([entry(sha256=hashlib.sha256(payload).hexdigest())])
        seen = []
        def downloader(url, dest):
            fd = os.open(self.root / ".portakit-lock", os.O_RDWR | os.O_BINARY)
            try:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    seen.append("free")
                except OSError:
                    seen.append("held")
            finally:
                os.close(fd)
            Path(dest).write_bytes(payload)
        code, _ = self.call("install", "demo", downloader=downloader)
        self.assertEqual((code, seen), (0, ["held"]))
        self.assertEqual((self.root / ".portakit-lock").stat().st_size, 0)
        with self.held_lock():
            pass  # lock was released by the finished command

    def test_first_run_creates_root_and_empty_lock_file(self):
        payload = zip_bytes([("demo.exe", b"1")])
        self.write_catalog([entry(sha256=hashlib.sha256(payload).hexdigest())])
        self.assertFalse(self.root.exists())
        code, _ = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "demo/demo.exe").exists())
        self.assertEqual((self.root / ".portakit-lock").stat().st_size, 0)

    def test_bad_catalog_install_exits_2_before_creating_root(self):
        self.catalog.write_text('{"tools": [{"id": "demo"}]}', encoding="utf-8")
        code, result = self.call("install", "demo")
        self.assertEqual((code, result["error"]["code"]), (2, "catalog"))
        self.assertFalse(self.root.exists())

    def test_list_rejects_todo_hash_with_exit_2(self):
        self.write_catalog([entry(sha256="TODO")])
        code, result = self.call("list")
        self.assertEqual(code, 2)
        self.assertIn("sha256", result["error"]["message"])


class TempFileTests(fixtures.InstallWorkspace):
    def test_stage_and_state_temp_names(self):
        stages, replaced = [], []
        real_extract, real_replace = pk.extract, os.replace
        def spy_extract(*args, **kwargs):
            stages.append(Path(args[2]).name)
            return real_extract(*args, **kwargs)
        def spy_replace(src, dst, *args, **kwargs):
            replaced.append((Path(src).name, Path(dst).name))
            return real_replace(src, dst, *args, **kwargs)
        tool, download = self.package()
        with mock.patch.object(pk, "extract", spy_extract), mock.patch.object(os, "replace", spy_replace):
            pk.install(tool, self.root, download)
        self.assertEqual(stages, [".portakit-stage-demo.tmp"])
        self.assertEqual(len(replaced), 1)
        self.assertRegex(replaced[0][0], r"\A\.portakit-state\.[0-9a-f]+\.tmp\Z")
        self.assertEqual(replaced[0][1], ".portakit-state.json")

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

    def test_state_and_lock_files_survive_temp_cleanup(self):
        previous = self.installed()
        tool, download = self.package("2")
        self.write_catalog([tool])
        code, _ = self.call("update", "demo", downloader=download)
        self.assertEqual(code, 0)
        self.assertTrue((self.root / ".portakit-lock").exists())
        self.assertNotEqual(self.state_bytes(), previous)


class UpdateByPinTests(fixtures.InstallWorkspace):
    def test_identical_pin_is_noop_with_changed_false(self):
        previous = self.installed()
        tool, _ = self.package()
        download = mock.Mock(side_effect=AssertionError("download"))
        result = pk.update(tool, self.root, download)
        self.assertFalse(result["changed"])
        download.assert_not_called()
        self.assertEqual(self.state_bytes(), previous)
        self.assertFalse((self.root / "demo.old").exists())

    def test_version_downgrade_also_updates(self):
        tool, download = self.package("2")
        pk.install(tool, self.root, download)
        tool, download = self.package("1")
        result = pk.update(tool, self.root, download)
        self.assertTrue(result["changed"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "1")

    def test_same_version_new_sha256_updates(self):
        self.installed()
        tool, download = self.package("1", [("demo.exe", b"rebuilt")])
        result = pk.update(tool, self.root, download)
        self.assertTrue(result["changed"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"rebuilt")
        self.assertEqual(pk.read_state(self.root)["demo"]["sha256"], tool["sha256"])

    def test_state_entry_without_sha256_counts_as_changed(self):
        self.installed()
        path = self.root / ".portakit-state.json"
        path.write_text(json.dumps({"demo": {"version": "1", "dest": "demo"}}))
        self.assertEqual(pk.read_state(self.root), {"demo": {"version": "1", "dest": "demo"}})
        tool, download = self.package()
        result = pk.update(tool, self.root, download)
        self.assertTrue(result["changed"])
        self.assertEqual(pk.read_state(self.root)["demo"]["sha256"], tool["sha256"])

    def test_identical_pin_with_missing_dest_is_repaired(self):
        self.installed()
        shutil.rmtree(self.root / "demo")
        tool, download = self.package()
        result = pk.update(tool, self.root, download)
        self.assertTrue(result["changed"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_state_stores_catalog_sha256_lowercase(self):
        payload = zip_bytes([("demo.exe", b"1")])
        self.write_catalog([entry(sha256=hashlib.sha256(payload).hexdigest().upper())])
        code, _ = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(code, 0)
        self.assertEqual(pk.read_state(self.root)["demo"]["sha256"], hashlib.sha256(payload).hexdigest())


class StateFileTests(fixtures.InstallWorkspace):
    def test_missing_state_file_is_empty(self):
        self.assertEqual(pk.read_state(self.root), {})

    def test_bad_shapes_are_state_errors(self):
        good = dict(version="1", dest="demo", sha256="a" * 64)
        for state in [[], {"demo": []}, {"demo": dict(good, version=1)},
                      {"demo": dict(good, sha256="zz")}, {"demo": dict(good, sha256=5)},
                      {"demo": dict(good, dest="../x")}, {"demo": dict(good, dest="a/b")},
                      {"demo": good, "other": dict(good, dest="DEMO")}]:
            (self.root / ".portakit-state.json").write_text(json.dumps(state))
            with self.subTest(state=state), self.assertRaises(pk.PortakitError) as caught:
                pk.read_state(self.root)
            self.assertEqual(caught.exception.code, "state")

    def test_write_state_round_trips_without_leftovers(self):
        state = {"demo": dict(version="1", dest="demo", sha256="a" * 64)}
        pk.write_state(self.root, state)
        self.assertEqual(pk.read_state(self.root), state)
        self.assertEqual([p.name for p in self.root.iterdir()], [".portakit-state.json"])


class SwapTests(fixtures.InstallWorkspace):
    def test_update_swap_is_exactly_two_os_renames_and_never_replace_or_move(self):
        self.installed()
        tool, download = self.package("2")
        renames = []
        real_replace = os.replace
        def guarded_replace(src, dst, *args, **kwargs):
            self.assertEqual(Path(dst).name, ".portakit-state.json")
            return real_replace(src, dst, *args, **kwargs)
        with self.patch_rename(lambda s, d: renames.append((s.name, d.name))), \
                mock.patch.object(os, "replace", guarded_replace), \
                mock.patch.object(shutil, "move", side_effect=AssertionError("shutil.move")):
            pk.update(tool, self.root, download)
        self.assertEqual(renames, [("demo", "demo.old"), (".portakit-stage-demo.tmp", "demo")])

    def test_install_swap_is_one_os_rename(self):
        tool, download = self.package()
        renames = []
        with self.patch_rename(lambda s, d: renames.append((s.name, d.name))):
            pk.install(tool, self.root, download)
        self.assertEqual(renames, [(".portakit-stage-demo.tmp", "demo")])

    def test_swap_never_overwrites_an_existing_target(self):
        previous = self.installed()
        tool, download = self.package("2")
        def intruder(src, dst):
            if src.name == ".portakit-stage-demo.tmp":
                (self.root / "demo").mkdir()
                (self.root / "demo/intruder").write_text("mine")
        with self.patch_rename(intruder), self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertIn(caught.exception.code, ("state", "busy"))
        self.assertEqual((self.root / "demo/intruder").read_text(), "mine")
        self.assertFalse((self.root / "demo/demo.exe").exists())
        self.assertEqual((self.root / "demo.old/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)

    def test_locked_dest_rename_via_cli_is_exit_6_with_state_unchanged(self):
        previous = self.installed()
        tool, download = self.package("2")
        self.write_catalog([tool])
        def locked(src, dst):
            if src.name == "demo":
                raise PermissionError("in use")
        with self.patch_rename(locked):
            code, result = self.call("update", "demo", downloader=download)
        self.assertEqual((code, result["error"]["code"]), (6, "busy"))
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"1")

    def test_stray_old_delete_failure_is_one_stderr_line_not_in_envelope(self):
        self.installed()
        tool, download = self.package("2")
        self.write_catalog([tool])
        real = pk.remove_tree
        def locked_old(path, *args, **kwargs):
            if Path(path).name == "demo.old":
                raise PermissionError("locked")
            return real(path, *args, **kwargs)
        for json_mode in (True, False):
            with self.subTest(json_mode=json_mode):
                with mock.patch.object(pk, "remove_tree", locked_old):
                    code, out, err = self.run_main("update", "demo", json_mode=json_mode, downloader=download)
                self.assertEqual(code, 0)
                self.assertEqual(len([l for l in err.splitlines() if l.startswith("warning:")]), 1)
                if json_mode:
                    result = json.loads(out)
                    self.assertNotIn("warnings", result)
                    self.assertNotIn("cleanupPending", result["data"])
                # reset: next sub-iteration starts from v1 again
                shutil.rmtree(self.root / "demo.old", ignore_errors=True)
                pk.remove("demo", self.root)
                v1, v1_download = self.package("1")
                pk.install(v1, self.root, v1_download)

    def test_after_stray_old_next_operation_aborts_both_present(self):
        self.installed()
        tool, download = self.package("2")
        self.write_catalog([tool])
        real = pk.remove_tree
        def locked_old(path, *args, **kwargs):
            if Path(path).name == "demo.old":
                raise PermissionError("locked")
            return real(path, *args, **kwargs)
        with mock.patch.object(pk, "remove_tree", locked_old):
            self.assertEqual(self.run_main("update", "demo", downloader=download)[0], 0)
        tool3, download3 = self.package("3")
        self.write_catalog([tool3])
        code, result = self.call("update", "demo", downloader=download3)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("both exist", result["error"]["message"])


class CliContractTests(fixtures.InstallWorkspace):
    def test_install_update_remove_data_shapes(self):
        tool, download = self.package()
        self.write_catalog([tool])
        code, result = self.call("install", "demo", downloader=download)
        self.assertEqual(code, 0)
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertTrue(result["data"]["changed"])
        self.assertTrue(os.path.samefile(result["data"]["dest"], self.root / "demo"))
        self.assertTrue(Path(result["data"]["dest"]).is_absolute())
        code, result = self.call("update", "demo", downloader=mock.Mock(side_effect=AssertionError("download")))
        self.assertEqual(code, 0)
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertFalse(result["data"]["changed"])
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["data"]), (0, {"id": "demo"}))

    def test_unknown_install_id_is_usage_and_changes_nothing(self):
        self.write_catalog([entry()])
        (self.root / "ghost.old").mkdir()
        code, result = self.call("install", "ghost")
        self.assertEqual((code, result["error"]["code"]), (1, "usage"))
        self.assertTrue((self.root / "ghost.old").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_update_of_uninstalled_id_with_stray_old_changes_nothing(self):
        self.write_catalog([entry()])
        (self.root / "demo.old").mkdir()
        download = mock.Mock(side_effect=AssertionError("download"))
        code, result = self.call("update", "demo", downloader=download)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("not installed", result["error"]["message"])
        self.assertTrue((self.root / "demo.old").exists())
        self.assertFalse((self.root / "demo").exists())

    def test_update_of_id_missing_from_catalog_is_not_in_catalog(self):
        previous = self.installed()
        self.write_catalog([entry(id="other", dest="other")])
        (self.root / "demo").rename(self.root / "demo.old")
        code, result = self.call("update", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("not in catalog", result["error"]["message"])
        self.assertIn("remove demo", result["error"]["message"])
        self.assertFalse((self.root / "demo").exists())  # resolve runs before recovery
        self.assertEqual(self.state_bytes(), previous)

    def test_update_with_changed_dest_is_state_error(self):
        previous = self.installed()
        tool, download = self.package("2", dest="other")
        self.write_catalog([tool])
        code, result = self.call("update", "demo", downloader=download)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("dest changed", result["error"]["message"])
        self.assertEqual(self.state_bytes(), previous)

    def test_remove_not_installed_and_install_already_installed(self):
        self.write_catalog([entry()])
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        tool, download = self.package()
        self.write_catalog([tool])
        self.assertEqual(self.call("install", "demo", downloader=download)[0], 0)
        again = mock.Mock(side_effect=AssertionError("download"))
        code, result = self.call("install", "demo", downloader=again)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("update", result["error"]["message"])


class CrashRecoveryTests(fixtures.InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.payload = zip_bytes([("demo.exe", b"2")])
        self.tool2 = entry(version="2", sha256=hashlib.sha256(self.payload).hexdigest())
        self.write_catalog([self.tool2])
        (self.base / "payload.zip").write_bytes(self.payload)

    def kill_at(self, command, step):
        done = subprocess.run(
            [sys.executable, "-I", "-c", KILL_SCRIPT, str(Path(pk.__file__)), str(self.root),
             str(self.catalog), str(self.base / "payload.zip"), command, step],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 42, done.stdout + done.stderr)

    def update_in_process(self):
        return self.call("update", "demo", downloader=lambda url, dest: dest.write_bytes(self.payload))

    def test_kill_after_first_rename_update_recovers(self):
        previous = self.installed()
        self.kill_at("update", "rename1")
        self.assertFalse((self.root / "demo").exists())
        self.assertEqual((self.root / "demo.old/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        code, result = self.call("list")  # list works mid-swap and touches nothing
        self.assertEqual(code, 0)
        self.assertFalse((self.root / "demo").exists())
        code, result = self.update_in_process()
        self.assertEqual(code, 0, result)
        self.assertTrue(result["data"]["changed"])
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")

    def test_kill_after_second_rename_update_aborts_both_present(self):
        previous = self.installed()
        self.kill_at("update", "rename2")
        self.assertEqual((self.root / "demo/demo.exe").read_bytes(), b"2")
        self.assertEqual((self.root / "demo.old/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual(self.call("list")[0], 0)
        code, result = self.update_in_process()
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("both exist", result["error"]["message"])
        self.assertTrue((self.root / "demo.old").exists())

    def test_kill_after_state_write_aborts_both_present_even_for_identical_pin(self):
        self.installed()
        self.kill_at("update", "state")
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")
        self.assertTrue((self.root / "demo.old").exists())
        code, result = self.update_in_process()
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("both exist", result["error"]["message"])
        shutil.rmtree(self.root / "demo.old")  # the documented manual fix
        code, result = self.update_in_process()
        self.assertEqual(code, 0)
        self.assertFalse(result["data"]["changed"])

    def test_kill_after_install_stage_rename_leaves_unmanaged_dest_to_delete(self):
        self.kill_at("install", "rename1")
        self.assertTrue((self.root / "demo/demo.exe").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        code, result = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(self.payload))
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("delete or rename", result["error"]["message"])
        shutil.rmtree(self.root / "demo")
        code, result = self.call("install", "demo", downloader=lambda url, dest: dest.write_bytes(self.payload))
        self.assertEqual(code, 0)
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "2")


@unittest.skipUnless(os.name == "nt", "Windows junctions")
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


@unittest.skipUnless(os.name == "nt", "Windows junctions")
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


class DestIsFileTests(fixtures.InstallWorkspace):
    def test_install_and_update_refuse_a_file_dest(self):
        (self.root / "demo").write_text("file")
        tool, download = self.package()
        with self.assertRaises(pk.PortakitError) as caught:
            pk.install(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual((self.root / "demo").read_text(), "file")

    def test_update_refuses_a_file_dest(self):
        previous = self.installed()
        shutil.rmtree(self.root / "demo")
        (self.root / "demo").write_text("file")
        tool, download = self.package("2")
        with self.assertRaises(pk.PortakitError) as caught:
            pk.update(tool, self.root, download)
        self.assertEqual(caught.exception.code, "state")
        self.assertEqual((self.root / "demo").read_text(), "file")
        self.assertEqual(self.state_bytes(), previous)
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(pk.__file__).with_name("README.md")).read_text(encoding="utf-8")

    def test_removed_features_are_not_documented(self):
        for removed in ("cleanupPending", "defaultConfig", "`kind`", "kind:", ".portakit-cache",
                        "--force", "TODO"):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, self.text)

    def test_exit_table_matches_spec(self):
        for code, name in [(0, None), (1, "usage"), (2, "catalog"), (3, "fetch"),
                           (4, "archive"), (5, "state"), (6, "busy")]:
            with self.subTest(code=code):
                pattern = rf"\|\s*{code}\s*\|" + (rf"\s*{name}\s*\|" if name else "")
                self.assertRegex(self.text, pattern)

    def test_documents_recovery_and_update_rules(self):
        for needle in ("dest.old", "both exist", "remove", "sha256", "-h", "data"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)


if __name__ == "__main__":
    unittest.main()
