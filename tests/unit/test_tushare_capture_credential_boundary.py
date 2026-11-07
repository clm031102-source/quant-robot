"""Capture credential boundaries using artificial mappings and in-memory transport."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from quant_robot.config import secrets
from quant_robot.ops import tushare_live_transport as live
from tests.unit import test_tushare_live_transport as fixtures


class _Environment:
    """Only one named lookup is allowed; no host environment is copied or inspected."""

    def __init__(self, values):
        self.values = values
        self.lookups = []

    def get(self, name):
        if name != 'TUSHARE_TOKEN':
            raise AssertionError('unrelated environment entry accessed')
        self.lookups.append(name)
        return self.values.get(name)


def _read_artificial(environment):
    # Replace the mapping object, not patch.dict: never snapshot host values.
    with patch.object(live.os, 'environ', environment):
        return live._existing_token()


class CaptureCredentialBoundaryTests(unittest.TestCase):
    def fixture(self):
        case = fixtures.ScopedTransportTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def no_files(self):
        guards = ExitStack()
        self.addCleanup(guards.close)
        for owner, names in (
            (Path, ('cwd', 'resolve', 'open', 'exists', 'is_file', 'iterdir')),
            (secrets, ('require_env_secret', 'get_env_secret', '_default_dotenv_paths')),
            (live.os, ('open',)),
        ):
            for name in names:
                guards.enter_context(patch.object(owner, name,
                    side_effect=AssertionError('credential filesystem access forbidden')))
        guards.enter_context(patch('builtins.open',
            side_effect=AssertionError('credential filesystem access forbidden')))
        return guards

    def hooks(self, case, environment):
        hooks = case.hooks()

        def token():
            folder = case.folder()
            for name in ('scope.json', 'gate.json', 'claim.json'):
                self.assertTrue((folder / name).is_file())
            self.assertFalse(list(folder.glob('.pending-*')))
            return _read_artificial(environment)

        hooks['token'] = token
        return hooks

    def assert_not_retained(self, case, marker, output=''):
        self.assertNotIn(marker, output)
        for path in case.folder().iterdir():
            if path.is_file():
                self.assertNotIn(marker.encode(), path.read_bytes())

    def test_named_environment_value_is_trimmed_without_files_or_generic_secret_helper(self):
        with self.no_files():
            for value in (fixtures.TOKEN, ' \t' + fixtures.TOKEN + '\r\n'):
                with self.subTest(padded=value != fixtures.TOKEN):
                    environment = _Environment({'TUSHARE_TOKEN': value, 'OTHER_SECRET': 'unused'})
                    self.assertEqual(_read_artificial(environment), fixtures.TOKEN)
                    self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])

    def test_missing_blank_or_nonstring_value_has_constant_error_without_file_fallback(self):
        cases = ({}, {'OTHER_SECRET': 'artificial-unrelated-value'},
                 *({'TUSHARE_TOKEN': value} for value in (None, '', ' \r\n\t', 123)))
        with self.no_files():
            for values in cases:
                with self.subTest(case=len(values), value_type=type(values.get('TUSHARE_TOKEN')).__name__):
                    environment = _Environment(values)
                    with self.assertRaises(live.ScopeError) as caught:
                        _read_artificial(environment)
                    self.assertEqual(str(caught.exception), 'existing_credential_unavailable')
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])

    def test_missing_or_blank_after_durable_claim_is_consumed_without_retry(self):
        for values in ({}, {'TUSHARE_TOKEN': ' \t\n'}):
            with self.subTest(missing=not values):
                case = self.fixture()
                environment = _Environment(values)
                hooks = self.hooks(case, environment)
                with patch.object(live, '_new_session', side_effect=AssertionError('real network')), \
                        patch.object(live, '_bounded_worker', side_effect=AssertionError('real worker')):
                    result = case.collect(hooks=hooks)
                    receipt = case.receipt(result)
                    self.assertEqual(result['status'], 'source_rejected')
                    self.assertEqual(receipt['failure_code'], 'existing_credential_unavailable')
                    self.assertEqual(receipt['http_attempts_started'], 0)
                    self.assertEqual(receipt['network_requests_started'], 0)
                    self.assertIsNone(receipt['raw_response'])
                    self.assertIsNone(receipt['request_started_at'])
                    self.assertEqual(case.collect(hooks=hooks)['status'], 'already_consumed')
                self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])
                self.assertFalse(case.session.calls)

    def test_existing_length_bounds_still_reject_before_request_and_never_retain_value(self):
        for value in ('fake-short', 'artificial-overlong-' * 20):
            with self.subTest(length=len(value)):
                case = self.fixture()
                environment = _Environment({'TUSHARE_TOKEN': value})
                hooks = self.hooks(case, environment)
                output = StringIO()
                with redirect_stdout(output), redirect_stderr(output):
                    result = case.collect(hooks=hooks)
                    self.assertEqual(case.collect(hooks=hooks)['status'], 'already_consumed')
                receipt = case.receipt(result)
                self.assertEqual(receipt['failure_code'], 'existing_credential_unavailable')
                self.assertEqual(receipt['http_attempts_started'], 0)
                self.assertFalse(case.session.calls)
                self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])
                self.assert_not_retained(case, value, output.getvalue())

    def test_artificial_valid_credential_preserves_mock_capture_without_secret_retention(self):
        case = self.fixture()
        environment = _Environment({'TUSHARE_TOKEN': ' \t' + fixtures.TOKEN + '\n'})
        hooks = self.hooks(case, environment)
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = case.collect(hooks=hooks)
            self.assertEqual(case.collect(hooks=hooks)['status'], 'already_consumed')
        receipt = case.receipt(result)
        self.assertEqual(result['status'], 'source_observed_unqualified')
        self.assertEqual(receipt['network_requests_started'], 0)
        self.assertEqual(receipt['mocked_requests_started'], 1)
        self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])
        self.assertEqual(len(case.session.calls), 1)
        self.assertEqual(case.session.calls[0][1]['json']['token'], fixtures.TOKEN)
        self.assert_not_retained(case, fixtures.TOKEN, output.getvalue())

    def test_expired_scope_after_claim_never_invokes_environment_lookup(self):
        case = self.fixture()
        environment = _Environment({'TUSHARE_TOKEN': fixtures.TOKEN})
        hooks = self.hooks(case, environment)
        confirm = live._confirm_references
        original_now = case.now

        def expire_after_persistence(folder, refs):
            confirm(folder, refs)
            case.now = live.parser._utc(case.scope['valid_until'])

        with patch.object(live, '_confirm_references', side_effect=expire_after_persistence):
            result = case.collect(hooks=hooks)
        self.assertEqual(case.receipt(result)['failure_code'], 'scope_expired_before_credential_read')
        case.now = original_now
        self.assertEqual(case.collect(hooks=hooks)['status'], 'already_consumed')
        self.assertFalse(environment.lookups)
        self.assertFalse(case.session.calls)

    def test_credential_exception_text_is_redacted_and_cannot_enable_retry(self):
        case = self.fixture()
        environment = _Environment({})
        hooks = self.hooks(case, environment)
        marker = 'artificial-provider-exception-sensitive-marker'
        output = StringIO()
        with patch.object(environment, 'get', side_effect=RuntimeError(marker)) as getter, \
                redirect_stdout(output), redirect_stderr(output):
            result = case.collect(hooks=hooks)
            self.assertEqual(case.collect(hooks=hooks)['status'], 'already_consumed')
        getter.assert_called_once_with('TUSHARE_TOKEN')
        self.assertEqual(case.receipt(result)['failure_code'], 'credential_read_failed_redacted')
        self.assertFalse(case.session.calls)
        self.assert_not_retained(case, marker, output.getvalue())

    def test_missing_credential_and_receipt_write_failure_preserve_recovery_without_retry(self):
        case = self.fixture()
        environment = _Environment({})
        hooks = self.hooks(case, environment)
        publish = live._publish_json

        def fail_receipt(path, value):
            if path.name == 'receipt.json':
                raise live.ArchiveWriteError('artificial publication failure')
            return publish(path, value)

        with patch.object(live, '_publish_json', side_effect=fail_receipt):
            result = case.collect(hooks=hooks)
        self.assertEqual(result['status'], 'recovery_review_required')
        self.assertTrue(result['request_reservation_consumed'])
        self.assertFalse(result['automatic_retry_allowed'])
        self.assertEqual(case.collect(hooks=hooks)['status'], 'recovery_review_required')
        self.assertEqual(environment.lookups, ['TUSHARE_TOKEN'])
        self.assertFalse(case.session.calls)


if __name__ == '__main__':
    unittest.main()
