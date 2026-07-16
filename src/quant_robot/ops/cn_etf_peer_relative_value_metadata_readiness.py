from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from quant_robot.storage.cn_etf_theme_map import build_cn_etf_theme_map
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_peer_relative_value_metadata_readiness"
PRIMARY_MARKET = "CN_ETF"
REQUIRED_PEER_MAPPING_COLUMNS = (
    "asset_id",
    "peer_id",
    "valid_from",
    "known_from",
    "mapping_method",
    "source",
)
APPROVED_MAPPING_METHODS = {
    "official_index_code",
    "official_benchmark_code",
    "official_benchmark_text",
    "audited_provider_taxonomy",
    "manual_verified_official",
}
PROHIBITED_NAME_ONLY_METHODS = {
    "name_keyword",
    "name_only",
    "fund_name_regex",
    "current_name_theme",
}
OFFICIAL_FUND_BASIC_PEER_COLUMNS = {
    "benchmark",
    "benchmark_code",
    "index_code",
    "tracked_index",
    "tracking_index",
}


def build_cn_etf_peer_relative_value_metadata_readiness(
    *,
    data_root: str | Path,
    analysis_start_date: str,
    analysis_end_date: str,
    peer_mapping_path: str | Path | None = None,
    min_peer_group_size: int = 2,
    min_qualifying_assets_per_date: int = 30,
    min_qualifying_date_coverage: float = 0.80,
) -> dict[str, Any]:
    root = Path(data_root)
    bars = _load_bars(root, analysis_start_date, analysis_end_date)
    fund_basic, snapshot_dates = _load_fund_basic_snapshots(root)
    mapping_root = Path(peer_mapping_path) if peer_mapping_path is not None else root / "metadata/cn_etf_peer_mapping"
    peer_mapping = _read_tabular_tree(mapping_root)
    try:
        share_size = load_etf_share_size_inputs(root, PRIMARY_MARKET)
    except FileNotFoundError:
        share_size = pd.DataFrame()
    return summarize_cn_etf_peer_relative_value_metadata_readiness(
        bars=bars,
        fund_basic=fund_basic,
        fund_basic_snapshot_dates=snapshot_dates,
        peer_mapping=peer_mapping,
        share_size=share_size,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_peer_group_size=min_peer_group_size,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
        min_qualifying_date_coverage=min_qualifying_date_coverage,
        data_root=str(root),
        peer_mapping_path=str(mapping_root),
    )


