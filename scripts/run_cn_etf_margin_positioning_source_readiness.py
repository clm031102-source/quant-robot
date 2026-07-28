from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.cn_trading_calendar import (  # noqa: E402
    validate_cn_trading_calendar_artifact,
)
from quant_robot.ops.cn_etf_margin_positioning_source_readiness import (  # noqa: E402
    SAFETY_BOUNDARIES,
    STAGE,
    VALUE_COLUMNS,
    build_cn_etf_margin_positioning_source_readiness,
    write_cn_etf_margin_positioning_source_readiness,
)
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_margin_positioning_source_readiness_20260728.json")
EXPECTED_ANALYSIS_DATES = {
    "start_date": "2020-01-02",
    "end_date": "2024-06-28",
    "next_session_read_end": "2024-07-05",
    "final_holdout_start": "2026-01-01",
}
EXPECTED_THRESHOLDS = {
    "minimum_assets_per_date": 50,
    "minimum_qualifying_date_coverage": 0.95,
    "minimum_positive_financing_balance_ratio": 0.95,
    "minimum_valid_nonnegative_numeric_ratio": 0.99,
}


def run_cn_etf_margin_positioning_source_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
    execute: bool = False,
    adapter: Any | None = None,
    bars: pd.DataFrame | None = None,
    trading_sessions: Sequence[str] | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    analysis = config["analysis"]
    destination = Path(output_dir or config["outputs"]["report_dir"])
    data_root = Path(data_dir or config["outputs"]["data_dir"])
    sessions = (
        list(trading_sessions)
        if trading_sessions is not None
        else _load_trading_sessions(analysis)
    )
    bar_frame = (
        bars.copy()
        if bars is not None
        else load_processed_bars(
            analysis["bar_root"],
            "CN_ETF",
            start_date=analysis["start_date"],
            end_date=analysis["end_date"],
        )
    )
    source = adapter or TushareAdapter(
        max_retries=int(config["provider"]["max_retries"]),
        retry_sleep_seconds=float(config["provider"]["retry_sleep_seconds"]),
    )
    margin, fetch_summary = _load_or_fetch_shards(
        adapter=source,
        bars=bar_frame,
        sessions=sessions,
        start_date=analysis["start_date"],
        end_date=analysis["end_date"],
        raw_root=data_root / "raw" / "tushare" / "margin_detail",
        execute=execute,
        max_workers=int(config["provider"]["max_workers"]),
    )
    canonical_files = _write_canonical_by_year(data_root, margin)
    canonical_hashes = {
        path.relative_to(data_root).as_posix(): sha256_file(path)
        for path in canonical_files
    }
    canonical_sha256 = _combined_hash(canonical_hashes)
    manifest_path = data_root / "manifest.json"
    manifest = {
        "schema_version": 1,
        "dataset": "cn_etf_margin_positioning",
        "market": "CN_ETF",
        "source": "tushare_margin_detail",
        "analysis": dict(analysis),
        "configuration_sha256": sha256_file(path),
        "rows": int(len(margin)),
        "assets": int(margin["symbol"].nunique()) if len(margin) else 0,
        "files": canonical_hashes,
        "content_sha256": canonical_sha256,
        "expected_shards": fetch_summary["expected_shards"],
    }
    atomic_write_json(manifest_path, manifest)

    result = build_cn_etf_margin_positioning_source_readiness(
        margin=margin,
        bars=bar_frame,
        trading_sessions=sessions,
        config=config,
        config_sha256=sha256_file(path),
    )
    result["configuration"].update(
        {
            "path": str(path),
            "frozen_analysis_boundary": True,
            "frozen_thresholds": True,
            "all_execution_boundaries_false": True,
        }
    )
    result["source_evidence"] = {
        "expected_shards": fetch_summary["expected_shards"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "canonical_files": canonical_hashes,
        "canonical_sha256": canonical_sha256,
    }
    report_paths = write_cn_etf_margin_positioning_source_readiness(
        destination,
        result,
    )
    paths = {"manifest": manifest_path, **report_paths}
    result["artifacts"] = {name: str(value) for name, value in paths.items()}
    result["artifact_hashes"] = {
        name: sha256_file(value)
        for name, value in sorted(paths.items())
    }
    result["runtime_cache"] = {
        "fetched_shards": fetch_summary["fetched_shards"],
        "reused_shards": fetch_summary["reused_shards"],
    }
    return result


def _load_or_fetch_shards(
    *,
    adapter: Any,
    bars: pd.DataFrame,
    sessions: Sequence[str],
    start_date: str,
    end_date: str,
    raw_root: Path,
    execute: bool,
    max_workers: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    normalized_sessions = pd.DatetimeIndex(pd.to_datetime(list(sessions))).normalize()
    normalized_sessions = normalized_sessions.drop_duplicates().sort_values()
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    source_sessions = normalized_sessions[
        (normalized_sessions >= start) & (normalized_sessions <= end)
    ]
    next_session = {
        normalized_sessions[index]: normalized_sessions[index + 1]
        for index in range(len(normalized_sessions) - 1)
    }
    if source_sessions.empty or source_sessions[-1] not in next_session:
        raise ValueError("trading sessions do not cover the source window plus next session")
    bar_map = _bar_universe_by_date(bars)
    cached: dict[pd.Timestamp, pd.DataFrame] = {}
    missing: list[pd.Timestamp] = []
    for session in source_sessions:
        shard = _raw_shard_path(raw_root, session)
        if shard.is_file():
            cached[session] = pd.read_parquet(shard)
        else:
            missing.append(session)
    if missing and not execute:
        raise FileNotFoundError(
            f"{len(missing)} margin-detail shards are missing; rerun with --execute"
        )

    fetched: dict[pd.Timestamp, pd.DataFrame] = {}

    def fetch(session: pd.Timestamp) -> tuple[pd.Timestamp, pd.DataFrame]:
        key = session.strftime("%Y%m%d")
        raw = adapter.fetch_margin_detail_by_trade_date(key)
        frame = _normalise_margin_response(
            raw,
            session=session,
            available_date=next_session[session],
            bar_assets=bar_map.get(session, {}),
        )
        shard = _raw_shard_path(raw_root, session)
        _atomic_write_parquet(shard, frame)
        return session, frame

    if missing:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch, session): session for session in missing}
            for future in as_completed(futures):
                session, frame = future.result()
                fetched[session] = frame
    frames = [
        (fetched if session in fetched else cached)[session]
        for session in source_sessions
    ]
    canonical = (
        pd.concat(frames, ignore_index=True)
        if frames
        else _empty_margin_frame()
    )
    canonical = canonical.sort_values(["date", "symbol"]).reset_index(drop=True)
    return canonical, {
        "expected_shards": int(len(source_sessions)),
        "fetched_shards": int(len(fetched)),
        "reused_shards": int(len(cached)),
    }


