import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.daily_basic_public_anomaly_residual_ensemble import (
    DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_public_anomaly_residual_ensemble_prescreen import (
    run_public_anomaly_residual_ensemble_prescreen_cli,
)
from tests.unit.test_daily_basic_public_anomaly_residual_ensemble_factors import (
    _bars,
    _daily_basic_inputs,
)
from tests.unit.test_public_anomaly_residual_ensemble_prescreen import _synthetic_frames


class PublicAnomalyResidualEnsemblePrescreenCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_round229_outputs_from_injected_frames(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_public_anomaly_residual_ensemble_prescreen_cli(
                output_dir=output,
                factor_frame=factor_frame,
                labels=labels,
                reference_factor_frame=reference_frame,
                exposure_frame=exposure_frame,
                candidate_factor_names=DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
                horizons=(5,),
                min_cross_section=15,
                min_ic_observations=4,
                min_industry_neutral_icir=0.0,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "public_anomaly_residual_ensemble_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 4)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertTrue((output / "public_anomaly_residual_ensemble_prescreen.json").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_prescreen_results.csv").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_residual_ic_observations.csv").exists())

    def test_cli_wrapper_supports_sharded_long_cycle_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            output = Path(tmp) / "report"
            bars = _sharded_bars()
            daily_basic = _sharded_daily_basic()
            store = DatasetStore(root)
            for year in sorted(bars["date"].dt.year.unique()):
                store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
            for year in sorted(daily_basic["date"].dt.year.unique()):
                store.write_frame(
                    daily_basic[daily_basic["date"].dt.year == year],
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = run_public_anomaly_residual_ensemble_prescreen_cli(
                bars_roots=[root],
                daily_basic_roots=[root],
                stock_basic=_stock_basic(bars["asset_id"].unique()),
                output_dir=output,
                sharded=True,
                candidate_factor_names=("public_anomaly_residual_equal_weight_20",),
                analysis_start_date="2024-04-01",
                analysis_end_date="2025-03-31",
                lookback_calendar_days=120,
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
            self.assertEqual(result["source_context"]["candidate_family"], "public_anomaly_residual_ensemble_risk_budget")
            self.assertGreater(result["summary"]["factor_rows"], 0)


def _sharded_bars() -> pd.DataFrame:
    base = _bars(day_count=330).copy()
    dates = pd.bdate_range("2024-01-02", periods=330)
    old_dates = sorted(base["date"].unique())
    date_map = dict(zip(old_dates, dates.date, strict=True))
    base["date"] = pd.to_datetime(base["date"].map(date_map))
    return base


def _sharded_daily_basic() -> pd.DataFrame:
    base = _daily_basic_inputs(day_count=330).copy()
    dates = pd.bdate_range("2024-01-02", periods=330)
    old_dates = sorted(base["date"].unique())
    date_map = dict(zip(old_dates, dates.date, strict=True))
    base["date"] = pd.to_datetime(base["date"].map(date_map))
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
