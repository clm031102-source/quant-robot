"""Monitor a child process owned by this supervisor; never auto-restart it."""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

from quant_robot.storage.atomic import atomic_write_json
from .offline_journal import OfflineOrderJournal
from .offline_runtime import validate_loop_limits
from .offline_runtime_health import (
    ensure_distinct_paths, health_record, journal_identity, protected_paths, read_health, seconds, validate_health,
)
from .offline_runtime_lease import RuntimeLease


def launch_owned_python(arguments, **options):
    """Keep the Popen handle on the interpreter, bypassing Windows venv redirectors."""
    defaults = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    defaults.update(options)
    if os.name == "nt" and sys.prefix != sys.base_prefix:
        import ctypes
        from ctypes import wintypes
        get_module = ctypes.WinDLL("kernel32", use_last_error=True).GetModuleFileNameW
        get_module.argtypes = (wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD)
        get_module.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        size = get_module(None, buffer, len(buffer))
        if not size or size >= len(buffer):
            raise ctypes.WinError(ctypes.get_last_error())
        base = buffer.value
        if not Path(base).is_file():
            raise ValueError("cannot identify the direct virtual-environment interpreter")
        environment = dict(os.environ if defaults.get("env") is None else defaults["env"])
        environment["__PYVENV_LAUNCHER__"] = sys.executable
        defaults.update(executable=base, env=environment)
    return subprocess.Popen([sys.executable, *arguments], **defaults)


def validate_supervisor_limits(interval_seconds, poll_seconds, startup_seconds, stall_seconds):
    validate_loop_limits(interval_seconds, None)
    seconds(poll_seconds, "poll interval", maximum=10)
    seconds(startup_seconds, "startup deadline")
    seconds(stall_seconds, "stall deadline")
    if stall_seconds <= interval_seconds + 2 * poll_seconds:
        raise ValueError("stall deadline must exceed the runtime interval plus two polls")


def assess_worker(value, *, previous_ticks=0, **binding):
    value = validate_health(value, role="worker", **binding)
    if value.get("owns_journal") is not True or value.get("phase") not in {"starting", "ticking", "idle", "stopped", "failed"}:
        raise ValueError("invalid worker phase or ownership evidence")
    count = value.get("completed_ticks")
    if type(count) is not int or count < 0:
        raise ValueError("invalid completed tick count")
    if count < previous_ticks:
        raise ValueError("completed tick count regressed")
    completed = value.get("last_completed_monotonic_ns")
    if count and (type(completed) is not int or not 0 <= completed <= value["updated_monotonic_ns"]):
        raise ValueError("invalid tick completion time")
    if (not count and completed is not None) or value.get("last_tick_status") not in {None, "ready", "attention"}:
        raise ValueError("invalid last tick evidence")
    return value


def _owns(value, identity, pid):
    return (isinstance(value, dict) and value.get("role") == "worker" and value.get("mode") == "offline_fixture_only"
        and value.get("executable") is False and value.get("owns_journal") is True
        and type(value.get("process_id")) is int and value["process_id"] == pid
        and all(value.get(key) == item for key, item in identity.items()))


def _stop_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
    return child.poll()


def _latch(journal, expected_genesis, reason):
    try:
        # The worker has exited. Never recover through another driver's ownership.
        with RuntimeLease(journal):
            if journal_identity(journal)["genesis_hash"] != expected_genesis:
                raise ValueError("journal was replaced; refusing to mutate another journal")
            with OfflineOrderJournal(journal) as book:
                book.note_runtime_supervision_fault(reason)
                state = book.snapshot()
                return dict(status="latched", paused=state["paused"], journal_sequence=state["sequence"])
    except (OSError, ValueError, sqlite3.Error) as exc:
        return dict(status="failed", reason=str(exc)[:500])


