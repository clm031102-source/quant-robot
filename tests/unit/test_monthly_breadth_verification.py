"""Independent hand ledger adaptation, never imports the strategy model."""
import copy
import hashlib
import unittest
from decimal import Decimal, getcontext, localcontext
from datetime import date, timedelta
import calendar

from quant_robot.research import monthly_breadth_verification as V
from tests.unit.test_equity_gold_constant_mix_verification import hand_case


def monthly_hand_case(**kwargs):
    fixture, account = hand_case(**kwargs)
    account['method_sha256'] = V.METHOD
    account['commission_bps'] = 1
    if account['policy'] != 'cash':
        account['policy'] = 'breadth'
    for group in ('intents', 'fills', 'rejections', 'unknown_execution_constraints', 'capacity_failures'):
        for item in account[group]:
            item['phase'] = item['phase'].replace('quarter_', 'monthly_')
    for item in account['risk_records']:
        item['kind'] = item['kind'].replace('next_quarter', 'next_month')
    # New terminal is open-only: do not apply the old close-time sale-cash release.
    account['days'][-1]['after'] = copy.deepcopy(account['days'][-1]['before_close_cash_release'])
    terminal_state = account['days'][-1]['after']
    account['summary']['terminal_spendable_cash'] = terminal_state['spendable_cash']
    account['summary']['terminal_locked_sale_cash'] = terminal_state['locked_sale_cash']
    account['summary']['terminal_inventory_and_rights_closed'] = not account['summary']['terminal_unsettled']
    account['summary']['terminal_cash_netPnL_is_fully_settled'] = (
        not account['summary']['terminal_unsettled'] and Decimal(terminal_state['locked_sale_cash']) == 0)
    return fixture, account


class MonthlyBreadthVerificationTests(unittest.TestCase):
    def test_hand_cash_distribution_fifo_and_cooldown(self):
        before = getcontext().copy()
        for kwargs, expected in (({'cash_only':True}, '0'), ({}, '-20'), ({'risk':True}, '-2020')):
            with self.subTest(kwargs=kwargs):
                fixture, account = monthly_hand_case(**kwargs)
                result = V.verify_account(fixture, account)
                self.assertEqual(Decimal(result['summary']['book_netPnL']), Decimal(expected))
        self.assertEqual(getcontext().flags, before.flags)
        self.assertEqual(getcontext().prec, before.prec)

    def test_changed_fee_cash_action_and_terminal_rejected(self):
        fixture, original = monthly_hand_case()
        for change in (lambda a:a['fills'][0].update(fee='6'),
                       lambda a:a['days'][2].update(NAV='9991'),
                       lambda a:a['action_records'][1].update(amount='11'),
                       lambda a:a['summary'].update(terminal_cash='9999'),
                       lambda a:a.update(commission_bps=5)):
            account = copy.deepcopy(original); change(account)
            with self.assertRaises(ValueError):
                V.verify_account(fixture, account)

    def test_confirmed_one_bp_and_minimum(self):
        with localcontext(V.CONTEXT):
            self.assertEqual(V._fee(Decimal('55000'), 5), Decimal('5.50'))
            self.assertEqual(V._fee(Decimal('100'), 5), Decimal('5.00'))
            self.assertEqual(V._fee(Decimal('100'), 0), Decimal('.01'))

    def test_hand_total_return_dividend_zero_and_discordant_weights(self):
        start, stop = date(2000,1,1), date(2001,2,5)
        dates = [(start+timedelta(days=i)).isoformat() for i in range((stop-start).days+1)]
        ends = [date(2000,m,calendar.monthrange(2000,m)[1]).isoformat() for m in range(1,13)]+['2001-01-31']
        assets = ['E','G']; final = dates.index(ends[-1]); ex = dates.index('2000-08-02')
        fixture = dict(assets=assets,dates=dates,terminal_index=len(dates)-1,month_end_sessions=ends,
            monthly_decision_indices=[final], event_indices=[final+1],
            bars={a:[dict(close='10') for _ in dates] for a in assets},
            actions=[dict(event_id='div',asset='E',known_index=0,record_index=ex-1,ex_index=ex,
                          pay_index=ex+1,share_multiplier='1',cash_per_share='1')])
        for i in range(ex,len(dates)):
            fixture['bars']['E'][i]['close']='9'
        fixture['bars']['G'][final]['close']='11'
        expected=[dict(index=final,date=ends[-1],month_count=13,prior_month_date=ends[0],
            TR={'E':'100','G':'110'},TR_prior12={'E':'100','G':'100'},signs=[0,1],exposure='.5',
            weights=dict(breadth={'E':'.25','G':'.25'},monthly_50_50={'E':'.5','G':'.5'},
                         own_trend={'E':'0','G':'.5'}),terminal_overrides=False)]
        V.verify_signal_frame(fixture,expected)
        fixture['bars']['G'][final+1]['close']='999'
        V.verify_signal_frame(fixture,expected)
        broken=copy.deepcopy(expected);broken[0]['signs']=[1,1]
        with self.assertRaises(ValueError):
            V.verify_signal_frame(fixture,broken)

    def test_nine_year_shared_zero_statistics_and_corruption(self):
        import numpy as np
        years = [str(y) for y in range(2015, 2024)]
        annual = {f'min{m}_slip{s}':{p:dict.fromkeys(years, '0') for p in V.POLICIES} for m,s in V.COSTS}
        keys = [f'min{m}_slip{s}/{e}' for m,s in V.COSTS for e in V.ENDPOINTS]
        digest = hashlib.sha256(bytes(5000*27*8)).hexdigest()
        stats = dict(status='computed_artificial_fixed_trace_sensitivity',
            source_nature='test_artificial_values_true_calendar', qualified=False, N=9, years=years,
            replications=5000, seed=20261107, block=2, starts_per_replication=5, truncate_rows_to=9,
            shared_indices_for_all27=True, units='CNY_per_artificial_year', statistic='arithmetic_mean_annual_PnL',
            endpoint_keys=keys, lower=dict.fromkeys(keys,0.0), observed_means=dict.fromkeys(keys,0.0),
            replicate_means_sha256=digest, quantile=.05/27, quantile_method='linear',
            numpy_version=np.__version__, historical_returns_computed=False)
        self.assertEqual(V.verify_statistics(annual, stats, stats['source_nature'], False), digest)
        bad = copy.deepcopy(stats); bad['lower'][keys[0]] = .01
        with self.assertRaises(ValueError):
            V.verify_statistics(annual, bad, stats['source_nature'], False)
