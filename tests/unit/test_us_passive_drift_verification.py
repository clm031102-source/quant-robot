import copy
import unittest

from quant_robot.research import us_passive_drift_allocation as engine
from quant_robot.research import us_passive_drift_verification as verify
from tests.unit.test_us_low_unit_allocation import fixture
from tests.unit.test_us_passive_drift_allocation import set_price


class DriftVerificationTests(unittest.TestCase):
    def test_both_costs_with_split_and_terminal_receivable(self):
        f = fixture(end="2001-03-30")
        for role in ("primary", "stress"):
            account = engine.run_artificial(f, role)
            result = verify.verify_account(f, account)
            self.assertEqual(result["status"], "recorded_account_consistent")
            self.assertTrue(result["recorded_fixed_order_coverage_checked"])

    def test_risk_exit_reentry_and_continuous_peak(self):
        f = fixture(split=False)
        for row in f["days"]:
            if row["date"] >= "2001-02-08":
                for asset in f["assets"]:
                    set_price(row, asset, "30")
        account = engine.run_artificial(f)
        self.assertEqual(verify.verify_account(f, account)["status"], "recorded_account_consistent")

    def test_missing_leg_and_dividend_cash_are_not_rebalanced(self):
        f = fixture(split=False)
        next(r for r in f["days"] if r["date"] == "2001-02-06")["execution"]["SPYM"]["buy_blocked"] = True
        f["dividends"] = [dict(id="invented_dividend", symbol="EFA", ex_date="2001-02-08", amount_per_share="2")]
        account = engine.run_artificial(f)
        self.assertEqual(verify.verify_account(f, account)["status"], "recorded_account_consistent")

    def test_changed_policy_or_skip_record_is_rejected(self):
        f = fixture(split=False)
        account = engine.run_artificial(f)
        for change in ("identity", "status", "wallet", "count", "claim"):
            mutated = copy.deepcopy(account)
            event = next(e for e in mutated["monthly_events"] if e["status"] == "skipped_passive_drift_while_invested")
            if change == "identity":
                mutated["holding_policy"] = "ordinary_monthly_rebalance"
            elif change == "status":
                event["status"] = "skipped_cash_risk_or_terminal"
            elif change == "wallet":
                event["pre_decision_balances"]["quantities"]["SPYM"] = 0
            elif change == "count":
                mutated["summary"]["skipped_invested_month_ends"] += 1
            else:
                mutated["numeric_marker_sha256"] = "f"*64
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify.verify_account(f, mutated)

    def test_missing_mandatory_risk_or_terminal_intent_is_rejected(self):
        f = fixture(split=False)
        account = engine.run_artificial(f)
        account["intents"].pop()
        with self.assertRaises(ValueError):
            verify.verify_account(f, account)


if __name__ == "__main__":
    unittest.main()
