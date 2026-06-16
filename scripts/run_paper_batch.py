from __future__ import annotations

import argparse
import ast
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.paper.simulator import write_paper_simulation_artifacts

try:
    from scripts.run_paper_simulation import run_simulation
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_paper_simulation import run_simulation


@dataclass(frozen=True)
class PaperBatchConfig:
    walk_forward_leaderboard: Path | None = None
    candidate_leaderboard: Path | None = None
    source: str = "fixture"
    data_root: Path = Path("data/processed")
    factor_input_root: Path | None = None
    moneyflow_input_root: Path | None = None
    output_dir: Path = Path("data/reports/paper_batch")
    max_candidates: int | None = None
    initial_cash: float = 100000.0
    commission_bps: float | None = None
    slippage_bps: float | None = None
    market_impact_bps: float = 0.0
    max_participation_rate: float | None = None
    min_trade_value: float = 1.0
    max_asset_weight: float = 1.0
    max_market_weight: float = 1.0
    max_gross_exposure: float = 1.0
    min_cash_weight: float = 0.0
    periods_per_year: float | None = None
    max_drawdown_guard: float | None = None
    guard_cooldown_periods: int = 0
    risk_profiles: tuple[dict[str, Any], ...] = ()
    profile_rank_by: str = "sharpe"
    profile_max_drawdown: float | None = None
    min_paper_sharpe: float = 0.5
    min_paper_total_return: float = 0.0
    max_paper_drawdown: float | None = None


def load_paper_batch_config(path: str | Path) -> PaperBatchConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return PaperBatchConfig(
        walk_forward_leaderboard=Path(data["walk_forward_leaderboard"]) if data.get("walk_forward_leaderboard") else None,
        candidate_leaderboard=Path(data["candidate_leaderboard"]) if data.get("candidate_leaderboard") else None,
        source=str(data.get("source", PaperBatchConfig.source)),
        data_root=Path(data.get("data_root", PaperBatchConfig.data_root)),
        factor_input_root=Path(data["factor_input_root"]) if data.get("factor_input_root") else None,
        moneyflow_input_root=Path(data["moneyflow_input_root"]) if data.get("moneyflow_input_root") else None,
        output_dir=Path(data.get("output_dir", PaperBatchConfig.output_dir)),
        max_candidates=int(data["max_candidates"]) if data.get("max_candidates") is not None else None,
        initial_cash=float(data.get("initial_cash", PaperBatchConfig.initial_cash)),
        commission_bps=float(data["commission_bps"]) if data.get("commission_bps") is not None else None,
        slippage_bps=float(data["slippage_bps"]) if data.get("slippage_bps") is not None else None,
        market_impact_bps=float(data.get("market_impact_bps", PaperBatchConfig.market_impact_bps)),
        max_participation_rate=float(data["max_participation_rate"]) if data.get("max_participation_rate") is not None else None,
        min_trade_value=float(data.get("min_trade_value", PaperBatchConfig.min_trade_value)),
        max_asset_weight=float(data.get("max_asset_weight", PaperBatchConfig.max_asset_weight)),
        max_market_weight=float(data.get("max_market_weight", PaperBatchConfig.max_market_weight)),
        max_gross_exposure=float(data.get("max_gross_exposure", PaperBatchConfig.max_gross_exposure)),
        min_cash_weight=float(data.get("min_cash_weight", PaperBatchConfig.min_cash_weight)),
        periods_per_year=float(data["periods_per_year"]) if data.get("periods_per_year") is not None else None,
        max_drawdown_guard=float(data["max_drawdown_guard"]) if data.get("max_drawdown_guard") is not None else None,
        guard_cooldown_periods=int(data.get("guard_cooldown_periods", PaperBatchConfig.guard_cooldown_periods)),
        risk_profiles=tuple(_risk_profile(value, index) for index, value in enumerate(data.get("risk_profiles", ()), start=1)),
        profile_rank_by=str(data.get("profile_rank_by", PaperBatchConfig.profile_rank_by)),
        profile_max_drawdown=float(data["profile_max_drawdown"]) if data.get("profile_max_drawdown") is not None else None,
        min_paper_sharpe=float(data.get("min_paper_sharpe", PaperBatchConfig.min_paper_sharpe)),
        min_paper_total_return=float(data.get("min_paper_total_return", PaperBatchConfig.min_paper_total_return)),
        max_paper_drawdown=float(data["max_paper_drawdown"]) if data.get("max_paper_drawdown") is not None else None,
    )


