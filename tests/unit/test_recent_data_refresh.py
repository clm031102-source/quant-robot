import json
import unittest

from quant_robot.ops.recent_data_refresh import build_recent_data_refresh_pack


class RecentDataRefreshTests(unittest.TestCase):
    def test_execute_blocks_when_tushare_readiness_is_missing(self):
        profile_observation = {
            "stage": "phase_5_6_profile_observation_ledger",
            "run_date": "2026-06-14",
            "decision": {
                "observation_status": "stopped",
                "paper_observation_allowed": False,
                "stop_reasons": ["signal_data_stale"],
            },
            "ledger": [
                {
                    "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                    "signal_date": "2026-05-22",
                    "profile_id": "cap60_guard12_cd3",
                    "risk_tier": "aggressive_growth",
                }
            ],
        }

        pack = build_recent_data_refresh_pack(
            profile_observation,
            readiness={"ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
            execute=True,
            source="tushare",
            market="CN_ETF",
            output_dir="data/processed/tushare_etf_recent",
        )

        self.assertEqual(pack["stage"], "phase_5_7_tushare_recent_data_refresh")
        self.assertEqual(pack["status"], "blocked")
        self.assertFalse(pack["will_download"])
        self.assertFalse(pack["decision"]["signal_data_stale_cleared"])
        self.assertIn("TUSHARE_TOKEN is not set", pack["decision"]["blockers"])
        self.assertEqual(pack["target_window"]["start_date"], "2026-05-23")
        self.assertEqual(pack["target_window"]["end_date"], "2026-06-14")
        self.assertEqual(pack["next_actions"][0]["action"], "set_tushare_token_env")
        serialized = json.dumps(pack, ensure_ascii=False)
        self.assertNotIn("4743", serialized)

    def test_completed_refresh_clears_stale_signal_when_coverage_reaches_run_date(self):
        profile_observation = {
            "run_date": "2026-06-14",
            "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
        }
        ingest_result = {
            "source": "tushare",
            "market": "CN_ETF",
            "downloaded_trade_dates": ["20260523", "20260614"],
            "skipped_trade_dates": [],
            "processed_rows": 4,
            "quality_report": {
                "rows": 4,
                "assets": 2,
                "start_date": "2026-05-23",
                "end_date": "2026-06-14",
                "missing_date_rows": 0,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
            },
        }

        pack = build_recent_data_refresh_pack(
            profile_observation,
            readiness={"ready": True, "missing": []},
            ingest_result=ingest_result,
            execute=True,
            source="tushare-fixture",
            market="CN_ETF",
            output_dir="data/processed/tushare_etf_recent",
        )

        self.assertEqual(pack["status"], "completed")
        self.assertTrue(pack["decision"]["signal_data_stale_cleared"])
        self.assertEqual(pack["coverage"]["coverage_status"], "pass")
        self.assertEqual(pack["next_actions"][0]["action"], "rerun_daily_ops_on_refreshed_data")
        self.assertFalse(pack["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()

