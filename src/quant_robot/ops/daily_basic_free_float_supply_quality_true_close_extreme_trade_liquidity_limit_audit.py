from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    load_price_basis_audit_bars,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import SAFETY


STAGE = "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit"
DEFAULT_REPAIRED_RERUN_REPORT = Path(
    "data/reports/daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_round138_20260622/"
    "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.json"
)
DEFAULT_MIN_LISTING_DAYS = 120
DEFAULT_MIN_ENTRY_AMOUNT = 10_000_000.0
DEFAULT_LIMIT_DETECTION_RATIO = 0.95
NEXT_EVENT_ADJUSTED_RERUN = (
    "round140_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_or_manual_review"
)
NEXT_HIBERNATE = (
    "round140_daily_basic_free_float_supply_quality_hibernation_or_family_rotation_after_extreme_trade_audit"
)

TRADE_PATH_AUDIT_COLUMNS = [
    "asset_id",
    "market",
    "signal_date",
    "entry_date",
    "exit_date",
    "duplicate_case_rows",
    "case_ids",
    "exchange",
    "symbol",
    "stock_market",
    "list_date",
    "listing_age_at_entry_days",
    "limit_threshold",
    "entry_prev_close",
    "entry_close",
    "entry_high",
    "entry_low",
    "entry_return_from_prev",
    "exit_prev_close",
    "exit_close",
    "exit_high",
    "exit_low",
    "exit_return_from_prev",
    "reported_gross_return_max",
    "computed_close_gross_return",
    "entry_amount",
    "exit_amount",
    "entry_volume",
    "exit_volume",
    "path_min_amount",
    "path_min_volume",
    "path_zero_volume_days",
    "path_suspended_days",
    "entry_limit_up_like",
    "exit_limit_down_like",
    "new_listing_path",
    "bse_path",
    "low_entry_amount_path",
    "metadata_missing",
    "missing_price_path",
    "tradeability_class",
    "blockers",
]
CONCENTRATION_COLUMNS = ["dimension", "value", "unique_trade_path_count", "share"]


def build_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
    *,
    bars_roots: Iterable[str | Path],
    stock_metadata_roots: Iterable[str | Path],
    repaired_rerun_report: dict[str, Any] | str | Path | None = DEFAULT_REPAIRED_RERUN_REPORT,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    min_listing_days: int = DEFAULT_MIN_LISTING_DAYS,
    min_entry_amount: float = DEFAULT_MIN_ENTRY_AMOUNT,
    limit_detection_ratio: float = DEFAULT_LIMIT_DETECTION_RATIO,
) -> dict[str, Any]:
    bars = load_price_basis_audit_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_metadata = load_stock_metadata(stock_metadata_roots)
    result = summarize_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
        extreme_trades=_load_extreme_trades_from_report(repaired_rerun_report),
        bars=bars,
        stock_metadata=stock_metadata,
        min_listing_days=min_listing_days,
        min_entry_amount=min_entry_amount,
        limit_detection_ratio=limit_detection_ratio,
    )
    result["data_window"] = _data_window(bars, stock_metadata)
    result["holdout_policy"] = {
        "final_holdout_included": bool(include_final_holdout),
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round138_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun",
        "source_report": str(repaired_rerun_report or DEFAULT_REPAIRED_RERUN_REPORT),
        "scope": "tradeability audit of true-close extreme trades only; no alpha parameter search",
    }
    result["markdown"] = (
        render_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_markdown(result)
    )
    return result


