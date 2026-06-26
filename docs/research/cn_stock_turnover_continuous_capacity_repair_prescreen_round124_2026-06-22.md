# CN Stock Turnover Continuous Capacity Repair Prescreen Round124 - 2026-06-22

## Scope

Round124 follows the Round123 preregistration for continuous capacity repairs of the raw low-turnover daily-basic leads:

- `turnover_rate_low`
- `turnover_rate_f_low`

This round is an Alphalens-style IC, quantile, turnover, and capacity prescreen. It is not a TopN portfolio grid and cannot promote a factor by itself.

Artifact:

`data/reports/turnover_continuous_capacity_repair_prescreen_round124_20260622`

Data window:

- Bars: 2015-01-05 through 2025-12-31
- Labels: through 2025-12-23
- Final holdout: 2026 not included
- Assets: 5,707
- Factor rows: 60,763,236
- Aligned factor-label rows: 120,634,176

## Result

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Top turnover | Max participation | Extreme rate | Raw corr | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.649 | 33.35 | 75.3% | 0.0673 | 0.900 | 27.8% | 0.0001 | 2.03% | 1.000 | yes |
| `turnover_rate_low_participation_budget_100k_20` | 20 | 0.0973 | 0.556 | 28.61 | 71.9% | 0.0648 | 0.900 | 23.2% | 0.0001 | 1.94% | 1.000 | yes |
| `turnover_rate_f_low_participation_budget_100k_20` | 5 | 0.0775 | 0.492 | 25.36 | 70.8% | 0.0327 | 1.000 | 27.8% | 0.0001 | 0.49% | 1.000 | yes |
| `turnover_rate_low_participation_budget_100k_20` | 5 | 0.0718 | 0.426 | 21.95 | 67.7% | 0.0302 | 1.000 | 23.2% | 0.0001 | 0.47% | 1.000 | yes |
| `turnover_rate_f_low_adv_soft_rank_20` | 5 | 0.0522 | 0.303 | 15.63 | 62.0% | 0.0227 | 0.700 | 11.5% | 0.0001 | 0.48% | 0.790 | yes |

Summary:

- Candidates: 6
- Tests: 12
- FDR-significant tests: 12
- Capacity-clean tests: 12
- Research leads: 5
- Promotion allowed: 0
- Portfolio grid allowed immediately: 0

## Interpretation

This is the first useful signal after the Round122 capacity audit:

- The binary `_large_mv` repair was too destructive.
- The continuous participation-budget repair keeps the raw low-turnover return engine at 100k / Top100 sizing.
- Capacity diagnostics are clean at this prescreen stage: max estimated participation is far below the 1% ADV policy and capacity-limited top-quantile trades are zero.
- The strongest 20-day candidates have high IC, high ICIR, strong t-stats, monotone quantiles, and moderate top-quantile turnover.

The result is still not a profitable-factor claim:

- This is IC and quantile evidence, not a costed long-only portfolio.
- The best candidates are highly correlated with the raw low-turnover lead, so they need de-duplication and sensitivity checks.
- The 100k / Top100 sizing assumption must be stress-tested before any larger capital claim.
- Walk-forward, cost, capacity, regime, and overlap-aware return gates remain mandatory.

## Decision

Classify the five passing factor-horizon pairs as:

`research_lead_capacity_repair_prescreen_passed`

Do not classify them as:

- paper-ready
- promotable
- manual/live usable
- portfolio-grid validated

## Process Fix

During Round124, the first generated report incorrectly treated any nonzero extreme forward-return count as an automatic blocker. That was too strict for a 10-year, large-universe prescreen. The gate now records both count and rate, and blocks only when the extreme top-quantile forward-return rate exceeds the configured limit.

This matters because a diagnostic count is not the same as tradeability failure.

## Next Direction

Advance to:

`turnover_repair_correlation_dedup_and_small_capital_sensitivity`

Required next checks:

- de-duplicate the five leads against raw `turnover_rate_low` and `turnover_rate_f_low`;
- replay small-capital sensitivity for 100k, 500k, 1m, and 5m notional assumptions;
- audit whether the 20-day lead can become a costed TopN portfolio without capacity/extreme-trade contamination;
- keep promotion and live/manual use blocked until walk-forward, costs, regime coverage, and overlap-aware return gates pass.
