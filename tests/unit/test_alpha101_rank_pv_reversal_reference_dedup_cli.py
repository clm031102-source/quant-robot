import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_alpha101_rank_pv_reversal_reference_dedup import (
    run_alpha101_rank_pv_reversal_reference_dedup_cli,
)


def _synthetic_bars(days: int = 95, assets: int = 38) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.04
        for day_idx, date in enumerate(dates):
            price = max(1.0, price * (1.0 + ((day_idx % 11) - 5) * 0.001 + (asset_idx % 6) * 0.0004))
            rows.append(
                {
                    "date": date,
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


class Alpha101RankPvReversalReferenceDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_audit_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_path = Path(tmp) / "bars.parquet"
            factor_input_path = Path(tmp) / "factor_inputs.parquet"
            moneyflow_input_path = Path(tmp) / "moneyflow_inputs.parquet"
            prescreen_path = Path(tmp) / "round128.json"
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
            prescreen_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "factor_name": "alpha101_rank_pv_reversal_liquid_20",
                                "horizon": 20,
                                "research_lead": True,
                            }
                        ],
                        "summary": {"research_lead_count": 3, "candidate_count": 20, "result_count": 60},
                    }
                ),
                encoding="utf-8",
            )

            result = run_alpha101_rank_pv_reversal_reference_dedup_cli(
                bars_path=bars_path,
                factor_input_path=factor_input_path,
                moneyflow_input_path=moneyflow_input_path,
                prescreen_report=prescreen_path,
                output_dir=output,
                analysis_end_date="2024-12-31",
                sample_every_n_dates=3,
                min_cross_section=20,
                min_ic_observations=5,
            )

            self.assertEqual(result["stage"], "alpha101_rank_pv_reversal_reference_dedup")
            self.assertTrue((output / "alpha101_rank_pv_reversal_reference_dedup.json").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_reference_dedup.md").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_reference_correlations.csv").exists())
            self.assertTrue((output / "alpha101_rank_pv_reversal_yearly_ic.csv").exists())
            payload = json.loads(
                (output / "alpha101_rank_pv_reversal_reference_dedup.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["lead_factor_name"], "alpha101_rank_pv_reversal_liquid_20")
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
