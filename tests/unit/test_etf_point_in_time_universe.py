import tempfile
import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.data.etf_point_in_time_universe import (
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)


class EtfPointInTimeUniverseTests(unittest.TestCase):
    def test_eligibility_uses_official_lifecycle_and_trailing_only_inputs(self) -> None:
        bars, lifecycle, dates = _eligibility_fixture()
        policy = EtfEligibilityPolicy(
            min_prior_observations=3,
            liquidity_window=3,
            min_trailing_median_amount=5_000_000.0,
            max_stale_rate=0.05,
            max_abs_return=0.20,
        )

        result = build_point_in_time_etf_eligibility(bars, lifecycle, policy=policy)

        self.assertTrue(_row(result, "CN_ETF_XSHG_510001", dates[4])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510002", dates[4])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510003", dates[5])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510004", dates[4])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510005", dates[4])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510006", dates[4])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510007", dates[-1])["eligible"])
        self.assertFalse(_row(result, "CN_ETF_XSHG_510008", dates[4])["eligible"])

        future = pd.DataFrame(
            [
                {
                    "date": dates[-1] + pd.offsets.BDay(1),
                    "asset_id": "CN_ETF_XSHG_510001",
                    "symbol": "510001.SH",
                    "market": "CN_ETF",
                    "adj_close": 999.0,
                    "amount": 1_000_000_000_000.0,
                }
            ]
        )
        with_future = build_point_in_time_etf_eligibility(
            pd.concat([bars, future], ignore_index=True),
            lifecycle,
            policy=policy,
        )
        columns = [
            "date",
            "asset_id",
            "prior_observations",
            "trailing_median_amount",
            "trailing_stale_rate",
            "eligible",
        ]
        cutoff = pd.Timestamp(dates[-1])
        baseline = result[result["date"] <= cutoff][columns].reset_index(drop=True)
        observed = with_future[with_future["date"] <= cutoff][columns].reset_index(drop=True)
        assert_frame_equal(baseline, observed)

    def test_history_count_starts_at_official_list_date(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=7)
        bars = pd.DataFrame(_asset_rows("510010.SH", "CN_ETF_XSHG_510010", dates, amount=10_000_000.0))
        lifecycle = pd.DataFrame(
            [
                {
                    "symbol": "510010.SH",
                    "is_etf": True,
                    "list_date": dates[3],
                    "delist_date": pd.NaT,
                }
            ]
        )

        result = build_point_in_time_etf_eligibility(
            bars,
            lifecycle,
            policy=EtfEligibilityPolicy(
                min_prior_observations=2,
                liquidity_window=2,
                min_trailing_median_amount=1.0,
                max_stale_rate=1.0,
                max_abs_return=1.0,
            ),
        )

        self.assertEqual(_row(result, "CN_ETF_XSHG_510010", dates[3])["prior_observations"], 0)
        self.assertEqual(_row(result, "CN_ETF_XSHG_510010", dates[5])["prior_observations"], 2)
        self.assertTrue(_row(result, "CN_ETF_XSHG_510010", dates[5])["eligible"])

    def test_loads_official_etf_lifecycle_and_fails_on_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = pd.DataFrame(
                [
                    {
                        "symbol": "510300.SH",
                        "is_etf": True,
                        "list_date": "2012-05-28",
                        "delist_date": None,
                    },
                    {
                        "symbol": "150001.SZ",
                        "is_etf": False,
                        "list_date": "2012-08-17",
                        "delist_date": "2015-08-14",
                    },
                ]
            )
            frame.to_parquet(root / "part-00000.parquet", index=False)

            lifecycle = load_official_etf_lifecycle(root)

            self.assertEqual(lifecycle["symbol"].tolist(), ["510300.SH"])
            self.assertEqual(lifecycle.iloc[0]["list_date"], pd.Timestamp("2012-05-28"))

            frame.iloc[[0, 0]].to_parquet(root / "part-00000.parquet", index=False)
            with self.assertRaisesRegex(ValueError, "duplicate official ETF lifecycle symbols"):
                load_official_etf_lifecycle(root)

    def test_loader_consolidates_dated_snapshots_and_preserves_older_only_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "snapshot=2026-06-21"
            latest = root / "snapshot=2026-07-16"
            older.mkdir()
            latest.mkdir()
            pd.DataFrame(
                [
                    {
                        "symbol": "510300.SH",
                        "is_etf": True,
                        "list_date": "2012-05-28",
                        "delist_date": None,
                    },
                    {
                        "symbol": "510500.SH",
                        "is_etf": True,
                        "list_date": "2013-03-15",
                        "delist_date": "2024-06-28",
                    },
                ]
            ).to_parquet(older / "part-00000.parquet", index=False)
            pd.DataFrame(
                [
                    {
                        "symbol": "510300.SH",
                        "is_etf": True,
                        "list_date": "2012-05-28",
                        "delist_date": "2026-07-15",
                    }
                ]
            ).to_parquet(latest / "part-00000.parquet", index=False)

            lifecycle = load_official_etf_lifecycle(root).set_index("symbol")

            self.assertEqual(set(lifecycle.index), {"510300.SH", "510500.SH"})
            self.assertEqual(lifecycle.loc["510300.SH", "delist_date"], pd.Timestamp("2026-07-15"))
            self.assertEqual(lifecycle.loc["510500.SH", "delist_date"], pd.Timestamp("2024-06-28"))

    def test_rejects_reversed_official_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pd.DataFrame(
                [
                    {
                        "symbol": "510300.SH",
                        "is_etf": True,
                        "list_date": "2024-01-10",
                        "delist_date": "2024-01-09",
                    }
                ]
            ).to_parquet(root / "part-00000.parquet", index=False)

            with self.assertRaisesRegex(ValueError, "reversed official ETF lifecycle"):
                load_official_etf_lifecycle(root)


