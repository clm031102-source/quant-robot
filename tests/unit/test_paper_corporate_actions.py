import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation

ASSET = "CN_ETF_XSHG_510300"


def dividend(**changes):
    return {"event_id": "div-1", "asset_id": ASSET, "kind": "cash_dividend",
            "announced_date": "2024-01-02", "record_date": "2024-01-03",
            "ex_date": "2024-01-04", "pay_date": "2024-01-06",
            "net_cash_per_share": 1.0, **changes}


def split(**changes):
    return {"event_id": "split-1", "asset_id": ASSET, "kind": "share_split",
            "announced_date": "2024-01-02", "ex_date": "2024-01-04",
            "tradable_date": "2024-01-04", "share_ratio": 2.0, **changes}


class PaperCorporateActionsTests(unittest.TestCase):
    def simulate(self, raw_prices, *, adjusted=None, events=None, rebalance=20, cash=1005,
                 max_asset_weight=1.0, initial_positions=None, start_date=None, supplied=True, omit_asset_bar_date=None, min_cash_weight=0, schema_version=1):
        bars = load_demo_market_bars()
        bars = bars[bars.asset_id.eq(ASSET)].head(len(raw_prices)).copy()
        for column in ("open", "high", "low", "close"):
            bars[column] = raw_prices
        bars["adj_close"] = adjusted if adjusted is not None else raw_prices
        if omit_asset_bar_date:
            reference = load_demo_market_bars()
            reference = reference[reference.asset_id.eq("CN_ETF_XSHE_159915")].head(len(raw_prices)).copy()
            bars = pd.concat([bars[~bars.date.astype(str).eq(omit_asset_bar_date)], reference], ignore_index=True)
        factors = bars[["asset_id", "market", "date"]].copy()
        factors = factors[factors.asset_id.eq(ASSET)]
        factors["factor_name"] = "synthetic_constant"
        factors["factor_value"] = 1.0
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(json.dumps({"schema_version": schema_version, "source_ref": "synthetic fixture",
                "coverage_start": str(bars.iloc[0].date), "coverage_end": str(bars.iloc[-1].date),
                "asset_ids": sorted(set(bars.asset_id)), "events": events or []}), encoding="utf-8")
            with patch("quant_robot.paper.simulator._compute_factors", return_value=factors):
                return run_paper_simulation(bars, PaperSimulationConfig(
                    market="CN_ETF", factor_name="synthetic_constant", top_n=1,
                    rebalance_interval=rebalance, initial_cash=cash, commission_bps=0,
                    slippage_bps=0, start_date=start_date, max_asset_weight=max_asset_weight,
                    corporate_actions_path=path if supplied else None,
                    min_cash_weight=min_cash_weight,
                ), initial_positions=initial_positions)

    def test_execution_and_valuation_use_raw_prices_independently_of_adjustment_scale(self):
        result = self.simulate([10] * 5, adjusted=[20] * 5)
        self.assertEqual(result["fills"][0]["quantity"], 100)
        self.assertEqual(result["fills"][0]["fill_price"], 10)
        self.assertEqual(result["intents"][0]["reference_price"], 10)
        self.assertEqual(result["metrics"]["ending_equity"], 1005)

    def test_locked_converted_odd_lot_cannot_be_sold_until_tradable_date(self):
        result = self.simulate([10, 10, 10 / 1.5, 10 / 1.5, 10 / 1.5, 10 / 1.5],
            events=[split(share_ratio=1.5, tradable_date="2024-01-06")],
            rebalance=1, cash=5, initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 100}]),
            start_date="2024-01-03", min_cash_weight=1)
        self.assertEqual([(fill["execution_date"], fill["quantity"]) for fill in result["fills"]], [("2024-01-06", 150)])
        self.assertAlmostEqual(result["metrics"]["ending_equity"], 1005)

    def test_dividend_becomes_receivable_on_ex_date_and_cash_after_pay_day_close(self):
        result = self.simulate([10, 10, 9, 9, 9, 9], adjusted=[9] * 6, events=[dividend()])
        curve = {row["date"]: row for row in result["equity_curve"]}
        self.assertEqual(curve["2024-01-03"]["dividend_receivable"], 0)
        self.assertEqual(curve["2024-01-04"]["dividend_receivable"], 100)
        self.assertEqual(curve["2024-01-04"]["cash"], 5)
        self.assertEqual(curve["2024-01-06"]["dividend_receivable"], 0)
        self.assertEqual(curve["2024-01-06"]["cash"], 105)
        self.assertTrue(all(row["equity"] == 1005 for row in result["equity_curve"]))
        self.assertEqual(result["metrics"]["dividend_cash_received"], 100)

    def test_unpaid_dividend_counts_in_equity_without_becoming_spendable(self):
        result = self.simulate([10, 10, 9, 9], adjusted=[9] * 4,
                               events=[dividend(pay_date="2024-01-10")])
        self.assertEqual(result["metrics"]["ending_cash"], 5)
        self.assertEqual(result["metrics"]["ending_dividend_receivable"], 100)
        self.assertEqual(result["metrics"]["ending_equity"], 1005)

    def test_dividend_cannot_fund_a_buy_before_the_payment_day_close(self):
        result = self.simulate([10, 10, 1, 1, 1, 1], events=[dividend(net_cash_per_share=9)],
                               cash=1000, rebalance=1)
        self.assertEqual([(fill["execution_date"], fill["quantity"]) for fill in result["fills"]],
                         [("2024-01-03", 100), ("2024-01-07", 900)])
        self.assertTrue(all(row["equity"] == 1000 for row in result["equity_curve"]))

    def test_buying_on_ex_date_does_not_receive_the_previous_holders_dividend(self):
        result = self.simulate([10, 10, 9, 9, 9, 9], events=[dividend()], start_date="2024-01-03")
        self.assertEqual(result["fills"][0]["execution_date"], "2024-01-04")
        self.assertEqual(result["metrics"]["dividend_cash_received"], 0)

    def test_split_changes_shares_and_pending_order_units_without_creating_profit(self):
        result = self.simulate([10, 10, 5, 5], adjusted=[5] * 4, events=[split()], rebalance=1)
        self.assertEqual(result["positions"][0]["quantity"], 200)
        self.assertEqual(result["metrics"]["ending_cash"], 5)
        self.assertEqual(result["metrics"]["ending_equity"], 1005)
        self.assertEqual(len(result["fills"]), 1)

    def test_pending_buy_before_split_is_converted_to_post_split_units(self):
        result = self.simulate([10, 10, 5, 5], events=[split()], start_date="2024-01-03")
        self.assertEqual(result["fills"][0]["execution_date"], "2024-01-04")
        self.assertEqual(result["fills"][0]["quantity"], 200)
        self.assertEqual(result["metrics"]["ending_equity"], 1005)

    def test_odd_lot_created_by_split_can_be_fully_sold(self):
        for ratio in (0.5, 1.5):
            with self.subTest(ratio=ratio):
                result = self.simulate([10, 10, 10 / ratio, 10 / ratio], events=[split(share_ratio=ratio)],
                    initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 100}]),
                    start_date="2024-01-03", cash=5, min_cash_weight=1, rebalance=1)
                self.assertEqual(result["fills"][0]["quantity"], 100 * ratio)
                self.assertEqual(result["positions"], [])
                self.assertAlmostEqual(result["metrics"]["ending_cash"], 1005)

    def test_post_action_price_is_required_even_when_other_assets_have_a_bar(self):
        for event in (split(), dividend()):
            with self.subTest(event=event), self.assertRaisesRegex(ValueError, "post.action.*price"):
                self.simulate([10, 10, 5, 5, 5, 5], events=[event], omit_asset_bar_date="2024-01-04")

    def test_initial_holdings_cannot_use_a_pre_split_quote_after_the_split(self):
        with self.assertRaisesRegex(ValueError, "post.action.*price"):
            self.simulate([10, 10, 5, 5], events=[split()], omit_asset_bar_date="2024-01-04",
                          start_date="2024-01-04", initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 200}]))

    def test_invalid_action_dates_duplicate_ids_and_unknown_kinds_are_rejected(self):
        invalid = [[dividend(), dividend()], [dividend(), dividend(event_id="same-dividend-again")], [dividend(record_date="2024-01-05")],
                   [dividend(announced_date="2024-01-04")], [split(share_ratio=0)],
                   [split(kind="unmodeled_rights_issue")]]
        for events in invalid:
            with self.subTest(events=events), self.assertRaises(ValueError):
                self.simulate([10] * 6, events=events)

    def test_missing_event_source_is_not_reported_as_complete_zero_action_history(self):
        result = self.simulate([10] * 4, supplied=False)
        self.assertFalse(result["accounting"]["source_audit_verified"])
        self.assertIn("corporate_action_source_missing", result["accounting"]["blocking_reasons"])

    def test_initial_holdings_cannot_invent_dividend_entitlement_before_window(self):
        with self.assertRaisesRegex(ValueError, "initial.*entitlement"):
            self.simulate([10] * 6, events=[dividend()], start_date="2024-01-04",
                          initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 100}]))

    def test_declared_holder_rounding_supports_odd_lot_full_liquidation(self):
        for ratio, expected in ((0.83788015, 84), (1.14539, 115)):
            with self.subTest(ratio=ratio):
                result = self.simulate([10, 10, 10 / ratio, 10 / ratio],
                    events=[split(share_ratio=ratio, share_rounding="ceil_per_holder")], schema_version=2,
                    initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 100}]),
                    start_date="2024-01-03", cash=5, min_cash_weight=1, rebalance=1)
                self.assertEqual(result["fills"][0]["quantity"], expected)
                self.assertEqual(result["positions"], [])
                self.assertAlmostEqual(result["metrics"]["ending_cash"], 5 + expected * 10 / ratio)
                self.assertEqual(result["metrics"]["dividend_cash_received"], 0)
                self.assertFalse(result["accounting"]["source_audit_verified"])

    def test_rounded_conversion_remains_locked_until_tradable_session(self):
        result = self.simulate([10, 10, 12, 12, 12, 12], schema_version=2,
            events=[split(share_ratio=0.83788015, share_rounding="ceil_per_holder", tradable_date="2024-01-06")],
            initial_positions=pd.DataFrame([{"asset_id": ASSET, "quantity": 100}]),
            start_date="2024-01-03", cash=5, min_cash_weight=1, rebalance=1)
        self.assertEqual([(f["execution_date"], f["quantity"]) for f in result["fills"]], [("2024-01-06", 84)])
        self.assertEqual(result["positions"], [])


