from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_official_template_cash_filter import (
    _flag_trades as _flag_dragon_trades,
    _load_dragon_tiger,
    _load_template_returns,
    _load_trades,
    _metrics,
    _project_to_template,
    _resolve_spec as _resolve_dragon_spec,
)


STAGE = "shortlist_public_factor_entry_filter"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)


@dataclass(frozen=True)
class PublicFactorEntryFilterSpec:
    name: str
    public_factor_name: str
    side: str
    quantile: float = 0.20


@dataclass(frozen=True)
class PublicFactorEntryTiltSpec:
    name: str
    public_factor_name: str
    side: str
    quantile: float = 0.20
    exposure_multiplier: float = 1.50


def build_public_factor_entry_filter_audit(
    *,
    template_period_returns: str | Path | pd.DataFrame,
    trades_source: str | Path | pd.DataFrame,
    public_factor_source: str | Path | pd.DataFrame,
    candidates: Sequence[PublicFactorEntryFilterSpec],
    pre_exclude_candidates: Sequence[str] = (),
    dragon_tiger_source: str | Path | pd.DataFrame | None = None,
    template_return_column: str = "period_return",
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "date",
    trade_signal_date_column: str = "signal_date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    lookback_anchor_column: str = "available_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_missing_factor_share: float = 0.20,
    max_unmatched_abs_contribution: float = 0.005,
    require_candidate_improvement: bool = False,
) -> dict[str, Any]:
    template = _load_template_returns(
        template_period_returns,
        return_column=template_return_column,
        date_column=date_column,
    )
    projection_template = template.drop(
        columns=["flagged_contribution", "flagged_trade_count", "base_period_return", "candidate_name"],
        errors="ignore",
    )
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        entry_date_column=trade_entry_date_column,
        exit_date_column=trade_exit_date_column,
    )
    if trade_signal_date_column not in trades:
        raise ValueError(f"trades source missing signal date column: {trade_signal_date_column}")
    trades[trade_signal_date_column] = pd.to_datetime(trades[trade_signal_date_column], errors="coerce")
    trades = trades.dropna(subset=[trade_signal_date_column]).reset_index(drop=True)
    trades["trade_id"] = np.arange(len(trades), dtype=int)

    pre_excluded_ids = _pre_excluded_trade_ids(
        trades,
        pre_exclude_candidates=pre_exclude_candidates,
        dragon_tiger_source=dragon_tiger_source,
        trade_entry_date_column=trade_entry_date_column,
        lookback_anchor_column=lookback_anchor_column,
    )
    candidate_universe = trades[~trades["trade_id"].isin(pre_excluded_ids)].copy()
    factors = _load_public_factor_values(public_factor_source)
    base_metrics = _metrics(
        template,
        candidate_name="official_template_base",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )

    rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    period_return_frames: dict[str, pd.DataFrame] = {}
    for spec in candidates:
        trade_factors, factor_summary = _attach_public_factor(
            candidate_universe,
            factors,
            spec=spec,
            trade_signal_date_column=trade_signal_date_column,
        )
        flagged = _flag_by_factor_quantile(
            trade_factors,
            spec=spec,
            trade_signal_date_column=trade_signal_date_column,
        )
        candidate_name = f"cash_public_{spec.name}"
        candidate_returns, contribution_summary, flags_for_candidate = _project_to_template(
            projection_template,
            flagged,
            candidate_name=candidate_name,
            trade_return_column=trade_return_column,
            exit_date_column=trade_exit_date_column,
        )
        period_return_frames[candidate_name] = candidate_returns
        flag_rows.extend(flags_for_candidate)
        candidate_metrics = _metrics(
            candidate_returns,
            candidate_name=candidate_name,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        metric_diffs = {
            key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key))
            for key in METRIC_KEYS
        }
        rows.append(
            {
                "candidate_name": candidate_name,
                "public_factor_name": spec.public_factor_name,
                "side": spec.side,
                "quantile": float(spec.quantile),
                **contribution_summary,
                "factor_summary": factor_summary,
                "base_metrics": {key: base_metrics.get(key) for key in METRIC_KEYS},
                "candidate_metrics": {key: candidate_metrics.get(key) for key in METRIC_KEYS},
                "metric_diffs": metric_diffs,
                "blockers": _blockers(
                    candidate_metrics,
                    base_metrics=base_metrics,
                    contribution_summary=contribution_summary,
                    factor_summary=factor_summary,
                    max_missing_factor_share=max_missing_factor_share,
                    max_unmatched_abs_contribution=max_unmatched_abs_contribution,
                    require_candidate_improvement=require_candidate_improvement,
                ),
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
                "trade_entry_date_column": trade_entry_date_column,
                "trade_exit_date_column": trade_exit_date_column,
                "lookback_anchor_column": lookback_anchor_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_missing_factor_share": float(max_missing_factor_share),
                "max_unmatched_abs_contribution": float(max_unmatched_abs_contribution),
                "require_candidate_improvement": bool(require_candidate_improvement),
                "pre_exclude_candidates": list(pre_exclude_candidates),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "template_date_count": int(len(template)),
                "trade_count": int(len(trades)),
                "pre_excluded_trade_count": int(len(pre_excluded_ids)),
                "candidate_universe_trade_count": int(len(candidate_universe)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "base_metrics": base_metrics,
            "rows": rows,
            "flag_rows": flag_rows,
            "period_return_frames": {
                name: _frame_rows(frame)
                for name, frame in period_return_frames.items()
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Public-factor selected-entry projections are official-template screens, not final simulation evidence.",
            },
        }
    )


def build_public_factor_entry_tilt_audit(
    *,
    template_period_returns: str | Path | pd.DataFrame,
    trades_source: str | Path | pd.DataFrame,
    public_factor_source: str | Path | pd.DataFrame,
    candidates: Sequence[PublicFactorEntryTiltSpec],
    pre_exclude_candidates: Sequence[str] = (),
    dragon_tiger_source: str | Path | pd.DataFrame | None = None,
    template_return_column: str = "period_return",
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "date",
    trade_signal_date_column: str = "signal_date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    lookback_anchor_column: str = "available_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_missing_factor_share: float = 0.20,
    max_unmatched_abs_contribution: float = 0.005,
    require_candidate_improvement: bool = False,
) -> dict[str, Any]:
    template = _load_template_returns(
        template_period_returns,
        return_column=template_return_column,
        date_column=date_column,
    )
    projection_template = template.drop(
        columns=["flagged_contribution", "flagged_trade_count", "base_period_return", "candidate_name"],
        errors="ignore",
    )
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        entry_date_column=trade_entry_date_column,
        exit_date_column=trade_exit_date_column,
    )
    if trade_signal_date_column not in trades:
        raise ValueError(f"trades source missing signal date column: {trade_signal_date_column}")
    trades[trade_signal_date_column] = pd.to_datetime(trades[trade_signal_date_column], errors="coerce")
    trades = trades.dropna(subset=[trade_signal_date_column]).reset_index(drop=True)
    trades["trade_id"] = np.arange(len(trades), dtype=int)

    pre_excluded_ids = _pre_excluded_trade_ids(
        trades,
        pre_exclude_candidates=pre_exclude_candidates,
        dragon_tiger_source=dragon_tiger_source,
        trade_entry_date_column=trade_entry_date_column,
        lookback_anchor_column=lookback_anchor_column,
    )
    candidate_universe = trades[~trades["trade_id"].isin(pre_excluded_ids)].copy()
    factors = _load_public_factor_values(public_factor_source)
    base_metrics = _metrics(
        template,
        candidate_name="official_template_base",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )

    rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    period_return_frames: dict[str, pd.DataFrame] = {}
    for spec in candidates:
        trade_factors, factor_summary = _attach_public_factor(
            candidate_universe,
            factors,
            spec=PublicFactorEntryFilterSpec(
                name=spec.name,
                public_factor_name=spec.public_factor_name,
                side=spec.side,
                quantile=spec.quantile,
            ),
            trade_signal_date_column=trade_signal_date_column,
        )
        flagged = _flag_by_factor_quantile(
            trade_factors,
            spec=PublicFactorEntryFilterSpec(
                name=spec.name,
                public_factor_name=spec.public_factor_name,
                side=spec.side,
                quantile=spec.quantile,
            ),
            trade_signal_date_column=trade_signal_date_column,
        )
        candidate_name = f"tilt_public_{spec.name}"
        candidate_returns, contribution_summary, flags_for_candidate = _project_to_template(
            projection_template,
            flagged,
            candidate_name=candidate_name,
            trade_return_column=trade_return_column,
            exit_date_column=trade_exit_date_column,
        )
        candidate_returns["period_return"] = (
            candidate_returns["base_period_return"]
            + (float(spec.exposure_multiplier) - 1.0) * candidate_returns["flagged_contribution"]
        )
        candidate_returns["candidate_name"] = candidate_name
        period_return_frames[candidate_name] = candidate_returns
        flag_rows.extend(flags_for_candidate)
        candidate_metrics = _metrics(
            candidate_returns,
            candidate_name=candidate_name,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        metric_diffs = {
            key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key))
            for key in METRIC_KEYS
        }
        rows.append(
            {
                "candidate_name": candidate_name,
                "public_factor_name": spec.public_factor_name,
                "side": spec.side,
                "quantile": float(spec.quantile),
                "exposure_multiplier": float(spec.exposure_multiplier),
                **contribution_summary,
                "factor_summary": factor_summary,
                "base_metrics": {key: base_metrics.get(key) for key in METRIC_KEYS},
                "candidate_metrics": {key: candidate_metrics.get(key) for key in METRIC_KEYS},
                "metric_diffs": metric_diffs,
                "blockers": _blockers(
                    candidate_metrics,
                    base_metrics=base_metrics,
                    contribution_summary=contribution_summary,
                    factor_summary=factor_summary,
                    max_missing_factor_share=max_missing_factor_share,
                    max_unmatched_abs_contribution=max_unmatched_abs_contribution,
                    require_candidate_improvement=require_candidate_improvement,
                ),
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
            "stage": "shortlist_public_factor_entry_tilt",
            "safety": SAFETY,
            "thresholds": {
                "template_return_column": template_return_column,
                "trade_return_column": trade_return_column,
                "date_column": date_column,
                "trade_signal_date_column": trade_signal_date_column,
                "trade_entry_date_column": trade_entry_date_column,
                "trade_exit_date_column": trade_exit_date_column,
                "lookback_anchor_column": lookback_anchor_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_missing_factor_share": float(max_missing_factor_share),
                "max_unmatched_abs_contribution": float(max_unmatched_abs_contribution),
                "require_candidate_improvement": bool(require_candidate_improvement),
                "pre_exclude_candidates": list(pre_exclude_candidates),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "template_date_count": int(len(template)),
                "trade_count": int(len(trades)),
                "pre_excluded_trade_count": int(len(pre_excluded_ids)),
                "candidate_universe_trade_count": int(len(candidate_universe)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "base_metrics": base_metrics,
            "rows": rows,
            "flag_rows": flag_rows,
            "period_return_frames": {
                name: _frame_rows(frame)
                for name, frame in period_return_frames.items()
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Public-factor selected-entry tilt screens require wrapper, OOS, cost, and capacity audits.",
            },
        }
    )


def write_public_factor_entry_filter_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    period_return_frames = sanitized.pop("period_return_frames", {})
    (output / "public_factor_entry_filter_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "public_factor_entry_filter_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("flag_rows", [])).to_csv(
        output / "public_factor_entry_filter_flag_rows.csv",
        index=False,
    )
    for candidate_name, rows in period_return_frames.items():
        safe_name = str(candidate_name).replace("/", "_").replace("\\", "_")
        pd.DataFrame(rows).to_csv(output / f"{safe_name}_official_template_period_returns.csv", index=False)


def write_public_factor_entry_tilt_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    period_return_frames = sanitized.pop("period_return_frames", {})
    (output / "public_factor_entry_tilt_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "public_factor_entry_tilt_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("flag_rows", [])).to_csv(
        output / "public_factor_entry_tilt_flag_rows.csv",
        index=False,
    )
    for candidate_name, rows in period_return_frames.items():
        safe_name = str(candidate_name).replace("/", "_").replace("\\", "_")
        pd.DataFrame(rows).to_csv(output / f"{safe_name}_official_template_period_returns.csv", index=False)


def parse_public_factor_filter_spec(value: str) -> PublicFactorEntryFilterSpec:
    if "=" not in value:
        raise ValueError("candidate spec must use name=public_factor_name:side[:quantile]")
    name, expression = value.split("=", 1)
    parts = [part.strip() for part in expression.split(":") if part.strip()]
    if len(parts) not in {2, 3}:
        raise ValueError("candidate expression must use public_factor_name:side[:quantile]")
    public_factor_name, side = parts[0], parts[1]
    quantile = float(parts[2]) if len(parts) == 3 else 0.20
    if side not in {"top", "bottom"}:
        raise ValueError("side must be 'top' or 'bottom'")
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be above 0 and no more than 0.5")
    return PublicFactorEntryFilterSpec(
        name=name.strip(),
        public_factor_name=public_factor_name,
        side=side,
        quantile=quantile,
    )


def parse_public_factor_tilt_spec(value: str) -> PublicFactorEntryTiltSpec:
    if "=" not in value:
        raise ValueError("tilt spec must use name=public_factor_name:side[:quantile[:multiplier]]")
    name, expression = value.split("=", 1)
    parts = [part.strip() for part in expression.split(":") if part.strip()]
    if len(parts) not in {2, 3, 4}:
        raise ValueError("tilt expression must use public_factor_name:side[:quantile[:multiplier]]")
    public_factor_name, side = parts[0], parts[1]
    quantile = float(parts[2]) if len(parts) >= 3 else 0.20
    multiplier = float(parts[3]) if len(parts) == 4 else 1.50
    if side not in {"top", "bottom"}:
        raise ValueError("side must be 'top' or 'bottom'")
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be above 0 and no more than 0.5")
    if multiplier <= 0.0:
        raise ValueError("multiplier must be positive")
    return PublicFactorEntryTiltSpec(
        name=name.strip(),
        public_factor_name=public_factor_name,
        side=side,
        quantile=quantile,
        exposure_multiplier=multiplier,
    )


def _pre_excluded_trade_ids(
    trades: pd.DataFrame,
    *,
    pre_exclude_candidates: Sequence[str],
    dragon_tiger_source: str | Path | pd.DataFrame | None,
    trade_entry_date_column: str,
    lookback_anchor_column: str,
) -> set[int]:
    if not pre_exclude_candidates:
        return set()
    if dragon_tiger_source is None:
        raise ValueError("dragon_tiger_source is required when pre_exclude_candidates are provided")
    dragon = _load_dragon_tiger(dragon_tiger_source)
    excluded: set[int] = set()
    for candidate in pre_exclude_candidates:
        flagged = _flag_dragon_trades(
            trades,
            dragon,
            spec=_resolve_dragon_spec(candidate),
            entry_date_column=trade_entry_date_column,
            lookback_anchor_column=lookback_anchor_column,
        )
        excluded.update(int(value) for value in flagged["trade_id"].dropna().astype(int).tolist())
    return excluded


def _load_public_factor_values(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = ["date", "asset_id", "public_factor_name", "factor_value"]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"public factor source missing columns: {', '.join(missing)}")
    output = frame[required].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["public_factor_name"] = output["public_factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "public_factor_name"])


def _attach_public_factor(
    trades: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    spec: PublicFactorEntryFilterSpec,
    trade_signal_date_column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    factor = factors[factors["public_factor_name"] == spec.public_factor_name].copy()
    merged = trades.merge(
        factor.rename(columns={"date": trade_signal_date_column}),
        on=["asset_id", trade_signal_date_column],
        how="left",
        validate="many_to_one",
    )
    has_factor = merged["factor_value"].notna()
    return (
        merged,
        {
            "public_factor_name": spec.public_factor_name,
            "candidate_universe_trade_count": int(len(merged)),
            "factor_matched_trade_count": int(has_factor.sum()),
            "missing_factor_trade_count": int((~has_factor).sum()),
            "missing_factor_share": float((~has_factor).mean()) if len(merged) else 0.0,
        },
    )


def _flag_by_factor_quantile(
    trade_factors: pd.DataFrame,
    *,
    spec: PublicFactorEntryFilterSpec,
    trade_signal_date_column: str,
) -> pd.DataFrame:
    working = trade_factors.dropna(subset=["factor_value"]).copy()
    if working.empty:
        return working
    grouped = working.groupby(trade_signal_date_column, sort=False)["factor_value"]
    working["rank_pct"] = grouped.rank(method="first", pct=True)
    if spec.side == "top":
        mask = working["rank_pct"] >= 1.0 - float(spec.quantile)
    elif spec.side == "bottom":
        mask = working["rank_pct"] <= float(spec.quantile)
    else:
        raise ValueError(f"unsupported side: {spec.side}")
    return working[mask].copy()


def _blockers(
    candidate_metrics: Mapping[str, Any],
    *,
    base_metrics: Mapping[str, Any],
    contribution_summary: Mapping[str, Any],
    factor_summary: Mapping[str, Any],
    max_missing_factor_share: float,
    max_unmatched_abs_contribution: float,
    require_candidate_improvement: bool,
) -> list[str]:
    blockers = []
    if int(contribution_summary.get("flagged_trade_count", 0)) <= 0:
        blockers.append("no_flagged_trades")
    if float(factor_summary.get("missing_factor_share", 0.0)) > float(max_missing_factor_share):
        blockers.append("missing_factor_share_above_limit")
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
        rows.append(_sanitize(record))
    return rows


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
