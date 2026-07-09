import unittest

import pandas as pd

from quant_robot.ops.lpr_macro_regime_pairwise_residual_ic_prescreen import (
    align_residual_ic_to_lpr_states,
    summarize_lpr_macro_regime_pairwise_residual_ic_prescreen,
)


def _state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "available_date": pd.to_datetime(["2024-01-02", "2024-01-05", "2024-01-09"]),
            "lpr_shibor_gap_state": ["insufficient_lookback", "gap_widening", "gap_narrowing"],
        }
    )


def _state_prescreen() -> dict[str, object]:
    return {
        "stage": "lpr_macro_regime_state_prescreen",
        "summary": {"passes": True},
        "decision": {
            "state_ready_for_regime_control": True,
            "residual_ic_pairing_allowed_next": True,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "live_boundary_allowed": False,
    }


class LPRMacroRegimePairwiseResidualICPrescreenTests(unittest.TestCase):
    def test_align_uses_latest_available_lpr_state_without_future_dates(self) -> None:
        observations = pd.DataFrame(
            {
                "factor_name": ["residual_a"] * 3,
                "horizon": [5, 5, 5],
                "date": pd.to_datetime(["2024-01-03", "2024-01-08", "2024-01-10"]),
                "spearman_ic": [0.01, 0.02, 0.03],
                "cross_section": [40, 41, 42],
            }
        )

        aligned = align_residual_ic_to_lpr_states(observations, _state_frame())

        self.assertEqual(aligned["lpr_shibor_gap_state"].tolist(), ["insufficient_lookback", "gap_widening", "gap_narrowing"])
        self.assertTrue((aligned["lpr_available_date"] <= aligned["date"]).all())

    def test_summarizes_directional_state_leads_without_promotion(self) -> None:
        rows = []
        dates = pd.bdate_range("2024-01-05", periods=36)
        for idx, signal_date in enumerate(dates):
            state = "gap_widening" if idx < 24 else "gap_narrowing"
            rows.append({"available_date": signal_date, "lpr_shibor_gap_state": state})
            for factor_name, base_ic in [("residual_a", 0.04), ("residual_b", -0.01)]:
                rows[-1].setdefault("_dummy", None)
        states = pd.DataFrame(rows).drop(columns=["_dummy"])

        observations = []
        for idx, signal_date in enumerate(dates):
            residual_a_ic = 0.04 if idx < 24 else 0.005
            for factor_name, base_ic in [("residual_a", residual_a_ic), ("residual_b", -0.01)]:
                observations.append(
                    {
                        "factor_name": factor_name,
                        "horizon": 5,
                        "date": signal_date,
                        "spearman_ic": base_ic + (0.001 if idx % 2 else -0.001),
                        "cross_section": 80,
                        "source_id": "synthetic_residual",
                    }
                )

        result = summarize_lpr_macro_regime_pairwise_residual_ic_prescreen(
            pd.DataFrame(observations),
            states,
            state_prescreen=_state_prescreen(),
            residual_ic_paths=["synthetic.csv"],
            min_state_ic_observations=10,
            min_mean_ic=0.02,
            min_icir=0.20,
            min_positive_ic_rate=0.55,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-03-31",
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_pairwise_residual_ic_prescreen")
        self.assertEqual(result["summary"]["state_research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        lead = next(row for row in result["state_ic_results"] if row["state_research_lead"])
        self.assertEqual(lead["factor_name"], "residual_a")
        self.assertEqual(lead["state"], "gap_widening")
        self.assertTrue(lead["fdr_significant"])

    def test_blocks_when_state_prescreen_is_not_ready(self) -> None:
        bad_state_prescreen = _state_prescreen()
        bad_state_prescreen["decision"] = {
            "state_ready_for_regime_control": False,
            "residual_ic_pairing_allowed_next": False,
        }
        observations = pd.DataFrame(
            {
                "factor_name": ["residual_a"],
                "horizon": [5],
                "date": pd.to_datetime(["2024-01-05"]),
                "spearman_ic": [0.05],
                "cross_section": [80],
                "source_id": ["synthetic"],
            }
        )

        result = summarize_lpr_macro_regime_pairwise_residual_ic_prescreen(
            observations,
            _state_frame(),
            state_prescreen=bad_state_prescreen,
            residual_ic_paths=["synthetic.csv"],
            min_state_ic_observations=1,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("lpr_state_prescreen_not_ready_for_pairing", result["decision"]["blockers"])

    def test_state_join_misses_are_audited_without_blocking_paired_leads(self) -> None:
        states = pd.DataFrame(
            {
                "available_date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
                "lpr_shibor_gap_state": ["gap_widening"] * 4,
            }
        )
        observations = pd.DataFrame(
            {
                "factor_name": ["residual_a"] * 5,
                "horizon": [5] * 5,
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
                "spearman_ic": [0.02, 0.04, 0.041, 0.039, 0.04],
                "cross_section": [80] * 5,
                "source_id": ["synthetic"] * 5,
            }
        )

        result = summarize_lpr_macro_regime_pairwise_residual_ic_prescreen(
            observations,
            states,
            state_prescreen=_state_prescreen(),
            residual_ic_paths=["synthetic.csv"],
            min_state_ic_observations=4,
            min_mean_ic=0.02,
            min_icir=0.20,
            min_positive_ic_rate=0.55,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
        )

        self.assertEqual(result["pairing_audit"]["state_join_miss_count"], 1)
        self.assertEqual(result["summary"]["analysis_window_ic_rows"], 5)
        self.assertEqual(result["summary"]["paired_ic_rows"], 4)
        self.assertTrue(result["summary"]["passes"])
        self.assertNotIn("residual_ic_state_join_missing", result["decision"]["blockers"])


if __name__ == "__main__":
    unittest.main()
