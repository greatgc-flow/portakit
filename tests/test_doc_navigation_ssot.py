"""Durable documentation navigation checks, never a dynamic GitHub status claim.

The live remote remains the authority; these tests only ensure old dated
checkpoints do not masquerade as the CURRENT handoff or a fresh run.
"""
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
CURRENT = "handoff/START_NEW_CHAT_PORTAKIT_20261101.md"


class DocumentationNavigationTests(unittest.TestCase):
    def test_current_pointer_is_unique_and_archive_is_labeled(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        handoff = (REPO / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
        backlog = (REPO / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("## Current status and authoritative handoff", readme)
        self.assertIn("docs/" + CURRENT, readme)
        self.assertIn("## Historical checkpoint — PR #84 source CI", readme)
        self.assertIn("historical, not the active handoff", handoff)
        self.assertIn(CURRENT, handoff)
        self.assertIn("Status authority:", backlog)
        self.assertIn("do not", backlog.lower())

    def test_new_chat_prompt_never_prescribes_stale_sha_or_test_count(self):
        document = (REPO / "docs" / CURRENT).read_text(encoding="utf-8")
        self.assertIn("## Active verification rule", document)
        self.assertIn("## 1. Archived PR #82-era remote state", document)
        self.assertIn("## 5. New-chat continuation prompt", document)
        prompt = document.split("## 5. New-chat continuation prompt", 1)[1]
        self.assertIn("actions/workflows/windows-tests.yml", prompt)
        self.assertIn("docs/BACKLOG.md", prompt)
        self.assertIn("Issues #25/#27/#36/#51/#87", prompt)
        # Commit and numeric CI evidence is intentionally retained in earlier
        # historical sections, but a copyable prompt must demand live lookup.
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", prompt))
        self.assertIsNone(re.search(r"\b\d+/\d+\s+PASS\b", prompt))


if __name__ == "__main__":
    unittest.main()
