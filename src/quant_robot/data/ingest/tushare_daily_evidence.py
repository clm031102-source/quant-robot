"""Capture SDK daily frames before mapping; never certify source publication history."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from quant_robot.data.sources.tushare_mapping import map_tushare_daily
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.dataset_store import FORMAT_MARKER


MAPPING_VERSION = 'tushare_daily_decimal_shift_v1'


def _ref(store, path):
    return {'path':path.resolve().relative_to(store.root.resolve()).as_posix(),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def _verified_content(store, reference, *, max_bytes=None):
    if not isinstance(reference,dict) or set(reference)!={'path','sha256'}:
        raise ValueError('invalid daily provider evidence reference')
    relative=reference['path']
    if not isinstance(relative,str) or Path(relative).is_absolute():
        raise ValueError('invalid daily provider evidence path')
    path=(store.root/relative).resolve()
    if not path.is_relative_to(store.root.resolve()):
        raise ValueError('daily provider evidence path escapes dataset')
    if not path.is_file():
        raise ValueError('daily provider evidence file missing')
    if max_bytes is not None and path.stat().st_size>max_bytes:
        raise ValueError('daily provider evidence document exceeds size limit')
    content=path.read_bytes()
    if max_bytes is not None and len(content)>max_bytes:
        raise ValueError('daily provider evidence document exceeds size limit')
    if hashlib.sha256(content).hexdigest()!=reference['sha256']:
        raise ValueError('daily provider evidence fingerprint mismatch')
    return path,content


def _verified_file(store, reference):
    return _verified_content(store,reference)[0]


def _verified_json(store, reference):
    _,content=_verified_content(store,reference,max_bytes=65536)
    return json.loads(content.decode('utf-8'))


def _verified_frame(store, frame_ref, marker_ref):
    path=_verified_file(store,frame_ref)
    marker_path=_verified_file(store,marker_ref)
    marker=_verified_json(store,marker_ref)
    if (marker_path!=path.parent/FORMAT_MARKER or marker.get('file')!=path.name
            or marker.get('format')!=path.suffix.lstrip('.')):
        raise ValueError('daily provider evidence storage selection mismatch')
    return path


def fetch_provider_capture(adapter, trade_date, market, store):
    method=getattr(adapter,'fetch_provider_daily_by_trade_date',None)
    if not callable(method):
        return None
    if (market not in {'CN','CN_ETF'} or not isinstance(trade_date,str)
            or len(trade_date)!=8 or not trade_date.isdigit()):
        raise ValueError('invalid provider daily request identity')
    datetime.strptime(trade_date,'%Y%m%d')
    started=datetime.now(timezone.utc).isoformat()
    frame=method(trade_date,market=market)
    received=datetime.now(timezone.utc).isoformat()
    if not isinstance(frame,pd.DataFrame):
        raise ValueError('provider daily response must be a DataFrame')
    frame=frame.copy(deep=True)
    if not frame.columns.is_unique or not all(isinstance(key,str) for key in frame.columns):
        raise ValueError('provider daily columns must have distinct string names')
    endpoint='fund_daily' if market=='CN_ETF' else 'daily'
    native=store.write_frame(frame,'provider_observations/tushare/'+endpoint,
        {'trade_date':trade_date,'observation':uuid4().hex})
    source_path=native.parent/'source.json'
    source={'schema_version':1,'provider':'tushare','market':market,'endpoint':endpoint,
        'request':{'trade_date':trade_date},'request_started_at':started,'received_at':received,
        'row_count':len(frame),'columns':list(frame.columns),'dtypes':{key:str(value) for key,value in frame.dtypes.items()},
        'provider_frame':_ref(store,native),'provider_format_marker':_ref(store,native.parent/FORMAT_MARKER),
        'provider_units':{'vol':'hands','amount':'thousand_CNY'},
        'representation':'SDK DataFrame persisted with DatasetStore;not the original HTTP body',
        'original_http_bytes_preserved':False,'first_publication_verified':False,'source_quality_verified':False}
    atomic_write_json(source_path,source)
    # Keep the received frame even when mapping fails. No success binding exists yet.
    if not frame.empty and ('trade_date' not in frame or not frame['trade_date'].astype(str).eq(trade_date).all()):
        raise ValueError('provider daily response date differs from request')
    mapped=map_tushare_daily(frame)
    capture={'source_path':source_path,'source_ref':_ref(store,source_path),
        'mapping_version':MAPPING_VERSION,
        'mapping_implementation_sha256':hashlib.sha256(Path(map_tushare_daily.__code__.co_filename).read_bytes()).hexdigest()}
    return mapped,capture


def bind_mapped_capture(store, capture, mapped_path):
    source=_verified_json(store,capture['source_ref'])
    _verified_frame(store,source['provider_frame'],source['provider_format_marker'])
    path=capture['source_path'].parent/'mapping.json'
    if path.exists():
        raise ValueError('provider daily mapping evidence already committed')
    record={'schema_version':1,'source_receipt':capture['source_ref'],'mapped_cache':_ref(store,mapped_path),
        'mapped_format_marker':_ref(store,mapped_path.parent/FORMAT_MARKER),
        'mapping_version':capture['mapping_version'],'mapping_implementation_sha256':capture['mapping_implementation_sha256'],
        'mapped_at':datetime.now(timezone.utc).isoformat(),'source_quality_verified':False}
    atomic_write_json(path,record)
    return _ref(store,path)


def inspect_provider_capture(store, binding, *, trade_date, market):
    if binding is None:
        return {'status':'legacy_mapped_cache_without_provider_evidence','source_quality_verified':False}
    try:
        mapping=_verified_json(store,binding)
        source=_verified_json(store,mapping['source_receipt'])
        native=_verified_frame(store,source['provider_frame'],source['provider_format_marker'])
        mapped=_verified_frame(store,mapping['mapped_cache'],mapping['mapped_format_marker'])
        endpoint='fund_daily' if market=='CN_ETF' else 'daily'
        expected=store.partition_path('raw/tushare/'+endpoint,{'trade_date':trade_date}).resolve()
        if (source['schema_version']!=1 or mapping['schema_version']!=1 or source['market']!=market
                or source['endpoint']!=endpoint or source['request']!={'trade_date':trade_date}
                or mapped.parent!=expected or native==mapped or source['source_quality_verified'] is not False
                or mapping['source_quality_verified'] is not False):
            raise ValueError('daily provider evidence identity mismatch')
        return {'status':'captured_provider_frame_matches_mapped_cache','binding':binding,
            'received_at':source['received_at'],'mapping_version':mapping['mapping_version'],
            'source_quality_verified':False,'first_publication_verified':False}
    except (KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        raise ValueError('invalid daily provider evidence') from exc
