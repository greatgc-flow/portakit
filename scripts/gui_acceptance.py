"""Local, consent-gated GUI acceptance for managed Windows portable apps.

Python 3.11+ standard library. Default probe NEVER starts vendor apps. Guided
review may optionally start the GUI, but never clicks or changes options.
No service/registry/network modifications are performed by this harness.
Vendor apps can have their own first-run side effects, so explicit flags guard
launch and Everything needs an additional first-run risk acknowledgement.

Exit 0: all selected tools manually attested as PASS (guided mode only).
Exit 1: FAIL (missing pin, path, crash or human failure).
Exit 2: NOT_VERIFIED (default safe probe, skipped/unconfirmed GUI).
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import portakit as core  # noqa: E402

TOOLS = {
    "everything": {
        "patterns": ("Everything.exe",),
        "requires": ("Everything.exe",),
        "checklist": [
            "Observe first-launch prompts and DECLINE UAC/NTFS service installation",
            "Use Tools > Options > Indexes > Folders for a TEST DIRECTORY ONLY",
            "Search the synthetic marker; verify no whole-drive index or HTTP/ETP enabled",
            "Check local/APPDATA settings/database writes; close the program manually",
        ],
    },
    "grepwin": {
        "patterns": ("grepWin.exe", "grepWin64.exe", "grepWin-x64.exe"),
        "requires": (),
        "checklist": [
            "Search ONLY synthetic evidence/fixtures; regex marker: PK-GUI-[0-9]+",
            "Observe matches in UTF-8 fixture and nonmatches; check no file modified",
            "Optionally review Replace UI but DO NOT trigger Replace on business files",
            "Close application manually; note settings/registry footprint",
        ],
    },
    "7zip": {
        "patterns": ("7zFM.exe",),
        "requires": ("7z.exe", "7z.dll", "7zG.exe", "License.txt"),
        "checklist": [
            "Open 7zFM.exe without administrative elevation",
            "Navigate ONLY synthetic evidence/fixtures and optionally create ZIP there",
            "Open ZIP and verify sample marker; do not change file associations",
            "Close application manually; note any registry/settings modifications",
        ],
    },
}
FIELDS = ["id", "status", "pin", "binary", "sha256", "source",
          "gui_launched", "human_attested", "note"]


class AcceptanceError(Exception):
    pass


def absolute(path):
    return Path(os.path.abspath(str(path)))


def discover_binary(folder, ident):
    """Exact known filenames only; unexpected or multiple matches are rejected."""
    folder = absolute(folder)
    core.check_links(folder)
    if not folder.is_dir():
        raise AcceptanceError("Managed directory missing: " + str(folder))
    files = []
    for path in folder.rglob("*"):
        core.check_links(path)
        if path.is_file() and path.name.lower() in {
                x.lower() for x in TOOLS[ident]["patterns"]}:
            files.append(path)
    if len(files) != 1:
        raise AcceptanceError("Expected one known " + ident + " GUI executable, found " +
                              str(len(files)))
    for name in TOOLS[ident]["requires"]:
        item = folder / name
        core.check_links(item)
        if not item.is_file():
            raise AcceptanceError("Required portable dependency missing: " + str(item))
    return files[0]


def probe_tool(root, ident, catalog, state):
    """Read-only pin and binary check; never tries to launch the GUI."""
    if ident not in TOOLS or ident not in catalog:
        raise AcceptanceError("Unknown tool ID: " + ident)
    pin = catalog[ident]
    installed = state.get(ident)
    if (not isinstance(installed, dict) or
            any(installed.get(x) != pin[x] for x in ("version", "sha256", "dest"))):
        raise AcceptanceError(ident + ": unmanaged, stale or mismatched catalog pin")
    exe = discover_binary(root / pin["dest"], ident)
    with exe.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"id": ident, "status": "NOT_VERIFIED", "pin": pin["version"],
            "binary": str(exe), "sha256": digest, "source": pin["url"],
            "gui_launched": False, "human_attested": False, "note": ""}


def ensure_evidence_path(root, evidence):
    core.check_links(root)
    core.check_links(evidence)
    try:
        if os.path.commonpath((str(root), str(evidence))) == str(root):
            raise AcceptanceError("Evidence must be OUTSIDE managed root to avoid touching apps")
    except ValueError:
        pass  # Different Windows drives are fine
    if os.path.lexists(evidence):
        raise AcceptanceError("Evidence directory already exists; refusal to overwrite")
    evidence.mkdir(parents=True, exist_ok=False)


class Evidence:
    def __init__(self, path):
        self.file = (path / "console.log").open("x", encoding="utf-8", newline="\n")

    def print(self, message):
        message = str(message)
        print(message, flush=True)
        self.file.write(message + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


def service_status():
    """Nonmutating query; service query failure is reported, never hidden."""
    if os.name != "nt":
        return "NOT_WINDOWS"
    try:
        p = subprocess.run(["sc.exe", "query", "Everything"],
                           capture_output=True, text=True, errors="replace",
                           timeout=8, check=False)
        return "PRESENT" if p.returncode == 0 else "NOT_FOUND_OR_INACCESSIBLE"
    except (OSError, subprocess.TimeoutExpired):
        return "UNAVAILABLE"


def fixture_files(folder):
    folder.mkdir(exist_ok=False)
    payload = ("PortaKit synthetic GUI test\n"
               "PK-GUI-12345\n"
               "a.b/c.log\n")
    (folder / "matching-utf8.txt").write_text(payload, encoding="utf-8")
    (folder / "nonmatching-utf8.txt").write_text("SAFE TEST DATA ONLY\n", encoding="utf-8")
    (folder / "matching-utf16.txt").write_text(payload, encoding="utf-16")
    return payload


def human_review(row, evidence, launch=False, allow_everything=False,
                 input_fn=input, launcher=subprocess.Popen):
    ident = row["id"]
    evidence.print("CHECKLIST " + ident + ":")
    for step in TOOLS[ident]["checklist"]:
        evidence.print("  - " + step)
    evidence.print("DATA: synthetic evidence/fixtures only; DO NOT use live MES data")
    if launch:
        if ident == "everything" and not allow_everything:
            row["note"] = "Everything launch blocked: explicit first-run approval missing"
            return row
        try:
            launcher([row["binary"]], cwd=str(Path(row["binary"]).parent))
            row["gui_launched"] = True
            evidence.print("GUI_START_REQUESTED: " + ident)
            evidence.print("NOTICE: manually inspect and CLOSE GUI; this harness never terminates it")
        except OSError as exc:
            row["status"] = "FAIL"
            row["note"] = "Failed to launch: " + str(exc)
            return row
    else:
        evidence.print("GUI NOT STARTED: launch manually if approved")
    verdict = input_fn("Result for " + ident + " [pass/fail/skip]: ").strip().lower()
    if verdict == "pass":
        row["status"] = "PASS"
        row["human_attested"] = True
        row["note"] = "Human attestation only; this script does not inspect GUI visually"
    elif verdict == "fail":
        row["status"] = "FAIL"
        row["note"] = "Human reported GUI failure"
    else:
        row["status"] = "NOT_VERIFIED"
        row["note"] = "Human did not attest PASS"
    return row


def run(args, *, read_input=input, launcher=subprocess.Popen):
    if os.name != "nt":
        raise AcceptanceError("Windows desktop only")
    root, evidence = absolute(args.root), absolute(args.evidence)
    if not root.is_dir():
        raise AcceptanceError("Managed root not found: " + str(root))
    if args.launch and not args.review:
        raise AcceptanceError("--launch requires --review")
    if args.allow_everything_first_run and not args.launch:
        raise AcceptanceError("--allow-everything-first-run requires --launch")
    if args.review and not sys.stdin.isatty():
        raise AcceptanceError("--review requires a local interactive console")
    tools = list(dict.fromkeys(args.tools))
    if not tools:
        raise AcceptanceError("At least one tool required")
    catalog = core.load_catalog(core.DEFAULT_CATALOG)
    state = core.read_state(root)
    ensure_evidence_path(root, evidence)
    emit = Evidence(evidence)
    rows = []
    try:
        emit.print("PORTAKIT GUI ACCEPTANCE (WINDOWS, LOCAL ONLY)")
        emit.print("ROOT: " + str(root))
        emit.print("EVIDENCE: " + str(evidence))
        emit.print("MODE: " + ("HUMAN REVIEW" if args.review else "READ-ONLY PROBE"))
        emit.print("LAUNCH: " + ("EXPLICIT" if args.launch else "NO"))
        emit.print("NOTICE: external process launches, if permitted, may change vendor settings")
        emit.print("NO AUTOINSTALL/REGISTRY/UPDATE/SERVICE/NETWORK/UPLOAD BY HARNESS")
        service_before = service_status()
        emit.print("EVERYTHING_SERVICE_BEFORE: " + service_before)
        fixture_files(evidence / "fixtures")
        for ident in tools:
            try:
                row = probe_tool(root, ident, catalog, state)
                emit.print("PIN_OK: " + ident + " " + row["pin"])
                emit.print("BIN_SHA256: " + ident + " " + row["sha256"])
                if args.review:
                    row = human_review(row, emit, launch=args.launch,
                                       allow_everything=args.allow_everything_first_run,
                                       input_fn=read_input, launcher=launcher)
            except (AcceptanceError, core.PortakitError, OSError, ValueError) as exc:
                row = {"id": ident, "status": "FAIL", "pin": "", "binary": "",
                       "sha256": "", "source": "", "gui_launched": False,
                       "human_attested": False, "note": str(exc)}
            rows.append(row)
            emit.print("STATUS: " + ident + " = " + row["status"] +
                       (": " + row["note"] if row["note"] else ""))
        emit.print("EVERYTHING_SERVICE_AFTER: " + service_status())
        with (evidence / "results.csv").open("x", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        manifest = {
            "schemaVersion": 1,
            "mode": "HUMAN_REVIEW" if args.review else "READ_ONLY_PROBE",
            "root": str(root),
            "selected": tools,
            "createdUtc": datetime.now(timezone.utc).isoformat(),
            "results": rows,
            "everythingServiceBefore": service_before,
        }
        (evidence / "result.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if any(row["status"] == "FAIL" for row in rows):
            result = 1
        elif any(row["status"] != "PASS" for row in rows):
            result = 2
        else:
            result = 0
        emit.print("RESULT: " + {0: "HUMAN_ATTESTED_PASS", 1: "FAIL",
                                2: "NOT_VERIFIED"}[result])
        emit.print("EVIDENCE_FILES: console.log, results.csv, result.json, fixtures/")
        emit.print("NOTE: Human PASS is not machine GUI automation proof")
        return result
    finally:
        emit.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--root", default=str(REPO / "portable"))
    ap.add_argument("--evidence", default=str(REPO.parent / (
        "portakit-gui-" + datetime.now().strftime("%Y%m%d-%H%M%S") +
        "-" + uuid.uuid4().hex[:8])))
    ap.add_argument("--tools", nargs="+", choices=tuple(TOOLS), default=list(TOOLS))
    ap.add_argument("--review", action="store_true",
                    help="interactive MANUAL checklist, may record human-attested PASS")
    ap.add_argument("--launch", action="store_true",
                    help="requires --review; explicitly launch each selected GUI")
    ap.add_argument("--allow-everything-first-run", action="store_true",
                    help="required to launch Everything: UAC/index/service effects possible")
    args = ap.parse_args(argv)
    try:
        return run(args)
    except (AcceptanceError, OSError, core.PortakitError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
