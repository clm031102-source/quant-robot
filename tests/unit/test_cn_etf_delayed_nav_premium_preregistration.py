from __future__ import annotations

import unittest

from quant_robot.ops.cn_etf_delayed_nav_premium_preregistration import (
    STATUS_READY,
    build_cn_etf_delayed_nav_premium_preregistration,
)


class CnEtfDelayedNavPremiumPreregistrationTests(unittest.TestCase):
    def test_ready_source_preregisters_exactly_one_candidate_without_label_permission(self):
        result = build_cn_etf_delayed_nav_premium_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="f" * 64,
        )

        self.assertEqual(result["status"], STATUS_READY)
        self.assertEqual(
            result["candidate"]["factor_name"],
            "etf_delayed_nav_premium_innovation_reversal_60",
        )
        self.assertEqual(result["candidate"]["hypothesis_count"], 1)
        self.assertEqual(result["evaluation"]["primary_horizon"], 1)
        self.assertEqual(result["evaluation"]["diagnostic_horizon"], 5)
        self.assertFalse(result["forward_return_read"])
        self.assertFalse(result["prescreen_execution_allowed"])
        self.assertFalse(result["broker_connection_allowed"])

    def test_blocked_source_cannot_preregister(self):
        source = _source_readiness()
        source["status"] = "blocked"
        source["gate"] = {"cleared": False, "blockers": ["fixture"]}

        result = build_cn_etf_delayed_nav_premium_preregistration(
            config=_config(),
            source_readiness=source,
            evidence_hashes=_evidence_hashes(),
            config_sha256="f" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("source_not_ready", result["summary"]["blockers"])

    def test_config_drift_in_candidate_or_boundary_blocks(self):
        config = _config()
        config["candidate"]["premium_lookback"] = 61
        result = build_cn_etf_delayed_nav_premium_preregistration(
            config=config,
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="f" * 64,
        )
        self.assertIn("candidate_contract_mismatch", result["summary"]["blockers"])

        config = _config()
        config["boundaries"]["final_holdout_allowed"] = True
        result = build_cn_etf_delayed_nav_premium_preregistration(
            config=config,
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="f" * 64,
        )
        self.assertIn(
            "boundary_enabled:final_holdout_allowed",
            result["summary"]["blockers"],
        )


def _config():
    return {
        "stage": "cn_etf_delayed_nav_premium_preregistration",
        "registration_date": "2026-07-29",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_nav_premium_relative_value",
        "candidate": {
            "factor_name": "etf_delayed_nav_premium_innovation_reversal_60",
            "hypothesis_count": 1,
            "premium_lookback": 60,
            "direction": "negative_innovation",
            "nav_availability_rule": "latest_known_from_lte_signal_date",
            "rolling_rule": "prior_60_complete_official_sessions_excluding_current",
        },
        "evaluation": {
            "horizons": [1, 5],
            "primary_horizon": 1,
            "diagnostic_horizon": 5,
            "execution_lag": 1,
        },
        "costs": {
            "one_way_costs_bps": [10.5, 26.6666666667, 60.0],
            "required_positive_net_spread_bps": 10.5,
        },
        "capacity": {
            "position_value_cny": 1000,
            "max_one_way_participation_rate": 0.01,
        },
        "source_evidence": {
            "required_status": "ready_for_nav_premium_preregistration",
        },
        "boundaries": {
            "forward_return_read_allowed": False,
            "factor_generation_allowed": False,
            "prescreen_execution_allowed": False,
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "final_holdout_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "live_trading_allowed": False,
            "live_boundary_allowed": False,
        },
    }


def _source_readiness():
    return {
        "stage": "cn_etf_tushare_nav_source_readiness",
        "status": "ready_for_nav_premium_preregistration",
        "gate": {"cleared": True, "blockers": []},
        "summary": {"nav_rows": 705081, "nav_assets": 1067},
    }


def _evidence_hashes():
    return {
        "source_config": "a" * 64,
        "source_result": "b" * 64,
        "request_manifest": "c" * 64,
        "canonical_nav": "d" * 64,
        "session_coverage": "e" * 64,
        "nav_agreement": "1" * 64,
        "small_capital_inputs": "2" * 64,
    }


if __name__ == "__main__":
    unittest.main()
