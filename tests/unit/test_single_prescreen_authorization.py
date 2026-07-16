import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.fingerprints import sha256_file
from quant_robot.validation.single_prescreen_authorization import (
    build_single_prescreen_authorization,
    claim_single_prescreen_authorization,
    validate_single_prescreen_authorization,
    write_single_prescreen_authorization,
)


class SinglePrescreenAuthorizationTests(unittest.TestCase):
    def test_builds_deterministic_hash_bound_single_use_packet(self) -> None:
        first = _packet()
        second = _packet()

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "authorized_single_prescreen")
        self.assertEqual(first["allowed_task"], "factor_batch")
        self.assertEqual(
            first["allowed_stage"],
            "cn_etf_dynamic_peer_dislocation_prescreen",
        )
        self.assertEqual(first["max_executions"], 1)
        self.assertTrue(first["execution_ledger_required"])
        self.assertEqual(
            first["execution_ledger_path"],
            "data/reports/fixture_single_prescreen_ledger.json",
        )
        self.assertEqual(len(first["authorization_id"]), 64)
        for field in _prohibited_boundaries():
            self.assertFalse(first[field])

    def test_invalid_identity_hash_fails_during_build(self) -> None:
        with self.assertRaisesRegex(ValueError, "preregistration config SHA-256"):
            build_single_prescreen_authorization(
                registration_date="2026-07-16",
                candidate_name=_candidate(),
                preregistration_config_sha256="not-a-hash",
                preregistration_result_sha256="b" * 64,
                source_hashes=_source_hashes(),
                execution_ledger_path="data/reports/fixture_single_prescreen_ledger.json",
            )

    def test_validate_rejects_candidate_config_and_packet_hash_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet_path = Path(tmp) / "authorization.json"
            write_single_prescreen_authorization(packet_path, _packet())
            packet_sha256 = sha256_file(packet_path)
            cases = (
                {
                    "expected_candidate_name": "wrong_candidate",
                    "expected_config_sha256": "a" * 64,
                    "expected_packet_sha256": packet_sha256,
                    "message": "candidate mismatch",
                },
                {
                    "expected_candidate_name": _candidate(),
                    "expected_config_sha256": "e" * 64,
                    "expected_packet_sha256": packet_sha256,
                    "message": "config hash mismatch",
                },
                {
                    "expected_candidate_name": _candidate(),
                    "expected_config_sha256": "a" * 64,
                    "expected_packet_sha256": "f" * 64,
                    "message": "authorization hash mismatch",
                },
            )
            for case in cases:
                with self.subTest(message=case["message"]):
                    with self.assertRaisesRegex(ValueError, case.pop("message")):
                        validate_single_prescreen_authorization(
                            packet_path=packet_path,
                            context="fixture prescreen",
                            **case,
                        )

    def test_validate_rejects_enabled_downstream_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for field in ("final_holdout_allowed", "live_boundary_allowed"):
                with self.subTest(field=field):
                    packet_path = Path(tmp) / f"{field}.json"
                    packet = _packet()
                    packet[field] = True
                    write_single_prescreen_authorization(packet_path, packet)

                    with self.assertRaisesRegex(ValueError, f"boundary enabled: {field}"):
                        validate_single_prescreen_authorization(
                            packet_path=packet_path,
                            expected_candidate_name=_candidate(),
                            expected_config_sha256="a" * 64,
                            expected_packet_sha256=sha256_file(packet_path),
                            context="fixture prescreen",
                        )

    def test_validate_rejects_tampered_authorization_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet_path = Path(tmp) / "authorization.json"
            packet = _packet()
            packet["authorization_id"] = "f" * 64
            write_single_prescreen_authorization(packet_path, packet)

            with self.assertRaisesRegex(ValueError, "authorization identity mismatch"):
                validate_single_prescreen_authorization(
                    packet_path=packet_path,
                    expected_candidate_name=_candidate(),
                    expected_config_sha256="a" * 64,
                    expected_packet_sha256=sha256_file(packet_path),
                    context="fixture prescreen",
                )

    def test_first_claim_succeeds_and_second_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "authorization.json"
            ledger_path = root / "claims.json"
            write_single_prescreen_authorization(
                packet_path,
                _packet(execution_ledger_path=str(ledger_path)),
            )
            kwargs = {
                "packet_path": packet_path,
                "ledger_path": ledger_path,
                "expected_candidate_name": _candidate(),
                "expected_config_sha256": "a" * 64,
                "expected_packet_sha256": sha256_file(packet_path),
                "context": "fixture prescreen",
            }

            receipt = claim_single_prescreen_authorization(**kwargs)

            self.assertTrue(receipt["execution_claim_recorded"])
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["schema_version"], 1)
            self.assertIn(receipt["authorization_id"], ledger["claims"])
            with self.assertRaisesRegex(ValueError, "already consumed"):
                claim_single_prescreen_authorization(**kwargs)

    def test_preexisting_lock_rejects_claim_without_removing_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "authorization.json"
            ledger_path = root / "claims.json"
            lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
            write_single_prescreen_authorization(
                packet_path,
                _packet(execution_ledger_path=str(ledger_path)),
            )
            lock_path.write_text("held", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ledger is locked"):
                claim_single_prescreen_authorization(
                    packet_path=packet_path,
                    ledger_path=ledger_path,
                    expected_candidate_name=_candidate(),
                    expected_config_sha256="a" * 64,
                    expected_packet_sha256=sha256_file(packet_path),
                    context="fixture prescreen",
                )

            self.assertTrue(lock_path.is_file())
            self.assertFalse(ledger_path.exists())

    def test_claim_rejects_a_ledger_path_not_bound_to_the_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "authorization.json"
            bound_ledger = root / "bound_claims.json"
            alternate_ledger = root / "alternate_claims.json"
            write_single_prescreen_authorization(
                packet_path,
                _packet(execution_ledger_path=str(bound_ledger)),
            )

            with self.assertRaisesRegex(ValueError, "ledger path mismatch"):
                claim_single_prescreen_authorization(
                    packet_path=packet_path,
                    ledger_path=alternate_ledger,
                    expected_candidate_name=_candidate(),
                    expected_config_sha256="a" * 64,
                    expected_packet_sha256=sha256_file(packet_path),
                    context="fixture prescreen",
                )

            self.assertFalse(bound_ledger.exists())
            self.assertFalse(alternate_ledger.exists())


def _packet(
    *,
    execution_ledger_path: str = "data/reports/fixture_single_prescreen_ledger.json",
) -> dict:
    return build_single_prescreen_authorization(
        registration_date="2026-07-16",
        candidate_name=_candidate(),
        preregistration_config_sha256="a" * 64,
        preregistration_result_sha256="b" * 64,
        source_hashes=_source_hashes(),
        execution_ledger_path=execution_ledger_path,
    )


def _candidate() -> str:
    return "etf_dynamic_peer_residual_dislocation_reversal_5_60"


def _source_hashes() -> dict[str, str]:
    return {
        "source_config": "c" * 64,
        "source_result": "d" * 64,
        "mapping": "e" * 64,
    }


def _prohibited_boundaries() -> tuple[str, ...]:
    return (
        "portfolio_grid_allowed",
        "walk_forward_allowed",
        "final_holdout_allowed",
        "promotion_allowed",
        "paper_signal_allowed",
        "broker_connection_allowed",
        "account_read_allowed",
        "order_placement_allowed",
        "live_boundary_allowed",
    )


if __name__ == "__main__":
    unittest.main()
