import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.ingest_tushare_legacy_suspension import main, run_legacy_suspension_ingest


class FakeAdapter:
    def fetch_legacy_suspension(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ts_code": [ts_code],
                "suspend_date": [start_date.replace("-", "")],
                "resume_date": [end_date.replace("-", "")],
                "suspend_reason": ["fixture"],
            }
        )


class TushareLegacySuspensionIngestCliTests(unittest.TestCase):
    def test_run_loads_unresolved_asset_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unresolved = root / "unresolved.csv"
            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_002260"],
                    "symbol": ["002260.SZ"],
                }
            ).to_csv(unresolved, index=False)

            report = run_legacy_suspension_ingest(
                unresolved_assets_path=unresolved,
                output_dir=root / "output",
                start_date="2015-01-01",
                end_date="2025-12-31",
                adapter=FakeAdapter(),
            )

            self.assertEqual(report["status"], "completed")

    def test_run_applies_official_bse_code_mapping_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unresolved = root / "unresolved.csv"
            pd.DataFrame(
                {
                    "asset_id": ["CN_XBEI_920039"],
                    "symbol": ["920039.BJ"],
                }
            ).to_csv(unresolved, index=False)
            mapping = root / "code_mapping.html"
            pd.DataFrame(
                {
                    "seq": [1],
                    "name": ["sample"],
                    "list_date": ["2021/11/15"],
                    "old_code": [831039],
                    "new_code": [920039],
                }
            ).to_html(mapping, index=False)
            adapter = FakeAdapter()

            report = run_legacy_suspension_ingest(
                unresolved_assets_path=unresolved,
                output_dir=root / "output",
                start_date="2015-01-01",
                end_date="2025-12-31",
                adapter=adapter,
                bse_code_mapping_path=mapping,
            )

            self.assertEqual(report["summary"]["mapped_provider_symbols"], 1)
            self.assertIn("sha256=", report["provider_mapping_source"])

    def test_main_prints_completed_report(self):
        report = {"status": "completed", "summary": {"requested_assets": 1}}
        with (
            patch(
                "scripts.ingest_tushare_legacy_suspension.run_legacy_suspension_ingest",
                return_value=report,
            ),
            patch(
                "sys.argv",
                [
                    "ingest_tushare_legacy_suspension.py",
                    "--unresolved-assets",
                    "unresolved.csv",
                ],
            ),
        ):
            main()


if __name__ == "__main__":
    unittest.main()
