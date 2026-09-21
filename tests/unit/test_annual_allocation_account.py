"""Behavioral fixtures for the continuous account, never market-outcome tests."""
from datetime import date, timedelta
import unittest

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account

A = 'CN_ETF_XSHG_510300'
G = 'CN_ETF_XSHG_518880'


def fixture(count=34, assets=(A, G), price=4):
    days = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    bars = [{'asset_id': asset, 'date': day, 'open': str(price), 'high': str(price),
             'low': str(price), 'close': str(price), 'volume': '100000', 'source': 'fixture'}
            for asset in assets for day in days]
    return days, bars


def change(bars, day, asset=A, *, price=None, volume=None, **flags):
    row = next(row for row in bars if row['date'] == day and row['asset_id'] == asset)
    if price is not None:
        row.update({key: str(price) for key in ('open', 'high', 'low', 'close')})
    if volume is not None:
        row['volume'] = str(volume)
    row.update(flags)


def cycle(days, entry=20, exit=25, name='one'):
    return {'cycle_id': name, 'entry_date': days[entry], 'exit_date': days[exit]}


def run(days, bars, *, assets=(A, G), cycles=None, actions=(), **kwargs):
    return run_allocation_account(bars, sessions=days, actions=actions,
        cycles=cycles or [cycle(days)], assets=assets,
        config=AllocationConfig(slippage_bps=0, **kwargs))


def cash_action(days, *, record=21, ex=22, pay=24, cash='0.1'):
    return {'event_id': 'cash-one', 'asset_id': A, 'record_date': days[record],
            'ex_date': days[ex], 'pay_date': days[pay], 'cash_per_unit': cash,
            'share_multiplier': '1'}


