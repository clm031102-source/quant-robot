from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


STAGE = "round270_financial_reporting_timeliness_source_audit"
NEXT_CANDIDATE_PLAN = "round270_financial_reporting_timeliness_candidate_plan_gate"
NEXT_BACKFILL = "round270_financial_reporting_timeliness_backfill_or_retire_before_factor_generation"

REQUIRED_FIELDS = ("symbol", "ann_date", "end_date")


def summarize_financial_reporting_timeliness_source_audit(
    *,
    financial_frames: Mapping[str, pd.DataFrame],
    analysis_start_date: str,
    analysis_end_date: str,
    min_unique_symbols: int = 1000,
    min_end_years: int = 8,
) -> dict[str, Any]:
    profiles = [
        _profile_source(
            source_name,
            frame,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            min_unique_symbols=min_unique_symbols,
            min_end_years=min_end_years,
        )
        for source_name, frame in sorted(financial_frames.items())
    ]
    year_rows = [row for profile in profiles for row in profile.pop("year_coverage")]
    source_ready_count = sum(1 for profile in profiles if profile["source_ready"])
    blockers = _dedupe(blocker for profile in profiles for blocker in profile["blockers"])
    if not profiles:
        blockers = ["no_financial_reporting_sources_provided"]
    status = "source_ready" if source_ready_count > 0 else "blocked"
    return {
        "stage": STAGE,
        "status": status,
        "analysis_window": {
            "start": analysis_start_date,
            "end": analysis_end_date,
            "final_holdout_included": False,
        },
        "summary": {
            "source_count": int(len(profiles)),
            "source_ready_count": int(source_ready_count),
            "row_count": int(sum(profile["row_count"] for profile in profiles)),
            "unique_symbols": int(max((profile["unique_symbols"] for profile in profiles), default=0)),
            "min_unique_symbols": int(min_unique_symbols),
            "min_end_years": int(min_end_years),
        },
        "source_profiles": profiles,
        "year_coverage": year_rows,
        "gate": {
            "blockers": blockers,
            "source_gate_cleared": status == "source_ready",
        },
        "candidate_plan_allowed": status == "source_ready",
        "promotion_policy": {
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "reason": "This stage audits source coverage only; candidates still require preregistration and PIT prescreen.",
        },
        "next_direction": NEXT_CANDIDATE_PLAN if status == "source_ready" else NEXT_BACKFILL,
    }


def build_financial_reporting_timeliness_source_audit(
    *,
    financial_roots: Iterable[str | Path],
    analysis_start_date: str,
    analysis_end_date: str,
    min_unique_symbols: int = 1000,
    min_end_years: int = 8,
) -> dict[str, Any]:
    frames = load_financial_reporting_timeliness_frames(financial_roots)
    return summarize_financial_reporting_timeliness_source_audit(
        financial_frames=frames,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_unique_symbols=min_unique_symbols,
        min_end_years=min_end_years,
    )


def load_financial_reporting_timeliness_frames(financial_roots: Iterable[str | Path]) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for root_value in financial_roots:
        root = Path(root_value)
        if not root.exists():
            frames[str(root)] = pd.DataFrame()
            continue
        pieces = []
        for path in sorted(root.rglob("*.parquet")):
            try:
                frame = pd.read_parquet(path)
            except Exception:
                continue
            if not frame.empty:
                pieces.append(frame)
        frames[root.name or str(root)] = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    return frames


