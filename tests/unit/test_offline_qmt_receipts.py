"""Synthetic protocol cases only; no SDK, client, account or network access."""
from copy import deepcopy
from decimal import Decimal
import unittest

from quant_robot.execution.offline_qmt_receipts import review_qmt_receipts


def expected():
    return dict(mode="offline_fixture_only", session_date="2025-01-06",
                source_ref="fixture:official-qmt-schema", account_id="fixture-account",
                account_type=2, stock_code="510300.SH", order_id=101,
                order_sysid="fixture-contract", order_volume=100, offset_flag=48)


def order(status=53, filled=40):
    return {**{k: v for k, v in expected().items() if k in (
        "account_id", "account_type", "stock_code", "order_id", "order_sysid", "order_volume", "offset_flag")},
        "order_status": status, "traded_volume": filled, "traded_price": 4.0,
        "order_time": 93000, "price_type": 999, "order_remark": "shared-truncated-prefix"}


def trade(trade_id="fill-a", volume=40, amount="160"):
    return {**{k: v for k, v in order().items() if k in (
        "account_id", "account_type", "stock_code", "order_id", "order_sysid", "offset_flag")},
        "traded_id": trade_id, "traded_volume": volume, "traded_price": "4",
        "traded_amount": amount, "traded_time": 93100}


