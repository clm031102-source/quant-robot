import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.accounting_quality_statement_matrix_label_smoke import (
    build_accounting_quality_statement_matrix_label_smoke,
    compute_accounting_quality_statement_factor_frame,
)
from quant_robot.storage.dataset_store import DatasetStore


class AccountingQualityStatementMatrixLabelSmokeTests(unittest.TestCase):
    def test_builds_statement_factor_matrix_on_first_trade_after_ann_date_and_aligned_forward_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            _write_statement_inputs(statement_root, _statement_rows())
            _write_bars(bars_root, _bar_rows())

            result = build_accounting_quality_statement_matrix_label_smoke(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                horizons=(5, 20),
                execution_lag=1,
                min_label_coverage=0.90,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)
            self.assertGreater(result["summary"]["label_aligned_rows"], 0)
            self.assertGreaterEqual(result["summary"]["label_coverage"], 0.90)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["execution_policy"]["ic_calculated"])
            factor_names = {row["factor_name"] for row in result["candidate_summaries"]}
            self.assertIn("aq_abnormal_accrual_change_reversal", factor_names)
            self.assertIn("aq_balance_sheet_stress_relief", factor_names)

            factor_frame = compute_accounting_quality_statement_factor_frame(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
            )
            self.assertFalse(factor_frame.empty)
            self.assertTrue((factor_frame["date"] == factor_frame["signal_date"]).all())
            self.assertTrue((factor_frame["signal_date"] > factor_frame["ann_date"]).all())
            self.assertIn("aq_abnormal_accrual_change_reversal", set(factor_frame["factor_name"]))
            self.assertIn("aq_balance_sheet_stress_relief", set(factor_frame["factor_name"]))

    def test_blocks_duplicate_statement_keys_when_deduplication_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            statement = _statement_rows()
            statement = pd.concat([statement, statement.head(1)], ignore_index=True)
            _write_statement_inputs(statement_root, statement)
            _write_bars(bars_root, _bar_rows())

            result = build_accounting_quality_statement_matrix_label_smoke(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                deduplicate=False,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertEqual(result["summary"]["duplicate_key_rows_asset_end_ann_report_type"], 1)
            self.assertIn("duplicate_statement_keys", result["summary"]["blockers"])


def _statement_rows(include_2026: bool = False) -> pd.DataFrame:
    rows = []
    periods = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
    if include_2026:
        periods = periods.append(pd.DatetimeIndex([pd.Timestamp("2026-03-31")]))
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for index, end_date in enumerate(periods):
            ann_date = end_date + pd.Timedelta(days=30)
            rows.append(
                {
                    "date": end_date,
                    "asset_id": asset_id,
                    "symbol": asset_id[-6:] + (".SZ" if "XSHE" in asset_id else ".SH"),
                    "market": "CN",
                    "ann_date": ann_date,
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
    return pd.DataFrame(rows)


def _bar_rows(end: str = "2024-06-28", include_2026: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2023-04-03", end)
    if include_2026:
        dates = dates.append(pd.bdate_range("2026-04-01", "2026-07-31"))
    rows = []
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0 + asset_index + index * 0.01,
                }
            )
    return pd.DataFrame(rows)


def _write_statement_inputs(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/financial_statement_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )


def _write_bars(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
