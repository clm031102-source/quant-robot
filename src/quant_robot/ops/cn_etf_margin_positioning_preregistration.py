from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any, Mapping

from quant_robot.storage.atomic import atomic_write_json, atomic_write_text


STAGE = "cn_etf_margin_positioning_preregistration"
STATUS_READY = "preregistered_single_prescreen"
SOURCE_BOUNDARIES = (
    "factor_generation_allowed",
    "forward_return_read",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)
BOUNDARY_FIELDS = (
    "forward_return_read_allowed",
    "factor_generation_allowed",
    "prescreen_execution_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
    "live_boundary_allowed",
)
FACTOR_NAME = "etf_residual_margin_financing_growth_reversal_20"
SAFETY = (
    "Research-to-paper only. One authorization-bound prescreen; no portfolio "
    "grid, walk-forward, final holdout, paper signal, broker, account, order, "
    "or live trading."
)


def build_cn_etf_margin_positioning_preregistration(
    *,
    config: Mapping[str, Any],
    source_readiness: Mapping[str, Any],
    evidence_hashes: Mapping[str, str],
    config_sha256: str,
) -> dict[str, Any]:
    blockers = _blockers(
        config=config,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
        config_sha256=config_sha256,
    )
    candidate = dict(config.get("candidate", {}))
    evaluation = dict(config.get("evaluation", {}))
    result: dict[str, Any] = {
        "stage": STAGE,
        "registration_date": config.get("registration_date"),
        "status": "blocked" if blockers else STATUS_READY,
        "primary_market": config.get("primary_market"),
        "research_family": config.get("research_family"),
        "configuration": {"sha256": config_sha256},
        "source_evidence": {
            "required_status": config.get("source_evidence", {}).get("required_status"),
            "expected_hashes": dict(config.get("source_evidence", {}).get("hashes", {})),
            "actual_hashes": dict(evidence_hashes),
            "source_stage": source_readiness.get("stage"),
            "source_status": source_readiness.get("status"),
        },
        "candidate": candidate,
        "candidates": [candidate] if candidate else [],
        "summary": {
            "candidate_count": 1 if candidate else 0,
            "hypothesis_count": len(evaluation.get("horizons", []) or []),
            "primary_horizon": evaluation.get("primary_horizon"),
            "diagnostic_horizon": evaluation.get("diagnostic_horizon"),
            "blockers": blockers,
        },
        "evaluation": evaluation,
        "reference_policy": dict(config.get("reference_policy", {})),
        "capacity": dict(config.get("capacity", {})),
        "costs": dict(config.get("costs", {})),
        "stop_policy": dict(config.get("stop_policy", {})),
        "data_boundary": dict(config.get("data_boundary", {})),
        "claim_policy": {
            "alpha_claim_allowed": False,
            "profitability_claim_allowed": False,
            "source_readiness_is_promotion_evidence": False,
        },
        "next_direction": "run_one_hash_bound_margin_positioning_prescreen",
        "safety": SAFETY,
    }
    for field in BOUNDARY_FIELDS:
        result[field] = False
    result["markdown"] = render_cn_etf_margin_positioning_preregistration(result)
    return result


def write_cn_etf_margin_positioning_preregistration(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / f"{STAGE}.json",
        "markdown": output / f"{STAGE}.md",
        "candidate_csv": output / "candidate.csv",
    }
    atomic_write_json(paths["json"], _sanitize(result))
    atomic_write_text(paths["markdown"], render_cn_etf_margin_positioning_preregistration(result))
    atomic_write_text(paths["candidate_csv"], _candidate_csv(result))
    return paths


def render_cn_etf_margin_positioning_preregistration(
    result: Mapping[str, Any],
) -> str:
    candidate = result.get("candidate", {})
    summary = result.get("summary", {})
    return "\n".join(
        [
            "# CN ETF Margin-Positioning Preregistration",
            "",
            f"- Status: {result.get('status', 'blocked')}",
            f"- Candidate: {candidate.get('factor_name', '')}",
            f"- Direction: {candidate.get('direction', '')}",
            f"- Primary horizon: {summary.get('primary_horizon', '')}",
            f"- Diagnostic horizon: {summary.get('diagnostic_horizon', '')}",
            f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
            "",
            "## Governance",
            "",
            "- Margin observations join only on audited next-session availability.",
            "- Gap-crossing factor and label windows are excluded.",
            "- No factor or forward return is calculated by this packet.",
            "- The diagnostic cannot rescue a failed primary.",
            "- Exactly one hash-bound execution authorization is required.",
            f"- Safety: {result.get('safety', SAFETY)}",
            "",
        ]
    )


