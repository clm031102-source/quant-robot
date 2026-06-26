from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.cn_stock_tradeability_gate import (
    CNStockTradeabilityPolicy,
    build_cn_stock_tradeability_frame,
)
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "cn_stock_tradeability_mask_cache"
DATASET = "processed/tradeability_masks"
MASK_COLUMNS = [
    "date",
    "asset_id",
    "market",
    "entry_tradeable",
    "exit_tradeable",
    "fully_tradeable",
    "can_buy",
    "can_sell",
    "suspended_official",
    "limit_up_official",
    "limit_down_official",
    "st_flag_official",
    "new_listing_flag",
    "delisted_or_inactive_flag",
    "board_permission_blocked",
    "blocked_reasons",
]


def build_cn_stock_tradeability_mask_cache(
    *,
    bars: pd.DataFrame,
    output_root: str | Path,
    market: str = "CN",
    stock_basic: pd.DataFrame | None = None,
    stk_limit: pd.DataFrame | None = None,
    suspension: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
    policy: CNStockTradeabilityPolicy | None = None,
) -> dict[str, Any]:
    frame = build_cn_stock_tradeability_frame(
        _prepare_gate_bars(bars),
        stock_basic,
        policy=policy,
        stk_limit=stk_limit,
        suspension=suspension,
        namechange=namechange,
    )
    mask = frame[[column for column in MASK_COLUMNS if column in frame.columns]].copy()
    mask["date"] = pd.to_datetime(mask["date"], errors="coerce").dt.date
    mask["asset_id"] = mask["asset_id"].astype(str)
    mask["market"] = mask["market"].fillna(market).astype(str).str.upper()
    mask = mask[mask["market"] == market.upper()].dropna(subset=["date", "asset_id"])

    store = DatasetStore(output_root)
    written: list[str] = []
    for year, group in mask.groupby(pd.to_datetime(mask["date"]).map(lambda value: int(value.year)), sort=True):
        path = store.write_frame(
            group.reset_index(drop=True),
            DATASET,
            {"frequency": "1d", "market": market.upper(), "year": str(int(year))},
        )
        written.append(str(path))

    report = _report(
        mask,
        written,
        market=market,
        stock_basic_supplied=stock_basic is not None and not stock_basic.empty,
    )
    _write_report(output_root, report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    stock_basic_supplied = summary.get(
        "stock_basic_supplied",
        summary.get("stock_basic_supplied_for_all_years", False),
    )
    lines = [
        "# CN Stock Tradeability Mask Cache",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Market: {report.get('market', 'CN')}",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Years: {summary.get('years', [])}",
        f"- Entry blocked rows: {summary.get('entry_blocked_rows', 0)}",
        f"- Exit blocked rows: {summary.get('exit_blocked_rows', 0)}",
        f"- Official mask hit rows: {summary.get('official_mask_hit_rows', 0)}",
        f"- Metadata mask hit rows: {summary.get('metadata_mask_hit_rows', 0)}",
        f"- Stock basic supplied: {stock_basic_supplied}",
        "",
    ]
    return "\n".join(lines)


def _report(
    mask: pd.DataFrame,
    written: list[str],
    *,
    market: str,
    stock_basic_supplied: bool,
) -> dict[str, Any]:
    years = sorted({int(pd.to_datetime(value).year) for value in mask["date"]}) if not mask.empty else []
    official_columns = ["suspended_official", "limit_up_official", "limit_down_official", "st_flag_official"]
    metadata_columns = ["new_listing_flag", "delisted_or_inactive_flag", "board_permission_blocked"]
    official_hit_rows = 0
    if not mask.empty and all(column in mask.columns for column in official_columns):
        official_hit_rows = int(mask[official_columns].fillna(False).any(axis=1).sum())
    metadata_hit_rows = 0
    if not mask.empty and all(column in mask.columns for column in metadata_columns):
        metadata_hit_rows = int(mask[metadata_columns].fillna(False).any(axis=1).sum())
    flag_counts = {
        f"{column}_rows": int(mask[column].fillna(False).astype(bool).sum()) if column in mask.columns else 0
        for column in [*official_columns, *metadata_columns]
    }
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market.upper(),
        "summary": {
            "rows": int(len(mask)),
            "years": years,
            "entry_blocked_rows": int((~mask["entry_tradeable"].fillna(False).astype(bool)).sum())
            if "entry_tradeable" in mask
            else 0,
            "exit_blocked_rows": int((~mask["exit_tradeable"].fillna(False).astype(bool)).sum())
            if "exit_tradeable" in mask
            else 0,
            "official_mask_hit_rows": official_hit_rows,
            "metadata_mask_hit_rows": metadata_hit_rows,
            "stock_basic_supplied": bool(stock_basic_supplied),
            "written_files": len(written),
            **flag_counts,
        },
        "written_files": written,
        "live_boundary_allowed": False,
        "safety": "Research-to-review only. No broker connection, no account reads, no order placement, no live trading.",
    }


def _write_report(output_root: str | Path, report: dict[str, Any]) -> None:
    path = Path(output_root)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{STAGE}.json").write_text(json.dumps(_json_safe(report), indent=2, sort_keys=True), encoding="utf-8")
    (path / f"{STAGE}.md").write_text(render_markdown(report), encoding="utf-8")


def _prepare_gate_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "close", "high", "low", "amount"]
    frame = bars.copy()
    if "close" not in frame.columns and "adj_close" in frame.columns:
        frame["close"] = frame["adj_close"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"bars missing required columns: {', '.join(missing)}")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    if "symbol" not in frame.columns:
        frame["symbol"] = frame["asset_id"]
    if "exchange" not in frame.columns:
        frame["exchange"] = frame["symbol"].map(_infer_exchange)
    if "open" not in frame.columns:
        frame["open"] = frame["close"]
    if "volume" not in frame.columns:
        close = pd.to_numeric(frame["close"], errors="coerce").replace(0, pd.NA)
        frame["volume"] = pd.to_numeric(frame["amount"], errors="coerce") / close
    return frame[
        [
            "date",
            "asset_id",
            "symbol",
            "market",
            "exchange",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]
    ].dropna(subset=["date", "asset_id", "market"])


def _infer_exchange(symbol: object) -> str:
    text = str(symbol).upper()
    if text.endswith(".SH") or "XSHG" in text:
        return "XSHG"
    if text.endswith(".SZ") or "XSHE" in text:
        return "XSHE"
    if text.endswith(".BJ") or "XBEI" in text:
        return "XBEI"
    return ""


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
