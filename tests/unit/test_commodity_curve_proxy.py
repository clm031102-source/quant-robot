"""Synthetic, non-market examples for the one-curve mechanism."""
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
import unittest

from quant_robot.research.commodity_curve_proxy import build_proxy_signals, select_contract_pairs


def contract(code, *, listed='20190101', expiry='20200302', delivery='20200305'):
    return dict(ts_code=code, fut_code='M', exchange='DCE', list_date=listed,
        delist_date=expiry, last_ddate=delivery, per_unit=10, trade_unit='吨', quote_unit='人民币元/吨')


class CommodityCurveProxyTests(unittest.TestCase):
    def setUp(self):
        self.records = [contract('M2003.DCE'),
            contract('M2005.DCE', expiry='20200511', delivery='20200514'),
            contract('M2007.DCE', expiry='20200713', delivery='20200716')]
        self.days = ['2020-01-02','2020-01-03','2020-01-06','2020-01-07','2020-01-08']
        self.prices = [dict(ts_code=code, trade_date=day.replace('-',''), settle=price)
            for day in self.days for code,price in [('M2003.DCE','3300'),('M2005.DCE','3000'),('M2007.DCE','2900')]]

    def test_exact_sixty_day_boundary_and_no_future_listing(self):
        pairs = select_contract_pairs(self.records,self.days)
        self.assertEqual((date(2020,3,2)-date(2020,1,2)).days,60)
        self.assertEqual(pairs[0]['near_contract'],'M2003.DCE')
        self.assertEqual(pairs[1]['near_contract'],'M2005.DCE')
        records = deepcopy(self.records)
        records[2]['list_date']='20200107'
        selected = select_contract_pairs(records,self.days)
        self.assertIsNone(selected[1]['near_contract'])
        self.assertEqual(selected[3]['near_contract'],'M2005.DCE')

    def test_full_session_lag_crosses_weekend_and_matches_fixed_formula(self):
        result = build_proxy_signals(self.records,self.prices,self.days)
        self.assertFalse(result['signals'][0]['known'])
        self.assertFalse(result['signals'][1]['known'])
        signal = result['signals'][2]
        self.assertEqual((signal['source_date'],signal['execution_date']),('2020-01-02','2020-01-06'))
        self.assertTrue(signal['desired'])
        distance = (date(2020,5,11)-date(2020,3,2)).days
        with localcontext() as context:
            context.prec=34
            expected=(Decimal('3300')/Decimal('3000')).ln()*365/distance
        self.assertEqual(Decimal(signal['annualized_log_curve']),expected)
        self.assertFalse(result['qualified'])
        self.assertEqual(result['real_forward_days_added'],0)

    def test_selected_missing_leg_exits_without_substituting_other_contract(self):
        rows = [row for row in self.prices if not(row['ts_code']=='M2003.DCE' and row['trade_date']=='20200102')]
        signal = build_proxy_signals(self.records,rows,self.days)['signals'][2]
        self.assertEqual(signal['near_contract'],'M2003.DCE')
        self.assertFalse(signal['known'])
        self.assertFalse(signal['desired'])
        self.assertIn('missing',signal['reason'])

    def test_future_prices_do_not_change_prefix_or_previous_pair_selection(self):
        original = build_proxy_signals(self.records,self.prices,self.days)
        changed = deepcopy(self.prices)
        for row in changed:
            if row['trade_date'] >= '20200106':row['settle']='999999'
        altered = build_proxy_signals(self.records,changed,self.days)
        self.assertEqual(original['signals'][:4],altered['signals'][:4])
        self.assertEqual(select_contract_pairs(list(reversed(self.records)),self.days),
                         select_contract_pairs(self.records,self.days))

    def test_nonpositive_or_missing_settlement_never_uses_close(self):
        for value in (None,0,-1,'NaN','Infinity',True,'1e99999'):
            rows=deepcopy(self.prices)
            rows[0].update(settle=value,close='4000')
            with self.subTest(value=value):
                signal=build_proxy_signals(self.records,rows,self.days)['signals'][2]
                self.assertFalse(signal['known'])
                self.assertFalse(signal['desired'])

    def test_zero_and_negative_curve_mean_cash_not_unknown(self):
        for near in ('3000','2700'):
            rows=deepcopy(self.prices);rows[0]['settle']=near
            signal=build_proxy_signals(self.records,rows,self.days)['signals'][2]
            self.assertTrue(signal['known'])
            self.assertFalse(signal['desired'])
            self.assertLessEqual(Decimal(signal['annualized_log_curve']),0)

    def test_duplicate_price_unknown_contract_and_ambiguous_lifecycle_rejected(self):
        for extra in (self.prices[0],dict(self.prices[0],ts_code='M2999.DCE')):
            with self.assertRaises(ValueError):
                build_proxy_signals(self.records,self.prices+[extra],self.days)
        bad=deepcopy(self.records);bad[1]['delist_date']=bad[0]['delist_date']
        with self.assertRaisesRegex(ValueError,'identical last-trade'):
            select_contract_pairs(bad,self.days)
        bad=deepcopy(self.records);bad[0]['last_ddate']='20200228'
        with self.assertRaisesRegex(ValueError,'chronology'):
            select_contract_pairs(bad,self.days)

    def test_unit_or_calendar_changes_do_not_silently_enter_model(self):
        bad=deepcopy(self.records);bad[0]['per_unit']=100
        with self.assertRaisesRegex(ValueError,'units changed'):
            select_contract_pairs(bad,self.days)
        for days in (self.days[::-1],self.days+[self.days[-1]],['2020-1-2']):
            with self.assertRaises(ValueError):
                select_contract_pairs(self.records,days)
