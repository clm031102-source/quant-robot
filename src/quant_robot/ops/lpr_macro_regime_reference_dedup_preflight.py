from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.lpr_macro_regime_pairwise_residual_ic_prescreen import (
    align_residual_ic_to_lpr_states,
    load_residual_ic_observations,
)
from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)


STAGE = "lpr_macro_regime_reference_dedup_preflight"
PAIRWISE_STAGE = "lpr_macro_regime_pairwise_residual_ic_prescreen"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
CANDIDATE_COLUMNS = [
    "cluster_id",
    "source_id",
    "factor_name",
    "base_factor_name",
    "horizon",
    "state",
    "cluster_representative",
    "factor_value_reference_dedup_allowed",
    "walk_forward_preflight_allowed",
    "mean_spearman_ic",
    "icir",
    "positive_ic_rate",
    "ic_observations",
    "max_abs_ic_curve_correlation_to_other_lead",
    "reference_redundancy_class",
    "exposure_class",
    "blockers",
    "requirements",
]
PAIRWISE_COLUMNS = [
    "left_source_id",
    "left_factor_name",
    "right_source_id",
    "right_factor_name",
    "state",
    "horizon",
    "overlap_observations",
    "ic_curve_correlation",
    "abs_ic_curve_correlation",
    "similarity_class",
]