def _blockers(
    *,
    config: Mapping[str, Any],
    source_readiness: Mapping[str, Any],
    evidence_hashes: Mapping[str, str],
    config_sha256: str,
) -> list[str]:
    blockers: list[str] = []
    source = config.get("source_evidence", {})
    if source_readiness.get("status") != source.get("required_status"):
        blockers.append("margin_positioning_source_not_ready")
    if (
        source_readiness.get("gate", {}).get("cleared") is not True
        or source_readiness.get("gate", {}).get("blockers", [])
    ):
        blockers.append("margin_positioning_source_gate_not_cleared")
    for field in SOURCE_BOUNDARIES:
        if source_readiness.get(field) is not False:
            blockers.append(f"source_boundary_not_false:{field}")
    expected = source.get("hashes", {})
    if set(expected) != set(evidence_hashes):
        blockers.append("source_evidence_hash_key_set_mismatch")
    for key in sorted(expected):
        if evidence_hashes.get(key) != expected.get(key):
            blockers.append(f"source_evidence_hash_mismatch:{key}")
    if not _is_sha256(config_sha256):
        blockers.append("invalid_preregistration_config_sha256")
    for field in BOUNDARY_FIELDS:
        if config.get(field) is not False:
            blockers.append(f"preregistration_boundary_not_false:{field}")
    candidate = config.get("candidate", {})
    if candidate.get("factor_name") != FACTOR_NAME:
        blockers.append("missing_frozen_candidate")
    if candidate.get("direction") != "higher_is_better":
        blockers.append("candidate_direction_not_frozen")
    evaluation = config.get("evaluation", {})
    if (
        evaluation.get("horizons") != [5, 20]
        or evaluation.get("primary_horizon") != 5
        or evaluation.get("diagnostic_horizon") != 20
        or evaluation.get("execution_lag") != 1
    ):
        blockers.append("invalid_frozen_hypothesis_scope")
    boundary = config.get("data_boundary", {})
    if boundary.get("bar_authority_gap_dates") != ["2020-05-28", "2020-06-03"]:
        blockers.append("bar_gap_dates_not_frozen")
    if (
        boundary.get("exclude_gap_crossing_factor_windows") is not True
        or boundary.get("exclude_gap_crossing_label_windows") is not True
    ):
        blockers.append("bar_gap_exclusion_not_required")
    stop = config.get("stop_policy", {})
    if stop.get("single_prescreen_run_limit") != 1:
        blockers.append("single_prescreen_run_limit_not_one")
    for field in (
        "sign_flip_rescue_allowed",
        "window_tuning_allowed",
        "control_removal_allowed",
        "threshold_relaxation_allowed",
        "horizon_substitution_allowed",
        "parameter_grid_allowed",
        "regime_rescue_allowed",
    ):
        if stop.get(field) is not False:
            blockers.append(f"stop_policy_not_fail_closed:{field}")
    return blockers


def _candidate_csv(result: Mapping[str, Any]) -> str:
    stream = StringIO(newline="")
    fields = (
        "factor_name",
        "direction",
        "formula",
        "primary_horizon",
        "diagnostic_horizon",
        "registration_status",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    candidate = result.get("candidate", {})
    summary = result.get("summary", {})
    writer.writerow(
        {
            "factor_name": candidate.get("factor_name"),
            "direction": candidate.get("direction"),
            "formula": candidate.get("formula"),
            "primary_horizon": summary.get("primary_horizon"),
            "diagnostic_horizon": summary.get("diagnostic_horizon"),
            "registration_status": result.get("status"),
        }
    )
    return stream.getvalue()


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if key != "markdown"
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )
