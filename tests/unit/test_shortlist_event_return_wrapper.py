from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_event_return_wrapper import (
    build_event_return_wrapper_audit,
    write_event_return_wrapper_audit,
)


class ShortlistEventReturnWrapperTest(unittest.TestCase):
    def test_wrapper_applies_reference_riskoff_after_vol_target(self) -> None:
        returns = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=35, freq="D"),
                "entry_date": pd.date_range("2019-12-31", periods=35, freq="D"),
                "period_return": [0.01] * 34 + [0.02],
            }
        )
        reference = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=35, freq="D"),
                "zz500_mom120_before_decision": [-0.1] * 35,
                "zz500_riskoff": [False] * 34 + [True],
            }
        )

        audit = build_event_return_wrapper_audit(
            return_sources={"candidate": returns},
            reference_schema_source=reference,
            riskoff_multipliers=(0.5,),
            periods_per_year=52.0,
            holding_period=4,
            target_annual_vol=0.06,
            lookback_events=30,
        )

        event = audit["events"][audit["rows"][0]["candidate_name"]]
        self.assertAlmostEqual(float(event.iloc[-1]["regime_guard_exposure"]), 0.5)
        self.assertAlmostEqual(
            float(event.iloc[-1]["period_return"]),
            float(event.iloc[-1]["vol_target_period_return"]) * 0.5,
        )

    def test_writer_exports_summary_and_events(self) -> None:
        with TemporaryDirectory() as tmp:
            returns = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "period_return": [0.01, 0.0, 0.02]})
            audit = build_event_return_wrapper_audit(
                return_sources={"candidate": returns},
                periods_per_year=52.0,
                holding_period=4,
            )

            write_event_return_wrapper_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "event_return_wrapper_audit.json").exists())
            self.assertTrue((Path(tmp) / "event_return_wrapper_summary.csv").exists())
            event_files = list(Path(tmp).glob("*_events.csv"))
            self.assertEqual(len(event_files), 1)

    def test_can_reuse_reference_vol_target_exposure(self) -> None:
        returns = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=2),
                "period_return": [0.10, 0.20],
            }
        )
        reference = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=2),
                "vol_target_exposure": [0.5, 0.25],
                "zz500_riskoff": [False, False],
            }
        )

        audit = build_event_return_wrapper_audit(
            return_sources={"candidate": returns},
            reference_schema_source=reference,
            reuse_reference_vol_target_exposure=True,
            periods_per_year=52.0,
            holding_period=4,
        )

        event = audit["events"][audit["rows"][0]["candidate_name"]]
        self.assertEqual(event["vol_target_exposure"].tolist(), [0.5, 0.25])
        self.assertEqual(event["period_return"].round(6).tolist(), [0.05, 0.05])


if __name__ == "__main__":
    unittest.main()
