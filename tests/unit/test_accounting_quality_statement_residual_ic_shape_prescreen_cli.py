import tempfile
import unittest
from pathlib import Path

from scripts.run_accounting_quality_statement_residual_ic_shape_prescreen import (
    run_accounting_quality_statement_residual_ic_shape_prescreen_cli,
)
from tests.unit.test_accounting_quality_statement_residual_ic_shape_prescreen import (
    _bar_rows,
    _statement_rows,
    _write_bars,
    _write_daily_basic,
    _write_statement_inputs,
    _write_stock_basic,
)


class AccountingQualityStatementResidualIcShapePrescreenCliTests(unittest.TestCase):
    def test_cli_writes_outputs_and_keeps_promotion_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["stage"], "accounting_quality_statement_residual_ic_shape_prescreen")
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_shape_prescreen.json").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_neutral_observations.csv").exists())

    def test_cli_supports_repaired_factor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                factor_mode="repaired",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["factor_mode"], "repaired")
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())

    def test_cli_supports_directional_audit_factor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                factor_mode="new_substructure_directional_audit",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["factor_mode"], "new_substructure_directional_audit")
            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())

    def test_cli_supports_statement_event_drift_factor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                factor_mode="statement_event_drift",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["factor_mode"], "statement_event_drift")
            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())

    def test_cli_supports_statement_profitability_revision_factor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                factor_mode="statement_profitability_revision",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["factor_mode"], "statement_profitability_revision")
            self.assertEqual(result["summary"]["candidate_count"], 2)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())

    def test_cli_supports_industry_relative_surprise_factor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "output"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = run_accounting_quality_statement_residual_ic_shape_prescreen_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                factor_mode="industry_relative_surprise",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["factor_mode"], "industry_relative_surprise")
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "accounting_quality_statement_residual_ic_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
