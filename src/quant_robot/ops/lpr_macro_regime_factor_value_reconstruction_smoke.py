from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)
from quant_robot.ops.public_anomaly_residual_ensemble_prescreen import (
    build_public_anomaly_residual_ensemble_factor_frame,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (
    DEFAULT_RESIDUAL_EXPOSURES,
    _merge_lead_exposures,
    industry_neutralize_technical_lead,
    residualize_technical_lead,
)
from quant_robot.ops.public_trend_strength_state_residual_prescreen import (
    build_public_trend_strength_state_bar_features,
    build_public_trend_strength_state_exposure_frame,
    build_public_trend_strength_state_factor_frame,
    _stock_basic_frame,
)


STAGE = "lpr_macro_regime_factor_value_reconstruction_smoke"
PREFLIGHT_STAGE = "lpr_macro_regime_reference_dedup_preflight"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
CANDIDATE_COLUMNS = [
    "source_id",
    "factor_name",
    "base_factor_name",
    "horizon",
    "state",
    "factor_value_rows",
    "state_factor_rows",
    "state_dates",
    "median_cross_section",
    "first_state_date",
    "last_state_date",
    "factor_value_reference_dedup_input_ready",
    "blockers",
]


def run_lpr_macro_regime_factor_value_reconstruction_smoke(
    *,
    processed_root: str | Path,
    preflight_path: str | Path,
    bars_roots: Sequence[str | Path],
    daily_basic_roots: Sequence[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    output_dir: str | Path,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
) -> dict[str, Any]:
    preflight = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    factor_frame = rebuild_lpr_representative_residual_factor_values(
        preflight,
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_signal_date_amount=min_signal_date_amount,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    result = summarize_lpr_macro_regime_factor_value_reconstruction_smoke(
        preflight,
        factor_frame,
        state_frame,
        processed_root=processed_root,
        preflight_path=preflight_path,
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        market=market,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        min_signal_date_amount=min_signal_date_amount,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
    )
    write_lpr_macro_regime_factor_value_reconstruction_smoke(output_dir, result)
    return result


def rebuild_lpr_representative_residual_factor_values(
    preflight: dict[str, Any],
    *,
    bars_roots: Sequence[str | Path],
    daily_basic_roots: Sequence[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    analysis_start_date: str,
    analysis_end_date: str,
    min_signal_date_amount: float,
    min_cross_section: int,
    min_industries: int,
    min_assets_per_industry: int,
) -> pd.DataFrame:
    candidates = _representative_candidates(preflight)
    if not candidates:
        return _empty_factor_frame()
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    horizons = tuple(sorted({int(row["horizon"]) for row in candidates if int(row["horizon"]) > 0})) or (5,)
    features = build_public_trend_strength_state_bar_features(bars, horizons=horizons, execution_lag=1)
    exposure_frame = build_public_trend_strength_state_exposure_frame(features, stock_basic_frame)
    pieces = []
    anomaly_names = [row["base_factor_name"] for row in candidates if _is_public_anomaly(row["base_factor_name"])]
    trend_names = [row["base_factor_name"] for row in candidates if not _is_public_anomaly(row["base_factor_name"])]
    if anomaly_names:
        daily_basic = load_daily_basic_non_price_public_carry_inputs(
            daily_basic_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=False,
        )
        anomaly = build_public_anomaly_residual_ensemble_factor_frame(
            bars,
            daily_basic,
            exposure_frame,
            candidate_factor_names=tuple(anomaly_names),
            min_signal_date_amount=min_signal_date_amount,
        )
        pieces.extend(
            _residualize_candidate_values(
                anomaly,
                exposure_frame,
                base_factor_names=anomaly_names,
                min_cross_section=min_cross_section,
                min_industries=min_industries,
                min_assets_per_industry=min_assets_per_industry,
            )
        )
    if trend_names:
        trend = build_public_trend_strength_state_factor_frame(
            bars,
            exposure_frame,
            candidate_factor_names=tuple(trend_names),
            min_signal_date_amount=min_signal_date_amount,
        )
        pieces.extend(
            _residualize_candidate_values(
                trend,
                exposure_frame,
                base_factor_names=trend_names,
                min_cross_section=min_cross_section,
                min_industries=min_industries,
                min_assets_per_industry=min_assets_per_industry,
            )
        )
    if not pieces:
        return _empty_factor_frame()
    return pd.concat(pieces, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_lpr_macro_regime_factor_value_reconstruction_smoke(
    preflight: dict[str, Any],
    factor_frame: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    processed_root: str | Path | None = None,
    preflight_path: str | Path | None = None,
    bars_roots: Sequence[str | Path] = (),
    daily_basic_roots: Sequence[str | Path] = (),
    stock_basic: str | Path | pd.DataFrame | None = None,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
) -> dict[str, Any]:
    global_blockers = _preflight_blockers(preflight)
    candidates = _representative_candidates(preflight)
    if not candidates:
        global_blockers.append("no_lpr_factor_value_reconstruction_representatives")
    aligned = _align_factor_values_to_lpr_states(factor_frame, state_frame)
    aligned = _analysis_window(aligned, analysis_start_date=analysis_start_date, analysis_end_date=analysis_end_date)
    candidate_results = _candidate_results(
        candidates,
        aligned,
        global_blockers=global_blockers,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
    )
    ready_count = sum(1 for row in candidate_results if row["factor_value_reference_dedup_input_ready"])
    decision_blockers = _unique(global_blockers)
    if ready_count <= 0:
        decision_blockers.append("no_factor_value_ready_lpr_representatives")
    passes = bool(not global_blockers and ready_count > 0)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "preflight_path": str(Path(preflight_path)) if preflight_path is not None else None,
        "bars_roots": [str(Path(path)) for path in bars_roots],
        "daily_basic_roots": [str(Path(path)) for path in daily_basic_roots],
        "stock_basic": str(stock_basic) if isinstance(stock_basic, (str, Path)) else None,
        "summary": {
            "passes": passes,
            "representative_candidate_count": len(candidates),
            "factor_value_rows": int(len(factor_frame)),
            "factor_value_ready_candidate_count": ready_count,
            "factor_value_blocked_candidate_count": len(candidate_results) - ready_count,
            "factor_value_reference_dedup_allowed_next": passes,
            "walk_forward_preflight_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": (
                "state_conditioned_factor_value_reference_dedup"
                if passes
                else "repair_lpr_factor_value_reconstruction"
            ),
        },
        "data_window": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "first_factor_date": _min_date(factor_frame, "date"),
            "last_factor_date": _max_date(factor_frame, "date"),
        },
        "thresholds": {
            "min_signal_date_amount": float(min_signal_date_amount),
            "min_state_dates": int(min_state_dates),
            "min_median_cross_section": int(min_median_cross_section),
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_use": "blocked_for_factor_value_reconstruction_smoke",
        },
        "candidate_results": candidate_results,
        "decision": {
            "research_screen_allowed": passes,
            "factor_value_reference_dedup_allowed_next": passes,
            "walk_forward_preflight_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": _unique(decision_blockers),
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_factor_value_reconstruction_smoke_markdown(result)
    return result


def write_lpr_macro_regime_factor_value_reconstruction_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_factor_value_reconstruction_smoke.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_factor_value_reconstruction_smoke.md").write_text(
        render_lpr_macro_regime_factor_value_reconstruction_smoke_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lpr_macro_regime_factor_value_reconstruction_candidates.csv",
        clean["candidate_results"],
        CANDIDATE_COLUMNS,
    )


def render_lpr_macro_regime_factor_value_reconstruction_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# LPR Macro Regime Factor Value Reconstruction Smoke",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Representative candidates: {summary.get('representative_candidate_count', 0)}",
        f"- Factor value rows: {summary.get('factor_value_rows', 0)}",
        f"- Ready candidates: {summary.get('factor_value_ready_candidate_count', 0)}",
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
            "## Candidate Reconstruction",
            "",
            "| Factor | State | Rows | State Rows | Dates | Median CS | Ready | Blockers |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("candidate_results", []):
        lines.append(
            "| {factor} | {state} | {rows} | {state_rows} | {dates} | {cs:.1f} | {ready} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                rows=row.get("factor_value_rows", 0),
                state_rows=row.get("state_factor_rows", 0),
                dates=row.get("state_dates", 0),
                cs=float(row.get("median_cross_section", 0.0) or 0.0),
                ready="yes" if row.get("factor_value_reference_dedup_input_ready", False) else "no",
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _residualize_candidate_values(
    factor_frame: pd.DataFrame,
    exposure_frame: pd.DataFrame,
    *,
    base_factor_names: Sequence[str],
    min_cross_section: int,
    min_industries: int,
    min_assets_per_industry: int,
) -> list[pd.DataFrame]:
    pieces = []
    for base_name in base_factor_names:
        lead = factor_frame[factor_frame["factor_name"] == base_name].reset_index(drop=True)
        if lead.empty:
            continue
        lead_with_exposures = _merge_lead_exposures(lead, exposure_frame)
        industry = industry_neutralize_technical_lead(
            lead_with_exposures,
            industry_factor_name=f"{base_name}_industry_neutral",
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
        )
        residual = residualize_technical_lead(
            industry,
            exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
            residual_factor_name=f"{base_name}_industry_size_liquidity_vol_residual",
            min_cross_section=min_cross_section,
        )
        if not residual.empty:
            pieces.append(residual)
    return pieces


def _preflight_blockers(preflight: dict[str, Any]) -> list[str]:
    decision = _dict(preflight.get("decision"))
    blockers = []
    if preflight.get("stage") != PREFLIGHT_STAGE:
        blockers.append("reference_dedup_preflight_stage_mismatch")
    if _dict(preflight.get("summary")).get("passes") is not True:
        blockers.append("reference_dedup_preflight_not_passing")
    if decision.get("factor_value_reference_dedup_allowed_next") is not True:
        blockers.append("reference_dedup_preflight_not_allowed_for_factor_value_reconstruction")
    if decision.get("walk_forward_preflight_allowed") is not False:
        blockers.append("reference_dedup_preflight_walk_forward_boundary_violation")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("reference_dedup_preflight_policy_boundary_violation")
    if preflight.get("live_boundary_allowed") is not False:
        blockers.append("reference_dedup_preflight_live_boundary_violation")
    return blockers


def _representative_candidates(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in preflight.get("candidate_results", []):
        if not isinstance(row, dict):
            continue
        if row.get("cluster_representative") is not True or row.get("factor_value_reference_dedup_allowed") is not True:
            continue
        rows.append(
            {
                "source_id": str(row.get("source_id", "")),
                "factor_name": str(row.get("factor_name", "")),
                "base_factor_name": str(row.get("base_factor_name", "")),
                "horizon": int(row.get("horizon", 0)),
                "state": str(row.get("state", "")),
            }
        )
    return rows


def _candidate_results(
    candidates: Sequence[dict[str, Any]],
    aligned: pd.DataFrame,
    *,
    global_blockers: Sequence[str],
    min_state_dates: int,
    min_median_cross_section: int,
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        factor_rows = aligned[aligned["factor_name"] == candidate["factor_name"]].copy()
        state_rows = factor_rows[factor_rows[STATE_COLUMN] == candidate["state"]].copy()
        cross_sections = state_rows.groupby("date")["asset_id"].nunique() if not state_rows.empty else pd.Series(dtype=float)
        median_cross_section = float(cross_sections.median()) if not cross_sections.empty else 0.0
        blockers = list(global_blockers)
        if state_rows["date"].nunique() < int(min_state_dates):
            blockers.append("state_factor_dates_below_threshold")
        if median_cross_section < float(min_median_cross_section):
            blockers.append("state_factor_median_cross_section_below_threshold")
        if int(len(factor_rows)) <= 0:
            blockers.append("factor_value_rows_missing")
        rows.append(
            {
                **candidate,
                "factor_value_rows": int(len(factor_rows)),
                "state_factor_rows": int(len(state_rows)),
                "state_dates": int(state_rows["date"].nunique()) if "date" in state_rows else 0,
                "median_cross_section": median_cross_section,
                "first_state_date": _min_date(state_rows, "date"),
                "last_state_date": _max_date(state_rows, "date"),
                "factor_value_reference_dedup_input_ready": not blockers,
                "blockers": _unique(blockers),
            }
        )
    return rows


def _align_factor_values_to_lpr_states(factor_frame: pd.DataFrame, state_frame: pd.DataFrame) -> pd.DataFrame:
    factors = _normalise_factor_frame(factor_frame)
    states = _normalise_state_frame(state_frame)
    if factors.empty or states.empty:
        return factors.assign(lpr_available_date=pd.NaT, **{STATE_COLUMN: pd.NA})
    aligned = pd.merge_asof(
        factors.sort_values("date").reset_index(drop=True),
        states.sort_values("available_date").reset_index(drop=True),
        left_on="date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=True,
    )
    return aligned.rename(columns={"available_date": "lpr_available_date"})


def _analysis_window(frame: pd.DataFrame, *, analysis_start_date: str, analysis_end_date: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame[
        (frame["date"] >= pd.Timestamp(analysis_start_date))
        & (frame["date"] <= pd.Timestamp(analysis_end_date))
        & (frame["date"] < pd.Timestamp(FINAL_HOLDOUT_START))
    ].copy()
    return output.reset_index(drop=True)


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_factor_frame()
    output = frame[["date", "asset_id", "market", "factor_name", "factor_value"]].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").astype("datetime64[ns]")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str)
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "factor_name", "factor_value"]).reset_index(drop=True)


def _normalise_state_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty or "available_date" not in frame or STATE_COLUMN not in frame:
        return pd.DataFrame(columns=["available_date", STATE_COLUMN])
    output = frame[["available_date", STATE_COLUMN]].copy()
    output["available_date"] = pd.to_datetime(output["available_date"], errors="coerce").astype("datetime64[ns]")
    output[STATE_COLUMN] = output[STATE_COLUMN].astype(str)
    return output.dropna(subset=["available_date", STATE_COLUMN]).drop_duplicates("available_date", keep="last")


def _is_public_anomaly(base_factor_name: str) -> bool:
    return str(base_factor_name).startswith("public_anomaly_residual_")


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            if isinstance(clean.get("blockers"), list):
                clean["blockers"] = "|".join(str(item) for item in clean["blockers"])
            writer.writerow(clean)


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


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
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
