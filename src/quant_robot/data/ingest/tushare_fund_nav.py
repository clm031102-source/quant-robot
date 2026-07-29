from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from quant_robot.data.sources.tushare_mapping import FUND_NAV_COLUMNS
from quant_robot.storage.atomic import atomic_write, atomic_write_json


CANONICAL_COLUMNS = [
    "nav_date",
    "ann_date",
    "known_from",
    "asset_id",
    "symbol",
    "exchange",
    "unit_nav",
    "accum_nav",
    "total_netasset",
    "update_flag",
    "is_pit_usable",
    "source",
]

_OPTIONAL_NUMERIC_COLUMNS = ["accum_nav", "total_netasset", "update_flag"]
_CONFLICT_VALUE_COLUMNS = ["unit_nav", "accum_nav", "total_netasset"]
_EXCHANGE_DETAILS = {
    "SSE": (".SH", "XSHG"),
    "SH": (".SH", "XSHG"),
    "XSHG": (".SH", "XSHG"),
    "SZSE": (".SZ", "XSHE"),
    "SZ": (".SZ", "XSHE"),
    "XSHE": (".SZ", "XSHE"),
}

MANIFEST_SCHEMA_VERSION = 1
REQUEST_MANIFEST_NAME = "request_manifest.json"
CANONICAL_MANIFEST_NAME = "canonical_manifest.json"


class FundNavAdapter(Protocol):
    def fetch_fund_nav(
        self,
        ts_code: str,
        start_date: str = "",
        end_date: str = "",
        market: str = "E",
    ) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class TushareFundNavIngestResult:
    manifest_path: Path
    canonical_path: Path
    canonical_manifest_path: Path
    summary: dict[str, Any]