class OfflineQmtReceiptTests(unittest.TestCase):
    def review(self, snapshot=None, trades=None):
        return review_qmt_receipts(expected(), snapshot, trades)

    def test_partial_cancel_preserves_fill_amount_and_is_not_account_reconciliation(self):
        result = self.review(order(), [trade()])
        self.assertEqual(result["projected_status"], "CANCELLED")
        self.assertTrue(result["receipt_quantities_match"])
        self.assertEqual(result["filled_quantity"], 40)
        self.assertEqual(Decimal(result["filled_amount"]), 160)
        self.assertFalse(result["executable"])
        self.assertFalse(result["accounting_verified"])
        self.assertFalse(result["reservation_release_allowed"])
        self.assertFalse(result["automatic_retry_allowed"])

    def test_cancel_wait_does_not_become_terminal(self):
        for status, filled in ((51, 0), (52, 40)):
            with self.subTest(status=status):
                result = self.review(order(status, filled), [trade()] if filled else [])
                self.assertEqual(result["projected_status"], "CANCEL_PENDING")
                self.assertFalse(result["terminal_status_observed"])

    def test_known_statuses_are_distinct_from_unknown_values(self):
        for raw, filled, mapped in ((48,0,"PENDING"),(49,0,"PENDING"),(50,0,"ACCEPTED"),
                (54,0,"CANCELLED"),(55,40,"PARTIAL"),(56,100,"FILLED"),(57,0,"REJECTED")):
            with self.subTest(raw=raw):
                result=self.review(order(raw,filled),[trade(volume=filled,amount=str(filled*4))] if filled else [])
                self.assertEqual(result["projected_status"],mapped)
                self.assertEqual(result["blockers"],[])
        for raw in (255,777):
            result=self.review(order(raw,0),[])
            self.assertEqual(result["projected_status"],"UNKNOWN")
            self.assertIn("unknown_order_status",result["blockers"])

    def test_none_trade_query_is_ambiguous_even_with_zero_fill_terminal_status(self):
        result=self.review(order(54,0),None)
        self.assertIn("trade_query_failed_or_empty",result["blockers"])
        self.assertFalse(result["receipt_quantities_match"])
        self.assertIsNone(result["filled_quantity"])

    def test_missing_order_is_unknown_not_rejected_or_retryable(self):
        result=self.review(None,[])
        self.assertEqual(result["projected_status"],"UNKNOWN")
        self.assertIn("order_observation_unavailable",result["blockers"])
        self.assertFalse(result["automatic_retry_allowed"])

    def test_cumulative_status_cannot_manufacture_missing_fills(self):
        result=self.review(order(56,100),[trade()])
        self.assertEqual(result["filled_quantity"],40)
        self.assertIn("snapshot_references_missing_fills",result["blockers"])
        self.assertFalse(result["receipt_quantities_match"])

    def test_stale_snapshot_cannot_erase_newer_trade_evidence(self):
        result=self.review(order(50,0),[trade()])
        self.assertEqual(result["filled_quantity"],40)
        self.assertIn("snapshot_behind_trade_evidence",result["blockers"])

    def test_duplicate_trade_id_counted_once_but_conflicting_duplicate_is_blocked(self):
        row=trade()
        result=self.review(order(),[row,deepcopy(row)])
        self.assertEqual(result["filled_quantity"],40)
        self.assertEqual(result["duplicate_receipts"],1)
        with self.assertRaisesRegex(ValueError,"conflicting trade identity"):
            self.review(order(),[row,trade(amount="161")])

    def test_same_remark_does_not_override_scope_identity(self):
        for field,value in (("account_id","fixture-other"),("account_type",3),
                ("stock_code","159915.SZ"),("order_id",102),("order_sysid","other"),("offset_flag",49)):
            with self.subTest(field=field):
                row=order();row[field]=value
                with self.assertRaisesRegex(ValueError,"identity mismatch"):
                    self.review(row,[trade()])
                row=trade();row[field]=value
                with self.assertRaisesRegex(ValueError,"identity mismatch"):
                    self.review(order(),[row])

    def test_status_quantity_contradictions_and_overfills_are_reviewed(self):
        for raw,filled in ((56,40),(53,0),(57,40),(54,40),(48,40),(55,100),(52,0)):
            with self.subTest(raw=raw,filled=filled):
                result=self.review(order(raw,filled),[trade(volume=filled,amount=str(filled*4))] if filled else [])
                self.assertIn("status_quantity_inconsistent",result["blockers"])
        result=self.review(order(56,100),[trade(volume=110,amount="440")])
        self.assertIn("trade_quantity_exceeds_intent",result["blockers"])

    def test_receipt_identity_includes_declared_date_and_exchange_scope(self):
        first=self.review(order(),[trade()])
        scope=expected();scope["session_date"]="2025-01-07"
        second=review_qmt_receipts(scope,order(),[trade()])
        self.assertNotEqual(first["receipts"][0]["receipt_key"],second["receipts"][0]["receipt_key"])
        self.assertFalse(second["capture_date_verified"])

    def test_input_is_not_mutated_and_reordered_receipts_have_stable_economic_totals(self):
        a,b=trade(volume=20,amount="80"),trade("fill-b",20,"80")
        scope,snapshot=expected(),order();before=deepcopy((scope,snapshot,a,b))
        first=review_qmt_receipts(scope,snapshot,[a,b]);second=review_qmt_receipts(scope,snapshot,[b,a])
        self.assertEqual((scope,snapshot,a,b),before)
        self.assertEqual(first,second)

    def test_nonfinite_money_boolean_quantity_and_malformed_identity_are_rejected(self):
        for field,value in (("traded_amount","NaN"),("traded_price","Infinity"),
                ("traded_volume",True),("traded_volume",0),("traded_id",""),("traded_time",True)):
            with self.subTest(field=field):
                row=trade();row[field]=value
                with self.assertRaises(ValueError):self.review(order(),[row])
        row=order();row["order_status"]=True
        with self.assertRaises(ValueError):self.review(row,[])

    def test_synthetic_scope_required_and_counter_price_type_is_not_reinterpreted(self):
        scope=expected();scope["mode"]="live"
        with self.assertRaisesRegex(ValueError,"offline_fixture_only"):
            review_qmt_receipts(scope,order(),[trade()])
        result=self.review(order(),[trade()])
        self.assertTrue(result["receipt_quantities_match"])
        self.assertFalse(result["counter_price_type_verified"])
        self.assertIn("fee_cash_position_reconciliation",result["integration_gaps"])

    def test_raw_trade_amount_is_preserved_without_certifying_price_precision(self):
        result=self.review(order(),[trade(amount="159.99")])
        self.assertTrue(result["receipt_quantities_match"])
        self.assertEqual(Decimal(result["filled_amount"]),Decimal("159.99"))
        self.assertFalse(result["amount_price_consistency_verified"])
        self.assertFalse(result["accounting_verified"])

    def test_malformed_scope_or_incomplete_identity_cannot_fall_back_to_remark(self):
        for field,value in (("order_sysid",""),("account_id","123456"),
                ("source_ref","live:receipt"),("session_date","2025-02-30"),("offset_flag",50)):
            with self.subTest(field=field):
                scope=expected();scope[field]=value
                with self.assertRaises(ValueError):review_qmt_receipts(scope,order(),[trade()])
        row=order();row["order_volume"]=200
        with self.assertRaisesRegex(ValueError,"original fixture intent"):
            self.review(row,[trade()])
        for rows in ({},[None]):
            with self.assertRaises(ValueError):self.review(order(),rows)


if __name__ == "__main__":
    unittest.main()
