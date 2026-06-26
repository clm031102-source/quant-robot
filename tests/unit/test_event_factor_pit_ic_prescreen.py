import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.event_factor_pit_ic_prescreen import (
    build_event_factor_pit_ic_prescreen,
    compute_event_factor_frame,
    summarize_event_factor_pit_ic_prescreen,
    write_event_factor_pit_ic_prescreen,
)
from quant_robot.ops.event_factor_preregistration import EventFactorCandidateSpec, default_event_factor_candidate_specs


class EventFactorPitIcPrescreenTests(unittest.TestCase):
    def test_compute_event_factor_frame_uses_next_trade_date_after_announcement(self) -> None:
        bars = _synthetic_bars(days=8, assets=4)
        stock_basic = _stock_basic(4)
        forecast = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "ann_date": ["20240102"] * 4,
                "end_date": ["20240331"] * 4,
                "p_change_min": [1.0, 2.0, 3.0, 4.0],
                "p_change_max": [1.0, 2.0, 3.0, 4.0],
                "net_profit_min": [10.0, 20.0, 30.0, 40.0],
                "net_profit_max": [10.0, 20.0, 30.0, 40.0],
            }
        )

        factors = compute_event_factor_frame(
            {"forecast": forecast},
            bars,
            stock_basic,
            candidate_specs=[default_event_factor_candidate_specs()[0]],
            pit_lag_trade_days=1,
        )

        self.assertEqual(set(factors["factor_name"]), {"event_forecast_profit_revision_1q"})
        self.assertEqual(set(pd.to_datetime(factors["event_date"]).dt.date.astype(str)), {"2024-01-02"})
        self.assertEqual(set(pd.to_datetime(factors["date"]).dt.date.astype(str)), {"2024-01-03"})
        self.assertTrue((factors["date"] > factors["event_date"]).all())
        self.assertTrue(factors["factor_value"].notna().all())
        self.assertTrue((factors["pit_lag_trade_days"] == 1).all())

    def test_compute_event_factor_frame_supports_express_profit_surprise(self) -> None:
        bars = _synthetic_bars(days=8, assets=4)
        stock_basic = _stock_basic(4)
        specs = {spec.factor_name: spec for spec in default_event_factor_candidate_specs()}
        express = pd.DataFrame(
            {
                "symbol": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "event_date": ["2024-01-02"] * 4,
                "end_date": ["2024-03-31"] * 4,
                "yoy_net_profit": [10.0, 20.0, 40.0, 80.0],
                "diluted_roe": [2.0, 4.0, 8.0, 16.0],
            }
        )

        factors = compute_event_factor_frame(
            {"express": express},
            bars,
            stock_basic,
            candidate_specs=[specs["event_express_profit_surprise_1q"]],
            pit_lag_trade_days=1,
        )

        self.assertEqual(set(factors["factor_name"]), {"event_express_profit_surprise_1q"})
        self.assertEqual(set(pd.to_datetime(factors["event_date"]).dt.date.astype(str)), {"2024-01-02"})
        self.assertEqual(set(pd.to_datetime(factors["date"]).dt.date.astype(str)), {"2024-01-03"})
        self.assertTrue((factors["date"] > factors["event_date"]).all())
        self.assertTrue(factors["factor_value"].notna().all())
        self.assertGreater(factors["factor_value"].max(), factors["factor_value"].min())

    def test_compute_event_factor_frame_supports_forecast_guidance_uncertainty_specs(self) -> None:
        bars = _synthetic_bars(days=8, assets=4)
        stock_basic = _stock_basic(4)
        forecast = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "ann_date": ["20240102"] * 4,
                "end_date": ["20240331"] * 4,
                "p_change_min": [10.0, 20.0, -10.0, 40.0],
                "p_change_max": [30.0, 22.0, 10.0, 80.0],
                "net_profit_min": [100.0, 120.0, -20.0, 60.0],
                "net_profit_max": [200.0, 122.0, 20.0, 120.0],
            }
        )

        factors = compute_event_factor_frame(
            {"forecast": forecast},
            bars,
            stock_basic,
            candidate_specs=_forecast_guidance_specs(),
            pit_lag_trade_days=1,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {
                "event_forecast_guidance_confidence_1q",
                "event_forecast_uncertainty_compression_1q",
                "event_forecast_positive_floor_skew_1q",
            },
        )
        self.assertEqual(set(pd.to_datetime(factors["date"]).dt.date.astype(str)), {"2024-01-03"})
        self.assertTrue((factors["date"] > factors["event_date"]).all())
        confidence = factors[factors["factor_name"] == "event_forecast_guidance_confidence_1q"]
        compressed = factors[factors["factor_name"] == "event_forecast_uncertainty_compression_1q"]
        floor_skew = factors[factors["factor_name"] == "event_forecast_positive_floor_skew_1q"]
        self.assertGreater(
            float(confidence.loc[confidence["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
            float(confidence.loc[confidence["asset_id"] == "CN_XSHE_000000", "factor_value"].iloc[0]),
        )
        self.assertGreater(
            float(compressed.loc[compressed["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
            float(compressed.loc[compressed["asset_id"] == "CN_XSHE_000003", "factor_value"].iloc[0]),
        )
        self.assertGreater(
            float(floor_skew.loc[floor_skew["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
            float(floor_skew.loc[floor_skew["asset_id"] == "CN_XSHE_000002", "factor_value"].iloc[0]),
        )

    def test_compute_event_factor_frame_supports_forecast_express_disagreement_specs(self) -> None:
        bars = _synthetic_bars(days=10, assets=4)
        stock_basic = _stock_basic(4)
        forecast = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "ann_date": ["20240102"] * 4,
                "end_date": ["20240331"] * 4,
                "p_change_min": [8.0, 28.0, 5.0, 20.0],
                "p_change_max": [12.0, 32.0, 5.0, 20.0],
            }
        )
        express = pd.DataFrame(
            {
                "symbol": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "ann_date": ["20240104"] * 4,
                "end_date": ["20240331"] * 4,
                "yoy_net_profit": [30.0, 20.0, 10.0, 40.0],
            }
        )

        factors = compute_event_factor_frame(
            {"forecast": forecast, "express": express},
            bars,
            stock_basic,
            candidate_specs=_forecast_express_disagreement_specs(),
            pit_lag_trade_days=1,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {
                "event_forecast_express_disagreement_1q",
                "event_forecast_express_disagreement_industry_relative_1q",
                "event_forecast_express_stale_forecast_correction_1q",
            },
        )
        self.assertEqual(set(pd.to_datetime(factors["event_date"]).dt.date.astype(str)), {"2024-01-04"})
        self.assertEqual(set(pd.to_datetime(factors["date"]).dt.date.astype(str)), {"2024-01-05"})
        self.assertTrue((factors["date"] > factors["event_date"]).all())
        raw = factors[factors["factor_name"] == "event_forecast_express_disagreement_1q"]
        self.assertAlmostEqual(
            float(raw.loc[raw["asset_id"] == "CN_XSHE_000000", "factor_value"].iloc[0]),
            20.0,
        )
        self.assertAlmostEqual(
            float(raw.loc[raw["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
            -10.0,
        )
        industry_relative = factors[
            factors["factor_name"] == "event_forecast_express_disagreement_industry_relative_1q"
        ]
        self.assertGreater(
            float(industry_relative.loc[industry_relative["asset_id"] == "CN_XSHE_000000", "factor_value"].iloc[0]),
            float(industry_relative.loc[industry_relative["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
        )

    def test_compute_event_factor_frame_supports_share_unlock_and_pledge_relief(self) -> None:
        bars = _synthetic_bars(days=12, assets=4)
        stock_basic = _stock_basic(4)
        specs = {spec.factor_name: spec for spec in default_event_factor_candidate_specs()}
        share_float = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"],
                "ann_date": ["20240102"] * 4,
                "float_date": ["20240119"] * 4,
                "float_share": [10_000_000.0, 2_000_000.0, 6_000_000.0, 1_000_000.0],
                "float_ratio": [5.0, 1.0, 3.0, 0.5],
                "share_type": ["locked"] * 4,
            }
        )
        pledge_stat = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"] * 2,
                "end_date": ["20240102"] * 4 + ["20240105"] * 4,
                "pledge_ratio": [10.0, 10.0, 5.0, 2.0, 8.0, 11.0, 5.0, 1.0],
                "pledge_count": [2, 2, 1, 1, 2, 3, 1, 1],
                "total_share": [100.0] * 8,
            }
        )

        factors = compute_event_factor_frame(
            {"share_float": share_float, "pledge_stat": pledge_stat},
            bars,
            stock_basic,
            candidate_specs=[
                specs["event_share_unlock_pressure_60"],
                specs["event_pledge_ratio_relief_1q"],
            ],
            pit_lag_trade_days=1,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {"event_share_unlock_pressure_60", "event_pledge_ratio_relief_1q"},
        )
        share_rows = factors[factors["factor_name"] == "event_share_unlock_pressure_60"]
        pledge_rows = factors[factors["factor_name"] == "event_pledge_ratio_relief_1q"]
        share_signal_dates = set(pd.to_datetime(share_rows["date"]).dt.date.astype(str))
        self.assertIn("2024-01-03", share_signal_dates)
        self.assertGreater(len(share_signal_dates), 1)
        self.assertTrue((pd.to_datetime(share_rows["date"]) <= pd.Timestamp("2024-01-19")).all())
        self.assertEqual(set(pd.to_datetime(pledge_rows["date"]).dt.date.astype(str)), {"2024-01-08"})
        self.assertAlmostEqual(
            float(share_rows.loc[share_rows["asset_id"] == "CN_XSHE_000000", "factor_value"].iloc[0]),
            -5.0,
        )
        self.assertAlmostEqual(
            float(pledge_rows.loc[pledge_rows["asset_id"] == "CN_XSHE_000000", "factor_value"].iloc[0]),
            2.0,
        )
        self.assertAlmostEqual(
            float(pledge_rows.loc[pledge_rows["asset_id"] == "CN_XSHE_000001", "factor_value"].iloc[0]),
            -1.0,
        )
        self.assertTrue((factors["date"] > factors["event_date"]).all())

    def test_summarize_requires_industry_and_size_neutral_ic_before_lead(self) -> None:
        dates = pd.bdate_range("2024-01-03", periods=8)
        factor_rows = []
        label_rows = []
        for date_value in dates:
            for asset_idx in range(4):
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                within_industry_rank = asset_idx % 2
                factor_rows.append(
                    {
                        "date": date_value,
                        "event_date": date_value - pd.Timedelta(days=1),
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "event_industry_neutral_signal",
                        "factor_value": float(within_industry_rank),
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0 + (asset_idx // 2) * 10_000_000.0,
                        "log_adv20": 1.0 + (asset_idx // 2),
                    }
                )
                label_rows.append(
                    {
                        "date": date_value,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": 0.01 + within_industry_rank * 0.03,
                    }
                )

        result = summarize_event_factor_pit_ic_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(label_rows),
            _stock_basic(4),
            horizons=(5,),
            min_cross_section=4,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=2,
            min_neutral_ic_t_stat=2.0,
            min_ic_years=1,
        )

        self.assertEqual(result["stage"], "event_factor_pit_ic_prescreen")
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["mean_spearman_ic"], 0.8)
        self.assertGreater(row["mean_industry_neutral_rank_ic"], 0.8)
        self.assertGreater(row["mean_size_neutral_rank_ic"], 0.8)
        self.assertNotIn("industry_neutral_ic_below_gate", row["blockers"])
        self.assertNotIn("size_neutral_ic_below_gate", row["blockers"])

    def test_industry_dominated_event_signal_is_not_a_research_lead(self) -> None:
        dates = pd.bdate_range("2024-01-03", periods=8)
        factor_rows = []
        label_rows = []
        for date_value in dates:
            for asset_idx in range(4):
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                industry_rank = asset_idx // 2
                factor_rows.append(
                    {
                        "date": date_value,
                        "event_date": date_value - pd.Timedelta(days=1),
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "event_industry_beta_only",
                        "factor_value": float(industry_rank),
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                        "log_adv20": 1.0,
                    }
                )
                label_rows.append(
                    {
                        "date": date_value,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": industry_rank * 0.03,
                    }
                )

        result = summarize_event_factor_pit_ic_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(label_rows),
            _stock_basic(4),
            horizons=(5,),
            min_cross_section=4,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=2,
            min_ic_years=1,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertIn("industry_neutral_ic_below_gate", row["blockers"])
        self.assertEqual(result["summary"]["research_lead_count"], 0)

    def test_event_top_quantile_turnover_is_diagnostic_not_a_lead_blocker(self) -> None:
        dates = pd.bdate_range("2024-01-03", periods=8)
        factor_rows = []
        label_rows = []
        for day_idx, date_value in enumerate(dates):
            for asset_idx in range(10):
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                signal = float((asset_idx + day_idx * 2) % 10)
                factor_rows.append(
                    {
                        "date": date_value,
                        "event_date": date_value - pd.Timedelta(days=1),
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "event_sparse_rotating_signal",
                        "factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0 + (asset_idx // 5) * 10_000_000.0,
                        "log_adv20": 1.0 + (asset_idx // 5),
                    }
                )
                label_rows.append(
                    {
                        "date": date_value,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 100.0,
                    }
                )

        stock_basic = _stock_basic(10)
        stock_basic.loc[:, "industry"] = ["Tech", "Tech", "Tech", "Tech", "Tech", "Bank", "Bank", "Bank", "Bank", "Bank"]
        result = summarize_event_factor_pit_ic_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(label_rows),
            stock_basic,
            horizons=(5,),
            min_cross_section=10,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=2,
            min_ic_years=1,
        )

        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["avg_top_quantile_turnover"], 0.90)
        self.assertNotIn("top_quantile_turnover_too_high", row["blockers"])

    def test_event_research_lead_requires_multi_year_ic_coverage(self) -> None:
        dates = pd.bdate_range("2024-01-03", periods=8)
        factor_rows = []
        label_rows = []
        for date_value in dates:
            for asset_idx in range(6):
                signal = float(asset_idx)
                factor_rows.append(
                    {
                        "date": date_value,
                        "event_date": date_value - pd.Timedelta(days=1),
                        "asset_id": f"CN_XSHE_{asset_idx:06d}",
                        "market": "CN",
                        "factor_name": "event_single_year_signal",
                        "factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                        "log_adv20": 1.0,
                    }
                )
                label_rows.append(
                    {
                        "date": date_value,
                        "asset_id": f"CN_XSHE_{asset_idx:06d}",
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 100.0,
                    }
                )

        result = summarize_event_factor_pit_ic_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(label_rows),
            _stock_basic(6),
            horizons=(5,),
            min_cross_section=6,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=3,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertEqual(row["ic_year_count"], 1)
        self.assertIn("ic_year_coverage_below_gate", row["blockers"])

    def test_build_and_writer_keep_final_holdout_and_promotion_blocked(self) -> None:
        bars = _synthetic_bars(days=16, assets=4)
        stock_basic = _stock_basic(4)
        forecast = pd.DataFrame(
            {
                "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"] * 8,
                "ann_date": [date.strftime("%Y%m%d") for date in pd.bdate_range("2024-01-02", periods=8) for _ in range(4)],
                "end_date": ["20240331"] * 32,
                "p_change_min": [0.0, 1.0, 0.0, 1.0] * 8,
                "p_change_max": [0.0, 1.0, 0.0, 1.0] * 8,
                "net_profit_min": [0.0, 1.0, 0.0, 1.0] * 8,
                "net_profit_max": [0.0, 1.0, 0.0, 1.0] * 8,
            }
        )

        result = build_event_factor_pit_ic_prescreen(
            bars=bars,
            stock_basic=stock_basic,
            event_frames={"forecast": forecast},
            candidate_specs=[default_event_factor_candidate_specs()[0]],
            horizons=(1,),
            execution_lag=0,
            min_cross_section=4,
            min_ic_observations=4,
        )

        self.assertEqual(result["stage"], "event_factor_pit_ic_prescreen")
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("forecast", result["event_snapshot_audit"])
        self.assertEqual(result["event_snapshot_audit"]["forecast"]["rows"], 32)
        self.assertIn("ann_date", result["event_snapshot_audit"]["forecast"]["date_ranges"])

        with tempfile.TemporaryDirectory() as tmp:
            write_event_factor_pit_ic_prescreen(tmp, result)
            self.assertTrue((Path(tmp) / "event_factor_pit_ic_prescreen.json").exists())
            self.assertTrue((Path(tmp) / "event_factor_pit_ic_prescreen.md").exists())
            self.assertTrue((Path(tmp) / "event_factor_pit_ic_prescreen_results.csv").exists())
            self.assertTrue((Path(tmp) / "event_factor_pit_ic_prescreen_ic_observations.csv").exists())


def _synthetic_bars(days: int = 12, assets: int = 4) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            price = price * (1.0 + (asset_idx % 2) * 0.01)
            rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 20_000_000.0 + asset_idx * 100_000 + day_idx,
                }
            )
    return pd.DataFrame(rows)


def _stock_basic(assets: int) -> pd.DataFrame:
    rows = []
    for asset_idx in range(assets):
        rows.append(
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "exchange": "XSHE",
                "industry": "Tech" if asset_idx < assets // 2 else "Bank",
                "name": f"Stock {asset_idx}",
                "list_date": "2020-01-01",
            }
        )
    return pd.DataFrame(rows)


def _forecast_guidance_specs() -> list[EventFactorCandidateSpec]:
    base = {
        "family": "forecast_guidance_uncertainty",
        "direction": "higher_is_better",
        "required_endpoints": ("forecast",),
        "required_fields": ("ann_date", "end_date", "p_change_min", "p_change_max", "net_profit_min", "net_profit_max"),
        "event_date_fields": ("ann_date",),
        "windows": (1,),
        "public_reference_tags": ("earnings_guidance", "forecast_uncertainty", "post_earnings_announcement_drift"),
        "expected_failure_modes": ("forecast_range_sparse_coverage", "management_guidance_bias", "industry_cycle_beta"),
    }
    return [
        EventFactorCandidateSpec(
            factor_name="event_forecast_guidance_confidence_1q",
            formula_template="positive guidance midpoint divided by guidance range width",
            economic_rationale="Positive narrow guidance can proxy management confidence rather than raw forecast direction.",
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_uncertainty_compression_1q",
            formula_template="negative guidance range width normalized by midpoint magnitude",
            economic_rationale="Narrower forecast ranges test whether lower earnings uncertainty is rewarded after announcement.",
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_positive_floor_skew_1q",
            formula_template="lower-bound positive forecast skew normalized by upper-bound magnitude",
            economic_rationale="A high positive lower bound tests asymmetric guidance confidence, not a sign flip of old forecast surprise.",
            **base,
        ),
    ]


def _forecast_express_disagreement_specs() -> list[EventFactorCandidateSpec]:
    base = {
        "family": "forecast_express_disagreement_event",
        "direction": "higher_is_better",
        "required_endpoints": ("forecast", "express"),
        "required_fields": ("ann_date", "end_date", "p_change_min", "p_change_max", "yoy_net_profit"),
        "event_date_fields": ("ann_date",),
        "windows": (1,),
        "public_reference_tags": ("earnings_revision", "expectation_update", "event_study"),
        "expected_failure_modes": ("forecast_express_join_sparse", "industry_cycle_beta", "stale_forecast_noise"),
    }
    return [
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_disagreement_1q",
            formula_template="express_yoy_net_profit - latest_prior_forecast_midpoint",
            economic_rationale="Later earnings express information can correct earlier forecast ranges; signal is tradable only after express availability.",
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_disagreement_industry_relative_1q",
            formula_template="forecast/express disagreement minus same-day industry median",
            economic_rationale="Industry-relative disagreement targets within-industry expectation updates rather than raw industry beta.",
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_stale_forecast_correction_1q",
            formula_template="forecast/express disagreement times log1p(days since forecast)",
            economic_rationale="Stale forecasts corrected by express releases may represent stronger expectation updates.",
            **base,
        ),
    ]


if __name__ == "__main__":
    unittest.main()
