from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_intent_contract import normalize_policy
from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class OfflineDrawdownGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'drawdown.sqlite'

    def create(self, *, cash='600', quantity=100, days=3, legacy=False):
        cfg = {**policy(), 'schema_version':2, 'policy_id':'fixture-drawdown-v2', 'max_drawdown':'0.08',
            'capital_limit_cny':'10000', 'session_dates':[(NOW+timedelta(days=i)).date().isoformat() for i in range(days)]}
        if legacy:
            cfg.pop('max_drawdown')
            cfg['schema_version']=1
        self.book = OfflineOrderJournal.create(self.path,initial_cash=cash,initial_positions={SYMBOL:quantity},
            commission_bps='5',minimum_commission='5',admission_policy=cfg)
        self.addCleanup(lambda:self.book.close())

    def packet(self, price, now=NOW, opening=False):
        packet = context(self.book,now)
        packet['quotes'][SYMBOL].update(bid=str(price),ask=str(price))
        if opening:
            metadata={s:{**instrument(s),'valid_until':(now+timedelta(days=1)).date().isoformat(),
                'adv_as_of':(now-timedelta(days=1)).date().isoformat()} for s in (SYMBOL,OTHER)}
            packet.update(instruments=metadata,sellable_positions=self.book.snapshot()['positions'])
        return packet

    def start(self, price='4', now=NOW):
        return self.book.begin_session(self.packet(price,now,True),clock=lambda:now)

    def value(self, price, now=NOW):
        return self.book.record_valuation(self.packet(price,now),clock=lambda:now)

    def test_policy_v2_requires_explicit_finite_positive_fraction_and_version_is_bound(self):
        good={**policy(),'schema_version':2,'max_drawdown':'0.08'}
        self.assertEqual(normalize_policy(good)['max_drawdown'],'0.08')
        for bad in (None,True,'NaN','Infinity',0,-.08,1,8):
            with self.subTest(value=bad),self.assertRaises(ValueError):
                normalize_policy({**good,'max_drawdown':bad})
        for cfg in ({**policy(),'max_drawdown':'.08'}, {**policy(),'schema_version':2},
                    {**good,'schema_version':True}):
            with self.assertRaises(ValueError):normalize_policy(cfg)

    def test_10000_account_stops_at_cumulative_eight_percent_despite_small_daily_losses(self):
        self.create(cash='9000',quantity=1000,days=17)
        for day in range(17):
            now=NOW+timedelta(days=day)
            opening=Decimal('1')-Decimal('.05')*max(0,day-1)
            self.start(opening,now)
            self.value(Decimal('1')-Decimal('.05')*day,now+timedelta(seconds=1))
            snap=self.book.snapshot()
            self.assertEqual(snap['paused'],day==16)
        guard=snap['drawdown_guard']
        self.assertEqual(Decimal(guard['peak_equity']),10000)
        self.assertEqual(Decimal(guard['book_drawdown']),Decimal('.08'))
        self.assertTrue(guard['stop_latched'])
        self.assertNotIn('daily_loss',snap['portfolio_valuation']['last_valid']['breaches'])

    def test_stop_survives_rebound_restart_next_session_and_operator_release(self):
        self.create()
        self.start()
        self.value('3.6')
        tomorrow=NOW+timedelta(days=1)
        self.start('3.6',tomorrow)
        self.value('3.2',tomorrow)
        self.book.close()
        self.book=OfflineOrderJournal(self.path)
        self.book.set_kill_switch(False,reason='fixture release cannot reset risk')
        self.value('4',tomorrow+timedelta(seconds=1))
        self.start('4',NOW+timedelta(days=2))
        self.assertTrue(self.book.snapshot()['paused'])
        with self.assertRaisesRegex(ValueError,'risk stop'):
            self.book.admit(intent(now=NOW+timedelta(days=2)),context(self.book,NOW+timedelta(days=2)),
                clock=lambda:NOW+timedelta(days=2))

    def test_overnight_threshold_is_observed_at_open_without_new_order(self):
        self.create()
        self.start()
        self.start('3.2',NOW+timedelta(days=1))
        self.assertTrue(self.book.snapshot()['drawdown_guard']['stop_latched'])
        self.assertTrue(self.book.snapshot()['paused'])

    def test_proposed_order_cost_at_threshold_is_rejected_and_persistently_latched(self):
        self.create()
        self.start()
        self.value('3.6')
        tomorrow=NOW+timedelta(days=1)
        self.start('3.6',tomorrow)
        with self.assertRaisesRegex(ValueError,'drawdown'):
            self.book.admit(intent(code=OTHER,now=tomorrow),self.packet('3.25',tomorrow),clock=lambda:tomorrow)
        self.assertEqual(self.book.snapshot()['orders'],{})
        self.assertTrue(self.book.snapshot()['drawdown_guard']['stop_latched'])
        self.assertEqual(Decimal(self.book.snapshot()['drawdown_guard']['projected_drawdown']),Decimal('.08'))

    def test_dispatch_rechecks_drawdown_and_preserves_denied_evidence(self):
        self.create()
        self.start()
        self.value('3.6')
        tomorrow=NOW+timedelta(days=1)
        self.start('3.6',tomorrow)
        self.book.admit(intent(code=OTHER,now=tomorrow),self.packet('3.6',tomorrow),clock=lambda:tomorrow)
        with self.assertRaisesRegex(ValueError,'drawdown'):
            self.book.prepare_dispatch('one','send',self.packet('3.25',tomorrow),clock=lambda:tomorrow)
        self.assertNotIn('dispatch',self.book.snapshot()['orders']['one'])
        self.assertTrue(self.book.snapshot()['drawdown_guard']['stop_latched'])

    def test_missing_quotes_cannot_overwrite_peak_or_clear_stop(self):
        self.create()
        self.start()
        self.value('3.2')
        before=self.book.snapshot()['drawdown_guard']
        packet=self.packet('4')
        packet['quotes']={}
        with self.assertRaises(ValueError):self.book.record_valuation(packet,clock=lambda:NOW)
        self.assertEqual(self.book.snapshot()['drawdown_guard'],before)
        self.value('4')
        self.assertTrue(self.book.snapshot()['paused'])

    def test_old_policy_is_not_reinterpreted_as_a_drawdown_certified_policy(self):
        self.create(legacy=True)
        self.start()
        self.value('3.6')
        self.start('3.6',NOW+timedelta(days=1))
        self.value('3.2',NOW+timedelta(days=1))
        self.assertFalse(self.book.snapshot()['paused'])
        self.assertIsNone(self.book.snapshot()['drawdown_guard'])
        self.assertFalse(self.book.snapshot()['drawdown_guard_configured'])

    def test_cross_day_peak_includes_prior_gains_instead_of_only_initial_cash(self):
        self.create()
        self.start()
        self.value('5')
        tomorrow=NOW+timedelta(days=1)
        self.start('5',tomorrow)
        self.value('4.12',tomorrow)
        guard=self.book.snapshot()['drawdown_guard']
        self.assertEqual(Decimal(guard['peak_equity']),1100)
        self.assertEqual(Decimal(guard['book_drawdown']),Decimal('.08'))
        self.assertGreater(Decimal(guard['book_equity']),1000)
        self.assertTrue(guard['stop_latched'])

    def test_candidate_cost_stop_survives_denial_and_order_reconciliation(self):
        self.create()
        self.start()
        self.value('3.6')
        tomorrow=NOW+timedelta(days=1)
        self.start('3.6',tomorrow)
        with self.assertRaisesRegex(ValueError,'drawdown'):
            self.book.admit(intent(code=OTHER,now=tomorrow),self.packet('3.25',tomorrow),clock=lambda:tomorrow)
        snap=self.book.snapshot()
        self.book.reconcile(snapshot_id='fixture',expected_sequence=snap['sequence'],cash=snap['cash'],
            positions=snap['positions'],orders={})
        self.book.close()
        self.book=OfflineOrderJournal(self.path)
        self.start('4',NOW+timedelta(days=2))
        self.assertTrue(self.book.snapshot()['paused'])
