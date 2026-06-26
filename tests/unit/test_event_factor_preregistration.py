import unittest

import pandas as pd

from quant_robot.ops.event_factor_preregistration import (
    ROUND145_SOURCE_AUDIT,
    ROUND146_NEXT_DIRECTION,
    SOURCE_EVIDENCE_STATUS,
    build_event_factor_preregistration,
    default_event_factor_candidate_specs,
)


class EventFactorPreregistrationTests(unittest.TestCase):
    def test_preregisters_event_candidates_without_promotion(self) -> None:
        result = build_event_factor_preregistration(
            min_candidates=8,
            min_families=5,
            endpoint_probe_results={
                "forecast": {"ok": True, "rows": 12, "columns": ["ts_code", "ann_date", "end_date"]},
                "express": {"ok": True, "rows": 8, "columns": ["ts_code", "ann_date", "end_date"]},
                "dividend": {"ok": True, "rows": 20, "columns": ["ts_code", "ann_date", "ex_date"]},
                "repurchase": {"ok": True, "rows": 5, "columns": ["ts_code", "ann_date", "amount"]},
                "stk_holdernumber": {"ok": True, "rows": 10, "columns": ["ts_code", "ann_date", "holder_num"]},
                "share_float": {"ok": True, "rows": 2, "columns": ["ts_code", "ann_date", "float_date"]},
                "top10_holders": {"ok": True, "rows": 7, "columns": ["ts_code", "ann_date", "hold_ratio"]},
                "top10_floatholders": {"ok": True, "rows": 7, "columns": ["ts_code", "ann_date", "hold_ratio"]},
                "pledge_stat": {"ok": True, "rows": 3, "columns": ["ts_code", "end_date", "pledge_ratio"]},
            },
        )

        self.assertEqual(result["stage"], "event_factor_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 5)
        self.assertGreaterEqual(result["summary"]["available_endpoint_count"], 6)
        self.assertEqual(result["summary"]["next_required_gate"], ROUND146_NEXT_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        rotation = result["family_rotation_context"]
        self.assertEqual(rotation["source_audit"], ROUND145_SOURCE_AUDIT)
        self.assertIn("daily_basic_free_float_supply_quality", rotation["hibernated_families"])
        self.assertEqual(rotation["next_direction"], ROUND146_NEXT_DIRECTION)

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("event_forecast_profit_revision_1q", names)
        self.assertIn("event_repurchase_amount_to_mv_20", names)
        self.assertIn("event_holder_number_contraction_2q", names)
        self.assertIn("event_top_holder_concentration_change_1q", names)

        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertTrue(candidate["expected_failure_modes"])
            self.assertTrue(candidate["required_endpoints"])
            self.assertIn("ann_date_or_effective_date_lag", candidate["pit_controls"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], ROUND146_NEXT_DIRECTION)

    def test_default_specs_are_unique_and_span_event_families(self) -> None:
        specs = default_event_factor_candidate_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertGreaterEqual(len({spec.family for spec in specs}), 5)
        self.assertTrue(all(spec.required_endpoints for spec in specs))
        self.assertTrue(all(spec.required_fields for spec in specs))
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(spec.expected_failure_modes for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))

    def test_missing_endpoint_coverage_blocks_preregistration(self) -> None:
        result = build_event_factor_preregistration(
            min_candidates=8,
            min_families=5,
            endpoint_probe_results={
                "forecast": {"ok": True, "rows": 0, "columns": ["ts_code", "ann_date", "end_date"]},
                "express": {"ok": False, "rows": 0, "columns": []},
            },
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("available_event_endpoints_below_minimum", result["summary"]["blockers"])
        self.assertIn("available_candidate_count_below_minimum", result["summary"]["blockers"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_partial_endpoint_coverage_allows_available_candidates_only(self) -> None:
        result = build_event_factor_preregistration(
            min_candidates=8,
            min_families=5,
            min_available_candidates=5,
            min_available_families=5,
            endpoint_probe_results={
                "forecast": {"ok": True, "rows": 6, "columns": ["ts_code", "ann_date", "end_date"]},
                "express": {"ok": True, "rows": 0, "columns": ["ts_code", "ann_date", "end_date"]},
                "dividend": {"ok": True, "rows": 266, "columns": ["ts_code", "ann_date", "ex_date"]},
                "repurchase": {"ok": True, "rows": 178, "columns": ["ts_code", "ann_date", "amount"]},
                "stk_holdernumber": {"ok": True, "rows": 71, "columns": ["ts_code", "ann_date", "holder_num"]},
                "share_float": {"ok": True, "rows": 0, "columns": ["ts_code", "ann_date", "float_date"]},
                "top10_holders": {"ok": True, "rows": 159, "columns": ["ts_code", "ann_date", "hold_ratio"]},
                "top10_floatholders": {"ok": True, "rows": 101, "columns": ["ts_code", "ann_date", "hold_ratio"]},
                "pledge_stat": {"ok": True, "rows": 0, "columns": ["ts_code", "end_date", "pledge_ratio"]},
            },
        )

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["available_candidate_count"], 5)
        self.assertEqual(result["summary"]["blocked_candidate_count"], 3)
        available_names = {candidate["factor_name"] for candidate in result["available_candidates"]}
        blocked_names = {candidate["factor_name"] for candidate in result["blocked_candidates"]}
        self.assertIn("event_repurchase_amount_to_mv_20", available_names)
        self.assertIn("event_top_holder_concentration_change_1q", available_names)
        self.assertIn("event_express_profit_surprise_1q", blocked_names)
        self.assertIn("event_share_unlock_pressure_60", blocked_names)
        self.assertIn("event_pledge_ratio_relief_1q", blocked_names)

    def test_probe_event_endpoints_handles_fake_adapter(self) -> None:
        from quant_robot.ops.event_factor_preregistration import probe_event_endpoints

        result = probe_event_endpoints(
            _FakeEventAdapter(),
            sample_symbols=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-12-31",
            ann_dates=("20240105",),
            periods=("20240331",),
        )

        self.assertEqual(result["dividend"]["rows"], 1)
        self.assertEqual(result["repurchase"]["rows"], 1)
        self.assertFalse(result["share_float"]["ok"])
        self.assertIn("permission denied", result["share_float"]["error"])

    def test_cross_section_probe_identifies_ready_query_patterns(self) -> None:
        from quant_robot.ops.event_factor_preregistration import probe_event_cross_section_patterns

        result = probe_event_cross_section_patterns(
            _CrossSectionPatternAdapter(),
            min_rows=30,
            forecast_ann_date="20240131",
            express_start_date="2024-01-01",
            express_end_date="2024-03-31",
            dividend_ann_date="20240329",
            holder_start_date="2024-01-01",
            holder_end_date="2024-03-31",
            top_holder_period="20240331",
        )

        self.assertTrue(result["forecast_ann_date"]["cross_section_ready"])
        self.assertTrue(result["express_start_end"]["cross_section_ready"])
        self.assertTrue(result["dividend_ann_date"]["cross_section_ready"])
        self.assertTrue(result["holdernumber_start_end"]["cross_section_ready"])
        self.assertTrue(result["top10_holders_period"]["cross_section_ready"])
        self.assertFalse(result["top10_floatholders_period"]["cross_section_ready"])
        self.assertEqual(result["top10_floatholders_period"]["rows"], 0)


class _FakeEventAdapter:
    def fetch_event_endpoint(self, endpoint, **kwargs):
        if endpoint == "share_float":
            raise RuntimeError("permission denied")
        if endpoint == "forecast":
            return pd.DataFrame(columns=["ts_code", "ann_date", "end_date"])
        if endpoint == "dividend":
            return pd.DataFrame({"ts_code": ["000001.SZ"], "ann_date": ["20240315"], "ex_date": ["20240601"]})
        if endpoint == "repurchase":
            return pd.DataFrame({"ts_code": ["000001.SZ"], "ann_date": ["20240105"], "amount": [1000.0]})
        return pd.DataFrame({"ts_code": ["000001.SZ"], "ann_date": ["20240331"], "end_date": ["20240331"]})


class _CrossSectionPatternAdapter:
    def fetch_event_endpoint(self, endpoint, **kwargs):
        row_counts = {
            ("forecast", "ann_date"): 120,
            ("express", "start_date"): 80,
            ("dividend", "ann_date"): 60,
            ("stk_holdernumber", "start_date"): 200,
            ("top10_holders", "period"): 300,
            ("top10_floatholders", "period"): 0,
        }
        key = (endpoint, next((name for name in ("ann_date", "start_date", "period") if name in kwargs), ""))
        rows = row_counts.get(key, 0)
        return pd.DataFrame(
            {
                "ts_code": [f"{index:06d}.SZ" for index in range(rows)],
                "ann_date": ["20240131"] * rows,
                "end_date": ["20240331"] * rows,
            }
        )


if __name__ == "__main__":
    unittest.main()
