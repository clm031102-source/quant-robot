import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.storage.fingerprints import sha256_file
from quant_robot.validation.single_prescreen_authorization import (
    build_single_prescreen_authorization,
    write_single_prescreen_authorization,
)
from scripts.run_cn_etf_dynamic_peer_dislocation_prescreen import (
    DEFAULT_CONFIG,
    FROZEN_HASHES,
    PreparedPrescreenInputs,
    PrescreenRuntime,
    _load_and_validate_config,
    run_cn_etf_dynamic_peer_dislocation_prescreen_cli,
)


class RunCnEtfDynamicPeerDislocationPrescreenTests(unittest.TestCase):
    def test_tampered_config_fails_before_market_or_label_read(self) -> None:
        payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        payload["candidate"]["beta_window"] = 121
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.load_processed_bars"
            ) as load_bars, patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.make_forward_returns"
            ) as make_labels:
                with self.assertRaisesRegex(ValueError, "config hash mismatch"):
                    _load_and_validate_config(
                        path,
                        expected_sha256=FROZEN_HASHES["config"],
                    )

        load_bars.assert_not_called()
        make_labels.assert_not_called()

    def test_execution_claims_after_unlabeled_prepare_and_before_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            calls: list[str] = []
            prepared = _prepared()

            with patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.preflight_cn_etf_dynamic_peer_dislocation_prescreen",
                side_effect=lambda **_: calls.append("preflight") or fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen._prepare_unlabeled_inputs",
                side_effect=lambda *_: calls.append("prepare") or prepared,
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.claim_single_prescreen_authorization",
                side_effect=lambda **kwargs: calls.append("claim") or fixture["claim"](**kwargs),
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.make_forward_returns",
                side_effect=lambda *_args, **_kwargs: calls.append("labels") or _labels(),
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.summarize_cn_etf_dynamic_peer_dislocation_prescreen",
                side_effect=lambda *_args, **_kwargs: calls.append("summary") or _result(),
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.write_cn_etf_dynamic_peer_dislocation_prescreen",
                side_effect=lambda output, result: calls.append("write")
                or _write_dummy_artifacts(Path(output)),
            ):
                observed = run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
                    mode="execute",
                    runtime=fixture["runtime"],
                )

            self.assertEqual(
                calls,
                ["preflight", "prepare", "claim", "labels", "summary", "write"],
            )
            self.assertTrue(fixture["runtime"].ledger_path.is_file())
            ledger = json.loads(fixture["runtime"].ledger_path.read_text(encoding="utf-8"))
            self.assertIn(fixture["authorization_id"], ledger["claims"])
            self.assertEqual(observed["status"], "primary_passed_backfill_required")
            self.assertTrue((fixture["runtime"].output_dir / "execution_outcome.json").is_file())

    def test_preclaim_failure_leaves_authorization_unconsumed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            with patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.preflight_cn_etf_dynamic_peer_dislocation_prescreen",
                return_value=fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen._prepare_unlabeled_inputs",
                side_effect=ValueError("unlabeled build failed"),
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.make_forward_returns"
            ) as labels:
                with self.assertRaisesRegex(ValueError, "unlabeled build failed"):
                    run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
                        mode="execute",
                        runtime=fixture["runtime"],
                    )

            self.assertFalse(fixture["runtime"].ledger_path.exists())
            labels.assert_not_called()

    def test_postclaim_failure_consumes_authorization_and_writes_terminal_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            with patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.preflight_cn_etf_dynamic_peer_dislocation_prescreen",
                return_value=fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen._prepare_unlabeled_inputs",
                return_value=_prepared(),
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.make_forward_returns",
                side_effect=RuntimeError("label build failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "label build failed"):
                    run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
                        mode="execute",
                        runtime=fixture["runtime"],
                    )

            self.assertTrue(fixture["runtime"].ledger_path.is_file())
            outcome = json.loads(
                (fixture["runtime"].output_dir / "execution_outcome.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(outcome["status"], "terminal_failure_after_claim")
            self.assertEqual(outcome["error_type"], "RuntimeError")
            self.assertIn("label build failed", outcome["error"])

    def test_preflight_mode_never_prepares_data_or_reads_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            with patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.preflight_cn_etf_dynamic_peer_dislocation_prescreen",
                return_value=fixture["preflight"],
            ), patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen._prepare_unlabeled_inputs"
            ) as prepare, patch(
                "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.make_forward_returns"
            ) as labels:
                observed = run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
                    mode="preflight",
                    runtime=fixture["runtime"],
                )

            self.assertEqual(observed["status"], "ready_unconsumed")
            prepare.assert_not_called()
            labels.assert_not_called()

    def test_rejects_unknown_execution_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "mode must be preflight or execute"):
            run_cn_etf_dynamic_peer_dislocation_prescreen_cli(mode="retry")

    def test_fixture_authorized_end_to_end_is_analytically_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            runs = []
            for tmp in (first_tmp, second_tmp):
                fixture = _fixture(Path(tmp))
                fixture["preflight"]["config"] = _e2e_config()
                prepared = _e2e_prepared()
                with patch(
                    "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen.preflight_cn_etf_dynamic_peer_dislocation_prescreen",
                    return_value=fixture["preflight"],
                ), patch(
                    "scripts.run_cn_etf_dynamic_peer_dislocation_prescreen._prepare_unlabeled_inputs",
                    return_value=prepared,
                ):
                    result = run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
                        mode="execute",
                        runtime=fixture["runtime"],
                    )
                runs.append(result)

            self.assertEqual(runs[0]["status"], "primary_passed_backfill_required")
            self.assertEqual(len(runs[0]["results"]), 2)
            self.assertTrue(runs[0]["data_window"]["market_calendar_alignment_required"])
            analytical_names = sorted(
                set(runs[0]["artifacts"])
                - {"json", "hash_manifest", "execution_outcome"}
            )
            for name in analytical_names:
                self.assertEqual(
                    Path(runs[0]["artifacts"][name]).read_bytes(),
                    Path(runs[1]["artifacts"][name]).read_bytes(),
                    msg=name,
                )


