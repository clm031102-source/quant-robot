import unittest

import numpy as np
import pandas as pd

from quant_robot.research.cross_sectional_prescreen_diagnostics import (
    summarize_direct_exposure_correlations,
    summarize_long_short_costs,
    summarize_top_quantile_capacity_by_date,
)


class CrossSectionalPrescreenDiagnosticsTests(unittest.TestCase):
    def test_long_short_costs_charge_initial_entry_and_both_sides(self) -> None:
        factors, labels = _two_date_rotation_frames()

        result = summarize_long_short_costs(
            factors,
            labels,
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            one_way_costs_bps=(5.0, 10.0),
        )

        self.assertEqual(len(result["daily"]), 2)
        first, second = result["daily"]
        self.assertEqual(first["top_turnover"], 1.0)
        self.assertEqual(first["bottom_turnover"], 1.0)
        self.assertEqual(second["top_turnover"], 0.5)
        self.assertEqual(second["bottom_turnover"], 0.5)
        self.assertAlmostEqual(first["gross_top_minus_bottom"], 0.02)
        self.assertAlmostEqual(first["net_top_minus_bottom_10bps"], 0.018)
        self.assertAlmostEqual(second["net_top_minus_bottom_10bps"], 0.019)

        summary = result["summary"][0]
        self.assertEqual(summary["evaluated_dates"], 2)
        self.assertAlmostEqual(summary["avg_top_turnover"], 0.5)
        self.assertAlmostEqual(summary["avg_bottom_turnover"], 0.5)
        self.assertAlmostEqual(summary["mean_gross_top_minus_bottom"], 0.02)
        self.assertAlmostEqual(summary["mean_net_top_minus_bottom_5bps"], 0.01925)
        self.assertAlmostEqual(summary["mean_net_top_minus_bottom_10bps"], 0.0185)

    def test_long_short_costs_skip_invalid_cross_sections_and_ties(self) -> None:
        factors, labels = _two_date_rotation_frames()
        tied_date = pd.Timestamp("2023-01-04")
        tied_factors = pd.DataFrame(
            {
                "date": tied_date,
                "asset_id": [f"A{index:02d}" for index in range(10)],
                "market": "CN_ETF",
                "factor_name": "candidate",
                "factor_value": 1.0,
                "lookback_window": 5,
            }
        )
        tied_labels = tied_factors[["date", "asset_id", "market"]].copy()
        tied_labels["horizon"] = 5
        tied_labels["forward_return"] = 0.01

        result = summarize_long_short_costs(
            pd.concat([factors, tied_factors], ignore_index=True),
            pd.concat([labels, tied_labels], ignore_index=True),
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            one_way_costs_bps=(10.0,),
        )

        self.assertEqual(result["summary"][0]["evaluated_dates"], 2)
        self.assertEqual({row["date"] for row in result["daily"]}, {"2023-01-02", "2023-01-03"})

    def test_capacity_requires_support_on_every_evaluated_date(self) -> None:
        factors, labels, adv = _capacity_frames()

        result = summarize_top_quantile_capacity_by_date(
            factors,
            labels,
            adv,
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            position_value_cny=100_000.0,
            max_one_way_participation_rate=0.01,
        )

        summary = result["summary"][0]
        self.assertEqual(summary["evaluated_dates"], 11)
        self.assertEqual(summary["qualifying_dates"], 10)
        self.assertFalse(summary["every_date_supported"])
        self.assertEqual(summary["worst_date"], "2023-01-02")
        self.assertAlmostEqual(summary["minimum_daily_p10_adv20"], 5_100_000.0)
        self.assertGreater(summary["maximum_daily_participation_rate"], 0.01)
        pooled_p10 = float(
            pd.Series(
                [row["adv20"] for row in result["top_constituents"]]
            ).quantile(0.10)
        )
        self.assertGreaterEqual(pooled_p10, 10_000_000.0)

    def test_capacity_fails_incomplete_top_quintile_adv_coverage(self) -> None:
        factors, labels = _two_date_rotation_frames()
        adv = factors[["date", "asset_id", "market"]].copy()
        adv["adv20"] = 20_000_000.0
        missing = (
            pd.to_datetime(adv["date"]).eq(pd.Timestamp("2023-01-03"))
            & adv["asset_id"].eq("A08")
        )
        adv = adv[~missing]

        result = summarize_top_quantile_capacity_by_date(
            factors,
            labels,
            adv,
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            position_value_cny=100_000.0,
            max_one_way_participation_rate=0.01,
        )

        second = result["daily"][1]
        self.assertEqual(second["top_count"], 2)
        self.assertEqual(second["finite_positive_adv_count"], 1)
        self.assertFalse(second["complete_adv_coverage"])
        self.assertFalse(result["summary"][0]["every_date_supported"])

    def test_direct_exposure_correlation_is_strict_and_complete(self) -> None:
        dates = pd.bdate_range("2023-01-02", periods=3)
        factors = _rank_frames(dates, factor_name="candidate")
        duplicate = _rank_frames(dates, factor_name="market_beta_120")

        result = summarize_direct_exposure_correlations(
            factors,
            duplicate,
            candidate_names=("candidate",),
            exposure_names=("market_beta_120", "log_adv20"),
            min_cross_section=10,
            min_daily_observations=2,
            max_abs_mean_daily_correlation=0.85,
        )

        self.assertEqual(result["summary"]["missing_exposure_names"], ["log_adv20"])
        self.assertEqual(result["summary"]["incomplete_exposure_names"], ["log_adv20"])
        self.assertEqual(result["summary"]["max_exposure_name"], "market_beta_120")
        self.assertAlmostEqual(result["summary"]["max_abs_mean_daily_spearman"], 1.0)
        self.assertFalse(result["summary"]["strict_correlation_ceiling_passed"])
        self.assertFalse(result["summary"]["evidence_complete"])
        self.assertFalse(result["summary"]["passed"])

    def test_direct_exposure_rejects_duplicate_rows(self) -> None:
        dates = pd.bdate_range("2023-01-02", periods=2)
        factors = _rank_frames(dates, factor_name="candidate")
        exposures = _rank_frames(dates, factor_name="market_beta_120")
        exposures = pd.concat([exposures, exposures.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "duplicate factor rows"):
            summarize_direct_exposure_correlations(
                factors,
                exposures,
                candidate_names=("candidate",),
                exposure_names=("market_beta_120",),
                min_cross_section=10,
                min_daily_observations=2,
                max_abs_mean_daily_correlation=0.85,
            )


def _two_date_rotation_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = (pd.Timestamp("2023-01-02"), pd.Timestamp("2023-01-03"))
    orders = (
        [f"A{index:02d}" for index in range(10)],
        ["A00", "A02", "A03", "A04", "A05", "A06", "A09", "A01", "A07", "A08"],
    )
    factor_rows: list[dict[str, object]] = []
    label_rows: list[dict[str, object]] = []
    top_sets = ({"A08", "A09"}, {"A07", "A08"})
    bottom_sets = ({"A00", "A01"}, {"A00", "A02"})
    for signal_date, order, top, bottom in zip(dates, orders, top_sets, bottom_sets, strict=True):
        for rank, asset_id in enumerate(order):
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "factor_name": "candidate",
                    "factor_value": float(rank),
                    "lookback_window": 5,
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "horizon": 5,
                    "forward_return": 0.03 if asset_id in top else 0.01 if asset_id in bottom else 0.02,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows)


def _capacity_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2023-01-02", periods=11)
    factors = _rank_frames(dates, factor_name="candidate")
    labels = factors[["date", "asset_id", "market"]].copy()
    labels["horizon"] = 5
    labels["forward_return"] = factors["factor_value"] / 100.0
    adv = factors[["date", "asset_id", "market"]].copy()
    adv["adv20"] = 100_000_000.0
    first_date = pd.Timestamp(dates[0])
    adv.loc[
        pd.to_datetime(adv["date"]).eq(first_date) & adv["asset_id"].eq("A08"),
        "adv20",
    ] = 5_000_000.0
    adv.loc[
        pd.to_datetime(adv["date"]).eq(first_date) & adv["asset_id"].eq("A09"),
        "adv20",
    ] = 6_000_000.0
    return factors, labels, adv


def _rank_frames(dates: pd.DatetimeIndex, *, factor_name: str) -> pd.DataFrame:
    rows = []
    for signal_date in dates:
        for index in range(10):
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"A{index:02d}",
                    "market": "CN_ETF",
                    "factor_name": factor_name,
                    "factor_value": float(index),
                    "lookback_window": 5,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
