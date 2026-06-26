# CN Stock Factor Mining Work Report Rounds 1-102 - 2026-06-22

## Current Mandate

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha research
- Not scope: ETF rotation, broker connection, account reads, orders, or live trading
- Governance: review every 3 factor batches, package/sync every 10 batches

## Headline Result

Through Round102:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current statistical research leads: 1
- Current lead: `bollinger_reversal_lowvol_liquid_20`, horizon 20
- Current next direction: `round103_capacity_safe_price_volume_bollinger_lead_dedup_and_three_round_review`

This is still not a profitable project result. It is, however, a better research result than the earlier blind sweeps: one public-reference-backed, capacity-filtered candidate survived a long-cycle IC/quantile/turnover prescreen without touching the 2026 final holdout.

## Latest Rounds 91-102

| Round | Work | Key output | Decision |
|---:|---|---|---|
| 91 | Tushare `fina_indicator` backfill plan | formal PIT financial data path | proceed to smoke |
| 92 | limited live smoke | 88 requests, 79 rows, 9 empty, duplicate 0, PIT pass | proceed to shard planning |
| 93 | full shard plan | 5,208 non-BJ symbols, 44 quarters, 229,152 planned requests, 53 shards | proceed to first10 |
| 94 | first10 shard | 440 requests, 429 final rows, duplicate 0, PIT 452/452 | proceed to full100 |
| 95 | full100 shard | 4,400 requests, 4,328 final rows, 72 empty, duplicate 0, missing asset id 0, PIT 4,412/4,412 | shard accepted |
| 96 | profitability-quality preregistration | 14 candidates, 14/14 coverage-passed | matrix smoke allowed |
| 97 | PIT factor matrix and label smoke | 58,711 factor rows, 117,394 label rows, 96.8949% label coverage, 0 alignment violations | IC screen allowed |
| 98 | controlled IC screen | 28 tests, 1,204 IC observations, Bonferroni 0, FDR 0 | no lead |
| 99 | family rejection audit | 6/6 requirements passed, family hibernated | rotate after sync |
| 100 | lightweight safe sync | commit `a21b119`, pushed current branch, upstream 0/0 | synced |
| 101 | capacity-safe price-volume preregistration | 10 candidates, 0 blockers, 0 promotion, 0 portfolio grid allowed | proceed to prescreen |
| 102 | long-cycle Alphalens-style prescreen | 10 candidates, 20 tests, 17 FDR-significant tests, 1 research lead, 0 promotion | proceed to dedup/review |

## Round102 Bright Data

Universe and sample:

- Bars: 10,785,537
- Assets: 5,707
- Factor rows: 100,830,409
- Labels: 21,417,227
- Aligned rows: 200,175,023
- Signal window: 2015-01-12 through 2025-12-31
- Final holdout included: false

Best current lead:

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Monotonicity | Top quantile turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `bollinger_reversal_lowvol_liquid_20` | 20 | 0.0379 | 0.314 | 16.15 | 61.3% | 0.0184 | 0.800 | 24.8% |

Notable blocked diagnostics:

- `range_contraction_lowvol_reversal_20`, horizon 20: IC 0.0973, ICIR 0.615, t 31.66, but monotonicity only 0.300.
- `pv_lowvol_reversal_blend_20`, horizon 20: IC 0.0790 and ICIR 0.683, but Q5-Q1 was negative.
- `price_volume_trend_quality_20_60`, horizon 20: IC -0.0698, confirming the pre-registered positive direction failed.

## Important User Preference Update

The user clarified that roughly 30% drawdown can be acceptable if total return and annualized return are strong.

Updated interpretation:

- Drawdown near 30% is no longer enough by itself to reject a high-return candidate.
- Capacity, tradability, extreme flags, cost, and execution remain hard gates.
- The old low-turnover high-return lines are therefore not discarded because drawdown is uncomfortable; they are blocked because capacity-clean variants lost most risk-adjusted quality.

This distinction is now recorded in the startup gate as:

```text
drawdown_tolerance_policy_separate_from_capacity_gate
```

## Best Work Products So Far

The best product is still the research machine rather than a promoted factor:

1. Long-cycle same-parameter replay is mandatory.
2. 2026 is protected as final holdout.
3. PIT financial data uses announcement-date availability.
4. Multiple-testing accounting is applied before claims.
5. Cost, capacity, turnover, drawdown, and regime checks are gates.
6. Failed families are hibernated instead of receiving endless parameter sweeps.
7. Round102 now has streaming prescreen infrastructure that can handle 200M aligned factor-label rows.

## Conclusion

Round102 improved the project from "no useful candidates in the active family" to "one credible statistical lead, no promotion yet."

The next useful work is not more blind mining. Round103 should run Bollinger lead correlation de-duplication, cost/capacity bridge checks, and the mandatory three-round review for Rounds 101-103 before any wider expansion.