class AnnualAllocationAccountTests(unittest.TestCase):
    def test_two_assets_fee_paid_and_cash_carried_across_cycles(self):
        days, bars = fixture()
        for day in days:
            change(bars, day, G, price=2.5)
        result = run(days, bars, cycles=[cycle(days), cycle(days, 28, 32, 'two')])
        self.assertEqual(result['metrics']['ending_cash'], 9960)
        self.assertEqual(result['metrics']['fees_paid'], 40)
        self.assertEqual(len(result['fills']), 8)
        self.assertTrue(result['risk']['terminal_settled'])
        self.assertEqual(result['equity_curve'][0]['equity'], 10000)
        self.assertEqual(result['metrics']['paired_entry_cycles'], ['one', 'two'])

    def test_entry_price_gap_cancels_original_quantity_without_resizing(self):
        days, bars = fixture()
        change(bars, days[20], price=5.1)
        result = run(days, bars)
        self.assertFalse(any(f['asset_id'] == A for f in result['fills']))
        self.assertTrue(any(e['reason'] == 'entry_budget_or_cash' for e in result['events']))
        self.assertEqual(result['metrics']['paired_entry_cycles'], [])

    def test_record_entitlement_survives_ex_date_sale_and_waits_for_pay_date(self):
        days, bars = fixture(26, (A,))
        result = run(days, bars, assets=(A,), cycles=[cycle(days, 20, 22)], actions=[cash_action(days)])
        rows = {r['date']: r for r in result['equity_curve']}
        self.assertEqual(rows[days[22]]['cash'], 9990)
        self.assertEqual(rows[days[22]]['dividend_receivable'], 20)
        self.assertEqual(rows[days[24]]['cash'], 10010)
        self.assertEqual(rows[days[24]]['dividend_receivable'], 0)

    def test_buy_on_ex_date_does_not_gain_preceding_record_entitlement(self):
        days, bars = fixture(26, (A,))
        result = run(days, bars, assets=(A,), actions=[cash_action(days, record=19, ex=20, pay=22)])
        self.assertEqual(result['metrics']['dividend_cash_received'], 0)
        self.assertEqual(result['metrics']['ending_cash'], 9990)

    def test_pay_date_cash_is_unavailable_to_that_sessions_entry(self):
        days, bars = fixture(30, (A,))
        for day in days[23:]:
            change(bars, day, price=3.3)
        result = run(days, bars, assets=(A,), initial_cash=1000,
            cycles=[cycle(days, 20, 22), cycle(days, 24, 28, 'two')], actions=[cash_action(days)])
        second = next(f for f in result['fills'] if f['date'] == days[24])
        self.assertEqual(second['quantity'], 200)
        row = next(r for r in result['equity_curve'] if r['date'] == days[24])
        self.assertEqual(row['cash_before_distribution_payment'], 325)
        self.assertEqual(row['cash'], 345)

    def test_unfilled_trim_is_cancelled_when_next_mark_is_within_cap(self):
        days, bars = fixture(27, (A,), price=3.3)
        change(bars, days[21], price=3.36)
        change(bars, days[22], price=3.32, volume=0)
        result = run(days, bars, assets=(A,))
        self.assertFalse(any(f['reason'] == 'position_trim' for f in result['fills']))
        self.assertEqual([f['quantity'] for f in result['fills']], [300, 300])
        self.assertTrue(any(b['reason'] == 'position_limit' for b in result['risk']['breaches']))
        self.assertFalse(result['risk']['within_all_observed_limits'])

    def test_partial_mandatory_exit_uses_daily_one_percent_and_persists(self):
        days, bars = fixture(28, (A,))
        change(bars, days[25], volume=10000)
        result = run(days, bars, assets=(A,))
        sells = [f for f in result['fills'] if f['side'] == 'sell']
        self.assertEqual([(f['date'], f['quantity']) for f in sells], [(days[25], 100), (days[26], 100)])
        self.assertEqual(result['metrics']['ending_cash'], 9985)

    def test_current_capacity_shortfall_cancels_entire_buy(self):
        days, bars = fixture(26, (A,))
        change(bars, days[20], volume=10000)
        result = run(days, bars, assets=(A,))
        self.assertEqual(result['fills'], [])
        self.assertTrue(any(e['reason'] == 'entry_current_capacity' for e in result['events']))

    def test_current_volume_spike_cannot_increase_prior_order_size(self):
        days, bars = fixture(26, (A,))
        for day in days[:20]:
            change(bars, day, volume=10000)
        change(bars, days[20], volume=1000000000)
        result = run(days, bars, assets=(A,))
        self.assertEqual(result['fills'][0]['quantity'], 100)

    def test_loss_stop_acts_next_session_and_never_resets_for_later_cycle(self):
        days, bars = fixture(34, (A,))
        change(bars, days[21], price=3.6)
        change(bars, days[22], price=3.5)
        result = run(days, bars, assets=(A,), cycles=[cycle(days), cycle(days, 28, 32, 'two')])
        self.assertEqual([(f['date'], f['side']) for f in result['fills']], [(days[20], 'buy'), (days[22], 'sell')])
        self.assertTrue(result['risk']['new_entries_halted'])
        self.assertEqual(result['metrics']['ending_cash'], 9890)

    def test_drawdown_includes_initial_cash_and_persists_after_partial_sale(self):
        days, bars = fixture(28, (A,))
        change(bars, days[21], price=3.5)
        change(bars, days[22], price=3.5, volume=10000)
        result = run(days, bars, assets=(A,), max_daily_loss_cny=1000, max_drawdown='.01')
        self.assertTrue(any(b['reason'] == 'drawdown_limit' for b in result['risk']['breaches']))
        self.assertEqual([f['date'] for f in result['fills'] if f['side'] == 'sell'], [days[22], days[23]])

    def test_unfilled_terminal_exit_does_not_invent_cash(self):
        days, bars = fixture(26, (A,))
        change(bars, days[25], volume=0)
        result = run(days, bars, assets=(A,))
        self.assertFalse(result['risk']['terminal_settled'])
        self.assertEqual(result['positions'][A], 200)
        self.assertEqual(result['metrics']['ending_cash'], 9195)

    def test_known_suspension_blocks_fill_but_unknown_flags_never_certify_execution(self):
        days, bars = fixture(27, (A,))
        change(bars, days[25], suspended=True)
        result = run(days, bars, assets=(A,))
        self.assertEqual(result['fills'][-1]['date'], days[26])
        self.assertFalse(result['executable'])
        self.assertFalse(result['source_quality_verified'])
        self.assertGreater(result['unknown_execution_flag_rows'], 0)

    def test_adverse_tick_and_cent_fee_rounding(self):
        days, bars = fixture(26, (A,))
        result = run_allocation_account(bars, sessions=days, actions=[], assets=(A,),
            cycles=[cycle(days)], config=AllocationConfig(slippage_bps=10))
        self.assertEqual([f['price'] for f in result['fills']], [4.004, 3.996])
        self.assertEqual(result['metrics']['ending_cash'], 9988.4)

    def test_cash_distribution_rounds_once_per_holder(self):
        days, bars = fixture(26, (A,))
        result = run(days, bars, assets=(A,), actions=[cash_action(days, cash='.003333')])
        self.assertEqual(result['metrics']['dividend_cash_received'], .67)

    def test_dense_calendar_duplicates_and_unsupported_split_are_rejected(self):
        days, bars = fixture(26, (A,))
        for invalid in [bars[:-1], bars+[bars[0]]]:
            with self.subTest(kind=len(invalid)), self.assertRaises(ValueError):
                run(days, invalid, assets=(A,))
        action = {**cash_action(days), 'share_multiplier': '2'}
        with self.assertRaises(ValueError):
            run(days, bars, assets=(A,), actions=[action])

    def test_limit_holding_exit_is_causal_even_before_cycle_end(self):
        days, bars = fixture(28, (A,))
        result = run(days, bars, assets=(A,), max_holding_sessions=2)
        self.assertEqual(result['fills'][-1]['date'], days[22])
        self.assertEqual(result['fills'][-1]['reason'], 'max_holding_exit')

    def test_failed_exit_on_maximum_holding_close_is_already_a_breach(self):
        days, bars = fixture(23, (A,))
        change(bars, days[22], volume=0)
        result = run(days, bars, assets=(A,), cycles=[cycle(days, 20, 22)], max_holding_sessions=2)
        self.assertTrue(any(b['reason'] == 'holding_limit' and b['date'] == days[22]
                            for b in result['risk']['breaches']))

    def test_advance_partial_sale_is_a_whole_lot_before_current_volume(self):
        days, bars = fixture(43, (A,))
        for day in days[20:40]:
            change(bars, day, volume=15000 if day != days[20] else 100000)
        # The20previous sessions at exit41 are all15000, independent of exit volume.
        change(bars, days[40], volume=15000)
        result = run(days, bars, assets=(A,), cycles=[cycle(days, 20, 41)])
        sale = next(f for f in result['fills'] if f['side'] == 'sell')
        self.assertEqual(sale['prior_capacity'], 150)
        self.assertEqual(sale['requested_quantity'], 100)

    def test_unpaid_terminal_receivable_prevents_cash_completion(self):
        days, bars = fixture(26, (A,))
        action = {**cash_action(days), 'pay_date': '2020-02-01'}
        result = run(days, bars, assets=(A,), actions=[action])
        self.assertEqual(result['positions'], {})
        self.assertFalse(result['risk']['terminal_settled'])
        self.assertEqual(result['metrics']['ending_cash'], 9990)
        self.assertEqual(result['metrics']['ending_equity'], 10010)


if __name__ == '__main__':
    unittest.main()
