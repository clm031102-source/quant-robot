import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_pit_post_announcement_drift_matrix_label_smoke import (
    run_financial_pit_post_announcement_drift_matrix_label_smoke_cli,
)
from tests.unit.test_financial_pit_post_announcement_drift_matrix_label_smoke import _bar_rows_for_label_window
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _financial_rows,
    _seed,
    _write_bars,
    _write_financial,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    build_financial_pit_post_announcement_drift_preregistration,
    write_financial_pit_post_announcement_drift_preregistration,
)


class FinancialPitPostAnnouncementDriftMatrixLabelSmokeCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            preregistration = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_drift_preregistration(prereg_output, preregistration)

            result = run_financial_pit_post_announcement_drift_matrix_label_smoke_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
                output_dir=output_dir,
                min_label_coverage=0.90,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_matrix_label_smoke.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_matrix_label_smoke.md").exists())


if __name__ == "__main__":
    unittest.main()