class PaperShareRoundingTests(unittest.TestCase):
    def ledger(self, *, quantity=100, ratio=0.83788015, rounding="ceil_per_holder", version=2, exact_json=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "actions.json"
        event = split(share_ratio=ratio)
        if rounding is not None:
            event["share_rounding"] = rounding
        payload = {"schema_version": version, "source_ref": "synthetic rounding fixture",
                   "coverage_start": "2024-01-02", "coverage_end": "2024-01-07",
                   "asset_ids": [ASSET], "events": [event]}
        raw = json.dumps(payload)
        if exact_json is not None:
            raw = raw.replace('"share_ratio": ' + str(ratio), '"share_ratio": ' + exact_json)
        path.write_text(raw, encoding="utf-8")
        positions = {ASSET: quantity} if quantity else {}
        return CorporateActionLedger(path, {ASSET}, [date(2024, 1, d) for d in range(2, 8)], positions), positions

    def intent(self, quantity, intent_id="intent-1"):
        return {"asset_id": ASSET, "intent_id": intent_id, "signed_quantity": quantity,
                "intended_quantity": abs(quantity), "reference_price": 10.0}

    def apply(self, ledger, positions, intents=()):
        return ledger.before_session(date(2024, 1, 4), positions, list(intents))

    def test_rounding_is_once_per_holder_not_per_pending_buy(self):
        ledger, positions = self.ledger()
        cash, intents = self.apply(ledger, positions, [self.intent(100), self.intent(100, "intent-2")])
        self.assertEqual(positions[ASSET], 84)
        self.assertEqual(cash, 0)
        self.assertEqual([i["signed_quantity"] for i in intents], [83.788015, 83.788015])
        self.assertEqual(ledger.journal[0]["unrounded_quantity"], "83.78801500")
        self.assertEqual(ledger.journal[0]["rounding_share_credit"], "0.21198500")
        self.assertEqual(ledger.journal[0]["share_ratio_exact"], "0.83788015")
        self.assertEqual(ledger.journal[0]["share_rounding"], "ceil_per_holder")

    def test_pending_full_sale_includes_the_single_holder_rounding_credit(self):
        ledger, positions = self.ledger()
        _, intents = self.apply(ledger, positions, [self.intent(-100)])
        self.assertEqual(intents[0]["signed_quantity"], -84)
        self.assertEqual(intents[0]["intended_quantity"], 84)
        self.assertAlmostEqual(intents[0]["reference_price"], 10 / 0.83788015)

    def test_partial_sales_do_not_each_receive_a_rounding_credit(self):
        ledger, positions = self.ledger()
        _, intents = self.apply(ledger, positions, [self.intent(-50), self.intent(-50, "intent-2")])
        self.assertEqual(positions[ASSET], 84)
        self.assertEqual([i["signed_quantity"] for i in intents], [-41.8940075, -41.8940075])

    def test_no_existing_holder_cannot_receive_rounding_shares_from_a_pending_buy(self):
        ledger, positions = self.ledger(quantity=0)
        self.apply(ledger, positions, [self.intent(100)])
        self.assertEqual(positions, {})
        self.assertEqual(Decimal(ledger.journal[0]["rounding_share_credit"]), 0)

    def test_decimal_ratio_is_preserved_before_rounding_at_integer_boundary(self):
        ledger, positions = self.ledger(ratio=1.0, exact_json="1.00000000000000000001")
        self.apply(ledger, positions)
        self.assertEqual(positions[ASSET], 101)
        self.assertEqual(ledger.journal[0]["share_ratio_exact"], "1.00000000000000000001")

    def test_integer_result_does_not_gain_an_extra_share_from_binary_float_error(self):
        ledger, positions = self.ledger(ratio=1.1)
        self.apply(ledger, positions)
        self.assertEqual(positions[ASSET], 110)

    def test_pending_buy_does_not_lose_a_round_lot_from_binary_float_error(self):
        ledger, positions = self.ledger(quantity=100000, ratio=1.001)
        _, intents = self.apply(ledger, positions, [self.intent(100000)])
        self.assertEqual(intents[0]["signed_quantity"], 100100)
        self.assertEqual(intents[0]["intended_quantity"], 100100)

    def test_overlapping_full_sales_are_rejected_before_any_position_change(self):
        ledger, positions = self.ledger(ratio=1.14539)
        with self.assertRaisesRegex(ValueError, "aggregate.*sale|sell.*holdings"):
            self.apply(ledger, positions, [self.intent(-100), self.intent(-100, "intent-2")])
        self.assertEqual(positions[ASSET], 100)
        self.assertEqual(ledger.processed, set())
        self.assertEqual(ledger.journal, [])

    def test_aggregate_sales_check_is_independent_of_callers_decimal_precision(self):
        ledger, positions = self.ledger(quantity=100000, ratio=1.001)
        with localcontext() as context:
            context.prec = 3
            with self.assertRaisesRegex(ValueError, "aggregate.*sales"):
                self.apply(ledger, positions, [self.intent(-100000), self.intent(-100, "intent-2")])
        self.assertEqual(positions[ASSET], 100000)
        self.assertEqual(ledger.processed, set())

    def test_event_is_applied_only_once(self):
        ledger, positions = self.ledger()
        self.apply(ledger, positions)
        self.apply(ledger, positions)
        self.assertEqual(positions[ASSET], 84)
        self.assertEqual(len(ledger.journal), 1)

    def test_v2_requires_an_explicit_supported_rounding_rule(self):
        for rule in (None, "nearest", "cash_in_lieu", True):
            with self.subTest(rule=rule), self.assertRaisesRegex(ValueError, "rounding|fields"):
                self.ledger(rounding=rule)

    def test_legacy_schema_keeps_fractional_conversion_rejection(self):
        ledger, positions = self.ledger(rounding=None, version=1)
        with self.assertRaisesRegex(ValueError, "fractional ETF"):
            self.apply(ledger, positions)

    def test_legacy_schema_does_not_silently_accept_a_new_rounding_rule(self):
        with self.assertRaisesRegex(ValueError, "fields"):
            self.ledger(version=1)

    def test_reject_fractional_policy_accepts_integer_splits_only(self):
        for ratio in (2, 10):
            ledger, positions = self.ledger(ratio=ratio, rounding="reject_fractional")
            self.apply(ledger, positions)
            self.assertEqual(positions[ASSET], 100 * ratio)
        ledger, positions = self.ledger(rounding="reject_fractional")
        with self.assertRaisesRegex(ValueError, "fractional"):
            self.apply(ledger, positions)

    def test_holder_rounding_rejects_non_integer_negative_or_unsafe_holdings(self):
        for quantity in (-1, 0.5, float("nan"), float("inf"), 2 ** 53):
            with self.subTest(quantity=quantity), self.assertRaisesRegex(ValueError, "whole|quantity"):
                ledger, positions = self.ledger(quantity=quantity)
                self.apply(ledger, positions)

    def test_unsafe_result_is_rejected_before_mutating_positions(self):
        ledger, positions = self.ledger(ratio=1e300)
        with self.assertRaisesRegex(ValueError, "quantity"):
            self.apply(ledger, positions)
        self.assertEqual(positions[ASSET], 100)
        self.assertEqual(ledger.journal, [])
