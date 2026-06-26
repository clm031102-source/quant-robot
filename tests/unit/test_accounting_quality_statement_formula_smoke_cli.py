import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_accounting_quality_statement_formula_smoke import (
    run_accounting_quality_statement_formula_smoke_cli,
)


class AccountingQualityStatementFormulaSmokeCliTests(unittest.TestCase):
    def test_cli_writes_formula_smoke_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "report"
            _write_statement_inputs(root)

            result = run_accounting_quality_statement_formula_smoke_cli(
                roots=[root],
                output_dir=output_dir,
                deduplicate=True,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "accounting_quality_statement_formula_smoke.json").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_formula_smoke.md").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_formula_coverage.csv").exists())
            saved = json.loads((output_dir / "accounting_quality_statement_formula_smoke.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["unique_symbols"], 2)

    def test_cli_blocks_when_smoke_fails_unless_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "report"
            _write_statement_inputs(root, include_required_columns=False)

            with self.assertRaisesRegex(RuntimeError, "accounting quality statement formula smoke is blocked"):
                run_accounting_quality_statement_formula_smoke_cli(
                    roots=[root],
                    output_dir=output_dir,
                )


def _write_statement_inputs(root: Path, *, include_required_columns: bool = True) -> None:
    rows = []
    periods = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
    for asset_id in ["CN_XSHE_000001", "CN_XSHG_600519"]:
        for index, end_date in enumerate(periods):
            row = {
                "date": end_date,
                "asset_id": asset_id,
                "symbol": asset_id[-6:] + (".SZ" if "XSHE" in asset_id else ".SH"),
                "market": "CN",
                "ann_date": end_date + pd.Timedelta(days=30),
                "end_date": end_date,
                "report_type": "1",
            }
            if include_required_columns:
                row.update(
                    {
                        "netprofit": 100.0 + index,
                        "n_cashflow_act": 120.0 + index,
                        "total_assets": 1000.0 + index * 10,
                        "total_liab": 400.0,
                        "total_cur_assets": 300.0 + index * 5,
                        "total_cur_liab": 180.0 + index * 2,
                    }
                )
            rows.append(row)
    path = root / "processed" / "financial_statement_inputs" / "frequency=1q" / "market=CN" / "year=2024"
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path / "part-00000.parquet", index=False)


if __name__ == "__main__":
    unittest.main()
