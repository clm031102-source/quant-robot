import unittest
from decimal import Decimal
from quant_robot.research.cash_carry_diagnostic import annual_observation, summarize


def pcf(**changes):
    p=dict(creation=True,redemption=True,cash_in=Decimal(100),cash_out=Decimal(100),
           caps={'NetCreationLimit':Decimal(100000),'NetRedemptionLimit':Decimal(100000),
                 'NetCreationLimitPerUser':Decimal(0),'CreationLimitPerUser':Decimal(0)})
    p.update(changes)
    return p


class CashCarryDiagnosticTests(unittest.TestCase):
    def test_small_account_fee_and_calendar_rounding_allowance(self):
        r=annual_observation(pcf(),pcf(),Decimal(200),365,5,Decimal('.01'))
        self.assertEqual(r['shares'],9)
        self.assertEqual(r['entry_debit_CNY'],905)
        self.assertEqual(r['pro_rata_income_CNY'],18)
        self.assertEqual(r['modeled_net_PnL_CNY'],4.35)

    def test_zero_flat_fee_uses_ten_whole_shares(self):
        r=annual_observation(pcf(),pcf(),Decimal(200),365,0,0)
        self.assertEqual(r['shares'],10)
        self.assertEqual(r['entry_debit_CNY'],1000)
        self.assertEqual(r['modeled_net_PnL_CNY'],20)

    def test_denied_entry_is_zero_unfilled_not_fee_loss(self):
        r=annual_observation(pcf(creation=False),pcf(),Decimal(200),365,5,Decimal('.01'))
        self.assertEqual((r['shares'],r['modeled_net_PnL_CNY']),(0,0))

    def test_future_exit_failure_cannot_rewrite_entry_as_zero_fill(self):
        with self.assertRaises(ValueError):
            annual_observation(pcf(),pcf(redemption=False),Decimal(200),365,5,Decimal('.01'))

    def test_disclosed_capacity_constraint_applies_before_entry(self):
        r=annual_observation(pcf(caps={'NetCreationLimit':Decimal(800)}),pcf(),Decimal(200),365,5,0)
        self.assertEqual(r['shares'],0)  # Nine shares exceed1%of800.

    def test_negative_income_remains_an_obligation(self):
        r=annual_observation(pcf(),pcf(),Decimal(-200),365,5,Decimal('.01'))
        self.assertEqual(r['modeled_net_PnL_CNY'],-31.65)

    def test_invalid_cost_days_and_income_rejected(self):
        for amount,days,fee,allowance in [(200,0,5,0),(200,365,-1,0),('NaN',365,5,0),(200,365,5,-1)]:
            with self.subTest(case=(amount,days,fee,allowance)),self.assertRaises(ValueError):
                annual_observation(pcf(),pcf(),amount,days,fee,allowance)

    def test_conditional_pass_is_never_profitability_certification(self):
        rows=[{'entry_year':y,'shares':9,'modeled_net_PnL_CNY':10.0} for y in range(2015,2024)]
        r=summarize(rows)
        self.assertTrue(r['conditional_cash_screen_passed'])
        self.assertEqual(r['block_interval_mean_PnL_CNY'],[10.0,10.0])
        self.assertFalse(r['net_positive_EV_verified'])

    def test_zeros_are_not_wins_and_missing_year_is_not_dropped(self):
        rows=[{'entry_year':y,'shares':9,'modeled_net_PnL_CNY':0.0} for y in range(2015,2024)]
        self.assertFalse(summarize(rows)['conditional_cash_screen_passed'])
        with self.assertRaises(ValueError):summarize(rows[:-1])


if __name__=='__main__':unittest.main()
