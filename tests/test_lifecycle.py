"""Tests for lifecycle behavior."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import unittest
from unittest import mock
import urllib.error

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes


class InstallTests(fixtures.InstallWorkspace):
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


class UpdateTests(fixtures.InstallWorkspace):
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


class RemoveTests(fixtures.InstallWorkspace):
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


@unittest.skipUnless(os.name == 'nt', 'Windows only')
class LockAndRootTests(fixtures.Workspace, fixtures.LockMixin):
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


class CrashRecoveryTests(fixtures.CrashWorkspace):
    def prepare_remove_crash(self):
        previous = self.installed()
        shutil.copytree(self.root / "demo", self.root / "demo.old")
        (self.root / "demo/user.ini").write_text("custom")
        (self.root / "unmanaged").mkdir()
        (self.root / "unmanaged/keep").write_bytes(b"precious")
        return previous

    def assert_remove_retry_finishes(self):
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["data"]), (0, {"id": "demo"}))
        self.assertEqual(pk.read_state(self.root), {})
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual((self.root / "unmanaged/keep").read_bytes(), b"precious")
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_kill_after_remove_dest_keeps_entry_and_backup_for_retry(self):
        previous = self.prepare_remove_crash()
        self.kill_at("remove", "remove_dest")
        self.assertFalse((self.root / "demo").exists())
        self.assertEqual((self.root / "demo.old/demo.exe").read_bytes(), b"1")
        self.assertEqual(self.state_bytes(), previous)
        self.assert_remove_retry_finishes()

    def test_kill_after_remove_backup_keeps_entry_for_retry(self):
        previous = self.prepare_remove_crash()
        self.kill_at("remove", "remove_old")
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(self.state_bytes(), previous)
        self.assert_remove_retry_finishes()

    def test_kill_after_remove_state_write_leaves_removal_committed(self):
        self.prepare_remove_crash()
        self.kill_at("remove", "state")
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / "demo.old").exists())
        self.assertEqual(pk.read_state(self.root), {})
        self.assertEqual((self.root / "unmanaged/keep").read_bytes(), b"precious")
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("not installed", result["error"]["message"])

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


class FilesystemEdges(fixtures.FilesystemWorkspace):
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


if __name__ == "__main__":
    unittest.main()