def build_tushare_fund_nav_request_plan(
    target_universe: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
) -> pd.DataFrame:
    required = {"etf_code", "market_exchange", "list_date", "delist_date"}
    missing = sorted(required - set(target_universe.columns))
    if missing:
        raise ValueError(f"target universe is missing columns: {', '.join(missing)}")

    analysis_start = _as_date(start_date, "start_date")
    analysis_end = _as_date(end_date, "end_date")
    if analysis_start > analysis_end:
        raise ValueError("start_date must be on or before end_date")

    rows: list[dict[str, object]] = []
    for record in target_universe.to_dict(orient="records"):
        exchange_key = str(record["market_exchange"]).strip().upper()
        if exchange_key not in _EXCHANGE_DETAILS:
            raise ValueError(f"unsupported ETF exchange: {exchange_key}")
        expected_suffix, canonical_exchange = _EXCHANGE_DETAILS[exchange_key]
        raw_symbol = str(record["etf_code"]).strip().upper()
        symbol = raw_symbol if raw_symbol.endswith((".SH", ".SZ")) else raw_symbol + expected_suffix
        if not symbol.endswith(expected_suffix):
            raise ValueError(
                f"ETF symbol/exchange mismatch: {symbol} does not match {exchange_key}"
            )
        code = symbol.split(".", maxsplit=1)[0]
        if not code.isdigit() or len(code) != 6:
            raise ValueError(f"invalid ETF symbol: {symbol}")

        list_date = _as_optional_date(record["list_date"], f"{symbol} list_date")
        if list_date is None:
            raise ValueError(f"{symbol} list_date is required")
        delist_date = _as_optional_date(record["delist_date"], f"{symbol} delist_date")
        request_start = max(analysis_start, list_date)
        request_end = min(analysis_end, delist_date or analysis_end)
        if request_start > request_end:
            continue
        rows.append(
            {
                "asset_id": f"CN_ETF_{canonical_exchange}_{code}",
                "symbol": symbol,
                "exchange": canonical_exchange,
                "request_start": request_start,
                "request_end": request_end,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=["asset_id", "symbol", "exchange", "request_start", "request_end"],
    )
    if result["symbol"].duplicated().any():
        duplicates = sorted(result.loc[result["symbol"].duplicated(keep=False), "symbol"].unique())
        raise ValueError(f"target universe contains duplicate ETF symbols: {', '.join(duplicates[:5])}")
    return result.sort_values("symbol").reset_index(drop=True)


def canonicalize_tushare_fund_nav(
    raw: pd.DataFrame,
    trading_sessions: Sequence[pd.Timestamp],
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    source: str = "tushare_fund_nav",
) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    required = {"symbol", "nav_date", "ann_date", "unit_nav"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Tushare fund NAV input is missing columns: {', '.join(missing)}")

    sessions = pd.DatetimeIndex(pd.to_datetime(pd.Series(trading_sessions), errors="raise")).normalize()
    if sessions.empty:
        raise ValueError("trading_sessions must not be empty")
    if sessions.duplicated().any():
        raise ValueError("trading_sessions contains duplicate dates")
    if not sessions.is_monotonic_increasing:
        sessions = sessions.sort_values()

    frame = raw.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    invalid_symbols = ~frame["symbol"].str.fullmatch(r"\d{6}\.(SH|SZ)")
    if invalid_symbols.any():
        raise ValueError(f"invalid ETF symbol: {frame.loc[invalid_symbols, 'symbol'].iloc[0]}")
    frame["nav_date"] = pd.to_datetime(frame["nav_date"], errors="coerce").dt.normalize()
    if frame["nav_date"].isna().any():
        raise ValueError("Tushare fund NAV input contains invalid nav_date")
    frame["ann_date"] = pd.to_datetime(frame["ann_date"], errors="coerce").dt.normalize()
    frame["unit_nav"] = pd.to_numeric(frame["unit_nav"], errors="coerce")
    for column in _OPTIONAL_NUMERIC_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if start_date is not None:
        start = pd.Timestamp(start_date).normalize()
        frame = frame.loc[frame["nav_date"] >= start].copy()
    if end_date is not None:
        end = pd.Timestamp(end_date).normalize()
        frame = frame.loc[frame["nav_date"] <= end].copy()
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    selected_rows = []
    for _, group in frame.groupby(["symbol", "nav_date"], sort=True, dropna=False):
        selected_rows.append(_select_revision(group).iloc[0].to_dict())
    selected = pd.DataFrame(selected_rows)
    selected["exchange"] = selected["symbol"].map(
        lambda value: "XSHG" if value.endswith(".SH") else "XSHE"
    )
    selected["asset_id"] = selected.apply(
        lambda row: f"CN_ETF_{row['exchange']}_{row['symbol'].split('.')[0]}",
        axis=1,
    )

    known_from: list[pd.Timestamp | pd.NaT] = []
    pit_usable: list[bool] = []
    for row in selected.itertuples(index=False):
        valid_lag = pd.notna(row.ann_date) and row.ann_date >= row.nav_date
        next_session: pd.Timestamp | pd.NaT = pd.NaT
        if valid_lag:
            cutoff = max(row.nav_date, row.ann_date)
            position = sessions.searchsorted(cutoff, side="right")
            if position < len(sessions):
                next_session = sessions[position]
        positive_nav = bool(np.isfinite(row.unit_nav) and row.unit_nav > 0.0)
        known_from.append(next_session)
        pit_usable.append(bool(valid_lag and pd.notna(next_session) and positive_nav))
    selected["known_from"] = known_from
    selected["is_pit_usable"] = pit_usable
    selected["source"] = source

    for column in ["nav_date", "ann_date", "known_from"]:
        selected[column] = pd.to_datetime(selected[column], errors="coerce").dt.date
    result = selected[CANONICAL_COLUMNS].sort_values(["asset_id", "nav_date"]).reset_index(drop=True)
    if result.duplicated(["asset_id", "nav_date"]).any():
        raise ValueError("canonical Tushare fund NAV contains duplicate asset-date rows")
    return result


def run_tushare_fund_nav_ingest(
    *,
    adapter: FundNavAdapter,
    target_universe: pd.DataFrame,
    trading_sessions: Sequence[pd.Timestamp],
    output_dir: str | Path,
    start_date: str,
    end_date: str,
    request_sleep_seconds: float = 0.35,
) -> TushareFundNavIngestResult:
    if request_sleep_seconds < 0.0:
        raise ValueError("request_sleep_seconds must be non-negative")
    output = Path(output_dir)
    source_dir = output / "source"
    canonical_dir = output / "canonical"
    source_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)
    request_plan = build_tushare_fund_nav_request_plan(
        target_universe,
        start_date=start_date,
        end_date=end_date,
    )
    scope = {
        "analysis_start": _as_date(start_date, "start_date").isoformat(),
        "analysis_end": _as_date(end_date, "end_date").isoformat(),
        "symbols": request_plan["symbol"].tolist(),
    }
    manifest_path = output / REQUEST_MANIFEST_NAME
    manifest = _load_or_create_request_manifest(manifest_path, scope)
    resumed = 0

    for request in request_plan.to_dict(orient="records"):
        symbol = str(request["symbol"])
        parameters = {
            "ts_code": symbol,
            "market": "E",
            "start_date": request["request_start"].isoformat(),
            "end_date": request["request_end"].isoformat(),
        }
        request_sha256 = _json_sha256(parameters)
        source_path = source_dir / f"{symbol.replace('.', '_')}.parquet"
        prior = manifest["requests"].get(symbol, {})
        if (
            prior.get("status") in {"completed", "empty"}
            and prior.get("request_sha256") == request_sha256
            and source_path.exists()
        ):
            resumed += 1
            continue
        try:
            fetched = adapter.fetch_fund_nav(
                symbol,
                start_date=parameters["start_date"],
                end_date=parameters["end_date"],
                market="E",
            )
            provider_frame = fetched.copy()
            if provider_frame.empty:
                provider_frame = pd.DataFrame(columns=FUND_NAV_COLUMNS)
            _atomic_write_parquet(source_path, provider_frame)
            manifest["requests"][symbol] = {
                "status": "empty" if provider_frame.empty else "completed",
                "parameters": parameters,
                "request_sha256": request_sha256,
                "response_sha256": _frame_sha256(provider_frame),
                "rows": int(len(provider_frame)),
                "source_path": str(source_path),
            }
        except Exception as exc:
            manifest["requests"][symbol] = {
                "status": "failed",
                "parameters": parameters,
                "request_sha256": request_sha256,
                "rows": 0,
                "error_type": type(exc).__name__,
                "error_message_sha256": hashlib.sha256(
                    str(exc).encode("utf-8", errors="replace")
                ).hexdigest(),
            }
        atomic_write_json(manifest_path, manifest)
        if request_sleep_seconds > 0.0:
            time.sleep(request_sleep_seconds)

    source_frames = []
    for symbol in request_plan["symbol"]:
        row = manifest["requests"].get(symbol, {})
        if row.get("status") != "completed":
            continue
        source_path = Path(str(row["source_path"]))
        if not source_path.exists():
            raise ValueError(f"completed NAV request is missing its source partition: {symbol}")
        source_frames.append(pd.read_parquet(source_path))
    raw = (
        pd.concat(source_frames, ignore_index=True)
        if source_frames
        else pd.DataFrame(columns=FUND_NAV_COLUMNS)
    )
    canonical = canonicalize_tushare_fund_nav(
        raw,
        trading_sessions,
        start_date=start_date,
        end_date=end_date,
    )
    canonical_path = canonical_dir / "nav.parquet"
    _atomic_write_parquet(canonical_path, canonical)

    statuses = [
        str(manifest["requests"].get(symbol, {}).get("status", "unresolved"))
        for symbol in request_plan["symbol"]
    ]
    request_summary = {
        "total": int(len(statuses)),
        "completed": statuses.count("completed"),
        "empty": statuses.count("empty"),
        "failed": statuses.count("failed"),
        "unresolved": statuses.count("unresolved"),
        "resumed": int(resumed),
    }
    canonical_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": "tushare_fund_nav_ingest",
        "status": "completed"
        if request_summary["failed"] == 0 and request_summary["unresolved"] == 0
        else "partial",
        "scope": scope,
        "request_manifest_path": str(manifest_path),
        "canonical_path": str(canonical_path),
        "canonical_sha256": _frame_sha256(canonical),
        "canonical_rows": int(len(canonical)),
        "canonical_assets": int(canonical["asset_id"].nunique()) if not canonical.empty else 0,
        "request_summary": request_summary,
        "boundaries": _disabled_boundaries(),
    }
    canonical_manifest_path = output / CANONICAL_MANIFEST_NAME
    atomic_write_json(canonical_manifest_path, canonical_manifest)
    summary = {
        **canonical_manifest,
        "manifest_path": str(manifest_path),
        "canonical_manifest_path": str(canonical_manifest_path),
    }
    return TushareFundNavIngestResult(
        manifest_path=manifest_path,
        canonical_path=canonical_path,
        canonical_manifest_path=canonical_manifest_path,
        summary=summary,
    )


