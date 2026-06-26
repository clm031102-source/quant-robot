# Office Desktop Two-Day Factor Mining Closeout

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock factor mining and validation support
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

The most important result from these two days is not a promoted factor. It is that the project stopped treating short-window or single-family backtests as useful evidence and moved the office desktop into a controlled CN A-share source-construction and validation role.

The work produced 0 promotable factors and 0 paper-ready signals. That is a correct outcome under the stricter process because every candidate route that looked tempting failed either source coverage, style/residual robustness, capacity/tradeability, fold persistence, or anti-overfit gates.

Useful output was instead created in four areas:

- scope correction: office_desktop mines CN stock factors, not ETF rotation signals;
- process correction: three-round reviews, ten-round syncs, startup gates, long-cycle 2015-2025 replay, final-holdout protection, and no short-sample promotion;
- family rotation: repeated failed moneyflow/public-technical/daily-basic/event directions were hibernated instead of blindly extended;
- data-source construction: PIT financial statement coverage was expanded so financial reporting timeliness factors can later be tested on a defensible universe.

## Quantitative Status

| Area | Result |
|---|---:|
| Promotable/live factors | 0 |
| Paper-ready factors | 0 |
| New usable live/manual signals | 0 |
| Financial reporting timeliness aggregate sources after Round289 | 94 |
| Financial reporting timeliness aggregate rows after Round289 | 71,955 |
| Financial reporting timeliness unique symbols after Round289 | 335 / 1,000 |
| Source-ready roots for this family | 0 |
| Candidate generation allowed for this family | false |
| CN bar rows in local manifest | 15,930,072 |
| CN bar symbols in local manifest | 5,774 |
| CN moneyflow rows in local manifest | 14,702,368 |
| CN moneyflow symbols in local manifest | 5,648 |

Round270 source audit started with only 100 unique symbols. By Round289 the aggregate reached 335 unique symbols. The improvement is +235 unique symbols in the June 26 backfill sequence, but the source is still only 33.5% of the required 1,000-symbol gate.

## Work Performed

### 1. Direction And Governance

The project corrected the main direction error:

- ETF rotation is a separate downstream strategy problem.
- This office desktop's current role is CN stock factor research and source validation.
- Tushare CN stock data is useful for CN stock alpha, but it does not directly solve ETF rotation unless translated into ETF-level signals later.

The startup protocol now requires the run to confirm:

- machine and task scope;
- CN stock scope instead of ETF scope;
- candidate plan and family rotation rules;
- long-cycle replay, overfit checks, lookahead checks, overlap-aware statistics, cost/capacity controls, and final-holdout protection.

### 2. Failed Directions Were Audited Instead Of Repeated

Several routes were tested, audited, and hibernated or blocked from blind continuation:

- moneyflow and smart-money variants;
- public technical indicators such as OBV/MFI/Supertrend/MACD/RSI composites;
- Alpha101/Alpha158-style public price-volume references;
- low-turnover and daily-basic reentry paths;
- event/contextual underreaction, forecast, pledge/unlock, dragon-tiger, and index-rebalance variants;
- accounting-quality formula mutations before sufficient PIT coverage.

The useful content here is the blacklist: future runs should not spend more rounds on these families unless a genuinely new orthogonal hypothesis or new source appears.

### 3. Financial Statement PIT Source Construction

The strongest constructive work was the financial reporting timeliness source pipeline:

- Tushare statement endpoint permission was verified.
- Financial statement shard plan and backfill scripts were used instead of ad hoc fetches.
- Stock-basic listing-date filters were applied to avoid pre-listing empty requests.
- Aggregate-overlap preview was added before live endpoint spend.
- Existing symbols are now skipped or split around before backfill.
- Source gates block candidate generation until at least 1,000 unique symbols are available.

Round286-288 review showed:

| Rounds | Net-new symbols | Endpoint requests | Processed rows | Empty requests | Duplicate rows | Aggregate symbols |
|---|---:|---:|---:|---:|---:|---:|
| 286-288 | 14 | 1,689 | 563 | 0 | 0 | 331 |

Round289 added:

| Round | Net-new symbols | Endpoint requests | Processed rows | Empty requests | Duplicate rows | Aggregate symbols |
|---:|---:|---:|---:|---:|---:|---:|
| 289 | 4 | 528 | 180 | 27 | 4 | 335 |

The Round289 scan-ahead behavior is now part of the process: offset10 had only 3 / 5 net-new symbols and was skipped; offset15 had 4 / 5 net-new symbols and was backfilled after splitting around one existing symbol.

## What Was Actually Useful

The useful outputs are infrastructure and decision quality, not alpha claims:

- a repeatable startup gate that prevents ETF/CN-stock scope confusion;
- three-round review records that force direction changes instead of family lock-in;
- a source gate that prevents short-sample financial IC fishing;
- overlap preview and scan-ahead, which reduce wasted Tushare calls;
- pre-listing filters, which reduce false empty-response noise;
- a current coverage baseline of 335 / 1,000 symbols for financial reporting timeliness;
- a documented warning that empty responses and duplicate rows returned in Round289 and must be watched before matrix construction.

## What Is Still Bad

- There is still no deployable profitable factor from this two-day block.
- Financial reporting timeliness cannot be evaluated honestly yet because 335 symbols is below the 1,000-symbol source gate.
- The project still has many historical factor attempts with attractive headline return but poor capacity, residual robustness, or fold persistence.
- Source construction is slow and endpoint-expensive.
- ETF rotation has not yet received a dedicated translation layer from CN stock signals into ETF allocation signals.

## Decision

The correct next step is not to promote anything. Continue financial reporting timeliness source construction until the 1,000-symbol gate clears, while preserving the new controls:

- preview before live requests;
- skip or split around existing symbols;
- scan ahead below 80% net-new ratio;
- record empty responses and duplicate rows;
- deduplicate before factor matrix;
- run three-round review after Rounds289-291;
- sync after the ten-round cadence or user-requested closeout;
- keep final holdout blocked.

If the source reaches 1,000 symbols, the first allowed candidate screen should be a PIT-safe, full-cycle, same-parameter test with industry/style controls, cost/capacity checks, overlap-aware statistics, and multiple-testing accounting. No candidate should be called useful before surviving those gates.
