"""Failure/once-only boundaries using invented callback results, never market data."""
import importlib.util
from datetime import datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("low_unit_controller_test", ROOT / "scripts/run_us_low_unit_allocation.py")
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.metadata = dict(blockers=[], numeric_decode_started=False)
        metadata = controller.save(self.output / "metadata.json", self.metadata)
        self.packet = dict(method=dict(sha256="a"*64), metadata=metadata,
            budget=dict(qa_close_values=5, fixture_builds=1, account_roles=list(controller.ROLES), downloads=0, reruns=0))
        self.proof = dict(registration=dict(sha256="b"*64), reviews={}, release={})
        self.calls = []
        for name, value in (
            ("admit", lambda _: (self.packet, {}, self.proof)),
            ("prepare_sources", lambda _: object()),
            ("metadata_summary", lambda _: self.metadata),
            ("run_unit_qa", self.qa),
            ("build_fixtures", self.fixtures),
            ("run_known_history", self.account),
            ("verify_account", self.check),
        ):
            self.addCleanup(patch.stopall)
            patch.object(controller, name, side_effect=value).start()

    def qa(self, _):
        self.assertTrue((self.output / "financial_decode_started.json").is_file())
        self.calls.append("QA")
        return dict(status="passed", converted_close_count=5)

    def fixtures(self, _, provenance):
        self.assertTrue(provenance["constructed_from_market_data"])
        self.calls.append("fixtures")
        return dict(old=dict(invented=True, name="old", assets=["OLD_A"]),
                    new=dict(invented=True, name="new", assets=["NEW_A"]))

    def account(self, fixture, role, **claims):
        self.assertEqual(fixture["name"], "new" if role.startswith("new_") else "old")
        self.assertTrue((self.output / "accounts" / f"{role}_claim.json").is_file())
        self.assertEqual(claims["method_sha256"], "a"*64)
        self.calls.append(role)
        return dict(role=role, assets=fixture["assets"], summary=dict(cash_and_locked_sale_proceeds_net_profit="2.00",
            observed_maxDD=".05", terminal_inventory_closed=True))

    def check(self, fixture, account, **claims):
        saved = self.output / "accounts" / (account["role"] + ".json")
        self.assertEqual(json.loads(saved.read_bytes()), account)
        self.assertEqual(claims["expected_registration"], "b"*64)
        self.assertEqual(claims["expected_marker"], controller.pin(self.output / "financial_decode_started.json")["sha256"])
        self.calls.append("verify_"+account["role"])
        return dict(status="recorded_account_consistent")

    def test_exact_five_accounts_saved_before_independent_check(self):
        outcome = json.loads(controller.bound(controller.run(self.output)))
        expected = ["QA", "fixtures"]
        for role in controller.ROLES:
            expected.extend((role, "verify_"+role))
        self.assertEqual(self.calls, expected)
        self.assertTrue(outcome["fixed_conditional_evaluation_passed"])
        self.assertEqual(outcome["accounts_run"], 5)
        self.assertFalse(outcome["qualified"])

    def test_consumed_claim_prevents_any_second_qa_or_account(self):
        controller.run(self.output)
        before = self.calls[:]
        with self.assertRaises(FileExistsError):
            controller.run(self.output)
        self.assertEqual(before, self.calls)

    def test_failed_qa_never_builds_or_runs(self):
        controller.run_unit_qa.side_effect = lambda _: dict(status="failed", converted_close_count=5)
        outcome = json.loads(controller.bound(controller.run(self.output)))
        self.assertEqual(outcome["status"], "closed_failed_fixed_unit_QA")
        self.assertFalse((self.output / "fixture_old.json").exists())
        self.assertEqual(self.calls, [])

    def test_changed_structure_fails_before_numeric_marker(self):
        controller.metadata_summary.side_effect = lambda _: dict(blockers=["changed"])
        with self.assertRaisesRegex(ValueError, "source_structure_changed"):
            controller.run(self.output)
        self.assertFalse((self.output / "financial_decode_started.json").exists())
        self.assertEqual(self.calls, [])

    def test_engine_failure_preserves_finished_account_and_never_retries(self):
        def failing(fixture, role, **claims):
            if role == "old_stress":
                self.calls.append("failed_old_stress")
                raise ValueError("injected_failure")
            return self.account(fixture, role, **claims)
        controller.run_known_history.side_effect = failing
        with self.assertRaisesRegex(ValueError, "injected_failure"):
            controller.run(self.output)
        failure = json.loads((self.output / "numeric_failure.json").read_bytes())
        self.assertEqual(list(failure["completed_accounts"]), ["old_primary"])
        self.assertNotIn("new_primary", self.calls)
        self.assertTrue((self.output / "accounts/old_stress_claim.json").exists())

    def test_independent_failure_stops_next_account(self):
        controller.verify_account.side_effect = ValueError("injected_cash_mismatch")
        with self.assertRaisesRegex(ValueError, "injected_cash_mismatch"):
            controller.run(self.output)
        self.assertEqual(self.calls, ["QA", "fixtures", "old_primary"])
        self.assertTrue((self.output / "accounts/old_primary.json").exists())
        self.assertFalse((self.output / "accounts/old_stress_claim.json").exists())

    def test_fixture_drift_after_check_is_detected(self):
        def drift(fixture, account, **claims):
            answer = self.check(fixture, account, **claims)
            if account["role"] == "old_primary":
                (self.output / "fixture_old.json").write_bytes(b"{}")
            return answer
        controller.verify_account.side_effect = drift
        with self.assertRaisesRegex(ValueError, "changed_input"):
            controller.run(self.output)
        self.assertNotIn("new_primary", self.calls)
        self.assertFalse((self.output / "outcome.json").exists())

    def test_prior_verification_drift_prevents_completed_result(self):
        def drift(fixture, account, **claims):
            answer = self.check(fixture, account, **claims)
            if account["role"] == "cash":
                (self.output / "accounts/old_primary_verification.json").write_bytes(b"{}")
            return answer
        controller.verify_account.side_effect = drift
        with self.assertRaisesRegex(ValueError, "changed_input"):
            controller.run(self.output)
        self.assertIn("cash", self.calls)
        self.assertFalse((self.output / "result.json").exists())


