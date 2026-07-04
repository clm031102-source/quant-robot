# Project Round478 Latest Validated ETF Observation Update

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: extend the repaired fund-basic validated CN ETF paper replay to the latest clean Tushare date available for the observed ETF target, without crossing the research-to-paper boundary.

## Progress Snapshot

Estimated project completion after this refresh: 97%.

The project is now blocked by integration and observation maturity, not by the earlier CN ETF membership leak. The current office-desktop branch contains the repaired membership gate, the live fund-basic fail-closed guard, and the latest validated ETF observation evidence. Mainline merge and remote branch cleanup remain laptop-owned tasks.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / data_pipeline |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM startup gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The run stayed inside the research-to-paper boundary. No broker connection, live account read, order placement, or automatic live trading was enabled.

## Latest Available Target Date Check

The observed fund-basic validated ETF remains `CN_ETF_XSHE_160615`.

Tushare calendar and target availability were checked before the refresh:

| Date | Calendar status | `160615.SZ` fund_daily row |
| --- | --- | --- |
| 2026-07-01 | open | present |
| 2026-07-02 | open | present |
| 2026-07-03 | open | missing |
| 2026-07-04 | no row expected | missing |

The latest clean target date is therefore 2026-07-02. The refresh intentionally did not use 2026-07-03 because that would introduce a required-asset coverage gap for the observed ETF.

## Latest Continuous Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\round477_post_refresh_replay_validated_continuous_20260704\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\round478_tushare_etf_recent_validated_latest_20260704 --report-dir data\reports\round478_recent_data_refresh_validated_latest_20260704 --start-date 2026-05-06 --end-date 2026-07-02 --machine office_desktop --execute
```

Result:

| Item | Value |
| --- | --- |
| Status | `completed` |
| Recent data ready | true |
| Target window | 2026-05-06 to 2026-07-02 |
| Processed rows | 82,333 |
| Coverage status | `pass` |
| Expected trade dates | 41 |
| Provider missing date rows | 676 |
| Required asset | `CN_ETF_XSHE_160615` |
| Required asset rows | 41 / 41 |
| Required asset missing rows | 0 |
| Duplicate bars | 0 |
| Zero-volume rows | 0 |
| Rotation membership source | `tushare_fund_basic_fund_daily` |
| Rotation fund_basic rows | 2,857 |
| Rotation member assets | 1,559 |
| Rotation member rows | 33,758 |

## Post-Refresh Replay

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\round478_recent_data_refresh_validated_latest_20260704\recent_data_refresh_pack.json --report-dir data\reports\round478_post_refresh_replay_validated_latest_20260704 --promotion-review data\reports\promotion_review\promotion_review_packet.json --readiness-board data\reports\pre_api_readiness_board\pre_api_readiness_board.json --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --run-date 2026-07-02 --portfolio-value 100000
```

Result:

| Item | Value |
| --- | --- |
| Status | `replay_blocked` |
| Daily Ops decision | `paper_ready` |
| Daily Ops paper allowed | true |
| Live boundary allowed | false |
| Profile observation allowed | false |
| Profile observation blocker | `minimum_fills_observed` |
| Observed asset | `CN_ETF_XSHE_160615` |

Daily Ops:

| Item | Value |
| --- | --- |
| Candidate | `CN_ETF_liquidity_10_top1_cost5_reb5` |
| Signal date | 2026-07-02 |
| Signal age | 0 days |
| Signal freshness | fresh |
| Market validation | matched |
| Target count | 1 |
| Cash weight | 40% |
| Target gross exposure | 60% |
| Total return | 4.16% |
| Max equity drawdown | -0.80% |
| Guard events | 0 |
| Execution blocks | 0 |
| Simulation fills | 5 |

Profile observation:

| Item | Value |
| --- | --- |
| Observation status | `stopped` |
| Stop reason | `minimum_fills_observed` |
| Observation window | 2026-06-03 to 2026-06-26 |
| Equity points | 5 |
| Warning count | 0 |

## Sufficiency Recheck

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\round478_post_refresh_replay_validated_latest_20260704\post_refresh_replay_pack.json --output-dir data\reports\round478_observation_sufficiency_validated_latest_20260704 --minimum-relaxation-fills 10
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

The latest clean Tushare extension did not increase the observed fill count. The paper lane remains valid and cleaner than the pre-repair replay, but it is still sample-size blocked at 5 / 20 fills.

Do not claim observation sufficiency, live readiness, or factor promotion. Do not use 2026-07-03 for this observed ETF until `160615.SZ` has a valid provider row or the paper lane is explicitly re-scoped. The highest-value remaining project work is laptop integration into `main`, safe remote branch cleanup, and continued paper-only observation after the integration branch is stable.
