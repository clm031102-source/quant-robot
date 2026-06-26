from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.bottom_exclusion_overlay_audit import (
    build_bottom_exclusion_overlay_audit,
    render_bottom_exclusion_overlay_markdown,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import compute_event_factor_frame
from quant_robot.ops.event_factor_preregistration import (
    EventFactorCandidateSpec,
    default_event_factor_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "share_unlock_bottom_exclusion_overlay_audit"
FACTOR_NAME = "event_share_unlock_pressure_60"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_share_unlock_bottom_exclusion_overlay_audit(
    *,
    event_frames: dict[str, pd.DataFrame] | None = None,
    stock_basic: pd.DataFrame | None = None,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    factor_frame: pd.DataFrame | None = None,
    label_frame: pd.DataFrame | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: Sequence[int] = (5, 20),
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    bottom_quantile: float = 0.2,
    rebalance_interval: int = 5,
    min_dates: int = 5,
    min_overlay_t_stat: float = 2.0,
    min_positive_overlay_rate: float = 0.55,
    min_mean_overlay_excess_return: float = 0.0,
) -> dict[str, Any]:
    if factor_frame is None:
        if event_frames is None or stock_basic is None:
            raise ValueError("event_frames and stock_basic are required when factor_frame is not provided")
        clean_bars = _load_or_prepare_bars(
            bars=bars,
            bars_roots=bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
        factor_frame = compute_event_factor_frame(
            event_frames,
            clean_bars,
            stock_basic,
            candidate_specs=(_share_unlock_spec(),),
            pit_lag_trade_days=pit_lag_trade_days,
        )
    elif bars is None:
        clean_bars = pd.DataFrame()
    else:
        clean_bars = _normalise_bars(bars)

    factor_frame = _filter_date_window(
        _prepare_factor_frame(factor_frame),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = factor_frame[factor_frame["factor_name"] == FACTOR_NAME].reset_index(drop=True)

    if label_frame is None:
        if clean_bars.empty:
            raise ValueError("bars or label_frame is required when labels are not provided")
        label_frame = make_forward_returns(
            clean_bars[["date", "asset_id", "market", "adj_close"]],
            horizons=tuple(int(value) for value in horizons),
            execution_lag=execution_lag,
        )
    label_frame = _filter_labels(
        label_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )

    audit = build_bottom_exclusion_overlay_audit(
        factor_frame,
        label_frame,
        source_report=(
            "share_unlock_pressure_as_bottom_exclusion_overlay; "
            "bottom bucket is highest unlock pressure because factor_value=-unlock_pressure"
        ),
        bottom_quantile=bottom_quantile,
        rebalance_interval=rebalance_interval,
        min_dates=min_dates,
        min_overlay_t_stat=min_overlay_t_stat,
        min_positive_overlay_rate=min_positive_overlay_rate,
        min_mean_overlay_excess_return=min_mean_overlay_excess_return,
    )
    audit.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "factor_under_test": FACTOR_NAME,
            "data_window": {
                "factor_rows": int(len(factor_frame)),
                "label_rows": int(len(label_frame)),
                "min_factor_date": _date_min(factor_frame, "date"),
                "max_factor_date": _date_max(factor_frame, "date"),
                "min_label_date": _date_min(label_frame, "date"),
                "max_label_date": _date_max(label_frame, "date"),
            },
            "holdout_policy": {
                "final_holdout_included": bool(include_final_holdout),
                "analysis_start_date": str(analysis_start_date),
                "analysis_end_date": str(analysis_end_date),
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_overlay_walk_forward_and_final_holdout_readiness_clear",
            },
            "pit_policy": {
                "pit_lag_trade_days": int(pit_lag_trade_days),
                "same_day_event_trading_allowed": False,
                "factor_interpretation": "lower factor_value means higher upcoming unlock pressure",
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "portfolio_grid_allowed": False,
                "reason": "This audit can only identify a possible exclusion overlay. It is not a portfolio, paper, or live signal.",
            },
            "diagnostic_only": True,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    audit["markdown"] = render_share_unlock_bottom_exclusion_overlay_markdown(audit)
    return audit


def write_share_unlock_bottom_exclusion_overlay_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "share_unlock_bottom_exclusion_overlay_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "share_unlock_bottom_exclusion_overlay_audit.md").write_text(
        render_share_unlock_bottom_exclusion_overlay_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("date_audits", [])).to_csv(output_path / "date_audits.csv", index=False)
    pd.DataFrame(audit.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)


def render_share_unlock_bottom_exclusion_overlay_markdown(audit: dict[str, Any]) -> str:
    base = render_bottom_exclusion_overlay_markdown(audit)
    policy = audit.get("promotion_policy", {}) if isinstance(audit.get("promotion_policy"), dict) else {}
    holdout = audit.get("holdout_policy", {}) if isinstance(audit.get("holdout_policy"), dict) else {}
    lines = [
        base.rstrip(),
        "",
        "## Share Unlock Overlay Controls",
        "",
        f"- Factor under test: {audit.get('factor_under_test', FACTOR_NAME)}",
        f"- Promotion allowed: {policy.get('promotion_allowed', False)}",
        f"- Portfolio grid allowed: {policy.get('portfolio_grid_allowed', False)}",
        f"- Final holdout included: {holdout.get('final_holdout_included', False)}",
        f"- Reason: {policy.get('reason', '')}",
    ]
    return "\n".join(lines) + "\n"


def _load_or_prepare_bars(
    *,
    bars: pd.DataFrame | None,
    bars_roots: Iterable[str | Path] | None,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if bars is not None:
        return _normalise_bars(bars)
    if bars_roots is None:
        raise ValueError("bars or bars_roots must be provided")
    return _normalise_bars(
        load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    )


def _share_unlock_spec() -> EventFactorCandidateSpec:
    for spec in default_event_factor_candidate_specs():
        if spec.factor_name == FACTOR_NAME:
            return spec
    raise ValueError(f"Missing default event factor spec: {FACTOR_NAME}")


def _prepare_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"factor_frame missing required columns: {missing}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"]).reset_index(drop=True)


def _filter_labels(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "forward_return"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"label_frame missing required columns: {missing}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["forward_return"] = pd.to_numeric(output["forward_return"], errors="coerce")
    output = _filter_date_window(
        output.dropna(subset=["date", "asset_id", "market", "forward_return"]),
        start_date=start_date,
        end_date=end_date,
        include_final_holdout=include_final_holdout,
    )
    return output.reset_index(drop=True)


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    start = pd.Timestamp(start_date)
    end = pd.Timestamp.max if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= start) & (output["date"] <= end)].reset_index(drop=True)


def _normalise_bars(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "adj_close" not in output.columns and "close" in output.columns:
        output["adj_close"] = output["close"]
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "adj_close"]).reset_index(drop=True)


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else str(value.date())


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else str(value.date())


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return str(value)
    return value
