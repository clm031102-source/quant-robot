"""Bounded HTTPS reads for independently scoped Tushare source qualification.

This opt-in client does not alter the installed SDK, system proxy, research
permissions, or default adapters. Callers must persist their scope and evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone

import pandas as pd


_PRIMARY_DATE = {
    "fund_adj": "trade_date", "fund_div": "ann_date",
    "anns_d": "ann_date", "etf_limit": "trade_date",
}


class TushareSourceError(RuntimeError):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(f"{kind}: {message}")


def _new_session():
    import requests

    return requests.Session()


def _date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        raise TushareSourceError("invalid_scope", "dates require YYYYMMDD")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise TushareSourceError("invalid_scope", "invalid calendar date") from exc
    return value


def _positive_integer(value: int) -> bool:
    return type(value) is int and value > 0


class TushareSourceHttpClient:
    def __init__(
        self, *, token: str, max_requests: int, max_date: str,
        trust_env: bool = True, max_response_bytes: int = 2_000_000,
        connect_timeout: float = 10, read_timeout: float = 20,
    ) -> None:
        if not isinstance(token, str) or not token.strip():
            raise TushareSourceError("invalid_scope", "existing token is required")
        if not _positive_integer(max_requests) or not _positive_integer(max_response_bytes):
            raise TushareSourceError("invalid_scope", "positive request/byte budgets are required")
        if type(trust_env) is not bool:
            raise TushareSourceError("invalid_scope", "trust_env must be explicit boolean")
        for timeout in (connect_timeout, read_timeout):
            if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
                raise TushareSourceError("invalid_scope", "timeouts must be finite and positive")
        self._token = token
        self.max_requests = max_requests
        self.max_date = _date(max_date)
        self.trust_env = trust_env
        self.max_response_bytes = max_response_bytes
        self.timeout = (connect_timeout, read_timeout)
        self.requests_used = 0
        self.last_attempt: dict[str, object] = {}
        self.last_payload: dict[str, object] | None = None

    def validate_query(self, api_name: str, *, fields: str, max_rows: int, **params) -> None:
        """Validate one request without credentials use, network, or budget consumption."""
        self._scope(api_name, fields, max_rows, params)

    def _scope(self, api_name, fields, max_rows, params):
        if not isinstance(api_name, str) or api_name not in _PRIMARY_DATE:
            raise TushareSourceError("invalid_scope", "unsupported source API")
        if not isinstance(fields, str) or not _positive_integer(max_rows):
            raise TushareSourceError("invalid_scope", "explicit fields and row budget required")
        names = fields.split(",")
        if any(not name or not name.isidentifier() for name in names) or len(set(names)) != len(names):
            raise TushareSourceError("invalid_scope", "fields must be unique identifiers")
        primary = _PRIMARY_DATE[api_name]
        point_dates = {"ann_date", "ex_date", "pay_date"} if api_name == "fund_div" else {primary}
        allowed = {"ts_code", *point_dates}
        if api_name != "fund_div":
            allowed |= {"start_date", "end_date"}
        if not set(params) <= allowed:
            raise TushareSourceError("invalid_scope", "unsupported query parameters")
        points = set(params) & point_dates
        ranged = "start_date" in params or "end_date" in params
        if (len(points) != 1 and not ranged) or (points and ranged):
            raise TushareSourceError("invalid_scope", "one date or a closed range is required")
        if ranged and not {"start_date", "end_date"} <= set(params):
            raise TushareSourceError("invalid_scope", "both range bounds are required")
        for key, value in params.items():
            if key != "ts_code" and _date(value) > self.max_date:
                raise TushareSourceError("invalid_scope", "request exceeds frozen date ceiling")
        if ranged and params["start_date"] > params["end_date"]:
            raise TushareSourceError("invalid_scope", "inverted date range")
        if "ts_code" in params and not re.fullmatch(r"[0-9]{6}\.(SH|SZ)", str(params["ts_code"])):
            raise TushareSourceError("invalid_scope", "one explicit SH/SZ code is required")
        if not {"ts_code", primary, *points} <= set(names):
            raise TushareSourceError("invalid_scope", "identity and scope date fields required")
        return names, primary, points

    def _frame(self, parsed, names, primary, points, max_rows, params):
        if not isinstance(parsed, dict) or type(parsed.get("code")) is not int:
            raise TushareSourceError("response_schema", "provider code missing or invalid")
        self.last_attempt["api_code"] = parsed["code"]
        if parsed["code"] != 0:
            raise TushareSourceError("provider_rejected", str(parsed.get("msg", "request rejected")).replace(self._token, "[REDACTED]"))
        data = parsed.get("data")
        if not isinstance(data, dict):
            raise TushareSourceError("response_schema", "data object missing")
        page = {key: data[key] for key in ("has_more", "count") if key in data}
        if "has_more" in page and type(page["has_more"]) is not bool:
            raise TushareSourceError("response_schema", "invalid has_more metadata")
        if "count" in page and (type(page["count"]) is not int or page["count"] < 0):
            raise TushareSourceError("response_schema", "invalid count metadata")
        self.last_attempt["provider_page_metadata"] = page
        if page.get("has_more") is True:
            raise TushareSourceError("response_incomplete", "provider reports more pages; no automatic pagination")
        columns, rows = data.get("fields"), data.get("items")
        if not isinstance(columns, list) or columns != list(dict.fromkeys(columns)) or set(columns) != set(names):
            raise TushareSourceError("response_schema", "columns differ from requested fields")
        if not isinstance(rows, list) or len(rows) > max_rows:
            raise TushareSourceError("response_schema", "row budget exceeded or rows invalid")
        cleaned = []
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns):
                raise TushareSourceError("response_schema", "invalid row width")
            if any(value is not None and not isinstance(value, (str, int, float)) for value in row):
                raise TushareSourceError("response_schema", "source fields must be scalar values")
            if any(isinstance(value, float) and not math.isfinite(value) for value in row):
                raise TushareSourceError("response_schema", "nonfinite source value")
            record = dict(zip(columns, row, strict=True))
            if _date(record[primary]) > self.max_date:
                raise TushareSourceError("response_scope", "response exceeds frozen date ceiling")
            if any(record[key] != params[key] for key in points):
                raise TushareSourceError("response_scope", "response date differs from request")
            if "start_date" in params and not params["start_date"] <= record[primary] <= params["end_date"]:
                raise TushareSourceError("response_scope", "response outside date range")
            if "ts_code" in params and record["ts_code"] != params["ts_code"]:
                raise TushareSourceError("response_scope", "response symbol differs from request")
            cleaned.append([value.replace(self._token, "[REDACTED]") if isinstance(value, str) else value for value in row])
        # Preserve provider scalar types/nulls before DataFrame type coercion.
        # This validated, redacted projection is not the original HTTP body.
        self.last_payload = {"code": 0, "data": {"fields": columns, "items": cleaned, **page}}
        return pd.DataFrame(cleaned, columns=columns)

    def query(self, api_name: str, *, fields: str, max_rows: int, **params) -> pd.DataFrame:
        names, primary, points = self._scope(api_name, fields, max_rows, params)
        if self.requests_used >= self.max_requests:
            raise TushareSourceError("request_budget", "frozen request budget exhausted")
        self.requests_used += 1
        self.last_payload = None
        self.last_attempt = {"api_name": api_name, "request_number": self.requests_used,
            "status": "started", "trust_env": self.trust_env,
            "params": dict(params), "fields": fields, "max_rows": max_rows,
            "max_date": self.max_date,
            "started_at": datetime.now(timezone.utc).isoformat()}
        try:
            with _new_session() as session:
                session.trust_env = self.trust_env
                with session.post("https://api.tushare.pro", json={"api_name": api_name,
                        "token": self._token, "params": params, "fields": fields},
                        timeout=self.timeout, stream=True, allow_redirects=False, verify=True) as response:
                    self.last_attempt["http_status"] = response.status_code
                    if response.status_code != 200:
                        raise TushareSourceError("http_error", f"HTTP {response.status_code}")
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=65536):
                        size += len(chunk)
                        if size > self.max_response_bytes:
                            raise TushareSourceError("response_size", "response exceeds byte budget")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
            self.last_attempt.update(response_bytes=len(raw), response_sha256=hashlib.sha256(raw).hexdigest())
            parsed = json.loads(raw)
            frame = self._frame(parsed, names, primary, points, max_rows, params)
            self.last_attempt.update(status="empty_unqualified" if frame.empty else "received", rows=len(frame))
            return frame
        except Exception as exc:
            kind = exc.kind if isinstance(exc, TushareSourceError) else "transport_or_decode_error"
            message = str(exc).replace(self._token, "[REDACTED]")
            self.last_attempt.update(status="failed", failure_kind=kind, message=message)
            raise TushareSourceError(kind, message) from None
        finally:
            self.last_attempt["finished_at"] = datetime.now(timezone.utc).isoformat()
