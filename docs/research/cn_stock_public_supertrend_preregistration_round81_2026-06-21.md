# CN Stock Public SuperTrend Pre-Registration Round81 - 2026-06-21

## Purpose

Round81 starts a new public-method family after the RSRS promotion path failed the Round79 costed walk-forward gate and was hibernated in Round80.

This is a pre-registration artifact. It defines what will be tested before any result is seen, so the project does not drift into another broad, after-the-fact parameter search.

Scope:

- Market: CN A-share stocks.
- Asset type: stock.
- Research mode: research-to-review only.
- No broker connection, account read, order placement, or live trading.

## Prior Evidence To Respect

This is not a clean-slate SuperTrend search.

Earlier CN stock evidence already showed that direct public trend-volume continuation was wrong-way or too weak:

- Round7: `supertrend_volume_confirmed_10_3_20` had mean IC -0.0450, total return -78%, and max drawdown -93.47%.
- Round8/Round9: inverse public trend-volume improved IC, but the best focused anti-OBV variant still had overlap-adjusted Sharpe only 0.121.
- Round68: standalone `anti_obv_breakout_low_tail_20` regime focus was rejected; best total return was only 3.43% with overlap-adjusted Sharpe 0.095.

Therefore Round81 must not repeat:

- direct SuperTrend TopN promotion;
- blind topN/rebalance/regime expansion;
- parameter mutation of public trend-volume single factors;
- treating a diagnostic bottom-exclusion overlay as promotion evidence.

## Hypothesis

SuperTrend-style public trend state may still be useful as a risk or exclusion signal because prior trend-volume factors were strongly wrong-way in CN stocks. The testable idea is not "buy the strongest trend names." The testable idea is:

1. The raw SuperTrend side may identify crowded or overextended names that underperform.
2. The inverse side may identify avoidance/risk information.
3. The signal may be more useful as bottom-exclusion or industry/market risk evidence than as a direct long-only alpha.

## Pre-Registered Candidates

| Candidate | Existing Source | Direction | Role | Rationale |
|---|---|---|---|---|
| `supertrend_volume_confirmed_10_3_20` | `public_trend_volume` | raw | direction check only | Prior CN stock evidence was wrong-way; retest only to quantify sign and tail behavior. |
| `anti_supertrend_volume_confirmed_10_3_20` | `public_trend_volume` | inverse | primary diagnostic | If raw trend confirmation is crowded/overextended, inverse ranking may contain risk-avoidance information. |
| `supertrend_volume_capacity_strict_10_3_20` | `public_trend_volume` | raw, capacity constrained | capacity diagnostic | Tests whether the raw signal only failed because it concentrated in weak-liquidity names. |

No new windows are introduced in this pre-registration. The source implementation remains the existing 10/3 SuperTrend-style score with 20-day confirmation/amount features.

## Required Evaluation Order

Round81 must run in this order:

1. Minimal same-parameter diagnostic grid only to generate factor, label, and raw portfolio evidence.
2. IC-to-portfolio gap audit.
3. Industry-neutral IC audit.
4. Bottom-exclusion overlay audit.
5. Only if steps 2-4 show coherent evidence, run a costed bottom-exclusion walk-forward portfolio.

Promotion is blocked unless a candidate survives costed walk-forward with:

- strict train/test separation;
- 10 bps cost and 20 bps market impact or stricter;
- capacity checks;
- overlap-adjusted Sharpe gate;
- max drawdown gate;
- fold stability;
- no final-holdout tuning.

## Round81 Minimal Config

Use:

- `configs/experiment_grid_cn_stock_public_supertrend_round81_20260621.json`

This config is intentionally narrow:

- 3 existing factor names;
- horizon 20;
- execution lag 1;
- rebalance interval 10;
- top100 only as diagnostic portfolio shape;
- cost 10 bps plus 20 bps market impact;
- target gross exposure 0.6;
- precomputed factor matrix enabled.

The config is not a promotion grid. Its purpose is to produce comparable factor/label/leaderboard artifacts for the translation audits.

## Stop-Loss Rule

Hibernate the SuperTrend line immediately if Round81 finds:

- no positive or sign-consistent IC after direction check;
- bottom-exclusion overlay t-stat below 2;
- overlap-adjusted Sharpe remains below 0.5 in any costed walk-forward conversion;
- the only positive result comes from a single fold, a capacity-blind tail, or direct TopN exposure.

## Next Expected Artifact

After running the minimal diagnostic grid, write:

`docs/research/cn_stock_public_supertrend_signal_audit_round81_2026-06-21.md`
