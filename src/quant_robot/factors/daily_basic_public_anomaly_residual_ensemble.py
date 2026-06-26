from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES = (
    "public_anomaly_residual_equal_weight_20",
    "public_anomaly_residual_agreement_20",
    "public_anomaly_residual_disagreement_risk_20",
    "public_anomaly_residual_regime_conditioned_20",
)

_EPSILON = 1e-12


def compute_daily_basic_public_anomaly_residual_ensemble_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    requested = _resolve_requested_factor_names(factor_names)
    _require_columns(bars, ["date", "asset_id", "market", "adj_close", "high", "low", "amount"], "bars")
    _require_columns(
        daily_basic_inputs,
        [
            "date",
            "asset_id",
            "market",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe_ttm",
            "pb",
            "ps_ttm",
            "dv_ttm",
            "total_mv",
            "circ_mv",
        ],
        "daily-basic inputs",
    )
    frame = _feature_frame(bars, daily_basic_inputs)
    values_by_name = _ensemble_values(frame)
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES
    supported = set(DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(
            "Unsupported daily-basic public anomaly residual ensemble factor_names: "
            + ", ".join(unknown)
        )
    return factor_names


def _feature_frame(bars: pd.DataFrame, daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    bar_frame = bars.copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"]).dt.date
    bar_frame["asset_id"] = bar_frame["asset_id"].astype(str)
    bar_frame["market"] = bar_frame["market"].astype(str).str.upper()
    bar_frame = bar_frame.sort_values(["asset_id", "date"]).reset_index(drop=True)

    input_frame = daily_basic_inputs.copy()
    input_frame["date"] = pd.to_datetime(input_frame["date"]).dt.date
    input_frame["asset_id"] = input_frame["asset_id"].astype(str)
    input_frame["market"] = input_frame["market"].astype(str).str.upper()
    input_columns = [
        "date",
        "asset_id",
        "market",
        "turnover_rate_f",
        "pe_ttm",
        "pb",
        "dv_ttm",
        "circ_mv",
    ]
    frame = bar_frame.merge(input_frame[input_columns], on=["date", "asset_id", "market"], how="left")

    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        item["return_1d"] = returns
        item["return_20"] = price.pct_change(20)
        item["volatility_20"] = returns.rolling(20).std(ddof=0)
        item["downside_volatility_20"] = returns.clip(upper=0.0).rolling(20).std(ddof=0)
        item["amount_20"] = amount.rolling(20).mean()
        pieces.append(item)

    out = pd.concat(pieces, ignore_index=True)
    market_returns = (
        out.groupby(["market", "date"], sort=False)["return_1d"]
        .mean()
        .rename("market_return_1d")
        .reset_index()
        .sort_values(["market", "date"])
    )
    market_returns["market_momentum_20"] = market_returns.groupby("market", sort=False)[
        "market_return_1d"
    ].transform(lambda item: item.rolling(20).sum())
    out = out.merge(market_returns[["market", "date", "market_momentum_20"]], on=["market", "date"], how="left")
    out["amount_20_rank"] = _cs_rank(out, out["amount_20"])
    out["tradeable_mask"] = (
        (out["amount_20_rank"] > 0.25)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _ensemble_values(frame: pd.DataFrame) -> dict[str, pd.Series]:
    pe = pd.to_numeric(frame["pe_ttm"], errors="coerce")
    pb = pd.to_numeric(frame["pb"], errors="coerce")
    dividend = pd.to_numeric(frame["dv_ttm"], errors="coerce")
    turnover = pd.to_numeric(frame["turnover_rate_f"], errors="coerce")
    amount = pd.to_numeric(frame["amount_20"], errors="coerce")

    value = (
        _cs_z(frame, -_safe_log(pe))
        + _cs_z(frame, -_safe_log(pb))
        + _cs_z(frame, dividend)
    ) / 3.0
    quality_stability = (
        -0.65 * _cs_z(frame, frame["downside_volatility_20"])
        -0.35 * _cs_z(frame, pd.to_numeric(frame["return_20"], errors="coerce").abs())
    )
    reversal = -_cs_z(frame, frame["return_20"])
    lowvol = -_cs_z(frame, frame["volatility_20"])
    liquidity_capacity = _cs_z(frame, _safe_log(amount)) - 0.25 * _cs_z(frame, turnover)

    component_ranks = pd.DataFrame(
        {
            "value": _cs_rank(frame, value),
            "quality": _cs_rank(frame, quality_stability),
            "reversal": _cs_rank(frame, reversal),
            "lowvol": _cs_rank(frame, lowvol),
            "liquidity": _cs_rank(frame, liquidity_capacity),
        },
        index=frame.index,
    )
    enough_components = component_ranks.notna().sum(axis=1) >= 4
    tradeable = frame["tradeable_mask"].fillna(False)
    valid = enough_components & tradeable
    equal_weight = component_ranks.mean(axis=1, skipna=True).where(valid)
    agreement = (component_ranks.gt(0.60).sum(axis=1) / float(component_ranks.shape[1])).where(valid)
    disagreement_risk = (1.0 - component_ranks.std(axis=1, skipna=True) + 0.05 * equal_weight).where(valid)
    regime_allowed = pd.to_numeric(frame["market_momentum_20"], errors="coerce") >= -0.02
    regime_conditioned = equal_weight.where(valid & regime_allowed)
    return {
        "public_anomaly_residual_equal_weight_20": equal_weight,
        "public_anomaly_residual_agreement_20": agreement,
        "public_anomaly_residual_disagreement_risk_20": disagreement_risk,
        "public_anomaly_residual_regime_conditioned_20": regime_conditioned,
    }


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(),
            "lookback_window": 20,
        }
    )


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    ranked = grouped.rank(method="average", pct=True)
    counts = grouped.transform("count")
    return ranked.where(counts > 1)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > _EPSILON)).replace([np.inf, -np.inf], np.nan)


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0.0))


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