def summarize_cn_etf_peer_relative_value_metadata_readiness(
    *,
    bars: pd.DataFrame,
    fund_basic: pd.DataFrame,
    fund_basic_snapshot_dates: Iterable[str],
    peer_mapping: pd.DataFrame,
    share_size: pd.DataFrame,
    analysis_start_date: str,
    analysis_end_date: str,
    min_peer_group_size: int = 2,
    min_qualifying_assets_per_date: int = 30,
    min_qualifying_date_coverage: float = 0.80,
    data_root: str | None = None,
    peer_mapping_path: str | None = None,
) -> dict[str, Any]:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if int(min_peer_group_size) < 2:
        raise ValueError("min_peer_group_size must be at least 2")
    if int(min_qualifying_assets_per_date) < int(min_peer_group_size):
        raise ValueError("min_qualifying_assets_per_date must be at least min_peer_group_size")
    if not 0.0 <= float(min_qualifying_date_coverage) <= 1.0:
        raise ValueError("min_qualifying_date_coverage must be between 0 and 1")

    blockers: list[str] = []
    warnings: list[str] = []
    prepared_bars = _prepare_bars(bars, start, end, blockers)
    fund_basic_profile, heuristic_profile = _profile_fund_basic(
        fund_basic,
        fund_basic_snapshot_dates,
        prepared_bars,
        analysis_end=end,
    )

    if peer_mapping.empty:
        blockers.extend(
            [
                "missing_dedicated_peer_mapping",
                "historical_peer_membership_unavailable",
            ]
        )
        if not fund_basic_profile["official_peer_columns_present"]:
            blockers.append("official_peer_identifier_missing")
        if fund_basic_profile["only_snapshots_after_analysis_window"]:
            blockers.append("fund_basic_snapshot_after_analysis_window")

    peer_profile, coverage_rows, peer_group_rows = _profile_peer_mapping(
        prepared_bars,
        peer_mapping,
        analysis_start=start,
        analysis_end=end,
        min_peer_group_size=int(min_peer_group_size),
        min_qualifying_assets_per_date=int(min_qualifying_assets_per_date),
        min_qualifying_date_coverage=float(min_qualifying_date_coverage),
        blockers=blockers,
    )
    share_size_profile = _profile_share_size(share_size, start, end)

    blockers = _dedupe(blockers)
    metadata_gate_cleared = not blockers
    capability_gaps = []
    if not share_size_profile["historical_nav_available"]:
        capability_gaps.append("historical_nav_missing")
    if not share_size_profile["historical_share_available"]:
        capability_gaps.append("historical_share_size_missing")
    if not fund_basic_profile["rows"]:
        warnings.append("fund_basic_unavailable_for_descriptive_cross_check")
    elif fund_basic_profile["only_snapshots_after_analysis_window"] and not peer_mapping.empty:
        warnings.append("post_window_fund_basic_snapshot_excluded_from_peer_gate")

    bar_profile = _profile_bars(prepared_bars)
    peer_price_ready = metadata_gate_cleared and bar_profile["close_available"]
    status = "ready_for_preregistration" if metadata_gate_cleared else "blocked"
    result = {
        "stage": STAGE,
        "status": status,
        "primary_market": PRIMARY_MARKET,
        "research_family": "cn_etf_peer_relative_value",
        "analysis_window": {
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "final_holdout_included": False,
        },
        "data_root": data_root,
        "peer_mapping_path": peer_mapping_path,
        "thresholds": {
            "min_peer_group_size": int(min_peer_group_size),
            "min_qualifying_assets_per_date": int(min_qualifying_assets_per_date),
            "min_qualifying_date_coverage": float(min_qualifying_date_coverage),
            "approved_mapping_methods": sorted(APPROVED_MAPPING_METHODS),
        },
        "bars": bar_profile,
        "fund_basic": fund_basic_profile,
        "heuristic_name_theme_map": heuristic_profile,
        "peer_mapping": peer_profile,
        "share_size_nav": share_size_profile,
        "feature_channels": {
            "peer_price_dislocation": {
                "data_ready": peer_price_ready,
                "requires": ["point_in_time_peer_mapping", "close"],
            },
            "price_nav_relative_value": {
                "data_ready": peer_price_ready and share_size_profile["historical_nav_available"],
                "requires": ["point_in_time_peer_mapping", "historical_nav"],
            },
            "share_flow_relative_value": {
                "data_ready": peer_price_ready and share_size_profile["historical_share_available"],
                "requires": ["point_in_time_peer_mapping", "historical_share"],
            },
        },
        "capability_gaps": capability_gaps,
        "gate": {
            "metadata_gate_cleared": metadata_gate_cleared,
            "blockers": blockers,
            "warnings": _dedupe(warnings),
        },
        "prescreen_preregistration_allowed": metadata_gate_cleared,
        "prescreen_execution_allowed": False,
        "promotion_policy": {
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "paper_signal_allowed": False,
            "promotion_allowed": False,
            "reason": "This stage audits metadata only; a frozen prescreen preregistration is still required.",
        },
        "next_direction": (
            "preregister_one_compact_peer_relative_value_prescreen"
            if metadata_gate_cleared
            else "acquire_point_in_time_official_peer_mapping_before_factor_generation"
        ),
        "coverage_by_date": coverage_rows,
        "peer_groups_by_date": peer_group_rows,
        "live_boundary_allowed": False,
        "safety": "Research-to-paper only. No broker connection, account read, order placement, or live trading.",
    }
    return _sanitize(result)


