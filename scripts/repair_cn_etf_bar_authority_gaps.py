from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.cn_trading_calendar import (  # noqa: E402
    validate_cn_trading_calendar_artifact,
)
from quant_robot.data.ingest.tushare_pipeline import (  # noqa: E402
    run_tushare_daily_ingest,
)
from quant_robot.data.quality_report import build_quality_report  # noqa: E402
from quant_robot.storage.atomic import (  # noqa: E402
    atomic_write_json,
    atomic_write_text,
)
from quant_robot.storage.dataset_store import DatasetStore  # noqa: E402
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


STAGE = "cn_etf_bar_authority_gap_repair"
DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_wide_history_2023_2026")
DEFAULT_CALENDAR = Path(
    "data/processed/trading_calendars/cn_tushare_2015_2025/"
    "cn_trading_calendar.csv"
)
DEFAULT_CALENDAR_MANIFEST = Path(
    "data/processed/trading_calendars/cn_tushare_2015_2025/"
    "cn_trading_calendar_manifest.json"
)
DEFAULT_REPORT_DIR = Path("data/reports/cn_etf_bar_authority_gap_repair_20260728")
DEFAULT_GAP_DATES = ("2020-05-28", "2020-06-03")


def repair_cn_etf_bar_authority_gaps(
    *,
    adapter: Any,
    data_root: str | Path,
    trading_calendar_path: str | Path,
    trading_calendar_manifest_path: str | Path,
    gap_dates: tuple[str, ...] = DEFAULT_GAP_DATES,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    execute: bool = False,
) -> dict[str, Any]:
    if not gap_dates:
        raise ValueError("gap_dates must not be empty")
    normalized_gaps = tuple(
        sorted({pd.Timestamp(value).date().isoformat() for value in gap_dates})
    )
    gap_years = {pd.Timestamp(value).year for value in normalized_gaps}
    if len(gap_years) != 1:
        raise ValueError("gap_dates must belong to one calendar year")
    year = next(iter(gap_years))

    calendar_path = Path(trading_calendar_path)
    calendar_manifest_path = Path(trading_calendar_manifest_path)
    validate_cn_trading_calendar_artifact(calendar_path, calendar_manifest_path)
    calendar = pd.read_csv(calendar_path)
    calendar_dates = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    missing_from_calendar = sorted(
        set(pd.to_datetime(list(normalized_gaps))) - set(calendar_dates)
    )
    if missing_from_calendar:
        raise ValueError(
            "gap dates are absent from the validated calendar: "
            + ", ".join(pd.Timestamp(value).date().isoformat() for value in missing_from_calendar)
        )

    root = Path(data_root)
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    before = load_processed_bars(
        root,
        "CN_ETF",
        start_date=year_start,
        end_date=year_end,
    )
    before_counts = _date_counts(before, normalized_gaps)
    partition_path = _processed_partition_file(root, year)
    before_partition_sha256 = sha256_file(partition_path)
    before_quality_path = root / "quality_report.json"
    before_quality_sha256 = (
        sha256_file(before_quality_path)
        if before_quality_path.is_file()
        else None
    )

    already_repaired = all(before_counts[value] > 0 for value in normalized_gaps)
    if already_repaired or not execute:
        status = "already_repaired" if already_repaired else "ready_to_execute"
        result = _result(
            status=status,
            gap_dates=normalized_gaps,
            before_counts=before_counts,
            after_counts=before_counts,
            before_rows=len(before),
            after_rows=len(before),
            before_partition_sha256=before_partition_sha256,
            after_partition_sha256=before_partition_sha256,
            before_quality_sha256=before_quality_sha256,
            after_quality_sha256=before_quality_sha256,
            calendar_path=calendar_path,
            calendar_manifest_path=calendar_manifest_path,
            runtime={},
            source_evidence={},
        )
        _write_report(report_dir, result)
        return result

    ingest = run_tushare_daily_ingest(
        adapter,
        normalized_gaps[0],
        normalized_gaps[-1],
        root,
        resume=True,
        market="CN_ETF",
    )
    after = load_processed_bars(
        root,
        "CN_ETF",
        start_date=year_start,
        end_date=year_end,
    )
    after_counts = _date_counts(after, normalized_gaps)
    missing_after = [value for value, count in after_counts.items() if count <= 0]
    duplicate_rows = int(
        after.duplicated(["asset_id", "timestamp", "frequency"], keep=False).sum()
    )
    if missing_after or duplicate_rows:
        raise RuntimeError(
            "CN ETF bar authority repair verification failed: "
            f"missing_dates={missing_after}, duplicate_rows={duplicate_rows}"
        )

    year_sessions = (
        calendar_dates[
            calendar_dates.between(pd.Timestamp(year_start), pd.Timestamp(year_end))
        ]
        .dt.date
        .tolist()
    )
    quality = build_quality_report(after, expected_dates=year_sessions)
    quality["repair"] = {
        "stage": STAGE,
        "gap_dates": list(normalized_gaps),
        "inserted_rows_by_date": {
            value: int(after_counts[value] - before_counts[value])
            for value in normalized_gaps
        },
    }
    atomic_write_json(before_quality_path, quality)

    store = DatasetStore(root)
    raw_evidence = {}
    for value in normalized_gaps:
        key = pd.Timestamp(value).strftime("%Y%m%d")
        raw_path = store.partition_path(
            "raw/tushare/fund_daily",
            {"trade_date": key},
        )
        raw_file = _single_data_file(raw_path)
        raw_evidence[value] = {
            "path": str(raw_file),
            "sha256": sha256_file(raw_file),
            "rows": int(len(store.read_frame("raw/tushare/fund_daily", {"trade_date": key}))),
        }

    after_partition_path = _processed_partition_file(root, year)
    result = _result(
        status="repaired",
        gap_dates=normalized_gaps,
        before_counts=before_counts,
        after_counts=after_counts,
        before_rows=len(before),
        after_rows=len(after),
        before_partition_sha256=before_partition_sha256,
        after_partition_sha256=sha256_file(after_partition_path),
        before_quality_sha256=before_quality_sha256,
        after_quality_sha256=sha256_file(before_quality_path),
        calendar_path=calendar_path,
        calendar_manifest_path=calendar_manifest_path,
        runtime={
            "downloaded_trade_dates": list(ingest.get("downloaded_trade_dates", [])),
            "skipped_trade_dates": list(ingest.get("skipped_trade_dates", [])),
            "processed_window_rows": int(ingest.get("processed_rows", 0)),
        },
        source_evidence={"raw_gap_partitions": raw_evidence},
    )
    _write_report(report_dir, result)
    return result


