import json
import unittest
from unittest.mock import patch
from quant_robot.research.cash_carry_income_repair import normalize_value, calculate


class CashCarryIncomeRepairTests(unittest.TestCase):
    def test_exact_closed_day_annotation_preserves_signed_amount(self):
        self.assertEqual(normalize_value('1.5748(节假日期间)', closed=True), ('1.5748', True))
        self.assertEqual(normalize_value('-0.1234(节假日期间)', closed=True), ('-0.1234', True))
        self.assertEqual(normalize_value('1.0000', closed=False), ('1.0000', False))

    def test_unknown_annotation_or_invalid_amount_is_not_silently_stripped(self):
        for value in ['1.0000(unknown)', '1.00(节假日期间)', 'NaN(节假日期间)',
                      '1.0000(节假日期间)extra', '1.0000(节假日期间)(节假日期间)', '--']:
            with self.subTest(value=value), self.assertRaises(ValueError): normalize_value(value, closed=True)

    def test_open_session_cannot_have_closed_period_annotation(self):
        with self.assertRaises(ValueError): normalize_value('1.0000(节假日期间)', closed=False)

    def test_input_bytes_unchanged_and_fixed_original_calculation_receives_only_normalization(self):
        snapshots={'proposal':b'{}'}
        for y in range(2015,2025):
            snapshots[f'income_{y}']=json.dumps({'data':{'data':[
                {'navDate':f'{y}-01-04','incomeUnit':'1.5748(节假日期间)','incomeRatio':'3.000'}]}}).encode()
        before=snapshots.copy()
        with patch('quant_robot.research.cash_carry_income_repair._calendar_and_intervals',return_value=([],[])),\
                patch('quant_robot.research.cash_carry_income_repair.EXPECTED_ANNOTATIONS',10),\
                patch('quant_robot.research.cash_carry_income_repair.original_calculate',return_value={'synthetic':True}) as call:
            result=calculate(snapshots)
        self.assertEqual(snapshots,before)
        self.assertEqual(result['format_repair']['annotations_normalized'],10)
        row=json.loads(call.call_args.args[0]['income_2015'])['data']['data'][0]
        self.assertEqual(row,{'navDate':'2015-01-04','incomeUnit':'1.5748','incomeRatio':'3.000'})

    def test_wrong_annotation_inventory_stops_before_original_calculation(self):
        snapshots={'proposal':b'{}',**{f'income_{y}':b'{"data":{"data":[]}}' for y in range(2015,2025)}}
        with patch('quant_robot.research.cash_carry_income_repair._calendar_and_intervals',return_value=([],[])),\
                patch('quant_robot.research.cash_carry_income_repair.original_calculate') as call:
            with self.assertRaisesRegex(ValueError,'annotation inventory'):calculate(snapshots)
        call.assert_not_called()
