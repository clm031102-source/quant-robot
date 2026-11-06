"""Hand-calculated planning cases, synthetic state and completed minutes only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, TradingRule
from quant_robot.research.crypto_carry_policy import (
    CompletedPrices, KnownPoint, OHLCMinute, SCENARIOS, VolumeMinute, WalletState,
    minute_risk_envelope, plan_target, volume_capacity,
)

D = Decimal
AT = datetime(2001, 1, 1, 0, 22, tzinfo=timezone.utc)


def fixture(*, spot_cash="500", futures_cash="500", spot_step=".001", minimum="10"):
    model = CarryModel(start=AT, spot_rule=TradingRule(spot_step, spot_step, minimum),
        futures_rule=TradingRule(".001", ".001", minimum),
        spot_cash=spot_cash, futures_cash=futures_cash, fees=FeeScenario(".001", ".0005", ".0002"))
    model.queue_quote(AT, spot="1000")
    model.run(AT)
    return model


def rows(volume="100", *, received_delay=timedelta(0)):
    return tuple(VolumeMinute(AT - timedelta(minutes=19 - i),
        AT - timedelta(minutes=19 - i) + received_delay, volume) for i in range(20))


def plan(model, *, spot_rows=None, future_rows=None):
    prices = CompletedPrices(AT, AT, model.spot_price, model.future_price, model.mark_price)
    return plan_target(model, decision_at=AT, prices=prices,
        spot_minutes=rows() if spot_rows is None else spot_rows,
        futures_minutes=rows() if future_rows is None else future_rows)


class CryptoCarryPolicyTests(unittest.TestCase):
    def test_fees_make_point_four_illegal_then_search_lowers_one_step(self):
        model = fixture()
        before = deepcopy(model.__dict__)
        result = plan(model)
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.reason, "largest_feasible_below_equal_quantity_ceiling")
        self.assertEqual(result.equal_quantity_ceiling, D(".400"))
        self.assertEqual(result.final_short_btc, D(".399"))
        self.assertEqual([leg.quantity for leg in result.legs], [D(".400"), D(".399")])
        self.assertEqual(result.candidates_checked, 2)
        self.assertEqual(result.projected_delta_btc, D(".0006"))
        self.assertEqual(model.__dict__, before)
        self.assertFalse(result.qualified)
        self.assertEqual(result.real_forward, 0)
        self.assertTrue(model.register_plan(result.legs, kind=result.kind))
        model.run(AT + timedelta(minutes=2))
        self.assertEqual(model.nav, result.projected_nav)
        self.assertEqual(model.gross, result.projected_gross)
        self.assertEqual(model.short_btc, result.final_short_btc)
        self.assertGreaterEqual(model.futures_equity, D("1.25") * model.short_btc * model.mark_price)

    def test_existing_dust_reduces_purchase_and_is_not_deleted(self):
        plain = plan(fixture())
        model = fixture(spot_cash="499.1")
        model.spot_btc = D(".0009")
        result = plan(model)
        self.assertEqual(result.final_short_btc, plain.final_short_btc)
        self.assertEqual(result.legs[0].quantity, D(".399"))
        self.assertLess(result.legs[0].quantity, plain.legs[0].quantity)
        self.assertEqual(result.projected_delta_btc, D(".000501"))
        self.assertEqual(model.spot_btc, D(".0009"))

    def test_base_fee_rounds_up_to_eight_places_before_covering_short(self):
        model = fixture(spot_step=".00000001")
        result = plan(model)
        buy = result.legs[0].quantity
        self.assertEqual(result.final_short_btc, D(".399"))
        self.assertEqual(buy, D(".39939940"))
        self.assertEqual(result.projected_delta_btc, D("0"))

    def test_ninety_percent_trigger_reduces_both_legal_legs_to_eighty(self):
        model = fixture(spot_cash="100", futures_cash="575")
        model.spot_btc = model.short_btc = D(".4")
        model.entry_vwap = D("1000")
        model.spot_price = model.future_price = model.mark_price = D("1200")
        # NAV=1075, gross=960: below the 90% trigger, so no premature trim.
        self.assertEqual(plan(model).status, "no_action")
        model.futures_cash = D("560")
        self.assertGreater(model.gross, D(".9") * model.nav)
        before = deepcopy(model.__dict__)
        result = plan(model)
        self.assertEqual(result.status, "planned")
        self.assertEqual([leg.side for leg in result.legs], ["short_close", "spot_sell"])
        self.assertEqual(result.legs[0].quantity, result.legs[1].quantity)
        self.assertLessEqual(result.projected_gross, D(".8") * result.projected_nav)
        self.assertEqual(model.__dict__, before)
        model.register_plan(result.legs, kind=result.kind)
        model.run(AT + timedelta(minutes=2))
        self.assertEqual(model.nav, result.projected_nav)
        self.assertEqual(model.short_btc, result.final_short_btc)

    def test_low_notional_cannot_reduce_only_one_side(self):
        model = fixture(spot_cash="0", futures_cash="2")
        model.spot_btc = model.short_btc = D(".02")
        model.entry_vwap = D("100")
        model.spot_price = model.future_price = model.mark_price = D("100")
        before = deepcopy(model.__dict__)
        result = plan(model)
        self.assertEqual(result.status, "blocked")
        self.assertIn("minimum_notional", result.reason)
        self.assertEqual(result.legs, ())
        self.assertEqual(model.__dict__, before)

    def test_separate_twenty_minute_capacities_not_infinite_or_pooled(self):
        self.assertEqual(volume_capacity(rows("10"), decision_at=AT), D(".1"))
        model = fixture()
        for spot_rows, future_rows in ((rows(".5"), rows()), (rows(), rows(".5"))):
            result = plan(model, spot_rows=spot_rows, future_rows=future_rows)
            self.assertEqual(result.status, "blocked")
            self.assertFalse(result.legs)
        result = plan(model, spot_rows=rows("10"), future_rows=rows("20"))
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.legs[0].capacity, D(".1"))
        self.assertEqual(result.legs[1].capacity, D(".2"))
        self.assertLessEqual(result.legs[0].quantity, D(".1"))
        self.assertLessEqual(result.legs[1].quantity, D(".2"))

    def test_missing_future_unreceived_or_unordered_volume_rejected(self):
        for bad in (rows()[:-1], rows()[1:] + rows()[:1], rows(received_delay=timedelta(seconds=1))):
            with self.assertRaises(ValueError):
                plan(fixture(), spot_rows=bad)
        self.assertEqual(plan(fixture(), spot_rows=rows("0")).reason, "zero_completed_volume_capacity")

    def test_no_cash_reallocation_and_only_nine_fee_scenarios(self):
        model = fixture(spot_cash="1", futures_cash="999")
        self.assertEqual(plan(model).status, "blocked")
        self.assertEqual(model.spot_cash, D("1"))
        self.assertEqual(len(SCENARIOS), 9)
        model = fixture()
        model.fees = FeeScenario("0", "0", "0")
        with self.assertRaisesRegex(ValueError, "nine frozen"):
            plan(model)

    def test_quote_state_and_decision_must_share_completed_prefix(self):
        model = fixture()
        for prices in (CompletedPrices(AT, AT + timedelta(seconds=1), "1000", "1000", "1000"),
                       CompletedPrices(AT, AT, "1001", "1000", "1000"),
                       CompletedPrices(AT-MINUTE, AT, "1000", "1000", "1000")):
            with self.assertRaises(ValueError):
                plan_target(model, decision_at=AT, prices=prices, spot_minutes=rows(), futures_minutes=rows())

    def test_each_frozen_scenario_agrees_with_later_kernel_accounting(self):
        for spot_fee, future_fee, slip in sorted(SCENARIOS):
            with self.subTest(spot=spot_fee, future=future_fee, slippage=slip):
                model = fixture()
                model.fees = FeeScenario(spot_fee, future_fee, slip)
                result = plan(model)
                self.assertEqual(result.status, "planned")
                model.register_plan(result.legs, kind=result.kind)
                model.run(AT + timedelta(minutes=2))
                self.assertEqual(model.nav, result.projected_nav)
                self.assertEqual(model.gross, result.projected_gross)
                self.assertEqual(model.delta_btc, result.projected_delta_btc)
                self.assertFalse(model.unresolved)

    def test_legal_minimum_buy_can_exceed_the_net_cover_quantity(self):
        model = fixture(spot_cash="113")
        model.spot_btc, model.short_btc, model.entry_vwap = D(".387"), D(".390"), D("1000")
        model.spot_rule = TradingRule(".015", ".001", "10")
        model.futures_rule = TradingRule(".001", ".001", "5")
        result = plan(model)
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.final_short_btc, D(".397"))
        self.assertEqual(result.legs[0].quantity, D(".015"))
        self.assertLessEqual(abs(result.projected_delta_btc)*model.spot_price, D(".005")*result.projected_nav)

    def test_one_extra_spot_sale_step_keeps_maximum_legal_future_target(self):
        model = fixture(spot_cash="0")
        model.spot_btc = model.short_btc = D(".5")
        model.entry_vwap = D("1000")
        result = plan(model)
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.reason, "largest_feasible_below_equal_quantity_ceiling")
        self.assertEqual(result.equal_quantity_ceiling, D(".4"))
        self.assertEqual(result.final_short_btc, D(".4"))
        self.assertEqual([leg.quantity for leg in result.legs], [D(".1"), D(".101")])
        self.assertEqual(result.projected_delta_btc, D("-.001"))
        model.register_plan(result.legs, kind=result.kind)
        model.run(AT+2*MINUTE)
        self.assertEqual(model.nav, result.projected_nav)
        self.assertFalse(model.unresolved)

    def test_future_queued_quote_does_not_resize_plan_and_execution_can_reject(self):
        model = fixture()
        expected = plan(model)
        model.queue_quote(AT+MINUTE, spot="2000")
        result = plan(model)
        self.assertEqual(result, expected)
        model.register_plan(result.legs, kind=result.kind)
        model.run(AT+2*MINUTE)
        self.assertEqual(model.spot_btc, 0)
        self.assertEqual(model.short_btc, 0)
        self.assertTrue(any(row["event"] == "leg_rejected" for row in model.journal))


def state(*, at=AT, label="start", cash="500", spot_cash="100", btc=".4", short=".4"):
    return WalletState(at, label, spot_cash, cash, btc, short, "1000", "0", "1000", "1000")


def candle(low="900", high="1100", *, close="1000", received=None):
    return OHLCMinute(AT, AT+MINUTE, received or AT+MINUTE, "1000", high, low, close)


class CryptoCarryEnvelopeTests(unittest.TestCase):
    def test_all_corners_safe_is_conditional_envelope_verification(self):
        result = minute_risk_envelope(states=(state(),), spot=candle("990", "1010"), mark=candle("990", "1010"),
            evaluated_at=AT+MINUTE, known_points=(KnownPoint(AT, 0, "1000", "1000"),), coverage_complete=True)
        self.assertEqual(result.status, "verified_within_envelope")
        self.assertEqual(result.nav_min, D("992"))
        self.assertEqual(result.nav_max, D("1008"))
        self.assertEqual(result.margin_buffer_min, D("92"))
        self.assertFalse(result.qualified)
        self.assertFalse(result.confirmed_breaches)

    def test_rectangle_violation_does_not_invent_confirmed_path(self):
        result = minute_risk_envelope(states=(state(),), spot=candle("1000", "2000"),
            mark=candle("1000", "2000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"),), coverage_complete=True)
        self.assertEqual(result.status, "unresolved_path")
        self.assertFalse(result.confirmed_breaches)
        self.assertIn("gross_over_100_percent", result.possible_breaches)
        self.assertIn("futures_wallet_below_1x", result.possible_breaches)

    def test_known_observation_breach_is_separate_from_possible_extremes(self):
        result = minute_risk_envelope(states=(state(),), spot=candle("1000", "2000", close="2000"),
            mark=candle("1000", "2000", close="2000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"), KnownPoint(AT+MINUTE, 0, "2000", "2000")),
            coverage_complete=True)
        self.assertEqual(result.status, "confirmed_breach")
        self.assertIn("gross_over_100_percent", result.confirmed_breaches)
        self.assertIn("futures_wallet_below_1x", result.confirmed_breaches)

    def test_event_wallet_cash_change_cannot_hide_drawdown(self):
        event = AT+timedelta(seconds=15, milliseconds=15)
        result = minute_risk_envelope(states=(state(), state(at=event, label="after_funding", cash="90")),
            spot=candle("1000", "1000"), mark=candle("1000", "1000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"), KnownPoint(event, 1, "1000", "1000")),
            coverage_complete=True)
        self.assertEqual(result.status, "confirmed_breach")
        self.assertEqual(result.nav_min, D("590"))
        self.assertIn("global_drawdown_over_40_percent", result.confirmed_breaches)
        self.assertIn("daily_loss_2_percent_trigger", result.known_pause_triggers)

    def test_possible_intraminute_peak_participates_without_claiming_actual_peak(self):
        result = minute_risk_envelope(states=(state(spot_cash="0", btc=".5", short="0"),),
            spot=candle("300", "2500"), mark=candle("1000", "1000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"),), coverage_complete=True)
        self.assertEqual(result.nav_min, D("650"))
        self.assertEqual(result.peak_upper_bound, D("1750"))
        self.assertGreater(result.drawdown_upper_bound, D(".4"))
        self.assertEqual(result.status, "unresolved_path")
        self.assertFalse(result.confirmed_breaches)

    def test_incomplete_event_coverage_cannot_claim_all_paths_verified(self):
        result = minute_risk_envelope(states=(state(),), spot=candle(), mark=candle(), evaluated_at=AT+MINUTE)
        self.assertEqual(result.status, "unresolved_path")
        self.assertFalse(result.coverage_complete)

    def test_possible_daily_pause_alone_leaves_runtime_path_unresolved(self):
        result = minute_risk_envelope(states=(state(),), spot=candle(), mark=candle(),
            evaluated_at=AT+MINUTE, coverage_complete=True)
        self.assertFalse(result.possible_breaches)
        self.assertIn("daily_loss_2_percent_trigger", result.possible_pause_triggers)
        self.assertEqual(result.status, "unresolved_path")

    def test_exact_gross_one_is_touch_not_breach(self):
        result = minute_risk_envelope(states=(state(spot_cash="0", cash="500", btc=".5", short=".5"),),
            spot=candle("1000", "1000"), mark=candle("1000", "1000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"),), coverage_complete=True)
        self.assertEqual(result.status, "verified_within_envelope")
        self.assertIn("gross_at_100_percent", result.known_touches)
        self.assertNotIn("gross_over_100_percent", result.confirmed_breaches)

    def test_unreceived_candle_and_point_outside_wallet_prefix_rejected(self):
        with self.assertRaises(ValueError):
            minute_risk_envelope(states=(state(),), spot=candle(received=AT+2*MINUTE),
                mark=candle(), evaluated_at=AT+MINUTE, coverage_complete=True)
        with self.assertRaises(ValueError):
            minute_risk_envelope(states=(state(), state(at=AT+timedelta(seconds=15), label="after")),
                spot=candle(), mark=candle(), evaluated_at=AT+MINUTE,
                known_points=(KnownPoint(AT+timedelta(seconds=20), 0, "1000", "1000"),), coverage_complete=True)

    def test_negative_futures_cash_remains_visible_as_confirmed_risk(self):
        result = minute_risk_envelope(states=(state(cash="-600"),),
            spot=candle("1000", "1000"), mark=candle("1000", "1000"), evaluated_at=AT+MINUTE,
            known_points=(KnownPoint(AT, 0, "1000", "1000"),), coverage_complete=True)
        self.assertEqual(result.status, "confirmed_breach")
        self.assertIn("nonpositive_nav", result.confirmed_breaches)
        self.assertIn("futures_wallet_below_1x", result.confirmed_breaches)


MINUTE = timedelta(minutes=1)

if __name__ == "__main__":
    unittest.main()
