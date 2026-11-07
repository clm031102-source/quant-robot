import copy
import importlib.util
import sys
import unittest
from dataclasses import FrozenInstanceError
from decimal import getcontext, localcontext
from pathlib import Path
from quant_robot.research import equity_gold_constant_mix as m


class ContextTests(unittest.TestCase):
    def test_context_immutable_and_public_guard_still_rejects_real(self):
        c=m._ExecutionContext()
        with self.assertRaises(FrozenInstanceError):c.assets=('x','y')
        with self.assertRaises(ValueError):m._ExecutionContext(['x','y'])
        f=m.make_fixture(35,[20]);f['assets']=['CN_ETF_XSHG_510300','CN_ETF_XSHG_518880']
        with self.assertRaisesRegex(ValueError,'artificial_identity'):m.run_account(f)

    def test_explicit_historical_test_identity_and_terminal_no_close(self):
        f=m.make_fixture(35,[20]);assets=('CN_ETF_XSHG_510300','CN_ETF_XSHG_518880')
        f['bars']={new:f['bars'][old] for new,old in zip(assets,m.ASSETS)}
        f.update(assets=list(assets),artifact_type='admitted_constant_mix_fixture_v1',
                 source_nature='test_artificial_values_true_calendar')
        f['dates']=[d.replace('2001','2014') for d in f['dates']]
        for a in assets:f['bars'][a][-1].update(close=None,terminal_close_not_observed=True)
        c=m._ExecutionContext(assets,f['source_nature'],True,True,'1'*64,m.digest(f),'2'*64)
        initial=m._context_record(getcontext())
        with localcontext(m.CONTEXT):p=m._prepare(f,context=c)
        out=m._run_prepared(p,'constant_mix',5,10,context=c)
        self.assertEqual(set(out['summary']['terminal_quantities']),set(assets))
        self.assertTrue(out['test_injected_values']);self.assertFalse(out['historical_returns_computed'])
        self.assertEqual(out['registration_sha256'],'1'*64)
        self.assertEqual(out['days'][-1]['marks'],dict.fromkeys(assets,'1.20'))
        self.assertEqual(initial,m._context_record(getcontext()))
        with self.assertRaisesRegex(ValueError,'artificial_identity'):m.run_account(f)

    def test_invalid_numeric_context_does_not_mutate_caller(self):
        f=m.make_fixture(30,[20]);f['bars'][m.ASSETS[0]][0]['open']='bad'
        before=m._context_record(getcontext())
        with self.assertRaises(ValueError):m.run_account(f)
        self.assertEqual(before,m._context_record(getcontext()))

    def test_current_synthetic_output_keys_remain_legacy(self):
        out=m.run_account(m.make_fixture(30,[20]))
        for key in ('registration_sha256','test_injected_values','evidence_class','normalized_input_sha256'):
            self.assertNotIn(key,out)
        self.assertEqual(out['artifact_type'],'artificial_constant_mix_account_v1')


if __name__=='__main__':unittest.main()