def _normalise_margin_response(
    raw: pd.DataFrame,
    *,
    session: pd.Timestamp,
    available_date: pd.Timestamp,
    bar_assets: Mapping[str, str],
) -> pd.DataFrame:
    required = {"ts_code", *VALUE_COLUMNS}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError("Tushare margin_detail missing columns: " + ", ".join(missing))
    frame = raw[["ts_code", *VALUE_COLUMNS]].copy()
    frame["symbol"] = frame["ts_code"].astype(str).str.upper().str.strip()
    frame = frame[frame["symbol"].isin(bar_assets)].copy()
    for column in VALUE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = session
    frame["available_date"] = available_date
    frame["asset_id"] = frame["symbol"].map(bar_assets)
    frame["market"] = "CN_ETF"
    frame["source"] = "tushare_margin_detail"
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        *VALUE_COLUMNS,
    ]
    return frame[columns].sort_values(["date", "symbol"]).reset_index(drop=True)


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"CN ETF margin-positioning config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF margin-positioning config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF margin-positioning config must be a JSON object")
    expected = {
        "schema_version": 1,
        "stage": STAGE,
        "review_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_margin_positioning",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} must be frozen as {value}")
    _require_keys(
        payload,
        ("analysis", "outputs", "provider", "thresholds", "boundaries"),
    )
    analysis = payload["analysis"]
    for key, value in EXPECTED_ANALYSIS_DATES.items():
        if analysis.get(key) != value:
            raise ValueError(f"config analysis {key} must be frozen as {value}")
    for key in ("bar_root", "trading_calendar_path", "trading_calendar_manifest_path"):
        if not isinstance(analysis.get(key), str) or not analysis[key].strip():
            raise ValueError(f"config analysis {key} must be a non-empty path")
    if payload["thresholds"] != EXPECTED_THRESHOLDS:
        raise ValueError("config thresholds do not match the frozen readiness gate")
    outputs = payload["outputs"]
    if set(outputs) != {"data_dir", "report_dir"} or not all(
        isinstance(value, str) and value.strip()
        for value in outputs.values()
    ):
        raise ValueError("config outputs must contain non-empty data_dir and report_dir")
    provider = payload["provider"]
    if provider.get("source") != "tushare_margin_detail":
        raise ValueError("config provider source must be tushare_margin_detail")
    if provider.get("fields") != "trade_date,ts_code," + ",".join(VALUE_COLUMNS):
        raise ValueError("config provider fields do not match the frozen schema")
    if not 1 <= int(provider.get("max_workers", 0)) <= 4:
        raise ValueError("config provider max_workers must be between 1 and 4")
    if not 1 <= int(provider.get("max_retries", 0)) <= 8:
        raise ValueError("config provider max_retries must be between 1 and 8")
    if not 0 <= float(provider.get("retry_sleep_seconds", -1)) <= 10:
        raise ValueError("config provider retry_sleep_seconds is outside the safe range")
    boundaries = payload["boundaries"]
    if set(boundaries) != set(SAFETY_BOUNDARIES):
        raise ValueError("config boundary keys do not match the frozen boundary contract")
    for key in SAFETY_BOUNDARIES:
        if boundaries.get(key) is not False:
            raise ValueError(f"config boundary {key} must be false")
    start = pd.Timestamp(analysis["start_date"])
    end = pd.Timestamp(analysis["end_date"])
    next_end = pd.Timestamp(analysis["next_session_read_end"])
    holdout = pd.Timestamp(analysis["final_holdout_start"])
    if not start <= end < next_end < holdout:
        raise ValueError("config analysis dates violate the sealed holdout")
    return payload


