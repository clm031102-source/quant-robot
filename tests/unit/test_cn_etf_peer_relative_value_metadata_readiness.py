import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_etf_peer_relative_value_metadata_readiness import (
    STAGE,
    summarize_cn_etf_peer_relative_value_metadata_readiness,
    write_cn_etf_peer_relative_value_metadata_readiness,
)


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"asset_id": "CN_ETF_A", "date": "2024-01-02", "close": 1.00},
            {"asset_id": "CN_ETF_B", "date": "2024-01-02", "close": 1.01},
            {"asset_id": "CN_ETF_A", "date": "2024-01-03", "close": 1.02},
            {"asset_id": "CN_ETF_B", "date": "2024-01-03", "close": 1.00},
        ]
    )


def _official_peer_mapping(*, known_from: str = "2023-12-01") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asset_id": "CN_ETF_A",
                "peer_id": "CSI300",
                "valid_from": "2023-01-01",
                "valid_to": None,
                "known_from": known_from,
                "mapping_method": "official_index_code",
                "source": "official_provider",
            },
            {
                "asset_id": "CN_ETF_B",
                "peer_id": "CSI300",
                "valid_from": "2023-01-01",
                "valid_to": None,
                "known_from": known_from,
                "mapping_method": "official_index_code",
                "source": "official_provider",
            },
        ]
    )


class CnEtfPeerRelativeValueMetadataReadinessTests(unittest.TestCase):
    def test_blocks_current_name_snapshot_without_historical_official_peer_mapping(self):
        fund_basic = pd.DataFrame(
            [
                {
                    "symbol": "510300.SH",
                    "name": "沪深300ETF",
                    "market": "E",
                    "is_etf": True,
                    "fund_type": "股票型",
                    "type": "ETF",
                    "list_date": "2012-05-28",
                    "delist_date": None,
                }
            ]
        )

        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=fund_basic,
            fund_basic_snapshot_dates=["2026-06-21"],
            peer_mapping=pd.DataFrame(),
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("missing_dedicated_peer_mapping", result["gate"]["blockers"])
        self.assertIn("official_peer_identifier_missing", result["gate"]["blockers"])
        self.assertIn("historical_peer_membership_unavailable", result["gate"]["blockers"])
        self.assertIn("fund_basic_snapshot_after_analysis_window", result["gate"]["blockers"])
        self.assertFalse(result["gate"]["metadata_gate_cleared"])
        self.assertFalse(result["prescreen_preregistration_allowed"])
        self.assertFalse(result["prescreen_execution_allowed"])
        self.assertFalse(result["heuristic_name_theme_map"]["accepted_for_gate"])
        self.assertIn("historical_nav_missing", result["capability_gaps"])
        self.assertIn("historical_share_size_missing", result["capability_gaps"])

    def test_official_point_in_time_mapping_clears_metadata_gate_only(self):
        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=_official_peer_mapping(),
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["status"], "ready_for_preregistration")
        self.assertEqual(result["gate"]["blockers"], [])
        self.assertTrue(result["gate"]["metadata_gate_cleared"])
        self.assertEqual(result["peer_mapping"]["eligible_asset_date_coverage"], 1.0)
        self.assertEqual(result["peer_mapping"]["qualifying_date_coverage"], 1.0)
        self.assertEqual(result["peer_mapping"]["qualifying_peer_groups"], 2)
        self.assertTrue(result["feature_channels"]["peer_price_dislocation"]["data_ready"])
        self.assertFalse(result["feature_channels"]["price_nav_relative_value"]["data_ready"])
        self.assertTrue(result["prescreen_preregistration_allowed"])
        self.assertFalse(result["prescreen_execution_allowed"])

    def test_missing_close_values_block_price_readiness(self):
        bars = _bars()
        bars["close"] = pd.NA

        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=bars,
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=_official_peer_mapping(),
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("historical_close_unavailable", result["gate"]["blockers"])
        self.assertFalse(result["bars"]["close_available"])
        self.assertFalse(result["feature_channels"]["peer_price_dislocation"]["data_ready"])

    def test_name_only_mapping_is_rejected_even_with_full_coverage(self):
        mapping = _official_peer_mapping()
        mapping["mapping_method"] = "name_keyword"
        mapping["source"] = "current_fund_name"

        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=mapping,
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("prohibited_name_only_peer_mapping", result["gate"]["blockers"])
        self.assertIn("unapproved_peer_mapping_method", result["gate"]["blockers"])

    def test_mapping_known_after_analysis_window_has_zero_usable_coverage(self):
        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=_official_peer_mapping(known_from="2026-06-21"),
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["peer_mapping"]["eligible_asset_date_coverage"], 0.0)
        self.assertIn("peer_mapping_date_coverage_below_minimum", result["gate"]["blockers"])

    def test_overlapping_active_peer_assignments_fail_closed(self):
        mapping = pd.concat(
            [
                _official_peer_mapping(),
                _official_peer_mapping().iloc[[0]].assign(peer_id="CSI500"),
            ],
            ignore_index=True,
        )

        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=mapping,
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("overlapping_active_peer_assignments", result["gate"]["blockers"])
        self.assertGreater(result["peer_mapping"]["ambiguous_asset_dates"], 0)

    def test_writer_emits_machine_and_human_readable_artifacts(self):
        result = summarize_cn_etf_peer_relative_value_metadata_readiness(
            bars=_bars(),
            fund_basic=pd.DataFrame(),
            fund_basic_snapshot_dates=[],
            peer_mapping=_official_peer_mapping(),
            share_size=pd.DataFrame(),
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-01-03",
            min_qualifying_assets_per_date=2,
        )

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cn_etf_peer_relative_value_metadata_readiness(tmp, result)

            self.assertEqual(set(paths), {"json", "markdown", "coverage_csv", "peer_groups_csv"})
            self.assertTrue(all(path.exists() for path in paths.values()))
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ready_for_preregistration")


if __name__ == "__main__":
    unittest.main()
