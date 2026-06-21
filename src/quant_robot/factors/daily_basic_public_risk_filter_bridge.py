from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.factors.daily_basic_smart_money_quality import compute_daily_basic_smart_money_quality_factors
from quant_robot.factors.public_trend_volume import compute_public_trend_volume_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES = (
    "risk_filter_bridge_equal_20",
    "risk_filter_bridge_agreement_20",
    "risk_filter_bridge_anti_obv_weighted_20",
)

_ANTI_OBV_FACTOR = "anti_obv_breakout_low_tail_20"
_SMART_REVERSAL_FACTOR = "smart_money_reversal_value_20"
_EPSILON = 1e-12


def compute_daily_basic_public_risk_filter_bridge_factors(
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

    public_factors = compute_public_trend_volume_factors(bars, factor_names=(_ANTI_OBV_FACTOR,))
    smart_factors = compute_daily_basic_smart_money_quality_factors(
        bars,
        daily_basic_inputs,
        factor_names=(_SMART_REVERSAL_FACTOR,),
    )
    frame = _component_frame(public_factors, smart_factors)
    values_by_name = _bridge_values(frame)
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES
    supported = set(DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(
            "Unsupported daily-basic public risk filter bridge factor_names: "
            + ", ".join(unknown)
        )
    return factor_names


def _component_frame(public_factors: pd.DataFrame, smart_factors: pd.DataFrame) -> pd.DataFrame:
    public = _component(public_factors, _ANTI_OBV_FACTOR, "anti_obv_rank")
    smart = _component(smart_factors, _SMART_REVERSAL_FACTOR, "smart_reversal_rank")
    frame = public.merge(smart, on=["date", "asset_id", "market"], how="outer")
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["anti_obv_rank"] = _cs_rank(frame, frame["anti_obv_rank"])
    frame["smart_reversal_rank"] = _cs_rank(frame, frame["smart_reversal_rank"])
    return frame


def _component(factors: pd.DataFrame, factor_name: str, value_column: str) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(factors, required, "component factors")
    frame = factors[factors["factor_name"] == factor_name].copy()
    if frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", value_column])
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame[value_column] = pd.to_numeric(frame["factor_value"], errors="coerce")
    return frame[["date", "asset_id", "market", value_column]]


def _bridge_values(frame: pd.DataFrame) -> dict[str, pd.Series]:
    anti = pd.to_numeric(frame["anti_obv_rank"], errors="coerce")
    smart = pd.to_numeric(frame["smart_reversal_rank"], errors="coerce")
    both = anti.notna() & smart.notna()
    equal = ((anti + smart) / 2.0).where(both)
    agreement = pd.Series(np.minimum(anti, smart), index=frame.index).where(both)
    anti_weighted = (0.65 * anti + 0.35 * smart).where(both)
    return {
        "risk_filter_bridge_equal_20": equal,
        "risk_filter_bridge_agreement_20": agreement,
        "risk_filter_bridge_anti_obv_weighted_20": anti_weighted,
    }


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    ranked = grouped.rank(method="average", pct=True)
    counts = grouped.transform("count")
    return ranked.where(counts > 1)


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


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
