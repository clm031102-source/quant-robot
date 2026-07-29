from __future__ import annotations

from typing import Any, Mapping


BOUNDARY_KEYS = (
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)
REQUIRED_ORDER_INTENT_FIELDS = (
    "schema_version",
    "client_intent_id",
    "idempotency_key",
    "strategy_id",
    "strategy_version",
    "signal_timestamp",
    "symbol",
    "exchange",
    "side",
    "quantity",
    "order_type",
    "limit_price",
    "time_in_force",
    "max_slippage_bps",
    "expires_at",
)
REQUIRED_BROKER_INPUTS = (
    "broker_name_and_api_documentation",
    "sandbox_or_simulation_endpoint",
    "authentication_and_session_model",
    "account_type_and_supported_cn_etf_exchanges",
    "minimum_commission_and_other_fees",
    "supported_order_types_and_time_in_force",
    "lot_size_price_tick_and_trading_status_endpoint",
    "rate_limits_error_codes_and_idempotency_semantics",
    "trade_fill_position_and_cash_reconciliation_endpoints",
)


def build_cn_etf_execution_interface_contract_readiness(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if config.get("schema_version") != 1:
        blockers.append("schema_version_mismatch")
    if config.get("purpose") != "execution_interface_readiness_without_external_access":
        blockers.append("purpose_mismatch")
    broker = _mapping(config.get("broker"))
    if broker.get("credentials_present") is not False:
        blockers.append("credentials_must_be_absent")
    market = _mapping(config.get("market_contract"))
    if (
        market.get("market") != "CN_ETF"
        or market.get("currency") != "CNY"
        or tuple(market.get("exchanges", ())) != ("SSE", "SZSE")
    ):
        blockers.append("market_contract_mismatch")
    order = _mapping(config.get("order_intent_schema"))
    if tuple(order.get("required_fields", ())) != REQUIRED_ORDER_INTENT_FIELDS:
        blockers.append("order_intent_schema_mismatch")
    if order.get("duplicate_intent_policy") != "reject_same_idempotency_key":
        blockers.append("idempotency_policy_mismatch")
    risk = _mapping(config.get("risk_contract"))
    if not _valid_risk_contract(risk):
        blockers.append("risk_contract_mismatch")
    paper = _mapping(config.get("paper_gates"))
    if (
        paper.get("minimum_days") != 20
        or paper.get("minimum_fills") != 30
        or paper.get("minimum_market_regimes") != 2
        or paper.get("manual_approval_required") is not True
        or paper.get("strategy_must_pass_frozen_prescreen") is not True
    ):
        blockers.append("paper_gate_mismatch")
    controls = _mapping(config.get("risk_controls"))
    if controls.get("kill_switch_required") is not True:
        blockers.append("kill_switch_not_required")
    for key in (
        "pre_trade_risk_check_required",
        "post_trade_reconciliation_required",
        "append_only_audit_log_required",
        "manual_confirmation_required",
        "default_deny_on_unknown_state",
    ):
        if controls.get(key) is not True:
            blockers.append(f"risk_control_not_required:{key}")
    if tuple(config.get("required_broker_onboarding_inputs", ())) != REQUIRED_BROKER_INPUTS:
        blockers.append("broker_onboarding_inputs_mismatch")
    boundaries = _mapping(config.get("boundaries"))
    if boundaries.get("schema_validation_allowed") is not True:
        blockers.append("schema_validation_not_allowed")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            blockers.append(f"boundary_enabled:{key}")
    blockers = list(dict.fromkeys(blockers))
    return {
        "stage": "cn_etf_execution_interface_contract_readiness",
        "status": "blocked" if blockers else "schema_ready_execution_disabled",
        "blockers": blockers,
        "broker": dict(broker),
        "market_contract": dict(market),
        "order_intent_schema": dict(order),
        "risk_contract": dict(risk),
        "paper_gates": dict(paper),
        "risk_controls": dict(controls),
        "required_broker_onboarding_inputs": list(
            config.get("required_broker_onboarding_inputs", ())
        ),
        "schema_validation_allowed": boundaries.get("schema_validation_allowed")
        is True,
        "broker_connection_allowed": boundaries.get("broker_connection_allowed")
        is True,
        "account_read_allowed": boundaries.get("account_read_allowed") is True,
        "order_placement_allowed": boundaries.get("order_placement_allowed")
        is True,
        "live_boundary_allowed": boundaries.get("live_boundary_allowed") is True,
        "next_direction": (
            "collect_broker_documentation_then_build_offline_contract_tests"
            if not blockers
            else "repair_schema_without_crossing_external_boundary"
        ),
    }


def _valid_risk_contract(risk: Mapping[str, Any]) -> bool:
    return (
        risk.get("capital_cny") == {"minimum": 1000, "maximum": 3000}
        and risk.get("commission_bps_per_side") == 0.5
        and risk.get("slippage_bps_per_side") == 10.0
        and risk.get("minimum_commission_cny_stress") == 5.0
        and risk.get("absolute_max_drawdown") == 0.4
        and risk.get("paper_promotion_max_drawdown") == 0.08
        and risk.get("max_holding_sessions") == 252
        and risk.get("max_single_position_cny") == 1000
        and risk.get("max_daily_loss_cny") == 60
        and risk.get("max_one_way_adv_participation") == 0.01
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
