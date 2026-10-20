"""Opt-in recommended profile tests: settings and verified external plugins."""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes


class RecommendedTests(fixtures.InstallWorkspace):
    def profile(self, *, with_plugin=True):
        plugin_data = zip_bytes([("ComparePlus.dll", b"trusted"), ("libs/sqlite.dll", b"lib")])
        plugin = dict(id="compareplus", version="3.0.0",
                      url="https://github.com/example/plugin/releases/download/v3/ComparePlus.zip",
                      sha256=hashlib.sha256(plugin_data).hexdigest(),
                      dest="plugins/ComparePlus", requiredFile="ComparePlus.dll")
        config = dict(settings="notepad++-dev", plugins=[plugin] if with_plugin else [])
        tool, base_downloader = self.package("1", members=[
            ("demo.exe", b"app"), ("config.xml", b'<NotepadPlus><GUIConfigs><GUIConfig name="TabSetting" size="8" replaceBySpace="no" /></GUIConfigs></NotepadPlus>')])
        tool["recommended"] = config
        base_data = zip_bytes([("demo.exe", b"app"), ("config.xml", b'<NotepadPlus><GUIConfigs><GUIConfig name="TabSetting" size="8" replaceBySpace="no" /></GUIConfigs></NotepadPlus>')])
        def download(url, path):
            path.write_bytes(plugin_data if "ComparePlus.zip" in url else base_data)
        return tool, download

    def test_recommended_install_adds_settings_and_plugins(self):
        tool, downloader = self.profile()
        pk.install(tool, self.root, downloader, recommended=True)
        dest = self.root / "demo"
        self.assertEqual((dest / "plugins/ComparePlus/ComparePlus.dll").read_bytes(), b"trusted")
        root = ET.parse(dest / "config.xml").getroot()
        tab = root.find("./GUIConfigs/GUIConfig[@name='TabSetting']")
        self.assertEqual((tab.get("size"), tab.get("replaceBySpace")), ("4", "yes"))
        self.assertEqual(pk.read_state(self.root)["demo"]["version"], "1")

    def test_without_optin_original_behavior_unchanged(self):
        tool, downloader = self.profile()
        pk.install(tool, self.root, downloader)
        self.assertFalse((self.root / "demo/plugins/ComparePlus").exists())
        self.assertEqual(ET.parse(self.root / "demo/config.xml").getroot().find(
            "./GUIConfigs/GUIConfig[@name='TabSetting']").get("size"), "8")

    def test_failed_plugin_hash_rolls_back_entire_install(self):
        tool, downloader = self.profile()
        tool["recommended"]["plugins"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(pk.PortakitError, "SHA256"):
            pk.install(tool, self.root, downloader, recommended=True)
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_missing_required_plugin_dll_rolls_back(self):
        tool, _ = self.profile()
        plugin_data = zip_bytes([("Other.dll", b"wrong")])
        tool["recommended"]["plugins"][0]["sha256"] = hashlib.sha256(plugin_data).hexdigest()
        base_data = zip_bytes([("demo.exe", b"app")])
        tool["sha256"] = hashlib.sha256(base_data).hexdigest()
        def download(url, path):
            path.write_bytes(plugin_data if "ComparePlus.zip" in url else base_data)
        with self.assertRaisesRegex(pk.PortakitError, "requiredFile"):
            pk.install(tool, self.root, download, recommended=True)
        self.assertFalse((self.root / "demo").exists())

    def test_profile_binaries_not_downloaded_when_optin_is_false(self):
        tool, downloader = self.profile()
        paths = []
        def track(url, path):
            paths.append(url)
            downloader(url, path)
        pk.install(tool, self.root, track)
        self.assertEqual(len(paths), 1)

    def test_winmerge_profile_creates_local_ini_without_registry_write(self):
        tool, downloader = self.package("1", members=[("WinMergeU.exe", b"exe")],
                                        recommended={"settings": "winmerge-dev", "plugins": []})
        pk.install(tool, self.root, downloader, recommended=True)
        ini = (self.root / "demo/WinMerge.ini").read_text(encoding="utf-8")
        self.assertIn("ViewLineNumbers = 1", ini)
        self.assertTrue((self.root / "demo/WinMergeU.exe").exists())

    def test_winmerge_office_plugins_are_available_and_auto_unpacking_enabled(self):
        names = ("CompareMSExcelFiles.sct", "CompareMSWordFiles.sct",
                 "CompareMSPowerPointFiles.sct", "CompareMSVisioFiles.sct")
        members = [("WinMergeU.exe", b"binary")] + [
            ("MergePlugins/" + name, b"<scriptlet/>") for name in names]
        tool, download = self.package(
            "1", members=members, recommended={"settings": "winmerge-dev",
                                              "plugins": [], "bundledPlugins": list(names)})
        pk.install(tool, self.root, download, recommended=True)
        for name in names:
            self.assertTrue((self.root / "demo/MergePlugins" / name).is_file(), name)
        import configparser
        ini = configparser.ConfigParser(interpolation=None)
        ini.optionxform = str
        ini.read(self.root / "demo/WinMerge.ini", encoding="utf-8")
        self.assertEqual(set(ini.sections()), {"WinMerge"})
        self.assertEqual(ini["WinMerge"]["Settings/ViewLineNumbers"], "1")
        self.assertEqual(ini["WinMerge"]["Settings/PluginsEnabled"], "1")
        self.assertEqual(ini["WinMerge"]["Settings/UnpackerMode"], "1")

    def test_winmerge_bundled_plugins_missing_aborts_without_state_or_partial_install(self):
        names = ["CompareMSExcelFiles.sct", "CompareMSWordFiles.sct"]
        tool, download = self.package(
            "1", members=[("WinMergeU.exe", b"exe"),
                          ("MergePlugins/CompareMSExcelFiles.sct", b"<scriptlet/>")],
            recommended={"settings": "winmerge-dev", "plugins": [], "bundledPlugins": names})
        with self.assertRaisesRegex(pk.PortakitError, "CompareMSWordFiles") as caught:
            pk.install(tool, self.root, download, recommended=True)
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_normal_winmerge_install_remains_unchanged_even_if_bundled_plugin_absent(self):
        tool, download = self.package(
            "1", members=[("WinMergeU.exe", b"exe")],
            recommended={"settings": "winmerge-dev", "plugins": [],
                         "bundledPlugins": ["CompareMSExcelFiles.sct"]})
        pk.install(tool, self.root, download)
        self.assertFalse((self.root / "demo/WinMerge.ini").exists())

    def test_winmerge_settings_do_not_overwrite_packaged_extra_ini_options(self):
        src = b"[WinMerge]\\nSettings/ExistingCustom=42\\nSettings/UnpackerMode=0\\n"
        src = src.replace(b"\\n", b"\n")
        tool, download = self.package(
            "1", members=[("WinMergeU.exe", b"exe"), ("WinMerge.ini", src)],
            recommended={"settings": "winmerge-dev", "plugins": []})
        pk.install(tool, self.root, download, recommended=True)
        import configparser
        ini = configparser.ConfigParser(interpolation=None)
        ini.optionxform = str
        ini.read(self.root / "demo/WinMerge.ini", encoding="utf-8")
        self.assertEqual(ini["WinMerge"]["Settings/ExistingCustom"], "42")
        self.assertEqual(ini["WinMerge"]["Settings/UnpackerMode"], "1")

    def test_missing_settings_node_is_created(self):
        tool, downloader = self.profile(with_plugin=False)
        base = zip_bytes([("demo.exe", b"app")])
        tool["sha256"] = hashlib.sha256(base).hexdigest()
        pk.install(tool, self.root, lambda url, path: path.write_bytes(base), recommended=True)
        root = ET.parse(self.root / "demo/config.xml").getroot()
        self.assertEqual(root.find("./GUIConfigs/GUIConfig[@name='TabSetting']").get("size"), "4")


class RecommendedCatalogTests(fixtures.Workspace):
    def test_recommended_catalog_rejects_invalid_schema(self):
        configurations = [
            {"settings": "unknown", "plugins": []},
            {"settings": "notepad++-dev", "plugins": "bad"},
            {"settings": "notepad++-dev", "plugins": [{"id": "p"}]},
            {"settings": "notepad++-dev", "plugins": [dict(
                id="p", version="1", url="http://wrong", sha256="a"*64,
                dest="plugins/P", requiredFile="P.dll")]},
            {"settings": "notepad++-dev", "plugins": [dict(
                id="p", version="1", url="https://example.com/latest/x.zip", sha256="a"*64,
                dest="plugins/P", requiredFile="P.dll")]},
            {"settings": "notepad++-dev", "plugins": [dict(
                id="p", version="1", url="https://example.com/v1/x.zip", sha256="a"*64,
                dest="../evil", requiredFile="P.dll")]}
        ]
        for config in configurations:
            with self.subTest(config=config), self.assertRaises(pk.PortakitError):
                self.write_catalog([entry(recommended=config)])
                pk.load_catalog(self.catalog)

    def test_winmerge_bundled_plugin_catalog_rejects_unsafe_names(self):
        for values in (
                "CompareMSExcelFiles.sct",
                ["../outside.sct"],
                ["nested/CompareMSExcelFiles.sct"],
                ["CON.sct"],
                ["Plugin.exe"],
                ["CompareMSExcelFiles.sct", "comparemsexcelfiles.SCT"],
                [12]):
            with self.subTest(values=values), self.assertRaisesRegex(
                    pk.PortakitError, "recommended.bundledPlugins"):
                self.write_catalog([entry(id="winmerge", dest="winmerge",
                                          recommended={"settings": "winmerge-dev",
                                                       "plugins": [],
                                                       "bundledPlugins": values})])
                pk.load_catalog(self.catalog)

    def test_office_bundled_plugins_are_winmerge_only(self):
        self.write_catalog([entry(id="notepad++", dest="notepad++",
                                  recommended={"settings": "notepad++-dev",
                                               "plugins": [],
                                               "bundledPlugins": ["CompareMSExcelFiles.sct"]})])
        with self.assertRaisesRegex(pk.PortakitError, "WinMerge-only"):
            pk.load_catalog(self.catalog)

    def test_recommended_requires_install_command(self):
        self.write_catalog([entry()])
        for cmd in (("list",), ("update", "demo"), ("remove", "demo")):
            with self.subTest(cmd=cmd):
                code, output = self.call(*cmd, "--recommended")
                self.assertEqual(code, 1)
                self.assertEqual(output["error"]["code"], "usage")


if __name__ == "__main__":
    unittest.main()
