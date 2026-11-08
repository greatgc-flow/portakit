"""Horizontal documentation closure: one MECE index and no dangling links.

docs/INDEX.md is the single classification of every file under docs/ and
research/. Each file must be matched by exactly one index entry: either an
explicit file link or a directory row (a link target ending in "/"). An
explicit entry wins over its directory row, so the current handoff can be
named directly while the rest of docs/handoff/ is covered by one row.

Every relative Markdown link in the repository must resolve to an existing
file so that moving history out of README cannot silently break navigation.
"""
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
INDEX = DOCS / "INDEX.md"
LINK = re.compile(r"\]\(([^)\s]+)\)")
SKIP_SCHEMES = ("http://", "https://", "mailto:")


def markdown_files():
    roots = [REPO / "README.md"]
    roots += sorted(DOCS.rglob("*.md"))
    roots += sorted((REPO / "research").glob("*.md"))
    return roots


def relative_links(path):
    text = path.read_text(encoding="utf-8")
    for target in LINK.findall(text):
        if target.startswith(SKIP_SCHEMES) or target.startswith("#"):
            continue
        yield target.split("#", 1)[0]


class RelativeLinkTests(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self):
        for path in markdown_files():
            for target in relative_links(path):
                with self.subTest(document=path.relative_to(REPO).as_posix(), link=target):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(resolved.exists(), f"dangling link {target}")


class DocumentationIndexTests(unittest.TestCase):
    def setUp(self):
        self.index_text = INDEX.read_text(encoding="utf-8")
        self.entries = [target for target in relative_links(INDEX)]
        self.files = sorted(p for p in DOCS.rglob("*") if p.is_file())
        self.files += sorted(p for p in (REPO / "research").glob("*") if p.is_file())

    def entry_key(self, path):
        return Path(path.relative_to(DOCS)).as_posix() if DOCS in path.parents \
            else "../" + path.relative_to(REPO).as_posix()

    def test_every_doc_and_research_file_matched_exactly_once(self):
        explicit = [e for e in self.entries if not e.endswith("/")]
        directories = [e for e in self.entries if e.endswith("/")]
        for path in self.files:
            key = self.entry_key(path)
            with self.subTest(file=key):
                direct = explicit.count(key)
                covering = [d for d in directories if key.startswith(d)]
                self.assertLessEqual(direct, 1, "listed more than once")
                if direct == 0:
                    self.assertEqual(len(covering), 1, "not covered by exactly one row")

    def test_index_entries_exist_and_are_table_rows(self):
        for entry in self.entries:
            with self.subTest(entry=entry):
                self.assertTrue((DOCS / entry).resolve().exists(), "index names a missing path")
        rows = [line for line in self.index_text.splitlines() if "](" in line]
        self.assertTrue(rows and all(line.startswith("|") for line in rows),
                        "every INDEX entry must live in a table row")

    def test_readme_points_to_index(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/INDEX.md", readme)


if __name__ == "__main__":
    unittest.main()
