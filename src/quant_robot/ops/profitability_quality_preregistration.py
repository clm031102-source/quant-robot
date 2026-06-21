from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


STAGE = "profitability_quality_factor_preregistration"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_BASE_COLUMNS = ("asset_id", "symbol", "market", "source", "ann_date", "end_date")


@dataclass(frozen=True)
class ProfitabilityQualityCandidateSpec:
    name: str
    category: str
    expression: str
    required_columns: tuple[str, ...]
    economic_rationale: str
    direction: str = "higher_is_better"
    min_history_quarters: int = 1
    min_row_coverage: float = 0.85


def default_profitability_quality_candidate_specs() -> list[ProfitabilityQualityCandidateSpec]:
    return [
        ProfitabilityQualityCandidateSpec(
            name="fina_roe_level",
            category="profitability_level",
            expression="roe",
            required_columns=("roe",),
            economic_rationale="Higher return on equity indicates stronger shareholder capital efficiency.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_roa_level",
            category="profitability_level",
            expression="roa",
            required_columns=("roa",),
            economic_rationale="Higher return on assets captures operating efficiency with less leverage dependence than ROE.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_net_margin_level",
            category="profitability_level",
            expression="netprofit_margin",
            required_columns=("netprofit_margin",),
            economic_rationale="Higher net margin indicates stronger retained economics after costs and taxes.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_gross_margin_level",
            category="profitability_level",
            expression="grossprofit_margin",
            required_columns=("grossprofit_margin",),
            economic_rationale="Higher gross margin can proxy pricing power and product competitiveness.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_netprofit_yoy_growth",
            category="growth_quality",
            expression="netprofit_yoy",
            required_columns=("netprofit_yoy",),
            economic_rationale="Higher profit growth can indicate improving earnings power when not purely cyclical.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_revenue_yoy_growth",
            category="growth_quality",
            expression="or_yoy",
            required_columns=("or_yoy",),
            economic_rationale="Higher operating revenue growth captures business expansion before margin effects.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_profit_growth_quality_spread",
            category="growth_quality",
            expression="netprofit_yoy - or_yoy",
            required_columns=("netprofit_yoy", "or_yoy"),
            economic_rationale="Profit growth above revenue growth can indicate operating leverage or margin improvement.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_cash_earnings_quality_ratio",
            category="cash_profit_quality",
            expression="ocfps / abs(cfps)",
            required_columns=("ocfps", "cfps"),
            economic_rationale="Operating cash flow relative to cash flow per share helps screen accrual-heavy earnings.",
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_profitability_quality_blend",
            category="composite_quality",
            expression="cs_zscore(roe) + cs_zscore(roa) + cs_zscore(netprofit_margin) + cs_zscore(grossprofit_margin)",
            required_columns=("roe", "roa", "netprofit_margin", "grossprofit_margin"),
            economic_rationale="A blended profitability score reduces dependence on a single accounting ratio.",
            min_row_coverage=0.8,
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_growth_quality_blend",
            category="composite_quality",
            expression="cs_zscore(netprofit_yoy) + cs_zscore(or_yoy) + cs_zscore(ocfps)",
            required_columns=("netprofit_yoy", "or_yoy", "ocfps"),
            economic_rationale="A blended growth-quality score combines profit growth, revenue growth, and cash flow support.",
            min_row_coverage=0.8,
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_roe_persistence_4q",
            category="profitability_stability",
            expression="ts_mean(roe, 4) - ts_std(roe, 4)",
            required_columns=("roe",),
            economic_rationale="Persistent high ROE is more robust than a single high quarter.",
            min_history_quarters=4,
            min_row_coverage=0.5,
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_roa_persistence_4q",
            category="profitability_stability",
            expression="ts_mean(roa, 4) - ts_std(roa, 4)",
            required_columns=("roa",),
            economic_rationale="Persistent high ROA favors durable asset efficiency over one-off leverage effects.",
            min_history_quarters=4,
            min_row_coverage=0.5,
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_net_margin_improvement_yoy",
            category="margin_change",
            expression="netprofit_margin - lag(netprofit_margin, 4)",
            required_columns=("netprofit_margin",),
            economic_rationale="Year-over-year margin improvement can capture improving cost control or pricing power.",
            min_history_quarters=5,
            min_row_coverage=0.45,
        ),
        ProfitabilityQualityCandidateSpec(
            name="fina_ocfps_improvement_yoy",
            category="cash_profit_quality",
            expression="ocfps - lag(ocfps, 4)",
            required_columns=("ocfps",),
            economic_rationale="Year-over-year operating cash-flow improvement helps separate real cash generation from accrual profit.",
            min_history_quarters=5,
            min_row_coverage=0.45,
        ),
    ]


