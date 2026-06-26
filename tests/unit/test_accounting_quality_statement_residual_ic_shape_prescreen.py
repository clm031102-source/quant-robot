import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.accounting_quality_statement_residual_ic_shape_prescreen import (
    build_accounting_quality_statement_directional_audit_factor_frame,
    build_accounting_quality_statement_event_drift_factor_frame,
    build_accounting_quality_statement_industry_relative_surprise_factor_frame,
    build_accounting_quality_statement_residual_ic_shape_prescreen,
    build_accounting_quality_statement_repaired_factor_frame,
    summarize_accounting_quality_statement_residual_ic_shape_prescreen,
)
from quant_robot.storage.dataset_store import DatasetStore


class AccountingQualityStatementResidualIcShapePrescreenTests(unittest.TestCase):
    def test_summarize_runs_neutral_ic_shape_without_promotion(self) -> None:
        factor_frame, labels, stock_basic = _neutral_frames()

        result = summarize_accounting_quality_statement_residual_ic_shape_prescreen(
            factor_frame,
            labels,
            stock_basic,
            expected_candidate_count=1,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_neutral_ic_t_stat=0.0,
        )

        self.assertEqual(result["stage"], "accounting_quality_statement_residual_ic_shape_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertGreaterEqual(result["summary"]["research_lead_count"], 1)
        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["mean_industry_neutral_rank_ic"], 0.8)
        self.assertGreater(row["mean_size_neutral_rank_ic"], 0.8)
        self.assertGreater(row["mean_liquidity_neutral_rank_ic"], 0.8)
        self.assertFalse(row["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])

    def test_builds_prescreen_from_statement_roots_and_context_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["stage"], "accounting_quality_statement_residual_ic_shape_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 5)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["aligned_rows"], 0)
        self.assertGreater(result["summary"]["test_count"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_builds_repaired_mode_prescreen_from_statement_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="repaired",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "repaired")
        self.assertEqual(result["summary"]["candidate_count"], 3)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_accruals_cashflow_quality_repaired",
        )

    def test_builds_new_substructure_mode_without_old_raw_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="new_substructure",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "new_substructure")
        self.assertEqual(result["summary"]["candidate_count"], 2)
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_quality_new_substructure",
        )
        tested_names = {row["factor_name"] for row in result["results"]}
        self.assertEqual(
            tested_names,
            {
                "aq_abnormal_accrual_change_reversal",
                "aq_balance_sheet_stress_relief",
            },
        )
        self.assertFalse(any(name.endswith("_raw") for name in tested_names))
        self.assertEqual(
            result["summary"]["next_direction"],
            "round245_accounting_quality_new_substructure_directional_audit_or_family_rotation",
        )
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_directional_audit_factor_frame_inverts_only_preregistered_source(self) -> None:
        signal_date = pd.Timestamp("2024-05-06")
        raw_factor_frame = pd.DataFrame(
            [
                {
                    "date": signal_date,
                    "ann_date": signal_date - pd.Timedelta(days=2),
                    "end_date": signal_date - pd.Timedelta(days=40),
                    "signal_date": signal_date,
                    "asset_id": "CN_XSHE_000001",
                    "market": "CN",
                    "factor_name": "aq_abnormal_accrual_change_reversal",
                    "factor_value": 1.25,
                    "log_circ_mv": 20.0,
                },
                {
                    "date": signal_date,
                    "ann_date": signal_date - pd.Timedelta(days=2),
                    "end_date": signal_date - pd.Timedelta(days=40),
                    "signal_date": signal_date,
                    "asset_id": "CN_XSHE_000001",
                    "market": "CN",
                    "factor_name": "aq_balance_sheet_stress_relief",
                    "factor_value": 9.0,
                    "log_circ_mv": 20.0,
                },
            ]
        )

        audit_frame = build_accounting_quality_statement_directional_audit_factor_frame(raw_factor_frame)

        self.assertEqual(
            set(audit_frame["factor_name"]),
            {"aq_abnormal_accrual_change_reversal_sign_flip_audit"},
        )
        self.assertEqual(len(audit_frame), 1)
        self.assertAlmostEqual(float(audit_frame.iloc[0]["factor_value"]), -1.25)
        self.assertEqual(audit_frame.iloc[0]["asset_id"], "CN_XSHE_000001")
        self.assertTrue((audit_frame["signal_date"] > audit_frame["ann_date"]).all())

    def test_builds_directional_audit_mode_as_single_preregistered_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="new_substructure_directional_audit",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "new_substructure_directional_audit")
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_quality_new_substructure_directional_audit",
        )
        tested_names = {row["factor_name"] for row in result["results"]}
        self.assertEqual(tested_names, {"aq_abnormal_accrual_change_reversal_sign_flip_audit"})
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_event_drift_factor_frame_combines_cash_conversion_with_muted_reaction(self) -> None:
        raw_factor_frame, bars = _event_drift_input_frames()

        event_frame = build_accounting_quality_statement_event_drift_factor_frame(raw_factor_frame, bars)

        self.assertEqual(set(event_frame["factor_name"]), {"aq_cash_conversion_muted_reaction_drift"})
        self.assertEqual(len(event_frame), 2)
        self.assertTrue((event_frame["signal_date"] > event_frame["ann_date"]).all())
        self.assertTrue(event_frame["factor_value"].notna().all())
        by_asset = event_frame.set_index("asset_id")["factor_value"]
        self.assertGreater(by_asset["CN_XSHE_000001"], by_asset["CN_XSHE_000002"])
        self.assertIn("announcement_reaction", event_frame.columns)

    def test_builds_statement_event_drift_mode_as_single_preregistered_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="statement_event_drift",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "statement_event_drift")
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_quality_statement_event_drift",
        )
        tested_names = {row["factor_name"] for row in result["results"]}
        self.assertEqual(tested_names, {"aq_cash_conversion_muted_reaction_drift"})
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_builds_statement_profitability_revision_mode_without_old_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="statement_profitability_revision",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "statement_profitability_revision")
        self.assertEqual(result["summary"]["candidate_count"], 2)
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_quality_statement_profitability_revision",
        )
        tested_names = {row["factor_name"] for row in result["results"]}
        self.assertEqual(
            tested_names,
            {
                "aq_profitability_revision_cash_confirmed",
                "aq_profitability_revision_asset_disciplined",
            },
        )
        self.assertFalse(any(name.endswith("_raw") for name in tested_names))
        self.assertEqual(
            result["summary"]["next_direction"],
            "round248_rotate_to_external_revision_or_nonfinancial_event_context",
        )
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_repaired_factor_frame_uses_industry_relative_and_residual_composites(self) -> None:
        raw_factor_frame, stock_basic = _repair_input_frames()

        repaired = build_accounting_quality_statement_repaired_factor_frame(
            raw_factor_frame,
            stock_basic,
            min_cross_section=6,
        )

        expected_names = {
            "aq_repaired_industry_relative_cash_accrual_quality",
            "aq_repaired_size_liquidity_residual_asset_growth_quality",
            "aq_repaired_balanced_cash_asset_quality",
        }
        self.assertEqual(set(repaired["factor_name"].unique()), expected_names)
        self.assertTrue((repaired["date"] == repaired["signal_date"]).all())
        self.assertTrue((repaired["signal_date"] > repaired["ann_date"]).all())
        self.assertFalse(any(name.endswith("_raw") for name in repaired["factor_name"].unique()))
        self.assertGreater(repaired["factor_value"].notna().sum(), 0)

    def test_industry_relative_surprise_factor_frame_uses_only_new_candidates(self) -> None:
        raw_factor_frame, stock_basic = _repair_input_frames()

        surprise = build_accounting_quality_statement_industry_relative_surprise_factor_frame(
            raw_factor_frame,
            stock_basic,
            min_cross_section=6,
        )

        expected_names = {
            "aq_industry_relative_profitability_surprise",
            "aq_industry_relative_asset_disciplined_surprise",
            "aq_industry_relative_cash_conversion_surprise",
        }
        self.assertEqual(set(surprise["factor_name"].unique()), expected_names)
        self.assertTrue((surprise["date"] == surprise["signal_date"]).all())
        self.assertTrue((surprise["signal_date"] > surprise["ann_date"]).all())
        self.assertFalse(any(name.endswith("_raw") for name in surprise["factor_name"].unique()))
        self.assertGreater(surprise["factor_value"].notna().sum(), 0)

    def test_builds_industry_relative_surprise_mode_without_old_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            assets = [f"CN_XSHE_{index:06d}" for index in range(8)]
            _write_statement_inputs(statement_root, _statement_rows(assets))
            _write_bars(bars_root, _bar_rows(assets))
            _write_daily_basic(daily_basic_root, assets)
            _write_stock_basic(stock_basic_root, assets)

            result = build_accounting_quality_statement_residual_ic_shape_prescreen(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                factor_mode="industry_relative_surprise",
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["factor_mode"], "industry_relative_surprise")
        self.assertEqual(result["summary"]["candidate_count"], 3)
        self.assertEqual(
            result["source_context"]["candidate_family"],
            "accounting_quality_industry_relative_surprise",
        )
        tested_names = {row["factor_name"] for row in result["results"]}
        self.assertEqual(
            tested_names,
            {
                "aq_industry_relative_profitability_surprise",
                "aq_industry_relative_asset_disciplined_surprise",
                "aq_industry_relative_cash_conversion_surprise",
            },
        )
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


