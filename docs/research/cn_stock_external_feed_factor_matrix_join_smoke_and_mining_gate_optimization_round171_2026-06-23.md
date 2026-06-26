# CN Stock External Feed Join Smoke And Mining Gate Optimization Round171

Date: 2026-06-23

Scope: CN stock cross-sectional factor mining on office desktop. This round optimizes the pre-mining process before continuing factor discovery.

## Why This Round Exists

The current mining process had three practical risks:

- External regime feeds were ingested but not yet proven safe for factor-matrix joins.
- Interaction seeds such as northbound stock holding plus aggregate northbound flow needed primary and secondary feed PIT alignment.
- Candidate generation still allowed economically described but source-anonymous ideas, which can drift back into blind parameter mining.

## Code Optimizations

- Added secondary-feed support to `external_feed_factor_matrix_join_smoke`.
- Required primary and secondary feeds to join only when `available_date <= signal_date`.
- Counted raw-date same-day/future violations across both feed layers.
- Allowed required seed columns such as `north_money` to resolve from `secondary_feed`.
- Added candidate-plan gate blocker `candidate_missing_hypothesis_source`.
- Added startup-gate protocol items:
  - `candidate_hypothesis_source_required_before_generation`
  - `candidate_hypothesis_source_declared`
- Updated the quality gate to mark external regime data controls as partial, not planned:
  - `policy_liquidity_regime`
  - `credit_cycle_proxy`
  - `northbound_margin_turnover_temperature`

## Round171 Live Join Smoke

Command:

```powershell
python scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round170_smoke_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round171_external_feed_factor_matrix_join_smoke_20260623
```

Summary:

- Seed count: 6
- Pass: 0
- Insufficient history: 6
- Warn: 0
- Fail: 0
- Joined rows: 49,466
- `available_date` violations: 0
- Raw same-day/future date violations: 0

Notable seed result:

- `northbound_hold_accumulation_flow_regime_20` resolved `north_money` from `external_hsgt_flow`, joined 3,325 stock rows on one available signal date, and had 0 PIT/raw-date violations.

## Interpretation

This is useful infrastructure evidence, not profitability evidence.

The external feed chain is now safer to use for factor-matrix construction, but the sample is only 1-5 observation dates. All six seeds remain `insufficient_history`, so no IC, portfolio, walk-forward, or promotion claim is allowed from this round.

## Next Direction

Round172 should not start a portfolio grid. It should run a long-cycle external feed backfill and coverage plan:

- Backfill enough history for margin, northbound holding, aggregate northbound flow, index state, and SHIBOR.
- Re-run the same join-smoke over the long-cycle processed root.
- Fail if required feeds have coverage gaps, PIT violations, raw same-day joins, or missing secondary-feed columns.
- Only after coverage is adequate should the project run IC/quantile/turnover prescreen, neutralization, redundancy, regime coverage, cost/capacity, and walk-forward tests.

## Current Blockers

- No long-cycle external-feed processed root yet.
- LPR coverage remains unavailable or rate-limited and is excluded.
- No IC evidence.
- No portfolio evidence.
- No cost/capacity evidence.
- No redundancy, regime-stress, or event-contamination audit for external-feed factors.