def run_paper_batch(
    config_path: str | Path = "configs/paper_batch_cn_etf.json",
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    config = load_paper_batch_config(config_path)
    if output_dir is not None:
        config = PaperBatchConfig(**{**config.__dict__, "output_dir": Path(output_dir)})
    _prepare_output_dir(config.output_dir)
    rows = _candidate_rows(config)
    results = [_run_candidate(row, config) for row in rows]
    summary = _summary(results)
    report = {"config": _config_dict(config), "summary": summary, "candidates": results}
    _write_summary(config.output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local paper simulations for walk-forward candidates.")
    parser.add_argument("--config", default="configs/paper_batch_cn_etf.json")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    report = run_paper_batch(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"summary": report["summary"], "top": report["candidates"][:10]}, indent=2, sort_keys=True))


def _candidate_rows(config: PaperBatchConfig) -> list[dict[str, Any]]:
    if config.candidate_leaderboard is not None:
        return _alpha_candidate_rows(config.candidate_leaderboard, config.max_candidates)
    if config.walk_forward_leaderboard is None:
        raise ValueError("paper batch requires walk_forward_leaderboard or candidate_leaderboard")
    return _walk_forward_candidate_rows(config.walk_forward_leaderboard, config.max_candidates)


def _walk_forward_candidate_rows(path: Path, max_candidates: int | None) -> list[dict[str, Any]]:
    frame = _read_leaderboard(path, "walk_forward_leaderboard")
    if "rank" in frame.columns:
        frame = frame.sort_values("rank")
    records = frame.to_dict(orient="records")
    accepted = [row for row in records if str(row.get("validation_status")) == "accepted"]
    skipped = [{**row, "_skip_reason": "walk_forward_not_accepted"} for row in records if str(row.get("validation_status")) != "accepted"]
    selected = accepted[:max_candidates] if max_candidates is not None else accepted
    deferred = accepted[len(selected) :] if max_candidates is not None else []
    skipped.extend({**row, "_skip_reason": "candidate_limit"} for row in deferred)
    return selected + skipped


def _alpha_candidate_rows(path: Path, max_candidates: int | None) -> list[dict[str, Any]]:
    frame = _read_leaderboard(path, "candidate_leaderboard")
    if "candidate_rank" in frame.columns:
        frame = frame.sort_values("candidate_rank")
    records = frame.to_dict(orient="records")
    eligible = []
    skipped = []
    for row in records:
        if str(row.get("status")) != "completed":
            skipped.append({**row, "_skip_reason": "alpha_candidate_not_completed"})
        elif not _truthy(row.get("passes_adjusted_ic_p_value")):
            skipped.append({**row, "_skip_reason": "adjusted_ic_significance_not_passed"})
        elif "paper_candidate_allowed" in row and not _truthy(row.get("paper_candidate_allowed")):
            skipped.append({**row, "_skip_reason": "paper_candidate_not_allowed"})
        elif row.get("significance_status") is not None and str(row.get("significance_status")) != "significant_positive":
            skipped.append({**row, "_skip_reason": "paper_candidate_not_allowed"})
        else:
            eligible.append({**row, "validation_status": "accepted"})
    selected = eligible[:max_candidates] if max_candidates is not None else eligible
    deferred = eligible[len(selected) :] if max_candidates is not None else []
    skipped.extend({**row, "_skip_reason": "candidate_limit"} for row in deferred)
    return selected + skipped


