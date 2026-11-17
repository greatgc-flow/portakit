"""Aegis's actual ZIP through the real offline installer; runtime never runs.

Temporary install roots only. These checks cover packaging/installer composition,
not Windows desktop behavior or actual PowerShell 2 compatibility.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest import mock
import zipfile

import support as fixtures


CORE = fixtures.pk
REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "assets" / "aegis" / "Aegis-4.1.0-ps2.zip"
SPEC = importlib.util.spec_from_file_location(
    "my_toolkit_aegis_test", REPO / "scripts" / "my_toolkit.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


class AegisIntegrationTests(fixtures.InstallWorkspace):
    @classmethod
    def setUpClass(cls):
        cls.tool = CORE.load_catalog(REPO / "catalog.json")["aegis"]
        cls.archive_bytes = ARCHIVE.read_bytes()
        with zipfile.ZipFile(ARCHIVE) as archive:
            prefix = "Aegis-" + cls.tool["version"] + "/"
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not names or any(not name.startswith(prefix) for name in names):
                raise AssertionError("Aegis ZIP must have its versioned top-level folder")
            # The real installer flattens a single archive root during extract.
            cls.members = {name[len(prefix):]: archive.read(name) for name in names}

    def setUp(self):
        super().setUp()
        # User-owned settings already exist before installation; the installer
        # must neither create a second copy nor overwrite/delete these bytes.
        self.user_data = self.root / "aegis-data"
        (self.user_data / "profiles").mkdir(parents=True)
        (self.user_data / "Aegis.Processes.csv").write_bytes(
            b"user-specific CSV: keep unchanged\r\n")
        (self.user_data / "profiles" / "home.xml").write_bytes(
            b"<user-profile>keep unchanged</user-profile>\r\n")
        self.user_before = snapshot(self.user_data)
        self.enterContext(mock.patch.object(
            CORE.urllib.request, "urlopen",
            side_effect=AssertionError("Network access is forbidden in this test")))
        self.enterContext(mock.patch.object(
            CORE.subprocess, "run",
            side_effect=AssertionError("Runtime execution is forbidden in this test")))
        self.enterContext(mock.patch.object(
            CORE.subprocess, "Popen",
            side_effect=AssertionError("Runtime execution is forbidden in this test")))

    def offline(self, archive=ARCHIVE):
        return CORE.offline_downloader(archive)

    def assert_user_data_unchanged(self):
        self.assertTrue((self.user_data / "profiles").is_dir())
        self.assertEqual(snapshot(self.user_data), self.user_before)

    def assert_clean_install(self):
        self.assertEqual(snapshot(self.root / "aegis"), self.members)
        self.assertFalse((self.root / "aegis.old").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])
        self.assert_user_data_unchanged()

    def install(self):
        result = CORE.install(self.tool, self.root, self.offline())
        self.assertTrue(result["changed"])
        self.assert_clean_install()
        return result

    def mark_previous_release(self):
        """Use a synthetic old receipt to exercise a real deploy of this ZIP."""
        state = CORE.read_state(self.root)
        state["aegis"]["version"] = "4.0.3-ps2-test-fixture"
        CORE.write_state(self.root, state)
        (self.root / "aegis" / "README_ko.txt").write_bytes(b"previous release fixture")

    def tampered_archive(self):
        path = self.base / ARCHIVE.name
        # Keep this a readable ZIP so SHA rejection is the active boundary.
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, payload in self.members.items():
                if name == "Aegis.ps1":
                    payload += b"\r\n# modified after pinning\r\n"
                archive.writestr(name, payload)
        return path

    def test_catalog_pin_names_the_exact_immutable_bundled_release(self):
        self.assertEqual(self.tool["version"], "4.1.0-ps2")
        self.assertEqual((self.tool["dest"], self.tool["artifact"]), ("aegis", "zip"))
        self.assertRegex(
            self.tool["url"],
            r"\Ahttps://raw\.githubusercontent\.com/greatgc-flow/portakit/"
            r"[0-9a-f]{40}/assets/aegis/Aegis-4\.1\.0-ps2\.zip\Z")
        self.assertEqual(self.tool["sha256"],
                         hashlib.sha256(self.archive_bytes).hexdigest())
        self.assertEqual(self.tool.get("preserveOnUpdate", []), [])
        self.assertEqual(self.tool.get("preserveMissingOnUpdate", []), [])

    def test_offline_install_changed_update_and_remove_preserve_sibling_data(self):
        self.install()
        state = CORE.read_state(self.root)["aegis"]
        self.assertEqual(state, {key: self.tool[key]
                                 for key in ("version", "sha256", "dest")})

        # Exercise actual replacement, not only the identical-pin no-op path.
        self.mark_previous_release()
        self.assertTrue(CORE.update(self.tool, self.root, self.offline())["changed"])
        self.assert_clean_install()
        self.assertEqual(CORE.read_state(self.root)["aegis"]["version"],
                         self.tool["version"])

        CORE.remove("aegis", self.root)
        self.assertFalse((self.root / "aegis").exists())
        self.assertFalse((self.root / "aegis.old").exists())
        self.assertEqual(CORE.read_state(self.root), {})
        self.assert_user_data_unchanged()
        self.assertEqual(ARCHIVE.read_bytes(), self.archive_bytes)

    def test_identical_pin_update_skips_source_and_preserves_installed_bytes(self):
        self.install()
        before = snapshot(self.root)
        fetch = mock.Mock(side_effect=AssertionError("Identical update must not fetch"))
        self.assertFalse(CORE.update(self.tool, self.root, fetch)["changed"])
        fetch.assert_not_called()
        self.assertEqual(snapshot(self.root), before)

    def test_tampered_zip_rejected_before_first_install(self):
        with self.assertRaisesRegex(CORE.PortakitError, "SHA256 mismatch"):
            CORE.install(self.tool, self.root, self.offline(self.tampered_archive()))
        self.assertFalse((self.root / "aegis").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])
        self.assert_user_data_unchanged()

    def test_tampered_update_keeps_prior_program_state_and_user_data(self):
        self.install()
        self.mark_previous_release()
        before = snapshot(self.root)
        with self.assertRaisesRegex(CORE.PortakitError, "SHA256 mismatch"):
            CORE.update(self.tool, self.root, self.offline(self.tampered_archive()))
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "aegis.old").exists())

    def test_wrong_catalog_digest_cannot_install_the_actual_zip(self):
        incorrect = dict(self.tool)
        incorrect["sha256"] = ("0" if self.tool["sha256"][0] != "0" else "1") + \
            self.tool["sha256"][1:]
        with self.assertRaisesRegex(CORE.PortakitError, "SHA256 mismatch"):
            CORE.install(incorrect, self.root, self.offline())
        self.assertFalse((self.root / "aegis").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assert_user_data_unchanged()

    def test_saved_personal_selection_rejects_changed_aegis_source_or_digest(self):
        pins, _, _, known = kit.inventory()
        saved = self.base / "aegis-personal-kit.json"
        saved.write_text(json.dumps(kit.make_kit("aegis-only", ["aegis"], pins, known)),
                         encoding="utf-8")
        self.assertEqual(kit.read_kit(saved, pins, known)["tools"], ["aegis"])
        for field, value in (("url", self.tool["url"] + "?different-source=1"),
                             ("sha256", "0" * 64)):
            with self.subTest(field=field):
                changed = dict(pins, aegis=dict(pins["aegis"], **{field: value}))
                with self.assertRaisesRegex(kit.KitError, "PIN_CHANGED for aegis"):
                    kit.read_kit(saved, changed, known)
        self.assertFalse((self.root / "aegis").exists())
        self.assert_user_data_unchanged()
