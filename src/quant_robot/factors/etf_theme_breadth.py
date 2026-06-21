from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_THEME_BREADTH_FACTOR_PREFIXES = (
    "theme_momentum_breadth",
    "theme_relative_strength",
    "theme_relative_strength_liquid",
    "theme_rank_strength",
    "theme_rank_strength_liquid",
    "theme_member_leadership",
    "theme_laggard_reversal",
    "theme_risk_adjusted_strength",
    "theme_risk_adjusted_strength_liquid",
)


def etf_theme_breadth_factor_names(windows: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(f"{prefix}_{window}" for window in windows for prefix in ETF_THEME_BREADTH_FACTOR_PREFIXES)


def compute_etf_theme_breadth_factors(
    bars: pd.DataFrame,
    theme_map: pd.DataFrame,
    *,
    windows: tuple[int, ...] = (60,),
    min_theme_members: int = 2,
) -> pd.DataFrame:
    required_bars = ["date", "asset_id", "market", "adj_close"]
    missing_bars = [column for column in required_bars if column not in bars.columns]
    if missing_bars:
        raise ValueError(f"Bars are missing columns for ETF theme breadth factors: {', '.join(missing_bars)}")
    required_theme = ["asset_id", "theme"]
    missing_theme = [column for column in required_theme if column not in theme_map.columns]
    if missing_theme:
        raise ValueError(f"ETF theme map is missing columns: {', '.join(missing_theme)}")
    if min_theme_members < 1:
        raise ValueError("min_theme_members must be positive")
    frame = _bars_with_theme(bars, theme_map)
    if frame.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    pieces = []
    for window in windows:
        pieces.extend(_window_theme_factors(frame, int(window), min_theme_members))
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _bars_with_theme(bars: pd.DataFrame, theme_map: pd.DataFrame) -> pd.DataFrame:
    mapping_columns = ["asset_id", "theme"]
    for optional in ["known_date", "delist_date"]:
        if optional in theme_map.columns:
            mapping_columns.append(optional)
    mapping = theme_map[mapping_columns].drop_duplicates(["asset_id"], keep="first").copy()
    bar_columns = ["date", "asset_id", "market", "adj_close"]
    if "amount" in bars.columns:
        bar_columns.append("amount")
    frame = bars[bar_columns].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.merge(mapping, on="asset_id", how="inner")
    if frame.empty:
        return frame
    frame["theme"] = frame["theme"].fillna("unclassified").astype(str)
    if "known_date" in frame.columns:
        known_date = pd.to_datetime(frame["known_date"], errors="coerce").dt.date
        frame = frame[known_date.isna() | (frame["date"] >= known_date)]
    if "delist_date" in frame.columns:
        delist_date = pd.to_datetime(frame["delist_date"], errors="coerce").dt.date
        frame = frame[delist_date.isna() | (frame["date"] < delist_date)]
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    if "amount" not in frame.columns:
        frame["amount"] = np.nan
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    return frame.dropna(subset=["adj_close"]).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _window_theme_factors(frame: pd.DataFrame, window: int, min_theme_members: int) -> list[pd.DataFrame]:
    enriched = frame.copy()
    grouped_assets = enriched.groupby("asset_id", sort=False)
    enriched["_return"] = grouped_assets["adj_close"].pct_change(fill_method=None)
    enriched["_momentum"] = grouped_assets["adj_close"].transform(lambda values: values / values.shift(window) - 1.0)
    enriched["_volatility"] = grouped_assets["_return"].transform(lambda values: values.rolling(window).std(ddof=0))
    liquidity_window = max(1, min(20, window))
    enriched["_adv_amount"] = grouped_assets["amount"].transform(
        lambda values: values.rolling(liquidity_window, min_periods=1).mean()
    )
    valid = enriched.dropna(subset=["_momentum"])
    if valid.empty:
        return []
    theme_stats = _theme_stats(valid, min_theme_members)
    merged = enriched.merge(theme_stats, on=["date", "market", "theme"], how="left")
    eligible = merged["_eligible_theme"].fillna(False).astype(bool)
    liquid_tiebreak = _liquidity_tiebreak(merged)
    values = {
        f"theme_momentum_breadth_{window}": merged["_theme_positive_ratio"].where(eligible),
        f"theme_relative_strength_{window}": merged["_theme_relative_strength"].where(eligible),
        f"theme_relative_strength_liquid_{window}": (
            merged["_theme_relative_strength"] + 0.05 * liquid_tiebreak
        ).where(eligible),
        f"theme_rank_strength_{window}": merged["_theme_rank_strength"].where(eligible),
        f"theme_rank_strength_liquid_{window}": (
            merged["_theme_rank_strength"] + 0.05 * liquid_tiebreak
        ).where(eligible),
        f"theme_member_leadership_{window}": (merged["_momentum"] - merged["_theme_median_momentum"]).where(eligible),
        f"theme_laggard_reversal_{window}": (merged["_theme_mean_momentum"] - merged["_momentum"]).where(eligible),
        f"theme_risk_adjusted_strength_{window}": merged["_theme_risk_adjusted_strength"].where(eligible),
        f"theme_risk_adjusted_strength_liquid_{window}": (
            merged["_theme_risk_adjusted_strength"] + 0.05 * liquid_tiebreak
        ).where(eligible),
    }
    return [_factor_frame(merged, name, factor_values, window) for name, factor_values in values.items()]


def _theme_stats(valid: pd.DataFrame, min_theme_members: int) -> pd.DataFrame:
    stats = (
        valid.groupby(["date", "market", "theme"], sort=False)
        .agg(
            _theme_mean_momentum=("_momentum", "mean"),
            _theme_median_momentum=("_momentum", "median"),
            _theme_member_count=("_momentum", "count"),
            _theme_positive_ratio=("_momentum", lambda values: float((values > 0.0).mean())),
            _theme_mean_volatility=("_volatility", "mean"),
        )
        .reset_index()
    )
    market_mean = valid.groupby(["date", "market"], sort=False)["_momentum"].mean().rename("_market_mean_momentum")
    stats = stats.merge(market_mean.reset_index(), on=["date", "market"], how="left")
    stats["_theme_relative_strength"] = stats["_theme_mean_momentum"] - stats["_market_mean_momentum"]
    eligible_member_count = stats["_theme_member_count"] >= min_theme_members
    stats["_rank_input"] = stats["_theme_mean_momentum"].where(eligible_member_count)
    stats["_theme_rank_strength"] = stats.groupby(["date", "market"], sort=False)["_rank_input"].rank(pct=True)
    eligible_theme_count = eligible_member_count.groupby([stats["date"], stats["market"]]).transform("sum")
    stats["_eligible_theme"] = eligible_member_count & (eligible_theme_count >= 2)
    denominator = stats["_theme_mean_volatility"].where(stats["_theme_mean_volatility"] > 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        stats["_theme_risk_adjusted_strength"] = (stats["_theme_mean_momentum"] / denominator).replace(
            [np.inf, -np.inf],
            np.nan,
        )
    return stats[
        [
            "date",
            "market",
            "theme",
            "_theme_mean_momentum",
            "_theme_median_momentum",
            "_theme_positive_ratio",
            "_theme_relative_strength",
            "_theme_rank_strength",
            "_theme_risk_adjusted_strength",
            "_eligible_theme",
        ]
    ]


def _liquidity_tiebreak(frame: pd.DataFrame) -> pd.Series:
    adv = pd.to_numeric(frame["_adv_amount"], errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        log_adv = np.log(adv.where(adv > 0.0))
    return _cs_z(frame, log_adv).fillna(0.0)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series, window: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": window,
        }
    )
