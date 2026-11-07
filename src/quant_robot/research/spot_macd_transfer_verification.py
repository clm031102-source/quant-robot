"""Reconcile retained spot ledgers and fixed statistics without importing a simulator.

This verifier reads only normalized input and saved account artifacts. It never
opens original exchange payloads, computes a signal, or executes an account.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, Context, localcontext, ROUND_HALF_EVEN, ROUND_FLOOR, ROUND_CEILING, FloatOperation
import hashlib
import json
from pathlib import Path
import re
import numpy as np
METHOD_SHA = '6ec96945600c35d7c4f8c31fcd3c4d090535517a9d41948faa6387827953b9f0'
Q, STEP, ZERO, INITIAL = (D('.00000001'), D('.00001'), D(0), D(1000))
CASES = tuple(((f, s) for f in (5, 10, 20) for s in (0, 10, 30)))
ACCOUNT_KEYS = {f'fee{f}_slip{s}/{role}' for f, s in CASES for role in ('strategy', 'holding', 'cash')}

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()

def _context():
    result = Context(prec=40, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
    result.traps[FloatOperation] = True
    result.clear_flags()
    return result

def down(x):
    return x.quantize(Q, rounding=ROUND_FLOOR)

def up(x):
    return x.quantize(Q, rounding=ROUND_CEILING)

def floorqty(x):
    return (x / STEP).to_integral_value(rounding=ROUND_FLOOR) * STEP

def eq(actual, expected, label):
    if not isinstance(actual, str) or not D(actual).is_finite() or D(actual) != expected:
        raise ValueError('Recorded amount mismatch: ' + label)

def _compare_observations(expected_rows, actual_rows, label):
    if len(expected_rows) != len(actual_rows):
        raise ValueError('Recorded observation count mismatch: ' + label)
    for expected, actual in zip(expected_rows, actual_rows):
        for key, value in expected.items():
            if isinstance(value, D):
                eq(actual[key], value, label + '/' + key)
            elif type(actual[key]) is not type(value) or actual[key] != value:
                raise ValueError('Recorded observation mismatch: ' + label + '/' + key)

def _identity(value, nature, registration, normalized, provenance):
    expected_class = 'conditional_historical' if nature == 'retained_official_history' else 'artificial_historical_adapter_test'
    for key, expected in {'evidence_class': expected_class, 'source_nature': nature, 'registration_sha256': registration, 'normalized_input_sha256': normalized, 'provenance_sha256': provenance, 'method_sha256': METHOD_SHA}.items():
        if value.get(key) != expected:
            raise ValueError('Evidence identity mismatch: ' + key)
    if value.get('historical_returns_computed') is not (nature == 'retained_official_history'):
        raise ValueError('Historical evidence classification mismatch')
    if value.get('qualified') is not False or value.get('real_forward_days_added') != 0:
        raise ValueError('Diagnostic cannot claim qualification or forward evidence')

def _fixture(value):
    if set(value) != {'artifact_type', 'asset_id', 'market', 'source_nature', 'warmup_days', 'daily', 'execution'} or value['artifact_type'] != 'claimed_spot_transfer_normalized_input_v1' or value['asset_id'] != 'BTCUSDT' or (value['market'] != 'spot') or (value['source_nature'] not in ('retained_official_history', 'artificial_protocol_fixture')) or (value['warmup_days'] != 366) or (len(value['daily']) != 2192) or (len(value['execution']) != 1827):
        raise ValueError('Fixed normalized source contract mismatch')
    for i, row in enumerate(value['daily']):
        if set(row) != {'date', 'open', 'high', 'low', 'close', 'volume'} or row['date'] != (date(2018, 1, 1) + timedelta(days=i)).isoformat():
            raise ValueError('Daily time/schema mismatch')
        for key in ('open', 'high', 'low', 'close', 'volume'):
            if not isinstance(row[key], str) or not D(row[key]).is_finite() or D(row[key]) < 0 or (key != 'volume' and D(row[key]) == 0):
                raise ValueError('Invalid normalized daily decimal string')
        if D(row['low']) > min(D(row['open']), D(row['close'])) or D(row['high']) < max(D(row['open']), D(row['close'])):
            raise ValueError('Normalized OHLC mismatch')
    for i, row in enumerate(value['execution']):
        day = (date(2019, 1, 2) + timedelta(days=i)).isoformat()
        if set(row) != {'date', 'open_time', 'close_time', 'open', 'volume'} or row['date'] != day or row['open_time'] != day + 'T00:03:00Z' or (row['close_time'] != day + 'T00:03:59.999Z'):
            raise ValueError('Execution time/schema mismatch')
        for key in ('open', 'volume'):
            if not isinstance(row[key], str) or not D(row[key]).is_finite() or D(row[key]) < 0 or (key == 'open' and D(row[key]) == 0):
                raise ValueError('Invalid normalized execution decimal string')

def _statistics(accounts, recorded):
    columns, keys = ([], [])
    for f, s in CASES:
        key = f'fee{f}_slip{s}'
        left = np.array([float(row['PnL']) for row in accounts[key + '/strategy']['daily_NAV']], dtype=np.float64)
        right = np.array([float(row['PnL']) for row in accounts[key + '/holding']['daily_NAV']], dtype=np.float64)
        columns.extend((left, left - right))
        keys.extend((key + '/net', key + '/minus_holding'))
    values = np.column_stack(columns)
    if values.shape != (1827, 18) or not np.isfinite(values).all():
        raise ValueError('Nonfinite fixed endpoint matrix')
    checks = {'N': 1827, 'replications': 5000, 'block': 20, 'starts_per_replication': 92, 'seed': 20261107, 'shared_indices_for_all18': True, 'units': 'USDT/observed interval', 'statistic': 'arithmetic_mean', 'endpoint_keys': keys, 'final_interval_is_partial': True}
    for key, expected in checks.items():
        if recorded.get(key) != expected:
            raise ValueError('Frozen statistical specification mismatch: ' + key)
    rng = np.random.Generator(np.random.PCG64(20261107))
    means = np.empty((5000, 18), dtype=np.float64)
    for k in range(5000):
        starts = rng.integers(0, 1827, size=92)
        indexes = np.concatenate([(np.arange(20) + start) % 1827 for start in starts])[:1827]
        means[k] = values[indexes].mean(axis=0)
    expected_hash = hashlib.sha256(means.astype('<f8').tobytes()).hexdigest()
    if recorded.get('replicate_means_sha256') != expected_hash:
        raise ValueError('Bootstrap replication digest mismatch')
    lower = np.quantile(means, 0.05 / 18, axis=0, method='linear')
    if recorded.get('lower') != dict(zip(keys, lower.tolist())) or recorded.get('observed_means') != dict(zip(keys, values.mean(axis=0).tolist())):
        raise ValueError('Fixed endpoint statistic mismatch')
    return {'endpoints': 18, 'replications': 5000, 'replicate_means_sha256': expected_hash, 'checked': True}

def verify_recorded_accounts(root, decoded_input_ref, account_refs, statistics_ref, expected_registration_sha256):
    """Audit already-recorded evidence. This function grants no execution permission."""
    root = Path(root).resolve()
    if not re.fullmatch('[0-9a-f]{64}', expected_registration_sha256):
        raise ValueError('Expected registration digest required')
    seen = {}

    def readpin(pin):
        if set(pin) != {'path', 'sha256'} or not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
            raise ValueError('Exact artifact reference required')
        path = (root / pin['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Artifact outside declared root')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('Artifact fingerprint mismatch')
        seen[path] = pin['sha256']
        return json.loads(raw)
    if set(account_refs) != ACCOUNT_KEYS:
        raise ValueError('Exactly27 distinct frozen roles/cost cases required')
    normalized = readpin(decoded_input_ref)
    if set(normalized) != {'fixture', 'provenance'}:
        raise ValueError('Normalized evidence wrapper mismatch')
    fixture = normalized['fixture']
    with localcontext(_context()):
        _fixture(fixture)
    nature = fixture['source_nature']
    provenance_method = normalized['provenance'].get('method_sha256')
    if nature == 'retained_official_history' and provenance_method != METHOD_SHA:
        raise ValueError('Actual source method provenance differs from frozen contract')
    input_digest, provenance_digest = (_digest(normalized), _digest(normalized['provenance']))
    suite = {'artifacts': account_refs}
    review = []
    accounts = {}
    with localcontext(_context()):
        for key, pin in suite['artifacts'].items():
            a = readpin(pin)
            _identity(a, nature, expected_registration_sha256, input_digest, provenance_digest)
            accounts[key] = a
            f, s = (D(a['fee_bps']) / 10000, D(a['slippage_bps']) / 10000)
            role = a['role']
            if not role in ('strategy', 'holding', 'cash'):
                raise ValueError('Recorded ledger invariant mismatch')
            if not key == f"fee{a['fee_bps']}_slip{a['slippage_bps']}/{role}":
                raise ValueError('Recorded ledger invariant mismatch')
            if any(type(x.get('index')) is not int or not 0 <= x['index'] < 1827 for x in a['fills']):
                raise ValueError('Fill index outside fixed execution intervals')
            fills = {x['index']: x for x in a['fills']}
            if not len(fills) == len(a['fills']):
                raise ValueError('Recorded ledger invariant mismatch')
            cash, btc, peak, prevNAV, prevDD = (INITIAL, ZERO, INITIAL, INITIAL, ZERO)
            legitimate_exit_residual = False
            basefees, quotefees, buydebits, sellcredits = (ZERO, ZERO, ZERO, ZERO)
            basefee_value, rounding_cost, tradable_exits = ZERO, ZERO, 0
            expected_obs = []
            expected_risks = []
            expected_curve = []
            lots = []
            expost = []
            maxdd = ZERO
            for i, minute in enumerate(fixture['execution']):
                dailyref = prevNAV
                active = False
                openprice = D(minute['open'])
                prior = fixture['daily'][fixture['warmup_days'] + i - 1]
                capacity = sum((D(x['volume']) for x in fixture['daily'][fixture['warmup_days'] + i - 20:fixture['warmup_days'] + i]), ZERO) / 20 * D('.01')
                phases = [('00:03_prefill', openprice, False)]
                if i in fills:
                    phases.append(('00:03_postfill', openprice, True))
                if i < len(fixture['execution']) - 1:
                    phases.append(('next00:02_completed_close', D(fixture['daily'][fixture['warmup_days'] + i]['close']), False))
                for phase, price, apply_fill in phases:
                    if apply_fill:
                        x = fills[i]
                        side = x['side']
                        qty = D(x['quantity'])
                        execprice = price * (1 + s if side == 'buy' else 1 - s)
                        if not (side in ('buy', 'sell') and qty >= STEP and (qty == floorqty(qty)) and (qty <= capacity)):
                            raise ValueError('Recorded ledger invariant mismatch')
                        if not qty * execprice >= 5:
                            raise ValueError('Recorded ledger invariant mismatch')
                        eq(x['raw_open'], price, 'raw open')
                        if x['decision_time'] != '00:02' or x['execution_time'] != '00:03':
                            raise ValueError('Fill timing mismatch')
                        eq(x['capacity'], capacity, 'capacity')
                        eq(x['planned_price'], D(prior['close']) * (1 + s if side == 'buy' else 1 - s), 'planprice')
                        eq(x['actual_price'], execprice, 'executionprice')
                        eq(x['cash_before'], cash, 'beforecash')
                        eq(x['BTC_before'], btc, 'beforeBTC')
                        if side == 'buy':
                            debit = up(qty * execprice)
                            fee = up(qty * f)
                            net = qty - fee
                            if not (debit <= cash and net > 0):
                                raise ValueError('Recorded ledger invariant mismatch')
                            cash -= debit
                            btc += net
                            buydebits += debit
                            basefees += fee
                            basefee_value += fee * execprice
                            rounding_cost += debit - qty * execprice
                            eq(x['quote_fee'], ZERO, 'buy quote fee')
                            active = True
                            legitimate_exit_residual = False
                            lots.append({'cycle': x['cycle'], 'remaining': net, 'cost': debit, 'realized': ZERO, 'buy_index': i, 'net_BTC': net, 'original_cost': debit})
                            eq(x['cash_debit'], debit, 'buydebit')
                            eq(x['base_fee'], fee, 'buyfee')
                            eq(x['net_BTC'], net, 'netBTC')
                        else:
                            if not qty <= btc:
                                raise ValueError('Recorded ledger invariant mismatch')
                            gross = down(qty * execprice)
                            fee = up(qty * execprice * f)
                            if not gross >= fee:
                                raise ValueError('Recorded ledger invariant mismatch')
                            remaining = qty
                            alloc = []
                            for lot in lots:
                                sold = min(remaining, lot['remaining'])
                                if sold <= 0:
                                    continue
                                cost = lot['cost'] if sold == lot['remaining'] else lot['cost'] * sold / lot['remaining']
                                lot['remaining'] -= sold
                                lot['cost'] -= cost
                                remaining -= sold
                                alloc.append((lot, sold, cost))
                                if remaining == 0:
                                    break
                            if not (remaining == 0 and len(alloc) == len(x['FIFO'])):
                                raise ValueError('Recorded ledger invariant mismatch')
                            gleft, fleft = (gross, fee)
                            for j, ((lot, sold, cost), actual) in enumerate(zip(alloc, x['FIFO'])):
                                g = gleft if j == len(alloc) - 1 else down(gross * sold / qty)
                                ff = fleft if j == len(alloc) - 1 else down(fee * sold / qty)
                                gleft -= g
                                fleft -= ff
                                lot['realized'] += g - ff - cost
                                if not actual['cycle'] == lot['cycle']:
                                    raise ValueError('Recorded ledger invariant mismatch')
                                for field, v in [('quantity', sold), ('released_cost', cost), ('gross', g), ('quote_fee', ff)]:
                                    eq(actual[field], v, field)
                            if not (gleft == 0 and fleft == 0):
                                raise ValueError('Recorded ledger invariant mismatch')
                            cash += gross - fee
                            btc -= qty
                            sellcredits += gross - fee
                            quotefees += fee
                            rounding_cost += qty * execprice - gross
                            eq(x['base_fee'], ZERO, 'sell base fee')
                            eq(x['gross_proceeds'], gross, 'gross sale proceeds')
                            legitimate_exit_residual = btc < STEP
                            tradable_exits += int(btc < STEP)
                            eq(x['cash_credit'], gross - fee, 'sellcredit')
                            eq(x['quote_fee'], fee, 'sellfee')
                        eq(x['cash_after'], cash, 'aftercash')
                        eq(x['BTC_after'], btc, 'afterBTC')
                        if qty > D(minute['volume']) * D('.01'):
                            expost.append(dict(index=i, known_at='00:04', filled_quantity=qty, minute_volume=D(minute['volume']), conditional_fill_retained=True))
                    nav = cash + btc * price
                    peak = max(peak, nav)
                    dd = 1 - nav / peak
                    loss = (dailyref - nav) / dailyref
                    maxdd = max(maxdd, dd)
                    active = active or (floorqty(btc) >= STEP and floorqty(btc) * price * (1 - s) >= 5)
                    fresh = prevDD < D('.4') <= dd
                    dd_event = dd >= D('.4') and (active or fresh)
                    daily_event = loss >= D('.02')
                    r = dict(index=i, phase=phase, price=price, cash=cash, BTC=btc, NAV=nav, peak=peak, DD=dd, daily_loss=loss, day_active=active, fresh_DD_cross=fresh, DD_event=dd_event, daily_event=daily_event, trigger=dd_event or daily_event)
                    expected_obs.append(r)
                    if dd >= D('.4') or daily_event:
                        expected_risks.append(r)
                    prevDD = dd
                if i == len(fixture['execution']) - 1:
                    nav = cash if btc < STEP else cash + btc * openprice
                else:
                    nav = cash + btc * D(fixture['daily'][fixture['warmup_days'] + i]['close'])
                expected_curve.append(dict(index=i, NAV=nav, PnL=nav - prevNAV, cash=cash, BTC=btc, economic_flat=btc == 0 or (legitimate_exit_residual and 0 < btc < STEP), active_exposure=active, positive_inventory=btc > 0, mark=price, kind='terminal_partial_interval' if i == 1826 else 'completed_daily'))
                prevNAV = nav
            if not (len(expected_obs) == len(a['observed_wallets']) and len(expected_risks) == len(a['risk_records'])):
                raise ValueError('Recorded ledger invariant mismatch')
            _compare_observations(expected_obs, a['observed_wallets'], key + '/observed')
            _compare_observations(expected_risks, a['risk_records'], key + '/risk')
            if not len(a['daily_NAV']) == len(expected_curve) == 1827:
                raise ValueError('Recorded ledger invariant mismatch')
            for expected, actual in zip(expected_curve, a['daily_NAV']):
                if not expected['index'] == actual['index']:
                    raise ValueError('Recorded ledger invariant mismatch')
                if not actual['date'] == fixture['execution'][expected['index']]['date']:
                    raise ValueError('Recorded ledger invariant mismatch')
                if not actual['economic_flat'] is expected['economic_flat']:
                    raise ValueError('Recorded ledger invariant mismatch')
                for k in ('active_exposure', 'positive_inventory', 'kind'):
                    if type(actual[k]) is not type(expected[k]) or actual[k] != expected[k]:
                        raise ValueError('Curve observation mismatch: ' + k)
                if expected['index'] == 1826:
                    eq(actual['mark_NAV'], expected['cash'] + expected['BTC'] * expected['mark'], 'curve terminal mark')
                for k in ('NAV', 'PnL', 'cash', 'BTC', 'mark'):
                    eq(actual[k], expected[k], 'curve' + k)
            for expected, actual in zip(lots, a['lots']):
                if not expected['cycle'] == actual['cycle'] or type(actual['buy_index']) is not int or actual['buy_index'] != expected['buy_index']:
                    raise ValueError('Recorded ledger invariant mismatch')
                for k, v in [('remaining_BTC', expected['remaining']), ('remaining_cost', expected['cost']), ('realized_PnL', expected['realized']), ('net_BTC', expected['net_BTC']), ('original_cost', expected['original_cost'])]:
                    eq(actual[k], v, 'lot' + k)
            if not (len(lots) == len(a['lots']) and sum((x['remaining'] for x in lots), ZERO) == btc):
                raise ValueError('Recorded ledger invariant mismatch')
            if not cash == INITIAL - buydebits + sellcredits:
                raise ValueError('Recorded ledger invariant mismatch')
            _compare_observations(expost, a['capacity_failures'], key + '/capacity')
            summary = a['summary']
            for label, expected_amount in [('initial_cash', INITIAL), ('average_cash', sum((x['cash'] for x in expected_curve), ZERO)/1827), ('buy_fee_quote_reporting', basefee_value), ('quote_rounding_cost', rounding_cost)]:
                eq(summary[label], expected_amount, 'summary ' + label)
            for label, expected_count in [('fill_count', len(fills)), ('rejection_count', len(a['rejections'])), ('full_cash_days', sum(x['BTC'] == 0 for x in expected_curve)), ('nontradable_days', sum(not x['active_exposure'] for x in expected_curve)), ('tradable_exit_episodes', tradable_exits), ('skipped_entry_cycles', sum(x['entry_status'] != 'planned' for x in a['cycles']))]:
                if type(summary[label]) is not int or summary[label] != expected_count:
                    raise ValueError('Summary count mismatch: ' + label)
            if summary['account_reconciled'] is not True:
                raise ValueError('Account reconciliation flag mismatch')
            for k, v in [('cash', cash), ('remaining_BTC', btc), ('net_PnL', prevNAV - INITIAL), ('sampled_DD_before_haircut', maxdd), ('sampled_DD_including_terminal_haircut', max(maxdd, 1 - prevNAV / peak)), ('buy_fee_BTC', basefees), ('sell_fee_USDT', quotefees)]:
                eq(summary[k], v, 'summary' + k)
            if not summary['strict_completed_episodes'] == sum((x['remaining'] == 0 for x in lots)):
                raise ValueError('Recorded ledger invariant mismatch')
            settled = btc == 0 or (legitimate_exit_residual and 0 < btc < STEP)
            if settled and summary['pending_exit'] is not None:
                raise ValueError('Settled terminal keeps pending exit')
            if not summary['terminal_economic_flat'] is settled:
                raise ValueError('Recorded ledger invariant mismatch')
            if not summary['exact_inventory_zero'] is (btc == 0):
                raise ValueError('Recorded ledger invariant mismatch')
            if not summary['terminal_strict_unsettled'] is (btc != 0):
                raise ValueError('Recorded ledger invariant mismatch')
            if not summary['execution_capacity_unverified'] is bool(expost):
                raise ValueError('Recorded ledger invariant mismatch')
            if not summary['common_valid'] is (settled and max(maxdd, 1 - prevNAV / peak) <= D('.4') and (not expost)):
                raise ValueError('Recorded ledger invariant mismatch')
            eq(summary['remaining_mark_value'], btc * openprice, 'remaining mark')
            eq(summary['mark_NAV'], cash + btc * openprice, 'terminal mark NAV')
            eq(summary['terminal_evaluation_NAV'], prevNAV, 'terminal evaluation NAV')
            if btc < STEP:
                eq(summary['dust_fully_haircut_cash_terminal'], cash, 'terminal dust valuation')
            elif summary['dust_fully_haircut_cash_terminal'] is not None:
                raise ValueError('Tradable residual haircut')
            if role == 'cash':
                if not (not fills and (not lots) and all((x['cash'] == INITIAL and x['BTC'] == 0 and (x['PnL'] == 0) for x in expected_curve))):
                    raise ValueError('Recorded ledger invariant mismatch')
            review.append(dict(account=key, artifact=pin, intervals=len(expected_curve), fills=len(fills), observations=len(expected_obs), risk_records=len(expected_risks), FIFO_lots=len(lots), recorded_accounting_fields_checked=True, strategy_intent_replayed=False))
    statistics = readpin(statistics_ref)
    _identity(statistics, nature, expected_registration_sha256, input_digest, provenance_digest)
    statistics_review = _statistics(accounts, statistics)
    for path, expected in seen.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Artifact changed during verification')
    return dict(artifact_type='spot_retained_ledger_independent_review_v1', at=datetime.now(timezone.utc).isoformat(), source_nature=nature, registration_sha256=expected_registration_sha256, normalized_input_sha256=input_digest, provenance_method_matches_frozen=provenance_method == METHOD_SHA, artificial_method_document_substitution_disclosed=nature == 'artificial_protocol_fixture' and provenance_method != METHOD_SHA, provenance_sha256=provenance_digest, accounting_passed=True, accounts=len(review), intervals=sum((x['intervals'] for x in review)), observations=sum((x['observations'] for x in review)), statistics=statistics_review, model_replays=0, signal_recomputations=0, raw_market_sources_opened=0, research_count_delta=0, real_forward_added=0, qualified=False, details=review)
