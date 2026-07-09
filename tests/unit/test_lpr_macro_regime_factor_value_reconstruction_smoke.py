import unittest

import pandas as pd

from quant_robot.ops.lpr_macro_regime_factor_value_reconstruction_smoke import (
    summarize_lpr_macro_regime_factor_value_reconstruction_smoke,
)


def _round733_preflight() -> dict[str, object]:
    return {
        "stage": "lpr_macro_regime_reference_dedup_preflight",
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
                "horizon": 5,
                "state": "gap_widening",
                "cluster_representative": True,
                "factor_value_reference_dedup_allowed": True,
            },
            {
                "source_id": "source_a",
                "factor_name": "factor_b_industry_size_liquidity_vol_residual",
                "base_factor_name": "factor_b",
                "horizon": 5,
                "state": "gap_widening",
                "cluster_representative": False,
                "factor_value_reference_dedup_allowed": False,
            },
        ],
        "live_boundary_allowed": False,
    }


class LPRMacroRegimeFactorValueReconstructionSmokeTests(unittest.TestCase):
    def test_marks_representative_factor_values_ready_inside_lpr_state(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=5)
        factor_rows = []
        for signal_date in dates:
            for asset_idx in range(4):
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": f"{asset_idx:06d}.SZ",
                        "market": "CN",
                        "factor_name": "factor_a_industry_size_liquidity_vol_residual",
                        "factor_value": asset_idx * 0.1,
                    }
                )
        state_frame = pd.DataFrame({"available_date": dates, "lpr_shibor_gap_state": ["gap_widening"] * len(dates)})

        result = summarize_lpr_macro_regime_factor_value_reconstruction_smoke(
            _round733_preflight(),
            pd.DataFrame(factor_rows),
            state_frame,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=4,
            min_median_cross_section=3,
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_factor_value_reconstruction_smoke")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["representative_candidate_count"], 1)
        self.assertEqual(result["summary"]["factor_value_ready_candidate_count"], 1)
        candidate = result["candidate_results"][0]
        self.assertTrue(candidate["factor_value_reference_dedup_input_ready"])
        self.assertEqual(candidate["state_dates"], 5)
        self.assertEqual(candidate["median_cross_section"], 4.0)
        self.assertFalse(result["decision"]["walk_forward_preflight_allowed"])

    def test_blocks_when_state_factor_value_coverage_is_too_small(self) -> None:
        factor_frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02"]),
                "asset_id": ["000001.SZ"],
                "market": ["CN"],
                "factor_name": ["factor_a_industry_size_liquidity_vol_residual"],
                "factor_value": [0.1],
            }
        )
        state_frame = pd.DataFrame(
            {"available_date": pd.to_datetime(["2024-01-02"]), "lpr_shibor_gap_state": ["gap_widening"]}
        )

        result = summarize_lpr_macro_regime_factor_value_reconstruction_smoke(
            _round733_preflight(),
            factor_frame,
            state_frame,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=4,
            min_median_cross_section=3,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("no_factor_value_ready_lpr_representatives", result["decision"]["blockers"])
        self.assertIn("state_factor_dates_below_threshold", result["candidate_results"][0]["blockers"])


if __name__ == "__main__":
    unittest.main()
