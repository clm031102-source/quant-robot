from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.storage.atomic import atomic_write_json, atomic_write_text


STAGE = "cn_etf_margin_positioning_source_readiness"
STATUS_READY = "ready_for_margin_positioning_preregistration"
VALUE_COLUMNS = (
    "rzye",
    "rqye",
    "rzmre",
    "rqyl",
    "rzche",
    "rqchl",
    "rqmcl",
    "rzrqye",
)
SAFETY_BOUNDARIES = (
    "factor_generation_allowed",
    "forward_return_read",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


def build_cn_etf_margin_positioning_source_readiness(
    *,
    margin: pd.DataFrame,
    bars: pd.DataFrame,
    trading_sessions: Sequence[str],
    config: Mapping[str, Any],
    config_sha256: str,
) -> dict[str, Any]:
    analysis = config["analysis"]
    thresholds = config["thresholds"]
    start = pd.Timestamp(analysis["start_date"]).normalize()
    end = pd.Timestamp(analysis["end_date"]).normalize()
    holdout = pd.Timestamp(analysis["final_holdout_start"]).normalize()
    sessions = pd.DatetimeIndex(pd.to_datetime(list(trading_sessions))).normalize()
    sessions = sessions.drop_duplicates().sort_values()
    analysis_sessions = sessions[(sessions >= start) & (sessions <= end)]
    next_session = {
        sessions[index]: sessions[index + 1]
        for index in range(len(sessions) - 1)
    }
    if analysis_sessions.empty:
        raise ValueError("validated trading sessions do not cover the analysis window")
    if analysis_sessions[-1] not in next_session:
        raise ValueError("validated trading sessions lack a next session after analysis end")

    frame = _normalise_margin(margin)
    bar_keys = _normalise_bar_keys(bars, start=start, end=end)
    duplicate_rows = int(frame.duplicated(["symbol", "date"]).sum())
    expected_available = frame["date"].map(next_session)
    exact_available = frame["available_date"].eq(expected_available)
    exact_next_session_ratio = float(exact_available.mean()) if len(frame) else 0.0
    same_date_bar = pd.MultiIndex.from_frame(frame[["symbol", "date"]]).isin(
        pd.MultiIndex.from_frame(bar_keys[["symbol", "date"]])
    )
    same_date_bar_ratio = float(same_date_bar.mean()) if len(frame) else 0.0
    numeric = frame[list(VALUE_COLUMNS)]
    valid_numeric = numeric.notna() & numeric.ge(0.0)
    valid_numeric_ratio = (
        float(valid_numeric.to_numpy().mean())
        if valid_numeric.size
        else 0.0
    )
    positive_financing_ratio = (
        float(frame["rzye"].gt(0.0).mean())
        if len(frame)
        else 0.0
    )
    final_holdout_rows = int(
        (frame["date"].ge(holdout) | frame["available_date"].ge(holdout)).sum()
    )
    out_of_window_rows = int(
        (~frame["date"].between(start, end, inclusive="both")).sum()
    )
    invalid_identity_rows = int(
        (
            frame["market"].ne("CN_ETF")
            | frame["source"].ne("tushare_margin_detail")
        ).sum()
    )

    minimum_assets = int(thresholds["minimum_assets_per_date"])
    coverage_rows = []
    by_date = {
        date: group
        for date, group in frame.groupby("date", sort=True)
    }
    for session in analysis_sessions:
        group = by_date.get(session, frame.iloc[0:0])
        numeric_values = group[list(VALUE_COLUMNS)]
        numeric_valid = numeric_values.notna() & numeric_values.ge(0.0)
        coverage_rows.append(
            {
                "date": session.date().isoformat(),
                "rows": int(len(group)),
                "assets": int(group["symbol"].nunique()),
                "positive_financing_balance_ratio": (
                    float(group["rzye"].gt(0.0).mean()) if len(group) else 0.0
                ),
                "valid_nonnegative_numeric_ratio": (
                    float(numeric_valid.to_numpy().mean())
                    if numeric_valid.size
                    else 0.0
                ),
                "qualifies": bool(group["symbol"].nunique() >= minimum_assets),
            }
        )
    coverage = pd.DataFrame(coverage_rows)
    qualifying_dates = int(coverage["qualifies"].sum())
    qualifying_coverage = float(qualifying_dates / len(analysis_sessions))

    blockers: list[str] = []
    if duplicate_rows:
        blockers.append("duplicate_margin_positioning_keys")
    if exact_next_session_ratio < 1.0:
        blockers.append("available_date_not_exact_next_session")
    if same_date_bar_ratio < 1.0:
        blockers.append("same_date_etf_bar_intersection_incomplete")
    if invalid_identity_rows:
        blockers.append("invalid_margin_positioning_identity")
    if out_of_window_rows:
        blockers.append("out_of_analysis_window_rows")
    if final_holdout_rows:
        blockers.append("final_holdout_rows_present")
    if qualifying_coverage < float(
        thresholds["minimum_qualifying_date_coverage"]
    ):
        blockers.append("qualifying_date_coverage_below_minimum")
    if positive_financing_ratio < float(
        thresholds["minimum_positive_financing_balance_ratio"]
    ):
        blockers.append("positive_financing_balance_ratio_below_minimum")
    if valid_numeric_ratio < float(
        thresholds["minimum_valid_nonnegative_numeric_ratio"]
    ):
        blockers.append("valid_nonnegative_numeric_ratio_below_minimum")

    assets_per_date = coverage["assets"] if not coverage.empty else pd.Series(dtype=float)
    result: dict[str, Any] = {
        "stage": STAGE,
        "review_date": config.get("review_date"),
        "status": "blocked" if blockers else STATUS_READY,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_margin_positioning",
        "configuration": {"sha256": config_sha256},
        "analysis": dict(analysis),
        "thresholds": dict(thresholds),
        "summary": {
            "rows": int(len(frame)),
            "assets": int(frame["symbol"].nunique()),
            "analysis_sessions": int(len(analysis_sessions)),
            "observed_dates": int(frame["date"].nunique()),
            "qualifying_dates": qualifying_dates,
            "qualifying_date_coverage": qualifying_coverage,
            "minimum_assets_per_date": int(assets_per_date.min()) if len(assets_per_date) else 0,
            "median_assets_per_date": (
                float(assets_per_date.median()) if len(assets_per_date) else 0.0
            ),
            "maximum_assets_per_date": int(assets_per_date.max()) if len(assets_per_date) else 0,
        },
        "integrity": {
            "duplicate_rows": duplicate_rows,
            "same_date_bar_intersection_ratio": same_date_bar_ratio,
            "exact_next_session_ratio": exact_next_session_ratio,
            "positive_financing_balance_ratio": positive_financing_ratio,
            "valid_nonnegative_numeric_ratio": valid_numeric_ratio,
            "invalid_identity_rows": invalid_identity_rows,
            "out_of_window_rows": out_of_window_rows,
            "final_holdout_rows": final_holdout_rows,
        },
        "date_coverage": coverage_rows,
        "gate": {
            "cleared": not blockers,
            "blockers": blockers,
        },
        "next_direction": (
            "preregister_one_compact_margin_positioning_prescreen"
            if not blockers
            else "repair_or_rotate_cn_etf_source_family"
        ),
    }
    for key in SAFETY_BOUNDARIES:
        result[key] = False
    result["markdown"] = render_cn_etf_margin_positioning_source_readiness(result)
    return result


def write_cn_etf_margin_positioning_source_readiness(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / f"{STAGE}.json",
        "markdown": output / f"{STAGE}.md",
        "date_coverage": output / "date_coverage.csv",
    }
    atomic_write_json(
        paths["json"],
        _sanitize({key: value for key, value in result.items() if key != "markdown"}),
    )
    atomic_write_text(
        paths["markdown"],
        render_cn_etf_margin_positioning_source_readiness(result),
    )
    pd.DataFrame(result.get("date_coverage", [])).sort_values("date").to_csv(
        paths["date_coverage"],
        index=False,
    )
    return paths


def render_cn_etf_margin_positioning_source_readiness(
    result: Mapping[str, Any],
) -> str:
    summary = result.get("summary", {})
    integrity = result.get("integrity", {})
    gate = result.get("gate", {})
    return "\n".join(
        [
            "# CN ETF Margin-Positioning Source Readiness",
            "",
            f"- Status: `{result.get('status', 'blocked')}`",
            f"- Canonical rows: {summary.get('rows', 0)}",
            f"- Assets: {summary.get('assets', 0)}",
            f"- Analysis sessions: {summary.get('analysis_sessions', 0)}",
            f"- Qualifying date coverage: {summary.get('qualifying_date_coverage', 0):.6f}",
            f"- Median assets/date: {summary.get('median_assets_per_date', 0):.2f}",
            f"- Positive financing-balance ratio: {integrity.get('positive_financing_balance_ratio', 0):.6f}",
            f"- Exact next-session ratio: {integrity.get('exact_next_session_ratio', 0):.6f}",
            f"- Blockers: {', '.join(gate.get('blockers', []) or []) or 'none'}",
            "- Factor generation: false",
            "- Forward-return read: false",
            "- Final holdout: sealed",
            "- Live boundary: false",
            "",
        ]
    )


def _normalise_margin(frame: pd.DataFrame) -> pd.DataFrame:
    required = (
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        *VALUE_COLUMNS,
    )
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("margin-positioning data missing columns: " + ", ".join(missing))
    result = frame[list(required)].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["available_date"] = pd.to_datetime(
        result["available_date"],
        errors="raise",
    ).dt.normalize()
    for column in ("asset_id", "symbol", "market", "source"):
        result[column] = result[column].astype(str)
    for column in VALUE_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.sort_values(["date", "symbol"]).reset_index(drop=True)


def _normalise_bar_keys(
    bars: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    required = {"date", "symbol"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError("CN ETF bars missing columns: " + ", ".join(missing))
    result = bars[["date", "symbol"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["symbol"] = result["symbol"].astype(str)
    return (
        result[result["date"].between(start, end, inclusive="both")]
        .drop_duplicates()
        .sort_values(["date", "symbol"])
        .reset_index(drop=True)
    )


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value
