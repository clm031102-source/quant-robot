# CN Stock Turnover Continuous Capacity Repair Preregistration Round123 - 2026-06-22

## Scope

Round123 follows the Round122 aggressive turnover capacity audit.

Round122 conclusion:

- `turnover_rate_low` and `turnover_rate_f_low` are real high-return research leads.
- Their drawdowns are acceptable under the user's aggressive risk tolerance.
- They are not promotable because raw returns are capacity/extreme-trade contaminated.
- The existing binary `_large_mv` repair removes the hard capacity issue but destroys most return quality.

This round does not run a portfolio grid. It preregisters one disciplined repair family that can be screened cheaply before any larger validation.

Artifact:

`data/reports/turnover_continuous_capacity_repair_preregistration_round123_20260622`

## Candidates

| Candidate | Raw source | Repair type | Formula |
|---|---|---|---|
| `turnover_rate_low_adv_soft_rank_20` | `turnover_rate_low` | continuous capacity weight | `cs_z(-turnover_rate) * clip(cs_rank(log_adv20), 0.35, 1.00) + 0.20*cs_z(log_circ_mv)` |
| `turnover_rate_low_adv_mv_soft_blend_20` | `turnover_rate_low` | continuous capacity weight | `0.60*cs_z(-turnover_rate) + 0.25*cs_z(log_adv20) + 0.15*cs_z(log_circ_mv)` |
| `turnover_rate_low_participation_budget_100k_20` | `turnover_rate_low` | continuous capacity weight | `cs_z(-turnover_rate) * clip(0.01 / estimated_participation_100k_top100_adv20, 0.00, 1.00)` |
| `turnover_rate_f_low_adv_soft_rank_20` | `turnover_rate_f_low` | continuous capacity weight | `cs_z(-turnover_rate_f) * clip(cs_rank(log_adv20), 0.35, 1.00) + 0.20*cs_z(log_circ_mv)` |
| `turnover_rate_f_low_adv_mv_soft_blend_20` | `turnover_rate_f_low` | continuous capacity weight | `0.60*cs_z(-turnover_rate_f) + 0.25*cs_z(log_adv20) + 0.15*cs_z(log_circ_mv)` |
| `turnover_rate_f_low_participation_budget_100k_20` | `turnover_rate_f_low` | continuous capacity weight | `cs_z(-turnover_rate_f) * clip(0.01 / estimated_participation_100k_top100_adv20, 0.00, 1.00)` |

## Guardrails

- Promotion allowed: 0
- Portfolio backtest allowed before prescreen: 0
- Required next gate: `capacity_repair_ic_quantile_turnover_prescreen`
- Required source fields: `turnover_rate` or `turnover_rate_f`, `amount`, `circ_mv`
- Maximum position participation policy: 1% ADV
- Required diagnostics before portfolio use:
  - RankIC / ICIR / t-stat
  - quantile spread and monotonicity
  - top-quantile turnover
  - max participation and capacity-limited trade count
  - extreme trade return count
  - correlation to raw turnover leads
  - multiple-testing accounting

## Decision

Round123 preregistration passes:

- Candidates: 6
- Blockers: 0
- Promotion: 0
- Portfolio backtest permission: 0

This is not a profitable-factor claim. It is a controlled attempt to answer whether the strongest raw daily-basic turnover lead can be repaired without losing its return engine.

## Next Direction

Advance to:

`round124_turnover_continuous_capacity_repair_prescreen`

Round124 should build the factor matrices and run an Alphalens-style IC/quantile/turnover/capacity prescreen. No TopN portfolio grid should run until at least one candidate passes the prescreen with capacity and extreme-trade cleanliness.

If Round124 shows the continuous repairs also lose the return engine, hibernate the low-turnover family and return to financial profitability-quality coverage work.
