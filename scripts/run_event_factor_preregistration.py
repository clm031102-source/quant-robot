from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.ops.event_factor_preregistration import (  # noqa: E402
    build_event_factor_preregistration,
    probe_event_cross_section_patterns,
    probe_event_endpoints,
    write_event_factor_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/event_factor_preregistration_round146_20260622")
DEFAULT_SAMPLE_SYMBOLS = ("000001.SZ", "600519.SH", "300750.SZ", "000858.SZ", "601318.SH")
DEFAULT_ANN_DATES = ("20240105", "20240430", "20250829", "20260120")
DEFAULT_PERIODS = ("20240331", "20240630", "20240930", "20241231", "20250331")


class TushareEventEndpointAdapter:
    def __init__(self, client: object | None = None) -> None:
        self._adapter = TushareAdapter()
        self._client = client

    @property
    def client(self) -> object:
        return self._client if self._client is not None else self._adapter.client

    def fetch_event_endpoint(self, endpoint: str, **kwargs: object) -> pd.DataFrame:
        method = getattr(self.client, endpoint)
        return method(**kwargs)


def run_event_factor_preregistration(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    adapter: Any | None = None,
    sample_symbols: tuple[str, ...] = DEFAULT_SAMPLE_SYMBOLS,
    start_date: str = "2024-01-01",
    end_date: str = "2026-06-15",
    ann_dates: tuple[str, ...] = DEFAULT_ANN_DATES,
    periods: tuple[str, ...] = DEFAULT_PERIODS,
) -> dict[str, Any]:
    endpoint_adapter = adapter or TushareEventEndpointAdapter()
    endpoint_probe = probe_event_endpoints(
        endpoint_adapter,
        sample_symbols=sample_symbols,
        start_date=start_date,
        end_date=end_date,
        ann_dates=ann_dates,
        periods=periods,
    )
    cross_section_probe = probe_event_cross_section_patterns(endpoint_adapter)
    result = build_event_factor_preregistration(
        endpoint_probe_results=endpoint_probe,
        cross_section_probe_results=cross_section_probe,
    )
    write_event_factor_preregistration(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round146 CN stock event-factor preregistration and endpoint smoke.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sample-symbols", default=",".join(DEFAULT_SAMPLE_SYMBOLS))
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2026-06-15")
    parser.add_argument("--ann-dates", default=",".join(DEFAULT_ANN_DATES))
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    args = parser.parse_args()
    result = run_event_factor_preregistration(
        output_dir=args.output_dir,
        sample_symbols=tuple(_split_csv(args.sample_symbols)),
        start_date=args.start_date,
        end_date=args.end_date,
        ann_dates=tuple(_split_csv(args.ann_dates)),
        periods=tuple(_split_csv(args.periods)),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


if __name__ == "__main__":
    main()
