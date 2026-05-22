import tempfile
import unittest
from pathlib import Path

from quant_robot.data.adapters.tradingview_csv_adapter import parse_tradingview_csv


class TradingViewCsvAdapterTests(unittest.TestCase):
    def test_parse_common_tradingview_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tv.csv"
            path.write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-02,100,110,99,105,12345\n",
                encoding="utf-8",
            )

            result = parse_tradingview_csv(path)

            self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
            self.assertEqual(result.loc[0, "open"], 100.0)
            self.assertEqual(result.loc[0, "volume"], 12345.0)

    def test_parse_accepts_capitalized_ohlc_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tv.csv"
            path.write_text(
                "Time,Open,High,Low,Close,Volume\n"
                "2024-01-02T00:00:00Z,100,110,99,105,12345\n",
                encoding="utf-8",
            )

            result = parse_tradingview_csv(path)

            self.assertEqual(result.loc[0, "close"], 105.0)


if __name__ == "__main__":
    unittest.main()