def _load_trading_sessions(analysis: Mapping[str, Any]) -> list[str]:
    calendar_path = Path(str(analysis["trading_calendar_path"]))
    manifest_path = Path(str(analysis["trading_calendar_manifest_path"]))
    validate_cn_trading_calendar_artifact(calendar_path, manifest_path)
    calendar = pd.read_csv(calendar_path)
    dates = pd.to_datetime(calendar["date"], errors="raise")
    start = pd.Timestamp(analysis["start_date"])
    next_end = pd.Timestamp(analysis["next_session_read_end"])
    sessions = (
        dates.loc[dates.between(start, next_end)]
        .drop_duplicates()
        .sort_values()
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    if not sessions or pd.Timestamp(sessions[-1]) <= pd.Timestamp(analysis["end_date"]):
        raise ValueError("validated CN trading calendar lacks a next analysis session")
    return sessions


def _bar_universe_by_date(bars: pd.DataFrame) -> dict[pd.Timestamp, dict[str, str]]:
    required = {"date", "symbol", "asset_id"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError("CN ETF bars missing columns: " + ", ".join(missing))
    frame = bars[["date", "symbol", "asset_id"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["asset_id"] = frame["asset_id"].astype(str)
    if frame.duplicated(["date", "symbol"]).any():
        raise ValueError("CN ETF bars contain duplicate date-symbol keys")
    return {
        date: dict(zip(group["symbol"], group["asset_id"], strict=True))
        for date, group in frame.groupby("date", sort=True)
    }


def _write_canonical_by_year(data_root: Path, frame: pd.DataFrame) -> list[Path]:
    dates = pd.to_datetime(frame["date"], errors="raise")
    paths: list[Path] = []
    for year, group in frame.groupby(dates.dt.year, sort=True):
        path = (
            data_root
            / "processed"
            / "margin_positioning"
            / "frequency=1d"
            / "market=CN_ETF"
            / f"year={year}"
            / "part-00000.parquet"
        )
        _atomic_write_parquet(
            path,
            group.sort_values(["date", "symbol"]).reset_index(drop=True),
        )
        paths.append(path)
    return paths


def _raw_shard_path(root: Path, session: pd.Timestamp) -> Path:
    return root / f"trade_date={session.strftime('%Y%m%d')}" / "part-00000.parquet"


def _atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def _combined_hash(files: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(files.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _empty_margin_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "available_date",
            "asset_id",
            "symbol",
            "market",
            "source",
            *VALUE_COLUMNS,
        ]
    )


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError("config missing required keys: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and audit the point-in-time CN ETF margin-positioning source."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    parser.add_argument("--data-dir")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_margin_positioning_source_readiness_cli(
        config_path=args.config,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "summary": result["summary"],
                "integrity": result["integrity"],
                "blockers": result["gate"]["blockers"],
                "source_evidence": result["source_evidence"],
                "artifacts": result["artifacts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