def _select_revision(group: pd.DataFrame) -> pd.DataFrame:
    working = group.copy()
    announcement_rank = working["ann_date"].fillna(pd.Timestamp.min)
    latest_announcement = announcement_rank.max()
    candidates = working.loc[announcement_rank == latest_announcement].copy()
    update_rank = candidates["update_flag"].fillna(float("-inf"))
    highest_update = update_rank.max()
    candidates = candidates.loc[update_rank == highest_update].copy()
    if len(candidates) > 1:
        comparison = candidates[_CONFLICT_VALUE_COLUMNS].copy()
        first = comparison.iloc[0]
        same = comparison.apply(lambda row: _values_equal(row, first), axis=1)
        if not bool(same.all()):
            symbol = str(candidates["symbol"].iloc[0])
            nav_date = pd.Timestamp(candidates["nav_date"].iloc[0]).date().isoformat()
            raise ValueError(f"conflicting NAV revisions for {symbol} on {nav_date}")
    return candidates.iloc[[0]]


def _values_equal(left: pd.Series, right: pd.Series) -> bool:
    for column in _CONFLICT_VALUE_COLUMNS:
        left_value = left[column]
        right_value = right[column]
        if pd.isna(left_value) and pd.isna(right_value):
            continue
        if left_value != right_value:
            return False
    return True


