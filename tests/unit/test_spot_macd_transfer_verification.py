"""Independent, hand-specified cash books; no model import or account simulation."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quant_robot.research import spot_macd_transfer_verification as audit


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


class SpotRecordedVerificationTests(unittest.TestCase):
    """No orders are asserted: every independently declared wallet remains cash.

    Such books test accounting, not whether a strategy should have traded.
    Dates match the adapter shape, but every value and source is artificial.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.root = cls.base / "books"
        cls.root.mkdir()
        cls.registration = "a" * 64
        nature = "artificial_protocol_fixture"
        fixture = dict(artifact_type="claimed_spot_transfer_normalized_input_v1",
            asset_id="BTCUSDT", market="spot", source_nature=nature, warmup_days=366,
            daily=[dict(date=(date(2018, 1, 1)+timedelta(days=i)).isoformat(),
                        open="100", high="100", low="100", close="100", volume="1000")
                   for i in range(2192)], execution=[])
        curve, observations = [], []
        for i in range(1827):
            day = (date(2019, 1, 2)+timedelta(days=i)).isoformat()
            fixture["execution"].append(dict(date=day, open_time=day+"T00:03:00Z",
                close_time=day+"T00:03:59.999Z", open="100", volume="1000"))
            curve.append(dict(index=i, date=day, NAV="1000", PnL="0", cash="1000", BTC="0",
                economic_flat=True, mark="100", active_exposure=False, positive_inventory=False,
                kind="terminal_partial_interval" if i == 1826 else "completed_daily"))
            if i == 1826:
                curve[-1]["mark_NAV"] = "1000"
            phases = ["00:03_prefill"]
            if i != 1826:
                phases.append("next00:02_completed_close")
            for phase in phases:
                observations.append(dict(index=i, phase=phase, price="100", cash="1000", BTC="0",
                    NAV="1000", peak="1000", DD="0", daily_loss="0", day_active=False,
                    fresh_DD_cross=False, DD_event=False, daily_event=False, trigger=False))
        provenance = dict(source_nature=nature, method_sha256=audit.METHOD_SHA,
                          description="Hand-specified constant prices and zero orders; no exchange source.")
        normalized = dict(fixture=fixture, provenance=provenance)
        cls.identity = dict(evidence_class="artificial_historical_adapter_test", source_nature=nature,
            registration_sha256=cls.registration, normalized_input_sha256=digest(normalized),
            provenance_sha256=digest(provenance), method_sha256=audit.METHOD_SHA,
            historical_returns_computed=False, qualified=False, real_forward_days_added=0)
        cls.decoded = cls.persist("decoded.json", normalized)
        summary = dict(initial_cash="1000", cash="1000", remaining_BTC="0", net_PnL="0",
            sampled_DD_before_haircut="0", sampled_DD_including_terminal_haircut="0",
            buy_fee_BTC="0", sell_fee_USDT="0", buy_fee_quote_reporting="0", quote_rounding_cost="0",
            strict_completed_episodes=0, terminal_economic_flat=True, exact_inventory_zero=True,
            terminal_strict_unsettled=False, execution_capacity_unverified=False, common_valid=True,
            remaining_mark_value="0", mark_NAV="1000", terminal_evaluation_NAV="1000",
            dust_fully_haircut_cash_terminal="1000", pending_exit=None, average_cash="1000",
            fill_count=0, rejection_count=0, full_cash_days=1827, nontradable_days=1827,
            account_reconciled=True, tradable_exit_episodes=0, skipped_entry_cycles=0)
        cls.account_refs, cls.account_values = {}, {}
        for fee in (5, 10, 20):
            for slip in (0, 10, 30):
                for role in ("strategy", "holding", "cash"):
                    key = f"fee{fee}_slip{slip}/{role}"
                    account = dict(**cls.identity, artifact_type="conditional_historical_spot_account_v1",
                        fee_bps=fee, slippage_bps=slip, role=role, fills=[], lots=[], risk_records=[], cycles=[],
                        rejections=[], capacity_failures=[], observed_wallets=observations,
                        daily_NAV=curve, summary=summary)
                    cls.account_values[key] = account
                    cls.account_refs[key] = cls.persist(key.replace("/", "_")+".json", account)
        keys = [f"fee{f}_slip{s}/{endpoint}" for f in (5, 10, 20) for s in (0, 10, 30)
                for endpoint in ("net", "minus_holding")]
        # Every replication is mathematically zero; do not construct bootstrap indices here.
        cls.zero_replication_sha = hashlib.sha256(bytes(5000*18*8)).hexdigest()
        cls.statistics_value = dict(**cls.identity, artifact_type="conditional_historical_spot_statistics_v1",
            N=1827, replications=5000, block=20, starts_per_replication=92, seed=20261107,
            shared_indices_for_all18=True, units="USDT/observed interval", statistic="arithmetic_mean",
            endpoint_keys=keys, final_interval_is_partial=True,
            replicate_means_sha256=cls.zero_replication_sha,
            lower={key: 0.0 for key in keys}, observed_means={key: 0.0 for key in keys})
        cls.statistics = cls.persist("statistics.json", cls.statistics_value)
        cls.first_key = next(iter(cls.account_refs))

    @classmethod
    def persist(cls, relative, value):
        raw = encoded(value)
        (cls.root/relative).write_bytes(raw)
        return dict(path=relative, sha256=hashlib.sha256(raw).hexdigest())

    def verify(self, *, accounts=None, decoded=None, statistics=None):
        return audit.verify_recorded_accounts(self.root, decoded or self.decoded,
            accounts or self.account_refs, statistics or self.statistics, self.registration)

    @contextmanager
    def altered_first(self, change):
        original = self.account_refs[self.first_key]
        path = self.root/original["path"]
        raw = path.read_bytes()
        value = json.loads(raw)
        change(value)
        refs = dict(self.account_refs)
        refs[self.first_key] = self.persist(original["path"], value)
        try:
            yield refs
        finally:
            path.write_bytes(raw)

    def test_complete_handwritten_cash_books_and_zero_statistics(self):
        result = self.verify()
        self.assertTrue(result["accounting_passed"])
        self.assertEqual((result["accounts"], result["intervals"], result["observations"]),
                         (27, 27*1827, 27*(1827*2-1)))
        self.assertEqual(result["statistics"]["replicate_means_sha256"], self.zero_replication_sha)
        self.assertEqual(result["source_nature"], "artificial_protocol_fixture")
        for field in ("model_replays", "signal_recomputations", "raw_market_sources_opened",
                      "research_count_delta", "real_forward_added"):
            self.assertEqual(result[field], 0)
        self.assertFalse(result["qualified"])

    def test_rehashed_fee_identity_NAV_and_terminal_corruption_is_rejected(self):
        cases = {
            "fee": lambda a: a["summary"].update(buy_fee_BTC="0.00001"),
            "identity": lambda a: a.update(source_nature="retained_official_history"),
            "NAV": lambda a: a["daily_NAV"][0].update(NAV="1001"),
            "terminal": lambda a: a["summary"].update(mark_NAV="1001"),
        }
        for label, change in cases.items():
            with self.subTest(label=label), self.altered_first(change) as refs:
                self.assertNotEqual(refs[self.first_key]["sha256"], self.account_refs[self.first_key]["sha256"])
                with self.assertRaises(ValueError):
                    self.verify(accounts=refs)

    def test_fill_indices_cannot_be_ignored_outside_the_window_or_coerced(self):
        for index in (-1, 1827, False):
            with self.subTest(index=index), self.altered_first(lambda a: a["fills"].append({"index": index})) as refs:
                with self.assertRaises(ValueError):
                    self.verify(accounts=refs)
        with self.altered_first(lambda a: a["fills"].extend([{"index": 0}, {"index": 0}])) as refs:
            with self.assertRaises(ValueError):
                self.verify(accounts=refs)

    def test_statistics_cannot_change_seed_or_recorded_replication_digest(self):
        for field, bad in (("seed", 20261108), ("replicate_means_sha256", "b"*64)):
            recorded = deepcopy(self.statistics_value)
            recorded[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit._statistics(self.account_values, recorded)

    def test_reference_boundaries_missing_role_and_bad_hash_are_rejected(self):
        outside = self.base/"outside.json"
        outside.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "outside"):
            self.verify(decoded=dict(path="../outside.json", sha256=hashlib.sha256(b"{}").hexdigest()))
        fewer = dict(self.account_refs)
        fewer.pop(self.first_key)
        with self.assertRaisesRegex(ValueError, "27"):
            self.verify(accounts=fewer)
        bad = dict(self.decoded, sha256="b"*64)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.verify(decoded=bad)

    def test_risk_copy_checks_price_trigger_and_boolean_type(self):
        expected = [dict(index=0, phase="00:03_prefill", price=Decimal("100"),
                         DD=Decimal("0.4"), day_active=True, DD_event=True, trigger=True)]
        actual = [dict(index=0, phase="00:03_prefill", price="100", DD="0.4",
                       day_active=True, DD_event=True, trigger=True)]
        audit._compare_observations(expected, actual, "independent_risk_copy")
        for field, bad in (("price", "101"), ("trigger", False), ("DD_event", 1), ("phase", "other")):
            corrupted = deepcopy(actual)
            corrupted[0][field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit._compare_observations(expected, corrupted, "independent_risk_copy")


if __name__ == "__main__":
    unittest.main()
