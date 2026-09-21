from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import pandas as pd

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.storage.dataset_store import DatasetStore


class TushareDecimalUnitIntegrationTests(unittest.TestCase):
    def test_native_unit_fixture_passes_adapter_ingest_and_storage_without_residue(self):
        source=pd.DataFrame({'ts_code':['510300.SH'],'trade_date':['20200107'],
            'open':[4.0],'high':[4.1],'low':[3.9],'close':[4.0],
            'vol':['4649595.14'],'amount':['2109910.834']})
        original=source.copy(deep=True)
        client=SimpleNamespace(fund_daily=lambda **kwargs:source,
            trade_cal=lambda **kwargs:pd.DataFrame({'exchange':['SSE'],'cal_date':['20200107'],'is_open':[1]}))
        adapter=TushareAdapter(client=client,max_retries=1)
        with tempfile.TemporaryDirectory() as directory:
            result=run_tushare_daily_ingest(adapter,'2020-01-07','2020-01-07',directory,market='CN_ETF')
            self.assertEqual(result['processed_rows'],1)
            store=DatasetStore(Path(directory))
            mapped=store.read_frame('raw/tushare/fund_daily',{'trade_date':'20200107'})
            processed=store.read_frame('processed/bars',{'frequency':'1d','market':'CN_ETF','year':'2020'})
            for frame in (mapped,processed):
                self.assertEqual(frame.loc[0,'volume'],464959514.0)
                self.assertEqual(frame.loc[0,'amount'],2109910834.0)
            pd.testing.assert_frame_equal(source,original)
            # Legacy resume is unchanged: it does not remap or certify an old cache.
            repeated=run_tushare_daily_ingest(adapter,'2020-01-07','2020-01-07',directory,market='CN_ETF')
            self.assertEqual(repeated['downloaded_trade_dates'],[])
