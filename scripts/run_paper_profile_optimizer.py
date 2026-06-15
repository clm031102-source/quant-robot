from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.risk_policy_tiers import (
    PHASE_5_4_STAGE,
    assign_risk_tier,
    normalize_risk_tiers,
    paper_calmar,
    risk_tier_counts,
    tier_label,
)

try:
    from scripts.run_paper_simulation import run_simulation
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_paper_simulation import run_simulation


STAGE = "phase_5_3_paper_profile_optimizer"
DEFAULT_CONFIG = Path("configs/paper_profile_optimizer_cn_etf.json")


@dataclass(frozen=True)
class PaperProfileOptimizerConfig:
    constrained_search_pack: Path = Path("data/reports/constrained_candidate_search/constrained_candidate_search_pack.json")
    source: str = "processed-bars"
    data_root: Path = Path("data/processed/etf_csv")
    output_dir: Path = Path("data/reports/paper_profile_optimizer")
    max_frontier_candidates: int = 1
    factor_windows: tuple[int, ...] = (5, 10, 20, 60, 120)
    initial_cash: float = 100000.0
    commission_bps: float = 5.0
    slippage_bps: float = 5.0
    min_trade_value: float = 1.0
    min_paper_sharpe: float = 0.5
    max_drawdown_limit: float = 0.2
    min_total_return: float = 0.0
    min_trades: int = 20
    risk_tiers: tuple[dict[str, Any], ...] = ()
    primary_risk_tier: str | None = None
    risk_profiles: tuple[dict[str, Any], ...] = ()


def load_paper_profile_optimizer_config(path: str | Path = DEFAULT_CONFIG) -> PaperProfileOptimizerConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PaperProfileOptimizerConfig(
        constrained_search_pack=Path(data.get("constrained_search_pack", PaperProfileOptimizerConfig.constrained_search_pack)),
        source=str(data.get("source", PaperProfileOptimizerConfig.source)),
        data_root=Path(data.get("data_root", PaperProfileOptimizerConfig.data_root)),
        output_dir=Path(data.get("output_dir", PaperProfileOptimizerConfig.output_dir)),
        max_frontier_candidates=int(data.get("max_frontier_candidates", PaperProfileOptimizerConfig.max_frontier_candidates)),
        factor_windows=tuple(int(value) for value in data.get("factor_windows", PaperProfileOptimizerConfig.factor_windows)),
        initial_cash=float(data.get("initial_cash", PaperProfileOptimizerConfig.initial_cash)),
        commission_bps=float(data.get("commission_bps", PaperProfileOptimizerConfig.commission_bps)),
        slippage_bps=float(data.get("slippage_bps", PaperProfileOptimizerConfig.slippage_bps)),
        min_trade_value=float(data.get("min_trade_value", PaperProfileOptimizerConfig.min_trade_value)),
        min_paper_sharpe=float(data.get("min_paper_sharpe", PaperProfileOptimizerConfig.min_paper_sharpe)),
        max_drawdown_limit=float(data.get("max_drawdown_limit", PaperProfileOptimizerConfig.max_drawdown_limit)),
        min_total_return=float(data.get("min_total_return", PaperProfileOptimizerConfig.min_total_return)),
        min_trades=int(data.get("min_trades", PaperProfileOptimizerConfig.min_trades)),
        risk_tiers=tuple(_risk_tier(value) for value in data.get("risk_tiers", PaperProfileOptimizerConfig.risk_tiers)),
        primary_risk_tier=data.get("primary_risk_tier", PaperProfileOptimizerConfig.primary_risk_tier),
        risk_profiles=tuple(_risk_profile(value, index) for index, value in enumerate(data.get("risk_profiles", ()), start=1)),
    )


