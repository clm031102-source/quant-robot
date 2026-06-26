import tempfile
import unittest
from pathlib import Path

from scripts.run_index_rebalance_event_audit import run_index_rebalance_event_audit_cli
from tests.unit.test_index_rebalance_event_audit import _calendar_rows, _index_weight_rows


class IndexRebalanceEventAuditCliTests(unittest.TestCase):
    def test_cli_reads_csv_inputs_and_writes_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            weights = root / "weights.csv"
            calendar = root / "calendar.csv"
            output_dir = root / "out"
            _index_weight_rows().to_csv(weights, index=False)
            _calendar_rows().to_csv(calendar, index=False)

            result = run_index_rebalance_event_audit_cli(
                index_weight_path=weights,
                trade_calendar_path=calendar,
                output_dir=output_dir,
                min_abs_weight_change=0.5,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "index_rebalance_event_audit.json").exists())
            self.assertTrue((output_dir / "index_rebalance_events.csv").exists())


if __name__ == "__main__":
    unittest.main()