def build_profitability_quality_preregistration(
    *,
    input_root: str | Path,
    min_assets: int = 50,
    min_passed_candidates: int = 8,
    candidate_specs: Iterable[ProfitabilityQualityCandidateSpec] | None = None,
) -> dict[str, Any]:
    input_path = Path(input_root)
    frame = _load_fina_indicator_inputs(input_path)
    quality = _dataset_quality(frame)
    specs = list(candidate_specs or default_profitability_quality_candidate_specs())
    candidates = [_candidate_payload(spec, frame, min_assets=min_assets) for spec in specs]
    coverage_passed = [candidate for candidate in candidates if candidate["coverage"]["passes"]]
    blockers = list(quality["blockers"])
    if len(coverage_passed) < min_passed_candidates:
        blockers.append("insufficient_coverage_passed_candidates")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "input_root": str(input_path),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "coverage_passed_candidates": len(coverage_passed),
            "coverage_failed_candidates": len(candidates) - len(coverage_passed),
            "min_assets": min_assets,
            "min_passed_candidates": min_passed_candidates,
            "rows": quality["rows"],
            "assets": quality["assets"],
        },
        "dataset_quality": quality,
        "candidates": candidates,
        "promotion_policy": {
            "promotion_allowed": False,
            "backtest_allowed_from_single_shard": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_multiple_testing_accounting": True,
            "next_allowed_action": "Use coverage-passed definitions for a controlled factor-matrix smoke, not promotion.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_profitability_quality_preregistration_markdown(result)
    return result


def write_profitability_quality_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "profitability_quality_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_quality_preregistration.md").write_text(
        render_profitability_quality_preregistration_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(_candidate_csv_rows(result)).to_csv(
        output_path / "profitability_quality_candidate_coverage.csv",
        index=False,
    )


def render_profitability_quality_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    quality = result.get("dataset_quality", {})
    lines = [
        "# Profitability Quality Factor Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Input root: `{result.get('input_root', '')}`",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Assets: {summary.get('assets', 0)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Coverage passed: {summary.get('coverage_passed_candidates', 0)}",
        f"- Coverage failed: {summary.get('coverage_failed_candidates', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Dataset Quality",
        "",
        f"- Duplicate financial keys: {quality.get('duplicate_rows', 0)}",
        f"- Missing asset id rows: {quality.get('missing_asset_id_rows', 0)}",
        f"- Announcement before report-period rows: {quality.get('ann_date_before_report_period_rows', 0)}",
        f"- Ann date range: {quality.get('ann_date_start')} to {quality.get('ann_date_end')}",
        f"- Report period range: {quality.get('report_period_start')} to {quality.get('report_period_end')}",
        "",
        "## Candidates",
        "",
        "| Name | Category | Status | Coverage | Assets | Required Columns |",
        "|---|---|---|---:|---:|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        coverage = candidate["coverage"]
        lines.append(
            "| {name} | {category} | {status} | {coverage:.2%} | {assets} | `{columns}` |".format(
                name=candidate["name"],
                category=candidate["category"],
                status=candidate["registration_status"],
                coverage=float(coverage.get("row_coverage", 0.0)),
                assets=coverage.get("eligible_assets", 0),
                columns="`, `".join(candidate.get("required_columns", []) or []),
            )
        )
    return "\n".join(lines) + "\n"


def _load_fina_indicator_inputs(input_root: Path) -> pd.DataFrame:
    dataset_root = input_root / "processed" / "fina_indicator_inputs"
    if not dataset_root.exists():
        dataset_root = input_root
    files = _dataset_files(dataset_root)
    if not files:
        return pd.DataFrame()
    frames = [_read_frame(path) for path in files]
    frame = pd.concat(frames, ignore_index=True)
    for column in ("date", "ann_date", "end_date"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame.sort_values([column for column in ("asset_id", "end_date", "ann_date") if column in frame.columns]).reset_index(drop=True)


def _dataset_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() in {".parquet", ".csv"}:
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".parquet", ".csv"})


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _dataset_quality(frame: pd.DataFrame) -> dict[str, Any]:
    blockers: list[str] = []
    missing_columns = [column for column in REQUIRED_BASE_COLUMNS if column not in frame.columns]
    if frame.empty:
        blockers.append("missing_processed_fina_indicator_inputs")
    if missing_columns:
        blockers.append("missing_required_base_columns")
    if frame.empty or missing_columns:
        return {
            "passes": False,
            "blockers": blockers,
            "rows": int(len(frame)),
            "assets": 0,
            "missing_required_base_columns": missing_columns,
            "duplicate_rows": 0,
            "missing_asset_id_rows": 0,
            "ann_date_before_report_period_rows": 0,
            "ann_date_start": None,
            "ann_date_end": None,
            "report_period_start": None,
            "report_period_end": None,
        }
    duplicate_rows = int(frame.duplicated(["asset_id", "ann_date", "end_date", "source"]).sum())
    missing_asset_id_rows = int(frame["asset_id"].isna().sum())
    ann_dates = pd.to_datetime(frame["ann_date"], errors="coerce")
    end_dates = pd.to_datetime(frame["end_date"], errors="coerce")
    ann_before_report = int((ann_dates < end_dates).sum())
    missing_pit_rows = int((ann_dates.isna() | end_dates.isna()).sum())
    if duplicate_rows:
        blockers.append("duplicate_financial_keys")
    if missing_asset_id_rows:
        blockers.append("missing_asset_id_rows")
    if ann_before_report:
        blockers.append("ann_date_before_report_period")
    if missing_pit_rows:
        blockers.append("missing_pit_date_rows")
    return {
        "passes": not blockers,
        "blockers": blockers,
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique(dropna=True)),
        "missing_required_base_columns": missing_columns,
        "duplicate_rows": duplicate_rows,
        "missing_asset_id_rows": missing_asset_id_rows,
        "ann_date_before_report_period_rows": ann_before_report,
        "missing_pit_date_rows": missing_pit_rows,
        "ann_date_start": ann_dates.min().date().isoformat() if not ann_dates.dropna().empty else None,
        "ann_date_end": ann_dates.max().date().isoformat() if not ann_dates.dropna().empty else None,
        "report_period_start": end_dates.min().date().isoformat() if not end_dates.dropna().empty else None,
        "report_period_end": end_dates.max().date().isoformat() if not end_dates.dropna().empty else None,
    }


def _candidate_payload(
    spec: ProfitabilityQualityCandidateSpec,
    frame: pd.DataFrame,
    *,
    min_assets: int,
) -> dict[str, Any]:
    coverage = _candidate_coverage(spec, frame, min_assets=min_assets)
    return {
        "name": spec.name,
        "category": spec.category,
        "expression": spec.expression,
        "direction": spec.direction,
        "required_columns": list(spec.required_columns),
        "min_history_quarters": spec.min_history_quarters,
        "economic_rationale": spec.economic_rationale,
        "registration_status": "pre_registered" if coverage["passes"] else "blocked_by_coverage",
        "coverage": coverage,
        "lookahead_policy": "Use ann_date as factor availability date; do not use report-period values before announcement.",
    }


def _candidate_coverage(
    spec: ProfitabilityQualityCandidateSpec,
    frame: pd.DataFrame,
    *,
    min_assets: int,
) -> dict[str, Any]:
    missing_columns = [column for column in spec.required_columns if column not in frame.columns]
    if frame.empty or missing_columns or "asset_id" not in frame.columns:
        blockers = []
        if frame.empty:
            blockers.append("missing_input_rows")
        if missing_columns:
            blockers.append("missing_required_columns")
        return {
            "passes": False,
            "blockers": blockers,
            "missing_required_columns": missing_columns,
            "eligible_rows": 0,
            "total_rows": int(len(frame)),
            "row_coverage": 0.0,
            "eligible_assets": 0,
            "eligible_report_periods": 0,
            "min_row_coverage": spec.min_row_coverage,
            "min_assets": min_assets,
        }
    required_mask = frame[list(spec.required_columns)].notna().all(axis=1)
    valid_history_count = required_mask.astype(int).groupby(frame["asset_id"]).cumsum()
    eligible_mask = required_mask & (valid_history_count >= spec.min_history_quarters)
    eligible_rows = int(eligible_mask.sum())
    total_rows = int(len(frame))
    row_coverage = eligible_rows / total_rows if total_rows else 0.0
    eligible_assets = int(frame.loc[eligible_mask, "asset_id"].nunique(dropna=True))
    eligible_periods = int(frame.loc[eligible_mask, "end_date"].nunique(dropna=True)) if "end_date" in frame.columns else 0
    blockers: list[str] = []
    if row_coverage < spec.min_row_coverage:
        blockers.append("row_coverage_below_threshold")
    if eligible_assets < min_assets:
        blockers.append("eligible_assets_below_threshold")
    if spec.min_history_quarters > 1 and eligible_periods < spec.min_history_quarters:
        blockers.append("history_periods_below_threshold")
    return {
        "passes": not blockers,
        "blockers": blockers,
        "missing_required_columns": [],
        "eligible_rows": eligible_rows,
        "total_rows": total_rows,
        "row_coverage": row_coverage,
        "eligible_assets": eligible_assets,
        "eligible_report_periods": eligible_periods,
        "min_row_coverage": spec.min_row_coverage,
        "min_assets": min_assets,
    }


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        coverage = candidate["coverage"]
        rows.append(
            {
                "name": candidate["name"],
                "category": candidate["category"],
                "registration_status": candidate["registration_status"],
                "row_coverage": coverage.get("row_coverage"),
                "eligible_rows": coverage.get("eligible_rows"),
                "total_rows": coverage.get("total_rows"),
                "eligible_assets": coverage.get("eligible_assets"),
                "eligible_report_periods": coverage.get("eligible_report_periods"),
                "required_columns": ",".join(candidate.get("required_columns", []) or []),
                "blockers": ",".join(coverage.get("blockers", []) or []),
            }
        )
    return rows


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
