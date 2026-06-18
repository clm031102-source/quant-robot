# Long-Cycle Factor Replay Design

## Goal

Build a conservative long-cycle replay and audit layer before more factor mining. The layer must freeze historical candidate parameters, check whether local data really covers enough market cycles, replay or block candidates under unchanged parameters, and classify each candidate as discarded, research-only, validation-ready, or paper-ready. It remains research-only: no broker connection, no account reads, no order placement, and no live trading.

## Scope

In scope:

- CN stock and CN ETF factor research artifacts already produced by this project.
- Historical candidate extraction from existing leaderboard, handoff, and config artifacts.
- Long-cycle coverage checks before any claim that a result is robust across cycles.
- Same-parameter replay using existing backtest/research pipeline code where factor definitions are supported.
- Audit gates for sample length, regime coverage, look-ahead risk, overfit risk, transaction cost, capacity, overlap-adjusted statistics, and strict split boundaries.
- Markdown, JSON, and CSV artifacts under `data/reports/long_cycle_factor_replay`.

Out of scope:

- Live trading readiness.
- Automatic parameter retuning on full history.
- Treating 2026 final holdout as a tuning set.
- Rewriting the whole research framework.

## Design Choice

Use an incremental guardrail design. Keep the existing `experiment_grid`, `walk_forward`, `backtest`, `market_regime_coverage`, and overlap modules. Add a small long-cycle replay module that orchestrates candidate freezing, data coverage, audit decisions, and report output. This avoids breaking existing batch outputs while making the next factor-mining cycle stricter.

## Workflow

1. Build a frozen candidate registry.
   - Read prior candidate rows from known reports and handoff files.
   - Deduplicate by `case_id`.
   - Preserve original `factor_name`, market, topN, holding period, rebalance/schedule, cost, gate, source report, and prior hypothesis count.
   - Mark unsupported custom candidates as `registry_only` until a replay adapter exists.

2. Check long-cycle data coverage.
   - Compute available start/end dates, row counts, asset counts, and market coverage from local bars.
   - Require a configured long-cycle start target, default `2015-01-01` for CN research.
   - Report missing cycle coverage explicitly instead of treating a short local sample as long-cycle evidence.

3. Replay supported candidates with unchanged parameters.
   - Use existing factor/backtest code for supported technical and Tushare-input candidates.
   - Keep all original parameters frozen.
   - Run full available sample plus strict slices: discovery, validation, final holdout, and named large-cycle periods when data covers them.
   - Apply costs, capacity, and overlap-aware return statistics.

4. Audit candidate risk.
   - Look-ahead audit: flag negative shifts, same-day execution, full-period normalization risk, and factor source lag requirements.
   - Overfit audit: use hypothesis count, parameter count, high Sharpe warnings, and short sample warnings.
   - Regime audit: require multiple bull/bear/sideways periods or named cycle coverage before upgrade.
   - Data audit: carry forward manifest warnings such as extreme returns and incomplete moneyflow coverage.

5. Classify candidates.
   - `discard`: negative or fragile full-sample economics, cost/capacity failure, or strong audit blockers.
   - `research_lead`: signal exists but long-cycle coverage or audit evidence is insufficient.
   - `validation_candidate`: frozen candidate survives long-cycle replay and audit gates, but still needs OOS validation.
   - `paper_candidate`: only after OOS and paper gates pass; this design does not promote directly.

## Reporting

The report must include:

- Candidate counts by source and market.
- Data coverage status and blockers.
- Replay status per candidate.
- Decision status per candidate.
- Explicit reason lists, especially when a candidate is blocked because local history is too short.
- No live-trading language beyond the research-only safety statement.

## Acceptance Criteria

- A CLI can create a long-cycle replay packet without reading or writing secrets.
- The packet blocks long-cycle claims when local data starts after the required cycle start.
- Candidate parameters are frozen and visible in the registry.
- Overfit, look-ahead, regime, cost/capacity, and overlap fields are present in candidate decisions.
- Tests cover candidate deduplication, data-coverage blocking, audit classification, and artifact writing.
