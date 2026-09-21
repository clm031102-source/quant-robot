from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_execution_evidence import validate_execution_supplement, load_execution_supplement
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from tests.unit.test_offline_dividends import dividend_policy, extended_policy, start
from tests.unit.test_offline_conversions import conversion_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context, intent


def supplement(evidence):
    row=next(row for row in evidence['events'] if row['event']['kind'] in {'FILL','CONVERSION_UNAPPLIED_FILL'})
    snapshot=evidence['snapshot'];data=row['event']['data']
    return {'schema_version':1,'mode':'offline_fixture_only',
        'journal':{'genesis_hash':evidence['events'][0]['event_hash'],'sequence':snapshot['sequence'],'hash':snapshot['journal_hash']},
        'records':[{'evidence_id':'e1','receipt':{'sequence':row['sequence'],'event_hash':row['event_hash'],
            'order_id':data['order_id'],'fill_id':data['fill_id']},'operation':'execution',
            'source':{'source_id':'synthetic','series_id':'series1','message_id':'message1','revision':0,
                'previous_evidence_id':None,'claimed_artifact_sha256':'a'*64},
            'observed_at':'2026-09-15T09:10:00+08:00',
            'execution':{'executed_at':'2026-09-14T14:30:00+08:00','quantity':40,'price':'4',
                'quantity_basis':'unknown','price_basis':'unknown','basis_event_id':None}}]}


class OfflineExecutionEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.path=self.root/'book.sqlite'
        with OfflineOrderJournal.create(self.path,initial_cash='3000',initial_positions={},commission_bps='.5',minimum_commission='5') as book:
            book.register(order_id='one',idempotency_key='one',symbol='510300.SH',side='BUY',quantity=100,limit_price='4')
            book.fill('one','fill1',40,'4')
        self.view=OfflineOrderJournal.inspect_evidence(self.path);self.packet=supplement(self.view)

    def validate(self,packet=None):return validate_execution_supplement(self.packet if packet is None else packet,self.view)

    def test_valid_binding_preserves_assertions_without_authenticating_or_upgrading(self):
        before=self.path.read_bytes();original=deepcopy(self.packet)
        result=self.validate()
        self.assertTrue(result['journal_and_receipt_binding_verified'])
        self.assertFalse(result['source_authenticated']);self.assertFalse(result['execution_attribution_confirmed'])
        self.assertEqual(result['records'][0]['assertion'],original['records'][0])
        self.assertIn('quantity_basis_unknown',result['records'][0]['unresolved'])
        self.assertIn('authoritative_entitlement_and_settlement_evidence',result['unresolved'])
        result['records'][0]['assertion']['execution']['quantity']=99
        self.assertEqual(self.packet,original);self.assertEqual(self.path.read_bytes(),before)

    def test_stale_or_different_journal_and_wrong_receipt_are_rejected(self):
        for section,key,value in [('journal','sequence',999),('journal','hash','f'*64),('journal','genesis_hash','f'*64),
                ('receipt','sequence',1),('receipt','event_hash','f'*64),('receipt','order_id','other'),('receipt','fill_id','other')]:
            packet=deepcopy(self.packet);target=packet['journal'] if section=='journal' else packet['records'][0]['receipt'];target[key]=value
            with self.subTest(section=section,key=key),self.assertRaises(ValueError):self.validate(packet)

    def test_unknown_execution_fields_stay_unknown(self):
        row=self.packet['records'][0];row['execution'].update(executed_at=None,quantity=None,price=None)
        row['source']['claimed_artifact_sha256']=None
        result=self.validate()['records'][0]
        for field in ('executed_at','quantity','price'):self.assertIn(field+'_unknown',result['unresolved'])
        self.assertIsNone(result['assertion']['execution']['executed_at'])

    def test_claim_differences_are_reported_without_changing_original_fill(self):
        self.packet['records'][0]['execution'].update(quantity=20,price='8')
        result=self.validate()['records'][0]
        self.assertEqual(set(result['recorded_receipt_differences']),{'quantity','price'})
        self.assertEqual(result['recorded_receipt']['quantity'],40)
        self.assertEqual(OfflineOrderJournal.inspect_snapshot(self.path)['positions']['510300.SH'],40)

    def test_timestamps_require_explicit_offset_and_execution_cannot_follow_observation(self):
        for field,value in [('executed_at','2026-09-14T14:30:00'),('executed_at','2026-09-16T14:30:00+08:00'),
                ('executed_at','2026-09-14T14:30:00-00:00'),
                ('executed_at',123),('observed_at',None),('observed_at','2026-09-14')]:
            packet=deepcopy(self.packet);row=packet['records'][0]
            (row if field=='observed_at' else row['execution'])[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.validate(packet)

    def test_bad_numbers_units_unknown_fields_and_live_mode_are_rejected(self):
        for key,value in [('quantity',True),('quantity',0),('quantity',1.5),('price','NaN'),('price','Infinity'),
                ('price','-1'),('price',4.0),('quantity_basis','adjusted'),('price_basis','adjusted_close'),('extra',1),
                ('quantity_basis','pre_action_shares'),('quantity_basis',[]),('price_basis',{})]:
            packet=deepcopy(self.packet);packet['records'][0]['execution'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.validate(packet)
        self.packet['mode']='live'
        with self.assertRaises(ValueError):self.validate()

    def revised(self,operation='correction'):
        row=deepcopy(self.packet['records'][0]);row['evidence_id']='e2';row['operation']=operation
        row['source'].update(message_id='message2',revision=1,previous_evidence_id='e1')
        return row

    def test_complete_revision_chain_keeps_all_records_and_no_latest_wins(self):
        self.packet['records'].append(self.revised('cancel'))
        result=self.validate()
        self.assertEqual(len(result['records']),2)
        self.assertIn('revision_requires_source_review',result['records'][1]['unresolved'])
        self.assertFalse(result['automatic_correction_allowed'])
        self.assertNotIn('effective_execution',result)

    def test_duplicate_dangling_forked_or_cross_series_revisions_are_rejected(self):
        revised=self.revised()
        cases=[]
        cases.append([deepcopy(self.packet['records'][0])]*2)
        cases.append([revised])
        branch=deepcopy(revised);branch['evidence_id']='e3';branch['source']['message_id']='message3'
        cases.append([self.packet['records'][0],revised,branch])
        wrong=deepcopy(revised);wrong['source']['series_id']='other'
        cases.append([self.packet['records'][0],wrong])
        wrong=deepcopy(revised);wrong['source']['revision']=2
        cases.append([self.packet['records'][0],wrong])
        for rows in cases:
            packet=deepcopy(self.packet);packet['records']=rows
            with self.subTest(rows=len(rows)),self.assertRaises(ValueError):self.validate(packet)

    def test_basis_action_must_exist_for_the_receipt_symbol(self):
        self.packet['records'][0]['execution'].update(quantity_basis='pre_action_shares',basis_event_id='invented')
        with self.assertRaisesRegex(ValueError,'basis action'):self.validate()

    def test_file_limits_duplicate_keys_and_constant_values_are_rejected(self):
        source=self.root/'source.json'
        for content in ('{"schema_version":1,"schema_version":1}', '{"x":NaN}', 'null', '['*2000+'0'+']'*2000, 'x'*1_000_001):
            source.write_text(content,encoding='utf-8')
            with self.subTest(content=content[:30]),self.assertRaises(ValueError):load_execution_supplement(source)
        self.packet['records']*=501
        with self.assertRaisesRegex(ValueError,'record limit'):self.validate()

    def test_non_scalar_operation_and_revision_time_reversal_are_rejected(self):
        revised=self.revised();revised['operation']=[];self.packet['records'].append(revised)
        with self.assertRaises(ValueError):self.validate()
        revised['operation']='correction';revised['observed_at']='2026-09-14T15:00:00+08:00'
        with self.assertRaisesRegex(ValueError,'predecessor'):self.validate()

    def test_optional_review_attachment_keeps_account_and_faults_identical(self):
        before=self.path.read_bytes();baseline=build_corporate_action_review(self.path)
        attached=build_corporate_action_review(self.path,execution_supplement=self.packet)
        self.assertEqual(attached['account'],baseline['account'])
        self.assertTrue(attached['execution_supplement']['journal_and_receipt_binding_verified'])
        self.assertFalse(attached['clears_faults']);self.assertEqual(self.path.read_bytes(),before)
        self.assertIsNone(baseline['execution_supplement'])

    def test_empty_supplement_does_not_imply_execution_completeness(self):
        self.packet['records']=[];result=self.validate()
        self.assertEqual(result['records'],[]);self.assertFalse(result['source_authenticated'])
        self.assertIn('execution_evidence_completeness_not_certified',result['unresolved'])

    def action_book(self,kind):
        path=self.root/(kind+'.sqlite')
        options={'dividend_policy':dividend_policy()} if kind=='dividend' else {'conversion_policy':conversion_policy()}
        book=OfflineOrderJournal.create(path,initial_cash='2600',initial_positions={SYMBOL:100},
            commission_bps='.5',minimum_commission='5',admission_policy=extended_policy(),**options)
        self.addCleanup(book.close);start(book,NOW)
        book.admit(intent(),context(book),clock=lambda:NOW);book.report_status('one','cancel','CANCELLED',0)
        return path,book

    def test_old_unit_assertion_does_not_apply_quarantined_conversion_fill(self):
        path,book=self.action_book('conversion')
        book.record_conversion_entitlements(clock=lambda:NOW.replace(hour=15))
        book.apply_share_conversions(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
        book.fill('one','late',40,'4');before=book.snapshot()
        packet=supplement(OfflineOrderJournal.inspect_evidence(path))
        packet['records'][0]['execution'].update(quantity_basis='pre_action_shares',price_basis='raw_execution',basis_event_id='merge-one')
        review=build_corporate_action_review(path,execution_supplement=packet)
        action=review['actions'][0]
        self.assertEqual(action['captured_entitlement']['quantity'],100)
        self.assertEqual(review['account']['positions'][SYMBOL],50)
        self.assertEqual(len(review['unapplied_fills']),1)
        self.assertFalse(action['candidate_receipts'][0]['execution_attribution_confirmed'])
        self.assertEqual(book.snapshot(),before)

    def test_post_record_date_assertion_does_not_change_paid_dividend_or_candidate(self):
        path,book=self.action_book('dividend')
        book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15))
        book.accrue_dividends(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
        book.record_dividend_cash_credit('div-one','paid','60',clock=lambda:NOW+timedelta(days=2))
        book.fill('one','late',40,'4');before=book.snapshot()
        packet=supplement(OfflineOrderJournal.inspect_evidence(path))
        packet['records'][0]['execution']['executed_at']='2026-09-15T09:05:00+08:00'
        review=build_corporate_action_review(path,execution_supplement=packet);action=review['actions'][0]
        self.assertTrue(action['paid']);self.assertIsNone(action['receivable'])
        self.assertEqual(action['captured_entitlement']['quantity'],100)
        self.assertEqual(len(action['candidate_receipts']),1)
        self.assertIsNone(action['candidate_receipts'][0]['actual_execution_at'])
        self.assertEqual(review['account']['cash'],before['cash']);self.assertEqual(book.snapshot(),before)


if __name__=='__main__':unittest.main()
