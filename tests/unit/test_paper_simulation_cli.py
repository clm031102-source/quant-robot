import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_paper_simulation import run_simulation


class PaperSimulationCliTests(unittest.TestCase):
    def test_run_simulation_writes_local_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_simulation(
                source="fixture",
                market="CN",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                rebalance_interval=2,
                start_date="2024-01-04",
                end_date="2024-01-10",
                output_dir=Path(tmp),
            )

            self.assertEqual(result["request"]["rebalance_interval"], 2)
            self.assertGreater(len(result["fills"]), 0)
            self.assertTrue((Path(tmp) / "intents.csv").exists())
            self.assertTrue((Path(tmp) / "fills.csv").exists())
            self.assertTrue((Path(tmp) / "equity_curve.csv").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())

    def test_run_simulation_supports_tushare_moneyflow_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moneyflow_root = root / "moneyflow_inputs"
            _write_moneyflow_inputs(moneyflow_root, load_demo_market_bars())

            result = run_simulation(
                source="fixture",
                market="CN",
                factor_source="tushare_moneyflow",
                factor_name="net_mf_amount_ratio",
                factor_windows=(1,),
                moneyflow_input_root=moneyflow_root,
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-10",
                output_dir=root / "paper",
            )

            self.assertEqual(result["request"]["factor_source"], "tushare_moneyflow")
            self.assertEqual(result["request"]["moneyflow_input_root"], str(moneyflow_root))
            self.assertGreater(len(result["fills"]), 0)

    def test_processed_cn_etf_simulation_auto_uses_rotation_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            cn_etf = bars[bars["market"] == "CN_ETF"].reset_index(drop=True)
            DatasetStore(root).write_frame(
                cn_etf,
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            membership = cn_etf[["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"].astype(str)
            membership["is_rotation_member"] = membership["asset_id"].eq("CN_ETF_XSHG_510300")
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )

            result = run_simulation(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=4,
                start_date="2024-01-04",
                end_date="2024-01-10",
            )

            self.assertEqual({row["asset_id"] for row in result["intents"]}, {"CN_ETF_XSHG_510300"})
            self.assertEqual(result["request"]["rotation_membership_root"], str(root))
            self.assertTrue(result["request"]["rotation_membership_required"])


def _write_moneyflow_inputs(root: Path, bars: pd.DataFrame) -> None:
    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        scale = 1.0 + index * 0.01
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare_moneyflow",
                "buy_sm_amount": 100.0 * scale,
                "sell_sm_amount": 80.0 * scale,
                "buy_md_amount": 300.0 * scale,
                "sell_md_amount": 250.0 * scale,
                "buy_lg_amount": 500.0 * scale,
                "sell_lg_amount": 450.0 * scale,
                "buy_elg_amount": 700.0 * scale,
                "sell_elg_amount": 650.0 * scale,
                "net_mf_amount": 120.0 + index,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/moneyflow_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
