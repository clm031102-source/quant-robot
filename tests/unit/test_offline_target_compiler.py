from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_order_timeouts import timeout_policy


def target(book, key='target-one', **changes):
    return {**{'schema_version':1,'mode':'offline_fixture_only','client_intent_id':key,'idempotency_key':'key-'+key,
        'strategy_id':'fixture','strategy_version':'1','case_id':'synthetic-case',
        'signal_timestamp':NOW.isoformat(),'source_as_of':(NOW-timedelta(minutes=1)).isoformat(),
        'source_ref':'synthetic-signal','source_fingerprint':'a'*64,
        'policy_fingerprint':book.snapshot()['admission_policy_fingerprint'],
        'symbol':SYMBOL,'exchange':'SSE','price_basis_id':'initial_raw',
        'target_notional_cny':'1000','limit_price':'4','max_slippage_bps':'10',
        'expires_at':(NOW+timedelta(minutes=2)).isoformat()},**changes}


def create_target_book(path, *, cash='10000', positions=None, sellable=None, minimum='5', legacy=False):
    cfg={**policy(),'capital_limit_cny':'10000','schema_version':2,'max_drawdown':'.08'}
    if legacy:
        cfg.pop('max_drawdown')
        cfg['schema_version']=1
    book=OfflineOrderJournal.create(path,initial_cash=cash,initial_positions=positions or {},
        commission_bps='5',minimum_commission=minimum,admission_policy=cfg,timeout_policy=timeout_policy())
    packet=context(book)
    packet.update(instruments={code:instrument(code) for code in (SYMBOL,OTHER)},
        sellable_positions=positions or {} if sellable is None else sellable)
    book.begin_session(packet,clock=lambda:NOW)
    return book


class OfflineTargetCompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index=0

    def book(self, **kwargs):
        self.index+=1
        book=create_target_book(Path(self.temp.name)/f'book-{self.index}.sqlite',**kwargs)
        self.addCleanup(book.close)
        return book

    def admit(self, book, request=None, packet=None):
        return book.admit_target(request or target(book),packet or context(book),clock=lambda:NOW)

    def test_target_compiles_and_admits_with_frozen_source_policy_and_actual_costs(self):
        book=self.book()
        self.admit(book)
        snap=book.snapshot()
        order=snap['orders']['target-one']
        self.assertEqual(order['quantity'],200)
        self.assertEqual(Decimal(snap['reserved_cash']),805)
        compiled=order['admission']['target_compilation']
        self.assertEqual(compiled['target']['case_id'],'synthetic-case')
        self.assertEqual(compiled['target']['source_fingerprint'],'a'*64)
        self.assertEqual(compiled['target']['policy_fingerprint'],snap['admission_policy_fingerprint'])
        self.assertEqual(Decimal(compiled['commission_bps']),5)
        self.assertEqual(Decimal(compiled['minimum_commission']),5)
        self.assertFalse(compiled['source_quality_verified'])
        self.assertFalse(snap['executable'])

    def test_minimum_fee_is_reserved_before_deciding_affordable_lots(self):
        book=self.book(cash='1000')
        packet=context(book)
        packet['quotes'][SYMBOL].update(bid='5',ask='5')
        self.admit(book,target(book,limit_price='5'),packet)
        self.assertEqual(book.snapshot()['orders']['target-one']['quantity'],100)
        self.assertEqual(Decimal(book.snapshot()['reserved_cash']),505)

    def test_existing_holdings_and_pending_buys_consume_the_same_fixed_budget(self):
        book=self.book(positions={SYMBOL:37})
        self.admit(book)
        self.assertEqual(book.snapshot()['orders']['target-one']['quantity'],200)
        book2=self.book()
        book2.admit(intent('existing'),context(book2),clock=lambda:NOW)
        self.admit(book2)
        self.assertEqual(book2.snapshot()['orders']['target-one']['quantity'],100)
        with self.assertRaisesRegex(ValueError,'lot|covered'):
            self.admit(book2,target(book2,'third'))

    def test_other_order_cash_reservations_are_not_spent_again(self):
        book=self.book(cash='1000')
        book.admit(intent('other',code=OTHER),context(book),clock=lambda:NOW)
        self.admit(book)
        self.assertEqual(book.snapshot()['orders']['target-one']['quantity'],100)
        self.assertEqual(Decimal(book.snapshot()['reserved_cash']),810)
        calculation=book.snapshot()['orders']['target-one']['admission']['target_compilation']
        self.assertEqual(Decimal(calculation['post_order_gross_committed_exposure_cny']),800)
        self.assertEqual(Decimal(calculation['post_order_committed_position_cny']),400)

    def test_partial_fill_and_remaining_reservation_are_counted_once(self):
        book=self.book(cash='1000')
        book.admit(intent('pending'),context(book),clock=lambda:NOW)
        book.fill('pending','partial',40,'4')
        self.admit(book)
        snap=book.snapshot()
        self.assertEqual(snap['orders']['target-one']['quantity'],100)
        self.assertEqual(Decimal(snap['cash']),835)
        self.assertEqual(Decimal(snap['reserved_cash']),645)
        self.assertEqual(Decimal(snap['available_cash']),190)

    def test_pending_sells_and_locked_shares_leave_explicit_target_shortfall(self):
        book=self.book(positions={SYMBOL:237},sellable={SYMBOL:137})
        book.admit(intent('selling',side='SELL',quantity=100),context(book),clock=lambda:NOW)
        self.admit(book,target(book,target_notional_cny='0'))
        order=book.snapshot()['orders']['target-one']
        self.assertEqual(order['quantity'],37)
        calculation=order['admission']['target_compilation']
        self.assertEqual(calculation['position_quantity_if_all_same_side_orders_fill'],100)
        self.assertEqual(Decimal(calculation['target_gap_at_known_mark_cny']),-400)
        self.assertEqual(calculation['sellable_quantity_before'],37)

    def test_callers_cannot_rewrite_committed_target_or_context(self):
        book=self.book()
        request,packet=target(book),context(book)
        self.admit(book,request,packet)
        before=book.snapshot()['orders']['target-one']['admission']
        request['source_ref']='changed'
        packet['quotes'][SYMBOL]['ask']='99'
        snapshot=book.snapshot()
        snapshot['orders']['target-one']['admission']['target_compilation']['target']['case_id']='changed'
        self.assertEqual(book.snapshot()['orders']['target-one']['admission'],before)

    def test_sell_reduction_uses_sellable_shares_and_preserves_odd_lot_liquidation(self):
        book=self.book(positions={SYMBOL:200})
        self.admit(book,target(book,target_notional_cny='400'))
        order=book.snapshot()['orders']['target-one']
        self.assertEqual((order['side'],order['quantity']),('SELL',100))
        odd=self.book(positions={SYMBOL:137})
        self.admit(odd,target(odd,target_notional_cny='0'))
        self.assertEqual(odd.snapshot()['orders']['target-one']['quantity'],137)
        locked=self.book(positions={SYMBOL:100},sellable={})
        with self.assertRaisesRegex(ValueError,'sellable'):
            self.admit(locked,target(locked,target_notional_cny='0'))

    def test_opposite_pending_order_requires_resolution_before_new_rebalance(self):
        book=self.book(positions={SYMBOL:100})
        book.admit(intent('pending'),context(book),clock=lambda:NOW)
        with self.assertRaisesRegex(ValueError,'pending|outstanding'):
            self.admit(book,target(book,target_notional_cny='0'))
        self.assertNotIn('target-one',book.snapshot()['orders'])

    def test_tick_rounding_preserves_buy_ceiling_and_sell_floor(self):
        book=self.book()
        self.admit(book,target(book,limit_price='4.0009'))
        self.assertEqual(Decimal(book.snapshot()['orders']['target-one']['limit_price']),Decimal('4'))
        seller=self.book(positions={SYMBOL:200})
        self.admit(seller,target(seller,target_notional_cny='0',limit_price='4.0001'))
        self.assertEqual(Decimal(seller.snapshot()['orders']['target-one']['limit_price']),Decimal('4.001'))

    def test_compiled_quantity_and_limit_are_not_rewritten_at_dispatch(self):
        book=self.book()
        self.admit(book)
        before=book.snapshot()['orders']['target-one']['admission']['intent']
        packet=context(book)
        packet['quotes'][SYMBOL].update(bid='4.2',ask='4.2')
        book.prepare_dispatch('target-one','send',packet,clock=lambda:NOW)
        self.assertEqual(book.snapshot()['orders']['target-one']['admission']['intent'],before)
        self.assertEqual(book.snapshot()['orders']['target-one']['filled_quantity'],0)

    def test_missing_identity_clock_source_or_basis_is_not_inferred(self):
        book=self.book()
        for index,field in enumerate(('case_id','signal_timestamp','source_as_of','source_ref','source_fingerprint','price_basis_id')):
            request=target(book,str(index))
            request.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):self.admit(book,request)
        self.assertEqual(book.snapshot()['orders'],{})

    def test_future_unknown_basis_policy_and_unregistered_input_fields_refuse(self):
        book=self.book()
        changes=[{'source_as_of':(NOW+timedelta(seconds=1)).isoformat()},
            {'signal_timestamp':(NOW+timedelta(seconds=1)).isoformat()}, {'source_fingerprint':'bad'},
            {'policy_fingerprint':'b'*64},{'price_basis_id':'unknown'}, {'mode':'real'},
            {'later_prices':[4,5]},{'target_notional_cny':'1001'}, {'target_notional_cny':True},
            {'target_notional_cny':'NaN'},{'signal_timestamp':'2026-09-14'}]
        for index,change in enumerate(changes):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.admit(book,target(book,str(index),**change))
        self.assertEqual(book.snapshot()['orders'],{})

    def test_rejected_target_identity_is_consumed_and_cannot_be_repurposed(self):
        book=self.book()
        with self.assertRaises(ValueError):self.admit(book,target(book,target_notional_cny='1'))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.admit(book,target(book,target_notional_cny='1000'))

    def test_legacy_policy_and_existing_risk_stop_cannot_be_bypassed(self):
        legacy=self.book(legacy=True)
        with self.assertRaisesRegex(ValueError,'version|v2|drawdown'):
            self.admit(legacy)
        stopped=self.book(cash='600',positions={SYMBOL:100})
        packet=context(stopped)
        packet['quotes'][SYMBOL].update(bid='3.2',ask='3.2')
        stopped.record_valuation(packet,clock=lambda:NOW)
        with self.assertRaisesRegex(ValueError,'stop'):
            self.admit(stopped)
