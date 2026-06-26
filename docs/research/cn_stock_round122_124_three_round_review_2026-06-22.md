# CN Stock Round122-124 Three-Round Review - 2026-06-22

## Scope

This review covers the required three-round audit cadence for:

- Round122: aggressive turnover capacity audit
- Round123: turnover continuous capacity repair preregistration
- Round124: turnover continuous capacity repair prescreen

The question under review:

Can the strong raw low-turnover daily-basic return engine be repaired for realistic small-capital execution without reusing the failed binary large-market-cap repair?

## Round Evidence

| Round | Action | Output | Main result |
|---:|---|---|---|
| 122 | Audit high-return raw low-turnover leads under aggressive drawdown tolerance | `docs/research/cn_stock_aggressive_turnover_capacity_audit_round122_2026-06-22.md` | Raw returns and drawdowns were attractive, but raw factors were capacity/extreme-trade blocked; binary `_large_mv` repair failed |
| 123 | Pre-register continuous capacity repair candidates | `docs/research/cn_stock_turnover_continuous_capacity_repair_preregistration_round123_2026-06-22.md` | 6 candidates registered; promotion and portfolio grid both blocked before prescreen |
| 124 | Run long-cycle IC/quantile/turnover/capacity prescreen | `docs/research/cn_stock_turnover_continuous_capacity_repair_prescreen_round124_2026-06-22.md` | 5 factor-horizon research leads, 0 promotion, 0 direct portfolio-grid permission |

## Best Evidence

The best Round124 leads are:

| Factor | Horizon | IC | ICIR | t-stat | Q5-Q1 | Mono | Top turnover | Max participation | Extreme rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.649 | 33.35 | 0.0673 | 0.900 | 27.8% | 0.0001 | 2.03% |
| `turnover_rate_low_participation_budget_100k_20` | 20 | 0.0973 | 0.556 | 28.61 | 0.0648 | 0.900 | 23.2% | 0.0001 | 1.94% |
| `turnover_rate_f_low_participation_budget_100k_20` | 5 | 0.0775 | 0.492 | 25.36 | 0.0327 | 1.000 | 27.8% | 0.0001 | 0.49% |
| `turnover_rate_low_participation_budget_100k_20` | 5 | 0.0718 | 0.426 | 21.95 | 0.0302 | 1.000 | 23.2% | 0.0001 | 0.47% |
| `turnover_rate_f_low_adv_soft_rank_20` | 5 | 0.0522 | 0.303 | 15.63 | 0.0227 | 0.700 | 11.5% | 0.0001 | 0.48% |

## What Improved

- Drawdown tolerance is now separated from tradability. A 30% drawdown tolerance no longer waives capacity.
- The failed binary `_large_mv` repair is explicitly rejected.
- Round123 candidates were preregistered before evaluation, reducing post-hoc parameter mining.
- Round124 used long-cycle 2015-2025 evidence and kept 2026 out of tuning.
- The extreme-return gate was corrected from raw count to rate, avoiding a large-sample false rejection.

## What Is Still Not Proven

These are not promotable factors yet:

- No costed TopN portfolio has passed.
- No walk-forward fold has accepted the repaired factors.
- No regime coverage or signal-window coverage has been checked for the repaired portfolio.
- No small-capital sensitivity curve has been run beyond the 100k / Top100 prescreen assumption.
- The best leads are highly correlated with raw low-turnover, so they may still be the same return engine in a cleaner package rather than a distinct alpha.

## Decision

Continue the repaired low-turnover line for one more disciplined gate, not a broad parameter search.

Allowed next direction:

`turnover_repair_correlation_dedup_and_small_capital_sensitivity`

Blocked next directions:

- direct promotion from Round124 IC evidence
- direct TopN grid before de-duplication and small-capital sensitivity
- reuse of binary `_large_mv` repair
- more low-turnover parameter sweeps without new capacity evidence

## Stop-Loss Rule

If Round125 shows that the five leads are either redundant with the raw blocked factors or fail above small capital assumptions, hibernate the low-turnover family and rotate back to financial profitability-quality coverage or another public-reference family.
