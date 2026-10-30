"""Read-only per-editor-plugin selections without host-side installation."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kit = load("portakit_kit_plugins", "my_toolkit.py")
gui = load("portakit_kit_plugin_picker", "toolkit_picker.py")
assets = load("portakit_kit_plugin_assets", "offline_assets.py")
foot = load("portakit_kit_plugin_foot", "kit_footprint.py")


class PluginKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.temp) / "plugin-kit.json"
        self.root = Path(self.temp) / "notinstalled"
        self.pins, self.cats, self.profiles, self.tools = kit.inventory()
        self.plugs = kit.plugin_inventory(self.pins)

    def save(self, obj):
        with contextlib.redirect_stdout(io.StringIO()):
            kit.save_new(obj, self.path)

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = kit.run(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_six_choices_and_alias_mapping(self):
        self.assertEqual(len(self.plugs), 6)
        self.assertEqual([x["host"] for x in self.plugs.values()].count("winmerge"), 2)
        pinned = [x for x in self.plugs.values()
                  if x["status"] == "PINNED_METADATA_ONLY"]
        self.assertEqual({x["id"] for x in pinned}, {"compareplus", "jsontools-npp"})
        self.assertEqual(pinned[1]["pin"]["sha256"],
                         self.pins["notepad++"]["recommended"]["plugins"][1]["sha256"])

    def test_v1_files_are_unchanged_with_no_plugin(self):
        v1 = kit.make_kit("legacy", ["notepad++"], self.pins, self.tools)
        self.assertEqual(v1["schemaVersion"], 1)
        self.assertNotIn("pluginSelections", v1)
        self.save(v1)
        self.assertEqual(kit.read_kit(self.path, self.pins, self.tools), v1)

    def test_single_plugin_becomes_v2_but_never_installable(self):
        v2 = kit.make_kit("my-kit", ["notepad++"], self.pins, self.tools,
                          plugins=["compareplus"])
        self.assertEqual(v2["schemaVersion"], 2)
        self.assertEqual(v2["pluginSelections"][0]["status"], "PINNED_METADATA_ONLY")
        self.assertEqual(v2["pluginSelections"][0]["lockedPin"]["version"], "3.0.0")
        self.save(v2)
        self.assertEqual(v2, kit.read_kit(self.path, self.pins, self.tools))
        self.assertFalse(self.root.exists())

    def test_multiple_plugin_host_dependency_and_dedup(self):
        data = kit.make_kit("x", ["notepad++", "winmerge"], self.pins, self.tools,
                            plugins=["compareplus", "compareplus", "xdocdiff"])
        self.assertEqual([x["id"] for x in data["pluginSelections"]],
                         ["compareplus", "xdocdiff"])
        self.assertEqual(data["pluginSelections"][1]["status"], "RESEARCH_ONLY")
        with self.assertRaisesRegex(kit.KitError, "host"):
            kit.make_kit("x", ["jq"], self.pins, self.tools, plugins=["compareplus"])
        with self.assertRaisesRegex(kit.KitError, "Unknown"):
            kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                         plugins=["inject-binary"])

    def test_v2_bad_shape_null_duplicates_and_host_mismatch(self):
        source = kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                              plugins=["compareplus"])
        for mutation in (
                lambda obj: obj.update(pluginSelections=[]),
                lambda obj: obj.update(pluginSelections=None),
                lambda obj: obj["pluginSelections"].append(
                    dict(obj["pluginSelections"][0])),
                lambda obj: obj["pluginSelections"][0].update(host="winmerge"),
                lambda obj: obj["pluginSelections"][0].update(status="INSTALL"),
                lambda obj: obj["pluginSelections"][0].update(extra="x"),
        ):
            with self.subTest(mutation=mutation):
                obj = json.loads(json.dumps(source))
                mutation(obj)
                self.path.write_text(json.dumps(obj), "utf-8")
                with self.assertRaises(kit.KitError):
                    kit.read_kit(self.path, self.pins, self.tools)

    def test_pin_drift_blocks_v2_before_actions(self):
        obj = kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                           plugins=["jsontools-npp"])
        obj["pluginSelections"][0]["lockedPin"]["sha256"] = "a" * 64
        self.path.write_text(json.dumps(obj), "utf-8")
        with self.assertRaisesRegex(kit.KitError, "PIN_CHANGED"):
            kit.read_kit(self.path, self.pins, self.tools)

    def test_research_plugin_must_not_carry_pin(self):
        obj = kit.make_kit("x", ["winmerge"], self.pins, self.tools,
                           plugins=["merge7z"])
        obj["pluginSelections"][0]["lockedPin"] = {"version": "1", "sha256": "f" * 64,
                                                    "dest": "plugins/bad"}
        self.path.write_text(json.dumps(obj), "utf-8")
        with self.assertRaisesRegex(kit.KitError, "Research"):
            kit.read_kit(self.path, self.pins, self.tools)

    def test_v2_build_blocks_even_pinned_plugin_and_recommended(self):
        self.save(kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                               plugins=["compareplus"]))
        with mock.patch.object(kit.sets, "apply") as apply:
            rc, out, err = self.call("build", "--kit", str(self.path),
                                     "--root", str(self.root), "--yes")
            self.assertEqual(rc, 1)
            self.assertIn("metadata-only", err)
            rc, out, err = self.call("build", "--kit", str(self.path),
                                     "--root", str(self.root), "--yes",
                                     "--recommended", "--skip-pending")
            self.assertEqual(rc, 1)
            self.assertIn("conflicts with explicit plugin", err)
            apply.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_v2_skip_pending_only_host_without_recommended(self):
        self.save(kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                               plugins=["compareplus"]))
        with mock.patch.object(kit.sets, "apply", return_value={"failed": None}) as op:
            rc, _, err = self.call("build", "--kit", str(self.path),
                                    "--root", str(self.root), "--yes", "--skip-pending")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual([x["id"] for x in op.call_args.args[0]["tools"]],
                         ["notepad++"])
        self.assertFalse(op.call_args.args[1])

    def test_cli_plugin_listing_and_creation(self):
        rc, out, err = self.call("plugins")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(len(out.strip().splitlines()), 6)
        rc, out, err = self.call("create", "--name", "one", "--out", str(self.path),
                                  "--tool", "notepad++", "--plugin", "csvlint-npp")
        self.assertEqual((rc, err), (0, ""))
        data = kit.read_kit(self.path, self.pins, self.tools)
        self.assertEqual(data["schemaVersion"], 2)
        self.assertEqual(data["pluginSelections"][0]["status"], "RESEARCH_ONLY")
        self.assertIn("EDITOR_PLUGINS_METADATA_ONLY", out)

    def test_gui_plugin_host_remove_and_import(self):
        model = gui.PickerModel()
        with self.assertRaisesRegex(gui.kit.KitError, "host"):
            model.add_plugin("compareplus")
        model.add(["notepad++"])
        model.add_plugin("compareplus")
        model.add_plugin("csvlint-npp")
        data = model.draft("x")
        self.assertEqual(len(data["pluginSelections"]), 2)
        with contextlib.redirect_stdout(io.StringIO()):
            model.save("x", self.path)
        loaded = gui.PickerModel()
        loaded.load_existing(self.path)
        self.assertEqual(loaded.selected_plugins, ["compareplus", "csvlint-npp"])
        loaded.remove(["notepad++"])
        self.assertEqual(loaded.selected_plugins, [])
        self.assertEqual(loaded.selected, [])
        self.assertFalse(self.root.exists())

    def test_gui_pending_plugin_not_silently_promoted(self):
        model = gui.PickerModel()
        model.add(["notepad++"])
        model.add_plugin("csvlint-npp")
        with contextlib.redirect_stdout(io.StringIO()):
            model.save("x", self.path)
        later = gui.PickerModel()
        later.load_existing(self.path)
        current = dict(later.plugin_catalog["csvlint-npp"])
        current["status"] = "PINNED_METADATA_ONLY"
        current["pin"] = {"version": "1", "sha256": "f" * 64,
                          "dest": "plugins/CSVLint"}
        later.plugin_catalog["csvlint-npp"] = current
        with mock.patch.object(gui.kit, "plugin_inventory",
                               return_value=later.plugin_catalog):
            saved = later.draft("still-unapproved")
            self.assertEqual(saved["pluginSelections"][0]["status"],
                             "RESEARCH_ONLY")
            later.remove_plugin("csvlint-npp")
            later.add_plugin("csvlint-npp")
            self.assertEqual(later.draft("new-choice")["pluginSelections"][0]["status"],
                             "PINNED_METADATA_ONLY")

    def test_readonly_ancillary_workflows_ignore_plugin_binaries(self):
        data = kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                            plugins=["compareplus"])
        obj = assets.make_manifest(data, self.pins)
        self.assertEqual(obj["approvedCatalogPins"], 1)
        self.assertEqual([x["id"] for x in obj["assets"]], ["notepad++"])
        self.assertEqual(foot.audit(data, self.root)["selectedPinned"], 1)

    def test_export_no_vendor_files_from_plugin_selection(self):
        self.save(kit.make_kit("x", ["notepad++"], self.pins, self.tools,
                               plugins=["xdocdiff" if False else "compareplus"]))
        code, output, err = self.call("plan", "--kit", str(self.path),
                                       "--root", str(self.root))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("PLUGIN: compareplus", output)
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
