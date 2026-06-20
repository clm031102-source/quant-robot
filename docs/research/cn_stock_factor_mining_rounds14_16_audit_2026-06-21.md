# CN Stock Factor Mining Rounds 14-16 Audit

Date: 2026-06-21

## Scope

This audit covers the required three-round review cycle:

- Round 14: public formula momentum-confirmed variants.
- Round 15: reusable IC-to-portfolio gap audit tooling.
- Round 16: broad TopN / bottom-exclusion probe.

## External Methods Checked

Public references used for direction control:

- Microsoft Qlib: https://github.com/microsoft/qlib
- Quantopian Alphalens: https://github.com/quantopian/alphalens
- 101 Formulaic Alphas paper: https://arxiv.org/abs/1601.00991
- Hudson & Thames MlFinLab: https://github.com/hudson-and-thames/mlfinlab

Process implications for this project:

- Borrow from Alphalens: always separate IC, quantile returns, turnover/capacity, and grouped exposure; do not equate IC with tradable alpha.
- Borrow from Qlib: treat research as a repeatable workflow with recorded artifacts, not one-off manual experiments.
- Borrow from 101 Formulaic Alphas carefully: public formula factors are useful templates, but short-horizon formula IC does not imply a robust long-only CN stock basket.
- Borrow from MlFinLab's philosophy: add bias/overfit filters before claiming progress; meta-labeling or gating should filter a primary signal, not fabricate alpha from noise.

## New Work Produced

New registered factors:

- Round 14:
  - `formula_pv_corr_momentum_confirmed_20_60`
  - `formula_volume_contraction_momentum_confirmed_20_60`

New reusable tooling:

- `src/quant_robot/ops/ic_portfolio_gap_audit.py`
- `scripts/run_ic_portfolio_gap_audit.py`
- JSONL partial-leaderboard support for interrupted long runs.

New configs/reports:

- `configs/experiment_grid_cn_stock_public_formula_price_volume_momentum_confirmed_fast_20260621.json`
- `configs/experiment_grid_cn_stock_public_formula_broad_exclusion_probe_20260621.json`
- `docs/research/cn_stock_public_formula_momentum_confirmed_round14_2026-06-21.md`
- `docs/research/cn_stock_ic_portfolio_gap_audit_round15_2026-06-21.md`
- `docs/research/cn_stock_public_formula_broad_exclusion_round16_2026-06-21.md`

## Results

Factor count:

- New factor names: 2
- New promotable factors: 0
- New research leads: 0 as standalone stock long-only signals
- Reclassified useful signal type: public formula factors remain ranking/exclusion/breadth candidates, not direct buy-list candidates.

Round 14:

- 8 / 8 cases completed.
- 8 / 8 rejected.
- 8 / 8 capacity-limited.
- Promotable: 0.

Round 15:

- Built the gap audit tool.
- Applied it to Round 12 and Round 14.
- Round 12: 12 / 12 strong RankIC cases had IC-to-portfolio gaps.
- Round 14: 8 / 8 strong RankIC cases had IC-to-portfolio gaps.

Round 16:

- 12 / 16 broad-basket cases completed before timeout.
- 12 / 12 completed cases still had strong RankIC.
- 12 / 12 completed cases still failed long-only translation.
- Capacity improved materially: only 1 / 12 completed cases was capacity-limited.
- Promotable: 0.

## Why The Results Are Still Bad

The problem is no longer "we have no signal."

Evidence says:

- RankIC is repeatedly significant.
- Long-short spreads are positive.
- Bottom quantiles are often worse than top quantiles.
- Capacity can be improved by broadening the basket.

But the strategy still fails because:

- The top long-only basket does not beat the broad CN stock benchmark.
- Benchmark beta and market regime dominate the absolute return path.
- Top quantile returns are too small relative to drawdown and cost.
- The signal is more useful for avoiding losers than selecting winners.
- Wider baskets dilute the signal without creating enough positive carry.

## Stop-Loss Decisions

Stop these directions for now:

- More momentum-confirmed variants of the same public formula family.
- More TopN stock-only sweeps for `formula_pv_corr_reversal_20`.
- More TopN stock-only sweeps for `formula_volume_contraction_reversal_20`.
- More formula mining without an explicit portfolio translation hypothesis.

Only continue a stock factor family if one of these is true:

- It passes the IC-to-portfolio gap audit.
- It is used as an ETF/theme breadth input.
- It is used as an exclusion/risk overlay on a separate buy signal.
- It is being tested for beta/sector/size exposure explanation.

## Direction Change

Round 17 must move away from raw CN stock TopN mining.

Priority order:

1. Build a stock-to-ETF/theme breadth bridge using the strong stock ranking/exclusion signals.
2. Add beta/sector/size exposure diagnostics to explain benchmark underperformance.
3. Test public technical indicators such as SuperTrend or smart-money style indicators only after they are tied to a clear ETF/portfolio translation plan.

## Governance

- Three-round review gate: satisfied for Rounds 14-16.
- Last GitHub sync: Round 10.
- Next GitHub sync target: Round 20 unless the user explicitly requests earlier sync.
- Live boundary: still blocked. Research-to-paper only.

## Current Conclusion

Rounds 14-16 produced no profitable factor.

They did produce a sharper process: stop treating strong IC as success, and stop spending compute on stock TopN variants once the gap audit says the family is an exclusion/breadth signal. The next productive route is to translate stock-level signals into ETF/theme rotation evidence, which is closer to the actual project objective.
