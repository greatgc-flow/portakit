"""Contract tests for supplemental qsv/xan source metadata (not admission)."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CSVAlternativesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT / "research" /
                                 "CSV_ALTERNATIVES_20261031.json").read_text("utf-8"))
        cls.catalog = json.loads((ROOT / "catalog.json").read_text("utf-8"))
        cls.known = {i["id"] for i in cls.catalog["tools"]}

    def test_research_comparison_is_not_an_install_catalog(self):
        self.assertEqual(self.source["schemaVersion"], 1)
        self.assertEqual(self.source["asOf"], "2026-10-31")
        self.assertEqual(self.source["incumbent"]["id"], "miller")
        self.assertTrue(self.source["incumbent"]["alreadyPinned"])
        self.assertIn("miller", self.known)
        self.assertEqual({x["id"] for x in self.source["alternatives"]},
                         {"qsv", "xan"})
        self.assertFalse({"qsv", "xan"} & self.known)
        self.assertIn("Supplemental", self.source["authority"])

    def test_published_source_urls_and_digest_shapes(self):
        for row in self.source["alternatives"]:
            with self.subTest(name=row["id"]):
                self.assertTrue(row["sourceRepo"].startswith("https://github.com/"))
                self.assertTrue(row["releaseURL"].startswith(row["sourceRepo"] + "/releases/tag/"))
                self.assertTrue(row["licenseSource"].startswith(row["sourceRepo"] + "/"))
                self.assertFalse(row["archived"])
                self.assertTrue(row["missing"])
                for asset in row["windowsX64"]:
                    self.assertTrue(asset["asset"].endswith(".zip"))
                    self.assertIn("windows", asset["asset"])
                    self.assertIs(type(asset["size"]), int)
                    self.assertGreater(asset["size"], 0)
                    self.assertIsNotNone(re.fullmatch("[0-9a-f]{64}", asset["sha256"]))

    def test_qsv_current_x64_is_over_global_archive_cap(self):
        import importlib.util
        # No vendor binary is loaded by this assertion.
        qsv = next(x for x in self.source["alternatives"] if x["id"] == "qsv")
        expected = [402543109, 129287020]
        self.assertEqual([a["size"] for a in qsv["windowsX64"]], expected)
        # Contract also guards against quietly broadening existing core limit.
        import ast
        tree = ast.parse((ROOT / "portakit.py").read_text(encoding="utf-8"))
        compressed_cap = next(
            x.value.value for x in tree.body
            if isinstance(x, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "MAX_DOWNLOAD_BYTES"
                    for t in x.targets)
            and isinstance(x.value, ast.BinOp)
        )  # first 100 in "100 * 1024 * 1024"
        self.assertEqual(compressed_cap, 100)
        self.assertTrue(all(a["size"] > 100 * 1024 * 1024
                            for a in qsv["windowsX64"]))

    def test_xan_compact_zip_not_automatically_admitted(self):
        xan = next(x for x in self.source["alternatives"] if x["id"] == "xan")
        self.assertEqual(xan["release"], "0.61.0")
        self.assertEqual(xan["windowsX64"][0]["size"], 6473075)
        self.assertEqual(xan["windowsX64"][0]["sha256"],
                         "5f7bef4dcffb3a3a937ac180ed76cdf966cb13647251beffddb84d01c1ae54")
        self.assertLess(xan["windowsX64"][0]["size"], 10 * 1024 * 1024)
        self.assertIn("corporateLicense", xan["missing"])
        self.assertIn("redistribution", xan["missing"])


if __name__ == "__main__":
    unittest.main()
