import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.authority_bars import (
    AuthorityBarSegment,
    load_authority_bars_config,
    load_authority_processed_bars,
    load_authority_processed_bars_from_config,
)
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

    def test_load_authority_bars_config_reads_adjusted_ratio_repair_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "repair_adjusted_ratio_mass_jumps": True,
                        "adjusted_ratio_jump_threshold": 2.5,
                        "adjusted_ratio_mass_jump_asset_threshold": 25,
                        "segments": [{"root": "data/processed/first"}],
                    }
                ),
                encoding="utf-8",
            )

            config = load_authority_bars_config(path)

            self.assertTrue(config.repair_adjusted_ratio_mass_jumps)
            self.assertEqual(config.adjusted_ratio_jump_threshold, 2.5)
            self.assertEqual(config.adjusted_ratio_mass_jump_asset_threshold, 25)
            self.assertFalse(config.exclude_adjusted_ratio_jump_assets)

    def test_load_authority_bars_config_reads_adjusted_ratio_jump_asset_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "exclude_adjusted_ratio_jump_assets": True,
                        "segments": [{"root": "data/processed/first"}],
                    }
                ),
                encoding="utf-8",
            )

            config = load_authority_bars_config(path)

            self.assertTrue(config.exclude_adjusted_ratio_jump_assets)

    def test_authority_config_loader_repairs_mass_adjusted_ratio_jumps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "store"
            _write_bars(
                store,
                [
                    _bar("2024-01-02", asset_id="CN_XSHE_000001", symbol="000001.SZ", close=10.0, adj_close=10.0),
                    _bar("2024-01-03", asset_id="CN_XSHE_000001", symbol="000001.SZ", close=10.5, adj_close=525.0),
                    _bar("2024-01-04", asset_id="CN_XSHE_000001", symbol="000001.SZ", close=11.0, adj_close=550.0),
                    _bar("2024-01-02", asset_id="CN_XSHE_000002", symbol="000002.SZ", close=20.0, adj_close=20.0),
                    _bar("2024-01-03", asset_id="CN_XSHE_000002", symbol="000002.SZ", close=20.5, adj_close=410.0),
                    _bar("2024-01-04", asset_id="CN_XSHE_000002", symbol="000002.SZ", close=21.0, adj_close=420.0),
                ],
            )
            config_path = root / "authority.json"
            config_path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "repair_adjusted_ratio_mass_jumps": True,
                        "adjusted_ratio_jump_threshold": 2.0,
                        "adjusted_ratio_mass_jump_asset_threshold": 2,
                        "segments": [{"root": str(store)}],
                    }
                ),
                encoding="utf-8",
            )

            repaired = load_authority_processed_bars_from_config(config_path, markets=("CN",))

            repaired = repaired.sort_values(["asset_id", "date"]).reset_index(drop=True)
            self.assertEqual(repaired.loc[1, "adj_close"], 10.5)
            self.assertEqual(repaired.loc[2, "adj_close"], 11.0)
            self.assertEqual(repaired.loc[4, "adj_close"], 20.5)
            self.assertEqual(repaired.loc[5, "adj_close"], 21.0)

    def test_authority_config_loader_excludes_assets_with_adjusted_ratio_jumps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "store"
            _write_bars(
                store,
                [
                    _bar("2024-01-02", asset_id="CN_XSHE_CLEAN", symbol="000001.SZ", close=10.0, adj_close=10.0),
                    _bar("2024-01-03", asset_id="CN_XSHE_CLEAN", symbol="000001.SZ", close=10.5, adj_close=10.5),
                    _bar("2024-01-04", asset_id="CN_XSHE_CLEAN", symbol="000001.SZ", close=11.0, adj_close=11.0),
                    _bar("2024-01-02", asset_id="CN_XSHE_BAD", symbol="000002.SZ", close=20.0, adj_close=20.0),
                    _bar("2024-01-03", asset_id="CN_XSHE_BAD", symbol="000002.SZ", close=20.5, adj_close=410.0),
                    _bar("2024-01-04", asset_id="CN_XSHE_BAD", symbol="000002.SZ", close=21.0, adj_close=420.0),
                ],
            )
            config_path = root / "authority.json"
            config_path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "exclude_adjusted_ratio_jump_assets": True,
                        "adjusted_ratio_jump_threshold": 2.0,
                        "segments": [{"root": str(store)}],
                    }
                ),
                encoding="utf-8",
            )

            bars = load_authority_processed_bars_from_config(config_path, markets=("CN",))

            self.assertEqual(set(bars["asset_id"]), {"CN_XSHE_CLEAN"})


def _write_bars(root: Path, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _bar(
    date: str,
    *,
    close: float,
    adjusted: bool = True,
    asset_id: str = "CN_XSHE_000001",
    symbol: str = "000001.SZ",
    adj_close: float | None = None,
) -> dict:
    stamp = pd.Timestamp(date)
    return {
        "asset_id": asset_id,
        "symbol": symbol,
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
        "adj_close": adj_close if adj_close is not None else close if adjusted else close / 2.0,
        "volume": 1000.0,
        "amount": close * 1000.0,
        "vwap": close,
        "currency": "CNY",
        "source": "tushare",
        "adjusted": adjusted,
        "ingested_at": pd.Timestamp("2024-01-01", tz="UTC"),
    }
