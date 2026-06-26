import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    build_financial_pit_post_announcement_drift_preregistration,
    write_financial_pit_post_announcement_drift_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore


class FinancialPitPostAnnouncementDriftPreregistrationTests(unittest.TestCase):
    def test_builds_pit_event_reaction_coverage_without_same_day_trading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")

            result = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["financial_assets"], 3)
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertEqual(result["summary"]["event_reaction_available_rows"], 6)
            self.assertEqual(result["summary"]["reaction_available_before_or_on_ann_date_rows"], 0)
            self.assertAlmostEqual(result["summary"]["event_reaction_coverage"], 1.0)
            self.assertFalse(result["pit_policy"]["same_day_announcement_trading_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertIn(
                "pead_event_reaction_continuation_1_20",
                {candidate["factor_name"] for candidate in result["candidates"]},
            )

    def test_blocks_when_event_reaction_is_not_available_after_signal_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_without_reaction_available_date())

            result = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=None,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("event_reaction_coverage_below_threshold", result["summary"]["blockers"])
            self.assertGreater(result["summary"]["reaction_available_date_missing_rows"], 0)
            self.assertFalse(any(candidate["registration_status"] == "pre_registered" for candidate in result["candidates"]))

    def test_excludes_final_holdout_dates_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial(financial_root, _financial_rows_with_2026())
            _write_bars(bars_root, _bar_rows_with_2026())

            result = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["holdout_policy"]["final_holdout_included"], False)
            self.assertLessEqual(result["summary"]["max_signal_date"], "2025-12-31")
            self.assertLessEqual(result["summary"]["max_reaction_available_date"], "2025-12-31")

    def test_write_outputs_json_markdown_and_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_dir = root / "output"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())

            result = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_drift_preregistration(output_dir, result)

            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_preregistration.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_preregistration.md").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_candidates.csv").exists())


def _financial_rows() -> pd.DataFrame:
    rows = []
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for quarter, ann_date in enumerate([pd.Timestamp("2024-01-02"), pd.Timestamp("2024-04-01")]):
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": asset_id,
                    "symbol": asset_id[-6:] + ".SZ",
                    "market": "CN",
                    "source": "fixture",
                    "ann_date": ann_date,
                    "end_date": pd.Timestamp("2023-12-31") + pd.DateOffset(months=quarter * 3),
                    "signal_date": ann_date + pd.offsets.BDay(1),
                    "available_date": ann_date + pd.offsets.BDay(1),
                    "signal_lag_calendar_days": 1,
                    "roe": 10.0 + asset_index + quarter,
                    "netprofit_yoy": 5.0 + asset_index + quarter,
                    "or_yoy": 3.0 + asset_index,
                    "ocfps": 1.0 + quarter,
                }
            )
    return pd.DataFrame(rows)


def _financial_rows_with_2026() -> pd.DataFrame:
    frame = _financial_rows()
    future = frame.iloc[:3].copy()
    future["ann_date"] = pd.Timestamp("2026-05-06")
    future["date"] = pd.Timestamp("2026-05-06")
    future["end_date"] = pd.Timestamp("2026-03-31")
    future["signal_date"] = pd.Timestamp("2026-05-07")
    future["available_date"] = pd.Timestamp("2026-05-07")
    return pd.concat([frame, future], ignore_index=True)


def _bar_rows() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", "2024-04-05")
    rows = []
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for day_index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": 10.0 + asset_index + day_index * 0.01,
                    "close": 10.1 + asset_index + day_index * 0.01,
                    "adj_close": 10.1 + asset_index + day_index * 0.01,
                    "volume": 1000000 + day_index,
                    "amount": 20000000 + day_index,
                }
            )
    return pd.DataFrame(rows)


def _bar_rows_with_2026() -> pd.DataFrame:
    frame = _bar_rows()
    dates = pd.bdate_range("2026-05-06", "2026-05-12")
    rows = []
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for day_index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": 20.0 + asset_index + day_index * 0.01,
                    "close": 20.1 + asset_index + day_index * 0.01,
                    "adj_close": 20.1 + asset_index + day_index * 0.01,
                    "volume": 1000000 + day_index,
                    "amount": 20000000 + day_index,
                }
            )
    return pd.concat([frame, pd.DataFrame(rows)], ignore_index=True)


def _bar_rows_without_reaction_available_date() -> pd.DataFrame:
    return _bar_rows()[lambda frame: pd.to_datetime(frame["date"]).dt.date <= pd.Timestamp("2024-04-02").date()]


def _seed() -> dict:
    return {
        "family": "financial_pit_post_announcement_drift",
        "candidate_ideas": [
            "pead_event_reaction_continuation_1_20",
            "pead_event_gap_underreaction_1_20",
            "pead_volume_disagreement_drift_1_20",
        ],
        "mandatory_controls": ["financial_pit_signal_date_filter_required"],
    }


def _write_financial(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "pit_signal"},
    )


def _write_bars(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
