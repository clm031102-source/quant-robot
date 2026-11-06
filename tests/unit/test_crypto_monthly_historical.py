"""Historical-shaped dates and formats below contain invented financial values."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import crypto_monthly_admission as a
from quant_robot.research import crypto_monthly_historical as h
from quant_robot.research.crypto_monthly_diagnostic import (
    _archive, _csv, _json, _run_account_core, load_raw_month, run_account, synthetic_raw_fixture,
)
from tests.unit.test_crypto_monthly_admission import PreparedFixture


def artificial_historical_payloads():
    """Generate all31 artificial days; no path to real files or connector data."""
    raw=synthetic_raw_fixture(days=31,funding_rate='-10')
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
                row[1:5]=['100000']*4
                row[7]='10000000'; row[10]='5000000'
            name='BTCUSDT-1m-2025-01'
        archive=_archive(name,rows)
        payloads[zip_role]=(f'data/fabricated/{market}/{archive.filename}',archive.body)
        payloads[checksum_role]=(f'data/fabricated/{market}/{archive.filename}.CHECKSUM',archive.checksum)
    tool=json.loads(raw.funding_tool_return)
    for event in tool['structuredContent']['result']:
        event['fundingTime']+=delta; event['markPrice']='100000'
    tool['content'][0]['text']=json.dumps(tool['structuredContent'])
    payloads['funding_raw_MCP']=('data/fabricated/funding_tool_return.json',a.canonical(tool))
    times=[t+delta for t in raw.expected_funding_times_ms]
    projection={'status':'complete_timestamp_projection','rows':[
        {'market':m,'exact_minute_grid':True,'row_count':44640,'financial_values_decoded':False}
        for m in ('spot_1m','futures_1m','mark_1m')]+[{'market':'funding','event_times_ms':times}]}
    capture={'row_count':93,'isError':False,'raw_artifact_kind':'serialized_MCP_response_not_native_HTTP_entity',
        'clocks':{'started':{'current_time':'2026-11-06 20:00:00 UTC'},'received':{'current_time':'2026-11-06 20:00:03 UTC'}}}
    for role,obj in (('time_projection_result',projection),('funding_source_capture',capture),
        ('archive_original_source_result',{'completed_at':'2026-11-06T17:00:00+00:00'}),
        ('spot_checksum_repair_result',{'completed_at':'2026-11-06T18:00:00+00:00'})):
        payloads[role]=(f'data/fabricated/{role}.json',a.canonical(obj))
    return payloads


class HistoricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.payloads=artificial_historical_payloads()

    def setUp(self):
        self.f=PreparedFixture(self.payloads); self.addCleanup(self.f.close)

    def test_no_capability_means_no_decode(self):
        with patch.object(h,'_decode_month_core') as decode:
            with self.assertRaisesRegex(ValueError,'Live reviewed claim'): h.load_claimed_month(None)
            decode.assert_not_called()

    def test_guarded_original_loader_to_artificial_high_price_account(self):
        saved={}
        def worker(claim):
            data=h.load_claimed_month(claim)
            self.assertEqual(data.start,h.START)
            self.assertEqual(data.funding[0].at,h.START+timedelta(milliseconds=15))
            self.assertEqual(data.bars['spot'][0].candle.open,100000)
            self.assertEqual(data.provenance['source_acquisition']['funding_mcp']['received_at'],'2026-11-06T20:00:03+00:00')
            self.assertEqual(data.bars['spot'][0].candle.received_at,h.START+timedelta(minutes=1))
            self.assertIsNone(data.provenance['fixture_created_at'])
            self.assertIsNone(data.funding[0].synchronous_spot)
            claim.guard('before','B_5')
            result=_run_account_core(data,scenario='B_5',output_dir=self.f.root/a.DIRECTORY/'accounts/B_5')
            claim.guard('after','B_5')
            saved.update(result)
            # Deliberately stop this unit fixture after its one full failure
            # trajectory; never pretend the ten-account production loop ran.
            raise RuntimeError('synthetic_fixture_stopped_after_one_account')
        with patch.object(h,'run_claimed_month',side_effect=worker):
            with self.assertRaisesRegex(RuntimeError,'synthetic_fixture_stopped'): self.f.execute()
        self.assertEqual(saved['reason'],'nonpositive_model_nav_stop_preserve_exposure')
        self.assertTrue(saved['historical_returns_computed'])
        self.assertEqual(saved['execution_class'],'conditional_historical_month')
        self.assertTrue(saved['ledger']['reconciled'])
        self.assertEqual(saved['orders'][0]['time'],'2025-01-02T00:03:00+00:00')
        self.assertEqual(saved['orders'][1]['quantity'],'0.003')
        self.assertNotIn('synthetic_only',saved['kernel_component'])
        self.assertFalse(saved['qualified'])
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_memory_mutation_detected_after_account(self):
        def changed(data,*,scenario,output_dir):
            data.provenance['tampered_after_first_account']=True
            return {}
        with patch.object(h,'_run_account_core',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'Decoded input changed'): self.f.execute()
        self.assertTrue((self.f.root/a.DIRECTORY/'outcome.json').exists())

    def test_all_nine_and_cash_retained_and_post_haircut_dd_governs(self):
        calls=[]
        def account(data,*,scenario,output_dir):
            calls.append(scenario); output_dir.mkdir(parents=True)
            result={'scenario':scenario,'qualified':False,'real_forward':0,'historical_returns_computed':True,
                'final_drawdown_metric':'conditional_drawdown_including_terminal_haircut',
                'status':'completed_with_execution_failures','account_complete':True,
                'terminal':{'terminal_unsettled':scenario=='C_10'},
                'sampled_book_drawdown_before_terminal_haircut':'.399',
                'conditional_drawdown_including_terminal_haircut':'.401'}
            (output_dir/'summary.json').write_text(_json(result),encoding='utf-8')
            return result
        with patch.object(h,'_run_account_core',side_effect=account): outcome=self.f.execute()
        self.assertEqual(calls,list(h.SCENARIOS))
        self.assertEqual(outcome['status'],'completed')
        result=json.loads((self.f.root/a.DIRECTORY/'result.json').read_bytes())
        self.assertEqual(set(result['accounts']),set(h.SCENARIOS)|{'CASH'})
        self.assertFalse(result['holding_control_tested'])
        self.assertFalse(result['alpha_or_promotion_eligible'])
        self.assertTrue(result['accounts']['C_10']['terminal_unsettled'])
        self.assertEqual(result['accounts']['B_5']['conditional_drawdown_including_terminal_haircut'],'.401')
        checks=list((self.f.root/a.DIRECTORY/'guard_checks').glob('*.json'))
        self.assertEqual(len(checks),24)  # decode boundary + source before/after +20 account sides + final

    def test_actual_windows_flush_handle_preserves_bytes(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp); target=folder/'summary.json'; target.write_bytes(b'{"fabricated":true}\n')
            before=target.read_bytes(); h._durable_account(folder)
            self.assertEqual(target.read_bytes(),before)

    def test_public_synthetic_entry_still_rejects_historical_identity(self):
        raw=synthetic_raw_fixture(days=2)
        with self.assertRaisesRegex(ValueError,'separate_admission_guard'):
            load_raw_month(replace(raw,evidence_class='retained_historical_sources'))
        data=load_raw_month(raw)
        provenance={**data.provenance,'evidence_class':'retained_historical_sources'}
        with self.assertRaisesRegex(ValueError,'separate_admission_guard'):
            run_account(replace(data,provenance=provenance),output_dir=self.f.root/'not_created')

    def test_shared_core_success_label_matches_evidence_without_changing_arithmetic(self):
        # Private-core regression only: both inputs are invented observations.
        # Public real entry still enforces exact202501 dates and its live claim.
        data=load_raw_month(synthetic_raw_fixture(days=2))
        synthetic=run_account(data,output_dir=self.f.root/'synthetic_comparison')
        historical=_run_account_core(replace(data,provenance={**data.provenance,
            'evidence_class':'retained_historical_sources'}),output_dir=self.f.root/'historical_label_comparison')
        self.assertEqual(synthetic['status'],'completed_synthetic_account')
        self.assertEqual(historical['status'],'completed_conditional_historical_account')
        self.assertEqual(synthetic['ledger'],historical['ledger'])
        self.assertEqual(synthetic['orders'],historical['orders'])
        self.assertGreater(__import__('decimal').Decimal(historical['conditional_drawdown_including_terminal_haircut']),
                           __import__('decimal').Decimal(historical['sampled_book_drawdown_before_terminal_haircut']))


if __name__=='__main__': unittest.main()
