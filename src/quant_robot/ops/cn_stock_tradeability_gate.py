from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "cn_stock_tradeability_gate"
REQUIRED_BAR_COLUMNS = (
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
)
FLAG_COLUMNS = (
    "suspended_proxy",
    "suspended_official",
    "limit_up_like",
    "limit_up_official",
    "limit_down_like",
    "limit_down_official",
    "st_flag",
    "st_flag_official",
    "new_listing_flag",
    "delisted_or_inactive_flag",
    "board_permission_blocked",
)


@dataclass(frozen=True)
class CNStockTradeabilityPolicy:
    min_listing_days: int = 120
    allow_bse: bool = False
    allow_star: bool = False
    allow_chinext: bool = False
    main_limit_pct: float = 0.10
    st_limit_pct: float = 0.05
    star_chinext_limit_pct: float = 0.20
    bse_limit_pct: float = 0.30
    limit_tolerance: float = 0.002


def build_cn_stock_tradeability_frame(
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame | None = None,
    policy: CNStockTradeabilityPolicy | None = None,
    *,
    stk_limit: pd.DataFrame | None = None,
    suspension: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
) -> pd.DataFrame:
    policy = policy or CNStockTradeabilityPolicy()
    _require_columns(bars, REQUIRED_BAR_COLUMNS, "bars")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    for column in ("open", "high", "low", "close", "volume", "amount"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = _merge_stock_basic(frame, stock_basic)
    frame["board"] = [_board(row) for row in frame.to_dict(orient="records")]
    frame["st_flag_basic"] = _bool_series(frame["name"].astype(str).map(_is_st_name), index=frame.index)
    frame = _merge_official_limit(frame, stk_limit, policy)
    frame = _merge_official_suspension(frame, suspension)
    frame = _apply_official_st_flags(frame, namechange)
    frame["st_flag"] = _bool_series(frame["st_flag_basic"], index=frame.index) | _bool_series(
        frame["st_flag_official"], index=frame.index
    )
    frame["new_listing_flag"] = _new_listing_flag(frame, policy)
    frame["delisted_or_inactive_flag"] = _delisted_or_inactive_flag(frame)
    frame["board_permission_blocked"] = _board_permission_blocked(frame["board"], policy)
    frame["suspended_proxy"] = (
        frame[["open", "high", "low", "close"]].isna().any(axis=1)
        | (frame[["open", "high", "low", "close"]] <= 0.0).any(axis=1)
        | frame["volume"].isna()
        | frame["amount"].isna()
        | (frame["volume"] <= 0.0)
        | (frame["amount"] <= 0.0)
    )
    frame["prev_close"] = frame.groupby("asset_id", sort=False)["close"].shift(1)
    frame["limit_pct"] = _limit_pct(frame, policy)
    close_at_high = frame["high"] <= frame["close"] * (1.0 + policy.limit_tolerance)
    close_at_low = frame["low"] >= frame["close"] * (1.0 - policy.limit_tolerance)
    frame["limit_up_like"] = (
        frame["prev_close"].notna()
        & (frame["prev_close"] > 0.0)
        & (frame["close"] >= frame["prev_close"] * (1.0 + frame["limit_pct"] - policy.limit_tolerance))
        & close_at_high
    )
    frame["limit_down_like"] = (
        frame["prev_close"].notna()
        & (frame["prev_close"] > 0.0)
        & (frame["close"] <= frame["prev_close"] * (1.0 - frame["limit_pct"] + policy.limit_tolerance))
        & close_at_low
    )
    base_block = (
        frame["suspended_proxy"]
        | frame["suspended_official"]
        | frame["st_flag"]
        | frame["new_listing_flag"]
        | frame["delisted_or_inactive_flag"]
        | frame["board_permission_blocked"]
    )
    frame["can_buy"] = ~(base_block | frame["limit_up_like"] | frame["limit_up_official"])
    frame["can_sell"] = ~(base_block | frame["limit_down_like"] | frame["limit_down_official"])
    frame["entry_tradeable"] = frame["can_buy"]
    frame["exit_tradeable"] = frame["can_sell"]
    frame["fully_tradeable"] = frame["can_buy"] & frame["can_sell"]
    frame["blocked_reasons"] = _blocked_reasons(frame)
    columns = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "exchange",
        "stock_market",
        "board",
        "name",
        "list_date",
        "delist_date",
        "is_active",
        "prev_close",
        "close",
        "volume",
        "amount",
        "limit_pct",
        "official_up_limit",
        "official_down_limit",
        *FLAG_COLUMNS,
        "can_buy",
        "can_sell",
        "entry_tradeable",
        "exit_tradeable",
        "fully_tradeable",
        "blocked_reasons",
    ]
    return frame[columns].reset_index(drop=True)


