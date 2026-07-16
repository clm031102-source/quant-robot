from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from quant_robot.data.etf_point_in_time_universe import (
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.research.dynamic_comovement_peer_source import (
    DynamicPeerPolicy,
    DynamicPeerSourceResult,
    build_dynamic_comovement_peer_source,
    validate_dynamic_peer_mapping,
)
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_dynamic_comovement_peer_readiness"
PRIMARY_MARKET = "CN_ETF"
REFERENCE_NAMES = (
    "market_beta_120",
    "residual_volatility_60",
    "momentum_60",
    "short_return_5",
    "log_adv20",
)
SAFETY = "Research-to-paper only. No broker connection, account read, order placement, or live trading."


@dataclass(frozen=True)
class DynamicPeerReadinessAudit:
    result: dict[str, Any]
    source: DynamicPeerSourceResult


def build_cn_etf_dynamic_comovement_peer_readiness(
    *,
    data_root: str | Path,
    analysis_start_date: str,
    analysis_end_date: str,
    metadata_root: str | Path | None = None,
    eligibility_policy: EtfEligibilityPolicy = EtfEligibilityPolicy(
        min_prior_observations=120,
        liquidity_window=20,
        min_trailing_median_amount=5_000_000.0,
        max_stale_rate=0.05,
        max_abs_return=0.20,
    ),
    peer_policy: DynamicPeerPolicy = DynamicPeerPolicy(),
    min_qualifying_assets_per_date: int = 30,
    min_qualifying_date_coverage: float = 0.80,
    min_comparable_assets_per_transition: int = 30,
    min_median_jaccard: float = 0.25,
    min_median_retention: float = 0.40,
    max_complete_churn_rate: float = 0.40,
    min_reciprocity_rate: float = 0.30,
    max_reference_edge_overlap: float = 0.50,
    min_reference_edge_coverage: float = 0.80,
) -> DynamicPeerReadinessAudit:
    start = pd.Timestamp(analysis_start_date).normalize()
    end = pd.Timestamp(analysis_end_date).normalize()
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if end >= pd.Timestamp("2026-01-01"):
        raise ValueError("dynamic peer readiness cannot read the sealed 2026 final holdout")
    root = Path(data_root)
    bars = load_processed_bars(root, PRIMARY_MARKET, end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
    official_root = (
        Path(metadata_root)
        if metadata_root is not None
        else root / "metadata" / "tushare_fund_basic"
    )
    lifecycle = load_official_etf_lifecycle(official_root)
    eligibility = build_point_in_time_etf_eligibility(
        bars,
        lifecycle,
        policy=eligibility_policy,
    )
    source = build_dynamic_comovement_peer_source(
        bars,
        eligibility,
        analysis_start_date=start,
        analysis_end_date=end,
        policy=peer_policy,
    )
    calendar = pd.DatetimeIndex(
        sorted(bars.loc[bars["date"].between(start, end), "date"].dropna().unique())
    )
    result = summarize_cn_etf_dynamic_comovement_peer_readiness(
        calendar_dates=calendar,
        source=source,
        daily_eligible_keys=eligibility.loc[
            eligibility["eligible"] & eligibility["date"].between(start, end),
            ["date", "asset_id"],
        ].drop_duplicates(),
        min_active_peers_per_asset=peer_policy.min_peers,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
        min_qualifying_date_coverage=min_qualifying_date_coverage,
        min_comparable_assets_per_transition=min_comparable_assets_per_transition,
        min_median_jaccard=min_median_jaccard,
        min_median_retention=min_median_retention,
        max_complete_churn_rate=max_complete_churn_rate,
        min_reciprocity_rate=min_reciprocity_rate,
        max_reference_edge_overlap=max_reference_edge_overlap,
        min_reference_edge_coverage=min_reference_edge_coverage,
    )
    window_bars = bars[bars["date"].between(start, end)]
    result["data_window"] = {
        "data_root": str(root),
        "metadata_root": str(official_root),
        "analysis_start_date": start.date().isoformat(),
        "analysis_end_date": end.date().isoformat(),
        "history_rows": int(len(window_bars)),
        "history_assets": int(window_bars["asset_id"].nunique()),
        "history_dates": int(window_bars["date"].nunique()),
        "lifecycle_assets": int(len(lifecycle)),
        "final_holdout_start": "2026-01-01",
        "final_holdout_included": False,
        "later_partitions_skipped_before_read": True,
    }
    result["eligibility_policy"] = asdict(eligibility_policy)
    result["peer_policy"] = _sanitize(asdict(peer_policy))
    result["source_boundaries"] = {
        "current_name_used": False,
        "official_2026_peer_mapping_used": False,
        "forward_returns_calculated": False,
        "factor_values_calculated": False,
    }
    return DynamicPeerReadinessAudit(result=_sanitize(result), source=source)


def summarize_cn_etf_dynamic_comovement_peer_readiness(
    *,
    calendar_dates: Iterable[str | pd.Timestamp],
    source: DynamicPeerSourceResult,
    daily_eligible_keys: pd.DataFrame | None = None,
    min_active_peers_per_asset: int = 3,
    min_qualifying_assets_per_date: int = 30,
    min_qualifying_date_coverage: float = 0.80,
    min_comparable_assets_per_transition: int = 30,
    min_median_jaccard: float = 0.25,
    min_median_retention: float = 0.40,
    max_complete_churn_rate: float = 0.40,
    min_reciprocity_rate: float = 0.30,
    max_reference_edge_overlap: float = 0.50,
    min_reference_edge_coverage: float = 0.80,
) -> dict[str, Any]:
    _validate_thresholds(
        min_active_peers_per_asset=min_active_peers_per_asset,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
        min_qualifying_date_coverage=min_qualifying_date_coverage,
        min_comparable_assets_per_transition=min_comparable_assets_per_transition,
        min_median_jaccard=min_median_jaccard,
        min_median_retention=min_median_retention,
        max_complete_churn_rate=max_complete_churn_rate,
        min_reciprocity_rate=min_reciprocity_rate,
        max_reference_edge_overlap=max_reference_edge_overlap,
        min_reference_edge_coverage=min_reference_edge_coverage,
    )
    blockers: list[str] = []
    integrity_error = None
    try:
        validate_dynamic_peer_mapping(source.mapping)
    except ValueError as exc:
        blockers.append("dynamic_peer_mapping_integrity_failed")
        integrity_error = str(exc)

    calendar = pd.DatetimeIndex(
        sorted(pd.to_datetime(list(calendar_dates), errors="coerce").dropna().unique())
    )
    coverage = _coverage_by_date(
        calendar,
        source.mapping,
        daily_eligible_keys=daily_eligible_keys,
        min_active_peers_per_asset=min_active_peers_per_asset,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
    )
    qualifying_dates = int(coverage["date_gate_passed"].sum()) if not coverage.empty else 0
    qualifying_date_coverage = _safe_ratio(qualifying_dates, len(calendar))
    if qualifying_date_coverage < min_qualifying_date_coverage:
        blockers.append("dynamic_peer_date_coverage_below_minimum")

    snapshots = source.snapshots.copy()
    if not snapshots.empty:
        snapshots["valid_from"] = pd.to_datetime(snapshots["valid_from"], errors="coerce")
        snapshots = snapshots.sort_values("valid_from").reset_index(drop=True)
    ready_snapshot_positions = snapshots.index[
        pd.to_numeric(snapshots.get("mapped_assets"), errors="coerce")
        .fillna(0)
        .ge(min_qualifying_assets_per_date)
    ].tolist() if not snapshots.empty else []
    if not ready_snapshot_positions:
        blockers.append("no_qualifying_dynamic_peer_snapshots")
        governed_snapshots = snapshots.iloc[0:0]
    else:
        first_ready = ready_snapshot_positions[0]
        governed_snapshots = snapshots.iloc[first_ready:].copy()
        if pd.to_numeric(governed_snapshots["mapped_assets"], errors="coerce").lt(
            min_qualifying_assets_per_date
        ).any():
            blockers.append("dynamic_peer_snapshot_asset_count_below_minimum")
        if pd.to_numeric(governed_snapshots["reciprocity_rate"], errors="coerce").lt(
            min_reciprocity_rate
        ).any():
            blockers.append("dynamic_peer_reciprocity_below_minimum")

    stability = source.stability.copy()
    if not stability.empty:
        for column in ("previous_valid_from", "valid_from"):
            stability[column] = pd.to_datetime(stability[column], errors="coerce")
    expected_transitions = []
    evaluated_stability_rows = []
    governed_dates = governed_snapshots["valid_from"].tolist() if not governed_snapshots.empty else []
    for previous_date, valid_date in zip(governed_dates, governed_dates[1:]):
        expected_transitions.append((pd.Timestamp(previous_date), pd.Timestamp(valid_date)))
        matched = stability[
            stability["previous_valid_from"].eq(previous_date)
            & stability["valid_from"].eq(valid_date)
        ] if not stability.empty else pd.DataFrame()
        if matched.empty:
            blockers.append("dynamic_peer_stability_evidence_missing")
            continue
        row = matched.iloc[0]
        evaluated_stability_rows.append(row.to_dict())
        if int(row["comparable_assets"]) < min_comparable_assets_per_transition:
            blockers.append("dynamic_peer_stability_comparison_below_minimum")
        if float(row["median_jaccard"]) < min_median_jaccard:
            blockers.append("dynamic_peer_jaccard_below_minimum")
        if float(row["median_retention"]) < min_median_retention:
            blockers.append("dynamic_peer_retention_below_minimum")
        if float(row["complete_churn_rate"]) > max_complete_churn_rate:
            blockers.append("dynamic_peer_complete_churn_above_maximum")
    if governed_dates and len(governed_dates) > 1 and not expected_transitions:
        blockers.append("dynamic_peer_stability_evidence_missing")

    duplicate = source.duplicate_overlap.copy()
    if not duplicate.empty:
        duplicate["valid_from"] = pd.to_datetime(duplicate["valid_from"], errors="coerce")
    for valid_date in governed_dates:
        rows = duplicate[duplicate["valid_from"].eq(valid_date)] if not duplicate.empty else pd.DataFrame()
        observed_names = set(rows["reference_name"].astype(str)) if not rows.empty else set()
        if observed_names != set(REFERENCE_NAMES):
            blockers.append("dynamic_peer_reference_evidence_missing")
        if not rows.empty and pd.to_numeric(rows["edge_evidence_coverage"], errors="coerce").lt(
            min_reference_edge_coverage
        ).any():
            blockers.append("dynamic_peer_reference_evidence_below_minimum")
        if not rows.empty and pd.to_numeric(rows["edge_overlap"], errors="coerce").ge(
            max_reference_edge_overlap
        ).any():
            blockers.append("dynamic_peer_reference_overlap_above_maximum")

    blockers = _dedupe(blockers)
    ready = not blockers
    mapping_dates = pd.to_datetime(source.mapping.get("valid_from"), errors="coerce") if not source.mapping.empty else pd.Series(dtype="datetime64[ns]")
    governed_duplicate = (
        duplicate[duplicate["valid_from"].isin(governed_dates)].copy()
        if not duplicate.empty
        else duplicate
    )
    duplicate_summary = _duplicate_summary(governed_duplicate)
    stability_summary = _stability_summary(pd.DataFrame(evaluated_stability_rows))
    result = {
        "stage": STAGE,
        "status": "ready_for_peer_source_preregistration" if ready else "blocked",
        "primary_market": PRIMARY_MARKET,
        "research_family": "cn_etf_dynamic_comovement_peer_dislocation",
        "mapping_integrity": {
            "passed": integrity_error is None,
            "error": integrity_error,
            "source_dates_strictly_lagged": integrity_error is None,
        },
        "mapping": {
            "rows": int(len(source.mapping)),
            "assets": int(source.mapping["asset_id"].nunique()) if not source.mapping.empty else 0,
            "peer_assets": int(source.mapping["peer_asset_id"].nunique()) if not source.mapping.empty else 0,
            "snapshots": int(mapping_dates.nunique()),
            "earliest_valid_from": _date_min(source.mapping, "valid_from"),
            "latest_valid_from": _date_max(source.mapping, "valid_from"),
        },
        "coverage": {
            "analysis_dates": int(len(calendar)),
            "qualifying_dates": qualifying_dates,
            "qualifying_date_coverage": qualifying_date_coverage,
            "daily_eligibility_intersection_used": daily_eligible_keys is not None,
            "min_mapped_assets": int(coverage["mapped_assets"].min()) if not coverage.empty else 0,
            "median_mapped_assets": float(coverage["mapped_assets"].median()) if not coverage.empty else 0.0,
            "max_mapped_assets": int(coverage["mapped_assets"].max()) if not coverage.empty else 0,
        },
        "stability": stability_summary,
        "duplicate_overlap": duplicate_summary,
        "thresholds": {
            "min_active_peers_per_asset": int(min_active_peers_per_asset),
            "min_qualifying_assets_per_date": int(min_qualifying_assets_per_date),
            "min_qualifying_date_coverage": float(min_qualifying_date_coverage),
            "min_comparable_assets_per_transition": int(min_comparable_assets_per_transition),
            "min_median_jaccard": float(min_median_jaccard),
            "min_median_retention": float(min_median_retention),
            "max_complete_churn_rate": float(max_complete_churn_rate),
            "min_reciprocity_rate": float(min_reciprocity_rate),
            "max_reference_edge_overlap": float(max_reference_edge_overlap),
            "min_reference_edge_coverage": float(min_reference_edge_coverage),
            "required_reference_names": list(REFERENCE_NAMES),
        },
        "gate": {
            "cleared": ready,
            "blockers": blockers,
        },
        "peer_source_preregistration_allowed": ready,
        "factor_generation_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "paper_signal_allowed": False,
        "promotion_allowed": False,
        "live_boundary_allowed": False,
        "next_direction": (
            "preregister_one_dynamic_peer_dislocation_prescreen"
            if ready
            else "rotate_to_non_price_cn_etf_source_inventory"
        ),
        "coverage_by_date": _records(coverage),
        "safety": SAFETY,
    }
    return _sanitize(result)


def write_cn_etf_dynamic_comovement_peer_readiness(
    output_dir: str | Path,
    *,
    result: Mapping[str, Any],
    source: DynamicPeerSourceResult,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_dynamic_comovement_peer_readiness.json",
        "markdown": output / "cn_etf_dynamic_comovement_peer_readiness.md",
        "mapping_csv": output / "dynamic_peer_mapping.csv",
        "snapshots_csv": output / "snapshot_summary.csv",
        "coverage_csv": output / "coverage_by_date.csv",
        "stability_csv": output / "stability_by_transition.csv",
        "duplicate_csv": output / "duplicate_overlap.csv",
    }
    sanitized = _sanitize(result)
    paths["json"].write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        render_cn_etf_dynamic_comovement_peer_readiness_markdown(sanitized),
        encoding="utf-8",
    )
    source.mapping.to_csv(paths["mapping_csv"], index=False)
    source.snapshots.to_csv(paths["snapshots_csv"], index=False)
    pd.DataFrame(sanitized.get("coverage_by_date", [])).to_csv(
        paths["coverage_csv"],
        index=False,
    )
    source.stability.to_csv(paths["stability_csv"], index=False)
    source.duplicate_overlap.to_csv(paths["duplicate_csv"], index=False)
    return paths


def render_cn_etf_dynamic_comovement_peer_readiness_markdown(
    result: Mapping[str, Any],
) -> str:
    gate = result.get("gate", {})
    coverage = result.get("coverage", {})
    stability = result.get("stability", {})
    duplicate = result.get("duplicate_overlap", {})
    blockers = gate.get("blockers", []) if isinstance(gate, Mapping) else []
    lines = [
        "# CN ETF Dynamic Co-Movement Peer Readiness",
        "",
        f"- Status: {result.get('status', 'blocked')}",
        f"- Mapping rows: {result.get('mapping', {}).get('rows', 0)}",
        f"- Mapping assets: {result.get('mapping', {}).get('assets', 0)}",
        f"- Qualifying dates: {coverage.get('qualifying_dates', 0)} / {coverage.get('analysis_dates', 0)}",
        f"- Qualifying-date coverage: {coverage.get('qualifying_date_coverage', 0.0):.4f}",
        f"- Stability transitions: {stability.get('transitions', 0)}",
        f"- Minimum median Jaccard: {stability.get('min_median_jaccard', 0.0):.4f}",
        f"- Maximum reference edge overlap: {duplicate.get('max_edge_overlap', 0.0):.4f}",
        f"- Peer-source preregistration allowed: {str(result.get('peer_source_preregistration_allowed', False)).lower()}",
        f"- Factor generation allowed: {str(result.get('factor_generation_allowed', False)).lower()}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Next direction: {result.get('next_direction')}",
            "- This audit uses no forward returns and authorizes no factor, portfolio, walk-forward, paper, or live action.",
        ]
    )
    return "\n".join(lines) + "\n"


