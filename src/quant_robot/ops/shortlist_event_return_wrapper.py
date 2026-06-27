from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks


STAGE = "shortlist_event_return_wrapper"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_event_return_wrapper_audit(
    *,
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    reference_schema_source: str | Path | pd.DataFrame | None = None,
    riskoff_multipliers: Sequence[float] = (1.0,),
    return_column: str | None = None,
    date_column: str = "date",
    decision_date_column: str = "entry_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    target_annual_vol: float = 0.06,
    lookback_events: int = 84,
    min_exposure: float = 0.25,
    max_exposure: float = 1.0,
    reuse_reference_vol_target_exposure: bool = False,
) -> dict[str, Any]:
    reference = _load_reference_schema(reference_schema_source, date_column=date_column)
    rows: list[dict[str, Any]] = []
    events: dict[str, pd.DataFrame] = {}
    for base_name, source in return_sources.items():
        frame, resolved_return_column, resolved_decision_column = _load_return_source(
            source,
            return_column=return_column,
            date_column=date_column,
            decision_date_column=decision_date_column,
        )
        if reuse_reference_vol_target_exposure:
            vol_frame = _apply_reference_vol_target(frame, reference)
        else:
            vol_frame = _apply_vol_target(
                frame,
                periods_per_year=periods_per_year,
                target_annual_vol=target_annual_vol,
                lookback_events=lookback_events,
                min_exposure=min_exposure,
                max_exposure=max_exposure,
            )
        for multiplier in riskoff_multipliers:
            candidate_name = f"{base_name}_vt{int(round(target_annual_vol * 100)):d}_zz500_mult_{float(multiplier):.2f}"
            event_frame = _apply_reference_riskoff(
                vol_frame,
                reference,
                candidate_name=candidate_name,
                riskoff_multiplier=float(multiplier),
            )
            metrics = summarize_return_blocks(
                event_frame[["date", "period_return"]],
                candidate_name=candidate_name,
                return_column="period_return",
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            row = {
                "candidate_name": candidate_name,
                "base_name": str(base_name),
                "source_return_column": resolved_return_column,
                "decision_date_column": resolved_decision_column,
                "riskoff_multiplier": float(multiplier),
                "average_vol_target_exposure": _number(event_frame["vol_target_exposure"].mean()),
                "average_final_exposure": _number(event_frame["final_exposure"].mean()),
                "riskoff_event_share": _number(event_frame["zz500_riskoff"].mean()),
                "event_path": "",
            }
            row.update(
                {
                    key: metrics[key]
                    for key in (
                        "total_return",
                        "annualized_return",
                        "sharpe",
                        "overlap_autocorr_adjusted_sharpe",
                        "max_drawdown",
                        "win_rate",
                        "leave_one_year_min_annualized_return",
                        "leave_one_year_min_overlap_sharpe",
                        "best_month_log_share_of_total",
                        "blockers",
                    )
                }
            )
            rows.append(row)
            events[candidate_name] = event_frame
    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["annualized_return"]),
            -float(row["overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "return_column": return_column or "auto",
            "date_column": date_column,
            "decision_date_column": decision_date_column,
            "periods_per_year": float(periods_per_year),
            "holding_period": int(holding_period),
            "target_annual_vol": float(target_annual_vol),
            "lookback_events": int(lookback_events),
            "min_exposure": float(min_exposure),
            "max_exposure": float(max_exposure),
            "reuse_reference_vol_target_exposure": bool(reuse_reference_vol_target_exposure),
            "riskoff_multipliers": [float(value) for value in riskoff_multipliers],
            "reference_schema_source": str(reference_schema_source) if reference_schema_source is not None else None,
        },
        "summary": {
            "base_count": int(len(return_sources)),
            "candidate_count": int(len(rows)),
            "reference_date_count": int(len(reference)) if reference is not None else 0,
            "best_candidate": rows[0]["candidate_name"] if rows else None,
        },
        "rows": _sanitize(rows),
        "events": events,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Event wrappers are pre-simulation projections; final holdout remains sealed.",
        },
    }