class ActionCoverageTests(unittest.TestCase):
    def test_complete_months_checked_without_quote_conversion(self):
        dates = [(2020, 12)] + [(y, m) for y in range(2021, 2027) for m in range(1, 13)
                               if (y, m) <= (2026, 11)]
        timestamps = [int(datetime(y, m, 1, tzinfo=ZoneInfo("America/New_York")).timestamp()) for y, m in dates]
        def body(ts):
            return json.dumps(dict(chart=dict(result=[dict(timestamp=ts,
                indicators=dict(quote=[dict(close=["DO_NOT_CONVERT"]*len(ts))]))]))).encode()
        self.assertEqual(controller.require_complete_action_months(body(timestamps))["months"], 72)
        stub = int(datetime(2026, 11, 6, 16, tzinfo=ZoneInfo("America/New_York")).timestamp())
        self.assertEqual(controller.require_complete_action_months(body(timestamps+[stub]))[
            "trailing_capture_session_stub"], "2026-11-06")
        with self.assertRaisesRegex(ValueError, "complete_actions_through_capture"):
            controller.require_complete_action_months(body(timestamps[:-1]+[stub]))
        with self.assertRaisesRegex(ValueError, "complete_actions_through_capture"):
            controller.require_complete_action_months(body(timestamps[:-1]))
        with self.assertRaisesRegex(ValueError, "complete_actions_through_capture"):
            controller.require_complete_action_months(body(timestamps[:10]+timestamps[11:]))


if __name__ == "__main__":
    unittest.main()
