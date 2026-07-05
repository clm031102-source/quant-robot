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
    feed_cache: dict[tuple[str, str], pd.DataFrame] = {}

    def read_feed(feed_name: str) -> pd.DataFrame:
        key = (feed_name, market)
        if key not in feed_cache:
            feed_cache[key] = _read_processed_dataset(processed_path, feed_name, market)
        return feed_cache[key]

    for seed in seeds:
        seed_name = str(seed["factor_name"])
        primary_feed = str(seed["primary_feed"])
        secondary_feed = str(seed.get("secondary_feed", "")).strip()
        frame = read_feed(primary_feed)
        secondary_frame = read_feed(secondary_feed) if secondary_feed else None
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

    joined = _latest_observations_for_signal_dates(normalized, signal_dates)
    frames_to_check = [joined]
    if secondary_normalized is not None:
        secondary_joined = _latest_observations_for_signal_dates(secondary_normalized, signal_dates)
        if joined.empty or secondary_joined.empty:
            joined = pd.DataFrame()
            frames_to_check = [joined, secondary_joined]
        else:
            secondary_signal_dates = set(pd.to_datetime(secondary_joined["_signal_date"]).dt.normalize())
            joined = joined[pd.to_datetime(joined["_signal_date"]).dt.normalize().isin(secondary_signal_dates)]
            joined_signal_date_set = set(pd.to_datetime(joined["_signal_date"]).dt.normalize())
            secondary_joined = secondary_joined[
                pd.to_datetime(secondary_joined["_signal_date"]).dt.normalize().isin(joined_signal_date_set)
            ]
            frames_to_check = [joined, secondary_joined]

    available_date_violations = 0
    raw_date_not_before_signal_violations = 0
    for joined_frame in frames_to_check:
        if joined_frame.empty:
            continue
        signal_ts = pd.to_datetime(joined_frame["_signal_date"])
        available_ts = pd.to_datetime(joined_frame["available_date"])
        raw_ts = pd.to_datetime(joined_frame["date"])
        available_date_violations += int((available_ts > signal_ts).sum())
        raw_date_not_before_signal_violations += int((raw_ts >= signal_ts).sum())
    joined_rows = int(len(joined))
    joined_signal_dates = [
        value.date().isoformat()
        for value in sorted(pd.to_datetime(joined["_signal_date"]).dropna().dt.normalize().unique())
    ]
    joined_symbols: set[str] = set()
    if "symbol" in joined.columns:
        joined_symbols.update(str(value) for value in joined["symbol"].dropna().unique())

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


def _latest_observations_for_signal_dates(frame: pd.DataFrame, signal_dates: list[pd.Timestamp]) -> pd.DataFrame:
    if frame.empty or not signal_dates:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.normalize().astype("datetime64[ns]")
    normalized["available_date"] = pd.to_datetime(normalized["available_date"]).dt.normalize().astype("datetime64[ns]")
    normalized = normalized.dropna(subset=["available_date"])
    if normalized.empty:
        return pd.DataFrame()
    signals = pd.DataFrame(
        {"_signal_date": sorted({pd.Timestamp(value).normalize() for value in signal_dates})}
    ).sort_values("_signal_date")
    signals["_signal_date"] = pd.to_datetime(signals["_signal_date"]).astype("datetime64[ns]")
    key_column = _latest_observation_key_column(normalized)
    if key_column is None:
        return _merge_latest_observations_for_group(normalized, signals)
    pieces = []
    for _, group in normalized.groupby(key_column, sort=False, dropna=False):
        latest = _merge_latest_observations_for_group(group, signals)
        if not latest.empty:
            pieces.append(latest)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def _latest_observation_key_column(frame: pd.DataFrame) -> str | None:
    if "symbol" in frame.columns:
        return "symbol"
    if "index_symbol" in frame.columns:
        return "index_symbol"
    return None


def _merge_latest_observations_for_group(group: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in ["available_date", "date"] if column in group.columns]
    sorted_group = group.sort_values(sort_columns)
    joined = pd.merge_asof(
        signals,
        sorted_group,
        left_on="_signal_date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=True,
    )
    return joined.dropna(subset=["available_date"]).reset_index(drop=True)


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
