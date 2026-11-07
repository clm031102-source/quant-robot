from copy import deepcopy
from decimal import Decimal, ROUND_DOWN, getcontext, localcontext
from pathlib import Path
import unittest

from quant_robot.paper import bond_risk_compensation as bond


def constant_fixture(count=45, price="91"):
    fixture = bond.fixed_artificial_fixture(count)
    fixture["actions"] = []
    for bar in fixture["bars"]:
        for key in ("open", "high", "low", "close"):
            bar[key] = price
    return fixture


def set_price(fixture, index, opening, close=None):
    close = opening if close is None else close
    bar = fixture["bars"][index]
    bar.update(open=str(opening), close=str(close), high=str(max(Decimal(str(opening)), Decimal(str(close)))),
               low=str(min(Decimal(str(opening)), Decimal(str(close)))))


def action(fixture, record=22, ex=23, pay=25, amount="1"):
    fixture["actions"] = [{"event_id": "invented_dividend", "asset_id": bond.ASSET,
        "record_date": fixture["sessions"][record], "ex_date": fixture["sessions"][ex],
        "pay_date": fixture["sessions"][pay], "cash_per_unit": amount, "share_multiplier": "1"}]


class BondContractTests(unittest.TestCase):
    def run_account(self, fixture, minimum=5, slip=10):
        return bond.run_synthetic_account(fixture, minimum_commission=minimum, slippage_bps=slip)

    def test_new_worktree_module_origin(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual(Path(bond.__file__).resolve(), root / "src/quant_robot/paper/bond_risk_compensation.py")

    def test_first20_cash_max_legal_lot_and_exact_frozen_budget(self):
        fixture = constant_fixture()
        result = self.run_account(fixture)
        self.assertTrue(all(row["quantity"] == 0 and row["equity"] == "10000" for row in result["rows"][:20]))
        fill = result["fills"][0]
        self.assertEqual(fill["date"], fixture["sessions"][20])
        self.assertEqual(fill["quantity"], 100)
        self.assertEqual(fill["plan"]["budget"], "10000")
        self.assertEqual(fill["execution_price"], "91.091")
        self.assertEqual(fill["fee"], "5.00")
        self.assertEqual(fill["cash_after"], "885.900")
        self.assertEqual(fill["plan"]["capacity_dates"], [fixture["sessions"][0], fixture["sessions"][19]])
        self.assertEqual(result["summary"]["total_slippage_and_tick_cost_CNY"], "18.200")
        self.assertEqual(result["summary"]["cash"], "9971.800")

    def test_open_gap_rejects_whole_order_without_resize_then_nextday_retry(self):
        fixture = constant_fixture()
        set_price(fixture, 20, "101", "91")
        result = self.run_account(fixture)
        self.assertEqual(result["attempts"][0]["requested_quantity"], 100)
        self.assertEqual(result["attempts"][0]["rejected"], "entry_budget_or_cash")
        self.assertEqual(result["fills"][0]["date"], fixture["sessions"][21])
        self.assertEqual(result["fills"][0]["quantity"], 100)
        self.assertFalse(any(fill["date"] == fixture["sessions"][20] for fill in result["fills"]))

    def test_current_volume_ex_post_only_keeps_fills_and_economic_path(self):
        ordinary = constant_fixture()
        low = deepcopy(ordinary); low["bars"][20]["volume"] = "0"
        a, b = self.run_account(ordinary), self.run_account(low)
        self.assertEqual(a["fills"], b["fills"])
        self.assertEqual(a["rows"], b["rows"])
        self.assertEqual(a["summary"]["terminal_book_NAV"], b["summary"]["terminal_book_NAV"])
        audit = next(x for x in b["execution_uncertainty"] if x["reason"] == "ex_post_full_day_capacity_not_met")
        self.assertTrue(audit["fill_retained"]); self.assertFalse(audit["economic_path_rolled_back"])

    def test_blocked_risk_exit_not_flat_and_five_complete_days_after_actual_sale(self):
        fixture = bond.fixed_artificial_fixture(45)
        for index in (26, 27): fixture["bars"][index]["limit_down"] = True
        result = self.run_account(fixture)
        self.assertEqual(result["rows"][26]["quantity"], 100)
        self.assertIsNone(result["rows"][26]["cooldown_flat_index"])
        sale = next(f for f in result["fills"] if f["side"] == "sell")
        self.assertEqual(sale["date"], fixture["sessions"][28])
        buys = [f for f in result["fills"] if f["side"] == "buy"]
        self.assertEqual(buys[1]["date"], fixture["sessions"][34])
        self.assertTrue(all(result["rows"][i]["quantity"] == 0 for i in range(28, 34)))

    def test_prior_capacity_partial_exit_does_not_start_cooling_early(self):
        fixture = constant_fixture(45, "10")
        for index in range(20, 26): fixture["bars"][index]["volume"] = "0"
        for index in range(25, 45): set_price(fixture, index, "9")
        result = self.run_account(fixture)
        sales = [f for f in result["fills"] if f["side"] == "sell"]
        self.assertEqual(sales[0]["date"], fixture["sessions"][26])
        self.assertEqual(sales[0]["quantity"], 700)
        self.assertEqual(sales[0]["position_after"], 200)
        self.assertIsNone(result["rows"][26]["cooldown_flat_index"])
        self.assertEqual(sales[1]["date"], fixture["sessions"][27])
        self.assertEqual(result["rows"][27]["cooldown_flat_index"], 27)
        self.assertEqual([f for f in result["fills"] if f["side"] == "buy"][1]["date"], fixture["sessions"][33])

    def test_global_peak_not_reset_and_exposed_reentry_retriggers_DD(self):
        fixture = constant_fixture(45)
        for index in range(25, 45): set_price(fixture, index, "50")
        result = self.run_account(fixture)
        self.assertTrue(all(row["global_peak"] == "10000" for row in result["rows"]))
        journal = [x for x in result["risk_journal"] if x["kind"] == "global_drawdown_pause"]
        self.assertEqual(journal[0]["date"], fixture["sessions"][25])
        self.assertIn(fixture["sessions"][32], [x["date"] for x in journal])
        self.assertTrue(result["summary"]["observed_drawdown_over_40pct"])

    def test_continuous_hold_past252_no_annual_or_holding_cap_exit(self):
        fixture = constant_fixture(282)
        result = self.run_account(fixture)
        self.assertEqual(len(result["fills"]), 2)
        self.assertEqual(result["fills"][-1]["date"], fixture["sessions"][-1])
        self.assertGreater(result["summary"]["maximum_holding_sessions"], 252)

    def test_record_ex_pay_cash_conservation_and_no_dividend_topup(self):
        fixture = constant_fixture(30); action(fixture)
        for index in range(23, 30): set_price(fixture, index, "90")
        result = self.run_account(fixture, 0, 0)
        self.assertEqual(result["rows"][22]["equity"], result["rows"][23]["equity"])
        self.assertEqual(result["rows"][23]["dividend_receivable"], "100.00")
        self.assertEqual(result["rows"][25]["dividend_receivable"], "0")
        self.assertEqual(result["rows"][25]["cash"], "995.450")
        self.assertEqual(result["summary"]["cash"], "9990.950")
        self.assertEqual(result["summary"]["dividend_cash_received"], "100.00")
        self.assertEqual(len([f for f in result["fills"] if f["side"] == "buy"]), 1)
        self.assertTrue(result["summary"]["cash_quantity_NAV_reconciled"])

    def test_payment_cannot_fund_same_open_but_next_open_can_use_it(self):
        fixture = constant_fixture(40); action(fixture, 24, 25, 32, "6")
        for index in range(25, 32): set_price(fixture, index, "50")
        for index in range(32, 40): set_price(fixture, index, "60")
        result = self.run_account(fixture)
        at_pay = next(x for x in result["attempts"] if x["date"] == fixture["sessions"][32])
        self.assertEqual(at_pay["rejected"], "entry_budget_or_cash")
        self.assertLess(Decimal(result["rows"][32]["cash_before_distribution_payment"]), Decimal(result["rows"][32]["cash"]))
        self.assertIn(fixture["sessions"][33], [f["date"] for f in result["fills"] if f["side"] == "buy"])

    def test_terminal_has_priority_and_unpaid_receivable_remains_separate(self):
        fixture = constant_fixture(30); action(fixture)
        fixture["actions"][0]["pay_date"] = "2001-02-05"
        for index in range(23, 30): set_price(fixture, index, "90")
        bundle = bond.run_synthetic_bundle(fixture)
        result = bundle["fee_accounts"][0]
        self.assertEqual(result["fills"][-1]["reason"], "terminal_exit")
        self.assertFalse(any(f["side"] == "buy" and f["date"] == fixture["sessions"][-1] for f in result["fills"]))
        self.assertEqual(result["summary"]["remaining_quantity"], 0)
        self.assertEqual(result["summary"]["dividend_receivable"], "100.00")
        self.assertEqual(result["summary"]["pending_record_entitlements"], [])
        self.assertTrue(result["summary"]["terminal_unsettled"])
        self.assertGreater(Decimal(bundle["reference"]["summary"]["terminal_unpaid_receivable"]), 0)
        self.assertEqual(bundle["reference"]["summary"]["pending_record_entitlements"], [])

    def test_recorded_right_before_future_ex_is_unsettled_but_not_extra_NAV(self):
        fixture = constant_fixture(30)
        baseline = bond.run_synthetic_bundle(fixture)
        fixture["actions"] = [{"event_id": "future_ex", "asset_id": bond.ASSET,
            "record_date": fixture["sessions"][-2], "ex_date": "2001-02-02", "pay_date": "2001-02-05",
            "cash_per_unit": "1", "share_multiplier": "1"}]
        actual = bond.run_synthetic_bundle(fixture)
        for before, after in zip(baseline["fee_accounts"], actual["fee_accounts"], strict=True):
            a, b = before["summary"], after["summary"]
            self.assertFalse(a["terminal_unsettled"])
            self.assertTrue(b["terminal_unsettled"])
            self.assertEqual(b["remaining_quantity"], 0)
            self.assertEqual(b["dividend_receivable"], "0")
            self.assertEqual((a["cash"], a["terminal_book_NAV"]), (b["cash"], b["terminal_book_NAV"]))
            right = b["pending_record_entitlements"][0]
            self.assertEqual(right["record_quantity"], 100)
            self.assertFalse(right["included_in_NAV"]); self.assertFalse(right["spendable_cash"])
            self.assertIn("if_pending_not_complete_settled_return", b["terminal_value_scope"])
        a, b = baseline["reference"]["summary"], actual["reference"]["summary"]
        self.assertEqual(a["terminal_economic_value"], b["terminal_economic_value"])
        self.assertEqual(a["terminal_cash"], b["terminal_cash"])
        self.assertEqual(b["terminal_unpaid_receivable"], "0")
        self.assertTrue(b["terminal_unsettled"])
        self.assertEqual(b["pending_record_entitlements"][0]["record_quantity"], actual["reference"]["fixed_theoretical_quantity"])
        self.assertFalse(b["pending_record_entitlements"][0]["included_in_NAV"])
        self.assertIn("if_pending_not_complete_settled_return", b["terminal_value_scope"])

    def test_terminal_ex_date_converts_record_right_to_receivable_once(self):
        fixture = constant_fixture(30)
        fixture["actions"] = [{"event_id": "terminal_ex", "asset_id": bond.ASSET,
            "record_date": fixture["sessions"][-2], "ex_date": fixture["sessions"][-1],
            "pay_date": "2001-02-05", "cash_per_unit": "1", "share_multiplier": "1"}]
        set_price(fixture, 29, "90")
        result = bond.run_synthetic_bundle(fixture)
        for account in result["fee_accounts"]:
            summary = account["summary"]
            self.assertEqual(summary["remaining_quantity"], 0)
            self.assertEqual(summary["pending_record_entitlements"], [])
            self.assertEqual(summary["dividend_receivable"], "100.00")
            self.assertEqual(Decimal(summary["terminal_book_NAV"]), Decimal(summary["cash"]) + Decimal("100"))
            self.assertTrue(summary["terminal_unsettled"])
            self.assertEqual([x["kind"] for x in account["actions"]], ["record_entitlement", "receivable_created"])
        reference = result["reference"]["summary"]
        self.assertEqual(reference["pending_record_entitlements"], [])
        self.assertEqual(reference["terminal_unpaid_receivable"], result["reference"]["fixed_theoretical_quantity"])
        self.assertTrue(reference["terminal_unsettled"])

    def test_zero_record_holdings_do_not_create_pending_right(self):
        fixture = constant_fixture(30)
        fixture["actions"] = [{"event_id": "record_while_cash", "asset_id": bond.ASSET,
            "record_date": fixture["sessions"][5], "ex_date": "2001-02-02", "pay_date": "2001-02-05",
            "cash_per_unit": "1", "share_multiplier": "1"}]
        result = bond.run_synthetic_bundle(fixture)
        for account in result["fee_accounts"]:
            self.assertEqual(account["summary"]["pending_record_entitlements"], [])
            self.assertFalse(account["summary"]["terminal_unsettled"])
        self.assertEqual(result["reference"]["summary"]["pending_record_entitlements"], [])
        self.assertFalse(result["reference"]["summary"]["terminal_unsettled"])

    def test_terminal_capacity_failure_retains_position_and_does_not_extend(self):
        fixture = constant_fixture(45)
        for index in range(20, 45): fixture["bars"][index]["volume"] = "1000"
        result = self.run_account(fixture)
        self.assertEqual(result["summary"]["remaining_quantity"], 100)
        self.assertTrue(result["summary"]["terminal_unsettled"])
        self.assertEqual(result["rows"][-1]["date"], fixture["sessions"][-1])
        self.assertEqual(result["attempts"][-1]["rejected"], "below_one_lot_or_prior_capacity")

    def test_unknown_flags_remain_unknown_conditional_not_known_false(self):
        fixture = constant_fixture()
        fixture["bars"][20]["suspended"] = None
        result = self.run_account(fixture)
        self.assertEqual(result["unknown_flag_rows"], 1)
        self.assertEqual(result["fills"][0]["unknown_flags"], ["suspended"])
        self.assertFalse(result["qualified"])
        self.assertIn("unknown_execution_flags", [x["reason"] for x in result["execution_uncertainty"]])

    def test_reject_real_or_missing_sources_split_unknown_units_and_float_input(self):
        variants = []
        f = constant_fixture(); f["evidence_class"] = "actual_historical"; variants.append(f)
        f = constant_fixture(); f["sessions"][0] = "2020-01-02"; variants.append(f)
        f = constant_fixture(); f["corporate_actions_complete"] = False; variants.append(f)
        f = constant_fixture(); f["actions"] = None; variants.append(f)
        f = constant_fixture(); f["volume_unit"] = "lots"; variants.append(f)
        f = constant_fixture(); del f["price_basis"]; variants.append(f)
        f = constant_fixture(); f["bars"][0]["open"] = 91.0; variants.append(f)
        f = constant_fixture(); del f["bars"][0]["suspended"]; variants.append(f)
        f = constant_fixture(); action(f); f["actions"][0]["share_multiplier"] = "10"; variants.append(f)
        f = constant_fixture(); action(f); del f["actions"][0]["share_multiplier"]; variants.append(f)
        for f in variants:
            with self.subTest(index=variants.index(f)):
                with self.assertRaises((ValueError, TypeError)):
                    self.run_account(f)

    def test_nine_costs_cash_and_reference_fixed_open_theoretical_not_extra_account(self):
        fixture = bond.fixed_artificial_fixture()
        bundle = bond.run_synthetic_bundle(fixture)
        self.assertEqual(bundle["account_count"], 10)
        self.assertEqual(bundle["additional_nontrading_reference_count"], 1)
        self.assertEqual([(a["cost_case"]["minimum_commission_CNY"], a["cost_case"]["slippage_bps_each"]) for a in bundle["fee_accounts"]], list(bond.COST_CASES))
        self.assertTrue(all(Decimal(a["summary"]["total_commission_CNY"]) > 0 for a in bundle["fee_accounts"]))
        self.assertTrue(all(a["summary"]["cash_quantity_NAV_reconciled"] and not a["qualified"] for a in bundle["fee_accounts"]))
        self.assertTrue(all(row["equity"] == "10000" for row in bundle["cash_control"]["rows"]))
        reference = bundle["reference"]
        self.assertEqual(reference["first_entry_date"], fixture["sessions"][20])
        self.assertEqual(reference["terminal_date"], fixture["sessions"][-1])
        self.assertTrue(reference["not_an_executable_account"])
        self.assertFalse(reference["distribution_cash_reinvested"])
        self.assertEqual(reference["rows"][-1]["quantity"], "0")
        self.assertEqual(reference["distribution_rounding"], "context40_theoretical_fractional_units_not_cent_payment_simulation")

    def test_precision40_isolated_from_ambient_context_and_no_float_outputs(self):
        fixture = constant_fixture(30); action(fixture, amount="0.000055")
        original_precision = getcontext().prec
        ordinary = bond.run_synthetic_bundle(fixture)
        with localcontext() as context:
            context.prec = 6; context.rounding = ROUND_DOWN
            changed = bond.run_synthetic_bundle(fixture)
            self.assertEqual(context.prec, 6)
        self.assertEqual(ordinary, changed)
        self.assertEqual(getcontext().prec, original_precision)
        self.assertEqual(ordinary["fee_accounts"][0]["summary"]["dividend_cash_received"], "0.01")
        def check(value):
            self.assertNotIsInstance(value, float)
            if isinstance(value, dict):
                for item in value.values(): check(item)
            elif isinstance(value, list):
                for item in value: check(item)
        check(ordinary)


def split_fixture(count=40, record=25, price="91"):
    fixture = constant_fixture(count, price)
    sessions = fixture["sessions"]
    ex = sessions[record + 1] if record + 1 < count else "2001-12-31"
    fixture["split_events"] = [{"event_id": "invented_split", "asset_id": bond.ASSET,
        "record_date": sessions[record], "ex_date": ex, "known_date": sessions[0],
        "share_multiplier": "10", "registry_phase": "record_day_end"}]
    for i, bar in enumerate(fixture["bars"]):
        bar["share_unit"] = "pre_split" if i <= record else "post_split"
        bar["volume"] = "100000" if i <= record else "1000000"
        if i > record:
            set_price(fixture, i, str(Decimal(price) / 10))
    return fixture


class BondSplitContractTests(unittest.TestCase):
    def run_account(self, fixture):
        return bond.run_synthetic_account(fixture, minimum_commission=0, slippage_bps=0,
                                          split_mode=bond.SPLIT_MODE)

    def test_registration_close_bridge_once_without_false_risk_or_cash(self):
        fixture = split_fixture()
        before = deepcopy(fixture)
        result = self.run_account(fixture)
        a, b, c = result["rows"][24:27]
        self.assertEqual((a["quantity"], b["quantity"], c["quantity"]), (100, 1000, 1000))
        self.assertEqual((b["raw_close"], b["valuation_price"], b["post_registration_quote_unit_factor"]), ("91", "9.1", 10))
        self.assertEqual(c["post_registration_quote_unit_factor"], 1)
        self.assertEqual((a["equity"], a["cash"], a["global_peak"]), (b["equity"], b["cash"], b["global_peak"]))
        self.assertEqual(Decimal(b["equity"]), Decimal(c["equity"]))
        self.assertEqual(result["risk_journal"], [])
        self.assertEqual(result["summary"]["nontrade_conversion_delta"], 900)
        self.assertTrue(result["summary"]["cash_quantity_NAV_reconciled"])
        self.assertEqual(len([a for a in result["actions"] if a["kind"] == "split_registration"]), 1)
        self.assertEqual(fixture, before)

    def test_mixed_prefix_native_units_and_new_plan_gap_rejection(self):
        fixture = split_fixture(45, 24)
        for bar in fixture["bars"][20:35]: bar["suspended"] = True
        set_price(fixture, 35, "11", "9.1")
        result = self.run_account(fixture)
        attempted = next(x for x in result["attempts"] if x["date"] == fixture["sessions"][35])
        self.assertEqual(attempted["prior_capacity"], 10000)
        self.assertEqual([x["factor"] for x in attempted["capacity_unit_factors"]], [10] * 10 + [1] * 10)
        self.assertEqual(attempted["requested_quantity"], 1000)
        self.assertEqual(attempted["rejected"], "entry_budget_or_cash")
        self.assertEqual(result["fills"][0]["date"], fixture["sessions"][36])
        self.assertEqual(result["fills"][0]["quantity"], 1000)
        self.assertEqual(result["rows"][36]["quantity"], 1000)
        self.assertEqual(result["summary"]["nontrade_conversion_delta"], 0)
        prior = next(x for x in result["attempts"] if x["date"] == fixture["sessions"][24])
        self.assertTrue(all(x["factor"] == 1 for x in prior["capacity_unit_factors"]))
        self.assertEqual(prior["prior_capacity"], 1000)

    def test_duplicate_unknown_noninteger_and_default_scope_rejected(self):
        original = split_fixture()
        with self.assertRaises(ValueError): bond.run_synthetic_account(original)
        variants = []
        f = deepcopy(original); f["split_events"].append(deepcopy(f["split_events"][0])); variants.append(f)
        f = deepcopy(original); f["split_events"][0]["share_multiplier"] = "2"; variants.append(f)
        f = deepcopy(original); f["split_events"][0]["record_date"] = "2023-01-13"; variants.append(f)
        f = deepcopy(original); del f["bars"][26]["share_unit"]; variants.append(f)
        f = deepcopy(original); f["bars"][26]["share_unit"] = "pre_split"; variants.append(f)
        f = deepcopy(original); f["evidence_class"] = "actual_historical"; variants.append(f)
        for fixture in variants:
            with self.subTest(fixture=variants.index(fixture)):
                with self.assertRaises((ValueError, KeyError)): self.run_account(fixture)
        split = original["split_events"][0]
        with self.assertRaises(ValueError): bond._register_split(Decimal("1.5"), split, split["record_date"], False)
        with self.assertRaises(ValueError): bond._register_split(100, split, split["record_date"], True)

    def test_partial_risk_exit_old_fill_and_remaining_new_units_preserve_cooldown(self):
        fixture = split_fixture(45, 26, "10")
        for i in range(20, 27): fixture["bars"][i]["volume"] = "0"
        for i in range(25, 27): set_price(fixture, i, "9")
        for i in range(27, 45): set_price(fixture, i, "0.9")
        result = self.run_account(fixture)
        sales = [f for f in result["fills"] if f["side"] == "sell"]
        self.assertEqual((sales[0]["quantity"], sales[0]["position_after"], sales[0]["trade_share_unit"]), (700, 200, "pre_split"))
        self.assertEqual(result["rows"][26]["quantity"], 2000)
        self.assertIsNone(result["rows"][26]["cooldown_flat_index"])
        self.assertEqual((sales[1]["quantity"], sales[1]["trade_share_unit"]), (2000, "post_split"))
        self.assertEqual(result["rows"][27]["cooldown_flat_index"], 27)
        self.assertEqual([f for f in result["fills"] if f["side"] == "buy"][1]["date"], fixture["sessions"][33])
        self.assertTrue(all(row["global_peak"] == "10000" for row in result["rows"]))
        audit = next(x for x in result["execution_uncertainty"] if x["date"] == fixture["sessions"][26])
        self.assertEqual((audit["quantity"], audit["realized_day_capacity"]), (700, 0))

    def test_old_record_right_and_receivable_not_multiplied_and_explicit_cash_units(self):
        fixture = split_fixture()
        action(fixture, 25, 27, 29, "1")
        fixture["actions"][0].update(record_quantity_unit="pre_split", cash_per_unit_basis="pre_split")
        # A second already-established receivable spans the conversion too.
        a = deepcopy(fixture["actions"][0]); a.update(event_id="already_ex", record_date=fixture["sessions"][22], ex_date=fixture["sessions"][23], pay_date=fixture["sessions"][30])
        fixture["actions"].append(a)
        result = self.run_account(fixture)
        same_day = [a for a in result["actions"] if a["date"] == fixture["sessions"][25]]
        self.assertEqual([a["kind"] for a in same_day], ["record_entitlement", "split_registration"])
        self.assertEqual(same_day[0]["quantity"], 100)
        self.assertEqual(same_day[1]["quantity_after"], 1000)
        self.assertEqual(result["rows"][25]["dividend_receivable"], "100.00")
        self.assertEqual(result["rows"][27]["dividend_receivable"], "200.00")
        self.assertEqual(result["summary"]["dividend_cash_received"], "200.00")
        self.assertEqual(len([f for f in result["fills"] if f["side"] == "buy"]), 1)
        mixed = deepcopy(fixture)
        mixed["actions"][0].update(cash_per_unit="0.1", cash_per_unit_basis="post_split")
        with self.assertRaises(ValueError): self.run_account(mixed)
        mixed["actions"][0]["cash_basis_mapping"] = "explicit_split10_conversion"
        self.assertEqual(self.run_account(mixed)["summary"], result["summary"])
        del mixed["actions"][0]["record_quantity_unit"]
        with self.assertRaises(ValueError): self.run_account(mixed)

    def test_fractional_reference_and_full_nine_fee_short_fixture(self):
        fixture = bond.fixed_split_artificial_fixture()
        with localcontext(bond.CONTEXT):
            bundle = bond.run_synthetic_bundle(fixture, split_mode=bond.SPLIT_MODE)
            reference = bundle["reference"]
            q = Decimal(reference["fixed_theoretical_quantity"])
            self.assertEqual(Decimal(reference["rows"][25]["quantity"]), q * 10)
            self.assertEqual(Decimal(reference["payments"][0]["cash_distribution"]), q * Decimal("0.2"))
            self.assertEqual(Decimal(reference["rows"][24]["economic_value"]), Decimal(reference["rows"][25]["economic_value"]))
        self.assertTrue(all(x["summary"]["cash_quantity_NAV_reconciled"] for x in bundle["fee_accounts"]))
        self.assertEqual(len(bundle["fee_accounts"]), 9)
        self.assertTrue(reference["not_an_executable_account"])
        self.assertFalse(reference["distribution_cash_reinvested"])
        self.assertEqual(reference["rows"][-1]["quantity"], "0")

    def test_terminal_registration_residual_new_unit_exit_and_unknown_flags(self):
        fixture = split_fixture(30, 29)
        fixture["bars"][-1]["limit_down"] = True
        result = self.run_account(fixture)
        self.assertEqual(result["summary"]["remaining_quantity"], 1000)
        self.assertTrue(result["summary"]["terminal_unsettled"])
        self.assertEqual(result["rows"][-1]["valuation_price"], "9.1")
        self.assertEqual(result["rows"][-1]["market_value"], "9100.0")
        fixture = split_fixture(30, 28)
        fixture["bars"][-1]["suspended"] = None
        result = self.run_account(fixture)
        self.assertEqual(result["fills"][-1]["quantity"], 1000)
        self.assertEqual(result["fills"][-1]["reason"], "terminal_exit")
        self.assertEqual(result["fills"][-1]["unknown_flags"], ["suspended"])
        self.assertTrue(any(x["reason"] == "unknown_execution_flags" for x in result["execution_uncertainty"]))
        self.assertFalse(result["qualified"])

    def test_pending_right_terminal_separate_from_ex_receivable_and_context_isolation(self):
        fixture = split_fixture(30, 25)
        action(fixture, 24, 27, 29, "1")
        a = fixture["actions"][0]
        a.update(record_quantity_unit="pre_split", cash_per_unit_basis="pre_split",
                 ex_date="2001-02-02", pay_date="2001-02-05")
        baseline = bond.run_synthetic_bundle(fixture, split_mode=bond.SPLIT_MODE)
        with localcontext() as ctx:
            ctx.prec = 6; ctx.rounding = ROUND_DOWN
            other = bond.run_synthetic_bundle(fixture, split_mode=bond.SPLIT_MODE)
        self.assertEqual(baseline, other)
        for account in baseline["fee_accounts"]:
            summary = account["summary"]
            self.assertEqual(summary["dividend_receivable"], "0")
            self.assertEqual(summary["pending_record_entitlements"][0]["record_quantity"], 100)
            self.assertEqual(summary["pending_record_entitlements"][0]["record_quantity_unit"], "pre_split")
            self.assertTrue(summary["terminal_unsettled"])
        ref = baseline["reference"]["summary"]
        self.assertTrue(ref["terminal_unsettled"])
        self.assertEqual(ref["pending_record_entitlements"][0]["record_quantity_unit"], "pre_split")


if __name__ == "__main__":
    unittest.main()