def _eligibility_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.bdate_range("2024-01-02", periods=8)
    rows = []
    rows.extend(_asset_rows("510001.SH", "CN_ETF_XSHG_510001", dates, amount=10_000_000.0))
    rows.extend(_asset_rows("510002.SH", "CN_ETF_XSHG_510002", dates, amount=10_000_000.0))
    rows.extend(_asset_rows("510003.SH", "CN_ETF_XSHG_510003", dates, amount=10_000_000.0))
    rows.extend(_asset_rows("510004.SH", "CN_ETF_XSHG_510004", dates, amount=10_000_000.0))
    rows.extend(_asset_rows("510005.SH", "CN_ETF_XSHG_510005", dates, amount=10_000_000.0))
    rows.extend(_asset_rows("510006.SH", "CN_ETF_XSHG_510006", dates, amount=10_000_000.0, flat=True))
    rows.extend(_asset_rows("510007.SH", "CN_ETF_XSHG_510007", dates[-3:], amount=10_000_000.0))
    rows.extend(_asset_rows("510008.SH", "CN_ETF_XSHG_510008", dates, amount=1_000_000.0))
    lifecycle = pd.DataFrame(
        [
            {"symbol": "510001.SH", "is_etf": True, "list_date": dates[0], "delist_date": pd.NaT},
            {"symbol": "510002.SH", "is_etf": True, "list_date": dates[6], "delist_date": pd.NaT},
            {"symbol": "510003.SH", "is_etf": True, "list_date": dates[0], "delist_date": dates[4]},
            {"symbol": "510005.SH", "is_etf": False, "list_date": dates[0], "delist_date": pd.NaT},
            {"symbol": "510006.SH", "is_etf": True, "list_date": dates[0], "delist_date": pd.NaT},
            {"symbol": "510007.SH", "is_etf": True, "list_date": dates[0], "delist_date": pd.NaT},
            {"symbol": "510008.SH", "is_etf": True, "list_date": dates[0], "delist_date": pd.NaT},
        ]
    )
    return pd.DataFrame(rows), lifecycle, dates


def _asset_rows(
    symbol: str,
    asset_id: str,
    dates: pd.DatetimeIndex,
    *,
    amount: float,
    flat: bool = False,
) -> list[dict[str, object]]:
    rows = []
    for index, signal_date in enumerate(dates):
        rows.append(
            {
                "date": signal_date,
                "asset_id": asset_id,
                "symbol": symbol,
                "market": "CN_ETF",
                "adj_close": 10.0 if flat else 10.0 + index * 0.1,
                "amount": amount,
            }
        )
    return rows


def _row(frame: pd.DataFrame, asset_id: str, signal_date: pd.Timestamp) -> pd.Series:
    match = frame[(frame["asset_id"] == asset_id) & (frame["date"] == pd.Timestamp(signal_date))]
    if len(match) != 1:
        raise AssertionError(f"Expected one row for {asset_id} on {signal_date}, found {len(match)}")
    return match.iloc[0]
