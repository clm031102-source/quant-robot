"""Read-only marked effects of correction-linked entries, never a return series."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .offline_admission import _marks
from .offline_intent_contract import instant
from .offline_journal import OfflineOrderJournal
from .offline_order_state import apply_event, money_context


_DIVIDEND_CASH = {'DIVIDEND_CASH_CREDIT', 'DIVIDEND_CASH_INSTALLMENT', 'DIVIDEND_CASH_REFUND'}
_REVISION = {'DIVIDEND_ENTITLEMENT_REVISION', 'CONVERSION_FILL_RESOLUTION'}


def _linked_entries(events):
    fills, dividend_ids = {}, {}
    for row in events:
        event = row['event']; data = event['data']
        if event['kind'] != 'DIVIDEND_ENTITLEMENT_REVISION':
            continue
        reference = dict(sequence=row['sequence'], event_hash=row['event_hash'], facts_fingerprint=data['facts_fingerprint'])
        dividend_ids.setdefault(data['event_id'], []).append(reference)
        facts = data['facts']; records = {r['evidence_id']: r for r in facts['execution_supplement']['records']}
        for decision in facts['receipt_decisions']:
            fills.setdefault(records[decision['evidence_id']]['receipt']['sequence'], []).append(reference)
    return fills, dividend_ids


def _selected_actions(state, event, sequence, fills, dividend_ids):
    kind, data = event['kind'], event['data']
    if kind in _REVISION:
        return [(data['event_id'], data['symbol'], kind == 'DIVIDEND_ENTITLEMENT_REVISION')]
    if kind == 'FILL' and sequence in fills:
        return [(None, state['orders'][data['order_id']]['symbol'], False)]
    if kind in _DIVIDEND_CASH and data['event_id'] in dividend_ids:
        rule = next(r for r in state['dividend_policy']['events'] if r['event_id'] == data['event_id'])
        return [(data['event_id'], rule['symbol'], True)]
    if kind == 'DIVIDEND_ACCRUAL':
        return [(key, state['dividends']['entitlements'][key]['symbol'], True) for key in data['event_ids']
            if key in dividend_ids and key in state['dividends']['revisions']]
    return []


def _values(state, code, action, is_dividend, order_ids):
    dividend = state['dividends']
    return dict(cash=state['cash'], shares=state['positions'].get(code, 0),
        receivable=Decimal(dividend['receivables'].get(action, '0')) if is_dividend else Decimal(0),
        payable=Decimal(dividend['payables'].get(action, '0')) if is_dividend else Decimal(0),
        commission=sum((state['orders'][key]['commission'] for key in order_ids), Decimal(0)))


@money_context
def _attribution_from_evidence(view, *, max_movements=10_000):
    if type(max_movements) is not int or not 0 < max_movements <= 10_000:
        raise ValueError('invalid attribution movement limit')
    events = view['events']; fills, dividend_ids = _linked_entries(events)
    desired = {r['event']['data']['symbol'] for r in events if r['event']['kind'] in _REVISION}
    desired |= {view['snapshot']['orders'][r['event']['data']['order_id']]['symbol'] for r in events if r['sequence'] in fills}
    state = {'sequence': 0, 'journal_hash': '0' * 64}; movements = []; references = {}; reference_count = 0; support_count = 0
    for source in events:
        event = source['event']; kind, data = event['kind'], event['data']; sequence = source['sequence']
        actions = _selected_actions(state, event, sequence, fills, dividend_ids) if kind != 'GENESIS' else []
        if len(movements) + len(actions) > max_movements:
            raise ValueError('attribution exceeds movement limit; no partial result returned')
        order_ids = [data['order_id']] if kind == 'FILL' else list(data['order_changes']) if kind == 'CONVERSION_FILL_RESOLUTION' else []
        before = [_values(state, code, action, div, order_ids) for action, code, div in actions]
        old_theoretical = None
        if kind == 'CONVERSION_FILL_RESOLUTION':
            old = state['conversions']['revisions'].get(data['event_id'], state['conversions']['applied'][data['event_id']])
            old_theoretical = Decimal(old['unrounded_quantity'])
        apply_event(state, event); state.update(sequence=sequence, journal_hash=source['event_hash'])
        for (action, code, div), prior in zip(actions, before):
            after = _values(state, code, action, div, order_ids)
            delta = {key: after[key] - prior[key] for key in after}; unrounded = Decimal(delta['shares'])
            if old_theoretical is not None: unrounded = Decimal(data['unrounded_quantity']) - old_theoretical
            baseline = Decimal(state['dividends']['entitlements'][action]['net_amount']) if kind == 'DIVIDEND_ACCRUAL' else Decimal(0)
            support = fills[sequence] if kind == 'FILL' else dividend_ids.get(action, [])
            if kind == 'CONVERSION_FILL_RESOLUTION':
                support = [dict(sequence=sequence, event_hash=source['event_hash'], facts_fingerprint=data['facts_fingerprint'])]
            receipt_refs = [dict(fill_id=key, sequence=value['sequence'], event_hash=value['event_hash'])
                for key, value in data.get('accounted_fills', {}).items()]
            support_count += len(support) + len(receipt_refs)
            if support_count > 25_000:
                raise ValueError('attribution exceeds correction support relation limit')
            movements.append(dict(sequence=sequence, event_hash=source['event_hash'], journal_recorded_at=source['journal_recorded_at'],
                kind=kind, event_id=action, symbol=code, price_basis_id=state['price_basis'].get(code),
                cash_delta=str(delta['cash']), receivable_delta=str(delta['receivable']), payable_delta=str(delta['payable']),
                share_delta=delta['shares'], commission_delta=str(delta['commission']), unrounded_share_delta=str(unrounded),
                rounding_share_delta=str(Decimal(delta['shares'])-unrounded), baseline_accrual=str(baseline),
                correction_scope='revised_component_of_accrual' if kind == 'DIVIDEND_ACCRUAL' else 'listed_recorded_entry',
                decision_at=data.get('decision_at'), original_fill_id=data.get('fill_id'),
                supporting_revision_events=support, resolved_original_receipts=receipt_refs,
                facts_fingerprint=data.get('facts_fingerprint'), source_authenticated=False))
        if kind in {'RISK_SESSION', 'PORTFOLIO_VALUATION'}:
            quote_context = data if kind == 'RISK_SESSION' else data['context']
            # Independently validate a supplied quote even after full liquidation.
            # Such a quote need not have been required for the recorded portfolio.
            for code in sorted(desired & set(quote_context['quotes'])):
                try:
                    mark = _marks(state['admission_policy'], quote_context, instant(data['decision_at']), {code}, state=state)[code]
                except ValueError:
                    continue
                reference_count += 1
                if reference_count > 25_000:
                    raise ValueError('attribution exceeds reference relation limit')
                key = (code, state['price_basis'].get(code))
                references.setdefault(key, []).append(dict(sequence=sequence, event_hash=source['event_hash'], kind=kind,
                    decision_at=data['decision_at'], mark=str(mark), retrospective=True,
                    quote_source_ref=quote_context['quotes'][code]['source_ref']))
    groups = {}
    for row in movements: groups.setdefault((row['symbol'], row['price_basis_id']), []).append(row)
    group_rows, gaps = [], []
    for (code, basis), rows in groups.items():
        last = max(row['sequence'] for row in rows)
        reference = next((r for r in references.get((code, basis), []) if r['sequence'] > last), None)
        requires_reference = any(Decimal(r['unrounded_share_delta']) or Decimal(r['rounding_share_delta']) for r in rows)
        if requires_reference and reference is None:
            gaps.append(dict(symbol=code, price_basis_id=basis, reason='matching_recorded_valuation_after_listed_movements_unavailable'))
        for row in rows:
            principal = Decimal(row['cash_delta']) + Decimal(row['commission_delta'])
            rights = Decimal(row['receivable_delta']) - Decimal(row['payable_delta']) - Decimal(row['baseline_accrual'])
            fee = -Decimal(row['commission_delta']); shares = row['share_delta']; theoretical = Decimal(row['unrounded_share_delta']); rounding = Decimal(row['rounding_share_delta'])
            mark = Decimal(reference['mark']) if reference is not None else None
            principal_effect = principal + rights + theoretical * mark if mark is not None else (principal + rights if theoretical == 0 else None)
            rounding_effect = rounding * mark if mark is not None else (Decimal(0) if rounding == 0 else None)
            effect = Decimal(row['cash_delta']) + rights + shares * mark if mark is not None else (Decimal(row['cash_delta']) + rights if shares == 0 else None)
            if principal_effect is not None and rounding_effect is not None and effect != principal_effect + rounding_effect + fee:
                raise ValueError('correction attribution decomposition does not reconcile')
            row.update(reference=reference, principal_and_rights_effect=None if principal_effect is None else str(principal_effect),
                rounding_effect=None if rounding_effect is None else str(rounding_effect), fee_effect=str(fee),
                recognized_correction_effect=None if effect is None else str(effect),
                decomposition_complete=principal_effect is not None and rounding_effect is not None)
        complete = all(r['recognized_correction_effect'] is not None for r in rows)
        total = sum((Decimal(r['recognized_correction_effect']) for r in rows), Decimal(0)) if complete else None
        group_rows.append(dict(symbol=code, price_basis_id=basis, reference=reference, movement_sequences=[r['sequence'] for r in rows],
            listed_movement_effect_at_reference=None if total is None else str(total),
            decomposition_complete=all(r['decomposition_complete'] for r in rows)))
    return dict(schema_version=1, mode='offline_fixture_only', status='reference_gaps' if gaps else ('listed_movements_reconciled' if movements else 'no_recorded_corrections'),
        generated_at=datetime.now(timezone.utc).isoformat(), journal=dict(sequence=view['snapshot']['sequence'], hash=view['snapshot']['journal_hash'],
            genesis_hash=events[0]['event_hash'], view='single_verified_read_transaction'), movements=movements, groups=group_rows, reference_gaps=gaps,
        source_event_count=view['source_event_count'], source_payload_bytes=view['source_payload_bytes'],
        excluded_unlinked_fill_count=sum(r['event']['kind']=='FILL' and r['sequence'] not in fills for r in events),
        selection_scope='accepted revisions, linked late fills, settlements of revised dividends, revised component of subsequent accrual',
        reference_policy='first_matching_recorded_valid_valuation_after_all_listed_movements_in_each_symbol_and_basis_group',
        restated_performance_complete=False, return_series_derived=False, source_authenticated=False, executable=False, clears_faults=False,
        qualifies_for_strategy_promotion=False, counts_as_forward_paper_days=0,
        limitations=['listed-entry accounting effects at retrospective reference quotes, not strategy returns or a market-price path',
            'unlinked ordinary trading and original non-revised accrual are excluded',
            'never sum groups with different price bases or reference instants as a portfolio return',
            'no price interpolation, implied conversion price, execution-time authentication or historical signal restatement',
            'monetary effect can be known while its principal and rounding decomposition lacks a reference'])


def build_correction_attribution(path, *, max_events=10_000, max_payload_bytes=16_000_000, max_movements=10_000):
    view = OfflineOrderJournal.inspect_evidence(path, max_events=max_events, max_payload_bytes=max_payload_bytes)
    result = _attribution_from_evidence(view, max_movements=max_movements)
    result['journal']['path'] = str(Path(path).resolve())
    return result
