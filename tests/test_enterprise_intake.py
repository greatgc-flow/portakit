"""Cross-check the optional industrial/enterprise research intake against SSOT.

No network, GUI, driver, service, installer or vendor executable is invoked.
New report-only candidates must NEVER be treated as approved or installable.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EnterpriseIntakeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intake = json.loads((ROOT / "research" /
            "INTAKE_ENTERPRISE_PORTABLE_20261025.json").read_text(encoding="utf-8"))
        cls.catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        cls.research = json.loads((ROOT / "research" /
            "TOOLS_CANDIDATES_20261020.json").read_text(encoding="utf-8"))
        cls.taxonomy = json.loads((ROOT / "toolsets.json").read_text(encoding="utf-8"))

    def test_provenance_and_53_row_mece_structure(self):
        source = self.intake["source"]
        self.assertEqual(source["reportedPages"], 31)
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        records = self.intake["records"]
        self.assertEqual(len(records), 53)
        self.assertEqual(source["matrixSoftwareRows"], len(records))
        self.assertEqual([r["matrixRow"] for r in records], list(range(1, 54)))
        self.assertEqual(len(set(r["id"] for r in records)), len(records))
        categories = {c["id"] for c in self.taxonomy["categories"]}
        self.assertTrue(all(r["primary"] in categories for r in records))
        self.assertTrue(all(isinstance(r["gates"], list) for r in records))

    def test_cross_reference_statuses_are_exact(self):
        pinned = {t["id"] for t in self.catalog["tools"]}
        previous = {t["id"]: t for t in self.research["tools"]}
        counts = {"ALREADY_PINNED": 0, "EXISTING_RESEARCH_ONLY": 0,
                  "NEW_RESEARCH_ONLY": 0}
        for item in self.intake["records"]:
            name, state = item["id"], item["stage"]
            self.assertIn(state, counts)
            counts[state] += 1
            if name in pinned:
                self.assertEqual(state, "ALREADY_PINNED")
                self.assertEqual(item["existingAdmission"], "PINNED_CATALOG")
            elif name in previous:
                self.assertEqual(state, "EXISTING_RESEARCH_ONLY")
                self.assertEqual(item["existingAdmission"], "RESEARCH_ONLY")
            else:
                self.assertEqual(state, "NEW_RESEARCH_ONLY")
                self.assertIsNone(item["existingAdmission"])
            if name in previous:
                self.assertEqual(item["primary"], previous[name]["primary"])
        self.assertEqual(counts, {"ALREADY_PINNED": 5,
                                   "EXISTING_RESEARCH_ONLY": 5,
                                   "NEW_RESEARCH_ONLY": 43})
        self.assertEqual(self.intake["counts"]["potentialUnionDistinct"], len(previous) + 43)
        self.assertEqual(self.intake["counts"]["existingResearchLedger"], len(previous))
        self.assertEqual(self.intake["counts"]["alreadyPinned"], counts["ALREADY_PINNED"])
        self.assertEqual(self.intake["counts"]["existingResearchOnly"], counts["EXISTING_RESEARCH_ONLY"])
        self.assertEqual(self.intake["counts"]["newResearchOnly"], counts["NEW_RESEARCH_ONLY"])

    def test_no_unapproved_executable_or_implicit_install_definition(self):
        self.assertEqual(self.intake["source"]["matrixSoftwareRows"], 53)
        self.assertEqual(len(self.intake["relatedEditorPlugins"]), 6)
        self.assertFalse(any("url" in x or "sha256" in x or "artifact" in x
                             for x in self.intake["records"]))
        high_risk = {
            "pymcprotocol": "CLIENT_NOT_SERVER",
            "com0com-hub4com": "KERNEL_DRIVER_INSTALL",
            "nssm": "SERVICE_CREATE_START",
            "everything": "FIRST_RUN_MAY_REQUEST_SERVICE_OR_UAC",
            "secs4net": "DOTNET_RUNTIME_COMPATIBILITY",
            "sysinternals-suite": "REDISTRIBUTION_REVIEW",
        }
        indexed = {x["id"]: x for x in self.intake["records"]}
        for ident, required in high_risk.items():
            self.assertIn(required, indexed[ident]["gates"])
        for plugin in self.intake["relatedEditorPlugins"]:
            self.assertTrue(plugin["stage"].endswith("PLUGIN_AS_OPTION")
                            or plugin["stage"] == "REVIEW_ONLY_PLUGIN")

if __name__ == "__main__":
    unittest.main()
