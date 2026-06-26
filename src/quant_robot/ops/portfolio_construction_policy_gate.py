from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any


STAGE = "portfolio_construction_policy_gate"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_METRIC_PACK = [
    "total_return",
    "annual_return",
    "sharpe",
    "cost_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
    "turnover",
    "capacity_usage",
]
CONTROL_REQUIREMENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "risk_budget_position_sizing": (
        "risk_budget",
        ("max_single_name_weight", "max_position_adv_participation", "max_gross_exposure"),
    ),
    "volatility_targeting": (
        "volatility_targeting",
        ("enabled", "target_annual_volatility", "max_annual_volatility"),
    ),
    "industry_weight_constraints": (
        "industry_constraints",
        ("max_industry_weight", "max_benchmark_relative_industry_deviation", "min_industry_count"),
    ),
    "turnover_constraints": (
        "turnover_controls",
        ("max_one_way_turnover_per_rebalance", "max_annual_turnover", "max_cost_degradation_pct"),
    ),
    "stop_loss_or_de_risk_rules": (
        "drawdown_controls",
        (
            "max_drawdown_soft_tolerance",
            "de_risk_drawdown_threshold",
            "hard_stop_drawdown_threshold",
            "capacity_tradeability_gates_remain_hard",
        ),
    ),
}


def default_cn_stock_portfolio_policy() -> dict[str, Any]:
    return {
        "market": "CN",
        "asset_type": "stock",
        "risk_budget": {
            "max_single_name_weight": 0.05,
            "max_position_adv_participation": 0.01,
            "max_gross_exposure": 1.0,
        },
        "volatility_targeting": {
            "enabled": True,
            "target_annual_volatility": 0.15,
            "max_annual_volatility": 0.25,
            "lookback_days": 60,
        },
        "industry_constraints": {
            "max_industry_weight": 0.25,
            "max_benchmark_relative_industry_deviation": 0.10,
            "min_industry_count": 5,
        },
        "turnover_controls": {
            "max_one_way_turnover_per_rebalance": 0.35,
            "max_annual_turnover": 6.0,
            "max_cost_degradation_pct": 0.35,
            "rebalance_churn_limit": 0.50,
        },
        "drawdown_controls": {
            "max_drawdown_soft_tolerance": 0.30,
            "de_risk_drawdown_threshold": 0.30,
            "hard_stop_drawdown_threshold": 0.45,
            "capacity_tradeability_gates_remain_hard": True,
        },
        "required_metric_pack": REQUIRED_METRIC_PACK,
    }


def build_portfolio_construction_policy_gate(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = dict(policy or {})
    missing_controls, missing_items = _missing_controls(policy)
    invalid_items, invalid_by_control = _invalid_items(policy)
    metric_pack = [str(item) for item in policy.get("required_metric_pack", []) or []]
    missing_metrics = [metric for metric in REQUIRED_METRIC_PACK if metric not in metric_pack]
    if missing_metrics:
        missing_controls.append("required_metric_pack")
        missing_items["required_metric_pack"] = missing_metrics
    control_status = {}
    for control in CONTROL_REQUIREMENTS:
        if control in missing_controls:
            control_status[control] = "missing"
        elif invalid_by_control.get(control):
            control_status[control] = "invalid"
        else:
            control_status[control] = "implemented"
    blockers = [f"missing_control:{control}" for control in missing_controls]
    blockers.extend(f"invalid_policy_item:{item}" for item in invalid_items)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "missing_required_controls": _dedupe(missing_controls),
            "missing_required_items": missing_items,
            "invalid_policy_items": invalid_items,
            "missing_metrics": missing_metrics,
        },
        "market": str(policy.get("market", "CN")),
        "asset_type": str(policy.get("asset_type", "stock")),
        "policy": policy,
        "control_status": control_status,
        "required_metric_pack": REQUIRED_METRIC_PACK,
        "promotion_policy": {
            "portfolio_grid_allowed_without_policy_gate": False,
            "promotion_allowed_without_policy_gate": False,
            "profitability_claim_allowed_without_policy_gate": False,
            "next_allowed_action": "Attach this policy gate to portfolio conversion and walk-forward promotion review.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_portfolio_construction_policy_gate_markdown(result)
    return result


def write_portfolio_construction_policy_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "portfolio_construction_policy_gate.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "portfolio_construction_policy_gate.md").write_text(
        render_portfolio_construction_policy_gate_markdown(result),
        encoding="utf-8",
    )


