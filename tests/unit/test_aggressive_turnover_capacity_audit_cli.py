import tempfile
import unittest
from pathlib import Path

from scripts.run_aggressive_turnover_capacity_audit import run_aggressive_turnover_capacity_audit


class AggressiveTurnoverCapacityAuditCliTests(unittest.TestCase):
    def test_cli_runner_reads_leaderboard_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "leaderboard.csv"
            output_dir = root / "audit"
            leaderboard.write_text(
                "case_id,factor_name,total_return,sharpe,overlap_autocorr_adjusted_sharpe,"
                "max_drawdown,capacity_limited_trades,max_participation_rate,"
                "extreme_trade_return_flag,relative_return\n"
                "raw,turnover_rate_low,10,1.5,0.8,-0.2,2,0.5,True,3\n"
                "repair,turnover_rate_low_large_mv,0.5,0.2,0.1,-0.4,0,0.001,False,-1\n",
                encoding="utf-8",
            )

            audit = run_aggressive_turnover_capacity_audit(
                leaderboard=leaderboard,
                output_dir=output_dir,
                target_factors=["turnover_rate_low"],
            )

            self.assertEqual(audit["summary"]["capacity_repair_failed_pairs"], 1)
            self.assertTrue((output_dir / "aggressive_turnover_capacity_audit.json").exists())
            self.assertTrue((output_dir / "aggressive_turnover_capacity_audit.md").exists())
            self.assertTrue((output_dir / "pair_audits.csv").exists())


if __name__ == "__main__":
    unittest.main()
