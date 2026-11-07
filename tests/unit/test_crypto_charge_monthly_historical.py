"""Entirely invented 2025-shaped input, never retained financial source files."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import gzip
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import crypto_charge_monthly_admission as a
from quant_robot.research import crypto_charge_monthly_historical as h
from quant_robot.research.crypto_carry_model import CHARGE_BASIS_FUNDING, FundingChargeEvent
from quant_robot.research.crypto_monthly_diagnostic import _archive, _csv, _json, synthetic_raw_fixture
from tests.unit.test_crypto_charge_monthly_admission import PreparedFixture


def invented_original_formats():
    """Generate31 artificial days in exact original layouts with B != P."""
    raw=synthetic_raw_fixture(days=31,funding_rate='.0001')
    delta=int((h.START-raw.start).total_seconds()*1000)
    payloads={}
    for market,(zip_role,checksum_role) in h.ARCHIVES.items():
        rows=_csv(raw.archives[market]); header=0 if market=='spot' else 1
        if market=='funding':
            for row in rows[1:]: row[0]=str(int(row[0])+delta)
            name='BTCUSDT-fundingRate-2025-01'
        else:
            factor=1000 if market=='spot' else 1
            for row in rows[header:]:
                row[0]=str(int(row[0])+delta*factor); row[6]=str(int(row[6])+delta*factor)
                row[1:5]=['100000']*4; row[7]='10000000'; row[10]='5000000'
            name='BTCUSDT-1m-2025-01'
        archive=_archive(name,rows)
        payloads[zip_role]=(f'data/invented/{market}/{archive.filename}',archive.body)
        payloads[checksum_role]=(f'data/invented/{market}/{archive.filename}.CHECKSUM',archive.checksum)
    tool=json.loads(raw.funding_tool_return)
    for event in tool['structuredContent']['result']:
        event['fundingTime']+=delta; event['markPrice']='120000'
    tool['content'][0]['text']=json.dumps(tool['structuredContent'])
    payloads['funding_raw_MCP']=('data/invented/funding_tool_return.json',a.canonical(tool))
    times=[t+delta for t in raw.expected_funding_times_ms]
    projection={'status':'complete_timestamp_projection','rows':[
        {'market':m,'exact_minute_grid':True,'row_count':44640,'financial_values_decoded':False}
        for m in ('spot_1m','futures_1m','mark_1m')]+[{'market':'funding','event_times_ms':times}]}
    capture={'row_count':93,'isError':False,'raw_artifact_kind':'serialized_MCP_response_not_native_HTTP_entity',
        'clocks':{'started':{'current_time':'2026-11-06 20:00:00 UTC'},'received':{'current_time':'2026-11-06 20:00:03 UTC'}}}
    for role,obj in (('time_projection_result',projection),('funding_source_capture',capture),
        ('archive_original_source_result',{'completed_at':'2026-11-06T17:00:00+00:00'}),
        ('spot_checksum_repair_result',{'completed_at':'2026-11-06T18:00:00+00:00'})):
        payloads[role]=(f'data/invented/{role}.json',a.canonical(obj))
    return payloads


class HistoricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.payloads=invented_original_formats()

    def setUp(self):
        self.f=PreparedFixture(self.payloads); self.addCleanup(self.f.close)

    def test_missing_new_claim_or_old_claim_type_cannot_decode(self):
        with patch.object(h,'_decode_month_core') as decoder:
            for claim in (None,object()):
                with self.assertRaisesRegex(ValueError,'Live reviewed claim'): h.load_claimed_month(claim)
            decoder.assert_not_called()

    def test_new_guard_loader_basis_kernel_and_two_day_account_invented_only(self):
        saved={}
        def worker(claim):
            data=h.load_claimed_month(claim)
            self.assertEqual(data.start,h.START)
            self.assertEqual(data.funding[0].at,h.START+timedelta(milliseconds=15))
            self.assertIsInstance(data.funding[0],FundingChargeEvent)
            self.assertEqual(data.funding[0].charge_basis,D(120000))
            self.assertEqual(data.bars['mark'][0].candle.open,D(100000))
            self.assertEqual(data.provenance['funding_mode'],CHARGE_BASIS_FUNDING)
            self.assertEqual(data.provenance['source_acquisition']['funding_mcp']['received_at'],'2026-11-06T20:00:03+00:00')
            self.assertEqual(data.bars['spot'][0].candle.received_at,h.START+timedelta(minutes=1))
            self.assertIsNone(data.provenance['fixture_created_at'])
            # Test-only prefix of invented observations. Production loader/scope
            # remains31 days; no real input is relabeled, shifted or truncated.
            two=replace(data,end=h.START+2*h.DAY,
                bars={name:rows[:2880] for name,rows in data.bars.items()},funding=data.funding[:6],
                provenance={**data.provenance,'test_fixture_values_are_invented':True,'test_prefix_two_days_only':True},
                coverage={**data.coverage,'days':2,'minutes_per_market':2880,'funding_events':6,'off_minute_funding_events':6})
            claim.guard('before','B_5_artificial_two_day_controller')
            output=self.f.root/a.DIRECTORY/'accounts/B_5'
            result=h._run_account_core(two,scenario='B_5',output_dir=output,funding_mode=CHARGE_BASIS_FUNDING)
            h._durable_account(output)
            claim.guard('after','B_5_artificial_two_day_controller')
            saved.update(result)
            self.assertEqual(len(result['funding_events']),6)
            for row in result['funding_events']:
                self.assertEqual(row['charge_basis'],'120000')
                self.assertEqual(row['valuation']['mark']['value'],'100000')
                self.assertEqual(row['valuation']['mark']['age_model_ms'],15)
                self.assertEqual(D(row['cash_delta']),D(row['quantity_before'])*D('.0001')*D(120000))
            with gzip.open(output/'minute_envelopes.jsonl.gz','rt') as stream:
                rows=[json.loads(line) for line in stream]
            self.assertFalse(any(p['at'].endswith('.015000+00:00') for row in rows for p in row['known_points']))
            evidence=os.environ.get('CRYPTO_CHARGE_MONTHLY_TEST_EVIDENCE')
            if evidence:
                target=Path(evidence)/'invented_two_day_account'
                shutil.copytree(output,target)
                (Path(evidence)/'artificial_input_notice.json').write_text(_json({
                    'all_financial_values_invented':True,'actual_market_source_files_decoded':0,
                    'actual_financial_admission_created':False,'production_account_count_exercised':1,
                    'source_structure_days':31,'account_test_prefix_days':2,
                    'historical_labels_are_under_test_not_actual_market_evidence':True,
                    'qualified':False,'real_forward':0})+'\n',encoding='utf-8')
            # Deliberately consume this temporary fixture after one account;
            # never claim the ten-account production loop completed.
            raise RuntimeError('invented_two_day_controller_complete_stop')
        with patch.object(h,'run_claimed_month',side_effect=worker):
            with self.assertRaisesRegex(RuntimeError,'invented_two_day'): self.f.execute()
        self.assertEqual(saved['status'],'completed_conditional_historical_account')
        self.assertEqual(saved['execution_class'],'conditional_historical_month')
        self.assertEqual(saved['funding_mode'],CHARGE_BASIS_FUNDING)
        self.assertTrue(saved['account_complete']); self.assertTrue(saved['ledger']['reconciled'])
        self.assertEqual(saved['fill_count'],4); self.assertEqual(len(saved['daily_nav']),2)
        self.assertEqual(saved['orders'][1]['quantity'],'0.003')
        self.assertFalse(saved['terminal']['terminal_unsettled'])
        self.assertGreater(D(saved['conditional_drawdown_including_terminal_haircut']),D(saved['sampled_book_drawdown_before_terminal_haircut']))
        self.assertFalse(saved['qualified']); self.assertNotIn('synthetic_only',saved['kernel_component'])
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_exact_full_original_schema_still_refuses_bad_funding_mirror(self):
        payloads=dict(self.payloads)
        path,body=payloads['funding_raw_MCP']; tool=json.loads(body)
        tool['content'][0]['text']='{}'; payloads['funding_raw_MCP']=(path,a.canonical(tool))
        fixture=PreparedFixture(payloads)
        try:
            with self.assertRaisesRegex(ValueError,'mirror'): fixture.execute()
            outcome=json.loads((fixture.root/a.DIRECTORY/'outcome.json').read_bytes())
            self.assertEqual(outcome['study_number'],20); self.assertTrue(outcome['financial_decode_started'])
            self.assertFalse((fixture.root/a.DIRECTORY/'accounts').exists())
        finally: fixture.close()

    def test_mutable_decoded_input_is_rechecked_after_each_account(self):
        def altered(data,*,scenario,output_dir,funding_mode):
            data.provenance['mutated']=True; return {}
        with patch.object(h,'_run_account_core',side_effect=altered):
            with self.assertRaisesRegex(ValueError,'Decoded input changed'): self.f.execute()

    def test_all_nine_identities_failures_dust_and_cash_retained(self):
        calls=[]
        def account(data,*,scenario,output_dir,funding_mode):
            calls.append(scenario); self.assertEqual(funding_mode,CHARGE_BASIS_FUNDING)
            output_dir.mkdir(parents=True)
            result={'scenario':scenario,'qualified':False,'real_forward':0,'historical_returns_computed':True,
                'funding_mode':CHARGE_BASIS_FUNDING,'final_drawdown_metric':'conditional_drawdown_including_terminal_haircut',
                'status':'completed_with_execution_failures','account_complete':True,
                'terminal':{'terminal_unsettled':scenario=='C_10'},
                'sampled_book_drawdown_before_terminal_haircut':'.399',
                'conditional_drawdown_including_terminal_haircut':'.401'}
            (output_dir/'summary.json').write_text(_json(result),encoding='utf-8'); return result
        with patch.object(h,'_run_account_core',side_effect=account): outcome=self.f.execute()
        result=json.loads((self.f.root/a.DIRECTORY/'result.json').read_bytes())
        self.assertEqual(calls,list(h.SCENARIOS)); self.assertEqual(outcome['study_number'],20)
        self.assertEqual(set(result['accounts']),set(h.SCENARIOS)|{'CASH'})
        self.assertEqual(result['funding_mode'],CHARGE_BASIS_FUNDING); self.assertFalse(result['old_study19_resumed'])
        self.assertTrue(result['accounts']['C_10']['terminal_unsettled'])
        self.assertEqual(result['accounts']['B_5']['conditional_drawdown_including_terminal_haircut'],'.401')
        self.assertEqual(len(list((self.f.root/a.DIRECTORY/'guard_checks').glob('*.json'))),25)
        self.assertFalse(result['holding_control_tested']); self.assertFalse(result['alpha_or_promotion_eligible'])

    def test_writable_windows_fsync_keeps_original_bytes(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp); p=folder/'summary.json'; p.write_bytes(b'{"invented":true}\n')
            before=p.read_bytes(); h._durable_account(folder); self.assertEqual(p.read_bytes(),before)


if __name__=='__main__': unittest.main()
