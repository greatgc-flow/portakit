"""Applying an opt-in recommended profile to an already managed installation."""

import configparser
import hashlib
import os
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

import support as fx

pk = fx.pk
zip_bytes = fx.zip_bytes


class ConfigureRecommendedTests(fx.InstallWorkspace):
    def notepad(self):
        base = zip_bytes([("notepad++.exe", b"app"), ("config.xml",
            b'<NotepadPlus><GUIConfigs><GUIConfig name="TabSetting" size="8" replaceBySpace="no" />'
            b'<GUIConfig name="Other" value="keep"/></GUIConfigs></NotepadPlus>')])
        plugin_bytes = zip_bytes([("ComparePlus.dll", b"plugin")])
        plugin = dict(id="compareplus", version="3.0.0",
                      url="https://github.com/owner/plugins/releases/download/v3/plugin.zip",
                      sha256=hashlib.sha256(plugin_bytes).hexdigest(),
                      dest="plugins/ComparePlus", requiredFile="ComparePlus.dll")
        tool = fx.entry(id="notepad++", dest="notepad++",
                        sha256=hashlib.sha256(base).hexdigest(),
                        recommended=dict(settings="notepad++-dev", plugins=[plugin]))
        def download(url, dst):
            Path(dst).write_bytes(plugin_bytes if url == plugin["url"] else base)
        self.write_catalog([tool])
        return tool, download

    def winmerge(self):
        scripts = ["CompareMSExcelFiles.sct", "CompareMSWordFiles.sct"]
        payload = zip_bytes([("WinMergeU.exe", b"app")] +
                            [("MergePlugins/" + f, b"script") for f in scripts])
        tool = fx.entry(id="winmerge", dest="winmerge",
                        sha256=hashlib.sha256(payload).hexdigest(),
                        recommended=dict(settings="winmerge-dev",
                                         plugins=[], bundledPlugins=scripts))
        def download(url, dst):
            Path(dst).write_bytes(payload)
        self.write_catalog([tool])
        return tool, download

    def test_configure_existing_npp_preserves_other_config_and_user_files(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        dest = self.root / "notepad++"
        (dest / "custom.txt").write_text("irreplaceable", encoding="utf-8")
        saved = self.state_bytes()
        result = pk.configure(tool, self.root, download)
        self.assertEqual(set(result), {"id", "version", "dest", "changed"})
        self.assertTrue(result["changed"])
        config = ET.parse(dest / "config.xml").getroot()
        tab = config.find("./GUIConfigs/GUIConfig[@name='TabSetting']")
        self.assertEqual((tab.get("size"), tab.get("replaceBySpace")), ("4", "yes"))
        self.assertEqual(config.find("./GUIConfigs/GUIConfig[@name='Other']").get("value"), "keep")
        self.assertEqual((dest / "plugins/ComparePlus/ComparePlus.dll").read_bytes(), b"plugin")
        self.assertEqual((dest / "custom.txt").read_text(encoding="utf-8"), "irreplaceable")
        self.assertEqual(saved, self.state_bytes())
        self.assertFalse((self.root / "notepad++.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_configure_is_idempotent_and_skips_existing_plugin_download(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        count = []
        def capture(url, dst):
            count.append(url)
            download(url, dst)
        self.assertTrue(pk.configure(tool, self.root, capture)["changed"])
        before = (self.root / "notepad++/plugins/ComparePlus/ComparePlus.dll").read_bytes()
        count.clear()
        self.assertFalse(pk.configure(tool, self.root, capture)["changed"])
        self.assertEqual(count, [])
        self.assertEqual((self.root / "notepad++/plugins/ComparePlus/ComparePlus.dll").read_bytes(), before)

    def test_configure_winmerge_preserves_unrelated_settings(self):
        tool, download = self.winmerge()
        pk.install(tool, self.root, download)
        path = self.root / "winmerge/WinMerge.ini"
        path.write_text("[WinMerge]\nSettings/Custom=8\nSettings/UnpackerMode=0\n", encoding="utf-8")
        response = pk.configure(tool, self.root, download)
        self.assertTrue(response["changed"])
        conf = configparser.ConfigParser(interpolation=None)
        conf.optionxform = str
        conf.read(path, encoding="utf-8")
        self.assertEqual(conf["WinMerge"]["Settings/Custom"], "8")
        self.assertEqual(conf["WinMerge"]["Settings/PluginsEnabled"], "1")
        self.assertEqual(conf["WinMerge"]["Settings/UnpackerMode"], "1")
        self.assertFalse(pk.configure(tool, self.root, download)["changed"])

    def test_missing_bundled_script_fails_and_leaves_original(self):
        tool, download = self.winmerge()
        pk.install(tool, self.root, download)
        (self.root / "winmerge/MergePlugins/CompareMSExcelFiles.sct").unlink()
        old = self.state_bytes()
        with self.assertRaisesRegex(pk.PortakitError, "CompareMSExcelFiles") as error:
            pk.configure(tool, self.root, download)
        self.assertEqual(error.exception.code, "archive")
        self.assertEqual(self.state_bytes(), old)
        self.assertFalse((self.root / "winmerge.old").exists())

    def test_wrong_plugin_digest_leaves_previous_install_untouched(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        marker = self.root / "notepad++/marker.txt"
        marker.write_text("original")
        state = self.state_bytes()
        tool["recommended"]["plugins"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(pk.PortakitError, "SHA256"):
            pk.configure(tool, self.root, download)
        self.assertEqual(self.state_bytes(), state)
        self.assertEqual(marker.read_text(), "original")
        self.assertFalse((self.root / "notepad++.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_missing_app_and_stale_pin_do_not_modify_state(self):
        tool, download = self.notepad()
        with self.assertRaisesRegex(pk.PortakitError, "not installed"):
            pk.configure(tool, self.root, download)
        pk.install(tool, self.root, download)
        state = self.state_bytes()
        mismatched = dict(tool, sha256="a" * 64)
        with self.assertRaisesRegex(pk.PortakitError, "update"):
            pk.configure(mismatched, self.root, download)
        self.assertEqual(self.state_bytes(), state)

    def test_existing_unmanaged_plugin_destination_is_not_overwritten(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        target = self.root / "notepad++/plugins/ComparePlus"
        target.mkdir(parents=True)
        (target / "user.ini").write_text("private")
        with self.assertRaisesRegex(pk.PortakitError, "requiredFile"):
            pk.configure(tool, self.root, download)
        self.assertEqual((target / "user.ini").read_text(), "private")
        self.assertFalse((target / "ComparePlus.dll").exists())

    def test_symlink_in_existing_install_aborts_before_copy(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("outside")
        self.junction(self.root / "notepad++/redirect", outside)
        with self.assertRaisesRegex(pk.PortakitError, "Reparse"):
            pk.configure(tool, self.root, download)
        self.assertEqual((outside / "keep.txt").read_text(), "outside")
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])

    def test_state_write_failure_rolls_back_reconfiguration(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        state = self.state_bytes()
        original = (self.root / "notepad++/config.xml").read_bytes()
        with mock.patch.object(pk, "write_state", side_effect=PermissionError("simulated")):
            with self.assertRaises(pk.PortakitError):
                pk.configure(tool, self.root, download)
        self.assertEqual(self.state_bytes(), state)
        self.assertEqual((self.root / "notepad++/config.xml").read_bytes(), original)
        self.assertFalse((self.root / "notepad++.old").exists())

    def test_cli_configure_and_reject_recommended_flag(self):
        tool, download = self.notepad()
        pk.install(tool, self.root, download)
        code, result = self.call("configure", "notepad++", downloader=download)
        self.assertEqual(code, 0)
        self.assertEqual(result["command"], "configure")
        self.assertTrue(result["data"]["changed"])
        code, result = self.call("configure", "notepad++", "--recommended")
        self.assertEqual(code, 1)
        self.assertEqual(result["error"]["code"], "usage")


if __name__ == "__main__":
    unittest.main()
