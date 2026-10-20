"""Package local Office acceptance evidence with SHA-256 provenance (Python 3.11+ stdlib).

This only reads a user-created disposable evidence folder, then writes a new ZIP
and separate checksum file. It never uploads evidence or overwrites output.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import zipfile


def refuse_reparse(path):
    """Reject symlink, junction and other Windows reparse points."""
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    if path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("Reparse/symlink path rejected: " + str(path))


def digest_file(path):
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(128 * 1024)
            if not chunk:
                break
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), size


def package_evidence(evidence, target, status):
    evidence = Path(evidence).absolute()
    target = Path(target).absolute()
    checksum = target.with_name(target.name + ".sha256.txt")
    if not evidence.is_dir():
        raise ValueError("EvidenceDir must exist and be a directory")
    if status not in (0, 1, 2):
        raise ValueError("Only exit status 0, 1 or 2 is valid")
    for item in (target, checksum):
        if os.path.lexists(item):
            raise FileExistsError("Refusing to overwrite existing file: " + str(item))
    refuse_reparse(evidence)
    for parent in evidence.parents:
        if parent.exists():
            refuse_reparse(parent)
    records = []
    for current, dirs, files in os.walk(str(evidence), followlinks=False):
        here = Path(current)
        refuse_reparse(here)
        for name in dirs:
            refuse_reparse(here / name)
        for name in files:
            src = here / name
            refuse_reparse(src)
            if not src.is_file():
                raise ValueError("Unexpected non-file in evidence: " + str(src))
            relative = src.relative_to(evidence).as_posix()
            if relative.casefold() == "manifest.json":
                raise ValueError("EvidenceDir already has manifest.json; use a fresh folder")
            sha, size = digest_file(src)
            records.append((relative, src, sha, size))
    records.sort(key=lambda x: x[0])
    if not records:
        raise ValueError("EvidenceDir contains no files")
    summary = {0: "PASS", 1: "FAIL", 2: "NOT_VERIFIED"}[status]
    manifest = {
        "format": "portakit-office-evidence-v1",
        "office_runtime": summary,
        "script_exit_code": status,
        "note": "PASS requires semantic Office reports; NOT_VERIFIED is not a pass",
        "files": [{"path": p, "size": size, "sha256": sha}
                  for p, _, sha, size in records],
    }
    # ZIP and checksum sit next to (not within) EvidenceDir.
    target.parent.mkdir(parents=True, exist_ok=True)
    created_zip = False
    created_checksum = False
    try:
        with target.open("xb") as binary:
            created_zip = True
            with zipfile.ZipFile(binary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, src, _, _ in records:
                    archive.write(src, arcname=name)
                archive.writestr("manifest.json", json.dumps(
                    manifest, ensure_ascii=True, indent=2) + "\n")
        sha, _ = digest_file(target)
        with checksum.open("x", encoding="utf-8") as text:
            created_checksum = True
            text.write(sha + "  " + target.name + "\n")
    except BaseException:
        # Clean ONLY paths successfully created by this process. In particular,
        # never delete another process's ZIP after an exclusive-create race.
        for item, owned in ((checksum, created_checksum), (target, created_zip)):
            if owned and item.exists():
                item.unlink()
        raise
    return {"zip": str(target), "sha256": sha, "checksum": str(checksum),
            "files": len(records), "runtime": summary}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--zip", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    args = parser.parse_args(argv)
    result = package_evidence(args.evidence, args.zip, args.exit_code)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
