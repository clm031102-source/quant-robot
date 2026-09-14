import hashlib
import unittest

from quant_robot.data.mof_fiscal_release import parse_mof_monthly_expenditure


def document(*, title='2024年5月财政收支情况', period='1-5月', national='120',
             central='20', local='100', unit='亿元', published='2024年6月24日',
             meta='2024-06-24 08:36:00', extra='', duplicate=False):
    paragraph = (f'<p>{period}累计，全国一般公共预算支出{national}{unit}，同比增长3%。'
                 f'其中，中央一般公共预算本级支出{central}亿元，增长2%；'
                 f'地方一般公共预算支出{local}亿元，增长4%。</p>')
    return (f'<html><head><meta charset="UTF-8"><title>{title}</title>'
            f'<meta name="PubDate" content="{meta}"></head><body>'
            f'<div>发布日期：{published}</div>{paragraph}'
            f'{paragraph if duplicate else ""}{extra}</body></html>').encode()


class MofFiscalReleaseTests(unittest.TestCase):
    def parse(self, raw=None, **kwargs):
        return parse_mof_monthly_expenditure(document() if raw is None else raw,
                                           expected_year=2024, expected_month=5, **kwargs)

    def test_cumulative_amounts_dates_and_hash_are_retained_without_factors(self):
        raw = document()
        r = self.parse(raw)
        self.assertEqual(r['period_start'], '2024-01-01')
        self.assertEqual(r['period_end'], '2024-05-31')
        self.assertEqual(r['amount_cny_100m'], '120')
        self.assertEqual(r['central_own_amount_cny_100m'], '20')
        self.assertEqual(r['local_amount_cny_100m'], '100')
        self.assertEqual(r['published_date_label'], '2024-06-24')
        self.assertEqual(r['assumed_available_civil_day'], '2024-06-25')
        self.assertEqual(r['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(r['historical_availability_verified'])
        self.assertFalse(r['research_admission_granted'])
        self.assertFalse(r['factor_or_return_computed'])

    def test_inline_spans_and_nonbreaking_spaces_do_not_change_source_numbers(self):
        raw = document(national='<span>1</span><span>20</span>',
                       central='<b>20</b>', local='1&nbsp;00')
        self.assertEqual(self.parse(raw)['amount_cny_100m'], '120')

    def test_central_transfers_and_other_budget_categories_are_not_added(self):
        other = ('<p>中央一般公共预算支出500亿元，含对地方转移支付。</p>'
                 '<p>全国政府性基金预算支出999亿元。</p>')
        r = self.parse(document(extra=other))
        self.assertEqual(r['amount_cny_100m'], '120')
        self.assertEqual(r['central_own_amount_cny_100m'], '20')

    def test_decimals_reconcile_exactly_without_float_rounding(self):
        r = self.parse(document(national='120.03', central='20.01', local='100.02'))
        self.assertEqual(r['amount_cny_100m'], '120.03')

    def test_expected_title_and_cumulative_period_must_agree(self):
        for args in ({'title': '2023年5月财政收支情况'},
                     {'title': '2024年4月财政收支情况'}, {'period': '1-4月'},
                     {'period': '5月'}, {'period': '2-5月'},
                     {'title': '2024年中央和地方预算草案报告'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.parse(document(**args))

    def test_explicit_january_to_month_and_half_year_titles_are_supported(self):
        self.assertEqual(self.parse(document(title='2024年1-5月财政收支情况'))['period_end'], '2024-05-31')
        raw = document(title='2024年上半年财政收支情况', period='上半年',
                       published='2024年7月19日', meta='2024-07-19 09:00:00')
        r = parse_mof_monthly_expenditure(raw, expected_year=2024, expected_month=6)
        self.assertEqual(r['period_end'], '2024-06-30')

    def test_duplicate_paragraphs_are_review_required_even_if_identical(self):
        for duplicate, extra in ((True, ''), (False, '<p>1-5月，全国一般公共预算支出121亿元。</p>')):
            with self.subTest(duplicate=duplicate), self.assertRaises(ValueError):
                self.parse(document(duplicate=duplicate, extra=extra))

    def test_missing_components_wrong_unit_negative_and_inconsistent_totals_fail(self):
        for raw in (document(unit='万元'), document(national='-120'),
                    document(national='0'), document(national='121'),
                    document().replace('中央一般公共预算本级支出'.encode(), '中央一般公共预算支出'.encode()),
                    document().replace('地方一般公共预算支出100亿元'.encode(), '地方支出未列'.encode())):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.parse(raw)

    def test_publication_day_labels_must_agree_and_follow_period_end(self):
        for args in ({'published': '2024年6月25日'}, {'meta': '2024-06-25 08:36:00'},
                     {'published': '2024年5月31日', 'meta': '2024-05-31 08:36:00'},
                     {'published': '2024年2月30日', 'meta': ''},
                     {'meta': '2024-06-24 bad-time'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.parse(document(**args))

    def test_date_only_label_does_not_invent_an_intraday_timestamp(self):
        r = self.parse(document(meta=''))
        self.assertEqual(r['published_date_label'], '2024-06-24')
        self.assertEqual(r['publication_metadata'], [])
        self.assertEqual(r['assumed_available_civil_day'], '2024-06-25')

    def test_metadata_without_visible_publication_evidence_is_insufficient(self):
        raw = document().replace('发布日期：2024年6月24日'.encode(), b'')
        with self.assertRaises(ValueError):
            self.parse(raw)

    def test_script_style_and_template_text_are_not_fiscal_evidence(self):
        hidden = ('<script>发布日期：2024年6月25日</script>'
                  '<style>1-5月，全国一般公共预算支出777亿元。</style>'
                  '<template><p>1-5月，全国一般公共预算支出888亿元。</p></template>')
        self.assertEqual(self.parse(document(extra=hidden))['amount_cny_100m'], '120')

    def test_malformed_input_and_period_types_fail(self):
        for raw in ('not-bytes', b'\xff\xfe', b'x' * 3_000_001):
            with self.subTest(type=type(raw).__name__), self.assertRaises(ValueError):
                self.parse(raw)
        for year, month in ((True, 5), (2024, True), (2024, 0), (2024, 13), ('2024', 5)):
            with self.subTest(year=year, month=month), self.assertRaises(ValueError):
                parse_mof_monthly_expenditure(document(), expected_year=year, expected_month=month)

    def test_quarter_and_full_year_titles_bind_to_exact_cumulative_period(self):
        for month, label, period in [(3, '一季度', '1-3月'), (9, '前三季度', '1-9月'),
                                     (12, '', '2024年')]:
            with self.subTest(month=month):
                raw = document(title='2024年' + label + '财政收支情况', period=period,
                               published='2025年1月29日', meta='2025-01-29 08:00:00')
                r = parse_mof_monthly_expenditure(raw, expected_year=2024, expected_month=month)
                self.assertEqual(r['period_end'], f'2024-{month:02d}-' + ('30' if month == 9 else '31'))

    def test_annual_body_year_cannot_substitute_for_month_or_different_year(self):
        for month, title, period in [(5, '2024年5月财政收支情况', '2024年'),
                                     (12, '2024年财政收支情况', '2023年'),
                                     (6, '2024年一季度财政收支情况', '上半年')]:
            with self.subTest(month=month), self.assertRaises(ValueError):
                parse_mof_monthly_expenditure(document(title=title, period=period,
                    published='2025年1月29日', meta='2025-01-29'), expected_year=2024, expected_month=month)

    def test_declared_gb2312_retains_original_byte_identity(self):
        text = document().decode().replace('<meta charset="UTF-8">',
            '<meta http-equiv="Content-Type" content="text/html; charset=gb2312">')
        raw = text.encode('gb2312')
        r = self.parse(raw)
        self.assertEqual(r['source_encoding'], 'gb2312')
        self.assertEqual(r['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(r['amount_cny_100m'], '120')

    def test_missing_conflicting_unknown_or_false_encoding_declarations_reject(self):
        cases = [document().decode().replace('UTF-8', 'gb2312').encode(),
                 document().decode().encode('gb2312'),
                 document().replace(b'<meta charset="UTF-8">', b'<meta charset="UTF-8"><meta charset="gb2312">'),
                 document().replace(b'UTF-8', b'gb18030'),
                 b'\xef\xbb\xbf' + document().decode().replace('UTF-8', 'gb2312').encode('gb2312')]
        for raw in cases:
            with self.subTest(raw_prefix=raw[:60]), self.assertRaises(ValueError):
                self.parse(raw)

    def test_legacy_central_local_labels_stay_review_required(self):
        raw = document().replace('中央一般公共预算本级支出'.encode(), '中央一般公共预算支出'.encode())
        raw = raw.replace('地方一般公共预算支出'.encode(), '地方一般公共预算本级支出'.encode())
        with self.assertRaises(ValueError):
            self.parse(raw)

    def test_explicit_legacy_schema_retains_labels_without_inventing_central_own_value(self):
        raw = document().replace('中央一般公共预算本级支出'.encode(), '中央一般公共预算支出'.encode())
        raw = raw.replace('地方一般公共预算支出'.encode(), '地方一般公共预算本级支出'.encode())
        r = self.parse(raw, component_label_schema='reported_legacy')
        self.assertEqual(r['amount_cny_100m'], '120')
        self.assertIsNone(r['central_own_amount_cny_100m'])
        self.assertEqual(r['component_amounts_as_reported'], [
            {'label': '中央一般公共预算支出', 'amount_cny_100m': '20'},
            {'label': '地方一般公共预算本级支出', 'amount_cny_100m': '100'}])
        self.assertFalse(r['research_admission_granted'])

    def test_explicit_schema_does_not_guess_mixed_labels_or_unknown_conventions(self):
        for raw, schema in [(document(), 'reported_legacy'), (document(), 'unknown'),
                            (document().replace('中央一般公共预算本级支出'.encode(),
                                                '中央一般公共预算支出'.encode()), 'reported_legacy')]:
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                self.parse(raw, component_label_schema=schema)

    def test_secondary_placeholder_template_title_does_not_change_primary_title(self):
        raw = document(extra='<head><title>无标题文档</title></head>')
        self.assertEqual(self.parse(raw)['title'], '2024年5月财政收支情况')

    def test_substantive_secondary_title_is_not_silently_discarded(self):
        for title in ['2023年5月财政收支情况', '2024年5月财政收支情况', 'unreviewed template']:
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.parse(document(extra=f'<head><title>{title}</title></head>'))

    def test_first_quarter_words_are_cumulative_only_for_march(self):
        raw = document(title='2024年一季度财政收支情况', period='一季度',
                       published='2024年4月22日', meta='2024-04-22')
        r = parse_mof_monthly_expenditure(raw, expected_year=2024, expected_month=3)
        self.assertEqual(r['period_end'], '2024-03-31')
        with self.assertRaises(ValueError):
            parse_mof_monthly_expenditure(raw, expected_year=2024, expected_month=4)

    def test_narrative_growth_discussion_is_not_a_second_amount_but_any_numeric_total_is(self):
        raw = document(extra='<p>全国一般公共预算支出增幅比去年同期加快。</p>')
        self.assertEqual(self.parse(raw)['amount_cny_100m'], '120')
        for unit in ['亿元', '万元']:
            with self.subTest(unit=unit), self.assertRaises(ValueError):
                self.parse(document(extra=f'<p>全国一般公共预算支出121{unit}。</p>'))


if __name__ == '__main__':
    unittest.main()
