import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.daily_ops import build_daily_ops_pack, write_daily_ops_pack


def synthetic_pack(metrics, limit=-0.08):
    return build_daily_ops_pack(
        {'selected_candidate': {'case_id': 'synthetic', 'market': 'CN_ETF',
                                'factor_name': 'momentum_2', 'promotion_status': 'paper_ready'}},
        {'blocker_register': []},
        {'signal_date': '2024-01-08', 'as_of_date': '2024-01-08',
         'rebalance_plan': [{'asset_id': 'CN_ETF_XSHG_510300', 'market': 'CN_ETF',
                             'estimated_quantity_delta': 100, 'target_weight': 0.1, 'delta_value': 500}]},
        {'metrics': metrics, 'fills': [], 'guard_events': [], 'execution_events': []},
        run_date='2024-01-09', max_drawdown_limit=limit,
    )


class DailyOpsRiskEvidenceTests(unittest.TestCase):
    def test_missing_and_invalid_drawdown_do_not_issue_tickets(self):
        inputs = [{}, None, [], {'max_equity_drawdown': None}]
        inputs += [{'max_equity_drawdown': value} for value in (
            True, False, 'bad', 'nan', float('nan'), float('inf'), -float('inf'), 0.1, -1.01,
        )]
        for metrics in inputs:
            with self.subTest(metrics=metrics):
                pack = synthetic_pack(metrics)
                self.assertEqual(pack['decision']['status'], 'blocked')
                self.assertFalse(pack['decision']['paper_trading_allowed'])
                self.assertEqual(pack['advisory_tickets'], [])
                self.assertIsNone(pack['risk']['max_equity_drawdown'])
                self.assertIsNone(pack['risk_policy']['max_drawdown_breached'])
                self.assertIn(pack['risk_policy']['drawdown_evidence_status'], ('missing', 'invalid'))
                json.dumps(pack, allow_nan=False)

    def test_explicit_zero_and_threshold_are_valid_values(self):
        for drawdown in (0, -0.08, '0.0'):
            with self.subTest(drawdown=drawdown):
                pack = synthetic_pack({'max_equity_drawdown': drawdown})
                self.assertEqual(pack['decision']['status'], 'paper_ready')
                self.assertEqual(pack['risk_policy']['drawdown_evidence_status'], 'value_valid')
                self.assertFalse(pack['risk_policy']['max_drawdown_breached'])

    def test_valid_breaching_value_retains_loss_blocker(self):
        pack = synthetic_pack({'max_equity_drawdown': -0.081})
        self.assertIn('risk_max_drawdown_breach', pack['decision']['blocking_reasons'])
        self.assertEqual(pack['advisory_tickets'], [])
        self.assertTrue(pack['risk_policy']['max_drawdown_breached'])

    def test_invalid_policy_threshold_is_rejected(self):
        for limit in (None, True, False, 'bad', 'nan', float('nan'), float('inf'), -1.01, 1.01):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'max_drawdown_limit'):
                synthetic_pack({'max_equity_drawdown': -0.01}, limit)

    def test_written_unknown_drawdown_stays_unknown_and_ticket_file_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = synthetic_pack({})
            write_daily_ops_pack(tmp, pack)
            result = json.loads((Path(tmp) / 'daily_ops_pack.json').read_text(encoding='utf-8'))
            self.assertIsNone(result['risk']['max_equity_drawdown'])
            self.assertIn('Max equity drawdown: unknown', result['markdown'])
            self.assertEqual(len((Path(tmp) / 'daily_ops_tickets.csv').read_text(encoding='utf-8').splitlines()), 1)
