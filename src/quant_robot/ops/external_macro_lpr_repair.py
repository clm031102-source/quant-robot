from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


STAGE = "external_macro_lpr_repair"
MACRO_DATASET = "external_macro_rates"
OTHER_EXTERNAL_FEED_DATASETS = [
    "external_margin_detail",
    "external_hk_hold",
    "external_hsgt_flow",
    "external_index_state",
]
LPR_MIN_PLAUSIBLE_RATE = 0.0
LPR_MAX_PLAUSIBLE_RATE = 20.0


def repair_external_macro_lpr(
    *,
    processed_root: str | Path,
    lpr_cache_path: str | Path,
    output_root: str | Path,
    report_dir: str | Path,
    market: str = "CN",
    copy_other_feeds: bool = False,
) -> dict[str, Any]:
    market = market.upper()
    source_root = _normalize_processed_root(Path(processed_root), MACRO_DATASET)
    output_path = Path(output_root)
    source_resolved = source_root.resolve()
    output_resolved = output_path.resolve()
    if output_resolved == source_resolved or output_resolved.is_relative_to(source_resolved):
        raise ValueError("output_root must be outside the source processed root")
    if output_path.exists() and any(output_path.iterdir()):
        raise FileExistsError(f"output_root must be empty or absent: {output_path}")

    macro_by_year = _read_dataset_by_year(source_root, MACRO_DATASET, market)
    if not macro_by_year:
        raise ValueError("external_macro_rates processed feed is missing or empty")
    lpr = _read_lpr_cache(Path(lpr_cache_path))
    repaired_by_year = {
        year: _repair_macro_frame(frame, lpr)
        for year, frame in macro_by_year.items()
    }

    output_store = DatasetStore(output_path)
    for year, frame in repaired_by_year.items():
        output_store.write_frame(
            frame,
            f"processed/{MACRO_DATASET}",
            {"frequency": "1d", "market": market, "year": str(year)},
        )

    copied_datasets: list[str] = []
    if copy_other_feeds:
        for dataset in OTHER_EXTERNAL_FEED_DATASETS:
            frames_by_year = _read_dataset_by_year(source_root, dataset, market)
            if not frames_by_year:
                continue
            for year, frame in frames_by_year.items():
                output_store.write_frame(
                    frame,
                    f"processed/{dataset}",
                    {"frequency": "1d", "market": market, "year": str(year)},
                )
            copied_datasets.append(dataset)

    before = pd.concat(list(macro_by_year.values()), ignore_index=True)
    after = pd.concat(list(repaired_by_year.values()), ignore_index=True)
    blockers = []
    if int(after["lpr_1y"].notna().sum()) == 0 or int(after["lpr_5y"].notna().sum()) == 0:
        blockers.append("lpr_repair_produced_zero_non_null_rows")
    report = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "blocked" if blockers else "pass",
        "market": market,
        "processed_root": str(Path(processed_root)),
        "normalized_source_root": str(source_root),
        "lpr_cache_path": str(Path(lpr_cache_path)),
        "output_root": str(output_path),
        "copy_other_feeds": bool(copy_other_feeds),
        "copied_datasets": copied_datasets,
        "summary": {
            "macro_years": sorted(str(year) for year in repaired_by_year),
            "macro_rows": int(len(after)),
            "lpr_cache_rows": int(len(lpr)),
            "lpr_1y_non_null_before": int(before["lpr_1y"].notna().sum()) if "lpr_1y" in before else 0,
            "lpr_5y_non_null_before": int(before["lpr_5y"].notna().sum()) if "lpr_5y" in before else 0,
            "lpr_1y_non_null_after": int(after["lpr_1y"].notna().sum()),
            "lpr_5y_non_null_after": int(after["lpr_5y"].notna().sum()),
        },
        "blockers": blockers,
        "promotion_allowed": False,
        "promotion_blockers": [
            "lpr_repair_is_source_data_maintenance_not_alpha_evidence",
            "coverage_audit_required_before_lpr_factor_use",
            "no_ic_portfolio_or_promotion_gate_from_repair_report",
        ],
    }
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    (report_path / "external_macro_lpr_repair_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (report_path / "external_macro_lpr_repair_report.md").write_text(
        render_external_macro_lpr_repair_markdown(report),
        encoding="utf-8",
    )
    return report


