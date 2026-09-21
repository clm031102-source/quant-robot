import copy
import json
import io
import unittest
from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd

from quant_robot.research.dividend_style_diagnostic import annual_intervals, endpoint, parse_opens, summarize


class DividendStyleDiagnosticTests(unittest.TestCase):
    def test_cap_lots_costs_and_record_date_entitlement(self):
        actions=[dict(asset_id='CN_ETF_XSHG_510880',kind='cash_dividend',cash_amount_basis='gross',
            record_date=d,ex_date=(date.fromisoformat(d)+timedelta(days=1)).isoformat(),cash_per_share='.1')
            for d in ['2019-12-31','2020-01-02','2021-01-04']]
        r=endpoint('2020-01-02','2021-01-04','3','3',actions,5,10)
        self.assertEqual(r['shares'],300)
        self.assertEqual(r['buy_debit_CNY'],905.9)
        self.assertEqual(r['cash_entitlement_CNY'],30)
        self.assertEqual(r['net_PnL_CNY'],18.2)
        self.assertEqual(r['total_commission_CNY'],10)
        self.assertEqual(r['one_share_gross_return'],.1/3)

    def test_unaffordable_lot_has_no_fee_or_pnl(self):
        r=endpoint('2020-01-02','2021-01-04',10,11,[],5,0)
        self.assertEqual((r['shares'],r['net_PnL_CNY'],r['total_commission_CNY']),(0,0,0))

    def test_wrong_asset_or_duplicate_action_rejected(self):
        a=dict(asset_id='CN_ETF_XSHG_510300',kind='cash_dividend',cash_amount_basis='gross',
            record_date='2020-01-03',ex_date='2020-01-06',cash_per_share='.1')
        with self.assertRaises(ValueError):endpoint('2020-01-02','2021-01-04',3,3,[a],5,10)
        a['asset_id']='CN_ETF_XSHG_510880'
        with self.assertRaises(ValueError):endpoint('2020-01-02','2021-01-04',3,3,[a,a],5,10)

    def test_exact_price_dates_and_identity_no_holdout_extension(self):
        raw={'code':'510880','kline':[[20080102,3],[20080103,3.1],[20240102,4]]}
        sessions=['2008-01-02','2008-01-03','2024-01-02']
        self.assertEqual(parse_opens(json.dumps(raw),sessions,[sessions[0],sessions[-1]]),{sessions[0]:3,sessions[-1]:4})
        for mutated in [dict(raw,code='510300'),dict(raw,kline=raw['kline']+[[20260102,9]]),
                        dict(raw,kline=raw['kline'][1:]),dict(raw,kline=[[20080102,3,9]]+raw['kline'][1:])]:
            with self.subTest(mutated=mutated),self.assertRaises(ValueError):
                parse_opens(json.dumps(mutated),sessions,[sessions[0],sessions[-1]])

    def test_fixed_calendar_first_sessions_and_duration(self):
        sessions=[]
        for y in range(2008,2025):
            sessions.extend((date(y,1,2)+timedelta(days=i)).isoformat() for i in range(240))
        rows=annual_intervals(sessions)
        self.assertEqual(len(rows),16)
        self.assertEqual(rows[0],dict(year=2008,entry_date='2008-01-02',exit_date='2009-01-02',sessions=240))
        with self.assertRaises(ValueError):annual_intervals([d for d in sessions if not d.startswith('2012')])

    def test_screen_keeps_zero_opportunities_and_later_losses(self):
        rows=[dict(year=y,entry_date=f'{y}-01-02',shares=100,net_PnL_CNY=10) for y in range(2008,2024)]
        good=summarize(rows)
        self.assertTrue(good['endpoint_cost_screen_passed'])
        self.assertEqual(good['annual_block']['mean_PnL_CNY_2_5_97_5'],[10,10])
        self.assertFalse(good['net_positive_EV_verified'])
        rows[-1].update(shares=0,net_PnL_CNY=0)
        bad=summarize(rows)
        self.assertEqual(bad['full']['positive_frequency'],15/16)
        self.assertFalse(bad['checks']['later_executed_count'])
        rows[-1].update(shares=100,net_PnL_CNY=-100)
        self.assertFalse(summarize(rows)['checks']['later_mean_positive'])
        with self.assertRaises(ValueError):summarize(rows[:-1])

    def test_bad_prices_and_dates_rejected(self):
        for a,b in [(0,3),(3,float('nan')),(float('inf'),2),(-2,3)]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError):
                endpoint('2020-01-02','2021-01-04',a,b,[],5,10)
        with self.assertRaises(ValueError):endpoint('2021-01-04','2020-01-02',3,3,[],5,10)

    def test_synthetic_full_join_and_raw_crosscheck_before_returns(self):
        from quant_robot.research import dividend_style_diagnostic as diagnostic
        days=[(date(y,1,2)+timedelta(days=i)).isoformat() for y in range(2008,2025) for i in range(240)]
        rows=annual_intervals(days)
        actions=[dict(asset_id='CN_ETF_XSHG_510880',kind='cash_dividend',cash_amount_basis='gross',
            record_date=f'{y}-01-03',ex_date=f'{y}-01-04',cash_per_share='.1') for y in range(2008,2024)]
        ledger=dict(status='conditional_current_official_source_reconciliation_complete',returns_calculated=False,
            annual_reports=[{'residual':0}]*16,intervals=rows,events=actions)
        snapshots={'source_ledger':json.dumps(ledger).encode(),'dividend_prices':json.dumps(dict(code='510880',
            kline=[[int(d.replace('-','')),3] for d in days if d<='2024-01-02'])).encode()}
        for y in range(2020,2025):
            stream=io.BytesIO();pd.DataFrame([dict(symbol='510880.SH',date=f'{y}-01-02',open=3),
                dict(symbol='510300.SH',date=f'{y}-01-02',open=999)]).to_parquet(stream,index=False)
            snapshots[f'raw_crosscheck_{y}']=stream.getvalue()
        benchmark={f'{y}-01-02':3 for y in range(2013,2025)}
        with patch.object(diagnostic,'study_sessions',return_value=days),patch.object(diagnostic,'price_anchors',return_value=benchmark),patch.object(diagnostic,'reviewed_actions',return_value=[]):
            result=diagnostic.calculate(snapshots)
            self.assertEqual(len(result['scenarios']),9)
            self.assertEqual(len(result['observations']),16)
            self.assertEqual(len(result['descriptive_comparisons']['broad_equity_observations']),11)
            self.assertEqual(result['diagnostic']['full']['total_net_PnL_CNY'],291.2)
            mutated=json.loads(snapshots['dividend_prices']);mutated['kline'][-1][1]=4
            snapshots['dividend_prices']=json.dumps(mutated).encode()
            with patch.object(diagnostic,'endpoint') as compute,self.assertRaisesRegex(ValueError,'anchor differ'):
                diagnostic.calculate(snapshots)
            compute.assert_not_called()
