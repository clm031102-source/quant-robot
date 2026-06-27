from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_replay import build_simulation_shortlist_replay


class SimulationShortlistReplayTest(unittest.TestCase):
    def test_replay_accepts_candidate_when_event_metrics_match_evidence(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "returns.csv"
            pd.DataFrame(
                {
                    "date": ["2021-01-31", "2021-02-28", "2021-03-31"],
                    "period_return": [0.01, 0.02, -0.005],
                }
            ).to_csv(source, index=False)
            config = {
                "simulation_candidates": [
                    {
                        "id": "primary",
                        "event_return_source": {"path": "returns.csv", "return_column": "period_return"},
                        "evidence": {
                            "full_sample_total_return": 0.025,
                            "full_sample_annualized_return": 0.10,
                        },
                    }
                ]
            }

            replay = build_simulation_shortlist_replay(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                metric_tolerance=0.20,
            )

            self.assertEqual(replay["blockers"], [])
            self.assertEqual(replay["summary"]["candidate_count"], 1)
            self.assertEqual(replay["rows"][0]["candidate_id"], "primary")
            self.assertGreater(replay["rows"][0]["actual_total_return"], 0.0)

    def test_replay_blocks_missing_source_and_metric_mismatch(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "returns.csv"
            pd.DataFrame(
                {
                    "date": ["2021-01-31", "2021-02-28"],
                    "period_return": [0.01, 0.01],
                }
            ).to_csv(source, index=False)
            config = {
                "simulation_candidates": [
                    {
                        "id": "mismatch",
                        "event_return_source": {"path": "returns.csv"},
                        "evidence": {"full_sample_total_return": 9.0},
                    },
                    {
                        "id": "missing",
                        "event_return_source": {"path": "missing.csv"},
                        "evidence": {"full_sample_total_return": 0.0},
                    },
                ]
            }

            replay = build_simulation_shortlist_replay(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                metric_tolerance=0.01,
            )

            self.assertIn("metric_mismatch:mismatch:full_sample_total_return", replay["blockers"])
            self.assertIn("event_return_source_missing:missing", replay["blockers"])

    def test_replay_blocks_shortlist_candidate_with_missing_event_structure(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "returns.csv"
            pd.DataFrame(
                {
                    "date": ["2021-01-31", "2021-02-28"],
                    "period_return": [0.01, 0.01],
                }
            ).to_csv(source, index=False)
            config = {
                "simulation_candidates": [
                    {
                        "id": "structured_candidate",
                        "formula": "turnover_rate_low Top50 + entry_cash + vol_target_6_lb84",
                        "event_return_source": {"path": "returns.csv"},
                        "volatility_target": {"target_annual_vol": 0.06, "lookback_events": 84},
                        "evidence": {"full_sample_total_return": 0.0201},
                    }
                ]
            }

            replay = build_simulation_shortlist_replay(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                metric_tolerance=0.01,
            )

            self.assertIn("event_schema_missing:structured_candidate:decision_date", replay["blockers"])
            self.assertIn("event_schema_missing:structured_candidate:final_exposure", replay["blockers"])

    def test_replay_blocks_riskoff_multiplier_mismatch_when_event_declares_multiplier(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "events.csv"
            pd.DataFrame(
                {
                    "date": ["2021-01-31", "2021-02-28"],
                    "decision_date": ["2021-01-01", "2021-02-01"],
                    "period_return": [0.01, 0.01],
                    "riskoff_multiplier": [0.75, 0.75],
                    "regime_guard_exposure": [1.0, 0.75],
                    "final_exposure": [1.0, 0.75],
                }
            ).to_csv(source, index=False)
            config = {
                "simulation_candidates": [
                    {
                        "id": "defensive",
                        "formula": "primary + zz500_mom120_neg_half",
                        "event_return_source": {"path": "events.csv"},
                        "external_regime_overlay": {
                            "benchmark_asset_id": "CN_ETF_XSHG_510500",
                            "risk_off_exposure_multiplier": 0.5,
                        },
                        "evidence": {"full_sample_total_return": 0.0201},
                    }
                ]
            }

            replay = build_simulation_shortlist_replay(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                metric_tolerance=0.01,
            )

            self.assertIn("riskoff_multiplier_mismatch:defensive", replay["blockers"])


if __name__ == "__main__":
    unittest.main()
