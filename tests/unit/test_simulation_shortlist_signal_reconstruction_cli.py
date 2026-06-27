from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.run_simulation_shortlist_signal_reconstruction import (
    run_simulation_shortlist_signal_reconstruction_cli,
)


class SimulationShortlistSignalReconstructionCliTest(unittest.TestCase):
    def test_cli_writes_reconstruction_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trades_path = root / "trades.csv"
            events_path = root / "events.csv"
            dragon_path = root / "dragon.csv"
            public_path = root / "public.csv"
            output = root / "out"

            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "signal_date": ["2024-01-01"],
                    "entry_date": ["2024-01-02"],
                    "exit_date": ["2024-01-10"],
                    "target_weight": [1.0],
                    "entry_cash_proxy_weighted_return": [0.02],
                }
            ).to_csv(trades_path, index=False)
            pd.DataFrame(
                {
                    "date": ["2024-01-10"],
                    "decision_date": ["2024-01-02"],
                    "final_exposure": [1.0],
                    "period_return": [0.03],
                }
            ).to_csv(events_path, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_999999"],
                    "date": ["2023-12-29"],
                    "available_date": ["2024-01-02"],
                    "top_list_event_count": [0],
                    "top_list_net_amount_sum": [0.0],
                    "top_list_abs_pct_change_max": [0.0],
                }
            ).to_csv(dragon_path, index=False)
            pd.DataFrame(
                {
                    "date": ["2024-01-01"],
                    "asset_id": ["CN_XSHE_000001"],
                    "public_factor_name": ["alpha"],
                    "factor_value": [1.0],
                }
            ).to_csv(public_path, index=False)

            result = run_simulation_shortlist_signal_reconstruction_cli(
                trades=trades_path,
                event_source=events_path,
                dragon_tiger_source=dragon_path,
                public_factor_source=public_path,
                public_factor_name="alpha",
                public_factor_side="top",
                public_factor_quantile=1.0,
                public_factor_exposure_multiplier=1.5,
                output_dir=output,
            )

            self.assertEqual(result["summary"]["public_tilt_trade_count"], 1)
            self.assertTrue((output / "simulation_shortlist_signal_reconstruction.json").exists())
            self.assertTrue((output / "simulation_shortlist_signal_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