def summarize_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
    *,
    extreme_trades: Iterable[dict[str, Any]] | pd.DataFrame,
    bars: pd.DataFrame,
    stock_metadata: pd.DataFrame,
    min_listing_days: int = DEFAULT_MIN_LISTING_DAYS,
    min_entry_amount: float = DEFAULT_MIN_ENTRY_AMOUNT,
    limit_detection_ratio: float = DEFAULT_LIMIT_DETECTION_RATIO,
) -> dict[str, Any]:
    trades = _normalise_extreme_trades(extreme_trades)
    clean_bars = _normalise_bars(bars)
    clean_metadata = _normalise_metadata(stock_metadata)
    trade_path_audit = _trade_path_audit(
        trades,
        clean_bars,
        clean_metadata,
        min_listing_days=min_listing_days,
        min_entry_amount=min_entry_amount,
        limit_detection_ratio=limit_detection_ratio,
    )
    concentration = _concentration_rows(trade_path_audit)
    summary = _summary(trades, trade_path_audit, concentration)
    gate = _gate(summary)
    next_direction = (
        NEXT_EVENT_ADJUSTED_RERUN
        if int(summary.get("no_obvious_tradeability_blocker_unique_paths", 0)) > 0
        else NEXT_HIBERNATE
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "thresholds": {
            "min_listing_days": int(min_listing_days),
            "min_entry_amount": float(min_entry_amount),
            "limit_detection_ratio": float(limit_detection_ratio),
            "bse_limit_threshold": 0.30,
            "star_chinext_limit_threshold": 0.20,
            "main_board_limit_threshold": 0.10,
        },
        "summary": summary,
        "gate": gate,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": gate["blockers"]
            + [
                "extreme_trade_audit_is_not_a_promotion_test",
                "event_adjusted_clean_rerun_required",
                "final_holdout_not_read",
                "paper_ready_requires_clean_oos_cost_capacity_regime_validation",
            ],
            "reason": (
                "High total return is useful only after the return path is tradable. "
                "This audit separates real trade paths from repeated parameter rows and flags limit, listing-age, "
                "BSE-permission, and liquidity risks before any promotion decision."
            ),
        },
        "trade_path_audit": trade_path_audit,
        "concentration": concentration,
        "next_direction": next_direction,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = (
        render_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_markdown(result)
    )
    return result


def load_stock_metadata(stock_metadata_roots: Iterable[str | Path]) -> pd.DataFrame:
    files: list[Path] = []
    for root in stock_metadata_roots:
        root_path = Path(root)
        files.extend(
            file
            for file in sorted(root_path.rglob("*.parquet"))
            if "stock_basic" in str(file).replace("\\", "/")
        )
        files.extend(
            file
            for file in sorted(root_path.rglob("*.csv"))
            if "stock_basic" in str(file).replace("\\", "/")
        )
    frames = [_read_metadata_file(file) for file in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["asset_id", "symbol", "market", "exchange", "stock_market", "list_date"])
    return _normalise_metadata(pd.concat(frames, ignore_index=True))


