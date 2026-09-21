"""Strict source-field extraction, independent of strategy or live execution."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import Any
from urllib.parse import urlsplit


def parse_cash_dividend_notice(text: str, *, symbol: str, announcement_date: str) -> dict[str, Any]:
    code = _sse_code(symbol)
    compact = re.sub(r"\s+", "", text)
    if _one(r"基金主代码([0-9]{6})(?![0-9])", compact, "fund code") != code:
        raise ValueError("notice fund code does not match requested symbol")
    announced = _notice_date(compact, "公告送出日期")
    if announced != _iso(announcement_date):
        raise ValueError("notice announcement date differs from index")
    record, ex, pay = (_notice_date(compact, label) for label in
        ("权益登记日", "除息日", "现金红利发放日"))
    if not announced <= record < ex <= pay or pay >= date(2026, 1, 1):
        raise ValueError("unsupported notice chronology or final holdout date")
    unit, raw_cash = _one(
        r"本次分红方案[（(]单位[：:]元/([0-9]+)份基金份额[）)](.*?)有关年度分红次数的说明",
        compact, "dividend amount and currency unit")
    denominator = Decimal(unit)
    if not 0 < denominator <= 1_000_000:
        raise ValueError("invalid cash denominator")
    if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", raw_cash):
        raise ValueError("unsupported complete dividend amount field")
    cash = Decimal(raw_cash)
    if not 0 < cash <= 1_000_000:
        raise ValueError("invalid dividend amount")
    return {"symbol": symbol, "kind": "cash_dividend", "announced_date": str(announced),
        "record_date": str(record), "ex_date": str(ex), "pay_date": str(pay),
        "currency": "CNY", "notice_cash_amount": raw_cash, "notice_share_denominator": unit,
        "cash_per_share": str(cash / denominator),
        "notice_states_tax_exemption": "暂不征收个人所得税和企业所得税" in compact,
        "broker_dividend_fees_verified": False}


def validate_announcement_page(payload: dict[str, Any], *, symbol: str,
                                start: str, end: str) -> list[dict[str, Any]]:
    code, first, last = _sse_code(symbol), _iso(start), _iso(end)
    if first > last or last >= date(2026, 1, 1):
        raise ValueError("invalid announcement window or final holdout")
    help_info, records = payload.get("pageHelp", {}), payload.get("result")
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ValueError("announcement records must be explicit objects")
    # This bounded reviewer accepts complete single-page windows only.
    if (type(help_info.get("total")) is not int or help_info["total"] != len(records)
            or help_info.get("pageNo") != 1 or help_info.get("pageCount") not in (0, 1)
            or type(help_info.get("pageSize")) is not int or not 1 <= help_info["pageSize"] <= 100
            or len(records) > help_info["pageSize"]):
        raise ValueError("incomplete or unsupported announcement pagination")
    urls, result = set(), []
    for row in records:
        if row.get("SECURITY_CODE") != code or not first <= _iso(row.get("SSEDATE")) <= last:
            raise ValueError("announcement code or date outside requested scope")
        title, url = row.get("TITLE"), row.get("URL")
        if not isinstance(title, str) or not title or not isinstance(url, str):
            raise ValueError("missing announcement title or URL")
        parsed = urlsplit(url)
        if (parsed.scheme or parsed.netloc or not parsed.path.startswith("/disclosure/fund/announcement/")
                or not parsed.path.endswith(".pdf") or ".." in parsed.path.split("/")
                or parsed.query or parsed.fragment or parsed.path.rsplit("/", 1)[-1].split("_")[0] != code):
            raise ValueError("announcement URL is outside the official fund PDF scope")
        if url in urls:
            raise ValueError("duplicate announcement URL")
        urls.add(url)
        kind = None
        if "分红" in title or "收益分配" in title or "利润分配" in title:
            kind = "cash_distribution_notice"
        if any(word in title for word in ("折算", "拆分", "合并", "终止", "转型", "更正")):
            kind = "manual_action_review"
        result.append({**row, "review_kind": kind})
    return result


def _notice_date(text: str, label: str) -> date:
    year, month, day = _one(re.escape(label) + r"[：:]?([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日", text, label)
    return date(int(year), int(month), int(day))


def _one(pattern: str, text: str, label: str) -> Any:
    values = re.findall(pattern, text)
    if len(values) != 1:
        raise ValueError(f"missing or ambiguous {label}")
    return values[0]


def _sse_code(symbol: str) -> str:
    if not isinstance(symbol, str) or not re.fullmatch(r"[0-9]{6}\.SH", symbol):
        raise ValueError("SSE notice reviewer requires an explicit six-digit .SH symbol")
    return symbol[:6]


def _iso(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("date must be ISO YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if value != parsed.isoformat():
        raise ValueError("date must be ISO YYYY-MM-DD")
    return parsed
