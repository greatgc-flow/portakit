# portakit — SPEC (unanimous: cc, cx, ag; rounds 1-2)
Windows CLI, Python 3.11+ stdlib only, single module `portakit.py` + `catalog.json`. No JSON schemas.
Commands: `list | install ID | update ID | remove ID`, global `--json`, `--root DIR`.
MVP tools: notepad++, winmerge, jq (jq = standalone exe, so artifacts: zip OR single exe).
## Order (amended by round 2)
1. Catalog load; error names the bad field; reject dest escaping root.
2. JSON envelope + exit-code table (defined EARLY, before features).
3. Download -> SHA256 verify BEFORE extract (mismatch: abort, nothing installed); cache keyed consistently.
4. Safe extract: zip-slip/absolute/reparse rejected; single-root flatten; exe artifact copy.
5. Install: staging dir; swap via two-phase rename (`dir.old` -> swap -> delete; restore on failure; handle Windows PermissionError); state written only after success.
6. Update: preserveOnUpdate paths; forced failure rolls back.
7. Remove: only managed dir + state entry.
8. github plugin kind + defaultConfig presets.
## Acceptance
Runs under `python -I`; malformed catalog -> named field; zip-slip -> zero files; bad SHA -> nothing installed; failed install/update leaves previous state; remove touches only managed dir; `--json` parses; `portakit install jq` then `jq.exe --version` works.
## Not ported (known bugs in v4.1 draft)
offline get-pip fetch; unverified cache; cache-key mismatch; catalog `../` dests. Deferred: offline bundle, doctor, pip tools, url kind, shims.
