"""Vertical closure for scripts/*.cmd launchers: every %~dp0 target exists.

Only `%~dp0<name>` tokens are parsed; comments, system executables such as
powershell.exe and free text are ignored. Quotes are stripped and the path is
resolved relative to scripts/ (so a `..\\` target is honored).
"""
from pathlib import Path
import re
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
TOKEN = re.compile(r"%~dp0([^\"\r\n]+)")


class LauncherTargetTests(unittest.TestCase):
    def test_every_cmd_launcher_targets_an_existing_script(self):
        launchers = sorted(SCRIPTS.glob("*.cmd"))
        self.assertTrue(launchers, "no launchers found")
        for launcher in launchers:
            text = launcher.read_text(encoding="utf-8", errors="replace")
            targets = [t.strip().strip('"') for t in TOKEN.findall(text)]
            with self.subTest(launcher=launcher.name):
                self.assertTrue(targets, "launcher references no %~dp0 target")
                for target in targets:
                    resolved = (SCRIPTS / target).resolve()
                    self.assertTrue(resolved.is_file(), f"missing target {target}")


if __name__ == "__main__":
    unittest.main()
