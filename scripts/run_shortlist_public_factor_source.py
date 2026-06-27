from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_public_factor_source import (  # noqa: E402
    DEFAULT_BARS_ROOTS,
    build_shortlist_public_factor_source,
    write_shortlist_public_factor_source,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_public_factor_source")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize PIT public factor values for shortlist trade signal dates."
    )
    parser.add_argument("--trades", required=True)
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--candidate-factor-name", action="append", dest="factor_names")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--trade-signal-date-column", default="signal_date")
    args = parser.parse_args()

    result = build_shortlist_public_factor_source(
        trades_source=Path(args.trades),
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        factor_names=tuple(args.factor_names or ()),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        trade_signal_date_column=args.trade_signal_date_column,
    )
    output_dir = Path(args.output_dir)
    write_shortlist_public_factor_source(output_dir, result)
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "coverage_rows": result["coverage_rows"][:20],
                "factor_value_source": str(output_dir / "public_factor_values_for_shortlist.parquet"),
                "output_dir": str(output_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
