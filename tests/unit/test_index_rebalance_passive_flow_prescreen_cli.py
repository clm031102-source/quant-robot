import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_index_rebalance_passive_flow_prescreen import run_index_rebalance_passive_flow_prescreen_cli
from tests.unit.test_index_rebalance_passive_flow_prescreen import _bars, _events, _stock_basic


class IndexRebalancePassiveFlowPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_results_and_factor_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events_path = root / "events.csv"
            bars_path = root / "bars.parquet"
            stock_basic_path = root / "stock_basic.csv"
            output_dir = root / "report"
            _events().to_csv(events_path, index=False)
            _bars().to_parquet(bars_path, index=False)
            _stock_basic().to_csv(stock_basic_path, index=False)

            result = run_index_rebalance_passive_flow_prescreen_cli(
                index_events_path=events_path,
                bars_path=bars_path,
                stock_basic_path=stock_basic_path,
                output_dir=output_dir,
                horizons=(1,),
                min_cross_section=5,
                min_ic_observations=1,
                min_neutral_rank_ic=-1.0,
                min_neutral_ic_t_stat=-1.0,
            )

            self.assertEqual(result["stage"], "index_rebalance_passive_flow_prescreen")
            payload = json.loads((output_dir / "index_rebalance_passive_flow_prescreen.json").read_text())
            self.assertEqual(payload["summary"]["candidate_count"], 5)
            self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen.md").exists())
            self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen_results.csv").exists())
            self.assertTrue((output_dir / "index_rebalance_passive_flow_factor_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
