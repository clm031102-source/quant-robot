import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
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
                 max_asset_weight=1.0, initial_positions=None, start_date=None, supplied=True, omit_asset_bar_date=None, min_cash_weight=0):
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
            path.write_text(json.dumps({"schema_version": 1, "source_ref": "synthetic fixture",
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
