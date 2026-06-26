# CN ETF Rounds 24-26 Audit

Date: 2026-06-21

## Scope

This audit covers:

- Round 24: 2020 CN ETF Tushare backfill
- Round 25: liquid-continuous ETF universe gate
- Round 26: filtered public trend-volume factor grid

This implements the standing rule: every 3 rounds, review the prior work and adjust direction.

## Results

| Round | Work | New factor names | Tested cases | Promotable factors | Main outcome |
|---:|---|---:|---:|---:|---|
| 24 | Backfilled 2020 into the wide ETF root | 0 | 0 | 0 | 1,119,490 rows, 1,781 ETFs, 1,085 trading dates |
| 25 | Built liquid-continuous ETF universe gate | 0 | 0 | 0 | Filtered 1,781 ETFs to 264 tradable ETF assets |
| 26 | Ran filtered public trend-volume grid | 0 | 48 | 0 | 48 completed; 2 weak gate-approved rows; 0 statistically promotable |

Round 26 reused 6 existing public factor names:

- `supertrend_volume_confirmed_10_3_20`
- `smart_money_trend_20`
- `obv_breakout_low_tail_20`
- `anti_supertrend_volume_confirmed_10_3_20`
- `anti_smart_money_trend_20`
- `anti_obv_breakout_low_tail_20`

## Audit Judgment

The direction is now correct.

The work moved from weak/narrow data and raw broad selection into a more realistic ETF rotation research path:

- long-enough ETF history,
- broad enough ETF candidate pool,
- liquid-continuous universe filtering,
- public, interpretable trend-volume indicators,
- transaction costs and market-impact checks enabled.

This is materially better than repeatedly mutating moneyflow or running indicators on a 10-ETF CSV root.

## What Is Still Bad

No tradable factor has been found yet.

The Round 26 leaderboard still has serious problems:

- raw IC significance is `not_significant` for all 48 cases,
- the best full-sample rows are capacity-rejected,
- current decision logic approved one negative-total-return / negative-Sharpe row,
- full-sample discovery can still be regime-driven and overfit,
- no walk-forward out-of-sample validation has been run on the filtered universe yet.

Therefore, the correct conclusion is:

- 0 promotable factors
- 0 paper-ready factors
- 1 main walk-forward lead
- 2 small-capital/capacity diagnostic leads

## Main Lead

Primary frozen candidate for walk-forward:

- Factor: `supertrend_volume_confirmed_10_3_20`
- TopN: 5
- Cost: 5 bps
- Rebalance interval: 10
- Regime lookback: 60
- Full-sample total return: 0.3113
- Relative return: 0.4709
- Sharpe: 0.7260
- Max drawdown: -0.1829
- Win rate: 0.5435
- IC t-stat: 0.5104

This is only a research lead because IC significance is weak.

## Secondary Leads

Capacity diagnostic leads:

- `supertrend_volume_confirmed_10_3_20_top5_cost5_reb5_regime60`
- `obv_breakout_low_tail_20_top5_cost5_reb5_regime60`

These have strong full-sample performance but were rejected because capacity-limited trades were present.

They should only be replayed under a lower portfolio value or stricter liquidity policy as diagnostics. They should not be promoted from the current run.

## Direction Adjustment

Stop:

- Treating current `decision_status=approved` as enough for ETF promotion.
- Mutating trend-volume parameters before out-of-sample validation.
- Counting full-sample relative-return rows as useful factors.

Continue:

- Using the Round 25 filtered ETF universe for ETF rotation research.
- Using public, economically interpretable factor families.
- Freezing the best candidates before validation.

Change:

- Add a stricter ETF promotion screen that rejects:
  - negative total return,
  - negative Sharpe,
  - non-significant IC unless explicitly marked diagnostic,
  - capacity-limited rows for normal-size paper candidates,
  - full-sample-only winners without walk-forward acceptance.

## Next Work

Round 27 should not mine more parameters.

It should freeze the Round 26 leads and run filtered-universe walk-forward validation:

1. Primary: `supertrend_volume_confirmed_10_3_20_top5_cost5_reb10_regime60`
2. Diagnostic: `supertrend_volume_confirmed_10_3_20_top5_cost5_reb5_regime60`
3. Diagnostic: `obv_breakout_low_tail_20_top5_cost5_reb5_regime60`

After walk-forward:

- if all fail, rotate to a new public ETF factor family,
- if one survives, run capacity and cost sensitivity before any paper-ready claim.

## Conclusion

Rounds 24-26 produced no usable profitable factor.

They did produce a better and repeatable ETF factor-mining method:

- long-cycle ETF data foundation,
- liquid-continuous universe gate,
- explicit white-listing in experiment configs,
- a small public-factor discovery batch,
- a frozen candidate path for walk-forward.

The project is no longer blindly digging in the same family. It now has a cleaner loop: data gate, interpretable factor family, frozen leads, walk-forward validation, then rotate or harden.
