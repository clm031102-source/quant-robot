"""Same-buffer calendar verification, with no hidden path rereads."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from quant_robot.data import cn_trading_calendar as calendar
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_recorded_sources as sources
from quant_robot.ops import paper_source_bundle as bundle
from hashlib import sha256
from tests.unit import test_cn_trading_calendar as fixtures
from tests.unit import test_paper_source_bundle as source_fixtures
from tests.unit import test_frozen_candidate_deferred as meters


class CalendarBytesTests(TestCase):
    probes=[]

    def buffers(self):
        frame,manifest=calendar.build_cn_trading_calendar(
            {exchange:fixtures._calendar_frame(exchange,['2024-01-02','2024-01-03']) for exchange in ('SSE','SZSE')},
            start_date='2024-01-01',end_date='2024-01-04')
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        paths=calendar.write_cn_trading_calendar(temporary.name,frame,manifest)
        return paths,Path(paths['calendar_path']).read_bytes(),Path(paths['manifest_path']).read_bytes()

    def test_bytes_and_path_wrapper_return_identical_contract_without_path_reads(self):
        paths,raw,manifest=self.buffers()
        expected=calendar.validate_cn_trading_calendar_artifact(paths['calendar_path'],paths['manifest_path'])
        read_csv=calendar.pd.read_csv
        def buffered(value,*args,**kwargs):
            self.assertIs(type(value),io.BytesIO)
            return read_csv(value,*args,**kwargs)
        with patch.object(Path,'open',side_effect=AssertionError('path read')), \
             patch.object(calendar,'sha256_file',side_effect=AssertionError('path hash')), \
             patch.object(calendar.pd,'read_csv',side_effect=buffered):
            actual=calendar.validate_cn_trading_calendar_bytes(raw,manifest,
                expected_start_date='2024-01-01',expected_end_date='2024-01-04')
        self.assertEqual(actual,expected)

    def test_changed_buffers_and_existing_contract_violations_fail(self):
        _,raw,manifest_raw=self.buffers();manifest=json.loads(manifest_raw)
        with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
            calendar.validate_cn_trading_calendar_bytes(raw+b'CN,2024-01-04,1,tushare\n',manifest_raw)
        for key,value in (('calendar_schema_version',9),('status','blocked'),('provider','other'),
                          ('required_exchanges',['SSE']),('live_boundary_allowed',True)):
            changed=deepcopy(manifest);changed[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):
                calendar.validate_cn_trading_calendar_bytes(raw,json.dumps(changed).encode())
        with self.assertRaisesRegex(ValueError,'requested end mismatch'):
            calendar.validate_cn_trading_calendar_bytes(raw,manifest_raw,expected_end_date='2024-01-05')
        with self.assertRaisesRegex(ValueError,'Exact calendar'):
            calendar.validate_cn_trading_calendar_bytes(bytearray(raw),manifest_raw)

    def test_published_factory_consumes_only_stage_buffers_and_rechecks_originals(self):
        fixture=source_fixtures.PaperSourceBundleTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        registry=fixture.published_calendar();entry=fixture.spec['evidence']['calendar']
        adapter=registry[entry['adapter_id']]
        operation=sessions.EvidenceOperation(fixture.root,policy=sessions.G1_RECORDED_POLICY)
        stack,counts=meters.content_meter()
        with stack:
            stage=operation.stage();assembly=sources._RecordedAssembly(stage,_offline=True)
            context=assembly.context('calendar');evidence=adapter.parse(context,entry['receipt'])
            ticket=context.child.propose(evidence.facts);verified=stage.commit()
        self.assertEqual(verified.result(ticket)['exchange'],'XSHG')
        self.assertEqual(evidence.evidence_class,'synthetic_only')
        actual=operation.measurements()
        self.assertEqual((counts['opens'],counts['reads'],counts['bytes']),
                         (actual['open_attempts'],actual['read_calls'],actual['io_bytes_returned']))
        self.probes.append(dict(label='published_calendar_same_buffers',external=counts,internal=actual))

    def test_same_buffer_calendar_preserves_strict_json_and_synthetic_taint(self):
        for marker,error in ((b'"status":"blocked",', 'duplicate_JSON_key'),
                             (b'"unrelated":NaN,', 'nonfinite_JSON_constant'),
                             (b'"evidence_class":"synthetic_only",', None)):
            with self.subTest(error=error):
                fixture=source_fixtures.PaperSourceBundleTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
                fixture.published_calendar()
                path=fixture.root/fixture.calendar_metadata['calendar_manifest_path']
                raw=path.read_bytes();raw=b'{'+marker+raw.lstrip()[1:];path.write_bytes(raw)
                fixture.calendar_metadata['calendar_manifest_sha256']=sha256(raw).hexdigest()
                registry=fixture.register_calendar();entry=fixture.spec['evidence']['calendar']
                operation=sessions.EvidenceOperation(fixture.root,policy=sessions.G1_RECORDED_POLICY)
                stack,counts=meters.content_meter()
                with stack:
                    stage=operation.stage();assembly=sources._RecordedAssembly(stage,_offline=True)
                    context=assembly.context('calendar');adapter=registry[entry['adapter_id']]
                    if error:
                        with self.assertRaisesRegex(bundle.BundleError,error):adapter.parse(context,entry['receipt'])
                        stage.abort()
                    else:
                        evidence=adapter.parse(context,entry['receipt'])
                        self.assertTrue(context.synthetic_seen)
                        context.child.propose(evidence.facts);stage.commit()
                actual=operation.measurements()
                self.assertEqual((counts['opens'],counts['reads'],counts['bytes']),
                                 (actual['open_attempts'],actual['read_calls'],actual['io_bytes_returned']))
                self.probes.append(dict(label='calendar_strict_json_'+str(error),external=counts,internal=actual))