def _result(
    *,
    status: str,
    gap_dates: tuple[str, ...],
    before_counts: dict[str, int],
    after_counts: dict[str, int],
    before_rows: int,
    after_rows: int,
    before_partition_sha256: str,
    after_partition_sha256: str,
    before_quality_sha256: str | None,
    after_quality_sha256: str | None,
    calendar_path: Path,
    calendar_manifest_path: Path,
    runtime: dict[str, Any],
    source_evidence: dict[str, Any],
) -> dict[str, Any]:
    inserted = {
        value: int(after_counts[value] - before_counts[value])
        for value in gap_dates
    }
    cleared = status in {"repaired", "already_repaired"} and all(
        after_counts[value] > 0 for value in gap_dates
    )
    return {
        "stage": STAGE,
        "status": status,
        "primary_market": "CN_ETF",
        "gap_dates": list(gap_dates),
        "rows_before": int(before_rows),
        "rows_after": int(after_rows),
        "date_rows_before": before_counts,
        "date_rows_after": after_counts,
        "inserted_rows_by_date": inserted,
        "artifacts": {
            "processed_partition_sha256_before": before_partition_sha256,
            "processed_partition_sha256_after": after_partition_sha256,
            "quality_report_sha256_before": before_quality_sha256,
            "quality_report_sha256_after": after_quality_sha256,
        },
        "calendar_evidence": {
            "path": str(calendar_path),
            "sha256": sha256_file(calendar_path),
            "manifest_path": str(calendar_manifest_path),
            "manifest_sha256": sha256_file(calendar_manifest_path),
        },
        "runtime": runtime,
        "source_evidence": source_evidence,
        "gate": {
            "cleared": cleared,
            "blockers": [] if cleared else ["cn_etf_bar_authority_gaps_unrepaired"],
        },
        "decision": {
            "bar_authority_gap_repaired": cleared,
            "factor_generation_allowed": False,
            "forward_return_read_allowed": False,
            "portfolio_grid_allowed": False,
            "final_holdout_allowed": False,
            "paper_signal_allowed": False,
            "live_boundary_allowed": False,
        },
        "next_direction": (
            "use_repaired_bar_authority_in_future_preregistered_source_gates"
            if cleared
            else "execute_bar_authority_gap_repair"
        ),
    }


def _date_counts(frame: pd.DataFrame, dates: tuple[str, ...]) -> dict[str, int]:
    values = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    return {value: int(values.eq(value).sum()) for value in dates}


def _processed_partition_file(root: Path, year: int) -> Path:
    partition = DatasetStore(root).partition_path(
        "processed/bars",
        {"frequency": "1d", "market": "CN_ETF", "year": str(year)},
    )
    return _single_data_file(partition)


def _single_data_file(partition: Path) -> Path:
    files = sorted([*partition.glob("*.parquet"), *partition.glob("*.csv")])
    if len(files) != 1:
        raise ValueError(
            f"expected one data file under {partition}, found {len(files)}"
        )
    return files[0]


def _write_report(report_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(report_dir)
    atomic_write_json(output / f"{STAGE}.json", result)
    atomic_write_text(output / f"{STAGE}.md", _render_markdown(result))


def _render_markdown(result: dict[str, Any]) -> str:
    inserted = result["inserted_rows_by_date"]
    lines = [
        "# CN ETF Bar Authority Gap Repair",
        "",
        f"- Status: `{result['status']}`",
        f"- Gate cleared: {str(result['gate']['cleared']).lower()}",
        f"- Rows before: {result['rows_before']:,}",
        f"- Rows after: {result['rows_after']:,}",
    ]
    lines.extend(
        f"- {value}: inserted {inserted[value]:,}, total {result['date_rows_after'][value]:,}"
        for value in result["gap_dates"]
    )
    lines.extend(
        [
            "- Factor generation: false",
            "- Forward-return read: false",
            "- Final holdout: sealed",
            "- Live boundary: false",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Repair the two adjudicated CN ETF bar-authority gaps from Tushare "
            "fund_daily and rebuild the full-year quality report."
        )
    )
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--trading-calendar", default=str(DEFAULT_CALENDAR))
    parser.add_argument(
        "--trading-calendar-manifest",
        default=str(DEFAULT_CALENDAR_MANIFEST),
    )
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = repair_cn_etf_bar_authority_gaps(
        adapter=TushareAdapter(max_retries=3, retry_sleep_seconds=1.0),
        data_root=args.data_root,
        trading_calendar_path=args.trading_calendar,
        trading_calendar_manifest_path=args.trading_calendar_manifest,
        report_dir=args.report_dir,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "gap_dates": result["gap_dates"],
                "date_rows_before": result["date_rows_before"],
                "date_rows_after": result["date_rows_after"],
                "inserted_rows_by_date": result["inserted_rows_by_date"],
                "gate": result["gate"],
                "artifacts": result["artifacts"],
                "runtime": result["runtime"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
