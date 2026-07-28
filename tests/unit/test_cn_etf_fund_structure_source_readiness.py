from __future__ import annotations

import unittest

import pandas as pd

from quant_robot.ops.cn_etf_fund_structure_source_readiness import (
    STATUS_READY,
    build_cn_etf_fund_structure_source_readiness,
)


class CnEtfFundStructureSourceReadinessTests(unittest.TestCase):
    def test_ready_packet_clears_frozen_source_gates_without_execution_permission(self) -> None:
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=_processed(),
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )

        self.assertEqual(result["status"], STATUS_READY)
        self.assertTrue(result["gate"]["cleared"])
        self.assertEqual(result["gate"]["blockers"], [])
        self.assertEqual(result["summary"]["analysis_sessions"], 5)
        self.assertEqual(result["summary"]["share_assets"], 80)
        self.assertEqual(result["coverage"]["combined_qualifying_date_coverage"], 1.0)
        self.assertEqual(result["coverage"]["exchange"]["SSE"]["date_coverage"], 1.0)
        self.assertEqual(result["coverage"]["exchange"]["SZSE"]["date_coverage"], 1.0)
        self.assertEqual(result["coverage"]["nav_intersection_coverage"], 1.0)
        for key in (
            "factor_generation_allowed",
            "forward_return_read",
            "portfolio_grid_allowed",
            "walk_forward_allowed",
            "final_holdout_allowed",
            "promotion_allowed",
            "paper_signal_allowed",
            "broker_connection_allowed",
            "account_read_allowed",
            "order_placement_allowed",
            "live_boundary_allowed",
        ):
            self.assertFalse(result[key], key)

    def test_combined_and_exchange_coverage_fail_closed(self) -> None:
        processed = _processed()
        first_date = processed["date"].min()
        processed = processed[
            ~((processed["exchange"] == "SZSE") & (processed["date"] != first_date))
        ].copy()

        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=processed,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("szse_share_date_coverage_below_minimum", result["gate"]["blockers"])

    def test_nav_intersection_and_positivity_fail_closed(self) -> None:
        processed = _processed()
        processed.loc[processed.index[:200], "nav"] = pd.NA
        processed.loc[processed.index[:200], "total_size"] = pd.NA
        processed.loc[processed.index[:200], "nav_premium_discount"] = pd.NA

        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=processed,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )

        self.assertIn("nav_intersection_coverage_below_minimum", result["gate"]["blockers"])

        processed = _processed()
        processed.loc[processed.index[:30], "total_share"] = 0.0
        processed.loc[processed.index[:30], "nav"] = 0.0
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=processed,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )
        self.assertIn("positive_share_ratio_below_minimum", result["gate"]["blockers"])
        self.assertIn("positive_nav_ratio_below_minimum", result["gate"]["blockers"])

    def test_duplicate_pit_and_holdout_rows_fail_closed(self) -> None:
        duplicate = pd.concat([_processed(), _processed().iloc[[0]]], ignore_index=True)
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=duplicate,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )
        self.assertIn("duplicate_processed_asset_date_rows", result["gate"]["blockers"])

        pit = _processed()
        pit.loc[pit.index[0], "known_from"] = pit.loc[pit.index[0], "date"]
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=pit,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )
        self.assertIn("known_from_not_after_observation_date", result["gate"]["blockers"])

        holdout = pd.concat(
            [
                _processed(),
                _processed().iloc[[0]].assign(
                    date=pd.Timestamp("2026-01-05").date(),
                    known_from=pd.Timestamp("2026-01-06").date(),
                ),
            ],
            ignore_index=True,
        )
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=holdout,
            bars=_bars(),
            request_manifest=_manifest(),
            configuration_sha256="a" * 64,
        )
        self.assertIn("processed_rows_outside_frozen_analysis_window", result["gate"]["blockers"])
        self.assertIn("final_holdout_rows_present", result["gate"]["blockers"])

    def test_failed_official_share_request_blocks_readiness(self) -> None:
        manifest = _manifest()
        manifest["requests"]["sse:2024-01-03"] = {
            "kind": "sse_share",
            "status": "failed",
            "error_category": "request_failure",
        }
        result = build_cn_etf_fund_structure_source_readiness(
            config=_config(),
            processed=_processed(),
            bars=_bars(),
            request_manifest=manifest,
            configuration_sha256="a" * 64,
        )
        self.assertIn("official_share_requests_incomplete", result["gate"]["blockers"])

    def test_any_enabled_downstream_boundary_blocks_readiness(self) -> None:
        for key in _config()["boundaries"]:
            with self.subTest(key=key):
                config = _config()
                config["boundaries"][key] = True
                result = build_cn_etf_fund_structure_source_readiness(
                    config=config,
                    processed=_processed(),
                    bars=_bars(),
                    request_manifest=_manifest(),
                    configuration_sha256="a" * 64,
                )
                self.assertIn(f"boundary_enabled:{key}", result["gate"]["blockers"])


