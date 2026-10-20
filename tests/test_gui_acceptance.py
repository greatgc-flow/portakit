"""No-GUI/no-network regression for a human-attested acceptance workflow."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import support as fixtures

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gui_acceptance", REPO / "scripts/gui_acceptance.py")
gui = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gui)


class GuiAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "portable"
        self.root.mkdir()
        self.evidence = self.base / "outside-evidence"
        self.catalog = {}
        self.state = {}

    def add(self, ident):
        path = self.root / ident
        path.mkdir()
        filename = {"everything": "Everything.exe", "grepwin": "grepWin-x64.exe",
                    "7zip": "7zFM.exe"}[ident]
        (path / filename).write_bytes(b"MZ" + b"x" * 500)
        for name in gui.TOOLS[ident]["requires"]:
            (path / name).write_bytes(b"MZ" + b"x" * 500)
        self.catalog[ident] = {
            "id": ident, "version": "test", "dest": ident,
            "url": "https://vendor.example/v1/" + ident + ".zip",
            "sha256": "a" * 64,
        }
        self.state[ident] = {"version": "test", "dest": ident, "sha256": "a" * 64}
        return path

    def args(self, tools, **overrides):
        values = dict(root=self.root, evidence=self.evidence, tools=tools,
                      review=False, launch=False, allow_everything_first_run=False)
        values.update(overrides)
        return SimpleNamespace(**values)

    def run_offline(self, args, *, input_fn=input, launcher=None, tty=False):
        with mock.patch.object(gui.core, "load_catalog", return_value=self.catalog), \
             mock.patch.object(gui.core, "read_state", return_value=self.state), \
             mock.patch.object(gui, "service_status", return_value="NOT_FOUND_OR_INACCESSIBLE"), \
             mock.patch.object(gui.sys, "stdin", mock.Mock(isatty=lambda: tty)):
            return gui.run(args, read_input=input_fn,
                           launcher=launcher or mock.Mock())

    def test_safe_probe_no_gui_no_socket_not_verified_and_mirrored_log(self):
        for ident in ("everything", "grepwin", "7zip"):
            self.add(ident)
        out = io.StringIO()
        launch = mock.Mock(side_effect=AssertionError("No GUI launch allowed"))
        with contextlib.redirect_stdout(out):
            result = self.run_offline(self.args(["everything", "grepwin", "7zip"]),
                                      launcher=launch)
        self.assertEqual(result, 2)
        self.assertEqual(out.getvalue(), (self.evidence / "console.log").read_text(
            encoding="utf-8"))
        self.assertEqual(launch.call_count, 0)
        rows = list(csv.DictReader((self.evidence / "results.csv").open(
            encoding="utf-8-sig", newline="")))
        self.assertEqual([r["status"] for r in rows], ["NOT_VERIFIED"] * 3)
        self.assertEqual(len(list((self.evidence / "fixtures").glob("*.txt"))), 3)
        for ident in ("everything", "grepwin", "7zip"):
            self.assertNotIn("installed", (self.evidence / "console.log").read_text(
                encoding="utf-8").lower())

    def test_pin_mismatch_does_not_launch_and_fail(self):
        self.add("everything")
        self.state["everything"]["sha256"] = "b" * 64
        launcher = mock.Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            code = self.run_offline(self.args(["everything"]), launcher=launcher)
        self.assertEqual(code, 1)
        self.assertEqual(launcher.call_count, 0)
        self.assertEqual(json.loads((self.evidence / "result.json").read_text(
            encoding="utf-8"))["results"][0]["status"], "FAIL")

    def test_existing_evidence_never_overwritten(self):
        self.add("grepwin")
        self.evidence.mkdir()
        with self.assertRaisesRegex(gui.AcceptanceError, "already exists"):
            self.run_offline(self.args(["grepwin"]))

    def test_refuse_evidence_within_managed_root(self):
        self.add("7zip")
        with self.assertRaisesRegex(gui.AcceptanceError, "OUTSIDE"):
            self.run_offline(self.args(["7zip"], evidence=self.root / "logs"))

    def test_review_requires_tty_and_launch_requires_review(self):
        self.add("7zip")
        with self.assertRaisesRegex(gui.AcceptanceError, "requires --review"):
            self.run_offline(self.args(["7zip"], launch=True))
        with self.assertRaisesRegex(gui.AcceptanceError, "interactive"):
            self.run_offline(self.args(["7zip"], review=True))

    def test_explicit_review_pass_has_human_marker(self):
        self.add("grepwin")
        launcher = mock.Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.run_offline(self.args(["grepwin"], review=True, launch=True),
                                      launcher=launcher, input_fn=lambda _: "pass", tty=True)
        self.assertEqual(result, 0)
        launcher.assert_called_once()
        row = json.loads((self.evidence / "result.json").read_text(
            encoding="utf-8"))["results"][0]
        self.assertEqual(row["status"], "PASS")
        self.assertTrue(row["human_attested"])
        self.assertTrue(row["gui_launched"])

    def test_everything_requires_separate_explicit_first_run_ack(self):
        self.add("everything")
        launcher = mock.Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.run_offline(self.args(["everything"], review=True, launch=True),
                                      launcher=launcher, input_fn=lambda _: "pass", tty=True)
        self.assertEqual(result, 2)
        launcher.assert_not_called()
        self.assertEqual(json.loads((self.evidence / "result.json").read_text(
            encoding="utf-8"))["results"][0]["status"], "NOT_VERIFIED")

    def test_everything_approved_launch_then_manual_skip(self):
        self.add("everything")
        launcher = mock.Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            code = self.run_offline(self.args(["everything"], review=True, launch=True,
                                      allow_everything_first_run=True), launcher=launcher,
                                      input_fn=lambda _: "skip", tty=True)
        self.assertEqual(code, 2)
        launcher.assert_called_once()
        self.assertFalse(json.loads((self.evidence / "result.json").read_text(
            encoding="utf-8"))["results"][0]["human_attested"])

    def test_binary_discovery_rejects_duplicate_and_symlink(self):
        d = self.add("grepwin")
        (d / "grepWin.exe").write_bytes(b"MZ")
        with self.assertRaisesRegex(gui.AcceptanceError, "found 2"):
            gui.discover_binary(d, "grepwin")
        (d / "grepWin.exe").unlink()
        link = d / "grepWin-other.exe"
        try:
            link.symlink_to(d / "grepWin-x64.exe")
        except (OSError, NotImplementedError):
            self.skipTest("Windows user lacks symlink creation privilege")
        with self.assertRaisesRegex(Exception, "Reparse path rejected"):
            gui.discover_binary(d, "grepwin")


if __name__ == "__main__":
    unittest.main()
