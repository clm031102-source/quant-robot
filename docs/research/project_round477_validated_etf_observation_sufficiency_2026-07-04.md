# Project Round477 Validated ETF Observation Sufficiency

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: rerun the paper-observation sufficiency path after the Round475/Round476 fund-basic rotation-membership repair. This round uses the fund-basic validated ETF target `CN_ETF_XSHE_160615`, not the invalid `CN_ETF_XSHG_501222` target from the pre-repair replay.

## Progress Snapshot

Estimated project completion after this evidence refresh: 97%.

The remaining blocker is now cleanly isolated: the paper lane has valid CN ETF membership and a clean continuous recent-data replay, but still does not meet the 20-fill observation policy.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / factor_review and data_pipeline |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM factor-review gate | `ready` |
| Quant PM data-pipeline gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The run stayed inside the research-to-paper boundary. No broker connection, live account read, order placement, or automatic live trading was enabled.

## Baseline Sufficiency After Round475 Repair

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\round475_post_refresh_replay_fund_basic_membership_20260704\post_refresh_replay_pack.json --output-dir data\reports\round477_observation_sufficiency_validated_etf_20260704 --minimum-relaxation-fills 10
```

Result:

| Item | Value |
| --- | ---: |
| Status | `needs_more_observation_data` |
| Observed fills | 2 |
| Required fills | 20 |
| Fill deficit | 18 |
| Observation days | 9 |
| Fill rate per day | 0.222222 |
| Threshold relaxation allowed | false |
| Suggested window | 2026-04-03 to 2026-07-01 |

## Recommended Window Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\round475_post_refresh_replay_fund_basic_membership_20260704\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\round477_tushare_etf_recent_validated_expanded_20260704 --report-dir data\reports\round477_recent_data_refresh_validated_expanded_20260704 --start-date 2026-04-03 --end-date 2026-07-01 --machine office_desktop --execute
```

Result:

| Item | Value |
| --- | --- |
| Status | `data_quality_blocked` |
| Processed rows | 117,299 |
| Coverage scope | `required_assets` |
| Required asset | `CN_ETF_XSHE_160615` |
| Expected rows | 59 |
| Required asset rows | 58 |
| Missing date | 2026-04-30 |
| Duplicate bars | 0 |
| Zero-volume rows | 0 |
| Rotation membership source | `tushare_fund_basic_fund_daily` |
| Rotation member rows | 60,669 |

This is a valid ETF target and the membership source is fund-basic validated. The strict required-asset gate still blocked the recommended window because `160615.SZ` is missing exactly one provider date, 2026-04-30.

Provider-calendar segments for `CN_ETF_XSHE_160615`:

| Segment | Rows |
| --- | ---: |
| 2026-04-03 to 2026-04-29 | 18 |
| 2026-05-06 to 2026-07-01 | 40 |

The continuous suffix from 2026-05-06 to 2026-07-01 was selected for a clean replay test.

## Continuous Window Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\round475_post_refresh_replay_fund_basic_membership_20260704\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\round477_tushare_etf_recent_validated_continuous_20260704 --report-dir data\reports\round477_recent_data_refresh_validated_continuous_20260704 --start-date 2026-05-06 --end-date 2026-07-01 --machine office_desktop --execute
```

Result:

| Item | Value |
| --- | --- |
| Status | `completed` |
| Recent data ready | true |
| Processed rows | 80,294 |
| Coverage status | `pass` |
| Required asset | `CN_ETF_XSHE_160615` |
| Required asset rows | 40 / 40 |
| Missing date rows | 0 |
| Duplicate bars | 0 |
| Zero-volume rows | 0 |
| Rotation membership source | `tushare_fund_basic_fund_daily` |
| Rotation member rows | 60,669 |

## Post-Refresh Replay

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\round477_recent_data_refresh_validated_continuous_20260704\recent_data_refresh_pack.json --report-dir data\reports\round477_post_refresh_replay_validated_continuous_20260704 --promotion-review data\reports\promotion_review\promotion_review_packet.json --readiness-board data\reports\pre_api_readiness_board\pre_api_readiness_board.json --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --run-date 2026-07-01 --portfolio-value 100000
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

Daily Ops:

| Item | Value |
| --- | --- |
| Candidate | `CN_ETF_liquidity_10_top1_cost5_reb5` |
| Advisory asset | `CN_ETF_XSHE_160615` |
| Paper trading allowed | true |
| Live boundary allowed | false |
| Signal freshness | fresh |
| Market validation | matched |
| Total return | 4.16% |
| Max equity drawdown | -0.80% |
| Guard events | 0 |
| Execution blocks | 0 |

Profile observation:

| Item | Value |
| --- | --- |
| Observed assets | `CN_ETF_XSHE_160615` |
| Observation status | `stopped` |
| Stop reason | `minimum_fills_observed` |
| Warning count | 0 |

## Final Sufficiency

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\round477_post_refresh_replay_validated_continuous_20260704\post_refresh_replay_pack.json --output-dir data\reports\round477_observation_sufficiency_validated_continuous_20260704 --minimum-relaxation-fills 10
```

Result:

| Item | Value |
| --- | ---: |
| Status | `needs_more_observation_data` |
| Observed fills | 5 |
| Required fills | 20 |
| Fill deficit | 15 |
| Observation days | 24 |
| Fill rate per day | 0.208333 |
| Estimated total observation days | 96 |
| Additional observation days | 72 |
| Threshold relaxation allowed | false |

## Decision

The paper lane is now clean but still immature:

- data quality is cleared for a continuous fund-basic validated ETF window;
- the invalid `501222.SH` non-ETF leak is no longer part of the replay;
- Daily Ops remains paper-ready with no execution blocks or guard events;
- profile observation remains blocked by sample size only.

Do not claim observation sufficiency, live readiness, or factor promotion. Continue paper-only observation, or after laptop integration explicitly re-scope the paper lane with the repaired membership evidence. Mainline integration and safe remote branch cleanup remain the highest-value project completion tasks before new profit-factor mining starts.
