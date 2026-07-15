import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_market_residual_volatility_prescreen import (
    run_cn_etf_market_residual_volatility_prescreen_cli,
)


EXPECTED_ARTIFACTS = (
    "cn_etf_market_residual_volatility_prescreen.json",
    "cn_etf_market_residual_volatility_prescreen.md",
    "cn_etf_market_residual_volatility_prescreen_results.csv",
    "cn_etf_market_residual_volatility_ic_observations.csv",
    "cn_etf_market_residual_volatility_yearly_ic.csv",
    "cn_etf_market_residual_volatility_reference_correlations.csv",
    "cn_etf_market_residual_volatility_capacity.csv",
)


class CnEtfMarketResidualVolatilityPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_frozen_artifacts_without_2026_signal_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "processed"
            metadata_root = data_root / "metadata" / "tushare_fund_basic"
            output_dir = root / "reports"
            legacy_report = root / "legacy" / "promotion_report.json"
            config_path = root / "config.json"
            bars = _synthetic_bars()
            store = DatasetStore(data_root)
            for year, frame in bars.groupby(bars["date"].dt.year):
                store.write_frame(
                    frame,
                    "processed/bars",
                    {"frequency": "1d", "market": "CN_ETF", "year": str(year)},
                )
            metadata_root.mkdir(parents=True)
            pd.DataFrame(
                [
                    {
                        "symbol": symbol,
                        "is_etf": True,
                        "list_date": "2018-01-01",
                        "delist_date": None,
                    }
                    for symbol in sorted(bars["symbol"].unique())
                ]
            ).to_parquet(metadata_root / "part-00000.parquet", index=False)
            legacy_report.parent.mkdir(parents=True)
            legacy_report.write_text(json.dumps(_legacy_report()), encoding="utf-8")
            config_path.write_text(
                json.dumps(_config(data_root, metadata_root, legacy_report, output_dir)),
                encoding="utf-8",
            )

            result = run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)

            self.assertEqual(result["stage"], "cn_etf_market_residual_volatility_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertEqual(result["summary"]["reference_count"], 9)
            self.assertEqual(result["summary"]["test_count"], 6)
            self.assertEqual(result["summary"]["capacity_row_count"], 6)
            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertEqual(result["legacy_promotion_quarantine"]["volatility_rows"], 45)
            self.assertFalse(result["decision"]["portfolio_grid_allowed"])
            self.assertFalse(result["decision"]["promotion_allowed"])
            for filename in EXPECTED_ARTIFACTS:
                self.assertTrue((output_dir / filename).exists(), filename)

            payload = json.loads(
                (output_dir / "cn_etf_market_residual_volatility_prescreen.json").read_text(
                    encoding="utf-8"
                )
            )
            signal_dates = {row["date"] for row in payload["ic_observations"]}
            self.assertTrue(signal_dates)
            self.assertTrue(all(signal_date < "2026-01-01" for signal_date in signal_dates))

    def test_cli_rejects_enabled_execution_boundary_before_loading_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(
                root / "missing-data",
                root / "missing-metadata",
                root / "missing-legacy.json",
                root / "output",
            )
            config["walk_forward_allowed"] = True
            config_path = root / "unsafe.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "walk_forward_allowed must be explicitly false"):
                run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)

    def test_cli_rejects_2026_analysis_end_before_loading_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(
                root / "missing-data",
                root / "missing-metadata",
                root / "missing-legacy.json",
                root / "output",
            )
            config["analysis_end_date"] = "2026-01-01"
            config_path = root / "holdout.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sealed 2026 final holdout"):
                run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)

    def test_cli_rejects_candidate_parameter_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(
                root / "missing-data",
                root / "missing-metadata",
                root / "missing-legacy.json",
                root / "output",
            )
            config["candidate_parameters"]["residual_model_lag"] = 0
            config_path = root / "drift.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "candidate_parameters do not match"):
                run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)

    def test_cli_rejects_statistical_threshold_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(
                root / "missing-data",
                root / "missing-metadata",
                root / "missing-legacy.json",
                root / "output",
            )
            config["thresholds"]["min_icir"] = 0.31
            config_path = root / "threshold-drift.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "thresholds do not match"):
                run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)

    def test_cli_rejects_multiple_testing_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(
                root / "missing-data",
                root / "missing-metadata",
                root / "missing-legacy.json",
                root / "output",
            )
            config["multiple_testing"]["method"] = "none"
            config_path = root / "multiple-testing-drift.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "multiple_testing does not match"):
                run_cn_etf_market_residual_volatility_prescreen_cli(config_path=config_path)


