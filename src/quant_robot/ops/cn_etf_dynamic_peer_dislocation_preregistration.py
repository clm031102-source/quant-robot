from __future__ import annotations

from copy import deepcopy
import csv
from io import StringIO
from pathlib import Path
from typing import Any, Mapping

from quant_robot.storage.atomic import atomic_write_json, atomic_write_text


STAGE = "cn_etf_dynamic_peer_dislocation_preregistration"
STATUS_READY = "preregistered_single_prescreen"
READY_STATUS = STATUS_READY
SAFETY = (
    "Research-to-review only. No forward-label read, factor generation, broker connection, "
    "account read, order placement, or live trading."
)
BOUNDARY_FIELDS = (
    "forward_return_read_allowed",
    "factor_generation_allowed",
    "prescreen_execution_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "paper_signal_allowed",
    "live_boundary_allowed",
)
SOURCE_BOUNDARY_BLOCKERS = {
    "current_name_used": "dynamic_peer_source_current_name_used",
    "official_2026_peer_mapping_used": "dynamic_peer_source_official_2026_peer_mapping_used",
    "forward_returns_calculated": "dynamic_peer_source_forward_returns_already_calculated",
    "factor_values_calculated": "dynamic_peer_source_factor_values_already_calculated",
}


def build_cn_etf_dynamic_peer_dislocation_preregistration(
    *,
    config: Mapping[str, Any],
    source_readiness: Mapping[str, Any],
    evidence_hashes: Mapping[str, str],
    config_sha256: str,
) -> dict[str, Any]:
    """Build a deterministic preregistration without reading bars or labels."""

    frozen_config = deepcopy(dict(config))
    frozen_source = deepcopy(dict(source_readiness))
    actual_hashes = {str(key): str(value) for key, value in evidence_hashes.items()}
    blockers = _collect_blockers(
        config=frozen_config,
        source_readiness=frozen_source,
        evidence_hashes=actual_hashes,
        config_sha256=config_sha256,
    )
    candidate = deepcopy(frozen_config.get("candidate", {}))
    evaluation = deepcopy(frozen_config.get("evaluation", {}))
    horizons = list(evaluation.get("horizons", []) or [])
    primary_horizon = evaluation.get("primary_horizon")
    diagnostic_horizon = evaluation.get("diagnostic_horizon")
    result: dict[str, Any] = {
        "stage": STAGE,
        "status": STATUS_READY if not blockers else "blocked",
        "registration_date": frozen_config.get("registration_date"),
        "primary_market": frozen_config.get("primary_market"),
        "research_family": frozen_config.get("research_family"),
        "config_sha256": config_sha256,
        "configuration": {"sha256": config_sha256},
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": 1 if candidate else 0,
            "hypothesis_count": len(horizons),
            "primary_horizon": primary_horizon,
            "diagnostic_horizon": diagnostic_horizon,
            "next_allowed_action": (
                "emit_single_prescreen_authorization"
                if not blockers
                else "repair_preregistration_evidence"
            ),
        },
        "source_evidence": {
            "required_status": frozen_config.get("source_evidence", {}).get("required_status"),
            "mapping_method": frozen_config.get("source_evidence", {}).get("mapping_method"),
            "expected_hashes": deepcopy(
                frozen_config.get("source_evidence", {}).get("hashes", {})
            ),
            "actual_hashes": actual_hashes,
            "source_stage": frozen_source.get("stage"),
            "source_status": frozen_source.get("status"),
        },
        "candidate": candidate,
        "candidates": [candidate] if candidate else [],
        "evaluation": evaluation,
        "reference_policy": deepcopy(frozen_config.get("reference_policy", {})),
        "capacity": deepcopy(frozen_config.get("capacity", {})),
        "costs": deepcopy(frozen_config.get("costs", {})),
        "stop_policy": deepcopy(frozen_config.get("stop_policy", {})),
        "claim_policy": {
            "alpha_claim_allowed": False,
            "profitability_claim_allowed": False,
            "source_readiness_is_promotion_evidence": False,
        },
        "next_direction": "run_one_hash_bound_dynamic_peer_dislocation_prescreen",
        "safety": SAFETY,
    }
    for field in BOUNDARY_FIELDS:
        result[field] = False
    result["markdown"] = render_cn_etf_dynamic_peer_dislocation_preregistration_markdown(result)
    return result


