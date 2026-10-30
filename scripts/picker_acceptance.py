"""Optional human GUI acceptance recorder for the personal-kit Tk picker.

CHECK (default) is read-only and does NOT create a GUI window. REVIEW records
only operator-entered PASS / FAIL / SKIP for synthetic nonproduction scenarios.
The recorder never starts vendors, probes networks, installs programs, changes
Windows settings or silently claims visual acceptance from CI.

Python 3.11+ standard library; Windows interactive REVIEW recommended.
Local JSON and exact program-produced console transcript are NEW-ONLY.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402

PICKER = HERE / "scripts" / "toolkit_picker.py"
SCHEMA_VERSION = 1
NOTICE = ("OPERATOR SELF-REPORT ONLY: NOT automated GUI proof, screen-reader "
          "certification, vendor authorization, EDR approval or release acceptance.")

# Independent cases: one observation cannot silently count as several passes.
CHECKS = (
    ("launch", "Open MyToolkitGUI.cmd as a normal user; no admin prompt or vendor launch"),
    ("dpi100", "At Windows 100% scale, check picker/overview no clipped controls"),
    ("dpi150", "At Windows 150% scale, check picker/overview no clipped controls"),
    ("dpi200", "At Windows 200% scale, check picker/overview no clipped controls"),
    ("ime", "Search Korean/ASCII/mixed case with IME; results and text remain usable"),
    ("keyboard", "Ctrl+F, Space/Enter, Ctrl+A, Delete, Escape, Tab and focus work"),
    ("search", "Search/domain/status filters preserve hidden kit choices and focus"),
    ("plugins", "Plugin host/selection/status labels update; research stays inert"),
    ("save", "Synthetic new kit JSON/log save succeeds; same-name overwrite refused"),
    ("import", "Valid synthetic kit import succeeds; changed pin is rejected unchanged"),
    ("readiness", "Inspect without originals shows blockers/UNKNOWN, no install"),
    ("budget", "Installed logical bytes only; missing/pending size never shown as zero"),
    ("a11y", "Contrast and screen-reader row/selection/status announcement checked"),
    ("no_side_effect", "No unintended software, registry/service/driver/network actions"),
)


class AcceptanceError(Exception):
    pass


def probe():
    """Static interpreter/source prerequisites only; NEVER instantiate Tk."""
    source = PICKER.read_bytes()
    ast.parse(source.decode("utf-8"), filename="toolkit_picker.py")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "PREREQUISITES_ONLY",
        "outcome": "NOT_VERIFIED",
        "pythonMajorMinor": "{}.{}".format(sys.version_info.major,
                                           sys.version_info.minor),
        "windows": os.name == "nt",
        "tkModuleFound": importlib.util.find_spec("tkinter") is not None,
        "pickerSha256": hashlib.sha256(source).hexdigest(),
        "notice": NOTICE,
    }


def answers_from_operator(emit, read=input):
    """Interactive, explicit per-case choice; no private notes or screenshots."""
    results = []
    for index, (ident, guidance) in enumerate(CHECKS, 1):
        emit("CHECK {}/{} [{}]: {}".format(index, len(CHECKS), ident, guidance))
        while True:
            emit("ENTER: P=pass observed, F=fail observed, S=skip/not verified")
            try:
                answer = read()
            except (EOFError, KeyboardInterrupt) as exc:
                raise AcceptanceError("Operator review interrupted; incomplete evidence log retained") from exc
            choice = str(answer).strip().upper()
            if choice in ("P", "F", "S"):
                status = {"P": "PASS", "F": "FAIL", "S": "SKIP"}[choice]
                emit("RECORDED: {} = {}".format(ident, status))
                results.append({"id": ident, "status": status})
                break
            emit("INVALID INPUT: enter P, F or S (no implicit PASS)")
    return results


def assess_results(results):
    """FAIL outranks SKIP; only all observed PASS is operator-reported pass."""
    if len(results) != len(CHECKS):
        raise AcceptanceError("Incomplete operator checklist")
    expected = [item[0] for item in CHECKS]
    if [item["id"] for item in results] != expected:
        raise AcceptanceError("Wrong/duplicate checklist item ordering")
    if any(item["status"] not in ("PASS", "FAIL", "SKIP") for item in results):
        raise AcceptanceError("Invalid checklist status")
    if any(item["status"] == "FAIL" for item in results):
        return "OPERATOR_REPORTED_FAIL"
    if any(item["status"] == "SKIP" for item in results):
        return "INCOMPLETE_NOT_VERIFIED"
    return "OPERATOR_REPORTED_PASS"


def summary_lines(report):
    """Single source of displayed evidence and report log."""
    lines = [
        "PICKER SHA256: " + report["pickerSha256"],
        "PYTHON: " + report["pythonMajorMinor"],
        "WINDOWS: " + str(report["windows"]),
        "TK MODULE FOUND: " + str(report["tkModuleFound"]),
    ]
    if report["mode"] == "PREREQUISITES_ONLY":
        lines.extend(["RESULT: NOT_VERIFIED (static prerequisites only)",
                      NOTICE, "NO GUI LAUNCHED / NO FILES WRITTEN"])
        return lines
    for row in report["checks"]:
        lines.append("RESULT {}: {}".format(row["id"], row["status"]))
    lines.extend([
        "REPORTED PASS: " + str(sum(x["status"] == "PASS" for x in report["checks"])),
        "REPORTED FAIL: " + str(sum(x["status"] == "FAIL" for x in report["checks"])),
        "NOT VERIFIED: " + str(sum(x["status"] == "SKIP" for x in report["checks"])),
        "RESULT: " + report["outcome"], NOTICE,
        "NO GUI/VENDOR LAUNCHED BY RECORDER / NO SYSTEM CHANGES",
    ])
    return lines


def verify_output(path):
    """Reject symlinks, existing output and log without touching them."""
    output = Path(path).absolute()
    if output.suffix.lower() != ".json":
        raise AcceptanceError("--out must be a new .json file")
    log = output.with_suffix(".log")
    kit.core.check_links(output)
    kit.core.check_links(log)
    if output == log or os.path.lexists(output) or os.path.lexists(log):
        raise AcceptanceError("JSON or log already exists; refusing overwrite")
    return output, log


def review(path, read=input):
    """Writes only user-requested new JSON and mirrored local evidence log."""
    output, log = verify_output(path)
    baseline = probe()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Open the evidence log BEFORE prompting to preserve interrupted sessions.
    with kit.sets.Evidence(log) as evidence:
        evidence.emit("MODE: EXPLICIT HUMAN REVIEW (no automatic GUI launch)")
        evidence.emit("Only use synthetic/nonproduction examples; keep output PRIVATE.")
        evidence.emit("PICKER SHA256: " + baseline["pickerSha256"])
        choices = answers_from_operator(evidence.emit, read=read)
        result = assess_results(choices)
        report = dict(baseline, mode="HUMAN_SELF_REPORT",
                      outcome=result, checks=choices,
                      observedUtc=datetime.now(timezone.utc).isoformat())
        try:
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except BaseException:
            if output.exists():
                output.unlink()
            raise
        for line in summary_lines(report):
            evidence.emit(line)
        evidence.emit("REPORT: " + str(output))
    return 1 if result == "OPERATOR_REPORTED_FAIL" else (
        2 if result == "INCOMPLETE_NOT_VERIFIED" else 0)


def run(argv=None):
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument("--review", action="store_true",
                   help="explicit interactive checklist; does NOT start GUI")
    p.add_argument("--out", help="new local JSON plus exact program console log; review requires it")
    args = p.parse_args(argv)
    try:
        if args.review:
            if not args.out:
                raise AcceptanceError("--review requires --out for durable local evidence")
            return review(args.out)
        if args.out:
            raise AcceptanceError("Use --review --out for interactive evidence")
        for line in summary_lines(probe()):
            print(line)
        return 0  # Only static syntax/readiness, NEVER human GUI PASS.
    except (AcceptanceError, kit.core.PortakitError, kit.KitError,
            OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
