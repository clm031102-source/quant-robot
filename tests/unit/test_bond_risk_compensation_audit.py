"""Small hand-calculated ledger and accounting corruption cases."""
import copy
from datetime import date, timedelta
from decimal import Decimal, getcontext, localcontext
import unittest

from quant_robot.research.bond_risk_compensation_audit import audit_account


def example():
    days = [(date(2001, 1, 1)+timedelta(days=i)).isoformat() for i in range(23)]
    fixture = dict(sessions=days, bars=[dict(date=d, open='90' if i<22 else '9',
        high='90' if i<22 else '9', low='90' if i<22 else '9', close='90' if i<22 else '9',
        volume='1000000', suspended=False, limit_up=False, limit_down=False) for i,d in enumerate(days)],
        actions=[dict(event_id='cash', record_date=days[20], ex_date=days[21], pay_date=days[22],
            cash_per_unit='.2', share_multiplier='1', record_quantity_unit='pre_split', cash_per_unit_basis='pre_split')],
        split_events=[dict(event_id='split',record_date=days[21],ex_date=days[22],known_date=days[19],share_multiplier='10')])
    with localcontext() as ctx:
        ctx.prec=40
        peak=Decimal('10015.5')
        last_dd=1-Decimal('10011')/peak
        rows=[]
        for i,d in enumerate(days):
            nav = Decimal('10000' if i<20 else '9995.5' if i==20 else '10015.5' if i==21 else '10011')
            previous = Decimal('10000' if i<=20 else '9995.5' if i==21 else '10015.5')
            rows.append(dict(date=d,index=i,cash='10000' if i<20 else '995.5' if i<22 else '10011',
                cash_before_distribution_payment='10000' if i<20 else '995.5' if i<22 else '9991',
                quantity=0 if i<20 or i==22 else 100 if i==20 else 1000,
                market_value='9000' if i in (20,21) else '0',dividend_receivable='20' if i==21 else '0',
                equity=str(nav),previous_close_NAV=str(previous),global_peak='10000' if i<=20 else str(peak),
                daily_loss_CNY=str(max(previous-nav,Decimal(0))),
                sampled_close_drawdown='0' if i<20 or i==21 else '.00045' if i==20 else str(last_dd),
                holding_sessions=1 if i==20 else 2 if i==21 else 0,terminal_session=i==22,
                raw_close='90' if i<22 else '9',valuation_price='90' if i<21 else '9',
                post_registration_quote_unit_factor=10 if i==21 else 1,
                cumulative_conversion_delta=900 if i>=21 else 0,split_event_applied=i>=21))
    fills=[dict(date=days[20],side='buy',quantity=100,requested_quantity=100,raw_open_price='90',
        execution_price='90.000',notional='9000',fee='4.50',cash_before='10000',cash_after='995.50',
        position_after=100,slippage_and_tick_cost_CNY='0',plan=dict(budget='10000'),rejected=None),
        dict(date=days[22],side='sell',quantity=1000,requested_quantity=1000,raw_open_price='9',
        execution_price='9.000',notional='9000',fee='4.50',cash_before='995.50',cash_after='9991.00',
        position_after=0,slippage_and_tick_cost_CNY='0',rejected=None)]
    actions=[dict(date=days[20],event_id='cash',kind='record_entitlement',quantity=100),
        dict(date=days[21],event_id='cash',kind='receivable_created',amount='20'),
        dict(date=days[21],event_id='split',kind='split_registration',quantity_before=100,
             quantity_after=1000,conversion_delta=900),
        dict(date=days[22],event_id='cash',kind='paid_after_fills',amount='20')]
    account=dict(initial_cash_CNY='10000',cost_case=dict(minimum_commission_CNY=0,
        slippage_bps_each=0,commission_bps_each=5),rows=rows,fills=fills,actions=actions,
        summary=dict(cash='10011',remaining_quantity=0,dividend_receivable='0',terminal_book_NAV='10011',
        net_book_PnL='11',cash_PnL='11',total_commission_CNY='9',dividend_cash_received='20',
        total_slippage_and_tick_cost_CNY='0',daily_close_model_max_drawdown='.00045',
        episodes_started=1,completed_roundtrips=1,maximum_holding_sessions=2,nontrade_conversion_delta=900,
        pending_record_entitlements=[],terminal_unsettled=False,observed_drawdown_over_40pct=False))
    return fixture,account


