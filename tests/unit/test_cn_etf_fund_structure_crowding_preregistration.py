import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_etf_fund_structure_crowding_preregistration import (
    STATUS_READY,
    build_cn_etf_fund_structure_crowding_preregistration,
    write_cn_etf_fund_structure_crowding_preregistration,
)


class CnEtfFundStructureCrowdingPreregistrationTests(unittest.TestCase):
    def test_builds_one_candidate_two_hypothesis_packet_without_label_access(self):
        result = build_cn_etf_fund_structure_crowding_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_hashes(),
            config_sha256="a" * 64,
        )

        self.assertEqual(result["status"], STATUS_READY)
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(result["summary"]["hypothesis_count"], 2)
        self.assertFalse(result["factor_generation_allowed"])
        self.assertFalse(result["forward_return_read_allowed"])
        self.assertFalse(result["prescreen_execution_allowed"])
        self.assertEqual(result["candidate"]["direction"], "higher_is_better")

    def test_blocks_source_hash_or_source_boundary_mismatch(self):
        cases = (
            (
                lambda source, hashes: hashes.__setitem__("canonical_2024", "f" * 64),
                "source_evidence_hash_mismatch:canonical_2024",
            ),
            (
                lambda source, hashes: source.__setitem__("factor_generation_allowed", True),
                "source_boundary_not_false:factor_generation_allowed",
            ),
        )
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                source = _source_readiness()
                hashes = _hashes()
                mutate(source, hashes)
                result = build_cn_etf_fund_structure_crowding_preregistration(
                    config=_config(),
                    source_readiness=source,
                    evidence_hashes=hashes,
                    config_sha256="a" * 64,
                )
                self.assertEqual(result["status"], "blocked")
                self.assertIn(blocker, result["summary"]["blockers"])

    def test_writes_deterministic_artifacts(self):
        result = build_cn_etf_fund_structure_crowding_preregistration(
            config=_config(),
            source_readiness=_source_readiness(),
            evidence_hashes=_hashes(),
            config_sha256="a" * 64,
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cn_etf_fund_structure_crowding_preregistration(tmp, result)
            first = {name: Path(path).read_bytes() for name, path in paths.items()}
            paths = write_cn_etf_fund_structure_crowding_preregistration(tmp, result)
            second = {name: Path(path).read_bytes() for name, path in paths.items()}
            self.assertEqual(first, second)


def _hashes() -> dict[str, str]:
    return {
        "source_config": "b" * 64,
        "source_result": "c" * 64,
        "canonical_2020": "d" * 64,
        "canonical_2021": "d" * 64,
        "canonical_2022": "d" * 64,
        "canonical_2023": "d" * 64,
        "canonical_2024": "d" * 64,
    }


def _source_readiness() -> dict:
    return {
        "status": "ready_for_fund_structure_preregistration",
        "gate": {"cleared": True, "blockers": []},
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
    }


def _config() -> dict:
    return {
        "registration_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_fund_structure",
        "source_evidence": {
            "required_status": "ready_for_fund_structure_preregistration",
            "hashes": _hashes(),
        },
        "candidate": {
            "factor_name": "etf_residual_share_creation_crowding_reversal_20",
            "direction": "higher_is_better",
            "formula": "-ols_residual(log_share_change_20|fixed_controls)",
        },
        "evaluation": {
            "horizons": [5, 20],
            "primary_horizon": 5,
            "diagnostic_horizon": 20,
            "execution_lag": 1,
        },
        "reference_policy": {},
        "capacity": {},
        "costs": {},
        "stop_policy": {
            "single_prescreen_run_limit": 1,
            "sign_flip_rescue_allowed": False,
            "window_tuning_allowed": False,
            "control_removal_allowed": False,
            "threshold_relaxation_allowed": False,
            "horizon_substitution_allowed": False,
            "parameter_grid_allowed": False,
            "regime_rescue_allowed": False,
        },
        **{
            field: False
            for field in (
                "forward_return_read_allowed",
                "factor_generation_allowed",
                "prescreen_execution_allowed",
                "portfolio_grid_allowed",
                "walk_forward_allowed",
                "final_holdout_allowed",
                "promotion_allowed",
                "paper_signal_allowed",
                "broker_connection_allowed",
                "account_read_allowed",
                "order_placement_allowed",
                "live_trading_allowed",
                "live_boundary_allowed",
            )
        },
    }


if __name__ == "__main__":
    unittest.main()