def render_portfolio_construction_policy_gate_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Portfolio Construction Policy Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Market: {result.get('market', 'CN')}",
        f"- Asset type: {result.get('asset_type', 'stock')}",
        f"- Missing controls: {', '.join(summary.get('missing_required_controls', []) or []) or 'none'}",
        f"- Invalid policy items: {', '.join(summary.get('invalid_policy_items', []) or []) or 'none'}",
        f"- Missing metrics: {', '.join(summary.get('missing_metrics', []) or []) or 'none'}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Controls",
        "",
        "| Control | Status |",
        "|---|---|",
    ]
    for control, status in (result.get("control_status", {}) or {}).items():
        lines.append(f"| {control} | {status} |")
    lines.extend(
        [
            "",
            "## Required Metric Pack",
            "",
            ", ".join(result.get("required_metric_pack", []) or []),
            "",
            "## Interpretation",
            "",
            "- This is a policy gate, not a portfolio backtest.",
            "- Passing means future portfolio conversions must report these constraints and metrics before promotion review.",
            "- It does not imply a factor is profitable.",
        ]
    )
    return "\n".join(lines) + "\n"


def _missing_controls(policy: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    missing_controls = []
    missing_items: dict[str, list[str]] = {}
    for control, (section_name, required_keys) in CONTROL_REQUIREMENTS.items():
        section = policy.get(section_name)
        if not isinstance(section, dict):
            missing_controls.append(control)
            missing_items[control] = list(required_keys)
            continue
        missing = [key for key in required_keys if key not in section]
        if missing:
            missing_controls.append(control)
            missing_items[control] = missing
    return _dedupe(missing_controls), missing_items


def _invalid_items(policy: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    invalid: list[str] = []
    by_control: dict[str, list[str]] = {}

    def add(control: str, item: str) -> None:
        invalid.append(item)
        by_control.setdefault(control, []).append(item)

    risk = _dict(policy.get("risk_budget"))
    if "max_single_name_weight" in risk and not 0 < _float(risk["max_single_name_weight"]) <= 0.10:
        add("risk_budget_position_sizing", "max_single_name_weight_out_of_range")
    if "max_position_adv_participation" in risk and not 0 < _float(risk["max_position_adv_participation"]) <= 0.05:
        add("risk_budget_position_sizing", "max_position_adv_participation_out_of_range")
    if "max_gross_exposure" in risk and not 0 < _float(risk["max_gross_exposure"]) <= 1.50:
        add("risk_budget_position_sizing", "max_gross_exposure_out_of_range")

    vol = _dict(policy.get("volatility_targeting"))
    target_vol = _float(vol.get("target_annual_volatility"))
    max_vol = _float(vol.get("max_annual_volatility"))
    if "target_annual_volatility" in vol and not 0 < target_vol <= 0.40:
        add("volatility_targeting", "target_annual_volatility_out_of_range")
    if "max_annual_volatility" in vol and not target_vol <= max_vol <= 0.60:
        add("volatility_targeting", "max_annual_volatility_out_of_range")

    industry = _dict(policy.get("industry_constraints"))
    if "max_industry_weight" in industry and not 0 < _float(industry["max_industry_weight"]) <= 0.40:
        add("industry_weight_constraints", "max_industry_weight_out_of_range")
    if "max_benchmark_relative_industry_deviation" in industry and not (
        0 < _float(industry["max_benchmark_relative_industry_deviation"]) <= 0.20
    ):
        add("industry_weight_constraints", "max_benchmark_relative_industry_deviation_out_of_range")
    if "min_industry_count" in industry and int(_float(industry["min_industry_count"])) < 3:
        add("industry_weight_constraints", "min_industry_count_too_low")

    turnover = _dict(policy.get("turnover_controls"))
    if "max_one_way_turnover_per_rebalance" in turnover and not (
        0 < _float(turnover["max_one_way_turnover_per_rebalance"]) <= 1.0
    ):
        add("turnover_constraints", "max_one_way_turnover_per_rebalance_out_of_range")
    if "max_annual_turnover" in turnover and not 0 < _float(turnover["max_annual_turnover"]) <= 20.0:
        add("turnover_constraints", "max_annual_turnover_out_of_range")
    if "max_cost_degradation_pct" in turnover and not 0 <= _float(turnover["max_cost_degradation_pct"]) <= 0.50:
        add("turnover_constraints", "max_cost_degradation_pct_out_of_range")

    drawdown = _dict(policy.get("drawdown_controls"))
    soft = _float(drawdown.get("max_drawdown_soft_tolerance"))
    de_risk = _float(drawdown.get("de_risk_drawdown_threshold"))
    hard = _float(drawdown.get("hard_stop_drawdown_threshold"))
    if "max_drawdown_soft_tolerance" in drawdown and not 0 < soft <= 0.50:
        add("stop_loss_or_de_risk_rules", "max_drawdown_soft_tolerance_out_of_range")
    if "de_risk_drawdown_threshold" in drawdown and not 0 < de_risk <= hard:
        add("stop_loss_or_de_risk_rules", "de_risk_drawdown_threshold_out_of_range")
    if "hard_stop_drawdown_threshold" in drawdown and not soft <= hard <= 0.60:
        add("stop_loss_or_de_risk_rules", "hard_stop_drawdown_threshold_out_of_range")
    if "capacity_tradeability_gates_remain_hard" in drawdown and drawdown.get("capacity_tradeability_gates_remain_hard") is not True:
        add("stop_loss_or_de_risk_rules", "capacity_tradeability_gates_must_remain_hard")
    return invalid, by_control


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
