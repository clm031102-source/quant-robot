"""Six bounded public-source requests for the frozen 2022-2025 gold account.

Retains opaque PDFs and raw prices; never calculates returns or grants account
admission. A source failure consumes this request scope rather than retrying.
"""
from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests

from quant_robot.research.monthly_diagnostic_registration import (
    resolve_path, runtime_environment, sha256, write_exclusive_json,
)
from quant_robot.research.geopolitical_account import make_plan

DIRECTORY = 'data/reports/geopolitical_account_20261104/source'
SCOPE = DIRECTORY + '/scope.json'
TRACKED_SCOPE = 'configs/cn_etf_geopolitical_account_source_scope_20261104.json'
BRANCH = 'codex/factor-batch-geopolitical-account-20261104'
PROPOSAL_SHA = '58a5f1e9ca392eadf6f2e90468d6100257a9e994e7b278eef5065d8f1d66dae4'
CADENCE_SHA = '94ea9f95a5522b9d40d1d51aa57dd24f2e9101fb51bad4b1b9c428088a2a081b'
QUOTE_URL = 'https://yunhq.sse.com.cn:32042/v1/sh1/dayk/518880'
CATALOG_URL = 'https://query.sse.com.cn/commonQuery.do'
IMPLEMENTATION = (
    'src/quant_robot/data/sources/geopolitical_account_sources.py',
    'src/quant_robot/research/geopolitical_account.py',
    'src/quant_robot/research/equity_gold_diagnostic.py',
    'src/quant_robot/paper/comparative_allocation.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/paper/position_buffer.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/storage/atomic.py',
    'scripts/collect_geopolitical_account_sources.py',
    'scripts/bootstrap.py',
)


def catalog_params():
    return {'isPagination': 'true', 'pageHelp.pageSize': 100, 'pageHelp.pageNo': 1,
        'pageHelp.beginPage': 1, 'pageHelp.cacheSize': 1, 'pageHelp.endPage': 1,
        'type': 'inParams', 'sqlId': 'COMMON_PL_JJXX_JJGG_NEW_L',
        'TITLE': '年度报告', 'SECURITY_CODE': '518880', 'BULLETIN_TYPE': '',
        'START_DATE': '2025-01-01', 'END_DATE': '2026-11-04', 'DATE_DESC': 1}


def complete_catalogue(payload, *, allow_empty=False):
    rows = payload.get('result'); page = payload.get('pageHelp', {})
    if (not isinstance(rows,list) or len(rows) > 100 or (not rows and not allow_empty)
            or type(page.get('total')) is not int or page['total'] != len(rows)
            or page.get('pageNo') != 1 or page.get('pageCount') != (1 if rows else 0)):
        raise ValueError('Complete single-page catalogue required')
    return rows


def annual_documents(payload):
    rows = complete_catalogue(payload)
    chosen = []
    for year in (2024, 2025):
        matches = []
        for row in rows:
            title = row.get('TITLE', '')
            if str(year) not in title or '年度报告' not in title:
                continue
            if any(word in title for word in ('更正', '修订', '补充')):
                raise ValueError('Annual correction requires separate source review')
            if any(word in title for word in ('摘要', '提示性', '提示公告')):
                continue
            matches.append(row)
        if len(matches) != 1:
            raise ValueError('Exactly one original full annual per fixed year required')
        row = matches[0]; path = row.get('URL', '')
        url = 'https://www.sse.com.cn' + path if path.startswith('/') else path
        split = urlsplit(url)
        if (split.scheme != 'https' or split.netloc != 'www.sse.com.cn'
                or not re.fullmatch(r'/disclosure/fund/announcement/c/(?:new/)?\d{4}-\d{2}-\d{2}/518880_[A-Za-z0-9_]+\.pdf', split.path)
                or split.query or split.fragment):
            raise ValueError('Unexpected official fund annual URL')
        chosen.append(dict(year=year, title=row['TITLE'], url=url))
    return chosen


