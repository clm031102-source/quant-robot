from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, Inexact, ROUND_DOWN, getcontext, localcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.research import repo_cash_contract as m


def event(result, kind, n=0):
    return [x for x in result["events"] if x["kind"] == kind][n]


class RepoCashContractTests(unittest.TestCase):
    def test_normal_hand_calculation_and_cash_attributes(self):
        r = m.run_synthetic_contract(m.synthetic_fixture())
        # Invented P9000, Q3.65, Fri inclusive to Mon exclusive: 3 days.
        # 9000/100*3.65*3/365 = 2.70; 2.70-.20-.10-.05 = 2.35.
        self.assertEqual(r["model_clocks"]["days"], 3)
        self.assertEqual(r["contract_interest"]["rounded_once_at_E"], "2.70")
        self.assertEqual(r["summary"]["terminal"]["cash"], "10002.35")
        trade, first, due, payment, release = [event(r, k) for k in
            ("trade", "first_settlement", "maturity", "confirmation", "available")]
        self.assertEqual(trade["after"]["cash"], "10000")
        self.assertEqual(trade["after"]["reserved"], "9000.35")
        self.assertEqual(first["after"]["cash"], "999.80")
        self.assertEqual(first["after"]["locked_principal"], "9000")
        self.assertEqual(due["after"]["payable_fee"], "0.10")
        self.assertEqual(due["after"]["conditional_book_NAV"], "10002.35")
        self.assertEqual(payment["after"]["available"], "999.80")
        self.assertEqual(payment["after"]["unreleased_cash"], "9002.55")
        self.assertFalse(payment["after"]["economic_flat"])
        self.assertEqual(release["before"]["cash"], release["after"]["cash"])
        self.assertEqual(release["after"]["available"], "10002.35")
        self.assertIsNone(release["after"]["withdrawable"])
        self.assertFalse(r["summary"]["terminal_unsettled"])
        self.assertFalse(r["qualified"])
        self.assertEqual(r["real_forward"], 0)

    def test_one_final_cent_rounding_not_daily_rounding(self):
        f = m.synthetic_fixture()
        f["contract"].update(principal="1000", quote_per100_year="1.005",
                             entry_fee="0.01", maturity_fee="0.01", tax="0.01")
        f["confirmations"][0].update(principal="1000", interest="0.08",
                                     maturity_fee="0.01", tax="0.01")
        r = m.run_synthetic_contract(f)
        self.assertEqual(r["contract_interest"]["rounded_once_at_E"], "0.08")
        self.assertNotEqual(r["contract_interest"]["unrounded"], "0.08")
        self.assertEqual(r["summary"]["terminal"]["cash"], "10000.05")

    def test_partial_late_payment_no_extra_interest(self):
        f = m.synthetic_fixture()
        f["confirmations"][0].update(principal="4500", interest="1.00")
        f["confirmations"].append({"id": "ARTIFICIAL_PAYMENT_2",
            "confirmed_at": "2001-01-10T08:01:00Z", "principal": "4500",
            "interest": "1.70", "maturity_fee": "0", "tax": "0"})
        f["terminal_date"] = "2001-01-09"
        early = m.run_synthetic_contract(f)
        t = early["summary"]["terminal"]
        self.assertEqual(t["locked_principal"], "4500")
        self.assertEqual(t["interest_receivable"], "1.70")
        self.assertEqual(t["cash"], "5500.65")
        self.assertEqual(t["conditional_book_NAV"], "10002.35")
        self.assertTrue(early["summary"]["terminal_unsettled"])
        f["terminal_date"] = "2001-01-16"
        late = m.run_synthetic_contract(f)
        self.assertEqual(late["summary"]["terminal"]["cash"], "10002.35")
        self.assertEqual(late["summary"]["late_payment_extra_interest"], "0")
        self.assertEqual(event(late, "confirmation", 1)["before"]["accrued_total"], "2.70")

    def test_early_terminal_never_forces_maturity_or_receipt(self):
        f = m.synthetic_fixture()
        f["terminal_date"] = "2001-01-05"
        r = m.run_synthetic_contract(f)
        self.assertEqual(r["summary"]["terminal"]["locked_principal"], "9000")
        self.assertFalse(r["summary"]["matured"])
        self.assertTrue(r["summary"]["terminal_unsettled"])
        self.assertFalse(r["summary"]["forced_terminal_liquidation"])
        self.assertFalse(any(x["kind"] == "confirmation" for x in r["events"]))

    def test_confirmed_but_unavailable_at_terminal_remains_unsettled(self):
        f = m.synthetic_fixture()
        f["terminal_date"] = "2001-01-08"
        r = m.run_synthetic_contract(f)
        t = r["summary"]["terminal"]
        self.assertEqual(t["locked_principal"], "0")
        self.assertEqual(t["unreleased_cash"], "9002.55")
        self.assertTrue(r["summary"]["terminal_unsettled"])

    def test_fee_reserve_prevents_full_principal_order(self):
        f = m.synthetic_fixture()
        f["contract"]["principal"] = "10000"
        f["confirmations"] = []
        r = m.run_synthetic_contract(f)
        self.assertFalse(r["summary"]["accepted"])
        self.assertEqual(r["summary"]["terminal"]["cash"], "10000")
        self.assertEqual(r["summary"]["terminal"]["entry_fee_paid"], "0")
        self.assertEqual(r["summary"]["contracts_attempted"], 1)

    def test_risk_locked_then_five_full_flat_days_no_peak_reset(self):
        f = m.synthetic_fixture()
        f["contract"].update(principal="1000", quote_per100_year="0",
                             entry_fee="4500", maturity_fee="0", tax="0")
        f["confirmations"][0].update(principal="1000", interest="0", maturity_fee="0", tax="0")
        r = m.run_synthetic_contract(f)
        first = event(r, "first_settlement")["after"]
        self.assertEqual(first["locked_principal"], "1000")
        self.assertTrue(first["paused"])
        self.assertEqual(first["maximum_observed_drawdown"], "0.45")
        self.assertTrue(any("daily_loss_2_percent" in b["failures"] for b in r["risk_breaches"]))
        self.assertTrue(all(not b["forced_exit"] for b in r["risk_breaches"]))
        closes = {e["at"][:10]: e["after"] for e in r["events"] if e["kind"] == "close"}
        self.assertEqual(closes["2001-01-09"]["complete_flat_days"], 0)
        self.assertEqual(closes["2001-01-15"]["complete_flat_days"], 4)
        self.assertEqual(closes["2001-01-16"]["complete_flat_days"], 5)
        self.assertFalse(closes["2001-01-16"]["paused"])
        self.assertEqual(closes["2001-01-16"]["continuous_peak"], "10000")
        self.assertEqual(r["observations"][-1]["drawdown"], "0.45")
        self.assertEqual(r["summary"]["automatic_reinvestments"], 0)

    def test_fee_only_payment_clears_liability_without_double_expense(self):
        f = m.synthetic_fixture()
        f["confirmations"][0].update(principal="0", interest="0")
        f["confirmations"].append({"id": "ARTIFICIAL_PAYMENT_2",
            "confirmed_at": "2001-01-09T08:01:00Z", "principal": "9000",
            "interest": "2.70", "maturity_fee": "0", "tax": "0"})
        r = m.run_synthetic_contract(f)
        p = event(r, "confirmation")
        self.assertEqual(p["after"]["cash"], "999.65")
        self.assertEqual(p["after"]["available"], "999.65")
        self.assertEqual(p["after"]["payable_fee"], "0.00")
        self.assertEqual(p["after"]["conditional_book_NAV"], p["after_accrual_before_event"]["conditional_book_NAV"])
        self.assertEqual(r["summary"]["terminal"]["cash"], "10002.35")

    def test_duplicate_early_overpay_and_component_omission_reject(self):
        for mode in ("duplicate", "early", "overpay", "missing_tax", "unsorted", "unknown"):
            with self.subTest(mode=mode):
                f = m.synthetic_fixture()
                if mode == "duplicate":
                    f["confirmations"].append(deepcopy(f["confirmations"][0]))
                elif mode == "early":
                    f["confirmations"][0]["confirmed_at"] = "2001-01-08T07:59:59Z"
                elif mode == "overpay":
                    f["confirmations"][0]["interest"] = "2.71"
                elif mode == "missing_tax":
                    del f["confirmations"][0]["tax"]
                elif mode == "unsorted":
                    f["calendar"] = list(reversed(f["calendar"]))
                else:
                    f["contract"]["tax"] = None
                with self.assertRaises(m.ContractError):
                    m.run_synthetic_contract(f)

    def test_identity_units_and_nonnumeric_rejection(self):
        cases = [("principal", "999"), ("quote_per100_year", "0.001"),
                 ("entry_fee", False), ("entry_fee", 5), ("entry_fee", 0.5),
                 ("entry_fee", "NaN"), ("entry_fee", "-1"), ("entry_fee", "1e2"),
                 ("entry_fee", "0.001"), ("nominal_term_days", True)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                f = m.synthetic_fixture()
                f["contract"][field] = value
                with self.assertRaises(m.ContractError):
                    m.run_synthetic_contract(f)
        for field, value in (("source_nature", "actual_market"), ("terminal_date", "2026-01-05")):
            f = m.synthetic_fixture()
            f[field] = value
            with self.assertRaises(m.ContractError):
                m.run_synthetic_contract(f)

    def test_full_context_isolation_failure_and_success(self):
        with localcontext() as ambient:
            ambient.prec = 17
            ambient.rounding = ROUND_DOWN
            ambient.flags[Inexact] = True
            before = m._context_record(getcontext())
            f = m.synthetic_fixture()
            f["contract"]["entry_fee"] = "not_a_decimal"
            with self.assertRaises(m.ContractError):
                m.run_synthetic_contract(f)
            self.assertEqual(m._context_record(getcontext()), before)
            original = m.synthetic_fixture()
            copy = deepcopy(original)
            r = m.run_synthetic_contract(original)
            self.assertEqual(original, copy)
            self.assertEqual(m._context_record(getcontext()), before)
            self.assertEqual(r["decimal_context"]["prec"], 40)
            self.assertEqual(r["decimal_context"]["rounding"], "ROUND_HALF_EVEN")
            self.assertEqual(set(r["decimal_context"]), set(before))

    def test_cli_accepts_only_output_and_reports_actual_module(self):
        root = Path(__file__).resolve().parents[2]
        env = {**os.environ, "PYTHONPATH": str(root / "src")}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "demo"
            command = [sys.executable, "-P", str(root / "scripts/run_repo_cash_contract_synthetic.py")]
            run = subprocess.run([*command, "--output-dir", str(out)], env=env,
                                 capture_output=True, text=True, check=True)
            self.assertIn("artificial_only", run.stdout)
            runtime = json.loads((out / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(Path(runtime["module_file"]), Path(m.__file__).resolve())
            bad = subprocess.run([*command, "--output-dir", str(Path(d) / "bad"),
                                  "--input", "market.json"], env=env, capture_output=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse((Path(d) / "bad").exists())


if __name__ == "__main__":
    unittest.main()
