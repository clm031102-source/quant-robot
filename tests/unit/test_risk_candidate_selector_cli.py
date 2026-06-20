import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_risk_candidate_selector import run_risk_candidate_selector


class RiskCandidateSelectorCliTests(unittest.TestCase):
    def test_run_risk_candidate_selector_writes_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_report.json"
            daily = root / "daily_ops_pack.json"
            output_dir = root / "risk_candidates"
            promotion.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "case_id": "case_a",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_20",
                                "promotion_rank": 1,
                                "promotion_status": "paper_ready",
                                "duplicate_of": None,
                                "walk_forward": {
                                    "validation_status": "accepted",
                                    "test_sharpe": 0.7,
                                    "test_relative_return": 0.03,
                                    "test_max_drawdown": -0.10,
                                    "test_trades": 40,
                                },
                                "paper": {"matched": True, "sharpe": 0.6, "max_drawdown": -0.08, "total_return": 0.1},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            daily.write_text(json.dumps({"decision": {"status": "blocked"}}), encoding="utf-8")

            pack = run_risk_candidate_selector(
                promotion_report=promotion,
                daily_ops_pack=daily,
                output_dir=output_dir,
                max_drawdown_limit=0.2,
            )

            self.assertEqual(pack["stage"], "phase_5_1_risk_candidate_selector")
            self.assertEqual(pack["selection_status"], "risk_candidate_selected")
            self.assertTrue((output_dir / "risk_candidate_pack.json").exists())
            payload = json.loads((output_dir / "risk_candidate_pack.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["live_boundary_allowed"])
            self.assertEqual(payload["selected_candidate"]["case_id"], "case_a")


if __name__ == "__main__":
    unittest.main()
