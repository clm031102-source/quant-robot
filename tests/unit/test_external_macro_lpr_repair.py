import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.external_macro_lpr_repair import repair_external_macro_lpr
from quant_robot.storage.dataset_store import DatasetStore


class ExternalMacroLprRepairTests(unittest.TestCase):
    def test_repairs_lpr_columns_from_cache_into_fresh_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            output_root = Path(tmp) / "repaired"
            report_dir = Path(tmp) / "report"
            lpr_cache = Path(tmp) / "lpr_cache.json"
            store = DatasetStore(source_root)
            macro = pd.DataFrame(
                {
                    "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                    "available_date": [pd.Timestamp("2024-01-03").date(), pd.Timestamp("2024-01-04").date()],
                    "market": ["CN", "CN"],
                    "source": ["tushare_macro_rates", "tushare_macro_rates"],
                    "ingested_at": [pd.Timestamp("2024-01-04", tz="UTC")] * 2,
                    "shibor_on": [1.0, 1.1],
                    "shibor_1w": [1.1, 1.2],
                    "shibor_1m": [1.2, 1.3],
                    "shibor_3m": [1.3, 1.4],
                    "shibor_1y": [1.8, 1.9],
                    "lpr_1y": [pd.NA, pd.NA],
                    "lpr_5y": [pd.NA, pd.NA],
                }
            )
            store.write_frame(macro, "processed/external_macro_rates", {"frequency": "1d", "market": "CN", "year": "2024"})
            lpr_cache.write_text(
                json.dumps({"rows": [{"date": "2024-01-01", "lpr_1y": 3.45, "lpr_5y": 3.95}]}),
                encoding="utf-8",
            )

            report = repair_external_macro_lpr(
                processed_root=source_root,
                lpr_cache_path=lpr_cache,
                output_root=output_root,
                report_dir=report_dir,
            )

            repaired = DatasetStore(output_root).read_frame(
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(report["status"], "pass")
            self.assertFalse(report["promotion_allowed"])
            self.assertEqual(report["summary"]["lpr_1y_non_null_after"], 2)
            self.assertEqual(repaired["lpr_1y"].tolist(), [3.45, 3.45])
            self.assertEqual(repaired["lpr_5y"].tolist(), [3.95, 3.95])
            self.assertEqual(repaired["shibor_1m"].tolist(), [1.2, 1.3])
            self.assertEqual(pd.to_datetime(repaired["available_date"]).dt.date.astype(str).tolist(), ["2024-01-03", "2024-01-04"])
            self.assertTrue((report_dir / "external_macro_lpr_repair_report.json").exists())

    def test_refuses_in_place_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            lpr_cache = Path(tmp) / "lpr_cache.json"
            lpr_cache.write_text(
                json.dumps({"rows": [{"date": "2024-01-01", "lpr_1y": 3.45, "lpr_5y": 3.95}]}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                repair_external_macro_lpr(
                    processed_root=source_root,
                    lpr_cache_path=lpr_cache,
                    output_root=source_root,
                    report_dir=Path(tmp) / "report",
                )

    def test_refuses_output_root_nested_under_source_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            nested_output_root = source_root / "nested_repair"
            lpr_cache = Path(tmp) / "lpr_cache.json"
            DatasetStore(source_root).write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "shibor_1m": [1.2],
                        "shibor_3m": [1.3],
                        "shibor_1y": [1.8],
                        "lpr_1y": [pd.NA],
                        "lpr_5y": [pd.NA],
                    }
                ),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            lpr_cache.write_text(
                json.dumps({"rows": [{"date": "2024-01-01", "lpr_1y": 3.45, "lpr_5y": 3.95}]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "outside the source processed root"):
                repair_external_macro_lpr(
                    processed_root=source_root,
                    lpr_cache_path=lpr_cache,
                    output_root=nested_output_root,
                    report_dir=Path(tmp) / "report",
                )

    def test_rejects_lpr_cache_without_numeric_plausible_rates(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            output_root = Path(tmp) / "repaired"
            report_dir = Path(tmp) / "report"
            lpr_cache = Path(tmp) / "lpr_cache.json"
            DatasetStore(source_root).write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "shibor_1m": [1.2],
                        "shibor_3m": [1.3],
                        "shibor_1y": [1.8],
                        "lpr_1y": [pd.NA],
                        "lpr_5y": [pd.NA],
                    }
                ),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            lpr_cache.write_text(
                json.dumps({"rows": [{"date": "2024-01-01", "lpr_1y": -1.0, "lpr_5y": 30.0}]}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                repair_external_macro_lpr(
                    processed_root=source_root,
                    lpr_cache_path=lpr_cache,
                    output_root=output_root,
                    report_dir=report_dir,
                )


if __name__ == "__main__":
    unittest.main()
