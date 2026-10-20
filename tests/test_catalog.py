"""Tests for catalog behavior."""

import json
from pathlib import Path
import unittest

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry


class CatalogTests(fixtures.Workspace):
    def load(self, tools):
        self.write_catalog(tools)
        return pk.load_catalog(self.catalog)

    def test_shipped_catalog_is_plain_url_sha_entries(self):
        path = Path(pk.__file__).with_name("catalog.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        catalog = pk.load_catalog(path)
        self.assertEqual(set(catalog), {"notepad++", "winmerge", "jq",
                                        "ripgrep", "fd", "fzf", "bat", "sd",
                                        "yq", "delta", "hyperfine"})
        for tool in raw["tools"]:
            with self.subTest(id=tool["id"]):
                for removed in ("kind", "repo", "tag", "asset", "github_url", "defaultConfig"):
                    self.assertNotIn(removed, tool)
                self.assertRegex(tool["sha256"], r"\A[a-f0-9]{64}\Z")
                self.assertEqual(pk.urllib.parse.urlsplit(tool["url"]).scheme, "https")
                self.assertTrue(pk.urllib.parse.urlsplit(tool["url"]).hostname)

    def test_valid_catalog(self):
        self.assertEqual(self.load([entry()])["demo"]["version"], "1")

    def test_mutable_latest_urls_are_catalog_errors(self):
        for path in ("latest/demo.zip", "releases/latest/download/demo.zip",
                     "releases/LATEST/demo.zip", "%6catest/demo.zip"):
            with self.subTest(path=path):
                self.write_catalog([entry(url="https://example.com/" + path)])
                code, result = self.call("list")
                self.assertEqual(code, 2)
                self.assertEqual(result["error"]["code"], "catalog")
                self.assertIn("url", result["error"]["message"])

    def test_latest_substring_in_pinned_filename_is_allowed(self):
        tool = entry(url="https://example.com/v1/latest-demo.zip")
        self.assertEqual(self.load([tool])["demo"]["url"], tool["url"])

    def test_bad_fields_are_named(self):
        for field, value in [("id", ""), ("id", "."), ("version", 1), ("version", ""),
                             ("url", "https://"), ("url", "file:///tmp/x"),
                             ("url", "http://example.com/demo.zip"),
                             ("url", "https://example.com/a b.zip"),
                             ("sha256", "bad"), ("artifact", "tar"),
                             ("preserveOnUpdate", ["../outside"]), ("preserveOnUpdate", "x")]:
            with self.subTest(field=field, value=value), self.assertRaisesRegex(pk.PortakitError, field):
                self.load([entry(**{field: value})])

    def test_optional_missing_on_update_paths_are_validated(self):
        self.assertEqual(self.load([entry(preserveMissingOnUpdate=["plugins", "MergePlugins"])])["demo"]["preserveMissingOnUpdate"],
                         ["plugins", "MergePlugins"])
        for value in (["../escape"], ["C:\\absolute"], ["plugins/../outside"],
                      ["plugins", 1], "plugins"):
            with self.subTest(value=value), self.assertRaisesRegex(
                    pk.PortakitError, "preserveMissingOnUpdate"):
                self.load([entry(preserveMissingOnUpdate=value)])

    def test_each_required_field_is_named_when_missing(self):
        for field in ("id", "version", "url", "sha256", "artifact", "dest"):
            tool = entry()
            del tool[field]
            with self.subTest(field=field), self.assertRaisesRegex(pk.PortakitError, field):
                self.load([tool])

    def test_duplicate_id(self):
        with self.assertRaisesRegex(pk.PortakitError, "id"):
            self.load([entry(), entry()])

    def test_removed_and_unknown_fields_are_ignored(self):
        tool = self.load([entry(kind="github", repo="x/y", tag="t", asset="a.zip",
                                defaultConfig={"a.ini": "x"}, whatever=1)])["demo"]
        self.assertEqual(tool["id"], "demo")

    def test_todo_hash_is_rejected_at_load(self):
        for value in ("TODO", "todo"):
            with self.subTest(value=value), self.assertRaisesRegex(pk.PortakitError, "sha256"):
                self.load([entry(sha256=value)])

    def test_sha256_is_normalized_to_lowercase(self):
        self.assertEqual(self.load([entry(sha256="A" * 64)])["demo"]["sha256"], "a" * 64)

    def test_dest_must_be_one_safe_unreserved_segment(self):
        for dest in ["../outside", "/absolute", "C:\\escape", "..\\outside", ".",
                     ".portakit-cache", ".portakit-state.json", ".portakit-x", "x.old",
                     "a/b", "a\\b", "con", "NUL.txt", "bad:name", "trail.", "trail "]:
            with self.subTest(dest=dest), self.assertRaisesRegex(pk.PortakitError, "dest"):
                self.load([entry(dest=dest)])

    def test_id_exe_must_pass_path_rule(self):
        for identifier in ("con", "nul", "aux", "com1", "lpt9"):
            with self.subTest(id=identifier), self.assertRaisesRegex(pk.PortakitError, "id"):
                self.load([entry(id=identifier, dest="ok")])

    def test_dest_unique_case_insensitively(self):
        with self.assertRaisesRegex(pk.PortakitError, "dest"):
            self.load([entry(id="a", dest="Tool"), entry(id="b", dest="tool")])

    def test_malformed_json_names_catalog(self):
        self.catalog.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(pk.PortakitError, "catalog"):
            pk.load_catalog(self.catalog)

    def test_tools_must_be_a_list(self):
        self.catalog.write_text('{"tools": false}', encoding="utf-8")
        with self.assertRaisesRegex(pk.PortakitError, "tools"):
            pk.load_catalog(self.catalog)


if __name__ == "__main__":
    unittest.main()
