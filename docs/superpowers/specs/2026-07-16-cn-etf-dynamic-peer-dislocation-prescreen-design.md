# CN ETF Dynamic Peer Dislocation Prescreen Design

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_batch`

Branch: `codex/factor-batch-cn-etf-dynamic-peer-dislocation-20260716`

## Objective

Execute exactly one hash-bound prescreen for the preregistered CN ETF factor
`etf_dynamic_peer_residual_dislocation_reversal_5_60`. The implementation must
preserve point-in-time construction, evaluate the frozen five-session primary
horizon and 20-session diagnostic horizon, enforce every statistical,
reference, exposure, capacity, and cost gate, and close the research family
according to the frozen stop policy.

This task is research-to-paper only. It cannot run a portfolio grid,
walk-forward, final holdout, paper signal, broker, account, order, or live path.

## Frozen Inputs

The prescreen accepts no tunable runtime parameters. It is bound to:

- preregistration config SHA-256
  `4811e1497bbfe9688e006dcb7764381c7ea977ddfde79790248f0223996233c6`;
- preregistration result SHA-256
  `2038a32fa9b250a33a76bdca08c204a349a1cdec959fc3c10dbe4b6a4f6440f5`;
- authorization packet SHA-256
  `c645de436c462365c443dd0574b750feb68b3955263b39a316b184862e99f5c9`;
- mapping SHA-256
  `52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63`;
- the source config and source result hashes recorded in the preregistration;
- the three closed-family reference-config hashes recorded in the
  preregistration; and
- the scheduler scope returned by the Quant PM `single_prescreen_only` gate.

Any missing file, changed hash, changed candidate, changed horizon, enabled
downstream boundary, pre-existing claim, or scope mismatch fails before label
construction.

## Factor Construction

The factor implementation is isolated in
`src/quant_robot/factors/etf_dynamic_peer_dislocation.py`. It exposes a pure
pandas calculation over bars, daily eligibility, and the audited mapping. It
does not read files or know about authorization.

For each ETF and date:

1. Calculate simple adjusted-close returns without forward fill.
2. Calculate the eligible ETF market median return, requiring 30 finite assets.
3. Estimate rolling intercept and beta from 120 paired observations ending at
   `t-1`, with a minimum of 80 observations.
4. Calculate date-`t` market-residual innovation using those lagged
   coefficients.
5. Sum five consecutive residual innovations, requiring all five.
6. Join the mapping interval active on the current date and retain only peers
   that are daily eligible with finite five-session residual moves.
7. Require at least three peers and use their ordinary median. Mapping
   similarity is not a factor weight.
8. Calculate raw dislocation as asset residual sum minus peer median residual
   sum.
9. Reindex each asset to the common signal-date calendar. Calculate center and
   MAD from the 60 calendar signal dates ending at `t-1`, requiring 40 finite
   dislocations. This is deliberately not the last 60 finite observations.
10. Emit the negative robust z-score only when `1.4826 * MAD` is finite and
    strictly greater than `1e-12`.

Historical dislocations are constructed with the mapping active on each
historical date. A new mapping interval is never projected backward. Current
factor output requires the asset itself and at least three peers to be daily
eligible.

The same feature pass emits five direct diagnostics without changing the
candidate: lagged `market_beta_120`, `residual_volatility_60`, `momentum_60`,
`short_return_5`, and `log_adv20`.

## Data Boundary

The unlabeled build loads processed CN ETF bars only through 2024-06-28. The
storage reader must receive the analysis end date so later partitions are
skipped before read. Warm-up observations before 2020-01-02 remain available
for lagged beta and robust history, but all emitted evaluation rows are clipped
to the frozen analysis range.

Daily eligibility uses official lifecycle membership, 120 prior observations,
20-session median amount of at least CNY 5 million, stale-price rate at most
5%, and absolute adjusted return at most 20%. No current name, current theme,
or current official peer assignment is used.

## Reference Challenge

The prescreen constructs the complete candidate-and-reference union from the
three frozen closed-family configs. The expected names are derived from those
configs, not from whatever a module happens to return. Every expected name must
exist and have at least one finite overlap with the candidate; missing or
all-null evidence blocks the primary row.

Mean daily Spearman correlation is calculated on same-date cross sections. The
maximum absolute correlation across the complete reference union must be
strictly below 0.85. Direct exposure correlations are reported separately so
the overlapping `momentum_60` name is not silently deduplicated; their maximum
absolute value must also be strictly below 0.85.

## Statistical Evaluation

The shared cross-sectional prescreen remains the authority for Rank IC,
Newey-West significance, Benjamini-Hochberg correction, quintile spread,
monotonicity, top-quintile turnover, yearly consistency, and reference
correlation.

Exactly two candidate-horizon rows enter Benjamini-Hochberg correction:

- horizon 5 is primary and must pass every shared and supplemental gate;
- horizon 20 is diagnostic and only requires non-negative mean Rank IC and
  non-negative gross top-minus-bottom spread.

The diagnostic row cannot rescue the primary row. The factor direction is not
inverted after seeing results.

## Turnover And Cost

For each horizon and valid evaluation date, quintiles are formed with the same
ranking convention used by the shared prescreen. Both top- and bottom-quintile
turnover are calculated as one minus retained-name overlap divided by the
larger of the previous and current set sizes.

Average reported transition turnover excludes the first date. Cost-adjusted
spread includes initial entry conservatively: both sides receive turnover 1.0
on the first date. For one-way cost `c`, the daily net spread is:

`gross_top_minus_bottom - c * (top_turnover + bottom_turnover)`

The report includes 5 bps and 10 bps results. The five-session mean net spread
must be strictly positive at 10 bps.

## Capacity

Capacity is checked separately for every evaluated date and horizon. For the
top quintile, every constituent must have finite positive ADV20. The daily
ADV20 10th percentile must support a CNY 100,000 position at no more than 1%
one-way participation. The primary gate fails if any evaluated date lacks
coverage or support.

The report records evaluated dates, qualifying dates, minimum daily P10 ADV20,
maximum daily participation, and the worst date. This is stricter than a
pooled P10 and intentionally prevents a strong liquid period from hiding an
illiquid date.

## Authorization Sequence

The command has two phases:

1. Preflight validates the frozen config, source/reference hashes, mapping
   contract, authorization packet, scheduler scope, output boundary, and the
   absence of an existing claim. It may build bars, eligibility, factor values,
   references, direct exposures, and ADV20, but it must not construct or read
   forward labels.
2. Execution atomically claims authorization ID
   `6460f4cafced4f39cc963c5e0bbc31fe4ae56d7f976804ae8beebfdd0d262a62`
   immediately before label construction. It then builds only horizons 5 and
   20, summarizes the prescreen, and writes deterministic evidence.

Unit and synthetic end-to-end tests use fixture authorizations and ledgers.
They never touch the real packet or real ledger. The real execution command is
run once and is never used as a reproducibility rerun.

If an exception occurs after the claim, the claim remains consumed. The CLI
writes a compact failure outcome when possible and exits without retrying or
changing the hypothesis.

## Artifacts

The ignored report directory contains:

- a deterministic summary JSON and Markdown report;
- candidate-horizon metrics CSV;
- daily IC, quintile, turnover/cost, and capacity CSV evidence;
- reference and direct-exposure correlation CSV evidence;
- source and authorization hash manifest; and
- an execution outcome JSON that records success or terminal post-claim
  failure.

Wall-clock claim time remains only in the authorization ledger and outcome
metadata. It is excluded from deterministic analytical artifacts.

## Decision And Stop Policy

If the five-session row fails any shared statistical gate, reference gate,
direct-exposure gate, all-date capacity gate, or 10 bps net-spread gate, the
family closes with zero budget. No sign flip, window change, peer change,
eligibility relaxation, threshold relaxation, alternate horizon, parameter
grid, regime rescue, portfolio rescue, or walk-forward rescue is allowed.

If every primary gate passes, the only next direction is data backfill and
quality audit for 2024-H2 through 2025, followed by a new preregistered
walk-forward design. The 2026 final holdout remains sealed in either outcome.
