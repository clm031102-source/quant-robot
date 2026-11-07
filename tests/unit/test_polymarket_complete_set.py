from copy import deepcopy
from decimal import Decimal as D
import unittest

from quant_robot.research.polymarket_complete_set import asks, buy_cost, screen


class CompleteSetTests(unittest.TestCase):
    def setUp(self):
        self.market = dict(id='1', question='Test binary question', slug='test', active=True,
            closed=False, acceptingOrders=True, enableOrderBook=True, negRisk=False,
            outcomes='["Yes", "No"]', clobTokenIds='["10", "20"]', conditionId='condition',
            feesEnabled=False)
        self.books = {asset:dict(asset_id=asset, market='condition', neg_risk=False,
            timestamp='1000000', min_order_size='5',
            asks=[dict(price='0.9', size='100'),dict(price='0.45',size='200')]) for asset in ('10','20')}

    def test_walks_unsorted_asks_and_cannot_fill_beyond_depth(self):
        levels = asks(dict(asks=[dict(price='0.8',size='20'),dict(price='0.4',size='10')]))
        result = buy_cost(levels, D('20'), D('0'))
        self.assertTrue(result['complete'])
        self.assertEqual(D(result['cash_cost']),D('12'))
        self.assertFalse(buy_cost(levels,D('31'),D('0'))['complete'])

    def test_fee_withheld_requires_extra_gross_shares(self):
        cash = buy_cost([(D('0.5'),D('200'))],D('100'),D('0.04'))
        shares = buy_cost([(D('0.5'),D('200'))],D('100'),D('0.04'),fee_in_shares=True)
        self.assertEqual(D(cash['cash_cost']),D('51'))
        self.assertTrue(shares['complete'])
        self.assertGreater(D(shares['gross_shares']),D('102'))
        self.assertGreater(D(shares['cash_cost']),D(cash['cash_cost']))

    def test_cost_reserve_and_minimum_are_not_silently_omitted(self):
        result = screen(self.market,self.books,observed_ms=1000100)
        small, _, large = result['observations']
        self.assertFalse(small['minimum_met'])
        self.assertEqual(D(large['conservative_cost']),D('90'))
        self.assertEqual(D(large['quote_surplus']),D('8.82'))
        self.assertTrue(large['positive_quote_candidate'])
        self.assertEqual(result['fills'],0)
        self.assertIsNone(result['realized_profit'])

    def test_stale_or_skewed_books_cannot_be_positive_candidates(self):
        for stamp in ('985000','1003000'):
            with self.subTest(stamp=stamp):
                books=deepcopy(self.books);books['10']['timestamp']=stamp
                result=screen(self.market,books,observed_ms=1003100)
                self.assertFalse(any(q['positive_quote_candidate'] for q in result['observations']))

    def test_missing_fees_mismatched_books_and_negative_risk_are_unavailable(self):
        cases = [(dict(self.market,feesEnabled=None),self.books),
                 (dict(self.market,negRisk=True),self.books),
                 (self.market,dict(self.books,**{'10':dict(self.books['10'],market='other')}))]
        for market,books in cases:
            with self.subTest(market=market):
                self.assertEqual(screen(market,books,observed_ms=1000100)['status'],'unavailable')

    def test_fees_can_erase_apparent_pair_discount(self):
        market=dict(self.market,feesEnabled=True,
                    feeSchedule=dict(rate='0.07',exponent=1,takerOnly=True))
        books=deepcopy(self.books)
        for book in books.values():book['asks']=[dict(price='0.49',size='200')]
        result=screen(market,books,observed_ms=1000100)
        self.assertLess(D(result['best_ask_sum']),D('1'))
        self.assertLess(D(result['observations'][-1]['quote_surplus']),D('0'))
        self.assertFalse(result['observations'][-1]['positive_quote_candidate'])


if __name__=='__main__': unittest.main()
