import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_market_regime_coverage import run_market_regime_coverage


class MarketRegimeCoverageCliTests(unittest.TestCase):
    def test_run_market_regime_coverage_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            regime_curve = root / "regime_curve.csv"
            pd.DataFrame(
                [
                    {"date": "2026-01-01", "regime_momentum": 0.05},
                    {"date": "2026-01-02", "regime_momentum": -0.04},
                    {"date": "2026-01-03", "regime_momentum": 0.00},
                ]
            ).to_csv(regime_curve, index=False)
            output_dir = root / "market_regime_coverage"

            pack = run_market_regime_coverage(
                regime_curve=regime_curve,
                output_dir=output_dir,
                min_regimes=3,
                min_rows_per_regime=1,
            )

            self.assertEqual(pack["stage"], "phase_6_0_market_regime_coverage")
            self.assertEqual(pack["status"], "sufficient")
            self.assertTrue((output_dir / "market_regime_coverage_pack.json").exists())
            self.assertTrue((output_dir / "market_regime_coverage_pack.md").exists())
            self.assertTrue((output_dir / "market_regime_coverage_ledger.csv").exists())
            payload = json.loads((output_dir / "market_regime_coverage_pack.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["decision"]["market_regime_coverage_cleared"])
            self.assertFalse(payload["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
