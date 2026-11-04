import unittest
import numpy as np
import pandas as pd

from quant_robot.research.indicator_combinations import indicator_frame, state_cycles, RULES


class IndicatorCombinationsTests(unittest.TestCase):
    def rows(self, count=360):
        days = pd.bdate_range('2014-01-01', periods=count).strftime('%Y-%m-%d').tolist()
        values = 10 + np.arange(count)*.01 + np.sin(np.arange(count)/7)*.3
        return [dict(date=d,asset_id='A',open=str(p),high=str(p+1),low=str(p-1),close=str(p),volume='100000',amount='1000000') for d,p in zip(days,values)]

    def test_future_prices_do_not_change_earlier_signals(self):
        bars=self.rows(); original=indicator_frame(bars,[])
        changed=[dict(r) for r in bars]
        for r in changed[320:]:r['close']=str(float(r['close'])*4);r['amount']='1'
        revised=indicator_frame(changed,[])
        pd.testing.assert_frame_equal(original.iloc[:320],revised.iloc[:320])

    def test_dividend_does_not_create_negative_pressure(self):
        bars=self.rows(40)
        for i,r in enumerate(bars):r['close']='10' if i<25 else '9'
        actions=[dict(asset_id='A',ex_date=bars[25]['date'],cash_per_unit='1')]
        frame=indicator_frame(bars,actions)
        self.assertAlmostEqual(frame.iloc[25]['signal_price'],10)
        self.assertEqual(frame.iloc[30]['pressure'],0)

    def test_known_up_days_have_unit_pressure(self):
        bars=self.rows(40)
        for i,r in enumerate(bars):r['close']=str(10+i)
        frame=indicator_frame(bars,[])
        self.assertEqual(frame.iloc[30]['pressure'],1)
        self.assertTrue(frame.iloc[:20]['pressure'].isna().all())

    def test_fractional_distribution_neutral_day_stays_neutral(self):
        bars=self.rows(340)
        for i,r in enumerate(bars):r['close']='2.002' if i<300 else '1.977'
        actions=[dict(asset_id='A',ex_date=bars[300]['date'],cash_per_unit='0.025')]
        frame=indicator_frame(bars,actions)
        self.assertTrue((frame['pressure'].dropna()==0).all())
        self.assertFalse(frame['pressure_positive'].fillna(False).any())
        self.assertFalse(frame['macd_positive'].fillna(False).any())

    def test_cycles_use_next_session_and_never_same_day(self):
        sessions=pd.bdate_range('2020-01-01',periods=30).strftime('%Y-%m-%d').tolist()
        states=[False]*30;states[20]=True;states[21]=True
        cycles=state_cycles(sessions,states,first=sessions[21],cadence=1)
        self.assertEqual([(c['entry_date'],c['exit_date']) for c in cycles],[(sessions[21],sessions[23])])

    def test_five_session_decisions_ignore_intermediate_changes(self):
        sessions=pd.bdate_range('2020-01-01',periods=35).strftime('%Y-%m-%d').tolist()
        states=[False]*35;states[20]=True
        cycles=state_cycles(sessions,states,first=sessions[21],cadence=5)
        self.assertEqual([(c['entry_date'],c['exit_date']) for c in cycles],[(sessions[21],sessions[26])])

    def test_last_close_cannot_generate_terminal_entry(self):
        sessions=pd.bdate_range('2020-01-01',periods=30).strftime('%Y-%m-%d').tolist()
        states=[False]*30;states[-2:]=[True,True]
        self.assertEqual(state_cycles(sessions,states,first=sessions[21],cadence=1),[])

    def test_rules_are_fixed_and_incomplete_zscore_stays_unknown(self):
        frame=indicator_frame(self.rows(),[])
        self.assertEqual(RULES,('pressure_positive','macd_positive','pressure_and_macd','equal_weight_zscore'))
        self.assertTrue(frame.iloc[:285]['equal_weight_zscore'].isna().all())


if __name__=='__main__':unittest.main()
