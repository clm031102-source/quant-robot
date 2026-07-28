from __future__ import annotations

import hashlib
import io
import json
import random
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


SSE_SHARE_SOURCE = "sse_official_etf_scale"
SZSE_SHARE_SOURCE = "szse_official_fund_scale"
EASTMONEY_NAV_SOURCE = "eastmoney_fund_detail_history"

SHARE_COLUMNS = [
    "date",
    "asset_id",
    "symbol",
    "exchange",
    "total_share",
    "share_source",
]
NAV_COLUMNS = [
    "date",
    "asset_id",
    "symbol",
    "exchange",
    "nav",
    "nav_source",
]


class ProviderResponseError(ValueError):
    def __init__(self, message: str, *, category: str = "invalid_provider_response") -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class FetchedFrame:
    frame: pd.DataFrame
    response_sha256: str
    request_url: str
    source: str


def parse_sse_share_response(payload: dict[str, Any], *, requested_date: str) -> pd.DataFrame:
    result = payload.get("result")
    if not isinstance(result, list):
        raise ProviderResponseError("SSE ETF share response schema is missing result rows")
    requested = pd.to_datetime(requested_date, errors="raise").date()
    rows: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        code = str(item.get("SEC_CODE", "")).strip()
        if not re.fullmatch(r"\d{6}", code):
            continue
        observed_date = pd.to_datetime(item.get("STAT_DATE"), errors="coerce")
        if pd.isna(observed_date) or observed_date.date() != requested:
            raise ProviderResponseError(
                f"SSE ETF share response does not match requested date {requested.isoformat()}"
            )
        share = pd.to_numeric(item.get("TOT_VOL"), errors="coerce")
        if pd.isna(share) or float(share) <= 0.0:
            raise ProviderResponseError("SSE ETF share response contains a non-positive share value")
        symbol = f"{code}.SH"
        rows.append(
            {
                "date": requested,
                "asset_id": _asset_id(symbol),
                "symbol": symbol,
                "exchange": "SSE",
                "total_share": float(share) * 10_000.0,
                "share_source": SSE_SHARE_SOURCE,
            }
        )
    frame = pd.DataFrame(rows, columns=SHARE_COLUMNS)
    _reject_duplicates(frame, ["asset_id", "date"], "SSE ETF share response")
    return frame.sort_values(["date", "asset_id"]).reset_index(drop=True)


