from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.factors.public_rsrs import PUBLIC_RSRS_FACTOR_NAMES, compute_public_rsrs_factors
from quant_robot.factors.public_technical import (
    PUBLIC_TECHNICAL_FACTOR_NAMES,
    compute_public_technical_factors,
)
from quant_robot.factors.public_trend_strength_state import (
    PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
    compute_public_trend_strength_state_factors,
)
from quant_robot.factors.public_trend_volume import (
    PUBLIC_TREND_VOLUME_FACTOR_NAMES,
    compute_public_trend_volume_factors,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.public_alpha101_capacity_safe_preregistration import (
    default_public_alpha101_candidate_specs,
)
from quant_robot.ops.public_alpha101_capacity_safe_prescreen import (
    compute_public_alpha101_capacity_safe_factors,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (
    load_public_reference_multi_family_bars,
)


STAGE = "shortlist_public_factor_source"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)

FactorBuilder = Callable[[pd.DataFrame, tuple[str, ...] | None], pd.DataFrame]

PUBLIC_ALPHA101_FACTOR_NAMES = tuple(spec.factor_name for spec in default_public_alpha101_candidate_specs())


def _compute_public_alpha101_factors(bars: pd.DataFrame, factor_names: tuple[str, ...] | None) -> pd.DataFrame:
    requested = set(factor_names or PUBLIC_ALPHA101_FACTOR_NAMES)
    specs = [spec for spec in default_public_alpha101_candidate_specs() if spec.factor_name in requested]
    return compute_public_alpha101_capacity_safe_factors(bars, candidate_specs=specs)


FACTOR_FAMILIES: tuple[tuple[str, tuple[str, ...], FactorBuilder], ...] = (
    ("public_alpha101_capacity_safe", PUBLIC_ALPHA101_FACTOR_NAMES, _compute_public_alpha101_factors),
    ("public_trend_strength_state", PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES, compute_public_trend_strength_state_factors),
    ("public_trend_volume", PUBLIC_TREND_VOLUME_FACTOR_NAMES, compute_public_trend_volume_factors),
    ("public_technical", PUBLIC_TECHNICAL_FACTOR_NAMES, compute_public_technical_factors),
    ("public_rsrs", PUBLIC_RSRS_FACTOR_NAMES, compute_public_rsrs_factors),
)


def build_shortlist_public_factor_source(
    *,
    trades_source: str | Path | pd.DataFrame,
    factor_names: Sequence[str],
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    bars_source: pd.DataFrame | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    trade_signal_date_column: str = "signal_date",
) -> dict[str, Any]:
    requested = _resolve_factor_names(factor_names)
    targets = _load_trade_targets(trades_source, signal_date_column=trade_signal_date_column)
    if bars_source is None:
        bars = load_public_reference_multi_family_bars(
            tuple(Path(root) for root in bars_roots),
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    else:
        bars = bars_source.copy()
    bars = _normalise_bars(bars)
    values = _compute_targeted_public_factor_values(bars, targets, requested)
    coverage_rows = _coverage_rows(values, target_pair_count=len(targets))
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "summary": {
            "target_pair_count": int(len(targets)),
            "requested_factor_count": int(len(requested)),
            "factor_value_rows": int(len(values)),
            "non_null_factor_value_rows": int(values["factor_value"].notna().sum()) if not values.empty else 0,
            "full_coverage_factor_count": int(sum(row["missing_factor_share"] <= 0.0 for row in coverage_rows)),
            "max_missing_factor_share": max((row["missing_factor_share"] for row in coverage_rows), default=0.0),
            "bar_rows": int(len(bars)),
            "bar_asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars and not bars.empty else 0,
        },
        "thresholds": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "include_final_holdout": bool(include_final_holdout),
            "trade_signal_date_column": trade_signal_date_column,
            "bars_roots": [str(Path(root)) for root in bars_roots],
        },
        "coverage_rows": coverage_rows,
        "factor_values": values,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "This only materializes PIT public factor values for shortlist screens; it is not portfolio evidence.",
        },
    }


def write_shortlist_public_factor_source(output_dir: str | Path, result: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    values = result.get("factor_values")
    if not isinstance(values, pd.DataFrame):
        values = pd.DataFrame()
    sanitized = _sanitize({key: value for key, value in result.items() if key != "factor_values"})
    value_path = output / "public_factor_values_for_shortlist.parquet"
    if not values.empty:
        values.to_parquet(value_path, index=False)
    else:
        pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"]).to_parquet(
            value_path,
            index=False,
        )
    sanitized["factor_value_source"] = str(value_path)
    (output / "shortlist_public_factor_source.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("coverage_rows", [])).to_csv(
        output / "shortlist_public_factor_source_coverage.csv",
        index=False,
    )


def supported_public_factor_names() -> tuple[str, ...]:
    names: list[str] = []
    for _, family_names, _ in FACTOR_FAMILIES:
        names.extend(family_names)
    return tuple(names)


def _resolve_factor_names(factor_names: Sequence[str]) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(str(name).strip() for name in factor_names if str(name).strip()))
    if not requested:
        return supported_public_factor_names()
    supported = set(supported_public_factor_names())
    unknown = [name for name in requested if name not in supported]
    if unknown:
        raise ValueError(
            "unsupported public factor names for shortlist source: "
            + ", ".join(unknown)
            + ". Supported: "
            + ", ".join(sorted(supported))
        )
    return requested


