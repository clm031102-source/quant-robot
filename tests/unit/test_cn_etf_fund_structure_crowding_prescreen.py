import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.etf_residual_share_creation_crowding import FACTOR_NAME
from quant_robot.ops.cn_etf_fund_structure_crowding_prescreen import (
    STAGE,
    summarize_cn_etf_fund_structure_crowding_prescreen,
    write_cn_etf_fund_structure_crowding_prescreen,
)


class CnEtfFundStructureCrowdingPrescreenTests(unittest.TestCase):
    def test_primary_passes_and_diagnostic_cannot_become_the_research_lead(self):
        frames = _frames()

        result = _summarize(frames)

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "primary_passed_backfill_required")
        self.assertTrue(result["decision"]["primary_passed"])
        self.assertFalse(_row(result, 20)["research_lead"])
        self.assertFalse(result["decision"]["walk_forward_allowed"])

    def test_positive_diagnostic_cannot_rescue_failed_primary(self):
        result = _summarize(_frames(primary_direction=-1.0))

        self.assertEqual(result["status"], "close_family_zero_budget")
        self.assertFalse(result["decision"]["primary_passed"])
        self.assertTrue(_row(result, 20)["role_passed"])

    def test_writer_is_deterministic(self):
        result = _summarize(_frames())
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = write_cn_etf_fund_structure_crowding_prescreen(first, result)
            second_paths = write_cn_etf_fund_structure_crowding_prescreen(second, result)
            self.assertEqual(set(first_paths), set(second_paths))
            for name in first_paths:
                self.assertEqual(
                    Path(first_paths[name]).read_bytes(),
                    Path(second_paths[name]).read_bytes(),
                )


def _summarize(frames: dict[str, pd.DataFrame]) -> dict:
    return summarize_cn_etf_fund_structure_crowding_prescreen(
        frames["factors"],
        frames["labels"],
        frames["references"],
        frames["direct"],
        frames["adv20"],
        expected_reference_names=("reference",),
        direct_exposure_names=("share_creation_20",),
        horizons=(5, 20),
        primary_horizon=5,
        diagnostic_horizon=20,
        min_cross_section=10,
        min_ic_observations=2,
        min_year_ic_observations=2,
        min_usable_years=1,
        alpha=1.0,
        min_mean_rank_ic=0.02,
        min_icir=0.0,
        min_positive_ic_rate=0.5,
        min_quantile_monotonicity=0.7,
        max_top_quantile_turnover=0.9,
        min_positive_year_rate=0.5,
        max_abs_reference_correlation=0.85,
        direct_min_daily_observations=2,
        max_abs_direct_exposure_correlation=0.85,
        position_value_cny=100_000.0,
        max_one_way_participation_rate=0.01,
        one_way_costs_bps=(5.0, 10.0),
        required_positive_net_spread_bps=10.0,
        diagnostic_min_mean_rank_ic=0.0,
        diagnostic_min_quantile_spread=0.0,
    )


def _frames(*, primary_direction: float = 1.0) -> dict[str, pd.DataFrame]:
    factors = []
    labels = []
    references = []
    direct = []
    adv = []
    for day, date in enumerate(pd.bdate_range("2023-01-02", periods=4)):
        for index in range(10):
            asset = f"A{index:02d}"
            value = float(index)
            factors.append(_factor(date, asset, FACTOR_NAME, value))
            references.append(
                _factor(date, asset, "reference", float(index if day % 2 == 0 else 9 - index))
            )
            direct.append(
                _factor(
                    date,
                    asset,
                    "share_creation_20",
                    float(index if day % 2 == 0 else 9 - index),
                )
            )
            labels.extend(
                [
                    {
                        "date": date,
                        "asset_id": asset,
                        "market": "CN_ETF",
                        "horizon": 5,
                        "forward_return": primary_direction * 0.01 * value,
                    },
                    {
                        "date": date,
                        "asset_id": asset,
                        "market": "CN_ETF",
                        "horizon": 20,
                        "forward_return": 0.005 * value,
                    },
                ]
            )
            adv.append(
                {
                    "date": date,
                    "asset_id": asset,
                    "market": "CN_ETF",
                    "adv20": 20_000_000.0,
                }
            )
    return {
        "factors": pd.DataFrame(factors),
        "labels": pd.DataFrame(labels),
        "references": pd.DataFrame(references),
        "direct": pd.DataFrame(direct),
        "adv20": pd.DataFrame(adv),
    }


def _factor(date, asset, name, value) -> dict:
    return {
        "date": date,
        "asset_id": asset,
        "market": "CN_ETF",
        "factor_name": name,
        "factor_value": value,
        "lookback_window": 60,
    }


def _row(result: dict, horizon: int) -> dict:
    return next(row for row in result["results"] if int(row["horizon"]) == horizon)


if __name__ == "__main__":
    unittest.main()
