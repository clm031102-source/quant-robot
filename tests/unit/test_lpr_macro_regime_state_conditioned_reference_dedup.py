import unittest

import pandas as pd

from quant_robot.ops.lpr_macro_regime_state_conditioned_reference_dedup import (
    summarize_lpr_macro_regime_state_conditioned_reference_dedup,
)


def _round734_smoke() -> dict[str, object]:
    return {
        "stage": "lpr_macro_regime_factor_value_reconstruction_smoke",
        "summary": {"passes": True},
        "decision": {
            "factor_value_reference_dedup_allowed_next": True,
            "walk_forward_preflight_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "candidate_results": [
            {
                "source_id": "source_a",
                "factor_name": "factor_a_industry_size_liquidity_vol_residual",
                "base_factor_name": "factor_a",
                "horizon": 20,
                "state": "gap_widening",
                "factor_value_reference_dedup_input_ready": True,
            },
            {
                "source_id": "source_b",
                "factor_name": "factor_b_industry_size_liquidity_vol_residual",
                "base_factor_name": "factor_b",
                "horizon": 20,
                "state": "gap_widening",
                "factor_value_reference_dedup_input_ready": True,
            },
        ],
        "live_boundary_allowed": False,
    }


class LPRMacroRegimeStateConditionedReferenceDedupTests(unittest.TestCase):
    def test_blocks_high_reference_redundancy_but_keeps_unique_candidate_for_next_preflight(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=4)
        factor_rows = []
        reference_rows = []
        exposure_rows = []
        for signal_date in dates:
            for asset_idx in range(4):
                asset_id = f"{asset_idx:06d}.SZ"
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "factor_a_industry_size_liquidity_vol_residual",
                        "factor_value": float(asset_idx),
                    }
                )
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "factor_b_industry_size_liquidity_vol_residual",
                        "factor_value": 1.0 if asset_idx in {0, 2} else -1.0,
                    }
                )
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "public_reference_same_as_a",
                        "factor_value": float(asset_idx),
                    }
                )
                exposure_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "log_adv20_amount": float(asset_idx),
                        "log_amount": float(asset_idx + 10),
                        "realized_vol_20": float(asset_idx + 20),
                        "amount_trend_20_60": float(asset_idx + 30),
                        "return_20": float(asset_idx + 40),
                    }
                )
        state_frame = pd.DataFrame({"available_date": dates, "lpr_shibor_gap_state": ["gap_widening"] * len(dates)})

        result = summarize_lpr_macro_regime_state_conditioned_reference_dedup(
            _round734_smoke(),
            pd.DataFrame(factor_rows),
            pd.DataFrame(reference_rows),
            pd.DataFrame(exposure_rows),
            state_frame,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=4,
            min_median_cross_section=4,
            min_cross_section=4,
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_state_conditioned_reference_dedup")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["state_conditioned_reference_dedup_pass_count"], 1)
        self.assertEqual(result["summary"]["state_conditioned_reference_dedup_blocked_count"], 1)
        by_name = {row["factor_name"]: row for row in result["candidate_results"]}
        self.assertFalse(by_name["factor_a_industry_size_liquidity_vol_residual"]["state_conditioned_reference_dedup_pass"])
        self.assertIn(
            "state_conditioned_high_reference_redundancy",
            by_name["factor_a_industry_size_liquidity_vol_residual"]["blockers"],
        )
        self.assertTrue(by_name["factor_b_industry_size_liquidity_vol_residual"]["state_conditioned_reference_dedup_pass"])
        self.assertTrue(
            by_name["factor_b_industry_size_liquidity_vol_residual"]["walk_forward_preflight_allowed_next"]
        )
        self.assertFalse(result["decision"]["walk_forward_preflight_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertGreater(len(result["reference_correlations"]), 0)
        self.assertGreater(len(result["exposure_correlations"]), 0)

    def test_blocks_when_factor_value_smoke_is_not_ready(self) -> None:
        smoke = _round734_smoke()
        smoke["decision"] = {"factor_value_reference_dedup_allowed_next": False}
        state_frame = pd.DataFrame(
            {"available_date": pd.to_datetime(["2024-01-02"]), "lpr_shibor_gap_state": ["gap_widening"]}
        )

        result = summarize_lpr_macro_regime_state_conditioned_reference_dedup(
            smoke,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            state_frame,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=1,
            min_median_cross_section=1,
            min_cross_section=1,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("factor_value_reconstruction_smoke_not_allowed_for_reference_dedup", result["decision"]["blockers"])
        self.assertFalse(result["decision"]["walk_forward_preflight_allowed_next"])


if __name__ == "__main__":
    unittest.main()
