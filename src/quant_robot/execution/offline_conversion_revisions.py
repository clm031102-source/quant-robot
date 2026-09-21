"""Single-conversion accounting under complete, explicitly assumed fixture facts."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time
from decimal import Decimal, ROUND_CEILING
import json
import re

from .offline_conversions import _clock, _convert
from .offline_execution_evidence import validate_execution_supplement, _time
from .offline_history import mutable_order
from .offline_intent_contract import SHANGHAI, exact, fingerprint, version
from .offline_order_state import ACTIVE, TERMINAL, CONVERSION_UNCERTAIN, AdmissionRejected, commission, identity, money_context, risk_deficit, units


def normalize_facts(value):
    exact(value, {'schema_version', 'mode', 'revision_id', 'journal', 'event_id', 'policy_fingerprint',
        'original_entitlement_fingerprint', 'original_conversion_fingerprint', 'corrected_old_quantity',
        'facts_as_of', 'entitlement_source', 'execution_supplement', 'selected_evidence_ids', 'order_resolutions'}, 'conversion resolution facts')
    version(value)
    if value['mode'] != 'offline_fixture_only':
        raise ValueError('only explicitly assumed offline conversion facts are supported')
    identity(value['revision_id']); identity(value['event_id']); units(value['corrected_old_quantity'])
    exact(value['journal'], {'sequence', 'hash', 'genesis_hash'}, 'conversion journal')
    units(value['journal']['sequence'], positive=True)
    exact(value['execution_supplement'], {'schema_version', 'mode', 'journal', 'records'}, 'execution supplement')
    exact(value['entitlement_source'], {'mode', 'source_ref', 'sha256'}, 'entitlement source')
    if value['entitlement_source']['mode'] != 'assumed_offline_fixture':
        raise ValueError('conversion source must be an assumed offline fixture')
    identity(value['entitlement_source']['source_ref']); _time(value['facts_as_of'], 'facts_as_of')
    for digest in (value['policy_fingerprint'], value['original_entitlement_fingerprint'], value['original_conversion_fingerprint'], value['entitlement_source']['sha256']):
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('invalid conversion evidence fingerprint')
    if not isinstance(value['selected_evidence_ids'], list) or len(value['selected_evidence_ids']) > 500:
        raise ValueError('invalid selected conversion evidence list')
    for key in value['selected_evidence_ids']: identity(key)
    if not isinstance(value['order_resolutions'], list) or len(value['order_resolutions']) > 500:
        raise ValueError('invalid terminal order resolution list')
    for row in value['order_resolutions']:
        exact(row, {'order_id', 'final_status', 'source_ref', 'source_sha256'}, 'terminal order resolution')
        identity(row['order_id']); identity(row['source_ref'])
        if row['final_status'] not in ('CANCELLED', 'FILLED') or not isinstance(row['source_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['source_sha256']):
            raise ValueError('terminal order status requires explicit synthetic source evidence')
    try:
        payload = json.dumps(value, allow_nan=False).encode('utf-8')
    except (TypeError, RecursionError) as exc:
        raise ValueError('unsupported conversion facts structure') from exc
    if len(payload) > 1_250_000:
        raise ValueError('conversion facts exceed byte limit')
    return deepcopy(value)


def _check_history(state, packet, view, rule):
    code, target = rule['symbol'], rule['event_id']
    if any(o['symbol'] == code and o['status'] in ACTIVE for o in state['orders'].values()):
        raise AdmissionRejected('active orders prevent conversion resolution')
    applied_ids = [key for key, row in state['conversions']['applied'].items() if row['symbol'] == code]
    if applied_ids != [target]:
        raise AdmissionRejected('multiple applied conversions require a dependency correction protocol')
    for other in state['conversion_policy']['events']:
        if (other['symbol'] == code and other['event_id'] != target and other['event_id'] in state['conversions']['entitlements']
                and other['record_date'] >= rule['record_date']):
            raise AdmissionRejected('later captured conversion dependency requires review')
    captures = [r for r in view['events'] if r['event']['kind'] == 'CONVERSION_ENTITLEMENTS'
        and target in r['event']['data']['entitlements']]
    applications = [r for r in view['events'] if r['event']['kind'] == 'SHARE_CONVERSIONS'
        and target in r['event']['data']['conversions']]
    if len(captures) != 1 or len(applications) != 1:
        raise AdmissionRejected('original conversion history is ambiguous')
    if any(r['sequence'] > captures[0]['sequence'] and r['event']['kind'] == 'FILL'
            and state['orders'][r['event']['data']['order_id']]['symbol'] == code for r in view['events']):
        raise AdmissionRejected('subsequent same-symbol fills require a dependency correction protocol')
    candidates = [r for r in view['events'] if r['event']['kind'] == 'CONVERSION_UNAPPLIED_FILL'
        and state['orders'][r['event']['data']['order_id']]['symbol'] == code]
    if not candidates or any(r['sequence'] <= applications[0]['sequence'] for r in candidates):
        raise AdmissionRejected('no complete post-conversion pending receipt history')
    for receipt in state['receipts'].values():
        if 'facts' not in receipt or receipt.get('event_id') != target or 'original_conversion_fingerprint' not in receipt['facts']:
            continue
        previous = receipt['facts']
        if previous['entitlement_source']['sha256'] == packet['entitlement_source']['sha256'] and previous['corrected_old_quantity'] != packet['corrected_old_quantity']:
            raise AdmissionRejected('same entitlement source cannot assert different holder quantities')
    return candidates


def _evidence(state, packet, view, rule, candidates):
    result = validate_execution_supplement(packet['execution_supplement'], view)
    records = {r['assertion']['evidence_id']: r['assertion'] for r in result['records']}
    prior = state['conversions']['revisions'].get(rule['event_id'])
    if prior:
        old = state['receipts']['conversion_revision:' + prior['revision_id']]['facts']['execution_supplement']['records']
        if any(records.get(r['evidence_id']) != r for r in old):
            raise AdmissionRejected('previous conversion evidence must be retained unchanged')
    parents = {r['source']['previous_evidence_id'] for r in records.values() if r['source']['previous_evidence_id'] is not None}
    leaves = set(records) - parents; selected = packet['selected_evidence_ids']
    if len(selected) != len(leaves) or set(selected) != leaves:
        raise AdmissionRejected('every terminal evidence assertion needs a unique selection')
    required = {r['sequence']: r for r in candidates}
    if any(r['receipt']['sequence'] not in required for r in records.values()):
        raise AdmissionRejected('unrelated conversion receipt evidence')
    cutoff = datetime.combine(datetime.fromisoformat(rule['record_date']).date(), time.fromisoformat(state['conversion_policy']['record_cutoff']), SHANGHAI)
    as_of = _time(packet['facts_as_of'], 'facts_as_of'); seen = set(); pending = []; evidence = {}
    quantity = state['conversions']['entitlements'][rule['event_id']]['quantity']
    for key in selected:
        assertion = records[key]; sequence = assertion['receipt']['sequence']; execution = assertion['execution']
        if sequence in seen:
            raise AdmissionRejected('multiple terminal sources for one conversion receipt remain ambiguous')
        seen.add(sequence); row = required[sequence]; data = row['event']['data']; order = state['orders'][data['order_id']]
        if (assertion['operation'] == 'cancel' or execution['executed_at'] is None or execution['quantity'] != data['quantity']
                or execution['price'] is None or Decimal(execution['price']) != Decimal(data['price'])
                or execution['quantity_basis'] != 'pre_action_shares' or execution['basis_event_id'] != rule['event_id']
                or execution['price_basis'] != 'raw_execution' or assertion['source']['claimed_artifact_sha256'] is None):
            raise AdmissionRejected('unresolved conversion execution, price or old-unit evidence')
        executed = _time(execution['executed_at'], 'executed_at')
        if executed > cutoff or executed < _time(order['admission']['decision_at'], 'order decision') or _time(assertion['observed_at'], 'observed_at') > as_of:
            raise AdmissionRejected('execution is outside the supported original-order record interval')
        for dividend in (state.get('dividend_policy') or {}).get('events', []):
            div_cutoff = datetime.combine(datetime.fromisoformat(dividend['record_date']).date(), time.fromisoformat(state['dividend_policy']['record_cutoff']), SHANGHAI)
            if dividend['symbol'] == rule['symbol'] and dividend['event_id'] in state['dividends']['entitlements'] and executed <= div_cutoff:
                raise AdmissionRejected('captured dividend depends on this old execution')
        quantity += (1 if order['side'] == 'BUY' else -1) * data['quantity']
        evidence[data['fill_id']] = dict(event_id=rule['event_id'], revision_id=packet['revision_id'], evidence_id=key,
            evidence_fingerprint=fingerprint(assertion), sequence=sequence, event_hash=row['event_hash'])
        accounted = state['conversions']['accounted_fills'].get(data['fill_id'])
        if accounted:
            if any(accounted[field] != evidence[data['fill_id']][field] for field in ('event_id', 'evidence_id', 'evidence_fingerprint', 'sequence', 'event_hash')):
                raise AdmissionRejected('already accounted execution facts cannot be revised by this route')
        else:
            pending.append(data)
    if seen != set(required) or quantity < 0 or quantity != packet['corrected_old_quantity'] or not pending:
        raise AdmissionRejected('incomplete receipts, unexplained quantity or no new pending fills')
    return quantity, pending, evidence, result['supplement_fingerprint']


@money_context
def resolution_event(state, packet, now, evidence_supplier):
    receipt_key = 'conversion_revision:' + packet['revision_id']
    if receipt_key in state['receipts']:
        if state['receipts'][receipt_key]['facts'] != packet:
            raise AdmissionRejected('conflicting conversion revision identity')
        return None
    policy, now, date = _clock(state, now); target = packet['event_id']; original = state['conversions']['entitlements'].get(target)
    applied = state['conversions']['applied'].get(target); rule = next((r for r in policy['events'] if r['event_id'] == target), None)
    as_of = _time(packet['facts_as_of'], 'facts_as_of')
    if as_of > now or (state['corporate_last_transition_at'] and as_of < _time(state['corporate_last_transition_at'], 'corporate transition')):
        raise AdmissionRejected('conversion facts are future or predate the corporate history')
    if original is None or applied is None or rule is None:
        raise AdmissionRejected('conversion must have original captured and applied records')
    if (packet['policy_fingerprint'] != state['conversion_policy_fingerprint'] or packet['original_entitlement_fingerprint'] != fingerprint(original)
            or packet['original_conversion_fingerprint'] != fingerprint(applied)):
        raise AdmissionRejected('original conversion fingerprint mismatch')
    view = evidence_supplier(); binding = dict(genesis_hash=view['events'][0]['event_hash'], sequence=state['sequence'], hash=state['journal_hash'])
    if packet['journal'] != binding or packet['execution_supplement']['journal'] != binding:
        raise AdmissionRejected('conversion facts have a stale journal anchor')
    candidates = _check_history(state, packet, view, rule)
    quantity, pending, evidence, supplement_hash = _evidence(state, packet, view, rule, candidates)
    prior = state['conversions']['revisions'].get(target, applied)
    if state['positions'].get(rule['symbol'], 0) != prior['new_quantity']:
        raise AdmissionRejected('current holdings differ from the prior effective conversion')
    converted, theoretical, rounding = _convert(quantity, rule)
    changes = {}; cash_delta = Decimal(0); directional = {'BUY': 0, 'SELL': 0}; faults = set()
    for data in pending:
        order = state['orders'][data['order_id']]; change = changes.setdefault(data['order_id'], dict(quantity=0, notional='0'))
        change['quantity'] += data['quantity']; change['notional'] = str(Decimal(change['notional']) + data['quantity'] * Decimal(data['price']))
        directional[order['side']] += data['quantity']
        if order['status'] in TERMINAL: faults.add('fill_after_terminal_status')
        if (1 if order['side'] == 'BUY' else -1) * (Decimal(data['price']) - order['limit_price']) > 0: faults.add('fill_outside_limit')
    for key, change in changes.items():
        order = state['orders'][key]; total_quantity = order['filled_quantity'] + change['quantity']
        if total_quantity > order['quantity']:
            raise AdmissionRejected('conversion receipt exceeds original order capacity')
        fee = commission(state, order['filled_notional'] + Decimal(change['notional']))
        cash_delta -= (1 if order['side'] == 'BUY' else -1) * Decimal(change['notional']) + fee - order['commission']
        change.update(commission=str(fee), status='FILLED' if total_quantity == order['quantity'] else 'CANCELLED')
    resolutions = {r['order_id']: r for r in packet['order_resolutions']}
    if len(resolutions) != len(packet['order_resolutions']) or set(resolutions) != set(changes):
        raise AdmissionRejected('complete unique terminal order evidence required for pending receipts')
    for key, change in changes.items():
        if resolutions[key]['final_status'] != change['status']:
            raise AdmissionRejected('terminal order evidence disagrees with cumulative execution quantity')
        for receipt in state['receipts'].values():
            facts = receipt.get('facts', {})
            for old in facts.get('order_resolutions', []):
                if old['order_id'] == key and old['source_sha256'] == resolutions[key]['source_sha256'] and old['final_status'] != resolutions[key]['final_status']:
                    raise AdmissionRejected('same terminal-order source cannot assert a different status')
    shares = {side: int((Decimal(qty) * Decimal(rule['share_ratio'])).to_integral_value(rounding=ROUND_CEILING)) for side, qty in directional.items() if qty}
    current = state.get('risk_session'); budget_session = date if current and current['session_date'] == date and date >= rule['tradable_date'] else None
    all_accounted = set(state['conversions']['accounted_fills']) | set(evidence)
    clear = not (set(state['conversions']['unapplied_fills']) - all_accounted)
    clear = clear and not any(r['event']['kind'] == 'FAULT' and r['event']['data'].get('reason') == CONVERSION_UNCERTAIN for r in view['events'])
    return dict(kind='CONVERSION_FILL_RESOLUTION', receipt_key=receipt_key, data=dict(event_id=target, revision_id=packet['revision_id'],
        symbol=rule['symbol'], old_quantity=quantity, new_quantity=converted, unrounded_quantity=theoretical, rounding_share_adjustment=rounding,
        share_delta=converted-prior['new_quantity'], cash_delta=str(cash_delta), order_changes=changes,
        accounted_fills={d['fill_id']: evidence[d['fill_id']] for d in pending}, participation=dict(event_id=target, symbol=rule['symbol'], shares=shares,
            consumed_session=budget_session, not_before_session=max(date, rule['tradable_date'])), new_faults=sorted(faults),
        clears_conversion_fault=clear, decision_at=now.isoformat(), facts=packet, facts_fingerprint=fingerprint(packet),
        supplement_fingerprint=supplement_hash, source_authenticated=False, executable=False))


def apply_resolution(state, data):
    conversions = state['conversions']; code = data['symbol']
    state['cash'] += Decimal(data['cash_delta']); state['positions'][code] = data['new_quantity']
    state['sellable_positions'][code] = min(state['sellable_positions'].get(code, 0), data['new_quantity'])
    if code in conversions['locks']:
        conversions['locks'][code]['quantity'] = data['new_quantity']; state['sellable_positions'][code] = 0
    conversions['revisions'][data['event_id']] = {key: data[key] for key in ('revision_id', 'symbol', 'old_quantity', 'new_quantity',
        'unrounded_quantity', 'rounding_share_adjustment', 'share_delta', 'cash_delta', 'facts_fingerprint', 'decision_at')}
    conversions['accounted_fills'].update(data['accounted_fills']); conversions['last_transition_at'] = data['decision_at']
    participation = deepcopy(data['participation']); conversions['participation'][data['revision_id']] = participation
    if participation['consumed_session'] is not None:
        current = state['risk_session']['carryover_fill_shares'].setdefault(code, {})
        for side, qty in participation['shares'].items(): current[side] = current.get(side, 0) + qty
    for key, change in data['order_changes'].items():
        order = mutable_order(state, key); order['filled_quantity'] += change['quantity']; order['filled_notional'] += Decimal(change['notional'])
        order['commission'] = Decimal(change['commission']); order['status'] = change['status']
    state['faults'].update(data['new_faults'])
    if data['clears_conversion_fault']: state['faults'].discard(CONVERSION_UNCERTAIN)
    if risk_deficit(state): state['faults'].add('account_or_reservation_deficit')


def opening_participation(state, date):
    shares = {}; revisions = []
    for key, row in state['conversions']['participation'].items():
        if row['consumed_session'] is None and date >= row['not_before_session']:
            revisions.append(key); current = shares.setdefault(row['symbol'], {})
            for side, qty in row['shares'].items(): current[side] = current.get(side, 0) + qty
    return shares, revisions
