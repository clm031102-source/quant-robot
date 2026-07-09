import unittest
import json
import tempfile
from pathlib import Path

import pandas as pd

from quant_robot.ops import financial_pit_post_announcement_drift_preregistration as prereg
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_matrix_label_smoke import (
    build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke,
)
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_residual_prescreen import (
    build_financial_pit_post_announcement_gap_reversal_residual_prescreen,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke import (
    run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_cli,
)
from scripts.run_financial_pit_post_announcement_gap_reversal_residual_prescreen import (
    run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli,
)


class FinancialPitPostAnnouncementGapReversalStatementSourceTests(unittest.TestCase):
    def test_statement_source_adapter_creates_reaction_available_rows(self) -> None:
        self.assertTrue(hasattr(prereg, "build_pead_statement_financial_frame"))

        frame = prereg.build_pead_statement_financial_frame(_statement_rows(), _bar_rows())

        self.assertFalse(frame.empty)
        self.assertTrue({"ann_date", "end_date", "signal_date", "available_date", "netprofit_yoy"}.issubset(frame.columns))
        self.assertTrue((pd.to_datetime(frame["signal_date"]) > pd.to_datetime(frame["ann_date"])).all())
        self.assertTrue((pd.to_datetime(frame["date"]) == pd.to_datetime(frame["signal_date"])).all())
        self.assertFalse(frame["netprofit_yoy"].dropna().empty)

    def test_gap_reversal_matrix_accepts_statement_input_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            preregistration_json = root / "preregistration.json"
            _write_statement(financial_root, _statement_rows())
            _write_bars(bars_root, _bar_rows())
            preregistration_json.write_text(json.dumps(_stmt_preregistration()), encoding="utf-8")

            result = build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(
                financial_root=financial_root,
                financial_input_kind="statement",
                bars_roots=[bars_root],
                preregistration_json=preregistration_json,
                horizons=(5,),
                execution_lag=1,
                min_label_coverage=0.50,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["active_candidate_count"], 5)
            self.assertEqual(result["summary"]["unknown_active_candidate_count"], 0)
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)

    def test_gap_reversal_residual_accepts_statement_input_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            preregistration_json = root / "preregistration.json"
            statement = _statement_rows(assets=6)
            bars = _bar_rows(assets=6)
            asset_ids = statement["asset_id"].drop_duplicates().tolist()
            _write_statement(financial_root, statement)
            _write_bars(bars_root, bars)
            _write_daily_basic(daily_basic_root, asset_ids)
            _write_stock_basic(stock_basic_root, asset_ids)
            preregistration_json.write_text(json.dumps(_stmt_preregistration()), encoding="utf-8")

            result = build_financial_pit_post_announcement_gap_reversal_residual_prescreen(
                financial_root=financial_root,
                financial_input_kind="statement",
                bars_roots=[bars_root],
                preregistration_json=preregistration_json,
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-10.0,
                min_neutral_retention=0.0,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_residual_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 5)
            self.assertGreater(result["summary"]["factor_rows"], 0)
            self.assertGreater(result["summary"]["test_count"], 0)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["live_boundary_allowed"])

    def test_gap_reversal_cli_wires_statement_input_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            matrix_output = root / "matrix_output"
            residual_output = root / "residual_output"
            preregistration_json = root / "preregistration.json"
            statement = _statement_rows(assets=6)
            asset_ids = statement["asset_id"].drop_duplicates().tolist()
            _write_statement(financial_root, statement)
            _write_bars(bars_root, _bar_rows(assets=6))
            _write_daily_basic(daily_basic_root, asset_ids)
            _write_stock_basic(stock_basic_root, asset_ids)
            preregistration_json.write_text(json.dumps(_stmt_preregistration()), encoding="utf-8")

            matrix = run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_cli(
                financial_root=financial_root,
                financial_input_kind="statement",
                bars_roots=[bars_root],
                preregistration_json=preregistration_json,
                output_dir=matrix_output,
                horizons=(5,),
                min_label_coverage=0.50,
            )
            residual = run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli(
                financial_root=financial_root,
                financial_input_kind="statement",
                bars_roots=[bars_root],
                preregistration_json=preregistration_json,
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=residual_output,
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-10.0,
                min_neutral_retention=0.0,
            )

            self.assertEqual(matrix["financial_input_kind"], "statement")
            self.assertEqual(residual["financial_input_kind"], "statement")
            self.assertTrue((matrix_output / "financial_pit_post_announcement_gap_reversal_matrix_label_smoke.json").exists())
            self.assertTrue((residual_output / "financial_pit_post_announcement_gap_reversal_residual_prescreen.json").exists())


def _statement_rows(assets: int = 2) -> pd.DataFrame:
    rows = []
    periods = pd.period_range("2022Q1", "2023Q2", freq="Q")
    for asset_idx in range(assets):
        for period_idx, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=10 + asset_idx)
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": f"CN_XSHE_00000{asset_idx}",
                    "symbol": f"00000{asset_idx}.SZ",
                    "market": "CN",
                    "source": "fixture_statement",
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "netprofit": 100.0 + asset_idx * 10.0 + period_idx * 5.0,
                    "total_revenue": 500.0 + asset_idx * 20.0 + period_idx * 10.0,
                    "n_cashflow_act": 50.0 + period_idx,
                    "total_assets": 1000.0 + asset_idx * 100.0,
                }
            )
    return pd.DataFrame(rows)


def _bar_rows(assets: int = 2) -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2022-04-01", "2023-08-31")
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_00000{asset_idx}"
        for day_index, day in enumerate(dates):
            price = 10.0 + asset_idx + day_index * 0.01
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": price,
                    "close": price * 1.001,
                    "adj_close": price * 1.001,
                    "volume": 1000000 + day_index,
                    "amount": 20000000 + day_index * 1000,
                }
            )
    return pd.DataFrame(rows)


def _stmt_preregistration() -> dict:
    candidates = [
        "stmt_pead_gap_overreaction_reversal_1_5",
        "stmt_pead_gap_overreaction_reversal_low_liquidity_penalized_1_5",
        "stmt_pead_gap_overreaction_reversal_volume_confirmed_1_5",
        "stmt_pead_gap_overreaction_reversal_size_neutral_candidate_1_5",
        "stmt_pead_gap_overreaction_reversal_quality_conditioned_1_5",
    ]
    return {
        "candidates": [
            {
                "factor_name": name,
                "family": "pead_gap_reversal_statement_source_repair",
                "registration_status": "pre_registered",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            }
            for name in candidates
        ],
    }


def _write_statement(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/financial_statement_inputs",
        {"frequency": "1q", "market": "CN", "year": "fixture"},
    )


def _write_bars(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "fixture"},
    )


def _write_daily_basic(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2022-04-01", "2023-08-31")
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        for day in dates:
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "turnover_rate": 0.8 + (asset_idx % 3) * 0.1,
                    "turnover_rate_f": 1.0 + (asset_idx % 3) * 0.1,
                    "volume_ratio": 1.2 + (asset_idx % 2) * 0.1,
                    "total_mv": 10_000_000 + asset_idx * 100_000,
                    "circ_mv": 8_000_000 + asset_idx * 100_000,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "fixture"},
    )


def _write_stock_basic(root: Path, asset_ids: list[str]) -> None:
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        rows.append(
            {
                "asset_id": asset_id,
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "industry": "Tech" if asset_idx < len(asset_ids) // 2 else "Bank",
            }
        )
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(root / "stock_basic.csv", index=False)


if __name__ == "__main__":
    unittest.main()