def write_event_return_wrapper_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in audit.get("rows", []):
        candidate_name = str(row["candidate_name"])
        event_path = output / f"{_safe_filename(candidate_name)}_events.csv"
        audit["events"][candidate_name].to_csv(event_path, index=False)
        row = dict(row)
        row["event_path"] = str(event_path)
        rows.append(row)
    sanitized = _sanitize({key: value for key, value in audit.items() if key != "events"})
    sanitized["rows"] = _sanitize(rows)
    (output / "event_return_wrapper_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized["rows"]).to_csv(output / "event_return_wrapper_summary.csv", index=False)


def _load_return_source(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    return_column: str | None,
    date_column: str,
    decision_date_column: str,
) -> tuple[pd.DataFrame, str, str]:
    source_path: str | Path | pd.DataFrame
    resolved_return_column = return_column
    resolved_decision_column = decision_date_column
    if isinstance(source, Mapping) and not isinstance(source, pd.DataFrame):
        source_path = source.get("path")
        if source_path is None:
            raise ValueError("return source spec missing path")
        resolved_return_column = str(source.get("return_column")) if source.get("return_column") else return_column
        resolved_decision_column = str(source.get("decision_date_column") or decision_date_column)
    else:
        source_path = source
    frame = source_path.copy() if isinstance(source_path, pd.DataFrame) else _read_frame(Path(source_path))
    if date_column not in frame:
        raise ValueError(f"return source missing date column: {date_column}")
    resolved_return_column = _resolve_return_column(frame, resolved_return_column)
    if resolved_decision_column not in frame:
        fallback = "decision_date" if "decision_date" in frame else date_column
        resolved_decision_column = fallback
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    output["decision_date"] = pd.to_datetime(output[resolved_decision_column], errors="coerce")
    output["raw_period_return"] = pd.to_numeric(output[resolved_return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    output["decision_date"] = output["decision_date"].fillna(output["date"])
    return output[["date", "decision_date", "raw_period_return"]], resolved_return_column, resolved_decision_column


def _load_reference_schema(source: str | Path | pd.DataFrame | None, *, date_column: str) -> pd.DataFrame | None:
    if source is None:
        return None
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    if date_column not in frame:
        raise ValueError(f"reference schema missing date column: {date_column}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    for column in ("zz500_mom120_before_decision", "zz500_riskoff", "vol_target_exposure"):
        if column not in output:
            output[column] = 1.0 if column == "vol_target_exposure" else (False if column == "zz500_riskoff" else 0.0)
    output["zz500_riskoff"] = output["zz500_riskoff"].astype(bool)
    output["zz500_mom120_before_decision"] = pd.to_numeric(
        output["zz500_mom120_before_decision"],
        errors="coerce",
    ).fillna(0.0)
    output["vol_target_exposure"] = pd.to_numeric(output["vol_target_exposure"], errors="coerce").fillna(1.0)
    return output[["date", "zz500_mom120_before_decision", "zz500_riskoff", "vol_target_exposure"]].dropna(subset=["date"])


def _apply_reference_vol_target(frame: pd.DataFrame, reference: pd.DataFrame | None) -> pd.DataFrame:
    if reference is None or "vol_target_exposure" not in reference:
        raise ValueError("reference_schema_source with vol_target_exposure is required when reusing reference exposure")
    output = frame.merge(reference[["date", "vol_target_exposure"]], on="date", how="left")
    output["vol_target_exposure"] = pd.to_numeric(output["vol_target_exposure"], errors="coerce").fillna(1.0)
    output["vol_target_period_return"] = output["raw_period_return"].astype(float) * output["vol_target_exposure"]
    return output


def _apply_vol_target(
    frame: pd.DataFrame,
    *,
    periods_per_year: float,
    target_annual_vol: float,
    lookback_events: int,
    min_exposure: float,
    max_exposure: float,
) -> pd.DataFrame:
    output = frame.copy()
    target_period_vol = float(target_annual_vol) / math.sqrt(float(periods_per_year))
    min_periods = max(10, int(lookback_events) // 3)
    rolling_vol = output["raw_period_return"].astype(float).rolling(
        int(lookback_events),
        min_periods=min_periods,
    ).std(ddof=1).shift(1)
    exposure = (target_period_vol / rolling_vol.replace(0.0, np.nan)).clip(
        lower=float(min_exposure),
        upper=float(max_exposure),
    ).fillna(1.0)
    output["vol_target_exposure"] = exposure
    output["vol_target_period_return"] = output["raw_period_return"].astype(float) * output["vol_target_exposure"]
    return output


def _apply_reference_riskoff(
    frame: pd.DataFrame,
    reference: pd.DataFrame | None,
    *,
    candidate_name: str,
    riskoff_multiplier: float,
) -> pd.DataFrame:
    output = frame.copy()
    if reference is not None:
        ref_columns = [column for column in ("date", "zz500_mom120_before_decision", "zz500_riskoff") if column in reference]
        output = output.merge(reference[ref_columns], on="date", how="left")
    else:
        output["zz500_mom120_before_decision"] = 0.0
        output["zz500_riskoff"] = False
    output["zz500_riskoff"] = output["zz500_riskoff"].fillna(False).astype(bool)
    output["zz500_mom120_before_decision"] = pd.to_numeric(
        output["zz500_mom120_before_decision"],
        errors="coerce",
    ).fillna(0.0)
    output["candidate"] = candidate_name
    output["riskoff_multiplier"] = float(riskoff_multiplier)
    output["regime_guard_exposure"] = np.where(output["zz500_riskoff"], float(riskoff_multiplier), 1.0)
    output["final_exposure"] = output["vol_target_exposure"] * output["regime_guard_exposure"]
    output["period_return"] = output["vol_target_period_return"] * output["regime_guard_exposure"]
    output["equity"] = (1.0 + output["period_return"]).cumprod()
    peak = output["equity"].cummax().replace(0.0, np.nan)
    output["drawdown"] = (output["equity"] / peak - 1.0).fillna(0.0)
    return output[
        [
            "date",
            "decision_date",
            "candidate",
            "riskoff_multiplier",
            "zz500_mom120_before_decision",
            "zz500_riskoff",
            "regime_guard_exposure",
            "vol_target_exposure",
            "final_exposure",
            "vol_target_period_return",
            "period_return",
            "equity",
            "drawdown",
        ]
    ]


def _resolve_return_column(frame: pd.DataFrame, return_column: str | None) -> str:
    if return_column:
        if return_column not in frame:
            raise ValueError(f"return source missing return column: {return_column}")
        return return_column
    for candidate in ("period_return", "period_return_variant", "overlay_return", "entry_cash_proxy_return"):
        if candidate in frame:
            return candidate
    raise ValueError("return source missing supported return column")


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


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
