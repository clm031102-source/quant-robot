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

    def test_run_market_regime_coverage_reads_globbed_regime_curves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            curve_a = root / "fold_01" / "test" / "case_a" / "regime_curve.csv"
            curve_b = root / "fold_02" / "test" / "case_a" / "regime_curve.csv"
            curve_a.parent.mkdir(parents=True)
            curve_b.parent.mkdir(parents=True)
            pd.DataFrame(
                [
                    {"date": "2026-01-01", "regime_momentum": 0.05},
                    {"date": "2026-01-02", "regime_momentum": -0.04},
                ]
            ).to_csv(curve_a, index=False)
            pd.DataFrame([{"date": "2026-01-03", "regime_momentum": 0.00}]).to_csv(curve_b, index=False)
            output_dir = root / "market_regime_coverage"

            pack = run_market_regime_coverage(
                regime_curve_glob=str(root / "fold_*" / "test" / "*" / "regime_curve.csv"),
                output_dir=output_dir,
                min_regimes=3,
                min_rows_per_regime=1,
                require_sufficient=True,
            )

            self.assertEqual(pack["status"], "sufficient")
            self.assertEqual(pack["summary"]["rows"], 3)
            self.assertTrue((output_dir / "market_regime_coverage_pack.json").exists())

    def test_run_market_regime_coverage_requires_sufficient_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            regime_curve = root / "regime_curve.csv"
            pd.DataFrame(
                [
                    {"date": "2026-01-01", "regime_momentum": 0.05},
                    {"date": "2026-01-02", "regime_momentum": 0.04},
                ]
            ).to_csv(regime_curve, index=False)

            with self.assertRaisesRegex(RuntimeError, "market regime coverage is insufficient"):
                run_market_regime_coverage(
                    regime_curve=regime_curve,
                    output_dir=root / "market_regime_coverage",
                    min_regimes=2,
                    min_rows_per_regime=1,
                    require_sufficient=True,
                )

    def test_run_market_regime_coverage_blocks_signal_window_without_allowed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fold_test = root / "fold_01" / "test"
            curve = fold_test / "case_a" / "regime_curve.csv"
            curve.parent.mkdir(parents=True)
            (fold_test / "manifest.json").write_text(
                '{"config": {"signal_start_date": "2026-01-02", "signal_end_date": "2026-01-03"}}',
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"date": "2026-01-01", "regime_momentum": 0.05, "regime_allowed": True},
                    {"date": "2026-01-02", "regime_momentum": -0.04, "regime_allowed": False},
                    {"date": "2026-01-03", "regime_momentum": -0.03, "regime_allowed": False},
                ]
            ).to_csv(curve, index=False)

            with self.assertRaisesRegex(RuntimeError, "market regime coverage is insufficient"):
                run_market_regime_coverage(
                    regime_curve_glob=str(root / "fold_*" / "test" / "*" / "regime_curve.csv"),
                    output_dir=root / "market_regime_coverage",
                    min_regimes=2,
                    min_rows_per_regime=1,
                    min_allowed_rows=1,
                    min_blocked_rows=1,
                    min_signal_window_allowed_rows=1,
                    min_signal_window_blocked_rows=1,
                    require_sufficient=True,
                )


if __name__ == "__main__":
    unittest.main()
