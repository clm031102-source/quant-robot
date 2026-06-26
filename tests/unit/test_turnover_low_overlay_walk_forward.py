import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.turnover_low_overlay_walk_forward import (
    DEFAULT_POLICIES,
    OverlayPolicy,
    apply_overlay_policy,
    apply_overlay_policy_to_period_events,
    align_market_caps_to_periods,
    calendar_walk_forward_overlay,
    prepare_period_return_events,
    market_state_cap_from_returns,
    prepare_period_returns,
    run_overlay_walk_forward_from_period_returns,
)


class TurnoverLowOverlayWalkForwardTests(unittest.TestCase):
    def test_drawdown_overlay_cuts_exposure_after_loss(self) -> None:
        returns = pd.Series(
            [-0.12, -0.12, 0.04, 0.04],
            index=pd.date_range("2020-01-01", periods=4, freq="ME"),
        )
        policy = OverlayPolicy(
            name="dd",
            kind="drawdown",
            warn_drawdown=-0.10,
            cut_drawdown=-0.20,
            warn_exposure=0.5,
            cut_exposure=0.25,
        )

        result = apply_overlay_policy(returns, policy, periods_per_year=12)

        self.assertLess(float(result["exposure"].min()), 1.0)
        self.assertEqual(float(result["exposure"].iloc[1]), 0.5)

    def test_calendar_walk_forward_selects_policy_and_summarizes(self) -> None:
        returns = pd.Series(
            [0.01, -0.005, 0.012, 0.004] * 60,
            index=pd.date_range("2015-01-31", periods=240, freq="ME"),
        )

        result = calendar_walk_forward_overlay(
            returns,
            periods_per_year=12.0,
            holding_period=3,
            train_years=3,
            test_years=1,
            step_years=1,
            policies=DEFAULT_POLICIES[:3],
        )

        self.assertGreater(result["summary"]["folds"], 0)
        self.assertIn("best_fixed_policy", result["summary"])
        self.assertGreater(len(result["selected_by_train"]), 0)
        self.assertGreater(len(result["policy_summary"]), 0)

    def test_cli_helper_reads_period_return_frame_and_writes_outputs(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.date_range("2015-01-31", periods=120, freq="ME"),
                "entry_cash_proxy_return": [0.01, -0.004, 0.008, 0.002] * 30,
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_overlay_walk_forward_from_period_returns(
                frame,
                output_dir=Path(tmp),
                periods_per_year=12.0,
                holding_period=3,
                train_years=3,
                test_years=1,
                step_years=1,
                policies=DEFAULT_POLICIES[:2],
            )

            self.assertGreater(result["summary"]["folds"], 0)
            self.assertTrue((Path(tmp) / "turnover_low_overlay_walk_forward.json").exists())
            self.assertTrue((Path(tmp) / "turnover_low_overlay_walk_forward_policy_summary.csv").exists())

    def test_prepare_period_returns_rejects_missing_column(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing return column"):
            prepare_period_returns(pd.DataFrame({"date": ["2020-01-01"], "x": [0.0]}), return_column="missing")

    def test_market_state_policy_requires_external_cap_series(self) -> None:
        returns = pd.Series([0.02, -0.01], index=pd.date_range("2020-01-31", periods=2, freq="ME"))
        policy = OverlayPolicy(name="market_cap", kind="market_state_cap")

        with self.assertRaisesRegex(ValueError, "market_exposure_cap"):
            apply_overlay_policy(returns, policy, periods_per_year=12.0)

    def test_market_state_cap_reduces_exposure_on_capped_periods(self) -> None:
        returns = pd.Series([0.10, -0.10], index=pd.date_range("2020-01-31", periods=2, freq="ME"))
        caps = pd.Series([0.25, 1.0], index=returns.index)
        policy = OverlayPolicy(name="market_cap", kind="market_state_cap")

        result = apply_overlay_policy(returns, policy, periods_per_year=12.0, market_exposure_cap=caps)

        self.assertEqual(float(result["exposure"].iloc[0]), 0.25)
        self.assertAlmostEqual(float(result["period_return"].iloc[0]), 0.025)
        self.assertEqual(float(result["exposure"].iloc[1]), 1.0)

    def test_market_caps_align_to_decision_date_not_exit_date(self) -> None:
        frame = pd.DataFrame(
            {
                "date": ["2020-01-10", "2020-01-20"],
                "entry_date": ["2020-01-02", "2020-01-12"],
                "entry_cash_proxy_return": [0.10, 0.02],
            }
        )
        caps = pd.Series(
            [0.25, 1.0],
            index=pd.to_datetime(["2020-01-02", "2020-01-10"]),
        )

        aligned = align_market_caps_to_periods(frame, caps, decision_date_column="entry_date")

        self.assertEqual(float(aligned.iloc[0]), 0.25)
        self.assertEqual(float(aligned.iloc[1]), 1.0)

    def test_market_state_cap_from_returns_lags_state_change(self) -> None:
        market_returns = pd.Series(
            [0.02, -0.05, 0.01],
            index=pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]),
        )

        caps = market_state_cap_from_returns(
            market_returns,
            lookback_periods=1,
            momentum_threshold=0.0,
            drawdown_threshold=-0.02,
            cap_exposure=0.25,
            lag_periods=1,
        )

        self.assertEqual(float(caps.loc[pd.Timestamp("2020-01-03")]), 1.0)
        self.assertEqual(float(caps.loc[pd.Timestamp("2020-01-06")]), 0.25)

    def test_period_event_drawdown_overlay_uses_only_returns_closed_before_decision_date(self) -> None:
        frame = pd.DataFrame(
            {
                "date": ["2020-01-20", "2020-01-30", "2020-02-10"],
                "entry_date": ["2020-01-01", "2020-01-10", "2020-01-25"],
                "entry_cash_proxy_return": [-0.30, 0.10, 0.10],
            }
        )
        events = prepare_period_return_events(
            frame,
            return_column="entry_cash_proxy_return",
            decision_date_column="entry_date",
        )
        policy = OverlayPolicy(
            name="dd",
            kind="drawdown",
            warn_drawdown=-0.10,
            cut_drawdown=-0.20,
            warn_exposure=0.5,
            cut_exposure=0.25,
        )

        result = apply_overlay_policy_to_period_events(events, policy, periods_per_year=12.0)

        by_decision_date = result.set_index("decision_date")["exposure"]
        self.assertEqual(float(by_decision_date.loc[pd.Timestamp("2020-01-01")]), 1.0)
        self.assertEqual(float(by_decision_date.loc[pd.Timestamp("2020-01-10")]), 1.0)
        self.assertEqual(float(by_decision_date.loc[pd.Timestamp("2020-01-25")]), 0.25)


if __name__ == "__main__":
    unittest.main()
