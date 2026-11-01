"""One create-only JSON report and exactly mirrored operator transcript.

This is a small shared write boundary, not a generic reporting framework.
The caller owns the report schema, displayed text, extension policy, and its
public error message. Default read-only reporting is handled by each caller.

On failure, remove only files created by THIS operation when their identities
are still known to match. This is best-effort cleanup, NOT an atomic pair
commit or protection against malicious filesystem concurrency.
"""
import json
import os
from pathlib import Path

import my_toolkit as kit


def emit_json_report(report, lines, output, *, error_type, collision_message):
    """Write a new JSON report and .log, never overwrite existing evidence.

    Preconditions:
    - The caller has validated any required suffix (if applicable).
    - lines is the already rendered, ordered console text.
    - No vendor tool or installer is executed by this function.

    Postconditions on success:
    - The JSON has stable indent/UTF-8 encoding and a final LF.
    - Console output is identical to the new .log file, including REPORT.
    Failure is propagated; owned outputs are removed only if unchanged by
    competing writers. Output directories may remain after a failed attempt.
    """
    target = Path(output).absolute()
    log = target.with_suffix(".log")
    kit.core.check_links(target)
    kit.core.check_links(log)
    if target == log or os.path.lexists(target) or os.path.lexists(log):
        raise error_type(collision_message)

    target.parent.mkdir(parents=True, exist_ok=True)
    # Parent creation can change path identities; validate again before open.
    kit.core.check_links(target)
    kit.core.check_links(log)

    json_identity = log_identity = None
    try:
        with kit.sets.Evidence(log) as transcript:
            log_identity = kit.sets.created_output_identity(
                os.fstat(transcript.stream.fileno()))
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json_identity = kit.sets.created_output_identity(
                    os.fstat(stream.fileno()))
                json.dump(report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            for line in lines:
                transcript.emit(line)
            transcript.emit("REPORT: " + str(target))
    except BaseException:
        kit.sets.cleanup_own_output(log, log_identity)
        kit.sets.cleanup_own_output(target, json_identity)
        raise