def _fixture(root: Path) -> dict[str, object]:
    ledger_path = root / "fixture_ledger.json"
    packet_path = root / "authorization.json"
    output_dir = root / "output"
    config_sha256 = FROZEN_HASHES["config"]
    result_sha256 = "b" * 64
    source_hashes = {
        "mapping": "c" * 64,
        "source_config": "d" * 64,
        "source_result": "e" * 64,
    }
    packet = build_single_prescreen_authorization(
        registration_date="2026-07-16",
        candidate_name="etf_dynamic_peer_residual_dislocation_reversal_5_60",
        preregistration_config_sha256=config_sha256,
        preregistration_result_sha256=result_sha256,
        source_hashes=source_hashes,
        execution_ledger_path=ledger_path,
    )
    write_single_prescreen_authorization(packet_path, packet)
    runtime = PrescreenRuntime(
        config_path=DEFAULT_CONFIG,
        preregistration_result_path=root / "preregistration.json",
        authorization_path=packet_path,
        scheduler_path=root / "scheduler.json",
        ledger_path=ledger_path,
        output_dir=output_dir,
    )
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    preflight = {
        "stage": "cn_etf_dynamic_peer_dislocation_prescreen_preflight",
        "status": "ready_unconsumed",
        "config": payload,
        "config_sha256": config_sha256,
        "preregistration_result_sha256": result_sha256,
        "authorization_sha256": sha256_file(packet_path),
        "authorization_id": packet["authorization_id"],
        "source_hashes": source_hashes,
        "reference_names": ["reference"],
        "runtime": runtime,
        "quant_pm_gate": {"status": "ready", "mode": "single_prescreen_only"},
    }
    from quant_robot.validation.single_prescreen_authorization import (
        claim_single_prescreen_authorization,
    )

    return {
        "runtime": runtime,
        "preflight": preflight,
        "claim": claim_single_prescreen_authorization,
        "authorization_id": packet["authorization_id"],
    }


def _prepared() -> PreparedPrescreenInputs:
    bars = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2023-01-02"),
                "asset_id": "A00",
                "market": "CN_ETF",
                "adj_close": 1.0,
            }
        ]
    )
    empty_factor = pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "lookback_window",
        ]
    )
    return PreparedPrescreenInputs(
        bars=bars,
        factors=empty_factor,
        references=empty_factor.copy(),
        direct_exposures=empty_factor.copy(),
        adv20=pd.DataFrame(columns=["date", "asset_id", "market", "adv20"]),
        metadata={"history_rows": 1},
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


def _result() -> dict[str, object]:
    return {
        "stage": "cn_etf_dynamic_peer_dislocation_prescreen",
        "status": "primary_passed_backfill_required",
        "summary": {},
        "results": [],
        "decision": {"primary_passed": True},
    }


def _write_dummy_artifacts(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / "result.json",
        "markdown": output_dir / "result.md",
    }
    paths["json"].write_text("{}\n", encoding="utf-8")
    paths["markdown"].write_text("# result\n", encoding="utf-8")
    return paths


def _e2e_config() -> dict[str, object]:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    evaluation = payload["evaluation"]
    evaluation.update(
        {
            "minimum_daily_cross_section": 10,
            "minimum_ic_observations": 2,
            "minimum_yearly_ic_observations": 2,
            "minimum_usable_years": 1,
            "newey_west_alpha": 1.0,
            "fdr_alpha": 1.0,
            "minimum_icir": 0.0,
            "minimum_positive_ic_rate": 0.5,
            "minimum_positive_year_rate": 0.5,
        }
    )
    return payload


def _e2e_prepared() -> PreparedPrescreenInputs:
    dates = pd.bdate_range("2023-01-02", periods=30)
    signal_dates = dates[:4]
    bar_rows: list[dict[str, object]] = []
    factor_rows: list[dict[str, object]] = []
    reference_rows: list[dict[str, object]] = []
    exposure_rows: list[dict[str, object]] = []
    adv_rows: list[dict[str, object]] = []
    for asset_index in range(10):
        asset_id = f"A{asset_index:02d}"
        price = 10.0 + asset_index
        for signal_date in dates:
            price *= 1.0 + 0.0005 * (asset_index + 1)
            bar_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adj_close": price,
                }
            )
        for day_index, signal_date in enumerate(signal_dates):
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "factor_name": "etf_dynamic_peer_residual_dislocation_reversal_5_60",
                    "factor_value": float(asset_index),
                    "lookback_window": 185,
                }
            )
            reference_value = float(asset_index if day_index % 2 == 0 else 9 - asset_index)
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "factor_name": "reference",
                    "factor_value": reference_value,
                    "lookback_window": 20,
                }
            )
            for exposure_name in (
                "market_beta_120",
                "residual_volatility_60",
                "momentum_60",
                "short_return_5",
                "log_adv20",
            ):
                exposure_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": exposure_name,
                        "factor_value": reference_value,
                        "lookback_window": 60,
                    }
                )
            adv_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adv20": 20_000_000.0,
                }
            )
    return PreparedPrescreenInputs(
        bars=pd.DataFrame(bar_rows),
        factors=pd.DataFrame(factor_rows),
        references=pd.DataFrame(reference_rows),
        direct_exposures=pd.DataFrame(exposure_rows),
        adv20=pd.DataFrame(adv_rows),
        metadata={"history_rows": len(bar_rows)},
    )


if __name__ == "__main__":
    unittest.main()
