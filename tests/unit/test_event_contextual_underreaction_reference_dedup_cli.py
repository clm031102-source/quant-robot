import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_event_contextual_underreaction_prescreen import _event_frames, _predictive_bars
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic


class EventContextualUnderreactionReferenceDedupCliTests(unittest.TestCase):
    def test_cli_runner_writes_reference_dedup_outputs_with_injected_events(self) -> None:
        from scripts.run_event_contextual_underreaction_reference_dedup import (
            run_event_contextual_underreaction_reference_dedup_cli,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "processed"
            report_dir = root / "report"
            stock_basic_path = root / "stock_basic.csv"
            prescreen_path = root / "prescreen.json"
            DatasetStore(store_root).write_frame(
                _predictive_bars(days=55, assets=8),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _stock_basic(8).to_csv(stock_basic_path, index=False)
            prescreen_path.write_text(
                '{"results":[{"factor_name":"event_holder_contraction_low_vol_20","horizon":5,"research_lead":true}],"summary":{"research_lead_count":1,"candidate_count":4,"test_count":8}}',
                encoding="utf-8",
            )

            result = run_event_contextual_underreaction_reference_dedup_cli(
                bars_roots=[store_root],
                stock_basic_path=stock_basic_path,
                prescreen_report=prescreen_path,
                output_dir=report_dir,
                event_frames=_event_frames(
                    assets=8,
                    dates=("2024-01-30", "2024-02-13", "2024-02-27", "2024-03-12"),
                ),
                include_price_volume_references=False,
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                execution_lag=0,
                min_cross_section=4,
                min_ic_observations=2,
            )

            self.assertEqual(result["stage"], "event_contextual_underreaction_reference_dedup")
            self.assertTrue((report_dir / "event_contextual_underreaction_reference_dedup.json").exists())
            self.assertTrue((report_dir / "event_contextual_underreaction_reference_correlations.csv").exists())
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
