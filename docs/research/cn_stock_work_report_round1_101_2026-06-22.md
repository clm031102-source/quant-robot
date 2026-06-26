# CN Stock Factor Mining Work Report Rounds 1-101 - 2026-06-22

## Current Mandate

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha research
- Not scope: ETF rotation, broker connection, account reads, orders, or live trading
- Governance: review every 3 factor batches, package/sync every 10 batches

## Headline Result

Through Round101:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current newly pre-registered Round101 candidates: 10
- Current next direction: `round102_capacity_safe_price_volume_alphalens_style_prescreen`

This is not a satisfying profitability result, but it is the correct research result: no weak or overfit evidence has been promoted.

## Latest Rounds 91-101

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

## Bright Data That Actually Matters

### Data Infrastructure

- Real Tushare financial data path now exists instead of relying on daily-basic profitability proxies.
- Full100 financial shard quality was clean: 4,328 final rows, 0 duplicates, 0 missing asset IDs.
- PIT readiness reached 4,412/4,412 in the shard audit.
- Factor-label alignment caught no violations in Round97.

### Research Governance

- Round98 blocked false promotion early: 28 statistical tests produced 0 Bonferroni and 0 FDR significant leads.
- Round99 hibernated the failed profitability-quality family instead of expanding parameters.
- Round101 prevents the next family from jumping directly into top-N portfolio grids.
- The startup gate now explicitly blocks random price-volume formula search without public rationale.

### Historical Near-Misses

These are useful research memories, not promotable results:

| Candidate / line | Bright number | Why not usable |
|---|---:|---|
| ETF range-contraction short-window lead | Sharpe around 1.83 in short-window grids | adjusted IC p-value stayed 1.0 and long-cycle replay collapsed to around 0.44-0.53 Sharpe |
| `mf_low_minus_volatility_20` stock line | top10/cost30/regime150 relative return 72.2635, Sharpe 1.2835, tail-IC p=0.0010 | 61 capacity-limited trades, max participation 169.3% |
| `large_minus_liquidity_20` small-capacity line | at 500k, top10/cost20/regime150 had relative return 38.2135, max DD -0.2824, tail-IC p=0.0040, capacity-limited trades 0 | corrected OOS later had negative benchmark-relative return, so it became defensive near-miss only |
| `large_plus_momentum_5` raw tail line | top3/cost20/regime150 Sharpe 5.2473 | drawdown and capacity failure; high Sharpe is not reliable promotion evidence |
| profitability-quality family | clean PIT matrix and 14/14 coverage-passed | controlled IC found 0 multiple-testing leads |

## Best Current Work Product

The best outcome so far is not a factor. It is the validation machinery:

1. Long-cycle and same-parameter replay are now mandatory.
2. Final holdout is protected from tuning.
3. PIT financial data uses announcement dates as availability.
4. Multiple-testing accounting is required.
5. Cost, capacity, turnover, drawdown, and regime coverage are gates rather than afterthoughts.
6. Failed families now rotate instead of receiving endless parameter sweeps.

## Round101 Factor Parameters

All Round101 candidates share:

- Market: CN stock
- Min signal-date amount: 10,000,000
- Max position ADV participation: 5%
- Min listing days: 120
- ST/suspended/limit-untradable exclusions
- Next gate: Alphalens-style IC, quantile, turnover, coverage, and capacity prescreen
- Portfolio backtest before prescreen: false
- Promotion allowed now: false

Most important Round101 candidates to screen next:

| Factor | Formula template |
|---|---|
| `pv_lowvol_reversal_blend_20` | `0.45*cs_z(reversal_5)+0.35*cs_z(-pv_corr_20)+0.20*cs_z(-downside_vol_20)` |
| `range_contraction_lowvol_reversal_20` | `0.40*cs_z(reversal_5)+0.35*cs_z(-hl_range_20)+0.25*cs_z(-realized_vol_20)` |
| `volume_contraction_reversal_lowvol_20` | `0.45*cs_z(reversal_5)+0.35*cs_z(-amount_trend_20)+0.20*cs_z(-downside_vol_20)` |
| `skip5_momentum_lowvol_20` | `0.60*cs_z(skip5_momentum_20)+0.40*cs_z(-realized_vol_20)` |
| `bollinger_reversal_lowvol_liquid_20` | `0.55*cs_z(bollinger_reversal_20)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20)` |

## Conclusion

The project has not yet produced a usable profitable factor. The best historical numbers are mostly useful as warnings: high Sharpe without IC significance, capacity, OOS, and benchmark-relative validation is not enough.

The useful progress is that the office desktop is now moving from undisciplined mining toward preregistered, public-reference-backed, capacity-aware factor research. Round102 should be a prescreen, not a portfolio sweep.
