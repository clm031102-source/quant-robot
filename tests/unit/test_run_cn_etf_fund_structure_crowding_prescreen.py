import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.storage.fingerprints import sha256_file
from quant_robot.validation.single_prescreen_authorization import (
    build_single_prescreen_authorization,
    claim_single_prescreen_authorization,
    write_single_prescreen_authorization,
)
from scripts.run_cn_etf_fund_structure_crowding_prescreen import (
    DEFAULT_CONFIG,
    FROZEN_HASHES,
    PreparedPrescreenInputs,
    PrescreenRuntime,
    _load_and_validate_config,
    run_cn_etf_fund_structure_crowding_prescreen_cli,
)
from scripts.run_cn_etf_fund_structure_crowding_preregistration import (
    PRESCREEN_STAGE,
    SOURCE_KEYS,
)


class RunCnEtfFundStructureCrowdingPrescreenTests(unittest.TestCase):
    def test_tampered_config_fails_before_any_label_read(self):
        payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        payload["candidate"]["share_lookback"] = 10
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.make_forward_returns"
            ) as labels:
                with self.assertRaisesRegex(ValueError, "config hash mismatch"):
                    _load_and_validate_config(
                        path,
                        expected_sha256=FROZEN_HASHES["config"],
                    )
            labels.assert_not_called()

    def test_claim_occurs_after_unlabeled_prepare_and_before_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            calls = []
            with patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.preflight_cn_etf_fund_structure_crowding_prescreen",
                side_effect=lambda **_: calls.append("preflight") or fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen._prepare_unlabeled_inputs",
                side_effect=lambda *_: calls.append("prepare") or _prepared(),
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.claim_single_prescreen_authorization",
                side_effect=lambda **kwargs: calls.append("claim")
                or claim_single_prescreen_authorization(**kwargs),
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.make_forward_returns",
                side_effect=lambda *_args, **_kwargs: calls.append("labels") or _labels(),
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen._summarize_prepared",
                side_effect=lambda *_args: calls.append("summary") or _result(),
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.write_cn_etf_fund_structure_crowding_prescreen",
                side_effect=lambda output, result: calls.append("write")
                or _write_artifacts(Path(output)),
            ):
                result = run_cn_etf_fund_structure_crowding_prescreen_cli(
                    mode="execute",
                    runtime=fixture["runtime"],
                )

            self.assertEqual(
                calls,
                ["preflight", "prepare", "claim", "labels", "summary", "write"],
            )
            self.assertTrue(fixture["runtime"].ledger_path.is_file())
            self.assertEqual(result["status"], "close_family_zero_budget")

    def test_preclaim_failure_does_not_consume_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            with patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen.preflight_cn_etf_fund_structure_crowding_prescreen",
                return_value=fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_fund_structure_crowding_prescreen._prepare_unlabeled_inputs",
                side_effect=ValueError("prepare failed"),
            ):
                with self.assertRaisesRegex(ValueError, "prepare failed"):
                    run_cn_etf_fund_structure_crowding_prescreen_cli(
                        mode="execute",
                        runtime=fixture["runtime"],
                    )
            self.assertFalse(fixture["runtime"].ledger_path.exists())


def _fixture(root: Path) -> dict:
    ledger = root / "ledger.json"
    authorization = root / "authorization.json"
    source_hashes = {
        key: f"{index + 1:x}" * 64
        for index, key in enumerate(SOURCE_KEYS)
    }
    packet = build_single_prescreen_authorization(
        registration_date="2026-07-28",
        candidate_name="etf_residual_share_creation_crowding_reversal_20",
        preregistration_config_sha256=FROZEN_HASHES["config"],
        preregistration_result_sha256="b" * 64,
        source_hashes=source_hashes,
        execution_ledger_path=ledger,
        allowed_stage=PRESCREEN_STAGE,
        source_hash_keys=SOURCE_KEYS,
    )
    write_single_prescreen_authorization(authorization, packet)
    runtime = PrescreenRuntime(
        config_path=DEFAULT_CONFIG,
        preregistration_result_path=root / "preregistration.json",
        authorization_path=authorization,
        scheduler_path=root / "scheduler.json",
        ledger_path=ledger,
        output_dir=root / "output",
    )
    return {
        "runtime": runtime,
        "preflight": {
            "status": "ready_unconsumed",
            "config": json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8")),
            "config_sha256": FROZEN_HASHES["config"],
            "preregistration_result_sha256": "b" * 64,
            "authorization_sha256": sha256_file(authorization),
            "authorization_id": packet["authorization_id"],
            "source_hashes": source_hashes,
            "reference_names": ["reference"],
            "runtime": runtime,
        },
    }


def _prepared() -> PreparedPrescreenInputs:
    columns = [
        "date",
        "asset_id",
        "market",
        "factor_name",
        "factor_value",
        "lookback_window",
    ]
    return PreparedPrescreenInputs(
        bars=pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2023-01-02"),
                    "asset_id": "A",
                    "market": "CN_ETF",
                    "adj_close": 1.0,
                }
            ]
        ),
        factors=pd.DataFrame(columns=columns),
        references=pd.DataFrame(columns=columns),
        direct_exposures=pd.DataFrame(columns=columns),
        adv20=pd.DataFrame(columns=["date", "asset_id", "market", "adv20"]),
        metadata={},
    )


def _labels() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "horizon",
            "execution_lag",
            "forward_return",
            "entry_date",
            "exit_date",
        ]
    )


def _result() -> dict:
    return {
        "stage": PRESCREEN_STAGE,
        "status": "close_family_zero_budget",
        "decision": {"primary_passed": False},
        "results": [],
    }


def _write_artifacts(output: Path) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "result.json"
    path.write_text("{}\n", encoding="utf-8")
    return {"json": path}


if __name__ == "__main__":
    unittest.main()
