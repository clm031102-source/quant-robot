from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.ingest.tushare_forecast_express_events import (  # noqa: E402
    run_tushare_forecast_express_event_cache,
)


class TushareEventEndpointAdapter:
    def __init__(self, adapter: TushareAdapter | None = None) -> None:
        self._adapter = adapter or TushareAdapter()

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        return self._adapter.fetch_trade_calendar(start_date, end_date)

    def fetch_event_endpoint(self, endpoint: str, **kwargs: object):
        method = getattr(self._adapter.client, endpoint)
        return method(**kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cache or audit Tushare forecast/express event endpoints.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", default="data/reports/tushare_forecast_express_event_cache")
    parser.add_argument("--processed-output-dir")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--endpoints", default="forecast,express")
    parser.add_argument("--progress-jsonl")
    parser.add_argument(
        "--execute-write-processed",
        action="store_true",
        help="Write processed event cache datasets. Default is report-only.",
    )
    args = parser.parse_args(argv)
    progress_callback = None
    if args.progress_jsonl:
        progress_path = Path(args.progress_jsonl)
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("", encoding="utf-8")

        def progress_callback(event: dict[str, object]) -> None:
            with progress_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")

    result = run_tushare_forecast_express_event_cache(
        TushareEventEndpointAdapter(),
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        processed_output_dir=Path(args.processed_output_dir) if args.processed_output_dir else None,
        execute_write_processed=args.execute_write_processed,
        market=args.market,
        endpoints=tuple(_split_csv(args.endpoints)),
        progress_callback=progress_callback,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