def write_financial_reporting_timeliness_source_audit(output_dir: str | Path, result: Mapping[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "financial_reporting_timeliness_source_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_reporting_timeliness_source_audit.md").write_text(
        render_financial_reporting_timeliness_source_audit_markdown(sanitized),
        encoding="utf-8",
    )
    _write_csv(output_path / "financial_reporting_timeliness_source_profiles.csv", sanitized["source_profiles"])
    _write_csv(output_path / "financial_reporting_timeliness_year_coverage.csv", sanitized["year_coverage"])


def render_financial_reporting_timeliness_source_audit_markdown(result: Mapping[str, Any]) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Financial Reporting Timeliness Source Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'blocked')}",
        f"- Sources: {summary.get('source_count', 0)}",
        f"- Source-ready count: {summary.get('source_ready_count', 0)}",
        f"- Rows: {summary.get('row_count', 0)}",
        f"- Max unique symbols: {summary.get('unique_symbols', 0)}",
        f"- Candidate plan allowed: {str(result.get('candidate_plan_allowed', False)).lower()}",
        f"- Next direction: {result.get('next_direction', NEXT_BACKFILL)}",
        f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
        "",
        "## Source Profiles",
        "",
        "| Source | Rows | Symbols | End years | Ann date range | End date range | Ready | Blockers |",
        "|---|---:|---:|---:|---|---|---|---|",
    ]
    for profile in result.get("source_profiles", []):
        lines.append(
            "| {source} | {rows} | {symbols} | {years} | {ann_min}..{ann_max} | {end_min}..{end_max} | {ready} | {blockers} |".format(
                source=profile.get("source", ""),
                rows=profile.get("row_count", 0),
                symbols=profile.get("unique_symbols", 0),
                years=profile.get("end_year_count", 0),
                ann_min=profile.get("min_ann_date") or "none",
                ann_max=profile.get("max_ann_date") or "none",
                end_min=profile.get("min_end_date") or "none",
                end_max=profile.get("max_end_date") or "none",
                ready="yes" if profile.get("source_ready") else "no",
                blockers=", ".join(profile.get("blockers", [])) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _profile_source(
    source_name: str,
    frame: pd.DataFrame,
    *,
    analysis_start_date: str,
    analysis_end_date: str,
    min_unique_symbols: int,
    min_end_years: int,
) -> dict[str, Any]:
    prepared = _prepare_frame(frame, analysis_start_date=analysis_start_date, analysis_end_date=analysis_end_date)
    missing_fields = [field for field in REQUIRED_FIELDS if field not in prepared]
    blockers: list[str] = []
    if prepared.empty:
        blockers.append("no_rows_after_window")
    if missing_fields:
        blockers.append("missing_required_fields")
    unique_symbols = int(prepared["symbol"].nunique()) if "symbol" in prepared else 0
    if unique_symbols < min_unique_symbols:
        blockers.append("unique_symbol_count_below_minimum")
    end_year_count = int(prepared["end_date"].dt.year.nunique()) if "end_date" in prepared and not prepared.empty else 0
    if end_year_count < min_end_years:
        blockers.append("end_year_coverage_below_minimum")
    year_coverage = _year_coverage(source_name, prepared)
    return {
        "source": str(source_name),
        "row_count": int(len(prepared)),
        "unique_symbols": unique_symbols,
        "end_year_count": end_year_count,
        "min_ann_date": _min_date(prepared, "ann_date"),
        "max_ann_date": _max_date(prepared, "ann_date"),
        "min_end_date": _min_date(prepared, "end_date"),
        "max_end_date": _max_date(prepared, "end_date"),
        "required_fields_present": not missing_fields,
        "missing_fields": missing_fields,
        "source_ready": not blockers,
        "blockers": _dedupe(blockers),
        "year_coverage": year_coverage,
    }


def _prepare_frame(frame: pd.DataFrame, *, analysis_start_date: str, analysis_end_date: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    if "symbol" not in output and "ts_code" in output:
        output["symbol"] = output["ts_code"]
    for column in ("ann_date", "end_date"):
        if column in output:
            output[column] = pd.to_datetime(output[column], errors="coerce")
    if "end_date" in output:
        output = output[
            (output["end_date"] >= pd.Timestamp(analysis_start_date))
            & (output["end_date"] <= pd.Timestamp(analysis_end_date))
        ]
    return output.reset_index(drop=True)


def _year_coverage(source_name: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty or "end_date" not in frame:
        return []
    rows = []
    for year, group in frame.groupby(frame["end_date"].dt.year, sort=True):
        rows.append(
            {
                "source": str(source_name),
                "end_year": int(year),
                "row_count": int(len(group)),
                "unique_symbols": int(group["symbol"].nunique()) if "symbol" in group else 0,
                "ann_date_min": _min_date(group, "ann_date"),
                "ann_date_max": _max_date(group, "ann_date"),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return None if values.empty else pd.Timestamp(values.min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return None if values.empty else pd.Timestamp(values.max()).date().isoformat()


def _dedupe(items: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen = set()
    for item in items:
        text = str(item)
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value