def write_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (
        output_path
        / "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.json"
    ).write_text(json.dumps(_sanitize(result), indent=2, sort_keys=True), encoding="utf-8")
    (
        output_path
        / "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.md"
    ).write_text(
        render_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_true_close_extreme_trade_path_audit.csv",
        result.get("trade_path_audit", []),
        TRADE_PATH_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_true_close_extreme_trade_concentration.csv",
        result.get("concentration", []),
        CONCENTRATION_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality True-Close Extreme Trade Liquidity/Limit Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Raw extreme trade rows: {summary.get('raw_extreme_trade_count', 0)}",
        f"- Unique trade paths: {summary.get('unique_trade_path_count', 0)}",
        f"- Entry limit-up-like paths: {summary.get('entry_limit_up_like_unique_paths', 0)}",
        f"- Exit limit-down-like paths: {summary.get('exit_limit_down_like_unique_paths', 0)}",
        f"- New-listing paths: {summary.get('new_listing_unique_paths', 0)}",
        f"- BSE paths: {summary.get('bse_unique_paths', 0)}",
        f"- Low entry-amount paths: {summary.get('low_entry_amount_unique_paths', 0)}",
        f"- No-obvious-blocker paths: {summary.get('no_obvious_tradeability_blocker_unique_paths', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_HIBERNATE)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Thresholds",
        "",
        f"- Min listing age: {thresholds.get('min_listing_days')} calendar days",
        f"- Min entry amount: {thresholds.get('min_entry_amount')}",
        f"- Limit detection ratio: {thresholds.get('limit_detection_ratio')}",
        "",
        "## Gate",
        "",
        f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
        f"- Observations: {', '.join(gate.get('observations', [])) if gate.get('observations') else 'none'}",
        "",
        "## Top Trade Paths",
        "",
        "| Asset | Entry | Exit | DupRows | Gross | CloseRet | EntryAmt | Class | Blockers |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("trade_path_audit", [])[:25]:
        lines.append(
            "| {asset} | {entry} | {exit} | {dup} | {gross:.2%} | {close_ret:.2%} | {amount:.0f} | {klass} | {blockers} |".format(
                asset=row.get("asset_id", ""),
                entry=row.get("entry_date", ""),
                exit=row.get("exit_date", ""),
                dup=int(_number(row.get("duplicate_case_rows"))),
                gross=_number(row.get("reported_gross_return_max")),
                close_ret=_number(row.get("computed_close_gross_return")),
                amount=_number(row.get("entry_amount")),
                klass=row.get("tradeability_class", ""),
                blockers=";".join(row.get("blockers", [])) if isinstance(row.get("blockers"), list) else row.get("blockers", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The drawdown tolerance can be relaxed only after the trade path is clean.",
            "- Repeated parameter rows are deduped into one real trade path before judging signal value.",
            "- Paths without obvious blockers must be rerun with event-adjusted, tradability-clean execution rules.",
        ]
    )
    return "\n".join(lines) + "\n"


def _trade_path_audit(
    trades: pd.DataFrame,
    bars: pd.DataFrame,
    stock_metadata: pd.DataFrame,
    *,
    min_listing_days: int,
    min_entry_amount: float,
    limit_detection_ratio: float,
) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    grouped_bars = {
        str(asset_id): group.sort_values("date").reset_index(drop=True)
        for asset_id, group in bars[bars["asset_id"].isin(set(trades["asset_id"]))].groupby("asset_id", sort=False)
    }
    metadata_lookup = {
        str(row.asset_id): row for row in stock_metadata.drop_duplicates("asset_id", keep="last").itertuples(index=False)
    }
    rows = []
    for _, group in trades.groupby(["asset_id", "signal_date", "entry_date", "exit_date"], sort=True, dropna=False):
        rows.append(
            _audit_one_trade_path(
                group,
                grouped_bars=grouped_bars,
                metadata_lookup=metadata_lookup,
                min_listing_days=min_listing_days,
                min_entry_amount=min_entry_amount,
                limit_detection_ratio=limit_detection_ratio,
            )
        )
    rows.sort(
        key=lambda row: (
            -abs(_number(row.get("reported_gross_return_max"))),
            str(row.get("asset_id", "")),
            str(row.get("entry_date", "")),
        )
    )
    return rows


def _audit_one_trade_path(
    path_rows: pd.DataFrame,
    *,
    grouped_bars: dict[str, pd.DataFrame],
    metadata_lookup: dict[str, Any],
    min_listing_days: int,
    min_entry_amount: float,
    limit_detection_ratio: float,
) -> dict[str, Any]:
    trade = path_rows.iloc[0].to_dict()
    asset_id = str(trade.get("asset_id", ""))
    entry_date = _date_str(trade.get("entry_date"))
    exit_date = _date_str(trade.get("exit_date"))
    signal_date = _date_str(trade.get("signal_date"))
    group = grouped_bars.get(asset_id, pd.DataFrame())
    metadata = metadata_lookup.get(asset_id)
    exchange = _exchange_for(asset_id, metadata)
    symbol = str(getattr(metadata, "symbol", "") if metadata is not None else "")
    stock_market = str(getattr(metadata, "stock_market", "") if metadata is not None else "")
    list_date = _date_str(getattr(metadata, "list_date", "")) if metadata is not None else ""
    limit_threshold = _limit_threshold(asset_id, exchange)
    entry = _bar_on(group, entry_date)
    exit_ = _bar_on(group, exit_date)
    prev_entry = _previous_bar(group, entry_date)
    prev_exit = _previous_bar(group, exit_date)
    window = _window(group, entry_date, exit_date)
    missing_price_path = entry is None or exit_ is None or prev_entry is None

    entry_close = _bar_number(entry, "close")
    exit_close = _bar_number(exit_, "close")
    entry_prev_close = _bar_number(prev_entry, "close")
    exit_prev_close = _bar_number(prev_exit, "close")
    entry_return = _safe_return(entry_close, entry_prev_close)
    exit_return = _safe_return(exit_close, exit_prev_close)
    entry_amount = _first_positive(_bar_number(entry, "amount"), _number(trade.get("entry_amount")))
    entry_volume = _bar_number(entry, "volume")
    exit_amount = _bar_number(exit_, "amount")
    exit_volume = _bar_number(exit_, "volume")
    path_min_amount = _path_min(window, "amount")
    path_min_volume = _path_min(window, "volume")
    path_zero_volume_days = _path_nonpositive_count(window, "volume")
    path_suspended_days = _path_truthy_count(window, "suspended")
    entry_limit_up_like = _is_limit_up_like(
        entry,
        prev_entry,
        threshold=limit_threshold,
        detection_ratio=limit_detection_ratio,
    )
    exit_limit_down_like = _is_limit_down_like(
        exit_,
        prev_exit,
        threshold=limit_threshold,
        detection_ratio=limit_detection_ratio,
    )
    listing_age = _listing_age(entry_date, list_date)
    new_listing_path = listing_age is not None and listing_age < int(min_listing_days)
    bse_path = exchange == "XBEI" or str(symbol).upper().endswith(".BJ")
    low_entry_amount_path = entry_amount > 0.0 and entry_amount < float(min_entry_amount)
    metadata_missing = metadata is None
    computed_return = _safe_return(exit_close, entry_close)
    reported_return = _path_abs_max(path_rows, "gross_return")

    blockers = []
    if missing_price_path:
        blockers.append("missing_entry_exit_or_previous_bar")
    if metadata_missing:
        blockers.append("stock_metadata_missing")
    if entry_limit_up_like:
        blockers.append("entry_limit_up_buy_execution_risk")
    if exit_limit_down_like:
        blockers.append("exit_limit_down_sell_execution_risk")
    if path_suspended_days > 0:
        blockers.append("suspended_path_execution_risk")
    if path_zero_volume_days > 0:
        blockers.append("zero_volume_path_execution_risk")
    if new_listing_path:
        blockers.append("new_listing_age_below_min")
    if bse_path:
        blockers.append("bse_execution_permission_and_limit_regime_risk")
    if low_entry_amount_path:
        blockers.append("low_entry_amount_liquidity_risk")

    tradeability_class = _tradeability_class(blockers)
    return _sanitize(
        {
            "asset_id": asset_id,
            "market": str(trade.get("market", "CN") or "CN"),
            "signal_date": signal_date,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "duplicate_case_rows": int(len(path_rows)),
            "case_ids": sorted(str(value) for value in path_rows.get("case_id", pd.Series(dtype=str)).dropna().unique()),
            "exchange": exchange,
            "symbol": symbol,
            "stock_market": stock_market,
            "list_date": list_date,
            "listing_age_at_entry_days": listing_age,
            "limit_threshold": limit_threshold,
            "entry_prev_close": entry_prev_close,
            "entry_close": entry_close,
            "entry_high": _bar_number(entry, "high"),
            "entry_low": _bar_number(entry, "low"),
            "entry_return_from_prev": entry_return,
            "exit_prev_close": exit_prev_close,
            "exit_close": exit_close,
            "exit_high": _bar_number(exit_, "high"),
            "exit_low": _bar_number(exit_, "low"),
            "exit_return_from_prev": exit_return,
            "reported_gross_return_max": reported_return,
            "computed_close_gross_return": computed_return,
            "entry_amount": entry_amount,
            "exit_amount": exit_amount,
            "entry_volume": entry_volume,
            "exit_volume": exit_volume,
            "path_min_amount": path_min_amount,
            "path_min_volume": path_min_volume,
            "path_zero_volume_days": path_zero_volume_days,
            "path_suspended_days": path_suspended_days,
            "entry_limit_up_like": entry_limit_up_like,
            "exit_limit_down_like": exit_limit_down_like,
            "new_listing_path": new_listing_path,
            "bse_path": bse_path,
            "low_entry_amount_path": low_entry_amount_path,
            "metadata_missing": metadata_missing,
            "missing_price_path": missing_price_path,
            "tradeability_class": tradeability_class,
            "blockers": _dedupe(blockers),
        }
    )


def _summary(
    trades: pd.DataFrame,
    trade_path_audit: list[dict[str, Any]],
    concentration: list[dict[str, Any]],
) -> dict[str, Any]:
    unique_count = len(trade_path_audit)
    no_obvious = sum(1 for row in trade_path_audit if not row.get("blockers"))
    blocked_rows = [row for row in trade_path_audit if row.get("blockers")]
    summary = {
        "raw_extreme_trade_count": int(len(trades)),
        "unique_trade_path_count": int(unique_count),
        "deduped_repeated_parameter_rows": int(max(len(trades) - unique_count, 0)),
        "entry_limit_up_like_unique_paths": _count_bool(trade_path_audit, "entry_limit_up_like"),
        "exit_limit_down_like_unique_paths": _count_bool(trade_path_audit, "exit_limit_down_like"),
        "new_listing_unique_paths": _count_bool(trade_path_audit, "new_listing_path"),
        "bse_unique_paths": _count_bool(trade_path_audit, "bse_path"),
        "low_entry_amount_unique_paths": _count_bool(trade_path_audit, "low_entry_amount_path"),
        "metadata_missing_unique_paths": _count_bool(trade_path_audit, "metadata_missing"),
        "missing_price_path_unique_paths": _count_bool(trade_path_audit, "missing_price_path"),
        "zero_volume_unique_paths": sum(1 for row in trade_path_audit if int(row.get("path_zero_volume_days", 0)) > 0),
        "suspended_unique_paths": sum(1 for row in trade_path_audit if int(row.get("path_suspended_days", 0)) > 0),
        "blocked_unique_paths": int(len(blocked_rows)),
        "no_obvious_tradeability_blocker_unique_paths": int(no_obvious),
        "raw_rows_represented_by_blocked_paths": int(sum(int(row.get("duplicate_case_rows", 0)) for row in blocked_rows)),
        "max_duplicate_case_rows_on_single_path": int(
            max((int(row.get("duplicate_case_rows", 0)) for row in trade_path_audit), default=0)
        ),
        "max_abs_reported_gross_return": _max_abs(trade_path_audit, "reported_gross_return_max"),
        "max_abs_computed_close_gross_return": _max_abs(trade_path_audit, "computed_close_gross_return"),
        "top_concentration": concentration[:6],
    }
    summary["all_unique_paths_have_tradeability_blocker"] = bool(unique_count > 0 and no_obvious == 0)
    return summary


def _gate(summary: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    observations = []
    if int(summary.get("raw_extreme_trade_count", 0)) <= 0:
        blockers.append("no_extreme_trade_rows_to_audit")
    if int(summary.get("missing_price_path_unique_paths", 0)) > 0:
        blockers.append("missing_price_path_for_extreme_trade")
    if int(summary.get("metadata_missing_unique_paths", 0)) > 0:
        blockers.append("stock_metadata_missing_for_extreme_trade")
    if int(summary.get("entry_limit_up_like_unique_paths", 0)) > 0:
        blockers.append("entry_limit_up_buy_execution_risk")
    if int(summary.get("exit_limit_down_like_unique_paths", 0)) > 0:
        blockers.append("exit_limit_down_sell_execution_risk")
    if int(summary.get("new_listing_unique_paths", 0)) > 0:
        blockers.append("new_listing_extreme_trade_risk")
    if int(summary.get("bse_unique_paths", 0)) > 0:
        blockers.append("bse_execution_permission_and_limit_regime_risk")
    if int(summary.get("low_entry_amount_unique_paths", 0)) > 0:
        blockers.append("low_entry_amount_liquidity_risk")
    if int(summary.get("no_obvious_tradeability_blocker_unique_paths", 0)) > 0:
        observations.append("no_obvious_blocker_extreme_paths_require_event_adjusted_rerun")
    if int(summary.get("deduped_repeated_parameter_rows", 0)) > 0:
        observations.append("repeated_parameter_rows_do_not_count_as_independent_alpha")
    return {
        "passes": False,
        "blockers": _dedupe(blockers),
        "observations": observations,
        "required_before_next_mining": [
            "dedupe_extreme_trades_by_asset_signal_entry_exit_path",
            "rerun_no_obvious_blocker_paths_with_event_adjusted_execution",
            "exclude_or_separately_gate_limit_new_listing_bse_and_low_liquidity_paths",
        ],
    }


def _concentration_rows(trade_path_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for dimension in ["asset_id", "exit_date", "entry_date"]:
        counts: dict[str, int] = {}
        for row in trade_path_audit:
            value = str(row.get(dimension, ""))
            counts[value] = counts.get(value, 0) + 1
        total = max(len(trade_path_audit), 1)
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]:
            rows.append(
                {
                    "dimension": dimension,
                    "value": value,
                    "unique_trade_path_count": int(count),
                    "share": float(count / total),
                }
            )
    rows.sort(key=lambda row: (-int(row["unique_trade_path_count"]), str(row["dimension"]), str(row["value"])))
    return rows


def _normalise_extreme_trades(extreme_trades: Iterable[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(extreme_trades, pd.DataFrame):
        frame = extreme_trades.copy()
    else:
        frame = pd.DataFrame(list(extreme_trades or []))
    if frame.empty:
        return pd.DataFrame(columns=["case_id", "asset_id", "market", "signal_date", "entry_date", "exit_date"])
    for column in ["case_id", "asset_id", "market"]:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    for column in ["signal_date", "entry_date", "exit_date"]:
        if column not in frame:
            frame[column] = ""
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date.astype(str)
    for column in [
        "gross_return",
        "net_return",
        "weighted_return",
        "target_notional",
        "entry_amount",
        "participation_rate",
    ]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.reset_index(drop=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["close", "high", "low", "amount", "volume"]:
        if column not in frame:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["high"] = frame["high"].fillna(frame["close"])
    frame["low"] = frame["low"].fillna(frame["close"])
    if "suspended" not in frame:
        frame["suspended"] = False
    if "limit_up" not in frame:
        frame["limit_up"] = False
    if "limit_down" not in frame:
        frame["limit_down"] = False
    frame = frame.dropna(subset=["date", "asset_id", "market", "close"])
    frame = frame[(frame["market"] == "CN") & (frame["close"] > 0)].copy()
    return (
        frame.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _normalise_metadata(stock_metadata: pd.DataFrame) -> pd.DataFrame:
    frame = stock_metadata.copy()
    for column in ["asset_id", "symbol", "market", "exchange", "stock_market", "list_date", "delist_date"]:
        if column not in frame:
            frame[column] = ""
    if frame.empty:
        return frame[["asset_id", "symbol", "market", "exchange", "stock_market", "list_date", "delist_date"]]
    frame["asset_id"] = frame["asset_id"].fillna("").astype(str)
    for column in ["symbol", "market", "exchange", "stock_market"]:
        frame[column] = frame[column].fillna("").astype(str)
    for column in ["list_date", "delist_date"]:
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date.astype(str).replace("NaT", "")
    return frame.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def _read_metadata_file(file: Path) -> pd.DataFrame:
    wanted = ["asset_id", "symbol", "market", "exchange", "name", "stock_market", "list_date", "delist_date"]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=wanted)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in wanted if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in wanted if column in frame.columns]]


def _load_extreme_trades_from_report(repaired_rerun_report: dict[str, Any] | str | Path | None) -> list[dict[str, Any]]:
    if repaired_rerun_report is None:
        repaired_rerun_report = DEFAULT_REPAIRED_RERUN_REPORT
    if isinstance(repaired_rerun_report, (str, Path)):
        path = Path(repaired_rerun_report)
        if not path.exists():
            raise FileNotFoundError(f"Repaired rerun report not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = dict(repaired_rerun_report)
    return list(payload.get("extreme_trades", []))


def _bar_on(group: pd.DataFrame, date_value: str) -> Any | None:
    if group.empty:
        return None
    rows = group[group["date"] == pd.Timestamp(date_value)]
    if rows.empty:
        return None
    return rows.iloc[-1]


def _previous_bar(group: pd.DataFrame, date_value: str) -> Any | None:
    if group.empty:
        return None
    rows = group[group["date"] < pd.Timestamp(date_value)].tail(1)
    if rows.empty:
        return None
    return rows.iloc[-1]


def _window(group: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if group.empty:
        return group
    return group[(group["date"] >= pd.Timestamp(start)) & (group["date"] <= pd.Timestamp(end))].copy()


def _is_limit_up_like(bar: Any | None, previous: Any | None, *, threshold: float, detection_ratio: float) -> bool:
    if bar is None or previous is None:
        return False
    if _truthy(getattr(bar, "limit_up", False)):
        return True
    close = _bar_number(bar, "close")
    high = _bar_number(bar, "high")
    prev_close = _bar_number(previous, "close")
    if close <= 0.0 or high <= 0.0 or prev_close <= 0.0:
        return False
    return bool(close / prev_close - 1.0 >= threshold * detection_ratio and close >= high * (1.0 - 1e-6))


def _is_limit_down_like(bar: Any | None, previous: Any | None, *, threshold: float, detection_ratio: float) -> bool:
    if bar is None or previous is None:
        return False
    if _truthy(getattr(bar, "limit_down", False)):
        return True
    close = _bar_number(bar, "close")
    low = _bar_number(bar, "low")
    prev_close = _bar_number(previous, "close")
    if close <= 0.0 or low <= 0.0 or prev_close <= 0.0:
        return False
    return bool(close / prev_close - 1.0 <= -threshold * detection_ratio and close <= low * (1.0 + 1e-6))


def _limit_threshold(asset_id: str, exchange: str) -> float:
    code = str(asset_id).split("_")[-1]
    if exchange == "XBEI":
        return 0.30
    if code.startswith(("688", "300", "301")):
        return 0.20
    return 0.10


def _exchange_for(asset_id: str, metadata: Any | None) -> str:
    if metadata is not None:
        exchange = str(getattr(metadata, "exchange", "") or "").upper()
        if exchange:
            return exchange
    parts = str(asset_id).split("_")
    return parts[1].upper() if len(parts) >= 3 else ""


def _listing_age(entry_date: str, list_date: str) -> int | None:
    entry = pd.to_datetime(entry_date, errors="coerce")
    listed = pd.to_datetime(list_date, errors="coerce")
    if pd.isna(entry) or pd.isna(listed):
        return None
    return int((entry.date() - listed.date()).days)


def _tradeability_class(blockers: list[str]) -> str:
    if not blockers:
        return "no_obvious_tradeability_blocker"
    priority = [
        ("missing_entry_exit_or_previous_bar", "missing_price_path"),
        ("entry_limit_up_buy_execution_risk", "entry_limit_up_buy_execution_risk"),
        ("exit_limit_down_sell_execution_risk", "exit_limit_down_sell_execution_risk"),
        ("suspended_path_execution_risk", "suspended_path_execution_risk"),
        ("zero_volume_path_execution_risk", "zero_volume_path_execution_risk"),
        ("new_listing_age_below_min", "new_listing_extreme_trade_risk"),
        ("bse_execution_permission_and_limit_regime_risk", "bse_extreme_trade_risk"),
        ("low_entry_amount_liquidity_risk", "low_entry_amount_liquidity_risk"),
        ("stock_metadata_missing", "stock_metadata_missing"),
    ]
    for blocker, klass in priority:
        if blocker in blockers:
            return klass
    return "blocked_tradeability_path"


def _data_window(bars: pd.DataFrame, stock_metadata: pd.DataFrame) -> dict[str, Any]:
    clean_bars = _normalise_bars(bars)
    return {
        "min_bar_date": _min_date(clean_bars),
        "max_bar_date": _max_date(clean_bars),
        "bar_rows": int(len(clean_bars)),
        "bar_assets": int(clean_bars["asset_id"].nunique()) if not clean_bars.empty else 0,
        "stock_metadata_rows": int(len(stock_metadata)),
        "stock_metadata_assets": int(stock_metadata["asset_id"].nunique()) if "asset_id" in stock_metadata else 0,
    }


def _path_abs_max(frame: pd.DataFrame, column: str) -> float:
    if column not in frame:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return 0.0
    index = values.abs().idxmax()
    return _number(values.loc[index])


def _path_min(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return 0.0
    return _number(values.min())


def _path_nonpositive_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return int((values <= 0.0).sum())


def _path_truthy_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    return int(sum(_truthy(value) for value in frame[column]))


def _bar_number(bar: Any | None, column: str) -> float:
    if bar is None:
        return 0.0
    if isinstance(bar, pd.Series):
        return _number(bar.get(column, 0.0))
    return _number(getattr(bar, column, 0.0))


def _safe_return(end: float, start: float) -> float:
    if start <= 0.0:
        return 0.0
    return float(end / start - 1.0)


def _first_positive(*values: float) -> float:
    for value in values:
        number = _number(value)
        if number > 0.0:
            return number
    return 0.0


def _count_bool(rows: list[dict[str, Any]], key: str) -> int:
    return int(sum(1 for row in rows if bool(row.get(key))))


def _max_abs(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((abs(_number(row.get(key))) for row in rows), default=0.0))


def _min_date(frame: pd.DataFrame) -> str | None:
    if frame.empty or "date" not in frame:
        return None
    return pd.Timestamp(frame["date"].min()).date().isoformat()


def _max_date(frame: pd.DataFrame) -> str | None:
    if frame.empty or "date" not in frame:
        return None
    return pd.Timestamp(frame["date"].max()).date().isoformat()


def _date_str(value: Any) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(timestamp) else timestamp.date().isoformat()


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
