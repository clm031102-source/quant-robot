import math
import json
from datetime import date, timedelta
import unittest

from quant_robot.research.currency_gold_diagnostic import ASSET, calculate, describe, open_return, summarize


def rows():
    return [dict(entry_date=f'{2014+i//4}-{1+3*(i%4):02d}-02', state=i%2,
                 episode_id=i//2 if i%2 else None, sessions=60+i%3,
                 return_value=.10 if i%2 else -.02) for i in range(40)]


class CurrencyGoldGrossTests(unittest.TestCase):
    def test_full_join_retained_schema_zero_gold_actions(self):
        days=[str(date(2014,1,2)+timedelta(days=i)) for i in range((date(2024,1,2)-date(2014,1,2)).days+1)]
        anchors=[min(d for d in days if d.startswith(f'{y}-{m:02d}-')) for y in range(2014,2024) for m in (1,4,7,10)]+[days[-1]]
        kept=set(anchors)
        kept.update(d for d in days if d not in kept and len(kept)<2435)
        sessions=[str(date(2013,12,5)+timedelta(days=i)) for i in range(19)]+sorted(kept)
        sample=rows()
        for i,r in enumerate(sample):
            r.update(entry_date=anchors[i],exit_date=anchors[i+1],sessions=sessions.index(anchors[i+1])-sessions.index(anchors[i]))
        # Match the retained account-action schema, which contains equity events
        # only and labels announced cash separately from investor clearing.
        raw=dict(cadence_result=dict(intervals=sample,screen={'passed':True},returns_computed=False),
            market_sessions=sessions,market_bars=[dict(asset_id=a,date=d,open='10') for a in [ASSET,'other'] for d in sessions],
            market_actions=dict(cash_amount_basis='announced_not_investor_verified',events=[dict(asset_id='other')]),
            market_gold_annual_audit=dict(rows=[dict(year=y,code='518880',cash_distribution='0',split_zero=True,unit_identity_passed=True) for y in range(2014,2024)]),
            market_gold_terminal_review=dict(covers_terminal_session='2024-01-02',no_distributions_or_unit_splits_reported=True))
        snapshots={k:json.dumps(v).encode() for k,v in raw.items()}
        result=calculate(snapshots)
        self.assertEqual(result['ETF_open_values_used'],41)
        self.assertEqual(result['diagnostic']['full']['session_transitions'],2434)
        self.assertEqual(result['diagnostic']['full']['selected_mean_gross'],0)
        raw['market_actions']['events'].append(dict(asset_id=ASSET))
        snapshots['market_actions']=json.dumps(raw['market_actions']).encode()
        with self.assertRaisesRegex(ValueError,'zero cash/split'):calculate(snapshots)

    def test_record_day_boundary_and_other_asset_exclusion(self):
        def event(day, asset=ASSET):
            return dict(asset_id=asset, kind='cash_dividend', cash_per_share='1', record_date=day, ex_date=day[:-2]+'20')
        events=[event('2020-01-02'),event('2020-04-02'),event('2020-01-02','other')]
        self.assertAlmostEqual(open_return('2020-01-02','2020-04-02','10','11',events),.2)

    def test_negative_and_nonfinite_open_rejected(self):
        for value in ['0','-1','NaN','Infinity']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                open_return('2020-01-02','2020-04-02',value,'10',[])

    def test_log_effect_uses_session_matched_exposure(self):
        sample=[dict(state=1,return_value=.1,sessions=1,episode_id=1),dict(state=0,return_value=.2,sessions=3,episode_id=None)]
        result=describe(sample)
        self.assertEqual(result['selected_session_fraction'],.25)
        self.assertAlmostEqual(result['D_daily_log'],(.75*math.log1p(.1)-.25*math.log1p(.2))/4)

    def test_unknown_is_cash_but_stays_in_denominator(self):
        sample=[dict(state=1,return_value=.1,sessions=1,episode_id=1),dict(state=None,return_value=.2,sessions=1,episode_id=None)]
        result=describe(sample)
        self.assertEqual(result['intervals'],2)
        self.assertEqual(result['selected_intervals'],1)
        self.assertAlmostEqual(result['D_daily_log'],(math.log1p(.1)-math.log1p(.2))/4)

    def test_positive_signal_passes_and_accounts_remain_unverified(self):
        result=summarize(rows())
        self.assertTrue(result['gross_screen_passed'])
        self.assertEqual(result['full']['selected_positive_fraction'],1)
        self.assertFalse(result['net_positive_EV_verified'])
        self.assertFalse(result['fresh_OOS'])

    def test_positive_gold_drift_alone_cannot_pass(self):
        sample=rows()
        for r in sample:r['sessions']=60;r['return_value']=.02
        result=summarize(sample)
        self.assertTrue(result['checks']['full_mean_positive'])
        self.assertFalse(result['gross_screen_passed'])
        self.assertAlmostEqual(result['full']['D_daily_log'],0)

    def test_later_negative_mean_rejects_full_positive(self):
        sample=rows()
        for r in sample[24:]:r['return_value']=-.01
        result=summarize(sample)
        self.assertTrue(result['checks']['full_mean_positive'])
        self.assertFalse(result['checks']['later_mean_positive'])
        self.assertFalse(result['gross_screen_passed'])

    def test_exact_window_and_valid_returns(self):
        with self.assertRaises(ValueError):summarize(rows()[:-1])
        for value in [-1,float('inf'),float('nan')]:
            sample=rows();sample[0]['return_value']=value
            with self.subTest(value=value),self.assertRaises(ValueError):summarize(sample)

    def test_zero_mean_does_not_pass(self):
        sample=rows()
        for r in sample:r['return_value']=0
        result=summarize(sample)
        self.assertFalse(any(result['checks'].values()))
