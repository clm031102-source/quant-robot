import unittest
from decimal import Decimal
import xml.etree.ElementTree as ET

from quant_robot.research.cash_carry_inputs import parse_pcf, income_periods, check_income_identities


def legacy(**changes):
    fields = dict(Version='2.0', FundID='159001', Type='4', TradingDay='20150105',
                  PreTradingDay='20141231', CreationRedemptionUnit='1', Creation='1',
                  Redemption='1', CashCreation='1', RecordNum='1', TotalRecordNum='1',
                  CashComponent='0.00', EstimateCashComponent='0.00', NAV='100.0000',
                  NAVperCU='100.00', CreationLimitPerUser='0', NetCreationLimit='1000',
                  NetRedemptionLimit='1000', NetCreationLimitPerUser='0')
    fields.update(changes)
    lines=['[ETFHZ]']+[f'{k}={v}' for k,v in fields.items() if v is not None]
    return ('\n'.join(lines)+'\nTAGTAG\n159900|cash||2||100.000|100.000|XSHE|\nENDENDEND').encode()


def xml_pcf():
    fields=dict(line.split('=',1) for line in legacy().decode().split('TAGTAG')[0].splitlines() if '=' in line)
    fields['Version']='1.0';fields['SecurityID']=fields.pop('FundID');fields['SecurityIDSource']='102'
    fields['Creation']='Y';fields['Redemption']='Y'
    root=ET.Element('PCFFile',xmlns='http://ts.szse.cn/Fund')
    for key,value in fields.items():ET.SubElement(root,key).text=value
    component=ET.SubElement(ET.SubElement(root,'Components'),'Component')
    for key,value in dict(UnderlyingSecurityID='159900',UnderlyingSecurityIDSource='102',
                          ComponentShare='0',SubstituteFlag='2',CreationCashSubstitute='100',
                          RedemptionCashSubstitute='100').items():ET.SubElement(component,key).text=value
    return ET.tostring(root)


class PcfTests(unittest.TestCase):
    def test_zero_is_preserved_and_missing_is_distinct(self):
        p=parse_pcf(legacy(), '2015-01-05')
        self.assertEqual(p['caps']['NetCreationLimitPerUser'], Decimal(0))
        self.assertIsNone(p['caps']['RedemptionLimitPerUser'])
        self.assertEqual(p['cash_in'], Decimal(100))

    def test_denied_subscription_is_not_malformed_source(self):
        self.assertFalse(parse_pcf(legacy(Creation='0'), '2015-01-05')['creation'])

    def test_unknown_active_cap_cannot_be_filled_with_zero(self):
        with self.assertRaises(ValueError):
            parse_pcf(legacy(NetCreationLimit=None), '2015-01-05')

    def test_wrong_identity_dates_units_or_cash_are_rejected(self):
        for change in [dict(FundID='159003'),dict(TradingDay='20260922'),
                       dict(Type='5'),dict(CreationRedemptionUnit='100'),
                       dict(CashComponent='1'),dict(RecordNum='2'),dict(Creation='2'),
                       dict(NetCreationLimit='-1'),dict(NetCreationLimit='0.5'),
                       dict(NetCreationLimit='NaN')]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                parse_pcf(legacy(**change),'2015-01-05')

    def test_duplicate_field_rejected(self):
        with self.assertRaises(ValueError):
            parse_pcf(legacy().replace(b'TAGTAG',b'FundID=159001\nTAGTAG'),'2015-01-05')

    def test_xml_matches_legacy_economics(self):
        self.assertEqual(parse_pcf(xml_pcf(),'2015-01-05'),parse_pcf(legacy(),'2015-01-05'))

    def test_wrong_xml_namespace_cash_or_component_count_rejected(self):
        raw=xml_pcf()
        for bad in [raw.replace(b'http://ts.szse.cn/Fund',b'http://example.invalid'),
                    raw.replace(b'<CreationCashSubstitute>100',b'<CreationCashSubstitute>99'),
                    raw.replace(b'<ComponentShare>0',b'<ComponentShare>1'),
                    raw.replace(b'<UnderlyingSecurityIDSource>102',b'<UnderlyingSecurityIDSource>101'),
                    raw.replace(b'</Components>',b'<Component /></Components>')]:
            with self.subTest(bad=bad[:30]),self.assertRaises(ValueError):parse_pcf(bad,'2015-01-05')


class IncomeCalendarTests(unittest.TestCase):
    sessions=['2016-12-28','2016-12-29','2016-12-30','2017-01-03']
    observed=sessions+['2016-12-31','2017-01-02']

    def test_year_end_parts_cover_each_calendar_day_once(self):
        p=income_periods(self.sessions,self.observed,'2016-12-28','2017-01-03')
        self.assertEqual(sum(x['days'] for x in p),7)
        self.assertEqual([(x['start'],x['end']) for x in p if x['days']>1],
                         [('2017-01-01','2017-01-02')])

    def test_missing_open_day_is_not_holiday_income(self):
        with self.assertRaises(ValueError):
            income_periods(self.sessions,[x for x in self.observed if x!='2016-12-29'],
                           '2016-12-28','2017-01-03')

    def test_partial_non_year_end_closed_run_is_rejected(self):
        with self.assertRaises(ValueError):
            income_periods(['2015-10-08'],['2015-10-03','2015-10-07','2015-10-08'],
                           '2015-10-01','2015-10-08')

    def test_duplicate_observation_rejected(self):
        with self.assertRaises(ValueError):
            income_periods(self.sessions,self.observed+['2016-12-31'],
                           '2016-12-28','2017-01-03')

    def test_unordered_or_invalid_trading_calendar_rejected(self):
        for sessions in [list(reversed(self.sessions)),self.sessions+['wrong-date']]:
            with self.subTest(sessions=sessions),self.assertRaises(ValueError):
                income_periods(sessions,self.observed,'2016-12-28','2017-01-03')

    def test_seven_day_identity_detects_duplicate_holiday_income(self):
        periods=income_periods(self.sessions,self.observed,'2016-12-28','2017-01-03')
        rows={p['end']:{'incomeUnit':str(Decimal('.7')*p['days']),'incomeRatio':'2.555%'} for p in periods}
        self.assertEqual(len(check_income_identities(rows,periods,['2017-01-03'])),1)
        rows['2017-01-02']['incomeUnit']='2.1'
        with self.assertRaises(ValueError):
            check_income_identities(rows,periods,['2017-01-03'])

    def test_source_precision_tolerance_is_not_unbounded(self):
        periods=income_periods(self.sessions,self.observed,'2016-12-28','2017-01-03')
        rows={p['end']:{'incomeUnit':str(Decimal('.7')*p['days']),'incomeRatio':'2.555'} for p in periods}
        rows['2017-01-03']['incomeRatio']='2.556'
        with self.assertRaises(ValueError):
            check_income_identities(rows,periods,['2017-01-03'])

    def test_negative_income_is_preserved_in_consistency_check(self):
        periods=income_periods(self.sessions,self.observed,'2016-12-28','2017-01-03')
        rows={p['end']:{'incomeUnit':str(-Decimal('.7')*p['days']),'incomeRatio':'-2.555'} for p in periods}
        self.assertEqual(len(check_income_identities(rows,periods,['2017-01-03'])),1)


if __name__=='__main__':
    unittest.main()
