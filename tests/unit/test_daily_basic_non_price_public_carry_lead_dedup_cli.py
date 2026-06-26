import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_non_price_public_carry_lead_dedup import (
    run_daily_basic_non_price_public_carry_lead_dedup_cli,
)
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import (
    _synthetic_bars,
    _synthetic_daily_basic,
)


class DailyBasicNonPricePublicCarryLeadDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_correlation_exposure_and_residual_ic_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            prescreen = Path(tmp) / "prescreen.json"
            store = DatasetStore(root)
            store.write_frame(
                _synthetic_bars(days=90),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                _synthetic_daily_basic(days=90),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            prescreen.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "factor_name": "daily_basic_free_float_supply_quality_20",
                                "horizon": 20,
                                "research_lead": True,
                            }
                        ],
                        "summary": {"research_lead_count": 1},
                    }
                ),
                encoding="utf-8",
            )

            result = run_daily_basic_non_price_public_carry_lead_dedup_cli(
                bars_roots=[root],
                daily_basic_roots=[root],
                prescreen_report=prescreen,
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizon=20,
                sample_every_n_dates=5,
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["stage"], "daily_basic_non_price_public_carry_lead_dedup")
            self.assertTrue((output / "daily_basic_non_price_public_carry_lead_dedup.json").exists())
            self.assertTrue((output / "daily_basic_non_price_public_carry_lead_dedup.md").exists())
            self.assertTrue((output / "daily_basic_lead_reference_correlations.csv").exists())
            self.assertTrue((output / "daily_basic_lead_exposure_correlations.csv").exists())
            self.assertTrue((output / "daily_basic_lead_raw_ic_observations.csv").exists())
            self.assertTrue((output / "daily_basic_lead_residual_ic_observations.csv").exists())
            payload = json.loads(
                (output / "daily_basic_non_price_public_carry_lead_dedup.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["lead_factor_name"], "daily_basic_free_float_supply_quality_20")
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
