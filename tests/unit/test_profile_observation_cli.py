import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_profile_observation import run_profile_observation


class ProfileObservationCliTests(unittest.TestCase):
    def test_run_profile_observation_writes_ledger_and_stop_rule_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            daily_ops = root / "daily_ops_pack.json"
            simulation_dir = root / "paper_simulation"
            output_dir = root / "profile_observation"
            simulation_dir.mkdir()
            daily_ops.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_5_profile_daily_ops_activation",
                        "run_date": "2026-06-14",
                        "candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"},
                        "decision": {"status": "paper_ready", "paper_trading_allowed": True, "live_boundary_allowed": False},
                        "paper_profile": {
                            "profile_id": "cap60_guard12_cd3",
                            "risk_tier": "aggressive_growth",
                            "max_asset_weight": 0.6,
                            "max_gross_exposure": 1.0,
                            "min_cash_weight": 0.0,
                            "max_drawdown_guard": 0.12,
                            "guard_cooldown_periods": 3,
                        },
                        "risk": {"total_return": 0.9, "max_equity_drawdown": -0.25, "execution_blocks": 0},
                        "risk_policy": {"max_drawdown_limit": -0.3},
                        "signal": {"signal_date": "2026-05-22", "target_gross_exposure": 0.6},
                        "simulation": {"fills": 30, "guard_events": 0, "execution_events": 0},
                    }
                ),
                encoding="utf-8",
            )
            (simulation_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "request": {
                            "max_asset_weight": 0.6,
                            "max_gross_exposure": 1.0,
                            "min_cash_weight": 0.0,
                            "max_drawdown_guard": 0.12,
                            "guard_cooldown_periods": 3,
                        }
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"date": "2026-05-22", "equity": 100000.0, "gross_exposure": 0.6},
                    {"date": "2026-05-23", "equity": 101000.0, "gross_exposure": 0.0},
                ]
            ).to_csv(simulation_dir / "equity_curve.csv", index=False)
            pd.DataFrame([]).to_csv(simulation_dir / "guard_events.csv", index=False)
            pd.DataFrame([]).to_csv(simulation_dir / "execution_events.csv", index=False)

            pack = run_profile_observation(
                daily_ops_pack=daily_ops,
                simulation_dir=simulation_dir,
                output_dir=output_dir,
                run_date="2026-06-14",
            )

            self.assertEqual(pack["stage"], "phase_5_6_profile_observation_ledger")
            self.assertEqual(pack["decision"]["observation_status"], "stopped")
            self.assertTrue((output_dir / "profile_observation_pack.json").exists())
            self.assertTrue((output_dir / "profile_observation_pack.md").exists())
            self.assertTrue((output_dir / "profile_observation_ledger.csv").exists())
            self.assertTrue((output_dir / "profile_observation_stop_rules.csv").exists())
            payload = json.loads((output_dir / "profile_observation_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["ledger"][0]["case_id"], "case_a")
            self.assertIn("signal_data_stale", payload["decision"]["stop_reasons"])


if __name__ == "__main__":
    unittest.main()