def build_cn_stock_tradeability_report(
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame | None = None,
    policy: CNStockTradeabilityPolicy | None = None,
    *,
    stk_limit: pd.DataFrame | None = None,
    suspension: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
) -> dict[str, Any]:
    policy = policy or CNStockTradeabilityPolicy()
    frame = build_cn_stock_tradeability_frame(
        bars,
        stock_basic,
        stk_limit=stk_limit,
        suspension=suspension,
        namechange=namechange,
        policy=policy,
    )
    summary: dict[str, Any] = {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()) if not frame.empty else 0,
        "can_buy_rows": int(frame["can_buy"].sum()) if not frame.empty else 0,
        "can_sell_rows": int(frame["can_sell"].sum()) if not frame.empty else 0,
        "fully_tradeable_rows": int(frame["fully_tradeable"].sum()) if not frame.empty else 0,
    }
    for column in FLAG_COLUMNS:
        summary[f"{column}_rows"] = int(frame[column].sum()) if not frame.empty else 0
    samples = (
        frame[frame["blocked_reasons"].astype(str) != ""]
        .head(25)
        .assign(date=lambda item: item["date"].astype(str))
        .to_dict(orient="records")
    )
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "policy": asdict(policy),
        "summary": summary,
        "blocked_samples": _json_safe(samples),
        "method_notes": [
            "official Tushare suspend_d rows set suspended_official when supplied; suspended_proxy remains a fallback for missing or zero OHLCV/amount rows.",
            "official Tushare stk_limit up_limit/down_limit rows set limit_up_official and limit_down_official when supplied; limit_up_like and limit_down_like remain OHLCV fallback flags.",
            "official Tushare namechange rows set st_flag_official over their effective date ranges when supplied; stock_basic names remain a fallback ST proxy.",
            "board_permission_blocked defaults to blocking BSE, STAR, and ChiNext unless explicitly allowed.",
            "This gate is local research infrastructure only and is not a live trading permission system.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# CN Stock Tradeability Gate",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Assets: {summary.get('assets', 0)}",
        f"- Can buy rows: {summary.get('can_buy_rows', 0)}",
        f"- Can sell rows: {summary.get('can_sell_rows', 0)}",
        f"- Fully tradeable rows: {summary.get('fully_tradeable_rows', 0)}",
        "",
        "## Flag Counts",
        "",
    ]
    for column in FLAG_COLUMNS:
        lines.append(f"- {column}: {summary.get(f'{column}_rows', 0)}")
    lines.extend(["", "## Method Notes", ""])
    lines.extend(f"- {note}" for note in report.get("method_notes", []))
    lines.extend(["", "## Blocked Samples", ""])
    samples = report.get("blocked_samples", [])
    if not samples:
        lines.append("- none")
    else:
        for sample in samples[:10]:
            lines.append(
                "- "
                + ", ".join(
                    [
                        f"date={sample.get('date')}",
                        f"asset_id={sample.get('asset_id')}",
                        f"symbol={sample.get('symbol')}",
                        f"reasons={sample.get('blocked_reasons')}",
                    ]
                )
            )
    lines.append("")
    return "\n".join(lines)


def write_tradeability_report(report: dict[str, Any], output_dir: str | Path) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "cn_stock_tradeability_gate.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (path / "cn_stock_tradeability_gate.md").write_text(render_markdown(report), encoding="utf-8")


