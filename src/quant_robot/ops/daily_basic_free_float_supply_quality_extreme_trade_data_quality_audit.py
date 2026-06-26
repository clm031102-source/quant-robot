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
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import SAFETY


STAGE = "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit"
NEXT_PRICE_BASIS_REPAIR = "round138_daily_basic_free_float_supply_quality_price_basis_repair_and_clean_preflight_rerun"
NEXT_UNEXPLAINED_EXTREME_AUDIT = (
    "round138_daily_basic_free_float_supply_quality_unexplained_extreme_trade_audit_or_family_rotation"
)
DEFAULT_PREFLIGHT_REPORT = Path(
    "data/reports/daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_round136_20260622/"
    "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight.json"
)
DEFAULT_PRICE_RATIO_JUMP_THRESHOLD = 1.5
DEFAULT_ADJUSTED_SHARE_JUMP_THRESHOLD = 0.25
DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD = 0.5
DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD = 0.5

ASSET_PATH_AUDIT_COLUMNS = [
    "case_id",
    "asset_id",
    "market",
    "signal_date",
    "entry_date",
    "exit_date",
    "entry_adjusted",
    "exit_adjusted",
    "entry_close",
    "exit_close",
    "entry_adj_close",
    "exit_adj_close",
    "entry_price_ratio",
    "exit_price_ratio",
    "ratio_jump",
    "close_gross_return",
    "adj_gross_return",
    "reported_gross_return",
    "max_abs_daily_close_return",
    "max_abs_daily_adj_return",
    "data_quality_class",
    "blockers",
]
DATE_BASIS_AUDIT_COLUMNS = [
    "date",
    "rows",
    "adjusted_true",
    "adjusted_false",
    "adjusted_true_share",
    "ratio_median",
    "ratio_min",
    "ratio_max",
    "median_ratio_jump",
    "adjusted_flag_transition",
    "market_wide_transition",
]


def build_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
    *,
    bars_roots: Iterable[str | Path],
    extreme_trades: Iterable[dict[str, Any]] | pd.DataFrame | None = None,
    preflight_report: dict[str, Any] | str | Path | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    price_ratio_jump_threshold: float = DEFAULT_PRICE_RATIO_JUMP_THRESHOLD,
    plausible_close_return_abs_threshold: float = DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD,
    extreme_adj_return_abs_threshold: float = DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD,
) -> dict[str, Any]:
    bars = load_price_basis_audit_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    resolved_extreme_trades = (
        extreme_trades if extreme_trades is not None else _load_extreme_trades_from_report(preflight_report)
    )
    result = summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
        extreme_trades=resolved_extreme_trades,
        bars=bars,
        price_ratio_jump_threshold=price_ratio_jump_threshold,
        plausible_close_return_abs_threshold=plausible_close_return_abs_threshold,
        extreme_adj_return_abs_threshold=extreme_adj_return_abs_threshold,
    )
    result["data_window"] = _data_window(bars)
    result["holdout_policy"] = {
        "final_holdout_included": bool(include_final_holdout),
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round136_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight",
        "source_report": str(preflight_report or DEFAULT_PREFLIGHT_REPORT),
        "scope": "extreme trade data-quality audit only; no alpha parameter search",
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_markdown(result)
    return result


def summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
    *,
    extreme_trades: Iterable[dict[str, Any]] | pd.DataFrame,
    bars: pd.DataFrame,
    price_ratio_jump_threshold: float = DEFAULT_PRICE_RATIO_JUMP_THRESHOLD,
    plausible_close_return_abs_threshold: float = DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD,
    extreme_adj_return_abs_threshold: float = DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD,
) -> dict[str, Any]:
    trades = _normalise_extreme_trades(extreme_trades)
    clean_bars = _normalise_price_basis_bars(bars)
    date_basis_audit = _date_basis_audit(clean_bars, price_ratio_jump_threshold=price_ratio_jump_threshold)
    asset_path_audit = _asset_path_audit(
        trades,
        clean_bars,
        price_ratio_jump_threshold=price_ratio_jump_threshold,
        plausible_close_return_abs_threshold=plausible_close_return_abs_threshold,
        extreme_adj_return_abs_threshold=extreme_adj_return_abs_threshold,
    )
    summary = _summary(trades, asset_path_audit, date_basis_audit)
    gate = _gate(summary, date_basis_audit)
    next_direction = NEXT_PRICE_BASIS_REPAIR if summary["phantom_alpha_trade_count"] else NEXT_UNEXPLAINED_EXTREME_AUDIT
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "thresholds": {
            "price_ratio_jump_threshold": float(price_ratio_jump_threshold),
            "plausible_close_return_abs_threshold": float(plausible_close_return_abs_threshold),
            "extreme_adj_return_abs_threshold": float(extreme_adj_return_abs_threshold),
        },
        "summary": summary,
        "gate": gate,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": gate["blockers"]
            + [
                "preflight_contaminated_by_extreme_trade_audit",
                "final_holdout_not_read",
                "price_basis_repair_required_before_any_promotion",
            ],
            "reason": (
                "Extreme trade audit can explain backtest contamination but cannot promote a factor. "
                "The factor must be rerun after a single consistent price basis is enforced."
            ),
        },
        "asset_path_audit": asset_path_audit,
        "date_basis_audit": date_basis_audit,
        "next_direction": next_direction,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_markdown(result)
    return result


