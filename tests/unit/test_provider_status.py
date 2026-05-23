import unittest

from quant_robot.data.provider_status import build_provider_status


class ProviderStatusTests(unittest.TestCase):
    def test_provider_status_reports_dependencies_and_token_requirements(self):
        status = build_provider_status(
            dependency_available=lambda name: name in {"pandas", "tushare", "yfinance", "ccxt"},
            secret_loader=lambda name: "token" if name == "TUSHARE_TOKEN" else None,
        )

        self.assertTrue(status["providers"]["tushare"]["ready"])
        self.assertTrue(status["providers"]["yfinance"]["ready"])
        self.assertTrue(status["providers"]["ccxt"]["ready"])
        self.assertFalse(status["providers"]["akshare"]["ready"])
        self.assertEqual(status["providers"]["tushare"]["credential"], "TUSHARE_TOKEN")
        self.assertEqual(status["providers"]["tushare"]["markets"], ["CN"])
        self.assertIn("CN_ETF", status["providers"]["tushare"]["planned_markets"])
        self.assertIn("CN_ETF", status["providers"]["akshare"]["planned_markets"])
        self.assertFalse(status["providers"]["akshare"]["implemented"])
        self.assertIn("adapter implementation is planned", status["providers"]["akshare"]["missing"])
        self.assertFalse(status["providers"]["yfinance"]["requires_token"])
        self.assertIn("parquet", status)


if __name__ == "__main__":
    unittest.main()
