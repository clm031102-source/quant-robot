"""Frozen credit-source collection; default preview, no spread or ETF outcome."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from scripts.collect_cn_etf_term_structure_history import now, sha, write_new
from quant_robot.data.sources.chinabond_credit_history import parse_credit_history, pair_months

SCOPE = 'configs/cn_etf_credit_premium_source_scope_20260922.json'
DIRECTORY = 'data/reports/positive_ev_20260922/credit_premium'
URL = 'https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery'


def expected_requests():
    ranges = [('2011', '2011-12-01', '2011-12-31')]
    ranges += [(str(y), f'{y}-01-01', f'{y}-12-31') for y in range(2012, 2019)]
    ranges += [('2019', '2019-01-01', '2019-12-30'), ('2020', '2020-01-03', '2020-12-31')]
    ranges += [(str(y), f'{y}-01-01', f'{y}-12-31') for y in [2021, 2022]]
    ranges += [('2023', '2023-01-01', '2023-09-30')]
    return [dict(id=key, params=dict(startDate=start, endDate=end, gjqx='1', qxId='zdqpjsylqx', locale='en_US')) for key,start,end in ranges]


def load_scope(root):
    scope = json.loads((root / SCOPE).read_bytes())
    if (scope['requests'] != expected_requests() or scope['max_requests'] != 13
            or scope['max_bytes_per_response'] != 1_000_000 or scope['retries'] != 0
            or scope['redirects'] is not False or scope['signal_generation_allowed'] is not False
            or scope['financial_execution_allowed'] is not False):
        raise ValueError('fixed source-only scope changed')
    for pin in scope['pins']:
        if sha(root / pin['path']) != pin['sha256']:
            raise ValueError('input/code pin changed: '+pin['path'])
    gate = json.loads((root / scope['gate_path']).read_bytes())
    if gate['status'] != 'ready' or gate['blockers'] or gate['primary_market'] != 'CN_ETF':
        raise ValueError('startup review gate not ready')
    for pin in gate['required_reading']:
        if sha(root / pin['path']) != pin['sha256']:
            raise ValueError('startup protocol changed')
    return scope


def collect(root):
    import requests
    scope = load_scope(root)
    folder = root / DIRECTORY / 'corpus'
    folder.mkdir(exist_ok=True)
    fingerprint = sha(root / SCOPE)
    write_new(folder / 'collection.claim.json', dict(scope_sha256=fingerprint, claimed_at=now()))
    for item in scope['requests']:
        path = folder / item['id']
        url = URL+'?'+urlencode(item['params'])
        claim = dict(scope_sha256=fingerprint, claimed_at=now(), url=url)
        write_new(path.with_suffix('.claim.json'), claim)
        receipt = dict(id=item['id'], params=item['params'], status='failed', **claim)
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.get(url, timeout=(10,20), stream=True, allow_redirects=False, verify=True) as response:
                    receipt.update(http_status=response.status_code, received_headers_at=now(), content_type=response.headers.get('Content-Type'))
                    raw = bytearray()
                    for chunk in response.iter_content(65536):
                        raw.extend(chunk)
                        if len(raw) > scope['max_bytes_per_response']:
                            raise ValueError('response exceeds frozen size limit')
                    receipt['body_completed_at'] = now()
                    with path.with_suffix('.html').open('xb') as handle:
                        handle.write(raw)
                    receipt.update(bytes=len(raw), sha256=sha(path.with_suffix('.html')))
                    if response.status_code != 200:
                        raise ValueError('HTTP response rejected')
                    rows = parse_credit_history(bytes(raw), start=item['params']['startDate'], end=item['params']['endDate'])
                    receipt.update(status='source_parsed', rows=len(rows))
        except Exception as error:
            receipt['error'] = type(error).__name__+': '+str(error)
            raise
        finally:
            write_new(path.with_suffix('.receipt.json'), receipt)
        print(json.dumps(dict(id=item['id'],rows=len(rows),bytes=len(raw))), flush=True)


def review(root):
    scope = load_scope(root)
    folder = root / DIRECTORY
    fingerprint = sha(root / SCOPE)
    claim = json.loads((folder/'corpus/collection.claim.json').read_bytes())
    assert claim['scope_sha256'] == fingerprint
    gov = json.loads((root/scope['government_corpus_path']).read_bytes())['source_rows_sorted']
    pilot = root/scope['corporate_pilot_path']
    corporate = parse_credit_history(pilot.read_bytes(),start='2019-12-31',end='2020-01-02')
    originals = [dict(path=str(pilot),sha256=sha(pilot),bytes=pilot.stat().st_size,rows=len(corporate),reused=True)]
    for item in scope['requests']:
        base = folder/'corpus'/item['id']
        receipt = json.loads(base.with_suffix('.receipt.json').read_bytes())
        request_claim = json.loads(base.with_suffix('.claim.json').read_bytes())
        assert receipt['scope_sha256'] == request_claim['scope_sha256'] == fingerprint
        assert receipt['status']=='source_parsed' and receipt['http_status']==200
        assert receipt['params']==item['params'] and receipt['url']==request_claim['url']==URL+'?'+urlencode(item['params'])
        assert scope['created_at'] <= claim['claimed_at'] <= request_claim['claimed_at'] == receipt['claimed_at'] <= receipt['received_headers_at'] <= receipt['body_completed_at']
        raw = base.with_suffix('.html')
        assert sha(raw)==receipt['sha256'] and raw.stat().st_size==receipt['bytes']
        rows = parse_credit_history(raw.read_bytes(),start=item['params']['startDate'],end=item['params']['endDate'])
        assert len(rows)==receipt['rows']
        corporate.extend(rows)
        originals.append(dict(path=raw.relative_to(root).as_posix(),sha256=sha(raw),bytes=raw.stat().st_size,rows=len(rows),reused=False))
    months = pair_months(gov,corporate,first='2011-12',last='2023-09')
    assert len(months)==142
    result = dict(created_at=now(), scope_sha256=fingerprint, originals=originals,
                  government_rows=len(gov),corporate_rows=len(corporate),months=months,
                  corporate_rows_sorted=sorted(corporate,key=lambda r:r['date']),
                  conditional_months=sum(r['status']=='conditional' for r in months),
                  unknown_months=[r['month'] for r in months if r['status']=='unknown'],
                  historical_vintage_certified=False,historical_release_clock_certified=False,
                  spreads_calculated=False,signals_generated=False,ETF_outcomes_read=False,
                  financial_execution_allowed=False)
    write_new(folder/'corpus_review.json',result)
    return {k:result[k] for k in ['government_rows','corporate_rows','conditional_months','unknown_months']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute',action='store_true')
    group.add_argument('--review',action='store_true')
    args=parser.parse_args()
    root=Path(args.root).resolve()
    if args.execute:
        collect(root)
        print(json.dumps(review(root),indent=2))
    elif args.review:
        print(json.dumps(review(root),indent=2))
    else:
        print(json.dumps(dict(status='preview',requests=len(load_scope(root)['requests']),financial_execution_allowed=False)))
