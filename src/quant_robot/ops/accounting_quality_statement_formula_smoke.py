from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


STAGE = "accounting_quality_statement_formula_smoke"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
SUPPORTED_SUFFIXES = {".parquet", ".csv", ".json", ".jsonl", ".ndjson"}
STATEMENT_INPUT_SEGMENT = "financial_statement_inputs"
STATEMENT_KEY_COLUMNS = ["asset_id", "end_date", "ann_date", "report_type"]

FORMULA_SPECS: list[dict[str, Any]] = [
    {
        "factor_name": "low_total_accruals_to_assets_raw",
        "formula": "(netprofit - n_cashflow_act) / total_assets",
        "economic_direction": "lower_accruals_better",
        "required_columns": ["netprofit", "n_cashflow_act", "total_assets"],
    },
    {
        "factor_name": "cashflow_minus_netprofit_to_assets_raw",
        "formula": "(n_cashflow_act - netprofit) / total_assets",
        "economic_direction": "higher_cash_conversion_better",
        "required_columns": ["netprofit", "n_cashflow_act", "total_assets"],
    },
    {
        "factor_name": "low_asset_growth_quality_raw",
        "formula": "-pct_change_4q(total_assets)",
        "economic_direction": "lower_asset_growth_better",
        "required_columns": ["asset_id", "total_assets"],
    },
    {
        "factor_name": "working_capital_accruals_to_assets_raw",
        "formula": "delta_4q(total_cur_assets - total_cur_liab) / total_assets",
        "economic_direction": "lower_working_capital_accrual_pressure_better",
        "required_columns": ["asset_id", "total_cur_assets", "total_cur_liab", "total_assets"],
    },
    {
        "factor_name": "earnings_cash_conversion_improvement_yoy_raw",
        "formula": "delta_4q((n_cashflow_act - netprofit) / total_assets)",
        "economic_direction": "improving_cash_conversion_better",
        "required_columns": ["asset_id", "netprofit", "n_cashflow_act", "total_assets"],
    },
    {
        "factor_name": "aq_abnormal_accrual_change_reversal",
        "formula": "-delta_4q((netprofit - n_cashflow_act) / total_assets)",
        "economic_direction": "abnormal_accrual_pressure_falling_better",
        "required_columns": ["asset_id", "netprofit", "n_cashflow_act", "total_assets"],
    },
    {
        "factor_name": "aq_balance_sheet_stress_relief",
        "formula": "-delta_4q(0.5 * total_liab / total_assets + 0.5 * total_cur_liab / total_assets) + (n_cashflow_act - netprofit) / total_assets",
        "economic_direction": "liability_stress_falling_with_cash_confirmation_better",
        "required_columns": [
            "asset_id",
            "netprofit",
            "n_cashflow_act",
            "total_assets",
            "total_liab",
            "total_cur_liab",
        ],
    },
    {
        "factor_name": "aq_profitability_revision_cash_confirmed",
        "formula": "delta_4q(netprofit / total_assets) + delta_4q(n_cashflow_act / total_assets)",
        "economic_direction": "profitability_acceleration_confirmed_by_operating_cashflow_better",
        "required_columns": ["asset_id", "netprofit", "n_cashflow_act", "total_assets"],
    },
    {
        "factor_name": "aq_profitability_revision_asset_disciplined",
        "formula": "delta_4q(netprofit / total_assets) - abs(pct_change_4q(total_assets))",
        "economic_direction": "profitability_acceleration_without_balance_sheet_expansion_better",
        "required_columns": ["asset_id", "netprofit", "total_assets"],
    },
]


