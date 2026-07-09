from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)


STAGE = "lpr_macro_regime_pairwise_residual_ic_prescreen"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
STATE_IC_COLUMNS = [
    "source_id",
    "factor_name",
    "horizon",
    "state",
    "state_type",
    "ic_observations",
    "mean_spearman_ic",
    "ic_std",
    "icir",
    "ic_t_stat",
    "p_value",
    "bonferroni_significant",
    "fdr_significant",
    "positive_ic_rate",
    "median_cross_section",
    "first_date",
    "last_date",
    "state_research_lead",
    "portfolio_grid_allowed",
    "promotion_allowed",
    "blockers",
]
CANDIDATE_COLUMNS = [
    "source_id",
    "factor_name",
    "horizon",
    "state_test_count",
    "state_research_lead_count",
    "best_state",
    "best_state_mean_ic",
    "best_state_icir",
    "best_state_t_stat",
    "portfolio_grid_allowed",
    "promotion_allowed",
    "blockers",
]


def run_lpr_macro_regime_pairwise_residual_ic_prescreen(
    *,
    processed_root: str | Path,
    state_prescreen_path: str | Path,
    residual_ic_paths: Sequence[str | Path],
    output_dir: str | Path,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_state_ic_observations: int = 20,
    min_mean_ic: float = 0.02,
    min_icir: float = 0.20,
    min_positive_ic_rate: float = 0.55,
    alpha: float = 0.05,
    include_final_holdout: bool = False,
) -> dict[str, Any]:
    state_prescreen = json.loads(Path(state_prescreen_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    residual_ic = load_residual_ic_observations(residual_ic_paths)
    result = summarize_lpr_macro_regime_pairwise_residual_ic_prescreen(
        residual_ic,
        state_frame,
        state_prescreen=state_prescreen,
        residual_ic_paths=[str(Path(path)) for path in residual_ic_paths],
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_state_ic_observations=min_state_ic_observations,
        min_mean_ic=min_mean_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        alpha=alpha,
        include_final_holdout=include_final_holdout,
        processed_root=processed_root,
        state_prescreen_path=state_prescreen_path,
        market=market,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
    )
    write_lpr_macro_regime_pairwise_residual_ic_prescreen(output_dir, result)
    return result


def load_residual_ic_observations(paths: Sequence[str | Path]) -> pd.DataFrame:
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
    if not frames:
        return _empty_residual_ic_frame()
    return pd.concat(frames, ignore_index=True)


def align_residual_ic_to_lpr_states(residual_ic: pd.DataFrame, state_frame: pd.DataFrame) -> pd.DataFrame:
    observations = _normalise_residual_ic(residual_ic).sort_values("date").reset_index(drop=True)
    states = _normalise_state_frame(state_frame).sort_values("available_date").reset_index(drop=True)
    if observations.empty or states.empty:
        return observations.assign(lpr_available_date=pd.NaT, lpr_shibor_gap_state=pd.NA)
    aligned = pd.merge_asof(
        observations,
        states,
        left_on="date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=True,
    )
    return aligned.rename(columns={"available_date": "lpr_available_date"})


def summarize_lpr_macro_regime_pairwise_residual_ic_prescreen(
    residual_ic: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    state_prescreen: dict[str, Any],
    residual_ic_paths: Sequence[str | Path],
    analysis_start_date: str,
    analysis_end_date: str,
    min_state_ic_observations: int = 20,
    min_mean_ic: float = 0.02,
    min_icir: float = 0.20,
    min_positive_ic_rate: float = 0.55,
    alpha: float = 0.05,
    include_final_holdout: bool = False,
    processed_root: str | Path | None = None,
    state_prescreen_path: str | Path | None = None,
    market: str = "CN",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
) -> dict[str, Any]:
    global_blockers = _state_prescreen_blockers(state_prescreen)
    aligned = align_residual_ic_to_lpr_states(residual_ic, state_frame)
    windowed, excluded_final_holdout_rows = _analysis_window(
        aligned,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    if include_final_holdout:
        global_blockers.append("final_holdout_included_in_pairwise_prescreen")
    if windowed.empty:
        global_blockers.append("no_residual_ic_observations_after_window")

    pairing_audit = _pairing_audit(windowed)
    if pairing_audit["available_date_after_signal_date_violations"] > 0:
        global_blockers.append("lpr_available_date_after_ic_signal_date")

    state_ic_results = _state_ic_results(
        windowed.dropna(subset=[STATE_COLUMN]),
        min_state_ic_observations=min_state_ic_observations,
        min_mean_ic=min_mean_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
    )
    _apply_multiple_testing(state_ic_results, alpha=alpha)
    _apply_state_lead_flags(
        state_ic_results,
        min_state_ic_observations=min_state_ic_observations,
        min_mean_ic=min_mean_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        global_blockers=global_blockers,
    )
    candidate_results = _candidate_results(state_ic_results, global_blockers=global_blockers)
    state_research_lead_count = sum(1 for row in state_ic_results if row["state_research_lead"])
    candidate_research_lead_count = sum(1 for row in candidate_results if row["state_research_lead_count"] > 0)
    paired_ic_rows = int(windowed[STATE_COLUMN].notna().sum()) if STATE_COLUMN in windowed else 0
    decision_blockers = _unique([*global_blockers])
    if state_research_lead_count <= 0:
        decision_blockers.append("no_lpr_regime_state_residual_ic_leads")
    passes = bool(not global_blockers and state_research_lead_count > 0)
    next_direction = (
        "lpr_regime_state_reference_dedup_walk_forward_preflight"
        if passes
        else "rotate_or_repair_lpr_regime_pairing_after_zero_state_leads"
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "state_prescreen_path": str(Path(state_prescreen_path)) if state_prescreen_path is not None else None,
        "residual_ic_paths": [str(Path(path)) for path in residual_ic_paths],
        "summary": {
            "passes": passes,
            "residual_ic_file_count": len(residual_ic_paths),
            "residual_ic_rows": int(len(residual_ic)),
            "analysis_window_ic_rows": int(len(windowed)),
            "paired_ic_rows": paired_ic_rows,
            "residual_factor_count": int(windowed["factor_name"].nunique()) if "factor_name" in windowed else 0,
            "state_test_count": len(state_ic_results),
            "state_research_lead_count": int(state_research_lead_count),
            "candidate_research_lead_count": int(candidate_research_lead_count),
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": next_direction,
        },
        "data_window": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "first_ic_date": _min_date(windowed, "date"),
            "last_ic_date": _max_date(windowed, "date"),
            "first_lpr_available_date": _min_date(windowed, "lpr_available_date"),
            "last_lpr_available_date": _max_date(windowed, "lpr_available_date"),
            "excluded_final_holdout_rows": int(excluded_final_holdout_rows),
        },
        "feature_definitions": {
            "state_source": "lpr_shibor_credit_gap_regime_60 from external_macro_rates",
            "state_join_rule": "latest LPR state with available_date <= residual IC date",
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
        },
        "thresholds": {
            "alpha": float(alpha),
            "min_state_ic_observations": int(min_state_ic_observations),
            "min_mean_ic": float(min_mean_ic),
            "min_icir": float(min_icir),
            "min_positive_ic_rate": float(min_positive_ic_rate),
        },
        "multiple_testing_policy": {
            "method": "Bonferroni and Benjamini-Hochberg FDR across residual factor x horizon x LPR state tests",
            "test_count": len(state_ic_results),
            "alpha": float(alpha),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_included": include_final_holdout,
            "excluded_final_holdout_rows": int(excluded_final_holdout_rows),
            "final_holdout_use": "blocked_for_pairwise_prescreen_and_tuning",
        },
        "pairing_audit": pairing_audit,
        "state_ic_results": sorted(
            state_ic_results,
            key=lambda row: (not row["state_research_lead"], -row["mean_spearman_ic"], row["factor_name"], row["state"]),
        ),
        "candidate_results": sorted(
            candidate_results,
            key=lambda row: (-row["state_research_lead_count"], -row["best_state_mean_ic"], row["factor_name"]),
        ),
        "decision": {
            "research_screen_allowed": passes,
            "reference_dedup_walk_forward_preflight_allowed_next": passes,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": _unique(decision_blockers),
            "next_direction": next_direction,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_reference_dedup_walk_forward": False,
            "requires_reference_dedup": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_final_holdout_read_once": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_pairwise_residual_ic_prescreen_markdown(result)
    return result


def write_lpr_macro_regime_pairwise_residual_ic_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_pairwise_residual_ic_prescreen.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_pairwise_residual_ic_prescreen.md").write_text(
        render_lpr_macro_regime_pairwise_residual_ic_prescreen_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "lpr_macro_regime_pairwise_state_ic.csv", clean["state_ic_results"], STATE_IC_COLUMNS)
    _write_csv(output_path / "lpr_macro_regime_pairwise_candidates.csv", clean["candidate_results"], CANDIDATE_COLUMNS)


def render_lpr_macro_regime_pairwise_residual_ic_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# LPR Macro Regime Pairwise Residual IC Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Residual IC files: {summary.get('residual_ic_file_count', 0)}",
        f"- Analysis-window IC rows: {summary.get('analysis_window_ic_rows', summary.get('paired_ic_rows', 0))}",
        f"- Paired IC rows: {summary.get('paired_ic_rows', 0)}",
        f"- Residual factors: {summary.get('residual_factor_count', 0)}",
        f"- State tests: {summary.get('state_test_count', 0)}",
        f"- State research leads: {summary.get('state_research_lead_count', 0)}",
        f"- Candidate research leads: {summary.get('candidate_research_lead_count', 0)}",
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
            "## Top State IC Results",
            "",
            "| Source | Factor | State | Obs | IC | ICIR | t-stat | IC+ | FDR | Lead | Blockers |",
            "|---|---|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in result.get("state_ic_results", [])[:30]:
        lines.append(
            "| {source} | {factor} | {state} | {obs} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {fdr} | {lead} | {blockers} |".format(
                source=row.get("source_id", ""),
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                obs=row.get("ic_observations", 0),
                ic=float(row.get("mean_spearman_ic", 0.0) or 0.0),
                icir=float(row.get("icir", 0.0) or 0.0),
                t=float(row.get("ic_t_stat", 0.0) or 0.0),
                pos=float(row.get("positive_ic_rate", 0.0) or 0.0),
                fdr="yes" if row.get("fdr_significant", False) else "no",
                lead="yes" if row.get("state_research_lead", False) else "no",
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _normalise_residual_ic(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["factor_name", "horizon", "date", "spearman_ic", "cross_section"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Residual IC observations missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["factor_name"] = output["factor_name"].astype(str)
    output["horizon"] = pd.to_numeric(output["horizon"], errors="coerce").astype("Int64")
    output["date"] = pd.to_datetime(output["date"], errors="coerce").astype("datetime64[ns]")
    output["spearman_ic"] = pd.to_numeric(output["spearman_ic"], errors="coerce")
    output["cross_section"] = pd.to_numeric(output["cross_section"], errors="coerce")
    if "source_id" not in output:
        output["source_id"] = "unspecified"
    output["source_id"] = output["source_id"].astype(str)
    return output.dropna(subset=["factor_name", "horizon", "date", "spearman_ic", "cross_section"]).reset_index(drop=True)


def _normalise_state_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["available_date", STATE_COLUMN]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"LPR state frame missing columns: {', '.join(missing)}")
    output = frame[required].copy()
    output["available_date"] = pd.to_datetime(output["available_date"], errors="coerce").astype("datetime64[ns]")
    output[STATE_COLUMN] = output[STATE_COLUMN].astype(str)
    return output.dropna(subset=["available_date", STATE_COLUMN]).drop_duplicates("available_date", keep="last")


def _analysis_window(
    frame: pd.DataFrame,
    *,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
) -> tuple[pd.DataFrame, int]:
    if frame.empty:
        return frame.copy(), 0
    output = frame[(frame["date"] >= pd.Timestamp(analysis_start_date)) & (frame["date"] <= pd.Timestamp(analysis_end_date))].copy()
    holdout_start = pd.Timestamp(FINAL_HOLDOUT_START)
    excluded = int((output["date"] >= holdout_start).sum())
    if not include_final_holdout:
        output = output[output["date"] < holdout_start].copy()
    return output.reset_index(drop=True), excluded


def _pairing_audit(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {
            "state_join_miss_count": 0,
            "available_date_after_signal_date_violations": 0,
            "paired_state_count": 0,
            "directional_state_count": 0,
        }
    states = frame[STATE_COLUMN].dropna()
    directional_states = states[states.isin(["gap_widening", "gap_narrowing"])]
    return {
        "state_join_miss_count": int(frame[STATE_COLUMN].isna().sum()),
        "available_date_after_signal_date_violations": int((frame["lpr_available_date"] > frame["date"]).sum()),
        "paired_state_count": int(states.nunique()),
        "directional_state_count": int(directional_states.nunique()),
    }


def _state_ic_results(
    frame: pd.DataFrame,
    *,
    min_state_ic_observations: int,
    min_mean_ic: float,
    min_icir: float,
    min_positive_ic_rate: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if frame.empty:
        return rows
    group_columns = ["source_id", "factor_name", "horizon", STATE_COLUMN]
    for (source_id, factor_name, horizon, state), group in frame.groupby(group_columns, sort=True):
        values = pd.to_numeric(group["spearman_ic"], errors="coerce").dropna()
        if values.empty:
            continue
        std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        mean = float(values.mean())
        t_stat = _t_stat(mean, std, len(values))
        rows.append(
            {
                "source_id": str(source_id),
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "state": str(state),
                "state_type": _state_type(str(state)),
                "ic_observations": int(len(values)),
                "mean_spearman_ic": mean,
                "ic_std": std,
                "icir": _safe_ratio(mean, std),
                "ic_t_stat": t_stat,
                "p_value": _normal_approx_two_sided_p(t_stat),
                "bonferroni_significant": False,
                "fdr_significant": False,
                "positive_ic_rate": float((values > 0).mean()),
                "median_cross_section": float(pd.to_numeric(group["cross_section"], errors="coerce").median()),
                "first_date": _min_date(group, "date"),
                "last_date": _max_date(group, "date"),
                "state_research_lead": False,
                "portfolio_grid_allowed": False,
                "promotion_allowed": False,
                "blockers": [],
                "threshold_context": {
                    "min_state_ic_observations": int(min_state_ic_observations),
                    "min_mean_ic": float(min_mean_ic),
                    "min_icir": float(min_icir),
                    "min_positive_ic_rate": float(min_positive_ic_rate),
                },
            }
        )
    return rows


def _apply_multiple_testing(rows: list[dict[str, Any]], *, alpha: float) -> None:
    if not rows:
        return
    test_count = len(rows)
    for row in rows:
        row["bonferroni_significant"] = bool(float(row["p_value"]) <= float(alpha) / test_count)
    sorted_rows = sorted(enumerate(rows), key=lambda item: float(item[1]["p_value"]))
    cutoff = None
    for rank, (_, row) in enumerate(sorted_rows, start=1):
        if float(row["p_value"]) <= (rank / test_count) * float(alpha):
            cutoff = float(row["p_value"])
    if cutoff is None:
        return
    for row in rows:
        row["fdr_significant"] = bool(float(row["p_value"]) <= cutoff)


def _apply_state_lead_flags(
    rows: list[dict[str, Any]],
    *,
    min_state_ic_observations: int,
    min_mean_ic: float,
    min_icir: float,
    min_positive_ic_rate: float,
    global_blockers: Sequence[str],
) -> None:
    for row in rows:
        blockers = list(global_blockers)
        if row["state_type"] != "directional":
            blockers.append("non_directional_lpr_state")
        if int(row["ic_observations"]) < int(min_state_ic_observations):
            blockers.append("state_ic_observations_below_threshold")
        if float(row["mean_spearman_ic"]) < float(min_mean_ic):
            blockers.append("state_mean_ic_below_threshold")
        if float(row["icir"]) < float(min_icir):
            blockers.append("state_icir_below_threshold")
        if float(row["positive_ic_rate"]) < float(min_positive_ic_rate):
            blockers.append("state_positive_ic_rate_below_threshold")
        if not row["fdr_significant"]:
            blockers.append("state_ic_not_fdr_significant")
        row["blockers"] = _unique(blockers)
        row["state_research_lead"] = not row["blockers"]


def _candidate_results(rows: list[dict[str, Any]], *, global_blockers: Sequence[str]) -> list[dict[str, Any]]:
    if not rows:
        return []
    output = []
    frame = pd.DataFrame(rows)
    for (source_id, factor_name, horizon), group in frame.groupby(["source_id", "factor_name", "horizon"], sort=True):
        leads = group[group["state_research_lead"]]
        best = group.sort_values("mean_spearman_ic", ascending=False).iloc[0]
        blockers = list(global_blockers)
        if leads.empty:
            blockers.append("no_directional_lpr_state_ic_lead")
        output.append(
            {
                "source_id": str(source_id),
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "state_test_count": int(len(group)),
                "state_research_lead_count": int(len(leads)),
                "best_state": str(best["state"]),
                "best_state_mean_ic": float(best["mean_spearman_ic"]),
                "best_state_icir": float(best["icir"]),
                "best_state_t_stat": float(best["ic_t_stat"]),
                "portfolio_grid_allowed": False,
                "promotion_allowed": False,
                "blockers": _unique(blockers),
            }
        )
    return output


def _state_prescreen_blockers(state_prescreen: dict[str, Any]) -> list[str]:
    decision = _dict(state_prescreen.get("decision"))
    blockers = []
    if state_prescreen.get("stage") != "lpr_macro_regime_state_prescreen":
        blockers.append("lpr_state_prescreen_stage_mismatch")
    if state_prescreen.get("live_boundary_allowed") is not False:
        blockers.append("lpr_state_prescreen_live_boundary_violation")
    if _dict(state_prescreen.get("summary")).get("passes") is not True:
        blockers.append("lpr_state_prescreen_not_passing")
    if decision.get("state_ready_for_regime_control") is not True or decision.get("residual_ic_pairing_allowed_next") is not True:
        blockers.append("lpr_state_prescreen_not_ready_for_pairing")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("lpr_state_prescreen_policy_boundary_violation")
    return blockers


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.DataFrame()


def _state_type(state: str) -> str:
    if state in {"gap_widening", "gap_narrowing"}:
        return "directional"
    if state == "insufficient_lookback":
        return "warmup"
    return "flat"


def _normal_approx_two_sided_p(t_stat: float) -> float:
    value = abs(float(t_stat))
    return float(math.erfc(value / math.sqrt(2.0)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(float(denominator)) <= 1e-12:
        return 0.0
    return float(numerator / denominator)


def _t_stat(mean: float, std: float, observations: int) -> float:
    if observations <= 1 or abs(float(std)) <= 1e-12:
        return 0.0
    return float(mean / (std / math.sqrt(observations)))


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            if isinstance(clean.get("blockers"), list):
                clean["blockers"] = "|".join(str(item) for item in clean["blockers"])
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


def _empty_residual_ic_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["source_id", "source_path", "factor_name", "horizon", "date", "spearman_ic", "cross_section"])


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


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
