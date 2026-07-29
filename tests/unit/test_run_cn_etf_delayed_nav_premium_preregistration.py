from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_cn_etf_delayed_nav_premium_preregistration import (
    SOURCE_KEYS,
    _load_and_validate_config,
    run_cn_etf_delayed_nav_premium_preregistration_cli,
)
from quant_robot.storage.fingerprints import sha256_file


class RunCnEtfDelayedNavPremiumPreregistrationTests(unittest.TestCase):
    def test_historical_preregistration_cannot_issue_again_after_strict_source_revalidation(
        self,
    ):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = _write_source_fixture_config(
                root,
                mismatch_key="source_result",
            )
            with self.assertRaisesRegex(
                ValueError,
                "source evidence hash mismatch: source_result",
            ):
                run_cn_etf_delayed_nav_premium_preregistration_cli(
                    config_path=config_path,
                    output_dir=root / "out",
                )

            self.assertFalse(
                (root / "out" / "single_prescreen_authorization.json").exists()
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

            path = _write_source_fixture_config(
                Path(directory),
                mismatch_key="canonical_nav",
            )
            with self.assertRaisesRegex(ValueError, "source evidence hash mismatch"):
                run_cn_etf_delayed_nav_premium_preregistration_cli(
                    config_path=path,
                    output_dir=Path(directory) / "out",
                )


def _write_source_fixture_config(root: Path, *, mismatch_key: str) -> Path:
    payload = json.loads(
        Path(
            "configs/cn_etf_delayed_nav_premium_innovation_reversal_60_20260729.json"
        ).read_text(encoding="utf-8")
    )
    paths: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for key in SOURCE_KEYS:
        path = root / f"{key}.fixture"
        content = "{}" if key == "source_result" else key
        path.write_text(content, encoding="utf-8")
        paths[key] = str(path)
        hashes[key] = sha256_file(path)
    hashes[mismatch_key] = "0" * 64
    payload["source_evidence"]["paths"] = paths
    payload["source_evidence"]["hashes"] = hashes
    config_path = root / f"config-{mismatch_key}.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


if __name__ == "__main__":
    unittest.main()
