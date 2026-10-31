"""Synthetic DuckDB tar.gz preflight tests, never read real vendor executables."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portakit_targz_preflight", ROOT / "scripts" / "targz_preflight.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


def archive_bytes(entries, *, pax=False):
    """Build an in-memory synthetic vendor original without OS or network."""
    buffer = io.BytesIO()
    fmt = tarfile.PAX_FORMAT if pax else tarfile.USTAR_FORMAT
    with tarfile.open(fileobj=buffer, mode="w:gz", format=fmt) as archive:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.size = 0
                archive.addfile(info)
            elif kind == "file":
                info.size = len(data)
                if pax:
                    info.pax_headers = {"comment": "extra metadata"}
                archive.addfile(info, io.BytesIO(data))
            else:
                info.type = kind
                info.linkname = "target"
                archive.addfile(info)
    return buffer.getvalue()


class TarGzReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        self.original = self.root / "original.tar.gz"

    def write(self, entries, *, pax=False):
        data = archive_bytes(entries, pax=pax)
        self.original.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def check_bad(self, entries, msg):
        digest = self.write(entries)
        with self.assertRaisesRegex(check.TarAuditError, msg):
            check.inspect(self.original, digest)
        self.assertEqual(list(self.root.iterdir()), [self.original])

    def test_valid_local_tar_report_is_only_structural(self):
        digest = self.write([
            ("bundle/", b"", "dir"),
            ("bundle/duckdb.exe", b"MZ-fake-do-not-run", "file"),
            ("bundle/readme.txt", b"offline fixture", "file"),
        ])
        report = check.inspect(self.original, digest)
        self.assertEqual(report["outcome"], "LOCAL_ORIGINAL_STRUCTURE_PASS")
        self.assertEqual(report["sourceSHA256"], digest)
        self.assertEqual(report["compressedBytes"], self.original.stat().st_size)
        self.assertEqual(report["structure"]["regularFiles"], 2)
        self.assertEqual(report["structure"]["directories"], 1)
        self.assertEqual(report["structure"]["expandedLogicalBytes"],
                         len(b"MZ-fake-do-not-run") + len(b"offline fixture"))
        self.assertEqual(report["structure"]["rootNames"], ["bundle"])
        self.assertIn("not publisher authentication", report["notice"])
        self.assertFalse((self.root / "bundle").exists())

    def test_casefold_collisions_and_unsafe_windows_paths(self):
        for bad in ("../escape", "/absolute", "C:/evil.dll",
                    "x/../../evil", "CON", "com1.txt", "x/dir. ",
                    "name:stream", "a//b", "\\\\host\\share\\x"):
            with self.subTest(path=bad):
                self.check_bad([("good.txt", b"x", "file"),
                                (bad, b"evil", "file")], "Unsafe TAR member")
        self.check_bad([("A.txt", b"a", "file"),
                        ("a.TXT", b"b", "file")], "duplicate/case")

    def test_file_used_as_directory_in_both_orders(self):
        for rows in (
            [("a", b"file", "file"), ("a/child.txt", b"child", "file")],
            [("a/child.txt", b"child", "file"), ("a", b"file", "file")]
        ):
            with self.subTest(rows=rows):
                self.check_bad(rows, "used as parent")

    def test_symlink_hardlink_fifo_and_empty_archive_refused(self):
        for typ in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE):
            with self.subTest(typ=typ):
                self.check_bad([("dir/file.txt", b"ok", "file"),
                                ("dir/bad", b"", typ)], "link, sparse, or special")
        self.check_bad([], "no regular files")
        self.check_bad([("directory/", b"", "dir")], "no regular files")

    def test_pax_metadata_requires_manual_review(self):
        digest = self.write([("safe.txt", b"data", "file")], pax=True)
        with self.assertRaisesRegex(check.TarAuditError, "PAX"):
            check.inspect(self.original, digest)

    def test_member_count_expanded_bytes_and_path_depth_limits(self):
        rows = [("a.txt", b"a", "file"), ("b.txt", b"b", "file")]
        digest = self.write(rows)
        with mock.patch.object(check, "MAX_MEMBERS", 1):
            with self.assertRaisesRegex(check.TarAuditError, "member count"):
                check.inspect(self.original, digest)
        with mock.patch.object(check, "MAX_EXPANDED_BYTES", 1):
            with self.assertRaisesRegex(check.TarAuditError, "expanded bytes"):
                check.inspect(self.original, digest)
        with mock.patch.object(check, "MAX_DEPTH", 1):
            digest = self.write([("dir/sub/file", b"x", "file")])
            with self.assertRaisesRegex(check.TarAuditError, "depth"):
                check.inspect(self.original, digest)

    def test_gzip_stream_budget_counts_headers_and_padding(self):
        digest = self.write([("small.txt", b"x", "file")])
        with mock.patch.object(check, "MAX_GZIP_OUTPUT", 512):
            with self.assertRaisesRegex(check.TarAuditError,
                                        "uncompressed stream exceeds"):
                check.inspect(self.original, digest)

    def test_sha_mismatch_missing_bad_digest_and_compressed_bound(self):
        sha = self.write([("file", b"content", "file")])
        with self.assertRaisesRegex(check.TarAuditError, "SHA-256 mismatch"):
            check.inspect(self.original, "0" * 64)
        with self.assertRaisesRegex(check.TarAuditError, "64 hex"):
            check.inspect(self.original, None)
        with self.assertRaisesRegex(check.TarAuditError, "64 hex"):
            check.inspect(self.original, "x" * 64)
        with mock.patch.object(check, "MAX_ARCHIVE_BYTES", 8):
            with self.assertRaisesRegex(check.TarAuditError, "compressed size"):
                check.inspect(self.original, sha)
        with self.assertRaisesRegex(check.TarAuditError, "not found"):
            check.inspect(self.root / "missing.tar.gz", sha)

    def test_truncated_or_bad_gzip_is_not_success(self):
        valid = archive_bytes([("good", b"data", "file")])
        for changed in (b"not-gzip-data", valid[:-7],
                        valid[:max(1, len(valid)//2)]):
            with self.subTest(size=len(changed)):
                self.original.write_bytes(changed)
                digest = hashlib.sha256(changed).hexdigest()
                with self.assertRaises(check.TarAuditError):
                    check.inspect(self.original, digest)

    def test_tampered_during_audit_rejected_and_never_written(self):
        sha = self.write([("safe.txt", b"hello", "file")])
        real = check.hash_stream
        calls = [0]
        def switched(stream):
            calls[0] += 1
            result = real(stream)
            if calls[0] == 2:
                return ("0" * 64, result[1])
            return result
        with mock.patch.object(check, "hash_stream", side_effect=switched):
            with self.assertRaisesRegex(check.TarAuditError, "changed"):
                check.inspect(self.original, sha)
        self.assertEqual(calls[0], 2)
        self.assertFalse((self.root / "safe.txt").exists())

    def test_cli_requires_official_digest_and_is_read_only_by_default(self):
        import subprocess
        sha = self.write([("duckdb.exe", b"synthetic", "file")])
        stdout, stderr = io.StringIO(), io.StringIO()
        official = {"sha256FromReleaseMetadata": sha}
        with mock.patch.object(check, "official_pin", return_value=official), (
                mock.patch.object(check.kit.core, "download",
                                  side_effect=AssertionError("download"))), (
                mock.patch.object(check.kit.sets, "apply",
                                  side_effect=AssertionError("install"))), (
                mock.patch.object(subprocess, "run",
                                  side_effect=AssertionError("vendor run"))):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = check.run(["--original", str(self.original)])
        self.assertEqual((rc, stderr.getvalue()), (0, ""))
        self.assertIn("LOCAL_ORIGINAL_STRUCTURE_PASS", stdout.getvalue())
        self.assertIn("NO EXTRACTION", stdout.getvalue())
        self.assertEqual(list(self.root.iterdir()), [self.original])

    def test_cli_new_only_json_and_exact_console_log(self):
        sha = self.write([("duckdb.exe", b"synthetic", "file")])
        target = self.root / "approved-local-report.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(check, "official_pin",
                               return_value={"sha256FromReleaseMetadata": sha}):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = check.run(["--original", str(self.original), "--out", str(target)])
        self.assertEqual((rc, stderr.getvalue()), (0, ""))
        self.assertEqual(stdout.getvalue(),
                         target.with_suffix(".log").read_text(encoding="utf-8"))
        report = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(report["sourceSHA256"], sha)
        old_json = target.read_bytes()
        old_log = target.with_suffix(".log").read_bytes()
        with mock.patch.object(check, "official_pin",
                               return_value={"sha256FromReleaseMetadata": sha}):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                rc = check.run(["--original", str(self.original), "--out", str(target)])
        self.assertEqual(rc, 2)
        self.assertIn("already exists", err.getvalue())
        self.assertEqual(target.read_bytes(), old_json)
        self.assertEqual(target.with_suffix(".log").read_bytes(), old_log)

    def test_unaltered_duckdb_official_pin_stays_research_only(self):
        real = check.official_pin()
        self.assertEqual(real["id"], "duckdb-cli")
        self.assertEqual(real["stage"], "RESEARCH_ONLY")
        self.assertEqual(real["artifactType"], "tar.gz")
        self.assertEqual(real["sha256FromReleaseMetadata"],
                         "91663c2f36c2a334b0e5e639006d8c29c29e013af0c477d80bb931df68870312")
        catalog = (ROOT / "catalog.json").read_text(encoding="utf-8")
        self.assertNotIn('"id": "duckdb-cli"', catalog)
        code = (ROOT / "scripts" / "targz_preflight.py").read_text("utf-8")
        self.assertNotIn("extractall(", code)
        self.assertNotIn("subprocess.run(", code)


if __name__ == "__main__":
    unittest.main()
