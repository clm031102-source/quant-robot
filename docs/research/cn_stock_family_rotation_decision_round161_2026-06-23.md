# CN Stock Family Rotation Decision Round161

Date: 2026-06-23

## Scope

This round converts the Round160 tradeability/limit-event proxy failure into a repeatable family-rotation decision before starting the next factor-mining branch.

Startup context:

- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Market / asset: CN stock
- Source audit: docs/research/cn_stock_cn_tradeability_limit_event_proxy_prescreen_round160_2026-06-23.md

## Decision

Selected next family:

- `china_market_regime_temperature_interaction`

Next action:

- `round161_china_market_regime_temperature_preregistration`

Allowed now:

- Research preregistration only

Not allowed now:

- Portfolio grid
- Promotion
- Live trading or live account actions

## Why This Family

Round160 found 0 proxy research leads from 8 tradeability/limit-event candidates. Continuing with true-limit feed audit, parameter tuning, or portfolio grids would spend more time on a family that did not clear its proxy screen.

The selected family is a different mechanism: lagged market-wide breadth, liquidity/turnover temperature, cross-sectional dispersion, and index-location proxies condition stock cross-sectional signals. It directly addresses the China-market-regime control gap from the eight-point optimization list while avoiding the failed recent families.

The next preregistration must enforce:

- lagged market-temperature state only;
- no same-day forward-label leakage;
- tradeability filter before signal evaluation;
- industry/style residual evaluation;
- regime coverage by signal window;
- multiple-testing accounting;
- no portfolio grid before residual prescreen.

## Family Review

| Family | Decision | Reason |
|---|---|---|
| `china_market_regime_temperature_interaction` | selected | Data can be built from bars, amount, and metadata; mechanism is not raw single-stock TopN. |
| `tradeability_limit_events` | hibernated | Round160 tested 8 proxy candidates and found 0 research leads. |
| `price_volume_shock_reversal` | hibernated | Round158 had 0 residual research leads. |
| `public_technical_failure_reversal` | hibernated | Round156 residual alpha failed and RSRS references were redundant. |
| `pit_profitability_event_revision` | hibernated | Round153 controlled PIT/neutral IC prescreen found 0 research leads. |
| `industry_relative_strength_breadth_bridge` | hibernated | Round69 had 0 bridge candidates despite positive industry RankIC. |
| `moneyflow_residual_regime` | hibernated | Earlier long-cycle validation remained capacity/regime-local and not paper-ready. |
| `external_macro_or_northbound_credit_feed` | blocked by data gap | Local processed data does not yet prove complete northbound, margin, or credit-cycle history. |

## Candidate Plan Seed

Round161 preregistration should start from these candidate ideas, without portfolio conversion:

- `regime_cold_liquidity_reversal_quality_20_5`
- `regime_hot_turnover_exhaustion_avoidance_10_5`
- `breadth_recovery_residual_momentum_20_10`
- `dispersion_high_lowvol_residual_reversal_20_5`
- `index_location_low_residual_value_liquidity_60_10`
- `market_temperature_state_interaction_composite_20_5`

## Artifacts

- Tool: `src/quant_robot/ops/cn_stock_family_rotation_decision.py`
- CLI: `scripts/run_cn_stock_family_rotation_decision.py`
- Tests: `tests/unit/test_cn_stock_family_rotation_decision.py`, `tests/unit/test_cn_stock_family_rotation_decision_cli.py`
- Local output: `data/reports/cn_stock_family_rotation_decision_round161_20260623`

