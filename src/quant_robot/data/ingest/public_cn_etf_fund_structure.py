from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
import pandas as pd

from quant_robot.data.adapters.public_cn_etf_fund_structure import (
    FetchedFrame,
    ProviderResponseError,
)
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.dataset_store import DatasetStore


MANIFEST_SCHEMA_VERSION = 1
MANIFEST_NAME = "public_source_manifest.json"
QUALITY_REPORT_NAME = "etf_share_size_quality_report.json"

CANONICAL_COLUMNS = [
    "date",
    "known_from",
    "asset_id",
    "symbol",
    "market",
    "exchange",
    "total_share",
    "nav",
    "close",
    "total_size",
    "share_change_1d",
    "size_change_1d",
    "nav_premium_discount",
    "share_source",
    "nav_source",
    "close_source",
    "source",
    "ingested_at",
]


class PublicFundStructureAdapter(Protocol):
    def fetch_sse_share_date(self, trade_date: str) -> FetchedFrame:
        ...

    def fetch_szse_share_window(self, start_date: str, end_date: str) -> FetchedFrame:
        ...

    def fetch_eastmoney_nav_symbol(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> FetchedFrame:
        ...


def build_public_source_request_plan(
    bars: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    szse_window_days: int = 183,
) -> dict[str, Any]:
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    if szse_window_days < 1 or szse_window_days > 184:
        raise ValueError("szse_window_days must be between 1 and 184")
    required = {"date", "symbol"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"bar authority is missing request-plan columns: {', '.join(missing)}")
    dates = pd.to_datetime(bars["date"], errors="coerce").dt.date
    inside = bars.loc[dates.between(start, end)].copy()
    inside_dates = pd.to_datetime(inside["date"], errors="coerce").dt.date
    sessions = sorted({value.isoformat() for value in inside_dates.dropna()})
    symbols = sorted(
        {
            value
            for value in inside["symbol"].astype(str).str.upper()
            if value.endswith((".SH", ".SZ")) and len(value) == 9
        }
    )
    windows = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + pd.Timedelta(days=szse_window_days - 1), end)
        windows.append({"start_date": cursor.isoformat(), "end_date": window_end.isoformat()})
        cursor = window_end + pd.Timedelta(days=1)
    return {
        "analysis_start": start.isoformat(),
        "analysis_end": end.isoformat(),
        "analysis_sessions": sessions,
        "symbols": symbols,
        "szse_windows": windows,
    }


