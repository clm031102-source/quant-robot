import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_etf_margin_positioning_preregistration import (
    SOURCE_KEYS,
    run_cn_etf_margin_positioning_preregistration_cli,
)
from quant_robot.ops.cn_etf_margin_positioning_preregistration import (
    SOURCE_BOUNDARIES,
)
from quant_robot.storage.fingerprints import sha256_file


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/cn_etf_margin_positioning_preregistration_20260728.json"


class CnEtfMarginPositioningPreregistrationTests(unittest.TestCase):
    def test_frozen_fixture_evidence_creates_one_use_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(CONFIG.read_text(encoding="utf-8"))
            paths: dict[str, str] = {}
            hashes: dict[str, str] = {}
            for key in SOURCE_KEYS:
                path = root / f"{key}.json"
                if key == "source_result":
                    content = {
                        "stage": "cn_etf_margin_positioning_source_readiness",
                        "status": "ready_for_margin_positioning_preregistration",
                        "gate": {"cleared": True, "blockers": []},
                        **{field: False for field in SOURCE_BOUNDARIES},
                    }
                    path.write_text(json.dumps(content), encoding="utf-8")
                else:
                    path.write_text(key, encoding="utf-8")
                paths[key] = str(path)
                hashes[key] = sha256_file(path)
            payload["source_evidence"]["paths"] = paths
            payload["source_evidence"]["hashes"] = hashes
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_cn_etf_margin_positioning_preregistration_cli(
                config_path=config_path,
                output_dir=root / "out",
            )

            self.assertEqual(result["status"], "preregistered_single_prescreen")
            self.assertEqual(
                result["candidate"]["factor_name"],
                "etf_residual_margin_financing_growth_reversal_20",
            )
            self.assertEqual(result["authorization"]["max_executions"], 1)
            self.assertFalse(result["forward_return_read_allowed"])
            self.assertFalse(result["prescreen_execution_allowed"])

    def test_boundary_mutation_fails_closed(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["factor_generation_allowed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "factor_generation_allowed"):
                run_cn_etf_margin_positioning_preregistration_cli(
                    config_path=path,
                    output_dir=Path(tmp) / "out",
                )


if __name__ == "__main__":
    unittest.main()
