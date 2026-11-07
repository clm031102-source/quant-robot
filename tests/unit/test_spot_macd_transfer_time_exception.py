"""Artificial carriers and test-injected hashes; no retained market values."""
from contextlib import ExitStack
from datetime import date,timedelta
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile,ZIP_DEFLATED

from quant_robot.research import spot_macd_transfer_time_exception as x
from quant_robot.research import spot_macd_transfer_historical as h
from quant_robot.research import spot_macd_transfer_admission as a


NAMES=('economic_contract','economic_method_text','original_source_plan','root_decision','old_failed_outcome',
       'native','native_capture','native_failed_receipt','archive','checksum','archive_receipt','time_outcome',
       'time_independent_review','token_scope','token_result','token_implementation')


def carrier_row(day, *, native=False):
    stamp=x._time(day)
    return [stamp,'100.00','101.00','99.00','100.00','100000.00',
        x.NATIVE_CLOSE if native and stamp==x.OPEN else stamp+x.DAY-1,
        '10000000.00',42,'50000.00','5000000.00','0']


class ArtificialProofPackage:
    def __init__(self, *, native_mutator=None, archive_mutator=None, mirror_mutator=None):
        self.stack=ExitStack();self.root=Path(self.stack.enter_context(TemporaryDirectory()))
        rows=[carrier_row(date(2018,1,2)+timedelta(days=i),native=True) for i in range(364)]
        if native_mutator:native_mutator(rows)
        left={'result':rows};right=json.loads(json.dumps(left))
        if mirror_mutator:mirror_mutator(right)
        self.native=a.canonical(dict(content=[dict(type='text',text=json.dumps(left))],isError=False,structuredContent=right))
        archive_rows=[[str(v).encode() for v in carrier_row(date(2018,2,1)+timedelta(days=i))] for i in range(28)]
        if archive_mutator:archive_mutator(archive_rows)
        buf=io.BytesIO()
        with ZipFile(buf,'w',compression=ZIP_DEFLATED) as z:
            z.writestr('BTCUSDT-1d-2018-02.csv',b'\n'.join(b','.join(row) for row in archive_rows)+b'\n')
        self.archive=buf.getvalue();self.checksum=(x._sha(self.archive)+'  BTCUSDT-1d-2018-02.zip\n').encode()
        self.pins={};authority={}
        for name in NAMES:
            raw={'native':self.native,'archive':self.archive,'checksum':self.checksum}.get(name,('artificial_'+name).encode())
            role='daily_2018_reuse' if name=='native' else name
            path=name+'.bin';(self.root/path).write_bytes(raw)
            self.pins[role]={'path':path,'sha256':x._sha(raw)}
            authority[name]={'path':path,'sha256':x._sha(raw),'bytes':len(raw)}
        self.addendum=a.canonical(dict(policy_id=x.POLICY_ID,authority=authority,economic_invariants={'method_sha256':a.METHOD_SHA}))
        (self.root/'addendum.json').write_bytes(self.addendum)
        (self.root/'root_review.json').write_bytes(b'artificial root source review')
        self.pins['addendum']={'path':'addendum.json','sha256':x._sha(self.addendum)}
        self.pins['source_root_review']={'path':'root_review.json','sha256':x._sha(b'artificial root source review')}
        self.policy=dict(policy_id=x.POLICY_ID,addendum_role='addendum',root_review_role='source_root_review',
            authority_roles={k:'daily_2018_reuse' if k=='native' else k for k in NAMES})
        for module,name,value in [(x,'NATIVE_SHA',x._sha(self.native)),(x,'ARCHIVE_SHA',x._sha(self.archive)),
            (x,'CHECKSUM_SHA',x._sha(self.checksum)),(x,'ADDENDUM_SHA',x._sha(self.addendum)),
            (x,'ROOT_REVIEW_SHA',self.pins['source_root_review']['sha256']),
            (a,'SOURCE_SCHEMA_SHA',x._sha(self.addendum)),(a,'SOURCE_SCHEMA_REVIEW_SHA',self.pins['source_root_review']['sha256'])]:
            self.stack.enter_context(patch.object(module,name,value))
        self.claim=object.__new__(a._Claim)
        self.claim.root=self.root;self.claim.active=True;self.claim.decoding_started=False
        self.claim.claim_hash='b'*64;self.claim.source_nature='artificial_protocol_fixture'
        self.claim.packet={'inputs':self.pins,'registration_sha256':'a'*64}
        self.claim.manifest={'source_schema_policy':self.policy,'daily_sources':[{'role':'unneeded_first_day'},{'role':'daily_2018_reuse'}]}
        self.guards=[];self.claim.guard=lambda phase,identity:self.guards.append((phase,identity))
        self.claim.read=lambda role:a.read_bound(self.root,self.pins[role],return_bytes=True)

    def close(self):self.stack.close()
    def proof(self):return x.prepare_claimed_exception(self.claim)