def write_cn_etf_dynamic_peer_dislocation_preregistration(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    """Write the preregistration packet deterministically and return its paths."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{STAGE}.json"
    markdown_path = output / f"{STAGE}.md"
    candidate_csv_path = output / "candidate.csv"
    clean = _sanitize(result)
    atomic_write_json(json_path, clean)
    atomic_write_text(
        markdown_path,
        render_cn_etf_dynamic_peer_dislocation_preregistration_markdown(result),
    )
    atomic_write_text(candidate_csv_path, _render_candidate_csv(result))
    return {
        "json": json_path,
        "markdown": markdown_path,
        "candidate_csv": candidate_csv_path,
    }


def render_cn_etf_dynamic_peer_dislocation_preregistration_markdown(
    result: Mapping[str, Any],
) -> str:
    summary = result.get("summary", {})
    candidates = result.get("candidates", []) or []
    candidate = candidates[0] if candidates else {}
    evaluation = result.get("evaluation", {})
    lines = [
        "# CN ETF Dynamic Peer Dislocation Preregistration",
        "",
        f"- Status: {result.get('status', 'blocked')}",
        f"- Market: {result.get('primary_market', '')}",
        f"- Candidate: {candidate.get('factor_name', '')}",
        f"- Primary horizon: {summary.get('primary_horizon', '')}",
        f"- Diagnostic horizon: {summary.get('diagnostic_horizon', '')}",
        f"- Hypotheses: {summary.get('hypothesis_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Prescreen execution allowed: {result.get('prescreen_execution_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        "",
        "## Frozen Candidate",
        "",
        f"- Family: {candidate.get('family', '')}",
        f"- Direction: {candidate.get('direction', '')}",
        f"- Formula: `{candidate.get('formula', '')}`",
        f"- Execution lag: {evaluation.get('execution_lag', '')}",
        "",
        "## Governance",
        "",
        "- This packet registers one candidate and does not read forward returns or factor values.",
        "- The diagnostic horizon cannot rescue a failed primary horizon.",
        "- A separate, hash-bound authorization is required before the single prescreen.",
        f"- Safety: {result.get('safety', SAFETY)}",
    ]
    return "\n".join(lines) + "\n"


def _collect_blockers(
    *,
    config: Mapping[str, Any],
    source_readiness: Mapping[str, Any],
    evidence_hashes: Mapping[str, str],
    config_sha256: str,
) -> list[str]:
    blockers: list[str] = []
    source_config = config.get("source_evidence", {})
    required_status = source_config.get("required_status")
    if source_readiness.get("status") != required_status:
        blockers.append("dynamic_peer_source_not_ready_for_preregistration")
    source_gate = source_readiness.get("gate", {})
    if not source_gate.get("cleared", False) or source_gate.get("blockers", []) or []:
        blockers.append("dynamic_peer_source_gate_not_cleared")
    expected_mapping_method = source_config.get("mapping_method")
    actual_mapping_method = source_readiness.get("mapping_integrity", {}).get("mapping_method")
    if actual_mapping_method != expected_mapping_method:
        blockers.append("dynamic_peer_source_mapping_method_mismatch")
    source_boundaries = source_readiness.get("source_boundaries", {})
    for field, blocker in SOURCE_BOUNDARY_BLOCKERS.items():
        if source_boundaries.get(field) is not False:
            blockers.append(blocker)
    if source_readiness.get("live_boundary_allowed") is not False:
        blockers.append("dynamic_peer_source_live_boundary_enabled")
    expected_hashes = source_config.get("hashes", {})
    for key in sorted(expected_hashes):
        if evidence_hashes.get(key) != expected_hashes.get(key):
            blockers.append(f"source_evidence_hash_mismatch:{key}")
    if set(evidence_hashes) != set(expected_hashes):
        blockers.append("source_evidence_hash_key_set_mismatch")
    if not _is_sha256(config_sha256):
        blockers.append("invalid_preregistration_config_sha256")
    for field in BOUNDARY_FIELDS:
        if config.get(field) is not False:
            blockers.append(f"preregistration_boundary_not_false:{field}")
    candidate = config.get("candidate", {})
    if not candidate.get("factor_name"):
        blockers.append("missing_frozen_candidate")
    evaluation = config.get("evaluation", {})
    horizons = list(evaluation.get("horizons", []) or [])
    if len(horizons) != 2 or len(set(horizons)) != 2:
        blockers.append("invalid_frozen_hypothesis_scope")
    if evaluation.get("primary_horizon") not in horizons:
        blockers.append("primary_horizon_not_frozen")
    if evaluation.get("diagnostic_horizon") not in horizons:
        blockers.append("diagnostic_horizon_not_frozen")
    if evaluation.get("primary_horizon") != 5:
        blockers.append("primary_horizon_not_five")
    if evaluation.get("diagnostic_horizon") != 20:
        blockers.append("diagnostic_horizon_not_twenty")
    if evaluation.get("execution_lag") != 1:
        blockers.append("execution_lag_not_one")
    stop_policy = config.get("stop_policy", {})
    if stop_policy.get("single_prescreen_run_limit") != 1:
        blockers.append("single_prescreen_run_limit_not_one")
    for field in (
        "sign_flip_rescue_allowed",
        "window_tuning_allowed",
        "threshold_relaxation_allowed",
        "horizon_substitution_allowed",
        "parameter_grid_allowed",
        "regime_rescue_allowed",
    ):
        if stop_policy.get(field) is not False:
            blockers.append(f"stop_policy_not_fail_closed:{field}")
    return blockers


def _render_candidate_csv(result: Mapping[str, Any]) -> str:
    columns = (
        "factor_name",
        "family",
        "direction",
        "formula",
        "primary_horizon",
        "diagnostic_horizon",
        "execution_lag",
        "registration_status",
        "prescreen_execution_allowed",
    )
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    summary = result.get("summary", {})
    evaluation = result.get("evaluation", {})
    for candidate in result.get("candidates", []) or []:
        writer.writerow(
            {
                "factor_name": candidate.get("factor_name"),
                "family": candidate.get("family"),
                "direction": candidate.get("direction"),
                "formula": candidate.get("formula"),
                "primary_horizon": summary.get("primary_horizon"),
                "diagnostic_horizon": summary.get("diagnostic_horizon"),
                "execution_lag": evaluation.get("execution_lag"),
                "registration_status": result.get("status"),
                "prescreen_execution_allowed": result.get("prescreen_execution_allowed", False),
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
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())
