import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.industry_style_exposure_audit import (
    build_industry_style_exposure_audit,
    render_industry_style_exposure_audit_markdown,
    write_industry_style_exposure_audit,
)


class IndustryStyleExposureAuditTests(unittest.TestCase):
    def test_allows_candidate_when_residual_ic_survives_industry_and_styles(self) -> None:
        factors, labels, stock_basic, styles = _sample_frames(include_all_styles=True)

        audit = build_industry_style_exposure_audit(
            factors=factors,
            labels=labels,
            stock_basic=stock_basic,
            style_factors=styles,
            min_dates=6,
            min_cross_section=12,
            min_residual_mean_ic=0.05,
            min_residual_ic_t_stat=1.0,
            min_residual_positive_rate=0.60,
        )

        self.assertTrue(audit["summary"]["passes"])
        self.assertEqual(audit["summary"]["residual_candidate_factors"], 1)
        self.assertEqual(audit["summary"]["missing_required_style_names"], [])
        self.assertGreater(audit["summary"]["residual_factor_rows"], 70)
        row = audit["factor_summary"][0]
        self.assertEqual(row["classification"], "residual_candidate")
        self.assertGreater(row["mean_residual_rank_ic"], 0.05)
        self.assertGreater(row["residual_positive_ic_rate"], 0.60)
        self.assertTrue(audit["promotion_policy"]["portfolio_grid_allowed_after_audit"])

    def test_blocks_missing_style_and_industry_coverage_before_portfolio_grid(self) -> None:
        factors, labels, stock_basic, styles = _sample_frames(include_all_styles=False)
        stock_basic = stock_basic[stock_basic["asset_id"].isin(["CN_000001", "CN_000002"])].copy()

        audit = build_industry_style_exposure_audit(
            factors=factors,
            labels=labels,
            stock_basic=stock_basic,
            style_factors=styles,
            min_dates=6,
            min_cross_section=12,
            min_style_coverage_ratio=0.95,
            max_missing_industry_fraction=0.05,
        )

        self.assertFalse(audit["summary"]["passes"])
        self.assertIn("missing_required_style_names", audit["summary"]["blockers"])
        self.assertIn("industry_coverage_below_threshold", audit["summary"]["blockers"])
        self.assertFalse(audit["promotion_policy"]["portfolio_grid_allowed_after_audit"])

    def test_write_outputs(self) -> None:
        factors, labels, stock_basic, styles = _sample_frames(include_all_styles=True)
        audit = build_industry_style_exposure_audit(
            factors=factors,
            labels=labels,
            stock_basic=stock_basic,
            style_factors=styles,
            min_dates=6,
            min_cross_section=12,
            min_residual_mean_ic=0.05,
            min_residual_ic_t_stat=1.0,
            min_residual_positive_rate=0.60,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "audit"

            write_industry_style_exposure_audit(output_dir, audit)

            self.assertTrue((output_dir / "industry_style_exposure_audit.json").exists())
            self.assertTrue((output_dir / "industry_style_exposure_audit.md").exists())
            self.assertTrue((output_dir / "factor_summary.csv").exists())
            self.assertTrue((output_dir / "style_exposure_rows.csv").exists())
            self.assertTrue((output_dir / "industry_date_rows.csv").exists())
            self.assertTrue((output_dir / "residual_factor_rows.csv").exists())
            markdown = render_industry_style_exposure_audit_markdown(audit)
            self.assertIn("Industry/Style Exposure Audit", markdown)
            self.assertIn("Residual candidate factors: 1", markdown)


def _sample_frames(*, include_all_styles: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range("2024-01-02", periods=8, freq="B")
    assets = [f"CN_{idx:06d}" for idx in range(1, 13)]
    industries = {
        asset: ["bank", "tech", "consumer"][idx % 3]
        for idx, asset in enumerate(assets)
    }
    factor_rows = []
    label_rows = []
    style_rows = []
    for date_idx, date_value in enumerate(dates):
        for asset_idx, asset_id in enumerate(assets):
            independent = float((asset_idx * 5 + date_idx * 3) % 13)
            size = float(asset_idx)
            value = float(12 - asset_idx)
            lowvol = float((asset_idx + date_idx) % 5)
            momentum = float((asset_idx * 2 + date_idx) % 7)
            liquidity = float((asset_idx * 3 + date_idx) % 11)
            signal = independent + 0.35 * size - 0.20 * value
            forward_return = independent * 0.01 + (asset_idx % 3) * 0.0001
            factor_rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "profitability_revision_quality_20",
                    "factor_value": signal,
                }
            )
            label_rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "market": "CN",
                    "forward_return": forward_return,
                    "horizon": 20,
                    "execution_lag": 1,
                }
            )
            style_values = {
                "size": size,
                "value": value,
                "lowvol": lowvol,
                "momentum": momentum,
                "liquidity": liquidity,
            }
            if not include_all_styles:
                style_values.pop("liquidity")
            for style_name, style_value in style_values.items():
                style_rows.append(
                    {
                        "date": date_value,
                        "asset_id": asset_id,
                        "market": "CN",
                        "style_name": style_name,
                        "style_value": style_value,
                    }
                )
    stock_basic = pd.DataFrame(
        [{"asset_id": asset_id, "industry": industry} for asset_id, industry in industries.items()]
    )
    return (
        pd.DataFrame(factor_rows),
        pd.DataFrame(label_rows),
        stock_basic,
        pd.DataFrame(style_rows),
    )


if __name__ == "__main__":
    unittest.main()
