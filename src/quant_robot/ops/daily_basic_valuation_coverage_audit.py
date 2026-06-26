from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from quant_robot.storage.factor_inputs import load_factor_inputs


STAGE = "round210_daily_basic_valuation_coverage_audit"
NEXT_REPAIR_PREREGISTRATION = "round211_preregister_daily_basic_valuation_coverage_repaired_candidate"
NEXT_REQUIRES_DATA_BACKFILL = "round211_backfill_or_retire_daily_basic_valuation_fields"
NEXT_RESUME_VALUATION_RESEARCH = "round211_resume_daily_basic_valuation_research_after_coverage_audit"

DEFAULT_MIN_FULL_COVERAGE_RATIO = 0.80
DEFAULT_MIN_FIELD_NON_NULL_RATIO = 0.80
DEFAULT_MIN_DATE_PASS_RATIO = 0.80

DEFAULT_TARGET_FACTOR_SPECS: tuple[dict[str, Any], ...] = (
    {
        "factor_name": "daily_basic_valuation_reversion_quality_60",
        "required_fields": ("pb", "ps_ttm", "dv_ttm"),
        "replacement_field_candidates": {
            "dv_ttm": ("dv_ratio",),
            "ps_ttm": ("ps",),
        },
        "source_round": "round132",
        "raw_h20_mean_ic": 0.0700775146759485,
        "raw_h20_icir": 0.5276070114596769,
        "raw_h20_quantile_spread": 0.20904014220073622,
        "raw_blocker": "daily_basic_field_coverage_clean_ratio_below_minimum",
    },
    {
        "factor_name": "daily_basic_valuation_dispersion_compression_60",
        "required_fields": ("pb", "pe_ttm", "dv_ratio"),
        "replacement_field_candidates": {
            "pe_ttm": ("pe",),
        },
        "source_round": "round132",
        "raw_h20_mean_ic": 0.015059575795432534,
        "raw_h20_icir": 0.14171977363751523,
        "raw_h20_quantile_spread": 0.04836733064933949,
        "raw_blocker": "daily_basic_field_coverage_clean_ratio_below_minimum",
    },
)


