import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quant_robot.data.provider_status import build_provider_status


class ProviderStatusTests(unittest.TestCase):
    def test_provider_status_reports_dependencies_and_token_requirements(self):
        status = build_provider_status(
            dependency_available=lambda name: name in {"pandas", "tushare", "akshare", "yfinance", "ccxt"},
            secret_loader=lambda name: "token" if name == "TUSHARE_TOKEN" else None,
        )

        self.assertTrue(status["providers"]["tushare"]["ready"])
        self.assertTrue(status["providers"]["akshare"]["ready"])
        self.assertTrue(status["providers"]["yfinance"]["ready"])
        self.assertTrue(status["providers"]["ccxt"]["ready"])
        self.assertEqual(status["providers"]["tushare"]["credential"], "TUSHARE_TOKEN")
        self.assertEqual(status["providers"]["tushare"]["markets"], ["CN", "CN_ETF"])
        self.assertNotIn("CN_ETF", status["providers"]["tushare"]["planned_markets"])
        self.assertEqual(status["providers"]["akshare"]["markets"], ["CN", "CN_ETF"])
        self.assertEqual(status["providers"]["akshare"]["planned_markets"], ["HK", "US"])
        self.assertTrue(status["providers"]["akshare"]["implemented"])
        self.assertEqual(status["providers"]["akshare"]["missing"], [])
        self.assertFalse(status["providers"]["yfinance"]["requires_token"])
        self.assertIn("parquet", status)

    def test_provider_status_cli_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "provider_status.json"
            repo_root = Path(__file__).resolve().parents[2]
            env = {**os.environ, "PYTHONPATH": "src"}

            result = subprocess.run(
                [sys.executable, "scripts/show_provider_status.py", "--output", str(output)],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("providers", status)
            self.assertIn("parquet", status)


if __name__ == "__main__":
    unittest.main()
