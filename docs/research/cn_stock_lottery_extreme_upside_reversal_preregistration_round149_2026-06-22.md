# CN Stock Lottery Extreme Upside Reversal Preregistration Round149

Date: 2026-06-22

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## Rotation Reason

Round148 rejected the event-dividend continuation path. The raw dividend event lead had signal, but it was highly tied to public dividend/value exposure and its long-cycle residual ICIR fell below gate.

Round149 therefore rotates away from event-dividend and registers a new public-anomaly family: lottery demand / extreme upside reversal.

The public thesis is the MAX effect: stocks with extreme recent upside can become lottery-demand or chase-demand crowded and later underperform. For A-shares, the thesis is especially relevant because limit-up style chasing and retail participation can create crowded upside tails. This is only a hypothesis, not profitability evidence.

## Registered Candidates

| Factor | Family | Windows | Fields | Public refs |
|---|---|---|---|---|
| `lottery_max_return_reversal_20` | max-effect reversal | 20 | adj_close, amount | max_effect, lottery_demand, alphalens |
| `lottery_limit_chase_exhaustion_20` | limit-chase exhaustion | 5,20 | adj_close, amount | max_effect, limit_chase, A-share microstructure |
| `lottery_upside_tail_asymmetry_reversal_60` | upside-tail asymmetry | 60 | adj_close, amount | max_effect, idiosyncratic_skew, qlib |
| `lottery_climax_volume_reversal_20` | climax-volume reversal | 5,20 | adj_close, amount | volume_climax, max_effect, pyfolio |
| `lottery_upper_shadow_reversal_20` | failed intraday chase | 20 | adj_close, high, low, amount | candlestick upper shadow, lottery_demand, vectorbt |
| `lottery_gapless_max_reversal_20` | pure close-to-close MAX control | 5,20 | adj_close, amount | max_effect, robustness_control, alphalens |

## Gates

No candidate is allowed to enter a portfolio grid from this preregistration.

Next required gate:

`round150_lottery_extreme_upside_reversal_ic_neutral_prescreen`

Round150 must include:

- long-cycle IC/ICIR and positive-IC rate;
- quantile monotonicity and top-minus-bottom spread;
- industry-neutral IC;
- size/liquidity-neutral IC;
- reference correlation versus reversal, low-vol, residual skew, and prior public technical factors;
- A-share limit-up/limit-down style tradeability audit before any portfolio conversion;
- multiple-testing accounting across all factor x horizon tests.

## Expected Failure Modes

Expected failure modes are part of the preregistration:

- duplicate short-horizon reversal signal;
- low-vol or residual-skew redundancy;
- limit-up buy execution artifact;
- microcap/capacity tail;
- yearly regime instability;
- extreme event path contamination.

## Decision

Round149 is successful as a preregistration round:

- candidates: 6
- blockers: 0
- promotion candidates: 0
- portfolio grid candidates: 0

Proceed to Round150 prescreen. Do not tune these formulas after seeing Round150 results.