def _config() -> dict:
    return {
        "schema_version": 1,
        "stage": "cn_etf_fund_structure_source_readiness",
        "review_date": "2026-07-28",
        "market": "CN_ETF",
        "analysis": {
            "start_date": "2024-01-02",
            "end_date": "2024-01-08",
            "final_holdout_start": "2026-01-01",
        },
        "thresholds": {
            "minimum_combined_assets_per_date": 30,
            "minimum_combined_date_coverage": 0.8,
            "minimum_exchange_assets_per_date": 30,
            "minimum_exchange_date_coverage": 0.75,
            "minimum_median_share_asset_coverage": 0.5,
            "minimum_nav_intersection_coverage": 0.7,
            "minimum_positive_share_ratio": 0.95,
            "minimum_positive_nav_ratio": 0.95,
        },
        "boundaries": {
            "factor_generation_allowed": False,
            "forward_return_read": False,
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "final_holdout_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "live_boundary_allowed": False,
        },
    }


def _bars() -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=5, freq="B")
    rows = []
    for date in dates:
        for idx in range(40):
            for suffix, exchange, base in [("SH", "SSE", 510000), ("SZ", "SZSE", 159000)]:
                code = f"{base + idx:06d}"
                rows.append(
                    {
                        "date": date.date(),
                        "asset_id": f"CN_ETF_{'XSHG' if suffix == 'SH' else 'XSHE'}_{code}",
                        "symbol": f"{code}.{suffix}",
                        "exchange": exchange,
                        "close": 1.0 + idx / 100,
                        "source": "tushare_fund_daily",
                    }
                )
    return pd.DataFrame(rows)


def _processed() -> pd.DataFrame:
    bars = _bars()
    result = bars.copy()
    result["known_from"] = pd.to_datetime(result["date"]) + pd.Timedelta(days=1)
    result["known_from"] = result["known_from"].dt.date
    result["total_share"] = 1_000_000.0
    result["nav"] = 1.0
    result["total_size"] = result["total_share"] * result["nav"]
    result["nav_premium_discount"] = result["close"] / result["nav"] - 1.0
    result["share_source"] = result["exchange"].map(
        {"SSE": "sse_official_etf_scale", "SZSE": "szse_official_fund_scale"}
    )
    result["nav_source"] = "eastmoney_fund_detail_history"
    result["close_source"] = "tushare_fund_daily"
    return result


def _manifest() -> dict:
    requests = {}
    for date in pd.date_range("2024-01-02", periods=5, freq="B"):
        requests[f"sse:{date.date()}"] = {"kind": "sse_share", "status": "completed"}
    requests["szse:2024-01-02:2024-01-08"] = {
        "kind": "szse_share",
        "status": "completed",
    }
    for idx in range(80):
        requests[f"nav:{idx}"] = {"kind": "eastmoney_nav", "status": "completed"}
    return {"schema_version": 1, "requests": requests}


if __name__ == "__main__":
    unittest.main()