def _load_or_create_request_manifest(path: Path, scope: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "stage": "tushare_fund_nav_requests",
            "scope": scope,
            "requests": {},
            "boundaries": _disabled_boundaries(),
        }
        atomic_write_json(path, manifest)
        return manifest
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"unsupported Tushare fund NAV manifest schema: {path}")
    if manifest.get("scope") != scope:
        raise ValueError(f"Tushare fund NAV manifest scope mismatch: {path}")
    if not isinstance(manifest.get("requests"), dict):
        raise ValueError(f"Tushare fund NAV manifest requests are invalid: {path}")
    return manifest


def _atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    atomic_write(path, lambda temporary: frame.to_parquet(temporary, index=False))


def _frame_sha256(frame: pd.DataFrame) -> str:
    stable = frame.copy()
    stable = stable.reindex(sorted(stable.columns), axis=1)
    if not stable.empty:
        stable = stable.sort_values(list(stable.columns), na_position="last").reset_index(drop=True)
    payload = stable.to_csv(index=False, lineterminator="\n", na_rep="<NA>")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _disabled_boundaries() -> dict[str, bool]:
    return {
        "factor_generation_allowed": False,
        "forward_return_read": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "promotion_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_boundary_allowed": False,
    }


def _as_date(value: object, label: str):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{label} is not a valid date")
    return parsed.date()


def _as_optional_date(value: object, label: str):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return _as_date(value, label)
