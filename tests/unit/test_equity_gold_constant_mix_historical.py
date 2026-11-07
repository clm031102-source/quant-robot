import copy
import json
import os
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from quant_robot.research import equity_gold_constant_mix_admission as a
from quant_robot.research import equity_gold_constant_mix_historical as h
from quant_robot.research import equity_gold_constant_mix as m
from quant_robot.ops import tushare_fund_daily_wire as w

QUARTERS=('2014-01-03 2014-04-01 2014-07-01 2014-10-08 2015-01-05 2015-04-01 2015-07-01 2015-10-08 '
 '2016-01-04 2016-04-01 2016-07-01 2016-10-10 2017-01-03 2017-04-05 2017-07-03 2017-10-09 '
 '2018-01-02 2018-04-02 2018-07-02 2018-10-08 2019-01-02 2019-04-01 2019-07-01 2019-10-08 '
 '2020-01-02 2020-04-01 2020-07-01 2020-10-09 2021-01-04 2021-04-01 2021-07-01 2021-10-08 '
 '2022-01-04 2022-04-01 2022-07-01 2022-10-10 2023-01-03 2023-04-03 2023-07-03 2023-10-09').split()


def package(root):
    """Entirely artificial values/calendar construction; no external file reads."""
    root=Path(root);pins={};originals={}
    def put(role,value):
        path=root/'artificial_sources'/(role+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        raw=value if type(value) is bytes else (json.dumps(value,ensure_ascii=False)+'\n').encode()
        path.write_bytes(raw);ref=dict(path=path.as_posix(),sha256=a.digest(raw),bytes=len(raw))
        pins[role]=dict(path=path.relative_to(root).as_posix(),sha256=ref['sha256']);originals[role]=ref
        return ref
    ds=[];day=date(2013,12,5)
    while day<=date(2024,1,2):
        if day.weekday()<5 and day.isoformat() not in ('2014-01-01','2024-01-01'):ds.append(day.isoformat())
        day+=timedelta(days=1)
    protected=set(ds[:30]+ds[-5:]+QUARTERS)
    for q in QUARTERS:protected.add(ds[ds.index(q)+1])
    remove=[]
    for d in reversed(ds):
        if len(ds)-len(remove)==2454:break
        if d not in protected and d[5:7] in ('02','05','08','11'):remove.append(d)
    ds=[d for d in ds if d not in set(remove)];assert len(ds)==2454
    put('sessions',ds);put('method',dict(window=dict(quarter_sell_sessions=QUARTERS)))
    put('relocations',dict(artifact_type='constant_mix_exact_source_relocations_v1',mappings=[]))
    batch=put('source_batch_claim',dict(at='2099-01-01T00:00:00Z',evidence_class='synthetic_only_not_source_evidence'))
    requests=[];entries=[]
    for i,(year,symbol) in enumerate((y,s) for y in range(2013,2025) for s in w.SYMBOLS):
        dates=[d for d in ds if d.startswith(str(year))];identity=f'{i+1:02}_fund_daily_{symbol.replace(".","_")}_{year}'
        role=f'fund_daily_{symbol[:6]}_{year}_provider_wire'
        request=dict(order=i+1,id=identity,role=role,endpoint=w.URL,method='POST',api_name=w.API,
            params=dict(ts_code=symbol,start_date='20131205' if year==2013 else f'{year}0101',end_date='20240102' if year==2024 else f'{year}1231'),
            fields=','.join(w.FIELDS),expected_trade_dates=[d.replace('-','') for d in dates],expected_rows=len(dates),
            expected_ISO_dates_sha256=w.date_digest(dates),expected_symbol_date_sha256=w.date_digest(dates,symbol),
            planned_capture_directory=f'capture/requests/{identity}',actual_response_ref=None)
        rows=[[symbol,d.replace('-',''),'1.20','1.21','1.19','1.20','100000','OPAQUE'] for d in dates]
        # amount syntax must be numeric, but its value is never interpreted.
        for row in rows:row[7]='999999999999999999999999999999999999999999999999999999999999'
        for row in rows:
            if row[1]=='20240102':row[3:6]=[None,None,None]
        raw=(json.dumps(dict(code=0,data=dict(fields=list(w.FIELDS),items=rows)))+'\n').encode()
        rawref=put(role,raw);structure=w.inspect_structure(raw,request)
        claim=put(role+'_claim',dict(at='2099-01-01T00:00:00Z',request=request,batch_claim=batch))
        receipt=put(role+'_receipt',dict(artifact_type='fund_daily_batch_request_receipt_v1',
            evidence_class='synthetic_only_not_source_evidence',request_id=identity,request_claim=claim,raw=rawref,
            structure=structure,error=None,body_complete=True,worker_exit_confirmed=True,http_status=200,received_bytes=len(raw),
            request_started_at='2099-01-01T00:00:01Z',headers_received_at='2099-01-01T00:00:02Z',
            body_completed_at='2099-01-01T00:00:03Z',retained_at='2099-01-01T00:00:04Z'))
        requests.append(request);entries.append(dict(request_id=identity,role=role,raw=rawref,receipt=receipt,request_claim=claim,structure=structure))
    manifest=dict(artifact_type='constant_mix_fixed_24_provider_requests_v1',symbols=list(w.SYMBOLS),range=[ds[0],ds[-1]],
        request_count=24,expected_total_symbol_date_rows=4908,old_dayk_or_971_mapped_rows_used_as_authority=False,
        request_budget=dict(max_POST=24,GET=0,automatic_pagination=0,retry=0,redirect=0,substitute_dates_or_symbols=False,resume_failed_batch=False),requests=requests)
    put('source_manifest',manifest)
    index=put('source_index',dict(evidence_class='synthetic_only_not_source_evidence',request_count=24,identity_rows=4908,roles=entries))
    put('source_outcome',dict(status='completed_structure_only',evidence_class='synthetic_only_not_source_evidence',
        request_receipts=entries,source_index=index,batch_claim=batch))
    put('source_final_review',dict(status='accepted_complete_source_structure_for_conditional_input',source_index_sha256=index['sha256'],qualified=False))
    actions=[];joins=[];tax=[]
    for year in range(2014,2024):
        available=[d for d in ds if d.startswith(str(year))];known,record,ex,pay=available[5:9]
        identity=f'artificial_event_{year}'
        notice=put(f'notice_{year}',dict(artificial=True,no_real_document=True));put(f'known_{year}',dict(date=known))
        actions.append(dict(event_id=identity,asset_id=h.ASSETS[0],record_date=record,ex_date=ex,pay_date=pay,cash_per_unit='0.01',share_multiplier='1'))
        joins.append(dict(event_id=identity,asset_id=h.ASSETS[0],record_date=record,ex_date=ex,pay_date=pay,
            known_date_bridge=dict(role=f'known_{year}',date_label=known),notice_sha256=notice['sha256'],retained_notice_roles_by_same_sha=[f'notice_{year}']))
        tax.append(dict(event_id=identity,status='documented_exemption',cash_mapping='announced_per_share_no_income_tax_withholding',
            investor_net_credit_verified=False,tax_scope='documented_notice_conditional_holder',source_role=f'notice_{year}',source_field_or_page='artificial_clause'))
    put('actions',dict(cash_amount_basis='announced_not_investor_verified',events=actions))
    bridge=put('action_bridge',dict(date_only_event_bridge=joins))
    put('action_review',dict(status='accepted_existing_metadata_bridge_for_future_conditional_input_only',bridge=bridge))
    taxref=put('tax_evidence',dict(artifact_type='constant_mix_event_tax_evidence_v1',events=tax))
    put('tax_review',dict(status='accepted_documented_event_tax_mapping',tax_evidence_sha256=taxref['sha256'],qualified=False))
    return dict(inputs=pins,registration_sha256='a'*64,policy=dict(a.POLICY,study_number=999)),put


class ArtificialClaim:
    """No production capability; immutable test sources, explicit artificial claim."""
    def __init__(self,root,packet):
        self.root=Path(root);self.packet=packet;self.active=True;self.decoding_started=False;self.guard_count=0
        a.write_exclusive_json(self.root/a.DIRECTORY/'artificial_attempt_claim.json',dict(test_injected_claim=True,research_study_consumed=False))
    def guard(self,phase,identity):
        for pin in self.packet['inputs'].values():a.read_bound(self.root,pin)
        self.guard_count+=1
    def read(self,role):return a.read_bound(self.root,self.packet['inputs'][role],return_bytes=True)
    def begin_financial_decode(self):
        if self.decoding_started:raise ValueError('once')
        a.write_exclusive_json(self.root/a.DIRECTORY/'artificial_decode_marker.json',dict(only_artificial_values=True,research_study_consumed=False))
        self.decoding_started=True


class HistoricalTests(unittest.TestCase):
    def setUp(self):
        retained=os.environ.get('CONSTANT_MIX_ARTIFICIAL_DEMO') if self._testMethodName=='test_full_artificial_27_and_persisted_mutation' else None
        if retained:
            self.root=Path(retained).resolve();self.root.mkdir(parents=True,exist_ok=False)
        else:
            self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.packet,self.put=package(self.root)
        self.claim=ArtificialClaim(self.root,self.packet)
    def test_production_rejects_artificial_claim_before_access(self):
        with self.assertRaisesRegex(ValueError,'production claim'):h.load_claimed_inputs(self.claim)
        self.assertFalse(self.claim.decoding_started)
    def test_wire_unit_and_terminal_no_future_close(self):
        data=h._load_core(self.claim,test_values=True)
        self.assertEqual(data.fixture['bars'][h.ASSETS[0]][0]['volume'],'10000000')
        self.assertIsNone(data.fixture['bars'][h.ASSETS[0]][-1]['close'])
        self.assertEqual(data.fixture['actions'][0]['cash_per_share'],'0.01')
        self.assertFalse(data.context.returns_computed)
        self.assertTrue(data.provenance['amount_tokens_not_converted'])
    def test_unknown_tax_rejects_before_financial_marker(self):
        tax=a._json(self.claim.read('tax_evidence'));tax['events'][0]['status']='unknown'
        ref=self.put('tax_evidence',tax)
        self.put('tax_review',dict(status='accepted_documented_event_tax_mapping',tax_evidence_sha256=ref['sha256'],qualified=False))
        with self.assertRaisesRegex(ValueError,'Unknown tax'):h._load_core(self.claim,test_values=True)
        self.assertFalse(self.claim.decoding_started)
    def test_first_raw_read_failure_has_no_decode_marker(self):
        original=self.claim.read
        def read(role):
            if role=='fund_daily_510300_2013_provider_wire':raise OSError('artificial read failure')
            return original(role)
        self.claim.read=read
        with self.assertRaises(OSError):h._load_core(self.claim,test_values=True)
        self.assertFalse(self.claim.decoding_started)
    def test_first_numeric_parser_failure_is_after_marker(self):
        with mock.patch.object(h,'_wire_rows',side_effect=ValueError('artificial bad numeric')):
            with self.assertRaises(ValueError):h._load_core(self.claim,test_values=True)
        self.assertTrue(self.claim.decoding_started)
    def test_wrong_original_path_even_same_hash_is_not_aliased(self):
        source=dict(self.put('extra',dict(x='identical')));source['path']=str(self.root/'not_bound.json')
        with self.assertRaisesRegex(ValueError,'Unmapped'):h._bound_source(self.claim,source,dict(mappings=[]))
    def test_receipt_batch_link_and_exact_byte_count(self):
        meta=h._metadata(self.claim,test_values=True);request=meta['source_manifest']['requests'][0];entry=meta['source_index']['roles'][0]
        with self.assertRaisesRegex(ValueError,'batch claim'):
            h._receipt(self.claim,request,entry,meta['relocations'],test_values=True,batch_claim={})
        receipt_role=request['role']+'_receipt';receipt=a._json(self.claim.read(receipt_role));receipt['received_bytes']-=1
        updated=self.put(receipt_role,receipt);entry=copy.deepcopy(entry);entry['receipt']=updated
        with self.assertRaisesRegex(ValueError,'receipt'):
            h._receipt(self.claim,request,entry,meta['relocations'],test_values=True,batch_claim=meta['source_outcome']['batch_claim'])
        self.assertFalse(self.claim.decoding_started)
    def test_numeric_invalid_missing_and_duplicate_rows(self):
        request=a._json(self.claim.read('source_manifest'))['requests'][0]
        raw=a._json(self.claim.read(request['role']))
        for change in ('duplicate','missing','negative'):
            x=copy.deepcopy(raw)
            if change=='duplicate':x['data']['items'][1]=x['data']['items'][0]
            if change=='missing':x['data']['items'].pop()
            if change=='negative':x['data']['items'][0][6]='-1'
            with self.subTest(change=change),self.assertRaises(ValueError):h._wire_rows(json.dumps(x).encode(),request)
    def test_full_artificial_27_and_persisted_mutation(self):
        data=h._load_core(self.claim,test_values=True);result=h._run_loaded(self.claim,data)
        self.assertEqual(len(result['accounts']),27);self.assertFalse(result['historical_returns_computed'])
        self.assertTrue(result['test_injected_values']);self.assertTrue(all(result['same_actual_initial_baskets'].values()))
        stats=a._json((self.root/result['statistics']['path']).read_bytes())
        self.assertEqual((stats['N'],stats['replications'],len(stats['endpoint_keys'])),(10,5000,18))
        a.write_exclusive_json(self.root/a.DIRECTORY/'result.json',result)
        snapshot=self.root/result['decoded_input_artifact']['path'];original=snapshot.read_bytes()
        try:
            snapshot.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'Frozen file changed'):a._final_artifacts(self.root,result)
        finally:snapshot.write_bytes(original)
        a._final_artifacts(self.root,result)
    def test_loaded_mutation_blocked_before_first_account(self):
        data=h._load_core(self.claim,test_values=True);data.fixture['bars'][h.ASSETS[0]][0]['open']='9'
        with self.assertRaisesRegex(ValueError,'Loaded financial snapshot'):h._run_loaded(self.claim,data)
        self.assertFalse((self.root/a.DIRECTORY/'accounts').exists())


class PersistenceAnchorTests(unittest.TestCase):
    def test_prewrite_bytes_anchor_rejects_same_length_replacement_and_accepts_unicode(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();value={'cash':'10000','synthetic':True,'unit':'份'}
            good=root/'good.json';artifact=h._persist(root,good,value)
            expected=h._persisted_json_bytes(value)
            self.assertEqual(good.read_bytes(),expected)
            self.assertEqual(artifact['sha256'],a.digest(expected))
            self.assertEqual(artifact['bytes'],len(expected))
            real_writer=a.write_exclusive_json
            def replaced(path,payload):
                real_writer(path,payload)
                changed=dict(payload,cash='00000')
                replacement=h._persisted_json_bytes(changed)
                self.assertEqual(len(replacement),len(expected))
                Path(path).write_bytes(replacement)
            bad=root/'bad.json'
            with mock.patch.object(a,'write_exclusive_json',side_effect=replaced):
                with self.assertRaisesRegex(ValueError,'pre-write intent'):
                    h._persist(root,bad,value)
            self.assertNotEqual(bad.read_bytes(),expected)
            self.assertEqual(value['cash'],'10000')


if __name__=='__main__':unittest.main()
