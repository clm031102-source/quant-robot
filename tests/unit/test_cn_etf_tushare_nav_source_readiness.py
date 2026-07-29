from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.cn_etf_tushare_nav_source_readiness import (
    STATUS_READY,
    build_cn_etf_tushare_nav_source_readiness,
    write_cn_etf_tushare_nav_source_readiness,
)


class CnEtfTushareNavSourceReadinessTests(unittest.TestCase):
    def test_ready_fixture_clears_frozen_gates_without_execution_permission(self):
        result = _evaluate()

        self.assertEqual(result["status"], STATUS_READY)
        self.assertTrue(result["gate"]["cleared"])
        self.assertEqual(result["gate"]["blockers"], [])
        self.assertEqual(result["summary"]["nav_assets"], 30)
        self.assertEqual(result["coverage"]["usable_session_coverage"], 1.0)
        self.assertEqual(result["agreement"]["within_10bp_ratio"], 1.0)
        for key, value in result["boundaries"].items():
            self.assertFalse(value, key)

    def test_failed_or_unresolved_request_blocks(self):
        manifest = _manifest()
        manifest["requests"]["510000.SH"]["status"] = "failed"
        result = _evaluate(request_manifest=manifest)
        self.assertIn("fund_nav_requests_failed", result["gate"]["blockers"])

        manifest = _manifest()
        del manifest["requests"]["510000.SH"]
        result = _evaluate(request_manifest=manifest)
        self.assertIn("fund_nav_requests_unresolved", result["gate"]["blockers"])

    def test_duplicate_outside_window_and_holdout_rows_block(self):
        duplicate = pd.concat([_nav(), _nav().iloc[[0]]], ignore_index=True)
        result = _evaluate(nav=duplicate)
        self.assertIn("duplicate_nav_asset_date_rows", result["gate"]["blockers"])

        outside = pd.concat(
            [
                _nav(),
                _nav().iloc[[0]].assign(
                    nav_date=pd.Timestamp("2025-01-02").date(),
                    ann_date=pd.Timestamp("2025-01-02").date(),
                    known_from=pd.Timestamp("2025-01-03").date(),
                ),
            ],
            ignore_index=True,
        )
        result = _evaluate(nav=outside)
        self.assertIn("nav_rows_outside_frozen_analysis_window", result["gate"]["blockers"])

        holdout = pd.concat(
            [
                _nav(),
                _nav().iloc[[0]].assign(
                    nav_date=pd.Timestamp("2026-01-02").date(),
                    ann_date=pd.Timestamp("2026-01-02").date(),
                    known_from=pd.Timestamp("2026-01-05").date(),
                ),
            ],
            ignore_index=True,
        )
        result = _evaluate(nav=holdout)
        self.assertIn("final_holdout_rows_present", result["gate"]["blockers"])

    def test_announcement_ratio_and_known_from_fail_closed(self):
        nav = _nav()
        nav.loc[nav.index[:2], "ann_date"] = pd.Timestamp("2023-12-29").date()
        nav.loc[nav.index[:2], "known_from"] = pd.NaT
        nav.loc[nav.index[:2], "is_pit_usable"] = False
        result = _evaluate(nav=nav)
        self.assertIn("valid_announcement_ratio_below_minimum", result["gate"]["blockers"])

        nav = _nav()
        nav.loc[nav.index[0], "known_from"] = nav.loc[nav.index[0], "ann_date"]
        result = _evaluate(nav=nav)
        self.assertIn("known_from_not_strictly_after_nav_and_announcement", result["gate"]["blockers"])

    def test_positive_nav_and_session_coverage_fail_closed(self):
        nav = _nav()
        nav.loc[nav.index[0], "unit_nav"] = 0.0
        nav.loc[nav.index[0], "is_pit_usable"] = False
        result = _evaluate(nav=nav)
        self.assertIn("positive_unit_nav_ratio_below_minimum", result["gate"]["blockers"])

        nav = _nav()
        removed_dates = sorted(nav["nav_date"].unique())[-2:]
        nav = nav[~nav["nav_date"].isin(removed_dates)].copy()
        public = _public_nav()
        public = public[~public["date"].isin(removed_dates)].copy()
        result = _evaluate(nav=nav, public_nav=public)
        self.assertIn("usable_session_coverage_below_minimum", result["gate"]["blockers"])

    def test_public_intersection_asset_match_and_agreement_fail_closed(self):
        nav = _nav()
        removed_assets = sorted(nav["asset_id"].unique())[-4:]
        nav = nav[~nav["asset_id"].isin(removed_assets)]
        result = _evaluate(nav=nav)
        self.assertIn("public_nav_key_intersection_below_minimum", result["gate"]["blockers"])
        self.assertIn("public_nav_asset_match_below_minimum", result["gate"]["blockers"])

        public = _public_nav()
        public.loc[public.index[:2], "nav"] *= 1.002
        result = _evaluate(public_nav=public)
        self.assertIn("nav_agreement_within_10bp_below_minimum", result["gate"]["blockers"])

        public = _public_nav()
        public.loc[public.index[0], "nav"] *= 1.10
        result = _evaluate(public_nav=public)
        self.assertIn("severe_nav_disagreement_above_maximum", result["gate"]["blockers"])

    def test_forbidden_column_and_enabled_boundary_block(self):
        nav = _nav()
        nav["forward_return_1d"] = 0.01
        result = _evaluate(nav=nav)
        self.assertIn("forbidden_analytical_columns_present", result["gate"]["blockers"])

        config = _config()
        config["boundaries"]["broker_connection_allowed"] = True
        result = _evaluate(config=config)
        self.assertIn(
            "boundary_enabled:broker_connection_allowed",
            result["gate"]["blockers"],
        )

    def test_writer_emits_deterministic_lightweight_artifacts(self):
        result = _evaluate()
        with TemporaryDirectory() as directory:
            paths = write_cn_etf_tushare_nav_source_readiness(directory, result)

            self.assertEqual(
                set(paths),
                {
                    "json",
                    "markdown",
                    "request_states_csv",
                    "nav_agreement_summary_csv",
                    "session_coverage_csv",
                },
            )
            self.assertTrue(all(Path(path).exists() for path in paths.values()))
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
            self.assertIn("No return, factor, portfolio, paper signal, broker", markdown)


