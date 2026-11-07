"""Selected fixed-allocation validation; unchanged USD ledger, new input identity.

No source reader, broker access, release or registration is implemented here.
The private historical controller owns permission before numeric normalization.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal as D, localcontext
import hashlib
from pathlib import Path

from quant_robot.research import us_monthly_rotation as kernel

METHOD_SHA = "c46de5d2ea527be77aea806cb6ab42c331b6e4b29070f4e89f840845ab7f74a1"
KERNEL_SHA = "3cd7fef3058d97a83e7a917a333a6acd2a9309743b3ac716bda5d885b2f6f202"
ASSETS = kernel.ASSETS
ROLES = ("primary", "stress", "cash")
COSTS = {"primary": ("fixed_quarters", "1.00", 10),
         "stress": ("fixed_quarters", "2.50", 30), "cash": ("cash", "0.35", 0)}
CONTEXT = kernel.CONTEXT.copy()
serial, digest, canonical = kernel.serial, kernel.digest, kernel.canonical
Prepared = kernel.Prepared
_require, _number, _hash = kernel._require, kernel._number, kernel._hash


@dataclass(frozen=True)
class _ExecutionContext:
    evidence_kind: str
    method_sha256: str
    fixture_sha256: str
    provenance_sha256: str
    registration_sha256: str | None = None
    test_values: bool = False

    def __post_init__(self):
        _require(self.evidence_kind in ("artificial", "known_history_conditional")
                 and self.method_sha256 == METHOD_SHA and type(self.test_values) is bool,
                 "fixed_allocation_context")
        _require(_hash(self.fixture_sha256) and _hash(self.provenance_sha256), "context_hash_required")
        if self.evidence_kind == "known_history_conditional":
            _require(_hash(self.registration_sha256), "registration_hash_required")
        else:
            _require(self.registration_sha256 is None and not self.test_values, "artificial_context_identity")

    @property
    def historical(self):
        return self.evidence_kind == "known_history_conditional" and not self.test_values

    @property
    def output_kind(self):
        return "artificial_values_true_calendar" if self.test_values else self.evidence_kind


def _kernel_pin():
    path = Path(kernel.__file__).resolve()
    _require(hashlib.sha256(path.read_bytes()).hexdigest() == KERNEL_SHA, "unchanged_ledger_required")
    return path


def prepare(fixture, *, context):
    """Validate a bound common-calendar packet; never read adjusted close."""
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags()
        _kernel_pin()
        _require(type(context) is _ExecutionContext and digest(fixture) == context.fixture_sha256
                 and digest(fixture["provenance"]) == context.provenance_sha256, "bound_fixture_context_required")
        _require(fixture.get("schema") == "us_fixed_allocation_2025_fixture_v1"
                 and fixture.get("method_sha256") == METHOD_SHA
                 and fixture.get("evidence_kind") == context.output_kind
                 and fixture.get("assets") == list(ASSETS), "fixed_fixture_identity")
        provenance = fixture["provenance"]
        _require(provenance.get("split_policy_verified") is True
                 and provenance.get("capital_gains_present") is False
                 and provenance.get("holding_window_splits_absent") is True, "fixed_action_identity_required")
        _require(provenance.get("constructed_from_market_data") is context.historical, "source_nature_required")
        rows = fixture["days"]
        dates = [r["date"] for r in rows]
        _require(len(dates) >= 25 and dates == sorted(set(dates)), "ordered_complete_common_calendar")
        parsed = [date.fromisoformat(d) for d in dates]
        _require(all(d.isoformat() == text for d, text in zip(parsed, dates)), "canonical_dates")
        first = dates.index(fixture["first_decision_date"])
        terminal = dates.index(fixture["terminal_date"])
        _require(terminal == len(rows)-1 and first >= 19 and first+4 < terminal,
                 "twenty_completed_warmup_and_terminal")
        _require(all(d[:7] == dates[first][:7] for d in dates[:first+1]), "one_month_warmup_only")
        if context.evidence_kind == "artificial":
            _require(all(2000 <= d.year <= 2004 for d in parsed), "public_artificial_years_only")
        else:
            _require(dates[0] >= "2024-12-01" and dates[first] == "2024-12-31"
                     and dates[terminal] == "2025-12-31"
                     and all(d[:4] == "2025" for d in dates[first+1:]), "fixed_2025_calendar")
        bars, execution = [], []
        for i, row in enumerate(rows):
            _require(set(row["prices"]) == set(ASSETS), "four_same_session_assets")
            new = {}
            for asset in ASSETS:
                raw = row["prices"][asset]
                new[asset] = dict(open=_number(raw["open"], positive=True), adj_close=None)
                if i == terminal:
                    _require(row.get("terminal_open_only") is True and all(raw.get(k) is None
                             for k in ("high", "low", "close", "adj_close", "volume")), "terminal_open_only")
                    new[asset].update(dict(high=None, low=None, close=None, volume=None))
                else:
                    _require(row.get("terminal_open_only") is not True, "early_terminal_flag")
                    new[asset].update({k: _number(raw[k], positive=k != "volume")
                                      for k in ("high", "low", "close", "volume")})
                    b = new[asset]
                    _require(b["low"] <= min(b["open"], b["close"]) <= max(b["open"], b["close"]) <= b["high"],
                             "OHLC_rectangle")
            flags = row.get("execution", {a: dict(suspended=None, buy_blocked=None, sell_blocked=None) for a in ASSETS})
            _require(set(flags) == set(ASSETS), "execution_assets")
            for f in flags.values():
                _require(set(f) == {"suspended", "buy_blocked", "sell_blocked"}
                         and all(v is None or type(v) is bool for v in f.values()), "explicit_execution_flags")
            bars.append(new); execution.append(copy.deepcopy(flags))
        month_ends = [i for i in range(first, terminal) if dates[i][:7] != dates[i+1][:7]]
        _require(month_ends and month_ends[0] == first, "first_decision_complete_month_end")
        months = [parsed[i].year*12+parsed[i].month for i in month_ends]
        _require(all(b-a == 1 for a, b in zip(months, months[1:])), "consecutive_complete_months")
        if context.evidence_kind == "known_history_conditional":
            _require(len(month_ends) == 12 and dates[month_ends[-1]][:7] == "2025-11", "twelve_fixed_decisions")
        dividends, ids = [], set()
        for item in fixture["dividends"]:
            _require(type(item["id"]) is str and item["id"] and item["id"] not in ids
                     and item["symbol"] in ASSETS, "unique_dividend_identity")
            ids.add(item["id"])
            _require(item["ex_date"] in dates and item["ex_date"] > dates[first], "no_inherited_warmup_dividend")
            dividends.append(dict(id=item["id"], symbol=item["symbol"], ex_index=dates.index(item["ex_date"]),
                amount_per_share=_number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        signals = {i: dict(index=i, date=dates[i], signal_kind="fixed_calendar_weights_no_momentum",
                   intended_gross=D(1), weights={"fixed_quarters": dict.fromkeys(ASSETS, D(".25"))},
                   ordinary_execution_possible=i+4 < terminal) for i in month_ends}
        normalized = dict(dates=dates, bars=bars, execution=execution, dividends=dividends,
                          signals=signals, first=first, terminal=terminal)
        return Prepared(context.fixture_sha256, normalized, digest(normalized))


def run_prepared(prepared, role, *, context):
    """Run exactly one permitted role, preserving the original ledger semantics."""
    _require(type(context) is _ExecutionContext and type(prepared) is Prepared and role in ROLES
             and prepared.fixture_sha256 == context.fixture_sha256
             and digest(prepared.normalized) == prepared.normalized_sha256, "prepared_role_context_binding")
    kernel_path = _kernel_pin()
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags(); initial = kernel.context_record(ctx)
        policy, minimum, slip = COSTS[role]
        result = kernel._Account(prepared, policy, minimum, slip).run()
        _require(digest(prepared.normalized) == prepared.normalized_sha256, "prepared_input_changed_during_run")
        _kernel_pin()
        result.update(schema="us_fixed_allocation_2025_account_v1", role=role, evidence_kind=context.output_kind,
            historical_returns_computed=context.historical, test_injected_values=context.test_values,
            qualified=False, real_forward=0, method_sha256=METHOD_SHA, fixture_sha256=context.fixture_sha256,
            provenance_sha256=context.provenance_sha256, registration_sha256=context.registration_sha256,
            selection="Selected after study26; this is a separate constrained-allocation validation, not blind alpha",
            runtime=dict(module_file=str(Path(__file__).resolve()),
                         module_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         ledger_module_file=str(kernel_path), ledger_sha256=KERNEL_SHA,
                         context_initial=initial, context_final=kernel.context_record(ctx)))
        result["zero_share_target_legs"] = [dict(decision_index=e["decision_index"], date=e["date"], asset=a,
            target_quantity=0) for e in result["monthly_events"] for a, q in e["targets"].items() if q == 0]
        result["zero_share_buy_legs"] = [copy.deepcopy(o) for e in result["monthly_events"]
                                         for o in e["buy_orders"] if o["quantity"] == 0]
        result["unheld_asset_sessions"] = {a: sum(d["after"]["quantities"][a] == 0 for d in result["days"]) for a in ASSETS}
        result["statistics"] = dict(status="not_applicable_single_selected_year", bootstrap_computed=False,
                                     statistical_significance_claimed=False, qualified=False)
        return serial(result)


def run_artificial(fixture, role="primary"):
    _require(fixture.get("evidence_kind") == "artificial", "public_artificial_only")
    context = _ExecutionContext("artificial", METHOD_SHA, digest(fixture), digest(fixture["provenance"]))
    return run_prepared(prepare(fixture, context=context), role, context=context)