def normalize_public_cn_etf_fund_structure(
    *,
    shares: pd.DataFrame,
    nav: pd.DataFrame,
    bars: pd.DataFrame,
    start_date: str,
    end_date: str,
    ingested_at: str | None = None,
    trading_sessions: list[str] | None = None,
) -> pd.DataFrame:
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    _require_columns(
        bars,
        ["date", "asset_id", "symbol", "close", "source"],
        "bar authority",
    )
    bar_frame = bars.copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"], errors="coerce").dt.date
    if bar_frame["date"].isna().any():
        raise ValueError("bar authority contains invalid dates")
    if bar_frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("bar authority contains duplicate bar asset-date rows")
    if trading_sessions is None:
        all_sessions = sorted(bar_frame["date"].unique())
    else:
        session_values = pd.to_datetime(pd.Series(trading_sessions), errors="raise").dt.date
        if session_values.duplicated().any():
            raise ValueError("trading_sessions contains duplicate dates")
        all_sessions = sorted(session_values.tolist())
        missing_bar_sessions = sorted(set(bar_frame["date"].unique()) - set(all_sessions))
        if missing_bar_sessions:
            raise ValueError(
                "trading_sessions does not cover bar authority dates: "
                + ", ".join(value.isoformat() for value in missing_bar_sessions[:5])
            )
    next_session = {
        all_sessions[index]: all_sessions[index + 1]
        for index in range(len(all_sessions) - 1)
    }

    _require_columns(
        shares,
        ["date", "asset_id", "symbol", "exchange", "total_share", "share_source"],
        "share inputs",
    )
    share_frame = shares.copy()
    share_frame["date"] = pd.to_datetime(share_frame["date"], errors="coerce").dt.date
    share_frame["total_share"] = pd.to_numeric(share_frame["total_share"], errors="coerce")
    share_frame = share_frame.loc[share_frame["date"].between(start, end)].copy()
    if share_frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("share inputs contain duplicate asset-date rows")

    _require_columns(
        nav,
        ["date", "asset_id", "symbol", "exchange", "nav", "nav_source"],
        "NAV inputs",
    )
    nav_frame = nav.copy()
    nav_frame["date"] = pd.to_datetime(nav_frame["date"], errors="coerce").dt.date
    nav_frame["nav"] = pd.to_numeric(nav_frame["nav"], errors="coerce")
    nav_frame = nav_frame.loc[nav_frame["date"].between(start, end)].copy()
    if nav_frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("NAV inputs contain duplicate asset-date rows")

    authority = bar_frame.loc[
        bar_frame["date"].between(start, end),
        ["date", "asset_id", "symbol", "close", "source"],
    ].copy()
    authority["close"] = pd.to_numeric(authority["close"], errors="coerce")
    authority = authority.rename(columns={"source": "close_source"})
    canonical = share_frame.merge(
        authority,
        on=["date", "asset_id", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    canonical = canonical.merge(
        nav_frame[["date", "asset_id", "nav", "nav_source"]],
        on=["date", "asset_id"],
        how="left",
        validate="one_to_one",
    )
    missing_next = sorted(
        {value for value in canonical["date"].dropna().unique() if value not in next_session}
    )
    if missing_next:
        raise ValueError(
            "share inputs do not have a next observed session for point-in-time lag: "
            + ", ".join(value.isoformat() for value in missing_next[:5])
        )
    canonical["known_from"] = canonical["date"].map(next_session)
    if not (pd.to_datetime(canonical["known_from"]) > pd.to_datetime(canonical["date"])).all():
        raise ValueError("canonical fund-structure rows violate the next observed session lag")
    canonical["market"] = "CN_ETF"
    canonical["source"] = "public_cn_etf_fund_structure"
    canonical["ingested_at"] = ingested_at or datetime.now(timezone.utc).isoformat()
    valid_nav = canonical["nav"].where(np.isfinite(canonical["nav"]) & (canonical["nav"] > 0.0))
    valid_share = canonical["total_share"].where(
        np.isfinite(canonical["total_share"]) & (canonical["total_share"] > 0.0)
    )
    valid_close = canonical["close"].where(
        np.isfinite(canonical["close"]) & (canonical["close"] > 0.0)
    )
    canonical["total_size"] = valid_share * valid_nav
    canonical["nav_premium_discount"] = valid_close / valid_nav - 1.0
    canonical = canonical.sort_values(["asset_id", "date"]).reset_index(drop=True)
    grouped = canonical.groupby("asset_id", sort=False)
    canonical["share_change_1d"] = grouped["total_share"].pct_change(fill_method=None)
    canonical["size_change_1d"] = grouped["total_size"].pct_change(fill_method=None)
    for column in CANONICAL_COLUMNS:
        if column not in canonical.columns:
            canonical[column] = pd.NA
    result = canonical[CANONICAL_COLUMNS].sort_values(["asset_id", "date"]).reset_index(drop=True)
    if result.duplicated(["asset_id", "date"]).any():
        raise ValueError("canonical fund-structure rows contain duplicate asset-date rows")
    return result


def run_public_cn_etf_fund_structure_ingest(
    *,
    adapter: PublicFundStructureAdapter,
    bars: pd.DataFrame,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    szse_window_days: int = 183,
    max_workers: int = 4,
    trading_sessions: list[str] | None = None,
) -> dict[str, Any]:
    if max_workers < 1 or max_workers > 16:
        raise ValueError("max_workers must be between 1 and 16")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(output)
    plan = build_public_source_request_plan(
        bars,
        start_date=start_date,
        end_date=end_date,
        szse_window_days=szse_window_days,
    )
    manifest_path = output / MANIFEST_NAME
    manifest = _load_manifest(manifest_path, plan)
    skipped_before = sum(1 for row in manifest["requests"].values() if row.get("status") == "completed")

    specs = _request_specs(adapter, plan)
    pending = [
        spec
        for spec in specs
        if not _completed_request_is_present(manifest, store, spec["key"])
    ]
    _run_pending_requests(
        pending=pending,
        manifest=manifest,
        manifest_path=manifest_path,
        store=store,
        max_workers=max_workers,
    )
    shares = _load_completed_frames(manifest, store, kinds={"sse_share", "szse_share"})
    nav = _load_completed_frames(manifest, store, kinds={"eastmoney_nav"})
    processed = normalize_public_cn_etf_fund_structure(
        shares=shares,
        nav=nav,
        bars=bars,
        start_date=start_date,
        end_date=end_date,
        trading_sessions=trading_sessions,
    )
    _write_processed_years(store, processed)
    quality = _quality_report(processed, plan)
    atomic_write_json(output / QUALITY_REPORT_NAME, quality)
    statuses = [str(row.get("status", "")) for row in manifest["requests"].values()]
    result = {
        "stage": "public_cn_etf_fund_structure_ingest",
        "status": "completed" if "failed" not in statuses else "partial",
        "analysis_start": plan["analysis_start"],
        "analysis_end": plan["analysis_end"],
        "processed_rows": int(len(processed)),
        "processed_assets": int(processed["asset_id"].nunique()) if not processed.empty else 0,
        "request_summary": {
            "total": len(statuses),
            "completed": statuses.count("completed"),
            "failed": statuses.count("failed"),
            "resumed_completed": skipped_before,
        },
        "quality_report": quality,
        "manifest_path": str(manifest_path),
        "output_dir": str(output),
        "factor_generation_allowed": False,
        "forward_return_read": False,
        "final_holdout_read": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "paper_signal_allowed": False,
        "live_boundary_allowed": False,
    }
    atomic_write_json(output / "public_cn_etf_fund_structure_ingest.json", result)
    return result


def _request_specs(adapter: PublicFundStructureAdapter, plan: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for trade_date in plan["analysis_sessions"]:
        specs.append(
            {
                "key": f"sse:{trade_date}",
                "kind": "sse_share",
                "dataset": "source/sse_share",
                "partitions": {"date": trade_date},
                "call": lambda value=trade_date: adapter.fetch_sse_share_date(value),
                "parameters": {"trade_date": trade_date},
            }
        )
    for window in plan["szse_windows"]:
        start = window["start_date"]
        end = window["end_date"]
        specs.append(
            {
                "key": f"szse:{start}:{end}",
                "kind": "szse_share",
                "dataset": "source/szse_share",
                "partitions": {"window": f"{start}_{end}"},
                "call": lambda first=start, last=end: adapter.fetch_szse_share_window(first, last),
                "parameters": {"start_date": start, "end_date": end},
            }
        )
    for symbol in plan["symbols"]:
        specs.append(
            {
                "key": f"nav:{symbol}",
                "kind": "eastmoney_nav",
                "dataset": "source/eastmoney_nav",
                "partitions": {"symbol": symbol.replace(".", "_")},
                "call": lambda value=symbol: adapter.fetch_eastmoney_nav_symbol(
                    value,
                    start_date=plan["analysis_start"],
                    end_date=plan["analysis_end"],
                ),
                "parameters": {
                    "symbol": symbol,
                    "start_date": plan["analysis_start"],
                    "end_date": plan["analysis_end"],
                },
            }
        )
    return specs


def _run_pending_requests(
    *,
    pending: list[dict[str, Any]],
    manifest: dict[str, Any],
    manifest_path: Path,
    store: DatasetStore,
    max_workers: int,
) -> None:
    futures: dict[Future[FetchedFrame], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for spec in pending:
            futures[executor.submit(spec["call"])] = spec
        for future in as_completed(futures):
            spec = futures[future]
            try:
                fetched = future.result()
                path = store.write_frame(fetched.frame, spec["dataset"], spec["partitions"])
                manifest["requests"][spec["key"]] = {
                    "status": "completed",
                    "kind": spec["kind"],
                    "dataset": spec["dataset"],
                    "partitions": spec["partitions"],
                    "parameters": spec["parameters"],
                    "rows": int(len(fetched.frame)),
                    "response_sha256": fetched.response_sha256,
                    "source": fetched.source,
                    "stored_path": str(path),
                }
            except Exception as exc:
                category = exc.category if isinstance(exc, ProviderResponseError) else "request_failure"
                manifest["requests"][spec["key"]] = {
                    "status": "failed",
                    "kind": spec["kind"],
                    "dataset": spec["dataset"],
                    "partitions": spec["partitions"],
                    "parameters": spec["parameters"],
                    "rows": 0,
                    "error_category": category,
                    "error": _bounded_error(exc),
                }
            _save_manifest(manifest_path, manifest)


def _load_completed_frames(
    manifest: dict[str, Any],
    store: DatasetStore,
    *,
    kinds: set[str],
) -> pd.DataFrame:
    frames = []
    for key in sorted(manifest["requests"]):
        row = manifest["requests"][key]
        if row.get("status") != "completed" or row.get("kind") not in kinds:
            continue
        frames.append(store.read_frame(str(row["dataset"]), dict(row["partitions"])))
    if frames:
        return pd.concat(frames, ignore_index=True)
    if kinds == {"eastmoney_nav"}:
        return pd.DataFrame(columns=["date", "asset_id", "symbol", "exchange", "nav", "nav_source"])
    return pd.DataFrame(
        columns=["date", "asset_id", "symbol", "exchange", "total_share", "share_source"]
    )


def _load_manifest(path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    scope = {
        "analysis_start": plan["analysis_start"],
        "analysis_end": plan["analysis_end"],
        "symbols": plan["symbols"],
        "analysis_sessions": plan["analysis_sessions"],
        "szse_windows": plan["szse_windows"],
    }
    if not path.exists():
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "scope": scope,
            "requests": {},
        }
        _save_manifest(path, manifest)
        return manifest
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"Unsupported public source manifest schema: {path}")
    if manifest.get("scope") != scope:
        raise ValueError(f"Public source manifest scope mismatch: {path}")
    if not isinstance(manifest.get("requests"), dict):
        raise ValueError(f"Public source manifest requests are invalid: {path}")
    return manifest


def _save_manifest(
    path: Path,
    manifest: dict[str, Any],
    *,
    max_attempts: int = 5,
    retry_delay_seconds: float = 0.1,
) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    for attempt in range(1, max_attempts + 1):
        try:
            atomic_write_json(path, manifest)
            return
        except PermissionError:
            if attempt == max_attempts:
                raise
            time.sleep(retry_delay_seconds)


def _completed_request_is_present(
    manifest: dict[str, Any],
    store: DatasetStore,
    key: str,
) -> bool:
    row = manifest["requests"].get(key, {})
    return bool(
        row.get("status") == "completed"
        and store.exists(str(row.get("dataset", "")), dict(row.get("partitions", {})))
    )


def _write_processed_years(store: DatasetStore, processed: pd.DataFrame) -> None:
    if processed.empty:
        return
    years = pd.to_datetime(processed["date"]).dt.year
    for year, frame in processed.groupby(years):
        store.write_frame(
            frame,
            "processed/etf_share_size",
            {"frequency": "1d", "market": "CN_ETF", "year": str(year)},
        )


def _quality_report(processed: pd.DataFrame, plan: dict[str, Any]) -> dict[str, Any]:
    if processed.empty:
        return {
            "rows": 0,
            "assets": 0,
            "sessions": 0,
            "start_date": None,
            "end_date": None,
            "analysis_sessions": len(plan["analysis_sessions"]),
            "duplicate_rows": 0,
            "positive_share_rows": 0,
            "positive_nav_rows": 0,
            "usable_scale_rows": 0,
            "usable_premium_discount_rows": 0,
        }
    dates = pd.to_datetime(processed["date"])
    return {
        "rows": int(len(processed)),
        "assets": int(processed["asset_id"].nunique()),
        "sessions": int(dates.nunique()),
        "start_date": dates.min().date().isoformat(),
        "end_date": dates.max().date().isoformat(),
        "analysis_sessions": len(plan["analysis_sessions"]),
        "duplicate_rows": int(processed.duplicated(["asset_id", "date"]).sum()),
        "positive_share_rows": int((pd.to_numeric(processed["total_share"], errors="coerce") > 0).sum()),
        "positive_nav_rows": int((pd.to_numeric(processed["nav"], errors="coerce") > 0).sum()),
        "usable_scale_rows": int(pd.to_numeric(processed["total_size"], errors="coerce").notna().sum()),
        "usable_premium_discount_rows": int(
            pd.to_numeric(processed["nav_premium_discount"], errors="coerce").notna().sum()
        ),
    }


def _require_columns(frame: pd.DataFrame, columns: list[str], context: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{context} is missing columns: {', '.join(missing)}")


def _bounded_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:500]
