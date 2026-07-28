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

from quant_robot.data.cn_trading_calendar import (  # noqa: E402
    validate_cn_trading_calendar_artifact,
)
from quant_robot.ops.cn_etf_pcf_delivery import (  # noqa: E402
    READINESS_STAGE,
    audit_cn_etf_pcf_history,
    normalize_cn_etf_pcf_delivery,
    normalize_cn_etf_pcf_target_universe,
)
from quant_robot.storage.atomic import (  # noqa: E402
    atomic_write,
    atomic_write_json,
    atomic_write_text,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402


def run_cn_etf_pcf_source_readiness_cli(
    *,
    sse_input: str | Path,
    szse_input: str | Path,
    target_universe_path: str | Path,
    trading_calendar_path: str | Path,
    trading_calendar_manifest_path: str | Path,
    source_provider: str,
    analysis_start: str,
    analysis_end: str,
    final_holdout_start: str,
    minimum_target_etfs: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    calendar_path = Path(trading_calendar_path)
    calendar_manifest_path = Path(trading_calendar_manifest_path)
    validate_cn_trading_calendar_artifact(calendar_path, calendar_manifest_path)
    calendar = pd.read_csv(calendar_path)
    trading_sessions = (
        pd.to_datetime(calendar["date"], errors="raise")
        .drop_duplicates()
        .sort_values()
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )

    canonical_frames: list[pd.DataFrame] = []
    pcf_files: list[dict[str, Any]] = []
    for exchange, root in (("SSE", Path(sse_input)), ("SZSE", Path(szse_input))):
        for path in _discover_delivery_files(root):
            raw = _read_frame(path)
            normalized = normalize_cn_etf_pcf_delivery(
                raw,
                market_exchange=exchange,
                source_provider=source_provider,
                source_file=_source_label(root, path),
            )
            canonical_frames.append(normalized)
            pcf_files.append(
                {
                    "exchange": exchange,
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "rows": int(len(raw)),
                    "normalized_rows": int(len(normalized)),
                }
            )
    canonical = pd.concat(canonical_frames, ignore_index=True)

    target_path = Path(target_universe_path)
    target_raw = _read_frame(target_path)
    targets = normalize_cn_etf_pcf_target_universe(target_raw)
    result = audit_cn_etf_pcf_history(
        canonical,
        target_universe=targets,
        trading_sessions=trading_sessions,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        final_holdout_start=final_holdout_start,
        minimum_target_etfs=minimum_target_etfs,
    )
    result["source_evidence"] = {
        "provider": str(source_provider),
        "pcf_files": pcf_files,
        "target_universe": {
            "path": str(target_path),
            "sha256": sha256_file(target_path),
            "input_rows": int(len(target_raw)),
            "normalized_etfs": int(len(targets)),
        },
        "trading_calendar": {
            "path": str(calendar_path),
            "sha256": sha256_file(calendar_path),
            "manifest_path": str(calendar_manifest_path),
            "manifest_sha256": sha256_file(calendar_manifest_path),
        },
    }

    output = Path(output_dir)
    artifacts = {
        "json": output / f"{READINESS_STAGE}.json",
        "markdown": output / f"{READINESS_STAGE}.md",
        "date_coverage": output / "date_coverage.csv",
        "etf_coverage": output / "etf_coverage.csv",
        "exchange_coverage": output / "exchange_coverage.csv",
    }
    result["artifacts"] = {
        name: str(path) for name, path in artifacts.items()
    }
    atomic_write_json(artifacts["json"], result)
    atomic_write_text(artifacts["markdown"], _render_markdown(result))
    _write_csv(artifacts["date_coverage"], result["date_coverage"])
    _write_csv(artifacts["etf_coverage"], result["etf_coverage"])
    _write_csv(artifacts["exchange_coverage"], result["exchange_coverage"])
    return result


def _discover_delivery_files(root: Path) -> list[Path]:
    if root.is_file():
        if root.suffix.lower() not in {".csv", ".parquet", ".pq"}:
            raise ValueError(f"unsupported PCF delivery format: {root}")
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"PCF delivery input does not exist: {root}")
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".csv", ".parquet", ".pq"}
        ),
        key=lambda path: path.as_posix(),
    )
    if not files:
        raise FileNotFoundError(f"PCF delivery input contains no CSV/Parquet files: {root}")
    return files


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype_backend="numpy_nullable")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"unsupported PCF delivery format: {path}")


def _source_label(root: Path, path: Path) -> str:
    if root.is_dir():
        return path.relative_to(root).as_posix()
    return path.name


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write(
        path,
        lambda temporary: pd.DataFrame(rows).to_csv(temporary, index=False),
    )


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    blockers = result["gate"]["blockers"]
    return "\n".join(
        [
            "# CN ETF PCF Source Readiness",
            "",
            f"- Status: `{result['status']}`",
            f"- PCF rows: {summary['pcf_rows']:,}",
            f"- Target ETFs: {summary['target_etfs']:,}",
            f"- Analysis sessions: {summary['analysis_sessions']:,}",
            f"- Expected ETF-sessions: {summary['expected_etf_sessions']:,}",
            f"- Observed ETF-sessions: {summary['observed_etf_sessions']:,}",
            f"- Missing ETF-sessions: {summary['missing_etf_sessions']:,}",
            f"- Coverage ratio: {summary['coverage_ratio']:.6f}",
            f"- Blockers: {', '.join(blockers) if blockers else 'none'}",
            "- Factor generation: false",
            "- Forward-return read: false",
            "- Final holdout: sealed",
            "- Live boundary: false",
            "",
            "A cleared result authorizes preregistration only. It does not authorize "
            "factor generation, return reads, portfolio tests, paper signals, or live use.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a fingerprinted cross-exchange historical CN ETF PCF delivery "
            "without writing canonical market data or generating factors."
        )
    )
    parser.add_argument("--sse-input", required=True)
    parser.add_argument("--szse-input", required=True)
    parser.add_argument(
        "--target-universe",
        default=(
            "data/processed/cn_etf_pcf_target_universe_2020_2024/"
            "target_universe.csv"
        ),
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument(
        "--trading-calendar",
        default=(
            "data/processed/trading_calendars/cn_tushare_2015_2025/"
            "cn_trading_calendar.csv"
        ),
    )
    parser.add_argument(
        "--trading-calendar-manifest",
        default=(
            "data/processed/trading_calendars/cn_tushare_2015_2025/"
            "cn_trading_calendar_manifest.json"
        ),
    )
    parser.add_argument("--analysis-start", default="2020-01-02")
    parser.add_argument("--analysis-end", default="2024-06-28")
    parser.add_argument("--final-holdout-start", default="2026-01-01")
    parser.add_argument("--minimum-target-etfs", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        default="data/reports/cn_etf_pcf_source_readiness",
    )
    args = parser.parse_args()
    result = run_cn_etf_pcf_source_readiness_cli(
        sse_input=args.sse_input,
        szse_input=args.szse_input,
        target_universe_path=args.target_universe,
        trading_calendar_path=args.trading_calendar,
        trading_calendar_manifest_path=args.trading_calendar_manifest,
        source_provider=args.provider,
        analysis_start=args.analysis_start,
        analysis_end=args.analysis_end,
        final_holdout_start=args.final_holdout_start,
        minimum_target_etfs=args.minimum_target_etfs,
        output_dir=args.output_dir,
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
