"""Synthetic-only bounded subprocess tests on Windows; never run vendors."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_bounded_process", REPO / "scripts" / "bounded_process.py")
bounded = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bounded)


def python_child(source):
    """A test-owned interpreter, not an external or vendor program."""
    return [sys.executable, "-I", "-c", source]


class BoundedProcessTests(unittest.TestCase):

    def test_simple_exact_stdout_stderr(self):
        result = bounded.run_bounded(python_child(
            "import sys; sys.stdout.write('ok'); sys.stderr.write('warning')"),
            timeout_seconds=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((result.stdout, result.stderr), ("ok", "warning"))

    def test_nonzero_exit_is_returned_not_successfully_reinterpreted(self):
        result = bounded.run_bounded(python_child(
            "import sys; print('error'); sys.exit(7)"), timeout_seconds=5)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout.strip(), "error")

    def test_concurrent_bounded_pipes_no_stdout_stderr_deadlock(self):
        result = bounded.run_bounded(python_child(
            "import sys; "
            "sys.stdout.buffer.write(b'A'*120000); sys.stdout.flush(); "
            "sys.stderr.buffer.write(b'B'*120000); sys.stderr.flush()"),
            timeout_seconds=5, max_capture_bytes=128000)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "A" * 120000)
        self.assertEqual(result.stderr, "B" * 120000)

    def test_stdout_flood_fails_and_kills_direct_child(self):
        with self.assertRaisesRegex(bounded.BoundedProcessError, "OUTPUT_LIMIT"):
            bounded.run_bounded(python_child(
                "import sys; sys.stdout.buffer.write(b'X'*131072); "
                "sys.stdout.flush()"), timeout_seconds=5, max_capture_bytes=4096)

    def test_stderr_flood_fails_and_kills_direct_child(self):
        with self.assertRaisesRegex(bounded.BoundedProcessError, "OUTPUT_LIMIT"):
            bounded.run_bounded(python_child(
                "import sys; sys.stderr.buffer.write(b'X'*131072); "
                "sys.stderr.flush()"), timeout_seconds=5, max_capture_bytes=4096)

    def test_wait_timeout_fails_without_fake_completion(self):
        with self.assertRaisesRegex(bounded.BoundedProcessError, "TIMEOUT"):
            bounded.run_bounded(python_child(
                "import time; time.sleep(15)"), timeout_seconds=1)

    def test_invalid_limits_rejected_before_process_creation(self):
        with mock.patch.object(subprocess, "Popen",
                               side_effect=AssertionError("unexpected launch")):
            for timeout in (None, 0, 3601, -1, 1.0, True, "10"):
                with self.subTest(timeout=timeout):
                    with self.assertRaisesRegex(ValueError, "Child timeout"):
                        bounded.run_bounded(python_child("pass"),
                                            timeout_seconds=timeout)
            for cap in (None, 0, -1, True, 1.0, 1024*1024+1):
                with self.subTest(cap=cap):
                    with self.assertRaisesRegex(ValueError, "Child output cap"):
                        bounded.run_bounded(python_child("pass"),
                                            max_capture_bytes=cap)
            for args in (None, [], ["python", None], [""]):
                with self.subTest(args=args):
                    with self.assertRaisesRegex(ValueError, "argv"):
                        bounded.run_bounded(args)

    def test_launch_error_propagates_without_claiming_complete(self):
        with mock.patch.object(subprocess, "Popen",
                               side_effect=OSError("synthetic executable denied")):
            with self.assertRaisesRegex(OSError, "executable denied"):
                bounded.run_bounded(python_child("pass"))


if __name__ == "__main__":
    unittest.main()
