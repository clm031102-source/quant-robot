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

    def test_globbed_coverage_uses_only_current_walk_forward_fold_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "fold_01" / "test" / "case_current" / "regime_curve.csv"
            stale = root / "fold_99" / "test" / "case_stale" / "regime_curve.csv"
            current.parent.mkdir(parents=True)
            stale.parent.mkdir(parents=True)
            pd.DataFrame(
                [{"date": "2024-01-02", "regime_momentum": -0.05, "regime_allowed": False}]
            ).to_csv(current, index=False)
            pd.DataFrame(
                [{"date": "2099-01-01", "regime_momentum": 0.08, "regime_allowed": True}]
            ).to_csv(stale, index=False)
            folds_path = root / "walk_forward_folds.csv"
            pd.DataFrame([{"fold": 1, "case_id": "case_current"}]).to_csv(folds_path, index=False)

            pack = run_market_regime_coverage(
                regime_curve_glob=str(root / "fold_*" / "test" / "*" / "regime_curve.csv"),
                walk_forward_folds_path=folds_path,
                output_dir=root / "coverage",
                min_regimes=1,
                min_rows_per_regime=1,
            )

            self.assertEqual(pack["summary"]["rows"], 1)
            self.assertEqual(pack["summary"]["observation_end"], "2024-01-02")
            self.assertEqual(pack["source_evidence"]["expected_fold_cases"], 1)
            self.assertEqual(pack["source_evidence"]["ignored_stale_curves"], 1)

    def test_globbed_coverage_rejects_missing_current_fold_case_curve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folds_path = root / "walk_forward_folds.csv"
            pd.DataFrame([{"fold": 1, "case_id": "case_missing"}]).to_csv(folds_path, index=False)

            with self.assertRaisesRegex(RuntimeError, "missing current walk-forward regime curves"):
                run_market_regime_coverage(
                    regime_curve_glob=str(root / "fold_*" / "test" / "*" / "regime_curve.csv"),
                    walk_forward_folds_path=folds_path,
                    output_dir=root / "coverage",
                )

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


if __name__ == "__main__":
    unittest.main()
