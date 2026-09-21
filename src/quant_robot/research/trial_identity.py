"""Execution provenance for exported trials; it does not certify search-history coverage."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import pandas as pd


TRIAL_IDENTITY_FIELDS = ("experiment_fingerprint", "trial_id", "trial_identity_schema_version")


def _valid_fingerprint(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def bind_experiment_trial_ids(rows: list[dict[str, Any]], fingerprint: str) -> list[dict[str, Any]]:
    """Bind a local case label to the complete recorded execution context."""
    if not _valid_fingerprint(fingerprint):
        raise ValueError("Invalid experiment fingerprint")
    bound = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str) or not row["case_id"].strip():
            raise ValueError("Trial identity requires a nonempty case_id")
        payload = {"schema_version": 1, "experiment_fingerprint": fingerprint, "case_id": row["case_id"]}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        identity = {"experiment_fingerprint": fingerprint, "trial_id": digest, "trial_identity_schema_version": 1}
        if any(key in row and row[key] != value for key, value in identity.items()):
            raise ValueError("Recorded trial identity does not match its experiment fingerprint and case_id")
        bound.append({**row, **identity})
    return bound


def statistical_inference_scope(experiments: pd.DataFrame, case_column: str) -> dict[str, Any]:
    scope = {
        "basis": "provided experiment rows",
        "case_column": case_column,
        "experiment_fingerprint_count": None,
        "complete_research_history_verified": False,
        "identity_semantics": "Execution context identity; independent hypotheses and full search coverage need separate review.",
    }
    if "trial_identity_schema_version" in experiments.columns:
        required = ["case_id", *TRIAL_IDENTITY_FIELDS]
        if not set(required).issubset(experiments.columns) or experiments[required].isna().any().any():
            raise ValueError("Declared trial identity is incomplete")
        for row in experiments[required].drop_duplicates().to_dict("records"):
            bind_experiment_trial_ids([row], row["experiment_fingerprint"])
    if "experiment_fingerprint" not in experiments.columns:
        return scope
    fingerprints = experiments["experiment_fingerprint"]
    if not all(_valid_fingerprint(value) for value in fingerprints):
        raise ValueError("Missing or invalid experiment fingerprint in statistical input")
    if not experiments.empty:
        if case_column not in experiments.columns or not all(
            isinstance(value, str) and value.strip() for value in experiments[case_column]
        ):
            raise ValueError("Experiment fingerprint requires an explicit nonempty case identity column")
        if (experiments.groupby(case_column)["experiment_fingerprint"].nunique() > 1).any():
            raise ValueError(
                f"{case_column} spans multiple experiment fingerprints; select the qualified trial_id column"
            )
    scope["experiment_fingerprint_count"] = int(fingerprints.nunique())
    return scope
