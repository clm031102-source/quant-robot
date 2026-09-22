"""Repair the observed H.10 table markup; retrieve only24never-requested releases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from scripts.collect_cn_etf_term_structure_history import now, sha, write_new
from quant_robot.data.sources.h10_currency_history import endpoint_snapshot

SCOPE = 'configs/cn_etf_currency_gold_source_repair_20260922.json'
DIRECTORY = 'data/reports/positive_ev_20260922/currency_gold_history'


def load_scope(root):
    scope = json.loads((root/SCOPE).read_bytes())
    for pin in scope['pins']:
        if sha(root/pin['path']) != pin['sha256']:
            raise ValueError('Repair input/code changed: '+pin['path'])
    base = json.loads((root/scope['original_scope']['path']).read_bytes())
    if sha(root/scope['original_scope']['path']) != scope['original_scope']['sha256']:
        raise ValueError('Original source scope changed')
    changed = 'src/quant_robot/data/sources/h10_currency_history.py'
    for pin in base['pins']:
        if pin['path'] == changed:
            frozen = subprocess.check_output(['git','show','608d8934:'+changed],cwd=root)
            if hashlib.sha256(frozen).hexdigest() != pin['sha256']:
                raise ValueError('Original parser identity differs')
        elif sha(root/pin['path']) != pin['sha256']:
            raise ValueError('Original unaffected pin changed')
    if (scope['requests'] != base['requests'][15:] or len(scope['requests']) != 24
            or base['requests'][14]['id'] != '20170626'
            or any(scope.get(k) is not False for k in
                   ('currency_changes_calculated','signals_generated','ETF_outcomes_read','financial_execution_allowed'))
            or scope['retries'] != 0 or scope['redirects'] is not False
            or scope['max_bytes_per_response'] != 3_000_000):
        raise ValueError('Exact unrequested24and unchanged source-only stage required')
    for item in base['requests'][:15]:
        receipt = json.loads((root/DIRECTORY/'corpus'/(item['id']+'.receipt.json')).read_bytes())
        assert receipt['http_status']==200
        assert receipt['status']==('failed' if item['id']=='20170626' else 'source_parsed')
    for item in scope['requests']:
        if any((root/DIRECTORY/sub/(item['id']+suffix)).exists()
               for sub in ('corpus','corpus_repair') for suffix in ('.claim.json','.receipt.json','.html')):
            raise ValueError('Remaining request already attempted')
    gate = json.loads((root/base['gate_path']).read_bytes())
    assert gate['status']=='ready' and not gate['blockers']
    for pin in gate['required_reading']:
        assert sha(root/pin['path'])==pin['sha256']
    return scope, base


def fetch(path, item, fingerprint):
    import requests
    claim = dict(item,scope_sha256=fingerprint,claimed_at=now())
    write_new(path.with_suffix('.claim.json'),claim)
    receipt = dict(claim,status='failed')
    try:
        with requests.Session() as session:
            session.trust_env=False
            with session.get(item['url'],timeout=(10,30),stream=True,allow_redirects=False,verify=True) as response:
                receipt.update(http_status=response.status_code,received_headers_at=now())
                raw=bytearray()
                for chunk in response.iter_content(65536):
                    raw.extend(chunk)
                    if len(raw)>3_000_000:
                        raise ValueError('Response exceeds frozen size cap')
                receipt['body_completed_at']=now()
                with path.with_suffix('.html').open('xb') as handle:handle.write(raw)
                receipt.update(bytes=len(raw),sha256=sha(path.with_suffix('.html')))
                if response.status_code!=200:raise ValueError('HTTP response rejected')
                result=endpoint_snapshot(bytes(raw),release_date=item['release_date'],quarter_end=item['quarter_end'])
                receipt.update(status='source_parsed',rows=len(result['source_rows']))
    except Exception as exc:
        receipt['error_type']=type(exc).__name__
        raise
    finally:
        write_new(path.with_suffix('.receipt.json'),receipt)
    return dict(id=item['id'],bytes=len(raw),rows=receipt['rows'])


def run(root, *, execute=False):
    scope,base=load_scope(root)
    if not execute:return dict(status='ready_source_repair',new_requests=24,reused_originals=17)
    folder=root/DIRECTORY
    corpus=folder/'corpus_repair'
    corpus.mkdir(exist_ok=True)
    fingerprint=sha(root/SCOPE)
    write_new(corpus/'collection.claim.json',dict(scope_sha256=fingerprint,claimed_at=now()))
    for item in scope['requests']:
        print(json.dumps(fetch(corpus/item['id'],item,fingerprint)),flush=True)
    endpoints, originals=[],[]
    new={item['id'] for item in scope['requests']}
    for item in base['endpoints']:
        if item['id'] in base['reused']:
            path=root/base['reused'][item['id']]['path']
        else:
            location='corpus_repair' if item['id'] in new else 'corpus'
            path=folder/location/(item['id']+'.html')
            receipt=json.loads(path.with_suffix('.receipt.json').read_bytes())
            assert receipt['sha256']==sha(path) and receipt['bytes']==path.stat().st_size
        endpoints.append(endpoint_snapshot(path.read_bytes(),release_date=item['release_date'],quarter_end=item['quarter_end']))
        originals.append(dict(path=path.relative_to(root).as_posix(),sha256=sha(path),
                              origin='new_repair_request' if item['id'] in new else 'retained_original'))
    report=dict(created_at=now(),scope_sha256=fingerprint,original_scope=scope['original_scope'],
        endpoints=endpoints,originals=originals,
        conditional_endpoints=sum(row['status']=='conditional' for row in endpoints),
        unknown_endpoints=[row['quarter_end'] for row in endpoints if row['status']=='unknown'],
        new_requests_original_scope=15,new_requests_repair_scope=24,reused_pilot_originals=2,
        historical_vintage_certified=False,historical_release_time_certified=False,
        currency_changes_calculated=False,signals_generated=False,ETF_outcomes_read=False,financial_execution_allowed=False)
    write_new(folder/'corpus_review.json',report)
    return {key:report[key] for key in ('conditional_endpoints','unknown_endpoints')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(Path(args.root).resolve(),execute=args.execute),indent=2))
