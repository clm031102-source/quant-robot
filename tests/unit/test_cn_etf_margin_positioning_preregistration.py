import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_etf_margin_positioning_preregistration import (
    run_cn_etf_margin_positioning_preregistration_cli,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/cn_etf_margin_positioning_preregistration_20260728.json"


class CnEtfMarginPositioningPreregistrationTests(unittest.TestCase):
    def test_real_frozen_evidence_creates_one_use_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cn_etf_margin_positioning_preregistration_cli(
                config_path=CONFIG,
                output_dir=tmp,
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
