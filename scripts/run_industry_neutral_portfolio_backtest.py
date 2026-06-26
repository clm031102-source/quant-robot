from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars  # noqa: E402
from quant_robot.experiments.runner import (  # noqa: E402
    _filter_bars_for_asset_universe,
    _pipeline_config,
    _precompute_factor_matrix,
    build_experiment_cases,
    load_experiment_grid_config,
)
from quant_robot.research.pipeline import (  # noqa: E402
    prepare_research_pipeline_inputs,
    research_input_fingerprint,
    run_research_pipeline,
)
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/industry_neutral_portfolio_backtest")


def run_industry_neutral_portfolio_backtest(
    *,
    config_path: str | Path,
    stock_basic: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    source: str = "authority-processed-bars",
    data_root: str | Path = "data/processed",
    authority_bars_config: str | Path | None = "configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json",
    progress: Any | None = None,
) -> dict[str, Any]:
    config = load_experiment_grid_config(config_path)
    bars = _load_bars(
        source,
        Path(data_root),
        config.markets,
        authority_bars_config=Path(authority_bars_config) if authority_bars_config else None,
    )
    bars = _filter_bars_for_asset_universe(bars, config)
    _emit(progress, "precompute_start", factor_source=config.factor_source, factors=list(config.factor_names))
    factors = _precompute_factor_matrix(bars, config)
    if factors is None or factors.empty:
        raise ValueError(f"Grid config produced no factor matrix: {config_path}")
    factors = _attach_industry(factors, _load_frame(Path(stock_basic)))
    _emit(progress, "precompute_done", factor_rows=len(factors))

    prepared_by_key = {}
    rows = []
    cases = build_experiment_cases(config)
    for index, case in enumerate(cases, start=1):
        _emit(progress, "case_start", case_id=case.case_id, case_index=index, case_count=len(cases))
        pipeline_config = replace(
            _pipeline_config(config, case, output_dir=None),
            selection_method="industry_neutral_top_n",
        )
        cache_key = research_input_fingerprint(pipeline_config)
        if cache_key not in prepared_by_key:
            prepared_by_key[cache_key] = prepare_research_pipeline_inputs(
                bars,
                pipeline_config,
                precomputed_factors=factors,
            )
        result = run_research_pipeline(
            bars,
            pipeline_config,
            precomputed_factors=factors,
            prepared_inputs=prepared_by_key[cache_key],
        )
        row = _leaderboard_row(case, result)
        rows.append(row)
        _emit(progress, "case_done", case_id=case.case_id, decision_status=row["decision_status"], trades=row["trades"])

    leaderboard = _rank_rows(rows)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary = _summary(leaderboard)
    result = {
        "stage": "industry_neutral_portfolio_backtest",
        "config_path": str(config_path),
        "selection_method": "industry_neutral_top_n",
        "summary": summary,
        "leaderboard": leaderboard,
        "live_boundary_allowed": False,
        "safety": "Research-to-review only. No broker connection, no account reads, no order placement, no live trading.",
    }
    pd.DataFrame(leaderboard).to_csv(output_path / "leaderboard.csv", index=False)
    (output_path / "summary.json").write_text(json.dumps(_sanitize(summary), indent=2, sort_keys=True), encoding="utf-8")
    (output_path / "industry_neutral_portfolio_backtest.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "industry_neutral_portfolio_backtest.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run industry-neutral TopN portfolio backtests from an experiment grid.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="authority-processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
    args = parser.parse_args()
    result = run_industry_neutral_portfolio_backtest(
        config_path=Path(args.config),
        stock_basic=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        source=args.source,
        data_root=Path(args.data_root),
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        progress=_stderr_progress,
    )
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:10]}, indent=2, sort_keys=True))


def _attach_industry(factors: pd.DataFrame, stock_basic: pd.DataFrame) -> pd.DataFrame:
    metadata = stock_basic.copy()
    if "asset_id" not in metadata.columns and "ts_code" in metadata.columns:
        metadata["asset_id"] = metadata["ts_code"]
    if "asset_id" not in metadata.columns or "industry" not in metadata.columns:
        raise ValueError("stock_basic must include asset_id/ts_code and industry columns")
    metadata = metadata[["asset_id", "industry"]].dropna(subset=["asset_id", "industry"])
    metadata["asset_id"] = metadata["asset_id"].astype(str)
    metadata["industry"] = metadata["industry"].astype(str)
    metadata = metadata.drop_duplicates(subset=["asset_id"], keep="last")
    return factors.merge(metadata, on="asset_id", how="left")


