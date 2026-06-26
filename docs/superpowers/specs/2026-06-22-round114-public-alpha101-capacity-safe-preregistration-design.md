# Round114 Public Alpha101 Capacity-Safe Preregistration Design

## Goal

Round114 rotates away from the blocked market-residual standalone line and preregisters a small curated set of public formulaic-alpha candidates for CN stock cross-sectional research.

## Context

The Round110-112 review hibernated the market-residual family after one statistical lead showed hard blockers: reference redundancy, high residual-volatility and market-correlation exposure, 2015 failure, and unstable monthly IC. The next direction in the startup gate is `round114_public_alpha101_capacity_safe_preregistration`.

The public references used as hypothesis sources are:

- Zura Kakushadze, "101 Formulaic Alphas", arXiv 1601.00991.
- Microsoft Qlib Alpha158/Alpha360 feature-handler workflow and signal evaluation style.
- Existing project gates for Alphalens-style IC, quantile monotonicity, turnover, cost, capacity, long-cycle replay, walk-forward, regime coverage, and multiple-testing accounting.

## Candidate Design

Create 10 public Alpha101/Qlib-style candidates using only signal-date OHLCV/amount information:

- Intraday close-position reversal.
- Gap fade with amount confirmation.
- Price-volume correlation reversal.
- VWAP proxy reversion.
- Decayed price-rank reversal.
- Amount shock exhaustion.
- Open-to-close pressure fade.
- High-low range compression with liquidity.
- Alpha158-style return/std/position blend.
- Volume rank divergence.

Each candidate must have a unique name, economic rationale, public reference tags, required fields, capacity filters, and a `source_evidence_status` that makes clear preregistration is not empirical proof.

## Gates

Round114 must not allow portfolio construction or promotion. The next required gate is `round115_public_alpha101_ic_quantile_turnover_prescreen`, which must later evaluate:

- 2015-2025 long-cycle signal matrix.
- 5/10/20 day forward labels with execution lag.
- RankIC, ICIR, t-stat, positive IC rate.
- Quantile spread and monotonicity.
- Turnover and overlap-aware diagnostics.
- Capacity participation and extreme-trade flags.
- Redundancy against existing low-vol/reversal, market-residual, trend, gap, and price-volume candidates.

## Safety

No broker connection, no account reads, no order placement, no live trading. Generated data reports remain under ignored `data/reports`. Code, tests, docs, and lightweight summaries are syncable only after explicit commit/push permission.

## Startup Gate Update

After preregistration, update `configs/factor_mining_startup_cn_stock.json` so the next run points to Round115 prescreen and records Round114 as read/registered. Also block direct Alpha101 portfolio-grid use and broad random Alpha101 formula search.
