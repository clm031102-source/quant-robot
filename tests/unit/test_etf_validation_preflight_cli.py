import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_etf_validation_preflight import run_etf_validation_preflight


class ETFValidationPreflightCliTests(unittest.TestCase):
    def test_run_etf_validation_preflight_writes_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "preflight"
            config_path = Path(tmp) / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "experiment_grid": {
                            "markets": ["CN_ETF"],
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [0],
                        },
                    }
                ),
                encoding="utf-8",
            )

            packet = run_etf_validation_preflight(
                config_path=config_path,
                source="fixture",
                output_dir=output_dir,
                min_assets=1,
                min_rebalance_opportunities_per_fold=1,
                min_median_allowed_rebalance_dates=1,
                max_zero_allowed_fold_rate=1.0,
            )

            self.assertEqual(packet["stage"], "cn_etf_validation_preflight")
            self.assertTrue((output_dir / "etf_validation_preflight.json").exists())
            self.assertTrue((output_dir / "etf_validation_preflight.md").exists())


if __name__ == "__main__":
    unittest.main()
