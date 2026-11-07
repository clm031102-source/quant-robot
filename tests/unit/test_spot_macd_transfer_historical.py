"""Invented values in exact native/archive schema, including actual-date shape.

These are not retained financial originals. Temporary admission explicitly
injects an artificial-only validator; real admission rejects that source class.
"""
import calendar
from dataclasses import replace
from datetime import date,timedelta
from decimal import Decimal,getcontext
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from zipfile import ZipFile,ZIP_DEFLATED

from quant_robot.research import spot_macd_transfer as m
from quant_robot.research import spot_macd_transfer_admission as a
from quant_robot.research import spot_macd_transfer_historical as h
from tests.unit.test_spot_macd_transfer_admission import ArtificialPackage


def invented_price(day):
    phase=(day-date(2018,1,1)).days%60
    return str(100+min(phase,60-phase))


def native(first,last):
    rows=[]; day=first
    while day<=last:
        p=invented_price(day);v='100000'
        rows.append([h._ms(day),p,str(int(p)+1),str(int(p)-1),p,v,h._ms(day)+h.DAY_MS-1,'opaque_unused_quote_volume',0,'opaque_unused','opaque_unused','0'])
        day+=timedelta(days=1)
    value={'result':rows}
    return a.canonical(dict(content=[dict(type='text',text=json.dumps(value))],isError=False,structuredContent=value))


