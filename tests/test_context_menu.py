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
                          "version": "test"})
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
        self.assertEqual(self.run_menu("status", "notepad++")["items"][0]["state"], "owned")
        self.assertTrue(self.run_menu("remove", "notepad++")["changed"])

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
