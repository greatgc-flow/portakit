"""Synthetic-only xan ZIP preflight tests: never download or run a vendor exe."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import unittest
from unittest import mock
import warnings
import zipfile

import support as fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "xan_local_zip_preflight", ROOT / "scripts" / "xan_zip_preflight.py")
auditor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auditor)


def build_zip(entries=None, compression=zipfile.ZIP_STORED):
    if entries is None:
        entries = [("xan.exe", b"SYNTHETIC-NOT-REAL-EXE"),
                   ("LICENSE", b"synthetic license notice")]
    output = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(output, "w") as archive:
        warnings.simplefilter("ignore", UserWarning)
        for item in entries:
            name, content = item
            archive.writestr(name, content, compress_type=compression)
    return output.getvalue()


class XanSourceTests(fixtures.Workspace):
    def setUp(self):
        super().setUp()
        self.source = self.base / "xan-x86_64-pc-windows-msvc.zip"
        self.data = build_zip()
        self.source.write_bytes(self.data)
        self.metadata = self.fake_metadata(self.data)
        self.evidence = self.base / "audit.json"

    @staticmethod
    def fake_metadata(data):
        return {
            "assetName": "xan-x86_64-pc-windows-msvc.zip",
            "expectedBytes": len(data),
            "expectedSha256": hashlib.sha256(data).hexdigest(),
            "version": "SYNTHETIC",
        }

    def use_zip(self, data):
        self.data = data
        self.source.write_bytes(data)
        self.metadata = self.fake_metadata(data)

    def test_source_ledger_pinned_official_metadata(self):
        result = auditor.official_record()
        self.assertEqual(result["version"], "0.61.0")
        self.assertEqual(result["candidateId"], "xan")
        self.assertEqual(result["assetName"], self.source.name)
        self.assertEqual(result["expectedBytes"], 6473075)
        self.assertEqual(
            result["expectedSha256"],
            "5f7bef4dcffbfb3a3a937ac180ed76cdf966cb13647251beffddb84d01c1ae54")

    def test_faked_synthetic_archive_audit_is_not_product_proof(self):
        before = self.source.read_bytes()
        report = auditor.inspect(self.source, self.metadata)
        self.assertEqual(report["outcome"], "LOCAL_ORIGINAL_STRUCTURE_PASS")
        self.assertEqual(report["structure"]["regularFiles"], 2)
        self.assertEqual(report["structure"]["xanExeCount"], 1)
        self.assertEqual(report["structure"]["expandedLogicalBytes"],
                         len(b"SYNTHETIC-NOT-REAL-EXE") + len(b"synthetic license notice"))
        self.assertEqual(report["runtimeWindows"], "NOT_VERIFIED")
        self.assertEqual(report["enterprisePermission"], "NOT_VERIFIED")
        self.assertEqual(report["release"], "SYNTHETIC")
        self.assertEqual(before, self.source.read_bytes())
        self.assertEqual(list(self.base.iterdir()), [self.source])

    def test_deflated_and_wrapped_zip_supported(self):
        self.use_zip(build_zip([
            ("xan-0.61.0/", b""),
            ("xan-0.61.0/xan.exe", b"synthetic" * 1200),
            ("xan-0.61.0/COPYING", b"synthetic notice")], zipfile.ZIP_DEFLATED))
        result = auditor.inspect(self.source, self.metadata)
        self.assertEqual(result["structure"]["directories"], 1)
        self.assertEqual(result["structure"]["regularFiles"], 2)
        self.assertEqual(result["structure"]["rootNames"], ["xan-0.61.0"])

    def test_hash_mismatch_and_changed_bytes_prevent_structure_read(self):
        self.metadata["expectedSha256"] = "0" * 64
        with mock.patch.object(auditor, "inspect_members",
                               side_effect=AssertionError("must not scan")):
            with self.assertRaisesRegex(auditor.XanPreflightError, "SHA-256 mismatch"):
                auditor.inspect(self.source, self.metadata)
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_exact_release_size_mismatch_rejected(self):
        self.metadata["expectedBytes"] += 1
        with self.assertRaisesRegex(auditor.XanPreflightError, "compressed bytes"):
            auditor.inspect(self.source, self.metadata)
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_invalid_source_metadata_null_empty_and_types(self):
        invalid = [
            None, [], {}, dict(self.metadata, assetName="different.zip"),
            dict(self.metadata, expectedBytes=0),
            dict(self.metadata, expectedBytes=True),
            dict(self.metadata, expectedSha256="invalid"),
            dict(self.metadata, expectedSha256="a" * 63),
        ]
        for source in invalid:
            with self.subTest(source=repr(source)[:40]):
                with self.assertRaises(auditor.XanPreflightError):
                    auditor.inspect(self.source, source)

    def test_original_wrong_basename_and_missing_path(self):
        other = self.base / "renamed.zip"
        other.write_bytes(self.data)
        with self.assertRaisesRegex(auditor.XanPreflightError, "filename"):
            auditor.inspect(other, self.metadata)
        self.source.unlink()
        with self.assertRaisesRegex(auditor.XanPreflightError, "missing"):
            auditor.inspect(self.source, self.metadata)
        with self.assertRaisesRegex(auditor.XanPreflightError, "path is required"):
            auditor.inspect(None, self.metadata)

    def test_casefold_duplicates_and_parent_file_conflicts(self):
        for pairs in [
            [("xan.exe", b"ok"), ("XAN.exe", b"evil")],
            [("xan.exe", b"ok"), ("folder", b"parent file"),
             ("folder/child", b"child")],
        ]:
            with self.subTest(pairs=pairs):
                self.use_zip(build_zip(pairs))
                with self.assertRaises(auditor.XanPreflightError):
                    auditor.inspect(self.source, self.metadata)

    def test_traversal_ads_reserved_drive_and_backslashes(self):
        for path in ("../xan.exe", "/xan.exe", "C:/xan.exe", "folder/../xan.exe",
                     "CON.txt", "xan.exe:stream", "folder\\xan.exe",
                     "xan.exe.", "xan.exe ", "folder//xan.exe"):
            with self.subTest(path=path):
                self.use_zip(build_zip([(path, b"synthetic")]))
                with self.assertRaises(auditor.XanPreflightError):
                    auditor.inspect(self.source, self.metadata)

    def test_symlink_and_special_members_denied(self):
        for filetype in (stat.S_IFLNK, stat.S_IFIFO):
            with self.subTest(filetype=filetype):
                link = zipfile.ZipInfo("xan.exe")
                link.create_system = 3
                link.external_attr = (filetype | 0o777) << 16
                self.use_zip(build_zip([(link, b"target")]))
                with self.assertRaisesRegex(auditor.XanPreflightError,
                                            "special ZIP member"):
                    auditor.inspect(self.source, self.metadata)

    def test_encrypted_and_unsupported_compression_denied(self):
        # Construct ZIP normally, then patch the in-memory ZipInfo metadata.
        with zipfile.ZipFile(io.BytesIO(self.data)) as z:
            info = z.infolist()[0]
            with mock.patch.object(info, "flag_bits", info.flag_bits | 1):
                with self.assertRaisesRegex(auditor.XanPreflightError, "Encrypted"):
                    auditor.inspect_members(io.BytesIO(self.data)) if False else (
                        self.check_encryption_via_zipinfo_patch())
        self.use_zip(build_zip(compression=zipfile.ZIP_BZIP2))
        with self.assertRaisesRegex(auditor.XanPreflightError, "Unsupported ZIP compression"):
            auditor.inspect(self.source, self.metadata)

    def check_encryption_via_zipinfo_patch(self):
        real = auditor.zipfile.ZipFile
        class EncryptedZip(real):
            def infolist(self):
                infos = super().infolist()
                infos[0].flag_bits |= 1
                return infos
        with mock.patch.object(auditor.zipfile, "ZipFile", EncryptedZip):
            auditor.inspect_members(io.BytesIO(self.data))

    def test_bad_crc_and_truncated_archive_fail_closed(self):
        damaged = bytearray(build_zip([("xan.exe", b"AAAA"), ("README", b"synthetic")]))
        at = damaged.find(b"AAAA")
        self.assertGreater(at, 0)
        damaged[at:at+4] = b"BBBB"
        self.use_zip(bytes(damaged))
        with self.assertRaisesRegex(auditor.XanPreflightError, "ZIP/CRC/read error"):
            auditor.inspect(self.source, self.metadata)
        self.use_zip(self.data[:17])
        with self.assertRaisesRegex(auditor.XanPreflightError, "ZIP/CRC/read error"):
            auditor.inspect(self.source, self.metadata)

    def test_zero_exes_and_multiple_exes_rejected(self):
        for items in [
            [("README", b"readme")],
            [("A/xan.exe", b"one"), ("B/xan.exe", b"two")],
            [],
        ]:
            with self.subTest(count=len(items)):
                self.use_zip(build_zip(items))
                with self.assertRaises(auditor.XanPreflightError):
                    auditor.inspect(self.source, self.metadata)

    def test_expanded_file_cap_and_member_cap_before_body_read(self):
        raw = bytearray(build_zip([("xan.exe", b"short")]))
        central = raw.find(b"PK\x01\x02")
        self.assertGreater(central, 0)
        struct.pack_into("<I", raw, central + 24, auditor.MAX_EXPANDED + 1)
        self.use_zip(bytes(raw))
        with self.assertRaisesRegex(auditor.XanPreflightError, "expanded byte limit"):
            auditor.inspect(self.source, self.metadata)
        with mock.patch.object(auditor, "MAX_MEMBERS", 1):
            self.use_zip(build_zip([("xan.exe", b"exe"), ("LICENSE", b"license")]))
            with self.assertRaisesRegex(auditor.XanPreflightError, "member count"):
                auditor.inspect(self.source, self.metadata)

    def test_changed_original_during_audit_is_detected(self):
        original = auditor.inspect_members
        def mutating(stream):
            result = original(stream)
            with self.source.open("r+b") as dst:
                dst.seek(0)
                dst.write(b"XXXX")
            return result
        with mock.patch.object(auditor, "inspect_members", side_effect=mutating):
            with self.assertRaisesRegex(auditor.XanPreflightError, "changed during"):
                auditor.inspect(self.source, self.metadata)

    def test_create_only_report_and_exact_console_log(self):
        report = auditor.inspect(self.source, self.metadata)
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            auditor.emit(report, self.evidence)
        transcript = self.evidence.with_suffix(".log").read_text(encoding="utf-8")
        self.assertEqual(capture.getvalue(), transcript)
        record = json.loads(self.evidence.read_text(encoding="utf-8"))
        self.assertEqual(record, report)
        with self.assertRaisesRegex(auditor.XanPreflightError, "already exists"):
            auditor.emit(report, self.evidence)
        self.assertEqual(self.evidence.with_suffix(".log").read_text(encoding="utf-8"),
                         transcript)

    def test_no_output_by_default_and_no_vendor_exec_even_on_cli_fail(self):
        with mock.patch.object(auditor, "official_record", return_value=self.metadata):
            with mock.patch("subprocess.Popen",
                            side_effect=AssertionError("vendor execution forbidden")):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(auditor.run(["--original", str(self.source)]), 0)
        self.assertIn("NO EXTRACTION / NO VENDOR EXECUTION", out.getvalue())
        self.assertFalse(self.evidence.exists())

    def test_cli_invalid_original_is_exit_2_not_success(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(auditor.run(["--original", str(self.source)]), 2)

    def test_ledger_negative_cases(self):
        correct = json.loads(auditor.LEDGER.read_text(encoding="utf-8"))
        for change in (
                lambda d: d.update(schemaVersion=9),
                lambda d: d.update(alternatives=[]),
                lambda d: d["alternatives"].append(dict(d["alternatives"][1])),
                lambda d: d["alternatives"][1]["windowsX64"].clear(),
                lambda d: d["alternatives"][1]["windowsX64"][0].update(sha256="broken"),
                lambda d: d["alternatives"][1]["windowsX64"][0].update(size=0)):
            copied = json.loads(json.dumps(correct))
            change(copied)
            p = self.base / "ledger.json"
            p.write_text(json.dumps(copied), encoding="utf-8")
            with self.assertRaises(auditor.XanPreflightError):
                auditor.official_record(p)


if __name__ == "__main__":
    unittest.main()
