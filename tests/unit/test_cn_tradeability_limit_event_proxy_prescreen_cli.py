import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_tradeability_limit_event_proxy_prescreen import (
    run_cn_tradeability_limit_event_proxy_prescreen_cli,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_cn_tradeability_limit_event_proxy_prescreen import _stock_basic
from tests.unit.test_public_reference_multi_family_prescreen import _synthetic_public_reference_bars


class CNTradeabilityLimitEventProxyPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_round160_outputs(self) -> None:
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
            stock_basic_path = root / "stock_basic.csv"
            _stock_basic(36).to_csv(stock_basic_path, index=False)

            output = root / "output"
            result = run_cn_tradeability_limit_event_proxy_prescreen_cli(
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

            self.assertEqual(result["stage"], "cn_tradeability_limit_event_proxy_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 8)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue(result["promotion_policy"]["requires_true_limit_status_audit"])
            self.assertTrue((output / "cn_tradeability_limit_event_proxy_prescreen.json").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_proxy_prescreen_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