def archive(month, *, mutate=None, header=False):
    y,mn=map(int,month.split('-'));first=date(y,mn,1);count=calendar.monthrange(y,mn)[1]*1440
    name=f'BTCUSDT-1m-{month}.csv';out=io.BytesIO()
    with ZipFile(out,'w',compression=ZIP_DEFLATED,compresslevel=1) as z:
        with z.open(name,'w') as f:
            if header:f.write((','.join(h.ARCHIVE_COLUMNS)+'\n').encode())
            for i in range(count):
                stamp=h._ms(first)+i*h.MINUTE_MS;day=first+timedelta(days=i//1440)
                # Poison all unapproved numeric tokens. Target open/volume are
                # the only financially interpreted fields in this adapter.
                row=[str(stamp),'NOT_APPROVED','NOT_APPROVED','NOT_APPROVED','NOT_APPROVED','NOT_APPROVED',str(stamp+59999),'NOT_APPROVED','0','NOT_APPROVED','NOT_APPROVED','0']
                if i%1440==3 and h.EXEC_FIRST<=day<=h.EXEC_LAST:
                    row[1]=invented_price(day-timedelta(days=1));row[5]='100000'
                if mutate:row=mutate(i,row)
                if row is None:continue
                f.write((','.join(row)+'\n').encode())
    raw=out.getvalue();checksum=(a.digest(raw)+'  '+name[:-4]+'.zip\n').encode()
    return raw,checksum


def full_payloads():
    result={}
    ranges=[(date(2018,1,1),date(2018,1,1)),(date(2018,1,2),date(2018,12,31))]+[(date(y,1,1),date(y,12,31)) for y in range(2019,2024)]+[(date(2024,1,1),date(2024,1,1))]
    for i,(first,last) in enumerate(ranges):result[f'daily_{i}']=native(first,last)
    for y in range(2019,2025):
        for month in range(1,13):
            if (y,month)>(2024,1):break
            key=f'minute_{y}-{month:02}';result[key],result[key+'_checksum']=archive(f'{y}-{month:02}')
    return result


class AdapterTests(unittest.TestCase):
    def test_native_both_wrappers_types_mirror_clock_and_numeric_failures(self):
        raw=native(date(2018,1,1),date(2018,1,1));r=h._daily(raw,'2018-01-01','2018-01-01')
        self.assertEqual(r[0]['date'],'2018-01-01');self.assertEqual(r[0]['close'],'100')
        value=json.loads(raw);value['content'][0]['text']=json.dumps(value['structuredContent']['result'])
        with self.assertRaisesRegex(ValueError,'mirrors'):h._daily(a.canonical(value),'2018-01-01','2018-01-01')
        for index,value in ((0,'1514764800000'),(6,1),(1,'NaN'),(5,'-1')):
            obj=json.loads(raw);obj['structuredContent']['result'][0][index]=value
            obj['content'][0]['text']=json.dumps(obj['structuredContent'])
            with self.assertRaises((ValueError,ArithmeticError)):h._daily(a.canonical(obj),'2018-01-01','2018-01-01')
        obj=json.loads(raw);obj['structuredContent']['result'][0][1]='101'
        with self.assertRaisesRegex(ValueError,'mirrors'):h._daily(a.canonical(obj),'2018-01-01','2018-01-01')

    def test_archive_target_projection_and_clock_gap_checksum(self):
        raw,checksum=archive('2019-01');rows,coverage=h._archive_targets(raw,checksum,'2019-01')
        self.assertEqual(len(rows),30);self.assertEqual(rows[0]['date'],'2019-01-02')
        self.assertEqual(coverage['rows'],44640);self.assertFalse(coverage['other_financial_tokens_used'])
        with self.assertRaisesRegex(ValueError,'checksum'):h._archive_targets(raw+b'drift',checksum,'2019-01')
        def duplicate(i,row):
            if i==20:row[0]=str(int(row[0])-60000)
            return row
        raw,checksum=archive('2019-01',mutate=duplicate)
        with self.assertRaisesRegex(ValueError,'duplicate'):h._archive_targets(raw,checksum,'2019-01')

    def test_sparse_nontarget_and_postterminal_minutes_do_not_change_target_coverage(self):
        def only_targets(i,row):return row if i%1440==3 and i//1440<2 else None
        raw,checksum=archive('2024-01',mutate=only_targets,header=True)
        rows,coverage=h._archive_targets(raw,checksum,'2024-01')
        self.assertEqual([r['date'] for r in rows],['2024-01-01','2024-01-02'])
        self.assertEqual(coverage['rows'],2);self.assertTrue(coverage['header_present'])
        self.assertFalse(coverage['full_month_minute_contiguity_verified'])

    def test_missing_target_duplicate_target_or_repeated_header_fail(self):
        raw,checksum=archive('2024-01',mutate=lambda i,r:None if i==1443 else r)
        with self.assertRaisesRegex(ValueError,'target minute missing'):h._archive_targets(raw,checksum,'2024-01')
        def repeated(i,row):
            if i==4:row[0]=str(int(row[0])-60000)
            return row
        raw,checksum=archive('2024-01',mutate=repeated)
        with self.assertRaisesRegex(ValueError,'duplicate'):h._archive_targets(raw,checksum,'2024-01')
        raw,checksum=archive('2024-01',mutate=lambda i,r:list(h.ARCHIVE_COLUMNS) if i==10 else r,header=True)
        with self.assertRaisesRegex(ValueError,'header'):h._archive_targets(raw,checksum,'2024-01')

    def test_final_month_does_not_numerically_decode_post_terminal_open(self):
        raw,checksum=archive('2024-01')
        rows,coverage=h._archive_targets(raw,checksum,'2024-01')
        self.assertEqual([r['date'] for r in rows],['2024-01-01','2024-01-02'])
        self.assertEqual(coverage['rows'],44640)

    def test_mutable_normalized_dict_and_artificial_public_guard(self):
        f=dict(artifact_type='claimed_spot_transfer_normalized_input_v1',asset_id='BTCUSDT',daily=[])
        loaded=h.LoadedHistory(f,{},a.digest(a.canonical(dict(fixture=f,provenance={}))))
        loaded.verify();f['daily'].append({'close':'999'})
        with self.assertRaisesRegex(ValueError,'in-memory'):loaded.verify()
        with self.assertRaises(ValueError):m.run_account(f)

    def test_receipt_jsonl_upper_bound_is_not_relabelled_received(self):
        fake=object.__new__(a._Claim);fake.active=True
        fake.packet={'inputs':{'receipt':{'path':'artificial.jsonl','sha256':'a'*64}}}
        fake.read=lambda role:b'{"ignored":true}\n{"completed_at":"2025-02-01T00:00:00Z"}\n'
        result=h._receipt_evidence(fake,dict(receipt_role='receipt',received_at_path=['completed_at'],
            receipt_line_1based=2,receipt_clock_kind='source_capture_completed_at'))
        self.assertFalse(result['exact_body_received_at_verified']);self.assertNotIn('actual_received_at',result)
        self.assertEqual(result['clock_kind'],'source_capture_completed_at')
        self.assertTrue(result['local_capture_completion_upper_bound'])
        tool=h._receipt_evidence(fake,dict(receipt_role='receipt',received_at_path=['completed_at'],
            receipt_line_1based=2,receipt_clock_kind='tool_return_received_at'))
        self.assertTrue(tool['tool_return_received_at_verified']);self.assertFalse(tool['exact_body_received_at_verified'])
        self.assertFalse(tool['historical_first_publication_verified'])


class ControllerTests(unittest.TestCase):
    def test_calculated_account_after_guard_failure_is_not_reported_as_zero_calculations(self):
        f=ArtificialPackage();self.addCleanup(f.close)
        rows=h._daily(native(h.FIRST,h.LAST),h.FIRST.isoformat(),h.LAST.isoformat())
        minutes=[]
        for i in range(1827):
            day=(h.EXEC_FIRST+timedelta(days=i)).isoformat()
            minutes.append(dict(date=day,open_time=day+'T00:03:00Z',close_time=day+'T00:03:59.999Z',
                open=rows[365+i]['close'],volume='100000'))
        fixture=dict(artifact_type='claimed_spot_transfer_normalized_input_v1',asset_id='BTCUSDT',market='spot',
            source_nature='artificial_protocol_fixture',warmup_days=366,daily=rows,execution=minutes)
        provenance=dict(source_nature='artificial_protocol_fixture',model_assumptions=['artificial_test_loader_injection'])
        loaded=h.LoadedHistory(fixture,provenance,a.digest(a.canonical(dict(fixture=fixture,provenance=provenance))))
        def artificial_loader(claim):claim.begin_financial_decode();return loaded
        original=a._Claim.guard
        def fail_after(claim,phase,identity):
            if phase=='after' and identity=='fee5_slip0/strategy':raise ValueError('artificial after-account guard failure')
            return original(claim,phase,identity)
        with patch.object(h,'load_claimed_inputs',side_effect=artificial_loader),patch.object(a._Claim,'guard',fail_after):
            with self.assertRaisesRegex(ValueError,'after-account guard'):f.execute()
        folder=f.root/a.DIRECTORY;out=json.loads((folder/'outcome.json').read_bytes())
        self.assertEqual(out['model_accounts_calculated'],1);self.assertEqual(out['model_accounts_completed'],0)
        self.assertTrue((folder/'accounts/fee5_slip0/strategy/complete.json').exists())
        self.assertTrue((folder/'accounts/fee5_slip0/strategy/failed.json').exists())
        self.assertFalse(out['historical_returns_computed']);self.assertFalse(out['full_fixed_27_completed'])
        self.assertFalse((folder/'result.json').exists())

    def test_first_original_read_failure_reserves_attempt_before_parse_marker(self):
        f=ArtificialPackage();self.addCleanup(f.close)
        original=a._Claim.read
        def read(claim,role):
            if role=='daily_0':raise OSError('artificial first raw read unavailable')
            return original(claim,role)
        with patch.object(a._Claim,'read',read),self.assertRaisesRegex(OSError,'first raw read'):f.execute()
        folder=f.root/a.DIRECTORY
        self.assertTrue((folder/'attempt_claim.json').exists())
        self.assertFalse((folder/'financial_decode_started.json').exists())
        out=json.loads((folder/'outcome.json').read_bytes())
        self.assertFalse(out['numerical_decode_started']);self.assertFalse(out['research_study_consumed'])
        with self.assertRaisesRegex(ValueError,'reserved or consumed'):f.execute()

    def test_source_shape_failure_consumed_after_marker_without_any_account(self):
        f=ArtificialPackage();self.addCleanup(f.close)
        with self.assertRaisesRegex(ValueError,'native outer'):f.execute()
        folder=f.root/a.DIRECTORY
        self.assertTrue((folder/'attempt_claim.json').exists());self.assertTrue((folder/'financial_decode_started.json').exists())
        self.assertFalse((folder/'accounts').exists())
        out=json.loads((folder/'outcome.json').read_bytes());self.assertFalse(out['research_study_consumed'])
        self.assertTrue(out['numerical_decode_started'])

    def test_full_invented_raw_loader_to_27_accounts_statistics_and_final_tamper(self):
        f=ArtificialPackage(full_payloads());self.addCleanup(f.close)
        before=m.context_record(getcontext())
        outcome=f.execute();self.assertEqual(outcome['status'],'completed')
        self.assertFalse(outcome['historical_returns_computed']);self.assertFalse(outcome['research_study_consumed'])
        self.assertEqual(outcome['model_accounts_completed'],27);self.assertEqual(before,m.context_record(getcontext()))
        folder=f.root/a.DIRECTORY;result=json.loads((folder/'result.json').read_bytes())
        self.assertEqual(result['evidence_class'],'artificial_historical_adapter_test')
        self.assertEqual(result['source_nature'],'artificial_protocol_fixture');self.assertFalse(result['qualified'])
        self.assertEqual(result['bootstrap']['N'],1827);self.assertEqual(len(result['bootstrap']['endpoint_keys']),18)
        decoded=json.loads((folder/'decoded_input.json').read_bytes())
        self.assertEqual(decoded['fixture']['daily'][0]['date'],'2018-01-01')
        self.assertEqual(decoded['fixture']['execution'][-1]['date'],'2024-01-02')
        self.assertNotIn('fixture_sha256',result)
        sample=json.loads((folder/'accounts/fee10_slip10/holding/complete.json').read_bytes())
        self.assertGreater(sample['summary']['fill_count'],0)
        self.assertTrue(sample['summary']['account_reconciled']);self.assertFalse(sample['historical_returns_computed'])
        fake=object.__new__(a._Claim);fake.root=f.root
        h.verify_final_artifacts(fake,result)
        path=folder/'accounts/fee5_slip0/cash/complete.json';raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'Bound file changed'):h.verify_final_artifacts(fake,result)
        path.write_bytes(raw)
        decoded['fixture']['daily'][0]['close']='999';f.write(a.DIRECTORY+'/decoded_input.json',a.canonical(decoded))
        result['decoded_input_artifact']=f.ref(a.DIRECTORY+'/decoded_input.json')
        with self.assertRaisesRegex(ValueError,'canonical evidence'):h.verify_final_artifacts(fake,result)


if __name__=='__main__':unittest.main()
