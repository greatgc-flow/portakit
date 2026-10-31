"""Tests for cli behavior."""

import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import unittest
from unittest import mock
import urllib.error

import support as fixtures

pk = fixtures.pk
entry = fixtures.entry
zip_bytes = fixtures.zip_bytes


class EnvelopeTests(fixtures.Workspace):
    def test_help_explains_commands_flags_and_data_loss(self):
        code, out, err = self.run_main("--help")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        for text in ("list", "install ID", "update ID", "remove ID",
                     "require ID", "current directory", "portable", "--root",
                     "--json", "JSON", "user data", "catalog"):
            with self.subTest(text=text):
                self.assertIn(text, " ".join(out.split()))

    def test_exit_codes_are_stable(self):
        self.assertEqual(pk.EXIT_CODES, dict(ok=0, usage=1, catalog=2, fetch=3,
                                             archive=4, state=5, busy=6))

    def test_abbreviated_options_are_usage_errors(self):
        self.write_catalog([entry()])
        for option in ["--j", "--roo"]:
            with self.subTest(option=option):
                code, result = self.call(option, "list")
                self.assertEqual(code, 1)
                self.assertEqual(result["error"]["code"], "usage")

    def test_http_exception_is_fetch_and_oserror_is_state(self):
        self.write_catalog([entry()])
        for error, expected in [(http.client.HTTPException("broken response"), "fetch"),
                                (OSError("disk full"), "state")]:
            with self.subTest(error=type(error).__name__), mock.patch.object(pk, "install", side_effect=error):
                code, result = self.call("install", "demo")
                self.assertEqual(code, pk.EXIT_CODES[expected])
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], expected)
                self.assertIn(str(error), result["error"]["message"])

    def test_urlerror_from_download_is_fetch(self):
        self.write_catalog([entry()])
        with mock.patch.object(pk.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            code, result = self.call("install", "demo")
        self.assertEqual(code, 3)
        self.assertEqual(result["error"]["code"], "fetch")

    def test_list_json_envelope_has_data_items(self):
        self.write_catalog([entry()])
        code, result = self.call("list")
        self.assertEqual(code, 0)
        self.assertEqual(set(result), {"ok", "command", "data", "error"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "list")
        self.assertIsNone(result["error"])
        self.assertEqual(set(result["data"]), {"items"})
        self.assertEqual(result["data"]["items"][0]["id"], "demo")

    def test_list_human_output_is_id_tab_version(self):
        self.write_catalog([entry()])
        code, out, _ = self.run_main("list", json_mode=False)
        self.assertEqual((code, out), (0, "demo\t1\n"))

    def test_catalog_error_json(self):
        self.catalog.write_text('{"tools":false}')
        code, result = self.call("list")
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "catalog")
        self.assertIn("tools", result["error"]["message"])

    def test_usage_error_is_json(self):
        code, result = self.call("install")
        self.assertEqual(code, 1)
        self.assertEqual(result["error"]["code"], "usage")

    def test_usage_error_under_json_is_exactly_one_envelope(self):
        code, out, err = self.run_main("--bogus")
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual((result["ok"], result["command"], result["data"]), (False, None, None))
        self.assertEqual(result["error"]["code"], "usage")
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_help_exits_zero_with_human_text_and_no_envelope(self):
        for argv in (["-h"], ["--json", "-h"], ["--help", "--json"]):
            out, err = io.StringIO(), io.StringIO()
            with self.subTest(argv=argv), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = pk.main(argv)
                except SystemExit as exc:
                    code = exc.code
            self.assertEqual(code, 0)
            self.assertIn("usage", out.getvalue().lower())
            with self.assertRaises(ValueError):
                json.loads(out.getvalue())

    def test_errors_go_to_stderr_without_json(self):
        self.root.mkdir()
        code, out, err = self.run_main("remove", "demo", json_mode=False)
        self.assertEqual(code, 5)
        self.assertEqual(out, "")
        self.assertIn("not installed", err)

    def test_opt_in_log_exact_json_without_install_root(self):
        self.write_catalog([entry()])
        log = self.base / "single-tool.log"
        code, out, err = self.run_main("--log-file", str(log), "list")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(log.read_text(encoding="utf-8"), out)
        self.assertTrue(json.loads(out)["ok"])
        self.assertFalse(self.root.exists())

    def test_opt_in_log_mirrors_error_stderr(self):
        self.root.mkdir()
        log = self.base / "stderr.log"
        code, out, err = self.run_main("--log-file", str(log), "remove",
                                       "demo", json_mode=False)
        self.assertEqual((code, out), (5, ""))
        self.assertIn("not installed", err)
        self.assertEqual(log.read_text(encoding="utf-8"), err)

    def test_opt_in_log_captures_program_warning_and_json_in_order(self):
        self.write_catalog([entry()])
        log = self.base / "both-streams.log"

        def fake_execute(args, downloader):
            print("synthetic warning", file=__import__("sys").stderr)
            return {"items": [entry()]}
        with mock.patch.object(pk, "execute", side_effect=fake_execute):
            code, out, err = self.run_main("--log-file", str(log), "list")
        self.assertEqual(code, 0)
        self.assertEqual(err, "synthetic warning\n")
        self.assertEqual(log.read_text(encoding="utf-8"), err + out)

    def test_opt_in_log_collision_or_bad_parent_blocks_before_install(self):
        self.write_catalog([entry()])
        log = self.base / "existing.log"
        log.write_text("private prior evidence", encoding="utf-8")
        for path in (log, self.base / "absent-parent" / "new.log"):
            with self.subTest(path=path):
                with mock.patch.object(pk, "execute",
                                       side_effect=AssertionError("executed")):
                    code, out, err = self.run_main("--log-file", str(path),
                                                   "install", "demo")
                self.assertEqual((code, err), (5, ""))
                self.assertEqual(json.loads(out)["error"]["code"], "state")
        self.assertEqual(log.read_text(encoding="utf-8"),
                         "private prior evidence")
        self.assertFalse(self.root.exists())

    def test_mutating_command_refuses_log_inside_tool_and_backup(self):
        # Synthetic ZIP fixture only. A successful remove/update must never
        # silently delete or relocate the evidence file it just wrote.
        tool, download = self.package()
        self.write_catalog([tool])
        self.assertEqual(self.call("install", "demo", downloader=download)[0], 0)
        receipt = self.state_bytes()
        for folder in ("demo", "demo.old", "unrelated"):
            with self.subTest(folder=folder):
                destination = self.root / folder
                destination.mkdir(exist_ok=True)
                log = destination / "audit.log"
                with mock.patch.object(pk, "execute",
                                       side_effect=AssertionError("executed")):
                    code, result = self.call("--log-file", str(log),
                                             "remove", "demo")
                self.assertEqual(code, 1)
                self.assertEqual(result["error"]["code"], "usage")
                self.assertIn(".portakit-evidence", result["error"]["message"])
                self.assertFalse(log.exists())
        self.assertEqual(self.state_bytes(), receipt)
        self.assertTrue((self.root / "demo" / "demo.exe").is_file())

    def test_mutating_command_refuses_log_in_cleaned_temp_directory(self):
        self.write_catalog([entry()])
        temporary = self.root / ".portakit-stage-demo.tmp"
        temporary.mkdir(parents=True)
        log = temporary / "test.log"
        with mock.patch.object(pk, "execute",
                               side_effect=AssertionError("executed")):
            code, result = self.call("--log-file", str(log),
                                     "install", "demo")
        self.assertEqual((code, result["error"]["code"]), (1, "usage"))
        self.assertFalse(log.exists())
        self.assertTrue(temporary.exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_mutating_command_accepts_reserved_local_evidence_and_retains_it(self):
        tool, download = self.package()
        self.write_catalog([tool])
        self.assertEqual(self.call("install", "demo", downloader=download)[0], 0)
        evidence_dir = self.root / ".portakit-evidence"
        evidence_dir.mkdir()
        log = evidence_dir / "remove.log"
        code, out, err = self.run_main("--log-file", str(log), "remove", "demo")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(log.read_text(encoding="utf-8"), out)
        self.assertEqual(json.loads(out)["data"]["id"], "demo")
        self.assertFalse((self.root / "demo").exists())

    def test_read_only_list_allows_user_log_under_other_root_dir(self):
        self.write_catalog([entry()])
        subfolder = self.root / "custom-evidence"
        subfolder.mkdir(parents=True)
        log = subfolder / "list.log"
        code, out, err = self.run_main("--log-file", str(log), "list")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(log.read_text(encoding="utf-8"), out)

    def test_failed_opt_in_log_write_restores_streams(self):
        self.write_catalog([entry()])
        log = self.base / "disk-full.log"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with mock.patch.object(pk._ConsoleTee, "write",
                                   side_effect=OSError("synthetic disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    pk.main(["--json", "--root", str(self.root),
                             "--log-file", str(log), "list"])
            # main() must restore the caller's redirect even after I/O failure.
            self.assertIs(__import__("sys").stdout, output)
        self.assertTrue(log.exists())
        self.assertFalse(self.root.exists())


class InstallTests(fixtures.InstallWorkspace):
    def test_cli_install_uses_injected_downloader(self):
        tool, download = self.package(artifact="exe", id="jq", dest="jq")
        self.write_catalog([tool])
        code, result = self.call("install", "jq", downloader=download)
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertTrue((self.root / "jq/jq.exe").exists())


@unittest.skipUnless(os.name == 'nt', 'Windows only')
class LockAndRootTests(fixtures.Workspace, fixtures.LockMixin):
    def test_bad_catalog_install_exits_2_before_creating_root(self):
        self.catalog.write_text('{"tools": [{"id": "demo"}]}', encoding="utf-8")
        code, result = self.call("install", "demo")
        self.assertEqual((code, result["error"]["code"]), (2, "catalog"))
        self.assertFalse(self.root.exists())

    def test_list_rejects_todo_hash_with_exit_2(self):
        self.write_catalog([entry(sha256="TODO")])
        code, result = self.call("list")
        self.assertEqual(code, 2)
        self.assertIn("sha256", result["error"]["message"])


class CliContractTests(fixtures.InstallWorkspace):
    def test_install_update_remove_data_shapes(self):
        tool, download = self.package()
        self.write_catalog([tool])
        code, result = self.call("install", "demo", downloader=download)
        self.assertEqual(code, 0)
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertTrue(result["data"]["changed"])
        self.assertTrue(os.path.samefile(result["data"]["dest"], self.root / "demo"))
        self.assertTrue(Path(result["data"]["dest"]).is_absolute())
        code, result = self.call("update", "demo", downloader=mock.Mock(side_effect=AssertionError("download")))
        self.assertEqual(code, 0)
        self.assertEqual(set(result["data"]), {"id", "version", "dest", "changed"})
        self.assertFalse(result["data"]["changed"])
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["data"]), (0, {"id": "demo"}))

    def test_unknown_install_id_is_usage_and_changes_nothing(self):
        self.write_catalog([entry()])
        (self.root / "ghost.old").mkdir()
        code, result = self.call("install", "ghost")
        self.assertEqual((code, result["error"]["code"]), (1, "usage"))
        self.assertTrue((self.root / "ghost.old").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())

    def test_update_of_uninstalled_id_with_stray_old_changes_nothing(self):
        self.write_catalog([entry()])
        (self.root / "demo.old").mkdir()
        download = mock.Mock(side_effect=AssertionError("download"))
        code, result = self.call("update", "demo", downloader=download)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("not installed", result["error"]["message"])
        self.assertTrue((self.root / "demo.old").exists())
        self.assertFalse((self.root / "demo").exists())

    def test_update_of_id_missing_from_catalog_is_not_in_catalog(self):
        previous = self.installed()
        self.write_catalog([entry(id="other", dest="other")])
        (self.root / "demo").rename(self.root / "demo.old")
        code, result = self.call("update", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("not in catalog", result["error"]["message"])
        self.assertIn("remove demo", result["error"]["message"])
        self.assertFalse((self.root / "demo").exists())  # resolve runs before recovery
        self.assertEqual(self.state_bytes(), previous)

    def test_update_with_changed_dest_is_state_error(self):
        previous = self.installed()
        tool, download = self.package("2", dest="other")
        self.write_catalog([tool])
        code, result = self.call("update", "demo", downloader=download)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("dest changed", result["error"]["message"])
        self.assertEqual(self.state_bytes(), previous)

    def test_remove_not_installed_and_install_already_installed(self):
        self.write_catalog([entry()])
        code, result = self.call("remove", "demo")
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        tool, download = self.package()
        self.write_catalog([tool])
        self.assertEqual(self.call("install", "demo", downloader=download)[0], 0)
        again = mock.Mock(side_effect=AssertionError("download"))
        code, result = self.call("install", "demo", downloader=again)
        self.assertEqual((code, result["error"]["code"]), (5, "state"))
        self.assertIn("update", result["error"]["message"])


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(pk.__file__).with_name("README.md")).read_text(encoding="utf-8")

    def test_removed_features_are_not_documented(self):
        for removed in ("cleanupPending", "defaultConfig", "`kind`", "kind:", ".portakit-cache",
                        "--force", "TODO"):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, self.text)

    def test_exit_table_matches_spec(self):
        for code, name in [(0, None), (1, "usage"), (2, "catalog"), (3, "fetch"),
                           (4, "archive"), (5, "state"), (6, "busy")]:
            with self.subTest(code=code):
                pattern = rf"\|\s*{code}\s*\|" + (rf"\s*{name}\s*\|" if name else "")
                self.assertRegex(self.text, pattern)

    def test_documents_recovery_and_update_rules(self):
        for needle in ("dest.old", "both exist", "remove", "sha256", "-h", "data"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)


