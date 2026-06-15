import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_provider_evidence import run_provider_evidence


class ProviderEvidenceCliTests(unittest.TestCase):
    def test_run_provider_evidence_writes_pack_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "provider_status.json"
            output_dir = root / "provider_evidence"
            status_path.write_text(
                json.dumps(
                    {
                        "providers": {
                            "tushare": {
                                "ready": False,
                                "package": "tushare",
                                "markets": ["CN", "CN_ETF"],
                                "planned_markets": [],
                                "implemented": True,
                                "requires_token": True,
                                "credential": "TUSHARE_TOKEN",
                                "missing": ["TUSHARE_TOKEN is not set"],
                            }
                        },
                        "parquet": {"ready": True, "missing": []},
                    }
                ),
                encoding="utf-8",
            )

            pack = run_provider_evidence(provider_status=status_path, output_dir=output_dir)

            self.assertEqual(pack["stage"], "phase_3_2_provider_readiness_evidence")
            self.assertTrue((output_dir / "provider_evidence_pack.json").exists())
            self.assertTrue((output_dir / "provider_evidence_pack.md").exists())
            self.assertTrue((output_dir / "provider_market_matrix.csv").exists())
            payload = json.loads((output_dir / "provider_evidence_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["providers"][0]["provider"], "tushare")


if __name__ == "__main__":
    unittest.main()
