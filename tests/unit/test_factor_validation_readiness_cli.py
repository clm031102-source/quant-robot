import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_factor_validation_readiness import run_factor_validation_readiness
from tests.unit.test_factor_validation_readiness import _fixture


class FactorValidationReadinessCliTests(unittest.TestCase):
    def test_cli_validates_upstream_packets_and_writes_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            args = fixture["build_args"]
            with (
                patch(
                    "scripts.run_factor_validation_readiness.validate_cleared_startup_gate_packet",
                    return_value=args["startup_gate_packet"],
                ) as startup,
                patch(
                    "scripts.run_factor_validation_readiness.validate_cn_stock_data_manifest_packet",
                    return_value=args["data_manifest_packet"],
                ) as manifest,
            ):
                packet = run_factor_validation_readiness(
                    config_path=fixture["config_path"],
                    source="authority-bars",
                    data_root=fixture["bars_config"],
                    startup_gate_path=args["startup_gate_path"],
                    data_manifest_path=args["data_manifest_path"],
                    calendar_path=args["calendar_path"],
                    calendar_manifest_path=args["calendar_manifest_path"],
                    output_dir=fixture["root"] / "readiness",
                )

            self.assertEqual(packet["status"], "ready")
            self.assertTrue((fixture["root"] / "readiness/factor_validation_readiness.json").exists())
            startup.assert_called_once()
            self.assertEqual(manifest.call_args.kwargs["expected_source_root"], fixture["bars_config"])
            self.assertEqual(manifest.call_args.kwargs["expected_moneyflow_source_root"], fixture["moneyflow_config"])
            self.assertTrue(manifest.call_args.kwargs["verify_source_fingerprint"])


if __name__ == "__main__":
    unittest.main()
