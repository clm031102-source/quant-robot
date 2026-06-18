import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.long_cycle_replay import (
    build_candidate_registry,
    build_long_cycle_coverage,
    build_long_cycle_coverage_from_manifest,
    build_long_cycle_replay_pack,
    write_long_cycle_replay_pack,
)


class LongCycleReplayTests(unittest.TestCase):
    def test_registry_deduplicates_candidates_and_preserves_parameters(self):
        rows = [
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 10,
                "forward_horizon": 20,
                "source_report": "report_a",
            },
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 20,
                "forward_horizon": 20,
                "source_report": "report_b",
            },
        ]

        registry = build_candidate_registry(rows)

        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]["case_id"], "case_a")
        self.assertEqual(registry[0]["market"], "CN")
        self.assertEqual(registry[0]["frozen_parameters"]["top_n"], 50)
        self.assertEqual(registry[0]["source_reports"], ["report_a", "report_b"])

    def test_coverage_blocks_when_available_history_starts_after_required_cycle(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )

        coverage = build_long_cycle_coverage(bars, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("history_starts_after_required_cycle_start", coverage["blockers"])
        self.assertEqual(coverage["date_start"], "2023-07-03")

    def test_coverage_can_be_built_from_data_manifest_summary(self):
        manifest = {
            "summary": {
                "date_start": "2023-07-03",
                "date_end": "2026-06-15",
                "bar_rows": 8286202,
                "bar_asset_ids": 5634,
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertEqual(coverage["bar_rows"], 8286202)
        self.assertEqual(coverage["asset_ids"], 5634)
        self.assertIn("history_starts_after_required_cycle_start", coverage["blockers"])

    def test_coverage_blocks_discontinuous_or_thin_years(self):
        bars = pd.DataFrame(
            {
                "date": [
                    "2015-01-05",
                    "2015-01-06",
                    "2023-07-03",
                    "2024-01-02",
                    "2025-01-02",
                    "2026-06-15",
                ],
                "asset_id": ["CN_A"] * 6,
                "market": ["CN"] * 6,
                "adj_close": [10.0, 10.1, 11.0, 12.0, 13.0, 14.0],
            }
        )

        coverage = build_long_cycle_coverage(bars, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("missing_required_years", coverage["blockers"])
        self.assertIn("thin_required_years", coverage["blockers"])
        self.assertEqual(coverage["missing_years"], [2016, 2017, 2018, 2019, 2020, 2021, 2022])

    def test_manifest_coverage_blocks_missing_years_even_when_start_date_is_old(self):
        manifest = {
            "summary": {
                "date_start": "2015-01-05",
                "date_end": "2026-06-15",
                "bar_rows": 1200000,
                "bar_asset_ids": 5634,
                "bar_trade_dates_by_year": {
                    "2015": 20,
                    "2023": 120,
                    "2024": 242,
                    "2025": 242,
                    "2026": 110,
                },
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("missing_required_years", coverage["blockers"])
        self.assertIn("thin_required_years", coverage["blockers"])
        self.assertEqual(coverage["missing_years"], [2016, 2017, 2018, 2019, 2020, 2021, 2022])

    def test_manifest_coverage_accepts_continuous_full_year_history(self):
        manifest = {
            "summary": {
                "date_start": "2015-01-05",
                "date_end": "2026-06-15",
                "bar_rows": 8000000,
                "bar_asset_ids": 5634,
                "bar_trade_dates_by_year": {str(year): 230 for year in range(2015, 2026)} | {"2026": 110},
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "sufficient")
        self.assertEqual(coverage["blockers"], [])

    def test_replay_pack_marks_candidates_research_only_when_coverage_is_short(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )
        candidates = [{"case_id": "case_a", "market": "CN", "factor_name": "factor_x", "sharpe": 4.2}]

        pack = build_long_cycle_replay_pack(candidates, bars, market="CN", required_start="2015-01-01")

        self.assertEqual(pack["stage"], "long_cycle_factor_replay")
        self.assertEqual(pack["coverage"]["status"], "insufficient")
        self.assertEqual(pack["summary"]["candidates"], 1)
        self.assertEqual(pack["candidate_decisions"][0]["decision_status"], "research_lead")
        self.assertIn("long_cycle_coverage_insufficient", pack["candidate_decisions"][0]["reasons"])
        self.assertIn("high_sharpe_overfit_warning", pack["candidate_decisions"][0]["reasons"])

    def test_writer_emits_json_markdown_and_csv_artifacts(self):
        pack = {
            "stage": "long_cycle_factor_replay",
            "summary": {"candidates": 1},
            "coverage": {"status": "insufficient"},
            "candidate_registry": [{"case_id": "case_a"}],
            "candidate_decisions": [{"case_id": "case_a", "decision_status": "research_lead"}],
            "markdown": "# Long-Cycle Factor Replay\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            write_long_cycle_replay_pack(tmp, pack)

            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.json").exists())
            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.md").exists())
            self.assertTrue((Path(tmp) / "candidate_registry.csv").exists())
            self.assertTrue((Path(tmp) / "candidate_decisions.csv").exists())


if __name__ == "__main__":
    unittest.main()
