from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from quant_robot.assets.etf_universe import (
    cn_etf_assets_from_tushare_fund_basic,
    filter_tushare_cn_etf_fund_basic,
)
from quant_robot.data.ingest.tushare_etf_share_size import run_tushare_etf_share_size_ingest
from quant_robot.data.ingest.tushare_fund_portfolio import run_tushare_fund_portfolio_basket_ingest
from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.storage.processed_bars import load_processed_bars
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "tushare_cn_etf_sync"


class TushareCnEtfSyncAdapter(Protocol):
    def fetch_fund_basic(self, market: str = "E", status: str = "L") -> pd.DataFrame:
        ...

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = "") -> pd.DataFrame:
        ...

    def fetch_fund_portfolio(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        ...


def run_tushare_cn_etf_sync(
    *,
    adapter: TushareCnEtfSyncAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    report_dir: str | Path,
    as_of: str | None = None,
    source: str = "tushare",
    resume: bool = True,
    execute: bool = True,
    min_rotation_history_rows: int = 20,
    min_rotation_median_amount: float = 0.0,
    max_rotation_zero_volume_ratio: float = 0.0,
    rotation_extreme_return_threshold: float = 0.5,
    include_etf_share_size: bool = True,
    etf_share_size_exchanges: tuple[str, ...] = ("SSE", "SZSE"),
    include_fund_portfolio_baskets: bool = True,
    date_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    report_path = Path(report_dir)
    as_of_date = _date_text(as_of or end_date)
    if not execute:
        pack = _pack(
            status="ready_to_execute",
            source=source,
            output_dir=output_path,
            report_dir=report_path,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of_date,
            blockers=[],
            date_resolution=date_resolution,
        )
        write_tushare_cn_etf_sync_pack(report_path, pack)
        return pack

    fund_basic = adapter.fetch_fund_basic(market="E", status="")
    universe = filter_tushare_cn_etf_fund_basic(fund_basic, as_of=as_of_date)
    assets = cn_etf_assets_from_tushare_fund_basic(fund_basic, as_of=as_of_date)
    _write_universe_datasets(output_path, fund_basic, universe, as_of_date)
    ingest = run_tushare_daily_ingest(adapter, start_date, end_date, output_path, resume=resume, market="CN_ETF")
    bars = load_processed_bars(output_path, "CN_ETF")
    etf_share_size = _run_etf_share_size_sync(
        adapter=adapter,
        start_date=start_date,
        end_date=end_date,
        output_path=output_path,
        resume=resume,
        include_etf_share_size=include_etf_share_size,
        exchanges=etf_share_size_exchanges,
    )
    fund_portfolio_baskets = _run_fund_portfolio_basket_sync(
        adapter=adapter,
        symbols=[str(value) for value in universe.get("symbol", pd.Series(dtype=str)).tolist()],
        start_date=start_date,
        end_date=end_date,
        output_path=output_path,
        resume=resume,
        include_fund_portfolio_baskets=include_fund_portfolio_baskets,
    )
    rotation_membership = build_cn_etf_rotation_membership(
        fund_basic,
        bars,
        min_history_rows=min_rotation_history_rows,
        min_median_amount=min_rotation_median_amount,
        max_zero_volume_ratio=max_rotation_zero_volume_ratio,
        extreme_return_threshold=rotation_extreme_return_threshold,
    )
    _write_rotation_membership_dataset(output_path, rotation_membership)
    rotation_pool = build_cn_etf_rotation_pool(
        universe,
        bars,
        min_history_rows=min_rotation_history_rows,
        min_median_amount=min_rotation_median_amount,
        max_zero_volume_ratio=max_rotation_zero_volume_ratio,
        extreme_return_threshold=rotation_extreme_return_threshold,
    )
    blockers = _blockers(universe, ingest, etf_share_size, fund_portfolio_baskets)
    pack = _pack(
        status="completed" if not blockers else "data_quality_blocked",
        source=source,
        output_dir=output_path,
        report_dir=report_path,
        start_date=start_date,
        end_date=end_date,
        as_of=as_of_date,
        fund_basic=fund_basic,
        universe=universe,
        assets=assets,
        ingest=ingest,
        etf_share_size=etf_share_size,
        fund_portfolio_baskets=fund_portfolio_baskets,
        rotation_membership=rotation_membership,
        blockers=blockers,
        rotation_pool=rotation_pool,
        include_etf_share_size=include_etf_share_size,
        include_fund_portfolio_baskets=include_fund_portfolio_baskets,
        date_resolution=date_resolution,
    )
    write_tushare_cn_etf_sync_pack(report_path, pack)
    return pack


def write_tushare_cn_etf_sync_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "tushare_cn_etf_sync_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_cn_etf_sync_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    universe = pack.get("universe", {}) if isinstance(pack.get("universe"), dict) else {}
    pd.DataFrame(
        {
            "symbol": universe.get("eligible_symbols", []),
            "asset_id": universe.get("eligible_asset_ids", []),
        }
    ).to_csv(output_path / "cn_etf_universe.csv", index=False)


def build_tushare_cn_etf_sync_readiness_blocked_pack(
    *,
    source: str,
    output_dir: str | Path,
    report_dir: str | Path,
    start_date: str,
    end_date: str,
    as_of: str,
    readiness: dict[str, Any],
    date_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = readiness.get("missing", []) if isinstance(readiness.get("missing", []), list) else []
    blockers = [str(item) for item in missing] or ["tushare_readiness_not_met"]
    pack = _pack(
        status="blocked_missing_readiness",
        source=source,
        output_dir=Path(output_dir),
        report_dir=Path(report_dir),
        start_date=start_date,
        end_date=end_date,
        as_of=str(as_of),
        blockers=blockers,
        date_resolution=date_resolution,
    )
    pack["readiness"] = _sanitize(readiness)
    pack["markdown"] = render_tushare_cn_etf_sync_markdown(pack)
    return pack


def build_tushare_cn_etf_sync_up_to_date_pack(
    *,
    source: str,
    output_dir: str | Path,
    report_dir: str | Path,
    start_date: str,
    end_date: str,
    as_of: str,
    date_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = _pack(
        status="up_to_date",
        source=source,
        output_dir=Path(output_dir),
        report_dir=Path(report_dir),
        start_date=start_date,
        end_date=end_date,
        as_of=str(as_of),
        blockers=[],
        ingest={
            "source": source,
            "market": "CN_ETF",
            "downloaded_trade_dates": [],
            "skipped_trade_dates": [],
            "processed_rows": 0,
            "status": "up_to_date",
        },
        etf_share_size={"source": source, "dataset": "etf_share_size", "status": "up_to_date", "processed_rows": 0},
        fund_portfolio_baskets={
            "source": source,
            "dataset": "fund_portfolio_baskets",
            "status": "up_to_date",
            "processed_rows": 0,
        },
        date_resolution=date_resolution,
    )
    pack["markdown"] = render_tushare_cn_etf_sync_markdown(pack)
    return pack


def render_tushare_cn_etf_sync_markdown(pack: dict[str, Any]) -> str:
    universe = pack.get("universe", {}) if isinstance(pack.get("universe"), dict) else {}
    ingest = pack.get("ingest", {}) if isinstance(pack.get("ingest"), dict) else {}
    rotation_membership = pack.get("rotation_membership", {})
    rotation_rows = rotation_membership.get("rows", 0) if isinstance(rotation_membership, dict) else 0
    rotation_member_rows = rotation_membership.get("member_rows", 0) if isinstance(rotation_membership, dict) else 0
    fund_portfolio_baskets = pack.get("fund_portfolio_baskets", {})
    fund_portfolio_rows = fund_portfolio_baskets.get("processed_rows", 0) if isinstance(fund_portfolio_baskets, dict) else 0
    date_resolution = pack.get("date_resolution", {}) if isinstance(pack.get("date_resolution"), dict) else {}
    start_resolution = date_resolution.get("start_date", {}) if isinstance(date_resolution.get("start_date"), dict) else {}
    end_resolution = date_resolution.get("end_date", {}) if isinstance(date_resolution.get("end_date"), dict) else {}
    lines = [
        "# Tushare CN ETF Sync",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Source: {pack.get('source', 'tushare')}",
        f"- Primary market: {pack.get('primary_market', 'CN_ETF')}",
        f"- Window: {pack.get('start_date')} to {pack.get('end_date')}",
        f"- Start-date resolution: {start_resolution.get('method', 'unknown')}",
        f"- End-date resolution: {end_resolution.get('method', 'unknown')}",
        f"- Universe as-of: {pack.get('as_of')}",
        f"- Eligible ETF symbols: {universe.get('eligible_count', 0)}",
        f"- Processed bar rows: {ingest.get('processed_rows', 0)}",
        f"- ETF share-size rows: {pack.get('etf_share_size', {}).get('processed_rows', 0) if isinstance(pack.get('etf_share_size'), dict) else 0}",
        f"- ETF moneyflow basket rows: {fund_portfolio_rows}",
        f"- Rotation membership rows: {rotation_rows}",
        f"- Rotation member rows: {rotation_member_rows}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = pack.get("blockers", []) if isinstance(pack.get("blockers"), list) else []
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    return "\n".join(lines) + "\n"


def _write_universe_datasets(
    output_dir: Path,
    fund_basic: pd.DataFrame,
    universe: pd.DataFrame,
    as_of: str,
) -> None:
    store = DatasetStore(output_dir)
    store.write_frame(fund_basic, "metadata/tushare_fund_basic", {"market": "E", "snapshot": as_of})
    store.write_frame(universe, "metadata/cn_etf_universe", {"as_of": as_of, "market": "CN_ETF"})


def _write_rotation_membership_dataset(output_dir: Path, membership: pd.DataFrame) -> None:
    if membership.empty:
        return
    DatasetStore(output_dir).write_frame(membership, "metadata/cn_etf_rotation_membership", {"market": "CN_ETF"})


def _pack(
    *,
    status: str,
    source: str,
    output_dir: Path,
    report_dir: Path,
    start_date: str,
    end_date: str,
    as_of: str,
    blockers: list[str],
    fund_basic: pd.DataFrame | None = None,
    universe: pd.DataFrame | None = None,
    assets: list[Any] | None = None,
    ingest: dict[str, Any] | None = None,
    etf_share_size: dict[str, Any] | None = None,
    fund_portfolio_baskets: dict[str, Any] | None = None,
    rotation_membership: pd.DataFrame | None = None,
    rotation_pool: dict[str, Any] | None = None,
    include_etf_share_size: bool = True,
    include_fund_portfolio_baskets: bool = True,
    date_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fund_basic = fund_basic if fund_basic is not None else pd.DataFrame()
    universe = universe if universe is not None else pd.DataFrame()
    rotation_membership = rotation_membership if rotation_membership is not None else pd.DataFrame()
    assets = assets or []
    pack = {
        "stage": STAGE,
        "status": status,
        "source": source,
        "primary_market": "CN_ETF",
        "primary_universe_source": "tushare_fund_basic",
        "primary_history_source": "tushare_fund_daily",
        "start_date": start_date,
        "end_date": end_date,
        "as_of": as_of,
        "date_resolution": date_resolution or {},
        "output_dir": str(output_dir),
        "report_dir": str(report_dir),
        "fund_basic": {
            "rows": int(len(fund_basic)),
            "source_market": "E",
            "status_requested": "all",
        },
        "universe": {
            "as_of": as_of,
            "eligible_count": int(len(universe)),
            "eligible_symbols": [str(value) for value in universe.get("symbol", pd.Series(dtype=str)).tolist()],
            "eligible_asset_ids": [asset.asset_id for asset in assets],
            "point_in_time_filter": "list_date <= as_of < delist_date",
        },
        "ingest": ingest or {},
        "etf_share_size": etf_share_size or {},
        "fund_portfolio_baskets": fund_portfolio_baskets or {},
        "rotation_membership": _rotation_membership_summary(rotation_membership),
        "rotation_pool": rotation_pool or {},
        "auxiliary_datasets": {
            "etf_share_size": "enabled" if include_etf_share_size else "disabled",
            "etf_moneyflow_baskets": "enabled" if include_fund_portfolio_baskets else "disabled",
            "cn_stock_moneyflow": "auxiliary_only",
        },
        "blockers": blockers,
        "lookahead_policy": {
            "fund_universe_as_of": as_of,
            "uses_list_and_delist_dates": True,
            "full_status_fund_basic_snapshot": True,
            "etf_share_size_known_on_trade_date": True,
            "fund_portfolio_known_date": "ann_date",
        },
        "survivorship_policy": {
            "historical_delisted_etfs": "preserved_when_listed_on_date",
            "current_tradable_pool": "excludes_as_of_delisted_etfs",
            "rotation_membership": "point_in_time_from_list_date_delist_date_and_trailing_quality",
        },
        "auxiliary_feature_policy": {
            "cn_stock_moneyflow": "auxiliary_only",
            "direct_cn_stock_selection": "forbidden",
        },
        "live_boundary_allowed": False,
        "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
    }
    pack["markdown"] = render_tushare_cn_etf_sync_markdown(pack)
    return _sanitize(pack)


def _run_etf_share_size_sync(
    *,
    adapter: TushareCnEtfSyncAdapter,
    start_date: str,
    end_date: str,
    output_path: Path,
    resume: bool,
    include_etf_share_size: bool,
    exchanges: tuple[str, ...],
) -> dict[str, Any]:
    if not include_etf_share_size:
        return {"source": "tushare", "dataset": "etf_share_size", "status": "disabled", "processed_rows": 0}
    try:
        result = run_tushare_etf_share_size_ingest(
            adapter,
            start_date,
            end_date,
            output_path,
            resume=resume,
            market="CN_ETF",
            exchanges=exchanges,
        )
    except Exception as exc:
        return {
            "source": "tushare",
            "dataset": "etf_share_size",
            "market": "CN_ETF",
            "status": "failed",
            "error": str(exc),
            "processed_rows": 0,
        }
    result["status"] = "completed"
    return result


def _run_fund_portfolio_basket_sync(
    *,
    adapter: TushareCnEtfSyncAdapter,
    symbols: list[str],
    start_date: str,
    end_date: str,
    output_path: Path,
    resume: bool,
    include_fund_portfolio_baskets: bool,
) -> dict[str, Any]:
    if not include_fund_portfolio_baskets:
        return {
            "source": "tushare",
            "dataset": "fund_portfolio_baskets",
            "status": "disabled",
            "processed_rows": 0,
        }
    try:
        result = run_tushare_fund_portfolio_basket_ingest(
            adapter,
            symbols,
            start_date,
            end_date,
            output_path,
            resume=resume,
            market="CN_ETF",
        )
    except Exception as exc:
        return {
            "source": "tushare",
            "dataset": "fund_portfolio_baskets",
            "market": "CN_ETF",
            "status": "failed",
            "error": str(exc),
            "processed_rows": 0,
        }
    result["status"] = "completed"
    return result


def build_cn_etf_rotation_pool(
    universe: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    min_history_rows: int = 20,
    min_median_amount: float = 0.0,
    max_zero_volume_ratio: float = 0.0,
    extreme_return_threshold: float = 0.5,
) -> dict[str, Any]:
    universe_symbols = [str(value).upper() for value in universe.get("symbol", pd.Series(dtype=str)).tolist()]
    rows = []
    excluded = []
    bar_frame = bars.copy()
    if "symbol" not in bar_frame.columns:
        bar_frame["symbol"] = bar_frame["asset_id"].map(_symbol_from_cn_etf_asset_id)
    bar_frame["symbol"] = bar_frame["symbol"].astype(str).str.upper()
    for symbol in sorted(universe_symbols):
        group = bar_frame[bar_frame["symbol"] == symbol].sort_values("date")
        metrics = _rotation_pool_metrics(group, extreme_return_threshold)
        reasons = _rotation_pool_reasons(
            metrics,
            min_history_rows=min_history_rows,
            min_median_amount=min_median_amount,
            max_zero_volume_ratio=max_zero_volume_ratio,
        )
        row = {"symbol": symbol, **metrics, "exclusion_reasons": reasons}
        if reasons:
            excluded.append(row)
        else:
            rows.append(row)
    return {
        "eligible_symbols": [row["symbol"] for row in rows],
        "eligible_count": len(rows),
        "excluded": excluded,
        "excluded_count": len(excluded),
        "thresholds": {
            "min_history_rows": int(min_history_rows),
            "min_median_amount": float(min_median_amount),
            "max_zero_volume_ratio": float(max_zero_volume_ratio),
            "extreme_return_threshold": float(extreme_return_threshold),
        },
    }


def build_cn_etf_rotation_membership(
    fund_basic: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    min_history_rows: int = 20,
    min_median_amount: float = 0.0,
    max_zero_volume_ratio: float = 0.0,
    extreme_return_threshold: float = 0.5,
) -> pd.DataFrame:
    output_columns = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "is_rotation_member",
        "exclusion_reasons",
        "history_rows_to_date",
        "median_amount_to_date",
        "zero_volume_ratio_to_date",
        "extreme_return_rows_to_date",
        "list_date",
        "delist_date",
    ]
    if bars.empty:
        return pd.DataFrame(columns=output_columns)
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    if "symbol" not in frame.columns:
        frame["symbol"] = frame["asset_id"].map(_symbol_from_cn_etf_asset_id)
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame["market"] = "CN_ETF"
    metadata = _rotation_fund_metadata(fund_basic)
    rows = []
    for symbol, group in frame.sort_values(["symbol", "date"]).groupby("symbol", sort=True):
        metrics = _membership_metrics(group, extreme_return_threshold)
        fund = metadata.get(symbol)
        for idx, row in group.reset_index(drop=True).iterrows():
            reasons = _membership_reasons(
                fund,
                row["date"],
                history_rows=int(metrics.loc[idx, "history_rows_to_date"]),
                median_amount=float(metrics.loc[idx, "median_amount_to_date"]),
                zero_volume_ratio=float(metrics.loc[idx, "zero_volume_ratio_to_date"]),
                extreme_return_rows=int(metrics.loc[idx, "extreme_return_rows_to_date"]),
                min_history_rows=min_history_rows,
                min_median_amount=min_median_amount,
                max_zero_volume_ratio=max_zero_volume_ratio,
            )
            rows.append(
                {
                    "date": row["date"],
                    "asset_id": row["asset_id"],
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "source": "tushare_fund_basic_fund_daily",
                    "is_rotation_member": not reasons,
                    "exclusion_reasons": ";".join(reasons),
                    "history_rows_to_date": int(metrics.loc[idx, "history_rows_to_date"]),
                    "median_amount_to_date": float(metrics.loc[idx, "median_amount_to_date"]),
                    "zero_volume_ratio_to_date": float(metrics.loc[idx, "zero_volume_ratio_to_date"]),
                    "extreme_return_rows_to_date": int(metrics.loc[idx, "extreme_return_rows_to_date"]),
                    "list_date": fund.get("list_date") if fund else pd.NaT,
                    "delist_date": fund.get("delist_date") if fund else pd.NaT,
                }
            )
    return pd.DataFrame(rows, columns=output_columns).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _rotation_fund_metadata(fund_basic: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if fund_basic.empty:
        return {}
    source = fund_basic.copy()
    source["symbol"] = source.get("symbol", pd.Series(dtype=str)).astype(str).str.upper()
    source["list_date"] = _optional_date_column(source, "list_date")
    source["delist_date"] = _optional_date_column(source, "delist_date")
    if "is_etf" not in source.columns:
        source["is_etf"] = _fund_text_contains(source, "ETF")
    if "is_exchange_traded" not in source.columns:
        source["is_exchange_traded"] = source.get("market", pd.Series(dtype=str)).astype(str).str.upper().eq("E")
    metadata: dict[str, dict[str, Any]] = {}
    for row in source.to_dict("records"):
        symbol = str(row.get("symbol", "")).upper()
        if symbol:
            metadata[symbol] = row
    return metadata


def _membership_metrics(group: pd.DataFrame, extreme_return_threshold: float) -> pd.DataFrame:
    source = group.sort_values("date").reset_index(drop=True)
    amount = pd.to_numeric(source.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    volume = pd.to_numeric(source.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    close = pd.to_numeric(source.get("close", pd.Series(dtype=float)), errors="coerce")
    history_rows = pd.Series(range(1, len(source) + 1), index=source.index)
    extreme_returns = (close.pct_change().abs() > abs(extreme_return_threshold)).fillna(False)
    return pd.DataFrame(
        {
            "history_rows_to_date": history_rows,
            "median_amount_to_date": amount.expanding().median(),
            "zero_volume_ratio_to_date": (volume <= 0.0).astype(int).cumsum() / history_rows,
            "extreme_return_rows_to_date": extreme_returns.astype(int).cumsum(),
        }
    )


def _membership_reasons(
    fund: dict[str, Any] | None,
    date: object,
    *,
    history_rows: int,
    median_amount: float,
    zero_volume_ratio: float,
    extreme_return_rows: int,
    min_history_rows: int,
    min_median_amount: float,
    max_zero_volume_ratio: float,
) -> list[str]:
    reasons = []
    if fund is None:
        reasons.append("no_fund_basic")
    else:
        if not bool(fund.get("is_exchange_traded")):
            reasons.append("not_exchange_traded")
        if not bool(fund.get("is_etf")):
            reasons.append("not_etf")
        if not _listed_on_membership_date(fund, date):
            reasons.append("not_listed_on_date")
    metrics = {
        "history_rows": history_rows,
        "median_amount": median_amount,
        "zero_volume_ratio": zero_volume_ratio,
        "extreme_return_rows": extreme_return_rows,
    }
    reasons.extend(
        _rotation_pool_reasons(
            metrics,
            min_history_rows=min_history_rows,
            min_median_amount=min_median_amount,
            max_zero_volume_ratio=max_zero_volume_ratio,
        )
    )
    return reasons


def _listed_on_membership_date(fund: dict[str, Any], date: object) -> bool:
    query_date = pd.to_datetime(date).date()
    list_date = _coerce_date(fund.get("list_date"))
    delist_date = _coerce_date(fund.get("delist_date"))
    return list_date is not None and list_date <= query_date and (delist_date is None or delist_date > query_date)


def _rotation_membership_summary(membership: pd.DataFrame) -> dict[str, Any]:
    if membership.empty:
        return {
            "rows": 0,
            "member_rows": 0,
            "assets": 0,
            "member_assets": 0,
            "start_date": None,
            "end_date": None,
            "dataset": "metadata/cn_etf_rotation_membership",
        }
    dates = pd.to_datetime(membership["date"])
    members = membership[membership["is_rotation_member"].astype(bool)]
    return {
        "rows": int(len(membership)),
        "member_rows": int(len(members)),
        "assets": int(membership["asset_id"].nunique()),
        "member_assets": int(members["asset_id"].nunique()) if not members.empty else 0,
        "start_date": dates.min().date().isoformat(),
        "end_date": dates.max().date().isoformat(),
        "dataset": "metadata/cn_etf_rotation_membership",
    }


def _blockers(
    universe: pd.DataFrame,
    ingest: dict[str, Any],
    etf_share_size: dict[str, Any] | None = None,
    fund_portfolio_baskets: dict[str, Any] | None = None,
) -> list[str]:
    blockers: list[str] = []
    if universe.empty:
        blockers.append("no_point_in_time_cn_etf_universe")
    if int(_number(ingest.get("processed_rows"), 0)) <= 0:
        blockers.append("no_processed_fund_daily_rows")
    report = ingest.get("quality_report", {}) if isinstance(ingest.get("quality_report"), dict) else {}
    if int(_number(report.get("duplicate_bars"), 0)) > 0:
        blockers.append("duplicate_bars")
    if int(_number(report.get("missing_date_rows"), 0)) > 0:
        blockers.append("missing_date_rows")
    share_size = etf_share_size or {}
    if share_size.get("status") == "failed":
        blockers.append("etf_share_size_sync_failed")
    elif share_size and int(_number(share_size.get("processed_rows"), 0)) <= 0:
        blockers.append("no_etf_share_size_rows")
    baskets = fund_portfolio_baskets or {}
    if baskets.get("status") == "failed":
        blockers.append("fund_portfolio_basket_sync_failed")
    return blockers


def _rotation_pool_metrics(group: pd.DataFrame, extreme_return_threshold: float) -> dict[str, Any]:
    if group.empty:
        return {
            "history_rows": 0,
            "median_amount": 0.0,
            "zero_volume_ratio": 1.0,
            "extreme_return_rows": 0,
        }
    volume = pd.to_numeric(group.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    amount = pd.to_numeric(group.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    close = pd.to_numeric(group.get("close", pd.Series(dtype=float)), errors="coerce")
    return {
        "history_rows": int(len(group)),
        "median_amount": float(amount.median()) if len(amount) else 0.0,
        "zero_volume_ratio": float((volume <= 0.0).sum() / len(group)) if len(group) else 1.0,
        "extreme_return_rows": int((close.pct_change().abs() > abs(extreme_return_threshold)).sum()),
    }


def _rotation_pool_reasons(
    metrics: dict[str, Any],
    *,
    min_history_rows: int,
    min_median_amount: float,
    max_zero_volume_ratio: float,
) -> list[str]:
    reasons = []
    if int(metrics.get("history_rows", 0)) < min_history_rows:
        reasons.append("insufficient_history_rows")
    if _number(metrics.get("median_amount"), 0.0) < min_median_amount:
        reasons.append("median_amount_below_threshold")
    if _number(metrics.get("zero_volume_ratio"), 1.0) > max_zero_volume_ratio:
        reasons.append("zero_volume_ratio_above_threshold")
    if int(metrics.get("extreme_return_rows", 0)) > 0:
        reasons.append("extreme_return_rows_present")
    return reasons


def _symbol_from_cn_etf_asset_id(asset_id: Any) -> str:
    parts = str(asset_id).split("_")
    if len(parts) >= 4 and parts[0] == "CN" and parts[1] == "ETF":
        suffix = "SH" if parts[2] == "XSHG" else "SZ" if parts[2] == "XSHE" else parts[2]
        return f"{parts[3]}.{suffix}"
    return str(asset_id)


def _optional_date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([pd.NaT] * len(frame), index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").map(lambda value: value.date() if pd.notna(value) else pd.NaT)


def _fund_text_contains(frame: pd.DataFrame, text: str) -> pd.Series:
    columns = [column for column in ["name", "fund_type", "invest_type", "type"] if column in frame.columns]
    if not columns:
        return pd.Series([False] * len(frame), index=frame.index)
    haystack = frame[columns].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
    return haystack.str.contains(text.upper(), regex=False)


def _coerce_date(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    return pd.to_datetime(value).date()


def _date_text(value: str) -> str:
    return pd.to_datetime(value).date().isoformat()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
