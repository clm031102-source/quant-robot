import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_financial_statement_shard_overlap_preview import (
    run_financial_statement_shard_overlap_preview,
)


class FinancialStatementShardOverlapPreviewCliTests(unittest.TestCase):
    def test_previews_net_new_symbols_against_existing_financial_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "shards": [
                            {
                                "shard_id": 13,
                                "symbols": [
                                    "002181.SZ",
                                    "000597.SZ",
                                    "000635.SZ",
                                    "002337.SZ",
                                    "000703.SZ",
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            existing = root / "existing_financial"
            existing.mkdir()
            pd.DataFrame(
                {
                    "asset_id": [
                        "CN_XSHE_000597",
                        "CN_XSHE_000703",
                        "CN_XSHG_600000",
                    ],
                    "date": pd.date_range("2024-01-01", periods=3),
                }
            ).to_parquet(existing / "part.parquet", index=False)
            output = root / "preview"

            result = run_financial_statement_shard_overlap_preview(
                plan_json=plan,
                shard_id=13,
                symbol_offset=0,
                symbol_limit=5,
                financial_roots=[existing],
                output_dir=output,
            )

            self.assertEqual(result["summary"]["symbol_count"], 5)
            self.assertEqual(result["summary"]["existing_symbol_count"], 2)
            self.assertEqual(result["summary"]["net_new_symbol_count"], 3)
            self.assertEqual(result["summary"]["net_new_ratio"], 0.6)
            self.assertEqual(
                result["net_new_symbols"],
                ["002181.SZ", "000635.SZ", "002337.SZ"],
            )
            self.assertEqual(result["existing_symbols"], ["000597.SZ", "000703.SZ"])
            self.assertTrue((output / "financial_statement_shard_overlap_preview.json").exists())
            self.assertTrue((output / "financial_statement_shard_overlap_preview.md").exists())


if __name__ == "__main__":
    unittest.main()
