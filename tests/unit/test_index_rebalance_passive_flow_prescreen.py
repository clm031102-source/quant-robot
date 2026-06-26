import tempfile
import unittest
import warnings
from pathlib import Path

import pandas as pd

from quant_robot.ops.index_rebalance_passive_flow_prescreen import (
    INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES,
    build_index_rebalance_passive_flow_factor_frame,
    build_index_rebalance_passive_flow_prescreen,
    write_index_rebalance_passive_flow_prescreen,
)


class IndexRebalancePassiveFlowPrescreenTests(unittest.TestCase):
    def test_build_factor_frame_creates_pit_sparse_factors(self):
        factors = build_index_rebalance_passive_flow_factor_frame(_events(), _bars())

        self.assertEqual(set(factors["factor_name"]), set(INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES))
        self.assertTrue((factors["date"] == pd.Timestamp("2024-01-03")).all())
        self.assertEqual(int(factors["asset_id"].nunique()), 5)
        self.assertTrue((factors["adv20_amount"] > 0).all())

        remove = factors[
            (factors["factor_name"] == "index_rebalance_remove_pressure_1d")
            & (factors["asset_id"] == "CN_000002")
        ]
        self.assertLess(float(remove.iloc[0]["factor_value"]), 0.0)

    def test_build_prescreen_blocks_promotion_and_uses_event_gate(self):
        result = build_index_rebalance_passive_flow_prescreen(
            index_events=_events(),
            bars=_bars(),
            stock_basic=_stock_basic(),
            horizons=(1,),
            min_cross_section=5,
            min_ic_observations=1,
            min_neutral_rank_ic=-1.0,
            min_neutral_ic_t_stat=-1.0,
        )

        self.assertEqual(result["stage"], "index_rebalance_passive_flow_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 5)
        self.assertEqual(result["summary"]["test_count"], 5)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertIn("index_rebalance_event_available_date", result["pit_policy"]["event_date_source"])

    def test_write_prescreen_outputs_reusable_files(self):
        result = build_index_rebalance_passive_flow_prescreen(
            index_events=_events(),
            bars=_bars(),
            stock_basic=_stock_basic(),
            horizons=(1,),
            min_cross_section=5,
            min_ic_observations=1,
            min_neutral_rank_ic=-1.0,
            min_neutral_ic_t_stat=-1.0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_index_rebalance_passive_flow_prescreen(output_dir, result)

            self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen.json").exists())
            self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen.md").exists())
            self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen_results.csv").exists())
            self.assertTrue((output_dir / "index_rebalance_passive_flow_factor_rows.csv").exists())

    def test_prescreen_drops_constant_factor_dates_before_ic(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            result = build_index_rebalance_passive_flow_prescreen(
                index_events=_constant_only_events(),
                bars=_bars(),
                stock_basic=_stock_basic(),
                horizons=(1,),
                min_cross_section=5,
                min_ic_observations=1,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-1.0,
            )

        factor_names_with_rows = {row["factor_name"] for row in result["factor_rows"]}
        self.assertIn("index_rebalance_weight_up_pressure_1d", factor_names_with_rows)
        self.assertNotIn("index_rebalance_add_pressure_1d", factor_names_with_rows)
        self.assertNotIn("index_rebalance_remove_pressure_1d", factor_names_with_rows)
        self.assertNotIn("index_rebalance_weight_down_pressure_1d", factor_names_with_rows)


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("CN_000001", "added", 0.0, 0.8, 0.8),
            _event("CN_000002", "removed", 0.7, 0.0, -0.7),
            _event("CN_000003", "weight_changed", 0.2, 0.9, 0.7),
            _event("CN_000004", "weight_changed", 0.9, 0.3, -0.6),
            _event("CN_000005", "weight_changed", 0.4, 0.5, 0.1),
        ]
    )


def _constant_only_events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("CN_000001", "weight_changed", 0.1, 0.2, 0.1),
            _event("CN_000002", "weight_changed", 0.1, 0.3, 0.2),
            _event("CN_000003", "weight_changed", 0.1, 0.4, 0.3),
            _event("CN_000004", "weight_changed", 0.1, 0.5, 0.4),
            _event("CN_000005", "weight_changed", 0.1, 0.6, 0.5),
        ]
    )


def _event(asset_id: str, event_type: str, prior_weight: float, current_weight: float, delta: float) -> dict:
    return {
        "available_date": "2024-01-03",
        "event_date": "2024-01-02",
        "asset_id": asset_id,
        "event_type": event_type,
        "prior_weight": prior_weight,
        "current_weight": current_weight,
        "weight_delta": delta,
        "index_code": "000300.SH",
    }


def _bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2023-12-01", periods=30, freq="B")
    for asset_index in range(1, 6):
        asset_id = f"CN_00000{asset_index}"
        for date_index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0 + asset_index + date_index * (0.01 * asset_index),
                    "amount": 50_000_000 + asset_index * 1_000_000,
                }
            )
    return pd.DataFrame(rows)


def _stock_basic() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": [f"CN_00000{asset_index}" for asset_index in range(1, 6)],
            "industry": ["bank", "bank", "tech", "tech", "health"],
        }
    )


if __name__ == "__main__":
    unittest.main()
