from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.dataset_store import DatasetStore


DATASET = "processed/legacy_suspension"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
OUTPUT_COLUMNS = [
    "asset_id",
    "symbol",
    "provider_symbol",
    "suspend_date",
    "resume_date",
    "suspend_reason",
    "source",
    "evidence_scope",
    "ingested_at",
]


class TushareLegacySuspensionAdapter(Protocol):
    def fetch_legacy_suspension(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...


def run_tushare_legacy_suspension_ingest(
    adapter: TushareLegacySuspensionAdapter,
    unresolved_assets: pd.DataFrame,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    max_requested_assets: int = 100,
    provider_mapping_source: str | None = None,
) -> dict[str, object]:
    requested = _prepare_requests(unresolved_assets, max_requested_assets)
    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    if end < start:
        raise ValueError("legacy suspension end_date precedes start_date")

    frames = []
    response_rows = 0
    ignored: Counter[str] = Counter()
    for row in requested.itertuples(index=False):
        raw = adapter.fetch_legacy_suspension(str(row.provider_symbol), start.isoformat(), end.isoformat())
        response_rows += int(len(raw))
        normalized, response_ignored = _normalize_response(
            raw,
            asset_id=str(row.asset_id),
            symbol=str(row.symbol),
            provider_symbol=str(row.provider_symbol),
            start_date=start,
            end_date=end,
        )
        ignored.update(response_ignored)
        if not normalized.empty:
            frames.append(normalized)
    intervals = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OUTPUT_COLUMNS)
    if intervals.duplicated(["asset_id", "suspend_date", "resume_date"]).any():
        raise ValueError("duplicate legacy suspension intervals")
    intervals = intervals.sort_values(["asset_id", "suspend_date", "resume_date"], na_position="last").reset_index(drop=True)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    window = f"{start:%Y%m%d}_{end:%Y%m%d}"
    written = DatasetStore(output).write_frame(
        intervals,
        DATASET,
        {"market": "CN", "window": window},
    )
    report = {
        "stage": "tushare_legacy_suspension_ingestion",
        "status": "completed",
        "source": "tushare_suspend",
        "provider_mapping_source": provider_mapping_source,
        "evidence_scope": "data_quality_only",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "summary": {
            "requested_assets": int(len(requested)),
            "mapped_provider_symbols": int((requested["provider_symbol"] != requested["symbol"]).sum()),
            "provider_response_rows": int(response_rows),
            "interval_rows": int(len(intervals)),
            "assets_with_evidence": int(intervals["asset_id"].nunique()) if not intervals.empty else 0,
            "open_ended_intervals": int(intervals["resume_date"].isna().sum()) if not intervals.empty else 0,
            "out_of_window_rows_ignored": int(ignored["out_of_window"]),
            "intraday_rows_ignored": int(ignored["intraday"]),
        },
        "written_path": str(written),
        "live_boundary_allowed": False,
        "safety": SAFETY_TEXT,
    }
    atomic_write_json(output / "tushare_legacy_suspension_ingestion_report.json", report)
    return report


def _prepare_requests(frame: pd.DataFrame, max_requested_assets: int) -> pd.DataFrame:
    missing = [column for column in ("asset_id", "symbol") if column not in frame]
    if missing:
        raise ValueError(f"unresolved asset list missing columns: {', '.join(missing)}")
    selected = ["asset_id", "symbol"] + (["provider_symbol"] if "provider_symbol" in frame else [])
    requests = frame[selected].copy()
    if "provider_symbol" not in requests:
        requests["provider_symbol"] = requests["symbol"]
    if requests[["asset_id", "symbol"]].isna().any().any():
        raise ValueError("unresolved asset list contains missing asset_id or symbol")
    requests["asset_id"] = requests["asset_id"].astype(str).str.strip()
    requests["symbol"] = requests["symbol"].astype(str).str.strip().str.upper()
    requests["provider_symbol"] = requests["provider_symbol"].astype(str).str.strip().str.upper()
    if requests["asset_id"].duplicated().any():
        raise ValueError("unresolved asset list requires unique asset_id rows")
    if requests["symbol"].duplicated().any():
        raise ValueError("unresolved asset list requires a one-to-one symbol mapping")
    if requests["provider_symbol"].duplicated().any():
        raise ValueError("unresolved asset list requires unique provider_symbol rows")
    if len(requests) > max_requested_assets:
        raise ValueError(f"legacy suspension ingest accepts at most {max_requested_assets} assets")
    return requests.sort_values("asset_id").reset_index(drop=True)


