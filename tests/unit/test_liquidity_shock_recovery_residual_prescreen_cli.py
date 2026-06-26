import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.liquidity_shock_recovery import LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_liquidity_shock_recovery_residual_prescreen import (
    run_liquidity_shock_recovery_residual_prescreen_cli,
)
from tests.unit.test_liquidity_shock_recovery_factors import _bars
from tests.unit.test_liquidity_shock_recovery_residual_prescreen import _synthetic_frames


class LiquidityShockRecoveryResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_round230_outputs_from_injected_frames(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_liquidity_shock_recovery_residual_prescreen_cli(
                output_dir=output,
                factor_frame=factor_frame,
                labels=labels,
                reference_factor_frame=reference_frame,
                exposure_frame=exposure_frame,
                candidate_factor_names=LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
                horizons=(5,),
                min_cross_section=15,
                min_ic_observations=4,
                min_industry_neutral_icir=0.0,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "liquidity_shock_recovery_residual_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 5)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertTrue((output / "liquidity_shock_recovery_residual_prescreen.json").exists())
            self.assertTrue((output / "liquidity_shock_recovery_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "liquidity_shock_recovery_residual_ic_observations.csv").exists())

    def test_cli_wrapper_supports_sharded_long_cycle_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            output = Path(tmp) / "report"
            bars = _sharded_bars()
            store = DatasetStore(root)
            for year in sorted(bars["date"].dt.year.unique()):
                store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = run_liquidity_shock_recovery_residual_prescreen_cli(
                bars_roots=[root],
                stock_basic=_stock_basic(bars["asset_id"].unique()),
                output_dir=output,
                sharded=True,
                candidate_factor_names=("amihud_shock_reversal_recovery_20_5",),
                analysis_start_date="2024-02-01",
                analysis_end_date="2024-04-30",
                lookback_calendar_days=60,
                forward_calendar_days=30,
                min_signal_date_amount=1_000,
                min_cross_section=2,
                min_ic_observations=2,
                min_industry_neutral_icir=-99.0,
                min_residual_icir=-99.0,
            )

            self.assertTrue(result["sharding_policy"]["enabled"])
            self.assertTrue(result["sharding_policy"]["streaming_summary"])
            self.assertEqual(result["reference_policy"]["mode"], "defer_until_residual_lead")
            self.assertEqual(result["summary"]["reference_factor_count"], 0)
            self.assertEqual(result["source_context"]["candidate_family"], "liquidity_shock_recovery")
            self.assertGreater(result["summary"]["factor_rows"], 0)


def _sharded_bars() -> pd.DataFrame:
    base = _bars().copy()
    base["date"] = pd.to_datetime(base["date"])
    return base


def _stock_basic(asset_ids) -> pd.DataFrame:
    rows = []
    industries = ["bank", "tech", "industrial"]
    for index, asset_id in enumerate(asset_ids):
        rows.append(
            {
                "asset_id": str(asset_id),
                "symbol": str(asset_id),
                "industry": industries[index % len(industries)],
                "list_status": "L",
                "list_date": "20100101",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