def write_cn_etf_peer_relative_value_metadata_readiness(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    paths = {
        "json": output_path / "cn_etf_peer_relative_value_metadata_readiness.json",
        "markdown": output_path / "cn_etf_peer_relative_value_metadata_readiness.md",
        "coverage_csv": output_path / "coverage_by_date.csv",
        "peer_groups_csv": output_path / "peer_groups_by_date.csv",
    }
    paths["json"].write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
    paths["markdown"].write_text(
        render_cn_etf_peer_relative_value_metadata_readiness_markdown(sanitized),
        encoding="utf-8",
    )
    _write_csv(paths["coverage_csv"], sanitized.get("coverage_by_date", []))
    _write_csv(paths["peer_groups_csv"], sanitized.get("peer_groups_by_date", []))
    return paths


def render_cn_etf_peer_relative_value_metadata_readiness_markdown(result: Mapping[str, Any]) -> str:
    gate = result.get("gate", {})
    mapping = result.get("peer_mapping", {})
    fund_basic = result.get("fund_basic", {})
    heuristic = result.get("heuristic_name_theme_map", {})
    share_size = result.get("share_size_nav", {})
    blockers = gate.get("blockers", []) if isinstance(gate, Mapping) else []
    gaps = result.get("capability_gaps", [])
    lines = [
        "# CN ETF Peer Relative-Value Metadata Readiness",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'blocked')}",
        f"- Analysis window: {result.get('analysis_window', {}).get('start')} to {result.get('analysis_window', {}).get('end')}",
        f"- Eligible bar rows: {result.get('bars', {}).get('rows', 0)}",
        f"- Eligible ETF assets: {result.get('bars', {}).get('assets', 0)}",
        f"- Dedicated mapping rows: {mapping.get('rows', 0)}",
        f"- Qualifying asset-date coverage: {mapping.get('eligible_asset_date_coverage', 0.0):.4f}",
        f"- Qualifying date coverage: {mapping.get('qualifying_date_coverage', 0.0):.4f}",
        f"- Fund-basic snapshots: {fund_basic.get('snapshot_count', 0)}",
        f"- Latest fund-basic snapshot: {fund_basic.get('latest_snapshot')}",
        f"- Heuristic theme-map asset coverage: {heuristic.get('bar_asset_coverage', 0.0):.4f}",
        f"- Heuristic theme-map accepted: {str(heuristic.get('accepted_for_gate', False)).lower()}",
        f"- Historical NAV available: {str(share_size.get('historical_nav_available', False)).lower()}",
        f"- Historical share available: {str(share_size.get('historical_share_available', False)).lower()}",
        f"- Prescreen preregistration allowed: {str(result.get('prescreen_preregistration_allowed', False)).lower()}",
        f"- Prescreen execution allowed: {str(result.get('prescreen_execution_allowed', False)).lower()}",
        "",
        "## Gate Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Capability Gaps", ""])
    lines.extend(f"- {item}" for item in gaps) if gaps else lines.append("- none")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Next direction: {result.get('next_direction')}",
            "- Current-name keyword themes are descriptive only and cannot satisfy the historical peer-mapping gate.",
            "- No factor generation, portfolio grid, walk-forward, paper signal, or live action is authorized by this audit.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_bars(root: Path, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        return load_processed_bars(
            root,
            PRIMARY_MARKET,
            start_date=start_date,
            end_date=end_date,
        )
    except FileNotFoundError:
        return pd.DataFrame()