def _normalize_response(
    raw: pd.DataFrame,
    *,
    asset_id: str,
    symbol: str,
    provider_symbol: str,
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, Counter[str]]:
    if raw.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS), Counter()
    missing = [column for column in ("ts_code", "suspend_date") if column not in raw]
    if missing:
        raise ValueError(f"legacy suspension response missing columns: {', '.join(missing)}")
    response = raw.copy()
    response["ts_code"] = response["ts_code"].astype(str).str.strip().str.upper()
    unexpected = sorted(set(response["ts_code"]) - {provider_symbol.upper()})
    if unexpected:
        raise ValueError(f"legacy suspension response contains unexpected symbols: {', '.join(unexpected)}")
    response["suspend_date"] = _parse_required_dates(response["suspend_date"], "suspend_date")
    if "resume_date" not in response:
        response["resume_date"] = pd.NaT
    response["resume_date"] = _parse_resume_dates(response["resume_date"])
    invalid_resume = response["resume_date"].notna() & (response["resume_date"] < response["suspend_date"])
    if invalid_resume.any():
        raise ValueError("legacy suspension resume_date must be after suspend_date")
    ignored: Counter[str] = Counter()
    out_of_window = (response["suspend_date"] > end_date) | (
        response["resume_date"].notna() & (response["resume_date"] <= start_date)
    )
    ignored["out_of_window"] = int(out_of_window.sum())
    response = response[~out_of_window].copy()
    intraday = response["resume_date"].notna() & (
        response["resume_date"] == response["suspend_date"]
    )
    ignored["intraday"] = int(intraday.sum())
    response = response[~intraday].copy()
    if "suspend_reason" not in response:
        response["suspend_reason"] = ""
    normalized = pd.DataFrame(
        {
            "asset_id": asset_id,
            "symbol": symbol.upper(),
            "provider_symbol": provider_symbol.upper(),
            "suspend_date": response["suspend_date"],
            "resume_date": response["resume_date"],
            "suspend_reason": response["suspend_reason"].fillna("").astype(str),
            "source": "tushare_suspend",
            "evidence_scope": "data_quality_only",
            "ingested_at": pd.Timestamp.now(tz="UTC"),
        }
    )
    if normalized.duplicated(["asset_id", "suspend_date", "resume_date"]).any():
        raise ValueError("duplicate legacy suspension intervals")
    return normalized[OUTPUT_COLUMNS], ignored


def _parse_required_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = _parse_dates(values)
    if parsed.isna().any():
        raise ValueError(f"legacy suspension response contains invalid {label}")
    return parsed


def _parse_resume_dates(values: pd.Series) -> pd.Series:
    text = values.map(lambda value: "" if pd.isna(value) else str(value).strip())
    parsed = _parse_dates(values)
    parsed.loc[text.isin({"19000101", "1900-01-01"})] = pd.NaT
    return parsed


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.map(lambda value: "" if pd.isna(value) else str(value).strip())
    digit_mask = text.str.fullmatch(r"\d{8}", na=False)
    parsed = pd.Series(pd.NaT, index=values.index, dtype="object")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(
            text.loc[digit_mask],
            format="%Y%m%d",
            errors="coerce",
        ).dt.date
    other_mask = ~digit_mask & (text != "") & (text.str.lower() != "nat")
    if other_mask.any():
        parsed.loc[other_mask] = pd.to_datetime(values.loc[other_mask], errors="coerce").dt.date
    return parsed
