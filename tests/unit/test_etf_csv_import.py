import tempfile
import unittest
from pathlib import Path

from scripts.import_etf_csv import import_etf_csv
from quant_robot.storage.processed_bars import load_processed_bars


class EtfCsvImportTests(unittest.TestCase):
    def test_import_tradingview_etf_csv_writes_processed_cn_etf_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "510300.csv"
            csv_path.write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-02,3.50,3.55,3.48,3.52,1000000\n"
                "2024-01-03,3.52,3.60,3.50,3.58,1200000\n",
                encoding="utf-8",
            )

            result = import_etf_csv(csv_path, root / "processed", symbol="510300.SH")
            bars = load_processed_bars(root / "processed", "CN_ETF")

            self.assertEqual(result["market"], "CN_ETF")
            self.assertEqual(result["symbol"], "510300.SH")
            self.assertEqual(result["rows"], 2)
            self.assertEqual(set(bars["market"]), {"CN_ETF"})
            self.assertEqual(set(bars["asset_type"]), {"etf"})
            self.assertEqual(bars.loc[0, "asset_id"], "CN_ETF_XSHG_510300")

    def test_import_tradingview_etf_csv_merges_symbols_in_same_year_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "510300.csv"
            second = root / "159915.csv"
            first.write_text("time,open,high,low,close,Volume\n2024-01-02,3,3.1,2.9,3.05,100\n", encoding="utf-8")
            second.write_text("time,open,high,low,close,Volume\n2024-01-02,2,2.1,1.9,2.05,200\n", encoding="utf-8")

            import_etf_csv(first, root / "processed", symbol="510300.SH")
            import_etf_csv(second, root / "processed", symbol="159915.SZ")
            bars = load_processed_bars(root / "processed", "CN_ETF")

            self.assertEqual(set(bars["symbol"]), {"510300.SH", "159915.SZ"})

    def test_import_rejects_filename_symbol_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "510500.csv"
            csv_path.write_text(
                "time,open,high,low,close,Volume\n2024-01-02,3,3.1,2.9,3.05,100\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "does not match symbol"):
                import_etf_csv(csv_path, root / "processed", symbol="510300.SH")

    def test_import_quality_report_does_not_treat_weekends_as_missing_without_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "510300.csv"
            csv_path.write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-05,3,3.1,2.9,3.05,100\n"
                "2024-01-08,3.1,3.2,3.0,3.15,120\n",
                encoding="utf-8",
            )

            result = import_etf_csv(csv_path, root / "processed", symbol="510300.SH")

            self.assertEqual(result["quality_report"]["missing_date_rows"], 0)

    def test_import_refuses_to_run_when_import_lock_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "processed"
            output.mkdir()
            (output / ".import_etf_csv.lock").write_text("locked", encoding="utf-8")
            csv_path = root / "510300.csv"
            csv_path.write_text(
                "time,open,high,low,close,Volume\n2024-01-02,3,3.1,2.9,3.05,100\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "ETF CSV import is already running"):
                import_etf_csv(csv_path, output, symbol="510300.SH")


if __name__ == "__main__":
    unittest.main()
