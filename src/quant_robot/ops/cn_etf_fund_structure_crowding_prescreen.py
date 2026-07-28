from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.factors.etf_residual_share_creation_crowding import FACTOR_NAME
from quant_robot.ops.cn_etf_dynamic_peer_dislocation_prescreen import (
    CLOSED_FAMILY_REFERENCE_NAMES,
    compute_closed_family_reference_union,
    summarize_cn_etf_dynamic_peer_dislocation_prescreen,
)


STAGE = "cn_etf_fund_structure_crowding_prescreen"
SAFETY = (
    "Research-to-paper only. No portfolio grid, walk-forward, final holdout, "
    "paper signal, broker connection, account read, order placement, or live trading."
)


def summarize_cn_etf_fund_structure_crowding_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    direct_exposures: pd.DataFrame,
    adv20: pd.DataFrame,
    **kwargs: Any,
) -> dict[str, Any]:
    return summarize_cn_etf_dynamic_peer_dislocation_prescreen(
        factors,
        labels,
        references,
        direct_exposures,
        adv20,
        candidate_name=FACTOR_NAME,
        result_stage=STAGE,
        safety_text=SAFETY,
        **kwargs,
    )


def write_cn_etf_fund_structure_crowding_prescreen(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / f"{STAGE}.json",
        "markdown": output / f"{STAGE}.md",
        "results": output / "candidate_horizon_results.csv",
        "ic_observations": output / "daily_ic.csv",
        "yearly_ic": output / "yearly_ic.csv",
        "reference_correlations": output / "reference_correlations.csv",
        "direct_exposure_correlations": output / "direct_exposure_correlations.csv",
        "turnover_cost_summary": output / "turnover_cost_summary.csv",
        "turnover_cost_daily": output / "turnover_cost_daily.csv",
        "capacity_summary": output / "capacity_summary.csv",
        "capacity_daily": output / "capacity_daily.csv",
        "capacity_top_constituents": output / "capacity_top_constituents.csv",
    }
    paths["json"].write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        render_cn_etf_fund_structure_crowding_prescreen(result),
        encoding="utf-8",
    )
    for name in paths.keys() - {"json", "markdown"}:
        _stable_frame(result.get(name, [])).to_csv(paths[name], index=False)
    return paths


def render_cn_etf_fund_structure_crowding_prescreen(
    result: dict[str, Any],
) -> str:
    decision = result.get("decision", {})
    lines = [
        "# CN ETF Fund-Structure Crowding Prescreen",
        "",
        f"- Status: `{result.get('status', 'unknown')}`",
        f"- Primary passed: {str(bool(decision.get('primary_passed', False))).lower()}",
        f"- Diagnostic passed: {str(bool(decision.get('diagnostic_passed', False))).lower()}",
        f"- Next action: `{decision.get('next_action', 'n/a')}`",
        "- Final 2026 holdout included: false",
        "- Live boundary allowed: false",
        "",
        "## Results",
        "",
        "| Role | H | Mean IC | ICIR | FDR q | Q5-Q1 | Net 10bps | Capacity | Max ref | Max exposure | Passed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {role} | {horizon} | {ic:.4f} | {icir:.3f} | {fdr:.4f} | "
            "{spread:.6f} | {net:.6f} | {capacity} | {reference:.4f} | "
            "{exposure:.4f} | {passed} |".format(
                role=row.get("horizon_role", ""),
                horizon=int(row.get("horizon", 0)),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                fdr=float(row.get("fdr_adjusted_p_value", 1.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                net=float(row.get("mean_net_top_minus_bottom_10bps", 0.0)),
                capacity="yes" if row.get("every_date_supported") else "no",
                reference=float(row.get("max_abs_reference_correlation", 0.0)),
                exposure=float(row.get("max_abs_direct_exposure_correlation", 0.0)),
                passed="yes" if row.get("role_passed") else "no",
            )
        )
        blockers = row.get("blockers", [])
        if blockers:
            lines.append(f"  Blockers: {', '.join(str(item) for item in blockers)}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The diagnostic horizon cannot rescue the primary. No sign flip, "
            "window tuning, control removal, threshold relaxation, subgroup, "
            "portfolio, walk-forward, or holdout rescue is allowed.",
            "",
        ]
    )
    return "\n".join(lines)


def _stable_frame(rows: Any) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    sort_columns = [
        column
        for column in (
            "factor_name",
            "horizon",
            "date",
            "candidate_factor_name",
            "reference_factor_name",
            "exposure_name",
            "asset_id",
        )
        if column in frame.columns
    ]
    if sort_columns and not frame.empty:
        frame = frame.sort_values(sort_columns, kind="stable").reset_index(drop=True)
    return frame


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


__all__ = [
    "CLOSED_FAMILY_REFERENCE_NAMES",
    "STAGE",
    "compute_closed_family_reference_union",
    "summarize_cn_etf_fund_structure_crowding_prescreen",
    "write_cn_etf_fund_structure_crowding_prescreen",
]
