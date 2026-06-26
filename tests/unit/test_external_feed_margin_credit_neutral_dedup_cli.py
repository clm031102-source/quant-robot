import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_external_feed_margin_credit_neutral_dedup import _round192_prescreen_report
from tests.unit.test_external_feed_margin_credit_prescreen import _synthetic_margin_detail
from tests.unit.test_external_feed_northbound_prescreen import _synthetic_bars


class ExternalFeedMarginCreditNeutralDedupCliTests(unittest.TestCase):
    def test_cli_loads_processed_feeds_and_writes_round193_outputs(self) -> None:
        from scripts.run_external_feed_margin_credit_neutral_dedup import (
            run_external_feed_margin_credit_neutral_dedup_cli,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bars_store"
            external_root = Path(tmp) / "external_store"
            output = Path(tmp) / "report"
            prescreen_path = Path(tmp) / "round192.json"
            bars = _synthetic_bars(days=58, assets=12, start="2024-01-02")
            margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=52))
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
            prescreen_path.write_text(json.dumps(_round192_prescreen_report()), encoding="utf-8")

            result = run_external_feed_margin_credit_neutral_dedup_cli(
                bars_roots=[root],
                processed_root=external_root / "processed",
                prescreen_report=prescreen_path,
                output_dir=output,
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizon=1,
                execution_lag=0,
                lookback=5,
                sample_every_n_dates=2,
                min_cross_section=6,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["stage"], "external_feed_margin_credit_neutral_dedup")
            self.assertTrue((output / "external_feed_margin_credit_neutral_dedup.json").exists())
            payload = json.loads(
                (output / "external_feed_margin_credit_neutral_dedup.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])
            self.assertIn("industry_metadata_missing_or_not_pit", payload["gate"]["blockers"])


if __name__ == "__main__":
    unittest.main()
