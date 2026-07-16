import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.cn_etf_peer_mapping import load_cn_etf_peer_mapping
from quant_robot.storage.dataset_store import DatasetStore
from scripts.ingest_tushare_etf_basic import run_tushare_etf_basic_ingest


class _Adapter:
    def __init__(self, index_code: str = "000300.SH") -> None:
        self.index_code = index_code

    def fetch_etf_basic(self, list_status: str = "") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "symbol": "510300.SH",
                    "name": "300ETF",
                    "extended_name": "沪深300ETF",
                    "full_name": "沪深300交易型开放式指数基金",
                    "index_code": self.index_code,
                    "index_name": "沪深300指数",
                    "setup_date": pd.Timestamp("2012-05-28").date(),
                    "list_date": pd.Timestamp("2012-05-28").date(),
                    "list_status": "L",
                    "exchange": "SH",
                    "manager": "Manager A",
                    "custodian": "Bank A",
                    "management_fee": 0.5,
                    "etf_type": "境内",
                    "is_active": True,
                }
            ]
        )


class _EmptyAdapter:
    def fetch_etf_basic(self, list_status: str = "") -> pd.DataFrame:
        return pd.DataFrame()


class IngestTushareEtfBasicTests(unittest.TestCase):
    def test_ingest_writes_official_snapshot_and_conservative_peer_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_etf_basic_ingest(
                _Adapter(),
                tmp,
                snapshot="2026-07-16",
            )

            raw = DatasetStore(tmp).read_frame(
                "metadata/tushare_etf_basic",
                {"market": "CN_ETF", "snapshot": "2026-07-16"},
            )
            mapping = load_cn_etf_peer_mapping(tmp)
            self.assertEqual(result["rows"], 1)
            self.assertEqual(result["peer_mapping_rows"], 1)
            self.assertEqual(raw.loc[0, "index_code"], "000300.SH")
            self.assertEqual(mapping.loc[0, "peer_id"], "000300.SH")
            self.assertEqual(str(mapping.loc[0, "known_from"]), "2026-07-16")
            self.assertEqual(str(mapping.loc[0, "valid_from"]), "2026-07-16")

    def test_later_snapshot_closes_previous_mapping_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_etf_basic_ingest(_Adapter("000300.SH"), tmp, snapshot="2026-07-16")
            run_tushare_etf_basic_ingest(_Adapter("000905.SH"), tmp, snapshot="2026-08-01")

            mapping = load_cn_etf_peer_mapping(tmp)
            self.assertEqual(len(mapping), 2)
            self.assertEqual(str(mapping.loc[0, "valid_to"]), "2026-07-31")
            self.assertEqual(mapping.loc[1, "peer_id"], "000905.SH")

    def test_empty_provider_response_is_rejected_without_writing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "returned no rows"):
                run_tushare_etf_basic_ingest(
                    _EmptyAdapter(),
                    tmp,
                    snapshot="2026-07-16",
                )

            self.assertFalse((Path(tmp) / "metadata").exists())


if __name__ == "__main__":
    unittest.main()
