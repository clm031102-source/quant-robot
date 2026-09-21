import unittest

from quant_robot.data.sources.pbc_enterprise_survey import (
    catalogue_rows, landing_details, report_fields,
)


class EnterpriseSurveySourceTests(unittest.TestCase):
    def test_older_summary_title_identifies_quarter_but_still_requires_field_method(self):
        raw = ('<td><a href="/a">2011年第4季度企业家问卷调查综述</a>'
               '<span>2011-12-22</span></td>').encode()
        self.assertEqual(catalogue_rows(raw, 'https://www.pbc.gov.cn/list')[0]['quarter'],
                         '2011Q4')
        pages = ['2011年第4季度全国企业家问卷调查综述', '资金周转指数为60.0%', self.method()]
        self.assertEqual(report_fields(pages, '2011Q4')['index_percent'], '60.0')
        with self.assertRaises(ValueError):
            report_fields(pages[:2], '2011Q4')

    def test_catalogue_keeps_row_date_and_excludes_other_surveys(self):
        raw = '''<td><a href="/a">2013年第2季度企业家问卷调查报告</a>
        <span>2013-06-21</span></td><td><a href="/b">2013年第二季度银行家问卷调查报告</a>
        <span>2013-06-20</span></td>'''.encode()
        rows = catalogue_rows(raw, 'https://www.pbc.gov.cn/list')
        self.assertEqual(rows, [{'quarter': '2013Q2', 'title': '2013年第2季度企业家问卷调查报告',
                                'catalogue_date': '2013-06-21', 'url': 'https://www.pbc.gov.cn/a'}])

    def test_catalogue_requires_unambiguous_date_in_same_row(self):
        for extra in ('', '<span>2013-06-21 2013-06-22</span>'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                catalogue_rows(('<td><a href="/a">2013年第二季度企业家问卷调查报告</a>'
                                + extra + '</td>').encode(), 'https://www.pbc.gov.cn/list')

    def test_landing_ignores_migration_metadata_but_requires_correct_identity(self):
        raw = '''<meta name="ArticleTitle" content="2023年第四季度企业家问卷调查报告">
        <meta name="createDate" content="2025-12-10 01:00:00"><meta name="PubDate" content="2024-03-22">
        <body>文章来源：2024-03-22 19:01:40<a href="../r.pdf">报告</a></body>'''.encode()
        got = landing_details(raw, 'https://www.pbc.gov.cn/abc/index.html', '2023Q4')
        self.assertEqual(got['published_at'], '2024-03-22 19:01:40')
        self.assertEqual(got['pdf_url'], 'https://www.pbc.gov.cn/r.pdf')
        with self.assertRaises(ValueError):
            landing_details(raw, 'https://www.pbc.gov.cn/abc/index.html', '2023Q3')
        with self.assertRaises(ValueError):
            landing_details(raw.replace(b'2024-03-22 19:01:40', b'no body date'),
                            'https://www.pbc.gov.cn/abc/index.html', '2023Q4')

    def test_landing_rejects_ambiguous_attachments_and_date_conflicts(self):
        raw = '''<meta name="ArticleTitle" content="2023年第四季度企业家问卷调查报告">
        <meta name="PubDate" content="2024-03-22"><body>2024-03-22 19:01:40
        <a href="/a.pdf">a</a></body>'''.encode()
        for data in (raw.replace(b'</body>', b'<a href="/b.pdf">b</a></body>'),
                     raw.replace(b'content="2024-03-22"', b'content="2024-03-21"')):
            with self.subTest(data=data), self.assertRaises(ValueError):
                landing_details(data, 'https://www.pbc.gov.cn/index.html', '2023Q4')

    def test_report_uses_printed_level_not_backtable_or_component_reconstruction(self):
        pages = ['2023年第四季度企业家问卷调查报告',
                 '资金周转指数为60.2%。其中良好33.1%，一般54.3%，困难12.6%。',
                 '附件2022Q4资金周转指数56.7', self.method()]
        got = report_fields(pages, '2023Q4')
        self.assertEqual(got['index_percent'], '60.2')
        self.assertIsNone(got['document_date'])
        with self.assertRaises(ValueError):
            report_fields(pages, '2023Q3')
        with self.assertRaises(ValueError):
            report_fields([pages[0], '资金周转指数为101%。', pages[2], pages[3]], '2023Q4')
        with self.assertRaises(ValueError):
            report_fields([pages[0], '资金周转指数为60.2%。资金周转指数为60.3%。',
                           pages[2], pages[3]], '2023Q4')

    def test_report_rejects_missing_level_or_changed_method(self):
        with self.assertRaises(ValueError):
            report_fields(['2013年第2季度企业家问卷调查报告', '表格58.2', self.method()], '2013Q2')
        with self.assertRaises(ValueError):
            report_fields(['2013年第2季度企业家问卷调查报告', '资金周转指数为58.2%',
                           self.method().replace('0.5', '0.3')], '2013Q2')

    @staticmethod
    def method():
        return ('反映企业家对本企业本季资金周转情况判断的扩散指数。该指数的计算方法是在全部调查'
                '的企业中，先分别计算认为本季企业资金周转“良好”与“一般”的占比，再分别赋予权重'
                '1和0.5后求和得出。')

    @staticmethod
    def old_method():
        return ('前述差额加上100%除以2，转化为在0和100%之间围绕50%波动的数值。'
                '表明企业家对本企业资金周转情况判断的扩散指数。一般指全部接受调查的企业家中，'
                '认为本企业资金周转状况“良好”的占比减去认为“困难”的占比。')

    def test_legacy_definition_requires_both_specific_field_and_scale_transform(self):
        pages = ['2012年第1季度企业家问卷调查报告', '企业资金周转指数为60.7%',
                 self.old_method()]
        self.assertEqual(report_fields(pages, '2012Q1')['index_percent'], '60.7')
        with self.assertRaises(ValueError):
            report_fields(pages[:2] + [self.old_method().replace('除以2', '除以3')], '2012Q1')

    def test_original_quarter_table_keeps_precision_and_never_fills_a_missing_quarter(self):
        header = ('附件：5000户企业家调查扩散指数表\n时间 企业家信心指数 企业景气指数 '
                  '设备能力利用指数 原材料供应情况 产品销售情况 产成品库存水平 国内订单水平 '
                  '出口产品订单 资金周转状况 企业盈利指数 设备投资指数\n')
        row = '2011.Q4 68.43 67.49 42.39 63.54 59.01 53.21 53.15 48.73 60.55 55.54 51.79'
        pages = ['2011年第4季度企业家问卷调查综述', header + row, self.old_method()]
        result = report_fields(pages, '2011Q4')
        self.assertEqual(result['index_percent'], '60.55')
        self.assertEqual(result['value_location'], 'original_quarter_appendix')
        for bad in (row.replace('2011.Q4', '2011.Q3'), row + ' 12.34', row + '\n' + row):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                report_fields([pages[0], header + bad, pages[2]], '2011Q4')


if __name__ == '__main__':
    unittest.main()
