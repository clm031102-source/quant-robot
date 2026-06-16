import json
import unittest

from quant_robot.ops.recent_data_refresh import build_recent_data_refresh_pack


class RecentDataRefreshTests(unittest.TestCase):
    WORKSTATION_CONFIG = {
        "machines": {
            "laptop": {"allowed_tasks": ["architecture_ops", "factor_smoke", "factor_review", "project_sync"]},
            "highspec_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
            "office_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
        },
        "tasks": {"data_pipeline": {"branch": "codex/tushare-data-pipeline"}},
    }

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

    def test_laptop_ready_refresh_hands_off_to_data_pipeline_workstations(self):
        profile_observation = {
            "run_date": "2026-06-14",
            "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
        }

        pack = build_recent_data_refresh_pack(
            profile_observation,
            readiness={"ready": True, "missing": []},
            execute=False,
            source="tushare",
            market="CN_ETF",
            output_dir="data/processed/tushare_etf_recent",
            machine="laptop",
            workstation_config=self.WORKSTATION_CONFIG,
        )

        self.assertEqual(pack["status"], "ready_to_execute")
        self.assertEqual(pack["workstation"]["machine"], "laptop")
        self.assertFalse(pack["workstation"]["can_run_data_pipeline"])
        self.assertEqual(pack["workstation"]["data_pipeline_machines"], ["highspec_desktop", "office_desktop"])
        self.assertEqual(pack["next_actions"][0]["action"], "handoff_recent_tushare_refresh")
        self.assertEqual(pack["next_actions"][0]["recommended_machines"], ["highspec_desktop", "office_desktop"])
        self.assertNotIn("execute_recent_tushare_refresh", [row["action"] for row in pack["next_actions"]])

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

    def test_refresh_can_clear_when_required_assets_cover_trading_window(self):
        profile_observation = {
            "run_date": "2026-06-14",
            "observed_assets": ["CN_ETF_XSHG_516160"],
            "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
        }
        ingest_result = {
            "source": "tushare",
            "market": "CN_ETF",
            "downloaded_trade_dates": [],
            "skipped_trade_dates": [
                "20260525",
                "20260526",
                "20260527",
                "20260528",
                "20260529",
                "20260601",
                "20260602",
                "20260603",
                "20260604",
                "20260605",
                "20260608",
                "20260609",
                "20260610",
                "20260611",
                "20260612",
            ],
            "processed_rows": 30106,
            "quality_report": {
                "rows": 30106,
                "assets": 2043,
                "start_date": "2026-05-25",
                "end_date": "2026-06-12",
                "missing_date_rows": 226,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
                "coverage_by_asset": [
                    {
                        "asset_id": "CN_ETF_XSHG_516160",
                        "rows": 15,
                        "start_date": "2026-05-25",
                        "end_date": "2026-06-12",
                    },
                    {
                        "asset_id": "CN_ETF_XSHG_589330",
                        "rows": 11,
                        "start_date": "2026-05-29",
                        "end_date": "2026-06-12",
                    },
                ],
            },
        }

        pack = build_recent_data_refresh_pack(
            profile_observation,
            readiness={"ready": True, "missing": []},
            ingest_result=ingest_result,
            execute=True,
            source="tushare",
            market="CN_ETF",
            output_dir="data/processed/tushare_etf_recent",
        )

        self.assertEqual(pack["status"], "completed")
        self.assertEqual(pack["coverage"]["coverage_status"], "pass")
        self.assertEqual(pack["coverage"]["coverage_scope"], "required_assets")
        self.assertEqual(pack["coverage"]["required_asset_ids"], ["CN_ETF_XSHG_516160"])
        self.assertEqual(pack["coverage"]["provider_missing_date_rows"], 226)
        self.assertNotIn("missing_date_rows", pack["decision"]["blockers"])

    def test_refresh_blocks_when_required_asset_misses_trade_date_inside_window(self):
        profile_observation = {
            "run_date": "2026-05-27",
            "observed_assets": ["CN_ETF_XSHG_516160"],
            "ledger": [{"signal_date": "2026-05-24", "profile_id": "cap60_guard12_cd3"}],
        }
        ingest_result = {
            "source": "tushare",
            "market": "CN_ETF",
            "downloaded_trade_dates": ["20260525", "20260526", "20260527"],
            "skipped_trade_dates": [],
            "processed_rows": 2,
            "quality_report": {
                "rows": 2,
                "assets": 1,
                "start_date": "2026-05-25",
                "end_date": "2026-05-27",
                "missing_date_rows": 0,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
                "coverage_by_asset": [
                    {
                        "asset_id": "CN_ETF_XSHG_516160",
                        "rows": 2,
                        "start_date": "2026-05-25",
                        "end_date": "2026-05-27",
                    }
                ],
            },
        }

        pack = build_recent_data_refresh_pack(
            profile_observation,
            readiness={"ready": True, "missing": []},
            ingest_result=ingest_result,
            execute=True,
            source="tushare",
            market="CN_ETF",
            output_dir="data/processed/tushare_etf_recent",
        )

        self.assertEqual(pack["status"], "data_quality_blocked")
        self.assertEqual(pack["coverage"]["coverage_status"], "fail")
        self.assertFalse(pack["coverage"]["required_assets_covered"])
        self.assertEqual(pack["coverage"]["missing_date_rows"], 1)
        self.assertIn("missing_date_rows", pack["decision"]["blockers"])
        self.assertIn("required_assets_not_covered", pack["decision"]["blockers"])


if __name__ == "__main__":
    unittest.main()
