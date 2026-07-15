import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_stock_asset_session_integrity_audit import main, run_cn_stock_asset_session_integrity_audit


class CNStockAssetSessionIntegrityAuditCliTests(unittest.TestCase):
    def test_run_accepts_in_memory_evidence_and_writes_packet(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "exchange": ["XSHE", "XSHE"],
                "market": ["CN", "CN"],
                "date": ["2024-01-02", "2024-01-04"],
            }
        )
        stock_basic = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "symbol": ["000001.SZ"],
                "list_date": ["2020-01-01"],
                "delist_date": [None],
            }
        )
        daily = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2024-01-03"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            packet = run_cn_stock_asset_session_integrity_audit(
                data_root="authority.json",
                output_dir=tmp,
                bars=bars,
                expected_sessions=pd.DataFrame(
                    {"date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])}
                ),
                stock_basic=stock_basic,
                daily_suspension=daily,
            )

            self.assertEqual(packet["status"], "cleared")
            self.assertTrue((Path(tmp) / "cn_stock_asset_session_integrity_audit.json").exists())

    def test_main_requires_allow_blocked_for_blocked_packet(self):
        blocked = {
            "status": "blocked",
            "summary": {},
            "decision": {"blockers": ["unresolved_active_sessions:1"]},
        }

        with (
            patch(
                "scripts.run_cn_stock_asset_session_integrity_audit.run_cn_stock_asset_session_integrity_audit",
                return_value=blocked,
            ),
            patch("sys.argv", ["run_cn_stock_asset_session_integrity_audit.py"]),
            self.assertRaises(SystemExit) as raised,
        ):
            main()
        self.assertEqual(raised.exception.code, 3)

        with (
            patch(
                "scripts.run_cn_stock_asset_session_integrity_audit.run_cn_stock_asset_session_integrity_audit",
                return_value=blocked,
            ),
            patch(
                "sys.argv",
                ["run_cn_stock_asset_session_integrity_audit.py", "--allow-blocked"],
            ),
        ):
            main()


if __name__ == "__main__":
    unittest.main()
