import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_tushare_ingest_pipeline import FakeTushareDailyAdapter


class TushareProviderCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=pd.DataFrame({'ts_code':['510300.SH'],'trade_date':['20200107'],
            'open':[4.0],'high':[4.1],'low':[3.9],'close':[4.0],'vol':['4649595.14'],'amount':['2109910.834']})
        self.calls=[]
        def fetch(**kwargs):
            self.calls.append(kwargs)
            return self.source
        self.client=SimpleNamespace(fund_daily=fetch,
            trade_cal=lambda **kwargs:pd.DataFrame({'exchange':['SSE'],'cal_date':['20200107'],'is_open':[1]}))
        self.adapter=TushareAdapter(client=self.client,max_retries=1)

    def run_ingest(self,adapter=None,**kwargs):
        return run_tushare_daily_ingest(adapter or self.adapter,'2020-01-07','2020-01-07',self.root,market='CN_ETF',**kwargs)

    def binding(self):
        manifest=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        return manifest['metadata']['daily_provider_evidence']['CN_ETF:daily:20200107']

    def test_pipeline_retains_native_units_reception_and_mapped_file_binding(self):
        result=self.run_ingest()
        evidence=result['provider_source_evidence']['20200107']
        self.assertEqual(evidence['status'],'captured_provider_frame_matches_mapped_cache')
        self.assertFalse(evidence['source_quality_verified'])
        binding=self.binding()
        mapped=json.loads((self.root/binding['path']).read_text(encoding='utf-8'))
        source=json.loads((self.root/mapped['source_receipt']['path']).read_text(encoding='utf-8'))
        frame=pd.read_parquet(self.root/source['provider_frame']['path'])
        self.assertEqual(frame.loc[0,'vol'],'4649595.14')
        self.assertEqual(frame.loc[0,'amount'],'2109910.834')
        self.assertEqual(source['request'],{'trade_date':'20200107'})
        self.assertEqual(source['endpoint'],'fund_daily')
        self.assertLessEqual(source['request_started_at'],source['received_at'])
        self.assertFalse(source['original_http_bytes_preserved'])
        self.assertFalse(source['first_publication_verified'])
        self.assertEqual(mapped['mapping_version'],'tushare_daily_decimal_shift_v1')
        self.assertEqual(len(self.calls),1)

    def test_resume_reuses_matching_evidence_without_redownloading_or_retimestamping(self):
        first=self.run_ingest()
        before=self.binding()
        second=self.run_ingest()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(before,self.binding())
        self.assertEqual(first['provider_source_evidence'],second['provider_source_evidence'])

    def test_legacy_mapped_cache_is_explicitly_unverified_and_not_retroactively_captured(self):
        self.run_ingest(FakeTushareDailyAdapter())
        result=self.run_ingest()
        self.assertEqual(self.calls,[])
        self.assertEqual(result['provider_source_evidence']['20200107']['status'],'legacy_mapped_cache_without_provider_evidence')
        self.assertFalse(result['provider_source_evidence']['20200107']['source_quality_verified'])

    def test_mapping_failure_preserves_received_frame_but_no_successful_mapping_binding(self):
        self.source=self.source.drop(columns=['open'])
        with self.assertRaises(ValueError):self.run_ingest()
        receipts=list((self.root/'provider_observations').rglob('source.json'))
        self.assertEqual(len(receipts),1)
        receipt=json.loads(receipts[0].read_text(encoding='utf-8'))
        self.assertTrue((self.root/receipt['provider_frame']['path']).is_file())
        manifest=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        self.assertNotIn('CN_ETF:daily:20200107',manifest['completed'])
        self.assertEqual(manifest['metadata']['daily_provider_evidence'],{})

    def test_changed_native_or_mapped_file_blocks_reuse_instead_of_certifying_it(self):
        for field in ('provider','mapped'):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
                self.root=Path(directory)
                self.run_ingest()
                mapping=json.loads((self.root/self.binding()['path']).read_text(encoding='utf-8'))
                if field=='provider':
                    receipt=json.loads((self.root/mapping['source_receipt']['path']).read_text(encoding='utf-8'))
                    path=self.root/receipt['provider_frame']['path']
                else:path=self.root/mapping['mapped_cache']['path']
                frame=pd.read_parquet(path)
                frame.loc[0,'amount']='999' if field=='provider' else 999
                frame.to_parquet(path,index=False)
                with self.assertRaisesRegex(ValueError,'evidence|fingerprint'):
                    self.run_ingest()

    def test_explicit_refresh_keeps_prior_provider_observation_and_rebinds_cache(self):
        self.run_ingest()
        first=self.binding()
        self.source.loc[0,'amount']='2109911.001'
        self.run_ingest(resume=False)
        second=self.binding()
        self.assertNotEqual(first,second)
        self.assertTrue((self.root/first['path']).is_file())
        self.assertEqual(len(list((self.root/'provider_observations').rglob('source.json'))),2)

    def test_bad_saved_evidence_path_is_rejected_before_external_file_access(self):
        self.run_ingest()
        path=self.root/'manifest.json'
        manifest=json.loads(path.read_text(encoding='utf-8'))
        manifest['metadata']['daily_provider_evidence']['CN_ETF:daily:20200107']['path']='../outside.json'
        path.write_text(json.dumps(manifest),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'path|evidence'):
            self.run_ingest()

    def test_retargeted_storage_marker_cannot_read_an_unbound_alternate_cache(self):
        self.run_ingest()
        mapping=json.loads((self.root/self.binding()['path']).read_text(encoding='utf-8'))
        path=self.root/mapping['mapped_cache']['path']
        changed=pd.read_parquet(path)
        changed.loc[0,'amount']=999
        changed.to_parquet(path.parent/'alternate.parquet',index=False)
        marker=path.parent/'_format.json'
        marker.write_text(json.dumps({'format':'parquet','file':'alternate.parquet'}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'evidence|fingerprint'):
            self.run_ingest()

    def test_wrong_provider_date_is_retained_for_diagnosis_but_not_admitted_to_cache(self):
        self.source.loc[0,'trade_date']='20200108'
        with self.assertRaisesRegex(ValueError,'date'):
            self.run_ingest()
        self.assertEqual(len(list((self.root/'provider_observations').rglob('source.json'))),1)
        self.assertFalse(DatasetStore(self.root).exists('raw/tushare/fund_daily',{'trade_date':'20200107'}))

    def test_csv_fallback_still_retains_provider_unit_text_and_hashes(self):
        with patch('quant_robot.storage.dataset_store._has_parquet_engine',return_value=False):
            result=self.run_ingest()
        self.assertEqual(result['provider_source_evidence']['20200107']['status'],'captured_provider_frame_matches_mapped_cache')
        mapping=json.loads((self.root/self.binding()['path']).read_text(encoding='utf-8'))
        receipt=json.loads((self.root/mapping['source_receipt']['path']).read_text(encoding='utf-8'))
        path=self.root/receipt['provider_frame']['path']
        self.assertEqual(path.suffix,'.csv')
        self.assertIn('4649595.14',path.read_text(encoding='utf-8'))
        self.assertIn('2109910.834',path.read_text(encoding='utf-8'))
        self.assertFalse(receipt['original_http_bytes_preserved'])

    def test_cn_capture_uses_stock_endpoint_and_keeps_market_identity(self):
        source=self.source.copy()
        source['ts_code']='000001.SZ'
        client=SimpleNamespace(daily=lambda **kwargs:source,
            trade_cal=self.client.trade_cal,
            adj_factor=lambda **kwargs:pd.DataFrame({'ts_code':['000001.SZ'],'trade_date':['20200107'],'adj_factor':[1.0]}))
        result=run_tushare_daily_ingest(TushareAdapter(client=client,max_retries=1),
            '2020-01-07','2020-01-07',self.root,market='CN')
        self.assertEqual(result['provider_source_evidence']['20200107']['status'],'captured_provider_frame_matches_mapped_cache')
        manifest=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        binding=manifest['metadata']['daily_provider_evidence']['daily:20200107']
        mapping=json.loads((self.root/binding['path']).read_text(encoding='utf-8'))
        source=json.loads((self.root/mapping['source_receipt']['path']).read_text(encoding='utf-8'))
        self.assertEqual((source['market'],source['endpoint']),('CN','daily'))

    def test_process_exit_before_manifest_does_not_create_a_verified_resume(self):
        code='''
import os,sys
from types import SimpleNamespace
import pandas as pd
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
import quant_robot.data.ingest.tushare_pipeline as pipeline
client=SimpleNamespace(
    fund_daily=lambda **kwargs:pd.DataFrame({'ts_code':['510300.SH'],'trade_date':['20200107'],
        'open':[4.0],'high':[4.1],'low':[3.9],'close':[4.0],'vol':['4649595.14'],'amount':['2109910.834']}),
    trade_cal=lambda **kwargs:pd.DataFrame({'exchange':['SSE'],'cal_date':['20200107'],'is_open':[1]}))
def crash(*args,**kwargs):os._exit(7)
pipeline._normalize_tushare_daily=crash
pipeline.run_tushare_daily_ingest(TushareAdapter(client=client,max_retries=1),'2020-01-07','2020-01-07',sys.argv[1],market='CN_ETF')
'''
        result=subprocess.run([sys.executable,'-c',code,str(self.root)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,7,result.stdout+result.stderr)
        self.assertEqual(len(list((self.root/'provider_observations').rglob('source.json'))),1)
        self.assertEqual(len(list((self.root/'provider_observations').rglob('mapping.json'))),1)
        result=self.run_ingest()
        self.assertEqual(self.calls,[])
        self.assertEqual(result['provider_source_evidence']['20200107']['status'],'legacy_mapped_cache_without_provider_evidence')
        self.assertFalse(result['provider_source_evidence']['20200107']['source_quality_verified'])
