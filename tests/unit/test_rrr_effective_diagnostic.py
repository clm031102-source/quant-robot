from datetime import date, timedelta
import math
import unittest
import io
import json
from unittest.mock import patch
import pandas as pd

from quant_robot.research.rrr_effective_diagnostic import event_intervals, endpoint, summarize, cluster_interval


class RRREffectiveDiagnosticTests(unittest.TestCase):
    def test_later_publication_and_effective_date_both_precede_entry(self):
        days = [(date(2020, 1, 1)+timedelta(days=i)).isoformat() for i in range(80)]
        events = [dict(event_id='a', conservative_available_date=days[4], first_effective_date=days[2]),
                  dict(event_id='b', conservative_available_date=days[3], first_effective_date=days[24]),
                  dict(event_id='c', conservative_available_date=days[1], first_effective_date=days[25]),
                  dict(event_id='d', conservative_available_date=days[1], first_effective_date=days[65])]
        rows, skipped = event_intervals(events, days)
        self.assertEqual([(r['entry_date'], r['exit_date']) for r in rows], [(days[5], days[25]), (days[26], days[46])])
        self.assertEqual([r['reason'] for r in skipped], ['overlap_or_exit_session', 'incomplete_terminal_interval'])

    def test_commission_lots_cap_and_adverse_tick_rounding(self):
        row = endpoint('2020-01-01', '2020-02-01', '3.333', '3.500', [], 5, 10)
        self.assertEqual(row['shares'], 200)  # 300 shares exceed the all-in cap.
        self.assertEqual(row['modeled_buy_price'], 3.337)
        self.assertEqual(row['modeled_sell_price'], 3.496)
        self.assertEqual(row['buy_debit_CNY'], 672.4)
        self.assertEqual(row['net_PnL_CNY'], 21.8)
        self.assertEqual(row['total_commission_CNY'], 10)
        zero = endpoint('2020-01-01', '2020-02-01', 10, 11, [], 5, 10)
        self.assertEqual((zero['shares'], zero['net_PnL_CNY']), (0, 0))
        self.assertEqual(zero['total_commission_CNY'], 0)

    def test_commission_round_half_up_and_positive_gross_can_lose(self):
        r = endpoint('2020-01-01', '2020-02-01', '3.35', '3.36', [], 0, 0)
        self.assertEqual(r['total_commission_CNY'], .68)
        r = endpoint('2020-01-01', '2020-02-01', '3.35', '3.36', [], 5, 0)
        self.assertGreater(r['one_share_gross_return'], 0)
        self.assertEqual(r['net_PnL_CNY'], -8)

    def test_record_date_entry_included_exit_excluded(self):
        actions = [dict(asset_id='CN_ETF_XSHG_510300', kind='cash_dividend', cash_amount_basis='gross',
                        record_date=d, ex_date=(date.fromisoformat(d)+timedelta(days=1)).isoformat(), cash_per_share=.1) for d in ['2019-12-31', '2020-01-01', '2020-02-01']]
        r = endpoint('2020-01-01', '2020-02-01', 3, 3, actions, 5, 0)
        self.assertEqual(r['cash_entitlement_CNY'], 30)
        self.assertEqual(r['net_PnL_CNY'], 20)

    def test_invalid_prices_and_nonforward_dates_rejected(self):
        for a, b in [(0, 2), (2, -1), (math.nan, 1), (1, math.inf)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                endpoint('2020-01-01', '2020-02-01', a, b, [], 5, 10)
        with self.assertRaises(ValueError): endpoint('2020-01-01', '2020-01-01', 3, 3, [], 5, 10)

    def test_cluster_bootstrap_keeps_empty_years_and_zero_draws(self):
        rows = [dict(entry_date='2015-01-01', net_PnL_CNY=100, shares=100)]
        result = cluster_interval(rows)
        self.assertGreater(result['zero_count_draws'], 1000)
        self.assertEqual(result['mean_PnL_CNY_2_5_97_5'], [0, 100])
        self.assertEqual(result, cluster_interval(rows))

    def test_full_summary_keeps_unfilled_zero_events_and_later_gate(self):
        rows = [dict(entry_date=f'{y}-01-01', shares=100, net_PnL_CNY=10) for y in range(2013, 2025)]
        rows += [dict(entry_date='2024-02-01', shares=0, net_PnL_CNY=0)]
        r = summarize(rows)
        self.assertEqual(r['full']['opportunities'], 13)
        self.assertEqual(r['full']['executed'], 12)
        self.assertEqual(r['full']['positive_frequency'], 12/13)
        self.assertEqual(r['later_2020_onward']['opportunities'], 6)
        self.assertTrue(r['endpoint_cost_screen_passed'])
        self.assertFalse(r['net_positive_EV_verified'])
        rows[-2]['net_PnL_CNY'] = -100
        self.assertFalse(summarize(rows)['checks']['later_mean_positive'])

    def test_synthetic_join_cost_grid_and_holdout_filter(self):
        from quant_robot.research import rrr_effective_diagnostic as diagnostic
        sessions=pd.bdate_range('2013-01-01','2024-06-28').date.tolist()
        days=[str(d) for d in sessions]
        effective=[f'{y}-01-01' for y in range(2013,2020)]+[
            '2020-01-01','2020-09-01','2021-01-01','2021-09-01','2022-01-01','2022-09-01','2023-09-01','2024-02-01']
        events=[dict(event_id=str(i),conservative_available_date=d,first_effective_date=d) for i,d in enumerate(effective)]
        intervals,_=diagnostic.event_intervals(events,days)
        for event,row in zip(events,intervals,strict=True):event.update(row)
        snapshots={'event_ledger':json.dumps(dict(included=events)).encode(),
            'annual_reconciliation':json.dumps(dict(status='reconciled_to_retained_official_annual_accounts',unresolved_count_discrepancies=[],total_general_announcements=15)).encode(),
            'early_price':json.dumps(dict(code='510300',kline=[[int(d.strftime('%Y%m%d')),2,2,2,2] for d in sessions if d.year<2020])).encode()}
        for y in range(2020,2025):
            rows=[dict(date=d,asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=2.) for d in sessions if d.year==y]
            rows.append(dict(date=date(2026,1,5),asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=9999.))
            stream=io.BytesIO();pd.DataFrame(rows).to_parquet(stream,index=False);snapshots[f'bars_{y}']=stream.getvalue()
        actions=[]
        for y in range(2014,2025):
            record=next(d for d in sessions if d>=date(y,1,15));ex=sessions[sessions.index(record)+1]
            actions.append(dict(asset_id='CN_ETF_XSHG_510300',kind='cash_dividend',cash_amount_basis='gross',record_date=str(record),ex_date=str(ex),cash_per_share=.1))
        snapshots['actions']=json.dumps({'events':actions[7:]}).encode()
        snapshots['early_actions']=json.dumps({'events':[{**r,'cash_per_unit':str(r['cash_per_share'])} for r in actions[:7]]}).encode()
        with patch.object(diagnostic,'cn_sessions',return_value=days),patch('pandas.read_parquet',wraps=pd.read_parquet) as reads:
            result=diagnostic.calculate(snapshots)
        self.assertEqual(len(result['scenarios']),9)
        self.assertEqual(len(result['observations']),15)
        self.assertEqual(result['diagnostic']['later_2020_onward']['opportunities'],8)
        self.assertEqual(result['descriptive_comparisons']['buy_and_hold']['cash_entitlement_CNY'],440)
        self.assertTrue(all(r['raw_entry_open']==2 and r['raw_exit_open']==2 for r in result['observations']))
        self.assertTrue(all(d<=date(2024,6,28) for call in reads.call_args_list for d in call.kwargs['filters'][0][2]))
        for scenario in result['scenarios']:
            self.assertTrue(all(r['buy_debit_CNY']<=1000 and r['shares']%100==0 for r in scenario['observations']))
        events[0]['exit_date']=days[40]
        snapshots['event_ledger']=json.dumps(dict(included=events)).encode()
        with patch.object(diagnostic,'cn_sessions',return_value=days),patch.object(diagnostic,'price_anchors') as prices:
            with self.assertRaisesRegex(ValueError,'calendar dates differ'):diagnostic.calculate(snapshots)
            prices.assert_not_called()
