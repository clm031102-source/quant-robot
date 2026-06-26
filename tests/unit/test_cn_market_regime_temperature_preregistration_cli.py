import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_market_regime_temperature_preregistration import (
    run_cn_market_regime_temperature_preregistration_cli,
)


class CNMarketRegimeTemperaturePreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            result = run_cn_market_regime_temperature_preregistration_cli(output_dir=output)

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "cn_market_regime_temperature_preregistration.json").exists())
            self.assertTrue((output / "cn_market_regime_temperature_preregistration.md").exists())
            self.assertTrue((output / "cn_market_regime_temperature_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