class BondAccountingTests(unittest.TestCase):
    def test_hand_calculated_split_dividend_fee_ledger(self):
        fixture, account=example()
        result=audit_account(fixture,account)
        self.assertEqual(result['terminal_NAV'],'10011.000')
        self.assertFalse(result['decisions_independently_validated'])

    def test_each_economic_corruption_is_rejected(self):
        fixture, original=example()
        edits=[lambda a:a['fills'][0].update(fee='0'),
            lambda a:a['fills'][1].update(cash_after='10011'),
            lambda a:a['rows'][21].update(quantity=10000),
            lambda a:a['rows'][20].update(equity='10000'),
            lambda a:a['rows'][20].update(cash='-1'),
            lambda a:a['actions'].append(copy.deepcopy(a['actions'][-1])),
            lambda a:a['summary'].update(terminal_unsettled=True),
            lambda a:a['summary'].update(total_slippage_and_tick_cost_CNY='1')]
        for i,edit in enumerate(edits):
            with self.subTest(case=i):
                account=copy.deepcopy(original); edit(account)
                with self.assertRaises(ValueError): audit_account(fixture,account)

    def test_missing_duplicate_or_extra_rows_and_fills_rejected(self):
        fixture, original=example()
        for edit in (lambda a:a['rows'].pop(),
                     lambda a:a['rows'].__setitem__(1,copy.deepcopy(a['rows'][0])),
                     lambda a:a['fills'].append(copy.deepcopy(a['fills'][0]))):
            account=copy.deepcopy(original); edit(account)
            with self.assertRaises(ValueError): audit_account(fixture,account)

    def test_source_amount_units_and_capacity_not_taken_from_ledger(self):
        fixture, account=example()
        for edit in (lambda f:f['actions'][0].update(cash_per_unit='2'),
                     lambda f:f['actions'][0].update(cash_per_unit_basis='post_split'),
                     lambda f:[bar.update(volume='1') for bar in f['bars']]):
            source=copy.deepcopy(fixture); edit(source)
            with self.assertRaises(ValueError): audit_account(source,account)

    def test_explicit_cross_basis_preserves_original_cash(self):
        fixture, account=example()
        fixture['actions'][0].update(cash_per_unit='.02',cash_per_unit_basis='post_split',
                                     cash_basis_mapping='explicit_split10_conversion')
        self.assertEqual(audit_account(fixture,account)['status'],'accounting_consistent')

    def test_decimal_context_is_independent_and_restored(self):
        fixture, account=example()
        with localcontext() as context:
            context.prec=7
            before=getcontext().copy()
            self.assertEqual(audit_account(fixture,account)['status'],'accounting_consistent')
            self.assertEqual(getcontext().prec,before.prec)
            self.assertEqual(getcontext().flags,before.flags)

    def test_terminal_sale_does_not_erase_unexercised_record_rights(self):
        fixture, account=example()
        day=fixture['sessions'][21]
        fixture['actions'].append(dict(event_id='later',record_date=day,ex_date='2001-01-25',
            pay_date='2001-01-26',cash_per_unit='.1',share_multiplier='1',
            record_quantity_unit='pre_split',cash_per_unit_basis='pre_split'))
        account['actions'].insert(2,dict(date=day,event_id='later',kind='record_entitlement',quantity=100))
        account['summary'].update(terminal_unsettled=True,pending_record_entitlements=[
            dict(event_id='later',record_quantity=100,declared_cash_per_unit='.1',
                 included_in_NAV=False,spendable_cash=False)])
        self.assertEqual(audit_account(fixture,account)['status'],'accounting_consistent')
        account['summary']['pending_record_entitlements'][0]['record_quantity']=1000
        with self.assertRaisesRegex(ValueError,'pending record quantity'):
            audit_account(fixture,account)


if __name__=='__main__':
    unittest.main()
