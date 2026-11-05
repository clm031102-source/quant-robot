"""Synthetic causal and selection-boundary tests; no retained market data."""
from copy import deepcopy
from datetime import date, timedelta
import unittest
import numpy as np
import pandas as pd
from quant_robot.research.full_position_factors import (
    CATALOG, candidate_combinations, feature_frame, combined_state,
    screen_training, choose_training_candidates)


def fixture(count=180):
    rows = []
    for i in range(count):
        price = 4 + i*.002 + .1*np.sin(i/4)
        rows.append(dict(asset_id='A', date=str(date(2017,1,1)+timedelta(days=i)),
            open=price, close=price, high=price+.05, low=price-.05,
            volume=100000+i*31, amount=(100000+i*31)*price))
    return rows


class FullPositionFactorTests(unittest.TestCase):
    def test_catalogue_and_prefix_are_causal(self):
        bars=fixture(); whole=feature_frame(bars,[])
        self.assertEqual(len(CATALOG),24)
        self.assertEqual(len(candidate_combinations()),2324)
        self.assertEqual(len(set(candidate_combinations())),2324)
        pd.testing.assert_frame_equal(whole.iloc[:100],feature_frame(bars[:100],[]))
        changed=deepcopy(bars)
        for row in changed[100:]:
            for k in ('open','high','low','close','volume','amount'):row[k]*=10
        pd.testing.assert_frame_equal(whole.iloc[:100],feature_frame(changed,[]).iloc[:100])
        self.assertTrue(whole[list(CATALOG)].iloc[0].isna().all())

    def test_open_total_return_label_does_not_depend_on_ex_date_close(self):
        bars=fixture(); actions=[dict(asset_id='A',ex_date=bars[110]['date'],cash_per_unit='.1')]
        expected=feature_frame(bars,actions)['signal_open']
        bars[110]['close']+=.02
        pd.testing.assert_series_equal(expected,feature_frame(bars,actions)['signal_open'])
        self.assertAlmostEqual(expected.iloc[110]/expected.iloc[109],
            (bars[110]['open']+.1)/bars[109]['open'])

    def test_missing_or_inconsistent_ohlc_is_rejected(self):
        for key in ('open','high','low','close'):
            bars=fixture();bars[110][key]=np.nan
            with self.assertRaisesRegex(ValueError,'OHLC'):feature_frame(bars,[])
        bars=fixture();bars[110]['high']=1
        with self.assertRaisesRegex(ValueError,'OHLC'):feature_frame(bars,[])

    def test_combination_preserves_unknown_and_is_and(self):
        frame=pd.DataFrame({list(CATALOG)[0]:[1,1,0,np.nan],list(CATALOG)[1]:[1,0,1,0]})
        np.testing.assert_equal(combined_state(frame,list(CATALOG)[:2]),[1,0,0,np.nan])

    def test_labels_are_purged_and_evaluation_dates_refused(self):
        bars=fixture();frame=feature_frame(bars,[])
        first,last=bars[90]['date'],bars[-1]['date']
        rows=screen_training(frame,first=first,last=last)
        for row in rows:
            self.assertLessEqual(row['training_selected_days']+row['training_other_days'],84)
        with self.assertRaisesRegex(ValueError,'evaluation dates'):
            screen_training(frame,first=first,last=bars[-2]['date'])
        chosen=choose_training_candidates(rows)
        self.assertLessEqual(len(chosen),3)
        self.assertTrue(all(r['selection_eligible'] for r in chosen))
        self.assertEqual(chosen,sorted(chosen,key=lambda r:(-r['training_point_biserial_IC'],r['candidate_id'])))
