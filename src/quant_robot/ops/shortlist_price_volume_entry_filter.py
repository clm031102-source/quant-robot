from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import load_capacity_safe_bars
from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks


STAGE = "shortlist_price_volume_entry_filter"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
DEFAULT_CANDIDATES = (
    "pv_overheat_volume_climax_20d",
    "pv_breakdown_volume_spike_20d",
    "pv_downtrend_high_vol_60d",
    "pv_weak_close_range_expansion_20d",
    "pv_short_squeeze_exhaustion_5d",
)
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)


@dataclass(frozen=True)
class PriceVolumeEntryFilterSpec:
    candidate_name: str
    min_return_5d: float | None = None
    max_return_5d: float | None = None
    min_return_20d: float | None = None
    max_return_20d: float | None = None
    min_return_60d: float | None = None
    max_return_60d: float | None = None
    min_amount_trend_5_20: float | None = None
    max_amount_trend_5_20: float | None = None
    min_close_location_20: float | None = None
    max_close_location_20: float | None = None
    min_hl_range_20: float | None = None
    min_realized_vol_20: float | None = None
    require_close_below_ma20: bool = False
    require_ma20_below_ma60: bool = False


PRICE_VOLUME_ENTRY_FILTER_SPECS: dict[str, PriceVolumeEntryFilterSpec] = {
    "pv_overheat_volume_climax_20d": PriceVolumeEntryFilterSpec(
        candidate_name="pv_overheat_volume_climax_20d",
        min_return_20d=0.20,
        min_amount_trend_5_20=1.50,
        min_close_location_20=0.80,
        min_realized_vol_20=0.025,
    ),
    "pv_breakdown_volume_spike_20d": PriceVolumeEntryFilterSpec(
        candidate_name="pv_breakdown_volume_spike_20d",
        max_return_20d=-0.12,
        min_amount_trend_5_20=1.30,
        max_close_location_20=0.35,
        min_realized_vol_20=0.025,
    ),
    "pv_downtrend_high_vol_60d": PriceVolumeEntryFilterSpec(
        candidate_name="pv_downtrend_high_vol_60d",
        max_return_60d=-0.15,
        min_realized_vol_20=0.030,
        require_close_below_ma20=True,
        require_ma20_below_ma60=True,
    ),
    "pv_weak_close_range_expansion_20d": PriceVolumeEntryFilterSpec(
        candidate_name="pv_weak_close_range_expansion_20d",
        min_hl_range_20=0.040,
        min_amount_trend_5_20=1.20,
        max_close_location_20=0.35,
    ),
    "pv_short_squeeze_exhaustion_5d": PriceVolumeEntryFilterSpec(
        candidate_name="pv_short_squeeze_exhaustion_5d",
        min_return_5d=0.08,
        min_amount_trend_5_20=1.80,
        min_close_location_20=0.85,
        min_realized_vol_20=0.030,
    ),
}


