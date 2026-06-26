from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


FINANCIAL_DATASET_HINTS = ("fina", "financial", "indicator", "income", "balancesheet", "cashflow", "profit")
PIT_DATE_COLUMNS = ("ann_date", "f_ann_date", "end_date", "report_date")
PROFITABILITY_COLUMNS = (
    "roe",
    "roa",
    "grossprofit_margin",
    "netprofit_margin",
    "netprofit_yoy",
    "or_yoy",
    "ocfps",
    "cfps",
)
SUPPORTED_SUFFIXES = {".parquet", ".csv", ".json", ".jsonl", ".ndjson"}
STAGE = "tushare_financial_pit_readiness"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def audit_tushare_financial_pit_readiness(
    roots: Iterable[str | Path],
    *,
    required_column_groups: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    root_paths = [Path(root) for root in roots]
    normalised_required_groups = _normalise_required_column_groups(required_column_groups)
    datasets = [_audit_file(path, root) for root in root_paths for path in _candidate_files(root)]
    financial_like = [row for row in datasets if row["financial_like"]]
    pit_ready = [row for row in financial_like if row["pit_status"] == "pass"]
    profitability_ready = [row for row in pit_ready if row["profitability_columns"]]
    group_rows = _required_column_group_rows(pit_ready, normalised_required_groups)
    blockers: list[str] = []
    if not financial_like:
        blockers.append("missing_financial_statement_or_indicator_dataset")
    if financial_like and not any(row["pit_date_columns"] for row in financial_like):
        blockers.append("missing_pit_date_columns")
    if financial_like and not normalised_required_groups and not any(row["profitability_columns"] for row in financial_like):
        blockers.append("missing_profitability_columns")
    if financial_like and normalised_required_groups and not pit_ready:
        blockers.append("no_pit_ready_financial_dataset")
    if financial_like and not normalised_required_groups and not profitability_ready:
        blockers.append("no_pit_ready_profitability_dataset")
    for row in group_rows:
        if not row["passes"]:
            blockers.append(f"missing_required_financial_column_group:{row['group_id']}")
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "roots": [str(root) for root in root_paths],
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "files_scanned": len(datasets),
            "financial_like_datasets": len(financial_like),
            "pit_ready_datasets": len(pit_ready),
            "required_column_group_count": len(group_rows),
            "required_column_groups_passing": sum(1 for row in group_rows if row["passes"]),
        },
        "datasets": financial_like,
        "required_column_groups": group_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_tushare_financial_pit_readiness_markdown(result)
    return result


def write_tushare_financial_pit_readiness(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "tushare_financial_pit_readiness.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_financial_pit_readiness.md").write_text(
        render_tushare_financial_pit_readiness_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("datasets", [])).to_csv(output_path / "tushare_financial_pit_readiness_datasets.csv", index=False)


def render_tushare_financial_pit_readiness_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    lines = [
        "# Tushare Financial PIT Readiness",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {bool(summary.get('passes', False))}",
        f"- Files scanned: {summary.get('files_scanned', 0)}",
        f"- Financial-like datasets: {summary.get('financial_like_datasets', 0)}",
        f"- PIT-ready datasets: {summary.get('pit_ready_datasets', 0)}",
        f"- Blockers: {', '.join(str(item) for item in summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Roots",
        "",
    ]
    for root in result.get("roots", []) or []:
        lines.append(f"- `{root}`")
    lines.extend(["", "## Financial-Like Datasets", ""])
    rows = result.get("datasets", []) or []
    if not rows:
        lines.append("- none")
    for row in rows:
        lines.append(
            "- {path}: pit={pit}, pit_cols={pit_cols}, profitability_cols={profit_cols}, rows={rows}".format(
                path=row.get("path"),
                pit=row.get("pit_status"),
                pit_cols="|".join(row.get("pit_date_columns", []) or []),
                profit_cols="|".join(row.get("profitability_columns", []) or []),
                rows=row.get("rows"),
            )
        )
    groups = result.get("required_column_groups", []) or []
    if groups:
        lines.extend(["", "## Required Column Groups", ""])
        for row in groups:
            lines.append(
                "- {group}: passes={passes}, required={required}, missing={missing}, matching={matching}".format(
                    group=row.get("group_id"),
                    passes=row.get("passes"),
                    required="|".join(row.get("required_columns", []) or []),
                    missing="|".join(row.get("missing_columns", []) or []) or "none",
                    matching=len(row.get("matching_dataset_paths", []) or []),
                )
            )
    return "\n".join(lines) + "\n"


def _candidate_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES]


def _audit_file(path: Path, root: Path) -> dict[str, Any]:
    financial_like = not _is_non_dataset_report(path) and any(
        hint in _financial_haystack(path, root) for hint in FINANCIAL_DATASET_HINTS
    )
    columns: list[str] = []
    rows: int | None = None
    error: str | None = None
    if financial_like:
        try:
            frame = _read_frame(path)
            columns = [str(column) for column in frame.columns]
            rows = int(len(frame))
        except Exception as exc:  # pragma: no cover - defensive reporting for corrupt local artifacts
            error = str(exc)
    pit_columns = [column for column in PIT_DATE_COLUMNS if column in columns]
    profitability_columns = [column for column in PROFITABILITY_COLUMNS if column in columns]
    pit_status = "pass" if pit_columns and error is None else "block"
    return {
        "path": str(path),
        "root": str(root),
        "financial_like": financial_like,
        "columns": columns,
        "pit_date_columns": pit_columns,
        "profitability_columns": profitability_columns,
        "pit_status": pit_status,
        "rows": rows,
        "error": error,
    }


def _required_column_group_rows(
    pit_ready_datasets: list[dict[str, Any]],
    required_column_groups: Mapping[str, Iterable[str]] | None,
) -> list[dict[str, Any]]:
    groups = _normalise_required_column_groups(required_column_groups)
    rows: list[dict[str, Any]] = []
    available_columns = {
        column
        for dataset in pit_ready_datasets
        for column in dataset.get("columns", []) or []
    }
    for group_id, required_columns in groups.items():
        required = list(required_columns)
        matching = [
            dataset
            for dataset in pit_ready_datasets
            if set(required).issubset(set(dataset.get("columns", []) or []))
        ]
        missing = [column for column in required if column not in available_columns]
        rows.append(
            {
                "group_id": group_id,
                "required_columns": required,
                "passes": bool(matching),
                "missing_columns": [] if matching else missing,
                "matching_dataset_paths": [str(dataset.get("path", "")) for dataset in matching],
            }
        )
    return rows


def _normalise_required_column_groups(
    required_column_groups: Mapping[str, Iterable[str]] | None,
) -> dict[str, list[str]]:
    if not required_column_groups:
        return {}
    output: dict[str, list[str]] = {}
    for group_id, columns in required_column_groups.items():
        clean_group = str(group_id).strip()
        clean_columns = [str(column).strip() for column in columns if str(column).strip()]
        if clean_group and clean_columns:
            output[clean_group] = clean_columns
    return output


def _financial_haystack(path: Path, root: Path) -> str:
    if root.is_file():
        return path.name.lower()
    try:
        return str(path.relative_to(root)).lower()
    except ValueError:
        return path.name.lower()


def _is_non_dataset_report(path: Path) -> bool:
    name = path.name.lower()
    return name == "manifest.json" or name.endswith("_quality_report.json")


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
