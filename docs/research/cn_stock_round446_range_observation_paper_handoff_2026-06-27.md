# CN Stock Round446 Range Observation Paper Handoff

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round446 upgrades the paper-simulation handoff pack with the two selected `range_contraction_lowvol_reversal_20` observation lanes from Rounds442-445.

These lanes are not promoted as final alpha. They are added so the next simulation stage can compare:

- the delayed-exit Alpha101/Dragon base;
- the more cost-robust range increment;
- the more aggressive high-return range increment.

## Command

```powershell
python scripts\run_simulation_shortlist_paper_handoff.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round446_24h_profit_sprint_range_observation_paper_handoff_20260627
```

## Handoff Result

Output:

`data/reports/round446_24h_profit_sprint_range_observation_paper_handoff_20260627`

Summary:

- total candidates: 8;
- ready candidates: 5;
- blocked research references: 3;
- default candidate remains `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`.

| Candidate | Role | Annualized | Max DD | OOS Strict | Status |
|---|---|---:|---:|---:|---|
| `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08` | default 10 bps | 6.66% | -26.21% | 90.00% | ready |
| `paper_ready_delayed_exit_m150_cost20_vt08_max100_self_roll21_x08` | heavier-cost 20 bps | 6.06% | -28.07% | 76.67% | ready |
| `paper_ready_delayed_exit_m150_cost30_vt075_max100_self_roll21_x08` | 30 bps fallback | 5.42% | -29.66% | 76.67% | ready |
| `paper_ready_cohort_entry_timed_range_q10_m150_cost10_vt08_max100_self_roll21_x08` | diagnostic | 7.08% | -26.99% | 90.00% | ready |
| `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08` | diagnostic | 7.72% | -29.31% | 90.00% | ready |

The three blocked rows are older superseded research references. They remain blocked because they are not current paper-ready cohort entry-timed candidates.

## Candidate Interpretation

`range_q10_m150` is the more cost-robust range observation lane:

- annualized return improves from 6.663% to 7.083%;
- total return improves from +218.46% to +241.70%;
- overlap Sharpe improves from 0.496 to 0.505;
- max drawdown worsens moderately from -26.21% to -26.99%;
- Round443 incremental CPCV annualized win rate is 90.83%;
- bootstrap drawdown-within-30% rate is only about 56%, so path risk remains.

`range_q20_m175` is the aggressive 10 bps observation lane:

- annualized return reaches 7.723%;
- total return reaches +280.30%;
- overlap Sharpe reaches 0.512;
- max drawdown is -29.31%, inside the approximate user tolerance but close to the line;
- mean OOS annualized return is 11.739% with 90.00% OOS strict pass;
- heavier-cost robustness is weak: 20 bps VT 8% drawdown was about -31.07%.

## Decision

Keep the delayed-exit 10 bps lane as the default paper-simulation candidate.

Add:

- `range_q10_m150` as a cost-robust return-enhancement observation lane;
- `range_q20_m175` as an aggressive 10 bps observation lane.

Do not use either range lane as a final promoted alpha. The evidence is strong enough for simulation comparison, but not strong enough to claim durable profitability after multiple-testing, bootstrap drawdown, and heavier-cost caveats.

## Next Direction

Stop widening the range-contraction grid for now. The next mining round should rotate to a genuinely different point-in-time family such as event-context underreaction, tradeability/liquidity microstructure, or PIT accounting-quality features, while preserving the Round446 handoff pack for the upcoming simulation stage.
