from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_etf_fund_structure_crowding_preregistration import (
    run_cn_etf_fund_structure_crowding_preregistration_cli,
)


ROOT = Path(__file__).resolve().parents[2]
FROZEN_CONFIG = (
    ROOT / "configs/cn_etf_fund_structure_crowding_preregistration_20260728.json"
)


class RunCnEtfFundStructureCrowdingPreregistrationTests(unittest.TestCase):
    def test_writes_hash_bound_packet_without_reading_market_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _write_fixture(Path(tmp))

            result = run_cn_etf_fund_structure_crowding_preregistration_cli(
                config_path=fixture["config_path"],
                output_dir=fixture["output_dir"],
            )

            self.assertEqual(result["status"], "preregistered_single_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(result["summary"]["hypothesis_count"], 2)
            self.assertFalse(result["factor_generation_allowed"])
            self.assertFalse(result["forward_return_read_allowed"])
            self.assertEqual(
                result["authorization"]["allowed_stage"],
                "cn_etf_fund_structure_crowding_prescreen",
            )
            for key in ("json", "markdown", "candidate_csv", "authorization"):
                self.assertTrue(Path(result["artifacts"][key]).is_file())

    def test_rejects_frozen_formula_source_and_execution_boundary_mutations(self):
        cases = (
            (
                lambda payload: payload["candidate"].__setitem__("share_lookback", 10),
                "frozen candidate",
            ),
            (
                lambda payload: payload["source_evidence"]["hashes"].__setitem__(
                    "canonical_2024", "f" * 64
                ),
                "frozen source evidence",
            ),
            (
                lambda payload: payload["evaluation"].__setitem__("primary_horizon", 20),
                "frozen evaluation",
            ),
            (
                lambda payload: payload["stop_policy"].__setitem__(
                    "sign_flip_rescue_allowed", True
                ),
                "frozen stop policy",
            ),
            (
                lambda payload: payload.__setitem__("factor_generation_allowed", True),
                "factor_generation_allowed",
            ),
        )
        for mutate, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                fixture = _write_fixture(Path(tmp), mutate=mutate)
                with self.assertRaisesRegex(ValueError, message):
                    run_cn_etf_fund_structure_crowding_preregistration_cli(
                        config_path=fixture["config_path"],
                        output_dir=fixture["output_dir"],
                    )


def _write_fixture(root: Path, *, mutate=None) -> dict[str, Path]:
    payload = json.loads(FROZEN_CONFIG.read_text(encoding="utf-8"))
    source_config = root / "source_config.json"
    source_result = root / "source_result.json"
    source_config.write_text('{"fixture": true}\n', encoding="utf-8")
    source_result.write_text(
        json.dumps(
            {
                "stage": "cn_etf_fund_structure_source_readiness",
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
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths = {"source_config": source_config, "source_result": source_result}
    for year in range(2020, 2025):
        path = root / f"canonical_{year}.parquet"
        path.write_bytes(f"fixture-{year}\n".encode())
        paths[f"canonical_{year}"] = path
    payload["source_evidence"]["paths"] = {
        key: str(path) for key, path in paths.items()
    }
    payload["source_evidence"]["hashes"] = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in paths.items()
    }
    if mutate is not None:
        mutate(payload)
    config_path = root / "config.json"
    config_path.write_text(json.dumps(deepcopy(payload), indent=2), encoding="utf-8")
    return {"config_path": config_path, "output_dir": root / "output"}


if __name__ == "__main__":
    unittest.main()
