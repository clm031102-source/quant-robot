import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.data_gap_evidence import build_data_gap_evidence_pack


class DataGapEvidenceTests(unittest.TestCase):
    def test_pack_enriches_gap_rows_with_raw_csv_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "510500_SH_1d.csv").write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-01,1,1,1,1,100\n"
                "2024-01-03,1,1,1,1,120\n",
                encoding="utf-8",
            )
            (raw_dir / "510300_SH_1d.csv").write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-02,1,1,1,1,200\n",
                encoding="utf-8",
            )
            gap_rows = [
                {
                    "gap_id": "DG-CN_ETF_XSHG_510500-20240102",
                    "asset_id": "CN_ETF_XSHG_510500",
                    "symbol": "510500.SH",
                    "missing_date": "2024-01-02",
                    "resolution_status": "needs_review",
                }
            ]

            pack = build_data_gap_evidence_pack(gap_rows, raw_dir)

        self.assertEqual(pack["stage"], "phase_4_16_data_gap_evidence_pack")
        self.assertEqual(pack["summary"]["gap_rows"], 1)
        self.assertEqual(pack["summary"]["target_raw_rows_found"], 0)
        self.assertEqual(pack["summary"]["gaps_with_peer_trading"], 1)
        row = pack["evidence_rows"][0]
        self.assertEqual(row["gap_id"], "DG-CN_ETF_XSHG_510500-20240102")
        self.assertFalse(row["target_raw_row_found"])
        self.assertEqual(row["peer_rows_on_missing_date"], 1)
        self.assertEqual(row["previous_target_date"], "2024-01-01")
        self.assertEqual(row["next_target_date"], "2024-01-03")
        self.assertIn("raw target row absent", row["evidence_note"])
        self.assertIn("verify suspension/no-trade", row["review_hint"])
        self.assertIn("No broker", pack["safety"])
        self.assertIn("Data Gap Evidence Pack", pack["markdown"])

    def test_pack_marks_gap_when_target_raw_row_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "159915_SZ_1d.csv").write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-02,2,2,2,2,300\n",
                encoding="utf-8",
            )
            gap_rows = [
                {
                    "gap_id": "DG-CN_ETF_XSHE_159915-20240102",
                    "asset_id": "CN_ETF_XSHE_159915",
                    "symbol": "159915.SZ",
                    "missing_date": "2024-01-02",
                    "resolution_status": "needs_review",
                }
            ]

            pack = build_data_gap_evidence_pack(gap_rows, raw_dir)

        row = pack["evidence_rows"][0]
        self.assertTrue(row["target_raw_row_found"])
        self.assertEqual(row["peer_rows_on_missing_date"], 0)
        self.assertIn("raw target row exists", row["evidence_note"])
        self.assertIn("rerun batch import", row["review_hint"])


if __name__ == "__main__":
    unittest.main()