def _neutral_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-03", periods=8)
    factor_rows = []
    label_rows = []
    stock_rows = []
    for asset_idx in range(20):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        industry = "Tech" if asset_idx < 10 else "Bank"
        stock_rows.append({"asset_id": asset_id, "industry": industry})
    for date_idx, signal_date in enumerate(dates):
        for asset_idx in range(20):
            asset_id = f"CN_XSHE_{asset_idx:06d}"
            within_industry_rank = asset_idx % 10
            factor_value = float(within_industry_rank)
            factor_rows.append(
                {
                    "date": signal_date,
                    "ann_date": signal_date - pd.Timedelta(days=1),
                    "end_date": signal_date - pd.Timedelta(days=30),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "low_total_accruals_to_assets_raw",
                    "factor_value": factor_value,
                    "amount": 20_000_000 + (asset_idx % 5) * 1_000_000,
                    "adv20_amount": 20_000_000 + (asset_idx // 2) * 1_000_000,
                    "log_adv20": 16.0 + (asset_idx // 2) * 0.01,
                    "log_circ_mv": 20.0 + (asset_idx // 2) * 0.01,
                    "turnover_rate_f": 1.0 + (asset_idx % 4) * 0.01,
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 5,
                    "execution_lag": 1,
                    "forward_return": factor_value / 100.0 + date_idx * 0.0001,
                    "entry_date": signal_date + pd.Timedelta(days=1),
                    "exit_date": signal_date + pd.Timedelta(days=6),
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(stock_rows)


def _repair_input_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    signal_date = pd.Timestamp("2024-05-06")
    raw_names = [
        "low_total_accruals_to_assets_raw",
        "cashflow_minus_netprofit_to_assets_raw",
        "low_asset_growth_quality_raw",
        "working_capital_accruals_to_assets_raw",
        "earnings_cash_conversion_improvement_yoy_raw",
        "aq_profitability_revision_cash_confirmed",
        "aq_profitability_revision_asset_disciplined",
    ]
    rows = []
    stock_rows = []
    for asset_index in range(12):
        asset_id = f"CN_XSHE_{asset_index:06d}"
        industry = "Tech" if asset_index < 6 else "Bank"
        stock_rows.append({"asset_id": asset_id, "industry": industry})
        base = float(asset_index % 6)
        values = {
            "low_total_accruals_to_assets_raw": -base,
            "cashflow_minus_netprofit_to_assets_raw": base,
            "low_asset_growth_quality_raw": base * 0.5,
            "working_capital_accruals_to_assets_raw": -base * 0.25,
            "earnings_cash_conversion_improvement_yoy_raw": base * 0.75,
            "aq_profitability_revision_cash_confirmed": base * 1.25,
            "aq_profitability_revision_asset_disciplined": base * 0.9,
        }
        for name in raw_names:
            rows.append(
                {
                    "date": signal_date,
                    "ann_date": signal_date - pd.Timedelta(days=3),
                    "end_date": signal_date - pd.Timedelta(days=35),
                    "signal_date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": name,
                    "factor_value": values[name],
                    "log_circ_mv": 20.0 + asset_index * 0.05,
                    "log_adv20": 16.0 + asset_index * 0.03,
                    "turnover_rate_f": 1.0 + (asset_index % 4) * 0.1,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(stock_rows)


def _event_drift_input_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    ann_date = pd.Timestamp("2024-05-03")
    signal_date = pd.Timestamp("2024-05-06")
    factor_rows = [
        {
            "date": signal_date,
            "ann_date": ann_date,
            "end_date": pd.Timestamp("2024-03-31"),
            "signal_date": signal_date,
            "asset_id": "CN_XSHE_000001",
            "market": "CN",
            "factor_name": "earnings_cash_conversion_improvement_yoy_raw",
            "factor_value": 2.0,
            "log_circ_mv": 20.0,
            "log_adv20": 16.0,
            "turnover_rate_f": 1.0,
        },
        {
            "date": signal_date,
            "ann_date": ann_date,
            "end_date": pd.Timestamp("2024-03-31"),
            "signal_date": signal_date,
            "asset_id": "CN_XSHE_000002",
            "market": "CN",
            "factor_name": "earnings_cash_conversion_improvement_yoy_raw",
            "factor_value": 1.0,
            "log_circ_mv": 20.5,
            "log_adv20": 16.5,
            "turnover_rate_f": 1.5,
        },
        {
            "date": signal_date,
            "ann_date": ann_date,
            "end_date": pd.Timestamp("2024-03-31"),
            "signal_date": signal_date,
            "asset_id": "CN_XSHE_000001",
            "market": "CN",
            "factor_name": "low_asset_growth_quality_raw",
            "factor_value": 99.0,
        },
    ]
    bars = pd.DataFrame(
        [
            {"date": pd.Timestamp("2024-05-02"), "asset_id": "CN_XSHE_000001", "market": "CN", "adj_close": 10.0},
            {"date": signal_date, "asset_id": "CN_XSHE_000001", "market": "CN", "adj_close": 10.1},
            {"date": pd.Timestamp("2024-05-02"), "asset_id": "CN_XSHE_000002", "market": "CN", "adj_close": 20.0},
            {"date": signal_date, "asset_id": "CN_XSHE_000002", "market": "CN", "adj_close": 24.0},
        ]
    )
    return pd.DataFrame(factor_rows), bars


def _statement_rows(asset_ids: list[str]) -> pd.DataFrame:
    rows = []
    periods = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31", "2024-03-31"])
    for asset_index, asset_id in enumerate(asset_ids):
        for period_index, end_date in enumerate(periods):
            rows.append(
                {
                    "date": end_date,
                    "asset_id": asset_id,
                    "symbol": asset_id[-6:] + ".SZ",
                    "market": "CN",
                    "ann_date": end_date + pd.Timedelta(days=30),
                    "end_date": end_date,
                    "report_type": "1",
                    "netprofit": 100.0 + asset_index * 10 + period_index,
                    "n_cashflow_act": 120.0 + asset_index * 12 + period_index * 2,
                    "total_assets": 1000.0 + asset_index * 100 + period_index * 10,
                    "total_liab": 400.0 + asset_index * 10,
                    "total_cur_assets": 300.0 + period_index * 5 + asset_index,
                    "total_cur_liab": 180.0 + period_index * 2,
                }
            )
    return pd.DataFrame(rows)


def _bar_rows(asset_ids: list[str]) -> pd.DataFrame:
    dates = pd.bdate_range("2023-04-03", "2024-08-30")
    rows = []
    for asset_index, asset_id in enumerate(asset_ids):
        price = 10.0 + asset_index
        for date_index, day in enumerate(dates):
            price += 0.01 + asset_index * 0.001
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 20_000_000 + asset_index * 1_000_000 + date_index * 1000,
                }
            )
    return pd.DataFrame(rows)


def _write_statement_inputs(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/financial_statement_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )


def _write_bars(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(frame, "processed/bars", {"frequency": "1d", "market": "CN", "year": "2024"})


def _write_daily_basic(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2023-04-03", "2024-08-30")
    rows = []
    for asset_index, asset_id in enumerate(asset_ids):
        for day in dates:
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "turnover_rate": 0.8 + (asset_index % 3) * 0.1,
                    "turnover_rate_f": 1.0 + (asset_index % 3) * 0.1,
                    "volume_ratio": 1.2 + (asset_index % 2) * 0.1,
                    "total_mv": 10_000_000 + asset_index * 100_000,
                    "circ_mv": 8_000_000 + asset_index * 100_000,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_stock_basic(root: Path, asset_ids: list[str]) -> None:
    rows = []
    for asset_index, asset_id in enumerate(asset_ids):
        rows.append(
            {
                "asset_id": asset_id,
                "market": "CN",
                "industry": "Tech" if asset_index < len(asset_ids) // 2 else "Bank",
            }
        )
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(root / "stock_basic.csv", index=False)


if __name__ == "__main__":
    unittest.main()
