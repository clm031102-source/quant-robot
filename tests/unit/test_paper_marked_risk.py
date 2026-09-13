import copy
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from quant_robot.gui.fixtures.mock_data import demo_bars
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation, write_paper_simulation_artifacts
from quant_robot.paper.account_comparison import compare_cash_accounts
from quant_robot.paper.risk_evidence import AccountRiskLimits, audit_cash_account_risk


class PaperMarkedRiskTests(unittest.TestCase):
    def result(self):
        return run_paper_simulation(demo_bars(),PaperSimulationConfig(market='CN_ETF',initial_cash=10000,
            max_asset_weight=.1,max_gross_exposure=.1,commission_bps=5,minimum_commission=5))

    def test_daily_positions_reconcile_to_actual_cash_account_without_changing_returns(self):
        result=self.result()
        for row in result['equity_curve']:
            marked=sum(value['market_value'] for value in row['position_values'].values())
            self.assertAlmostEqual(row['equity'],row['cash']+row['dividend_receivable']+marked)
        report=audit_cash_account_risk(result)
        self.assertTrue(report['evidence_complete_on_supplied_calendar'])
        self.assertFalse(report['execution_enforcement_verified'])
        self.assertFalse(report['source_quality_verified'])

    def test_weight_limit_is_not_treated_as_fixed_cny_position_limit(self):
        result=self.result()
        row=next(row for row in result['equity_curve'] if row['position_values'])
        item=next(iter(row['position_values'].values()))
        item.update(quantity=1100/item['price'],market_value=1100)
        row['cash']=row['equity']-row['dividend_receivable']-sum(x['market_value'] for x in row['position_values'].values())
        report=audit_cash_account_risk(result)
        self.assertFalse(report['within_limits_on_supplied_marks'])
        self.assertIn('position_limit',[row['reason'] for row in report['breaches']])

    def test_missing_or_inconsistent_daily_positions_do_not_pass(self):
        result=self.result()
        held=next(i for i,row in enumerate(result['equity_curve']) if row['position_values'])
        for change in ('missing','empty','quantity','value','nan','stale'):
            altered=copy.deepcopy(result)
            row=altered['equity_curve'][held]
            item=next(iter(row['position_values'].values()))
            if change=='missing':row.pop('position_values')
            elif change=='empty':row['position_values']={}
            elif change=='quantity':item['quantity']=-1
            elif change=='value':item['market_value']+=1
            elif change=='nan':item['price']=float('nan')
            else:item['price_date']='2000-01-01'
            with self.subTest(change=change):
                audit=audit_cash_account_risk(altered)
                self.assertFalse(audit['within_limits_on_supplied_marks'])
                self.assertFalse(audit['evidence_complete_on_supplied_calendar'])
                self.assertIsNone(audit['max_position_cny'])

    def test_limits_are_explicit_and_invalid_thresholds_are_not_defaulted(self):
        result=self.result()
        for field,bad in [('initial_cash',0),('max_position_cny',True),('max_daily_loss_cny',float('nan')),
                          ('max_drawdown',1),('max_drawdown',-.08)]:
            with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):
                audit_cash_account_risk(result,replace(AccountRiskLimits(),**{field:bad}))
        audit=audit_cash_account_risk(result,replace(AccountRiskLimits(),initial_cash=2000))
        self.assertFalse(audit['within_limits_on_supplied_marks'])
        self.assertIn('initial_capital_mismatch',[row['reason'] for row in audit['breaches']])

    def test_daily_and_cumulative_loss_are_computed_from_net_equity(self):
        result=self.result()
        for index,row in enumerate(result['equity_curve']):
            row.update(equity=10000-index*60,cash=10000-index*60,dividend_receivable=0,position_values={})
            row['period_return']=0 if index==0 else row['equity']/result['equity_curve'][index-1]['equity']-1
        audit=audit_cash_account_risk(result)
        self.assertEqual(audit['max_daily_loss_cny'],60)
        self.assertIn('daily_loss_limit',[row['reason'] for row in audit['breaches']])
        self.assertFalse(audit['within_limits_on_supplied_marks'])

    def test_comparison_includes_each_accounts_risk_and_missing_evidence_remains_unknown(self):
        result=self.result()
        other=copy.deepcopy(result)
        for row in other['equity_curve']:row.pop('position_values')
        comparison=compare_cash_accounts(result,other)
        self.assertTrue(comparison['risk_comparison']['strategy']['evidence_complete_on_supplied_calendar'])
        self.assertFalse(comparison['risk_comparison']['benchmark']['within_limits_on_supplied_marks'])
        self.assertFalse(comparison['risk_adjusted_alpha_verified'])

    def test_saved_csv_positions_are_valid_json_and_replay_the_same_risk_audit(self):
        result=self.result()
        expected=audit_cash_account_risk(result)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_paper_simulation_artifacts(result,root)
            manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
            rows=pd.read_csv(root/'equity_curve.csv').to_dict(orient='records')
            for row in rows:self.assertIsInstance(json.loads(row['position_values']),dict)
            actual=audit_cash_account_risk({**manifest,'equity_curve':rows})
            self.assertEqual(actual['breaches'],expected['breaches'])
            self.assertEqual(actual['issues'],expected['issues'])
            self.assertEqual(actual['within_limits_on_supplied_marks'],expected['within_limits_on_supplied_marks'])

    def test_exact_eight_percent_drawdown_is_a_breach(self):
        result=self.result()
        for index,row in enumerate(result['equity_curve']):
            equity=10000 if index==0 else 9200
            row.update(equity=equity,cash=equity,dividend_receivable=0,position_values={})
            row['period_return']=0 if index==0 else equity/result['equity_curve'][index-1]['equity']-1
        audit=audit_cash_account_risk(result)
        self.assertIn('drawdown_limit',[row['reason'] for row in audit['breaches']])
