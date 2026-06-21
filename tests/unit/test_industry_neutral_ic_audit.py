import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.industry_neutral_ic_audit import (
    build_industry_neutral_ic_audit,
    render_industry_neutral_ic_markdown,
    write_industry_neutral_ic_audit,
)


class IndustryNeutralIcAuditTests(unittest.TestCase):
    def test_flags_industry_exposure_dominated_signal(self):
        factors, labels, stock_basic = _industry_exposure_dominated_inputs()

        audit = build_industry_neutral_ic_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic_industry_beta",
            min_overall_rank_ic=0.2,
            min_neutral_rank_ic=0.2,
            min_rank_ic_t_stat=2.0,
            min_industry_rank_ic=0.2,
        )

        self.assertEqual(audit["summary"]["factors"], 1)
        self.assertEqual(audit["summary"]["industry_exposure_dominated_factors"], 1)
        self.assertEqual(audit["summary"]["industry_neutral_signal_factors"], 0)
        self.assertIn("stock_to_etf_or_industry_breadth_bridge", audit["recommended_next_actions"])
        self.assertIn("industry_neutral_sort_before_portfolio_test", audit["recommended_next_actions"])

        row = audit["factor_summary"][0]
        self.assertEqual(row["factor_name"], "industry_beta_factor")
        self.assertEqual(row["classification"], "industry_exposure_dominated")
        self.assertGreater(row["mean_overall_rank_ic"], 0.8)
        self.assertGreater(row["mean_industry_rank_ic"], 0.8)
        self.assertLess(abs(row["mean_neutral_rank_ic"]), 0.2)

    def test_keeps_signal_when_rank_ic_survives_within_industry(self):
        factors, labels, stock_basic = _industry_neutral_signal_inputs()

        audit = build_industry_neutral_ic_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic_industry_neutral",
            min_overall_rank_ic=0.2,
            min_neutral_rank_ic=0.2,
            min_rank_ic_t_stat=2.0,
            min_industry_rank_ic=0.2,
        )

        self.assertEqual(audit["summary"]["industry_neutral_signal_factors"], 1)
        self.assertEqual(audit["summary"]["industry_exposure_dominated_factors"], 0)
        self.assertIn("run_industry_neutral_portfolio_backtest", audit["recommended_next_actions"])

        row = audit["factor_summary"][0]
        self.assertEqual(row["classification"], "industry_neutral_signal")
        self.assertGreater(row["mean_overall_rank_ic"], 0.8)
        self.assertGreater(row["mean_neutral_rank_ic"], 0.8)
        self.assertGreater(row["neutral_retention_ratio"], 0.8)

    def test_writer_emits_json_markdown_and_csvs(self):
        factors, labels, stock_basic = _industry_neutral_signal_inputs()
        audit = build_industry_neutral_ic_audit(factors, labels, stock_basic)

        markdown = render_industry_neutral_ic_markdown(audit)

        self.assertIn("Industry-Neutral IC Audit", markdown)
        self.assertIn("industry_neutral_signal", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            write_industry_neutral_ic_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "industry_neutral_ic_audit.json").exists())
            self.assertTrue((Path(tmp) / "industry_neutral_ic_audit.md").exists())
            self.assertTrue((Path(tmp) / "date_audits.csv").exists())
            self.assertTrue((Path(tmp) / "factor_summary.csv").exists())


def _industry_exposure_dominated_inputs():
    rows = []
    label_rows = []
    for day in pd.date_range("2024-01-02", periods=8, freq="D"):
        for asset_id, industry, factor_value, forward_return in [
            ("tech_a", "Tech", 10.0, 0.10),
            ("tech_b", "Tech", 11.0, 0.10),
            ("bank_a", "Bank", 1.0, 0.00),
            ("bank_b", "Bank", 2.0, 0.00),
        ]:
            rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "industry_beta_factor",
                    "factor_value": factor_value,
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "execution_lag": 1,
                    "forward_return": forward_return,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(label_rows), _stock_basic()


def _industry_neutral_signal_inputs():
    rows = []
    label_rows = []
    for day in pd.date_range("2024-01-02", periods=8, freq="D"):
        for asset_id, industry, factor_value, forward_return in [
            ("tech_a", "Tech", 1.0, 0.01),
            ("tech_b", "Tech", 2.0, 0.04),
            ("bank_a", "Bank", 1.0, 0.01),
            ("bank_b", "Bank", 2.0, 0.04),
        ]:
            rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "industry_neutral_factor",
                    "factor_value": factor_value,
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "execution_lag": 1,
                    "forward_return": forward_return,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(label_rows), _stock_basic()


def _stock_basic():
    return pd.DataFrame(
        [
            {"asset_id": "tech_a", "industry": "Tech"},
            {"asset_id": "tech_b", "industry": "Tech"},
            {"asset_id": "bank_a", "industry": "Bank"},
            {"asset_id": "bank_b", "industry": "Bank"},
        ]
    )


if __name__ == "__main__":
    unittest.main()
