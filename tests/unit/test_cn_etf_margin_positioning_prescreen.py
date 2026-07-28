import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.etf_residual_margin_financing_growth import FACTOR_NAME
from quant_robot.ops.cn_etf_margin_positioning_prescreen import (
    STAGE,
    summarize_cn_etf_margin_positioning_prescreen,
    write_cn_etf_margin_positioning_prescreen,
)
from scripts.run_cn_etf_margin_positioning_prescreen import (
    _exclude_gap_crossing_labels,
    _factor_gap_dates,
)
from tests.unit.test_cn_etf_fund_structure_crowding_prescreen import (
    _frames as fund_structure_frames,
)


class CnEtfMarginPositioningPrescreenTests(unittest.TestCase):
    def test_positive_diagnostic_cannot_rescue_failed_primary(self):
        result = _summarize(_frames(primary_direction=-1.0))

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "close_family_zero_budget")
        self.assertFalse(result["decision"]["primary_passed"])
        self.assertTrue(_row(result, 20)["role_passed"])
        self.assertFalse(_row(result, 20)["research_lead"])

    def test_writer_is_deterministic(self):
        result = _summarize(_frames())
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = write_cn_etf_margin_positioning_prescreen(first, result)
            second_paths = write_cn_etf_margin_positioning_prescreen(second, result)
            self.assertEqual(set(first_paths), set(second_paths))
            for name in first_paths:
                self.assertEqual(
                    Path(first_paths[name]).read_bytes(),
                    Path(second_paths[name]).read_bytes(),
                )

    def test_bar_gap_exclusions_cover_factor_and_forward_label_windows(self):
        sessions = pd.bdate_range("2024-01-02", periods=10)
        gap = sessions[4]

        factor_dates = _factor_gap_dates(
            sessions,
            [gap.date().isoformat()],
            window=3,
        )
        self.assertEqual(factor_dates, set(sessions[4:8]))

        labels = pd.DataFrame(
            {
                "date": list(sessions) * 2,
                "horizon": [2] * len(sessions) + [4] * len(sessions),
            }
        )
        filtered = _exclude_gap_crossing_labels(
            labels,
            official_sessions=sessions,
            gap_dates=[gap.date().isoformat()],
            execution_lag=1,
        )
        observed = {
            horizon: set(pd.to_datetime(group["date"]))
            for horizon, group in filtered.groupby("horizon")
        }
        self.assertTrue(set(sessions[1:5]).isdisjoint(observed[2]))
        self.assertTrue(set(sessions[:5]).isdisjoint(observed[4]))
        self.assertIn(sessions[0], observed[2])
        self.assertIn(sessions[5], observed[4])


def _summarize(frames: dict[str, pd.DataFrame]) -> dict:
    return summarize_cn_etf_margin_positioning_prescreen(
        frames["factors"],
        frames["labels"],
        frames["references"],
        frames["direct"],
        frames["adv20"],
        expected_reference_names=("reference",),
        direct_exposure_names=("margin_financing_growth_20",),
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
    frames = fund_structure_frames(primary_direction=primary_direction)
    frames["factors"]["factor_name"] = FACTOR_NAME
    frames["direct"]["factor_name"] = "margin_financing_growth_20"
    return frames


def _row(result: dict, horizon: int) -> dict:
    return next(row for row in result["results"] if int(row["horizon"]) == horizon)


if __name__ == "__main__":
    unittest.main()
