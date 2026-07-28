import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_cn_etf_pcf_target_universe import (
    build_cn_etf_pcf_target_universe_cli,
)


class BuildCnEtfPcfTargetUniverseCliTests(unittest.TestCase):
    def test_writes_fingerprinted_target_and_review_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fund_path = root / "fund.parquet"
            pd.DataFrame(
                {
                    "symbol": ["510050.SH", "159919.SZ", "159999.SZ"],
                    "is_etf": [True, True, True],
                    "status": ["L", "D", "L"],
                    "list_date": ["20041230", "20121225", None],
                    "delist_date": [None, "20240103", None],
                }
            ).to_parquet(fund_path, index=False)
            bar_root = root / "bars"
            bar_root.mkdir()
            pd.DataFrame(
                {
                    "symbol": ["510050.SH", "159919.SZ"],
                    "date": ["2024-01-02", "2024-01-02"],
                }
            ).to_parquet(bar_root / "part.parquet", index=False)
            output = root / "output"

            result = build_cn_etf_pcf_target_universe_cli(
                fund_basic_path=fund_path,
                bar_root=bar_root,
                analysis_start="2024-01-02",
                analysis_end="2024-01-03",
                minimum_target_etfs=2,
                output_dir=output,
            )

            self.assertEqual(result["status"], "ready")
            self.assertTrue((output / "target_universe.csv").is_file())
            self.assertTrue((output / "cn_etf_pcf_target_universe.json").is_file())
            self.assertEqual(len(result["source_evidence"]["bar_files"]), 1)
            self.assertEqual(result["summary"]["target_etfs"], 2)


if __name__ == "__main__":
    unittest.main()
