import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_event_factor_control_gate import run_event_factor_control_gate_cli
from tests.unit.test_event_factor_control_gate import _policy


class EventFactorControlGateCliTests(unittest.TestCase):
    def test_cli_writes_event_control_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "policy.json"
            output_dir = root / "out"
            config.write_text(json.dumps(_policy()), encoding="utf-8")

            result = run_event_factor_control_gate_cli(config_path=config, output_dir=output_dir)

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "event_factor_control_gate.json").exists())
            self.assertTrue((output_dir / "event_control_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
