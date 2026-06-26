from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.profitability_quality_factor_matrix_smoke import (
    _align_factor_values_to_labels,
    _event_frame,
    _factor_values,
    _load_bars,
)
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "profitability_quality_controlled_ic_screen"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_profitability_quality_controlled_ic_screen(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    alpha: float = 0.05,
) -> dict[str, Any]:
    financial = _load_fina_indicator_inputs(Path(financial_root))
    preregistration = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [
        candidate
        for candidate in preregistration.get("candidates", []) or []
        if candidate.get("registration_status") == "pre_registered"
    ]
    assets = sorted(financial["asset_id"].dropna().unique()) if "asset_id" in financial.columns else []
    bars = _load_bars([Path(root) for root in bars_roots], assets)
    labels = make_forward_returns(bars, horizons=tuple(horizons), execution_lag=execution_lag) if not bars.empty else _empty_labels()
    event_frame = _event_frame(financial, bars)
    factor_values = _factor_values(financial, candidates)
    aligned = _align_factor_values_to_labels(factor_values, event_frame, labels)
    result = summarize_controlled_ic(
        aligned,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        alpha=alpha,
    )
    blockers = list(result["summary"]["blockers"])
    if financial.empty:
        blockers.append("missing_financial_rows")
    if not candidates:
        blockers.append("missing_preregistered_candidates")
    if bars.empty:
        blockers.append("missing_bars")
    payload: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(Path(financial_root)),
        "bars_roots": [str(Path(root)) for root in bars_roots],
        "preregistration_json": str(Path(preregistration_json)),
        "summary": {
            **result["summary"],
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "aligned_rows": int(len(aligned)),
            "bar_rows": int(len(bars)),
            "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
            "horizons": list(horizons),
            "execution_lag": execution_lag,
        },
        "ic_results": result["ic_results"],
        "ic_observations": result["ic_observations"],
        "multiple_testing": result["multiple_testing"],
        "promotion_policy": {
            "promotion_allowed": False,
            "paper_ready_allowed": False,
            "portfolio_backtest_allowed": False,
            "next_allowed_action": "Review IC evidence; only research leads may proceed to robustness and portfolio-translation checks.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    payload["markdown"] = render_profitability_quality_controlled_ic_screen_markdown(payload)
    return payload


def summarize_controlled_ic(
    aligned: pd.DataFrame,
    *,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    alpha: float = 0.05,
) -> dict[str, Any]:
    required = {"factor_name", "horizon", "end_date", "asset_id", "factor_value", "forward_return"}
    missing = sorted(required - set(aligned.columns))
    blockers: list[str] = []
    if missing:
        blockers.append("missing_required_aligned_columns")
    ic_rows = [] if missing else _ic_observation_rows(aligned, min_cross_section=min_cross_section)
    observations = pd.DataFrame(ic_rows)
    results = _ic_result_rows(observations, min_ic_observations=min_ic_observations, alpha=alpha)
    results = _apply_multiple_testing(results, alpha=alpha)
    if not results:
        blockers.append("missing_ic_results")
    if results and all(row["ic_observation_count"] < min_ic_observations for row in results):
        blockers.append("insufficient_ic_observations")
    bonferroni_significant = sum(1 for row in results if row["bonferroni_significant"])
    fdr_significant = sum(1 for row in results if row["fdr_significant"])
    return {
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "test_count": len(results),
            "ic_observation_count": int(len(observations)),
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "alpha": alpha,
            "bonferroni_significant": bonferroni_significant,
            "fdr_significant": fdr_significant,
            "research_lead_count": sum(1 for row in results if row["research_lead"]),
        },
        "ic_results": results,
        "ic_observations": observations.to_dict("records") if not observations.empty else [],
        "multiple_testing": {
            "method": "bonferroni_and_benjamini_hochberg",
            "test_count": len(results),
            "alpha": alpha,
            "bonferroni_alpha": alpha / len(results) if results else None,
        },
    }


def write_profitability_quality_controlled_ic_screen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_quality_controlled_ic_screen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_quality_controlled_ic_screen.md").write_text(
        render_profitability_quality_controlled_ic_screen_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("ic_results", []) or []).to_csv(
        output_path / "profitability_quality_controlled_ic_results.csv",
        index=False,
    )
    pd.DataFrame(result.get("ic_observations", []) or []).to_csv(
        output_path / "profitability_quality_controlled_ic_observations.csv",
        index=False,
    )


