import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_financial_pit_signal_date_filter import run_financial_pit_signal_date_filter_cli
from tests.unit.test_financial_pit_timing_audit import _financial_row, _write_bars, _write_financial_rows


class FinancialPitSignalDateFilterCliTests(unittest.TestCase):
    def test_cli_writes_filtered_processed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_root = root / "filtered"
            _write_financial_rows(
                financial_root,
                pd.DataFrame([_financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1)]),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06"])

            result = run_financial_pit_signal_date_filter_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                output_root=output_root,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_root / "financial_pit_signal_date_filter.json").exists())
            self.assertTrue(any((output_root / "processed" / "fina_indicator_inputs").rglob("*.parquet")))


if __name__ == "__main__":
    unittest.main()