def _coverage_by_date(
    calendar: pd.DatetimeIndex,
    mapping: pd.DataFrame,
    *,
    daily_eligible_keys: pd.DataFrame | None,
    min_active_peers_per_asset: int,
    min_qualifying_assets_per_date: int,
) -> pd.DataFrame:
    rows = []
    if mapping.empty:
        parsed = mapping
    else:
        parsed = mapping.copy()
        parsed["valid_from"] = pd.to_datetime(parsed["valid_from"], errors="coerce")
        parsed["valid_to"] = pd.to_datetime(parsed["valid_to"], errors="coerce")
    eligible_by_date: dict[pd.Timestamp, set[str]] | None = None
    if daily_eligible_keys is not None:
        required = {"date", "asset_id"}
        missing = sorted(required.difference(daily_eligible_keys.columns))
        if missing:
            raise ValueError("daily eligible keys are missing columns: " + ", ".join(missing))
        daily = daily_eligible_keys[["date", "asset_id"]].copy()
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
        daily["asset_id"] = daily["asset_id"].fillna("").astype(str).str.strip()
        daily = daily[daily["date"].notna() & daily["asset_id"].ne("")].drop_duplicates()
        eligible_by_date = {
            pd.Timestamp(signal_date): set(group["asset_id"])
            for signal_date, group in daily.groupby("date", sort=False)
        }
    for signal_date in calendar:
        active = (
            parsed[
                parsed["valid_from"].le(signal_date)
                & parsed["valid_to"].ge(signal_date)
            ]
            if not parsed.empty
            else parsed
        )
        active_mapping_assets = int(active["asset_id"].nunique()) if not active.empty else 0
        if active.empty or eligible_by_date is None:
            mapped_assets = active_mapping_assets
        else:
            eligible_assets = eligible_by_date.get(pd.Timestamp(signal_date), set())
            usable_edges = active[
                active["asset_id"].astype(str).isin(eligible_assets)
                & active["peer_asset_id"].astype(str).isin(eligible_assets)
            ]
            peer_counts = usable_edges.groupby("asset_id")["peer_asset_id"].nunique()
            mapped_assets = int(peer_counts.ge(min_active_peers_per_asset).sum())
        rows.append(
            {
                "date": pd.Timestamp(signal_date),
                "active_mapping_assets": active_mapping_assets,
                "mapped_assets": mapped_assets,
                "date_gate_passed": bool(mapped_assets >= min_qualifying_assets_per_date),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["date", "active_mapping_assets", "mapped_assets", "date_gate_passed"],
    )


def _duplicate_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "references": 0,
            "min_edge_evidence_coverage": 0.0,
            "max_edge_overlap": 0.0,
            "by_reference": [],
        }
    rows = []
    for reference_name, group in frame.groupby("reference_name", sort=True):
        rows.append(
            {
                "reference_name": str(reference_name),
                "snapshots": int(group["valid_from"].nunique()),
                "min_edge_evidence_coverage": float(
                    pd.to_numeric(group["edge_evidence_coverage"], errors="coerce").min()
                ),
                "max_edge_overlap": float(
                    pd.to_numeric(group["edge_overlap"], errors="coerce").max()
                ),
            }
        )
    return {
        "rows": int(len(frame)),
        "references": int(frame["reference_name"].nunique()),
        "min_edge_evidence_coverage": float(
            pd.to_numeric(frame["edge_evidence_coverage"], errors="coerce").min()
        ),
        "max_edge_overlap": float(
            pd.to_numeric(frame["edge_overlap"], errors="coerce").max()
        ),
        "by_reference": rows,
    }


