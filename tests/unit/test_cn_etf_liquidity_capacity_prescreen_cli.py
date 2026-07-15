import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_liquidity_capacity_prescreen import (
    run_cn_etf_liquidity_capacity_prescreen_cli,
)


EXPECTED_ARTIFACTS = (
    "cn_etf_liquidity_capacity_prescreen.json",
    "cn_etf_liquidity_capacity_prescreen.md",
    "cn_etf_liquidity_capacity_prescreen_results.csv",
    "cn_etf_liquidity_capacity_ic_observations.csv",
    "cn_etf_liquidity_capacity_yearly_ic.csv",
    "cn_etf_liquidity_capacity_reference_correlations.csv",
    "cn_etf_liquidity_capacity_capacity.csv",
)


class CnEtfLiquidityCapacityPrescreenCliTests(unittest.TestCase):
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
                        "list_date": "2020-01-01",
                        "delist_date": None,
                    }
                    for symbol in sorted(bars["symbol"].unique())
                ]
            ).to_parquet(metadata_root / "part-00000.parquet", index=False)
            legacy_report.parent.mkdir(parents=True)
            legacy_report.write_text(
                json.dumps(
                    {
                        "summary": {
                            "candidates": 270,
                            "blocked": 270,
                            "paper_ready": 0,
                            "research_only": 0,
                        }
                    }
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps(_config(data_root, metadata_root, legacy_report, output_dir)),
                encoding="utf-8",
            )

            result = run_cn_etf_liquidity_capacity_prescreen_cli(config_path=config_path)

            self.assertEqual(result["stage"], "cn_etf_liquidity_capacity_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertEqual(result["summary"]["reference_count"], 13)
            self.assertEqual(result["summary"]["test_count"], 6)
            self.assertEqual(result["summary"]["capacity_row_count"], 6)
            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertEqual(result["legacy_promotion_quarantine"]["summary"]["blocked"], 270)
            self.assertEqual(result["legacy_promotion_quarantine"]["summary"]["paper_ready"], 0)
            self.assertFalse(result["decision"]["portfolio_grid_allowed"])
            self.assertFalse(result["decision"]["promotion_allowed"])
            for filename in EXPECTED_ARTIFACTS:
                self.assertTrue((output_dir / filename).exists(), filename)

            payload = json.loads(
                (output_dir / "cn_etf_liquidity_capacity_prescreen.json").read_text(encoding="utf-8")
            )
            signal_dates = {row["date"] for row in payload["ic_observations"]}
            self.assertTrue(signal_dates)
            self.assertTrue(all(signal_date < "2026-01-01" for signal_date in signal_dates))
            observations = pd.read_csv(output_dir / "cn_etf_liquidity_capacity_ic_observations.csv")
            self.assertTrue((pd.to_datetime(observations["date"]).dt.year < 2026).all())

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
                run_cn_etf_liquidity_capacity_prescreen_cli(config_path=config_path)

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
                run_cn_etf_liquidity_capacity_prescreen_cli(config_path=config_path)


def _synthetic_bars(*, assets: int = 8) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=180).append(pd.bdate_range("2026-01-05", periods=8))
    rows = []
    for asset_index in range(assets):
        symbol = f"{510000 + asset_index}.SH"
        asset_id = f"CN_ETF_XSHG_{510000 + asset_index}"
        price = 1.0 + asset_index * 0.05
        for date_index, signal_date in enumerate(dates):
            price *= 1.0 + 0.0005 * (asset_index + 1) + 0.001 * ((date_index % 7) - 3)
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "adj_close": price,
                    "volume": 1_000_000.0 + asset_index * 100_000.0,
                    "amount": 20_000_000.0 + asset_index * 500_000.0 + (date_index % 11) * 100_000.0,
                }
            )
    return pd.DataFrame(rows)


def _config(
    data_root: Path,
    metadata_root: Path,
    legacy_report: Path,
    output_dir: Path,
) -> dict[str, object]:
    return {
        "stage": "cn_etf_liquidity_capacity_prescreen",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_liquidity_capacity",
        "data_root": str(data_root),
        "metadata_root": str(metadata_root),
        "legacy_promotion_report": str(legacy_report),
        "analysis_start_date": "2024-01-02",
        "analysis_end_date": "2024-12-31",
        "candidate_names": [
            "etf_amihud_improvement_5_60",
            "etf_amount_participation_breadth_20_60",
            "etf_amount_distribution_quality_20",
        ],
        "reference_names": [
            "liquidity_5",
            "liquidity_10",
            "liquidity_20",
            "liquidity_60",
            "liquidity_resilience_60",
            "amount_stability_20",
            "amount_stability_60",
            "average_amount_20",
            "average_amount_60",
            "volume_change_20",
            "volume_change_60",
            "demand_pressure_60",
            "quiet_accumulation_60",
        ],
        "horizons": [5, 20],
        "execution_lag": 1,
        "eligibility": {
            "point_in_time": True,
            "official_etf_only": True,
            "min_prior_observations": 20,
            "liquidity_window": 5,
            "min_trailing_median_amount": 1.0,
            "max_stale_rate": 1.0,
            "max_abs_return": 1.0,
        },
        "thresholds": {
            "alpha": 0.05,
            "min_cross_section": 5,
            "min_ic_observations": 5,
            "min_year_ic_observations": 2,
            "min_usable_years": 1,
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
        "zero_lead_decision": {
            "closed_family": "cn_etf_liquidity_capacity",
            "closed_budget_share": 0.35,
            "resulting_budget_shares": {
                "cn_etf_volatility_regime": 0.35,
                "cn_etf_flow_breadth_aggregation": 0.35,
                "cn_etf_fund_structure": 0.30,
            },
        },
        "output_dir": str(output_dir),
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
