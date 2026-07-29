from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.factors.etf_delayed_nav_premium_innovation import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
)
from quant_robot.ops.cn_etf_dynamic_peer_dislocation_prescreen import (
    CLOSED_FAMILY_REFERENCE_NAMES,
    compute_closed_family_reference_union,
    summarize_cn_etf_dynamic_peer_dislocation_prescreen,
)
from quant_robot.storage.atomic import atomic_write, atomic_write_text


STAGE = "cn_etf_delayed_nav_premium_prescreen"
SAFETY = (
    "Research-to-paper only. No portfolio grid, walk-forward, final holdout, "
    "paper signal, broker connection, account read, order placement, or live trading."
)
ONE_WAY_COSTS_BPS = (10.5, 26.6666666667, 60.0)


def summarize_cn_etf_delayed_nav_premium_prescreen(
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
        expected_reference_names=CLOSED_FAMILY_REFERENCE_NAMES,
        direct_exposure_names=DIRECT_EXPOSURE_NAMES,
        horizons=(1, 5),
        primary_horizon=1,
        diagnostic_horizon=5,
        position_value_cny=1000.0,
        max_one_way_participation_rate=0.01,
        one_way_costs_bps=ONE_WAY_COSTS_BPS,
        required_positive_net_spread_bps=10.5,
        candidate_name=FACTOR_NAME,
        result_stage=STAGE,
        safety_text=SAFETY,
        expected_horizons=(1, 5),
        expected_one_way_costs_bps=ONE_WAY_COSTS_BPS,
        expected_required_positive_net_spread_bps=10.5,
        **kwargs,
    )


def write_cn_etf_delayed_nav_premium_prescreen(
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
    atomic_write_text(
        paths["json"],
        json.dumps(_sanitize(result), indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(paths["markdown"], render_cn_etf_delayed_nav_premium_prescreen(result))
    for name in paths.keys() - {"json", "markdown"}:
        frame = _stable_frame(result.get(name, []))
        atomic_write(paths[name], lambda temporary, value=frame: value.to_csv(temporary, index=False))
    return paths


def render_cn_etf_delayed_nav_premium_prescreen(result: dict[str, Any]) -> str:
    decision = result.get("decision", {})
    lines = [
        "# CN ETF Delayed-NAV Premium Prescreen",
        "",
        f"- Status: `{result.get('status', 'unknown')}`",
        f"- Primary H1 passed: {str(bool(decision.get('primary_passed', False))).lower()}",
        f"- Diagnostic H5 passed: {str(bool(decision.get('diagnostic_passed', False))).lower()}",
        f"- Next action: `{decision.get('next_action', 'n/a')}`",
        "- Base one-way cost: 10.5 bp",
        "- CNY 3,000 minimum-fee stress: 26.6667 bp one way",
        "- CNY 1,000 minimum-fee stress: 60 bp one way",
        "- Final 2026 holdout included: false",
        "- Live boundary allowed: false",
        "",
        "## Results",
        "",
    ]
    for row in result.get("results", []):
        lines.append(
            "- {role} H{horizon}: mean IC {ic:.6f}, ICIR {icir:.4f}, "
            "FDR q {fdr:.6f}, base-cost net spread {net:.6f}, passed {passed}".format(
                role=row.get("horizon_role", ""),
                horizon=int(row.get("horizon", 0)),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                fdr=float(row.get("fdr_adjusted_p_value", 1.0)),
                net=float(row.get("mean_net_top_minus_bottom_10.5bps", 0.0)),
                passed=str(bool(row.get("role_passed", False))).lower(),
            )
        )
        if row.get("blockers"):
            lines.append("  Blockers: " + ", ".join(str(value) for value in row["blockers"]))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "H5 cannot rescue H1. No sign flip, lookback change, subgroup rescue, "
            "threshold relaxation, second execution, portfolio grid, walk-forward, "
            "holdout access, paper signal, or broker action is allowed.",
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
    "summarize_cn_etf_delayed_nav_premium_prescreen",
    "write_cn_etf_delayed_nav_premium_prescreen",
]
