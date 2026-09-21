"""Collect the frozen remaining39H.10releases; no FX change or ETF outcome."""
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from scripts.collect_cn_etf_term_structure_history import now, sha, write_new
from quant_robot.data.sources.h10_currency_history import endpoint_snapshot, quarter_requests

SCOPE = 'configs/cn_etf_currency_gold_source_scope_20260922.json'
DIRECTORY = 'data/reports/positive_ev_20260922/currency_gold_history'


def load_scope(root):
    scope = json.loads((root/SCOPE).read_bytes())
    for pin in scope['pins']:
        if sha(root/pin['path']) != pin['sha256']:
            raise ValueError('Pinned source/code changed: '+pin['path'])
    catalog = json.loads((root/scope['catalog_path']).read_bytes())
    expected = quarter_requests(catalog)
    if (scope['endpoints'] != expected or scope['max_requests'] != 39
            or scope['max_bytes_per_response'] != 3_000_000 or scope['retries'] != 0
            or scope['redirects'] is not False
            or any(scope.get(k) is not False for k in
                   ('signals_generated', 'signal_generation_allowed', 'financial_execution_allowed', 'ETF_outcomes_read'))):
        raise ValueError('Fixed source-only scope changed')
    reused = scope['reused']
    if set(reused) != {'20131230', '20230925'}:
        raise ValueError('Exact two pilot releases must be reused')
    if scope['requests'] != [row for row in expected if row['id'] not in reused]:
        raise ValueError('Exactly39new releases required')
    gate = json.loads((root/scope['gate_path']).read_bytes())
    if gate['status'] != 'ready' or gate['blockers'] or gate['primary_market'] != 'CN_ETF':
        raise ValueError('Startup review gate not ready')
    for pin in gate['required_reading']:
        if sha(root/pin['path']) != pin['sha256']:
            raise ValueError('Startup protocol changed')
    return scope


def collect(root):
    import requests
    scope = load_scope(root)
    folder = root/DIRECTORY/'corpus'
    folder.mkdir(parents=True, exist_ok=True)
    fingerprint = sha(root/SCOPE)
    write_new(folder/'collection.claim.json', dict(scope_sha256=fingerprint, claimed_at=now()))
    for item in scope['requests']:
        path = folder/item['id']
        claim = dict(scope_sha256=fingerprint, claimed_at=now(), **item)
        write_new(path.with_suffix('.claim.json'), claim)
        receipt = dict(claim, status='failed')
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.get(item['url'],timeout=(10,30),stream=True,allow_redirects=False,verify=True) as response:
                    receipt.update(http_status=response.status_code, received_headers_at=now())
                    raw = bytearray()
                    for chunk in response.iter_content(65536):
                        raw.extend(chunk)
                        if len(raw) > scope['max_bytes_per_response']:
                            raise ValueError('Response exceeds frozen size cap')
                    receipt['body_completed_at'] = now()
                    with path.with_suffix('.html').open('xb') as handle:
                        handle.write(raw)
                    receipt.update(bytes=len(raw),sha256=sha(path.with_suffix('.html')))
                    if response.status_code != 200:
                        raise ValueError('HTTP response rejected')
                    result = endpoint_snapshot(bytes(raw),release_date=item['release_date'],quarter_end=item['quarter_end'])
                    receipt.update(status='source_parsed',rows=len(result['source_rows']))
        except Exception as exc:
            receipt['error_type'] = type(exc).__name__
            raise
        finally:
            write_new(path.with_suffix('.receipt.json'),receipt)
        print(json.dumps(dict(id=item['id'],bytes=len(raw),rows=receipt['rows'])),flush=True)


def review(root):
    scope = load_scope(root)
    fingerprint = sha(root/SCOPE)
    folder = root/DIRECTORY
    global_claim = json.loads((folder/'corpus/collection.claim.json').read_bytes())
    assert global_claim['scope_sha256'] == fingerprint
    endpoints, originals = [], []
    for item in scope['endpoints']:
        reused = item['id'] in scope['reused']
        if reused:
            path = root/scope['reused'][item['id']]['path']
            assert sha(path) == scope['reused'][item['id']]['sha256']
        else:
            base = folder/'corpus'/item['id']
            path = base.with_suffix('.html')
            claim = json.loads(base.with_suffix('.claim.json').read_bytes())
            receipt = json.loads(base.with_suffix('.receipt.json').read_bytes())
            assert receipt['scope_sha256'] == claim['scope_sha256'] == fingerprint
            assert receipt['status'] == 'source_parsed' and receipt['http_status'] == 200
            assert all(claim[k] == receipt[k] == v for k,v in item.items())
            assert scope['created_at'] <= global_claim['claimed_at'] <= claim['claimed_at'] <= receipt['received_headers_at'] <= receipt['body_completed_at']
            assert sha(path) == receipt['sha256'] and path.stat().st_size == receipt['bytes']
        result = endpoint_snapshot(path.read_bytes(),release_date=item['release_date'],quarter_end=item['quarter_end'])
        endpoints.append(result)
        originals.append(dict(path=path.relative_to(root).as_posix(),sha256=sha(path),reused=reused))
    result = dict(created_at=now(),scope_sha256=fingerprint,endpoints=endpoints,originals=originals,
        conditional_endpoints=sum(row['status']=='conditional' for row in endpoints),
        unknown_endpoints=[row['quarter_end'] for row in endpoints if row['status']=='unknown'],
        historical_vintage_certified=False,historical_release_time_certified=False,
        currency_changes_calculated=False,signals_generated=False,ETF_outcomes_read=False,
        financial_execution_allowed=False)
    write_new(folder/'corpus_review.json',result)
    return {k:result[k] for k in ('conditional_endpoints','unknown_endpoints')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.execute:
        collect(root)
        print(json.dumps(review(root),indent=2))
    else:
        print(json.dumps(dict(status='preview',requests=len(load_scope(root)['requests']),
                              financial_execution_allowed=False)))
