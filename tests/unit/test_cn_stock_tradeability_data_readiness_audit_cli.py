import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_stock_tradeability_data_readiness_audit import (
    run_cn_stock_tradeability_data_readiness_audit,
)


class CnStockTradeabilityDataReadinessAuditCliTests(unittest.TestCase):
    def test_cli_writes_tradeability_readiness_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            output_dir = root / "output"
            bars = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "open": [10.0],
                    "high": [10.2],
                    "low": [9.8],
                    "close": [10.1],
                    "volume": [1000.0],
                    "amount": [10000.0],
                }
            )
            path = data_root / "processed/bars/frequency=1d/market=CN/year=2015/part-00000.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            bars.to_parquet(path, index=False)

            packet = run_cn_stock_tradeability_data_readiness_audit(
                data_roots=[data_root],
                output_dir=output_dir,
            )

            self.assertEqual(packet["status"], "direct_mining_blocked")
            json_path = output_dir / "cn_stock_tradeability_data_readiness_audit.json"
            md_path = output_dir / "cn_stock_tradeability_data_readiness_audit.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            written = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(written["stage"], "cn_stock_tradeability_data_readiness_audit")
            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("CN Stock Tradeability Data Readiness Audit", markdown)
            self.assertIn("limit_up_down_filter", markdown)


if __name__ == "__main__":
    unittest.main()
