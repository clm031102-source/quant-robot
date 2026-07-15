import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_stock_price_integrity_audit import main, run_cn_stock_price_integrity_audit


class CNStockPriceIntegrityAuditCliTests(unittest.TestCase):
    def test_run_accepts_in_memory_inputs_and_writes_packet(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "exchange": ["XSHE", "XSHE"],
                "market": ["CN", "CN"],
                "date": ["2024-01-02", "2024-01-03"],
                "close": [10.0, 10.1],
                "adj_close": [10.0, 10.1],
            }
        )
        stock_basic = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "list_date": ["2020-01-01"],
                "delist_date": [None],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            packet = run_cn_stock_price_integrity_audit(
                data_root="authority.json",
                output_dir=tmp,
                bars=bars,
                stock_basic=stock_basic,
            )

            self.assertEqual(packet["status"], "cleared")
            self.assertTrue((Path(tmp) / "cn_stock_price_integrity_audit.json").exists())

    def test_main_requires_allow_blocked_for_blocked_packet(self):
        blocked = {
            "status": "blocked",
            "summary": {},
            "decision": {"blockers": ["raw_price_discontinuity_rows:1"]},
        }
        with (
            patch(
                "scripts.run_cn_stock_price_integrity_audit.run_cn_stock_price_integrity_audit",
                return_value=blocked,
            ),
            patch("sys.argv", ["run_cn_stock_price_integrity_audit.py"]),
            self.assertRaises(SystemExit) as raised,
        ):
            main()
        self.assertEqual(raised.exception.code, 3)

        with (
            patch(
                "scripts.run_cn_stock_price_integrity_audit.run_cn_stock_price_integrity_audit",
                return_value=blocked,
            ),
            patch("sys.argv", ["run_cn_stock_price_integrity_audit.py", "--allow-blocked"]),
        ):
            main()


if __name__ == "__main__":
    unittest.main()
