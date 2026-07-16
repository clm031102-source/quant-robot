# CN ETF Dynamic Co-Movement Peer Readiness Design

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_review`

Branch: `codex/factor-review-cn-etf-dynamic-comovement-20260716`

## Objective

Determine whether lagged ETF return co-movement can provide a point-in-time, sufficiently broad, stable, and non-duplicate peer source for later CN ETF relative-value research.

This stage audits the peer source only. It must not calculate forward returns, factor IC, quantile returns, portfolio performance, walk-forward performance, paper signals, or profitability.

## Alternatives Considered

### Historical official benchmark membership

This is the economically cleanest peer definition, but the current official mapping is first known on 2026-07-16. It cannot support the 2020-2024 analysis window without look-ahead and remains source-blocked.

### Hierarchical or connected-component clustering

Rejected for this stage. Cluster counts, linkage rules, and chaining thresholds add degrees of freedom, group sizes can become unstable, and the project has no established clustering dependency or frozen cluster-selection policy.

### Cointegration or pair-selection tests

Rejected for this stage. Thousands of pairwise hypothesis tests would require a separate multiple-testing protocol and would turn a source-readiness review into a statistical-arbitrage prescreen.

### Lagged market-residual correlation Top-K peers

Selected. Each asset receives a compact directed peer set based on trailing market-residual return correlation. The method has deterministic ties, bounded peer counts, explicit knowledge dates, no forward label, and directly measurable stability and source-level duplication.

## Lifecycle Snapshot Repair

The ETF lifecycle loader currently rejects repeated symbols across legitimate dated `fund_basic` snapshots. The repair must:

1. Continue rejecting duplicate symbols inside one authority snapshot.
2. Allow the same symbol across distinct dated snapshots.
3. Use the latest dated snapshot row for symbols present more than once.
4. Retain older-snapshot symbols absent from later snapshots, preserving delisted ETF history.
5. Continue rejecting duplicate symbols whose source files have no dated snapshot authority.

Official lifecycle fields are used only for stable ETF identity and list/delist boundaries. Current names, benchmark text, themes, and 2026 peer assignments are prohibited.

## Frozen Data Boundary

- Primary market: `CN_ETF`.
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`.
- Analysis start: 2020-01-02.
- Analysis end: 2024-06-28.
- Final holdout start: 2026-01-01.
- The loader must skip later partitions before reading them.
- Price field: positive `adj_close` only.
- The 2026 holdout and current official peer map cannot be read by the source builder.

## Frozen Eligibility Policy

Eligibility is evaluated on the source-through date, never on the mapping-valid date.

- Minimum prior observations: 120.
- Liquidity window: 20 sessions.
- Minimum trailing median amount: CNY 5 million.
- Maximum trailing stale-price rate: 5%.
- Maximum absolute one-session adjusted return: 20%.
- The asset must be inside its official list/delist lifecycle.

The shorter 120-observation history requirement is deliberate. A 252-session requirement would make 80% full-window date coverage mathematically unreachable on data beginning in 2020, while the source itself uses only 120 trailing returns.

## Rebalance And Knowledge Policy

- Rebalance frequency: quarterly.
- Valid dates: first available market session of January, April, July, and October.
- Source-through date: the immediately preceding market session.
- `known_from` equals `valid_from`.
- Every source-through date must be strictly earlier than its valid date.
- An assignment expires on the market session before the next scheduled rebalance, even if the next snapshot fails. Stale mappings are never carried forward.
- The final assignment expires on the analysis end date.

## Frozen Peer Construction

For every scheduled valid date:

1. Select assets eligible on the source-through date.
2. Read the last 121 market sessions ending on the source-through date and calculate at most 120 simple adjusted-close returns without forward filling.
3. Require at least 100 finite asset returns.
4. Calculate the cross-sectional median return per session from the selected universe, requiring at least 30 asset returns.
5. Estimate an intercept and market beta for each asset using at least 80 paired observations.
6. Calculate in-window residual returns using only that frozen window.
7. Calculate pairwise Pearson residual correlation with at least 80 overlapping residual observations.
8. For each asset, sort peers by descending correlation and then ascending `peer_asset_id` for deterministic ties.
9. Keep correlations at least 0.50, retain at most five peers, and accept the asset only when at least three peers survive.

No alternate windows, correlation thresholds, peer counts, clustering transforms, signs, or distance measures may be introduced after observing the real audit result.

## Mapping Contract

Every persisted row contains:

- `asset_id`
- `peer_asset_id`
- `valid_from`
- `valid_to`
- `known_from`
- `source_end_date`
- `similarity`
- `pair_observations`
- `peer_rank`
- `peer_count`
- `mapping_method`
- `source`

The mapping method is `lagged_market_residual_correlation_topk`. Duplicate asset-peer intervals, reversed intervals, source dates on or after valid dates, and overlapping intervals for the same directed edge fail closed.

## Coverage Gate

- Minimum qualifying mapped assets per analysis date: 30.
- Minimum qualifying-date coverage across all 1,085 analysis dates: 80%.
- Warm-up dates remain in the denominator.
- A mapped asset must have three to five peers in its active snapshot.
- Daily coverage counts an asset only when that asset and at least three of its active peers pass the point-in-time eligibility policy on that analysis date. Quarterly source membership alone is not sufficient.
- The coverage artifact reports both the active snapshot population and the smaller daily-usable mapped population so lifecycle exits, liquidity deterioration, stale prices, and extreme-return exclusions cannot be hidden.

## Stability Gate

For assets mapped in consecutive quarterly snapshots:

- Minimum comparable assets per transition: 30.
- Minimum median peer-set Jaccard similarity: 0.25.
- Minimum median prior-peer retention: 0.40.
- Maximum complete peer-set churn rate: 0.40.
- Minimum directed-edge reciprocity rate within each snapshot: 0.30.

Missing transition evidence fails closed. Stability is assessed on peer membership only and never on subsequent returns.

## Source-Duplicate Gate

For each snapshot, construct deterministic five-nearest-neighbor reference edges from source-through-date exposures:

- market beta over the frozen return window;
- 60-session residual volatility;
- 60-session cumulative return;
- 5-session cumulative return;
- log trailing 20-session median amount.

For each reference:

- At least 80% of selected dynamic edges must have usable exposure evidence.
- Dynamic/reference directed-edge overlap must remain below 0.50.
- Missing reference evidence fails closed.

These checks reject a topology that is mainly a repackaging of the closed market-beta, low-volatility, price-rotation, short-horizon reversal, or liquidity families. Current-name themes are descriptive only and cannot clear or fail this gate.

## Result States

### `ready_for_peer_source_preregistration`

Allowed only if leakage, interval, coverage, stability, reciprocity, and every source-duplicate gate pass. This state authorizes writing one compact factor-prescreen preregistration in a later task. It does not authorize factor generation.

### `blocked`

Any failed gate blocks the source. The scheduler keeps budget at zero, records exact blockers, and rotates to a non-price source inventory instead of tuning this method.

## Required Artifacts

- Frozen JSON config.
- Lifecycle snapshot repair and regression tests.
- Pure peer-source construction module.
- Readiness operation and config-validating CLI.
- JSON and Markdown summaries.
- Mapping, snapshot, date-coverage, stability, and duplicate-overlap CSV artifacts under ignored `data/reports/`.
- Durable research report, scheduler decision, and research-index update.

## Safety

Research-to-paper only. Factor generation, forward labels, portfolio grids, walk-forward runs, paper signals, broker connections, account reads, order placement, automatic trading, and profitability claims are all prohibited in this stage.
