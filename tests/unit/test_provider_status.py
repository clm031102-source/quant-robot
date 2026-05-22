import unittest

from quant_robot.data.provider_status import build_provider_status


class ProviderStatusTests(unittest.TestCase):
    def test_provider_status_reports_dependencies_and_token_requirements(self):
        status = build_provider_status(
            dependency_available=lambda name: name in {"pandas", "tushare"},
            secret_loader=lambda name: "token" if name == "TUSHARE_TOKEN" else None,
        )

        self.assertTrue(status["providers"]["tushare"]["ready"])
        self.assertFalse(status["providers"]["akshare"]["ready"])
        self.assertEqual(status["providers"]["tushare"]["credential"], "TUSHARE_TOKEN")
        self.assertFalse(status["providers"]["yfinance"]["requires_token"])
        self.assertIn("parquet", status)


if __name__ == "__main__":
    unittest.main()