def _load_trade_targets(source: str | Path | pd.DataFrame, *, signal_date_column: str) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = ["asset_id", signal_date_column]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades source missing columns for public factor source: {', '.join(missing)}")
    targets = frame[["asset_id", signal_date_column]].copy()
    targets["asset_id"] = targets["asset_id"].astype(str)
    targets["date"] = pd.to_datetime(targets[signal_date_column], errors="coerce")
    return (
        targets.dropna(subset=["asset_id", "date"])
        [["date", "asset_id"]]
        .drop_duplicates()
        .sort_values(["date", "asset_id"])
        .reset_index(drop=True)
    )


def _normalise_bars(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "adj_close", "high", "low", "amount"])
    bars = frame.copy()
    if "adj_close" not in bars and "close" in bars:
        bars["adj_close"] = bars["close"]
    if "market" not in bars:
        bars["market"] = "CN"
    bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
    bars["asset_id"] = bars["asset_id"].astype(str)
    bars["market"] = bars["market"].fillna("CN").astype(str)
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        if column in bars:
            bars[column] = pd.to_numeric(bars[column], errors="coerce")
    return (
        bars.dropna(subset=["date", "asset_id", "market", "adj_close", "high", "low"])
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _compute_requested_public_factors(bars: pd.DataFrame, requested: tuple[str, ...]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    requested_set = set(requested)
    for family_name, family_names, builder in FACTOR_FAMILIES:
        names = tuple(name for name in family_names if name in requested_set)
        if not names:
            continue
        frame = builder(bars, names)
        if frame.empty:
            continue
        pieces.append(_normalise_public_factor_frame(frame, family_name=family_name))
    if not pieces:
        return pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"])
    factors = pd.concat(pieces, ignore_index=True)
    return _finalise_public_factor_frame(factors)


def _compute_targeted_public_factor_values(
    bars: pd.DataFrame,
    targets: pd.DataFrame,
    requested: tuple[str, ...],
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    requested_set = set(requested)
    for family_name, family_names, builder in FACTOR_FAMILIES:
        names = tuple(name for name in family_names if name in requested_set)
        if not names:
            continue
        frame = builder(bars, names)
        if frame.empty:
            frame = pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"])
        else:
            frame = _finalise_public_factor_frame(
                _normalise_public_factor_frame(frame, family_name=family_name)
            )
        pieces.append(_target_public_factor_values(targets, frame, names))
    if not pieces:
        return _target_public_factor_values(
            targets,
            pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"]),
            requested,
        )
    return pd.concat(pieces, ignore_index=True)


def _normalise_public_factor_frame(frame: pd.DataFrame, *, family_name: str) -> pd.DataFrame:
    keep = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in keep if column not in frame]
    if missing:
        raise ValueError(
            f"public factor family {family_name} output missing columns: {', '.join(missing)}"
        )
    out = frame[keep].copy()
    out["public_factor_family"] = family_name
    return out


def _finalise_public_factor_frame(factors: pd.DataFrame) -> pd.DataFrame:
    if factors.empty:
        return pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"])
    factors["date"] = pd.to_datetime(factors["date"], errors="coerce")
    factors["asset_id"] = factors["asset_id"].astype(str)
    factors["public_factor_name"] = factors["factor_name"].astype(str)
    factors["factor_value"] = pd.to_numeric(factors["factor_value"], errors="coerce")
    keep = ["date", "asset_id", "market", "public_factor_family", "public_factor_name", "factor_value"]
    return factors[keep].dropna(subset=["date", "asset_id", "public_factor_name"]).reset_index(drop=True)


def _target_public_factor_values(
    targets: pd.DataFrame,
    factors: pd.DataFrame,
    requested: tuple[str, ...],
) -> pd.DataFrame:
    if targets.empty:
        return pd.DataFrame(columns=["date", "asset_id", "public_factor_name", "factor_value"])
    base = targets.assign(_key=1).merge(
        pd.DataFrame({"public_factor_name": list(requested), "_key": 1}),
        on="_key",
        how="inner",
    ).drop(columns="_key")
    merged = base.merge(
        factors,
        on=["date", "asset_id", "public_factor_name"],
        how="left",
        validate="many_to_one",
    )
    columns = ["date", "asset_id", "public_factor_name", "factor_value"]
    if "market" in merged:
        columns.insert(2, "market")
    if "public_factor_family" in merged:
        columns.insert(3 if "market" in columns else 2, "public_factor_family")
    return merged[columns].sort_values(["public_factor_name", "date", "asset_id"]).reset_index(drop=True)


def _coverage_rows(values: pd.DataFrame, *, target_pair_count: int) -> list[dict[str, Any]]:
    rows = []
    if values.empty:
        return rows
    for factor_name, group in values.groupby("public_factor_name", sort=True):
        matched = int(group["factor_value"].notna().sum())
        rows.append(
            {
                "public_factor_name": str(factor_name),
                "target_pair_count": int(target_pair_count),
                "factor_value_rows": int(len(group)),
                "matched_factor_value_count": matched,
                "missing_factor_value_count": int(len(group) - matched),
                "missing_factor_share": float(1.0 - matched / len(group)) if len(group) else 0.0,
            }
        )
    return rows


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _number(value)
    if isinstance(value, float):
        return _number(value)
    return value
