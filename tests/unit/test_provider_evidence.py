import unittest

from quant_robot.ops.provider_evidence import build_provider_evidence_pack


class ProviderEvidencePackTests(unittest.TestCase):
    def test_provider_evidence_pack_classifies_readiness_and_market_coverage(self):
        status = {
            "providers": {
                "tushare": {
                    "ready": False,
                    "package": "tushare",
                    "markets": ["CN", "CN_ETF"],
                    "planned_markets": [],
                    "implemented": True,
                    "requires_token": True,
                    "credential": "TUSHARE_TOKEN",
                    "missing": ["tushare package is not installed", "TUSHARE_TOKEN is not set"],
                },
                "yfinance": {
                    "ready": True,
                    "package": "yfinance",
                    "markets": ["HK", "US"],
                    "planned_markets": [],
                    "implemented": True,
                    "requires_token": False,
                    "credential": None,
                    "missing": [],
                },
                "akshare": {
                    "ready": False,
                    "package": "akshare",
                    "markets": [],
                    "planned_markets": ["CN", "CN_ETF"],
                    "implemented": False,
                    "requires_token": False,
                    "credential": None,
                    "missing": ["adapter implementation is planned"],
                },
            },
            "parquet": {"ready": False, "missing": ["pyarrow or fastparquet package is not installed"]},
        }

        pack = build_provider_evidence_pack(status)

        self.assertEqual(pack["stage"], "phase_3_2_provider_readiness_evidence")
        self.assertEqual(pack["summary"]["ready_providers"], 1)
        self.assertEqual(pack["summary"]["blocked_providers"], 2)
        providers = {item["provider"]: item for item in pack["providers"]}
        self.assertEqual(providers["tushare"]["readiness_status"], "missing_dependency_and_token")
        self.assertEqual(providers["akshare"]["readiness_status"], "planned_adapter")
        self.assertEqual(providers["yfinance"]["readiness_status"], "ready")
        matrix = {(row["market"], row["provider"]): row for row in pack["market_matrix"]}
        self.assertEqual(matrix[("CN_ETF", "tushare")]["coverage_status"], "implemented_blocked")
        self.assertEqual(matrix[("CN_ETF", "akshare")]["coverage_status"], "planned")
        self.assertIn("Research only", pack["safety"])
        self.assertIn("TUSHARE_TOKEN", pack["markdown"])


if __name__ == "__main__":
    unittest.main()
