"""Invented original-format data with real-shaped dates, never market files."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, getcontext, Inexact, localcontext
import io
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from quant_robot.paper import bond_risk_compensation as kernel
from quant_robot.research import bond_risk_compensation_admission as a
from quant_robot.research import bond_risk_compensation_historical as h
from tests.unit.test_bond_risk_compensation_admission import PreparedFixture


def invented_original_formats(price_before=91.0):
    start,end=date.fromisoformat(h.START),date.fromisoformat(h.END)
    days=[start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<5]
    # Fabricated calendar satisfying the fixed shape, NOT historical holidays.
    prefix=[d for d in days if d<date(2020,2,6)][:19]+[date(2020,2,6)]
    rest=[d for d in days if d>=date(2020,2,7)]
    remove=len(prefix)+len(rest)-1087
    removable=[d for d in rest if date(2020,3,1)<=d<date(2021,1,1)]
    removed=set(removable[:remove]);days=prefix+[d for d in rest if d not in removed]
    assert len(days)==1087 and days[20]==date(2020,2,7)
    payloads={}
    def store(role,obj,path=None):
        payloads[role]=(path or 'data/invented/'+role+'.json',a.canonical(obj))
    calendar='market,date,is_open,source\n'+''.join('CN,'+d.isoformat()+',1,tushare\n' for d in days)
    payloads['calendar']=('data/invented/calendar.csv',calendar.encode())
    sources={};requests=[]
    for order in range(1,23):
        path=f'data/invented/document_{order:02}.pdf';raw=f'INVENTED_SOURCE_{order}'.encode()
        payloads[f'official_PDF_{order:02}']=(path,raw)
        sources[order]={'path':path,'sha256':a.digest(raw),'bytes':len(raw)}
        store(f'PDF_receipt_{order:02}',dict(body_complete=True,entity={'sha256':a.digest(raw)},
            body_received_at='2026-11-06T20:00:00+00:00'))
        requests.append({'order':order,'role':'cash_distribution_notice' if 3<=order<=17 else 'other',
                         'symbol':'511220','catalog_date':'2020-01-02','url':f'https://example.invalid/{order}.pdf'})
    requests[0]['catalog_date']='2023-01-10'
    events=[]
    for i,order in enumerate(range(3,18)):
        index=60+i*65;record,ex,pay=(days[index+n].isoformat() for n in (0,1,3))
        requests[order-1]['catalog_date']=days[index-1].isoformat()
        events.append(dict(event_id='invented_cash_'+str(i),asset_id=h.ASSET,document=order,
            record_date=record,ex_date=ex,pay_date=pay,declared_amount_cny='0.1',declared_denominator_shares=10,
            cash_per_event_date_share_cny='0.01',conditional_receipt_per_share_cny='0.01',
            share_unit_era='pre_20230113_1_to_10_split' if record<'2023-01-16' else 'post_20230113_1_to_10_split',
            source=sources[order],notice_url=requests[order-1]['url'],gross_net_status='invented conditional amount',
            investor_cash_availability='invented date only; after trading'))
    store('cash_action_facts',dict(artifact_type='511220_fifteen_dividend_notice_action_facts_v1',events=events))
    store('cash_action_closure',dict(artifact_type='511220_annual_dividend_and_share_closure_v1',research_subinterval=[h.START,h.END],
        all_15_notice_events_matched_once=True,cross_report_share_balance_links_exact=True,total_notice_events_matched=15,
        reports=[{'source':sources[n]} for n in range(18,23)]))
    store('split_projection',dict(event=dict(asset_id=h.ASSET,share_multiplier='10',rights_record_date='2023-01-13',ex_date='2023-01-16'),
        raw_sources={'1':sources[1],'2':sources[2]}))
    store('report_proposal',dict(requests=requests))
    store('input_authority',dict(asset_id=h.ASSET,metadata_expected=h.IDENTITY,date_coverage={'rows':1087}))
    import pyarrow as pa
    import pyarrow.parquet as pq
    for year in range(2020,2025):
        rows=[]
        for day in days:
            if day.year!=year: continue
            price=price_before if day<date(2023,1,16) else price_before/10
            row={**h.IDENTITY,'date':day,'timestamp':datetime.combine(day,datetime.min.time(),timezone(timedelta(hours=8))).astimezone(timezone.utc),
                'ingested_at':datetime(2026,11,6,20,tzinfo=timezone.utc),
                **{k:price for k in ('open','high','low','close')},'volume':100000.0 if day<date(2023,1,16) else 1000000.0}
            rows.append(row)
        neighbor={**rows[0],'asset_id':'CN_ETF_XSHG_OTHER','symbol':'OTHER.SH','open':float('nan')}
        rows.append(neighbor)
        sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(rows),sink)
        payloads['bars_'+str(year)]=(a.BAR_PATH.format(year),sink.getvalue().to_pybytes())
    return payloads


class HistoricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.payloads=invented_original_formats()

    def setUp(self):
        self.f=PreparedFixture(self.payloads);self.addCleanup(self.f.close)

    def test_no_capability_cannot_decode_real_shaped_input(self):
        with patch('pyarrow.parquet.read_table') as read:
            for claim in (None,object()):
                with self.assertRaisesRegex(ValueError,'claim required'): h.load_claimed_inputs(claim)
            read.assert_not_called()

    def test_exact_decoded_snapshot_is_durable_before_first_account_without_redecode(self):
        data=h.LoadedBond({'invented_only':'91'},{'all_values_invented':True})
        def load(claim):
            claim.begin_financial_decode(); return data
        def first_account(*args,**kwargs):
            path=self.f.root/a.DIRECTORY/'decoded_input.json'
            self.assertTrue(path.is_file())
            snapshot=json.loads(path.read_bytes())
            self.assertEqual(snapshot,{'fixture':data.fixture,'provenance':data.provenance})
            self.assertEqual(a.digest(a.canonical(snapshot)),h.loaded_digest(data))
            with self.assertRaises(FileExistsError): a.write_exclusive_json(path,snapshot)
            raise RuntimeError('test stops before any economic account')
        with patch.object(h,'load_claimed_inputs',side_effect=load) as loader,patch.object(kernel,'_prepare',side_effect=first_account):
            with self.assertRaisesRegex(RuntimeError,'before any economic account'): self.f.execute()
            loader.assert_called_once()
        folder=self.f.root/a.DIRECTORY
        self.assertTrue((folder/'decoded_input.json').is_file())
        self.assertFalse((folder/'accounts/M0_S0/complete.json').exists())
        self.assertEqual(json.loads((folder/'outcome.json').read_bytes())['status'],'failed_consumed')

    def test_full_guard_loader_ten_accounts_reference_artificial_values(self):
        before=a.runtime_environment();ambient=getcontext().copy()
        outcome=self.f.execute()
        self.assertEqual(outcome['status'],'completed')
        self.assertEqual(a.runtime_environment(),before)
        self.assertEqual(getcontext().flags,ambient.flags)
        folder=self.f.root/a.DIRECTORY; result=json.loads((folder/'result.json').read_bytes())
        self.assertEqual(set(result['accounts']),{f'M{m}_S{s}' for m,s in kernel.COST_CASES}|{'CASH'})
        self.assertEqual(result['additional_nontrading_references'],1)
        primary=json.loads((self.f.root/result['accounts']['M5_S10']['path']).read_bytes())
        self.assertEqual(len(primary['rows']),1087)
        self.assertEqual(primary['asset_id'],h.ASSET)
        self.assertEqual(primary['rows'][0]['date'],h.START)
        self.assertTrue(primary['historical_returns_computed'])
        self.assertEqual(primary['evidence_class'],h.SOURCE_CLASS)
        self.assertTrue(primary['summary']['cash_quantity_NAV_reconciled'])
        with localcontext(kernel.CONTEXT):
            self.assertEqual(sum((Decimal(x['net_book_change']) for x in primary['annual_attribution']),Decimal(0)),
                             Decimal(primary['summary']['net_book_PnL']))
        self.assertEqual(primary['source_provenance']['source_acquisition']['retained_row_ingested_at_min'],'2026-11-06T20:00:00+00:00')
        record=next(row for row in primary['rows'] if row['date']=='2023-01-13')
        ex=next(row for row in primary['rows'] if row['date']=='2023-01-16')
        self.assertEqual(record['post_registration_quote_unit_factor'],10)
        self.assertEqual(ex['post_registration_quote_unit_factor'],1)
        self.assertEqual(record['quantity'],ex['quantity'])
        self.assertTrue(all(fill['unknown_flags']==['suspended','limit_up','limit_down'] for fill in primary['fills']))
        self.assertFalse(result['qualified']);self.assertFalse(result['holding_control_tested'])
        self.assertEqual(primary['source_provenance']['action_evidence'][0]['actual_body_received_at'],'2026-11-06T20:00:00+00:00')
        self.assertIn('complete.json',result['reference']['path'])
        evidence=os.environ.get('BOND_HISTORICAL_TEST_EVIDENCE')
        if evidence:
            target=Path(evidence)/'invented_1087_session_run';shutil.copytree(folder,target)
            (Path(evidence)/'artificial_values_notice.json').write_text(json.dumps(dict(
                financial_values_all_invented=True,calendar_fabricated_shape_not_historical_holidays=True,
                real_market_inputs_decoded=0,real_financial_admission_created=False,
                historical_labels_under_test_only=True,qualified=False),indent=2),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_first_parser_failure_consumes_without_accounts(self):
        with patch('pyarrow.parquet.read_table',side_effect=ValueError('invented column failure')):
            with self.assertRaisesRegex(ValueError,'invented column'): self.f.execute()
        folder=self.f.root/a.DIRECTORY
        self.assertTrue(json.loads((folder/'outcome.json').read_bytes())['research_study_consumed'])
        self.assertFalse((folder/'accounts').exists())

    def test_old_expensive_lot_does_not_fake_pre_split_holding(self):
        fixture=PreparedFixture(invented_original_formats(100.0))
        try:
            def worker(claim):
                data=h.load_claimed_inputs(claim)
                with localcontext(kernel.CONTEXT):
                    prepared=kernel._prepare(data.fixture,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
                    split=kernel._prepare_split(data.fixture,prepared,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
                    account=kernel._exact(kernel._account(prepared,5,10,split,context=kernel.HISTORICAL_CONTEXT))
                self.assertFalse(any(f['date']<'2023-01-16' for f in account['fills']))
                self.assertEqual(account['fills'][0]['quantity'],900)
                self.assertEqual(account['summary']['nontrade_conversion_delta'],0)
                raise RuntimeError('test-only one account complete')
            with patch.object(h,'run_claimed_diagnostic',side_effect=worker):
                with self.assertRaisesRegex(RuntimeError,'test-only'): fixture.execute()
        finally: fixture.close()

    def test_memory_mutation_after_account_is_detected_and_retained(self):
        original=h._persist_account
        captured={}
        load=h.load_claimed_inputs
        def capture(claim):
            data=load(claim);captured['data']=data;return data
        def tamper(folder,result):
            artifact=original(folder,result);captured['data'].fixture['bars'][0]['close']='101';return artifact
        with patch.object(h,'load_claimed_inputs',side_effect=capture),patch.object(h,'_persist_account',side_effect=tamper):
            with self.assertRaisesRegex(ValueError,'Decoded inputs changed'): self.f.execute()
        self.assertTrue((self.f.root/a.DIRECTORY/'accounts/M0_S0/complete.json').exists())
        self.assertFalse((self.f.root/a.DIRECTORY/'accounts/M0_S10').exists())

    def test_public_synthetic_gate_does_not_accept_historical_context_identity(self):
        fixture=kernel.fixed_artificial_fixture(30)
        fixture.update(evidence_class=h.SOURCE_CLASS,asset_id=h.ASSET,invented_values=False)
        with self.assertRaises(ValueError): kernel.run_synthetic_account(fixture)

    def test_real_parser_rejects_bad_volume_missing_date_or_cash_denominator(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        for problem in ('negative_volume','missing_target_date','bad_denominator'):
            payloads=dict(self.payloads)
            if problem=='bad_denominator':
                path,body=payloads['cash_action_facts']; obj=json.loads(body)
                obj['events'][0]['declared_denominator_shares']=1
                payloads['cash_action_facts']=(path,a.canonical(obj))
            else:
                path,body=payloads['bars_2021']; table=pq.read_table(pa.BufferReader(body)); rows=table.to_pylist()
                if problem=='negative_volume': rows[0]['volume']=-1.0
                else: rows.pop(0)
                sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(rows,schema=table.schema),sink)
                payloads['bars_2021']=(path,sink.getvalue().to_pybytes())
            fixture=PreparedFixture(payloads)
            try:
                with self.subTest(problem=problem),self.assertRaises(ValueError): fixture.execute()
                self.assertFalse((fixture.root/a.DIRECTORY/'accounts').exists())
                self.assertTrue(json.loads((fixture.root/a.DIRECTORY/'outcome.json').read_bytes())['research_study_consumed'])
            finally: fixture.close()


if __name__=='__main__': unittest.main()
