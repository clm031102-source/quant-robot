import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.industry_breadth_bridge_audit import (
    build_industry_breadth_bridge_audit,
    render_industry_breadth_bridge_markdown,
    write_industry_breadth_bridge_audit,
)


class IndustryBreadthBridgeAuditTests(unittest.TestCase):
    def test_classifies_factor_as_bridge_candidate_when_industry_breadth_leads_returns(self):
        factors, labels, stock_basic = _bridge_candidate_inputs()

        audit = build_industry_breadth_bridge_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic_bridge",
            top_industries=1,
            min_assets_per_industry=2,
            min_industries_per_date=2,
            min_dates=6,
            min_mean_excess_return=0.0,
            min_excess_t_stat=2.0,
            min_positive_excess_rate=0.8,
            min_industry_rank_ic=0.2,
            min_rank_ic_t_stat=2.0,
        )

        self.assertEqual(audit["summary"]["factors"], 1)
        self.assertEqual(audit["summary"]["industry_breadth_bridge_candidate_factors"], 1)
        self.assertIn("map_industry_signal_to_liquid_etf_or_theme_universe", audit["recommended_next_actions"])

        row = audit["factor_summary"][0]
        self.assertEqual(row["factor_name"], "known_industry_breadth_factor")
        self.assertEqual(row["classification"], "industry_breadth_bridge_candidate")
        self.assertGreater(row["mean_industry_rank_ic"], 0.8)
        self.assertGreater(row["mean_top_industry_excess_return"], 0.0)
        self.assertEqual(row["positive_excess_rate"], 1.0)

    def test_rejects_factor_when_industry_breadth_does_not_translate_to_returns(self):
        factors, labels, stock_basic = _weak_bridge_inputs()

        audit = build_industry_breadth_bridge_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic_weak_bridge",
            top_industries=1,
            min_assets_per_industry=2,
            min_industries_per_date=2,
            min_dates=6,
        )

        self.assertEqual(audit["summary"]["industry_breadth_bridge_candidate_factors"], 0)
        self.assertEqual(audit["summary"]["weak_or_unproven_bridge_factors"], 1)

        row = audit["factor_summary"][0]
        self.assertEqual(row["classification"], "weak_or_unproven_bridge")
        self.assertLess(row["mean_top_industry_excess_return"], 0.0)

    def test_writer_emits_json_markdown_and_csvs(self):
        factors, labels, stock_basic = _bridge_candidate_inputs()
        audit = build_industry_breadth_bridge_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic",
            top_industries=1,
            min_assets_per_industry=2,
            min_industries_per_date=2,
            min_dates=6,
        )

        markdown = render_industry_breadth_bridge_markdown(audit)

        self.assertIn("Industry-Breadth Bridge Audit", markdown)
        self.assertIn("industry_breadth_bridge_candidate", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            write_industry_breadth_bridge_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "industry_breadth_bridge_audit.json").exists())
            self.assertTrue((Path(tmp) / "industry_breadth_bridge_audit.md").exists())
            self.assertTrue((Path(tmp) / "date_audits.csv").exists())
            self.assertTrue((Path(tmp) / "factor_summary.csv").exists())

    def test_rebalance_interval_samples_signal_dates(self):
        factors, labels, stock_basic = _bridge_candidate_inputs()

        audit = build_industry_breadth_bridge_audit(
            factors,
            labels,
            stock_basic,
            source_report="synthetic_rebalance",
            top_industries=1,
            min_assets_per_industry=2,
            min_industries_per_date=2,
            rebalance_interval=2,
        )

        self.assertEqual(audit["summary"]["date_factor_rows"], 4)
        self.assertEqual(audit["factor_summary"][0]["dates"], 4)


def _bridge_candidate_inputs():
    return _inputs(reverse_returns=False)


def _weak_bridge_inputs():
    return _inputs(reverse_returns=True)


def _inputs(*, reverse_returns: bool):
    factor_rows = []
    label_rows = []
    industries = {
        "leader": (0.90, 0.04),
        "middle": (0.50, 0.01),
        "laggard": (0.10, -0.02),
    }
    if reverse_returns:
        industries = {
            name: (factor_value, -forward_return)
            for name, (factor_value, forward_return) in industries.items()
        }
    for day in pd.date_range("2024-01-02", periods=8, freq="D"):
        for industry, (factor_value, forward_return) in industries.items():
            for asset_index in range(3):
                asset_id = f"{industry}_{asset_index}"
                factor_rows.append(
                    {
                        "date": day.date(),
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "known_industry_breadth_factor",
                        "factor_value": factor_value + asset_index * 0.01,
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
    stock_basic = pd.DataFrame(
        [
            {"asset_id": f"{industry}_{asset_index}", "industry": industry}
            for industry in industries
            for asset_index in range(3)
        ]
    )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), stock_basic


if __name__ == "__main__":
    unittest.main()
