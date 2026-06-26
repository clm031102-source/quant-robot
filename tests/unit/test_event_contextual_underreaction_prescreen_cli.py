import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_event_contextual_underreaction_prescreen import _event_frames, _predictive_bars
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic


class EventContextualUnderreactionPrescreenCliTests(unittest.TestCase):
    def test_cli_runner_writes_contextual_outputs_with_injected_events(self) -> None:
        from scripts.run_event_contextual_underreaction_prescreen import (
            run_event_contextual_underreaction_prescreen_cli,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "processed"
            report_dir = root / "report"
            stock_basic_path = root / "stock_basic.csv"
            DatasetStore(store_root).write_frame(
                _predictive_bars(days=55, assets=8),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _stock_basic(8).to_csv(stock_basic_path, index=False)

            result = run_event_contextual_underreaction_prescreen_cli(
                bars_roots=[store_root],
                stock_basic_path=stock_basic_path,
                output_dir=report_dir,
                event_frames=_event_frames(
                    assets=8,
                    dates=("2024-01-30", "2024-02-13", "2024-02-27", "2024-03-12"),
                ),
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizons=(5,),
                execution_lag=0,
                min_cross_section=4,
                min_ic_observations=2,
                min_industries=2,
                min_assets_per_industry=2,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-10.0,
                min_neutral_retention=0.0,
            )

            self.assertEqual(result["stage"], "event_contextual_underreaction_prescreen")
            self.assertTrue((report_dir / "event_contextual_underreaction_prescreen.json").exists())
            self.assertTrue((report_dir / "event_contextual_underreaction_prescreen.md").exists())
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