def build_price_volume_entry_filter_audit(
    *,
    template_period_returns: str | Path | pd.DataFrame,
    trades_source: str | Path | pd.DataFrame,
    bars_roots: Iterable[str | Path] | None = None,
    bars_source: str | Path | pd.DataFrame | None = None,
    candidates: Sequence[str] = DEFAULT_CANDIDATES,
    template_return_column: str = "period_return",
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "date",
    trade_signal_date_column: str = "signal_date",
    trade_exit_date_column: str = "exit_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_missing_feature_share: float = 0.10,
    max_unmatched_abs_contribution: float = 0.005,
    require_candidate_improvement: bool = False,
) -> dict[str, Any]:
    template = _load_template_returns(
        template_period_returns,
        return_column=template_return_column,
        date_column=date_column,
    )
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        signal_date_column=trade_signal_date_column,
        exit_date_column=trade_exit_date_column,
    )
    bars = _load_bars_for_trades(
        bars_source=bars_source,
        bars_roots=bars_roots,
        trades=trades,
        signal_date_column=trade_signal_date_column,
    )
    features = _price_volume_feature_frame(bars)
    trade_features, feature_summary = _attach_features(
        trades,
        features,
        signal_date_column=trade_signal_date_column,
    )
    base_metrics = _metrics(
        template,
        candidate_name="official_template_base",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    rows: list[dict[str, Any]] = []
    period_return_frames: dict[str, pd.DataFrame] = {}
    flag_rows: list[dict[str, Any]] = []
    specs = [_resolve_spec(candidate) for candidate in candidates]
    for spec in specs:
        flagged = _flag_trades(trade_features, spec=spec)
        candidate_returns, contribution_summary, flags_for_candidate = _project_to_template(
            template,
            flagged,
            candidate_name=f"cash_{spec.candidate_name}",
            trade_return_column=trade_return_column,
            exit_date_column=trade_exit_date_column,
        )
        period_return_frames[f"cash_{spec.candidate_name}"] = candidate_returns
        flag_rows.extend(flags_for_candidate)
        candidate_metrics = _metrics(
            candidate_returns,
            candidate_name=f"cash_{spec.candidate_name}",
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        metric_diffs = {
            key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key))
            for key in METRIC_KEYS
        }
        blockers = _blockers(
            candidate_metrics,
            base_metrics=base_metrics,
            contribution_summary=contribution_summary,
            feature_summary=feature_summary,
            max_missing_feature_share=max_missing_feature_share,
            max_unmatched_abs_contribution=max_unmatched_abs_contribution,
            require_candidate_improvement=require_candidate_improvement,
        )
        rows.append(
            {
                "candidate_name": f"cash_{spec.candidate_name}",
                "source_flag_name": spec.candidate_name,
                "spec": _spec_payload(spec),
                **contribution_summary,
                "feature_summary": feature_summary,
                "base_metrics": {key: base_metrics.get(key) for key in METRIC_KEYS},
                "candidate_metrics": {key: candidate_metrics.get(key) for key in METRIC_KEYS},
                "metric_diffs": metric_diffs,
                "blockers": blockers,
            }
        )
    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["metric_diffs"]["annualized_return"]),
            -float(row["candidate_metrics"]["overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "template_return_column": template_return_column,
                "trade_return_column": trade_return_column,
                "date_column": date_column,
                "trade_signal_date_column": trade_signal_date_column,
                "trade_exit_date_column": trade_exit_date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_missing_feature_share": float(max_missing_feature_share),
                "max_unmatched_abs_contribution": float(max_unmatched_abs_contribution),
                "require_candidate_improvement": bool(require_candidate_improvement),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "template_date_count": int(len(template)),
                "trade_count": int(len(trades)),
                "feature_row_count": int(len(features)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "base_metrics": base_metrics,
            "feature_summary": feature_summary,
            "rows": rows,
            "flag_rows": flag_rows,
            "period_return_frames": {
                name: _frame_rows(frame)
                for name, frame in period_return_frames.items()
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Official-template projection is a calendar-safety audit, not final simulation evidence.",
            },
        }
    )


def write_price_volume_entry_filter_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    period_return_frames = sanitized.pop("period_return_frames", {})
    (output / "price_volume_entry_filter_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "price_volume_entry_filter_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("flag_rows", [])).to_csv(
        output / "price_volume_entry_filter_flag_rows.csv",
        index=False,
    )
    for candidate_name, rows in period_return_frames.items():
        safe_name = str(candidate_name).replace("/", "_").replace("\\", "_")
        pd.DataFrame(rows).to_csv(output / f"{safe_name}_official_template_period_returns.csv", index=False)


def _load_template_returns(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    missing = [column for column in (date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"template period returns missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    output["period_return"] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return output


def _load_trades(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    signal_date_column: str,
    exit_date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = ["asset_id", signal_date_column, exit_date_column, return_column]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output[signal_date_column] = pd.to_datetime(output[signal_date_column], errors="coerce")
    output[exit_date_column] = pd.to_datetime(output[exit_date_column], errors="coerce")
    output[return_column] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=["asset_id", signal_date_column, exit_date_column]).reset_index(drop=True)
    output["trade_id"] = np.arange(len(output), dtype=int)
    return output


def _load_bars_for_trades(
    *,
    bars_source: str | Path | pd.DataFrame | None,
    bars_roots: Iterable[str | Path] | None,
    trades: pd.DataFrame,
    signal_date_column: str,
) -> pd.DataFrame:
    if bars_source is not None:
        bars = bars_source.copy() if isinstance(bars_source, pd.DataFrame) else _read_frame(Path(bars_source))
    elif bars_roots is not None:
        min_signal = pd.Timestamp(trades[signal_date_column].min())
        max_signal = pd.Timestamp(trades[signal_date_column].max())
        analysis_start = (min_signal - pd.Timedelta(days=140)).date().isoformat()
        analysis_end = max_signal.date().isoformat()
        bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start,
            analysis_end_date=analysis_end,
            include_final_holdout=False,
        )
    else:
        raise ValueError("either bars_source or bars_roots must be provided")
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars]
    if missing:
        raise ValueError(f"bars source missing columns: {', '.join(missing)}")
    output = bars.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str)
    for column in ["adj_close", "high", "low", "amount"]:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.dropna(subset=required)
    trade_assets = set(trades["asset_id"].astype(str))
    max_signal = pd.Timestamp(trades[signal_date_column].max())
    output = output[(output["asset_id"].isin(trade_assets)) & (output["date"] <= max_signal)]
    return (
        output.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _price_volume_feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        returns = close.pct_change()
        rolling_high20 = high.rolling(20, min_periods=10).max()
        rolling_low20 = low.rolling(20, min_periods=10).min()
        range_width = (rolling_high20 - rolling_low20).replace(0, pd.NA)
        prev_close = close.shift(1)
        true_range = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        frame = group[["date", "asset_id", "market"]].copy()
        frame["return_5d"] = close.pct_change(5)
        frame["return_20d"] = close.pct_change(20)
        frame["return_60d"] = close.pct_change(60)
        frame["amount_ma5"] = amount.rolling(5, min_periods=3).mean()
        frame["amount_ma20"] = amount.rolling(20, min_periods=10).mean()
        frame["amount_trend_5_20"] = frame["amount_ma5"] / frame["amount_ma20"].replace(0, pd.NA)
        frame["close_location_20"] = (close - rolling_low20) / range_width
        frame["hl_range_20"] = ((high / low) - 1.0).rolling(20, min_periods=10).mean()
        frame["realized_vol_20"] = returns.rolling(20, min_periods=10).std(ddof=0)
        frame["atr14_to_close"] = true_range.rolling(14, min_periods=7).mean() / close.replace(0, pd.NA)
        frame["ma20"] = close.rolling(20, min_periods=10).mean()
        frame["ma60"] = close.rolling(60, min_periods=30).mean()
        frame["close_below_ma20"] = close < frame["ma20"]
        frame["ma20_below_ma60"] = frame["ma20"] < frame["ma60"]
        frame["adj_close"] = close
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    return pd.concat(pieces, ignore_index=True).replace([float("inf"), float("-inf")], pd.NA)


def _attach_features(
    trades: pd.DataFrame,
    features: pd.DataFrame,
    *,
    signal_date_column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    feature_columns = [
        "return_5d",
        "return_20d",
        "return_60d",
        "amount_trend_5_20",
        "close_location_20",
        "hl_range_20",
        "realized_vol_20",
        "atr14_to_close",
        "close_below_ma20",
        "ma20_below_ma60",
    ]
    join_features = features[["date", "asset_id", *feature_columns]].copy()
    output = trades.merge(
        join_features.rename(columns={"date": signal_date_column}),
        on=["asset_id", signal_date_column],
        how="left",
        validate="many_to_one",
    )
    required_for_any = ["return_20d", "amount_trend_5_20", "close_location_20", "realized_vol_20"]
    has_feature = output[required_for_any].notna().all(axis=1)
    return (
        output,
        {
            "trade_count": int(len(output)),
            "feature_matched_trade_count": int(has_feature.sum()),
            "missing_feature_trade_count": int((~has_feature).sum()),
            "missing_feature_share": float((~has_feature).mean()) if len(output) else 0.0,
        },
    )


def _resolve_spec(candidate_name: str) -> PriceVolumeEntryFilterSpec:
    if candidate_name not in PRICE_VOLUME_ENTRY_FILTER_SPECS:
        raise ValueError(
            f"unsupported price-volume entry filter candidate: {candidate_name}. "
            f"Supported: {', '.join(sorted(PRICE_VOLUME_ENTRY_FILTER_SPECS))}"
        )
    return PRICE_VOLUME_ENTRY_FILTER_SPECS[candidate_name]


def _flag_trades(trade_features: pd.DataFrame, *, spec: PriceVolumeEntryFilterSpec) -> pd.DataFrame:
    mask = pd.Series(True, index=trade_features.index)
    for column, minimum, maximum in (
        ("return_5d", spec.min_return_5d, spec.max_return_5d),
        ("return_20d", spec.min_return_20d, spec.max_return_20d),
        ("return_60d", spec.min_return_60d, spec.max_return_60d),
        ("amount_trend_5_20", spec.min_amount_trend_5_20, spec.max_amount_trend_5_20),
        ("close_location_20", spec.min_close_location_20, spec.max_close_location_20),
        ("hl_range_20", spec.min_hl_range_20, None),
        ("realized_vol_20", spec.min_realized_vol_20, None),
    ):
        values = pd.to_numeric(trade_features[column], errors="coerce")
        if minimum is not None:
            mask &= values >= float(minimum)
        if maximum is not None:
            mask &= values <= float(maximum)
    if spec.require_close_below_ma20:
        mask &= trade_features["close_below_ma20"].fillna(False).astype(bool)
    if spec.require_ma20_below_ma60:
        mask &= trade_features["ma20_below_ma60"].fillna(False).astype(bool)
    return trade_features[mask].copy()


def _project_to_template(
    template: pd.DataFrame,
    flagged: pd.DataFrame,
    *,
    candidate_name: str,
    trade_return_column: str,
    exit_date_column: str,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    template_dates = set(pd.to_datetime(template["date"]))
    contributions = (
        flagged.assign(exit_date=pd.to_datetime(flagged[exit_date_column], errors="coerce"))
        .dropna(subset=["exit_date"])
        .groupby("exit_date", as_index=False)
        .agg(
            flagged_trade_count=("trade_id", "count"),
            flagged_contribution=(trade_return_column, "sum"),
            flagged_abs_contribution=(trade_return_column, lambda values: float(pd.Series(values).abs().sum())),
        )
    )
    contributions["in_template"] = contributions["exit_date"].isin(template_dates)
    matched = contributions[contributions["in_template"]].copy()
    unmatched = contributions[~contributions["in_template"]].copy()
    template_working = template.copy()
    template_working = template_working.merge(
        matched[["exit_date", "flagged_contribution", "flagged_trade_count"]].rename(columns={"exit_date": "date"}),
        on="date",
        how="left",
    )
    template_working["flagged_contribution"] = pd.to_numeric(
        template_working["flagged_contribution"],
        errors="coerce",
    ).fillna(0.0)
    template_working["flagged_trade_count"] = pd.to_numeric(
        template_working["flagged_trade_count"],
        errors="coerce",
    ).fillna(0).astype(int)
    template_working["base_period_return"] = pd.to_numeric(
        template_working["period_return"],
        errors="coerce",
    ).fillna(0.0)
    template_working["period_return"] = template_working["base_period_return"] - template_working["flagged_contribution"]
    template_working["candidate_name"] = candidate_name

    matched_count = int(matched["flagged_trade_count"].sum()) if not matched.empty else 0
    unmatched_count = int(unmatched["flagged_trade_count"].sum()) if not unmatched.empty else 0
    total_count = int(len(flagged))
    matched_contribution = _number(matched["flagged_contribution"].sum()) if not matched.empty else 0.0
    unmatched_contribution = _number(unmatched["flagged_contribution"].sum()) if not unmatched.empty else 0.0
    unmatched_abs_contribution = _number(unmatched["flagged_abs_contribution"].sum()) if not unmatched.empty else 0.0
    total_abs_contribution = _number(contributions["flagged_abs_contribution"].sum()) if not contributions.empty else 0.0
    contribution_summary = {
        "flagged_trade_count": total_count,
        "matched_flagged_trade_count": matched_count,
        "unmatched_flagged_trade_count": unmatched_count,
        "matched_flagged_contribution": matched_contribution,
        "unmatched_flagged_contribution": unmatched_contribution,
        "unmatched_abs_flagged_contribution": unmatched_abs_contribution,
        "total_abs_flagged_contribution": total_abs_contribution,
        "unmatched_abs_contribution_share": (
            unmatched_abs_contribution / total_abs_contribution if total_abs_contribution > 0 else 0.0
        ),
    }
    flag_rows = [
        {
            "candidate_name": candidate_name,
            "exit_date": pd.Timestamp(row.exit_date).date().isoformat(),
            "flagged_trade_count": int(row.flagged_trade_count),
            "flagged_contribution": _number(row.flagged_contribution),
            "flagged_abs_contribution": _number(row.flagged_abs_contribution),
            "in_template": bool(row.in_template),
        }
        for row in contributions.sort_values("flagged_abs_contribution", ascending=False).itertuples(index=False)
    ]
    return (
        _candidate_output_columns(template_working),
        contribution_summary,
        flag_rows,
    )


def _metrics(
    period_returns: pd.DataFrame,
    *,
    candidate_name: str,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    row = summarize_return_blocks(
        period_returns[["date", "period_return"]],
        candidate_name=candidate_name,
        return_column="period_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    return {key: row.get(key) for key in ("candidate_name", "period_count", *METRIC_KEYS)}


def _blockers(
    candidate_metrics: Mapping[str, Any],
    *,
    base_metrics: Mapping[str, Any],
    contribution_summary: Mapping[str, Any],
    feature_summary: Mapping[str, Any],
    max_missing_feature_share: float,
    max_unmatched_abs_contribution: float,
    require_candidate_improvement: bool,
) -> list[str]:
    blockers = []
    if int(contribution_summary.get("flagged_trade_count", 0)) <= 0:
        blockers.append("no_flagged_trades")
    if float(feature_summary.get("missing_feature_share", 0.0)) > float(max_missing_feature_share):
        blockers.append("missing_feature_share_above_limit")
    if float(contribution_summary.get("unmatched_abs_flagged_contribution", 0.0)) > float(max_unmatched_abs_contribution):
        blockers.append("unmatched_flagged_contribution_above_limit")
    if require_candidate_improvement and (
        _number(candidate_metrics.get("annualized_return")) <= _number(base_metrics.get("annualized_return"))
    ):
        blockers.append("candidate_does_not_improve_annualized_return")
    return blockers


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _spec_payload(spec: PriceVolumeEntryFilterSpec) -> dict[str, Any]:
    return {
        key: value
        for key, value in spec.__dict__.items()
        if key == "candidate_name" or value not in (None, False)
    }


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in frame.sort_values("date").itertuples(index=False):
        record = {}
        for column, value in row._asdict().items():
            if column in {"date", "signal_date", "entry_date", "decision_date"} and not pd.isna(value):
                record[column] = pd.Timestamp(value).date().isoformat()
            elif column in {"period_return", "base_period_return", "flagged_contribution"}:
                record[column] = _number(value)
            elif column == "flagged_trade_count":
                record[column] = int(value)
            else:
                record[column] = value
        rows.append(record)
    return rows


def _candidate_output_columns(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        column
        for column in (
            "date",
            "signal_date",
            "entry_date",
            "decision_date",
            "signal_date_count",
            "entry_date_count",
            "period_return",
            "base_period_return",
            "flagged_contribution",
            "flagged_trade_count",
            "filter_name",
            "candidate_name",
        )
        if column in frame
    ]
    if "date" not in columns or "period_return" not in columns:
        raise ValueError("candidate output must contain date and period_return")
    return frame[columns]


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
