import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_data_manifest import (
    build_cn_stock_data_manifest,
    validate_cn_stock_data_manifest_packet,
    write_cn_stock_data_manifest,
)


class CnStockDataManifestTests(unittest.TestCase):
    def test_manifest_blocks_whole_market_bar_and_moneyflow_session_gaps(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-04"],
                "asset_id": ["A", "A"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "asset_type": ["stock", "stock"],
                "adj_close": [10.0, 10.1],
                "volume": [1000, 1100],
                "amount": [10000.0, 11100.0],
            }
        )
        moneyflow = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "asset_id": ["A", "A"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "net_mf_amount": [100.0, 120.0],
            }
        )
        calendar = pd.DataFrame(
            {
                "market": ["CN", "CN", "CN"],
                "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
                "is_open": [1, 1, 1],
                "source": ["tushare", "tushare", "tushare"],
            }
        )
        calendar_manifest = {
            "provider": "tushare",
            "endpoint": "trade_cal",
            "effective_range": {"start": "2024-01-02", "end": "2024-01-04"},
            "summary": {"session_date_sha256": "calendar-sha"},
            "artifact": {"sha256": "artifact-sha"},
        }

        manifest = build_cn_stock_data_manifest(
            bars=bars,
            moneyflow_inputs=moneyflow,
            source_root="data/processed/demo",
            expected_sessions=calendar,
            calendar_manifest=calendar_manifest,
        )

        self.assertEqual(manifest["status"], "blocked")
        self.assertEqual(manifest["manifest_schema_version"], 5)
        self.assertEqual(manifest["summary"]["expected_market_sessions"], 3)
        self.assertEqual(manifest["summary"]["missing_bar_market_sessions"], 1)
        self.assertEqual(manifest["summary"]["missing_moneyflow_market_sessions"], 1)
        self.assertEqual(manifest["summary"]["missing_bar_market_session_examples"], ["2024-01-03"])
        self.assertEqual(manifest["summary"]["missing_moneyflow_market_session_examples"], ["2024-01-04"])
        self.assertIn("whole_market_bar_sessions_missing:1", manifest["decision"]["blockers"])
        self.assertIn("whole_market_moneyflow_sessions_missing:1", manifest["decision"]["blockers"])
        self.assertEqual(manifest["calendar"]["artifact_sha256"], "artifact-sha")

    def test_manifest_summarizes_cn_stock_bars_and_moneyflow_inputs(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03", "2024-01-02", "2024-01-03"],
                "asset_id": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
                "symbol": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
                "market": ["CN", "CN", "CN", "CN"],
                "asset_type": ["stock", "stock", "stock", "stock"],
                "adj_close": [10.0, 10.5, 20.0, 40.5],
                "volume": [1000, 0, 2000, 2100],
                "amount": [10000.0, 0.0, 20000.0, 22000.0],
            }
        )
        moneyflow = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "asset_id": ["000001.SZ", "000001.SZ"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "net_mf_amount": [100.0, 120.0],
            }
        )

        manifest = build_cn_stock_data_manifest(bars=bars, moneyflow_inputs=moneyflow, source_root=Path("data/processed/demo"))

        self.assertEqual(manifest["status"], "review_required")
        self.assertEqual(manifest["summary"]["bar_rows"], 4)
        self.assertEqual(manifest["summary"]["bar_symbols"], 2)
        self.assertEqual(manifest["summary"]["moneyflow_symbols"], 1)
        self.assertEqual(manifest["summary"]["date_start"], "2024-01-02")
        self.assertEqual(manifest["summary"]["date_end"], "2024-01-03")
        self.assertEqual(manifest["summary"]["bar_years"], [2024])
        self.assertEqual(manifest["summary"]["bar_trade_dates_by_year"], {"2024": 2})
        self.assertIn("zero_volume_rows_present", manifest["decision"]["warnings"])
        self.assertIn("extreme_return_rows_present", manifest["decision"]["warnings"])
        self.assertIn("moneyflow_symbol_coverage_below_bars", manifest["decision"]["warnings"])
        self.assertFalse(manifest["live_boundary_allowed"])

    def test_manifest_blocks_non_cn_or_non_stock_bars(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "asset_id": ["510300.SH"],
                "symbol": ["510300.SH"],
                "market": ["CN_ETF"],
                "asset_type": ["etf"],
                "adj_close": [4.0],
                "volume": [1000],
                "amount": [4000.0],
            }
        )

        manifest = build_cn_stock_data_manifest(bars=bars, moneyflow_inputs=None, source_root=Path("data/processed/demo"))

        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("non_cn_rows_present", manifest["decision"]["blockers"])
        self.assertIn("non_stock_rows_present", manifest["decision"]["blockers"])

    def test_manifest_blocks_when_integrity_packet_is_blocked(self) -> None:
        bars, moneyflow = _clean_manifest_inputs()
        session_packet = _integrity_packet(
            stage="cn_stock_asset_session_integrity_audit",
            status="blocked",
            source_root="data/processed/demo",
            blockers=["unresolved_active_sessions:1"],
        )

        manifest = build_cn_stock_data_manifest(
            bars=bars,
            moneyflow_inputs=moneyflow,
            source_root="data/processed/demo",
            session_integrity_packet=session_packet,
        )

        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("asset_session_integrity_blocked", manifest["decision"]["blockers"])
        self.assertIn(
            "asset_session_integrity:unresolved_active_sessions:1",
            manifest["decision"]["blockers"],
        )

    def test_manifest_preserves_review_required_integrity_provenance(self) -> None:
        bars, moneyflow = _clean_manifest_inputs()
        session_packet = _integrity_packet(
            stage="cn_stock_asset_session_integrity_audit",
            status="review_required",
            source_root="data/processed/demo",
            review_reasons=["retrospective_legacy_suspension_evidence"],
        )
        session_packet["generated_at"] = (
            pd.Timestamp(date.today())
            .tz_localize("Asia/Shanghai")
            .tz_convert("UTC")
            .isoformat()
        )
        price_packet = _integrity_packet(
            stage="cn_stock_price_integrity_audit",
            status="review_required",
            source_root="data/processed/demo",
            review_reasons=["official_post_suspension_repricing_rows:2"],
        )
        price_packet["_provenance"] = {
            "path": "data/reports/price.json",
            "sha256": "a" * 64,
        }

        manifest = build_cn_stock_data_manifest(
            bars=bars,
            moneyflow_inputs=moneyflow,
            source_root="data/processed/demo",
            session_integrity_packet=session_packet,
            price_integrity_packet=price_packet,
        )

        self.assertEqual(manifest["status"], "review_required")
        self.assertIn("asset_session_integrity_review_required", manifest["decision"]["warnings"])
        self.assertIn("price_integrity_review_required", manifest["decision"]["warnings"])
        self.assertNotIn("extreme_return_rows_present", manifest["decision"]["warnings"])
        self.assertEqual(manifest["integrity"]["price"]["packet_sha256"], "a" * 64)
        self.assertEqual(manifest["integrity"]["asset_session"]["status"], "review_required")

    def test_write_manifest_outputs_json_markdown_and_symbol_coverage(self) -> None:
        manifest = build_cn_stock_data_manifest(
            bars=pd.DataFrame(
                {
                    "date": ["2024-01-02"],
                    "asset_id": ["000001.SZ"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "asset_type": ["stock"],
                    "adj_close": [10.0],
                    "volume": [1000],
                    "amount": [10000.0],
                }
            ),
            moneyflow_inputs=None,
            source_root=Path("data/processed/demo"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_cn_stock_data_manifest(Path(tmp), manifest)

            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.json").exists())
            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.md").exists())
            self.assertTrue((Path(tmp) / "cn_stock_symbol_coverage.csv").exists())

    def test_validate_manifest_accepts_cleared_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "cleared",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": true, "blockers": [], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            packet = validate_cn_stock_data_manifest_packet(path, expected_source_root=Path("data/processed/demo"))

        self.assertEqual(packet["status"], "cleared")

    def test_validate_manifest_blocks_review_required_without_explicit_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "review_required",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": false, "blockers": [], "warnings": ["moneyflow_inputs_missing"]},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "review required"):
                validate_cn_stock_data_manifest_packet(path)

            packet = validate_cn_stock_data_manifest_packet(path, allow_review_required=True)

        self.assertEqual(packet["status"], "review_required")

    def test_validate_manifest_rejects_blocked_or_mismatched_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "blocked",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 0, "bar_symbols": 0},
                  "decision": {"data_manifest_cleared": false, "blockers": ["bars_missing"], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "blocked"):
                validate_cn_stock_data_manifest_packet(path)

    def test_validate_manifest_rejects_stale_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "cleared",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": true, "blockers": [], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % (date.today() - timedelta(days=1)).isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "generated today"):
                validate_cn_stock_data_manifest_packet(path)

    def test_manifest_records_and_validates_source_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            source_file = root / "bars.csv"
            source_file.write_text("date,asset_id\n2024-01-02,A\n", encoding="utf-8")
            manifest = build_cn_stock_data_manifest(
                bars=pd.DataFrame(
                    {
                        "date": ["2024-01-02"],
                        "asset_id": ["A"],
                        "symbol": ["000001.SZ"],
                        "market": ["CN"],
                        "asset_type": ["stock"],
                        "adj_close": [10.0],
                        "volume": [1000],
                        "amount": [10000.0],
                    }
                ),
                moneyflow_inputs=None,
                source_root=root,
            )
            output = Path(tmp) / "report"
            write_cn_stock_data_manifest(output, manifest)
            packet_path = output / "cn_stock_data_manifest.json"

            self.assertEqual(manifest["manifest_schema_version"], 5)
            self.assertEqual(manifest["summary"]["source_file_count"], 1)
            self.assertEqual(len(manifest["summary"]["source_content_sha256"]), 64)
            validate_cn_stock_data_manifest_packet(
                packet_path,
                expected_source_root=root,
                allow_review_required=True,
                verify_source_fingerprint=True,
            )

            source_file.write_text("date,asset_id\n2024-01-02,B\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source fingerprint mismatch"):
                validate_cn_stock_data_manifest_packet(
                    packet_path,
                    expected_source_root=root,
                    allow_review_required=True,
                    verify_source_fingerprint=True,
                )

    def test_authority_manifest_fingerprints_referenced_bar_and_moneyflow_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bar_store = root / "bars_store"
            moneyflow_store = root / "moneyflow_store"
            bar_file = bar_store / "processed/bars/frequency=1d/market=CN/year=2024/bars.csv"
            moneyflow_file = (
                moneyflow_store / "processed/moneyflow_inputs/frequency=1d/market=CN/year=2024/moneyflow.csv"
            )
            bar_file.parent.mkdir(parents=True)
            moneyflow_file.parent.mkdir(parents=True)
            bar_file.write_text("date,asset_id\n2024-01-02,A\n", encoding="utf-8")
            moneyflow_file.write_text("date,asset_id\n2024-01-02,A\n", encoding="utf-8")
            bar_config = root / "authority_bars.json"
            moneyflow_config = root / "authority_moneyflow.json"
            bar_config.write_text(
                json.dumps({"market": "CN", "segments": [{"root": str(bar_store)}]}),
                encoding="utf-8",
            )
            moneyflow_config.write_text(
                json.dumps({"market": "CN", "segments": [{"root": str(moneyflow_store)}]}),
                encoding="utf-8",
            )
            bars = pd.DataFrame(
                {
                    "date": ["2024-01-02"],
                    "asset_id": ["A"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "asset_type": ["stock"],
                    "adj_close": [10.0],
                    "volume": [1000],
                    "amount": [10000.0],
                }
            )
            moneyflow = pd.DataFrame(
                {
                    "date": ["2024-01-02"],
                    "asset_id": ["A"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "net_mf_amount": [10.0],
                }
            )
            manifest = build_cn_stock_data_manifest(
                bars=bars,
                moneyflow_inputs=moneyflow,
                source_root=bar_config,
                moneyflow_source_root=moneyflow_config,
            )
            output = root / "report"
            write_cn_stock_data_manifest(output, manifest)
            packet_path = output / "cn_stock_data_manifest.json"

            self.assertEqual(manifest["summary"]["source_file_count"], 2)
            self.assertEqual(manifest["summary"]["moneyflow_source_file_count"], 2)
            self.assertEqual(manifest["summary"]["moneyflow_source_root"], str(moneyflow_config))
            validate_cn_stock_data_manifest_packet(
                packet_path,
                expected_source_root=bar_config,
                expected_moneyflow_source_root=moneyflow_config,
                verify_source_fingerprint=True,
            )

            bar_file.write_text("date,asset_id\n2024-01-02,B\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source fingerprint mismatch"):
                validate_cn_stock_data_manifest_packet(
                    packet_path,
                    expected_source_root=bar_config,
                    expected_moneyflow_source_root=moneyflow_config,
                    verify_source_fingerprint=True,
                )

    def test_validate_manifest_rejects_moneyflow_source_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": date.today().isoformat(),
                        "status": "cleared",
                        "summary": {
                            "source_root": "bars.json",
                            "moneyflow_source_root": "moneyflow.json",
                            "bar_rows": 10,
                            "bar_symbols": 2,
                        },
                        "decision": {"data_manifest_cleared": True, "blockers": [], "warnings": []},
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "moneyflow source root mismatch"):
                validate_cn_stock_data_manifest_packet(
                    path,
                    expected_source_root="bars.json",
                    expected_moneyflow_source_root="other_moneyflow.json",
                )


def _clean_manifest_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    bars = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03"],
            "asset_id": ["A", "A"],
            "symbol": ["000001.SZ", "000001.SZ"],
            "market": ["CN", "CN"],
            "asset_type": ["stock", "stock"],
            "adj_close": [10.0, 10.1],
            "volume": [1000, 1100],
            "amount": [10000.0, 11100.0],
        }
    )
    moneyflow = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03"],
            "asset_id": ["A", "A"],
            "symbol": ["000001.SZ", "000001.SZ"],
            "market": ["CN", "CN"],
            "net_mf_amount": [100.0, 120.0],
        }
    )
    return bars, moneyflow


def _integrity_packet(
    *,
    stage: str,
    status: str,
    source_root: str,
    blockers: list[str] | None = None,
    review_reasons: list[str] | None = None,
) -> dict:
    return {
        "stage": stage,
        "generated_at": date.today().isoformat() + "T00:00:00+00:00",
        "status": status,
        "source_root": source_root,
        "summary": {},
        "decision": {
            "blockers": blockers or [],
            "review_reasons": review_reasons or [],
        },
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
