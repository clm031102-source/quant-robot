import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_recent_data_refresh import run_recent_data_refresh
from quant_robot.storage.cn_etf_rotation_membership import load_cn_etf_rotation_membership
from quant_robot.storage.dataset_store import DatasetStore


class RecentDataRefreshCliTests(unittest.TestCase):
    WORKSTATION_CONFIG = {
        "machines": {
            "laptop": {"allowed_tasks": ["architecture_ops", "factor_smoke", "factor_review", "project_sync"]},
            "highspec_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
            "office_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
        },
        "tasks": {"data_pipeline": {"branch": "codex/tushare-data-pipeline"}},
    }

    def test_cli_writes_completed_fixture_refresh_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2024-01-04",
                        "decision": {"stop_reasons": ["signal_data_stale"]},
                        "ledger": [
                            {
                                "case_id": "case_fixture",
                                "signal_date": "2024-01-02",
                                "profile_id": "cap60_guard12_cd3",
                                "risk_tier": "aggressive_growth",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            processed_dir = root / "processed"
            report_dir = root / "report"

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare-fixture",
                market="CN_ETF",
                output_dir=processed_dir,
                report_dir=report_dir,
                execute=True,
                readiness={"ready": True, "missing": []},
            )

            self.assertEqual(pack["stage"], "phase_5_7_tushare_recent_data_refresh")
            self.assertEqual(pack["status"], "completed")
            self.assertTrue(pack["decision"]["signal_data_stale_cleared"])
            self.assertTrue((report_dir / "recent_data_refresh_pack.json").exists())
            self.assertTrue((report_dir / "recent_data_refresh_pack.md").exists())
            self.assertTrue((report_dir / "recent_data_refresh_coverage.csv").exists())
            self.assertTrue((report_dir / "recent_data_refresh_next_actions.csv").exists())
            self.assertTrue((processed_dir / "quality_report.json").exists())
            self.assertGreater(pack["ingest"]["processed_rows"], 0)
            self.assertEqual(pack["coverage"]["latest_data_date"], "2024-01-04")

    def test_completed_fixture_refresh_writes_recent_rotation_membership_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2024-01-04",
                        "ledger": [
                            {
                                "signal_date": "2024-01-02",
                                "observed_assets": "CN_ETF_XSHG_510300",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            processed_dir = root / "processed"

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare-fixture",
                market="CN_ETF",
                output_dir=processed_dir,
                report_dir=root / "report",
                execute=True,
                readiness={"ready": True, "missing": []},
            )

            membership = load_cn_etf_rotation_membership(processed_dir, "CN_ETF")

            self.assertEqual(pack["status"], "completed")
            self.assertGreater(len(membership), 0)
            self.assertTrue(membership["is_rotation_member"].all())
            self.assertIn("history_rows_to_date", membership.columns)
            self.assertIn("recent_refresh_provider_daily_bars", set(membership["membership_source"]))
            self.assertEqual(pack["ingest"]["rotation_membership"]["rows"], len(membership))

    def test_fund_basic_rotation_membership_excludes_lof_from_recent_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2024-01-04",
                        "ledger": [
                            {
                                "signal_date": "2024-01-01",
                                "observed_assets": "CN_ETF_XSHG_510300",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            processed_dir = root / "processed"
            dates = list(pd.date_range("2024-01-02", periods=3).date)

            def ingest_runner(**kwargs):
                output_dir = Path(kwargs["output_dir"])
                bars = pd.DataFrame(
                    {
                        "asset_id": ["CN_ETF_XSHG_510300"] * 3 + ["CN_ETF_XSHG_501001"] * 3,
                        "symbol": ["510300.SH"] * 3 + ["501001.SH"] * 3,
                        "date": dates * 2,
                        "market": ["CN_ETF"] * 6,
                        "frequency": ["1d"] * 6,
                        "open": [1.0] * 6,
                        "high": [1.01] * 6,
                        "low": [0.99] * 6,
                        "close": [1.0, 1.01, 1.02, 2.0, 2.01, 2.02],
                        "volume": [100.0] * 6,
                        "amount": [1_000_000.0] * 6,
                    }
                )
                DatasetStore(output_dir).write_frame(
                    bars,
                    "processed/bars",
                    {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
                )
                return {
                    "source": "tushare",
                    "market": "CN_ETF",
                    "downloaded_trade_dates": ["20240102", "20240103", "20240104"],
                    "skipped_trade_dates": [],
                    "processed_rows": len(bars),
                    "quality_report": {
                        "rows": len(bars),
                        "assets": 2,
                        "start_date": "2024-01-02",
                        "end_date": "2024-01-04",
                        "missing_date_rows": 0,
                        "duplicate_bars": 0,
                        "zero_volume_rows": 0,
                        "coverage_by_asset": [
                            {
                                "asset_id": "CN_ETF_XSHG_510300",
                                "rows": 3,
                                "start_date": "2024-01-02",
                                "end_date": "2024-01-04",
                            }
                        ],
                    },
                }

            fund_basic = pd.DataFrame(
                {
                    "symbol": ["510300.SH", "501001.SH"],
                    "name": ["CSI 300 ETF", "Listed LOF"],
                    "market": ["E", "E"],
                    "status": ["L", "L"],
                    "fund_type": ["ETF", "LOF"],
                    "type": ["ETF", "LOF"],
                    "invest_type": ["Passive", "LOF"],
                    "is_exchange_traded": [True, True],
                    "is_etf": [True, False],
                    "list_date": [pd.Timestamp("2020-01-01").date(), pd.Timestamp("2020-01-01").date()],
                    "delist_date": [pd.NaT, pd.NaT],
                }
            )

            class FakeFundBasicAdapter:
                def fetch_fund_basic(self, market="E", status="L"):
                    self.request = {"market": market, "status": status}
                    return fund_basic

            fake_adapter = FakeFundBasicAdapter()
            with patch("scripts.run_recent_data_refresh.TushareAdapter", return_value=fake_adapter):
                pack = run_recent_data_refresh(
                    profile_observation_pack=profile_pack,
                    source="tushare",
                    market="CN_ETF",
                    output_dir=processed_dir,
                    report_dir=root / "report",
                    execute=True,
                    readiness={"ready": True, "missing": []},
                    ingest_runner=ingest_runner,
                )

            membership = load_cn_etf_rotation_membership(processed_dir, "CN_ETF")
            lof = membership[membership["asset_id"].eq("CN_ETF_XSHG_501001")].iloc[-1]

            self.assertEqual(pack["status"], "completed")
            self.assertFalse(bool(lof["is_rotation_member"]))
            self.assertIn("not_etf", str(lof["exclusion_reasons"]))
            self.assertEqual(pack["ingest"]["rotation_membership"]["source"], "tushare_fund_basic_fund_daily")
            self.assertEqual(fake_adapter.request, {"market": "E", "status": ""})

    def test_function_writes_machine_aware_handoff_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "report"

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare",
                market="CN_ETF",
                output_dir=root / "processed",
                report_dir=report_dir,
                execute=False,
                readiness={"ready": True, "missing": []},
                machine="laptop",
                workstation_config=self.WORKSTATION_CONFIG,
            )

            self.assertEqual(pack["next_actions"][0]["action"], "handoff_recent_tushare_refresh")
            written_pack = json.loads((report_dir / "recent_data_refresh_pack.json").read_text(encoding="utf-8"))
            self.assertFalse(written_pack["workstation"]["can_run_data_pipeline"])
            self.assertIn("handoff_recent_tushare_refresh", (report_dir / "recent_data_refresh_pack.md").read_text(encoding="utf-8"))

    def test_execute_request_on_laptop_does_not_run_data_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )

            def fail_if_called(**_kwargs):
                raise AssertionError("laptop must not run recent Tushare ingest")

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare",
                market="CN_ETF",
                output_dir=root / "processed",
                report_dir=root / "report",
                execute=True,
                readiness={"ready": True, "missing": []},
                ingest_runner=fail_if_called,
                machine="laptop",
                workstation_config=self.WORKSTATION_CONFIG,
            )

            self.assertFalse(pack["will_download"])
            self.assertEqual(pack["status"], "ready_to_execute")
            self.assertEqual(pack["next_actions"][0]["action"], "handoff_recent_tushare_refresh")

    def test_script_entrypoint_runs_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2024-01-04",
                        "ledger": [{"signal_date": "2024-01-02", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_recent_data_refresh.py",
                    "--profile-observation-pack",
                    str(profile_pack),
                    "--source",
                    "tushare-fixture",
                    "--output-dir",
                    str(root / "processed"),
                    "--report-dir",
                    str(root / "report"),
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("phase_5_7_tushare_recent_data_refresh", result.stdout)


if __name__ == "__main__":
    unittest.main()
