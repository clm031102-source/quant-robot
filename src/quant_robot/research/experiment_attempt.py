"""Prospective execution evidence, separate from statistical hypothesis counts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from uuid import uuid4

from quant_robot.research.trial_identity import bind_experiment_trial_ids
from quant_robot.storage.atomic import atomic_write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperimentAttemptRecorder:
    """Record a cache-miss grid before factor computation; no historical backfill.

    An ungraceful process termination leaves the last durable running state.
    That state is unfinished/unknown, never proof of successful completion.
    Without an output directory, this object only tracks in-memory progress.
    """

    def __init__(self, output_dir: Path | None, reproducibility: dict, config: dict, case_ids: list[str]):
        self.directory = None
        attempt_id = uuid4().hex
        fingerprint = reproducibility["fingerprint"]
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("Experiment attempt requires unique planned case identities")
        self.state = {"schema_version": 1, "attempt_id": attempt_id,
            "experiment_fingerprint": fingerprint, "started_at": _now(),
            "status": "running", "phase": "precompute", "planned_cases": len(case_ids),
            "started_cases": 0, "finished_cases": 0, "active_case_id": None,
            "result_status_counts": {}, "complete_research_history_verified": False,
            "attempt_is_independent_hypothesis": False}
        self.plan = {"schema_version": 1, "attempt_id": attempt_id,
            "config": config, "reproducibility": reproducibility,
            "ordered_trials": bind_experiment_trial_ids([{"case_id": case_id} for case_id in case_ids], fingerprint)}
        if output_dir is not None:
            self.directory = Path(output_dir) / "attempts" / attempt_id

    def __enter__(self):
        if self.directory is not None:
            self.directory.mkdir(parents=True, exist_ok=False)
            plan_path = self.directory / "plan.json"
            atomic_write_json(plan_path, self.plan)
            self.state["plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
            self._save()
        return self

    def _save(self):
        if self.directory is not None:
            atomic_write_json(self.directory / "attempt.json", self.state)

    def start_case(self, case_id: str):
        self.state.update(phase="cases", active_case_id=case_id)
        self.state["started_cases"] += 1
        self._save()

    def finish_case(self, result_status: str):
        self.state["finished_cases"] += 1
        counts = self.state["result_status_counts"]
        counts[result_status] = counts.get(result_status, 0) + 1
        self.state["active_case_id"] = None
        self._save()

    def set_phase(self, phase: str):
        self.state["phase"] = phase
        self._save()

    def complete(self):
        self.state.update(status="completed", phase="complete", finished_at=_now())
        self._save()

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self.state.update(status="failed" if issubclass(exc_type, Exception) else "interrupted",
                failure_kind=exc_type.__name__, finished_at=_now())
            # Exception messages may contain provider/account details. Store type only.
            self._save()
        return False
