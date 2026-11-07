"""Invented saved UI records; no market data, strategy execution or scheduler."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.gui import us_low_unit_model_status as S


def saved_record():
    accounts={}
    for role in S.ROLES:
        cost=role.split('_')[1]
        accounts[role]=dict(scenario_id=role,scenario_role=cost,currency='USD',initial_cash='1000.00',
            minimum_commission='1.00' if cost=='primary' else '2.50',slippage_bps=10 if cost=='primary' else 30,
            ledger=dict(date='2026-11-06',NAV='1000.00',maxDD='0',days=[],fills=[],
                total_commission='0',total_slippage='0',total_sell_levy='0',total_CIL_cost='0',
                balances=dict(spendable_cash='1000.00',locked_cash='0',receivables={},quantities=dict.fromkeys(S.ASSETS,0))))
    snapshot=dict(schema='us_low_unit_four_model_snapshot_v1',evidence_kind='conditional_provider_observation',
        constructed_from_market_data=True,qualified=False,strict_forward_days=0,artificial_model_days=0,
        model_forward_days=0,assets=list(S.ASSETS),accounts=accounts,date='2026-11-06',
        last_source_received_at='2026-11-07T22:00:00Z',independent_scenarios_not_one_4000USD_portfolio=True)
    return dict(schema='us_low_unit_model_operations_v1',snapshot=snapshot,status='initialized_unique_entry_waiting_for_completed_session',
        updated_at='2026-11-07T22:01:00Z',qualified=False,strict_real_forward_days=0,capture_scope_sha256='a'*64,
        operation_window=dict(start='2026-11-09',end='2026-12-07',scheduled_sessions=20),
        schedule=dict(installed=True,next_capture_at='2026-11-09T21:15:00Z',last_attempt_at='2026-11-07T22:01:00Z',
            last_attempt_status='initialized_unique_entry_waiting_for_completed_session'))


def save(root,value):
    path=Path(root)/S.STATUS_PATH;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


class LowUnitModelStatusTests(unittest.TestCase):
    def test_initialization_has_four_accounts_but_no_earned_profit_or_installation_claim(self):
        with tempfile.TemporaryDirectory() as root:
            save(root,saved_record());value=S.current_low_unit_model_status(root)
        self.assertTrue(value['available']);self.assertEqual(len(value['accounts']),4)
        self.assertEqual(value['model_forward_days'],0);self.assertEqual(value['real_forward_days'],0)
        self.assertFalse(value['schedule']['installed'])
        self.assertTrue(all(a['model_profit_USD'] is None for a in value['accounts'].values()))
        self.assertTrue(value['independent_scenarios_not_one_4000USD_portfolio'])

    def test_observed_day_has_separate_net_values_costs_and_all_receivables(self):
        record=saved_record();snapshot=record['snapshot'];snapshot.update(model_forward_days=1,date='2026-11-09')
        for account in snapshot['accounts'].values():
            account['ledger'].update(date='2026-11-09',days=[{}],NAV='1001.25',total_commission='4.00',total_slippage='0.24')
            account['ledger']['balances']['receivables']={'div':dict(amount='1.00'),'cil':dict(amount='2.50')}
        with tempfile.TemporaryDirectory() as root:
            save(root,record);value=S.current_low_unit_model_status(root)
        self.assertTrue(value['available'])
        for account in value['accounts'].values():
            self.assertEqual(account['model_profit_USD'],'1.25')
            self.assertEqual(account['receivable_USD'],'3.50');self.assertEqual(account['execution_cost_USD'],'4.24')

    def test_artificial_incomplete_inconsistent_or_false_forward_cannot_display_results(self):
        changes=[lambda s:s.update(evidence_kind='artificial'),lambda s:s['accounts'].pop('drift_stress'),
            lambda s:s.update(model_forward_days=1),lambda s:s.update(strict_forward_days=1),
            lambda s:s['accounts']['monthly_primary']['ledger'].update(NAV='NaN')]
        for change in changes:
            record=saved_record();change(record['snapshot'])
            with tempfile.TemporaryDirectory() as root:
                save(root,record);value=S.current_low_unit_model_status(root)
            self.assertFalse(value['available']);self.assertEqual(value['accounts'],{})

    def test_schedule_needs_matching_export_and_scope(self):
        with tempfile.TemporaryDirectory() as root:
            record=saved_record();save(root,record);parent=Path(root)/S.STATUS_PATH.parent
            export=parent/'scheduled_task_preparation/registered.utf16.xml';export.parent.mkdir()
            raw='artificial task export'.encode('utf-16');export.write_bytes(raw)
            schedule=dict(schema='us_low_unit_model_schedule_v1',installed=True,capture_scope_sha256='a'*64,
                task_name='USDLowUnitFourModels_20261109_20261207',actual_export=dict(path=str(export.resolve()),
                bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            (parent/'schedule_registration.json').write_text(json.dumps(schedule),encoding='utf-8-sig')
            self.assertTrue(S.current_low_unit_model_status(root)['schedule']['installed'])
            export.write_bytes(raw+b'x')
            self.assertFalse(S.current_low_unit_model_status(root)['schedule']['installed'])

    def test_missing_and_recorded_failure_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(S.current_low_unit_model_status(root)['status'],'not_deployed')
            record=saved_record();record.update(status='blocked_before_source_request',snapshot={})
            save(root,record);value=S.current_low_unit_model_status(root)
            self.assertTrue(value['available']);self.assertIsNone(value['model_forward_days'])


if __name__=='__main__':unittest.main()
