"""Synthetic transport and date isolation checks; no network or real quotes."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from quant_robot.data.sources import geopolitical_account_sources as source
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from tests.unit.test_geopolitical_account import invented_calendar, source_states


def catalogue():
    rows = [dict(TITLE=f'Gold ETF {year}年度报告', SECURITY_CODE='518880',
                 URL=f'/disclosure/fund/announcement/c/new/{year+1}-03-28/518880_{year+1}0328_ABCD.pdf')
            for year in (2024, 2025)]
    return dict(result=rows, pageHelp=dict(total=2, pageCount=1, pageNo=1))


class GoldSourceTests(unittest.TestCase):
    def test_complete_six_request_transport_is_scoped_and_claim_is_exclusive(self):
        days = ['2025-12-30', '2025-12-31']
        date_payload = dict(code='518880', begin=0, end=3, total=3,
                            kline=[[20251230], [20251231], [20260102]])
        price_payload = dict(code='518880', kline=[
            [20251230, 4, 5, 3, 4, 100, 400],
            [20251231, 4, 5, 3, 4, 100, 400]])
        payloads = [canonical(catalogue()), b'%PDF-synthetic-2024', b'%PDF-synthetic-2025',
                    canonical(dict(result=[], pageHelp=dict(total=0, pageCount=0, pageNo=1))),
                    canonical(date_payload), canonical(price_payload)]
        session = Mock()
        responses = []
        for payload in payloads:
            response = Mock(status_code=200)
            response.iter_content.return_value = [payload]
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            responses.append(context)
        session.get.side_effect = responses
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / source.DIRECTORY
            directory.mkdir(parents=True)
            with patch.object(source, 'preflight', return_value=({}, b'{}', dict(sessions=days))), \
                    patch.object(source.requests, 'Session', return_value=session):
                result = source.execute(root, {})
                self.assertEqual(result['requests'], 6)
                self.assertFalse(result['account_execution_allowed'])
                self.assertEqual(result['status'], 'raw_sources_retained_review_pending')
                with self.assertRaises(FileExistsError):
                    source.execute(root, {})
            self.assertEqual(session.get.call_count, 6)
            self.assertFalse(session.trust_env)
            for call in session.get.call_args_list:
                self.assertFalse(call.kwargs['allow_redirects'])
                self.assertEqual(call.kwargs['timeout'], (5, 30))
            self.assertEqual(session.get.call_args_list[0].kwargs['params']['END_DATE'], '2026-11-04')
            self.assertEqual(session.get.call_args_list[4].kwargs['params']['select'], 'date')
            price_request = session.get.call_args_list[5].kwargs['params']
            self.assertEqual((price_request['begin'], price_request['end']), (0, 2))
            self.assertEqual(price_request['select'], 'date,open,high,low,close,volume,amount')
            outcome = json.loads((directory / 'source_outcome.json').read_bytes())
            self.assertEqual(len(outcome['receipts']), 6)

    def test_paginated_terminal_catalogue_stops_before_quotes_and_consumes_scope(self):
        terminal = dict(result=[dict(TITLE='synthetic incomplete catalogue')],
                        pageHelp=dict(total=1, pageCount=2, pageNo=2))
        payloads = [canonical(catalogue()), b'%PDF-synthetic-2024', b'%PDF-synthetic-2025',
                    canonical(terminal)]
        session = Mock()
        responses = []
        for payload in payloads:
            response = Mock(status_code=200)
            response.iter_content.return_value = [payload]
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            responses.append(context)
        session.get.side_effect = responses
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / source.DIRECTORY
            directory.mkdir(parents=True)
            with patch.object(source, 'preflight', return_value=({}, b'{}', dict(sessions=['2025-12-31']))), \
                    patch.object(source.requests, 'Session', return_value=session):
                with self.assertRaisesRegex(ValueError, 'single-page catalogue'):
                    source.execute(root, {})
                with self.assertRaises(FileExistsError):
                    source.execute(root, {})
            self.assertEqual(session.get.call_count, 4)
            self.assertNotIn(source.QUOTE_URL, [call.args[0] for call in session.get.call_args_list])
            self.assertFalse((directory / 'gold_dates_claim.json').exists())
            outcome = json.loads((directory / 'source_outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'failed_consumed')
            self.assertEqual(outcome['error_type'], 'ValueError')
            self.assertEqual(len(outcome['receipts']), 4)

    def test_terminal_catalogue_rejects_nonfirst_pages_and_accepts_explicit_zero(self):
        value=dict(result=[{}],pageHelp=dict(total=1,pageCount=2,pageNo=2))
        with self.assertRaisesRegex(ValueError,'single-page'):
            source.complete_catalogue(value,allow_empty=True)
        empty=dict(result=[],pageHelp=dict(total=0,pageCount=0,pageNo=1))
        self.assertEqual(source.complete_catalogue(empty,allow_empty=True),[])
        with self.assertRaises(ValueError):
            source.complete_catalogue(empty)
        self.assertEqual(source.catalog_params()['END_DATE'],'2026-11-04')

    def test_selects_exact_original_annuals_and_rejects_ambiguous_or_external_files(self):
        self.assertEqual([r['year'] for r in source.annual_documents(catalogue())], [2024,2025])
        variants = []
        value = catalogue(); value['result'].append(dict(value['result'][0])); value['pageHelp']['total']=3; variants.append(value)
        value = catalogue(); value['result'][0]['TITLE'] += '更正'; variants.append(value)
        value = catalogue(); value['result'][0]['URL']='https://example.com/518880.pdf'; variants.append(value)
        value = catalogue(); value['pageHelp']['total']=9; variants.append(value)
        for payload in variants:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                source.annual_documents(payload)

    def test_date_only_window_never_requests_2026_price_positions(self):
        payload = dict(code='518880', total=5, begin=0, end=5,
                       kline=[[20251229],[20251230],[20251231],[20260102],[20260105]])
        parameters = source.quote_window(payload, ['2025-12-30','2025-12-31'])
        self.assertEqual(parameters['begin'],1)
        self.assertEqual(parameters['end'],3)
        with self.assertRaisesRegex(ValueError,'2026'):
            source.quote_window(payload,['2025-12-31','2026-01-02'])
        with self.assertRaisesRegex(ValueError,'differ'):
            source.quote_window(payload,['2025-12-29','2025-12-31'])
        payload['kline'][0].append(4.0)
        with self.assertRaisesRegex(ValueError,'date-only'):
            source.quote_window(payload,['2025-12-30','2025-12-31'])

    def test_price_integrity_rejects_scope_drift_boolean_and_invalid_bounds(self):
        payload = dict(code='518880',kline=[[20251231,4,5,3,4,100000,400000]])
        source.validate_raw_prices(payload,['2025-12-31'])
        for index, bad in ((0,20260102),(1,True),(1,6),(5,-1),(4,float('nan'))):
            modified = deepcopy(payload); modified['kline'][0][index]=bad
            with self.subTest(index=index,bad=bad),self.assertRaises(ValueError):
                source.validate_raw_prices(modified,['2025-12-31'])

    def test_claim_and_pins_stop_reuse_or_missing_dependencies_before_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); directory=root/source.DIRECTORY; directory.mkdir(parents=True)
            inputs={}
            for role in ('proposal','method','account_plan','calendar','calendar_manifest',
                         'cadence_result','cadence_review','method_review'):
                path=f'inputs/{role}.json'; target=root/path; target.parent.mkdir(exist_ok=True)
                value={}
                target.write_bytes(canonical(value)); inputs[role]=dict(path=path,sha256=sha256(target.read_bytes()))
            def replace(role, content):
                target=root/inputs[role]['path'];target.write_bytes(content);inputs[role]['sha256']=sha256(content)
            # Invented weekdays with a fixed-size session subset, never market data.
            days=invented_calendar()
            first=days.index('2022-02-15'); days=days[first:]
            remove=set(days[60:-1:5][:len(days)-944]);days=[d for d in days if d not in remove]
            states=source_states(); plan=source.make_plan(days,states)
            replace('account_plan',canonical(plan))
            replace('cadence_result',canonical(dict(rows=states)))
            calendar=('market,date,is_open,source\n'+''.join(f'CN,{d},1,synthetic\n' for d in days)).encode()
            replace('calendar',calendar)
            replace('calendar_manifest',canonical(dict(artifact=dict(sha256=sha256(calendar)),decision=dict(calendar_cleared=True,blockers=[]))))
            replace('method',canonical(dict(account_plan=inputs['account_plan'],original_proposal=inputs['proposal'],cadence_result=inputs['cadence_result'],account_execution_allowed=False)))
            code={}
            for path in source.IMPLEMENTATION:
                target=root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b'# synthetic\n')
                code[path]=dict(path=path,sha256=sha256(target.read_bytes()))
            packet=dict(stage='fixed_geopolitical_account_source_preparation',branch=source.BRANCH,
                max_requests=6,price_window=['2022-02-15','2025-12-31'],inputs=inputs,code_files=code,
                environment=runtime_environment(),
                returns_allowed=False,account_execution_allowed=False,holdout_2026_prices_allowed=False,
                paper_promotion_allowed=False,live_boundary_allowed=False)
            target=root/source.SCOPE; tracked=root/source.TRACKED_SCOPE;tracked.parent.mkdir(exist_ok=True)
            def set_scope(packet):
                target.write_bytes(canonical(packet));tracked.write_bytes(canonical(packet))
            set_scope(packet)
            gate=dict(generated_at=datetime.now(timezone.utc).isoformat(),status='ready',blockers=[],primary_market='CN_ETF',
                selected=dict(machine='office_desktop',task='factor_review',branch=source.BRANCH,current_branch=source.BRANCH),
                safety=dict(live_boundary_allowed=False))
            with patch.object(source,'PROPOSAL_SHA',inputs['proposal']['sha256']),patch.object(source,'CADENCE_SHA',inputs['cadence_result']['sha256']):
                source.preflight(root,gate)
                modified=deepcopy(packet);modified['code_files'].pop(next(iter(code)));set_scope(modified)
                with self.assertRaisesRegex(ValueError,'pins'):
                    source.preflight(root,gate)
                set_scope(packet); (directory/'source_attempt_claim.json').write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError,'consumed'):
                    source.preflight(root,gate)


if __name__ == '__main__':
    unittest.main()