def _merge_stock_basic(frame: pd.DataFrame, stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    defaults = {
        "name": "",
        "stock_market": "",
        "list_date": pd.NaT,
        "delist_date": pd.NaT,
        "is_active": True,
    }
    if stock_basic is None or stock_basic.empty:
        for column, default in defaults.items():
            frame[column] = default
        return frame
    basic = stock_basic.copy()
    keep = [
        column
        for column in (
            "asset_id",
            "symbol",
            "name",
            "stock_market",
            "list_date",
            "delist_date",
            "is_active",
        )
        if column in basic.columns
    ]
    basic = basic[keep].drop_duplicates(subset=[column for column in ("asset_id", "symbol") if column in keep])
    merged = frame.merge(basic, on=[column for column in ("asset_id", "symbol") if column in basic.columns], how="left")
    for column, default in defaults.items():
        if column not in merged.columns:
            merged[column] = default
        elif column in {"list_date", "delist_date"}:
            merged[column] = pd.to_datetime(merged[column], errors="coerce").dt.date
        elif column == "is_active":
            merged[column] = merged[column].map(_boolish).fillna(True)
        else:
            merged[column] = merged[column].fillna(default)
    return merged


def _merge_official_limit(
    frame: pd.DataFrame,
    stk_limit: pd.DataFrame | None,
    policy: CNStockTradeabilityPolicy,
) -> pd.DataFrame:
    frame["official_up_limit"] = pd.NA
    frame["official_down_limit"] = pd.NA
    frame["limit_up_official"] = False
    frame["limit_down_official"] = False
    if stk_limit is None or stk_limit.empty:
        return frame
    feed = stk_limit.copy()
    if "date" not in feed.columns:
        return frame
    feed["date"] = pd.to_datetime(feed["date"], errors="coerce").dt.date
    for column in ("up_limit", "down_limit"):
        if column in feed.columns:
            feed[column] = pd.to_numeric(feed[column], errors="coerce")
    join_keys = _join_keys(frame, feed)
    if not join_keys or "up_limit" not in feed.columns or "down_limit" not in feed.columns:
        return frame
    keep = [*join_keys, "up_limit", "down_limit"]
    feed = feed[keep].dropna(subset=["date"]).drop_duplicates(subset=join_keys, keep="last")
    merged = frame.merge(feed, on=join_keys, how="left")
    merged["official_up_limit"] = merged["up_limit"]
    merged["official_down_limit"] = merged["down_limit"]
    close = pd.to_numeric(merged["close"], errors="coerce")
    up_limit = pd.to_numeric(merged["official_up_limit"], errors="coerce")
    down_limit = pd.to_numeric(merged["official_down_limit"], errors="coerce")
    merged["limit_up_official"] = up_limit.notna() & close.notna() & (close >= up_limit * (1.0 - policy.limit_tolerance))
    merged["limit_down_official"] = (
        down_limit.notna() & close.notna() & (close <= down_limit * (1.0 + policy.limit_tolerance))
    )
    return merged.drop(columns=["up_limit", "down_limit"])


def _merge_official_suspension(frame: pd.DataFrame, suspension: pd.DataFrame | None) -> pd.DataFrame:
    frame["suspended_official"] = False
    if suspension is None or suspension.empty or "date" not in suspension.columns:
        return frame
    feed = suspension.copy()
    feed["date"] = pd.to_datetime(feed["date"], errors="coerce").dt.date
    join_keys = _join_keys(frame, feed)
    if not join_keys:
        return frame
    feed = feed[join_keys].dropna(subset=["date"]).drop_duplicates()
    feed["_official_suspension_hit"] = True
    merged = frame.merge(feed, on=join_keys, how="left")
    merged["suspended_official"] = merged["_official_suspension_hit"].fillna(False).astype(bool)
    return merged.drop(columns=["_official_suspension_hit"])


def _apply_official_st_flags(frame: pd.DataFrame, namechange: pd.DataFrame | None) -> pd.DataFrame:
    frame["st_flag_official"] = False
    if namechange is None or namechange.empty or "start_date" not in namechange.columns:
        return frame
    feed = namechange.copy()
    key = _event_key(frame, feed)
    if key is None:
        return frame
    feed["_event_key"] = feed[key].astype(str)
    feed["start_date"] = pd.to_datetime(feed["start_date"], errors="coerce")
    if "available_date" in feed.columns:
        feed["available_date"] = pd.to_datetime(feed["available_date"], errors="coerce")
        feed["effective_start"] = feed[["start_date", "available_date"]].max(axis=1)
    else:
        feed["effective_start"] = feed["start_date"]
    if "end_date" in feed.columns:
        feed["end_date"] = pd.to_datetime(feed["end_date"], errors="coerce")
    else:
        feed["end_date"] = pd.NaT
    if "is_st_name" in feed.columns:
        feed = feed[feed["is_st_name"].map(_boolish).fillna(False)]
    elif "name" in feed.columns:
        feed = feed[feed["name"].astype(str).map(_is_st_name)]
    else:
        return frame
    feed = feed.dropna(subset=["effective_start"])
    if feed.empty:
        return frame
    frame["_event_key"] = frame[key].astype(str)
    frame_dates = pd.to_datetime(frame["date"], errors="coerce")
    groups = frame.groupby("_event_key", sort=False).groups
    for event_key, events in feed.groupby("_event_key", sort=False):
        indices = groups.get(event_key)
        if indices is None:
            continue
        dates = frame_dates.loc[indices]
        mask = pd.Series(False, index=indices)
        for event in events.to_dict(orient="records"):
            start = event["effective_start"]
            end = event.get("end_date")
            active = dates >= start
            if pd.notna(end):
                active &= dates <= end
            mask |= active
        frame.loc[indices, "st_flag_official"] = mask.to_numpy()
    return frame.drop(columns=["_event_key"])


def _join_keys(frame: pd.DataFrame, feed: pd.DataFrame) -> list[str]:
    keys = ["date"]
    if "asset_id" in frame.columns and "asset_id" in feed.columns:
        return ["asset_id", *keys]
    if "symbol" in frame.columns and "symbol" in feed.columns:
        return ["symbol", *keys]
    return []


def _event_key(frame: pd.DataFrame, feed: pd.DataFrame) -> str | None:
    if "asset_id" in frame.columns and "asset_id" in feed.columns:
        return "asset_id"
    if "symbol" in frame.columns and "symbol" in feed.columns:
        return "symbol"
    return None


def _new_listing_flag(frame: pd.DataFrame, policy: CNStockTradeabilityPolicy) -> pd.Series:
    list_dates = pd.to_datetime(frame["list_date"], errors="coerce")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    age_days = (dates - list_dates).dt.days
    return age_days.notna() & (age_days < int(policy.min_listing_days))


def _delisted_or_inactive_flag(frame: pd.DataFrame) -> pd.Series:
    delist_dates = pd.to_datetime(frame["delist_date"], errors="coerce")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    after_delist = delist_dates.notna() & (dates >= delist_dates)
    inactive = ~frame["is_active"].map(_boolish).fillna(True)
    return after_delist | inactive


def _board_permission_blocked(boards: pd.Series, policy: CNStockTradeabilityPolicy) -> pd.Series:
    board = boards.astype(str)
    return (
        ((board == "bse") & (not policy.allow_bse))
        | ((board == "star") & (not policy.allow_star))
        | ((board == "chinext") & (not policy.allow_chinext))
    )


def _limit_pct(frame: pd.DataFrame, policy: CNStockTradeabilityPolicy) -> pd.Series:
    result = pd.Series(float(policy.main_limit_pct), index=frame.index, dtype=float)
    result.loc[frame["board"] == "bse"] = float(policy.bse_limit_pct)
    result.loc[frame["board"].isin(["star", "chinext"])] = float(policy.star_chinext_limit_pct)
    result.loc[frame["st_flag"]] = float(policy.st_limit_pct)
    return result


def _board(row: dict[str, Any]) -> str:
    stock_market = str(row.get("stock_market", "")).strip()
    symbol = str(row.get("symbol", "")).strip()
    exchange = str(row.get("exchange", "")).strip().upper()
    if "北交" in stock_market or exchange == "XBEI" or symbol.endswith(".BJ"):
        return "bse"
    if "科创" in stock_market or symbol.startswith(("688", "689")):
        return "star"
    if "创业" in stock_market or symbol.startswith(("300", "301")):
        return "chinext"
    return "main"


def _is_st_name(name: str) -> bool:
    text = str(name).strip().upper()
    return "ST" in text or "退" in text


def _blocked_reasons(frame: pd.DataFrame) -> list[str]:
    reasons = []
    for row in frame.to_dict(orient="records"):
        row_reasons = [column for column in FLAG_COLUMNS if bool(row.get(column, False))]
        reasons.append(";".join(row_reasons))
    return reasons


def _require_columns(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _boolish(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        return bool(text)
    return bool(value)


def _bool_series(values: Any, *, index: pd.Index) -> pd.Series:
    series = pd.Series(values, index=index)
    return pd.Series(series.map(_boolish).fillna(False).astype(bool).to_numpy(), index=index, dtype=bool)


def _json_safe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_records = []
    for record in records:
        safe = {}
        for key, value in record.items():
            if hasattr(value, "isoformat"):
                safe[key] = value.isoformat()
            elif pd.isna(value):
                safe[key] = None
            else:
                safe[key] = value
        safe_records.append(safe)
    return safe_records
