import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_promotion_report import run_promotion_report


class PromotionGateCliTests(unittest.TestCase):
    def test_run_promotion_report_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_ETF_momentum_20_top2_cost5_reb5",
                        "market": "CN_ETF",
                        "factor_name": "momentum_20",
                        "top_n": 2,
                        "validation_status": "accepted",
                        "data_mode": "research",
                        "test_trades": 324,
                        "test_sharpe": 0.34,
                        "test_relative_return": 0.06,
                        "test_max_drawdown": -0.12,
                        "stability_score": 0.34,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            paper_manifest_path = root / "paper_manifest.json"
            paper_manifest_path.write_text(
                json.dumps(
                    {
                        "data_mode": "research",
                        "metrics": {
                            "max_equity_drawdown": -0.56,
                            "sharpe": 0.46,
                            "total_return": 1.92,
                        },
                        "request": {
                            "market": "CN_ETF",
                            "factor_name": "momentum_20",
                            "top_n": 2,
                        },
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "promotion"
            config_path = root / "promotion_gate.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "paper_manifest": str(paper_manifest_path),
                        "output_dir": str(output_dir),
                        "max_paper_drawdown": 0.25,
                    }
                ),
                encoding="utf-8",
            )

            report = run_promotion_report(config_path)

            self.assertEqual(report["summary"]["blocked"], 1)
            self.assertTrue((output_dir / "promotion_report.csv").exists())
            self.assertTrue((output_dir / "promotion_report.json").exists())

    def test_run_promotion_report_reads_paper_manifest_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_ETF_momentum_20_top2_cost5_reb5",
                        "market": "CN_ETF",
                        "factor_name": "momentum_20",
                        "top_n": 2,
                        "validation_status": "accepted",
                        "data_mode": "research",
                        "test_trades": 324,
                        "test_sharpe": 0.72,
                        "test_relative_return": 0.06,
                        "test_max_drawdown": -0.12,
                        "stability_score": 0.64,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            manifest_dir = root / "paper_batch"
            case_dir = manifest_dir / "CN_ETF_momentum_20_top2_cost5_reb5"
            case_dir.mkdir(parents=True)
            (case_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "data_mode": "research",
                        "metrics": {
                            "max_equity_drawdown": -0.10,
                            "sharpe": 0.80,
                            "total_return": 0.20,
                        },
                        "request": {
                            "market": "CN_ETF",
                            "factor_name": "momentum_20",
                            "top_n": 2,
                            "rebalance_interval": 5,
                        },
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "promotion_gate.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "paper_manifest_dir": str(manifest_dir),
                        "min_oos_sharpe": 0.5,
                        "min_paper_sharpe": 0.5,
                    }
                ),
                encoding="utf-8",
            )

            report = run_promotion_report(config_path)

            self.assertEqual(report["summary"]["paper_ready"], 1)
            self.assertEqual(report["candidates"][0]["paper"]["manifest_path"], str(case_dir / "manifest.json"))


if __name__ == "__main__":
    unittest.main()
