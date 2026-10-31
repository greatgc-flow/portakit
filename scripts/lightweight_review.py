"""Read-only, offline triage of three lightweight PortaKit research candidates.

Uses source-only, dated public release metadata. Never downloads, executes,
installs, or certifies vendor binaries or corporate licensing/EDR approval.
Research-only is invariant; not a pathway to auto-promotion into catalog.json.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import my_toolkit as kit  # noqa: E402

LEDGER = HERE / "research" / "LIGHTWEIGHT_CANDIDATES_20261031.json"
EXTRACTOR_FORMATS = frozenset(("zip", "exe", "sfx7z"))
NOTICE = ("RESEARCH ONLY: release metadata is not a locally verified file, "
          "publisher signature, enterprise license/transfer/EDR approval, "
          "offline runtime smoke, or permission to install.")


class ResearchError(Exception):
    pass


def _https(value):
    if not isinstance(value, str) or any(ch.isspace() for ch in value):
        return False
    parts = urlsplit(value)
    return parts.scheme == "https" and bool(parts.netloc)


def load_ledger(path=LEDGER):
    """Validate the checked-in research snapshot against current canonical IDs."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ResearchError("Cannot read candidate ledger: " + str(exc)) from exc
    if not isinstance(data, dict) or type(data.get("schemaVersion")) is not int or (
            data["schemaVersion"] != 1):
        raise ResearchError("Unsupported candidate ledger schema")
    rows = data.get("candidates")
    gates = data.get("requiredIndependentGates")
    if (not isinstance(rows, list) or not rows or len(rows) > 30 or
            not isinstance(gates, list) or len(gates) != 8 or
            any(not isinstance(g, str) or not g for g in gates) or
            len(set(gates)) != len(gates) or
            data.get("admissionDecision") != "RESEARCH_ONLY_NOT_INSTALLABLE"):
        raise ResearchError("Invalid research candidate scope or gates")
    pins, _, _, known = kit.inventory()
    seen = set()
    fields = ("id", "primary", "stage", "repoURL", "repoArchived",
              "licenseReported", "releaseTag", "publishedAt", "releaseURL",
              "assetName", "assetURL", "assetBytesFromMetadata",
              "sha256FromReleaseMetadata", "artifactType", "target",
              "runtimeRequirement", "functionalGate", "sources")
    for item in rows:
        if not isinstance(item, dict) or any(k not in item for k in fields):
            raise ResearchError("Incomplete candidate record")
        ident = item["id"]
        if (not isinstance(ident, str) or ident in seen or ident in pins or
                ident not in known or known[ident]["admission"] != "RESEARCH_ONLY" or
                item["stage"] != "RESEARCH_ONLY" or
                item["primary"] != known[ident]["primary"]):
            raise ResearchError("Candidate admission/taxonomy changed: " + str(ident))
        seen.add(ident)
        if type(item["repoArchived"]) is not bool:
            raise ResearchError("Invalid archived flag: " + ident)
        if (type(item["assetBytesFromMetadata"]) is not int or
                item["assetBytesFromMetadata"] <= 0):
            raise ResearchError("Missing positive release asset size: " + ident)
        digest = item["sha256FromReleaseMetadata"]
        if digest is not None and (not isinstance(digest, str) or
                                   re.fullmatch(r"[a-f0-9]{64}", digest) is None):
            raise ResearchError("Invalid release metadata SHA: " + ident)
        if item["artifactType"] not in ("zip", "tar.gz", "exe", "sfx7z"):
            raise ResearchError("Unknown source archive type: " + ident)
        suffix = ".tar.gz" if item["artifactType"] == "tar.gz" else (
            "." + item["artifactType"])
        if (not isinstance(item["assetName"], str) or
                not item["assetName"].endswith(suffix) or
                not isinstance(item["releaseTag"], str) or
                not item["releaseTag"] or
                not item["assetURL"].endswith("/" + item["assetName"]) or
                "/download/" + item["releaseTag"] + "/" not in item["assetURL"]):
            raise ResearchError("Release URL/asset mismatch: " + ident)
        if any(not _https(item[k]) for k in ("repoURL", "releaseURL", "assetURL")):
            raise ResearchError("Non-HTTPS vendor reference: " + ident)
        sources = item["sources"]
        if not isinstance(sources, list) or not sources or not all(
                _https(s) for s in sources):
            raise ResearchError("Missing official source references: " + ident)
        for key in ("licenseReported", "publishedAt", "target",
                    "runtimeRequirement", "functionalGate"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ResearchError("Invalid candidate field: " + ident + "/" + key)
    return data


def assess(data, ids=None):
    """Produce a deterministic CHECKLIST, never an installation approval."""
    entries = {row["id"]: row for row in data["candidates"]}
    if ids is None:
        chosen = sorted(entries)
    elif not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        raise ResearchError("Tool IDs must be a list of strings")
    else:
        chosen = list(dict.fromkeys(ids))
    if not chosen:
        raise ResearchError("Select at least one candidate")
    if any(i not in entries for i in chosen):
        raise ResearchError("Unknown candidate ID: " +
                            ", ".join(i for i in chosen if i not in entries))
    results = []
    for ident in chosen:
        rec = entries[ident]
        blockers = list(data["requiredIndependentGates"])
        if rec["sha256FromReleaseMetadata"] is None:
            blockers.append("vendorReleaseDidNotPublishSHA256InAPI")
        if rec["artifactType"] not in EXTRACTOR_FORMATS:
            blockers.append("currentCoreDoesNotAcceptArchiveType")
        if rec["repoArchived"]:
            blockers.append("upstreamArchivedMaintenanceDecision")
        results.append({
            "id": ident, "stage": "RESEARCH_ONLY", "asset": rec["assetName"],
            "version": rec["releaseTag"],
            "releaseSha256Metadata": rec["sha256FromReleaseMetadata"],
            "compressedBytesMetadata": rec["assetBytesFromMetadata"],
            "blockedBy": blockers, "status": "NOT_ADMITTED",
        })
    return {"schemaVersion": 1, "asOf": data["asOf"],
            "outcome": "RESEARCH_ONLY_NOT_INSTALLABLE", "tools": results,
            "notice": NOTICE}


def report_lines(report):
    rows = ["PORTAKIT LIGHTWEIGHT CANDIDATE REVIEW (READ ONLY)",
            "SNAPSHOT: " + report["asOf"]]
    for item in report["tools"]:
        rows.append(item["id"] + " / " + item["status"] +
                    " / " + item["version"] + " / " + item["asset"])
        rows.append("  OPEN GATES: " + ", ".join(item["blockedBy"]))
    rows.extend(["OVERALL: " + report["outcome"], NOTICE,
                 "NO DOWNLOAD / NO EXECUTION / NO INSTALL / NO CHANGES"])
    return rows


def emit(report, output=None):
    """No writes unless explicit --out; report JSON and exact stdout log are new-only."""
    lines = report_lines(report)
    if output is None:
        for line in lines:
            print(line)
        return
    target = Path(output).absolute()
    transcript = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(transcript)
    if target == transcript or os.path.lexists(target) or os.path.lexists(transcript):
        raise ResearchError("Report or console transcript already exists; no overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with kit.sets.Evidence(transcript) as evidence:
        try:
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except BaseException:
            if target.exists():
                target.unlink()
            raise
        for line in lines:
            evidence.emit(line)
        evidence.emit("REPORT: " + str(target))


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--id", action="append", help="candidate ID; repeatable (default all)")
    parser.add_argument("--out", help="optional new JSON plus exact local console log")
    args = parser.parse_args(argv)
    try:
        report = assess(load_ledger(), args.id)
        emit(report, args.out)
        return 2  # research-only: intentionally never exit success for install
    except (ResearchError, kit.KitError, kit.core.PortakitError,
            kit.sets.ToolsetError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