class LocalFilesystemClassificationTests(fixtures.InstallWorkspace):
    def test_catalog_filesystem_errors_are_state_5(self):
        for command in (("list",), ("install", "demo")):
            for error in (FileNotFoundError("missing catalog"),
                          PermissionError("catalog access denied"), OSError("catalog disk error")):
                with self.subTest(command=command, error=error), \
                        mock.patch.object(Path, "read_text", side_effect=error):
                    code, result = self.call(*command)
                    self.assertEqual((code, result["error"]["code"]), (5, "state"))
                    self.assertIn(str(error), result["error"]["message"])
        self.assertFalse((self.root / ".portakit-lock").exists())


class SpecDriftTests(unittest.TestCase):
    def setUp(self):
        self.project = Path(pk.__file__).parent

    def test_documented_exit_tables_match_runtime_codes(self):
        for relative in ("README.md", "docs/SPEC.md"):
            text = (self.project / relative).read_text(encoding="utf-8")
            for name, code in pk.EXIT_CODES.items():
                label = "-" if name == "ok" else name
                with self.subTest(document=relative, code=code):
                    self.assertRegex(text, rf"\|\s*{code}\s*\|\s*{label}\s*\|")

    def test_spec_documents_catalog_and_operation_guarantees(self):
        text = " ".join((self.project / "docs/SPEC.md").read_text(encoding="utf-8").split())
        for rule in ("`latest` path segment after URL decoding",
                     "install refuses a destination owned by another state ID",
                     "case-insensitively", "even if its directory is absent",
                     "Identical and dest present -> no-op without downloading",
                     "`list` takes no lock, reads only the catalog, and does not clean temporary files",
                     "delete the state entry LAST"):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)


if __name__ == "__main__":
    unittest.main()
