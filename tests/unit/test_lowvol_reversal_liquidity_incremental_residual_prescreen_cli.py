import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_lowvol_reversal_liquidity_incremental_residual_prescreen import (
    run_lowvol_reversal_liquidity_incremental_residual_prescreen_cli,
)
from tests.unit.test_lowvol_reversal_liquidity_incremental_residual_prescreen import (
    _synthetic_ohlcv_bars,
)


class LowvolReversalLiquidityIncrementalResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_diagnostic_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            DatasetStore(root).write_frame(
                _synthetic_ohlcv_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_lowvol_reversal_liquidity_incremental_residual_prescreen_cli(
                bars_roots=[root],
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
                sample_every_n_dates=5,
            )

            self.assertEqual(result["stage"], "lowvol_reversal_liquidity_incremental_residual_prescreen")
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_prescreen.json").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_prescreen.md").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_reference_correlations.csv").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_exposure_correlations.csv").exists())
            payload = json.loads(
                (output / "lowvol_reversal_liquidity_incremental_residual_prescreen.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["summary"]["candidate_count"], 8)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
