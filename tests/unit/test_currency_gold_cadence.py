"""Synthetic currency state, timing and episode tests; no real outcomes."""
from datetime import date, timedelta
from decimal import Decimal
import unittest

from quant_robot.research.currency_gold_cadence import quarter_ends, quarterly_intervals
from quant_robot.research.enterprise_liquidity_cadence import later_intervals, screen_counts


def endpoints():
    result=[]
    for i,day in enumerate(quarter_ends()):
        end=date.fromisoformat(day)
        result.append(dict(quarter_end=day,release_date=str(end-timedelta(days=4)),
            observation_date=str(end-timedelta(days=7)),age_calendar_days=7,status='conditional',
            cny_per_usd=str(Decimal('6')+Decimal(i)/100)))
    return result


def sessions():
    a,b=date(2014,1,1),date(2024,1,5)
    days=[a+timedelta(days=i) for i in range((b-a).days+1)]
    return [str(d) for d in days if d.weekday()<5 and d.strftime('%m-%d')!='01-01']


class CurrencyGoldCadenceTests(unittest.TestCase):
    def test_strict_direction_equality_and_exact_decimal_comparison(self):
        source=endpoints()
        source[1]['cny_per_usd']=source[0]['cny_per_usd']
        self.assertEqual(quarterly_intervals(source,sessions())[0]['state'],0)
        source[1]['cny_per_usd']=str(Decimal(source[0]['cny_per_usd'])+Decimal('0.0000000001'))
        self.assertEqual(quarterly_intervals(source,sessions())[0]['state'],1)
        source[1]['cny_per_usd']='5.99'
        self.assertEqual(quarterly_intervals(source,sessions())[0]['state'],0)

    def test_unknown_endpoint_affects_exactly_two_adjacent_decisions(self):
        source=endpoints()
        source[24]['status']='unknown'
        rows=quarterly_intervals(source,sessions())
        self.assertEqual([i for i,r in enumerate(rows) if r['state'] is None],[23,24])
        self.assertEqual(len(rows),40)

    def test_unknown_warmup_and_terminal_each_affect_one_decision(self):
        source=endpoints()
        source[0]['status']=source[-1]['status']='unknown'
        rows=quarterly_intervals(source,sessions())
        self.assertEqual([i for i,r in enumerate(rows) if r['state'] is None],[0,39])

    def test_full_quarter_partition_and_publication_bound(self):
        days=sessions()
        rows=quarterly_intervals(endpoints(),days)
        self.assertEqual((rows[0]['entry_date'],rows[-1]['exit_date']),('2014-01-02','2024-01-02'))
        self.assertEqual(len(rows),40)
        self.assertEqual(sum(r['sessions'] for r in rows),days.index('2024-01-02'))
        self.assertTrue(all(a['exit_date']==b['entry_date'] for a,b in zip(rows,rows[1:])))
        self.assertEqual(rows[0]['publication_upper_bound_UTC'],'2013-12-28T05:00:00+00:00')

    def test_selected_run_is_one_episode_and_later_carry_in(self):
        days=sessions()
        rows=quarterly_intervals(endpoints(),days)
        later=later_intervals(rows,days)
        screen=screen_counts(rows,later)
        self.assertEqual(len(later),16)
        self.assertEqual(screen['full']['selected_episodes'],1)
        self.assertEqual(screen['later']['carry_in_episodes'],1)
        self.assertEqual(screen['later']['new_selected_episodes'],0)
        self.assertFalse(screen['passed'])

    def test_new_state_at_later_boundary_is_new_entry(self):
        source=endpoints()
        source[24]['cny_per_usd']='1'
        days=sessions()
        rows=quarterly_intervals(source,days)
        screen=screen_counts(rows,later_intervals(rows,days))
        self.assertEqual(rows[23]['state'],0)
        self.assertEqual(rows[24]['state'],1)
        self.assertEqual(screen['later']['new_selected_episodes'],1)
        self.assertEqual(screen['later']['carry_in_episodes'],0)

    def test_same_day_release_stale_quote_and_wrong_age_are_rejected(self):
        for field,value in [('release_date','2013-12-31'),('observation_date','2013-12-01'),
                            ('age_calendar_days',8),('observation_date','2013-12-30')]:
            source=endpoints();source[1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                quarterly_intervals(source,sessions())

    def test_nonfinite_nonpositive_and_malformed_known_quotes_rejected(self):
        for value in ('NaN','Infinity','0','-1','bad',None):
            source=endpoints();source[1]['cny_per_usd']=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                quarterly_intervals(source,sessions())

    def test_missing_duplicate_or_shuffled_endpoint_rejected(self):
        source=endpoints()
        for rows in (source[1:],source+[source[-1]],source[::-1]):
            with self.assertRaises(ValueError):
                quarterly_intervals(rows,sessions())

    def test_calendar_missing_quarter_or_bad_order_rejected(self):
        days=sessions()
        for calendar in (days[::-1],days+[days[-1]],[d for d in days if not d.startswith('2020-04')]):
            with self.assertRaises(ValueError):
                quarterly_intervals(endpoints(),calendar)
