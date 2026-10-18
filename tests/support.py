"""Shared fixtures and subprocess harnesses; contains no discoverable tests."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


SPEC = importlib.util.spec_from_file_location("portakit", Path(__file__).resolve().parents[1] / "portakit.py")
pk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pk)

# Real implementations captured before any test patches them.
REAL_RENAME = os.rename


def entry(**changes):
    value = dict(id="demo", version="1",
                 url="https://github.com/owner/project/releases/download/v1/demo.zip",
                 sha256="a" * 64, artifact="zip", dest="demo", preserveOnUpdate=[])
    value.update(changes)
    return value


def zip_bytes(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return output.getvalue()


class Workspace(unittest.TestCase):
    def setUp(self):
        # On Windows, inherit workspace ACLs instead of tempfile's mode=0o700.
        mkdir = os.mkdir
        with mock.patch("tempfile._os.mkdir", side_effect=lambda path, mode: mkdir(path, 0o777)):
            temporary = self.enterContext(tempfile.TemporaryDirectory(
                dir=Path(__file__).resolve().parent, prefix="tmp-"))
        self.base = Path(temporary)
        self.root = self.base / "root"
        self.catalog = self.base / "catalog.json"

    def write_catalog(self, tools):
        self.catalog.write_text(json.dumps({"tools": tools}), encoding="utf-8")

    def run_main(self, *args, json_mode=True, downloader=None):
        out, err = io.StringIO(), io.StringIO()
        argv = (["--json"] if json_mode else []) + ["--root", str(self.root), *args]
        with mock.patch.object(pk, "DEFAULT_CATALOG", self.catalog), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = pk.main(argv, downloader=downloader)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def call(self, *args, downloader=None):
        code, out, _ = self.run_main(*args, downloader=downloader)
        return code, json.loads(out)

    def patch_rename(self, hook):
        """Call hook(src, dst) before every os.rename, then rename for real."""
        def rename(src, dst, *args, **kwargs):
            hook(Path(src), Path(dst))
            return REAL_RENAME(src, dst, *args, **kwargs)
        return mock.patch.object(os, "rename", rename)

    def junction(self, link, target):
        Path(target).mkdir(parents=True, exist_ok=True)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
        self.addCleanup(self.drop_junction, link)

    @staticmethod
    def drop_junction(link):
        try:
            os.rmdir(link)
        except OSError:
            pass



class InstallWorkspace(Workspace):
    def setUp(self):
        super().setUp()
        self.root.mkdir()

    def package(self, version="1", members=None, **changes):
        payload = zip_bytes(members if members is not None else [("demo.exe", version.encode())])
        tool = entry(version=version, sha256=hashlib.sha256(payload).hexdigest(), **changes)
        return tool, lambda url, dest: dest.write_bytes(payload)

    def installed(self):
        tool, download = self.package()
        pk.install(tool, self.root, download)
        return (self.root / ".portakit-state.json").read_bytes()

    def state_bytes(self):
        return (self.root / ".portakit-state.json").read_bytes()


class ExtractWorkspace(Workspace):
    def extract(self, members):
        artifact = self.base / "input.zip"
        artifact.write_bytes(zip_bytes(members))
        pk.extract(artifact, entry(), self.root)


class ArchiveWorkspace(InstallWorkspace):
    def check_archive_error(self, payload):
        tool = entry(sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaises(pk.PortakitError) as caught:
            pk.install(tool, self.root, lambda url, dest: dest.write_bytes(payload))
        self.assertEqual(caught.exception.code, "archive")
        self.assertFalse((self.root / "demo").exists())
        self.assertFalse((self.root / ".portakit-state.json").exists())
        self.assertEqual(list(self.root.glob(".portakit-*.tmp")), [])


class FilesystemWorkspace(InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.clear_readonly_for_fixture_cleanup)

    def clear_readonly_for_fixture_cleanup(self):
        for path in self.base.rglob("*"):
            if path.is_file():
                path.chmod(path.stat().st_mode | stat.S_IWRITE)


HOLD_LOCK = (
    "import os, msvcrt, sys\n"
    "fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT | os.O_BINARY)\n"
    "msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)\n"
    "print('ready', flush=True)\n"
    "sys.stdin.readline()\n"
)

# Runs one portakit command and hard-exits (os._exit(42)) right after the chosen
# step: rename1/rename2, remove_dest/remove_old, or state (write_state).
KILL_SCRIPT = r'''
import importlib.util, os, sys
from pathlib import Path
module_path, root, catalog, payload, command, step = sys.argv[1:7]
spec = importlib.util.spec_from_file_location("portakit", module_path)
pk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pk)
pk.DEFAULT_CATALOG = Path(catalog)
real_rename, real_write, real_remove = os.rename, pk.write_state, pk.remove_tree
count = [0]
def rename(src, dst, *args, **kwargs):
    real_rename(src, dst, *args, **kwargs)
    count[0] += 1
    if step == "rename%d" % count[0]:
        os._exit(42)
def write_state(*args, **kwargs):
    real_write(*args, **kwargs)
    if step == "state":
        os._exit(42)
def remove_tree(path):
    real_remove(path)
    name = Path(path).name
    if ((step == "remove_dest" and name == "demo")
            or (step == "remove_old" and name == "demo.old")):
        os._exit(42)

pk.remove_tree = remove_tree
os.rename = rename
pk.write_state = write_state
def downloader(url, dest):
    Path(dest).write_bytes(Path(payload).read_bytes())
sys.exit(pk.main(["--json", "--root", root, command, "demo"], downloader=downloader))
'''


class LockMixin:
    @contextlib.contextmanager
    def held_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen([sys.executable, "-I", "-c", HOLD_LOCK, str(self.root / ".portakit-lock")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "ready")
            yield proc
        finally:
            proc.kill()
            proc.wait()
            proc.stdin.close()
            proc.stdout.close()


class CrashWorkspace(InstallWorkspace):
    def setUp(self):
        super().setUp()
        self.payload = zip_bytes([("demo.exe", b"2")])
        self.tool2 = entry(version="2", sha256=hashlib.sha256(self.payload).hexdigest())
        self.write_catalog([self.tool2])
        (self.base / "payload.zip").write_bytes(self.payload)

    def kill_at(self, command, step):
        done = subprocess.run(
            [sys.executable, "-I", "-c", KILL_SCRIPT, str(Path(pk.__file__)), str(self.root),
             str(self.catalog), str(self.base / "payload.zip"), command, step],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 42, done.stdout + done.stderr)

    def update_in_process(self):
        return self.call("update", "demo", downloader=lambda url, dest: dest.write_bytes(self.payload))
