import unittest

import pandas as pd

from scripts.run_required_asset_target_end_check import (
    asset_id_to_tushare_symbol,
    build_required_asset_target_end_check,
)


class FakeTargetEndAdapter:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.trade_dates: list[str] = []

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        self.trade_dates.append(trade_date)
        return self.frame.copy()


class RequiredAssetTargetEndCheckTests(unittest.TestCase):
    def test_asset_id_to_tushare_symbol_maps_cn_etf_exchange_suffix(self) -> None:
        self.assertEqual(asset_id_to_tushare_symbol("CN_ETF_XSHE_160615"), "160615.SZ")
        self.assertEqual(asset_id_to_tushare_symbol("CN_ETF_XSHG_510300"), "510300.SH")

    def test_execute_reports_target_end_missing_when_provider_lacks_required_asset(self) -> None:
        adapter = FakeTargetEndAdapter(pd.DataFrame({"symbol": ["510300.SH", "159915.SZ"]}))

        pack = build_required_asset_target_end_check(
            recent_data_refresh_pack=_target_gap_pack(),
            recent_data_refresh_pack_path="data/reports/round491/recent_data_refresh_pack.json",
            machine="office_desktop",
            task="data_pipeline",
            current_branch="codex/factor-batch-current",
            python_executable="python",
            execute=True,
            adapter=adapter,
        )

        self.assertEqual(pack["status"], "target_end_missing")
        self.assertEqual(adapter.trade_dates, ["2026-07-03"])
        self.assertEqual(pack["provider_checks"][0]["asset_id"], "CN_ETF_XSHE_160615")
        self.assertEqual(pack["provider_checks"][0]["symbol"], "160615.SZ")
        self.assertEqual(pack["provider_checks"][0]["target_rows"], 0)
        self.assertEqual(pack["next_actions"][0]["action"], "recheck_required_asset_target_end")

    def test_execute_reports_available_and_emits_refresh_command_when_provider_has_required_asset(self) -> None:
        adapter = FakeTargetEndAdapter(pd.DataFrame({"symbol": ["160615.SZ", "510300.SH"]}))

        pack = build_required_asset_target_end_check(
            recent_data_refresh_pack=_target_gap_pack(),
            recent_data_refresh_pack_path="data/reports/round491/recent_data_refresh_pack.json",
            profile_observation_pack_path="data/reports/round478/profile_observation/profile_observation_pack.json",
            machine="office_desktop",
            task="data_pipeline",
            current_branch="codex/factor-batch-current",
            python_executable="python",
            output_dir="data/processed/round494_retry",
            report_dir="data/reports/round494_recent_refresh",
            execute=True,
            adapter=adapter,
        )

        self.assertEqual(pack["status"], "target_end_available")
        self.assertEqual(pack["provider_checks"][0]["target_rows"], 1)
        self.assertEqual(pack["next_actions"][0]["action"], "run_recent_refresh_to_target_end")
        self.assertEqual(
            pack["next_actions"][0]["command"],
            (
                "python scripts/run_recent_data_refresh.py --machine office_desktop "
                "--profile-observation-pack data/reports/round478/profile_observation/profile_observation_pack.json "
                "--start-date 2026-05-06 --end-date 2026-07-03 "
                "--output-dir data/processed/round494_retry --report-dir data/reports/round494_recent_refresh --execute"
            ),
        )


def _target_gap_pack() -> dict:
    return {
        "status": "data_quality_blocked",
        "target_window": {"start_date": "2026-05-06", "end_date": "2026-07-03"},
        "coverage": {
            "target_start_covered": True,
            "target_end_covered": False,
            "required_asset_coverage": [
                {
                    "asset_id": "CN_ETF_XSHE_160615",
                    "target_start_covered": True,
                    "target_end_covered": False,
                    "end_date": "2026-07-02",
                }
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
