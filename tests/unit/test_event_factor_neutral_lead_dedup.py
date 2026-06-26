import unittest

import pandas as pd

from quant_robot.ops.event_factor_neutral_lead_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_PORTFOLIO_PREFLIGHT_DIRECTION,
    ROTATE_AFTER_DEDUP_FAILURE_DIRECTION,
    summarize_event_factor_neutral_lead_dedup,
)


def _lead_rows(
    dates: list[pd.Timestamp],
    *,
    implementation_locked: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lead_rows = []
    labels = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(48):
            common = {
                "date": signal_date,
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "market": "CN",
            }
            signal_value = float(asset_idx)
            implementation_value = float(asset_idx if implementation_locked else (asset_idx * 17) % 48)
            lead_value = implementation_value if implementation_locked else signal_value + implementation_value * 0.02
            forward_return = (implementation_value if implementation_locked else signal_value) / 1000.0
            lead_rows.append(
                common
                | {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "factor_value": lead_value,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            labels.append(common | {"horizon": 20, "forward_return": forward_return})
            reference_rows.append(
                common
                | {
                    "factor_name": "daily_basic_dv_ttm",
                    "factor_value": implementation_value,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "daily_basic_independent_value_proxy",
                    "factor_value": float((asset_idx * 11) % 48),
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            exposure_rows.append(
                common
                | {
                    "daily_basic_dv_ttm": implementation_value,
                    "daily_basic_inv_pb": implementation_value * 0.7,
                    "daily_basic_inv_ps_ttm": implementation_value * 0.5,
                    "daily_basic_log_circ_mv": implementation_value,
                    "daily_basic_log_total_mv": implementation_value * 0.9,
                    "log_adv20_amount": implementation_value * 0.4,
                }
            )
    return pd.DataFrame(lead_rows), pd.DataFrame(labels), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class EventFactorNeutralLeadDedupTests(unittest.TestCase):
    def test_blocks_portfolio_conversion_when_dividend_event_lead_is_public_yield_exposure(self) -> None:
        dates = list(pd.bdate_range("2018-01-02", periods=8))
        lead_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=True)
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_event_factor_neutral_lead_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
        )

        self.assertEqual(result["stage"], "event_factor_neutral_lead_dedup")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_conversion_candidate"])
        self.assertEqual(result["next_direction"], ROTATE_AFTER_DEDUP_FAILURE_DIRECTION)
        self.assertIn("lead_highly_redundant_with_public_reference_factor", result["gate"]["blockers"])
        self.assertIn("lead_high_public_yield_or_value_exposure", result["gate"]["blockers"])
        self.assertIn("residual_ic_observations_below_threshold", result["gate"]["blockers"])
        self.assertGreater(result["raw_ic_summary"]["mean_spearman_ic"], 0.90)
        self.assertEqual(
            next(row for row in result["exposure_correlations"] if row["exposure_name"] == "daily_basic_dv_ttm")[
                "exposure_class"
            ],
            "high_exposure",
        )

    def test_allows_portfolio_preflight_when_event_residual_ic_survives_public_exposure_dedup(self) -> None:
        dates = list(pd.bdate_range("2022-01-04", periods=10))
        lead_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=False)
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_event_factor_neutral_lead_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame[reference_frame["factor_name"] == "daily_basic_independent_value_proxy"],
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_mean_ic=0.02,
            min_residual_icir=0.0,
            min_residual_positive_ic_rate=0.55,
        )

        self.assertEqual(result["next_direction"], NEXT_PORTFOLIO_PREFLIGHT_DIRECTION)
        self.assertTrue(result["promotion_policy"]["portfolio_conversion_candidate"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertGreater(result["residual_ic_summary"]["mean_spearman_ic"], 0.02)
        self.assertGreaterEqual(result["residual_ic_summary"]["positive_ic_rate"], 0.55)
        self.assertNotIn("lead_high_public_yield_or_value_exposure", result["gate"]["blockers"])


if __name__ == "__main__":
    unittest.main()
