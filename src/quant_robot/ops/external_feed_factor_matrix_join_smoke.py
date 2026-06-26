from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


def run_external_feed_factor_matrix_join_smoke(
    *,
    processed_root: str | Path,
    seed_config_path: str | Path,
    output_dir: str | Path,
    signal_start_date: str | None = None,
    signal_end_date: str | None = None,
    market: str = "CN",
) -> dict[str, object]:
    processed_path = Path(processed_root)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    seed_config = json.loads(Path(seed_config_path).read_text(encoding="utf-8"))
    seeds = list(seed_config.get("factor_seeds", []))

    seed_join_coverage: dict[str, dict[str, object]] = {}
    for seed in seeds:
        seed_name = str(seed["factor_name"])
        primary_feed = str(seed["primary_feed"])
        secondary_feed = str(seed.get("secondary_feed", "")).strip()
        frame = _read_processed_dataset(processed_path, primary_feed, market)
        secondary_frame = _read_processed_dataset(processed_path, secondary_feed, market) if secondary_feed else None
        coverage = _seed_join_coverage(
            seed=seed,
            frame=frame,
            secondary_frame=secondary_frame,
            signal_start_date=signal_start_date,
            signal_end_date=signal_end_date,
        )
        seed_join_coverage[seed_name] = coverage

    summary = _summary(seed_join_coverage)
    report = {
        "stage": "external_feed_factor_matrix_join_smoke",
        "processed_root": str(processed_path),
        "seed_config": str(Path(seed_config_path)),
        "market": market,
        "signal_start_date": signal_start_date,
        "signal_end_date": signal_end_date,
        "summary": summary,
        "seed_join_coverage": seed_join_coverage,
        "promotion_allowed": False,
        "promotion_blockers": [
            "join_smoke_is_not_ic_evidence",
            "no_cost_capacity_walk_forward",
            "no_redundancy_or_regime_audit",
        ],
    }
    (output_path / "external_feed_factor_matrix_join_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def _read_processed_dataset(root: Path, dataset: str, market: str) -> pd.DataFrame:
    store_root = _normalize_processed_root(root, dataset)
    store = DatasetStore(store_root)
    base = store_root / "processed" / dataset / "frequency=1d" / f"market={market}"
    frames = []
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frames.append(store.read_frame(f"processed/{dataset}", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
    if "available_date" in frame.columns:
        frame["available_date"] = pd.to_datetime(frame["available_date"]).dt.date
    return frame


def _normalize_processed_root(root: Path, dataset: str) -> Path:
    if (root / dataset).exists() and not (root / "processed" / dataset).exists():
        return root.parent
    return root


def _seed_join_coverage(
    *,
    seed: dict[str, Any],
    frame: pd.DataFrame,
    secondary_frame: pd.DataFrame | None,
    signal_start_date: str | None,
    signal_end_date: str | None,
) -> dict[str, object]:
    required = list(seed.get("required_columns", []))
    minimum_history_days = int(seed.get("minimum_history_days", 0) or 0)
    secondary_feed = str(seed.get("secondary_feed", "")).strip()
    if frame.empty:
        return _empty_seed_result("fail", required, ["processed_feed_missing_or_empty"], minimum_history_days)
    if secondary_feed and (secondary_frame is None or secondary_frame.empty):
        return {
            **_empty_seed_result("fail", required, ["secondary_feed_missing_or_empty"], minimum_history_days),
            "secondary_feed": secondary_feed,
        }
    secondary_columns = set(secondary_frame.columns) if secondary_frame is not None else set()
    primary_columns = set(frame.columns)
    missing_required = [column for column in required if column not in primary_columns and column not in secondary_columns]
    if missing_required:
        return {
            **_empty_seed_result("fail", required, [], minimum_history_days),
            "missing_required_columns": missing_required,
        }
    for column in ["date", "available_date"]:
        if column not in frame.columns:
            return {
                **_empty_seed_result("fail", required, [], minimum_history_days),
                "missing_required_columns": [column],
            }
    if secondary_feed:
        for column in ["date", "available_date"]:
            if secondary_frame is None or column not in secondary_frame.columns:
                return {
                    **_empty_seed_result("fail", required, [], minimum_history_days),
                    "secondary_feed": secondary_feed,
                    "missing_required_columns": [column],
                }

    normalized = _normalize_join_dates(frame)
    secondary_normalized = _normalize_join_dates(secondary_frame) if secondary_feed and secondary_frame is not None else None
    signal_dates = _signal_dates(normalized, signal_start_date, signal_end_date, secondary_normalized)

    joined_rows = 0
    joined_signal_dates: list[str] = []
    joined_symbols: set[str] = set()
    available_date_violations = 0
    raw_date_not_before_signal_violations = 0
    for signal_date in signal_dates:
        signal_ts = pd.Timestamp(signal_date)
        eligible = normalized[pd.to_datetime(normalized["available_date"]) <= signal_ts]
        if eligible.empty:
            continue
        latest = _latest_observations_for_signal_date(eligible)
        frames_to_check = [latest]
        if secondary_normalized is not None:
            secondary_eligible = secondary_normalized[
                pd.to_datetime(secondary_normalized["available_date"]) <= signal_ts
            ]
            if secondary_eligible.empty:
                continue
            frames_to_check.append(_latest_observations_for_signal_date(secondary_eligible))
        for joined_frame in frames_to_check:
            available_ts = pd.to_datetime(joined_frame["available_date"])
            raw_ts = pd.to_datetime(joined_frame["date"])
            available_date_violations += int((available_ts > signal_ts).sum())
            raw_date_not_before_signal_violations += int((raw_ts >= signal_ts).sum())
        joined_rows += int(len(latest))
        joined_signal_dates.append(signal_ts.date().isoformat())
        if "symbol" in latest.columns:
            joined_symbols.update(str(value) for value in latest["symbol"].dropna().unique())

    primary_observation_dates = int(pd.to_datetime(normalized["date"]).nunique())
    secondary_observation_dates = (
        int(pd.to_datetime(secondary_normalized["date"]).nunique()) if secondary_normalized is not None else None
    )
    unique_observation_dates = (
        min(primary_observation_dates, secondary_observation_dates)
        if secondary_observation_dates is not None
        else primary_observation_dates
    )
    status = "pass"
    if available_date_violations or raw_date_not_before_signal_violations:
        status = "fail"
    elif joined_rows == 0:
        status = "warn"
    elif minimum_history_days and unique_observation_dates < minimum_history_days:
        status = "insufficient_history"

    return {
        "status": status,
        "primary_feed": str(seed.get("primary_feed", "")),
        "secondary_feed": secondary_feed or None,
        "required_columns": required,
        "missing_required_columns": [],
        "columns_resolved_from_secondary_feed": [
            column for column in required if column not in primary_columns and column in secondary_columns
        ],
        "minimum_history_days": minimum_history_days,
        "unique_observation_dates": unique_observation_dates,
        "primary_unique_observation_dates": primary_observation_dates,
        "secondary_unique_observation_dates": secondary_observation_dates,
        "history_ready": bool(not minimum_history_days or unique_observation_dates >= minimum_history_days),
        "joined_rows": joined_rows,
        "joined_signal_dates": len(set(joined_signal_dates)),
        "first_signal_date": min(joined_signal_dates) if joined_signal_dates else None,
        "last_signal_date": max(joined_signal_dates) if joined_signal_dates else None,
        "unique_symbols": len(joined_symbols) if joined_symbols else None,
        "available_date_violations": available_date_violations,
        "raw_date_not_before_signal_violations": raw_date_not_before_signal_violations,
    }


def _normalize_join_dates(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date
    normalized["available_date"] = pd.to_datetime(normalized["available_date"]).dt.date
    return normalized


def _empty_seed_result(
    status: str,
    required_columns: list[str],
    warnings: list[str],
    minimum_history_days: int,
) -> dict[str, object]:
    return {
        "status": status,
        "warnings": warnings,
        "required_columns": required_columns,
        "missing_required_columns": [],
        "columns_resolved_from_secondary_feed": [],
        "minimum_history_days": minimum_history_days,
        "unique_observation_dates": 0,
        "primary_unique_observation_dates": 0,
        "secondary_unique_observation_dates": None,
        "history_ready": False,
        "joined_rows": 0,
        "joined_signal_dates": 0,
        "first_signal_date": None,
        "last_signal_date": None,
        "unique_symbols": None,
        "available_date_violations": 0,
        "raw_date_not_before_signal_violations": 0,
    }


def _signal_dates(
    frame: pd.DataFrame,
    signal_start_date: str | None,
    signal_end_date: str | None,
    secondary_frame: pd.DataFrame | None = None,
) -> list[pd.Timestamp]:
    if signal_start_date and signal_end_date:
        return [pd.Timestamp(value).normalize() for value in pd.date_range(signal_start_date, signal_end_date, freq="D")]
    available = pd.to_datetime(frame["available_date"]).dropna()
    if secondary_frame is not None and not secondary_frame.empty:
        available = pd.concat([available, pd.to_datetime(secondary_frame["available_date"]).dropna()])
    available = available.sort_values().drop_duplicates()
    return [pd.Timestamp(value).normalize() for value in available]


def _latest_observations_for_signal_date(frame: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in ["symbol", "index_symbol", "available_date", "date"] if column in frame.columns]
    sorted_frame = frame.sort_values(sort_columns)
    if "symbol" in sorted_frame.columns:
        return sorted_frame.drop_duplicates("symbol", keep="last")
    if "index_symbol" in sorted_frame.columns:
        return sorted_frame.drop_duplicates("index_symbol", keep="last")
    return sorted_frame.tail(1)


def _summary(seed_join_coverage: dict[str, dict[str, object]]) -> dict[str, int]:
    statuses = [str(value["status"]) for value in seed_join_coverage.values()]
    return {
        "seed_count": len(seed_join_coverage),
        "pass_count": statuses.count("pass"),
        "warn_count": statuses.count("warn"),
        "fail_count": statuses.count("fail"),
        "insufficient_history_count": statuses.count("insufficient_history"),
        "joined_rows": sum(int(value["joined_rows"]) for value in seed_join_coverage.values()),
        "available_date_violations": sum(int(value["available_date_violations"]) for value in seed_join_coverage.values()),
        "same_day_or_future_raw_date_violations": sum(
            int(value["raw_date_not_before_signal_violations"]) for value in seed_join_coverage.values()
        ),
    }
