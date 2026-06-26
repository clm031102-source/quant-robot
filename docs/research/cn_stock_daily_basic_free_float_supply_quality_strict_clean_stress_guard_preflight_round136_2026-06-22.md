# CN Stock Daily-Basic Free-Float Supply Quality Strict-Clean Stress-Guard Preflight - Round136

## Scope

- Machine/task: office_desktop factor validation.
- Market/universe: CN stocks only, not CN ETF rotation.
- Candidate: `daily_basic_free_float_supply_quality_20_strict_clean_implementation_residual`.
- Source: Round134 residual stability audit and Round135 three-round review.
- Sample: bars from 2015-01-05 to 2025-12-31; factor availability from 2023-07-03 to 2025-12-31.
- Final holdout: 2026 data was not read.
- Method: single frozen candidate, TopN 100, hold 20, rebalance 20, T+1, costs 10/20 bps, capital 100k/500k/1m, with and without pre-registered stress-date blocking.

## Outputs

- Report dir: `data/reports/daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_round136_20260622`
- JSON: `daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight.json`
- Leaderboard: `daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_leaderboard.csv`
- Extreme trades: `daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_extreme_trades.csv`

## Result Summary

- Unique factor tested: 1.
- Portfolio cases: 12.
- Signal rows after rebalance filter: 110,813 across 31 signal dates.
- Walk-forward allowed candidates: 0.
- Promotion allowed: 0.
- Capacity-limited trades: 0 in all cases.
- Best total return: 1,212.90% in the stress-guarded 10 bps / 100k case.
- Best full overlap-adjusted Sharpe: 2.089 in the stress-guarded 10 bps cases.
- Best OOS overlap-adjusted Sharpe: 2.168 in unguarded 10 bps cases.
- Best stress-guarded max drawdown: about -10.76%.
- Worst max drawdown across cases: -31.48%.

## Gate Decision

No case can advance to walk-forward or promotion.

The apparent best cases are not rejected because of capacity or because a 30% drawdown is automatically unacceptable. The key hard blocker is `extreme_trade_return_present`, which appears in all 12 cases. Unguarded cases also have `calendar_holding_gate_filtered_trades`; the 20 bps unguarded cases breach the -30% user drawdown floor.

Stress guard materially improves portfolio quality:

| Mode | Cost | Capital | Full Total | Full Overlap Sharpe | Test Total | Test Overlap Sharpe | MaxDD | Blockers |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| none | 10 bps | 100k | 1144.93% | 0.771 | 1233.47% | 2.168 | -29.59% | calendar holding, extreme trades |
| block stress | 10 bps | 100k | 1212.90% | 2.089 | 1163.96% | 1.899 | -10.76% | extreme trades |
| block stress | 20 bps | 1m | 1184.18% | 2.084 | 1153.96% | 1.897 | -11.68% | extreme trades |

## Extreme Trade Diagnostic

- Extreme trade rows across cases: 1,104.
- Unique assets involved: 92.
- Unique exit dates involved: 11.
- Max absolute gross return: 209.79x.
- Largest trade example: `CN_XSHE_000651`, signal 2025-05-29, entry 2025-05-30, exit 2025-07-01, gross return 209.79x.
- Another large example: `CN_XSHG_600887`, same signal/entry/exit window, gross return 80.68x.

These are not plausible normal holding-period stock returns. The next step must audit price adjustment, symbol mapping, suspension/delist handling, corporate actions, and bar continuity around the extreme-trade windows before any walk-forward validation.

## Conclusion

Round136 found a stronger-looking implementation than prior raw turnover lines, especially after blocking stress dates, but all apparent profitability is untrusted until the extreme trade root cause is resolved.

Decision:

- Useful/promotable factors: 0.
- Walk-forward candidates: 0.
- Continuing research lead: 1 conditional lead, only if the extreme-trade/data-quality audit removes the anomaly without destroying the guarded case metrics.
- Next direction: `round137_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit`.
