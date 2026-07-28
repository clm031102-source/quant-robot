import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.validate_cn_etf_pcf_delivery import validate_cn_etf_pcf_delivery


class ValidateCnEtfPcfDeliveryTests(unittest.TestCase):
    def test_validates_csv_without_writing_canonical_market_data(self):
        frame = pd.DataFrame(
            {
                "trade_date": ["20240102"],
                "ts_code": ["510050.SH"],
                "con_code": ["600000.SH"],
                "qty": [1000],
                "sub_flag": ["allowed"],
                "cpr": [10.0],
                "rdr": [0.0],
                "sca": [12345.0],
                "exchange": ["SH"],
            }
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "delivery.csv"
            output = root / "report"
            frame.to_csv(source, index=False)

            result = validate_cn_etf_pcf_delivery(
                source,
                market_exchange="SSE",
                source_provider="vendor",
                analysis_start="2020-01-02",
                analysis_end="2024-06-28",
                output_dir=output,
            )

            self.assertEqual(
                result["status"],
                "delivery_structurally_valid_source_readiness_required",
            )
            self.assertFalse(result["decision"]["source_ready"])
            self.assertTrue((output / "cn_etf_pcf_delivery_validation.json").is_file())
            self.assertFalse(any(output.glob("*.parquet")))
            written = json.loads(
                (output / "cn_etf_pcf_delivery_validation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(written["source"]["rows"], 1)


if __name__ == "__main__":
    unittest.main()
