from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from quant_robot.storage.atomic import atomic_write_json, atomic_write_text


STAGE = "cn_etf_delayed_nav_premium_preregistration"
STATUS_READY = "preregistered_single_prescreen"
FACTOR_NAME = "etf_delayed_nav_premium_innovation_reversal_60"
EXPECTED_CANDIDATE = {
    "factor_name": FACTOR_NAME,
    "hypothesis_count": 1,
    "premium_lookback": 60,
    "direction": "negative_innovation",
    "nav_availability_rule": "latest_known_from_lte_signal_date",
    "rolling_rule": "prior_60_complete_official_sessions_excluding_current",
}
EXPECTED_EVALUATION = {
    "horizons": [1, 5],
    "primary_horizon": 1,
    "diagnostic_horizon": 5,
    "execution_lag": 1,
}
EXPECTED_COSTS = {
    "one_way_costs_bps": [10.5, 26.6666666667, 60.0],
    "required_positive_net_spread_bps": 10.5,
}
EXPECTED_CAPACITY = {
    "position_value_cny": 1000,
    "max_one_way_participation_rate": 0.01,
}
BOUNDARY_KEYS = (
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


def build_cn_etf_delayed_nav_premium_preregistration(
    *,
    config: Mapping[str, Any],
    source_readiness: Mapping[str, Any],
    evidence_hashes: Mapping[str, str],
    config_sha256: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if (
        source_readiness.get("status")
        != config.get("source_evidence", {}).get("required_status")
        or source_readiness.get("gate", {}).get("cleared") is not True
    ):
        blockers.append("source_not_ready")
    if config.get("candidate") != EXPECTED_CANDIDATE:
        blockers.append("candidate_contract_mismatch")
    if config.get("evaluation") != EXPECTED_EVALUATION:
        blockers.append("evaluation_contract_mismatch")
    if config.get("costs") != EXPECTED_COSTS:
        blockers.append("cost_contract_mismatch")
    if config.get("capacity") != EXPECTED_CAPACITY:
        blockers.append("capacity_contract_mismatch")
    boundaries = config.get("boundaries")
    if not isinstance(boundaries, Mapping) or set(boundaries) != set(BOUNDARY_KEYS):
        blockers.append("boundary_contract_mismatch")
        boundaries = {}
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            blockers.append(f"boundary_enabled:{key}")
    if not _is_sha256(config_sha256):
        blockers.append("invalid_config_sha256")
    if not evidence_hashes or any(
        not isinstance(key, str) or not _is_sha256(value)
        for key, value in evidence_hashes.items()
    ):
        blockers.append("invalid_evidence_hashes")
    blockers = list(dict.fromkeys(blockers))
    status = "blocked" if blockers else STATUS_READY
    result = {
        "stage": STAGE,
        "registration_date": config.get("registration_date"),
        "status": status,
        "primary_market": config.get("primary_market"),
        "research_family": config.get("research_family"),
        "candidate": dict(config.get("candidate", {})),
        "evaluation": dict(config.get("evaluation", {})),
        "costs": dict(config.get("costs", {})),
        "capacity": dict(config.get("capacity", {})),
        "configuration": {"sha256": config_sha256},
        "source_evidence": {
            "status": source_readiness.get("status"),
            "hashes": dict(evidence_hashes),
            "nav_rows": source_readiness.get("summary", {}).get("nav_rows"),
            "nav_assets": source_readiness.get("summary", {}).get("nav_assets"),
        },
        "summary": {
            "blockers": blockers,
            "candidate_count": 1 if not blockers else 0,
            "hypothesis_count": config.get("candidate", {}).get("hypothesis_count"),
        },
        "forward_return_read": False,
        "factor_generation_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "promotion_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_trading_allowed": False,
        "live_boundary_allowed": False,
        "next_direction": (
            "issue_one_hash_bound_h1_h5_prescreen_authorization"
            if status == STATUS_READY
            else "close_nav_premium_preregistration_without_label_read"
        ),
    }
    result["markdown"] = render_cn_etf_delayed_nav_premium_preregistration(result)
    return result


def write_cn_etf_delayed_nav_premium_preregistration(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{STAGE}.json"
    markdown_path = output / f"{STAGE}.md"
    clean = {key: value for key, value in result.items() if key != "markdown"}
    atomic_write_json(json_path, clean)
    atomic_write_text(
        markdown_path,
        render_cn_etf_delayed_nav_premium_preregistration(result),
    )
    return {"json": json_path, "markdown": markdown_path}


def render_cn_etf_delayed_nav_premium_preregistration(
    result: Mapping[str, Any],
) -> str:
    blockers = result["summary"]["blockers"]
    lines = [
        "# CN ETF Delayed-NAV Premium Preregistration",
        "",
        f"- Status: `{result['status']}`",
        f"- Candidate: `{result['candidate'].get('factor_name', '')}`",
        "- Candidate count: 1",
        "- Primary horizon: H1",
        "- Diagnostic-only horizon: H5",
        "- Base one-way cost: 10.5 bp",
        "- Minimum-fee stress: 26.6667 and 60 bp one way",
        "- Forward return read: false",
        "- Prescreen execution allowed by preregistration alone: false",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{value}`" for value in blockers] or ["- None"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Only a separate hash-bound single-use authorization may allow the frozen "
            "prescreen. No second execution, rescue, holdout, paper, broker, account, "
            "order, or live action is authorized.",
            "",
        ]
    )
    return "\n".join(lines)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )
