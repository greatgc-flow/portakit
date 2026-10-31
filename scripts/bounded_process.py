"""Bounded direct-child subprocess capture for PortaKit's own core installer.

Only the caller decides which executable is permitted. This module is NOT
sandboxing: it kills the direct process only, not descendants/process trees,
and it does not cap child CPU, private memory, network or filesystem writes.

Two concurrent reader threads prevent the stdout/stderr pipe deadlock. Each
pipe retains at most MAX_CAPTURE + 1 bytes and an overflow fails closed.
Compatible with Windows Python 3.11+ using only the standard library.
"""
import os
import subprocess
import threading


MAX_CAPTURE = 256 * 1024
DEFAULT_TIMEOUT = 600
MAX_TIMEOUT = 3600


class BoundedProcessError(Exception):
    """Timeout, pipe read failure, or exceeded capture bound."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def run_bounded(argv, *, timeout_seconds=DEFAULT_TIMEOUT,
                max_capture_bytes=MAX_CAPTURE):
    """Execute a predetermined argv array without shell or inherited stdin.

    Args:
        argv: Exact non-shell child command. Caller owns validation/permission.
        timeout_seconds: Positive int 1..3600; default 600s per installed tool.
        max_capture_bytes: Positive int (<= 1MiB), per stdout and stderr;
                           default 256KiB. Overflow is an explicit failure.

    Returns:
        subprocess.CompletedProcess with UTF-8 replacement-decoded streams.

    Raises:
        OSError: Process creation failure.
        ValueError: Invalid invocation or limits.
        BoundedProcessError: TIMEOUT, OUTPUT_LIMIT, RUNTIME_ERROR.

    An error is never interpreted as a completed install, even when the child
    wrote a successful-looking JSON prefix. Previously completed tools are
    not rolled back by a batch caller.
    """
    if (not isinstance(argv, (list, tuple)) or not argv or
            any(not isinstance(arg, str) or not arg for arg in argv)):
        raise ValueError("Expected nonempty argv string list")
    if (type(timeout_seconds) is not int or
            not 1 <= timeout_seconds <= MAX_TIMEOUT):
        raise ValueError("Child timeout must be an integer in 1..3600 seconds")
    if (type(max_capture_bytes) is not int or
            not 1 <= max_capture_bytes <= 1024 * 1024):
        raise ValueError("Child output cap must be an integer in 1..1048576 bytes")

    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=False)
    output = [bytearray(), bytearray()]
    overflow = threading.Event()
    pipe_failure = threading.Event()
    threads = []

    def capture(pipe, buffer):
        try:
            while True:
                block = os.read(pipe.fileno(), 8192)
                if not block:
                    break
                available = max_capture_bytes + 1 - len(buffer)
                if available > 0:
                    buffer.extend(block[:available])
                if len(buffer) > max_capture_bytes:
                    overflow.set()
                    try:
                        child.kill()
                    except OSError:
                        pass
                    break
        except (OSError, ValueError):
            pipe_failure.set()
            try:
                child.kill()
            except OSError:
                pass
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    failure = None
    try:
        for stream, buffer in zip((child.stdout, child.stderr), output):
            worker = threading.Thread(target=capture, args=(stream, buffer),
                                      daemon=True)
            threads.append(worker)
            worker.start()
        try:
            child.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            failure = "TIMEOUT"
            try:
                child.kill()
            except OSError:
                pass
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                failure = "RUNTIME_ERROR"
        except OSError:
            failure = "RUNTIME_ERROR"
            try:
                child.kill()
            except OSError:
                pass
        for worker in threads:
            worker.join(timeout=2)
        if any(worker.is_alive() for worker in threads):
            pipe_failure.set()  # Descendant may still hold an inherited pipe.
    finally:
        if child.poll() is None:
            try:
                child.kill()
                child.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
        for pipe in (child.stdout, child.stderr):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass

    if overflow.is_set():
        raise BoundedProcessError("OUTPUT_LIMIT")
    if pipe_failure.is_set():
        raise BoundedProcessError("RUNTIME_ERROR")
    if failure is not None:
        raise BoundedProcessError(failure)
    return subprocess.CompletedProcess(
        argv, child.returncode,
        output[0].decode("utf-8", errors="replace"),
        output[1].decode("utf-8", errors="replace"))
