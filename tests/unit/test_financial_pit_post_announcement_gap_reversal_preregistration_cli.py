import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_pit_post_announcement_gap_reversal_preregistration import (
    run_financial_pit_post_announcement_gap_reversal_preregistration_cli,
)
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _bar_rows,
    _financial_rows,
    _write_bars,
    _write_financial,
)
from tests.unit.test_financial_pit_post_announcement_gap_reversal_preregistration import _seed


class FinancialPitPostAnnouncementGapReversalPreregistrationCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_gap_reversal_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")

            result = run_financial_pit_post_announcement_gap_reversal_preregistration_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                output_dir=output_dir,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_preregistration.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_preregistration.md").exists())


if __name__ == "__main__":
    unittest.main()