class TimeExceptionTests(unittest.TestCase):
    def package(self,**kwargs):
        f=ArtificialProofPackage(**kwargs);self.addCleanup(f.close);return f

    def test_exact_proof_preserves_native_economics_both_clocks_and_strict_default(self):
        f=self.package();proof=f.proof()
        with self.assertRaisesRegex(ValueError,'clock'):h._daily(f.native,'2018-01-02','2018-12-31')
        rows=h._daily(f.native,'2018-01-02','2018-12-31',source_time_exception=proof)
        selected=next(r for r in rows if r['date']=='2018-02-08')
        self.assertEqual(selected,dict(date='2018-02-08',open='100.00',high='101.00',low='99.00',close='100.00',volume='100000.00'))
        p=proof.provenance()
        self.assertEqual((p['original_native_close_time_ms'],p['original_archive_close_time_ms']),(1518049694788,1518134399999))
        self.assertEqual(p['non_time_exact_equal_count'],10);self.assertEqual(p['equality_financial_numeric_conversions'],0)
        self.assertEqual(p['source_nature'],'artificial_protocol_fixture');self.assertEqual(p['original_phase2_status'],'failed_consumed')
        self.assertFalse(p['historical_first_publication_verified']);self.assertFalse(p['economic_fields_replaced'])
        self.assertEqual(len(self.guards if hasattr(self,'guards') else f.guards),2)
        self.assertFalse(f.claim.decoding_started)

    def test_no_boolean_wrong_carrier_range_and_claim_are_rejected(self):
        f=self.package();proof=f.proof()
        with self.assertRaisesRegex(ValueError,'proof'):h._daily(f.native,'2018-01-02','2018-12-31',source_time_exception=True)
        with self.assertRaisesRegex(ValueError,'source/range'):h._daily(f.native+b' ','2018-01-02','2018-12-31',source_time_exception=proof)
        with self.assertRaisesRegex(ValueError,'source/range'):h._daily(f.native,'2018-01-03','2019-01-01',source_time_exception=proof)
        f.claim.claim_hash='c'*64
        with self.assertRaisesRegex(ValueError,'different claim'):proof.validate_claim(f.claim)
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            x._prove_bytes(f.native+b' ',f.archive,f.checksum,f.addendum,registration_sha256='a'*64,
                claim_sha256='b'*64,source_nature='artificial_protocol_fixture',bound_refs={})

    def test_all_ten_opaque_payloads_including_integer_spelling_must_match(self):
        for k in x.INDICES:
            with self.subTest(field=k):
                def change(rows):rows[7][k]=b'042' if k==8 else rows[7][k]+b'0'
                f=self.package(archive_mutator=change)
                with self.assertRaisesRegex(ValueError,'ten non-time'):f.proof()
                f.close()

    def test_type_or_literal_mirror_conflict_and_any_new_date_exception_rejected(self):
        f=self.package(mirror_mutator=lambda obj:obj['result'][37].__setitem__(8,'42'))
        with self.assertRaisesRegex(ValueError,'mirrors'):f.proof()
        f.close()
        f=self.package(native_mutator=lambda rows:rows[38].__setitem__(6,x.NATIVE_CLOSE))
        with self.assertRaisesRegex(ValueError,'Unapproved native close'):f.proof()
        f.close()
        f=self.package(native_mutator=lambda rows:rows[37].__setitem__(6,x.ARCHIVE_CLOSE))
        with self.assertRaisesRegex(ValueError,'Unapproved native close'):f.proof()

    def test_archive_order_missing_row_and_changed_target_close_rejected(self):
        for change in (lambda rows:rows.pop(0),lambda rows:rows.__setitem__(1,rows[0]),lambda rows:rows[7].__setitem__(6,b'1518134399998')):
            f=self.package(archive_mutator=change)
            with self.assertRaisesRegex(ValueError,'Archive date|Exact28'):f.proof()
            f.close()

    def test_metadata_policy_exact_roles_and_hashes_without_helper_import(self):
        f=self.package();a.validate_source_schema_policy(f.root,f.claim.manifest,f.pins)
        policy=f.claim.manifest['source_schema_policy']
        for name,new in [('policy_id','some_other_exception'),('addendum_role','native_capture')]:
            old=policy[name];policy[name]=new
            with self.assertRaises(ValueError):a.validate_source_schema_policy(f.root,f.claim.manifest,f.pins)
            policy[name]=old
        old=policy['authority_roles']['native'];policy['authority_roles']['native']='archive'
        with self.assertRaises(ValueError):a.validate_source_schema_policy(f.root,f.claim.manifest,f.pins)
        policy['authority_roles']['native']=old
        raw=(f.root/'native.bin').read_bytes();(f.root/'native.bin').write_bytes(raw+b' ')
        with self.assertRaises(ValueError):a.validate_source_schema_policy(f.root,f.claim.manifest,f.pins)
        a.validate_source_schema_policy(f.root,{},f.pins)
        with self.assertRaises(ValueError):a.validate_source_schema_policy(f.root,{'source_schema_policy':None},f.pins)

    def test_controller_passes_verified_proof_and_default_does_not_construct_it(self):
        f=self.package();proof=f.proof()
        with patch.object(x,'prepare_claimed_exception',return_value=proof) as prepare,patch.object(h,'load_claimed_inputs',side_effect=ValueError('artificial stop before decoder')) as load,patch('quant_robot.research.spot_macd_transfer._run_prepared') as ledger:
            with self.assertRaisesRegex(ValueError,'artificial stop'):h.run_claimed_diagnostic(f.claim)
            prepare.assert_called_once_with(f.claim);load.assert_called_once_with(f.claim,source_time_exception=proof);ledger.assert_not_called()
        f.claim.manifest.pop('source_schema_policy')
        with patch.object(x,'prepare_claimed_exception') as prepare,patch.object(h,'load_claimed_inputs',side_effect=ValueError('strict path stop')) as load,patch('quant_robot.research.spot_macd_transfer._run_prepared') as ledger:
            with self.assertRaisesRegex(ValueError,'strict path'):h.run_claimed_diagnostic(f.claim)
            prepare.assert_not_called();load.assert_called_once_with(f.claim);ledger.assert_not_called()

    def test_old_daily_strict_path_normal_row_output_unchanged(self):
        row=carrier_row(date(2018,1,1));value={'result':[row]}
        raw=a.canonical(dict(content=[dict(type='text',text=json.dumps(value))],structuredContent=value,isError=False))
        expected=[dict(date='2018-01-01',open='100.00',high='101.00',low='99.00',close='100.00',volume='100000.00')]
        self.assertEqual(h._daily(raw,'2018-01-01','2018-01-01'),expected)
        self.assertEqual(h._daily(raw,'2018-01-01','2018-01-01',source_time_exception=None),expected)


if __name__=='__main__':unittest.main()
