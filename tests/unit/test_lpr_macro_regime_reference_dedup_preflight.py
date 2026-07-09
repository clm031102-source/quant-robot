import unittest

import pandas as pd

from quant_robot.ops.lpr_macro_regime_reference_dedup_preflight import (
    summarize_lpr_macro_regime_reference_dedup_preflight,
)


def _pairwise_report() -> dict[str, object]:
    return {
        "stage": "lpr_macro_regime_pairwise_residual_ic_prescreen",
        "summary": {"passes": True},
        "decision": {
            "reference_dedup_walk_forward_preflight_allowed_next": True,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "data_window": {
            "analysis_start_date": "2024-01-01",
            "analysis_end_date": "2024-01-31",
        },
        "live_boundary_allowed": False,
        "state_ic_results": [
            {
                "source_id": "source_a",
                "factor_name": "factor_a_industry_size_liquidity_vol_residual",
                "horizon": 5,
                "state": "gap_widening",
                "state_research_lead": True,
                "mean_spearman_ic": 0.04,
                "icir": 0.50,
                "positive_ic_rate": 0.70,
                "ic_observations": 6,
            },
            {
                "source_id": "source_a",
                "factor_name": "factor_b_industry_size_liquidity_vol_residual",
                "horizon": 5,
                "state": "gap_widening",
                "state_research_lead": True,
                "mean_spearman_ic": 0.035,
                "icir": 0.45,
                "positive_ic_rate": 0.67,
                "ic_observations": 6,
            },
            {
                "source_id": "source_b",
                "factor_name": "factor_c_industry_size_liquidity_vol_residual",
                "horizon": 5,
                "state": "gap_widening",
                "state_research_lead": True,
                "mean_spearman_ic": 0.025,
                "icir": 0.30,
                "positive_ic_rate": 0.60,
                "ic_observations": 6,
            },
        ],
    }


class LPRMacroRegimeReferenceDedupPreflightTests(unittest.TestCase):
    def test_clusters_highly_similar_leads_and_keeps_representatives_for_reference_dedup(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=6)
        state_frame = pd.DataFrame({"available_date": dates, "lpr_shibor_gap_state": ["gap_widening"] * len(dates)})
        residual_rows = []
        for idx, signal_date in enumerate(dates):
            a_value = 0.02 + idx * 0.002
            for source_id, factor_name, ic_value in [
                ("source_a", "factor_a_industry_size_liquidity_vol_residual", a_value),
                ("source_a", "factor_b_industry_size_liquidity_vol_residual", a_value * 1.1),
                ("source_b", "factor_c_industry_size_liquidity_vol_residual", 0.03 if idx % 2 else -0.01),
            ]:
                residual_rows.append(
                    {
                        "source_id": source_id,
                        "factor_name": factor_name,
                        "horizon": 5,
                        "date": signal_date,
                        "spearman_ic": ic_value,
                        "cross_section": 80,
                    }
                )
        exposure = pd.DataFrame(
            {
                "lead_factor_name": ["factor_a"],
                "exposure_name": ["realized_vol_20"],
                "exposure_class": ["high_exposure"],
                "mean_abs_correlation": [0.8],
                "blockers": ["high_size_liquidity_or_volatility_exposure_correlation"],
            }
        )
        reference = pd.DataFrame(
            {
                "lead_factor_name": ["factor_c"],
                "factor_name": ["bollinger_reversal_20"],
                "redundancy_class": ["moderately_redundant"],
                "mean_abs_correlation": [0.42],
                "blockers": ["moderate_reference_correlation_with_lead"],
            }
        )

        result = summarize_lpr_macro_regime_reference_dedup_preflight(
            _pairwise_report(),
            pd.DataFrame(residual_rows),
            state_frame,
            reference_correlations=reference,
            exposure_correlations=exposure,
            residual_ic_paths=["source_a.csv", "source_b.csv"],
            cluster_abs_ic_corr=0.90,
            duplicate_abs_ic_corr=0.98,
            min_pair_overlap=4,
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_reference_dedup_preflight")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["state_lead_count"], 3)
        self.assertEqual(result["summary"]["candidate_cluster_count"], 2)
        self.assertEqual(result["summary"]["representative_candidate_count"], 2)
        self.assertEqual(result["summary"]["cluster_blocked_candidate_count"], 1)
        self.assertEqual(result["summary"]["factor_value_reference_dedup_allowed_candidate_count"], 2)
        self.assertEqual(result["summary"]["walk_forward_preflight_allowed_candidate_count"], 0)
        by_factor = {row["factor_name"]: row for row in result["candidate_results"]}
        self.assertTrue(by_factor["factor_a_industry_size_liquidity_vol_residual"]["cluster_representative"])
        self.assertFalse(by_factor["factor_b_industry_size_liquidity_vol_residual"]["cluster_representative"])
        self.assertIn(
            "cluster_duplicate_or_high_similarity_with_stronger_lpr_lead",
            by_factor["factor_b_industry_size_liquidity_vol_residual"]["blockers"],
        )
        self.assertIn(
            "source_exposure_requires_factor_value_reaudit",
            by_factor["factor_a_industry_size_liquidity_vol_residual"]["requirements"],
        )
        self.assertIn(
            "source_reference_redundancy_requires_factor_value_dedup",
            by_factor["factor_c_industry_size_liquidity_vol_residual"]["requirements"],
        )
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])

    def test_blocks_when_pairwise_prescreen_is_not_ready(self) -> None:
        bad_report = _pairwise_report()
        bad_report["summary"] = {"passes": False}
        bad_report["decision"] = {
            "reference_dedup_walk_forward_preflight_allowed_next": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        }

        result = summarize_lpr_macro_regime_reference_dedup_preflight(
            bad_report,
            pd.DataFrame(),
            pd.DataFrame(),
            residual_ic_paths=[],
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("pairwise_prescreen_not_passing", result["decision"]["blockers"])


if __name__ == "__main__":
    unittest.main()
