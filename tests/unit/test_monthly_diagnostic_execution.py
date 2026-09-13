import copy
from datetime import date, timedelta, datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.research.monthly_diagnostic_registration import build_registration, sha256, DIRECTORY
from quant_robot.research.monthly_diagnostic_registration import verified_input_bytes
from quant_robot.research.monthly_diagnostic_execution import execute_registration, preflight_registration
from quant_robot.research.monthly_diagnostic_inputs import _calendar, _signals
from tests.unit.test_monthly_diagnostic_registration import scheduler_fixture

REPO = Path(__file__).resolve().parents[2]


def execution_fixture(root):
    dates = pd.bdate_range('2020-01-02', '2024-06-28')
    anchors = list(pd.Series(dates).groupby(dates.to_period('M')).first().dt.date)
    vintages = [(item - timedelta(days=7)).isoformat() for item in anchors]
    source = root / 'data'; source.mkdir(exist_ok=True)
    inputs = {}
    def put(role, content, suffix='.json'):
        path = source / (role + suffix); path.write_bytes(content)
        inputs[role] = {'path': path.relative_to(root).as_posix(), 'sha256': sha256(content)}
    def encoded(value): return json.dumps(value).encode()
    put('proposal', (REPO / 'configs/cn_etf_policy_uncertainty_historical_diagnostic_proposal_20260914.json').read_bytes())
    calendar = pd.DataFrame({'market': 'CN', 'date': dates.date, 'is_open': 1, 'source': 'synthetic'})
    put('calendar', calendar.to_csv(index=False).encode(), '.csv')
    put('actions', encoded({'schema_version': 3, 'source_ref': 'synthetic fixture', 'asset_ids': ['CN_ETF_XSHG_510300'],
        'coverage_start': '2020-01-02', 'coverage_end': '2024-06-28', 'events': []}))
    for year in range(2020, 2025):
        sessions = dates[dates.year == year]
        bars = pd.DataFrame({'date': sessions.date, 'asset_id': 'CN_ETF_XSHG_510300', 'market': 'CN_ETF', 'currency': 'CNY', 'close': 10.0})
        content = io.BytesIO(); bars.to_parquet(content, index=False); put('bars_' + str(year), content.getvalue(), '.parquet')
    months = pd.date_range('2018-01-01', '2024-05-01', freq='MS')
    batches = []
    coverage = []
    for index, batch in enumerate((vintages[:27], vintages[27:]), 1):
        frame = pd.DataFrame({'observation_date': months.date})
        for vintage in batch:
            latest = pd.Timestamp(vintage).to_period('M').to_timestamp()
            frame['CHNMAINLANDEPU_' + vintage.replace('-', '')] = ['1' if month <= latest else '' for month in months]
        content = frame.to_csv(index=False).encode(); put('policy_' + str(index), content, '.csv')
        batches.append({'index': index, 'requested_vintages': batch, 'csv_sha256': sha256(content)})
    for anchor, vintage in zip(anchors, vintages):
        latest = pd.Timestamp(vintage).to_period('M').to_timestamp()
        coverage.append({'execution_date': anchor.isoformat(), 'vintage_date': vintage,
            'latest_available_observation': latest.date().isoformat(), 'latest_month_and_prior_12_complete': True})
    put('policy_scope', encoded({'observation_start':'2018-01-01','observation_end':'2024-05-01'}))
    put('policy_audit', encoded({'batches':batches, 'coverage':coverage, 'anchors_with_required_13_months':54}))
    price_roles = ['calendar', 'actions', *['bars_' + str(year) for year in range(2020, 2025)]]
    join = {'fingerprints': {inputs[role]['path']:inputs[role]['sha256'] for role in price_roles}}
    put('source_join', encoded(join))
    review = {'status':'conditional_analytical_use_review_complete_not_execution_admission',
        'proposal_sha256':inputs['proposal']['sha256'], 'retained_joint_audit_sha256':inputs['source_join']['sha256'],
        'retained_ALFRED_audit_sha256':inputs['policy_audit']['sha256'],
        'newly_hash_checked_policy_files':{inputs['policy_' + str(i)]['path']:inputs['policy_' + str(i)]['sha256'] for i in (1,2)},
        'source_audit_verified':False, 'research_admission_granted':False}
    put('source_review', encoded(review))
    (root / 'implementation.py').write_text('# fixture\n')
    packet = build_registration(inputs=inputs, code_files={'implementation.py':sha256((root / 'implementation.py').read_bytes())},
        environment={'python':'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')
    (root / 'registration.json').write_text(json.dumps(packet, sort_keys=True))
    scheduler = scheduler_fixture(packet)
    gate = {'status':'ready', 'mode':'single_monthly_diagnostic_only', 'generated_at':datetime.now(timezone.utc).isoformat(),
        'selected':{'machine':'office_desktop','task':'factor_batch','branch':packet['branch'],'current_branch':packet['branch']},
        'blockers':[], 'primary_market':'CN_ETF', 'safety':{'factor_batch_allowed':False,'monthly_diagnostic_allowed':True,
            'monthly_diagnostic_scope':scheduler['monthly_diagnostic_decision'], 'final_holdout_allowed':False,'live_boundary_allowed':False}}
    return packet, scheduler, gate


class MonthlyExecutionTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);self.root=Path(directory.name)
        self.packet,self.scheduler,self.gate=execution_fixture(self.root)

    def run_study(self, **changes):
        args = dict(root=self.root, registration_path='registration.json', scheduler=self.scheduler,
            gate_supplier=lambda:self.gate, environment={'python':'fixture'})
        args.update(changes)
        return execute_registration(**args)

    def test_preflight_reads_no_price_table_and_claims_no_attempt(self):
        with patch('pandas.read_parquet', side_effect=AssertionError('must not decode prices')):
            result = preflight_registration(root=self.root, registration_path='registration.json',
                scheduler=self.scheduler, gate_supplier=lambda:self.gate, environment={'python':'fixture'})
        self.assertFalse((self.root/self.packet['ledger_path']).exists())
        self.assertEqual(result.registration['registration_id'],self.packet['registration_id'])

    def test_full_fifty_three_interval_pipeline_is_gross_only_and_one_use(self):
        result=self.run_study()
        self.assertEqual(result['diagnostic']['interval_count'],53)
        self.assertEqual(len(result['intervals']),53)
        self.assertEqual(result['diagnostic']['decision'],'reject_fixed_diagnostic')
        self.assertEqual(result['source_origin'],'synthetic_fixture')
        self.assertFalse(result['qualifies_for_promotion'])
        self.assertFalse(result['net_account_result'])
        self.assertEqual(result['counts_as_forward_paper_days'],0)
        with self.assertRaisesRegex(ValueError,'claimed'):self.run_study()

    def test_denied_or_stale_gate_fails_before_decode_or_claim(self):
        for change in ({'status':'blocked'},{'generated_at':'2020-01-01T00:00:00+00:00'},{'mode':'family_rotation_review_only'}):
            gate=copy.deepcopy(self.gate);gate.update(change)
            with self.subTest(change=change), patch('pandas.read_parquet', side_effect=AssertionError('no decode')):
                with self.assertRaises(ValueError):self.run_study(gate_supplier=lambda:gate)
        self.assertFalse((self.root/self.packet['ledger_path']).exists())

    def test_parse_failure_consumes_attempt_and_records_failure(self):
        with patch('pandas.read_parquet',side_effect=ValueError('injected decode failure')):
            with self.assertRaises(ValueError):self.run_study()
        outcome=json.loads((self.root/DIRECTORY/'outcome.json').read_text())
        self.assertEqual(outcome['status'],'failed')
        self.assertEqual(outcome['failure_kind'],'ValueError')
        with self.assertRaisesRegex(ValueError,'claimed'):self.run_study()

    def test_source_metadata_cannot_promote_itself(self):
        self.gate['safety']['monthly_diagnostic_scope']['promotion_allowed']=True
        with self.assertRaises(ValueError):self.run_study()
        self.assertFalse((self.root/self.packet['ledger_path']).exists())

    def test_execution_uses_checked_action_bytes_after_original_file_changes(self):
        def replace_original(_):
            (self.root/self.packet['inputs']['actions']['path']).write_text('corrupted after claim')
        result=self.run_study(on_claim=replace_original)
        self.assertEqual(result['diagnostic']['interval_count'],53)
        self.assertEqual(result['analytical_price_evidence']['applied_events'],0)

    def test_policy_decimal_above_median_is_not_rounded_into_a_tie(self):
        snapshots=verified_input_bytes(self.root,self.packet,environment={'python':'fixture'})
        packet=copy.deepcopy(self.packet)
        audit=json.loads(snapshots['policy_audit'])
        for batch in audit['batches']:
            role='policy_'+str(batch['index'])
            frame=pd.read_csv(io.BytesIO(snapshots[role]),dtype=str,keep_default_na=False)
            for vintage in batch['requested_vintages']:
                latest=pd.Timestamp(vintage).to_period('M').start_time.date().isoformat()
                frame.loc[frame['observation_date'].eq(latest),'CHNMAINLANDEPU_'+vintage.replace('-','')]='1.0000000000000000000001'
            snapshots[role]=frame.to_csv(index=False).encode()
            packet['inputs'][role]['sha256']=sha256(snapshots[role])
            batch['csv_sha256']=sha256(snapshots[role])
        snapshots['policy_audit']=json.dumps(audit).encode()
        _,anchors=_calendar(snapshots['calendar'])
        signals,details=_signals(packet,snapshots,anchors)
        self.assertEqual(signals,[0]*53)
        self.assertEqual(len(details),53)

    def test_vintage_substitution_cannot_change_the_original_cutoff(self):
        snapshots=verified_input_bytes(self.root,self.packet,environment={'python':'fixture'})
        _,anchors=_calendar(snapshots['calendar'])
        audit=json.loads(snapshots['policy_audit']);audit['coverage'][0]['vintage_date']='2020-01-01'
        snapshots['policy_audit']=json.dumps(audit).encode()
        with self.assertRaisesRegex(ValueError,'54C-7'):_signals(self.packet,snapshots,anchors)

    def test_unregistered_scope_fields_fail_before_claim(self):
        self.gate['safety']['monthly_diagnostic_scope']['new_policy']='change direction'
        with self.assertRaises(ValueError):self.run_study()
        self.assertFalse((self.root/self.packet['ledger_path']).exists())


if __name__=='__main__':unittest.main()
