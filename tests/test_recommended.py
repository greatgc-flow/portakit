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

    def test_recommended_requires_install_command(self):
        self.write_catalog([entry()])
        for cmd in (("list",), ("update", "demo"), ("remove", "demo")):
            with self.subTest(cmd=cmd):
                code, output = self.call(*cmd, "--recommended")
                self.assertEqual(code, 1)
                self.assertEqual(output["error"]["code"], "usage")


if __name__ == "__main__":
    unittest.main()
