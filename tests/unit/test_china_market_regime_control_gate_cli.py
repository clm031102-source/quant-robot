import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_china_market_regime_control_gate import run_china_market_regime_control_gate_cli
from tests.unit.test_china_market_regime_control_gate import _policy


class ChinaMarketRegimeControlGateCliTests(unittest.TestCase):
    def test_cli_writes_gate_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "policy.json"
            output_dir = root / "out"
            config.write_text(json.dumps(_policy()), encoding="utf-8")

            result = run_china_market_regime_control_gate_cli(config_path=config, output_dir=output_dir)

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "china_market_regime_control_gate.json").exists())
            self.assertTrue((output_dir / "control_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