def quote_window(payload, sessions):
    """Use only dates to construct absolute API positions excluding 2026 prices."""
    rows = payload.get('kline')
    if (payload.get('code') != '518880' or payload.get('begin') != 0
            or not isinstance(rows, list) or not rows or len(rows) > 5000
            or payload.get('total') != len(rows) or payload.get('end') != len(rows)
            or any(not isinstance(r, list) or len(r) != 1 or type(r[0]) is not int for r in rows)):
        raise ValueError('Complete date-only exchange response required')
    dates = [datetime.strptime(str(row[0]), '%Y%m%d').date().isoformat() for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError('Unique ascending exchange dates required')
    if not sessions or sessions[-1] > '2025-12-31':
        raise ValueError('Frozen pre-2026 sessions required')
    begin = dates.index(sessions[0]); end = dates.index(sessions[-1]) + 1
    if dates[begin:end] != sessions:
        raise ValueError('Exchange dates differ from frozen calendar')
    return dict(begin=begin, end=end, period='day', select='date,open,high,low,close,volume,amount')


def validate_raw_prices(payload, sessions):
    """Date identity and numeric integrity only; no returns or price summaries."""
    rows = payload.get('kline')
    if payload.get('code') != '518880' or not isinstance(rows, list) or len(rows) != len(sessions):
        raise ValueError('Exact gold raw price row count required')
    from decimal import Decimal
    for row, day in zip(rows, sessions):
        if (not isinstance(row, list) or len(row) != 7 or type(row[0]) is not int
                or str(row[0]) != day.replace('-', '') or any(type(v) is bool for v in row[1:])):
            raise ValueError('Exact scoped dates and numeric fields required')
        o, h, l, c, v, amount = [Decimal(str(x)) for x in row[1:]]
        if (not all(x.is_finite() for x in (o,h,l,c,v,amount)) or min(o,h,l,c) <= 0
                or min(v, amount) < 0 or not l <= min(o,c) <= max(o,c) <= h):
            raise ValueError('Invalid raw price or volume integrity')


def preflight(root, gate):
    raw = resolve_path(root, SCOPE).read_bytes(); scope = json.loads(raw)
    if raw != resolve_path(root, TRACKED_SCOPE).read_bytes():
        raise ValueError('Exact tracked source scope required')
    if (scope.get('stage') != 'fixed_geopolitical_account_source_preparation'
            or scope.get('branch') != BRANCH or scope.get('max_requests') != 6
            or scope.get('price_window') != ['2022-02-15', '2025-12-31']
            or scope.get('environment') != runtime_environment()
            or any(scope.get(k) is not False for k in ('returns_allowed', 'account_execution_allowed',
                'holdout_2026_prices_allowed', 'paper_promotion_allowed', 'live_boundary_allowed'))):
        raise ValueError('Exact fixed source-only scope required')
    for name in ('source_attempt_claim.json', 'source_outcome.json'):
        if resolve_path(root, DIRECTORY+'/'+name).exists():
            raise ValueError('Source scope consumed; no retry')
    inputs = scope['inputs']; code = scope['code_files']
    if set(code) != set(IMPLEMENTATION) or any(k != v['path'] for k,v in code.items()) or set(inputs) != {'proposal','method','account_plan','calendar','calendar_manifest',
                                    'cadence_result','cadence_review','method_review'}:
        raise ValueError('Complete method, source, calendar and review pins required')
    for role, item in {**inputs, **code}.items():
        if set(item) != {'path','sha256'} or sha256(resolve_path(root,item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Pinned preparation changed: '+role)
    if inputs['proposal']['sha256'] != PROPOSAL_SHA or inputs['cadence_result']['sha256'] != CADENCE_SHA:
        raise ValueError('Original proposal and consumed cadence required')
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    selected = gate['selected']
    if (not 0 <= age <= 30 or gate['status'] != 'ready' or gate['blockers']
            or gate['primary_market'] != 'CN_ETF' or selected['machine'] != 'office_desktop'
            or selected['task'] != 'factor_review' or selected['branch'] != BRANCH
            or selected['current_branch'] != BRANCH or gate['safety']['live_boundary_allowed'] is not False):
        raise ValueError('Fresh matching office source-review PM gate required')
    plan = json.loads(resolve_path(root,inputs['account_plan']['path']).read_bytes())
    if len(plan['sessions']) != 944 or [plan['sessions'][0], plan['sessions'][-1]] != scope['price_window']:
        raise ValueError('Exact 944-session preparation required')
    calendar_raw = resolve_path(root,inputs['calendar']['path']).read_bytes()
    calendar = list(csv.DictReader(io.StringIO(calendar_raw.decode('utf-8-sig'))))
    manifest = json.loads(resolve_path(root,inputs['calendar_manifest']['path']).read_bytes())
    if (manifest.get('artifact',{}).get('sha256') != sha256(calendar_raw)
            or manifest.get('decision',{}).get('calendar_cleared') is not True
            or manifest.get('decision',{}).get('blockers') != []
            or any(r.get('market') != 'CN' or r.get('is_open') != '1' for r in calendar)):
        raise ValueError('Cleared fingerprinted CN calendar required')
    cadence = json.loads(resolve_path(root,inputs['cadence_result']['path']).read_bytes())
    if plan != make_plan([r['date'] for r in calendar],cadence['rows']):
        raise ValueError('Price-independent source/calendar plan differs')
    method = json.loads(resolve_path(root,inputs['method']['path']).read_bytes())
    if (method.get('account_plan') != inputs['account_plan']
            or method.get('original_proposal') != inputs['proposal']
            or method.get('cadence_result') != inputs['cadence_result']
            or method.get('account_execution_allowed') is not False):
        raise ValueError('Complete frozen method binding required')
    return scope, raw, plan


def execute(root, gate):
    scope, raw, plan = preflight(root, gate)
    directory = resolve_path(root, DIRECTORY)
    claim = dict(scope_sha256=sha256(raw), claimed_at=datetime.now(timezone.utc).isoformat(),
                 status='claimed_before_source_requests', pm_gate=gate)
    write_exclusive_json(directory/'source_attempt_claim.json', claim)
    receipts = []
    session = requests.Session(); session.trust_env = False
    session.headers.update({'User-Agent':'Mozilla/5.0', 'Referer':'https://www.sse.com.cn/'})

    def fetch(name, url, params=None, *, pdf=False):
        if len(receipts) >= 6:
            raise ValueError('Fixed request budget exhausted')
        request = dict(url=url, params=params, scope_sha256=sha256(raw),
                       claimed_at=datetime.now(timezone.utc).isoformat())
        write_exclusive_json(directory/(name+'_claim.json'), request)
        content = bytearray(); maximum = 16*1024*1024 if pdf else 1024*1024
        with session.get(url, params=params, timeout=(5,30), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('No redirect or non-200 source response allowed')
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > maximum:
                    raise ValueError('Source response byte limit exceeded')
        target = directory/(name+('.pdf' if pdf else '.response'))
        with target.open('xb') as f: f.write(content)
        receipt = dict(request, status='retained_current_source_version',
            completed_at=datetime.now(timezone.utc).isoformat(), http_status=200,
            path=target.relative_to(Path(root).resolve()).as_posix(), bytes=len(content), sha256=sha256(content))
        write_exclusive_json(directory/(name+'_receipt.json'), receipt); receipts.append(receipt)
        if pdf:
            if not content.startswith(b'%PDF-'):
                raise ValueError('Expected original PDF bytes')
            return None
        return json.loads(content)

    terminal = dict(status='failed_consumed')
    try:
        catalogue = fetch('annual_catalog', CATALOG_URL, catalog_params())
        selected = annual_documents(catalogue)
        write_exclusive_json(directory/'selected_annuals.json', selected)
        for item in selected:
            fetch('annual_'+str(item['year']), item['url'], pdf=True)
        terminal_params = dict(catalog_params(), TITLE='', START_DATE='2025-12-01', END_DATE='2026-01-31')
        terminal_catalog = fetch('terminal_action_catalog', CATALOG_URL, terminal_params)
        complete_catalogue(terminal_catalog, allow_empty=True)
        dates = fetch('gold_dates', QUOTE_URL, dict(begin=0,end=5000,period='day',select='date'))
        parameters = quote_window(dates, plan['sessions'])
        write_exclusive_json(directory/'price_request_binding.json', parameters)
        prices = fetch('gold_ohlcva', QUOTE_URL, parameters)
        validate_raw_prices(prices, plan['sessions'])
        terminal = dict(status='raw_sources_retained_review_pending', requests=len(receipts),
            session_count=len(plan['sessions']), annual_years=[2024,2025],
            market_outcomes_computed=False, corporate_actions_reviewed=False,
            historical_execution_flags_verified=False, account_execution_allowed=False)
    except BaseException as exc:
        terminal['error_type'] = type(exc).__name__
        terminal['error_message'] = str(exc)
        raise
    finally:
        session.close()
        write_exclusive_json(directory/'source_outcome.json', dict(claim,
            **terminal, finished_at=datetime.now(timezone.utc).isoformat(), receipts=receipts))
    return terminal
