import copy
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("drift_controller_test", ROOT / "scripts/run_us_passive_drift.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def summary(profit="20.00", cost="12.00"):
    return dict(cash_and_locked_sale_proceeds_net_profit=profit, same_path_total_execution_cost=cost,
        observed_maxDD=".10", book_CAGR=".03", average_market_deployment_ratio=".80",
        terminal_inventory_closed=True, fills=8)


class DriftControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.fixture = dict(assets=m.ASSETS, provenance=dict(constructed_from_market_data=True), invented=True)
        fixture_ref = m.save(self.directory / "invented_fixture.json", self.fixture)
        self.packet = dict(method=dict(sha256="a"*64), comparison=dict(sha256="b"*64),
                           saved_evidence=dict(fixture=fixture_ref))
        self.baseline = dict(summaries={"new_"+r: summary("10.00", "20.00") for r in m.ROLES})
        self.proof = dict(registration=dict(sha256="c"*64), reviews={}, release={})
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(m, "admit", side_effect=self.admit).start()
        patch.object(m, "run_known_history", side_effect=self.account).start()
        patch.object(m, "verify_account", side_effect=self.verify).start()

    def admit(self, _):
        m.bound(self.packet["saved_evidence"]["fixture"])
        return self.packet, self.baseline, self.proof

    def account(self, fixture, role, **claims):
        self.assertTrue((self.directory / "financial_started.json").exists())
        self.assertTrue((self.directory / f"{role}_claim.json").exists())
        self.assertEqual(fixture, self.fixture)
        self.assertEqual(claims["method_sha256"], "a"*64)
        self.calls.append(role)
        return dict(role="new_"+role, scenario_role=role, assets=m.ASSETS, summary=summary())

    def verify(self, fixture, account, **claims):
        role = account["scenario_role"]
        self.assertEqual(json.loads((self.directory / f"{role}_account.json").read_bytes()), account)
        self.assertEqual(claims["expected_registration"], "c"*64)
        self.assertEqual(claims["expected_marker"], m.pin(self.directory / "financial_started.json")["sha256"])
        self.calls.append("verify_"+role)
        return dict(status="recorded_account_consistent")

    def test_two_new_accounts_only_and_no_second_attempt(self):
        outcome = json.loads(m.bound(m.run(self.directory)))
        self.assertEqual(self.calls, ["primary", "verify_primary", "stress", "verify_stress"])
        result = json.loads(m.bound(outcome["result"]))
        self.assertEqual(result["account_count"], 2)
        self.assertEqual(result["baseline_account_reruns"], 0)
        self.assertTrue(result["stress_practical_improvement"])
        self.assertFalse(result["qualified"])
        with self.assertRaises(FileExistsError):
            m.run(self.directory)
        self.assertEqual(len(self.calls), 4)

    def test_second_engine_failure_keeps_first_evidence(self):
        def fail(fixture, role, **claims):
            if role == "stress":
                raise ValueError("injected_engine_failure")
            return self.account(fixture, role, **claims)
        m.run_known_history.side_effect = fail
        with self.assertRaisesRegex(ValueError, "injected_engine_failure"):
            m.run(self.directory)
        failure = json.loads((self.directory / "failure.json").read_bytes())
        self.assertEqual(list(failure["completed_accounts"]), ["primary"])
        self.assertTrue((self.directory / "primary_verification.json").exists())
        self.assertFalse((self.directory / "result.json").exists())

    def test_scenario_identity_cannot_be_swapped(self):
        def wrong(fixture, role, **claims):
            result = self.account(fixture, role, **claims)
            result["role"] = "new_stress"
            return result
        m.run_known_history.side_effect = wrong
        with self.assertRaisesRegex(ValueError, "registered_scenario_identity"):
            m.run(self.directory)
        self.assertEqual(self.calls, ["primary"])

    def test_saved_fixture_drift_closes_before_second_account(self):
        def drift(fixture, account, **claims):
            check = self.verify(fixture, account, **claims)
            (self.directory / "invented_fixture.json").write_bytes(b"{}")
            return check
        m.verify_account.side_effect = drift
        with self.assertRaisesRegex(ValueError, "changed_input"):
            m.run(self.directory)
        self.assertEqual(self.calls, ["primary", "verify_primary"])

    def test_saved_verification_drift_prevents_completion(self):
        def drift(fixture, account, **claims):
            check = self.verify(fixture, account, **claims)
            if account["scenario_role"] == "stress":
                (self.directory / "primary_verification.json").write_bytes(b"{}")
            return check
        m.verify_account.side_effect = drift
        with self.assertRaisesRegex(ValueError, "changed_input"):
            m.run(self.directory)
        self.assertFalse((self.directory / "outcome.json").exists())

    def test_cost_saving_alone_is_not_practical_improvement(self):
        summaries = {r: summary("9.00", "1.00") for r in m.ROLES}
        answer = m.comparison_summary(summaries, self.baseline)
        self.assertTrue(answer["fixed_conditional_evaluation_passed"])
        self.assertFalse(answer["stress_practical_improvement"])
        self.assertEqual(answer["differences_from_saved_monthly"]["stress"]["cash_and_locked_sale_proceeds_net_profit"], "-1.00")


if __name__ == "__main__":
    unittest.main()