def run_paper_profile_optimizer(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = load_paper_profile_optimizer_config(config_path)
    constrained = _read_json(config.constrained_search_pack)
    frontier = _frontier_candidates(constrained, config.max_frontier_candidates)
    attempts = []
    for candidate in frontier:
        for profile in _risk_profiles(config):
            attempts.append(_run_profile_attempt(candidate, profile, config))
    pack = build_paper_profile_optimizer_pack(constrained, config, frontier, attempts)
    write_paper_profile_optimizer_pack(config.output_dir, pack)
    return pack


def build_paper_profile_optimizer_pack(
    constrained_search_pack: dict[str, Any],
    config: PaperProfileOptimizerConfig,
    frontier: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [row for row in attempts if row.get("profile_status") == "paper_profile_eligible"]
    selected = _selected_profile(eligible, config)
    if not frontier:
        selection_status = "no_frontier_candidate"
    else:
        selection_status = _selection_status(selected, config)
    fallback_policy = {
        "max_drawdown_limit": -abs(config.max_drawdown_limit),
        "min_paper_sharpe": config.min_paper_sharpe,
        "min_total_return": config.min_total_return,
        "min_trades": config.min_trades,
    }
    tiers, primary = normalize_risk_tiers(config.risk_tiers, fallback_policy, config.primary_risk_tier)
    pack = {
        "stage": PHASE_5_4_STAGE if tiers else STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": constrained_search_pack.get("stage"),
        "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        "live_boundary_allowed": False,
        "paper_trading_allowed": bool(selected),
        "selection_status": selection_status,
        "policy": {
            "min_paper_sharpe": config.min_paper_sharpe,
            "max_drawdown_limit": -abs(config.max_drawdown_limit),
            "min_total_return": config.min_total_return,
            "min_trades": config.min_trades,
            "primary_risk_tier": primary if tiers else None,
            "risk_tiers": tiers,
        },
        "config": _config_dict(config),
        "summary": _summary(frontier, attempts),
        "selected_profile": selected,
        "frontier_candidates": frontier,
        "attempts": attempts,
        "next_actions": _next_actions(selection_status),
    }
    pack["markdown"] = render_paper_profile_optimizer_markdown(pack)
    return _sanitize(pack)


def write_paper_profile_optimizer_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "paper_profile_optimizer_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "paper_profile_optimizer_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("attempts", [])).to_csv(output_path / "paper_profile_attempts.csv", index=False)
    pd.DataFrame([pack.get("summary", {})]).to_csv(output_path / "paper_profile_summary.csv", index=False)


def render_paper_profile_optimizer_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    selected = pack.get("selected_profile") if isinstance(pack.get("selected_profile"), dict) else None
    lines = [
        "# Phase 5.3 Paper Profile Optimizer",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Selection: {pack.get('selection_status', 'unknown')}",
        f"- Frontier candidates: {summary.get('frontier_candidates', 0)}",
        f"- Profile attempts: {summary.get('profile_attempts', 0)}",
        f"- Eligible profiles: {summary.get('eligible_profiles', 0)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', '')}",
        "",
        "## Selected Profile",
        "",
    ]
    if selected:
        lines.extend(
            [
                f"- Case: {selected.get('case_id')}",
                f"- Profile: {selected.get('profile_id')}",
                f"- Risk tier: {selected.get('risk_tier')}",
                f"- Paper Sharpe: {selected.get('paper_sharpe')}",
                f"- Paper drawdown: {selected.get('paper_max_drawdown')}",
                f"- Total return: {selected.get('paper_total_return')}",
                f"- Paper Calmar: {selected.get('paper_calmar')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Attempts",
            "",
            "| Case | Profile | Status | Risk tier | Sharpe | Drawdown | Return | Calmar | Rejections |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("attempts", [])[:20]:
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('case_id', '')} | "
                f"{row.get('profile_id', '')} | "
                f"{row.get('profile_status', '')} | "
                f"{row.get('risk_tier', '')} | "
                f"{row.get('paper_sharpe', '')} | "
                f"{row.get('paper_max_drawdown', '')} | "
                f"{row.get('paper_total_return', '')} | "
                f"{row.get('paper_calmar', '')} | "
                f"{', '.join(row.get('rejection_reasons', [])) if isinstance(row.get('rejection_reasons'), list) else ''} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize paper risk profiles for constrained frontier candidates.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    pack = run_paper_profile_optimizer(Path(args.config))
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "selection_status": pack["selection_status"],
                "summary": pack["summary"],
                "selected_profile": pack["selected_profile"],
                "output_dir": pack["config"]["output_dir"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _run_profile_attempt(candidate: dict[str, Any], profile: dict[str, Any], config: PaperProfileOptimizerConfig) -> dict[str, Any]:
    case_id = str(candidate.get("case_id", "unknown"))
    try:
        result = run_simulation(
            source=config.source,
            data_root=config.data_root,
            market=str(candidate.get("market")),
            factor_name=str(candidate.get("factor_name")),
            factor_windows=config.factor_windows,
            top_n=_case_top_n(case_id),
            rebalance_interval=_case_rebalance_interval(case_id),
            initial_cash=config.initial_cash,
            commission_bps=config.commission_bps,
            slippage_bps=config.slippage_bps,
            min_trade_value=config.min_trade_value,
            max_asset_weight=_float(profile.get("max_asset_weight"), 1.0),
            max_market_weight=_float(profile.get("max_market_weight"), 1.0),
            max_gross_exposure=_float(profile.get("max_gross_exposure"), 1.0),
            min_cash_weight=_float(profile.get("min_cash_weight"), 0.0),
            max_drawdown_guard=profile.get("max_drawdown_guard"),
            guard_cooldown_periods=_int(profile.get("guard_cooldown_periods")),
            output_dir=None,
        )
        metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
        attempt = {
            "case_id": case_id,
            "market": candidate.get("market"),
            "factor_name": candidate.get("factor_name"),
            "profile_id": profile.get("profile_id"),
            "profile_status": "completed",
            "error": None,
            "paper_sharpe": _round(metrics.get("sharpe")),
            "paper_total_return": _round(metrics.get("total_return")),
            "paper_max_drawdown": _round(metrics.get("max_equity_drawdown", metrics.get("max_drawdown"))),
            "fills": len(result.get("fills", [])) if isinstance(result.get("fills"), list) else 0,
            "guard_events": len(result.get("guard_events", [])) if isinstance(result.get("guard_events"), list) else 0,
            "max_asset_weight": _round(profile.get("max_asset_weight")),
            "max_gross_exposure": _round(profile.get("max_gross_exposure")),
            "min_cash_weight": _round(profile.get("min_cash_weight")),
            "max_drawdown_guard": _round(profile.get("max_drawdown_guard")),
            "guard_cooldown_periods": _int(profile.get("guard_cooldown_periods")),
        }
        attempt["paper_calmar"] = _round(paper_calmar(attempt["paper_total_return"], attempt["paper_max_drawdown"]))
        attempt["rejection_reasons"] = _rejection_reasons(attempt, config)
        _apply_risk_tiers(attempt, config)
        attempt["profile_status"] = "paper_profile_eligible" if not attempt["rejection_reasons"] else "rejected"
        return attempt
    except Exception as exc:
        return {
            "case_id": case_id,
            "market": candidate.get("market"),
            "factor_name": candidate.get("factor_name"),
            "profile_id": profile.get("profile_id"),
            "profile_status": "failed",
            "error": str(exc),
            "rejection_reasons": ["profile_simulation_failed"],
        }


def _rejection_reasons(attempt: dict[str, Any], config: PaperProfileOptimizerConfig) -> list[str]:
    reasons = []
    if _float(attempt.get("paper_sharpe")) < config.min_paper_sharpe:
        reasons.append("paper_sharpe_below_min")
    if _float(attempt.get("paper_max_drawdown")) < -abs(config.max_drawdown_limit):
        reasons.append("paper_drawdown_breach")
    if _float(attempt.get("paper_total_return")) < config.min_total_return:
        reasons.append("paper_total_return_below_min")
    return reasons


def _selected_profile(eligible: list[dict[str, Any]], config: PaperProfileOptimizerConfig) -> dict[str, Any] | None:
    if not eligible:
        return None
    if config.risk_tiers:
        selected = sorted(
            eligible,
            key=lambda row: (
                -_float(row.get("paper_total_return")),
                -_float(row.get("paper_calmar")),
                -_float(row.get("paper_sharpe")),
                _float(row.get("paper_max_drawdown")),
                str(row.get("case_id")),
                str(row.get("profile_id")),
            ),
        )[0]
    else:
        selected = sorted(
            eligible,
            key=lambda row: (
                -_float(row.get("paper_sharpe")),
                _float(row.get("paper_max_drawdown")),
                -_float(row.get("paper_total_return")),
                str(row.get("case_id")),
                str(row.get("profile_id")),
            ),
        )[0]
    return {**selected, "live_order_allowed": False}


def _summary(frontier: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, int]:
    tier_rows = [row for row in attempts if row.get("profile_status") == "paper_profile_eligible" and row.get("risk_tier")]
    tier_ids = []
    for row in tier_rows:
        if row.get("risk_tier") not in tier_ids:
            tier_ids.append(row.get("risk_tier"))
    return {
        "frontier_candidates": len(frontier),
        "profile_attempts": len(attempts),
        "eligible_profiles": sum(1 for row in attempts if row.get("profile_status") == "paper_profile_eligible"),
        "rejected_profiles": sum(1 for row in attempts if row.get("profile_status") == "rejected"),
        "failed_profiles": sum(1 for row in attempts if row.get("profile_status") == "failed"),
        "risk_tier_counts": risk_tier_counts(tier_rows, [{"tier_id": tier_id} for tier_id in tier_ids]),
    }


def _next_actions(selection_status: str) -> list[dict[str, Any]]:
    if selection_status in {"paper_profile_selected", "risk_tier_profile_selected"}:
        return [
            {
                "action": "rerun_promotion_gate_with_selected_profile",
                "reason": "A paper profile passed the configured paper Sharpe, return, and drawdown policy; refresh promotion and daily ops before observation.",
                "local_only": True,
            }
        ]
    if selection_status == "no_frontier_candidate":
        return [
            {
                "action": "run_constrained_candidate_search",
                "reason": "No near-miss frontier candidate exists for profile optimization.",
                "local_only": True,
            }
        ]
    return [
        {
            "action": "expand_profile_grid_or_factor_family",
            "reason": "No profile passed both paper Sharpe and drawdown policy.",
            "local_only": True,
        }
    ]


def _frontier_candidates(constrained: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = constrained.get("frontier_candidates", []) if isinstance(constrained.get("frontier_candidates"), list) else []
    return [row for row in rows if isinstance(row, dict)][:limit]


def _risk_profiles(config: PaperProfileOptimizerConfig) -> tuple[dict[str, Any], ...]:
    if config.risk_profiles:
        return config.risk_profiles
    return (
        {"profile_id": "cap46_guard10_cd3", "max_asset_weight": 0.46, "max_gross_exposure": 1.0, "min_cash_weight": 0.0, "max_drawdown_guard": 0.1, "guard_cooldown_periods": 3},
        {"profile_id": "cap47_guard10_cd3", "max_asset_weight": 0.47, "max_gross_exposure": 1.0, "min_cash_weight": 0.0, "max_drawdown_guard": 0.1, "guard_cooldown_periods": 3},
        {"profile_id": "cap48_guard10_cd3", "max_asset_weight": 0.48, "max_gross_exposure": 1.0, "min_cash_weight": 0.0, "max_drawdown_guard": 0.1, "guard_cooldown_periods": 3},
    )


def _risk_profile(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("risk_profiles entries must be JSON objects")
    profile = dict(value)
    profile.setdefault("profile_id", f"profile_{index}")
    return profile


def _risk_tier(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("risk_tiers entries must be JSON objects")
    return dict(value)


def _apply_risk_tiers(attempt: dict[str, Any], config: PaperProfileOptimizerConfig) -> None:
    fallback_policy = {
        "max_drawdown_limit": -abs(config.max_drawdown_limit),
        "min_paper_sharpe": config.min_paper_sharpe,
        "min_total_return": config.min_total_return,
        "min_trades": config.min_trades,
    }
    tiers, _primary = normalize_risk_tiers(config.risk_tiers, fallback_policy, config.primary_risk_tier)
    if not tiers:
        attempt["eligible_risk_tiers"] = []
        attempt["risk_tier"] = None
        return
    tier_rejections = {str(tier.get("tier_id")): _profile_tier_rejections(attempt, tier) for tier in tiers}
    eligible_tiers, assigned_tier = assign_risk_tier(tier_rejections, tiers)
    attempt["risk_tier_rejections"] = tier_rejections
    attempt["eligible_risk_tiers"] = eligible_tiers
    attempt["risk_tier"] = assigned_tier
    attempt["risk_tier_label"] = tier_label(tiers, assigned_tier)
    attempt["rejection_reasons"] = tier_rejections.get(assigned_tier, []) if assigned_tier else _merged_tier_rejection_reasons(tier_rejections)


def _profile_tier_rejections(attempt: dict[str, Any], tier: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _float(attempt.get("paper_sharpe")) < _float(tier.get("min_paper_sharpe")):
        reasons.append("paper_sharpe_below_min")
    if _float(attempt.get("paper_max_drawdown")) < _float(tier.get("max_drawdown_limit")):
        reasons.append("paper_drawdown_breach")
    if _float(attempt.get("paper_calmar")) < _float(tier.get("min_paper_calmar")):
        reasons.append("paper_calmar_below_min")
    if _float(attempt.get("paper_total_return")) < _float(tier.get("min_total_return")):
        reasons.append("paper_total_return_below_min")
    if _int(attempt.get("fills")) < _int(tier.get("min_trades")):
        reasons.append("paper_trades_below_min")
    return reasons


def _merged_tier_rejection_reasons(tier_rejections: dict[str, list[str]]) -> list[str]:
    reasons: list[str] = []
    for tier_reasons in tier_rejections.values():
        for reason in tier_reasons:
            if reason not in reasons:
                reasons.append(reason)
    return reasons or ["no_risk_tier_passed"]


def _selection_status(selected: dict[str, Any] | None, config: PaperProfileOptimizerConfig) -> str:
    if not selected:
        return "no_paper_profile_candidate"
    if not config.risk_tiers:
        return "paper_profile_selected"
    fallback_policy = {
        "max_drawdown_limit": -abs(config.max_drawdown_limit),
        "min_paper_sharpe": config.min_paper_sharpe,
        "min_total_return": config.min_total_return,
        "min_trades": config.min_trades,
    }
    _tiers, primary = normalize_risk_tiers(config.risk_tiers, fallback_policy, config.primary_risk_tier)
    if selected.get("risk_tier") == primary:
        return "paper_profile_selected"
    return "risk_tier_profile_selected"


def _case_top_n(case_id: str) -> int:
    marker = "_top"
    if marker not in case_id:
        return 1
    try:
        return int(case_id.split(marker, 1)[1].split("_", 1)[0])
    except ValueError:
        return 1


def _case_rebalance_interval(case_id: str) -> int:
    marker = "_reb"
    if marker not in case_id:
        return 1
    try:
        return int(case_id.rsplit(marker, 1)[1])
    except ValueError:
        return 1


def _config_dict(config: PaperProfileOptimizerConfig) -> dict[str, Any]:
    return {
        "constrained_search_pack": str(config.constrained_search_pack),
        "source": config.source,
        "data_root": str(config.data_root),
        "output_dir": str(config.output_dir),
        "max_frontier_candidates": config.max_frontier_candidates,
        "factor_windows": list(config.factor_windows),
        "initial_cash": config.initial_cash,
        "commission_bps": config.commission_bps,
        "slippage_bps": config.slippage_bps,
        "min_trade_value": config.min_trade_value,
        "min_paper_sharpe": config.min_paper_sharpe,
        "max_drawdown_limit": config.max_drawdown_limit,
        "min_total_return": config.min_total_return,
        "min_trades": config.min_trades,
        "risk_tiers": list(config.risk_tiers),
        "primary_risk_tier": config.primary_risk_tier,
        "risk_profiles": list(config.risk_profiles),
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _round(value: Any) -> float:
    return round(_float(value), 6)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
