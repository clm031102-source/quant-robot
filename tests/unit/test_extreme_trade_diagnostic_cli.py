import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_extreme_trade_diagnostic import run_extreme_trade_diagnostic_from_config


class ExtremeTradeDiagnosticCliTests(unittest.TestCase):
    def test_cli_runner_writes_lightweight_diagnostic_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            output_dir = root / "diagnostic"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_source": "daily_basic_value_liquidity_tail",
                        "factor_names": ["value_low_turnover_low_tail_20"],
                        "factor_windows": [20],
                        "factor_input_root": "daily-basic-root",
                        "factor_input_required": True,
                        "top_n_values": [100],
                        "cost_bps_values": [10],
                        "forward_horizon": 20,
                        "execution_lag": 1,
                        "rebalance_intervals": [5],
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.run_extreme_trade_diagnostic._load_bars", return_value=_bars()) as load_bars,
                patch("scripts.run_extreme_trade_diagnostic.run_research_pipeline", return_value={"trades": _trades()}) as pipeline,
            ):
                diagnostic = run_extreme_trade_diagnostic_from_config(
                    config_path=config_path,
                    factor_name="value_low_turnover_low_tail_20",
                    source="fixture",
                    data_root=Path("data/processed"),
                    output_dir=output_dir,
                    threshold=5.0,
                )

            self.assertEqual(diagnostic["summary"]["extreme_trades"], 1)
            load_bars.assert_called_once()
            passed_config = pipeline.call_args.args[1]
            self.assertEqual(passed_config.factor_source, "daily_basic_value_liquidity_tail")
            self.assertEqual(passed_config.factor_name, "value_low_turnover_low_tail_20")
            self.assertEqual(passed_config.top_n, 100)
            self.assertEqual(passed_config.cost_bps, 10.0)
            self.assertTrue((output_dir / "extreme_trade_diagnostic.json").exists())
            self.assertTrue((output_dir / "extreme_trade_diagnostic.csv").exists())
            self.assertTrue((output_dir / "extreme_trade_diagnostic.md").exists())


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_date": pd.Timestamp("2024-01-01").date(),
                "entry_date": pd.Timestamp("2024-01-02").date(),
                "exit_date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "market": "CN",
                "factor_name": "value_low_turnover_low_tail_20",
                "gross_return": 6.0,
                "target_weight": 0.01,
            }
        ]
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-02").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 10.0,
                "source": "fixture",
            },
            {
                "date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 70.0,
                "source": "fixture",
            },
        ]
    )


if __name__ == "__main__":
    unittest.main()
