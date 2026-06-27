from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd

from quant_robot.ops.shortlist_self_risk_overlay import (
    build_shortlist_self_risk_overlay,
    write_shortlist_self_risk_overlay,
)


class ShortlistSelfRiskOverlayTest(unittest.TestCase):
    def test_baseline_preserves_source_returns(self) -> None:
        dates = pd.date_range("2020-01-03", periods=60, freq="W-FRI")
        returns = pd.DataFrame({"date": dates, "period_return": [0.01] * len(dates)})

        audit = build_shortlist_self_risk_overlay(
            {"base": returns},
            policy_names=("baseline",),
            periods_per_year=52.0,
            holding_period=4,
        )

        event_frame = audit["events"]["base"]
        self.assertEqual(audit["summary"]["candidate_count"], 1)
        self.assertTrue((event_frame["self_risk_exposure"] == 1.0).all())
        self.assertAlmostEqual(event_frame["period_return"].sum(), returns["period_return"].sum())

    def test_roll42_policy_uses_prior_returns_only(self) -> None:
        dates = pd.date_range("2020-01-03", periods=50, freq="W-FRI")
        period_returns = [-0.0005] * 42 + [-0.02] + [0.01] * 7
        returns = pd.DataFrame({"date": dates, "period_return": period_returns})

        audit = build_shortlist_self_risk_overlay(
            {"base": returns},
            policy_names=("roll42_sum_m3_half",),
            periods_per_year=52.0,
            holding_period=4,
        )
        event_frame = audit["events"]["base_self_roll42_sum_m3_half"]

        self.assertEqual(event_frame.loc[42, "self_risk_exposure"], 1.0)
        self.assertEqual(event_frame.loc[43, "self_risk_exposure"], 0.5)
        self.assertAlmostEqual(event_frame.loc[43, "period_return"], 0.005)

    def test_overlay_preserves_event_schema_and_combines_final_exposure(self) -> None:
        dates = pd.date_range("2020-01-03", periods=25, freq="W-FRI")
        returns = pd.DataFrame(
            {
                "date": dates,
                "decision_date": dates - pd.Timedelta(days=1),
                "period_return": [-0.001] * 24 + [0.02],
                "final_exposure": [0.8] * 25,
                "regime_guard_exposure": [0.9] * 25,
                "riskoff_multiplier": [0.5] * 25,
            }
        )

        audit = build_shortlist_self_risk_overlay(
            {"base": returns},
            policy_names=("roll21_sum_neg_half",),
            periods_per_year=52.0,
            holding_period=4,
        )
        event_frame = audit["events"]["base_self_roll21_sum_neg_half"]

        self.assertIn("decision_date", event_frame.columns)
        self.assertIn("regime_guard_exposure", event_frame.columns)
        self.assertIn("riskoff_multiplier", event_frame.columns)
        self.assertIn("source_final_exposure", event_frame.columns)
        self.assertEqual(event_frame.loc[1, "self_risk_exposure"], 0.5)
        self.assertAlmostEqual(event_frame.loc[1, "source_final_exposure"], 0.8)
        self.assertAlmostEqual(event_frame.loc[1, "final_exposure"], 0.4)

    def test_write_outputs_event_paths_and_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            dates = pd.date_range("2020-01-03", periods=60, freq="W-FRI")
            returns = pd.DataFrame({"date": dates, "period_return": [0.004] * len(dates)})
            audit = build_shortlist_self_risk_overlay(
                {"base": returns},
                policy_names=("baseline",),
                periods_per_year=52.0,
                holding_period=4,
            )

            write_shortlist_self_risk_overlay(tmp, audit)

            self.assertTrue((Path(tmp) / "base_events.csv").exists())
            self.assertTrue((Path(tmp) / "shortlist_self_risk_overlay_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
