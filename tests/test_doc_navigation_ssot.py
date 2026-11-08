"""Durable documentation navigation checks, never a dynamic GitHub status claim.

The live remote remains the authority; these tests only ensure old dated
checkpoints do not masquerade as the CURRENT handoff or a fresh run.

CURRENT is derived, not hardcoded: the START_NEW_CHAT_PORTAKIT_<YYYYMMDD>*.md
file with the greatest date wins, and two files sharing that date fail the
test so a suffix such as _R2 can never fork the pointer silently.
"""
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
HANDOFF_DIR = DOCS / "handoff"
NAME = re.compile(r"START_NEW_CHAT_PORTAKIT_(\d{8})\w*\.md")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{8}")
POINTERS = ("README.md", "docs/HANDOFF.md", "docs/BACKLOG.md", "docs/INDEX.md")


def current_handoff():
    dated = [(NAME.fullmatch(p.name).group(1), p)
             for p in HANDOFF_DIR.glob("START_NEW_CHAT_PORTAKIT_*.md") if NAME.fullmatch(p.name)]
    newest = max(date for date, _ in dated)
    return [path for date, path in dated if date == newest]


class DocumentationNavigationTests(unittest.TestCase):
    def setUp(self):
        winners = current_handoff()
        self.assertEqual(len(winners), 1,
                         "two handoffs share the newest date; rename one before merging")
        self.current = winners[0]
        self.readme = (REPO / "README.md").read_text(encoding="utf-8")

    def test_every_pointer_names_the_current_handoff(self):
        for relative in POINTERS:
            text = (REPO / relative).read_text(encoding="utf-8")
            with self.subTest(document=relative):
                self.assertIn("handoff/" + self.current.name, text)
        self.assertIn("## Current status and authoritative handoff", self.readme)
        handoff = (DOCS / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("historical, not the active handoff", handoff)
        backlog = (DOCS / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("Status authority:", backlog)
        self.assertIn("do not", backlog.lower())

    def test_readme_keeps_history_out_of_the_present(self):
        first_heading = next(line for line in self.readme.splitlines() if line.startswith("## "))
        self.assertIsNone(DATE.search(first_heading), "README top heading must carry no date")
        for line in self.readme.splitlines():
            others = [m.group(0) for m in NAME.finditer(line) if m.group(0) != self.current.name]
            if others and re.search(r"latest|current", line, re.I):
                self.fail(f"README labels another handoff latest/current: {line[:80]}")
        history = (DOCS / "HISTORY.md").read_text(encoding="utf-8")
        self.assertIn("## Historical checkpoint — PR #84 source CI", history)

    def test_new_chat_prompt_never_prescribes_stale_sha_or_test_count(self):
        document = self.current.read_text(encoding="utf-8")
        self.assertRegex(document, re.compile(r"^#+ .*verification rule", re.I | re.M))
        prompt = document.rsplit("\n## ", 1)[1]
        self.assertIn("actions/workflows/windows-tests.yml", prompt)
        # Commit and numeric CI evidence is intentionally retained in earlier
        # historical sections, but a copyable prompt must demand live lookup.
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", prompt))
        self.assertIsNone(re.search(r"\b\d+/\d+\s+PASS\b", prompt))


if __name__ == "__main__":
    unittest.main()
