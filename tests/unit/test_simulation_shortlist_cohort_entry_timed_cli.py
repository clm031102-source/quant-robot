from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


class SimulationShortlistCohortEntryTimedCliTest(unittest.TestCase):
    def test_cli_writes_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trades = root / "trades.csv"
            dragon = root / "dragon.csv"
            public = root / "public.csv"
            output = root / "out"
            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "signal_date": ["2024-01-01"],
                    "entry_date": ["2024-01-02"],
                    "exit_date": ["2024-01-10"],
                    "target_weight": [1.0],
                    "entry_cash_proxy_weighted_return": [0.02],
                    "turnover_rate_f": [5.0],
                    "entry_blocked_reasons": ["limit_down_like;limit_down_official"],
                }
            ).to_csv(trades, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_999999"],
                    "date": ["2023-12-29"],
                    "available_date": ["2024-01-02"],
                    "top_list_event_count": [0],
                    "top_list_net_amount_sum": [0.0],
                    "top_list_abs_pct_change_max": [0.0],
                }
            ).to_csv(dragon, index=False)
            pd.DataFrame(
                {
                    "date": ["2024-01-01"],
                    "asset_id": ["CN_XSHE_000001"],
                    "public_factor_name": ["alpha"],
                    "factor_value": [1.0],
                }
            ).to_csv(public, index=False)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_simulation_shortlist_cohort_entry_timed.py",
                    "--trades",
                    str(trades),
                    "--dragon-tiger-source",
                    str(dragon),
                    "--public-factor-source",
                    str(public),
                    "--public-factor-name",
                    "alpha",
                    "--public-factor-side",
                    "top",
                    "--public-factor-quantile",
                    "1.0",
                    "--candidate-name",
                    "demo",
                    "--target-annual-vol",
                    "9.99",
                    "--self-risk-threshold",
                    "-999",
                    "--public-factor-exposure-multiplier",
                    "2.0",
                    "--public-factor-tilt-risk-cap-column",
                    "turnover_rate_f",
                    "--public-factor-tilt-risk-cap-operator",
                    "gt",
                    "--public-factor-tilt-risk-cap-value",
                    "3.0",
                    "--entry-attribute-cash-rule",
                    "entry_limit_down=entry_blocked_reasons:eq:limit_down_like;limit_down_official",
                    "--output-dir",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("demo", completed.stdout)
            self.assertIn("public_tilt_risk_capped_trade_count", completed.stdout)
            self.assertIn("entry_attribute_cash_trade_count", completed.stdout)
            self.assertTrue((output / "simulation_shortlist_cohort_entry_timed.json").exists())


if __name__ == "__main__":
    unittest.main()
