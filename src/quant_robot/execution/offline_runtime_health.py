"""Same-host process evidence, separate from the synthetic market clock."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time

from quant_robot.storage.atomic import atomic_write_json


def seconds(value, name, *, maximum=300):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError(name + " must be finite, positive and at most " + str(maximum))
    return value


def journal_identity(path):
    path = Path(path).resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT event_hash FROM events WHERE sequence=1").fetchone()
        if row is None or not re.fullmatch(r"[0-9a-f]{64}", row[0]):
            raise ValueError("invalid journal genesis identity")
        return dict(journal_path=str(path), genesis_hash=row[0])
    finally:
        connection.close()


def ensure_distinct_paths(paths):
    resolved = [(name, Path(path).resolve()) for name, path in paths.items() if path is not None]
    for index, (name, path) in enumerate(resolved):
        for other_name, other in resolved[:index]:
            if path == other or (path.exists() and other.exists() and path.samefile(other)):
                raise ValueError(name + " must not replace or alias " + other_name)


def protected_paths(journal, feed):
    journal = Path(journal).resolve()
    return dict(journal=journal, feed=feed, driver_lease=str(journal)+".driver.lock",
        supervisor_lease=str(journal)+".supervisor.lock", sqlite_wal=str(journal)+"-wal", sqlite_shm=str(journal)+"-shm")


def health_record(role, *, instance_id, journal_path, genesis_hash, phase, process_id=None, monotonic_ns=None, **details):
    return dict(schema_version=1, mode="offline_fixture_only", executable=False, role=role,
        instance_id=instance_id, journal_path=journal_path, genesis_hash=genesis_hash,
        process_id=os.getpid() if process_id is None else process_id, phase=phase,
        updated_monotonic_ns=time.monotonic_ns() if monotonic_ns is None else monotonic_ns,
        updated_wall_utc=datetime.now(timezone.utc).isoformat(), **details)


def read_health(path):
    with Path(path).open("rb") as handle:
        payload = handle.read(65537)
    if len(payload) > 65536:
        raise ValueError("process evidence exceeds size limit")
    value = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("process evidence must be an object")
    return value


def validate_health(value, *, role, instance_id, journal_path, genesis_hash, process_id=None, now_ns=None, max_age_seconds):
    seconds(max_age_seconds, "health age")
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ValueError("invalid process evidence schema")
    if value.get("mode") != "offline_fixture_only" or value.get("executable") is not False or value.get("role") != role:
        raise ValueError("invalid process evidence role or scope")
    expected = dict(instance_id=instance_id, journal_path=journal_path, genesis_hash=genesis_hash)
    if process_id is not None:
        expected["process_id"] = process_id
    if any(value.get(key) != item for key, item in expected.items()):
        raise ValueError("process evidence identity mismatch")
    if type(value.get("process_id")) is not int or value["process_id"] <= 0:
        raise ValueError("invalid process identity")
    updated = value.get("updated_monotonic_ns")
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if type(updated) is not int or updated < 0 or updated > now_ns:
        raise ValueError("invalid or future process clock")
    if now_ns - updated > max_age_seconds * 1_000_000_000:
        raise ValueError("stale process evidence")
    return value


class SupervisorPermit:
    def __init__(self, path, *, max_age_seconds, monotonic_ns=time.monotonic_ns, **identity):
        self.path, self.identity = path, identity
        self.max_age = seconds(max_age_seconds, "supervisor age")
        self.monotonic_ns = monotonic_ns

    def __call__(self):
        value = validate_health(read_health(self.path), role="supervisor", **self.identity,
            max_age_seconds=self.max_age, now_ns=self.monotonic_ns())
        if value.get("phase") != "running":
            raise ValueError("supervisor is not running")


class WorkerHealth:
    def __init__(self, path, *, instance_id, journal_path, genesis_hash):
        self.path = path
        self.identity = dict(instance_id=instance_id, journal_path=journal_path, genesis_hash=genesis_hash)
        self.completed_ticks, self.last_tick_status = 0, None
        self.last_completed_ns = None

    def publish(self, phase, **details):
        value = health_record("worker", **self.identity, phase=phase, owns_journal=True,
            completed_ticks=self.completed_ticks, last_tick_status=self.last_tick_status,
            last_completed_monotonic_ns=self.last_completed_ns, **details)
        atomic_write_json(self.path, value)
        return value

    def start_tick(self):
        self.publish("ticking")

    def complete_tick(self, report):
        self.completed_ticks += 1
        self.last_tick_status = report["status"]
        self.last_completed_ns = time.monotonic_ns()
        self.publish("idle", market_observed_at=report["observed_at"])
