from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_etf_dynamic_peer_dislocation_preregistration import (
    run_cn_etf_dynamic_peer_dislocation_preregistration_cli,
)


ROOT = Path(__file__).resolve().parents[2]
FROZEN_CONFIG = ROOT / "configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json"


class RunCnEtfDynamicPeerDislocationPreregistrationTests(unittest.TestCase):
    def test_cli_writes_preregistration_and_authorization_without_market_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _write_fixture(Path(tmp))

            result = run_cn_etf_dynamic_peer_dislocation_preregistration_cli(
                config_path=fixture["config_path"],
                output_dir=fixture["output_dir"],
            )

            self.assertEqual(result["status"], "preregistered_single_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(result["summary"]["hypothesis_count"], 2)
            self.assertFalse(result["factor_generation_allowed"])
            self.assertFalse(result["prescreen_execution_allowed"])
            for key in ("json", "markdown", "candidate_csv", "authorization"):
                self.assertTrue(Path(result["artifacts"][key]).is_file())
            self.assertEqual(len(result["artifact_hashes"]["config"]), 64)
            self.assertEqual(len(result["artifact_hashes"]["result"]), 64)
            self.assertEqual(len(result["artifact_hashes"]["authorization"]), 64)
            self.assertNotIn("execution_receipt", result["artifacts"])

    def test_cli_rejects_frozen_contract_and_boundary_mutations(self) -> None:
        cases = (
            (
                "source_hash",
                lambda payload: payload["source_evidence"]["hashes"].__setitem__(
                    "source_result", "f" * 64
                ),
                "frozen source evidence",
            ),
            (
                "formula",
                lambda payload: payload["candidate"].__setitem__("formula", "changed"),
                "frozen candidate",
            ),
            (
                "beta_lag",
                lambda payload: payload["candidate"].__setitem__("beta_lag", 0),
                "frozen candidate",
            ),
            (
                "primary_horizon",
                lambda payload: payload["evaluation"].__setitem__("primary_horizon", 20),
                "frozen evaluation",
            ),
            (
                "fdr_scope",
                lambda payload: payload["evaluation"].__setitem__(
                    "multiple_testing_scope", "primary_only"
                ),
                "frozen evaluation",
            ),
            (
                "reference_hash",
                lambda payload: payload["reference_policy"]["reference_configs"][0].__setitem__(
                    "sha256", "f" * 64
                ),
                "frozen reference policy",
            ),
            (
                "cost_stress",
                lambda payload: payload["costs"].__setitem__("one_way_bps", [5.0]),
                "frozen costs",
            ),
            (
                "run_limit",
                lambda payload: payload["stop_policy"].__setitem__(
                    "single_prescreen_run_limit", 2
                ),
                "frozen stop policy",
            ),
            (
                "factor_generation",
                lambda payload: payload.__setitem__("factor_generation_allowed", True),
                "factor_generation_allowed",
            ),
            (
                "final_holdout",
                lambda payload: payload.__setitem__("final_holdout_allowed", True),
                "final_holdout_allowed",
            ),
            (
                "live_trading",
                lambda payload: payload.__setitem__("live_trading_allowed", True),
                "live_trading_allowed",
            ),
        )
        for name, mutate, expected_message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                fixture = _write_fixture(Path(tmp), mutate=mutate)

                with self.assertRaisesRegex(ValueError, expected_message):
                    run_cn_etf_dynamic_peer_dislocation_preregistration_cli(
                        config_path=fixture["config_path"],
                        output_dir=fixture["output_dir"],
                    )


def _write_fixture(root: Path, *, mutate=None) -> dict[str, Path]:
    payload = json.loads(FROZEN_CONFIG.read_text(encoding="utf-8"))
    source_config_path = root / "source_config.json"
    source_result_path = root / "source_result.json"
    mapping_path = root / "mapping.csv"
    output_dir = root / "report"
    source_config_path.write_text('{"fixture": true}\n', encoding="utf-8")
    source_result_path.write_text(
        json.dumps(
            {
                "stage": "cn_etf_dynamic_comovement_peer_readiness",
                "status": "ready_for_peer_source_preregistration",
                "gate": {"cleared": True, "blockers": []},
                "mapping_integrity": {
                    "mapping_method": "lagged_market_residual_correlation_topk"
                },
                "source_boundaries": {
                    "current_name_used": False,
                    "official_2026_peer_mapping_used": False,
                    "forward_returns_calculated": False,
                    "factor_values_calculated": False
                },
                "live_boundary_allowed": False
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    mapping_path.write_bytes(b"snapshot_date,asset_id,peer_asset_id,correlation\n")
    paths = {
        "source_config": source_config_path,
        "source_result": source_result_path,
        "mapping": mapping_path,
    }
    payload["source_evidence"]["paths"] = {
        key: str(path) for key, path in paths.items()
    }
    payload["source_evidence"]["hashes"] = {
        key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()
    }
    if mutate is not None:
        mutate(payload)
    config_path = root / "config.json"
    config_path.write_text(json.dumps(deepcopy(payload), indent=2), encoding="utf-8")
    return {
        "config_path": config_path,
        "output_dir": output_dir,
    }


if __name__ == "__main__":
    unittest.main()