def load_price_basis_audit_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    files: list[Path] = []
    for root in bars_roots:
        root_path = Path(root)
        bars_root = root_path / "bars" if (root_path / "bars").exists() else root_path
        files.extend(sorted(bars_root.rglob("*.parquet")))
        files.extend(sorted(bars_root.rglob("*.csv")))
    frames = [_read_bars_file(file) for file in files if "market=CN" in str(file) or "bars" in str(file)]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bars files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = _normalise_price_basis_bars(pd.concat(frames, ignore_index=True))
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)].copy()
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def write_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.md").write_text(
        render_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_extreme_trade_asset_path_audit.csv",
        result.get("asset_path_audit", []),
        ASSET_PATH_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_extreme_trade_date_basis_audit.csv",
        result.get("date_basis_audit", []),
        DATE_BASIS_AUDIT_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Extreme Trade Data-Quality Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Extreme trades audited: {summary.get('extreme_trade_count', 0)}",
        f"- Mixed price-basis trades: {summary.get('mixed_price_basis_trade_count', 0)}",
        f"- Phantom-alpha trades: {summary.get('phantom_alpha_trade_count', 0)}",
        f"- Market-wide transition dates: {summary.get('market_wide_transition_date_count', 0)}",
        f"- Dominant exit date: {summary.get('dominant_exit_date')}",
        f"- Dominant trade window: {summary.get('dominant_trade_window')}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_UNEXPLAINED_EXTREME_AUDIT)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Thresholds",
        "",
        f"- Price ratio jump threshold: {thresholds.get('price_ratio_jump_threshold')}",
        f"- Plausible close return abs threshold: {thresholds.get('plausible_close_return_abs_threshold')}",
        f"- Extreme adjusted return abs threshold: {thresholds.get('extreme_adj_return_abs_threshold')}",
        "",
        "## Gate",
        "",
        f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
        f"- Observations: {', '.join(gate.get('observations', [])) if gate.get('observations') else 'none'}",
        "",
        "## Top Asset Path Findings",
        "",
        "| Asset | Entry | Exit | Ratio Jump | Close Ret | Adj Ret | Class |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in result.get("asset_path_audit", [])[:20]:
        lines.append(
            "| {asset} | {entry} | {exit} | {jump:.2f} | {close:.2%} | {adj:.2%} | {klass} |".format(
                asset=row.get("asset_id", ""),
                entry=row.get("entry_date", ""),
                exit=row.get("exit_date", ""),
                jump=_number(row.get("ratio_jump")),
                close=_number(row.get("close_gross_return")),
                adj=_number(row.get("adj_gross_return")),
                klass=row.get("data_quality_class", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A tolerable drawdown does not waive data-quality gates.",
            "- If adjusted and unadjusted price bases are mixed across the trade holding window, the return is not evidence of alpha.",
            "- The next valid step is to rebuild returns on one consistent price basis and rerun the same frozen parameters.",
        ]
    )
    return "\n".join(lines) + "\n"


def _date_basis_audit(bars: pd.DataFrame, *, price_ratio_jump_threshold: float) -> list[dict[str, Any]]:
    if bars.empty:
        return []
    frame = bars.copy()
    frame["price_ratio"] = _price_ratio(frame)
    daily = (
        frame.groupby("date", sort=True)
        .agg(
            rows=("asset_id", "size"),
            adjusted_true=("adjusted", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
            ratio_median=("price_ratio", "median"),
            ratio_min=("price_ratio", "min"),
            ratio_max=("price_ratio", "max"),
        )
        .reset_index()
    )
    daily["adjusted_false"] = daily["rows"] - daily["adjusted_true"]
    daily["adjusted_true_share"] = daily["adjusted_true"] / daily["rows"].replace(0, pd.NA)
    previous_ratio = daily["ratio_median"].shift(1)
    daily["median_ratio_jump"] = [
        _ratio_jump(current, previous)
        for current, previous in zip(daily["ratio_median"], previous_ratio, strict=False)
    ]
    previous_adjusted_share = daily["adjusted_true_share"].shift(1)
    daily["adjusted_flag_transition"] = [
        bool(idx > 0 and abs(_number(current) - _number(previous)) >= DEFAULT_ADJUSTED_SHARE_JUMP_THRESHOLD)
        for idx, (current, previous) in enumerate(
            zip(daily["adjusted_true_share"], previous_adjusted_share, strict=False)
        )
    ]
    daily["market_wide_transition"] = (
        (daily["median_ratio_jump"] >= float(price_ratio_jump_threshold)) | daily["adjusted_flag_transition"]
    )
    rows = []
    for item in daily.to_dict("records"):
        rows.append(
            _sanitize(
                {
                    "date": _date_str(item.get("date")),
                    "rows": int(item.get("rows", 0)),
                    "adjusted_true": int(item.get("adjusted_true", 0)),
                    "adjusted_false": int(item.get("adjusted_false", 0)),
                    "adjusted_true_share": _number(item.get("adjusted_true_share")),
                    "ratio_median": _number(item.get("ratio_median")),
                    "ratio_min": _number(item.get("ratio_min")),
                    "ratio_max": _number(item.get("ratio_max")),
                    "median_ratio_jump": _number(item.get("median_ratio_jump")),
                    "adjusted_flag_transition": bool(item.get("adjusted_flag_transition")),
                    "market_wide_transition": bool(item.get("market_wide_transition")),
                }
            )
        )
    return rows


def _asset_path_audit(
    trades: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    price_ratio_jump_threshold: float,
    plausible_close_return_abs_threshold: float,
    extreme_adj_return_abs_threshold: float,
) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    relevant_assets = set(trades["asset_id"].dropna().astype(str))
    relevant_bars = bars[bars["asset_id"].isin(relevant_assets)].copy()
    lookup = {
        (str(row.asset_id), pd.Timestamp(row.date).date().isoformat()): row
        for row in relevant_bars.itertuples(index=False)
    }
    grouped_bars = {
        str(asset_id): group.sort_values("date").reset_index(drop=True)
        for asset_id, group in relevant_bars.groupby("asset_id", sort=False)
    }
    rows = []
    for trade in trades.to_dict("records"):
        rows.append(
            _audit_trade_path(
                trade,
                lookup=lookup,
                grouped_bars=grouped_bars,
                price_ratio_jump_threshold=price_ratio_jump_threshold,
                plausible_close_return_abs_threshold=plausible_close_return_abs_threshold,
                extreme_adj_return_abs_threshold=extreme_adj_return_abs_threshold,
            )
        )
    return rows


def _audit_trade_path(
    trade: dict[str, Any],
    *,
    lookup: dict[tuple[str, str], Any],
    grouped_bars: dict[str, pd.DataFrame],
    price_ratio_jump_threshold: float,
    plausible_close_return_abs_threshold: float,
    extreme_adj_return_abs_threshold: float,
) -> dict[str, Any]:
    asset_id = str(trade.get("asset_id", ""))
    entry_date = _date_str(trade.get("entry_date"))
    exit_date = _date_str(trade.get("exit_date"))
    entry = lookup.get((asset_id, entry_date))
    exit_ = lookup.get((asset_id, exit_date))
    if entry is None or exit_ is None:
        return _sanitize(
            {
                **_trade_identity(trade),
                "entry_adjusted": False,
                "exit_adjusted": False,
                "entry_close": 0.0,
                "exit_close": 0.0,
                "entry_adj_close": 0.0,
                "exit_adj_close": 0.0,
                "entry_price_ratio": 0.0,
                "exit_price_ratio": 0.0,
                "ratio_jump": 0.0,
                "close_gross_return": 0.0,
                "adj_gross_return": _number(trade.get("gross_return")),
                "reported_gross_return": _number(trade.get("gross_return")),
                "max_abs_daily_close_return": 0.0,
                "max_abs_daily_adj_return": 0.0,
                "data_quality_class": "missing_entry_or_exit_bar",
                "blockers": ["missing_entry_or_exit_bar"],
            }
        )
    entry_close = _number(getattr(entry, "close", 0.0))
    exit_close = _number(getattr(exit_, "close", 0.0))
    entry_adj_close = _number(getattr(entry, "adj_close", 0.0))
    exit_adj_close = _number(getattr(exit_, "adj_close", 0.0))
    entry_ratio = _safe_ratio(entry_adj_close, entry_close)
    exit_ratio = _safe_ratio(exit_adj_close, exit_close)
    ratio_jump = _ratio_jump(exit_ratio, entry_ratio)
    close_return = _safe_ratio(exit_close, entry_close) - 1.0 if entry_close > 0 else 0.0
    adj_return = _safe_ratio(exit_adj_close, entry_adj_close) - 1.0 if entry_adj_close > 0 else 0.0
    entry_adjusted = bool(getattr(entry, "adjusted", False))
    exit_adjusted = bool(getattr(exit_, "adjusted", False))
    max_close, max_adj = _max_path_daily_returns(grouped_bars.get(asset_id), entry_date, exit_date)
    basis_transition = bool(entry_adjusted != exit_adjusted or ratio_jump >= float(price_ratio_jump_threshold))
    phantom_alpha = bool(
        basis_transition
        and abs(adj_return) >= float(extreme_adj_return_abs_threshold)
        and abs(close_return) <= float(plausible_close_return_abs_threshold)
    )
    data_quality_class, blockers = _classify_trade(
        basis_transition=basis_transition,
        phantom_alpha=phantom_alpha,
        close_return=close_return,
        adj_return=adj_return,
        plausible_close_return_abs_threshold=plausible_close_return_abs_threshold,
        extreme_adj_return_abs_threshold=extreme_adj_return_abs_threshold,
    )
    return _sanitize(
        {
            **_trade_identity(trade),
            "entry_adjusted": entry_adjusted,
            "exit_adjusted": exit_adjusted,
            "entry_close": entry_close,
            "exit_close": exit_close,
            "entry_adj_close": entry_adj_close,
            "exit_adj_close": exit_adj_close,
            "entry_price_ratio": entry_ratio,
            "exit_price_ratio": exit_ratio,
            "ratio_jump": ratio_jump,
            "close_gross_return": close_return,
            "adj_gross_return": adj_return,
            "reported_gross_return": _number(trade.get("gross_return")),
            "max_abs_daily_close_return": max_close,
            "max_abs_daily_adj_return": max_adj,
            "data_quality_class": data_quality_class,
            "blockers": blockers,
        }
    )


def _classify_trade(
    *,
    basis_transition: bool,
    phantom_alpha: bool,
    close_return: float,
    adj_return: float,
    plausible_close_return_abs_threshold: float,
    extreme_adj_return_abs_threshold: float,
) -> tuple[str, list[str]]:
    if phantom_alpha:
        return "mixed_price_basis_phantom_alpha", [
            "mixed_price_basis_trade",
            "phantom_alpha_from_price_basis_jump",
        ]
    if basis_transition:
        return "mixed_price_basis_extreme_return", ["mixed_price_basis_trade"]
    if abs(close_return) > float(plausible_close_return_abs_threshold):
        return "true_close_extreme_return", ["true_close_extreme_return_requires_manual_audit"]
    if abs(adj_return) > float(extreme_adj_return_abs_threshold):
        return "unexplained_extreme_adj_return", ["unexplained_extreme_adj_return"]
    return "non_extreme_after_price_path_check", []


def _max_path_daily_returns(group: pd.DataFrame | None, entry_date: str, exit_date: str) -> tuple[float, float]:
    if group is None or group.empty:
        return 0.0, 0.0
    start = pd.Timestamp(entry_date)
    end = pd.Timestamp(exit_date)
    window = group[(group["date"] >= start) & (group["date"] <= end)].sort_values("date")
    if len(window) < 2:
        return 0.0, 0.0
    close_returns = pd.to_numeric(window["close"], errors="coerce").pct_change().abs()
    adj_returns = pd.to_numeric(window["adj_close"], errors="coerce").pct_change().abs()
    return _number(close_returns.max()), _number(adj_returns.max())


def _summary(
    trades: pd.DataFrame,
    asset_path_audit: list[dict[str, Any]],
    date_basis_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    classes = [str(row.get("data_quality_class", "")) for row in asset_path_audit]
    exit_dates = trades["exit_date"].astype(str).tolist() if not trades.empty and "exit_date" in trades else []
    windows = (
        (trades["entry_date"].astype(str) + " -> " + trades["exit_date"].astype(str)).tolist()
        if not trades.empty and {"entry_date", "exit_date"}.issubset(trades.columns)
        else []
    )
    return {
        "extreme_trade_count": int(len(trades)),
        "asset_path_audit_count": int(len(asset_path_audit)),
        "unique_extreme_assets": int(trades["asset_id"].nunique()) if not trades.empty and "asset_id" in trades else 0,
        "unique_exit_dates": int(len(set(exit_dates))),
        "mixed_price_basis_trade_count": int(sum(klass.startswith("mixed_price_basis") for klass in classes)),
        "phantom_alpha_trade_count": int(sum(klass == "mixed_price_basis_phantom_alpha" for klass in classes)),
        "true_close_extreme_trade_count": int(sum(klass == "true_close_extreme_return" for klass in classes)),
        "unexplained_extreme_adj_trade_count": int(sum(klass == "unexplained_extreme_adj_return" for klass in classes)),
        "market_wide_transition_date_count": int(
            sum(1 for row in date_basis_audit if row.get("market_wide_transition"))
        ),
        "dominant_exit_date": _top_value(exit_dates),
        "dominant_trade_window": _top_value(windows),
        "price_basis_root_cause_confirmed": bool(
            any(klass == "mixed_price_basis_phantom_alpha" for klass in classes)
            and any(row.get("market_wide_transition") for row in date_basis_audit)
        ),
    }


def _gate(summary: dict[str, Any], date_basis_audit: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = []
    observations = []
    if int(summary.get("extreme_trade_count", 0)) <= 0:
        blockers.append("no_extreme_trades_to_audit")
    if any(row.get("market_wide_transition") for row in date_basis_audit):
        blockers.append("market_wide_price_basis_transition")
    if int(summary.get("phantom_alpha_trade_count", 0)) > 0:
        blockers.append("mixed_price_basis_phantom_alpha")
        blockers.append("rerun_same_parameters_after_price_basis_repair")
    if int(summary.get("true_close_extreme_trade_count", 0)) > 0:
        observations.append("true_close_extreme_returns_require_liquidity_limit_audit")
    if int(summary.get("unexplained_extreme_adj_trade_count", 0)) > 0:
        observations.append("unexplained_extreme_adjusted_returns_remain")
    return {
        "passes": not blockers,
        "blockers": _dedupe(blockers),
        "observations": observations,
        "required_before_next_mining": [
            "read_round137_extreme_trade_data_quality_audit",
            "repair_or_filter_mixed_price_basis_before_portfolio_backtest",
            "rerun_same_frozen_parameters_after_price_basis_repair",
        ],
    }


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
    for column in ["gross_return", "net_return", "weighted_return", "target_notional", "entry_amount", "participation_rate"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.reset_index(drop=True)


def _normalise_price_basis_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "adjusted" not in frame:
        frame["adjusted"] = frame["adj_close"] != frame["close"]
    if "amount" not in frame:
        frame["amount"] = 0.0
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in ["close", "adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["adjusted"] = frame["adjusted"].fillna(False).astype(bool)
    frame = frame.dropna(subset=["date", "asset_id", "market", "close", "adj_close"])
    frame = frame[(frame["market"] == "CN") & (frame["close"] > 0) & (frame["adj_close"] > 0)]
    return frame.reset_index(drop=True)


def _read_bars_file(file: Path) -> pd.DataFrame:
    wanted = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "close",
        "adj_close",
        "adjusted",
        "high",
        "low",
        "amount",
        "volume",
        "source",
    ]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=wanted)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in wanted if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in wanted if column in frame.columns]]


def _load_extreme_trades_from_report(preflight_report: dict[str, Any] | str | Path | None) -> list[dict[str, Any]]:
    if preflight_report is None:
        preflight_report = DEFAULT_PREFLIGHT_REPORT
    if isinstance(preflight_report, (str, Path)):
        path = Path(preflight_report)
        if not path.exists():
            raise FileNotFoundError(f"Preflight report not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = dict(preflight_report)
    return list(payload.get("extreme_trades", []))


def _trade_identity(trade: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(trade.get("case_id", "")),
        "asset_id": str(trade.get("asset_id", "")),
        "market": str(trade.get("market", "CN") or "CN"),
        "signal_date": _date_str(trade.get("signal_date")),
        "entry_date": _date_str(trade.get("entry_date")),
        "exit_date": _date_str(trade.get("exit_date")),
    }


def _data_window(bars: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars),
        "max_bar_date": _max_date(bars),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
    }


def _price_ratio(frame: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(frame["adj_close"], errors="coerce") / pd.to_numeric(frame["close"], errors="coerce")


def _ratio_jump(current: Any, previous: Any) -> float:
    current_number = _number(current)
    previous_number = _number(previous)
    if current_number <= 0 or previous_number <= 0:
        return 1.0
    return float(max(current_number / previous_number, previous_number / current_number))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _top_value(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


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
