import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.analyst_report_source_extension_priority_gate import (
    build_analyst_report_source_extension_priority_gate,
    write_analyst_report_source_extension_priority_gate,
)


class AnalystReportSourceExtensionPriorityGateTests(unittest.TestCase):
    def test_prioritizes_target_upside_row_but_blocks_until_quota_and_year_coverage(self) -> None:
        result = build_analyst_report_source_extension_priority_gate(
            source_gate=_source_gate(),
            analyst_prescreen=_analyst_prescreen(),
        )

        self.assertEqual(result["stage"], "analyst_report_source_extension_priority_gate")
        self.assertEqual(result["status"], "blocked_waiting_for_quota")
        self.assertEqual(result["decision"]["priority_source"], "analyst_report_revision")
        self.assertEqual(result["decision"]["priority_factor_name"], "analyst_target_upside_60")
        self.assertEqual(result["decision"]["priority_horizon"], 5)
        self.assertFalse(result["decision"]["provider_cache_allowed_now"])
        self.assertTrue(result["decision"]["cache_next_month_after_quota_reset"])
        self.assertTrue(result["decision"]["frozen_prescreen_required"])
        self.assertFalse(result["decision"]["formula_tuning_allowed"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertIn("provider_quota_preflight_blocked", result["decision"]["blockers"])
        self.assertIn("priority_row_year_coverage_below_gate", result["decision"]["blockers"])
        self.assertEqual(result["priority_table"][0]["factor_name"], "analyst_target_upside_60")
        self.assertGreater(result["priority_table"][0]["priority_score"], result["priority_table"][1]["priority_score"])

    def test_blocks_when_non_lpr_source_gate_did_not_select_analyst_source(self) -> None:
        source_gate = _source_gate()
        source_gate["decision"]["source_gate_selected"] = False
        source_gate["decision"]["selected_source"] = ""

        result = build_analyst_report_source_extension_priority_gate(
            source_gate=source_gate,
            analyst_prescreen=_analyst_prescreen(),
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("analyst_source_not_selected", result["decision"]["blockers"])
        self.assertEqual(result["priority_table"], [])
        self.assertFalse(result["decision"]["cache_next_month_after_quota_reset"])

    def test_write_outputs(self) -> None:
        result = build_analyst_report_source_extension_priority_gate(
            source_gate=_source_gate(),
            analyst_prescreen=_analyst_prescreen(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_analyst_report_source_extension_priority_gate(output, result)

            self.assertTrue((output / "analyst_report_source_extension_priority_gate.json").exists())
            self.assertTrue((output / "analyst_report_source_extension_priority_gate.md").exists())
            self.assertTrue((output / "analyst_report_source_extension_priority_rows.csv").exists())


def _source_gate() -> dict:
    return {
        "stage": "cn_stock_non_lpr_orthogonal_source_gate",
        "status": "blocked",
        "decision": {
            "selected_source": "analyst_report_revision",
            "source_gate_selected": True,
            "source_gate_ready": False,
            "provider_request_allowed": False,
            "local_cached_prescreen_allowed": True,
            "full_factor_batch_allowed": False,
            "blockers": [
                "provider_quota_preflight_blocked",
                "analyst_year_coverage_below_gate",
                "analyst_research_lead_count_zero",
            ],
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "live_boundary_allowed": False,
    }


def _analyst_prescreen() -> dict:
    return {
        "stage": "analyst_report_revision_pit_prescreen",
        "summary": {
            "candidate_count": 4,
            "multiple_testing_lead_count": 4,
            "neutral_gate_pass_count": 2,
            "year_coverage_pass_count": 0,
            "research_lead_count": 0,
            "promotion_allowed_candidates": 0,
        },
        "data_window": {
            "max_report_date": "2024-06-30",
            "report_rows": 10509,
            "report_assets": 2226,
        },
        "results": [
            {
                "factor_name": "analyst_revision_target_composite_90",
                "horizon": 20,
                "mean_spearman_ic": 0.0510,
                "ic_t_stat": 2.51,
                "icir": 0.379,
                "fdr_significant": True,
                "bonferroni_significant": False,
                "mean_size_neutral_rank_ic": 0.0425,
                "size_neutral_rank_ic_t_stat": 2.06,
                "mean_industry_neutral_rank_ic": 0.4340,
                "industry_neutral_rank_ic_t_stat": 26.24,
                "ic_year_count": 1,
                "research_lead": False,
                "promotion_allowed": False,
                "blockers": ["ic_year_coverage_below_gate"],
            },
            {
                "factor_name": "analyst_target_upside_60",
                "horizon": 5,
                "mean_spearman_ic": 0.1511,
                "ic_t_stat": 3.74,
                "icir": 0.577,
                "fdr_significant": True,
                "bonferroni_significant": True,
                "mean_size_neutral_rank_ic": 0.1146,
                "size_neutral_rank_ic_t_stat": 2.91,
                "mean_industry_neutral_rank_ic": 0.4182,
                "industry_neutral_rank_ic_t_stat": 14.76,
                "ic_year_count": 1,
                "research_lead": False,
                "promotion_allowed": False,
                "blockers": ["ic_year_coverage_below_gate"],
            },
        ],
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