def _read_leaderboard(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise ValueError(f"{label} not found: {path}")
    return pd.read_csv(path)


def _run_candidate(row: dict[str, Any], config: PaperBatchConfig) -> dict[str, Any]:
    case_id = str(row.get("case_id"))
    skip_reason = row.get("_skip_reason")
    if skip_reason:
        return _candidate_summary(row, status="skipped", config=config, error=str(skip_reason))
    profiles = _risk_profiles(config)
    attempts = [_run_profile_attempt(row, config, profile) for profile in profiles]
    selected = _select_profile_attempt(attempts, config)
    if selected is None:
        errors = [f"{attempt['risk_profile_id']}:{attempt['error']}" for attempt in attempts if attempt.get("error")]
        return _candidate_summary(
            row,
            status="failed",
            config=config,
            error="; ".join(errors) if errors else "no_completed_risk_profile",
            attempted_profiles=len(profiles),
        )
    output_dir = config.output_dir / case_id
    write_paper_simulation_artifacts(selected["result"], output_dir)
    return _candidate_summary(
        row,
        status="completed",
        config=config,
        result=selected["result"],
        output_dir=output_dir,
        risk_profile_id=str(selected["risk_profile_id"]),
        attempted_profiles=len(profiles),
    )


def _run_profile_attempt(row: dict[str, Any], config: PaperBatchConfig, profile: dict[str, Any]) -> dict[str, Any]:
    case_id = str(row.get("case_id"))
    risk_profile_id = str(profile["profile_id"])
    try:
        rebalance_interval = _case_rebalance_interval(case_id)
        cost_bps = _float(row.get("cost_bps"), 5.0)
        commission_bps = _profile_value(config, profile, "commission_bps")
        slippage_bps = _profile_value(config, profile, "slippage_bps")
        result = run_simulation(
            source=config.source,
            data_root=config.data_root,
            market=str(row.get("market")),
            factor_source=str(row.get("factor_source", "technical")),
            factor_name=str(row.get("factor_name")),
            factor_windows=_factor_windows(row.get("factor_windows")),
            factor_input_root=config.factor_input_root,
            moneyflow_input_root=config.moneyflow_input_root,
            top_n=int(_float(row.get("top_n"), 1.0)),
            rebalance_interval=rebalance_interval,
            initial_cash=config.initial_cash,
            commission_bps=commission_bps if commission_bps is not None else cost_bps,
            slippage_bps=slippage_bps if slippage_bps is not None else cost_bps,
            market_impact_bps=float(_profile_value(config, profile, "market_impact_bps")),
            max_participation_rate=_profile_value(config, profile, "max_participation_rate"),
            min_trade_value=float(_profile_value(config, profile, "min_trade_value")),
            max_asset_weight=float(_profile_value(config, profile, "max_asset_weight")),
            max_market_weight=float(_profile_value(config, profile, "max_market_weight")),
            max_gross_exposure=float(_profile_value(config, profile, "max_gross_exposure")),
            min_cash_weight=float(_profile_value(config, profile, "min_cash_weight")),
            periods_per_year=_profile_value(config, profile, "periods_per_year"),
            max_drawdown_guard=_profile_value(config, profile, "max_drawdown_guard"),
            guard_cooldown_periods=int(_profile_value(config, profile, "guard_cooldown_periods")),
            output_dir=None,
        )
        result["request"]["case_id"] = case_id
        result["request"]["risk_profile_id"] = risk_profile_id
        return {"status": "completed", "risk_profile_id": risk_profile_id, "result": result}
    except Exception as exc:
        return {"status": "failed", "risk_profile_id": risk_profile_id, "error": str(exc)}


def _candidate_summary(
    row: dict[str, Any],
    status: str,
    config: PaperBatchConfig,
    result: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    error: str | None = None,
    risk_profile_id: str | None = None,
    attempted_profiles: int = 0,
) -> dict[str, Any]:
    metrics = result.get("metrics", {}) if result is not None else {}
    paper_reasons = _paper_rejection_reasons(status, metrics, config)
    return {
        "case_id": str(row.get("case_id")),
        "market": row.get("market"),
        "factor_source": row.get("factor_source"),
        "factor_name": row.get("factor_name"),
        "top_n": int(_float(row.get("top_n"), 0.0)),
        "status": status,
        "error": error,
        "output_dir": str(output_dir) if output_dir is not None else None,
        "manifest_path": str(output_dir / "manifest.json") if output_dir is not None else None,
        "risk_profile_id": risk_profile_id,
        "attempted_profiles": attempted_profiles,
        "total_return": _float(metrics.get("total_return"), 0.0),
        "sharpe": _float(metrics.get("sharpe"), 0.0),
        "max_equity_drawdown": _float(metrics.get("max_equity_drawdown", metrics.get("max_drawdown")), 0.0),
        "fills": len(result.get("fills", [])) if result is not None else 0,
        "guard_events": len(result.get("guard_events", [])) if result is not None else 0,
        "paper_passed": not paper_reasons,
        "paper_rejection_reasons": paper_reasons,
    }


def _write_summary(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = report["candidates"]
    pd.DataFrame(rows).to_csv(output_dir / "paper_batch_summary.csv", index=False)
    (output_dir / "paper_batch_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _prepare_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_dir() and (child / "manifest.json").exists():
            shutil.rmtree(child)
    for name in ("paper_batch_summary.csv", "paper_batch_summary.json"):
        path = output_dir / name
        if path.exists():
            path.unlink()


def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "cases": len(results),
        "completed": sum(1 for row in results if row["status"] == "completed"),
        "failed": sum(1 for row in results if row["status"] == "failed"),
        "skipped": sum(1 for row in results if row["status"] == "skipped"),
        "paper_passed": sum(1 for row in results if row.get("paper_passed")),
        "paper_failed": sum(1 for row in results if row["status"] == "completed" and not row.get("paper_passed")),
    }


def _factor_windows(value: Any) -> tuple[int, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(int(item) for item in value)
    parsed = ast.literal_eval(str(value))
    if isinstance(parsed, int):
        return (parsed,)
    return tuple(int(item) for item in parsed)


def _paper_rejection_reasons(status: str, metrics: dict[str, Any], config: PaperBatchConfig) -> list[str]:
    reasons: list[str] = []
    if status != "completed":
        reasons.append("paper_simulation_not_completed")
        return reasons
    sharpe = _float(metrics.get("sharpe"), 0.0)
    total_return = _float(metrics.get("total_return"), 0.0)
    drawdown = _float(metrics.get("max_equity_drawdown", metrics.get("max_drawdown")), 0.0)
    drawdown_limit = config.max_paper_drawdown if config.max_paper_drawdown is not None else config.profile_max_drawdown
    if sharpe < config.min_paper_sharpe:
        reasons.append("paper_sharpe_below_min")
    if total_return < config.min_paper_total_return:
        reasons.append("paper_total_return_below_min")
    if drawdown_limit is not None and drawdown < -abs(drawdown_limit):
        reasons.append("paper_drawdown_above_limit")
    return reasons


def _case_rebalance_interval(case_id: str) -> int:
    marker = "_reb"
    if marker not in case_id:
        return 1
    try:
        return int(case_id.rsplit(marker, 1)[1])
    except ValueError:
        return 1


def _float(value: Any, default: float | None = None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        if default is None:
            raise
        return default


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def _risk_profile(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("risk_profiles entries must be JSON objects")
    allowed = {
        "profile_id",
        "commission_bps",
        "slippage_bps",
        "market_impact_bps",
        "max_participation_rate",
        "min_trade_value",
        "max_asset_weight",
        "max_market_weight",
        "max_gross_exposure",
        "min_cash_weight",
        "periods_per_year",
        "max_drawdown_guard",
        "guard_cooldown_periods",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError("Unknown risk profile fields: " + ", ".join(unknown))
    profile = dict(value)
    profile.setdefault("profile_id", f"profile_{index}")
    profile["profile_id"] = str(profile["profile_id"])
    return profile


def _risk_profiles(config: PaperBatchConfig) -> tuple[dict[str, Any], ...]:
    if config.risk_profiles:
        return config.risk_profiles
    return ({"profile_id": "base"},)


def _profile_value(config: PaperBatchConfig, profile: dict[str, Any], key: str) -> Any:
    return profile[key] if key in profile else getattr(config, key)


def _select_profile_attempt(attempts: list[dict[str, Any]], config: PaperBatchConfig) -> dict[str, Any] | None:
    completed = [attempt for attempt in attempts if attempt.get("status") == "completed"]
    if not completed:
        return None
    return max(completed, key=lambda attempt: _profile_attempt_key(attempt, config))


def _profile_attempt_key(attempt: dict[str, Any], config: PaperBatchConfig) -> tuple[int, float, float, float, float, str]:
    metrics = attempt["result"].get("metrics", {})
    drawdown = _float(metrics.get("max_equity_drawdown", metrics.get("max_drawdown")), 0.0)
    eligible = 1
    if config.profile_max_drawdown is not None and drawdown < -abs(config.profile_max_drawdown):
        eligible = 0
    rank_value = _float(metrics.get(config.profile_rank_by), 0.0)
    return (
        eligible,
        rank_value,
        _float(metrics.get("sharpe"), 0.0),
        _float(metrics.get("total_return"), 0.0),
        drawdown,
        str(attempt.get("risk_profile_id")),
    )


def _config_dict(config: PaperBatchConfig) -> dict[str, Any]:
    return {
        "walk_forward_leaderboard": str(config.walk_forward_leaderboard) if config.walk_forward_leaderboard is not None else None,
        "candidate_leaderboard": str(config.candidate_leaderboard) if config.candidate_leaderboard is not None else None,
        "source": config.source,
        "data_root": str(config.data_root),
        "factor_input_root": str(config.factor_input_root) if config.factor_input_root is not None else None,
        "moneyflow_input_root": str(config.moneyflow_input_root) if config.moneyflow_input_root is not None else None,
        "output_dir": str(config.output_dir),
        "max_candidates": config.max_candidates,
        "initial_cash": config.initial_cash,
        "commission_bps": config.commission_bps,
        "slippage_bps": config.slippage_bps,
        "market_impact_bps": config.market_impact_bps,
        "max_participation_rate": config.max_participation_rate,
        "min_trade_value": config.min_trade_value,
        "max_asset_weight": config.max_asset_weight,
        "max_market_weight": config.max_market_weight,
        "max_gross_exposure": config.max_gross_exposure,
        "min_cash_weight": config.min_cash_weight,
        "periods_per_year": config.periods_per_year,
        "max_drawdown_guard": config.max_drawdown_guard,
        "guard_cooldown_periods": config.guard_cooldown_periods,
        "risk_profiles": list(config.risk_profiles),
        "profile_rank_by": config.profile_rank_by,
        "profile_max_drawdown": config.profile_max_drawdown,
        "min_paper_sharpe": config.min_paper_sharpe,
        "min_paper_total_return": config.min_paper_total_return,
        "max_paper_drawdown": config.max_paper_drawdown,
    }


if __name__ == "__main__":
    main()
