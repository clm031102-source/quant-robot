import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    build_financial_pit_post_announcement_drift_preregistration,
    write_financial_pit_post_announcement_drift_preregistration,
)
from quant_robot.ops.financial_pit_post_announcement_drift_residual_prescreen import (
    build_financial_pit_post_announcement_drift_residual_prescreen,
)
from quant_robot.storage.dataset_store import DatasetStore


class FinancialPitPostAnnouncementDriftResidualPrescreenTests(unittest.TestCase):
    def test_builds_residual_prescreen_from_preregistered_pead_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            prereg_output = root / "prereg"
            seed_path = root / "seed.json"
            financial = _financial_rows(assets=6)
            asset_ids = financial["asset_id"].drop_duplicates().tolist()
            _write_financial(financial_root, financial)
            _write_bars(bars_root, asset_ids)
            _write_daily_basic(daily_basic_root, asset_ids)
            _write_stock_basic(stock_basic_root, asset_ids)
            seed_path.write_text(json.dumps(_seed_all_candidates()), encoding="utf-8")
            prereg = build_financial_pit_post_announcement_drift_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=6,
                min_signal_dates=4,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_drift_preregistration(prereg_output, prereg)

            result = build_financial_pit_post_announcement_drift_residual_prescreen(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-10.0,
                min_neutral_retention=0.0,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_drift_residual_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 7)
            self.assertGreater(result["summary"]["factor_rows"], 0)
            self.assertGreater(result["summary"]["test_count"], 0)
            self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["live_boundary_allowed"])
            self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")


def _seed_all_candidates() -> dict:
    return {
        "family": "financial_pit_post_announcement_drift",
        "candidate_ideas": [
            "pead_event_reaction_continuation_1_20",
            "pead_event_gap_underreaction_1_20",
            "pead_volume_disagreement_drift_1_20",
            "pead_late_announcer_risk_reversal_5_20",
            "pead_positive_fundamental_change_low_reaction_20",
            "pead_negative_surprise_reaction_avoidance_20",
            "pead_reaction_quality_residual_composite_20",
        ],
        "mandatory_controls": ["financial_pit_signal_date_filter_required"],
    }


def _financial_rows(assets: int) -> pd.DataFrame:
    rows = []
    periods = pd.period_range("2023Q1", "2024Q4", freq="Q")
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        for period_idx, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=15 + asset_idx)
            signal_date = ann_date + pd.offsets.BDay(1)
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "signal_date": signal_date,
                    "available_date": signal_date,
                    "netprofit_yoy": 5.0 + period_idx * 0.8 + asset_idx * 0.3,
                    "or_yoy": 4.0 + period_idx * 0.5 + asset_idx * 0.2,
                    "roe": 8.0 + period_idx * 0.2 + asset_idx * 0.1,
                    "ocfps": 1.0 + period_idx * 0.1,
                }
            )
    return pd.DataFrame(rows)


def _write_financial(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "pit_signal"},
    )


def _write_bars(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2023-04-01", "2025-03-31")
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        for day_index, day in enumerate(dates):
            price = 10.0 + asset_idx * 0.5 + day_index * (0.01 + asset_idx * 0.0005)
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price * (1.001 + asset_idx * 0.0001),
                    "adj_close": price * (1.001 + asset_idx * 0.0001),
                    "volume": 1000000 + asset_idx * 1000 + day_index,
                    "amount": 20000000 + asset_idx * 100000 + day_index * 1000,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_daily_basic(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2023-04-01", "2025-03-31")
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        for day in dates:
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "turnover_rate": 0.8 + (asset_idx % 3) * 0.1,
                    "turnover_rate_f": 1.0 + (asset_idx % 3) * 0.1,
                    "volume_ratio": 1.2 + (asset_idx % 2) * 0.1,
                    "total_mv": 10_000_000 + asset_idx * 100_000,
                    "circ_mv": 8_000_000 + asset_idx * 100_000,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_stock_basic(root: Path, asset_ids: list[str]) -> None:
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        rows.append(
            {
                "asset_id": asset_id,
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "industry": "Tech" if asset_idx < len(asset_ids) // 2 else "Bank",
            }
        )
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(root / "stock_basic.csv", index=False)


if __name__ == "__main__":
    unittest.main()