def render_external_macro_lpr_repair_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# External Macro LPR Repair Report",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Status: {report.get('status', '')}",
        f"- Market: {report.get('market', '')}",
        f"- Source root: {report.get('normalized_source_root', '')}",
        f"- Output root: {report.get('output_root', '')}",
        f"- LPR cache: {report.get('lpr_cache_path', '')}",
        f"- Macro rows: {summary.get('macro_rows', 0)}",
        f"- LPR 1Y non-null before/after: {summary.get('lpr_1y_non_null_before', 0)} / {summary.get('lpr_1y_non_null_after', 0)}",
        f"- LPR 5Y non-null before/after: {summary.get('lpr_5y_non_null_before', 0)} / {summary.get('lpr_5y_non_null_after', 0)}",
        f"- Copied other feeds: {', '.join(report.get('copied_datasets', [])) or 'none'}",
        f"- Promotion allowed: {report.get('promotion_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blockers", [])
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _repair_macro_frame(frame: pd.DataFrame, lpr: pd.DataFrame) -> pd.DataFrame:
    macro = frame.copy()
    macro["_repair_date"] = pd.to_datetime(macro["date"]).dt.normalize().astype("datetime64[ns]")
    lpr_sorted = lpr.copy()
    lpr_sorted["_lpr_date"] = pd.to_datetime(lpr_sorted["date"]).dt.normalize().astype("datetime64[ns]")
    lpr_sorted["repair_lpr_1y"] = pd.to_numeric(lpr_sorted["lpr_1y"], errors="coerce")
    lpr_sorted["repair_lpr_5y"] = pd.to_numeric(lpr_sorted["lpr_5y"], errors="coerce")
    lpr_sorted = lpr_sorted.dropna(subset=["_lpr_date", "repair_lpr_1y", "repair_lpr_5y"]).sort_values("_lpr_date")
    merged = pd.merge_asof(
        macro.sort_values("_repair_date"),
        lpr_sorted[["_lpr_date", "repair_lpr_1y", "repair_lpr_5y"]],
        left_on="_repair_date",
        right_on="_lpr_date",
        direction="backward",
    )
    merged["lpr_1y"] = merged["repair_lpr_1y"]
    merged["lpr_5y"] = merged["repair_lpr_5y"]
    drop_columns = [column for column in ["_repair_date", "_lpr_date", "repair_lpr_1y", "repair_lpr_5y"] if column in merged]
    return merged.drop(columns=drop_columns).reset_index(drop=True)


def _read_lpr_cache(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"LPR cache file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(payload.get("rows", []))
    required = {"date", "lpr_1y", "lpr_5y"}
    if frame.empty or not required.issubset(frame.columns):
        raise ValueError("LPR cache must contain non-empty rows with date, lpr_1y, and lpr_5y")
    usable = frame.copy()
    usable["date"] = pd.to_datetime(usable["date"], errors="coerce")
    usable["lpr_1y"] = pd.to_numeric(usable["lpr_1y"], errors="coerce")
    usable["lpr_5y"] = pd.to_numeric(usable["lpr_5y"], errors="coerce")
    usable = usable[
        usable["date"].notna()
        & usable["lpr_1y"].between(LPR_MIN_PLAUSIBLE_RATE, LPR_MAX_PLAUSIBLE_RATE, inclusive="neither")
        & usable["lpr_5y"].between(LPR_MIN_PLAUSIBLE_RATE, LPR_MAX_PLAUSIBLE_RATE, inclusive="neither")
    ].reset_index(drop=True)
    if usable.empty:
        raise ValueError("LPR cache has no rows with numeric plausible lpr_1y and lpr_5y")
    return usable


def _read_dataset_by_year(root: Path, dataset: str, market: str) -> dict[str, pd.DataFrame]:
    store = DatasetStore(root)
    base = root / "processed" / dataset / "frequency=1d" / f"market={market}"
    frames: dict[str, pd.DataFrame] = {}
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frames[year] = store.read_frame(f"processed/{dataset}", {"frequency": "1d", "market": market, "year": year})
    return frames


def _normalize_processed_root(root: Path, dataset: str) -> Path:
    if (root / dataset).exists() and not (root / "processed" / dataset).exists():
        return root.parent
    return root
