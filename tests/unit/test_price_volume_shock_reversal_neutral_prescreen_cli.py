import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_price_volume_shock_reversal_neutral_prescreen import (
    run_price_volume_shock_reversal_neutral_prescreen_cli,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_public_reference_multi_family_prescreen import _synthetic_public_reference_bars


class PriceVolumeShockReversalNeutralPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_outputs_from_preregistration_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _synthetic_public_reference_bars(days=90, assets=36)
            store = DatasetStore(root)
            for year in sorted(pd.to_datetime(bars["date"]).dt.year.unique()):
                year_frame = bars[pd.to_datetime(bars["date"]).dt.year == year]
                store.write_frame(
                    year_frame,
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
            stock_basic = pd.DataFrame(
                {
                    "asset_id": [f"CN_XSHE_{idx:06d}" for idx in range(36)],
                    "industry": ["bank"] * 12 + ["tech"] * 12 + ["industrial"] * 12,
                }
            )
            stock_basic_path = root / "stock_basic.csv"
            stock_basic.to_csv(stock_basic_path, index=False)

            output = root / "output"
            result = run_price_volume_shock_reversal_neutral_prescreen_cli(
                bars_roots=[root],
                stock_basic=stock_basic_path,
                preregistration_json=None,
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=18,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["stage"], "price_volume_shock_reversal_neutral_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 8)
            self.assertTrue((output / "price_volume_shock_reversal_neutral_prescreen.json").exists())
            self.assertTrue((output / "price_volume_shock_reversal_neutral_prescreen_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
