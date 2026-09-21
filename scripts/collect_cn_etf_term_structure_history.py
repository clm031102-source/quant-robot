"""One bounded source collection for the frozen sovereign-curve proposal.

Default is a pin-checked preview. This does not calculate spreads or ETF returns.
Every attempted request is retained and cannot be retried by this command.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.data.sources.chinabond_history import parse_history, monthly_inputs

SCOPE = 'configs/cn_etf_term_structure_source_scope_20260922.json'
DIRECTORY = 'data/reports/positive_ev_20260921/term_structure_review_20260922'
URL = 'https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery'
PROPOSAL_SHA = '1a28e483354fe9254283a0a20ba4c0284574031638a0ad8989226d5f6e469ebe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def expected_requests():
    ranges = [('warmup_remaining', '2011-12-01', '2011-12-25')]
    ranges += [(str(year), f'{year}-01-01', f'{year}-12-31') for year in range(2012, 2023)]
    ranges += [('last_year_remaining', '2023-01-01', '2023-09-24')]
    return [{'id': key, 'params': {'startDate': start, 'endDate': end,
             'gjqx': '0', 'qxId': 'hzsylqx', 'locale': 'en_US'}} for key, start, end in ranges]


def load_scope(root):
    scope = json.loads((root / SCOPE).read_bytes())
    if (scope['economic_proposal_sha256'] != PROPOSAL_SHA
            or scope['requests'] != expected_requests()
            or scope['max_requests'] != 13 or scope['max_bytes_per_response'] != 1_000_000
            or scope['retries'] != 0 or scope['redirects'] is not False
            or scope['financial_execution_allowed'] is not False
            or scope['signal_generation_allowed'] is not False):
        raise ValueError('fixed source-only scope changed')
    for pin in scope['pins']:
        if sha(root / pin['path']) != pin['sha256']:
            raise ValueError('source/code pin changed: ' + pin['path'])
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
    scope_sha = sha(root / SCOPE)
    write_new(folder / 'collection.claim.json', {'scope_sha256': scope_sha, 'claimed_at': now()})
    for request in scope['requests']:
        path = folder / request['id']
        url = URL + '?' + urlencode(request['params'])
        claim = {'scope_sha256': scope_sha, 'url': url, 'claimed_at': now()}
        write_new(path.with_suffix('.claim.json'), claim)
        receipt = {'id': request['id'], **claim, 'params': request['params'], 'status': 'failed'}
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.get(url, timeout=(10, 20), stream=True, allow_redirects=False) as response:
                    receipt.update(http_status=response.status_code, received_headers_at=now(),
                                   content_type=response.headers.get('Content-Type'),
                                   server_date_header=response.headers.get('Date'))
                    raw = bytearray()
                    for chunk in response.iter_content(65536):
                        raw.extend(chunk)
                        if len(raw) > scope['max_bytes_per_response']:
                            raise ValueError('response exceeds frozen size limit')
                    receipt['body_completed_at'] = now()
                    with path.with_suffix('.html').open('xb') as handle:
                        handle.write(raw)
                    receipt.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    if response.status_code != 200:
                        raise ValueError('HTTP response rejected')
                    rows = parse_history(bytes(raw), start=request['params']['startDate'],
                                         end=request['params']['endDate'])
                    receipt.update(status='source_parsed', rows=len(rows))
        except Exception as error:
            receipt['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            write_new(path.with_suffix('.receipt.json'), receipt)
        print(json.dumps({'id': request['id'], 'rows': len(rows), 'bytes': len(raw)}), flush=True)


def review(root):
    scope = load_scope(root)
    folder = root / DIRECTORY
    scope_sha = sha(root / SCOPE)
    collection_claim = json.loads((folder / 'corpus/collection.claim.json').read_bytes())
    assert collection_claim['scope_sha256'] == scope_sha
    all_rows, originals = [], []
    pilot = json.loads((folder / 'pilot_source_ledger.json').read_bytes())
    for item in pilot['requests']:
        raw_path = folder / item['file']
        assert sha(raw_path) == item['sha256'] and raw_path.stat().st_size == item['bytes']
        rows = parse_history(raw_path.read_bytes(), start=item['params']['startDate'],
                             end=item['params']['endDate'], max_rows=6)
        all_rows.extend(rows)
        originals.append({'path': str(raw_path.relative_to(root)).replace('\\', '/'),
                          'sha256': sha(raw_path), 'bytes': item['bytes'], 'rows': len(rows), 'reused': True})
    for item in scope['requests']:
        path = folder / 'corpus' / item['id']
        receipt = json.loads(path.with_suffix('.receipt.json').read_bytes())
        claim = json.loads(path.with_suffix('.claim.json').read_bytes())
        assert claim['scope_sha256'] == receipt['scope_sha256'] == scope_sha
        assert claim['url'] == receipt['url'] == URL + '?' + urlencode(item['params'])
        assert receipt['params'] == item['params'] and receipt['status'] == 'source_parsed'
        assert receipt['http_status'] == 200 and receipt['claimed_at'] == claim['claimed_at']
        clocks = [scope['created_at'], collection_claim['claimed_at'], claim['claimed_at'],
                  receipt['received_headers_at'], receipt['body_completed_at']]
        assert [datetime.fromisoformat(x) for x in clocks] == sorted(datetime.fromisoformat(x) for x in clocks)
        raw_path = path.with_suffix('.html')
        assert sha(raw_path) == receipt['sha256'] and raw_path.stat().st_size == receipt['bytes']
        rows = parse_history(raw_path.read_bytes(), start=item['params']['startDate'], end=item['params']['endDate'])
        assert len(rows) == receipt['rows']
        all_rows.extend(rows)
        originals.append({'path': str(raw_path.relative_to(root)).replace('\\', '/'),
                          'sha256': sha(raw_path), 'bytes': receipt['bytes'], 'rows': len(rows), 'reused': False})
    months = monthly_inputs(all_rows, first='2011-12', last='2023-09')
    assert len(months) == 142
    result = {'created_at': now(), 'scope_sha256': scope_sha, 'economic_proposal_sha256': PROPOSAL_SHA,
              'originals': originals, 'source_rows': len(all_rows), 'months': months,
              'conditional_months': sum(x['status'] == 'conditional' for x in months),
              'unknown_months': sum(x['status'] == 'unknown' for x in months),
              'weekend_source_rows': sum(datetime.fromisoformat(x['date']).weekday() >= 5 for x in all_rows),
              'source_rows_sorted': sorted(all_rows, key=lambda x: x['date']),
              'historical_vintage_certified': False, 'historical_release_clock_certified': False,
              'spreads_calculated': False, 'signals_generated': False, 'ETF_outcomes_read': False,
              'financial_execution_allowed': False}
    write_new(folder / 'corpus_review.json', result)
    return {key: result[key] for key in ('source_rows', 'conditional_months', 'unknown_months', 'weekend_source_rows')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--execute', action='store_true')
    group.add_argument('--review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.execute:
        collect(root)
        print(json.dumps(review(root), indent=2))
    elif args.review:
        print(json.dumps(review(root), indent=2))
    else:
        print(json.dumps({'status': 'preview', 'requests': len(load_scope(root)['requests']),
                          'spreads_or_financial_execution_allowed': False}, indent=2))
