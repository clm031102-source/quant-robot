import unittest

from quant_robot.data.readiness import check_tushare_readiness


class ReadinessTests(unittest.TestCase):
    def test_tushare_readiness_reports_missing_dependency_and_token(self):
        result = check_tushare_readiness(
            dependency_available=lambda name: False,
            secret_loader=lambda name: None,
        )

        self.assertFalse(result["ready"])
        self.assertIn("tushare package is not installed", result["missing"])
        self.assertIn("TUSHARE_TOKEN is not set", result["missing"])

    def test_tushare_readiness_ready_when_dependency_and_token_exist(self):
        result = check_tushare_readiness(
            dependency_available=lambda name: True,
            secret_loader=lambda name: "token",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["missing"], [])


if __name__ == "__main__":
    unittest.main()
