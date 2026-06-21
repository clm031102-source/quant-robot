import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_tushare_financial_pit_readiness import run_tushare_financial_pit_readiness_cli


class TushareFinancialPitReadinessCliTests(unittest.TestCase):
    def test_cli_writes_not_ready_packet_for_daily_basic_only_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "daily_basic_root"
            output_dir = root / "report"
            _write_parquet(
                data_root
                / "processed"
                / "factor_inputs"
                / "frequency=1d"
                / "market=CN"
                / "year=2025"
                / "part-00000.parquet",
                pd.DataFrame(
                    [
                        {
                            "date": "2025-01-02",
                            "asset_id": "CN_XSHE_000001",
                            "symbol": "000001.SZ",
                            "pe_ttm": 8.0,
                            "pb": 0.8,
                        }
                    ]
                ),
            )

            result = run_tushare_financial_pit_readiness_cli(
                roots=[data_root],
                output_dir=output_dir,
                allow_not_ready=True,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("missing_financial_statement_or_indicator_dataset", result["summary"]["blockers"])
            self.assertTrue((output_dir / "tushare_financial_pit_readiness.json").exists())
            self.assertTrue((output_dir / "tushare_financial_pit_readiness.md").exists())

    def test_cli_raises_when_not_ready_without_allow_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                run_tushare_financial_pit_readiness_cli(
                    roots=[root],
                    output_dir=root / "report",
                    allow_not_ready=False,
                )


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


if __name__ == "__main__":
    unittest.main()
