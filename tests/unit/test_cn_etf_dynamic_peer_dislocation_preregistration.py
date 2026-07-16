import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_etf_dynamic_peer_dislocation_preregistration import (
    build_cn_etf_dynamic_peer_dislocation_preregistration,
    write_cn_etf_dynamic_peer_dislocation_preregistration,
)


class CnEtfDynamicPeerDislocationPreregistrationTests(unittest.TestCase):
    def test_ready_source_builds_one_candidate_without_execution_permission(self) -> None:
        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="d" * 64,
        )

        self.assertEqual(result["status"], "preregistered_single_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(result["summary"]["hypothesis_count"], 2)
        self.assertEqual(result["summary"]["primary_horizon"], 5)
        self.assertEqual(result["summary"]["diagnostic_horizon"], 20)
        self.assertEqual(result["summary"]["blockers"], [])
        self.assertFalse(result["forward_return_read_allowed"])
        self.assertFalse(result["factor_generation_allowed"])
        self.assertFalse(result["prescreen_execution_allowed"])
        self.assertFalse(result["portfolio_grid_allowed"])
        self.assertFalse(result["walk_forward_allowed"])
        self.assertFalse(result["final_holdout_allowed"])
        self.assertFalse(result["paper_signal_allowed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_source_status_fails_closed(self) -> None:
        source = _source_readiness()
        source["status"] = "blocked"

        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=source,
            evidence_hashes=_evidence_hashes(),
            config_sha256="d" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "dynamic_peer_source_not_ready_for_preregistration",
            result["summary"]["blockers"],
        )

    def test_source_factor_generation_boundary_fails_closed(self) -> None:
        source = _source_readiness()
        source["source_boundaries"]["factor_values_calculated"] = True

        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=source,
            evidence_hashes=_evidence_hashes(),
            config_sha256="d" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "dynamic_peer_source_factor_values_already_calculated",
            result["summary"]["blockers"],
        )

    def test_source_hash_mismatch_fails_closed(self) -> None:
        hashes = _evidence_hashes()
        hashes["source_result"] = "e" * 64

        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=hashes,
            config_sha256="d" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "source_evidence_hash_mismatch:source_result",
            result["summary"]["blockers"],
        )

    def test_frozen_horizon_and_execution_contract_fails_closed(self) -> None:
        mutations = (
            ("primary_horizon", 20, "primary_horizon_not_five"),
            ("diagnostic_horizon", 5, "diagnostic_horizon_not_twenty"),
            ("execution_lag", 0, "execution_lag_not_one"),
        )
        for field, value, expected_blocker in mutations:
            with self.subTest(field=field):
                config = _config()
                config["evaluation"][field] = value

                result = build_cn_etf_dynamic_peer_dislocation_preregistration(
                    config=config,
                    source_readiness=_source_readiness(),
                    evidence_hashes=_evidence_hashes(),
                    config_sha256="d" * 64,
                )

                self.assertEqual(result["status"], "blocked")
                self.assertIn(expected_blocker, result["summary"]["blockers"])

    def test_ready_packet_exposes_frozen_candidate_and_configuration_hash(self) -> None:
        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="d" * 64,
        )

        self.assertEqual(
            result["candidate"]["factor_name"],
            "etf_dynamic_peer_residual_dislocation_reversal_5_60",
        )
        self.assertEqual(result["configuration"]["sha256"], "d" * 64)
        self.assertEqual(
            result["next_direction"],
            "run_one_hash_bound_dynamic_peer_dislocation_prescreen",
        )

    def test_writer_emits_deterministic_json_markdown_and_candidate_csv(self) -> None:
        result = build_cn_etf_dynamic_peer_dislocation_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_evidence_hashes(),
            config_sha256="d" * 64,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            paths = write_cn_etf_dynamic_peer_dislocation_preregistration(output, result)
            first_json = paths["json"].read_bytes()
            first_csv = paths["candidate_csv"].read_bytes()

            paths = write_cn_etf_dynamic_peer_dislocation_preregistration(output, result)
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))

            self.assertEqual(paths["json"].read_bytes(), first_json)
            self.assertEqual(paths["candidate_csv"].read_bytes(), first_csv)
            self.assertNotIn("markdown", payload)
            self.assertIn("etf_dynamic_peer_residual_dislocation_reversal_5_60", first_csv.decode())
            self.assertIn("Preregistration", paths["markdown"].read_text(encoding="utf-8"))


def _config() -> dict:
    return {
        "stage": "cn_etf_dynamic_peer_dislocation_preregistration",
        "registration_date": "2026-07-16",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_dynamic_comovement_peer_dislocation",
        "source_evidence": {
            "required_status": "ready_for_peer_source_preregistration",
            "mapping_method": "lagged_market_residual_correlation_topk",
            "hashes": {
                "source_config": "a" * 64,
                "source_result": "b" * 64,
                "mapping": "c" * 64,
            },
        },
        "candidate": {
            "factor_name": "etf_dynamic_peer_residual_dislocation_reversal_5_60",
            "family": "lagged_market_residual_peer_dislocation",
            "direction": "higher_is_better",
            "formula": "-robust_z_60(asset_residual_sum_5-peer_median_residual_sum_5)",
            "beta_window": 120,
            "beta_min_observations": 80,
            "beta_lag": 1,
            "residual_sum_window": 5,
            "robust_scale_window": 60,
            "robust_scale_min_observations": 40,
            "minimum_daily_peers": 3,
        },
        "evaluation": {
            "horizons": [5, 20],
            "primary_horizon": 5,
            "diagnostic_horizon": 20,
            "execution_lag": 1,
            "multiple_testing_method": "benjamini_hochberg",
            "multiple_testing_scope": "all_frozen_candidate_horizon_tests",
        },
        "reference_policy": {
            "max_abs_reference_correlation": 0.85,
            "direct_exposure_names": [
                "market_beta_120",
                "residual_volatility_60",
                "momentum_60",
                "short_return_5",
                "log_adv20",
            ],
        },
        "capacity": {
            "portfolio_value_cny": 1_000_000.0,
            "position_count": 10,
            "max_one_way_participation_rate": 0.01,
        },
        "costs": {
            "one_way_bps": [5.0, 10.0],
            "required_positive_net_spread_bps": 10.0,
        },
        "stop_policy": {
            "single_prescreen_run_limit": 1,
            "primary_horizon_must_pass": True,
            "sign_flip_rescue_allowed": False,
            "window_tuning_allowed": False,
            "threshold_relaxation_allowed": False,
            "horizon_substitution_allowed": False,
            "parameter_grid_allowed": False,
            "regime_rescue_allowed": False,
        },
        "forward_return_read_allowed": False,
        "factor_generation_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "paper_signal_allowed": False,
        "live_boundary_allowed": False,
    }


def _source_readiness() -> dict:
    return {
        "stage": "cn_etf_dynamic_comovement_peer_readiness",
        "status": "ready_for_peer_source_preregistration",
        "gate": {"cleared": True, "blockers": []},
        "mapping_integrity": {"mapping_method": "lagged_market_residual_correlation_topk"},
        "source_boundaries": {
            "current_name_used": False,
            "official_2026_peer_mapping_used": False,
            "forward_returns_calculated": False,
            "factor_values_calculated": False,
        },
        "live_boundary_allowed": False,
    }


def _evidence_hashes() -> dict[str, str]:
    return {
        "source_config": "a" * 64,
        "source_result": "b" * 64,
        "mapping": "c" * 64,
    }


if __name__ == "__main__":
    unittest.main()
