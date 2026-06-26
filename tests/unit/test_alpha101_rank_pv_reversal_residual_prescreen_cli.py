import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_alpha101_rank_pv_reversal_residual_prescreen import (
    run_alpha101_rank_pv_reversal_residual_prescreen_cli,
)


def _synthetic_bars(days: int = 95, assets: int = 38) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.04
        for day_idx, signal_date in enumerate(dates):
            price = max(1.0, price * (1.0 + ((day_idx % 11) - 5) * 0.001 + (asset_idx % 6) * 0.0004))
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "open": price * 0.995,
                    "high": price * 1.015,
                    "low": price * 0.985,
                    "adj_close": price,
                    "amount": 60_000_000 + asset_idx * 80_000 + day_idx * 1_000,
                }
            )
    return pd.DataFrame(rows)


class Alpha101RankPvReversalResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_residual_audit_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_path = Path(tmp) / "bars.parquet"
            factor_input_path = Path(tmp) / "factor_inputs.parquet"
            moneyflow_input_path = Path(tmp) / "moneyflow_inputs.parquet"
            round129_report_path = Path(tmp) / "round129.json"
            output = Path(tmp) / "output"

            bars = _synthetic_bars()
            bars.to_parquet(bars_path, index=False)
            aux = bars[["date", "asset_id", "market"]].copy()
            aux["pe_ttm"] = 20.0
            aux["pb"] = 2.0
            aux["dv_ttm"] = 1.0
            aux["turnover_rate_f"] = 1.5
            aux["circ_mv"] = 2_000_000.0
            aux.to_parquet(factor_input_path, index=False)
            flow = bars[["date", "asset_id", "market"]].copy()
            flow["buy_lg_amount"] = 1_000_000.0
            flow["sell_lg_amount"] = 900_000.0
            flow["buy_elg_amount"] = 500_000.0
            flow["sell_elg_amount"] = 450_000.0
            flow["net_mf_amount"] = 150_000.0
            flow.to_parquet(moneyflow_input_path, index=False)
            round129_report_path.write_text(
                json.dumps(
                    {
                        "stage": "alpha101_rank_pv_reversal_reference_dedup",
                        "summary": {
                            "reference_highly_redundant_count": 3,
                            "reference_moderately_redundant_count": 4,
                        },
                        "gate": {"blockers": ["lead_highly_redundant_with_reference_factor"]},
                        "next_direction": "round130_alpha101_rank_pv_reversal_hibernate_or_orthogonalize_after_dedup",
                    }
                ),
                encoding="utf-8",
            )

            result = run_alpha101_rank_pv_reversal_residual_prescreen_cli(
                bars_path=bars_path,
                factor_input_path=factor_input_path,
                moneyflow_input_path=moneyflow_input_path,
                round129_report=round129_report_path,
                output_dir=output,
                analysis_end_date="2024-12-31",
                min_cross_section=20,
                min_ic_observations=5,
            )

            self.assertEqual(result["stage"], "alpha101_rank_pv_reversal_residual_prescreen")
            self.assertTrue((output / "alpha101_rank_pv_reversal_residual_prescreen.json").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_residual_prescreen.md").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_residual_ic_observations.csv").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_residual_yearly_ic.csv").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_residual_diagnostics.csv").exists())
            payload = json.loads(
                (output / "alpha101_rank_pv_reversal_residual_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["residual_factor_name"], "alpha101_rank_pv_reversal_residual_vs_pv_cluster_20")
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
