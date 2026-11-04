"""Complete finite reporting on invented prices, never retained market outcomes."""
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.paper.comparative_allocation import buffered_policy_template
from quant_robot.research.slow_indicator_accounts import calculate
from quant_robot.research.indicator_combinations import ASSETS


class SlowAccountReportingTests(unittest.TestCase):
    def test_all_four_candidates_all_nine_costs_and_all_three_controls_are_retained(self):
        proposal=json.loads(Path('configs/cn_etf_slow_indicator_combinations_20261104.json').read_bytes())
        days=pd.bdate_range('2013-12-05','2024-01-02').strftime('%Y-%m-%d').tolist()
        protected={proposal[k] for k in ('first_session','evaluation_first','later_start','terminal_session')}
        protected.add(days[0])
        removable=[d for d in days[150:-1] if d not in protected]
        dropped=set(removable[:len(days)-2454])
        days=[d for d in days if d not in dropped]
        bars=[]
        for asset in ASSETS:
            for i,day in enumerate(days):
                price=round(3 + .0001*i + .1*math.sin(i/30),3)
                bars.append(dict(asset_id=asset,date=day,open=str(price),high=str(price+.01),
                                 low=str(price-.01),close=str(price),volume='10000000',amount='30000000'))
        policy=buffered_policy_template(study_id=proposal['study_id'],first_session=proposal['first_session'],
                                       terminal_session=proposal['terminal_session'],later_start=proposal['later_start'])
        snapshots={k:json.dumps(v).encode() for k,v in dict(proposal=proposal,bars=bars,sessions=days,
                                                          actions={'events':[]},comparison_policy=policy).items()}
        progress=[]
        result=calculate(snapshots,progress=progress.append)
        self.assertEqual(len(result['findings']),4)
        self.assertEqual(len(progress),4)
        self.assertEqual(sum(len(accounts) for case in result['accounts'].values() for accounts in case['accounts'].values()),108)
        for finding in result['findings']:
            self.assertEqual(len(finding['cost_summaries']),9)
            self.assertEqual(finding['uncertainty']['seed'],20261011)
            self.assertEqual(finding['uncertainty']['correction'],'Bonferroni4_within_batch_not_all_historical_search')
            self.assertEqual(finding['conditional_screen_passed'],all(finding['checks'].values()))
            self.assertEqual([x['year'] for x in finding['evaluation_folds']],[2019,2020,2021,2022,2023])
        self.assertFalse(result['fresh_out_of_sample'])
        self.assertFalse(result['paper_promotion_allowed'])
        self.assertFalse(result['net_positive_EV_verified'])
        self.assertEqual(result['new_forward_days'],0)
        proposal['hypothesis_count']=5
        snapshots['proposal']=json.dumps(proposal).encode()
        with patch('quant_robot.research.slow_indicator_accounts.run_comparison') as runner:
            with self.assertRaisesRegex(ValueError,'finite experiment'):
                calculate(snapshots)
            runner.assert_not_called()
