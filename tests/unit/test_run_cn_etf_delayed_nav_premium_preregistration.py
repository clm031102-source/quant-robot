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
    def test_historical_preregistration_cannot_issue_again_after_strict_source_revalidation(
        self,
    ):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                ValueError,
                "source evidence hash mismatch: source_result",
            ):
                run_cn_etf_delayed_nav_premium_preregistration_cli(
                    output_dir=directory
                )

            self.assertFalse(
                (Path(directory) / "single_prescreen_authorization.json").exists()
            )

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
