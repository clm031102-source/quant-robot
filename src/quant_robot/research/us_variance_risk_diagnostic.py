"""Fixed US variance-insurance proxy and quarterly CN ETF gross diagnostic."""
from datetime import date, datetime, timedelta
import csv
import io
import json
import math
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from quant_robot.research.disclosed_flow_diagnostic import open_return
from quant_robot.research.labor_risk_diagnostic import _description


def quarterly_anchors(sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered CN calendar required')
    out = []
    for year in range(2013, 2025):
        for month in (1, 4, 7, 10):
            if (year, month) > (2024, 4):
                break
            prefix = f'{year}-{month:02}'
            days = [d for d in sessions if d.startswith(prefix)]
            if len(days) < 2:
                raise ValueError('Two CN sessions per fixed quarter required')
            prior_month = (date(year, month, 1)-timedelta(days=1)).strftime('%Y-%m')
            out.append(dict(decision_date=days[0], entry_date=days[1], observation_month=prior_month))
    return out


def variance_signal(month, sessions, spx, vix):
    if sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered US equity calendar required')
    ids = [i for i, d in enumerate(sessions) if d.startswith(month)]
    if not ids or ids[0] == 0 or sessions[ids[-1]] not in vix:
        raise ValueError('Full completed month, previous close and terminal VIX required')
    required = [sessions[i] for i in range(ids[0]-1, ids[-1]+1)]
    if any(d not in spx or not math.isfinite(spx[d]) or spx[d] <= 0 for d in required):
        raise ValueError('Every calendar session and prior-month seed close required')
    level = vix[sessions[ids[-1]]]
    if not math.isfinite(level) or level <= 0:
        raise ValueError('Positive finite VIX required')
    realized = math.fsum((100*math.log(spx[sessions[i]]/spx[sessions[i-1]]))**2 for i in ids)
    gap = level**2/12-realized
    return dict(observation_date=sessions[ids[-1]], month_US_sessions=len(ids),
        implied_variance_pct2=level**2/12, realized_variance_pct2=realized,
        gap_pct2=gap, selected=int(gap > 0))


def describe(rows):
    result = _description(rows)
    states = [r['selected'] for r in rows]
    result['selected_runs'] = sum(z == 1 and (i == 0 or states[i-1] == 0) for i, z in enumerate(states))
    return result


def summarize(rows):
    if len(rows) != 45 or len([r for r in rows if r['entry_date'] >= '2020-01-01']) != 17:
        raise ValueError('Fixed45quarter/17later universe required')
    for r in rows:
        if (type(r['selected']) is not int or r['selected'] not in (0, 1)
                or type(r['sessions']) is not int or r['sessions'] <= 0
                or not math.isfinite(r['return_value']) or r['return_value'] <= -1):
            raise ValueError('Binary states, positive durations, finite returns greater than-1 required')
    full = describe(rows)
    later = describe([r for r in rows if r['entry_date'] >= '2020-01-01'])
    z, y, n = (np.array([r[k] for r in rows]) for k in ('selected', 'return_value', 'sessions'))
    starts = np.random.default_rng(20260921).integers(0, 45, size=(5000, 12))
    ids = ((starts[:, :, None]+np.arange(4)) % 45).reshape(5000, -1)[:, :45]
    zr, nr, lr = z[ids], n[ids], np.log1p(y[ids])
    exposures = (zr*nr).sum(axis=1)/nr.sum(axis=1)
    effects = ((zr-exposures[:, None])*lr).sum(axis=1)/nr.sum(axis=1)
    interval = [float(x) for x in np.quantile(effects, [.025, .975])]
    checks = dict(selected_count=full['selected_intervals'] >= 6, cash_count=full['unselected_intervals'] >= 6,
        later_selected_count=later['selected_intervals'] >= 3, later_cash_count=later['unselected_intervals'] >= 3,
        selected_runs=full['selected_runs'] >= 6, later_selected_runs=later['selected_runs'] >= 3,
        effect_lower_positive=interval[0] > 0, later_effect_positive=later['D_daily_log'] > 0,
        selected_mean_positive=full['selected_mean_gross'] is not None and full['selected_mean_gross'] > 0,
        later_mean_positive=later['selected_mean_gross'] is not None and later['selected_mean_gross'] > 0)
    return dict(full=full, later_2020_onward=later, bootstrap_D_daily_log_2_5_97_5=interval,
        bootstrap_replications=5000, block_quarters=4, seed=20260921, checks=checks,
        gross_screen_passed=all(checks.values()), annual={y: describe([r for r in rows if r['entry_date'].startswith(y)])
        for y in sorted({r['entry_date'][:4] for r in rows})}, net_positive_EV_verified=False,
        fresh_OOS=False, multiple_testing_adjusted=False, historical_vintage_verified=False,
        completed_account_trade_count=None)


def _iso(compact):
    return datetime.strptime(compact, '%Y%m%d').date().isoformat()


def _provider_rows(raw, fields):
    value = json.loads(raw)
    if value.get('code') != 0 or value['data']['fields'] != fields:
        raise ValueError('Exact successful provider schema required')
    return [dict(zip(fields, r, strict=True)) for r in value['data']['items']]


def us_sources(snapshots):
    calendar = _provider_rows(snapshots['US_calendar'], ['cal_date', 'is_open', 'pretrade_date'])
    by = {_iso(r['cal_date']): r for r in calendar}
    start, end = date(2012, 11, 1), date(2023, 12, 31)
    expected = {(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)}
    if (len(by) != len(calendar) or set(by) != expected
            or any(type(r['is_open']) is not int or r['is_open'] not in (0, 1) for r in calendar)):
        raise ValueError('Complete civil-day US calendar with strict open flags required')
    sessions = sorted(d for d, r in by.items() if r['is_open'])
    for i, day in enumerate(sessions[1:], 1):
        if _iso(by[day]['pretrade_date']) != sessions[i-1]:
            raise ValueError('US previous-session chain differs')
    rows = _provider_rows(snapshots['SPX'], ['ts_code', 'trade_date', 'open', 'high', 'low', 'close'])
    spx = {_iso(r['trade_date']): float(r['close']) for r in rows}
    if len(spx) != len(rows) or set(spx) != set(sessions) or any(r['ts_code'] != 'SPX' for r in rows):
        raise ValueError('Unique SPX identity and exact US session coverage required')
    vix = {}
    for r in csv.DictReader(io.StringIO(snapshots['VIX'].decode('utf-8-sig'))):
        day = datetime.strptime(r['DATE'], '%m/%d/%Y').date()
        if start <= day <= end:
            if day.isoformat() in vix:
                raise ValueError('Duplicate scoped VIX dates')
            vix[day.isoformat()] = float(r['CLOSE'])
    if not set(sessions) <= set(vix):
        raise ValueError('Missing VIX on US equity sessions')
    return sessions, spx, vix


def cn_sessions(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    sessions = []
    for role, start, end in [('old_calendar', date(2013, 1, 1), date(2014, 12, 31)),
                             ('calendar', date(2015, 1, 1), date(2024, 6, 28))]:
        rows = calendar_rows_from_snapshot(snapshots[role], snapshots[role+'_manifest'], start=start, end=end)
        sessions.extend(str(d) for d, opened in rows if opened)
    if sessions != sorted(set(sessions)):
        raise ValueError('Merged CN calendar must be unique and ordered')
    return sessions


def price_anchors(snapshots, anchors, sessions):
    x = json.loads(snapshots['early_price'])
    dates = [_iso(str(r[0])) for r in x['kline']]
    if x['code'] != '510300' or dates != [d for d in sessions if d < '2020-01-01']:
        raise ValueError('Exact early ETF date universe required')
    opens = {d: r[1] for d, r in zip(dates, x['kline'], strict=True) if d in anchors}
    for year in range(2020, 2025):
        days = [date.fromisoformat(d) for d in anchors if d.startswith(str(year))]
        bars = pd.read_parquet(io.BytesIO(snapshots[f'bars_{year}']), columns=['date', 'asset_id', 'market', 'currency', 'open'],
            filters=[('date', 'in', days), ('asset_id', '==', 'CN_ETF_XSHG_510300')])
        for r in bars.to_dict('records'):
            d = str(r['date'])
            if d not in anchors or d in opens or r['market'] != 'CN_ETF' or r['currency'] != 'CNY':
                raise ValueError('Unique scoped ETF/CNY anchors required')
            opens[d] = r['open']
    if sorted(opens) != sorted(anchors):
        raise ValueError('Complete price anchors required')
    return opens


def calculate(snapshots):
    sessions = cn_sessions(snapshots)
    anchors = quarterly_anchors(sessions)
    us, spx, vix = us_sources(snapshots)
    rows = []
    for a, b in zip(anchors, anchors[1:]):
        signal = variance_signal(a['observation_month'], us, spx, vix)
        assumed = datetime.fromisoformat(signal['observation_date']+'T18:00:00').replace(tzinfo=ZoneInfo('America/New_York'))
        decision = datetime.fromisoformat(a['decision_date']+'T15:00:00').replace(tzinfo=ZoneInfo('Asia/Shanghai'))
        if assumed >= decision:
            raise ValueError('US month-end source would not precede fixed CN decision')
        rows.append(dict(**a, **signal, exit_date=b['entry_date'],
            sessions=sessions.index(b['entry_date'])-sessions.index(a['entry_date']),
            assumed_source_to_decision_hours=(decision-assumed).total_seconds()/3600))
    opens = price_anchors(snapshots, [a['entry_date'] for a in anchors], sessions)
    events = json.loads(snapshots['actions'])['events']
    early = json.loads(snapshots['early_actions'])['events']
    events += [dict(asset_id=r['asset_id'], kind='cash_dividend', cash_amount_basis='gross',
        record_date=r['record_date'], ex_date=r['ex_date'], cash_per_share=r['cash_per_unit']) for r in early]
    if len(events) != 11 or len({r['record_date'] for r in events}) != 11:
        raise ValueError('Exactly11 unique reviewed distributions required')
    for r in events:
        if (r['asset_id'] != 'CN_ETF_XSHG_510300' or r['record_date'] not in sessions
                or r['ex_date'] not in sessions or sessions.index(r['record_date'])+1 != sessions.index(r['ex_date'])):
            raise ValueError('Reviewed record/ex session order required')
    for r in rows:
        r['return_value'] = open_return(r['entry_date'], r['exit_date'], opens[r['entry_date']], opens[r['exit_date']], events)
    return dict(diagnostic=summarize(rows), observations=rows, net_account_run=False,
        new_forward_paper_days=0, ETF_open_values_used=len(opens),
        price_basis='one_share_open_to_open_declared_cash_gross_v1',
        US_historical_publication_assumed=True)
