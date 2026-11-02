"""Mock-backed HKCU Explorer context-menu tests, without real registry changes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "context_menu.py"
spec = importlib.util.spec_from_file_location("portakit_context_menu", SOURCE)
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class FakeKey:
    def __init__(self, registry, path):
        self.registry, self.path = registry, path

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = 1
    KEY_READ = 1
    KEY_WRITE = 2
    REG_SZ = 1

    def __init__(self):
        self.keys = {}
        self.fail_on_set = None

    def OpenKey(self, hive, path, *args):
        if hive != self.HKEY_CURRENT_USER or path not in self.keys:
            raise FileNotFoundError(path)
        return FakeKey(self, path)

    def CreateKeyEx(self, hive, path, *args):
        if hive != self.HKEY_CURRENT_USER:
            raise ValueError("Wrong hive")
        self.keys.setdefault(path, {})
        return FakeKey(self, path)

    def SetValueEx(self, key, name, reserved, kind, value):
        if name == self.fail_on_set:
            raise PermissionError("injected registry denial")
        self.keys[key.path][name] = (value, kind)

    def EnumValue(self, key, index):
        values = list(self.keys[key.path].items())
        if index >= len(values):
            raise OSError("No more values")
        name, (value, kind) = values[index]
        return name, value, kind

    def EnumKey(self, key, index):
        prefix = key.path + "\\"
        children = sorted({p[len(prefix):].split("\\")[0] for p in self.keys
                           if p.startswith(prefix)})
        if index >= len(children):
            raise OSError("No more keys")
        return children[index]

    def QueryInfoKey(self, key):
        return (len([1 for x in self.keys if x.startswith(key.path + "\\")]),
                len(self.keys[key.path]), None)

    def DeleteKey(self, hive, path):
        if hive != self.HKEY_CURRENT_USER:
            raise ValueError("Wrong hive")
        if path not in self.keys:
            raise FileNotFoundError(path)
        if any(p.startswith(path + "\\") for p in self.keys):
            raise PermissionError("Subkeys exist")
        del self.keys[path]


class ContextMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        self.root = self.dir / "portable"
        self.root.mkdir()
        self.registry = FakeWinreg()
        tools = []
        state = {}
        for app in ("notepad++", "winmerge"):
            (self.root / app).mkdir()
            (self.root / app / menu.EXES[app]).write_bytes(b"EXE")
            tools.append({"id": app, "dest": app, "sha256": "a" * 64,
                          "version": "test", "artifact": "zip",
                          "url": "https://example.invalid/releases/download/test/" +
                                 app + ".zip"})
            state[app] = {"version": "test", "dest": app, "sha256": "a" * 64}
        (self.root / ".portakit-state.json").write_text(json.dumps(state))
        (self.repo / "catalog.json").write_text(json.dumps({"tools": tools}))

    def run_menu(self, verb, app):
        return menu.perform(verb, app, self.root, self.repo, self.registry)

    def test_notepad_install_is_opt_in_and_idempotent(self):
        self.assertEqual(self.run_menu("status", "notepad++")["items"][0]["state"], "absent")
        self.assertTrue(self.run_menu("install", "notepad++")["changed"])
        self.assertFalse(self.run_menu("install", "notepad++")["changed"])
        key = menu.registry_path(menu.ENTRIES["notepad++"][0][0])
        self.assertEqual(self.registry.keys[key]["PortaKitOwner"][0], menu.OWNER)
        self.assertEqual(self.registry.keys[key + r"\command"][""][0],
                         '"' + str(self.root / "notepad++/notepad++.exe") + '" "%1"')
        self.assertEqual(self.run_menu("status", "notepad++")["items"][0]["state"], "owned")
        self.assertTrue(self.run_menu("remove", "notepad++")["changed"])
        self.assertFalse(self.run_menu("remove", "notepad++")["changed"])
        self.assertFalse(self.registry.keys)

    def test_winmerge_files_and_directories_are_independent(self):
        self.assertTrue(self.run_menu("install", "winmerge")["changed"])
        self.assertEqual(len(self.run_menu("status", "winmerge")["items"]), 2)
        keys = sorted(self.registry.keys)
        self.assertEqual(len(keys), 4)
        self.assertTrue(any("Directory" in x for x in keys))
        self.assertTrue(any("*" in x for x in keys))
        self.assertTrue(self.run_menu("remove", "winmerge")["changed"])
        self.assertFalse(self.registry.keys)

    def test_collision_refuses_all_changes(self):
        target = menu.registry_path(menu.ENTRIES["winmerge"][1][0])
        self.registry.keys[target] = {"": ("foreign", self.registry.REG_SZ)}
        with self.assertRaisesRegex(menu.MenuError, "already exists"):
            self.run_menu("install", "winmerge")
        self.assertEqual(self.registry.keys, {
            target: {"": ("foreign", self.registry.REG_SZ)}})

    def test_modified_entry_is_never_deleted(self):
        self.run_menu("install", "winmerge")
        key = menu.registry_path(menu.ENTRIES["winmerge"][1][0])
        self.registry.keys[key + r"\command"][""] = ("evil.exe", self.registry.REG_SZ)
        with self.assertRaisesRegex(menu.MenuError, "modified"):
            self.run_menu("remove", "winmerge")
        self.assertIn(key, self.registry.keys)

    def test_not_owned_key_is_not_removed(self):
        key = menu.registry_path(menu.ENTRIES["notepad++"][0][0])
        self.registry.keys[key] = {"": ("someone else's command", self.registry.REG_SZ)}
        with self.assertRaisesRegex(menu.MenuError, "foreign"):
            self.run_menu("remove", "notepad++")
        self.assertIn(key, self.registry.keys)

    def test_removed_app_still_has_reversible_context_menu(self):
        self.run_menu("install", "notepad++")
        (self.root / "notepad++/notepad++.exe").unlink()
        before = dict(self.registry.keys)
        report = self.run_menu("status", "notepad++")
        self.assertFalse(report["changed"])
        self.assertEqual(report["items"][0]["state"], "stale")
        self.assertEqual(self.registry.keys, before)
        self.assertTrue(self.run_menu("remove", "notepad++")["changed"])
        self.assertFalse(self.registry.keys)

    def test_missing_managed_receipt_is_stale_not_foreign_and_removable(self):
        self.run_menu("install", "notepad++")
        (self.root / ".portakit-state.json").unlink()
        state = self.run_menu("status", "notepad++")
        self.assertEqual(state["items"][0]["state"], "stale")
        self.assertFalse(state["changed"])
        self.assertTrue(self.run_menu("remove", "notepad++")["changed"])

    def test_moved_root_reports_stale_without_registry_mutation(self):
        self.run_menu("install", "winmerge")
        other_root = self.dir / "moved-root"
        (other_root / "winmerge").mkdir(parents=True)
        (other_root / "winmerge" / menu.EXES["winmerge"]).write_bytes(b"EXE")
        (other_root / ".portakit-state.json").write_bytes(
            (self.root / ".portakit-state.json").read_bytes())
        before = {key: dict(value) for key, value in self.registry.keys.items()}
        report = menu.perform("status", "winmerge", other_root, self.repo,
                              self.registry)
        self.assertEqual([x["state"] for x in report["items"]],
                         ["stale", "stale"])
        self.assertFalse(report["changed"])
        self.assertEqual(self.registry.keys, before)
        self.assertTrue(self.run_menu("remove", "winmerge")["changed"])

    def test_missing_or_changed_pin_is_stale_and_cannot_register(self):
        for mutation in ("no-sha", "wrong-sha", "wrong-version"):
            with self.subTest(mutation=mutation):
                self.run_menu("install", "notepad++")
                state_file = self.root / ".portakit-state.json"
                source = json.loads(state_file.read_text(encoding="utf-8"))
                if mutation == "no-sha":
                    source["notepad++"].pop("sha256")
                elif mutation == "wrong-sha":
                    source["notepad++"]["sha256"] = "f" * 64
                else:
                    source["notepad++"]["version"] = "other"
                state_file.write_text(json.dumps(source), encoding="utf-8")
                self.assertEqual(self.run_menu("status", "notepad++")
                                 ["items"][0]["state"], "stale")
                with self.assertRaisesRegex(menu.MenuError, "mismatch"):
                    self.run_menu("install", "notepad++")
                # Explicit remove may still remove only an exact owned key.
                self.assertTrue(self.run_menu("remove", "notepad++")["changed"])
                source["notepad++"] = {"version": "test", "dest": "notepad++",
                                        "sha256": "a" * 64}
                state_file.write_text(json.dumps(source), encoding="utf-8")

    def test_duplicate_json_fields_and_catalog_ids_fail_closed(self):
        catalog_path = self.repo / "catalog.json"
        state_path = self.root / ".portakit-state.json"
        valid_catalog = catalog_path.read_text(encoding="utf-8")
        valid_state = state_path.read_text(encoding="utf-8")
        tests = (
            (catalog_path, '{"tools": [], "tools": ' +
             json.dumps(json.loads(valid_catalog)["tools"]) + '}'),
            (state_path, valid_state.replace('"version": "test"',
                                             '"version": "other", "version": "test"', 1)),
            (catalog_path, json.dumps({"tools":
                 json.loads(valid_catalog)["tools"] +
                 [json.loads(valid_catalog)["tools"][0]]})),
            (state_path, valid_state.replace('"dest": "notepad++"',
                                             '"unused": NaN, "dest": "notepad++"', 1)),
        )
        for path, malformed in tests:
            with self.subTest(path=path, invalid=malformed[:35]):
                path.write_text(malformed, encoding="utf-8")
                with self.assertRaises(menu.MenuError):
                    self.run_menu("install", "notepad++")
                self.assertFalse(self.registry.keys)
                path.write_text(valid_catalog if path == catalog_path else valid_state,
                                encoding="utf-8")

    def test_unmanaged_or_missing_app_never_registers(self):
        state = self.root / ".portakit-state.json"
        state.unlink()
        with self.assertRaisesRegex(menu.MenuError, "managed"):
            self.run_menu("install", "notepad++")
        self.assertFalse(self.registry.keys)

    def test_partial_winmerge_install_failure_rolls_back_created_keys(self):
        self.registry.fail_on_set = "Icon"
        with self.assertRaises(PermissionError):
            self.run_menu("install", "winmerge")
        self.assertFalse(self.registry.keys)

    def test_no_jq_context_menu(self):
        with self.assertRaisesRegex(menu.MenuError, "jq"):
            self.run_menu("install", "jq")

    def test_cli_evidence_cannot_modify_managed_root_or_backup(self):
        """All commands must reject logs that would contaminate managed data."""
        import contextlib
        import io
        paths = (
            self.root / "notepad++" / "menu.log",
            self.root / "winmerge" / "menu.log",
            self.root / "notepad++" / "plugins" / "menu.log",
            self.root / "notepad++.old" / "menu.log",
            self.root / ".portakit-stage-test.tmp" / "menu.log",
            self.root / "misc" / "menu.log",
            self.root / "direct.log",
        )
        state_before = (self.root / ".portakit-state.json").read_bytes()
        for verb in ("status", "install", "remove"):
            for path in paths:
                with self.subTest(verb=verb, path=str(path)):
                    out, err = io.StringIO(), io.StringIO()
                    with mock.patch.object(
                            menu, "perform",
                            side_effect=AssertionError("unexpected registry call")) as action:
                        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                            rc = menu.main([verb, "notepad++", "--root",
                                            str(self.root), "--log-file", str(path)])
                    self.assertEqual(rc, 1)
                    self.assertEqual(out.getvalue(), "")
                    self.assertIn("within --root", err.getvalue())
                    self.assertFalse(path.exists())
                    action.assert_not_called()
        self.assertEqual((self.root / ".portakit-state.json").read_bytes(),
                         state_before)
        self.assertFalse(self.registry.keys)

    def test_cli_allowed_evidence_paths_keep_exact_transcript(self):
        """Reserved and external new logs remain supported with no registry side effects."""
        import contextlib
        import io
        for target in (self.root / ".portakit-evidence" / "context.log",
                       self.dir / "external-context.log"):
            with self.subTest(target=str(target)):
                out, err = io.StringIO(), io.StringIO()
                with mock.patch.object(
                        menu, "perform",
                        return_value={"changed": False, "items": [
                            {"key": "synthetic", "state": "absent"}]}) as action:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = menu.main(["status", "notepad++", "--root",
                                        str(self.root), "--log-file", str(target)])
                self.assertEqual((rc, err.getvalue()), (0, ""))
                action.assert_called_once()
                self.assertEqual(out.getvalue(), target.read_text("utf-8"))
                self.assertIn("RESULT: NO_CHANGE", out.getvalue())
        self.assertFalse(self.registry.keys)

    def test_echo_reparse_path_fails_before_creating_parent(self):
        """A synthetic unsafe ancestor never becomes an evidence directory."""
        target = self.dir / "unsafe" / "menu.log"
        with mock.patch.object(menu.core, "check_links",
                               side_effect=menu.core.PortakitError(
                                   "state", "synthetic reparse ancestor")):
            with self.assertRaisesRegex(menu.core.PortakitError, "reparse"):
                menu.Echo(target)
        self.assertFalse(target.parent.exists())
        self.assertFalse(target.exists())

    def test_mocked_console_log_matches_displayed_text(self):
        log = self.dir / "logs" / "menu.log"
        with mock.patch("builtins.print") as p:
            echo = menu.Echo(log)
            try:
                echo.line("OPERATION: install notepad++")
                echo.line("RESULT: NO_CHANGE")
            finally:
                echo.close()
        self.assertEqual(log.read_text(), "OPERATION: install notepad++\nRESULT: NO_CHANGE\n")
        self.assertEqual([x.args[0] for x in p.call_args_list],
                         ["OPERATION: install notepad++", "RESULT: NO_CHANGE"])


if __name__ == "__main__":
    unittest.main()
