import tempfile
import unittest
import json
from pathlib import Path

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate
from quant_robot.ops.profitability_event_revision_controlled_ic_neutral_prescreen import (
    build_profitability_event_revision_controlled_ic_neutral_prescreen,
    summarize_profitability_event_revision_controlled_ic_neutral_prescreen,
)
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    write_profitability_event_revision_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore


class ProfitabilityEventRevisionControlledIcNeutralPrescreenTests(unittest.TestCase):
    def test_summarize_requires_industry_size_liquidity_neutral_pass(self) -> None:
        factor_frame, labels, stock_basic = _neutral_test_frames()

        result = summarize_profitability_event_revision_controlled_ic_neutral_prescreen(
            factor_frame,
            labels,
            stock_basic,
            expected_candidate_count=1,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_neutral_ic_t_stat=2.0,
        )

        self.assertEqual(result["stage"], "profitability_event_revision_controlled_ic_neutral_prescreen")
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["neutral_gate_pass_count"], 1)
        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["mean_industry_neutral_rank_ic"], 0.8)
        self.assertGreater(row["mean_size_neutral_rank_ic"], 0.8)
        self.assertGreater(row["mean_liquidity_neutral_rank_ic"], 0.8)
        self.assertFalse(row["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_static_round96_reference_correlation_blocks_research_lead(self) -> None:
        factor_frame, labels, stock_basic = _neutral_test_frames()
        reference = factor_frame[["date", "asset_id", "market", "factor_value"]].copy()
        reference = reference.rename(columns={"factor_value": "reference_factor_value"})
        reference["reference_factor_name"] = "fina_roe_level"

        result = summarize_profitability_event_revision_controlled_ic_neutral_prescreen(
            factor_frame,
            labels,
            stock_basic,
            reference_factor_frame=reference,
            expected_candidate_count=1,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_neutral_ic_t_stat=2.0,
            reference_high_corr_threshold=0.9,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertGreaterEqual(row["reference_max_abs_correlation"], 0.9)
        self.assertIn("high_correlation_with_round96_static_profitability", row["blockers"])
        self.assertEqual(result["summary"]["research_lead_count"], 0)

    def test_builds_round153_prescreen_from_preregistered_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            prereg_dir = root / "prereg"
            financial = _financial_rows(assets=6)
            _write_fina_indicator_inputs(financial_root, financial)
            _write_bars(bars_root, financial["asset_id"].unique().tolist())
            _write_daily_basic(daily_basic_root, financial["asset_id"].unique().tolist())
            _write_stock_basic(stock_basic_root, financial["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=6,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)
            gate = build_factor_mining_candidate_plan_gate(prereg, gate_stage="discovery")
            gate_path = root / "gate.json"
            gate_path.write_text(json.dumps(gate), encoding="utf-8")

            result = build_profitability_event_revision_controlled_ic_neutral_prescreen(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                candidate_plan_gate_json=gate_path,
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

        self.assertEqual(result["stage"], "profitability_event_revision_controlled_ic_neutral_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 7)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["test_count"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])


def _neutral_test_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
                    "factor_name": "pit_fina_neutral_quality_test",
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


def _financial_rows(assets: int) -> pd.DataFrame:
    rows = []
    periods = pd.period_range("2022Q1", "2024Q4", freq="Q")
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        for period_idx, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=30 + asset_idx)
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "tushare_fina_indicator",
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "roe": 8.0 + asset_idx + period_idx * 0.2,
                    "roa": 3.0 + asset_idx + period_idx * 0.1,
                    "grossprofit_margin": 20.0 + period_idx,
                    "netprofit_margin": 6.0 + period_idx * 0.5 + asset_idx * 0.1,
                    "netprofit_yoy": 5.0 + period_idx * 1.2 + asset_idx * 0.2,
                    "or_yoy": 4.0 + period_idx * 0.8 + asset_idx * 0.1,
                    "ocfps": 1.0 + period_idx * 0.1 + asset_idx * 0.01,
                    "cfps": 1.2 + period_idx * 0.1 + asset_idx * 0.01,
                }
            )
    return pd.DataFrame(rows)


def _write_fina_indicator_inputs(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )


def _write_bars(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2022-04-01", "2025-06-30")
    rows = []
    for asset_idx, asset_id in enumerate(asset_ids):
        price = 10.0 + asset_idx
        for index, day in enumerate(dates):
            price += 0.01 + asset_idx * 0.001
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 20_000_000 + asset_idx * 1_000_000 + index * 1000,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_daily_basic(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2022-04-01", "2025-06-30")
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
        {"frequency": "1d", "market": "CN", "year": "2024"},
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
