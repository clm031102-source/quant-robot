from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.etf_listing_evidence import review_listing_bundle, review_listing_text


FUND = '测试沪深300交易型开放式指数证券投资基金'
TITLE = FUND + '上市交易公告书'
COVER = '1\n' + TITLE + '\n上市日期：2019年10月9日\n公告日期：2019年9月27日'
BODY = '二、基金概览\n1、基金名称：' + FUND + '\n3、二级市场交易代码：510100\n4、申购、赎回代码：510101\n9、上市交易日期：2019年10月9日'


class ListingTextTests(unittest.TestCase):
    def review(self, **overrides):
        args = {'symbol': '510100.SH', 'title': TITLE, 'published_date': '2019-09-27',
                'pages': {1: COVER, 4: BODY}}
        args.update(overrides)
        return review_listing_text(**args)

    def test_listing_date_and_market_code_are_distinct_from_publication_and_creation_code(self):
        r = self.review()
        self.assertEqual(r['trading_code'], '510100')
        self.assertEqual(r['listing_date_observed'], '2019-10-09')
        self.assertEqual(r['publication_date_observed'], '2019-09-27')
        self.assertEqual(r['legal_fund_name_observed'], FUND)
        self.assertFalse(r['historical_membership_verified'])
        self.assertFalse(r['mapping_eligible'])
        self.assertIsNone(r['known_from'])

    def test_observed_code_label_layouts_preserve_explicit_role(self):
        for line in ['（二）二级市场交易代码：510100。', '5.基金交易代码：510100。',
                     '证券代码（二级市场交易代码）：510100',
                     '6、基金二级市场交易简称及交易代码：测试ETF，交易代码：510100']:
            with self.subTest(line=line):
                r = self.review(pages={1: COVER, 4: line})
                self.assertEqual(r['trading_code'], '510100')

    def test_subscription_code_and_bare_number_cannot_replace_missing_market_code(self):
        for body in ['申购、赎回代码：510100', '认购代码：510100', '基金代码：510100',
                     '文件510100_20190927.pdf', '交易代码：5101004', '交易代码：510100A',
                     '交易代码：510100_SH']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.review(pages={1: COVER, 4: body})

    def test_code_under_matching_filename_does_not_override_explicit_other_code(self):
        with self.assertRaisesRegex(ValueError, 'code'):
            self.review(pages={1: COVER, 4: '交易代码：510300'})

    def test_cross_fund_cover_and_body_names_are_rejected(self):
        for pages in [{1: COVER.replace('沪深300', '通信设备'), 4: BODY},
                      {1: COVER, 4: BODY.replace('沪深300', '通信设备')}]:
            with self.subTest(pages=pages), self.assertRaisesRegex(ValueError, 'identity'):
                self.review(pages=pages)

    def test_linked_fund_and_notice_summary_are_not_target_listing_books(self):
        for title in [FUND + '联接基金上市交易公告书', TITLE + '摘要', '关于' + TITLE + '的提示性公告']:
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.review(title=title)

    def test_conflicting_market_codes_and_listing_dates_are_not_silently_selected(self):
        for extra in ['\n交易代码：510300', '\n交易代码：5103004', '\n上市交易日期：2019年10月10日',
                      '；交易代码：510300', '，交易代码：510300']:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.review(pages={1: COVER, 4: BODY + extra})

    def test_explicit_manager_header_must_match_exactly_before_it_can_be_removed(self):
        header = '测试基金管理有限公司 上市交易公告书\n'
        r = self.review(pages={1: header + COVER[2:], 4: BODY},
                        expected_manager_name='测试基金管理有限公司')
        self.assertEqual(r['status'], 'identity_fields_observed')
        for manager in [None, '其他基金管理有限公司']:
            with self.subTest(manager=manager), self.assertRaises(ValueError):
                self.review(pages={1: header + COVER[2:], 4: BODY}, expected_manager_name=manager)

    def test_entire_code_field_rejects_unlabeled_second_value_but_allows_next_named_field(self):
        for value in ['510100，510300', '510100 510300', '510100；510300', '510100/510300']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.review(pages={1: COVER, 4: '交易代码：' + value})
        for line in ['交易代码：510100；申购代码：510101', '交易代码：510100；交易代码：510100']:
            with self.subTest(line=line):
                self.assertEqual(self.review(pages={1: COVER, 4: line})['trading_code'], '510100')

    def test_example_fields_are_not_product_identity(self):
        for body in ['例如：交易代码：510100', '其他基金交易代码：510100',
                     '示例：\n交易代码：510100', '示例\n交易代码：510100',
                     '示例\n说明以下字段\n交易代码：510100', '若申购成功：\n交易代码：510100']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.review(pages={1: COVER, 4: body})

    def test_hypothetical_listing_date_and_cross_page_example_scope_are_rejected(self):
        cover = COVER.replace('上市日期：2019年10月9日\n', '')
        for body in ['假设上市交易日期：2019年10月9日\n交易代码：510100',
                     '若上市成功\n上市交易日期：2019年10月9日\n交易代码：510100']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.review(pages={1: cover, 4: body})
        with self.assertRaises(ValueError):
            self.review(pages={1: COVER, 3: '示例\n以下展示另一个基金的字段', 4: BODY})

    def test_publication_mismatch_missing_or_invalid_date_is_rejected(self):
        for cover in [COVER.replace('9月27日', '9月26日'), COVER.replace('公告日期', '基金成立日期'),
                      COVER.replace('10月9日', '13月9日'), COVER.replace('10月9日', '待定')]:
            with self.subTest(cover=cover), self.assertRaises(ValueError):
                self.review(pages={1: cover, 4: BODY})

    def test_listing_before_publication_or_sealed_date_is_not_accepted(self):
        for old, new in [('2019年10月9日', '2019年9月20日'), ('2019年10月9日', '2026年1月1日')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.review(pages={1: COVER.replace(old, new), 4: BODY.replace(old, new)})

    def test_bounded_page_and_symbol_contract(self):
        for overrides in [{'symbol': '510100.SZ'}, {'published_date': '20190927'},
                          {'published_date': '2026-01-01'}, {'pages': {7: BODY}},
                          {'pages': {True: COVER, 4: BODY}}, {'pages': {1: COVER, 4: None}}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.review(**overrides)


class ListingBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / 'listing.pdf'; self.pdf.write_bytes(b'%PDF-1.7 offline source fixture')
        self.record = {'symbol': '510100.SH', 'title': TITLE, 'date': '2019-09-27',
            'path': str(self.pdf), 'url': 'https://www.sse.com.cn/disclosure/listing.pdf',
            'sha256': hashlib.sha256(self.pdf.read_bytes()).hexdigest()}
        self.packet = self.root / 'packet.json'

    def config(self, records=None):
        self.packet.write_text(json.dumps({'records': records or [self.record], 'complete': True}), encoding='utf-8')
        return {'source_manifest_path': str(self.packet),
                'source_manifest_sha256': hashlib.sha256(self.packet.read_bytes()).hexdigest()}

    def test_reopens_fingerprinted_pdf_instead_of_trusting_extracted_candidate_text(self):
        with patch('quant_robot.data.etf_listing_evidence._listing_pages', return_value={1: COVER, 4: BODY}):
            r = review_listing_bundle(self.config([{**self.record, 'selected_pages': [{'text': 'forged'}]}]))
        self.assertEqual(r['counts'], {'identity_fields_observed': 1})
        self.assertFalse(r['source_gate_passed'])
        self.assertFalse(r['historical_mapping_written'])

    def test_all_dates_are_preflighted_before_first_pdf_is_read(self):
        bad = {**self.record, 'date': '2026-01-01', 'path': 'missing.pdf'}
        with patch('quant_robot.data.etf_listing_evidence._listing_pages') as parse:
            with self.assertRaises(ValueError): review_listing_bundle(self.config([self.record, bad]))
        parse.assert_not_called()

    def test_packet_or_pdf_tampering_and_duplicate_paths_fail_closed(self):
        config = self.config(); self.packet.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): review_listing_bundle(config)
        config = self.config(); self.pdf.write_bytes(b'%PDF-1.7 changed')
        with self.assertRaises(ValueError): review_listing_bundle(config)
        with self.assertRaises(ValueError): review_listing_bundle(self.config([self.record, self.record]))

    def test_rejected_identity_is_reported_without_historical_assignment(self):
        with patch('quant_robot.data.etf_listing_evidence._listing_pages', return_value={1: COVER, 4: '交易代码：510300'}):
            r = review_listing_bundle(self.config())
        self.assertEqual(r['counts'], {'rejected_listing_fields': 1})
        self.assertFalse(r['documents'][0]['mapping_eligible'])

    def test_source_mutation_during_review_is_detected(self):
        def mutate(_):
            self.pdf.write_bytes(b'%PDF-1.7 changed during review')
            return {1: COVER, 4: BODY}
        with patch('quant_robot.data.etf_listing_evidence._listing_pages', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): review_listing_bundle(self.config())

    def test_empty_incomplete_or_over_budget_packet_is_rejected(self):
        for packet in [{'records': [], 'complete': True}, {'records': [self.record], 'complete': False},
                       {'records': [self.record] * 41, 'complete': True}]:
            self.packet.write_text(json.dumps(packet), encoding='utf-8')
            config = {'source_manifest_path': str(self.packet), 'source_manifest_sha256': hashlib.sha256(self.packet.read_bytes()).hexdigest()}
            with self.subTest(packet=packet), self.assertRaises(ValueError): review_listing_bundle(config)


if __name__ == '__main__':
    unittest.main()
