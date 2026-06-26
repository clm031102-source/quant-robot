import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_pit_post_announcement_gap_reversal_residual_prescreen import (
    run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli,
)
from tests.unit.test_financial_pit_post_announcement_drift_residual_prescreen import (
    _financial_rows,
    _write_bars,
    _write_daily_basic,
    _write_financial,
    _write_stock_basic,
)
from tests.unit.test_financial_pit_post_announcement_gap_reversal_preregistration import _seed
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_preregistration import (
    build_financial_pit_post_announcement_gap_reversal_preregistration,
    write_financial_pit_post_announcement_gap_reversal_preregistration,
)


class FinancialPitPostAnnouncementGapReversalResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_gap_reversal_residual_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            prereg_output = root / "prereg"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            financial = _financial_rows(assets=6)
            asset_ids = financial["asset_id"].drop_duplicates().tolist()
            _write_financial(financial_root, financial)
            _write_bars(bars_root, asset_ids)
            _write_daily_basic(daily_basic_root, asset_ids)
            _write_stock_basic(stock_basic_root, asset_ids)
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            prereg = build_financial_pit_post_announcement_gap_reversal_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=6,
                min_signal_dates=4,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_gap_reversal_preregistration(prereg_output, prereg)

            result = run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_gap_reversal_preregistration.json",
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=[5],
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-10.0,
                min_neutral_retention=0.0,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_residual_prescreen")
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_residual_prescreen.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_residual_prescreen.md").exists())


if __name__ == "__main__":
    unittest.main()