def audit_accounting_quality_statement_formula_smoke(
    roots: Iterable[str | Path],
    *,
    deduplicate: bool = True,
) -> dict[str, Any]:
    root_paths = [Path(root) for root in roots]
    files_by_root = {str(root): _statement_files(root) for root in root_paths}
    missing_roots = [root for root, files in files_by_root.items() if not files]
    frames: list[pd.DataFrame] = []
    read_errors: list[dict[str, str]] = []
    for root, files in files_by_root.items():
        for path in files:
            try:
                frame = _read_frame(path)
                frame["source_root"] = root
                frame["source_path"] = str(path)
                frames.append(frame)
            except Exception as exc:  # pragma: no cover - defensive reporting for local corrupt artifacts
                read_errors.append({"path": str(path), "error": str(exc)})

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    combined = _prepare_statement_frame(combined)
    statement_rows_before_dedup = int(len(combined))
    duplicate_key_rows = _duplicate_key_rows(combined)
    missing_key_columns = [column for column in STATEMENT_KEY_COLUMNS if column not in combined.columns]
    statement = combined
    if deduplicate and not missing_key_columns and duplicate_key_rows:
        statement = statement.drop_duplicates(STATEMENT_KEY_COLUMNS, keep="last").reset_index(drop=True)

    formula_frame = _add_formula_values(statement)
    formula_coverage = [_formula_coverage_row(formula_frame, spec) for spec in FORMULA_SPECS]
    blockers = _blockers(
        missing_roots=missing_roots,
        read_errors=read_errors,
        missing_key_columns=missing_key_columns,
        duplicate_key_rows=duplicate_key_rows,
        deduplicate=deduplicate,
        formula_coverage=formula_coverage,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "roots": [str(root) for root in root_paths],
        "source_files": [str(path) for files in files_by_root.values() for path in files],
        "missing_roots": missing_roots,
        "read_errors": read_errors,
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "source_root_count": len(root_paths),
            "source_file_count": sum(len(files) for files in files_by_root.values()),
            "statement_rows_before_dedup": statement_rows_before_dedup,
            "statement_rows": int(len(statement)),
            "unique_symbols": _nunique(statement, "asset_id"),
            "unique_symbol_report_periods": _unique_symbol_report_periods(statement),
            "duplicate_key_rows_asset_end_ann_report_type": duplicate_key_rows,
            "deduplicated": bool(deduplicate),
            "formula_count": len(formula_coverage),
            "formulas_with_values": sum(1 for row in formula_coverage if int(row["valid_rows"]) > 0),
            "ann_date_min": _date_min(statement, "ann_date"),
            "ann_date_max": _date_max(statement, "ann_date"),
            "end_date_min": _date_min(statement, "end_date"),
            "end_date_max": _date_max(statement, "end_date"),
        },
        "formula_coverage": formula_coverage,
        "execution_policy": {
            "return_labels_used": False,
            "ic_calculated": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "final_holdout_touched": False,
            "requires_pit_signal_date_after_ann_date_before_ic": True,
            "requires_multiple_testing_log_before_promotion": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_accounting_quality_statement_formula_smoke_markdown(result)
    return result


def write_accounting_quality_statement_formula_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "accounting_quality_statement_formula_smoke.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "accounting_quality_statement_formula_smoke.md").write_text(
        render_accounting_quality_statement_formula_smoke_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("formula_coverage", [])).to_csv(
        output_path / "accounting_quality_statement_formula_coverage.csv",
        index=False,
    )


def render_accounting_quality_statement_formula_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Accounting Quality Statement Formula Smoke",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Source roots: {summary['source_root_count']}",
        f"- Source files: {summary['source_file_count']}",
        f"- Statement rows before dedup: {summary['statement_rows_before_dedup']}",
        f"- Statement rows: {summary['statement_rows']}",
        f"- Unique symbols: {summary['unique_symbols']}",
        f"- Duplicate key rows: {summary['duplicate_key_rows_asset_end_ann_report_type']}",
        f"- Deduplicated: {summary['deduplicated']}",
        f"- Announcement date range: {summary['ann_date_min']} to {summary['ann_date_max']}",
        f"- Report period range: {summary['end_date_min']} to {summary['end_date_max']}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## Formula Coverage",
        "",
    ]
    for row in result.get("formula_coverage", []) or []:
        lines.append(
            "- {name}: valid_rows={valid_rows}, coverage={coverage_pct_of_statement_rows}%, symbols={symbols}, missing={missing}".format(
                name=row["factor_name"],
                valid_rows=row["valid_rows"],
                coverage_pct_of_statement_rows=row["coverage_pct_of_statement_rows"],
                symbols=row["symbols_with_values"],
                missing="|".join(row.get("missing_columns", []) or []) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- This smoke does not use return labels.",
            "- This smoke does not calculate IC or portfolio performance.",
            "- Promotion and final holdout access remain blocked.",
        ]
    )
    return "\n".join(lines) + "\n"


def _statement_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []
    if not root.exists():
        return []
    base = root / "processed" / STATEMENT_INPUT_SEGMENT
    search_root = base if base.exists() else root
    files = [path for path in search_root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES]
    return [path for path in files if STATEMENT_INPUT_SEGMENT in str(path).replace("\\", "/")]


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"Unsupported file type: {path}")


def _prepare_statement_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in ["ann_date", "end_date", "date"]:
        if column in output:
            output[column] = pd.to_datetime(output[column], errors="coerce")
    for column in [
        "netprofit",
        "n_cashflow_act",
        "total_assets",
        "total_liab",
        "total_cur_assets",
        "total_cur_liab",
    ]:
        if column in output:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    sort_columns = [column for column in ["asset_id", "end_date", "ann_date", "report_type"] if column in output]
    if sort_columns:
        output = output.sort_values(sort_columns).reset_index(drop=True)
    return output


def _duplicate_key_rows(frame: pd.DataFrame) -> int:
    if not set(STATEMENT_KEY_COLUMNS).issubset(frame.columns):
        return 0
    return int(frame.duplicated(STATEMENT_KEY_COLUMNS).sum())


