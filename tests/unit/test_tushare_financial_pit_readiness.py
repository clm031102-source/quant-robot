import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.tushare_financial_pit_readiness import (
    audit_tushare_financial_pit_readiness,
    render_tushare_financial_pit_readiness_markdown,
    write_tushare_financial_pit_readiness,
)


class TushareFinancialPitReadinessTests(unittest.TestCase):
    def test_blocks_when_only_daily_basic_columns_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_parquet(
                root / "processed" / "factor_inputs" / "frequency=1d" / "market=CN" / "year=2025" / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "date": "2025-01-02",
                            "asset_id": "CN_XSHE_000001",
                            "symbol": "000001.SZ",
                            "pe_ttm": 8.0,
                            "pb": 0.8,
                            "dv_ttm": 4.2,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness([root])

            self.assertFalse(result["summary"]["passes"])
            self.assertEqual(result["summary"]["pit_ready_datasets"], 0)
            self.assertIn("missing_financial_statement_or_indicator_dataset", result["summary"]["blockers"])
            self.assertEqual(result["summary"]["financial_like_datasets"], 0)

    def test_passes_when_financial_dataset_has_pit_dates_and_profitability_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_parquet(
                root
                / "processed"
                / "fina_indicator"
                / "frequency=1q"
                / "market=CN"
                / "year=2025"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "ts_code": "000001.SZ",
                            "ann_date": "20250425",
                            "end_date": "20250331",
                            "roe": 11.2,
                            "roa": 0.92,
                            "grossprofit_margin": 28.5,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness([root])

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["pit_ready_datasets"], 1)
            self.assertEqual(result["summary"]["financial_like_datasets"], 1)
            self.assertEqual(result["datasets"][0]["pit_status"], "pass")
            self.assertIn("roe", result["datasets"][0]["profitability_columns"])

    def test_blocks_missing_required_accounting_column_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_parquet(
                root
                / "processed"
                / "fina_indicator"
                / "frequency=1q"
                / "market=CN"
                / "year=2025"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "ts_code": "000001.SZ",
                            "ann_date": "20250425",
                            "end_date": "20250331",
                            "roe": 11.2,
                            "roa": 0.92,
                            "ocfps": 0.8,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness(
                [root],
                required_column_groups={
                    "accounting_accrual_quality": ["netprofit", "ocfps", "total_assets"],
                },
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertEqual(result["summary"]["required_column_group_count"], 1)
            self.assertEqual(result["summary"]["required_column_groups_passing"], 0)
            self.assertIn(
                "missing_required_financial_column_group:accounting_accrual_quality",
                result["summary"]["blockers"],
            )
            group = result["required_column_groups"][0]
            self.assertEqual(group["group_id"], "accounting_accrual_quality")
            self.assertFalse(group["passes"])
            self.assertIn("netprofit", group["missing_columns"])
            self.assertIn("total_assets", group["missing_columns"])

    def test_passes_required_accounting_column_group_when_one_pit_dataset_has_all_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_parquet(
                root
                / "processed"
                / "income_cashflow_balance"
                / "frequency=1q"
                / "market=CN"
                / "year=2025"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "ts_code": "000001.SZ",
                            "ann_date": "20250425",
                            "end_date": "20250331",
                            "roe": 11.2,
                            "netprofit": 100.0,
                            "ocfps": 0.8,
                            "total_assets": 1200.0,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness(
                [root],
                required_column_groups={
                    "accounting_accrual_quality": ["netprofit", "ocfps", "total_assets"],
                },
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["required_column_groups_passing"], 1)
            self.assertTrue(result["required_column_groups"][0]["passes"])

    def test_required_statement_column_group_does_not_need_profitability_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_parquet(
                root
                / "processed"
                / "financial_statement_inputs"
                / "frequency=1q"
                / "market=CN"
                / "year=2025"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "symbol": "000001.SZ",
                            "ann_date": "20250425",
                            "end_date": "20250331",
                            "netprofit": 100.0,
                            "n_cashflow_act": 80.0,
                            "total_assets": 1200.0,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness(
                [root],
                required_column_groups={
                    "accounting_accrual_quality": ["netprofit", "n_cashflow_act", "total_assets"],
                },
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["pit_ready_datasets"], 1)
            self.assertEqual(result["summary"]["required_column_groups_passing"], 1)
            self.assertTrue(result["required_column_groups"][0]["passes"])

    def test_financial_like_detection_ignores_root_directory_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tushare_fina_indicator_smoke"
            root.mkdir()
            (root / "manifest.json").write_text('{"completed": {}}', encoding="utf-8")
            (root / "financial_input_quality_report.json").write_text('{"rows": 1}', encoding="utf-8")
            _write_parquet(
                root
                / "processed"
                / "fina_indicator_inputs"
                / "frequency=1q"
                / "market=CN"
                / "year=2024"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "symbol": "000001.SZ",
                            "ann_date": "20240425",
                            "end_date": "20240331",
                            "roe": 11.2,
                        }
                    ]
                ),
            )

            result = audit_tushare_financial_pit_readiness([root])

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["financial_like_datasets"], 1)
            self.assertEqual(result["summary"]["pit_ready_datasets"], 1)

    def test_writes_json_and_markdown_outputs(self):
        result = audit_tushare_financial_pit_readiness([])
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_tushare_financial_pit_readiness(output_dir, result)

            self.assertTrue((output_dir / "tushare_financial_pit_readiness.json").exists())
            self.assertTrue((output_dir / "tushare_financial_pit_readiness.md").exists())
            markdown = render_tushare_financial_pit_readiness_markdown(result)
            self.assertIn("Tushare Financial PIT Readiness", markdown)
            self.assertIn("Passes: False", markdown)


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


if __name__ == "__main__":
    unittest.main()
