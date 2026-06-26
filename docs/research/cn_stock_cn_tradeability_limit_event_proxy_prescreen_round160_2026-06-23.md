# CN Stock Tradeability Limit Event Proxy Prescreen Round160

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: cn_tradeability_limit_event_proxy_prescreen
- Source preregistration: docs/research/cn_stock_cn_tradeability_limit_event_preregistration_round159_2026-06-23.md
- Output: data/reports/cn_tradeability_limit_event_proxy_prescreen_round160_20260623

## Run Scope

- Bar rows: 10,785,537
- Assets: 5,707
- Window: 2015-01-05 to 2025-12-31
- Candidate count: 8
- Test count: 8
- Factor rows: 81,168,168
- Industry-neutral rows: 78,227,424
- Residual rows: 77,661,592
- Horizon: 5 trading days
- Execution lag: 1 trading day
- Final holdout included: false

## Headline Result

- Proxy research leads: 0
- Portfolio preflight candidates: 0
- Promotion candidates: 0
- True-limit status audit required candidates: 8
- Next direction: round161_rotate_after_tradeability_limit_event_proxy_prescreen_failure

This means the Round159 tradeability/limit-event family did not produce a candidate worth spending more budget on official true-limit/suspension feed integration or portfolio conversion.

## Candidate Results

| Candidate | Raw IC | Raw ICIR | Neutral IC | Residual IC | Residual ICIR | Blocked signal rate | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| limit_down_relief_reversal_liquid_1_5 | -0.0178 | -0.141 | -0.0118 | 0.0249 | 0.339 | 0.359 | reject |
| near_limit_down_rebound_quality_3_10 | -0.0144 | -0.108 | -0.0067 | 0.0193 | 0.309 | 0.359 | reject |
| limit_pressure_asymmetry_reversal_5_20 | 0.0044 | 0.039 | 0.0088 | 0.0120 | 0.190 | 0.359 | reject |
| limit_event_cooling_momentum_5_20 | -0.0534 | -0.435 | -0.0428 | 0.0081 | 0.122 | 0.359 | reject |
| new_high_near_limit_failure_reversal_20 | 0.0598 | 0.563 | 0.0499 | 0.0036 | 0.061 | 0.359 | reject |
| post_limit_down_nonst_recovery_5_20 | -0.0191 | -0.125 | -0.0114 | -0.0050 | -0.085 | 0.359 | reject |
| failed_limit_up_reversal_1_5 | 0.0272 | 0.285 | 0.0215 | -0.0143 | -0.233 | 0.359 | reject |
| limit_up_exhaustion_avoidance_1_5 | 0.0072 | 0.071 | 0.0084 | -0.0162 | -0.213 | 0.359 | reject |

## Why The Apparent Leads Are Not Usable

- `new_high_near_limit_failure_reversal_20` had strong raw and industry-neutral IC, but residual IC collapsed to 0.0036. The signal is mostly style/exposure, not robust standalone alpha.
- `limit_down_relief_reversal_liquid_1_5` had residual IC 0.0249 and residual positive rate 0.635, but raw and industry-neutral IC were negative, tradeability-blocked signal rate was 35.9%, and size/liquidity exposure was high.
- All candidates had tradeability-blocked signal rate above the 35% cap, which is a serious warning for a family based on limit-event proxies.
- The family remains proxy-only; official true-limit/suspension status was not integrated, so no result can be promoted even if IC were stronger.

## Yearly Residual Stability

- `limit_down_relief_reversal_liquid_1_5`: 0 failed years, residual IC range 0.0061 to 0.0399, but blocked by negative industry-neutral behavior, blocked signal rate, and high liquidity exposure.
- `near_limit_down_rebound_quality_3_10`: 0 failed years, residual IC range 0.0086 to 0.0408, but residual mean 0.0193 is below the 0.02 threshold and blocked rate is high.
- `limit_up_exhaustion_avoidance_1_5` and `failed_limit_up_reversal_1_5`: 11 failed residual years each.
- `post_limit_down_nonst_recovery_5_20`: 9 failed residual years.
- `new_high_near_limit_failure_reversal_20`: 5 failed residual years.

## Decision

Do not proceed to official true-limit feed audit, cost/capacity walk-forward, or portfolio grid for this family. The next action is to rotate away from tradeability/limit-event proxies and choose a new, economically distinct family for Round161.