def render_profitability_quality_controlled_ic_screen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Profitability Quality Controlled IC Screen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- IC observations: {summary.get('ic_observation_count', 0)}",
        f"- Bonferroni significant: {summary.get('bonferroni_significant', 0)}",
        f"- FDR significant: {summary.get('fdr_significant', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## IC Results",
        "",
        "| Factor | Horizon | IC Mean | ICIR | t-stat | p-value | N | Bonferroni | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in result.get("ic_results", []) or []:
        lines.append(
            "| {factor} | {horizon} | {ic_mean:.4f} | {icir:.3f} | {t_stat:.2f} | {p_value:.4g} | {count} | {bonf} | {fdr} | {lead} |".format(
                factor=row["factor_name"],
                horizon=row["horizon"],
                ic_mean=float(row["ic_mean"]),
                icir=float(row["icir"]),
                t_stat=float(row["t_stat"]),
                p_value=float(row["p_value"]),
                count=row["ic_observation_count"],
                bonf=row["bonferroni_significant"],
                fdr=row["fdr_significant"],
                lead=row["research_lead"],
            )
        )
    return "\n".join(lines) + "\n"


def _empty_labels() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "horizon", "execution_lag", "forward_return", "entry_date", "exit_date"]
    )


def _ic_observation_rows(aligned: pd.DataFrame, *, min_cross_section: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grouped = aligned.dropna(subset=["factor_value", "forward_return"]).groupby(["factor_name", "horizon", "end_date"])
    for (factor_name, horizon, end_date), group in grouped:
        cross_section = group.drop_duplicates("asset_id", keep="last")
        n = int(len(cross_section))
        if n < min_cross_section:
            continue
        ic = _spearman(cross_section["factor_value"], cross_section["forward_return"])
        if math.isfinite(ic):
            rows.append(
                {
                    "factor_name": str(factor_name),
                    "horizon": int(horizon),
                    "end_date": pd.to_datetime(end_date).date().isoformat(),
                    "ic": ic,
                    "cross_section_size": n,
                }
            )
    return rows


def _ic_result_rows(observations: pd.DataFrame, *, min_ic_observations: int, alpha: float) -> list[dict[str, Any]]:
    if observations.empty:
        return []
    rows: list[dict[str, Any]] = []
    for (factor_name, horizon), group in observations.groupby(["factor_name", "horizon"]):
        count = int(len(group))
        ic_mean = float(group["ic"].mean())
        ic_std = float(group["ic"].std(ddof=1)) if count > 1 else 0.0
        icir = ic_mean / ic_std if ic_std > 0 else 0.0
        t_stat = ic_mean / (ic_std / math.sqrt(count)) if ic_std > 0 else (math.inf if ic_mean > 0 else -math.inf)
        p_value = _two_sided_normal_p_value(t_stat)
        positive_rate = float((group["ic"] > 0).mean())
        eligible = count >= min_ic_observations
        rows.append(
            {
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "ic_mean": ic_mean,
                "ic_std": ic_std,
                "icir": icir,
                "t_stat": t_stat,
                "p_value": p_value,
                "positive_ic_rate": positive_rate,
                "ic_observation_count": count,
                "eligible_observation_count": eligible,
                "research_lead": bool(eligible and abs(ic_mean) >= 0.02 and abs(icir) >= 0.3 and abs(t_stat) >= 2.0),
                "alpha": alpha,
            }
        )
    return sorted(rows, key=lambda row: (abs(row["t_stat"]), abs(row["ic_mean"])), reverse=True)


def _apply_multiple_testing(rows: list[dict[str, Any]], *, alpha: float) -> list[dict[str, Any]]:
    if not rows:
        return []
    n_tests = len(rows)
    for row in rows:
        row["bonferroni_p_value"] = min(float(row["p_value"]) * n_tests, 1.0)
        row["bonferroni_significant"] = bool(row["p_value"] <= alpha / n_tests)
        row["fdr_significant"] = False
    indexed = sorted(enumerate(rows), key=lambda item: item[1]["p_value"])
    max_significant_rank = -1
    for rank, (_, row) in enumerate(indexed, start=1):
        if row["p_value"] <= (rank / n_tests) * alpha:
            max_significant_rank = rank
    if max_significant_rank > 0:
        for rank, (_, row) in enumerate(indexed, start=1):
            if rank <= max_significant_rank:
                row["fdr_significant"] = True
    for row in rows:
        row["research_lead_after_multiple_testing"] = bool(row["research_lead"] and row["fdr_significant"])
    return rows


def _spearman(left: pd.Series, right: pd.Series) -> float:
    left_rank = pd.Series(left).rank(method="average")
    right_rank = pd.Series(right).rank(method="average")
    if left_rank.nunique(dropna=True) < 2 or right_rank.nunique(dropna=True) < 2:
        return math.nan
    corr = left_rank.corr(right_rank)
    return float(corr) if corr is not None else math.nan


def _two_sided_normal_p_value(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return 0.0
    return math.erfc(abs(t_stat) / math.sqrt(2.0))
