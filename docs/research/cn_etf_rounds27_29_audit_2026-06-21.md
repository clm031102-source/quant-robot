# CN ETF Rounds 27-29 Audit

Date: 2026-06-21

## Scope

This audit covers:

- Round 27: regime-filtered walk-forward for frozen public trend-volume leads
- Round 28: no-regime walk-forward for the same frozen public trend-volume leads
- Round 29: no-regime walk-forward for basic momentum / risk-adjusted momentum

This implements the standing rule: every 3 rounds, review the prior work and adjust direction.

## Results

| Round | Work | Tested cases | Accepted candidates | Promotable factors | Main outcome |
|---:|---|---:|---:|---:|---|
| 27 | Regime-filtered WF for trend-volume leads | 6 | 0 | 0 | Invalid/weak validation: preflight should have blocked insufficient regime-allowed dates |
| 28 | No-regime WF for trend-volume leads | 6 | 0 | 0 | Best lead had 3/4 accepted folds, Sharpe 0.67, but failed adjusted IC significance |
| 29 | No-regime WF for momentum / risk-adjusted momentum | 8 | 0 | 0 | Basic momentum failed; best Sharpe only 0.20 and no IC significance |

## Key Findings

1. The Round 27 regime filter was too restrictive.

Post-run preflight showed:

- median regime-allowed rebalance dates: 6.5
- policy minimum: 20
- status: blocked

This explains the 0-trade and low-trade folds. It was a process failure that has now been corrected by making preflight respect `asset_universe_path` and running preflight before new WF jobs.

2. Trend-volume improved after removing the regime filter, but still failed promotion.

Best Round 28 row:

- `CN_ETF_smart_money_trend_20_top5_cost5_reb5`
- accepted folds: 3 / 4
- mean OOS Sharpe: 0.6701
- mean OOS relative return: 0.0800
- total OOS trades: 480
- adjusted IC p-value: 1.0
- status: rejected

This is a real research lead, but not a tradable/paper-ready factor.

3. Basic momentum was weaker.

Best Round 29 row:

- `CN_ETF_risk_adjusted_momentum_20_top5_cost5_reb5`
- accepted folds: 1 / 4
- mean OOS Sharpe: 0.2013
- mean OOS relative return: 0.0630
- total OOS trades: 480
- adjusted IC p-value: 1.0
- status: rejected

This family should not be mutated further under the same setup.

## Useful Work Produced

New promotable factors:

- 0

New paper-ready factors:

- 0

Reusable method improvements:

- ETF validation preflight now respects `asset_universe_path`.
- Walk-forward configs now preserve `asset_universe_path`.
- Preflight is now a hard gate before ETF walk-forward.
- The filtered ETF universe path is wired into experiment and validation configs.

Research leads to remember:

- `smart_money_trend_20_top5_cost5_reb5` on the liquid ETF universe is the best diagnostic lead so far, but fails adjusted IC significance.

## Direction Decision

Stop:

- Mutating public trend-volume parameters.
- Mutating basic momentum windows under the same structure.
- Running regime-filtered ETF WF unless preflight shows enough regime-allowed rebalance dates.

Continue:

- Round 25 liquid ETF universe.
- No-regime or preflight-cleared validation first.
- Public, interpretable ETF factor families.
- Strict rejection when adjusted IC significance fails.

Rotate next to:

- liquidity/tail-guard mean reversion,
- low-volatility defensive rotation,
- drawdown recovery,
- breadth/risk-on overlay.

## Round 30 Requirement

Round 30 should be the ten-round sync point:

- run targeted verification,
- run project audit,
- run safe sync audit,
- commit and push syncable code/config/docs to GitHub,
- keep data and reports out of Git.

## Conclusion

Rounds 27-29 did not find a usable profitable factor.

They did improve the process and eliminated two bad paths:

- regime-filtered trend-volume with too little OOS coverage,
- basic ETF momentum under the current Top5 setup.

The project should now sync the completed infrastructure and reports, then continue factor search from a new public ETF family.
