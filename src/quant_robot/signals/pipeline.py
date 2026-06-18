from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.portfolio import select_top_n
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.portfolio.constraints import PortfolioConstraints, apply_portfolio_constraints
from quant_robot.storage.cn_etf_rotation_membership import filter_signals_to_cn_etf_rotation_membership


@dataclass(frozen=True)
class SignalPipelineConfig:
    factor_name: str = "momentum_2"
    factor_windows: tuple[int, ...] = (2, 3)
    market: str = "ALL"
    rotation_membership_root: Path | None = None
    rotation_membership_required: bool = False
    as_of_date: str | None = None
    top_n: int = 2
    portfolio_scope: str | None = None
    max_asset_weight: float = 1.0
    max_market_weight: float = 1.0
    max_gross_exposure: float = 1.0
    min_cash_weight: float = 0.0


def generate_signal_snapshot(bars: pd.DataFrame, config: SignalPipelineConfig) -> dict[str, Any]:
    filtered = _filter_bars(bars, config)
    validate_market_data(filtered)
    as_of_date = _resolve_as_of_date(filtered, config)
    factors = compute_basic_factors(filtered, windows=config.factor_windows)
    return _build_signal_snapshot(filtered, factors, config, as_of_date)


def generate_signal_snapshot_from_factors(
    bars: pd.DataFrame,
    factors: pd.DataFrame,
    config: SignalPipelineConfig,
    validate: bool = True,
) -> dict[str, Any]:
    filtered = _filter_bars(bars, config)
    if validate:
        validate_market_data(filtered)
    as_of_date = _resolve_as_of_date(filtered, config)
    factor_frame = _filter_factor_rows(factors, config)
    return _build_signal_snapshot(filtered, factor_frame, config, as_of_date)


def _build_signal_snapshot(
    filtered: pd.DataFrame,
    factors: pd.DataFrame,
    config: SignalPipelineConfig,
    as_of_date: Any,
) -> dict[str, Any]:
    selected = _latest_factor_slice(factors, config.factor_name, as_of_date)
    selected = filter_signals_to_cn_etf_rotation_membership(
        selected,
        root=config.rotation_membership_root,
        market=config.market,
        required=config.rotation_membership_required,
    )
    portfolio_scope = _resolve_portfolio_scope(config)
    ranked = select_top_n(selected, top_n=config.top_n, portfolio_scope=portfolio_scope)
    targets = _attach_latest_prices(ranked, filtered, as_of_date)
    constraints = PortfolioConstraints(
        max_asset_weight=config.max_asset_weight,
        max_market_weight=config.max_market_weight,
        max_gross_exposure=config.max_gross_exposure,
        min_cash_weight=config.min_cash_weight,
    )
    constrained, cash_weight, warnings = apply_portfolio_constraints(targets, constraints)
    signal_date = _signal_date(constrained, selected)
    target_gross = float(constrained["target_weight"].sum()) if not constrained.empty else 0.0
    return _sanitize(
        {
            "data_mode": "fixture" if set(filtered["source"].astype(str)) == {"fixture"} else "research",
            "as_of_date": str(as_of_date),
            "signal_date": str(signal_date),
            "request": _config_dict(config, portfolio_scope),
            "constraints": asdict(constraints),
            "target_gross_exposure": target_gross,
            "cash_weight": cash_weight,
            "warnings": warnings,
            "targets": _records(constrained),
        }
    )


def write_signal_snapshot(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(result["targets"]).to_csv(output_dir / "targets.csv", index=False)
    manifest = {key: value for key, value in result.items() if key != "targets"}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _filter_bars(bars: pd.DataFrame, config: SignalPipelineConfig) -> pd.DataFrame:
    frame = bars.copy()
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    if config.as_of_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.as_of_date).date()]
    if frame.empty:
        raise ValueError("No bars available for signal snapshot")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _filter_factor_rows(factors: pd.DataFrame, config: SignalPipelineConfig) -> pd.DataFrame:
    frame = factors.copy()
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _resolve_as_of_date(bars: pd.DataFrame, config: SignalPipelineConfig) -> Any:
    if config.as_of_date:
        return pd.to_datetime(config.as_of_date).date()
    return pd.to_datetime(bars["date"]).dt.date.max()


def _latest_factor_slice(factors: pd.DataFrame, factor_name: str, as_of_date: Any) -> pd.DataFrame:
    selected = factors[factors["factor_name"] == factor_name].dropna(subset=["factor_value"]).copy()
    selected = selected[pd.to_datetime(selected["date"]).dt.date <= as_of_date]
    if selected.empty:
        raise ValueError(f"No factor rows available for {factor_name} on or before {as_of_date}")
    signal_date = pd.to_datetime(selected["date"]).dt.date.max()
    return selected[pd.to_datetime(selected["date"]).dt.date == signal_date].reset_index(drop=True)


def _resolve_portfolio_scope(config: SignalPipelineConfig) -> str:
    if config.portfolio_scope is not None:
        return config.portfolio_scope
    return "global" if config.market.upper() == "ALL" else "market"


def _attach_latest_prices(targets: pd.DataFrame, bars: pd.DataFrame, as_of_date: Any) -> pd.DataFrame:
    if targets.empty:
        return targets.assign(latest_price=pd.Series(dtype=float))
    available = bars[pd.to_datetime(bars["date"]).dt.date <= as_of_date].sort_values(["asset_id", "date"])
    prices = (
        available.groupby("asset_id", as_index=False, group_keys=False)
        .tail(1)[["asset_id", "adj_close"]]
        .rename(columns={"adj_close": "latest_price"})
    )
    merged = targets.merge(prices, on="asset_id", how="left")
    if merged["latest_price"].isna().any():
        missing = sorted(merged.loc[merged["latest_price"].isna(), "asset_id"].astype(str).unique())
        raise ValueError("Missing latest prices for signal targets: " + ", ".join(missing))
    merged["signal_date"] = merged["date"]
    return merged


def _signal_date(targets: pd.DataFrame, fallback: pd.DataFrame) -> Any:
    source = targets if not targets.empty else fallback
    return pd.to_datetime(source["date"]).dt.date.max()


def _config_dict(config: SignalPipelineConfig, portfolio_scope: str) -> dict[str, Any]:
    data = asdict(config)
    data["factor_windows"] = list(config.factor_windows)
    data["rotation_membership_root"] = (
        str(config.rotation_membership_root) if config.rotation_membership_root is not None else None
    )
    data["portfolio_scope"] = portfolio_scope
    return data


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
