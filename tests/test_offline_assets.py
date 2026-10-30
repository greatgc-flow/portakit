"""Offline manifest and SHA validation checks without network/vendor binaries."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portakit_assets",
                                              ROOT / "scripts" / "offline_assets.py")
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class OfflineAssetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.tmp) / "MyKit.json"
        self.out = Path(self.tmp) / "MyKit.assets.json"
        self.log = Path(self.tmp) / "verify.log"
        self.pins, cats, profiles, known = assets.kit.inventory()
        self.saved = assets.kit.make_kit("personal", ["jq", "duckdb-cli", "cmd"],
                                         self.pins, known)

    def manifest(self):
        return assets.make_manifest(self.saved, self.pins)

    def test_metadata_only_and_research_never_in_archive_rows(self):
        m = self.manifest()
        self.assertEqual(m["schemaVersion"], 1)
        self.assertEqual(m["policy"], "METADATA_ONLY_NOT_LICENSED_FOR_REDISTRIBUTION")
        self.assertEqual(m["approvedCatalogPins"], 1)
        self.assertEqual([x["id"] for x in m["assets"]], ["jq"])
        self.assertEqual(m["researchOnlyNotPackaged"], ["duckdb-cli"])
        self.assertEqual(m["osBuiltinsNotPackaged"], ["cmd"])
        self.assertEqual(m["assets"][0]["sha256"], self.pins["jq"]["sha256"])

    def test_normal_url_parsing_and_unsafe_rejected(self):
        self.assertEqual(assets.original_filename(
            "https://vendor.example/download/final%20kit.zip"), "final kit.zip")
        for url in ("http://example.com/a.zip", "https://example.com/",
                    "https://example.com/%2e%2e", "https://example.com/%2funsafe.zip",
                    "https://example.com/a%5cb.zip"):
            with self.subTest(url=url):
                with self.assertRaises(assets.AssetError):
                    assets.original_filename(url)

    def test_filename_collision_with_distinct_hash_refused(self):
        selected = assets.kit.make_kit("x", ["jq", "ripgrep"], self.pins,
                                       assets.kit.inventory()[3])
        pins = {k: dict(v) for k, v in self.pins.items()}
        pins["ripgrep"]["url"] = pins["jq"]["url"]
        with self.assertRaisesRegex(assets.AssetError, "collision"):
            assets.make_manifest(selected, pins)

    def test_export_new_manifest_and_mirrored_console(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            assets.create_manifest_file(self.manifest(), self.out)
        self.assertEqual(output.getvalue(),
                         self.out.with_suffix(".log").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(self.out.read_text("utf-8")), self.manifest())
        with self.assertRaisesRegex(assets.AssetError, "exists"):
            assets.create_manifest_file(self.manifest(), self.out)

    def test_verify_uses_existing_SHA_engine_without_invoking_install(self):
        data = self.manifest()
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               return_value={"jq": Path(self.tmp) / "jq.exe"}) as verified:
            with mock.patch.object(assets.kit.sets, "apply",
                                   side_effect=AssertionError("installer invoked")):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertTrue(assets.verify_archives(data, self.tmp, self.log))
        self.assertEqual(verified.call_args.args[0], [{"id": "jq", "status": "install"}])
        self.assertEqual(output.getvalue(), self.log.read_text(encoding="utf-8"))
        self.assertIn("SHA256 PASS: jq", output.getvalue())

    def test_missing_archive_is_failure_evidence_not_partial_install(self):
        with mock.patch.object(assets.kit.sets, "verify_offline_assets",
                               side_effect=assets.kit.sets.ToolsetError("Missing source")):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertFalse(assets.verify_archives(self.manifest(),
                                                       self.tmp, self.log))
        self.assertEqual(stdout.getvalue(), self.log.read_text("utf-8"))
        self.assertIn("RESULT: FAILED", stdout.getvalue())
        self.assertIn("NO PARTIAL DEPLOYMENT", stdout.getvalue())

    def test_empty_os_and_pending_kit_uses_no_source_verifier(self):
        m = assets.make_manifest(
            assets.kit.make_kit("nothing", ["cmd", "duckdb-cli"], self.pins,
                                assets.kit.inventory()[3]), self.pins)
        with mock.patch.object(assets.kit.sets, "verify_offline_assets") as verifier:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertTrue(assets.verify_archives(m, self.tmp, self.log))
            verifier.assert_not_called()
        self.assertIn("NO_OP", out.getvalue())

    def test_list_cli_read_only_and_export_requires_new_path(self):
        with contextlib.redirect_stdout(io.StringIO()):
            assets.kit.save_new(self.saved, self.path)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(assets.run(["list", "--kit", str(self.path)]), 0)
        self.assertIn("OFFICIAL URL", output.getvalue())
        self.assertFalse(self.out.exists())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(assets.run(["export", "--kit", str(self.path),
                                         "--out", str(self.out)]), 0)
        self.assertTrue(self.out.is_file())
        self.assertEqual(output.getvalue(),
                         self.out.with_suffix(".log").read_text("utf-8"))

    def test_drifted_pin_rejected_before_source_handling(self):
        with contextlib.redirect_stdout(io.StringIO()):
            assets.kit.save_new(self.saved, self.path)
        data = json.loads(self.path.read_text("utf-8"))
        data["lockedPins"]["jq"]["sha256"] = "0" * 64
        self.path.write_text(json.dumps(data), "utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(assets.run(["list", "--kit", str(self.path)]), 1)
        self.assertIn("PIN_CHANGED", err.getvalue())


if __name__ == "__main__":
    unittest.main()
