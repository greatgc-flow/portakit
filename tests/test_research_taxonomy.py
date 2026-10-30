"""Offline evidence invariants for exclusive primary taxonomy and tool research."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TaxonomyEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        cls.groups = json.loads((ROOT / "toolsets.json").read_text(encoding="utf-8"))
        cls.research = json.loads((ROOT / "research" /
                                   "TOOLS_CANDIDATES_20261020.json").read_text(encoding="utf-8"))

    def test_every_canonical_pinned_id_has_exact_one_owner(self):
        pinned = {tool["id"] for tool in self.catalog["tools"]}
        primary = [tool for group in self.groups["categories"] for tool in group["tools"]]
        self.assertEqual(len(primary), len(set(primary)))
        self.assertEqual(set(primary), pinned)

    def test_all_107_research_unique_and_primary_complete(self):
        records = self.research["tools"]
        self.assertEqual(len(records), self.research["counts"]["total"])
        self.assertGreaterEqual(len(records), 100)
        self.assertEqual(len({r["id"] for r in records}), len(records))
        categories = {row["id"] for row in self.groups["categories"]}
        self.assertEqual({r["primary"] for r in records}, categories)
        self.assertTrue(all(r["primary"] in categories and r["source"].startswith("https://")
                            for r in records))
        count_by_status = {key: sum(r["admission"] == value for r in records)
                           for key, value in (("pinned", "PINNED_CATALOG"),
                                              ("builtIn", "OS_BUILTIN"),
                                              ("research", "RESEARCH_ONLY"))}
        self.assertEqual(count_by_status, {key: self.research["counts"][key] for key in count_by_status})

    def test_research_install_boundary_and_sha_asset_sizes(self):
        pinned = {tool["id"] for tool in self.catalog["tools"]}
        pinned_rows = {r["id"] for r in self.research["tools"]
                       if r["admission"] == "PINNED_CATALOG"}
        self.assertEqual(pinned, pinned_rows)
        for r in self.research["tools"]:
            if r["admission"] != "PINNED_CATALOG":
                self.assertNotIn(r["id"], pinned)
            if r["verifiedCompressedBytes"] is None:
                self.assertEqual(r["sizeMethod"], "NOT_MEASURED")
            else:
                self.assertIn(r["id"], pinned)
                self.assertIn(r["sizeMethod"], ("github_release_asset_metadata", "official_download_measured"))
                self.assertGreater(r["verifiedCompressedBytes"], 0)
                self.assertLess(r["verifiedCompressedBytes"], 10 * 1024 * 1024)
        self.assertEqual(sum(r["verifiedCompressedBytes"] or 0
                             for r in self.research["tools"]), 22239623)


if __name__ == "__main__":
    unittest.main()
