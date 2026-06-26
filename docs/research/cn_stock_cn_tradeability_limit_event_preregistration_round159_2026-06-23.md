# CN Stock Tradeability Limit Event Preregistration Round159

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: cn_tradeability_limit_event_preregistration
- Source audit: docs/research/cn_stock_price_volume_shock_reversal_neutral_prescreen_round158_2026-06-23.md
- Output: data/reports/cn_tradeability_limit_event_preregistration_round159_20260623

## Why This Round Exists

Round158 produced zero residual research leads from the price-volume shock reversal family. Continuing that line would mostly be parameter tuning after a neutral/residual failure. Round159 rotates to a different mechanism: A-share real tradeability and limit-event structure.

This directly addresses the optimization gaps raised by the user:

- A-share trading rules: limit-up/down, suspension proxy, ST, new listing, delisting/inactive metadata, and board permission controls must be explicit.
- Financial PIT timing: financial factors must use announcement/revision/availability timing; not report-period-only timing.
- Industry/style neutrality: raw IC is not enough; residual and exposure checks are mandatory before ranking results.
- ETF rotation boundary: CN stock alpha mining is not CN ETF rotation; ETF signals need a separate pack.
- Portfolio construction: raw TopN is not promotion evidence; risk budget, volatility, industry, turnover, and de-risk rules are separate gates.
- Strict statistics: deflated Sharpe, CPCV/FDR, and parameter sensitivity remain required before promotion.
- China regimes: policy, credit, flow/liquidity, and index-location context must be audited before walk-forward promotion.
- Event factors: event timing and event-contamination controls are required before promotion.

## Preregistration Result

- Candidates: 8
- Families: 7
- RSRS candidates: 0
- Moneyflow candidates: 0
- Price-volume-shock candidates: 0
- True limit audit required candidates: 8
- Tradeability controls required candidates: 8
- Portfolio backtest allowed now: 0
- Promotion allowed now: 0
- Next required gate: round160_cn_tradeability_limit_event_proxy_prescreen

## Candidate Names

| Candidate | Family | Direction | Windows |
| --- | --- | --- | --- |
| limit_down_relief_reversal_liquid_1_5 | limit_down_recovery | higher_is_better | 1, 5, 20 |
| near_limit_down_rebound_quality_3_10 | limit_down_recovery | higher_is_better | 3, 10, 20 |
| limit_up_exhaustion_avoidance_1_5 | limit_up_exhaustion | lower_is_better | 1, 5, 20 |
| failed_limit_up_reversal_1_5 | limit_up_failure | higher_is_worse | 1, 5, 20 |
| limit_event_cooling_momentum_5_20 | post_limit_cooling | higher_is_better | 5, 20 |
| post_limit_down_nonst_recovery_5_20 | nonst_limit_down_recovery | higher_is_better | 5, 20 |
| limit_pressure_asymmetry_reversal_5_20 | limit_pressure_asymmetry | higher_is_better | 5, 20 |
| new_high_near_limit_failure_reversal_20 | new_high_limit_failure | higher_is_worse | 1, 5, 20 |

## Required Controls Before Any Portfolio Use

- Official or audited true-limit status coverage, or explicit proxy-error accounting if official limit feeds are unavailable.
- CN stock tradeability gate coverage for suspension, ST, new listing, delisting/inactive rows, board permissions, and entry/exit blocking.
- Industry-neutral and style-residual IC after raw IC.
- Signal-window regime coverage so a filter cannot silently remove the whole trading window.
- Multiple-testing accounting and parameter sensitivity before any ranking by Sharpe or profit.
- Cost/capacity and turnover stress before any portfolio-grid claim.

## Decision

Round159 is a preregistration success, not a profitability result. It adds 8 new candidate hypotheses and updates the process so future starts must explicitly confirm the eight optimization controls. The correct next action is Round160 proxy prescreen over the long sample with execution lag and tradeability-blocked signal accounting.
