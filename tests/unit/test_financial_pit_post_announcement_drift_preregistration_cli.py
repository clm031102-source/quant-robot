import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_pit_post_announcement_drift_preregistration import (
    run_financial_pit_post_announcement_drift_preregistration_cli,
)
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _bar_rows,
    _financial_rows,
    _write_bars,
    _write_financial,
)


class FinancialPitPostAnnouncementDriftPreregistrationCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_dir = root / "output"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())

            result = run_financial_pit_post_announcement_drift_preregistration_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                output_dir=output_dir,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_preregistration.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_preregistration.md").exists())


if __name__ == "__main__":
    unittest.main()
