import unittest

from quant_robot.data.etf_dividend_notice import parse_cash_dividend_notice, validate_announcement_page


NOTICE = """华泰柏瑞沪深300交易型开放式指数证券投资基金收益分配公告
公告送出日期：2021 年 1 月 11 日
基金主代码 510300
本次分红方案（单位：元/10 份基金份额） 0.7200
有关年度分红次数的说明 2020年第一次分红
权益登记日 2021年1月15日
除息日 2021年1月18日
现金红利发放日 2021年1月21日
暂不征收个人所得税和企业所得税。
本公司于2021年1月19日将款项划入登记公司账户。
"""


class DividendNoticeTests(unittest.TestCase):
    def test_amount_unit_and_cash_year_are_taken_from_notice_fields(self):
        event = parse_cash_dividend_notice(NOTICE, symbol="510300.SH", announcement_date="2021-01-11")
        self.assertEqual(event["cash_per_share"], "0.0720")
        self.assertEqual(event["pay_date"], "2021-01-21")
        self.assertEqual(event["ex_date"], "2021-01-18")
        self.assertTrue(event["notice_states_tax_exemption"])
        self.assertFalse(event["broker_dividend_fees_verified"])

    def test_other_explicit_denominator_is_not_assumed_to_be_ten(self):
        result = parse_cash_dividend_notice(NOTICE.replace("元/10", "元/100"),
            symbol="510300.SH", announcement_date="2021-01-11")
        self.assertEqual(result["cash_per_share"], "0.0072")

    def test_missing_pay_date_is_not_inferred_from_bank_transfer(self):
        with self.assertRaisesRegex(ValueError, "现金红利发放日"):
            parse_cash_dividend_notice(NOTICE.replace("现金红利发放日", "银行划付日"),
                symbol="510300.SH", announcement_date="2021-01-11")

    def test_duplicate_and_mismatched_notice_fields_fail(self):
        cases = [(NOTICE + "除息日2021年1月19日", "ambiguous"),
            (NOTICE.replace("基金主代码 510300", "基金主代码 510500"), "code"),
            (NOTICE.replace("1 月 11 日", "1 月 12 日"), "announcement"),
            (NOTICE.replace("元/10", "美元/10"), "unit"),
            (NOTICE.replace("0.7200", "-0.7200"), "amount"),
            (NOTICE.replace("元/10", "元/0"), "denominator"),
            (NOTICE.replace("现金红利发放日 2021年1月21日", "现金红利发放日 2021年1月14日"), "chronology")]
        for text, pattern in cases:
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                parse_cash_dividend_notice(text, symbol="510300.SH", announcement_date="2021-01-11")

    def test_no_tax_statement_does_not_create_net_cash_assumption(self):
        event = parse_cash_dividend_notice(NOTICE.replace("暂不征收个人所得税和企业所得税", "税费待确认"),
            symbol="510300.SH", announcement_date="2021-01-11")
        self.assertFalse(event["notice_states_tax_exemption"])
        self.assertNotIn("net_cash_per_share", event)

    def test_unsupported_amount_formats_are_not_silently_truncated(self):
        for value in ("1,000.00", "0.7200e2", "0.7200至0.8000", "0.7200%", "0.7200（待定）"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "amount"):
                parse_cash_dividend_notice(NOTICE.replace("0.7200", value),
                    symbol="510300.SH", announcement_date="2021-01-11")

    def test_complete_page_accepts_alternative_distribution_title(self):
        page = announcement_page()
        rows = validate_announcement_page(page, symbol="510300.SH", start="2021-01-01", end="2021-12-31")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_kind"], "cash_distribution_notice")

    def test_truncated_duplicate_wrong_identity_and_out_of_window_pages_fail(self):
        for kind in ("truncated", "duplicate", "wrong_code", "outside", "untrusted_url", "holdout"):
            page = announcement_page()
            if kind == "truncated": page["pageHelp"]["total"] = 2
            if kind == "duplicate":
                page["result"].append(dict(page["result"][0]));page["pageHelp"]["total"] = 2
            if kind == "wrong_code": page["result"][0]["SECURITY_CODE"] = "510500"
            if kind == "outside": page["result"][0]["SSEDATE"] = "2020-12-31"
            if kind == "untrusted_url": page["result"][0]["URL"] = "https://example.com/event.pdf"
            end = "2026-01-01" if kind == "holdout" else "2021-12-31"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_announcement_page(page, symbol="510300.SH", start="2021-01-01", end=end)


def announcement_page():
    return {"pageHelp": {"pageNo": 1, "pageCount": 1, "pageSize": 100, "total": 1},
        "result": [{"SSEDATE": "2021-01-11", "SECURITY_CODE": "510300",
            "TITLE": "华泰柏瑞沪深300交易型开放式指数证券投资基金收益分配公告",
            "ORG_BULLETIN_TYPE_DESC": "其他",
            "URL": "/disclosure/fund/announcement/c/2021-01-11/510300_20210111_1.pdf"}]}
