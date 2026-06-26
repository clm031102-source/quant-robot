import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.accounting_quality_statement_formula_smoke import (
    audit_accounting_quality_statement_formula_smoke,
)


class AccountingQualityStatementFormulaSmokeTests(unittest.TestCase):
    def test_computes_statement_formula_coverage_and_deduplicates_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_statement_inputs(root, duplicate_first_row=True)

            result = audit_accounting_quality_statement_formula_smoke([root], deduplicate=True)

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["statement_rows_before_dedup"], 11)
            self.assertEqual(result["summary"]["statement_rows"], 10)
            self.assertEqual(result["summary"]["unique_symbols"], 2)
            self.assertEqual(result["summary"]["duplicate_key_rows_asset_end_ann_report_type"], 1)
            self.assertEqual(result["summary"]["blockers"], [])
            coverage = {row["factor_name"]: row for row in result["formula_coverage"]}
            self.assertEqual(coverage["low_total_accruals_to_assets_raw"]["valid_rows"], 10)
            self.assertEqual(coverage["cashflow_minus_netprofit_to_assets_raw"]["valid_rows"], 10)
            self.assertEqual(coverage["low_asset_growth_quality_raw"]["valid_rows"], 2)
            self.assertEqual(coverage["working_capital_accruals_to_assets_raw"]["valid_rows"], 2)
            self.assertEqual(coverage["earnings_cash_conversion_improvement_yoy_raw"]["valid_rows"], 2)
            self.assertEqual(coverage["aq_abnormal_accrual_change_reversal"]["valid_rows"], 2)
            self.assertEqual(coverage["aq_balance_sheet_stress_relief"]["valid_rows"], 2)
            self.assertEqual(coverage["aq_profitability_revision_cash_confirmed"]["valid_rows"], 2)
            self.assertEqual(coverage["aq_profitability_revision_asset_disciplined"]["valid_rows"], 2)
            self.assertFalse(result["execution_policy"]["return_labels_used"])
            self.assertFalse(result["execution_policy"]["promotion_allowed"])

    def test_blocks_duplicate_keys_when_deduplication_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_statement_inputs(root, duplicate_first_row=True)

            result = audit_accounting_quality_statement_formula_smoke([root], deduplicate=False)

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("duplicate_statement_keys", result["summary"]["blockers"])
            self.assertEqual(result["summary"]["statement_rows"], 11)


def _write_statement_inputs(root: Path, *, duplicate_first_row: bool) -> None:
    rows = []
    periods = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600519"]):
        for index, end_date in enumerate(periods):
            rows.append(
                {
                    "date": end_date,
                    "asset_id": asset_id,
                    "symbol": asset_id[-6:] + (".SZ" if "XSHE" in asset_id else ".SH"),
                    "market": "CN",
                    "ann_date": end_date + pd.Timedelta(days=30),
                    "end_date": end_date,
                    "report_type": "1",
                    "netprofit": 100.0 + asset_index * 10 + index,
                    "n_cashflow_act": 120.0 + asset_index * 10 + index * 2,
                    "total_assets": 1000.0 + asset_index * 100 + index * 10,
                    "total_liab": 400.0 + asset_index * 10,
                    "total_cur_assets": 300.0 + index * 5,
                    "total_cur_liab": 180.0 + index * 2,
                }
            )
    if duplicate_first_row:
        rows.append(dict(rows[0]))
    path = root / "processed" / "financial_statement_inputs" / "frequency=1q" / "market=CN" / "year=2024"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path / "part-00000.parquet", index=False)


if __name__ == "__main__":
    unittest.main()
