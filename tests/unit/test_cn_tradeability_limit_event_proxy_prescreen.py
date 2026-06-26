import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_tradeability_limit_event_preregistration import (
    build_cn_tradeability_limit_event_preregistration,
)
from quant_robot.ops.cn_tradeability_limit_event_proxy_prescreen import (
    NEXT_DIRECTION_WITHOUT_PROXY_LEADS,
    build_cn_tradeability_limit_event_feature_frame,
    summarize_cn_tradeability_limit_event_proxy_prescreen_from_features,
    write_cn_tradeability_limit_event_proxy_prescreen,
)
from tests.unit.test_public_reference_multi_family_prescreen import _synthetic_public_reference_bars


def _stock_basic(assets: int = 45) -> pd.DataFrame:
    rows = []
    for asset_idx in range(assets):
        industry = "bank" if asset_idx < assets // 3 else "tech" if asset_idx < 2 * assets // 3 else "industrial"
        rows.append(
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "industry": industry,
                "name": f"Test{asset_idx:06d}",
                "stock_market": "主板",
                "list_date": "2010-01-01",
                "is_active": True,
            }
        )
    return pd.DataFrame(rows)


class CNTradeabilityLimitEventProxyPrescreenTests(unittest.TestCase):
    def test_limit_down_relief_uses_current_and_lagged_limit_state_only(self) -> None:
        bars = pd.DataFrame(
            [
                {"date": "2024-01-01", "asset_id": "CN_XSHE_000001", "symbol": "000001.SZ", "market": "CN", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "adj_close": 100.0, "volume": 1000.0, "amount": 100_000_000.0},
                {"date": "2024-01-02", "asset_id": "CN_XSHE_000001", "symbol": "000001.SZ", "market": "CN", "open": 90.0, "high": 90.0, "low": 90.0, "close": 90.0, "adj_close": 90.0, "volume": 1000.0, "amount": 90_000_000.0},
                {"date": "2024-01-03", "asset_id": "CN_XSHE_000001", "symbol": "000001.SZ", "market": "CN", "open": 91.0, "high": 92.0, "low": 90.5, "close": 91.0, "adj_close": 91.0, "volume": 1000.0, "amount": 91_000_000.0},
                {"date": "2024-01-04", "asset_id": "CN_XSHE_000001", "symbol": "000001.SZ", "market": "CN", "open": 92.0, "high": 93.0, "low": 91.0, "close": 92.0, "adj_close": 92.0, "volume": 1000.0, "amount": 92_000_000.0},
            ]
        )

        features = build_cn_tradeability_limit_event_feature_frame(
            bars,
            stock_basic=_stock_basic(1),
            horizons=(1,),
            execution_lag=1,
        )
        by_date = features.set_index(features["date"].dt.strftime("%Y-%m-%d"))

        self.assertEqual(int(by_date.loc["2024-01-02", "limit_down_like_0"]), 1)
        self.assertEqual(int(by_date.loc["2024-01-03", "limit_down_relief_proxy"]), 1)
        self.assertEqual(int(by_date.loc["2024-01-04", "limit_down_relief_proxy"]), 0)
        self.assertNotIn("next_day_not_limit_down_proxy", features.columns)

    def test_proxy_prescreen_evaluates_all_round159_candidates_without_promotion(self) -> None:
        bars = _synthetic_public_reference_bars(days=150, assets=45)
        features = build_cn_tradeability_limit_event_feature_frame(
            bars,
            stock_basic=_stock_basic(45),
            horizons=(5,),
            execution_lag=1,
        )
        prereg = build_cn_tradeability_limit_event_preregistration()

        result = summarize_cn_tradeability_limit_event_proxy_prescreen_from_features(
            features,
            stock_basic=_stock_basic(45),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
            min_industries=2,
            min_assets_per_industry=2,
        )

        self.assertEqual(result["stage"], "cn_tradeability_limit_event_proxy_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertGreaterEqual(result["summary"]["true_limit_status_audit_required_candidates"], 8)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_true_limit_audit"])
        self.assertTrue(result["promotion_policy"]["requires_true_limit_status_audit"])
        self.assertEqual(result["multiple_testing_policy"]["round159_candidate_count"], 8)
        self.assertEqual(len(result["results"]), 8)
        for row in result["results"]:
            self.assertIn("raw_mean_spearman_ic", row)
            self.assertIn("industry_neutral_mean_spearman_ic", row)
            self.assertIn("residual_mean_spearman_ic", row)
            self.assertIn("tradeability_blocked_signal_rate", row)
            self.assertFalse(row["promotion_allowed"])
            self.assertFalse(row["portfolio_grid_allowed"])

    def test_high_residual_threshold_blocks_proxy_leads_and_rotates(self) -> None:
        bars = _synthetic_public_reference_bars(days=90, assets=36)
        features = build_cn_tradeability_limit_event_feature_frame(
            bars,
            stock_basic=_stock_basic(36),
            horizons=(5,),
            execution_lag=1,
        )
        prereg = build_cn_tradeability_limit_event_preregistration()

        result = summarize_cn_tradeability_limit_event_proxy_prescreen_from_features(
            features,
            stock_basic=_stock_basic(36),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=18,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
            min_residual_mean_ic=0.99,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["proxy_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_PROXY_LEADS)
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_writer_outputs_structured_files(self) -> None:
        bars = _synthetic_public_reference_bars(days=80, assets=36)
        features = build_cn_tradeability_limit_event_feature_frame(
            bars,
            stock_basic=_stock_basic(36),
            horizons=(5,),
            execution_lag=1,
        )
        prereg = build_cn_tradeability_limit_event_preregistration()
        result = summarize_cn_tradeability_limit_event_proxy_prescreen_from_features(
            features,
            stock_basic=_stock_basic(36),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=18,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_tradeability_limit_event_proxy_prescreen(output, result)
            self.assertTrue((output / "cn_tradeability_limit_event_proxy_prescreen.json").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_proxy_prescreen.md").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_proxy_prescreen_results.csv").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_reference_correlations.csv").exists())


if __name__ == "__main__":
    unittest.main()
