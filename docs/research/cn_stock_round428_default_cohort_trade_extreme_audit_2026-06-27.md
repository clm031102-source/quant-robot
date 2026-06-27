# CN Stock Round428 Default Cohort Trade Extreme Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round428 audits the current Round425 default handoff candidate at trade level. The goal is not to find another in-sample parameter tweak. The goal is to answer whether the strongest paper-simulation candidate is being carried by a small number of extreme individual trades.

Candidate:

`paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

Output:

`data/reports/round428_24h_profit_sprint_default_cohort_trade_extreme_audit_20260627`

## Important Causality Rule

The stress exclusions in this audit use realized trade gross return. That is future information at entry time.

Therefore, excluding trades after observing `gross_return` is a diagnostic stress haircut only. It is not a deployable live rule and must not be promoted as a paper-simulation signal.

The usable next step is to profile the extreme trades by entry-known features, then test entry-time quarantines such as board, listing age, liquidity, turnover, amount, price-limit state, suspension/ST/delist risk, or industry crowding.

## Trade-Level Findings

| Metric | Value |
|---|---:|
| total trades in source | 26,450 |
| active final trades | 26,090 |
| Dragon-Hot cash-filtered trades | 360 |
| public-factor tilted trades | 2,420 |
| capacity-limited trades | 0 |
| active trades with `abs(gross_return) > 50%` | 190 |
| active trades with `abs(gross_return) > 100%` | 24 |
| active trades with `gross_return > 50%` | 173 |
| active trades with `gross_return < -50%` | 17 |
| max active gross return | +676.58% |
| min active gross return | -67.40% |
| contribution from active `abs(gross_return) > 50%` trades | +40.92 percentage points |
| contribution share of original total return | 25.00% |

## Diagnostic Stress Results

These figures are trade-level diagnostics on the cohort source rows. They are not a replacement for the Round425 event-level handoff metrics because the aggregation basis differs.

| Scenario | Total Return | Annualized | Sharpe | Overlap Sharpe | Max DD | Win Rate | LOY Min Ann. | Blockers |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| original diagnostic stream | +163.71% | 4.67% | 0.787 | 0.436 | -29.17% | 37.72% | 3.22% | none |
| exclude `abs(gross_return) > 100%` | +132.33% | 5.01% | 0.771 | 0.420 | -32.56% | 40.51% | 3.11% | none |
| exclude `abs(gross_return) > 50%` | +76.25% | 3.41% | 0.572 | 0.314 | -33.07% | 40.61% | 2.11% | `best_months_contribution_too_high` |

## Interpretation

The default candidate still has positive return after removing all active trades with `abs(gross_return) > 50%`, but its quality degrades sharply:

- total return falls from about +164% to +76%;
- overlap Sharpe falls from 0.436 to 0.314;
- max drawdown worsens beyond the user's approximate -30% tolerance;
- best-month concentration becomes a formal blocker.

This does not prove the factor is worthless. It proves the current paper-simulation handoff is not clean enough to describe as an unqualified default. A meaningful part of the headline return is tied to rare extreme trades, especially around 2015.

## Decision

Downgrade the Round425 default handoff from clean default to conditional default pending an entry-time extreme-risk repair.

Keep it in the candidate pack as the best ordinary-metric benchmark, but do not treat it as simulation-ready without one of the following:

1. an entry-known quarantine that reduces the extreme-trade dependency without killing the edge;
2. a paper-simulation policy that explicitly accepts the extreme-trade tail profile and uses conservative sizing, drawdown stops, and capacity controls;
3. a stronger independent family that beats the candidate after the same stress audit.

## Next Direction

Round429 should use this finding in the three-round review. Round430 should profile the extreme trades by entry-known fields and test only causal repair rules. Future-return filters are forbidden as live logic.