def _leaderboard_row(case: Any, result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics", {})
    benchmark = result.get("benchmark_metrics", {})
    decision = result.get("decision", {})
    factor_summary = result.get("factor_summary", {})
    artifacts = result.get("artifact_rows", {})
    return _sanitize(
        {
            "case_id": f"{case.case_id}_industry_neutral",
            "base_case_id": case.case_id,
            "market": case.market,
            "factor_source": case.factor_source,
            "factor_name": case.factor_name,
            "selection_method": "industry_neutral_top_n",
            "top_n": case.top_n,
            "cost_bps": case.cost_bps,
            "rebalance_interval": case.rebalance_interval,
            "regime_lookback": case.regime_lookback,
            "decision_status": decision.get("decision_status", "unknown"),
            "decision_reasons": list(decision.get("rejection_reasons", []) or []),
            "trades": int(artifacts.get("trades", 0)),
            "holdings": int(artifacts.get("holdings", 0)),
            "total_return": metrics.get("total_return", 0.0),
            "annualized_return": metrics.get("annualized_return", 0.0),
            "sharpe": metrics.get("sharpe", 0.0),
            "overlap_autocorr_adjusted_sharpe": metrics.get("overlap_autocorr_adjusted_sharpe", 0.0),
            "max_drawdown": metrics.get("max_drawdown", 0.0),
            "win_rate": metrics.get("win_rate", 0.0),
            "turnover": metrics.get("turnover", 0.0),
            "average_holdings": metrics.get("average_holdings", 0.0),
            "avg_participation_rate": metrics.get("avg_participation_rate", 0.0),
            "max_participation_rate": metrics.get("max_participation_rate", 0.0),
            "capacity_limited_trades": metrics.get("capacity_limited_trades", 0),
            "relative_return": benchmark.get("relative_return", 0.0),
            "benchmark_total_return": benchmark.get("benchmark_total_return", 0.0),
            "mean_rank_ic": factor_summary.get("mean_rank_ic", 0.0),
            "rank_ic_t_stat": factor_summary.get("rank_ic_t_stat", 0.0),
            "tail_mean_rank_ic": factor_summary.get("tail_mean_rank_ic", 0.0),
            "tail_rank_ic_t_stat": factor_summary.get("tail_rank_ic_t_stat", 0.0),
        }
    )


def _rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            str(row.get("decision_status")) != "approved",
            -_number(row.get("overlap_autocorr_adjusted_sharpe")),
            -_number(row.get("total_return")),
            str(row.get("case_id")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(rows),
        "approved": sum(1 for row in rows if row.get("decision_status") == "approved"),
        "rejected": sum(1 for row in rows if row.get("decision_status") == "rejected"),
        "capacity_limited_cases": sum(1 for row in rows if int(_number(row.get("capacity_limited_trades"))) > 0),
        "best_total_return": max((_number(row.get("total_return")) for row in rows), default=0.0),
        "best_overlap_autocorr_adjusted_sharpe": max(
            (_number(row.get("overlap_autocorr_adjusted_sharpe")) for row in rows),
            default=0.0,
        ),
        "best_relative_return": max((_number(row.get("relative_return")) for row in rows), default=0.0),
    }


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Industry-Neutral Portfolio Backtest",
        "",
        f"- Config: {result.get('config_path')}",
        f"- Selection method: {result.get('selection_method')}",
        f"- Cases: {summary.get('cases')}",
        f"- Approved: {summary.get('approved')}",
        f"- Rejected: {summary.get('rejected')}",
        f"- Capacity-limited cases: {summary.get('capacity_limited_cases')}",
        f"- Best total return: {_number(summary.get('best_total_return')):.4f}",
        f"- Best overlap-adjusted Sharpe: {_number(summary.get('best_overlap_autocorr_adjusted_sharpe')):.4f}",
        f"- Best relative return: {_number(summary.get('best_relative_return')):.4f}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety')}",
        "",
        "## Top Cases",
        "",
    ]
    for row in result.get("leaderboard", [])[:20]:
        lines.append(
            "- {case}: status={status}, total={total:.4f}, relative={relative:.4f}, sharpe={sharpe:.4f}, "
            "overlap={overlap:.4f}, dd={dd:.4f}, win={win:.4f}, cap_limited={cap}".format(
                case=row.get("case_id"),
                status=row.get("decision_status"),
                total=_number(row.get("total_return")),
                relative=_number(row.get("relative_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                win=_number(row.get("win_rate")),
                cap=int(_number(row.get("capacity_limited_trades"))),
            )
        )
    return "\n".join(lines) + "\n"


def _load_bars(
    source: str,
    data_root: Path,
    markets: tuple[str, ...],
    *,
    authority_bars_config: Path | None,
) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source == "authority-processed-bars":
        if authority_bars_config is None:
            raise ValueError("authority_bars_config is required for authority-processed-bars source")
        return load_authority_processed_bars_from_config(authority_bars_config, markets=markets)
    if source != "processed-bars":
        raise ValueError(f"Unsupported source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([*path.rglob("*.parquet"), *path.rglob("*.csv"), *path.rglob("*.json"), *path.rglob("*.jsonl")])
        if not files:
            raise FileNotFoundError(f"No tabular files found under {path}")
        return pd.concat([_load_frame(file) for file in files], ignore_index=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ("rows", "data", "stock_basic"):
                value = data.get(key)
                if isinstance(value, list):
                    return pd.DataFrame(value)
        raise ValueError(f"JSON file does not contain a supported row list: {path}")
    raise ValueError(f"Unsupported frame file type: {path}")


def _stderr_progress(event: dict[str, Any]) -> None:
    print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)


def _emit(progress: Any | None, event: str, **fields: Any) -> None:
    if progress is not None:
        progress({"event": event, **fields})


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if pd.notna(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