def supervise_worker(journal_path, *, health_path, permit_path, report_path, launch,
        interval_seconds=1, poll_seconds=.25, startup_seconds=10, stall_seconds=5, on_observation=None):
    """Launch returns a Popen handle for the one child we may stop.

    The callable receives a fresh binding; the production CLI constructs a fixed
    Python entrypoint argument list. It is also a seam for real faulting test children.
    """
    validate_supervisor_limits(interval_seconds, poll_seconds, startup_seconds, stall_seconds)
    journal = Path(journal_path).resolve()
    ensure_distinct_paths({**protected_paths(journal, None), "health": health_path, "permit": permit_path, "report": report_path})
    with RuntimeLease(journal, role="supervisor"):
        probe = RuntimeLease(journal)
        probe.close()
        identity = dict(instance_id=uuid4().hex, **journal_identity(journal))
        binding = dict(**identity, supervisor_pid=os.getpid(), health_path=str(Path(health_path).resolve()),
            permit_path=str(Path(permit_path).resolve()), max_age_seconds=stall_seconds)
        child, latest, owned, previous_ticks = None, None, False, 0
        failure, report_error, latch = None, None, dict(status="not_needed")
        started = progress_at = time.monotonic()
        progress_seen = False

        def permit(phase):
            atomic_write_json(permit_path, health_record("supervisor", **identity, phase=phase))

        def output(phase):
            record = health_record("supervisor", **identity, phase=phase,
                status="attention" if failure or (latest or {}).get("last_tick_status") == "attention" else phase,
                child_pid=child.pid if child else None, child_returncode=child.poll() if child else None,
                child_alive=child is not None and child.poll() is None, owner_observed=owned,
                completed_ticks=previous_ticks, last_worker_phase=(latest or {}).get("phase"),
                last_tick_status=(latest or {}).get("last_tick_status"), failure=failure, pause_enforcement=latch,
                counts_as_forward_paper_days=0, qualifies_for_strategy_promotion=False)
            atomic_write_json(report_path, record)
            return record

        try:
            permit("running")
            child = launch(binding)
            while True:
                permit("running")
                code = child.poll()
                now = time.monotonic()
                try:
                    value = read_health(health_path)
                    matches = _owns(value, identity, child.pid)
                    owned = owned or matches
                    if not matches:
                        raise ValueError("worker identity or ownership mismatch")
                    latest = assess_worker(value, **identity, process_id=child.pid, previous_ticks=previous_ticks,
                        max_age_seconds=stall_seconds)
                    if not progress_seen or latest["completed_ticks"] > previous_ticks:
                        progress_at = now
                    progress_seen = True
                    previous_ticks = latest["completed_ticks"]
                except (OSError, ValueError, UnicodeError) as exc:
                    if owned:
                        raise ValueError("worker health rejected: " + str(exc)) from exc
                    latest = None
                if code is not None:
                    if code == 0 and latest is not None and latest["phase"] == "stopped":
                        break
                    raise ValueError("worker exited without verified clean stop: " + str(code))
                if latest is None:
                    if now - started > startup_seconds:
                        raise ValueError("worker startup deadline exceeded")
                else:
                    if latest["phase"] == "failed":
                        raise ValueError("worker reported failure")
                    if now - progress_at > stall_seconds:
                        raise ValueError("completed tick progress deadline exceeded")
                phase = "starting" if latest is None else "stopping" if latest["phase"] == "stopped" else "running"
                observation = output(phase)
                if on_observation is not None:
                    on_observation(observation)
                time.sleep(poll_seconds)
        except BaseException as exc:
            failure = type(exc).__name__ + ": " + str(exc)[:450]
            if child is not None:
                try:
                    _stop_child(child)
                except (OSError, subprocess.TimeoutExpired) as stop_error:
                    failure += "; termination failed: " + str(stop_error)[:200]
                try:
                    owned = owned or _owns(read_health(health_path), identity, child.pid)
                except (OSError, ValueError, UnicodeError):
                    pass
                if owned and child.poll() is not None:
                    latch = _latch(journal, identity["genesis_hash"], failure)
                else:
                    latch = dict(status="not_attempted", reason="owned worker exit not verified")
        phase = "failed" if failure else "stopped"
        try:
            permit(phase)
        except OSError as exc:
            report_error = str(exc)[:500]
        try:
            result = output(phase)
        except OSError as exc:
            result = dict(status="attention", phase=phase, failure=failure, pause_enforcement=latch,
                child_alive=child is not None and child.poll() is None, executable=False, counts_as_forward_paper_days=0)
            report_error = str(exc)[:500]
        if report_error:
            result.update(status="attention", evidence_write_error=report_error)
        return result
