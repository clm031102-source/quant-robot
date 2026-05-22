from __future__ import annotations

import argparse
from pathlib import Path

from quant_robot.data.adapters.tradingview_csv_adapter import parse_tradingview_csv


def import_tradingview_csv(input_path: Path | str, output_path: Path | str) -> Path:
    parsed = parse_tradingview_csv(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    parsed.to_csv(output, index=False)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manually exported TradingView CSV data.")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    import_tradingview_csv(args.input, args.output)


if __name__ == "__main__":
    main()
