import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_industry_leader_lag_residual_prescreen import (
    run_industry_leader_lag_residual_prescreen_cli,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_industry_leader_lag_residual_prescreen import (
    _synthetic_frames,
    _synthetic_sharded_bars,
    _synthetic_stock_basic,
)


class IndustryLeaderLagResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_round220_prescreen_outputs_from_prebuilt_frames(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_industry_leader_lag_residual_prescreen_cli(
                output_dir=output,
                factor_frame=factor_frame,
                labels=labels,
                reference_factor_frame=reference_frame,
                exposure_frame=exposure_frame,
                min_cross_section=15,
                min_ic_observations=4,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "industry_leader_lag_residual_prescreen")
            self.assertTrue((output / "industry_leader_lag_residual_prescreen.json").exists())
            self.assertTrue((output / "industry_leader_lag_residual_prescreen.md").exists())
            payload = json.loads((output / "industry_leader_lag_residual_prescreen.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], 6)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])
            self.assertFalse(payload["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertEqual(
                payload["source_context"]["source_audit"],
                "docs/research/cn_stock_round220_family_rotation_industry_leader_lag_2026-06-24.md",
            )

    def test_cli_wrapper_supports_sharded_long_cycle_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            output = Path(tmp) / "report"
            bars = _synthetic_sharded_bars()
            store = DatasetStore(root)
            for year in sorted(bars["date"].dt.year.unique()):
                store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = run_industry_leader_lag_residual_prescreen_cli(
                bars_roots=[root],
                stock_basic=_synthetic_stock_basic(),
                output_dir=output,
                sharded=True,
                candidate_factor_names=("industry_leader_laggard_gap_reversion_5_20",),
                analysis_start_date="2024-01-02",
                analysis_end_date="2025-02-28",
                lookback_calendar_days=90,
                forward_calendar_days=30,
                min_signal_date_amount=1_000,
                min_cross_section=9,
                min_ic_observations=2,
                min_industry_neutral_icir=-99.0,
                min_residual_icir=-99.0,
            )

            self.assertTrue(result["sharding_policy"]["enabled"])
            self.assertEqual(result["sharding_policy"]["shard_count"], 2)
            payload = json.loads((output / "industry_leader_lag_residual_prescreen.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["source_context"]["sharded_full_cycle_prescreen"])


if __name__ == "__main__":
    unittest.main()
