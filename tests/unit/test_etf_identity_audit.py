import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.etf_identity_audit import audit_identity_frames, run_identity_audit


def identities(symbols=("510300.SH", "160119.SZ", "161022A.SZ")):
    return pd.DataFrame([{"date": "2024-01-02", "symbol": s,
        "asset_id": "CN_ETF_" + ("XSHG" if s.endswith(".SH") else "XSHE") + "_" + s.split(".")[0]}
        for s in symbols])


def catalogue(flag=True):
    return pd.DataFrame([{"symbol": s, "name": name, "is_etf": etf,
        "status": status, "list_date": "2012-01-01", "delist_date": None}
        for s, name, etf, status in (("510300.SH", "test ETF", True, "L"),
            ("160119.SZ", "test ETF linked LOF", flag, "D"))])


class EtfIdentityAuditTests(unittest.TestCase):
    def test_dated_labels_never_certify_historical_membership(self):
        report = audit_identity_frames(identities(), {"2026-06-21": catalogue(),
            "2026-07-16": catalogue(False)}, identities(("510300.SH",)))
        self.assertEqual(report["invalid_bar_identities"]["rows"], 1)
        self.assertEqual(report["classification_changes"][0]["symbol"], "160119.SZ")
        self.assertFalse(report["classification_changes"][0]["to_is_etf"])
        self.assertEqual(report["catalogues"][1]["bar_classification"]["snapshot_non_etf"]["rows"], 1)
        self.assertEqual(report["catalogues"][1]["status_counts"]["D"], 1)
        self.assertEqual(report["cached_roster_observations"]["bar_rows_with_same_day_observation"]["rows"], 1)
        self.assertFalse(report["historical_membership_verified"])
        self.assertFalse(report["cached_roster_observations"]["absence_is_negative_classification"])
        json.dumps(report, allow_nan=False)

    def test_roster_presence_is_date_specific_and_missing_name_is_json_null(self):
        observed = identities(("510300.SH",))
        observed["date"] = "2024-01-03"
        old, new = catalogue(), catalogue(False)
        new.loc[new.symbol.eq("160119.SZ"), "name"] = None
        report = audit_identity_frames(identities(), {"2026-06-21": old, "2026-07-16": new}, observed)
        self.assertIsNone(report["classification_changes"][0]["name"])
        self.assertEqual(report["cached_roster_observations"]["bar_rows_with_same_day_observation"]["rows"], 0)

    def test_rejects_unknown_classification_instead_of_boolean_coercion(self):
        for value in ("unknown", "", None, 1.0):
            frame = catalogue().astype({"is_etf": object})
            frame.loc[0, "is_etf"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "explicit boolean"):
                audit_identity_frames(identities(), {"2026-06-21": frame}, identities(("510300.SH",)))

    def test_string_false_is_negative_not_truthy(self):
        frame = catalogue(False).astype({"is_etf": str})
        report = audit_identity_frames(identities(), {"2026-06-21": frame}, identities(("510300.SH",)))
        self.assertEqual(report["catalogues"][0]["label_counts"]["non_etf"], 1)

    def test_rejects_duplicate_keys_and_final_holdout_dates(self):
        observed = identities(("510300.SH",))
        for bars, cats, roster, pattern in (
            (pd.concat([identities(), identities()]), catalogue(), observed, "duplicate bar"),
            (identities(), pd.concat([catalogue(), catalogue()]), observed, "duplicate catalogue"),
            (identities(), catalogue(), pd.concat([observed, observed]), "duplicate roster"),
            (identities().assign(date="2026-01-02"), catalogue(), observed, "final holdout"),
        ):
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                audit_identity_frames(bars, {"2026-06-21": cats}, roster)

    def test_reads_only_identity_columns_and_current_manifest_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, root, manifest = disk_fixture(tmp)
            # An obsolete partition contains invalid data and must never be visited.
            stale = root / "source/szse_share/window=2024-01-01_2024-06-30"
            stale.mkdir(parents=True)
            (stale / "part.parquet").write_bytes(b"not parquet")
            import pyarrow.dataset as ds
            original_dataset = ds.dataset
            projected = []

            class Reader:
                def __init__(self, *args, **kwargs):
                    self.reader = original_dataset(*args, **kwargs)

                def to_table(self, **kwargs):
                    projected.extend(kwargs["columns"])
                    return self.reader.to_table(**kwargs)

            with patch("pyarrow.dataset.dataset", Reader):
                report = run_identity_audit(**config)
            self.assertEqual(set(projected), {"date", "symbol", "asset_id", "share_source"})
            self.assertEqual(report["cached_roster_evidence"]["completed_requests_used"], 1)
            self.assertEqual(report["source_changed_during_audit"], [])
            self.assertTrue(all(len(item["sha256"]) == 64 for item in report["input_files"]))
            self.assertFalse(report["cached_roster_evidence"]["transport_payloads_reverified"])

    def test_final_holdout_and_mislabelled_roster_dates_fail_before_identity_projection(self):
        for bad_date in ("2026-01-02", "2024-02-01"):
            with self.subTest(bad_date=bad_date), tempfile.TemporaryDirectory() as tmp:
                config, root, manifest = disk_fixture(tmp)
                part = root / "source/sse_share/date=2024-01-02/part.parquet"
                # Missing identity columns proves only dates were read before failure.
                pd.DataFrame({"date": [bad_date]}).to_parquet(part, index=False)
                with self.assertRaisesRegex(ValueError, "holdout|label and row dates"):
                    run_identity_audit(**config)

    def test_szse_request_bounds_checked_even_for_partial_audit_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, root, manifest = disk_fixture(tmp)
            key, entry = next(iter(manifest["requests"].items()))
            entry.update(dataset="source/szse_share", source="szse_official_fund_scale",
                parameters={"start_date": "2024-01-01", "end_date": "2024-01-03"},
                partitions={"window": "2024-01-01_2024-01-03"},
                stored_path=str(root / "source/szse_share/window=2024-01-01_2024-01-03/part.parquet"))
            manifest["requests"] = {"szse:2024-01-01:2024-01-03": entry}
            (root / "public_source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            folder = root / "source/szse_share/window=2024-01-01_2024-01-03"
            folder.mkdir(parents=True)
            pd.DataFrame({"date": ["2024-01-04"]}).to_parquet(folder / "part.parquet", index=False)
            with self.assertRaisesRegex(ValueError, "label and row dates"):
                run_identity_audit(**config)

    def test_bad_provenance_row_count_and_snapshot_date_are_rejected(self):
        for field, value, pattern in (("source", "guessed", "provenance"),
                ("rows", 99, "row count"), ("response_sha256", "missing", "provenance")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                config, root, manifest = disk_fixture(tmp)
                next(iter(manifest["requests"].values()))[field] = value
                (root / "public_source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, pattern):
                    run_identity_audit(**config)
        with tempfile.TemporaryDirectory() as tmp:
            config, _, _ = disk_fixture(tmp)
            config["catalogues"][0]["captured_on"] = "2024-01-02"
            with self.assertRaisesRegex(ValueError, "snapshot date"):
                run_identity_audit(**config)

    def test_manifest_partition_and_stored_file_must_match_actual_source(self):
        for change in ("partition", "folder", "filename"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                config, root, manifest = disk_fixture(tmp)
                entry = next(iter(manifest["requests"].values()))
                if change == "partition":
                    entry["partitions"] = {"date": "2024-01-03"}
                elif change == "folder":
                    entry["stored_path"] = str(root / "source/sse_share/date=2024-01-03/part.parquet")
                else:
                    entry["stored_path"] = str(root / "source/sse_share/date=2024-01-02/other.parquet")
                (root / "public_source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "provenance|stored path"):
                    run_identity_audit(**config)

    def test_sse_source_cannot_count_shenzhen_symbols_as_verified_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, root, _ = disk_fixture(tmp)
            identities(("160119.SZ",)).assign(share_source="sse_official_etf_scale").to_parquet(
                root / "source/sse_share/date=2024-01-02/part.parquet", index=False)
            with self.assertRaisesRegex(ValueError, "exchange disagrees"):
                run_identity_audit(**config)


def disk_fixture(tmp):
    root = Path(tmp)
    bars = root / "processed/bars/frequency=1d/market=CN_ETF/year=2024"
    bars.mkdir(parents=True)
    identities().assign(close="DO NOT READ", adj_close="DO NOT READ").to_parquet(bars / "part.parquet", index=False)
    metadata = root / "metadata/snapshot=2026-06-21/part.parquet"
    metadata.parent.mkdir(parents=True)
    catalogue().to_parquet(metadata, index=False)
    folder = root / "source/sse_share/date=2024-01-02"
    folder.mkdir(parents=True)
    identities(("510300.SH",)).assign(share_source="sse_official_etf_scale", total_share="DO NOT READ").to_parquet(
        folder / "part.parquet", index=False)
    manifest = {"requests": {"sse:2024-01-02": {"status": "completed", "dataset": "source/sse_share",
        "source": "sse_official_etf_scale", "parameters": {"trade_date": "2024-01-02"},
        "response_sha256": "a" * 64, "rows": 1, "partitions": {"date": "2024-01-02"},
        "stored_path": str(folder / "part.parquet")}}}
    (root / "public_source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return {"data_root": root, "share_root": root, "start_date": "2024-01-02", "end_date": "2024-01-02",
        "catalogues": [{"captured_on": "2026-06-21", "path": str(metadata)}]}, root, manifest