def _add_formula_values(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if {"netprofit", "n_cashflow_act", "total_assets"}.issubset(output.columns):
        denominator = output["total_assets"].replace(0, np.nan)
        output["low_total_accruals_to_assets_raw"] = (output["netprofit"] - output["n_cashflow_act"]) / denominator
        output["cashflow_minus_netprofit_to_assets_raw"] = (output["n_cashflow_act"] - output["netprofit"]) / denominator
    if {"asset_id", "total_assets"}.issubset(output.columns):
        output["low_asset_growth_quality_raw"] = -output.groupby("asset_id")["total_assets"].pct_change(4, fill_method=None)
    if {"asset_id", "total_cur_assets", "total_cur_liab", "total_assets"}.issubset(output.columns):
        working_capital = output["total_cur_assets"] - output["total_cur_liab"]
        output["working_capital_accruals_to_assets_raw"] = (
            working_capital - working_capital.groupby(output["asset_id"]).shift(4)
        ) / output["total_assets"].replace(0, np.nan)
    if {"asset_id", "netprofit", "n_cashflow_act", "total_assets"}.issubset(output.columns):
        cash_conversion = (output["n_cashflow_act"] - output["netprofit"]) / output["total_assets"].replace(0, np.nan)
        output["earnings_cash_conversion_improvement_yoy_raw"] = cash_conversion - cash_conversion.groupby(output["asset_id"]).shift(4)
        accrual_pressure = (output["netprofit"] - output["n_cashflow_act"]) / output["total_assets"].replace(0, np.nan)
        output["aq_abnormal_accrual_change_reversal"] = -(
            accrual_pressure - accrual_pressure.groupby(output["asset_id"]).shift(4)
        )
        denominator = output["total_assets"].replace(0, np.nan)
        roa = output["netprofit"] / denominator
        cash_roa = output["n_cashflow_act"] / denominator
        roa_revision = roa - roa.groupby(output["asset_id"]).shift(4)
        cash_roa_revision = cash_roa - cash_roa.groupby(output["asset_id"]).shift(4)
        output["aq_profitability_revision_cash_confirmed"] = roa_revision + cash_roa_revision
    if {"asset_id", "netprofit", "total_assets"}.issubset(output.columns):
        denominator = output["total_assets"].replace(0, np.nan)
        roa = output["netprofit"] / denominator
        roa_revision = roa - roa.groupby(output["asset_id"]).shift(4)
        asset_growth_abs = output.groupby("asset_id")["total_assets"].pct_change(4, fill_method=None).abs()
        output["aq_profitability_revision_asset_disciplined"] = roa_revision - asset_growth_abs
    if {"asset_id", "netprofit", "n_cashflow_act", "total_assets", "total_liab", "total_cur_liab"}.issubset(output.columns):
        denominator = output["total_assets"].replace(0, np.nan)
        liability_stress = 0.5 * (output["total_liab"] / denominator) + 0.5 * (output["total_cur_liab"] / denominator)
        stress_relief = -(liability_stress - liability_stress.groupby(output["asset_id"]).shift(4))
        cash_confirmation = (output["n_cashflow_act"] - output["netprofit"]) / denominator
        output["aq_balance_sheet_stress_relief"] = stress_relief + cash_confirmation
    return output


def _formula_coverage_row(frame: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    name = str(spec["factor_name"])
    missing_columns = [column for column in spec["required_columns"] if column not in frame.columns]
    if missing_columns or name not in frame.columns:
        valid = pd.Series(False, index=frame.index)
    else:
        values = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        valid = values.notna()
    valid_frame = frame.loc[valid]
    return {
        "factor_name": name,
        "formula": spec["formula"],
        "economic_direction": spec["economic_direction"],
        "required_columns": list(spec["required_columns"]),
        "missing_columns": missing_columns,
        "valid_rows": int(valid.sum()),
        "coverage_pct_of_statement_rows": round(float(valid.mean() * 100), 4) if len(frame) else 0.0,
        "symbols_with_values": _nunique(valid_frame, "asset_id"),
        "ann_date_min": _date_min(valid_frame, "ann_date"),
        "ann_date_max": _date_max(valid_frame, "ann_date"),
        "end_date_min": _date_min(valid_frame, "end_date"),
        "end_date_max": _date_max(valid_frame, "end_date"),
    }


def _blockers(
    *,
    missing_roots: list[str],
    read_errors: list[dict[str, str]],
    missing_key_columns: list[str],
    duplicate_key_rows: int,
    deduplicate: bool,
    formula_coverage: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if missing_roots:
        blockers.append("missing_statement_input_files")
    if read_errors:
        blockers.append("statement_input_read_errors")
    if missing_key_columns:
        blockers.append("missing_statement_key_columns")
    if duplicate_key_rows and not deduplicate:
        blockers.append("duplicate_statement_keys")
    formulas_with_missing_columns = [row["factor_name"] for row in formula_coverage if row.get("missing_columns")]
    if formulas_with_missing_columns:
        blockers.append("missing_required_formula_columns")
    if formula_coverage and not any(int(row["valid_rows"]) > 0 for row in formula_coverage):
        blockers.append("no_formula_values")
    return blockers


def _nunique(frame: pd.DataFrame, column: str) -> int:
    return int(frame[column].nunique()) if column in frame else 0


def _unique_symbol_report_periods(frame: pd.DataFrame) -> int:
    if not {"asset_id", "end_date"}.issubset(frame.columns):
        return 0
    return int(frame[["asset_id", "end_date"]].drop_duplicates().shape[0])


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame or frame.empty:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else str(value.date())


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame or frame.empty:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else str(value.date())


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
