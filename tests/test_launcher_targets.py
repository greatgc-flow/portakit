"""Vertical closure for scripts/ launchers: every literal script target exists.

CMD: only `%~dp0<name>` tokens are parsed; comments, system executables such as
powershell.exe and free text are ignored. Quotes are stripped and the path is
resolved relative to scripts/ (so a `..\\` target is honored).

PowerShell: `Join-Path $scriptDir <quoted>` targets must exist in scripts/ and
`Join-Path $repo <quoted>.py` targets at the repository root. Positional or
`-Path`/`-ChildPath` named forms, either quote style, any casing and spacing
are accepted. Every `Join-Path` line naming `$scriptDir` must parse as a
literal; for `$repo` a parenthesized computed name is also allowed (evidence
folders), and non-`.py` literals such as "portable" are directories whose
existence is not required. Anything else fails so a bypass cannot hide.
"""
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
TOKEN = re.compile(r"%~dp0([^\"\r\n]+)")


def join_path_patterns(var):
    head = rf"Join-Path\s+(?:-Path\s+)?\${var}\s+(?:-ChildPath\s+)?"
    return (re.compile(head + r"[\"']([^\"'$]+)[\"']", re.I),   # quoted literal
            re.compile(head + r"\(", re.I),                      # computed name
            re.compile(rf"Join-Path[^\n]*\${var}\b", re.I))       # any occurrence


SCRIPT_LITERAL, SCRIPT_COMPUTED, SCRIPT_ANY = join_path_patterns("scriptDir")
REPO_LITERAL, REPO_COMPUTED, REPO_ANY = join_path_patterns("repo")


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

    def test_every_powershell_literal_script_target_exists(self):
        runners = sorted(SCRIPTS.glob("*.ps1"))
        self.assertTrue(runners, "no PowerShell runners found")
        for runner in runners:
            text = runner.read_text(encoding="utf-8", errors="replace")
            script_targets = SCRIPT_LITERAL.findall(text)
            repo_targets = REPO_LITERAL.findall(text)
            with self.subTest(runner=runner.name, variable="$scriptDir"):
                self.assertEqual(len(SCRIPT_ANY.findall(text)), len(script_targets),
                                 "a Join-Path $scriptDir occurrence was not parsed as a literal")
            with self.subTest(runner=runner.name, variable="$repo"):
                self.assertEqual(len(REPO_ANY.findall(text)),
                                 len(repo_targets) + len(REPO_COMPUTED.findall(text)),
                                 "a Join-Path $repo occurrence is neither literal nor computed")
            expected = [(SCRIPTS, name) for name in script_targets]
            expected += [(REPO, name) for name in repo_targets if name.lower().endswith(".py")]
            for base, name in expected:
                with self.subTest(runner=runner.name, target=name):
                    self.assertTrue((base / name).resolve().is_file(), f"missing target {name}")

    def test_powershell_pattern_accepts_quote_case_spacing_and_named_parameters(self):
        for sample in ('Join-Path $scriptDir "a.py"', "join-path  $ScriptDir  'a.py'",
                       "JOIN-PATH\t$scriptdir 'a.py'",
                       'Join-Path -Path $scriptDir -ChildPath "a.py"',
                       "Join-Path -Path $scriptDir 'a.py'", 'Join-Path $scriptDir -ChildPath "a.py"'):
            with self.subTest(sample=sample):
                self.assertEqual(SCRIPT_LITERAL.findall(sample), ["a.py"])
                self.assertEqual(len(SCRIPT_ANY.findall(sample)), 1)
        for sample in ('Join-Path $scriptDir $name', 'Join-Path $scriptDir "$name"',
                       'Join-Path -Path $scriptDir -ChildPath $name',
                       'Join-Path -ChildPath "a.py" -Path $scriptDir'):
            with self.subTest(sample=sample):
                self.assertEqual(SCRIPT_LITERAL.findall(sample), [])
                self.assertEqual(len(SCRIPT_ANY.findall(sample)), 1, "guard must count the bypass")
        self.assertEqual(SCRIPT_ANY.findall('Join-Path $outDir "log.txt"'), [])
        computed = 'Join-Path $repo ("office4-evidence-" + $stamp)'
        self.assertEqual((REPO_LITERAL.findall(computed), len(REPO_COMPUTED.findall(computed)),
                          len(REPO_ANY.findall(computed))), ([], 1, 1))
        self.assertEqual(REPO_LITERAL.findall('Join-Path -Path $repo -ChildPath "MISSING.py"'),
                         ["MISSING.py"])


if __name__ == "__main__":
    unittest.main()
