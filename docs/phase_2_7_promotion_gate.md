# Phase 2.7 Pre-API Promotion Gate

Phase 2.7 adds a local strategy promotion gate before any broker or market-data API work.

It does not connect to brokers, read accounts, place orders, or make live-trading decisions.

## What It Adds

- Reads walk-forward validation output, experiment-grid output, paper-simulation metrics, and optional data-quality/provider-readiness evidence.
- Supports one paper manifest, an explicit list of paper manifests, or a directory tree of `manifest.json` files from future batch paper runs.
- Produces a conservative promotion report for each candidate.
- Deduplicates candidates whose paper-simulation intent signatures are effectively identical, keeping the highest-ranked representative and blocking redundant clones with `duplicate_signal_candidate`.
- Assigns one of four states:
  - `blocked`: evidence fails hard gates such as rejected walk-forward validation, fixture-only data, insufficient out-of-sample trades, excessive drawdown, or duplicate bars.
  - `research_only`: candidate is not blocked but still lacks enough strength or matching paper evidence.
  - `paper_ready`: candidate can continue in local paper workflows, but is not cleared for live trading.
  - `manual_live_review`: reserved for a future state when providers are ready and explicit config allows manual live review.
- Keeps pre-API work honest by preventing high-return, high-drawdown candidates from being treated as deployable.

## Command

Generate per-candidate paper evidence first:

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_batch.py --config configs\paper_batch_cn_etf.json
```

Then run the promotion gate:

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_report.py --config configs\promotion_gate_cn_etf.json
```

Default output:

```text
data/reports/paper_batch_cn_etf/
data/reports/promotion_gate_cn_etf/
```

Output files:

- `paper_batch_summary.csv`
- `paper_batch_summary.json`
- `promotion_report.csv`
- `promotion_report.json`

## Paper Risk Profile Sweep

The paper batch runner can evaluate multiple local risk profiles per accepted walk-forward candidate before writing the final manifest. Each profile can override sizing and guard settings such as `max_asset_weight`, `min_cash_weight`, `max_drawdown_guard`, and `guard_cooldown_periods`.

The batch selects the best completed profile by `profile_rank_by` while preferring profiles whose paper drawdown stays within `profile_max_drawdown`. The selected `risk_profile_id` is written to both `paper_batch_summary.csv` and the candidate manifest request.

Current CN ETF configs include three local profiles:

- `conservative_guard`: 40% max asset weight, 20% cash floor, 10% drawdown guard, 5-period cooldown.
- `balanced_fast_guard`: 50% max asset weight, no cash floor, 10% drawdown guard, 3-period cooldown.
- `balanced_wide_guard`: 50% max asset weight, no cash floor, 12% drawdown guard, 8-period cooldown.

## Default CN ETF Gates

The default config is intentionally conservative:

- minimum out-of-sample trades: `20`;
- minimum out-of-sample Sharpe for paper readiness: `0.5`;
- minimum stability score for paper readiness: `0.3`;
- minimum out-of-sample relative return: `0`;
- maximum out-of-sample drawdown: `25%`;
- minimum paper-simulation Sharpe: `0.5`;
- maximum paper-simulation drawdown: `25%`;
- duplicate paper-intent similarity threshold: `98%`;
- fixture data cannot be promoted.

## Paper Evidence Matching

The promotion gate matches paper evidence to candidates by market, factor name, `top_n`, and rebalance interval parsed from the candidate `case_id` such as `_reb5` or `_reb10`. This prevents a paper run for a 5-day rebalance strategy from being reused for a 10-day rebalance strategy.

Configs can use:

```json
{
  "paper_manifest": "data/reports/paper_simulation_cn_etf_low_turnover/manifest.json",
  "paper_manifests": [
    "data/reports/paper_batch/case_a/manifest.json",
    "data/reports/paper_batch/case_b/manifest.json"
  ],
  "paper_manifest_dir": "data/reports/paper_batch"
}
```

When `paper_manifest_dir` is set, every nested `manifest.json` is loaded. A later batch paper runner can write one folder per candidate and the promotion gate will consume the full evidence set without API access.

## Candidate Deduplication

When matching paper artifacts include sibling `intents.csv` files, the gate builds a signature from `signal_date`, `execution_date`, `asset_id`, and `side`. Non-blocked candidates with at least three intent events are compared by Jaccard similarity. If a later candidate is at least `98%` similar to an earlier stronger candidate, it is marked `blocked` with `duplicate_signal_candidate`, `duplicate_of`, and `duplicate_similarity`.

This keeps parameter sweeps from filling the top of the report with the same trade list under several factor window names.

## Current Interpretation

After adding batch paper evidence and risk-profile sweep, the current CN ETF low-turnover set promotes one canonical candidate to `paper_ready`: `CN_ETF_liquidity_20_top1_cost5_reb5`. In the expanded candidate search, equivalent liquidity-window variants are blocked as duplicate signal candidates, leaving `CN_ETF_liquidity_10_top1_cost5_reb5` as the canonical `paper_ready` representative.

The selected profile is `balanced_fast_guard`, with paper Sharpe above `0.5` and paper drawdown below the `25%` limit. This is still pre-API evidence only: high headline return is not enough, and duplicated trade lists are not treated as multiple independent opportunities.

## API Boundary

This gate is a local evidence layer. Future broker/API code should consume this report and refuse to progress candidates that are not at least `paper_ready`. Even `paper_ready` is not a live signal; it only means the candidate deserves more paper-running evidence.
