"""Pure passive-drift sibling of the frozen low-unit allocation ledger.

Only the ordinary invested month-end decision changes. Execution, capacity,
cash, company actions, risk recovery and terminal liquidation are inherited.
No source IO, release authorization or live account access belongs here.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import localcontext

from quant_robot.research import us_low_unit_allocation as core


STRATEGY_ID = "us_low_unit_passive_drift_v1"
HOLDING_POLICY = "no_regular_rebalance_while_any_inventory"
ENTRY_ALLOCATION_POLICY = "fixed_quarters"
ROLES = ("primary", "stress")


class _DriftAccount(core._Account):
    def decision(self, index):
        signal = self.p["signals"][index]
        # Preserve the original risk/terminal skip before considering drift.
        if (not self.paused and self.risk_due is None
                and signal["ordinary_execution_possible"]
                and any(self.q.values())):
            core._require(self.pending is None, "overlapping_monthly_plan")
            self.events.append(dict(
                decision_index=index, date=self.p["dates"][index],
                signal=deepcopy(signal), policy=self.policy,
                status="skipped_passive_drift_while_invested",
                decision_NAV=self.previous,
                pre_decision_balances=self.balances(),
                targets={}, sell_orders=[], buy_orders=[]))
            return
        super().decision(index)


def _run(fixture, role, *, historical, method_sha256=None,
         registration_sha256=None, numeric_marker_sha256=None):
    core._require(type(role) is str and role in ROLES, "fixed_passive_drift_role")
    inherited_role = "new_" + role
    with localcontext(core.CONTEXT) as ctx:
        ctx.clear_flags()
        initial_context = core.context_record(ctx)
        fixture_sha = core.digest(fixture)
        prepared = core.prepare(fixture, inherited_role, historical=historical)
        minimum, slip = ("2.50", 30) if role == "stress" else ("1.00", 10)
        result = _DriftAccount(prepared, ENTRY_ALLOCATION_POLICY, minimum, slip).run()
        core._require(core.digest(fixture) == fixture_sha
                      and core.digest(prepared.normalized) == prepared.normalized_sha256,
                      "immutable_input")
        result["summary"]["skipped_invested_month_ends"] = sum(
            event["status"] == "skipped_passive_drift_while_invested"
            for event in result["monthly_events"])
        result.update(
            schema="us_passive_drift_allocation_account_v1", role=inherited_role, scenario_role=role,
            inherited_cost_role=inherited_role, strategy_id=STRATEGY_ID,
            holding_policy=HOLDING_POLICY,
            entry_allocation_policy=ENTRY_ALLOCATION_POLICY,
            assets=list(prepared.assets),
            evidence_kind="known_history_conditional" if historical else "artificial",
            historical_returns_computed=historical, test_injected_values=not historical,
            qualified=False, real_forward=0, fixture_sha256=fixture_sha,
            method_sha256=method_sha256, registration_sha256=registration_sha256,
            numeric_marker_sha256=numeric_marker_sha256,
            capacity_basis="previous20completed_lower_two_convention_nominal_mean_one_percent",
            runtime_context=dict(initial=initial_context, final=core.context_record(ctx)))
        return core.serial(result)


def run_artificial(fixture, role="primary"):
    """Invented prices in years 2000..2004 only; never reads saved market data."""
    return _run(fixture, role, historical=False)


def run_known_history(fixture, role, *, method_sha256, registration_sha256, numeric_marker_sha256):
    """Pure entry for the externally admitted, already decoded saved fixture.

    Hash arguments document the controller's prior authorization and durable
    marker; this function itself neither grants nor authenticates a release.
    """
    core._require(all(core._hex(x) for x in
                      (method_sha256, registration_sha256, numeric_marker_sha256)),
                  "external_numeric_claim_hashes")
    return _run(fixture, role, historical=True, method_sha256=method_sha256,
                registration_sha256=registration_sha256, numeric_marker_sha256=numeric_marker_sha256)