def _load_fund_basic_snapshots(root: Path) -> tuple[pd.DataFrame, list[str]]:
    base = root / "metadata/tushare_fund_basic/market=E"
    snapshots = sorted(
        path.name.split("=", 1)[1]
        for path in base.glob("snapshot=*")
        if path.is_dir() and "=" in path.name
    )
    frames = []
    store = DatasetStore(root)
    for snapshot in snapshots:
        try:
            frame = store.read_frame(
                "metadata/tushare_fund_basic",
                {"market": "E", "snapshot": snapshot},
            )
        except FileNotFoundError:
            continue
        frame = frame.copy()
        frame["snapshot_date"] = snapshot
        frames.append(frame)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), snapshots)


def _read_tabular_tree(root: Path) -> pd.DataFrame:
    if not root.exists():
        return pd.DataFrame()
    frames = []
    for path in sorted(root.rglob("*.parquet")):
        frames.append(pd.read_parquet(path))
    for path in sorted(root.rglob("*.csv")):
        frames.append(pd.read_csv(path))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _prepare_bars(
    bars: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    blockers: list[str],
) -> pd.DataFrame:
    required = {"asset_id", "date"}
    if bars.empty:
        blockers.append("missing_cn_etf_bar_history")
        return pd.DataFrame(columns=list(bars.columns))
    missing = sorted(required.difference(bars.columns))
    if missing:
        blockers.append("bar_history_required_columns_missing")
        return pd.DataFrame(columns=list(bars.columns))
    output = bars.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output = output[output["date"].between(start, end)].copy()
    output["asset_id"] = output["asset_id"].fillna("").astype(str).str.strip()
    output = output[output["date"].notna() & output["asset_id"].ne("")]
    duplicate_rows = int(output.duplicated(["asset_id", "date"]).sum())
    if duplicate_rows:
        blockers.append("duplicate_bar_asset_dates")
    output = output.drop_duplicates(["asset_id", "date"], keep="first")
    if output.empty:
        blockers.append("no_cn_etf_bar_rows_in_analysis_window")
    close_values = (
        pd.to_numeric(output["close"], errors="coerce")
        if "close" in output.columns
        else pd.Series(dtype="float64")
    )
    if not bool(close_values.notna().any()):
        blockers.append("historical_close_unavailable")
    return output.sort_values(["date", "asset_id"]).reset_index(drop=True)


def _profile_bars(bars: pd.DataFrame) -> dict[str, Any]:
    dates = pd.to_datetime(bars["date"], errors="coerce").dropna() if "date" in bars else pd.Series(dtype="datetime64[ns]")
    close_values = (
        pd.to_numeric(bars["close"], errors="coerce")
        if "close" in bars.columns
        else pd.Series(dtype="float64")
    )
    return {
        "rows": int(len(bars)),
        "assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "dates": int(dates.nunique()),
        "start_date": None if dates.empty else dates.min().date().isoformat(),
        "end_date": None if dates.empty else dates.max().date().isoformat(),
        "close_column_present": "close" in bars.columns,
        "close_non_null_rows": int(close_values.notna().sum()),
        "close_available": bool(close_values.notna().any()),
    }