def _evaluate(**overrides):
    kwargs = {
        "config": _config(),
        "nav": _nav(),
        "request_manifest": _manifest(),
        "public_nav": _public_nav(),
        "official_sessions": pd.date_range("2024-01-02", "2024-01-09", freq="B"),
        "configuration_sha256": "a" * 64,
    }
    kwargs.update(overrides)
    return build_cn_etf_tushare_nav_source_readiness(**kwargs)


def _config():
    return {
        "schema_version": 1,
        "stage": "cn_etf_tushare_nav_source_readiness",
        "review_date": "2026-07-29",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_nav_premium_relative_value",
        "analysis": {
            "start_date": "2024-01-02",
            "end_date": "2024-01-08",
            "final_holdout_start": "2026-01-01",
        },
        "thresholds": {
            "minimum_terminal_request_ratio": 1.0,
            "minimum_valid_announcement_ratio": 0.99,
            "minimum_positive_unit_nav_ratio": 0.999,
            "minimum_public_key_intersection_ratio": 0.90,
            "minimum_public_asset_match_ratio": 0.90,
            "minimum_within_10bp_ratio": 0.99,
            "maximum_severe_disagreement_ratio": 0.001,
            "severe_disagreement_threshold": 0.05,
            "minimum_usable_assets_per_session": 30,
            "minimum_usable_session_coverage": 0.80,
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


def _nav():
    rows = []
    dates = pd.date_range("2024-01-02", "2024-01-08", freq="B")
    for date in dates:
        next_session = pd.offsets.BDay().rollforward(date + pd.Timedelta(days=1))
        for index in range(30):
            code = f"{510000 + index:06d}"
            rows.append(
                {
                    "nav_date": date.date(),
                    "ann_date": date.date(),
                    "known_from": next_session.date(),
                    "asset_id": f"CN_ETF_XSHG_{code}",
                    "symbol": f"{code}.SH",
                    "exchange": "XSHG",
                    "unit_nav": 1.0 + index / 1000,
                    "accum_nav": 1.0 + index / 1000,
                    "total_netasset": 100_000_000.0,
                    "update_flag": 1.0,
                    "is_pit_usable": True,
                    "source": "tushare_fund_nav",
                }
            )
    return pd.DataFrame(rows)


def _public_nav():
    return _nav()[["nav_date", "asset_id", "unit_nav"]].rename(
        columns={"nav_date": "date", "unit_nav": "nav"}
    )


def _manifest():
    symbols = sorted(_nav()["symbol"].unique())
    return {
        "schema_version": 1,
        "scope": {"symbols": symbols},
        "requests": {
            symbol: {
                "status": "completed",
                "rows": 5,
                "request_sha256": "a" * 64,
                "response_sha256": "b" * 64,
            }
            for symbol in symbols
        },
        "boundaries": _config()["boundaries"],
    }


if __name__ == "__main__":
    unittest.main()
