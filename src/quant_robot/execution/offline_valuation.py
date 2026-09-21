"""Order-independent synthetic book valuation, including while trading is paused."""
from __future__ import annotations

from decimal import Decimal

from .offline_admission import _marks
from .offline_intent_contract import SHANGHAI, instant
from .offline_order_state import ACTIVE, VALUATION_UNAVAILABLE, AdmissionRejected, money_context, risk_deficit
from .offline_portfolio_risk import portfolio_totals
from .offline_drawdown import drawdown_evidence


class ValuationRejected(AdmissionRejected):
    def __init__(self, message, *, unavailable):
        super().__init__(message)
        self.valuation_unavailable = unavailable


def _context(state, packet, now):
    policy, session = state.get("admission_policy"), state.get("risk_session")
    if policy is None or session is None:
        raise ValuationRejected("valuation requires an initialized guarded risk session", unavailable=False)
    now = instant(now)
    if (packet["session_date"] != now.astimezone(SHANGHAI).date().isoformat()
            or packet["session_date"] not in policy["session_dates"]
            or packet["session_date"] != session["session_date"]):
        raise ValuationRejected("valuation session date mismatch", unavailable=False)
    if packet["journal_sequence"] != state["sequence"] or packet["journal_hash"] != state["journal_hash"]:
        raise ValuationRejected("valuation context has a stale journal anchor", unavailable=False)
    previous = state["portfolio_valuation"]["last_valid"]
    if now < instant(session["decision_at"]) or (previous and now < instant(previous["decision_at"])):
        raise ValuationRejected("valuation clock moved backward", unavailable=False)
    age = (now - instant(packet["as_of"])).total_seconds()
    if age < 0 or age > policy["max_context_age_seconds"]:
        raise ValuationRejected("stale or future valuation context", unavailable=True)
    if previous and instant(packet["as_of"]) < instant(previous["context"]["as_of"]):
        raise ValuationRejected("valuation context timestamp regressed", unavailable=True)
    return policy, session, now, previous


@money_context
def valuation_event(state, packet, now):
    policy, session, now, previous = _context(state, packet, now)
    required = {key for key, qty in state["positions"].items() if qty}
    required |= {row["symbol"] for row in state["orders"].values() if row["status"] in ACTIVE}
    try:
        marks = _marks(policy, packet, now, required, state=state)
    except AdmissionRejected as exc:
        raise ValuationRejected(str(exc), unavailable=True) from exc
    prior_quotes = previous["context"]["quotes"] if previous else session["quotes"]
    for code in required:
        quote = packet["quotes"][code]
        if code in prior_quotes and instant(quote["timestamp"]) < instant(prior_quotes[code]["timestamp"]):
            raise ValuationRejected("valuation quote timestamp regressed", unavailable=True)
    totals = portfolio_totals(state, marks)
    opening, equity = Decimal(session["opening_equity"]), totals["equity"]
    peak = max(Decimal(session.get("valuation_peak_equity", session["opening_equity"])), equity)
    breaches = []
    guard = drawdown_evidence(state, equity, totals['pending_cost'])
    if guard and guard['stop_latched']:
        breaches.append('cumulative_drawdown')
    if totals["projected_loss"] >= Decimal(policy["max_daily_loss_cny"]):
        breaches.append("daily_loss")
    if totals["gross"] > Decimal(policy["capital_limit_cny"]):
        breaches.append("capital_exposure")
    if any(value > Decimal(policy["max_position_cny"]) for value in totals["exposure"].values()):
        breaches.append("single_position")
    if risk_deficit(state):
        breaches.append("account_or_reservation_deficit")
    account_faults = sorted(state["faults"] - {VALUATION_UNAVAILABLE})
    unknown_orders = sorted(key for key, row in state["orders"].items() if row["status"] == "UNKNOWN")
    from .offline_session_baseline import close_observation, loss_from_reference
    closing = close_observation(state, policy, packet, now, equity)
    return {"kind": "PORTFOLIO_VALUATION", "data": {"context": packet, "decision_at": now.isoformat(),
        **({'session_close_observation': closing} if closing is not None else {}),
        **({'daily_loss_reference': session['daily_loss_reference'], 'book_daily_loss': str(loss_from_reference(session, equity))}
            if 'daily_loss_reference' in session else {}),
        **({'drawdown_guard':guard} if guard is not None else {}),
        "basis": "recorded_synthetic_book_at_supplied_quotes", "book_equity": str(equity),
        "opening_equity": str(opening), "book_pnl_from_open": str(equity - opening),
        "book_loss_from_open": str(opening - equity), "book_equity_peak": str(peak),
        "book_peak_drawdown": str(peak - equity), "pending_cost_bound": str(totals["pending_cost"]),
        "dividend_receivable": str(totals["dividend_receivable"]),
        "dividend_payable": str(totals["dividend_payable"]),
        "dividend_adjustment_since_open": str(totals["dividend_adjustment_since_open"]),
        "conversion_revision_count": len(state["conversions"]["revisions"]),
        "performance_attribution_status": "requires_restatement" if state["dividends"]["revisions"] or state["conversions"]["revisions"] else "recorded_book_only",
        "projected_daily_loss": str(totals["projected_loss"]), "gross_committed_exposure": str(totals["gross"]),
        "committed_position_values": {key: str(value) for key, value in totals["exposure"].items()},
        "marks": {key: str(value) for key, value in marks.items() if key in required},
        "account_faults": account_faults, "unknown_order_ids": unknown_orders,
        "account_state_known": not account_faults and not unknown_orders,
        "breaches": breaches, "risk_stop_required": bool(breaches), "policy_fingerprint": state["admission_policy_fingerprint"],
        "mode": "offline_fixture_only", "executable": False}}
