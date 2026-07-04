import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.ops import external_feed_factor_matrix_join_smoke as join_smoke
from quant_robot.ops.external_feed_factor_matrix_join_smoke import run_external_feed_factor_matrix_join_smoke
from quant_robot.storage.dataset_store import DatasetStore


class ExternalFeedFactorMatrixJoinSmokeTests(unittest.TestCase):
    def test_latest_observations_for_signal_dates_aligns_all_dates_in_one_pass(self):
        frame = pd.DataFrame(
            {
                "date": [
                    pd.Timestamp("2024-01-01").date(),
                    pd.Timestamp("2024-01-04").date(),
                    pd.Timestamp("2024-01-02").date(),
                ],
                "available_date": [
                    pd.Timestamp("2024-01-02").date(),
                    pd.Timestamp("2024-01-05").date(),
                    pd.Timestamp("2024-01-03").date(),
                ],
                "symbol": ["000001.SZ", "000001.SZ", "000002.SZ"],
                "value": [1.0, 2.0, 3.0],
            }
        )

        joined = join_smoke._latest_observations_for_signal_dates(
            frame,
            [pd.Timestamp(value) for value in pd.date_range("2024-01-01", "2024-01-05", freq="D")],
        )

        self.assertEqual(len(joined), 7)
        self.assertEqual(sorted(joined["_signal_date"].dt.date.astype(str).unique()), [
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
        ])
        jan5 = joined[joined["_signal_date"] == pd.Timestamp("2024-01-05")]
        self.assertEqual(dict(zip(jan5["symbol"], jan5["value"])), {"000001.SZ": 2.0, "000002.SZ": 3.0})
        self.assertTrue((pd.to_datetime(joined["available_date"]) <= joined["_signal_date"]).all())

    def test_join_smoke_uses_available_date_not_raw_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            seed_config = Path(tmp) / "seeds.json"
            DatasetStore(root).write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "asset_id": ["CN_XSHE_000001"],
                        "symbol": ["000001.SZ"],
                        "market": ["CN"],
                        "source": ["tushare_margin_detail"],
                        "rzmre": [100.0],
                        "rzye": [1000.0],
                    }
                ),
                "processed/external_margin_detail",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            seed_config.write_text(
                json.dumps(
                    {
                        "factor_seeds": [
                            {
                                "factor_name": "margin_financing_acceleration_exhaustion_20",
                                "primary_feed": "external_margin_detail",
                                "required_columns": ["symbol", "available_date", "rzmre", "rzye"],
                                "minimum_history_days": 20,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_external_feed_factor_matrix_join_smoke(
                processed_root=root,
                seed_config_path=seed_config,
                output_dir=output_dir,
                signal_start_date="2024-01-02",
                signal_end_date="2024-01-03",
            )

            seed = result["seed_join_coverage"]["margin_financing_acceleration_exhaustion_20"]
            self.assertEqual(seed["joined_rows"], 1)
            self.assertEqual(seed["first_signal_date"], "2024-01-03")
            self.assertEqual(seed["last_signal_date"], "2024-01-03")
            self.assertEqual(seed["available_date_violations"], 0)
            self.assertEqual(seed["raw_date_not_before_signal_violations"], 0)
            self.assertEqual(result["summary"]["same_day_or_future_raw_date_violations"], 0)
            self.assertTrue((output_dir / "external_feed_factor_matrix_join_smoke.json").exists())

    def test_join_smoke_reads_shared_processed_feed_once_across_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            seed_config = Path(tmp) / "seeds.json"
            seed_config.write_text(
                json.dumps(
                    {
                        "factor_seeds": [
                            {
                                "factor_name": "seed_a",
                                "primary_feed": "external_margin_detail",
                                "required_columns": ["symbol", "available_date", "rzmre"],
                            },
                            {
                                "factor_name": "seed_b",
                                "primary_feed": "external_margin_detail",
                                "required_columns": ["symbol", "available_date", "rzye"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            feed = pd.DataFrame(
                {
                    "date": [pd.Timestamp("2024-01-02").date()],
                    "available_date": [pd.Timestamp("2024-01-03").date()],
                    "symbol": ["000001.SZ"],
                    "rzmre": [100.0],
                    "rzye": [1000.0],
                }
            )
            calls = []

            def fake_read_processed_dataset(_root, dataset, market):
                calls.append((str(dataset), market))
                return feed.copy()

            with patch.object(join_smoke, "_read_processed_dataset", side_effect=fake_read_processed_dataset):
                result = run_external_feed_factor_matrix_join_smoke(
                    processed_root=root,
                    seed_config_path=seed_config,
                    output_dir=output_dir,
                )

        self.assertEqual(result["summary"]["seed_count"], 2)
        self.assertEqual(calls, [("external_margin_detail", "CN")])

    def test_join_smoke_blocks_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            seed_config = Path(tmp) / "seeds.json"
            DatasetStore(root).write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "symbol": ["000001.SZ"],
                    }
                ),
                "processed/external_margin_detail",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            seed_config.write_text(
                json.dumps(
                    {
                        "factor_seeds": [
                            {
                                "factor_name": "bad_margin_seed",
                                "primary_feed": "external_margin_detail",
                                "required_columns": ["symbol", "available_date", "rzmre"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_external_feed_factor_matrix_join_smoke(
                processed_root=root,
                seed_config_path=seed_config,
                output_dir=output_dir,
            )

            seed = result["seed_join_coverage"]["bad_margin_seed"]
            self.assertEqual(seed["status"], "fail")
            self.assertEqual(seed["missing_required_columns"], ["rzmre"])

    def test_join_smoke_accepts_processed_child_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            seed_config = Path(tmp) / "seeds.json"
            DatasetStore(root).write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "symbol": ["000001.SZ"],
                        "rzmre": [100.0],
                        "rzye": [1000.0],
                    }
                ),
                "processed/external_margin_detail",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            seed_config.write_text(
                json.dumps(
                    {
                        "factor_seeds": [
                            {
                                "factor_name": "margin_financing_acceleration_exhaustion_20",
                                "primary_feed": "external_margin_detail",
                                "required_columns": ["symbol", "available_date", "rzmre", "rzye"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_external_feed_factor_matrix_join_smoke(
                processed_root=root / "processed",
                seed_config_path=seed_config,
                output_dir=output_dir,
            )

            seed = result["seed_join_coverage"]["margin_financing_acceleration_exhaustion_20"]
            self.assertEqual(seed["status"], "pass")
            self.assertEqual(seed["joined_rows"], 1)

    def test_join_smoke_resolves_required_columns_from_secondary_feed_with_pit_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            seed_config = Path(tmp) / "seeds.json"
            store = DatasetStore(root)
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "available_date": [pd.Timestamp("2024-01-03").date()],
                        "asset_id": ["CN_XSHE_000001"],
                        "symbol": ["000001.SZ"],
                        "market": ["CN"],
                        "source": ["tushare_hk_hold"],
                        "hold_ratio": [3.2],
                    }
                ),
                "processed/external_hk_hold",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2024-01-03").date()],
                        "available_date": [pd.Timestamp("2024-01-04").date()],
                        "market": ["CN"],
                        "source": ["tushare_moneyflow_hsgt"],
                        "north_money": [12500.0],
                    }
                ),
                "processed/external_hsgt_flow",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            seed_config.write_text(
                json.dumps(
                    {
                        "factor_seeds": [
                            {
                                "factor_name": "northbound_hold_accumulation_flow_regime_20",
                                "primary_feed": "external_hk_hold",
                                "secondary_feed": "external_hsgt_flow",
                                "required_columns": ["symbol", "available_date", "hold_ratio", "north_money"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_external_feed_factor_matrix_join_smoke(
                processed_root=root,
                seed_config_path=seed_config,
                output_dir=output_dir,
                signal_start_date="2024-01-03",
                signal_end_date="2024-01-04",
            )

            seed = result["seed_join_coverage"]["northbound_hold_accumulation_flow_regime_20"]
            self.assertEqual(seed["status"], "pass")
            self.assertEqual(seed["secondary_feed"], "external_hsgt_flow")
            self.assertEqual(seed["missing_required_columns"], [])
            self.assertEqual(seed["columns_resolved_from_secondary_feed"], ["north_money"])
            self.assertEqual(seed["joined_rows"], 1)
            self.assertEqual(seed["joined_signal_dates"], 1)
            self.assertEqual(seed["first_signal_date"], "2024-01-04")
            self.assertEqual(seed["available_date_violations"], 0)
            self.assertEqual(seed["raw_date_not_before_signal_violations"], 0)


if __name__ == "__main__":
    unittest.main()