def _profile_fund_basic(
    fund_basic: pd.DataFrame,
    snapshot_dates: Iterable[str],
    bars: pd.DataFrame,
    *,
    analysis_end: pd.Timestamp,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed_snapshots = sorted(
        {
            pd.Timestamp(value).date().isoformat()
            for value in snapshot_dates
            if pd.notna(pd.to_datetime(value, errors="coerce"))
        }
    )
    usable_snapshots = [value for value in parsed_snapshots if pd.Timestamp(value) <= analysis_end]
    official_columns = sorted(OFFICIAL_FUND_BASIC_PEER_COLUMNS.intersection(fund_basic.columns))
    profile = {
        "rows": int(len(fund_basic)),
        "unique_symbols": int(fund_basic["symbol"].nunique()) if "symbol" in fund_basic else 0,
        "columns": sorted(str(column) for column in fund_basic.columns),
        "snapshot_count": int(len(parsed_snapshots)),
        "earliest_snapshot": parsed_snapshots[0] if parsed_snapshots else None,
        "latest_snapshot": parsed_snapshots[-1] if parsed_snapshots else None,
        "snapshots_on_or_before_analysis_end": int(len(usable_snapshots)),
        "only_snapshots_after_analysis_window": bool(parsed_snapshots and not usable_snapshots),
        "official_peer_columns_present": official_columns,
    }
    heuristic = _profile_heuristic_theme_map(fund_basic, bars, parsed_snapshots)
    return profile, heuristic


def _profile_heuristic_theme_map(
    fund_basic: pd.DataFrame,
    bars: pd.DataFrame,
    snapshot_dates: list[str],
) -> dict[str, Any]:
    latest = fund_basic
    if not fund_basic.empty and "snapshot_date" in fund_basic:
        dates = pd.to_datetime(fund_basic["snapshot_date"], errors="coerce")
        latest_date = dates.max()
        latest = fund_basic.loc[dates.eq(latest_date)].copy()
    try:
        theme_map = build_cn_etf_theme_map(
            latest,
            source=f"tushare_fund_basic:{snapshot_dates[-1]}" if snapshot_dates else "tushare_fund_basic",
        )
    except (TypeError, ValueError):
        theme_map = pd.DataFrame()
    bar_assets = set(bars["asset_id"].astype(str)) if "asset_id" in bars else set()
    mapped_assets = set(theme_map["asset_id"].astype(str)) if "asset_id" in theme_map else set()
    groups = theme_map.groupby("theme").size() if "theme" in theme_map else pd.Series(dtype="int64")
    return {
        "rows": int(len(theme_map)),
        "themes": int(len(groups)),
        "bar_assets_mapped": int(len(bar_assets.intersection(mapped_assets))),
        "bar_asset_coverage": _safe_ratio(len(bar_assets.intersection(mapped_assets)), len(bar_assets)),
        "min_group_assets": int(groups.min()) if not groups.empty else 0,
        "median_group_assets": float(groups.median()) if not groups.empty else 0.0,
        "max_group_assets": int(groups.max()) if not groups.empty else 0,
        "other_equity_assets": int((theme_map.get("theme") == "other_equity").sum()) if not theme_map.empty else 0,
        "mapping_method": "current_name_keyword",
        "point_in_time_taxonomy": False,
        "accepted_for_gate": False,
    }


def _profile_peer_mapping(
    bars: pd.DataFrame,
    peer_mapping: pd.DataFrame,
    *,
    analysis_start: pd.Timestamp,
    analysis_end: pd.Timestamp,
    min_peer_group_size: int,
    min_qualifying_assets_per_date: int,
    min_qualifying_date_coverage: float,
    blockers: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    empty_profile = {
        "rows": int(len(peer_mapping)),
        "assets": 0,
        "peer_ids": 0,
        "mapping_methods": [],
        "eligible_asset_dates": int(len(bars)),
        "qualifying_asset_dates": 0,
        "eligible_asset_date_coverage": 0.0,
        "qualifying_dates": 0,
        "eligible_dates": int(bars["date"].nunique()) if "date" in bars else 0,
        "qualifying_date_coverage": 0.0,
        "qualifying_peer_groups": 0,
        "ambiguous_asset_dates": 0,
    }
    if peer_mapping.empty:
        return empty_profile, [], []
    missing = [column for column in REQUIRED_PEER_MAPPING_COLUMNS if column not in peer_mapping]
    if missing:
        blockers.append("peer_mapping_required_columns_missing")
        empty_profile["missing_columns"] = missing
        return empty_profile, [], []

    mapping = peer_mapping.copy()
    if "valid_to" not in mapping:
        mapping["valid_to"] = pd.NaT
    for column in ("valid_from", "valid_to", "known_from"):
        mapping[column] = pd.to_datetime(mapping[column], errors="coerce")
    for column in ("asset_id", "peer_id", "mapping_method", "source"):
        mapping[column] = mapping[column].fillna("").astype(str).str.strip()
    required_value_missing = (
        mapping[["asset_id", "peer_id", "mapping_method", "source"]].eq("").any(axis=1)
        | mapping["valid_from"].isna()
        | mapping["known_from"].isna()
    )
    if required_value_missing.any():
        blockers.append("peer_mapping_required_values_missing")
    methods = sorted(mapping["mapping_method"].dropna().unique().tolist())
    if mapping["mapping_method"].isin(PROHIBITED_NAME_ONLY_METHODS).any():
        blockers.append("prohibited_name_only_peer_mapping")
    if not mapping["mapping_method"].isin(APPROVED_MAPPING_METHODS).all():
        blockers.append("unapproved_peer_mapping_method")
    if mapping["source"].eq("").any():
        blockers.append("peer_mapping_source_missing")

    mapping["available_from"] = mapping[["valid_from", "known_from"]].max(axis=1)
    keys = bars[["asset_id", "date"]].drop_duplicates().copy() if not bars.empty else pd.DataFrame(columns=["asset_id", "date"])
    active = keys.merge(mapping, on="asset_id", how="inner")
    active = active[
        active["date"].between(analysis_start, analysis_end)
        & active["available_from"].notna()
        & active["date"].ge(active["available_from"])
        & (active["valid_to"].isna() | active["date"].le(active["valid_to"]))
    ].copy()
    assignment_counts = active.groupby(["asset_id", "date"])["peer_id"].nunique()
    ambiguous_keys = assignment_counts[assignment_counts.gt(1)].reset_index()[["asset_id", "date"]]
    ambiguous_asset_dates = int(len(ambiguous_keys))
    if ambiguous_asset_dates:
        blockers.append("overlapping_active_peer_assignments")
        active = active.merge(ambiguous_keys.assign(_ambiguous=True), on=["asset_id", "date"], how="left")
        active = active[active["_ambiguous"].isna()].drop(columns="_ambiguous")
    active = active.drop_duplicates(["asset_id", "date", "peer_id"])

    group_counts = (
        active.groupby(["date", "peer_id"], as_index=False)["asset_id"]
        .nunique()
        .rename(columns={"asset_id": "group_assets"})
    )
    qualifying_groups = group_counts[group_counts["group_assets"].ge(min_peer_group_size)].copy()
    qualifying = active.merge(
        qualifying_groups[["date", "peer_id"]],
        on=["date", "peer_id"],
        how="inner",
    )
    qualifying_keys = qualifying[["asset_id", "date"]].drop_duplicates()
    coverage = _safe_ratio(len(qualifying_keys), len(keys))
    if qualifying_groups.empty:
        blockers.append("no_qualifying_peer_groups")

    coverage_by_date = _coverage_by_date(
        keys,
        qualifying_keys,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
    )
    qualifying_dates = sum(1 for row in coverage_by_date if row["date_gate_passed"])
    eligible_dates = len(coverage_by_date)
    qualifying_date_coverage = _safe_ratio(qualifying_dates, eligible_dates)
    if qualifying_date_coverage < min_qualifying_date_coverage:
        blockers.append("peer_mapping_date_coverage_below_minimum")
    peer_groups_by_date = _peer_groups_by_date(qualifying_groups)
    profile = {
        "rows": int(len(mapping)),
        "assets": int(mapping["asset_id"].nunique()),
        "peer_ids": int(mapping["peer_id"].nunique()),
        "mapping_methods": methods,
        "approved_methods_only": bool(mapping["mapping_method"].isin(APPROVED_MAPPING_METHODS).all()),
        "eligible_asset_dates": int(len(keys)),
        "qualifying_asset_dates": int(len(qualifying_keys)),
        "eligible_asset_date_coverage": coverage,
        "qualifying_dates": int(qualifying_dates),
        "eligible_dates": int(eligible_dates),
        "qualifying_date_coverage": qualifying_date_coverage,
        "qualifying_peer_groups": int(len(qualifying_groups)),
        "ambiguous_asset_dates": ambiguous_asset_dates,
        "earliest_known_from": _date_min(mapping, "known_from"),
        "latest_known_from": _date_max(mapping, "known_from"),
    }
    return profile, coverage_by_date, peer_groups_by_date


def _coverage_by_date(
    keys: pd.DataFrame,
    qualifying_keys: pd.DataFrame,
    *,
    min_qualifying_assets_per_date: int,
) -> list[dict[str, Any]]:
    if keys.empty:
        return []
    eligible = keys.groupby("date").size().rename("eligible_asset_dates")
    qualifying = qualifying_keys.groupby("date").size().rename("qualifying_asset_dates")
    frame = pd.concat([eligible, qualifying], axis=1).fillna(0).reset_index()
    return [
        {
            "date": pd.Timestamp(row.date).date().isoformat(),
            "eligible_asset_dates": int(row.eligible_asset_dates),
            "qualifying_asset_dates": int(row.qualifying_asset_dates),
            "coverage": _safe_ratio(row.qualifying_asset_dates, row.eligible_asset_dates),
            "date_gate_passed": bool(row.qualifying_asset_dates >= min_qualifying_assets_per_date),
        }
        for row in frame.itertuples(index=False)
    ]


def _peer_groups_by_date(groups: pd.DataFrame) -> list[dict[str, Any]]:
    if groups.empty:
        return []
    rows = []
    for date, frame in groups.groupby("date", sort=True):
        rows.append(
            {
                "date": pd.Timestamp(date).date().isoformat(),
                "qualifying_groups": int(len(frame)),
                "min_group_assets": int(frame["group_assets"].min()),
                "median_group_assets": float(frame["group_assets"].median()),
                "max_group_assets": int(frame["group_assets"].max()),
            }
        )
    return rows


def _profile_share_size(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    nav_columns = sorted(set(frame.columns).intersection({"nav", "unit_nav", "adj_nav", "accum_nav", "total_nav"}))
    share_columns = sorted(set(frame.columns).intersection({"total_share", "share", "fund_share"}))
    dates = pd.to_datetime(frame["date"], errors="coerce") if "date" in frame else pd.Series(dtype="datetime64[ns]")
    in_window = dates.between(start, end) if not dates.empty else pd.Series(False, index=frame.index)
    window_rows = int(in_window.sum())
    return {
        "rows": int(len(frame)),
        "rows_in_analysis_window": window_rows,
        "assets_in_analysis_window": int(frame.loc[in_window, "asset_id"].nunique()) if window_rows and "asset_id" in frame else 0,
        "nav_columns": nav_columns,
        "share_columns": share_columns,
        "historical_nav_available": bool(window_rows and nav_columns),
        "historical_share_available": bool(window_rows and share_columns),
        "start_date": None if dates.dropna().empty else dates.min().date().isoformat(),
        "end_date": None if dates.dropna().empty else dates.max().date().isoformat(),
    }


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    values = pd.to_datetime(frame[column], errors="coerce").dropna() if column in frame else pd.Series(dtype="datetime64[ns]")
    return None if values.empty else values.min().date().isoformat()


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    values = pd.to_datetime(frame[column], errors="coerce").dropna() if column in frame else pd.Series(dtype="datetime64[ns]")
    return None if values.empty else values.max().date().isoformat()


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0].keys()))
        writer.writeheader()
        writer.writerows(materialized)


def _safe_ratio(numerator: float | int, denominator: float | int) -> float:
    return 0.0 if not denominator else float(numerator) / float(denominator)


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        try:
            return _sanitize(value.item())
        except (TypeError, ValueError):
            return value
    return value