def _stability_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "transitions": 0,
            "min_comparable_assets": 0,
            "min_median_jaccard": 0.0,
            "min_median_retention": 0.0,
            "max_complete_churn_rate": 0.0,
        }
    return {
        "transitions": int(len(frame)),
        "min_comparable_assets": int(pd.to_numeric(frame["comparable_assets"]).min()),
        "min_median_jaccard": float(pd.to_numeric(frame["median_jaccard"]).min()),
        "min_median_retention": float(pd.to_numeric(frame["median_retention"]).min()),
        "max_complete_churn_rate": float(pd.to_numeric(frame["complete_churn_rate"]).max()),
    }


def _validate_thresholds(**thresholds: int | float) -> None:
    positive_integer_names = (
        "min_active_peers_per_asset",
        "min_qualifying_assets_per_date",
        "min_comparable_assets_per_transition",
    )
    for name in positive_integer_names:
        if int(thresholds[name]) < 1:
            raise ValueError(f"{name} must be positive")
    for name, value in thresholds.items():
        if name in positive_integer_names:
            continue
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    values = pd.to_datetime(frame[column], errors="coerce").dropna() if column in frame else pd.Series(dtype="datetime64[ns]")
    return None if values.empty else values.min().date().isoformat()


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    values = pd.to_datetime(frame[column], errors="coerce").dropna() if column in frame else pd.Series(dtype="datetime64[ns]")
    return None if values.empty else values.max().date().isoformat()


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_sanitize(row) for row in frame.to_dict(orient="records")]


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if not denominator else float(numerator) / float(denominator)


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).date().isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        try:
            return _sanitize(value.item())
        except (TypeError, ValueError):
            return value
    return value