def _normalise_specs(target_factor_specs: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    specs = list(target_factor_specs or DEFAULT_TARGET_FACTOR_SPECS)
    normalised = []
    for spec in specs:
        factor_name = str(spec["factor_name"])
        required_fields = tuple(str(field) for field in spec.get("required_fields", ()))
        replacements: dict[str, tuple[str, ...]] = {}
        for field, candidates in dict(spec.get("replacement_field_candidates", {})).items():
            replacements[str(field)] = tuple(str(candidate) for candidate in candidates)
        row = dict(spec)
        row["factor_name"] = factor_name
        row["required_fields"] = required_fields
        row["replacement_field_candidates"] = replacements
        normalised.append(row)
    return normalised


def _prepare_daily_basic_frame(
    daily_basic_frame: pd.DataFrame,
    *,
    analysis_start_date: str | None,
    analysis_end_date: str | None,
) -> pd.DataFrame:
    if daily_basic_frame.empty:
        return daily_basic_frame.copy()
    frame = daily_basic_frame.copy()
    if "date" not in frame:
        raise ValueError("daily_basic_frame must contain a date column")
    if "asset_id" not in frame:
        raise ValueError("daily_basic_frame must contain an asset_id column")
    frame["date"] = pd.to_datetime(frame["date"])
    if analysis_start_date:
        frame = frame[frame["date"] >= pd.Timestamp(analysis_start_date)]
    if analysis_end_date:
        frame = frame[frame["date"] <= pd.Timestamp(analysis_end_date)]
    return frame.reset_index(drop=True)


def _field_metrics(
    frame: pd.DataFrame,
    field: str,
    *,
    min_field_non_null_ratio: float,
    min_date_pass_ratio: float,
) -> dict[str, Any]:
    if frame.empty:
        return {
            "field": field,
            "row_count": 0,
            "non_null_count": 0,
            "non_null_ratio": 0.0,
            "date_count": 0,
            "date_pass_ratio": 0.0,
            "worst_month": "",
            "worst_month_non_null_ratio": 0.0,
            "field_pass": False,
            "field_exists": field in frame.columns,
        }
    if field in frame.columns:
        non_null = frame[field].notna()
    else:
        non_null = pd.Series(False, index=frame.index)
    date_ratio = non_null.groupby(frame["date"]).mean() if not frame.empty else pd.Series(dtype=float)
    month_ratio = non_null.groupby(frame["date"].dt.to_period("M").astype(str)).mean() if not frame.empty else pd.Series(dtype=float)
    worst_month = ""
    worst_month_ratio = 0.0
    if not month_ratio.empty:
        worst_month = str(month_ratio.idxmin())
        worst_month_ratio = float(month_ratio.min())
    field_pass = bool(
        float(non_null.mean()) >= min_field_non_null_ratio
        and (float((date_ratio >= min_field_non_null_ratio).mean()) if not date_ratio.empty else 0.0) >= min_date_pass_ratio
    )
    return {
        "field": field,
        "row_count": int(len(frame)),
        "non_null_count": int(non_null.sum()),
        "non_null_ratio": float(non_null.mean()) if len(non_null) else 0.0,
        "date_count": int(frame["date"].nunique()),
        "date_pass_ratio": float((date_ratio >= min_field_non_null_ratio).mean()) if not date_ratio.empty else 0.0,
        "worst_month": worst_month,
        "worst_month_non_null_ratio": worst_month_ratio,
        "field_pass": field_pass,
        "field_exists": field in frame.columns,
    }


def _factor_monthly_rows(frame: pd.DataFrame, factor_name: str, required_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    rows = []
    month_series = frame["date"].dt.to_period("M").astype(str)
    for month, group in frame.groupby(month_series, sort=True):
        field_valid = pd.DataFrame(index=group.index)
        row = {
            "factor_name": factor_name,
            "month": str(month),
            "row_count": int(len(group)),
            "asset_count": int(group["asset_id"].nunique()),
            "date_count": int(group["date"].nunique()),
        }
        for field in required_fields:
            valid = group[field].notna() if field in group.columns else pd.Series(False, index=group.index)
            field_valid[field] = valid
            row[f"{field}_non_null_ratio"] = float(valid.mean()) if len(valid) else 0.0
        full_valid = field_valid.all(axis=1) if not field_valid.empty else pd.Series(False, index=group.index)
        row["full_required_field_coverage_ratio"] = float(full_valid.mean()) if len(full_valid) else 0.0
        rows.append(row)
    return rows


def summarize_daily_basic_valuation_coverage_audit(
    *,
    daily_basic_frame: pd.DataFrame,
    target_factor_specs: Iterable[Mapping[str, Any]] | None = None,
    analysis_start_date: str | None = None,
    analysis_end_date: str | None = None,
    min_full_coverage_ratio: float = DEFAULT_MIN_FULL_COVERAGE_RATIO,
    min_field_non_null_ratio: float = DEFAULT_MIN_FIELD_NON_NULL_RATIO,
    min_date_pass_ratio: float = DEFAULT_MIN_DATE_PASS_RATIO,
) -> dict[str, Any]:
    frame = _prepare_daily_basic_frame(
        daily_basic_frame,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    specs = _normalise_specs(target_factor_specs)
    factor_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    replacement_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []

    for spec in specs:
        factor_name = spec["factor_name"]
        required_fields = tuple(spec["required_fields"])
        if required_fields:
            required_valid = pd.DataFrame(index=frame.index)
            for field in required_fields:
                required_valid[field] = frame[field].notna() if field in frame.columns else False
            full_valid = required_valid.all(axis=1)
        else:
            full_valid = pd.Series(False, index=frame.index)
        date_ratio = full_valid.groupby(frame["date"]).mean() if not frame.empty else pd.Series(dtype=float)
        full_ratio = float(full_valid.mean()) if len(full_valid) else 0.0
        date_pass_ratio = float((date_ratio >= min_full_coverage_ratio).mean()) if not date_ratio.empty else 0.0
        coverage_pass = bool(full_ratio >= min_full_coverage_ratio and date_pass_ratio >= min_date_pass_ratio)

        factor_field_rows = []
        low_coverage_fields = []
        for field in required_fields:
            metrics = _field_metrics(
                frame,
                field,
                min_field_non_null_ratio=min_field_non_null_ratio,
                min_date_pass_ratio=min_date_pass_ratio,
            )
            row = {
                "factor_name": factor_name,
                "field": field,
                "role": "required",
                **metrics,
            }
            field_rows.append(row)
            factor_field_rows.append(row)
            if not metrics["field_pass"]:
                low_coverage_fields.append(field)

        replacements = dict(spec.get("replacement_field_candidates", {}))
        low_field_repair_pass = {}
        for missing_field in low_coverage_fields:
            candidates = tuple(replacements.get(missing_field, ()))
            passed_candidates = 0
            for candidate_field in candidates:
                metrics = _field_metrics(
                    frame,
                    candidate_field,
                    min_field_non_null_ratio=min_field_non_null_ratio,
                    min_date_pass_ratio=min_date_pass_ratio,
                )
                replacement_pass = bool(metrics["field_pass"] and candidate_field != missing_field)
                passed_candidates += int(replacement_pass)
                replacement_rows.append(
                    {
                        "factor_name": factor_name,
                        "missing_field": missing_field,
                        "candidate_field": candidate_field,
                        "replacement_pass": replacement_pass,
                        **metrics,
                    }
                )
            low_field_repair_pass[missing_field] = passed_candidates > 0

        repair_allowed = bool(
            not coverage_pass
            and low_coverage_fields
            and all(low_field_repair_pass.get(field, False) for field in low_coverage_fields)
        )
        factor_rows.append(
            {
                "factor_name": factor_name,
                "required_fields": "|".join(required_fields),
                "row_count": int(len(frame)),
                "date_count": int(frame["date"].nunique()) if not frame.empty else 0,
                "asset_count": int(frame["asset_id"].nunique()) if not frame.empty else 0,
                "full_required_field_coverage_ratio": full_ratio,
                "date_pass_ratio": date_pass_ratio,
                "min_full_coverage_ratio": float(min_full_coverage_ratio),
                "min_field_non_null_ratio": float(min_field_non_null_ratio),
                "coverage_pass": coverage_pass,
                "low_coverage_fields": low_coverage_fields,
                "repair_candidate_pre_registration_allowed": repair_allowed,
                "source_round": spec.get("source_round", ""),
                "raw_h20_mean_ic": spec.get("raw_h20_mean_ic"),
                "raw_h20_icir": spec.get("raw_h20_icir"),
                "raw_h20_quantile_spread": spec.get("raw_h20_quantile_spread"),
                "raw_blocker": spec.get("raw_blocker", ""),
            }
        )
        monthly_rows.extend(_factor_monthly_rows(frame, factor_name, required_fields))

    coverage_pass_count = sum(int(row["coverage_pass"]) for row in factor_rows)
    repair_allowed_count = sum(int(row["repair_candidate_pre_registration_allowed"]) for row in factor_rows)
    blocked_count = sum(int(not row["coverage_pass"] and not row["repair_candidate_pre_registration_allowed"]) for row in factor_rows)
    blockers = []
    if coverage_pass_count < len(factor_rows):
        blockers.append("target_factor_field_coverage_below_threshold")
    if blocked_count:
        blockers.append("no_coverage_safe_replacement_field")
    if repair_allowed_count:
        blockers.append("portfolio_grid_blocked_until_repaired_factor_preregistered_and_rescreened")

    if repair_allowed_count and blocked_count:
        gate_status = "mixed_repair_ready_with_blocked_factors"
        next_direction = NEXT_REPAIR_PREREGISTRATION
    elif repair_allowed_count:
        gate_status = "repair_ready"
        next_direction = NEXT_REPAIR_PREREGISTRATION
    elif coverage_pass_count == len(factor_rows) and factor_rows:
        gate_status = "coverage_passed"
        next_direction = NEXT_RESUME_VALUATION_RESEARCH
    else:
        gate_status = "blocked"
        next_direction = NEXT_REQUIRES_DATA_BACKFILL

    return {
        "stage": STAGE,
        "data_window": {
            "min_date": frame["date"].min().strftime("%Y-%m-%d") if not frame.empty else "",
            "max_date": frame["date"].max().strftime("%Y-%m-%d") if not frame.empty else "",
            "row_count": int(len(frame)),
            "asset_count": int(frame["asset_id"].nunique()) if not frame.empty else 0,
        },
        "thresholds": {
            "min_full_coverage_ratio": float(min_full_coverage_ratio),
            "min_field_non_null_ratio": float(min_field_non_null_ratio),
            "min_date_pass_ratio": float(min_date_pass_ratio),
        },
        "summary": {
            "target_factor_count": int(len(factor_rows)),
            "coverage_pass_count": int(coverage_pass_count),
            "repair_candidate_pre_registration_allowed_count": int(repair_allowed_count),
            "blocked_factor_count": int(blocked_count),
            "replacement_candidate_count": int(len(replacement_rows)),
            "replacement_pass_count": int(sum(int(row["replacement_pass"]) for row in replacement_rows)),
        },
        "gate": {
            "status": gate_status,
            "blockers": blockers,
            "coverage_repair_required": coverage_pass_count < len(factor_rows),
        },
        "promotion_policy": {
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "live_boundary_allowed": False,
            "final_holdout_available_for_tuning": False,
            "reason": "coverage audit can only authorize preregistered repair; repaired factors must be rescreened.",
        },
        "factor_coverage": factor_rows,
        "field_coverage": field_rows,
        "replacement_candidates": replacement_rows,
        "monthly_coverage": monthly_rows,
        "next_direction": next_direction,
    }


def build_daily_basic_valuation_coverage_audit(
    *,
    daily_basic_roots: Iterable[str | Path],
    market: str = "CN",
    target_factor_specs: Iterable[Mapping[str, Any]] | None = None,
    analysis_start_date: str | None = None,
    analysis_end_date: str | None = None,
    min_full_coverage_ratio: float = DEFAULT_MIN_FULL_COVERAGE_RATIO,
    min_field_non_null_ratio: float = DEFAULT_MIN_FIELD_NON_NULL_RATIO,
    min_date_pass_ratio: float = DEFAULT_MIN_DATE_PASS_RATIO,
) -> dict[str, Any]:
    frames = [load_factor_inputs(root, market) for root in daily_basic_roots]
    daily_basic_frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return summarize_daily_basic_valuation_coverage_audit(
        daily_basic_frame=daily_basic_frame,
        target_factor_specs=target_factor_specs,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_full_coverage_ratio=min_full_coverage_ratio,
        min_field_non_null_ratio=min_field_non_null_ratio,
        min_date_pass_ratio=min_date_pass_ratio,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value):
        return None
    return str(value)


def _csv_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in frame.columns:
        frame[column] = frame[column].map(
            lambda item: "|".join(str(value) for value in item)
            if isinstance(item, (list, tuple))
            else json.dumps(item, sort_keys=True)
            if isinstance(item, dict)
            else item
        )
    return frame


def write_daily_basic_valuation_coverage_audit(output_dir: str | Path, result: Mapping[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_valuation_coverage_audit_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    _csv_frame(list(result.get("factor_coverage", []))).to_csv(
        output_path / "daily_basic_valuation_coverage_factor_coverage.csv",
        index=False,
    )
    _csv_frame(list(result.get("field_coverage", []))).to_csv(
        output_path / "daily_basic_valuation_coverage_field_coverage.csv",
        index=False,
    )
    _csv_frame(list(result.get("replacement_candidates", []))).to_csv(
        output_path / "daily_basic_valuation_coverage_replacement_candidates.csv",
        index=False,
    )
    _csv_frame(list(result.get("monthly_coverage", []))).to_csv(
        output_path / "daily_basic_valuation_coverage_monthly_coverage.csv",
        index=False,
    )
    (output_path / "daily_basic_valuation_coverage_audit.md").write_text(
        _markdown_report(result),
        encoding="utf-8",
    )


def _markdown_report(result: Mapping[str, Any]) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Round210 Daily-Basic Valuation Coverage Audit",
        "",
        "Purpose: explain whether Round132 valuation signals were blocked by repairable field coverage gaps.",
        "",
        "## Summary",
        "",
        f"- Stage: `{result.get('stage', '')}`",
        f"- Data window: `{result.get('data_window', {}).get('min_date', '')}` to `{result.get('data_window', {}).get('max_date', '')}`",
        f"- Target factors: `{summary.get('target_factor_count', 0)}`",
        f"- Coverage pass: `{summary.get('coverage_pass_count', 0)}`",
        f"- Repair-ready for preregistration: `{summary.get('repair_candidate_pre_registration_allowed_count', 0)}`",
        f"- Blocked factors: `{summary.get('blocked_factor_count', 0)}`",
        f"- Gate status: `{gate.get('status', '')}`",
        f"- Blockers: `{', '.join(gate.get('blockers', []))}`",
        "",
        "## Policy",
        "",
        "This audit does not permit promotion or portfolio grid search. A repair-ready result only permits a separately preregistered repaired factor, followed by a fresh prescreen and walk-forward validation.",
        "",
        "## Factor Coverage",
        "",
    ]
    for row in result.get("factor_coverage", []):
        lines.extend(
            [
                f"- `{row.get('factor_name')}`: full coverage `{row.get('full_required_field_coverage_ratio'):.4f}`, date pass `{row.get('date_pass_ratio'):.4f}`, low fields `{', '.join(row.get('low_coverage_fields', [])) or 'none'}`, repair-ready `{row.get('repair_candidate_pre_registration_allowed')}`",
            ]
        )
    lines.extend(["", f"Next direction: `{result.get('next_direction', '')}`", ""])
    return "\n".join(lines)
