import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_asset_session_integrity_audit import (
    build_cn_stock_asset_session_integrity_audit,
    write_cn_stock_asset_session_integrity_audit,
)


class CNStockAssetSessionIntegrityAuditTests(unittest.TestCase):
    def test_unresolved_sessions_and_lifecycle_contamination_are_blockers(self):
        bars = _bars(["2024-01-02", "2024-01-04", "2024-01-05"], exchange="XBEI")
        stock_basic = _stock_basic(list_date="2024-01-04")

        packet, classification = build_cn_stock_asset_session_integrity_audit(
            bars=bars,
            expected_sessions=_sessions(),
            stock_basic=stock_basic,
            source_root="authority.json",
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("observed_outside_official_lifecycle:1", packet["decision"]["blockers"])
        self.assertFalse(packet["decision"]["asset_session_integrity_cleared"])
        self.assertEqual(classification.summary["before_official_list_date_rows"], 1)
        self.assertFalse(packet["live_boundary_allowed"])
        self.assertIn("Research-to-review only", packet["safety"])

    def test_daily_suspension_evidence_can_clear_audit(self):
        bars = _bars(["2024-01-02", "2024-01-04"])
        daily = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2024-01-03"],
                "source": ["tushare_suspend_d"],
            }
        )

        packet, _ = build_cn_stock_asset_session_integrity_audit(
            bars=bars,
            expected_sessions=_sessions(end="2024-01-04"),
            stock_basic=_stock_basic(),
            daily_suspension=daily,
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertTrue(packet["decision"]["asset_session_integrity_cleared"])

    def test_legacy_suspension_evidence_requires_review(self):
        bars = _bars(["2024-01-02", "2024-01-04"])
        legacy = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "suspend_date": ["2024-01-03"],
                "resume_date": ["2024-01-04"],
            }
        )

        packet, _ = build_cn_stock_asset_session_integrity_audit(
            bars=bars,
            expected_sessions=_sessions(end="2024-01-04"),
            stock_basic=_stock_basic(),
            legacy_suspension=legacy,
        )

        self.assertEqual(packet["status"], "review_required")
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertEqual(
            packet["decision"]["review_reasons"],
            ["retrospective_legacy_suspension_evidence"],
        )

    def test_writer_emits_complete_deterministic_artifact_set(self):
        bars = _bars(["2024-01-02", "2024-01-04"])
        packet, classification = build_cn_stock_asset_session_integrity_audit(
            bars=bars,
            expected_sessions=_sessions(end="2024-01-04"),
            stock_basic=_stock_basic(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_stock_asset_session_integrity_audit(output, packet, classification)

            expected = {
                "cn_stock_asset_session_integrity_audit.json",
                "cn_stock_asset_session_integrity_audit.md",
                "asset_session_gap_classifications.csv",
                "unresolved_asset_sessions.csv",
                "unresolved_assets.csv",
                "observed_outside_lifecycle.csv",
                "coverage_by_asset.csv",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            payload = json.loads(
                (output / "cn_stock_asset_session_integrity_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["stage"], "cn_stock_asset_session_integrity_audit")
            unresolved = pd.read_csv(output / "unresolved_asset_sessions.csv")
            self.assertEqual(unresolved.loc[0, "classification"], "unresolved_active_session")


def _bars(dates: list[str], *, exchange: str = "XSHE") -> pd.DataFrame:
    asset_id = "CN_XBEI_920001" if exchange == "XBEI" else "CN_XSHE_000001"
    symbol = "920001.BJ" if exchange == "XBEI" else "000001.SZ"
    return pd.DataFrame(
        {
            "asset_id": [asset_id] * len(dates),
            "symbol": [symbol] * len(dates),
            "exchange": [exchange] * len(dates),
            "market": ["CN"] * len(dates),
            "date": dates,
        }
    )


def _stock_basic(*, list_date: str = "2020-01-01") -> pd.DataFrame:
    is_xbei = list_date == "2024-01-04"
    return pd.DataFrame(
        {
            "asset_id": ["CN_XBEI_920001" if is_xbei else "CN_XSHE_000001"],
            "symbol": ["920001.BJ" if is_xbei else "000001.SZ"],
            "list_date": [list_date],
            "delist_date": [None],
        }
    )


def _sessions(*, end: str = "2024-01-05") -> pd.DataFrame:
    return pd.DataFrame({"date": pd.date_range("2024-01-02", end, freq="B")})


if __name__ == "__main__":
    unittest.main()