def parse_szse_share_workbook(content: bytes) -> pd.DataFrame:
    try:
        raw = pd.read_excel(io.BytesIO(content), engine="openpyxl").dropna(how="all")
    except Exception as exc:
        raise ProviderResponseError("SZSE ETF share workbook could not be parsed") from exc
    required = {"日期", "基金代码", "基金简称"}
    share_column = _first_present(raw.columns, ("基金规模(份)", "基金份额"))
    if not required.issubset(set(raw.columns)) or share_column is None:
        raise ProviderResponseError("SZSE ETF share workbook schema is invalid")
    codes = pd.to_numeric(raw["基金代码"], errors="coerce")
    dates = pd.to_datetime(raw["日期"], errors="coerce")
    shares = pd.to_numeric(
        raw[share_column].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    valid = codes.notna() & dates.notna() & shares.notna()
    source = raw.loc[valid].copy()
    codes = codes.loc[valid].astype(int).astype(str).str.zfill(6)
    dates = dates.loc[valid].dt.date
    shares = shares.loc[valid].astype(float)
    if (shares <= 0.0).any():
        raise ProviderResponseError("SZSE ETF share workbook contains a non-positive share value")
    rows = []
    for idx, code in codes.items():
        symbol = f"{code}.SZ"
        rows.append(
            {
                "date": dates.loc[idx],
                "asset_id": _asset_id(symbol),
                "symbol": symbol,
                "exchange": "SZSE",
                "total_share": float(shares.loc[idx]),
                "share_source": SZSE_SHARE_SOURCE,
            }
        )
    frame = pd.DataFrame(rows, columns=SHARE_COLUMNS)
    _reject_duplicates(frame, ["asset_id", "date"], "SZSE ETF share workbook")
    return frame.sort_values(["date", "asset_id"]).reset_index(drop=True)


def parse_eastmoney_nav_javascript(
    javascript: str,
    *,
    symbol: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    match = re.search(r"var\s+Data_netWorthTrend\s*=\s*(.*?);", javascript, flags=re.DOTALL)
    if match is None:
        raise ProviderResponseError(
            "Eastmoney response is missing Data_netWorthTrend",
            category="missing_nav_dataset",
        )
    try:
        raw_rows = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("Eastmoney Data_netWorthTrend is not valid JSON") from exc
    if not isinstance(raw_rows, list):
        raise ProviderResponseError("Eastmoney Data_netWorthTrend schema is invalid")
    normalized_symbol = _normalize_symbol(symbol)
    start = pd.to_datetime(start_date, errors="raise").date()
    end = pd.to_datetime(end_date, errors="raise").date()
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    rows = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        timestamp = pd.to_numeric(item.get("x"), errors="coerce")
        nav = pd.to_numeric(item.get("y"), errors="coerce")
        if pd.isna(timestamp) or pd.isna(nav):
            continue
        observed_date = (
            pd.to_datetime(float(timestamp), unit="ms", utc=True)
            .tz_convert("Asia/Shanghai")
            .date()
        )
        if observed_date < start or observed_date > end:
            continue
        if float(nav) <= 0.0:
            raise ProviderResponseError("Eastmoney NAV response contains a non-positive NAV value")
        rows.append(
            {
                "date": observed_date,
                "asset_id": _asset_id(normalized_symbol),
                "symbol": normalized_symbol,
                "exchange": _exchange(normalized_symbol),
                "nav": float(nav),
                "nav_source": EASTMONEY_NAV_SOURCE,
            }
        )
    frame = pd.DataFrame(rows, columns=NAV_COLUMNS)
    _reject_duplicates(frame, ["asset_id", "date"], "Eastmoney NAV response")
    return frame.sort_values(["date", "asset_id"]).reset_index(drop=True)


class PublicCnEtfFundStructureAdapter:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        max_retries: int = 4,
        backoff_factor: float = 0.75,
        connect_timeout_seconds: float = 15.0,
        read_timeout_seconds: float = 60.0,
    ) -> None:
        self.session = session or _retry_session(max_retries=max_retries, backoff_factor=backoff_factor)
        self.timeout = (connect_timeout_seconds, read_timeout_seconds)

    def fetch_sse_share_date(self, trade_date: str) -> FetchedFrame:
        date_text = pd.to_datetime(trade_date).date().isoformat()
        url = "https://query.sse.com.cn/commonQuery.do"
        params = {
            "isPagination": "true",
            "pageHelp.pageSize": "10000",
            "pageHelp.pageNo": "1",
            "pageHelp.beginPage": "1",
            "pageHelp.cacheSize": "1",
            "pageHelp.endPage": "1",
            "sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
            "STAT_DATE": date_text,
        }
        headers = {
            "Referer": "https://www.sse.com.cn/",
            "User-Agent": _user_agent(),
        }
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        content = response.content
        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            raise ProviderResponseError("SSE ETF share response is not JSON") from exc
        return FetchedFrame(
            frame=parse_sse_share_response(payload, requested_date=date_text),
            response_sha256=hashlib.sha256(content).hexdigest(),
            request_url=response.url,
            source=SSE_SHARE_SOURCE,
        )

    def fetch_szse_share_window(self, start_date: str, end_date: str) -> FetchedFrame:
        start = pd.to_datetime(start_date).date()
        end = pd.to_datetime(end_date).date()
        if start > end:
            raise ValueError("start_date must be on or before end_date")
        if (end - start).days > 183:
            raise ValueError("SZSE ETF share request window cannot exceed six months")
        url = "https://www.szse.cn/api/report/ShowReport"
        params = {
            "SHOWTYPE": "xlsx",
            "CATALOGID": "scsj_fund_jjgm",
            "TABKEY": "tab1",
            "txtStart": start.isoformat(),
            "txtEnd": end.isoformat(),
            "jjlb": "ETF",
            "random": str(random.random()),
        }
        headers = {
            "Host": "www.szse.cn",
            "Referer": "https://www.szse.cn/market/fund/volume/etf/index.html",
            "User-Agent": _user_agent(),
        }
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        content = response.content
        return FetchedFrame(
            frame=parse_szse_share_workbook(content),
            response_sha256=hashlib.sha256(content).hexdigest(),
            request_url=response.url,
            source=SZSE_SHARE_SOURCE,
        )

    def fetch_eastmoney_nav_symbol(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> FetchedFrame:
        normalized_symbol = _normalize_symbol(symbol)
        code = normalized_symbol.split(".", 1)[0]
        url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
        headers = {
            "Referer": f"https://fund.eastmoney.com/{code}.html",
            "User-Agent": _user_agent(),
        }
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        content = response.content
        response.encoding = response.apparent_encoding or "utf-8"
        javascript = response.text
        return FetchedFrame(
            frame=parse_eastmoney_nav_javascript(
                javascript,
                symbol=normalized_symbol,
                start_date=start_date,
                end_date=end_date,
            ),
            response_sha256=hashlib.sha256(content).hexdigest(),
            request_url=response.url,
            source=EASTMONEY_NAV_SOURCE,
        )


def _retry_session(*, max_retries: int, backoff_factor: float) -> requests.Session:
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _normalize_symbol(symbol: str) -> str:
    value = str(symbol).strip().upper()
    if not re.fullmatch(r"\d{6}\.(SH|SZ)", value):
        raise ValueError(f"Unsupported CN ETF symbol: {symbol}")
    return value


def _asset_id(symbol: str) -> str:
    normalized = _normalize_symbol(symbol)
    code, suffix = normalized.split(".", 1)
    exchange = {"SH": "XSHG", "SZ": "XSHE"}[suffix]
    return f"CN_ETF_{exchange}_{code}"


def _exchange(symbol: str) -> str:
    return {"SH": "SSE", "SZ": "SZSE"}[_normalize_symbol(symbol).split(".", 1)[1]]


def _first_present(columns: pd.Index, candidates: tuple[str, ...]) -> str | None:
    available = set(columns)
    return next((candidate for candidate in candidates if candidate in available), None)


def _reject_duplicates(frame: pd.DataFrame, columns: list[str], context: str) -> None:
    if not frame.empty and frame.duplicated(columns).any():
        raise ProviderResponseError(f"{context} contains duplicate asset-date rows")


def _user_agent() -> str:
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
