"""Synthetic source contracts; actual retained PDF is separately reviewed locally."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.ops.paper_source_bundle import EvidenceContext, BundleError
from quant_robot.ops import sse_annual_report_inputs as annual


def sections():
    return {1:annual.TITLE+'\n送出日期：2025年3月31日',
        2:'本报告期自2024年1月1日起至12月31日止。',
        5:'基金名称'+annual.FUND+' 基金主代码518880 基金运作方式交易型开放式 '
          '基金份额上市的证券交易所上海证券交易所 上市日期2013年7月29日',
        15:'4.8 管理人对报告期内基金利润分配情况的说明 本报告期不进行收益分配。 4.9 下一节',
        52:'本报告期基金拆分变动份额 - 本报告期期末基金份额总额'}


class AnnualSourceTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.scope=self.save('scope.json',dict(stage='fixed_geopolitical_account_source_preparation',
                                              evidence_class='synthetic_only'))
        self.pdf=self.save('annual.pdf',b'%PDF-1.7 explicit synthetic fixture only')
        row=dict(TITLE=annual.TITLE,SECURITY_CODE='518880',SSEDATE='2025-03-31',
                 URL=annual.REPORT_URL.removeprefix('https://www.sse.com.cn'))
        self.catalog_body=dict(result=[row],pageHelp=dict(data=[row],pageNo=1,pageCount=1,total=1),
                               actionErrors=[],fieldErrors={})
        self.catalog=self.save('catalog.json',self.catalog_body)
        self.metadata=dict(artifact_type=annual.TYPE,created_at='2026-11-06T18:00:00Z',
            source_scope=self.scope,pdf=self.pdf,pdf_receipt=self.receipt(self.pdf,annual.REPORT_URL),
            catalog=self.catalog,catalog_receipt=self.receipt(self.catalog,'https://query.sse.com.cn/commonQuery.do'))

    def save(self,name,value):
        raw=value if isinstance(value,bytes) else json.dumps(value).encode()
        (self.root/name).write_bytes(raw)
        return dict(path=name,sha256=sha256(raw).hexdigest())

    def receipt(self,ref,base_url,**changes):
        value=dict(status='retained_current_source_version',http_status=200,url=base_url,
            path=ref['path'],sha256=ref['sha256'],bytes=len((self.root/ref['path']).read_bytes()),
            scope_sha256=self.scope['sha256'],claimed_at='2026-11-04T18:00:00+00:00',
            completed_at='2026-11-04T18:00:01+00:00')
        value.update(changes)
        return self.save(ref['path']+'.receipt.json',value)

    def parse(self,kind='identity'):
        ref=self.save('metadata.json',self.metadata)
        adapter=annual.retained_annual_adapters(reviewed_metadata_sha256=ref['sha256'])[kind]
        context=EvidenceContext(self.root,component=kind)
        with patch.object(annual,'_extract_pdf',return_value=(sections(),'synthetic-parser')) as extractor:
            result=adapter.parse(context,ref)
            extractor.assert_called_once_with((self.root/'annual.pdf').read_bytes())
        return result,context

    def test_identity_and_no_action_coverage_come_from_original_sections(self):
        identity,context=self.parse()
        actions,_=self.parse('actions')
        self.assertEqual(identity.facts['asset_id'],annual.ASSET)
        self.assertEqual(identity.facts['valid_through'],'2024-12-31')
        self.assertEqual(actions.facts['pages'][0]['total_records'],0)
        self.assertEqual(actions.facts['notices'],[])
        self.assertEqual(identity.received_at,'2026-11-06T18:00:00Z')
        self.assertEqual(identity.evidence_class,'synthetic_only')
        self.assertFalse(identity.implementation_binding['historical_point_in_time_certified'])
        self.assertIsNone(identity.implementation_binding['provider_first_publication_at'])
        self.assertEqual(len(context.references),6)

    def test_report_layout_and_coverage_are_not_inferred_from_empty_query(self):
        valid=sections()
        self.assertTrue(annual.parse_annual_sections(valid)['no_cash_distributions_reported'])
        for number,replacement in (
            (1,valid[1].replace('2024','2023')),
            (2,valid[2].replace('12月31日','6月30日')),
            (5,valid[5].replace('518880','518881')),
            (15,valid[15].replace('不进行','暂未进行')),
            (15,valid[15].replace('本报告期不进行收益分配。','若无收益则不进行分配。')),
            (52,valid[52].replace(' - ',' 100 ')),
        ):
            with self.subTest(page=number), self.assertRaises(BundleError):
                annual.parse_annual_sections(dict(valid) | {number:replacement})

    def test_unreviewed_metadata_hash_cannot_register_itself(self):
        ref=self.save('metadata.json',self.metadata)
        adapter=annual.retained_annual_adapters(reviewed_metadata_sha256='0'*64)['identity']
        with self.assertRaisesRegex(BundleError,'not_reviewed'), patch.object(annual,'_extract_pdf') as extract:
            adapter.parse(EvidenceContext(self.root,component='identity'),ref)
        extract.assert_not_called()

    def test_original_mutation_blocks_before_PDF_extraction(self):
        (self.root/'annual.pdf').write_bytes(b'%PDF-1.7 changed original')
        with self.assertRaisesRegex(BundleError,'hash_mismatch'):
            self.parse()

    def test_receipt_url_size_hash_and_scope_cannot_be_self_asserted(self):
        for change in (dict(url='https://example.org/report.pdf'),dict(bytes=1),
                       dict(sha256='0'*64),dict(scope_sha256='0'*64),dict(http_status=404)):
            self.metadata['pdf_receipt']=self.receipt(self.pdf,annual.REPORT_URL,**change)
            with self.subTest(change=change), self.assertRaisesRegex(BundleError,'does_not_bind'):
                self.parse()

    def test_backdated_capture_or_metadata_cannot_certify_historical_availability(self):
        for change in (dict(claimed_at='2026-11-05T18:00:00Z'),
                       dict(claimed_at='2024-06-28T18:00:00Z',completed_at='2024-06-28T18:00:01Z')):
            self.metadata['pdf_receipt']=self.receipt(self.pdf,annual.REPORT_URL,**change)
            with self.assertRaises(BundleError):self.parse()
        self.metadata['pdf_receipt']=self.receipt(self.pdf,annual.REPORT_URL)
        self.metadata['created_at']='2025-03-31T18:00:00Z'
        with self.assertRaisesRegex(BundleError,'predates_its_originals'):self.parse()

    def test_incomplete_or_conflicting_catalog_is_not_complete_coverage(self):
        for kind in ('pages','missing','duplicate','date'):
            catalog=deepcopy(self.catalog_body)
            if kind=='pages':catalog['pageHelp']['pageCount']=2
            elif kind=='missing':catalog['result']=[]
            elif kind=='duplicate':
                catalog['result']*=2;catalog['pageHelp']['data']=catalog['result'];catalog['pageHelp']['total']=2
            else:catalog['result'][0]['SSEDATE']='2024-03-31';catalog['pageHelp']['data']=catalog['result']
            self.metadata['catalog']=self.save('catalog.json',catalog)
            self.metadata['catalog_receipt']=self.receipt(self.metadata['catalog'],'https://query.sse.com.cn/commonQuery.do')
            with self.subTest(kind=kind),self.assertRaises(BundleError):self.parse()

    def test_original_PDF_byte_budget_and_signature_precede_optional_parser(self):
        for raw in (b'not a PDF',b'%PDF-'+b'0'*2_000_000):
            with self.assertRaisesRegex(BundleError,'bounded_original'):
                annual._extract_pdf(raw)
