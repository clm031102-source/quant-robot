"""Artificial-only observer contracts. Never reads a real token or source response."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from quant_robot.ops import future_etf_source_observer as obs
from quant_robot.ops import tushare_fund_daily_batch as batch
from quant_robot.ops import tushare_fund_daily_wire as wire
from quant_robot.research import pm_startup_gate as pm


def plan_fixture(days=None):
    days = days or ["2026-11-09"]
    plan = {"artifact_type": "finite_future_etf_observer_scope_v1", "purpose": obs.SOURCE,
        "limits": deepcopy(obs.LIMITS), "context": deepcopy(obs.CONTEXT), "symbols": list(wire.SYMBOLS),
        "api": wire.API, "fields": ",".join(wire.FIELDS), "created_at": "2026-11-07T00:00:00+00:00",
        "expires_at": days[-1]+"T12:00:00+00:00", "authority_kind": "campaign_72h",
        "slots": [{"date": d, "not_before": d+"T07:30:00+00:00", "deadline": d+"T10:00:00+00:00"} for d in days],
        "request_budget": len(days)*2, "body_byte_budget": len(days)*2*obs.LIMITS["response_bytes"],
        "financial_decode_allowed": False, "qualified": False, "real_forward": 0}
    calendar = {"timezone": "Asia/Shanghai", "session_rows": [{"date": d, "exchange_codes": ["SSE"],
        "daily_observation_not_before_utc": d+"T07:30:00+00:00"} for d in days]}
    return plan, calendar


def response_fixture(request, at):
    # Intentionally artificial numeric tokens, never real market observations.
    raw = json.dumps({"code": 0, "data": {"fields": list(wire.FIELDS), "items": [
        [request["params"]["ts_code"], request["params"]["trade_date"], "1", "2", "1", "1", "3", "4"]]}}).encode()
    return {"body": raw, "error": None, "body_complete": True, "worker_exit_confirmed": True,
        "received_bytes": len(raw), "received_bytes_lower_bound": len(raw),
        "attempts_started": 1, "attempts_started_lower_bound": 1, "request_started_at": at,
        "headers_received_at": at, "body_completed_at": at,
        "headers": {"content-type": "application/json"}, "http_status": 200, "failed_at": None}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.plan, self.calendar = plan_fixture()
        self.at = "2026-11-09T08:00:00+00:00"
        self.clock = lambda: obs.instant(self.at)
        self.calls = []

    def exchange(self, request, token, timeout):
        self.assertEqual(token, "ARTIFICIAL_TEST_SENTINEL")
        self.assertLessEqual(timeout, 40)
        self.calls.append(request)
        return response_fixture(request, self.at)

    def run_pair(self, **overrides):
        args = dict(clock=self.clock, exchange=self.exchange)
        args.update(overrides)
        return obs.capture_synthetic(self.plan, self.calendar, "2026-11-09", self.folder, **args)

    def test_one_pair_exact_day_fields_and_opaque_tokens_not_forward(self):
        result = self.run_pair()
        self.assertEqual(result["status"], "completed_structure_only")
        self.assertEqual(result["attempts_started"], 2)
        self.assertEqual(result["evidence_class"], obs.ARTIFICIAL)
        self.assertFalse(result["qualified"]); self.assertEqual(result["real_forward"], 0)
        self.assertEqual([r["params"] for r in self.calls], [
            {"ts_code": s, "trade_date": "20261109"} for s in wire.SYMBOLS])
        for r in self.calls:
            self.assertEqual(r["fields"], ",".join(wire.FIELDS))
        receipt = json.loads(Path(result["receipts"][0]["receipt"]["path"]).read_bytes())
        self.assertEqual(receipt["exposure"], "complete_raw_structure_observed")
        self.assertFalse(receipt["financial_numeric_values_decoded"])
        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["headers"], {"content-type": "application/json"})
        self.assertIsNone(receipt["failed_at"])
        self.assertFalse(receipt["originals_not_retained_due_safety_screen"])
        with self.assertRaises(wire.WireError):
            float(wire.decode_opaque(b'{"n":1}')["n"])
        summary = obs.paired_coverage(self.plan, self.calendar,
            [batch.reference(self.folder/"2026-11-09/outcome.json")], expected_scope_sha256=obs._digest(self.plan))
        self.assertEqual(summary["complete_paired_sessions"], 0)

    def test_day_claim_prevents_new_scope_replay_and_any_second_leg_retry(self):
        self.run_pair()
        self.plan["created_at"] = "2026-11-06T00:00:00+00:00"
        with self.assertRaises(FileExistsError):
            self.run_pair()
        self.assertEqual(len(self.calls), 2)

    def test_failure_consumes_pair_and_retains_first_leg_without_retry(self):
        def exchange(request, token, timeout):
            response = self.exchange(request, token, timeout)
            if len(self.calls) == 2:
                response["error"] = "HTTP_status_rejected"
                response["http_status"] = 403
                response["failed_at"] = self.at
            return response
        result = self.run_pair(exchange=exchange)
        self.assertEqual(result["status"], "failed_consumed")
        self.assertTrue(result["receipts"][0]["complete"])
        self.assertFalse(result["receipts"][1]["complete"])
        receipt = json.loads(Path(result["receipts"][1]["receipt"]["path"]).read_bytes())
        self.assertEqual(receipt["http_status"], 403)
        self.assertEqual(receipt["failed_at"], self.at)
        self.assertEqual(receipt["headers"], {"content-type": "application/json"})
        with self.assertRaises(FileExistsError):
            self.run_pair()
        self.assertEqual(len(self.calls), 2)

    def test_unknown_exit_never_hashes_body_or_claims_zero_and_halts_later_days(self):
        class Poison:
            def __bytes__(self):
                raise AssertionError("unknown worker body touched")
        def exchange(request, token, timeout):
            return {"worker_exit_confirmed": False, "body": Poison(), "error": None,
                "attempts_started": 0, "received_bytes": 0, "attempts_started_lower_bound": 0,
                "received_bytes_lower_bound": 0}
        result = self.run_pair(exchange=exchange)
        self.assertIsNone(result["attempts_started"]); self.assertIsNone(result["received_bytes"])
        self.assertEqual(result["reserved_request_upper_bound"], 1)
        receipt = json.loads(Path(result["receipts"][0]["receipt"]["path"]).read_bytes())
        self.assertIsNone(receipt["raw"])
        self.assertEqual(receipt["exposure"], "possible_exposure_unknown")
        self.assertTrue((self.folder/"halt.json").is_file())
        with self.assertRaisesRegex(obs.ObservationError, "unconfirmed_worker"):
            self.run_pair()

    def test_transport_throw_preserves_consumption_unknown_counts_and_no_exception_text(self):
        result = self.run_pair(exchange=Mock(side_effect=RuntimeError("ARTIFICIAL_SECRET_DO_NOT_ECHO")))
        self.assertEqual(result["status"], "failed_consumed")
        self.assertIsNone(result["attempts_started"])
        self.assertNotIn("ARTIFICIAL_SECRET", json.dumps(result))
        self.assertTrue((self.folder/"halt.json").exists())

    def test_abandoned_prior_day_reservation_blocks_next_day_before_dispatch(self):
        prior = self.folder/'2026-11-06'; prior.mkdir()
        batch._save(prior/'claim.json', {'artificial_interruption': True})
        with self.assertRaisesRegex(obs.ObservationError, 'prior_day_incomplete'):
            self.run_pair()
        self.assertEqual(self.calls, [])
        self.assertFalse((self.folder/'2026-11-09').exists())

    def test_credential_echo_is_not_retained(self):
        def exchange(request, token, timeout):
            response = response_fixture(request, self.at)
            response["body"] = json.dumps({"message": token}).encode()
            return response
        result = self.run_pair(exchange=exchange)
        self.assertEqual(result["status"], "failed_consumed")
        self.assertIsNone(result["receipts"][0]["raw"])
        self.assertFalse(list(self.folder.rglob("response.entity.json")))
        receipt = json.loads(Path(result["receipts"][0]["receipt"]["path"]).read_bytes())
        self.assertTrue(receipt["originals_not_retained_due_safety_screen"])

    def test_received_wrong_date_is_exposed_but_not_a_complete_session(self):
        def exchange(request, token, timeout):
            response = response_fixture(request, self.at)
            response["body"] = response["body"].replace(b'20261109', b'20261106')
            return response
        result = self.run_pair(exchange=exchange)
        self.assertFalse(result["paired_session_complete"])
        receipt = json.loads(Path(result["receipts"][0]["receipt"]["path"]).read_bytes())
        self.assertEqual(receipt["exposure"], "partial_or_unvalidated_raw_observed")
        self.assertIsNotNone(receipt["raw"])

    def test_clock_slot_and_future_only_boundaries_stop_before_dispatch(self):
        for at in ("2026-11-09T07:29:59+00:00", "2026-11-09T10:00:00+00:00",
                   "2026-11-10T08:00:00+00:00"):
            with self.subTest(at=at), self.assertRaises(obs.ObservationError):
                self.run_pair(clock=lambda: obs.instant(at))
        self.assertEqual(self.calls, [])
        self.plan["created_at"] = "2026-11-09T00:00:00+00:00"
        with self.assertRaises(obs.ObservationError):
            self.run_pair()

    def test_internal_receipt_clock_unknown_or_reversed_is_not_complete(self):
        for header in (None, "2026-11-09T07:59:59+00:00", "2026-11-09T08:00:01+00:00"):
            with self.subTest(header=header), TemporaryDirectory() as tmp:
                def exchange(request, token, timeout):
                    response = response_fixture(request, self.at)
                    response['headers_received_at'] = header
                    return response
                result = obs.capture_synthetic(self.plan, self.calendar, '2026-11-09', Path(tmp),
                                               clock=self.clock, exchange=exchange)
                self.assertFalse(result['paired_session_complete'])
                receipt = json.loads(Path(result['receipts'][0]['receipt']['path']).read_bytes())
                self.assertFalse(receipt['clock_valid'])
                self.assertEqual(receipt['headers_received_at'], header)
                self.assertIsNotNone(receipt['raw'])
                self.assertEqual(receipt['retained_at'], self.at)

    def test_bad_calendar_budget_or_extended_campaign_never_dispatches(self):
        p, c = plan_fixture(["2026-11-09", "2026-11-10"])
        with self.assertRaisesRegex(obs.ObservationError, "campaign"):
            obs.validate_plan(p, c)
        p["authority_kind"] = "separately_authorized_finite"
        obs.validate_plan(p, c)
        c["session_rows"].insert(1, {"date": "2026-11-09", "exchange_codes": ["SSE"]})
        with self.assertRaises(obs.ObservationError):
            obs.validate_plan(p, c)
        self.plan["request_budget"] = 3
        with self.assertRaisesRegex(obs.ObservationError, "budget"):
            self.run_pair()

    def test_pair_bound_original_changed_before_second_leg_is_not_rebaselined(self):
        bound = self.folder/"fixed_metadata.txt"
        bound.write_bytes(b"a")
        ref = batch.reference(bound)
        def exchange(request, token, timeout):
            value = self.exchange(request, token, timeout)
            bound.write_bytes(b"b")
            return value
        result = self.run_pair(exchange=exchange, bound_refs=[ref])
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(result["final_integrity"])
        self.assertEqual(result["original_refs"][0], ref)

    def test_twenty_artificial_pairs_never_become_real_warmup_or_skip_missing_day(self):
        # Explicit artificial exchange dates: no inference from weekdays by the engine.
        start = datetime(2026, 11, 9)
        days = [(start+timedelta(days=i)).date().isoformat() for i in range(20)]
        plan, calendar = plan_fixture(days)
        plan["authority_kind"] = "separately_authorized_finite"
        refs = []
        for day in days:
            at = day+"T08:00:00+00:00"
            result = obs.capture_synthetic(plan, calendar, day, self.folder,
                clock=lambda at=at: obs.instant(at),
                exchange=lambda r, t, wall, at=at: response_fixture(r, at))
            self.assertTrue(result["paired_session_complete"])
            refs.append(batch.reference(self.folder/day/"outcome.json"))
        summary = obs.paired_coverage(plan, calendar, refs, expected_scope_sha256=obs._digest(plan))
        self.assertEqual(summary["complete_paired_sessions"], 0)
        self.assertFalse(summary["twenty_common_contiguous_source_sessions"])
        # Arbitrarily dropping a date from the planned window is rejected, not renumbered.
        bad = deepcopy(plan); bad["slots"].pop(5)
        with self.assertRaisesRegex(obs.ObservationError, "calendar_gap"):
            obs.validate_plan(bad, calendar)
        # Relabelling only the day outcome cannot override the artificial claim/receipts.
        changed = json.loads(Path(refs[0]["path"]).read_bytes()); changed["evidence_class"] = obs.SOURCE
        forged = self.folder/"relabeled.json"; forged.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(obs.ObservationError, "coverage_claim"):
            obs.paired_coverage(plan, calendar, [batch.reference(forged)], expected_scope_sha256=obs._digest(plan))

    def test_real_entry_missing_release_stops_before_PM_credentials_and_HTTP(self):
        with (patch.object(batch, '_fresh_gate', side_effect=AssertionError('PM before release')),
              patch.object(batch, '_isolated', side_effect=AssertionError('HTTP')),
              patch.object(obs.os.environ, 'get', side_effect=AssertionError('credential lookup'))):
            with self.assertRaises(FileNotFoundError):
                obs.capture('2026-11-09', repo_root=self.folder, expected_scope_sha256='a'*64, execute=True)
        self.assertFalse((self.folder/'claim.json').exists())


class ReleaseTests(unittest.TestCase):
    """Full release-envelope metadata fixture; no real file or source authority."""
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); (self.root/'configs').mkdir()
        self.plan, calendar = plan_fixture()
        self.calendar_ref = batch._save(self.root/'calendar.json', calendar)
        evidence = batch._save(self.root/'source_definitions.json', {'artificial': True})
        code = self.root/obs.CODE_FILES[0]; code.parent.mkdir(parents=True); code.write_text('# artificial code\n')
        executable = self.root/'artificial.exe'; executable.write_bytes(b'artificial')
        self.impl = {'code': {obs.CODE_FILES[0]: batch.reference(code)}, 'executable': batch.reference(executable)}
        self.plan.update(calendar=self.calendar_ref, implementation=self.impl, head='a'*40,
                         ledger_directory=obs.PRODUCTION_LEDGER.as_posix(), protocol_bindings=[], bindings=[evidence])
        self.scope_ref = batch._save(self.root/'scope.json', self.plan)
        self.reviews = {}
        for role in ('root', 'manager'):
            review = {'artifact_type': 'future_etf_source_exact_review_v1', 'reviewer': role,
                'status': 'accepted_exact_source_observation', 'scope_sha256': self.scope_ref['sha256'],
                'implementation_sha256': obs._digest(self.impl), 'authority_kind': self.plan['authority_kind'],
                'dates': ['2026-11-09'], 'request_budget': 2, 'expires_at': self.plan['expires_at'],
                'source_only': True, 'accepted_at': '2026-11-07T01:00:00+00:00'}
            self.reviews[role+'_review'] = batch._save(self.root/(role+'.json'), review)
        self.admission = {'artifact_type': 'future_etf_source_release_v1', 'scope': self.scope_ref, **self.reviews}
        (self.root/obs.CONFIG).write_text(json.dumps(self.admission), encoding='utf-8')
        patches = [patch.object(obs, 'implementation', return_value=self.impl),
            patch.object(obs, '_protocol_refs', return_value=[]), patch.object(obs, '__file__', str(code)),
            patch.object(batch, '_git', side_effect=lambda root, *args: obs.BRANCH if args[0]=='branch' else 'a'*40),
            patch.object(obs, 'utc_now', return_value=obs.instant('2026-11-09T08:00:00+00:00'))]
        for item in patches:
            item.start(); self.addCleanup(item.stop)

    def test_exact_two_review_metadata_accepted_but_tamper_or_late_review_rejected(self):
        obs.load_authority(self.root)
        manager = self.root/'manager.json'
        original = manager.read_bytes()
        manager.write_bytes(original.replace(b'accepted_exact_source_observation', b'rejected_exact_source_observation'))
        with self.assertRaises(batch.BatchError):
            obs.load_authority(self.root)
        manager.write_bytes(original)
        value = json.loads(original); value['accepted_at'] = '2026-11-09T00:00:00+00:00'
        manager.write_text(json.dumps(value), encoding='utf-8')
        self.admission['manager_review'] = batch.reference(manager)
        (self.root/obs.CONFIG).write_text(json.dumps(self.admission), encoding='utf-8')
        with self.assertRaisesRegex(obs.ObservationError, 'dual_review'):
            obs.load_authority(self.root)

    def test_scope_digest_mismatch_and_non_source_PM_block_before_credentials(self):
        with patch.object(obs.os.environ, 'get', side_effect=AssertionError('credential lookup')):
            with self.assertRaisesRegex(obs.ObservationError, 'exact_scope'):
                obs.capture('2026-11-09', repo_root=self.root, expected_scope_sha256='b'*64, execute=True)
            gate = batch._save(self.root/'gate.json', {'mode': obs.MODE,
                'safety': {'future_source_observation_allowed': False}})
            with patch.object(batch, '_fresh_gate', return_value=[gate]):
                with self.assertRaisesRegex(obs.ObservationError, 'source_PM'):
                    obs.capture('2026-11-09', repo_root=self.root,
                                expected_scope_sha256=self.scope_ref['sha256'], execute=True)

    def test_production_dispatch_protocol_can_complete_with_only_artificial_dependencies(self):
        """Exercises the real wiring, not a live capture: every boundary is an artificial fixture."""
        ledger = self.root/'artificial_project_ledger'
        plan = deepcopy(self.plan); plan['ledger_directory'] = ledger.as_posix()
        gate = batch._save(self.root/'accepted_gate.json', {'mode': obs.MODE,
            'generated_at': '2026-11-09T08:00:00+00:00', 'safety': {
            'future_source_observation_allowed': True,
            'future_source_observation_scope': {'scope_sha256': self.scope_ref['sha256']},
            'factor_batch_allowed': False, 'final_holdout_allowed': False, 'live_boundary_allowed': False}})
        calls = []
        def exchange(request, token, timeout):
            self.assertEqual(token, 'ARTIFICIAL_ONLY')
            self.assertTrue((ledger/'2026-11-09/claim.json').is_file())
            self.assertTrue((ledger/'2026-11-09'/request['id']/'claim.json').is_file())
            calls.append(request)
            return response_fixture(request, '2026-11-09T08:00:00+00:00')
        with (patch.object(obs, 'PRODUCTION_LEDGER', ledger),
              patch.object(obs, 'load_authority', return_value=(plan, self.scope_ref, [self.scope_ref])),
              patch.object(batch, '_fresh_gate', return_value=[gate]),
              patch.object(obs.os.environ, 'get', return_value='ARTIFICIAL_ONLY'),
              patch.object(batch, '_isolated', side_effect=exchange)):
            result = obs.capture('2026-11-09', repo_root=self.root,
                                 expected_scope_sha256=self.scope_ref['sha256'], execute=True)
        self.assertEqual(result['status'], 'completed_structure_only')
        self.assertEqual(len(calls), 2)
        # Temporary fixture result is never published as actual source evidence.
        coverage = obs.paired_coverage(plan, json.loads(batch._bound(self.calendar_ref)),
            [batch.reference(ledger/'2026-11-09/outcome.json')],
            expected_scope_sha256=self.scope_ref['sha256'])
        self.assertEqual(coverage['complete_paired_sessions'], 1)
        self.assertFalse(coverage['ready_for_candidate'])


class SourcePMTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        repo = Path(__file__).resolve().parents[2]
        self.config = json.loads((repo/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.family = json.loads((repo/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.workstations = json.loads((repo/'configs/workstations.json').read_bytes())
        for row in self.config['required_reading']:
            p = self.root/row['path']; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('ARTIFICIAL\n')

    def build(self):
        return pm.build_quant_pm_startup_gate(gate_config=self.config, family_config=self.family,
            workstations_config=self.workstations, repo_root=self.root, machine='office_desktop',
            task='data_pipeline', branch=obs.BRANCH, current_branch=obs.BRANCH)

    def test_missing_release_blocks_and_exact_source_mode_closes_all_financial_permissions(self):
        missing = self.build()
        self.assertEqual(missing['status'], 'blocked')
        self.assertEqual(missing['mode'], obs.CLOSED_MODE)
        self.assertFalse(missing['safety']['future_source_observation_allowed'])
        with patch.object(pm, 'future_source_observation_scope', return_value={
                'mode': obs.MODE, 'scope': {'scope_sha256': 'a'*64}}):
            ready = self.build()
        self.assertEqual(ready['status'], 'ready', ready['blockers'])
        self.assertTrue(ready['safety']['future_source_observation_allowed'])
        for key, value in ready['safety'].items():
            if key.endswith('_allowed') and key != 'future_source_observation_allowed':
                self.assertIs(value, False, key)
        self.assertEqual(ready['safety']['factor_batch_scope'], {})
        self.assertEqual(ready['account_comparison']['status'], 'not_applicable')


if __name__ == '__main__':
    unittest.main()
