import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.authority_bars import AuthorityBarSegment, load_authority_bars_config, load_authority_processed_bars
from quant_robot.storage.dataset_store import DatasetStore


class AuthorityBarsTests(unittest.TestCase):
    def test_authority_loader_filters_segments_adjusted_rows_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            _write_bars(
                first,
                [
                    _bar("2024-01-02", close=10.0, adjusted=True),
                    _bar("2024-01-03", close=11.0, adjusted=True),
                    _bar("2024-01-04", close=12.0, adjusted=False),
                ],
            )
            _write_bars(
                second,
                [
                    _bar("2024-01-04", close=12.5, adjusted=True),
                    _bar("2024-01-05", close=13.0, adjusted=True),
                ],
            )

            bars = load_authority_processed_bars(
                [
                    AuthorityBarSegment(root=first, end_date="2024-01-03"),
                    AuthorityBarSegment(root=second, start_date="2024-01-04"),
                ],
                market="CN",
            )

            self.assertEqual(pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d").tolist(), ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
            self.assertTrue(bars["adjusted"].all())
            self.assertFalse(bars.duplicated(["asset_id", "timestamp", "frequency", "source"]).any())

    def test_authority_loader_rejects_duplicate_authority_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            _write_bars(first, [_bar("2024-01-02", close=10.0, adjusted=True)])
            _write_bars(second, [_bar("2024-01-02", close=10.5, adjusted=True)])

            with self.assertRaisesRegex(ValueError, "duplicate authority bars"):
                load_authority_processed_bars(
                    [
                        AuthorityBarSegment(root=first),
                        AuthorityBarSegment(root=second),
                    ],
                    market="CN",
                )

    def test_load_authority_bars_config_reads_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "segments": [
                            {"root": "data/processed/first", "end_date": "2023-06-30"},
                            {"root": "data/processed/second", "start_date": "2023-07-03", "adjusted_only": False},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            config = load_authority_bars_config(path)

            self.assertEqual(config.market, "CN")
            self.assertEqual(config.segments[0].root, Path("data/processed/first"))
            self.assertEqual(config.segments[0].end_date, "2023-06-30")
            self.assertFalse(config.segments[1].adjusted_only)


def _write_bars(root: Path, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _bar(date: str, *, close: float, adjusted: bool) -> dict:
    stamp = pd.Timestamp(date)
    return {
        "asset_id": "CN_XSHE_000001",
        "symbol": "000001.SZ",
        "market": "CN",
        "exchange": "XSHE",
        "asset_type": "stock",
        "timestamp": stamp.tz_localize("Asia/Shanghai").tz_convert("UTC"),
        "date": stamp.date(),
        "timezone": "Asia/Shanghai",
        "calendar": "XSHG",
        "frequency": "1d",
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "adj_close": close if adjusted else close / 2.0,
        "volume": 1000.0,
        "amount": close * 1000.0,
        "vwap": close,
        "currency": "CNY",
        "source": "tushare",
        "adjusted": adjusted,
        "ingested_at": pd.Timestamp("2024-01-01", tz="UTC"),
    }