def _synthetic_bars(*, assets: int = 30) -> pd.DataFrame:
    dates = pd.bdate_range("2019-01-02", periods=500).append(
        pd.bdate_range("2026-01-05", periods=8)
    )
    rows = []
    prices = [1.0 + asset_index * 0.05 for asset_index in range(assets)]
    for date_index, signal_date in enumerate(dates):
        common = 0.004 * np.sin(date_index / 3.0) - 0.002 * np.cos(date_index / 7.0)
        for asset_index in range(assets):
            daily_return = common * (0.6 + asset_index * 0.1)
            daily_return += 0.0015 * np.sin(date_index / (2.0 + asset_index * 0.2) + asset_index)
            prices[asset_index] *= 1.0 + daily_return
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"CN_ETF_XSHG_{510000 + asset_index}",
                    "symbol": f"{510000 + asset_index}.SH",
                    "market": "CN_ETF",
                    "adj_close": prices[asset_index],
                    "high": prices[asset_index] * 1.006,
                    "low": prices[asset_index] * 0.994,
                    "volume": 1_000_000.0 + asset_index * 100_000.0,
                    "amount": 20_000_000.0 + asset_index * 500_000.0 + (date_index % 11) * 100_000.0,
                }
            )
    return pd.DataFrame(rows)


def _legacy_report() -> dict[str, object]:
    volatility_rows = []
    for window in (5, 10, 20, 60, 120):
        for top_n in (1, 2, 3):
            for rebalance in (5, 10, 20):
                volatility_rows.append(
                    {
                        "case_id": f"CN_ETF_volatility_{window}_top{top_n}_cost5_reb{rebalance}",
                        "factor_name": f"volatility_{window}",
                        "promotion_status": "blocked",
                    }
                )
    other_rows = [
        {
            "case_id": f"other_{index}",
            "factor_name": "other",
            "promotion_status": "blocked",
        }
        for index in range(225)
    ]
    return {
        "summary": {
            "candidates": 270,
            "blocked": 270,
            "paper_ready": 0,
            "research_only": 0,
        },
        "candidates": volatility_rows + other_rows,
    }


def _config(
    data_root: Path,
    metadata_root: Path,
    legacy_report: Path,
    output_dir: Path,
) -> dict[str, object]:
    return {
        "stage": "cn_etf_market_residual_volatility_prescreen",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_volatility_regime",
        "research_scope": "market_residual_volatility_asymmetry_last_chance",
        "data_root": str(data_root),
        "metadata_root": str(metadata_root),
        "legacy_promotion_report": str(legacy_report),
        "analysis_start_date": "2020-01-02",
        "analysis_end_date": "2024-06-28",
        "final_holdout_start": "2026-01-01",
        "market_proxy": {
            "method": "point_in_time_eligible_cross_sectional_median_return",
            "min_cross_section": 30,
        },
        "candidate_names": [
            "etf_idio_vol_low_60",
            "etf_downside_beta_low_120",
            "etf_positive_residual_skew_60",
        ],
        "candidate_parameters": {
            "beta_window": 120,
            "beta_min_observations": 80,
            "downside_beta_window": 120,
            "downside_beta_min_observations": 24,
            "residual_window": 60,
            "residual_min_observations": 40,
            "residual_model_lag": 1,
            "include_intercept": True,
        },
        "reference_names": [
            "low_volatility_20",
            "low_volatility_60",
            "low_downside_volatility_60",
            "drawdown_resilience_60",
            "crash_recovery_60",
            "recovery_quality_60",
            "formula_range_contraction_breakout_20",
            "formula_range_contraction_breakout_lowvol_20",
            "bollinger_reversal_20",
        ],
        "horizons": [5, 20],
        "execution_lag": 1,
        "eligibility": {
            "point_in_time": True,
            "official_etf_only": True,
            "min_prior_observations": 252,
            "liquidity_window": 20,
            "min_trailing_median_amount": 5000000.0,
            "max_stale_rate": 0.05,
            "max_abs_return": 0.2,
        },
        "thresholds": {
            "alpha": 0.05,
            "min_cross_section": 30,
            "min_ic_observations": 20,
            "min_year_ic_observations": 20,
            "min_usable_years": 3,
            "min_mean_rank_ic": 0.02,
            "min_icir": 0.3,
            "min_positive_ic_rate": 0.55,
            "min_quantile_monotonicity": 0.7,
            "max_top_quantile_turnover": 0.9,
            "min_positive_year_rate": 0.6,
            "max_abs_reference_correlation": 0.85,
        },
        "capacity": {
            "amount_unit": "CNY",
            "adv_window": 20,
            "portfolio_value_cny": 1000000.0,
            "position_count": 10,
            "max_one_way_participation_rate": 0.01,
            "top_quantile_adv20_percentile": 0.1,
            "required_capacity_coverage_rate": 1.0,
        },
        "multiple_testing": {
            "method": "benjamini_hochberg",
            "scope": "all_frozen_candidate_horizon_tests",
        },
        "zero_lead_decision": {
            "closed_family": "cn_etf_volatility_regime",
            "closed_budget_share": 0.35,
            "activated_family": "cn_etf_peer_relative_value",
            "resulting_budget_shares": {
                "cn_etf_flow_breadth_aggregation": 0.35,
                "cn_etf_fund_structure": 0.35,
                "cn_etf_peer_relative_value": 0.30,
            },
        },
        "output_dir": str(output_dir),
        "last_chance_batch": True,
        "sign_flip_rescue_allowed": False,
        "parameter_rescue_allowed": False,
        "window_tuning_allowed": False,
        "threshold_relaxation_allowed": False,
        "regime_rescue_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_trading_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