def run_lpr_macro_regime_reference_dedup_preflight(
    *,
    processed_root: str | Path,
    pairwise_prescreen_path: str | Path,
    residual_ic_paths: Sequence[str | Path],
    output_dir: str | Path,
    reference_correlation_paths: Sequence[str | Path] = (),
    exposure_correlation_paths: Sequence[str | Path] = (),
    market: str = "CN",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    cluster_abs_ic_corr: float = 0.90,
    duplicate_abs_ic_corr: float = 0.98,
    min_pair_overlap: int = 20,
) -> dict[str, Any]:
    pairwise_report = json.loads(Path(pairwise_prescreen_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    residual_ic = load_residual_ic_observations(residual_ic_paths)
    result = summarize_lpr_macro_regime_reference_dedup_preflight(
        pairwise_report,
        residual_ic,
        state_frame,
        reference_correlations=_load_evidence_tables(reference_correlation_paths),
        exposure_correlations=_load_evidence_tables(exposure_correlation_paths),
        residual_ic_paths=residual_ic_paths,
        pairwise_prescreen_path=pairwise_prescreen_path,
        processed_root=processed_root,
        reference_correlation_paths=reference_correlation_paths,
        exposure_correlation_paths=exposure_correlation_paths,
        market=market,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        cluster_abs_ic_corr=cluster_abs_ic_corr,
        duplicate_abs_ic_corr=duplicate_abs_ic_corr,
        min_pair_overlap=min_pair_overlap,
    )
    write_lpr_macro_regime_reference_dedup_preflight(output_dir, result)
    return result


def summarize_lpr_macro_regime_reference_dedup_preflight(
    pairwise_report: dict[str, Any],
    residual_ic: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    residual_ic_paths: Sequence[str | Path],
    reference_correlations: pd.DataFrame | None = None,
    exposure_correlations: pd.DataFrame | None = None,
    pairwise_prescreen_path: str | Path | None = None,
    processed_root: str | Path | None = None,
    reference_correlation_paths: Sequence[str | Path] = (),
    exposure_correlation_paths: Sequence[str | Path] = (),
    market: str = "CN",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    cluster_abs_ic_corr: float = 0.90,
    duplicate_abs_ic_corr: float = 0.98,
    min_pair_overlap: int = 20,
) -> dict[str, Any]:
    global_blockers = _pairwise_report_blockers(pairwise_report)
    leads = _state_leads(pairwise_report)
    if not leads:
        global_blockers.append("no_lpr_pairwise_state_leads")

    aligned = _safe_align_residual_ic_to_lpr_states(residual_ic, state_frame)
    windowed = _analysis_window_from_pairwise_report(aligned, pairwise_report)
    ic_series = _lead_ic_series(windowed, leads)
    pairwise_correlations = _pairwise_ic_curve_correlations(
        leads,
        ic_series,
        min_pair_overlap=min_pair_overlap,
        duplicate_abs_ic_corr=duplicate_abs_ic_corr,
        cluster_abs_ic_corr=cluster_abs_ic_corr,
    )
    cluster_map = _cluster_leads(leads, pairwise_correlations, cluster_abs_ic_corr=cluster_abs_ic_corr)
    representatives = _cluster_representatives(leads, cluster_map)
    reference_frame = _normalise_evidence(reference_correlations, class_column="redundancy_class")
    exposure_frame = _normalise_evidence(exposure_correlations, class_column="exposure_class")
    candidate_results = _candidate_results(
        leads,
        cluster_map=cluster_map,
        representatives=representatives,
        pairwise_correlations=pairwise_correlations,
        reference_correlations=reference_frame,
        exposure_correlations=exposure_frame,
        global_blockers=global_blockers,
    )
    representative_count = sum(1 for row in candidate_results if row["cluster_representative"])
    factor_value_reference_dedup_allowed_count = sum(
        1 for row in candidate_results if row["factor_value_reference_dedup_allowed"]
    )
    walk_forward_allowed_count = sum(1 for row in candidate_results if row["walk_forward_preflight_allowed"])
    cluster_blocked_count = sum(
        1 for row in candidate_results if "cluster_duplicate_or_high_similarity_with_stronger_lpr_lead" in row["blockers"]
    )
    decision_blockers = _unique(global_blockers)
    if representative_count <= 0:
        decision_blockers.append("no_lpr_representative_candidate_for_factor_value_dedup")
    passes = bool(not global_blockers and representative_count > 0)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "pairwise_prescreen_path": str(Path(pairwise_prescreen_path)) if pairwise_prescreen_path is not None else None,
        "residual_ic_paths": [str(Path(path)) for path in residual_ic_paths],
        "reference_correlation_paths": [str(Path(path)) for path in reference_correlation_paths],
        "exposure_correlation_paths": [str(Path(path)) for path in exposure_correlation_paths],
        "summary": {
            "passes": passes,
            "state_lead_count": len(leads),
            "candidate_cluster_count": len(set(cluster_map.values())) if cluster_map else 0,
            "representative_candidate_count": representative_count,
            "cluster_blocked_candidate_count": cluster_blocked_count,
            "factor_value_reference_dedup_allowed_candidate_count": factor_value_reference_dedup_allowed_count,
            "walk_forward_preflight_allowed_candidate_count": walk_forward_allowed_count,
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": (
                "factor_value_reference_dedup_for_lpr_gap_widening_representatives"
                if passes
                else "repair_or_rotate_lpr_reference_dedup_preflight"
            ),
        },
        "feature_definitions": {
            "state_join_rule": "latest LPR state with available_date <= residual IC date",
            "ic_curve_clustering": "Pearson correlation of residual IC time series within the same LPR state",
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
        },
        "thresholds": {
            "cluster_abs_ic_corr": float(cluster_abs_ic_corr),
            "duplicate_abs_ic_corr": float(duplicate_abs_ic_corr),
            "min_pair_overlap": int(min_pair_overlap),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_use": "blocked_for_preflight_and_tuning",
        },
        "candidate_results": sorted(
            candidate_results,
            key=lambda row: (not row["cluster_representative"], row["cluster_id"], -row["mean_spearman_ic"], row["factor_name"]),
        ),
        "pairwise_ic_curve_correlations": pairwise_correlations,
        "decision": {
            "research_screen_allowed": passes,
            "factor_value_reference_dedup_allowed_next": passes,
            "walk_forward_preflight_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": _unique(decision_blockers),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "requires_factor_value_reference_dedup": True,
            "requires_walk_forward_after_dedup": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_final_holdout_read_once": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_reference_dedup_preflight_markdown(result)
    return result


def write_lpr_macro_regime_reference_dedup_preflight(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_reference_dedup_preflight.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_reference_dedup_preflight.md").write_text(
        render_lpr_macro_regime_reference_dedup_preflight_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "lpr_macro_regime_reference_dedup_candidates.csv", clean["candidate_results"], CANDIDATE_COLUMNS)
    _write_csv(
        output_path / "lpr_macro_regime_reference_dedup_pairwise_ic_correlations.csv",
        clean["pairwise_ic_curve_correlations"],
        PAIRWISE_COLUMNS,
    )


def render_lpr_macro_regime_reference_dedup_preflight_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# LPR Macro Regime Reference Dedup Preflight",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- State leads: {summary.get('state_lead_count', 0)}",
        f"- Candidate clusters: {summary.get('candidate_cluster_count', 0)}",
        f"- Representative candidates: {summary.get('representative_candidate_count', 0)}",
        f"- Cluster-blocked candidates: {summary.get('cluster_blocked_candidate_count', 0)}",
        f"- Factor-value reference dedup allowed: {summary.get('factor_value_reference_dedup_allowed_candidate_count', 0)}",
        f"- Walk-forward preflight allowed: {decision.get('walk_forward_preflight_allowed', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Decision Blockers",
        "",
    ]
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Candidate Routing",
            "",
            "| Cluster | Representative | Factor | State | IC | ICIR | Max IC-Corr | Ref | Exposure | Dedup Next | WF Now | Blockers | Requirements |",
            "|---:|---|---|---|---:|---:|---:|---|---|---|---|---|---|",
        ]
    )
    for row in result.get("candidate_results", []):
        lines.append(
            "| {cluster} | {rep} | {factor} | {state} | {ic:.4f} | {icir:.3f} | {corr:.3f} | {ref} | {exp} | {dedup} | {wf} | {blockers} | {reqs} |".format(
                cluster=row.get("cluster_id", ""),
                rep="yes" if row.get("cluster_representative", False) else "no",
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                ic=float(row.get("mean_spearman_ic", 0.0) or 0.0),
                icir=float(row.get("icir", 0.0) or 0.0),
                corr=float(row.get("max_abs_ic_curve_correlation_to_other_lead", 0.0) or 0.0),
                ref=row.get("reference_redundancy_class", ""),
                exp=row.get("exposure_class", ""),
                dedup="yes" if row.get("factor_value_reference_dedup_allowed", False) else "no",
                wf="yes" if row.get("walk_forward_preflight_allowed", False) else "no",
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
                reqs=", ".join(_as_list(row.get("requirements"))) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _pairwise_report_blockers(pairwise_report: dict[str, Any]) -> list[str]:
    decision = _dict(pairwise_report.get("decision"))
    blockers = []
    if pairwise_report.get("stage") != PAIRWISE_STAGE:
        blockers.append("pairwise_prescreen_stage_mismatch")
    if _dict(pairwise_report.get("summary")).get("passes") is not True:
        blockers.append("pairwise_prescreen_not_passing")
    if decision.get("reference_dedup_walk_forward_preflight_allowed_next") is not True:
        blockers.append("pairwise_prescreen_not_allowed_for_reference_dedup_preflight")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("pairwise_prescreen_policy_boundary_violation")
    if pairwise_report.get("live_boundary_allowed") is not False:
        blockers.append("pairwise_prescreen_live_boundary_violation")
    return blockers


def _state_leads(pairwise_report: dict[str, Any]) -> list[dict[str, Any]]:
    leads = []
    for row in pairwise_report.get("state_ic_results", []):
        if not isinstance(row, dict) or row.get("state_research_lead") is not True:
            continue
        lead = dict(row)
        lead["source_id"] = str(lead.get("source_id", ""))
        lead["factor_name"] = str(lead.get("factor_name", ""))
        lead["horizon"] = int(lead.get("horizon", 0))
        lead["state"] = str(lead.get("state", ""))
        lead["base_factor_name"] = _base_factor_name(lead["factor_name"])
        leads.append(lead)
    return leads


def _analysis_window_from_pairwise_report(frame: pd.DataFrame, pairwise_report: dict[str, Any]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    data_window = _dict(pairwise_report.get("data_window"))
    start = pd.Timestamp(data_window.get("analysis_start_date", "1900-01-01"))
    end = pd.Timestamp(data_window.get("analysis_end_date", "2099-12-31"))
    output = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()
    output = output[output["date"] < pd.Timestamp(FINAL_HOLDOUT_START)].copy()
    return output.reset_index(drop=True)


def _safe_align_residual_ic_to_lpr_states(residual_ic: pd.DataFrame, state_frame: pd.DataFrame) -> pd.DataFrame:
    required_residual_columns = {"source_id", "factor_name", "horizon", "date", "spearman_ic", "cross_section"}
    required_state_columns = {"available_date", STATE_COLUMN}
    if not required_residual_columns.issubset(set(residual_ic.columns)) or not required_state_columns.issubset(
        set(state_frame.columns)
    ):
        return pd.DataFrame(
            columns=[
                "source_id",
                "factor_name",
                "horizon",
                "date",
                "spearman_ic",
                "cross_section",
                "lpr_available_date",
                STATE_COLUMN,
            ]
        )
    return align_residual_ic_to_lpr_states(residual_ic, state_frame)


def _lead_ic_series(frame: pd.DataFrame, leads: Sequence[dict[str, Any]]) -> dict[tuple[str, str, int, str], pd.Series]:
    series = {}
    for lead in leads:
        key = _lead_key(lead)
        rows = frame[
            (frame["source_id"] == key[0])
            & (frame["factor_name"] == key[1])
            & (frame["horizon"] == key[2])
            & (frame[STATE_COLUMN] == key[3])
        ]
        series[key] = rows.set_index("date")["spearman_ic"].sort_index()
    return series


def _pairwise_ic_curve_correlations(
    leads: Sequence[dict[str, Any]],
    ic_series: dict[tuple[str, str, int, str], pd.Series],
    *,
    min_pair_overlap: int,
    duplicate_abs_ic_corr: float,
    cluster_abs_ic_corr: float,
) -> list[dict[str, Any]]:
    rows = []
    for left_index, left in enumerate(leads):
        for right in leads[left_index + 1 :]:
            left_key = _lead_key(left)
            right_key = _lead_key(right)
            joined = pd.concat([ic_series.get(left_key, pd.Series(dtype=float)), ic_series.get(right_key, pd.Series(dtype=float))], axis=1, join="inner").dropna()
            corr = _series_corr(joined)
            abs_corr = abs(corr) if corr is not None else None
            rows.append(
                {
                    "left_source_id": left_key[0],
                    "left_factor_name": left_key[1],
                    "right_source_id": right_key[0],
                    "right_factor_name": right_key[1],
                    "state": left_key[3] if left_key[3] == right_key[3] else f"{left_key[3]}|{right_key[3]}",
                    "horizon": left_key[2] if left_key[2] == right_key[2] else 0,
                    "overlap_observations": int(len(joined)),
                    "ic_curve_correlation": corr,
                    "abs_ic_curve_correlation": abs_corr,
                    "similarity_class": _similarity_class(
                        abs_corr,
                        overlap=len(joined),
                        min_pair_overlap=min_pair_overlap,
                        duplicate_abs_ic_corr=duplicate_abs_ic_corr,
                        cluster_abs_ic_corr=cluster_abs_ic_corr,
                    ),
                }
            )
    return rows


def _cluster_leads(
    leads: Sequence[dict[str, Any]],
    pairwise_correlations: Sequence[dict[str, Any]],
    *,
    cluster_abs_ic_corr: float,
) -> dict[tuple[str, str, int, str], int]:
    keys = [_lead_key(lead) for lead in leads]
    parent = {key: key for key in keys}

    def find(key: tuple[str, str, int, str]) -> tuple[str, str, int, str]:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: tuple[str, str, int, str], right: tuple[str, str, int, str]) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for row in pairwise_correlations:
        abs_corr = row.get("abs_ic_curve_correlation")
        if abs_corr is None or float(abs_corr) < float(cluster_abs_ic_corr):
            continue
        left = (row["left_source_id"], row["left_factor_name"], int(row["horizon"]), row["state"])
        right = (row["right_source_id"], row["right_factor_name"], int(row["horizon"]), row["state"])
        if left in parent and right in parent:
            union(left, right)

    roots = {}
    cluster_map = {}
    for key in keys:
        root = find(key)
        if root not in roots:
            roots[root] = len(roots) + 1
        cluster_map[key] = roots[root]
    return cluster_map


def _cluster_representatives(
    leads: Sequence[dict[str, Any]],
    cluster_map: dict[tuple[str, str, int, str], int],
) -> dict[int, tuple[str, str, int, str]]:
    by_cluster: dict[int, list[dict[str, Any]]] = {}
    for lead in leads:
        by_cluster.setdefault(cluster_map[_lead_key(lead)], []).append(lead)
    representatives = {}
    for cluster_id, rows in by_cluster.items():
        best = sorted(
            rows,
            key=lambda row: (
                -float(row.get("mean_spearman_ic", 0.0) or 0.0),
                -float(row.get("icir", 0.0) or 0.0),
                row.get("factor_name", ""),
            ),
        )[0]
        representatives[cluster_id] = _lead_key(best)
    return representatives


def _candidate_results(
    leads: Sequence[dict[str, Any]],
    *,
    cluster_map: dict[tuple[str, str, int, str], int],
    representatives: dict[int, tuple[str, str, int, str]],
    pairwise_correlations: Sequence[dict[str, Any]],
    reference_correlations: pd.DataFrame,
    exposure_correlations: pd.DataFrame,
    global_blockers: Sequence[str],
) -> list[dict[str, Any]]:
    rows = []
    for lead in leads:
        key = _lead_key(lead)
        cluster_id = cluster_map.get(key, 0)
        is_representative = representatives.get(cluster_id) == key
        blockers = list(global_blockers)
        requirements = ["requires_factor_value_reference_dedup_before_walk_forward"]
        if not is_representative:
            blockers.append("cluster_duplicate_or_high_similarity_with_stronger_lpr_lead")
        reference_class = _evidence_class(reference_correlations, lead, class_column="redundancy_class")
        exposure_class = _evidence_class(exposure_correlations, lead, class_column="exposure_class")
        if reference_class in {"moderately_redundant", "highly_redundant"}:
            requirements.append("source_reference_redundancy_requires_factor_value_dedup")
        if exposure_class in {"moderate_exposure", "high_exposure"}:
            requirements.append("source_exposure_requires_factor_value_reaudit")
        rows.append(
            {
                "cluster_id": int(cluster_id),
                "source_id": lead["source_id"],
                "factor_name": lead["factor_name"],
                "base_factor_name": lead["base_factor_name"],
                "horizon": int(lead["horizon"]),
                "state": lead["state"],
                "cluster_representative": bool(is_representative),
                "factor_value_reference_dedup_allowed": bool(is_representative and not global_blockers),
                "walk_forward_preflight_allowed": False,
                "mean_spearman_ic": float(lead.get("mean_spearman_ic", 0.0) or 0.0),
                "icir": float(lead.get("icir", 0.0) or 0.0),
                "positive_ic_rate": float(lead.get("positive_ic_rate", 0.0) or 0.0),
                "ic_observations": int(lead.get("ic_observations", 0) or 0),
                "max_abs_ic_curve_correlation_to_other_lead": _max_abs_corr_for_lead(pairwise_correlations, key),
                "reference_redundancy_class": reference_class,
                "exposure_class": exposure_class,
                "blockers": _unique(blockers),
                "requirements": _unique(requirements),
            }
        )
    return rows


def _load_evidence_tables(paths: Sequence[str | Path]) -> pd.DataFrame:
    frames = []
    for path_value in paths:
        path = Path(path_value)
        frame = _read_table(path)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["source_id"] = path.parent.name
        frame["source_path"] = str(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _normalise_evidence(frame: pd.DataFrame | None, *, class_column: str) -> pd.DataFrame:
    if frame is None or frame.empty or "lead_factor_name" not in frame or class_column not in frame:
        return pd.DataFrame(columns=["source_id", "lead_factor_name", class_column])
    output = frame.copy()
    if "source_id" not in output:
        output["source_id"] = ""
    output["source_id"] = output["source_id"].astype(str)
    output["lead_factor_name"] = output["lead_factor_name"].astype(str)
    output[class_column] = output[class_column].astype(str)
    if "mean_abs_correlation" in output:
        output["mean_abs_correlation"] = pd.to_numeric(output["mean_abs_correlation"], errors="coerce")
    else:
        output["mean_abs_correlation"] = pd.NA
    return output


def _evidence_class(frame: pd.DataFrame, lead: dict[str, Any], *, class_column: str) -> str:
    if frame.empty:
        return "missing"
    source_matches = frame["source_id"].isin(["", lead["source_id"]]) if "source_id" in frame else pd.Series(True, index=frame.index)
    matches = frame[source_matches & (frame["lead_factor_name"] == lead["base_factor_name"])]
    if matches.empty:
        return "missing"
    order = {
        "highly_redundant": 4,
        "high_exposure": 4,
        "moderately_redundant": 3,
        "moderate_exposure": 3,
        "unique": 2,
        "low_exposure": 2,
        "missing": 1,
    }
    values = sorted(
        {str(value) for value in matches[class_column].dropna()},
        key=lambda value: (-order.get(value, 0), value),
    )
    return values[0] if values else "missing"


def _base_factor_name(factor_name: str) -> str:
    suffixes = (
        "_industry_size_liquidity_vol_residual",
        "__style_residual",
    )
    for suffix in suffixes:
        if factor_name.endswith(suffix):
            return factor_name[: -len(suffix)]
    return factor_name


def _lead_key(lead: dict[str, Any]) -> tuple[str, str, int, str]:
    return (str(lead["source_id"]), str(lead["factor_name"]), int(lead["horizon"]), str(lead["state"]))


def _series_corr(frame: pd.DataFrame) -> float | None:
    if len(frame) < 2:
        return None
    corr = frame.iloc[:, 0].corr(frame.iloc[:, 1])
    if corr is None or pd.isna(corr) or not math.isfinite(float(corr)):
        return None
    return float(corr)


def _similarity_class(
    abs_corr: float | None,
    *,
    overlap: int,
    min_pair_overlap: int,
    duplicate_abs_ic_corr: float,
    cluster_abs_ic_corr: float,
) -> str:
    if overlap < int(min_pair_overlap) or abs_corr is None:
        return "insufficient_overlap"
    if float(abs_corr) >= float(duplicate_abs_ic_corr):
        return "duplicate_ic_curve"
    if float(abs_corr) >= float(cluster_abs_ic_corr):
        return "high_ic_curve_similarity"
    if float(abs_corr) >= 0.75:
        return "moderate_ic_curve_similarity"
    return "unique_ic_curve"


def _max_abs_corr_for_lead(pairwise_correlations: Sequence[dict[str, Any]], key: tuple[str, str, int, str]) -> float:
    values = []
    for row in pairwise_correlations:
        left = (row["left_source_id"], row["left_factor_name"], int(row["horizon"]), row["state"])
        right = (row["right_source_id"], row["right_factor_name"], int(row["horizon"]), row["state"])
        if key in {left, right} and row.get("abs_ic_curve_correlation") is not None:
            values.append(float(row["abs_ic_curve_correlation"]))
    return max(values) if values else 0.0


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.DataFrame()


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            for field in ("blockers", "requirements"):
                if isinstance(clean.get(field), list):
                    clean[field] = "|".join(str(item) for item in clean[field])
            writer.writerow(clean)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _unique(values: Iterable[Any]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            output.append(text)
            seen.add(text)
    return output
