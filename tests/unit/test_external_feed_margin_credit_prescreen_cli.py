import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_external_feed_margin_credit_prescreen import _synthetic_margin_detail
from tests.unit.test_external_feed_northbound_prescreen import _synthetic_bars


class ExternalFeedMarginCreditPrescreenCliTests(unittest.TestCase):
    def test_cli_runner_loads_processed_external_margin_feed_and_writes_outputs(self) -> None:
        from scripts.run_external_feed_margin_credit_prescreen import run_external_feed_margin_credit_prescreen_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            external_root = Path(tmp) / "external"
            output = Path(tmp) / "report"
            bars = _synthetic_bars(days=36, assets=7, start="2024-01-02")
            margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=30))
            DatasetStore(root).write_frame(
                bars,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            DatasetStore(external_root).write_frame(
                margin,
                "processed/external_margin_detail",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )

            result = run_external_feed_margin_credit_prescreen_cli(
                bars_roots=[root],
                processed_root=external_root / "processed",
                output_dir=output,
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizons=(1,),
                execution_lag=0,
                lookback=5,
                min_cross_section=6,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["stage"], "external_feed_margin_credit_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 2)
            self.assertTrue((output / "external_feed_margin_credit_prescreen.json").exists())
            payload = json.loads(
                (output / "external_feed_margin_credit_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
