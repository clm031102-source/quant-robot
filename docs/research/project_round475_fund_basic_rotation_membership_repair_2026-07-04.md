# Project Round475 Fund-Basic Rotation Membership Repair

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: close the Round473 required-asset data-quality investigation by checking whether `CN_ETF_XSHG_501222` is a valid ETF paper-observation asset, repairing the recent-refresh rotation membership generator, and rerunning the paper-only post-refresh replay with fund-basic validated membership.

## Progress Snapshot

Estimated project completion after this repair: 96%.

This round reduced the remaining blocker from an ambiguous ETF data gap to a specific universe-boundary defect: the recent-refresh replay membership had treated every Tushare `fund_daily` row as a CN ETF rotation member. That allowed an exchange-traded LOF/FOF fund, `501222.SH`, to enter the paper-observation chain.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / data_pipeline and factor_review |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM data-pipeline gate | `ready` |
| Quant PM factor-review gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The work stayed inside the research-to-paper boundary: no broker connection, no account reads, no order placement, and no automatic live trading.

## Root Cause

Tushare `fund_basic` evidence:

| Symbol | Name | Market | Status | Fund Type | Invest Type | Listed | `is_etf` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `501222.SH` | 易方达如意招享混合(FOF-LOF)-A | E | L | 混合型 | 混合型 | 2023-02-01 | false |
| `160615.SZ` | 鹏华沪深300ETF联接(LOF)-A | E | L | 股票型 | 被动指数型 | 2009-05-08 | true |

Additional provider checks:

- `fund_daily(ts_code=501222.SH, 2026-04-13 to 2026-07-01)` returned 37 rows, matching the processed bars.
- The same 17 Round473 missing dates were absent from the direct `ts_code` query.
- `suspend_d` had no `501222` hits for the 17 missing dates.
- Raw full-market fund_daily partitions had rows on all 17 missing dates, but no `501222.SH` row.

Conclusion: `501222.SH` should not have been a CN ETF paper-observation target. It is not an ETF according to the project’s fund-basic mapping, so the main issue was recent-refresh membership construction, not a tradable ETF data gap.

## Code Repair

Changed:

- `scripts/run_recent_data_refresh.py`
- `tests/unit/test_recent_data_refresh_cli.py`

The recent-refresh membership writer now uses Tushare `fund_basic` when source is live `tushare`, then delegates to the formal `build_cn_etf_rotation_membership` logic from `quant_robot.ops.tushare_cn_etf_sync`. This keeps the fast recent-refresh path aligned with the canonical CN ETF universe boundary.

The fixture fallback remains available for fixture tests, but live Tushare recent refreshes now write membership with source:

```text
tushare_fund_basic_fund_daily
```

Regression test added:

```text
test_fund_basic_rotation_membership_excludes_lof_from_recent_refresh
```

This test reproduces the failure mode with one ETF and one LOF. It fails before the repair because live recent refresh membership does not load `fund_basic`; it passes after the repair because the LOF receives `not_etf` and `is_rotation_member=false`.

## Local Membership Repair Evidence

After applying the code repair, the local recent data roots were rebuilt with fund-basic validated membership.

Ready recent-data root:

| Item | Value |
| --- | ---: |
| Root | `data\processed\tushare_etf_recent` |
| Membership rows | 54,553 |
| Member rows | 12,376 |
| Assets | 2,064 |
| Member assets | 1,559 |
| Fund-basic rows | 2,857 |
| Excluded rows | 42,177 |
| Source | `tushare_fund_basic_fund_daily` |

Round473 expanded root:

| Item | Value |
| --- | ---: |
| Root | `data\processed\round473_tushare_etf_recent_expanded_20260704` |
| Membership rows | 107,598 |
| Member rows | 53,200 |
| Assets | 2,065 |
| Member assets | 1,560 |
| Fund-basic rows | 2,857 |
| Excluded rows | 54,398 |
| Source | `tushare_fund_basic_fund_daily` |

Target checks:

| Asset | Rows | Member Rows | Latest Reason |
| --- | ---: | ---: | --- |
| `CN_ETF_XSHG_501222` in ready root | 17 | 0 | `not_etf;insufficient_history_rows` |
| `CN_ETF_XSHG_501222` in expanded root | 37 | 0 | `not_etf` |
| `CN_ETF_XSHE_160615` in ready root | 27 | 8 | member on latest dates |

## Post-Repair Replay

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\recent_data_refresh\recent_data_refresh_pack.json --report-dir data\reports\round475_post_refresh_replay_fund_basic_membership_20260704 --promotion-review data\reports\promotion_review\promotion_review_packet.json --readiness-board data\reports\pre_api_readiness_board\pre_api_readiness_board.json --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --run-date 2026-07-01 --portfolio-value 100000
```

Result:

| Item | Value |
| --- | --- |
| Stage | `phase_5_8_post_refresh_replay` |
| Status | `replay_blocked` |
| Recent data ready | true |
| Daily Ops paper allowed | true |
| Profile observation allowed | false |
| Blocker | `minimum_fills_observed` |
| Observed asset after repair | `CN_ETF_XSHE_160615` |
| Previous invalid observed asset | `CN_ETF_XSHG_501222` |

Daily Ops after repair:

| Item | Value |
| --- | --- |
| Candidate | `CN_ETF_liquidity_10_top1_cost5_reb5` |
| Status | `paper_ready` |
| Paper trading allowed | true |
| Live boundary allowed | false |
| Advisory asset | `CN_ETF_XSHE_160615` |
| Signal date | 2026-07-01 |
| Signal age | 0 days |
| Market validation | matched |
| Total return | 1.00% |
| Max equity drawdown | -0.06% |
| Guard events | 0 |
| Execution blocks | 0 |

Profile observation after repair:

| Item | Value |
| --- | --- |
| Observed assets | `CN_ETF_XSHE_160615` |
| Observation status | `stopped` |
| Stop reason | `minimum_fills_observed` |
| Warning count | 0 |

## Decision

The Round473 data-quality block is resolved as a universe-boundary bug, not as a missing ETF backfill requirement. Do not backfill or forward-fill `501222.SH`; exclude it from CN ETF rotation membership through fund-basic validation.

The current paper candidate remains paper-only. It is cleaner after the repair because the observed asset is now fund-basic validated, but it still has insufficient observation fills and no live-readiness claim.

Allowed next actions:

- keep laptop `project_sync` / mainline integration as the highest-priority project completion step;
- after integration, rerun paper observation sufficiency from the fund-basic validated replay pack;
- start new profit-factor mining only after main is stable and the scheduler opens a pre-registered, orthogonal research direction.

Blocked:

- treating `501222.SH` as a CN ETF target;
- live readiness;
- broker connection, account reads, order placement, or automatic trading.
