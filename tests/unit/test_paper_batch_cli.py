import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_paper_batch import run_paper_batch


class PaperBatchCliTests(unittest.TestCase):
    def test_run_paper_batch_writes_one_manifest_per_accepted_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    },
                    {
                        "case_id": "CN_reversal_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "reversal_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "rejected",
                        "rank": 2,
                    },
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                        "initial_cash": 100000,
                        "max_asset_weight": 0.4,
                        "min_cash_weight": 0.1,
                    }
                ),
                encoding="utf-8",
            )

            result = run_paper_batch(config_path)

            self.assertEqual(result["summary"]["completed"], 1)
            self.assertEqual(result["summary"]["skipped"], 1)
            manifest_path = output_dir / "CN_momentum_2_top1_cost5_reb2" / "manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["request"]["case_id"], "CN_momentum_2_top1_cost5_reb2")
            self.assertEqual(manifest["request"]["rebalance_interval"], 2)
            self.assertTrue((output_dir / "paper_batch_summary.csv").exists())
            self.assertTrue((output_dir / "paper_batch_summary.json").exists())

    def test_run_paper_batch_removes_stale_candidate_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "rejected",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            stale_dir = output_dir / "CN_old_candidate"
            stale_dir.mkdir(parents=True)
            (stale_dir / "manifest.json").write_text("{}", encoding="utf-8")
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                    }
                ),
                encoding="utf-8",
            )

            result = run_paper_batch(config_path)

            self.assertEqual(result["summary"]["completed"], 0)
            self.assertFalse((stale_dir / "manifest.json").exists())

    def test_paper_batch_script_runs_when_executed_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(root / "paper_batch"),
                        "max_candidates": 1,
                        "max_asset_weight": 0.4,
                        "min_cash_weight": 0.1,
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            completed = subprocess.run(
                [sys.executable, "scripts/run_paper_batch.py", "--config", str(config_path)],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_run_paper_batch_sweeps_risk_profiles_and_writes_best_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_liquidity_10_top1_cost5_reb5",
                        "market": "CN",
                        "factor_name": "liquidity_10",
                        "factor_windows": "[5, 10]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 1,
                        "profile_max_drawdown": 0.25,
                        "risk_profiles": [
                            {"profile_id": "defensive", "max_asset_weight": 0.3, "max_drawdown_guard": 0.1},
                            {
                                "profile_id": "balanced",
                                "max_asset_weight": 0.5,
                                "max_drawdown_guard": 0.1,
                                "guard_cooldown_periods": 3,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                profile_id = "balanced" if kwargs["max_asset_weight"] == 0.5 else "defensive"
                sharpe = 0.62 if profile_id == "balanced" else 0.44
                return {
                    "data_mode": "research",
                    "request": {
                        "market": kwargs["market"],
                        "factor_name": kwargs["factor_name"],
                        "top_n": kwargs["top_n"],
                        "rebalance_interval": kwargs["rebalance_interval"],
                        "max_asset_weight": kwargs["max_asset_weight"],
                    },
                    "metrics": {
                        "sharpe": sharpe,
                        "total_return": 0.30,
                        "max_equity_drawdown": -0.20,
                    },
                    "intents": [],
                    "fills": [],
                    "positions": [],
                    "equity_curve": [],
                    "snapshots": [],
                    "guard_events": [],
                }

            with patch("scripts.run_paper_batch.run_simulation", side_effect=fake_run_simulation) as run_mock:
                result = run_paper_batch(config_path)

            self.assertEqual(run_mock.call_count, 2)
            selected = result["candidates"][0]
            self.assertEqual(selected["status"], "completed")
            self.assertEqual(selected["risk_profile_id"], "balanced")
            self.assertEqual(selected["attempted_profiles"], 2)
            self.assertAlmostEqual(selected["sharpe"], 0.62)
            manifest = json.loads((output_dir / "CN_liquidity_10_top1_cost5_reb5" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["request"]["risk_profile_id"], "balanced")
            self.assertEqual(manifest["request"]["max_asset_weight"], 0.5)


if __name__ == "__main__":
    unittest.main()
