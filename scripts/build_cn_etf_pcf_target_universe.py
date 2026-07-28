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

from quant_robot.ops.cn_etf_pcf_target_universe import (  # noqa: E402
    STAGE,
    build_cn_etf_pcf_target_universe,
)
from quant_robot.storage.atomic import (  # noqa: E402
    atomic_write,
    atomic_write_json,
    atomic_write_text,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402


DEFAULT_FUND_BASIC = Path(
    "data/processed/tushare_etf_wide_history_2023_2026/metadata/"
    "tushare_fund_basic/market=E/snapshot=2026-06-21/part-00000.parquet"
)
DEFAULT_BAR_ROOT = Path(
    "data/processed/tushare_etf_wide_history_2023_2026/processed/"
    "bars/frequency=1d/market=CN_ETF"
)
DEFAULT_OUTPUT = Path("data/processed/cn_etf_pcf_target_universe_2020_2024")


def build_cn_etf_pcf_target_universe_cli(
    *,
    fund_basic_path: str | Path,
    bar_root: str | Path,
    analysis_start: str,
    analysis_end: str,
    minimum_target_etfs: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    fund_path = Path(fund_basic_path)
    fund = _read_frame(fund_path)
    bar_path = Path(bar_root)
    bar_files = _discover_files(bar_path)
    bar_frames = [
        _read_frame(path, columns=["symbol", "date"])
        for path in bar_files
    ]
    bars = pd.concat(bar_frames, ignore_index=True)
    target, result = build_cn_etf_pcf_target_universe(
        fund_basic=fund,
        bars=bars,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        minimum_target_etfs=minimum_target_etfs,
    )

    output = Path(output_dir)
    target_path = output / "target_universe.csv"
    json_path = output / f"{STAGE}.json"
    markdown_path = output / f"{STAGE}.md"
    atomic_write(
        target_path,
        lambda temporary: target.to_csv(
            temporary,
            index=False,
            date_format="%Y-%m-%d",
        ),
    )
    result["source_evidence"] = {
        "fund_basic": {
            "path": str(fund_path),
            "sha256": sha256_file(fund_path),
            "rows": int(len(fund)),
        },
        "bar_files": [
            {
                "path": str(path),
                "sha256": sha256_file(path),
            }
            for path in bar_files
        ],
    }
    result["target_artifact"] = {
        "path": str(target_path),
        "sha256": sha256_file(target_path),
        "rows": int(len(target)),
    }
    result["artifacts"] = {
        "target_universe": str(target_path),
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
    atomic_write_json(json_path, result)
    atomic_write_text(markdown_path, _render_markdown(result))
    return result


def _discover_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"bar root does not exist: {root}")
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".csv", ".parquet", ".pq"}
        ),
        key=lambda path: path.as_posix(),
    )
    if not files:
        raise FileNotFoundError(f"bar root contains no CSV/Parquet files: {root}")
    return files


def _read_frame(
    path: Path,
    *,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"source file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, dtype_backend="numpy_nullable")
        return frame if columns is None else frame.loc[:, columns]
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path, columns=columns)
    raise ValueError(f"unsupported source format: {path}")


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    integrity = result["integrity"]
    blockers = result["gate"]["blockers"]
    return "\n".join(
        [
            "# CN ETF PCF Target Universe",
            "",
            f"- Status: `{result['status']}`",
            f"- Target ETFs: {summary['target_etfs']:,}",
            f"- SSE ETFs: {summary['sse_target_etfs']:,}",
            f"- SZSE ETFs: {summary['szse_target_etfs']:,}",
            f"- Delisted target ETFs: {summary['delisted_target_etfs']:,}",
            (
                "- Missing list date with analysis-window bars: "
                f"{integrity['missing_list_date_with_bar_rows']:,}"
            ),
            f"- Blockers: {', '.join(blockers) if blockers else 'none'}",
            "- Factor generation: false",
            "- Forward-return read: false",
            "- Live boundary: false",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a survivorship-reviewed historical ETF target universe for "
            "the PCF delivery gate without generating factors or reading returns."
        )
    )
    parser.add_argument("--fund-basic", default=str(DEFAULT_FUND_BASIC))
    parser.add_argument("--bar-root", default=str(DEFAULT_BAR_ROOT))
    parser.add_argument("--analysis-start", default="2020-01-02")
    parser.add_argument("--analysis-end", default="2024-06-28")
    parser.add_argument("--minimum-target-etfs", type=int, default=30)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = build_cn_etf_pcf_target_universe_cli(
        fund_basic_path=args.fund_basic,
        bar_root=args.bar_root,
        analysis_start=args.analysis_start,
        analysis_end=args.analysis_end,
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
                "target_artifact": result["target_artifact"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
