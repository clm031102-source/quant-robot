from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_cn_etf_delayed_nav_premium_preregistration import (
    _load_and_validate_config,
    run_cn_etf_delayed_nav_premium_preregistration_cli,
)


class RunCnEtfDelayedNavPremiumPreregistrationTests(unittest.TestCase):
    def test_real_ready_source_produces_h1_h5_single_use_authorization(self):
        with TemporaryDirectory() as directory:
            result = run_cn_etf_delayed_nav_premium_preregistration_cli(
                output_dir=directory
            )

            self.assertEqual(result["status"], "preregistered_single_prescreen")
            self.assertEqual(result["authorization"]["primary_horizon"], 1)
            self.assertEqual(result["authorization"]["diagnostic_horizon"], 5)
            self.assertEqual(result["authorization"]["max_executions"], 1)
            self.assertFalse(result["forward_return_read"])
            for path in result["artifacts"].values():
                self.assertTrue(Path(path).exists(), path)

    def test_config_rejects_candidate_and_source_hash_drift(self):
        source = Path(
            "configs/cn_etf_delayed_nav_premium_innovation_reversal_60_20260729.json"
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            payload = json.loads(source.read_text(encoding="utf-8"))
            payload["candidate"]["premium_lookback"] = 61
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate"):
                _load_and_validate_config(path)

            payload["candidate"]["premium_lookback"] = 60
            payload["source_evidence"]["hashes"]["canonical_nav"] = "f" * 64
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source evidence hash mismatch"):
                run_cn_etf_delayed_nav_premium_preregistration_cli(
                    config_path=path,
                    output_dir=directory,
                )


if __name__ == "__main__":
    unittest.main()
