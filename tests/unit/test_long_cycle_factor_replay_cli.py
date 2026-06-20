import tempfile
import unittest
import json
from pathlib import Path

import pandas as pd

from scripts.run_long_cycle_factor_replay import run_long_cycle_factor_replay


class LongCycleFactorReplayCliTests(unittest.TestCase):
    def test_run_long_cycle_factor_replay_writes_blocked_pack_for_short_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            bars = root / "bars.csv"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                        "top_n": 50,
                        "cost_bps": 10,
                        "sharpe": 4.2,
                        "source_report": "fixture",
                    }
                ]
            ).to_csv(candidates, index=False)
            pd.DataFrame(
                [
                    {"date": "2023-07-03", "asset_id": "CN_A", "market": "CN", "adj_close": 10.0},
                    {"date": "2024-01-02", "asset_id": "CN_A", "market": "CN", "adj_close": 11.0},
                ]
            ).to_csv(bars, index=False)

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                bars_csv=bars,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            self.assertEqual(pack["coverage"]["status"], "insufficient")
            self.assertEqual(pack["summary"]["candidates"], 1)
            self.assertTrue((output / "long_cycle_replay_pack.json").exists())
            self.assertTrue((output / "candidate_decisions.csv").exists())

    def test_run_long_cycle_factor_replay_can_use_manifest_instead_of_bars_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            manifest = root / "manifest.json"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                        "source_report": "fixture",
                    }
                ]
            ).to_csv(candidates, index=False)
            manifest.write_text(
                json.dumps(
                    {
                        "summary": {
                            "date_start": "2023-07-03",
                            "date_end": "2026-06-15",
                            "bar_rows": 8286202,
                            "bar_asset_ids": 5634,
                        }
                    }
                ),
                encoding="utf-8",
            )

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                manifest_json=manifest,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            self.assertEqual(pack["coverage"]["bar_rows"], 8286202)
            self.assertEqual(pack["coverage"]["asset_ids"], 5634)
            self.assertEqual(pack["coverage"]["status"], "insufficient")

    def test_run_long_cycle_factor_replay_accepts_utf8_sig_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            manifest = root / "manifest.json"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                    }
                ]
            ).to_csv(candidates, index=False)
            manifest.write_text(
                json.dumps(
                    {
                        "summary": {
                            "date_start": "2023-07-03",
                            "date_end": "2026-06-15",
                            "bar_rows": 8286202,
                            "bar_asset_ids": 5634,
                        }
                    }
                ),
                encoding="utf-8-sig",
            )

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                manifest_json=manifest,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            self.assertEqual(pack["coverage"]["bar_rows"], 8286202)

    def test_run_long_cycle_factor_replay_tags_candidate_csv_source_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            manifest = root / "manifest.json"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                    }
                ]
            ).to_csv(candidates, index=False)
            manifest.write_text(
                json.dumps(
                    {
                        "summary": {
                            "date_start": "2015-01-05",
                            "date_end": "2025-12-31",
                            "bar_rows": 8000000,
                            "bar_asset_ids": 5634,
                            "bar_trade_dates_by_year": {str(year): 230 for year in range(2015, 2026)},
                        }
                    }
                ),
                encoding="utf-8",
            )

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                manifest_json=manifest,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            decision = pack["candidate_decisions"][0]
            self.assertEqual(decision["source_kind"], "candidate_csv")
            self.assertEqual(decision["source_report"], str(candidates))

    def test_run_long_cycle_factor_replay_backfills_audit_fields_from_walk_forward_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "walk_forward_leaderboard.csv"
            manifest = root / "manifest.json"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                        "test_total_return": 0.12,
                        "test_sharpe": 0.8,
                        "cost_bps": 10,
                        "test_max_participation_rate": 0.004,
                        "test_overlap_autocorr_adjusted_sharpe": 0.7,
                    }
                ]
            ).to_csv(candidates, index=False)
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "fold": 1,
                        "train_start_date": "2018-01-02",
                        "train_end_date": "2018-12-31",
                        "test_start_date": "2019-01-02",
                        "test_end_date": "2019-03-29",
                    },
                    {
                        "case_id": "case_a",
                        "fold": 2,
                        "train_start_date": "2019-01-02",
                        "train_end_date": "2019-12-31",
                        "test_start_date": "2020-01-02",
                        "test_end_date": "2020-03-31",
                    },
                ]
            ).to_csv(root / "walk_forward_folds.csv", index=False)
            manifest.write_text(
                json.dumps(
                    {
                        "config": {
                            "experiment_grid": {
                                "execution_lag": 1,
                                "forward_horizon": 1,
                            }
                        },
                        "summary": {
                            "date_start": "2015-01-05",
                            "date_end": "2025-12-31",
                            "bar_rows": 8000000,
                            "bar_asset_ids": 5634,
                            "bar_trade_dates_by_year": {str(year): 230 for year in range(2015, 2026)},
                        },
                    }
                ),
                encoding="utf-8",
            )

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                manifest_json=manifest,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            decision = pack["candidate_decisions"][0]
            self.assertEqual(decision["execution_lag"], 1)
            self.assertEqual(decision["lookahead_audit_status"], "pass")
            self.assertEqual(decision["strict_split_status"], "pass")
            self.assertNotIn("execution_lag_missing", decision["reasons"])
            self.assertNotIn("strict_split_dates_missing", decision["reasons"])
            self.assertEqual(decision["train_start_date"], "2018-01-02")
            self.assertEqual(decision["train_end_date"], "2018-12-31")
            self.assertEqual(decision["test_start_date"], "2019-01-02")
            self.assertEqual(decision["test_end_date"], "2019-03-29")


if __name__ == "__main__":
    unittest.main()
