# Project Round473 Expanded Observation Data Quality Block

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: execute the expanded CN ETF recent-data refresh recommended by Round472, then stop or replay according to the existing paper-only gates. This round stayed inside the research-to-paper boundary: no broker connection, no account reads, no order placement, no automatic trading, and no live-readiness enablement.

## Progress Snapshot

Estimated project completion after this audit: 95%.

Round472 cleared the missing-artifact blocker and showed 6 / 20 required fills. Round473 executed the recommended expanded observation refresh window, but the data-quality gate correctly blocked it because the observed required asset did not have continuous provider bars through the target window.

This is now a data/asset coverage blocker, not a code execution blocker.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task for refresh | office_desktop / data_pipeline |
| Machine/task for replay gate | office_desktop / factor_review |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM data-pipeline gate | `ready` |
| Quant PM factor-review gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The refresh was allowed on office_desktop by `configs/workstations.json`, and the Quant PM startup gate reread the required protocol files before the ETF-affecting data work.

## Expanded Recent-Data Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\round472_post_refresh_replay_20260704\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\round473_tushare_etf_recent_expanded_20260704 --report-dir data\reports\round473_recent_data_refresh_expanded_20260704 --start-date 2026-04-13 --end-date 2026-07-01 --machine office_desktop --execute
```

Result:

| Item | Value |
| --- | --- |
| Stage | `phase_5_7_tushare_recent_data_refresh` |
| Status | `data_quality_blocked` |
| Mode | `execute` |
| Source / market | `tushare` / `CN_ETF` |
| Target window | 2026-04-13 to 2026-07-01 |
| Processed rows | 107,598 |
| Assets | 2,065 |
| Provider trade dates | 54 |
| Coverage scope | `required_assets` |
| Coverage status | `fail` |
| Required asset | `CN_ETF_XSHG_501222` |
| Required asset rows | 37 / 54 expected |
| Required asset missing rows | 17 |
| Provider missing date rows | 904 |
| Duplicate bars | 0 |
| Zero-volume rows | 0 |
| Decision blockers | `required_assets_not_covered`, `target_start_not_covered`, `missing_date_rows` |

The gate did not fail because of duplicate rows, zero-volume rows, or Tushare readiness. It failed because the current observed asset itself does not cover the required expanded window.

## Root Cause Evidence

Processed bars loaded from `data\processed\round473_tushare_etf_recent_expanded_20260704`:

| Item | Value |
| --- | --- |
| Total loaded rows | 107,598 |
| Unique assets | 2,065 |
| Provider dates | 54 |
| Provider date range | 2026-04-13 to 2026-07-01 |
| `CN_ETF_XSHG_501222` rows | 37 |
| `CN_ETF_XSHG_501222` date range | 2026-04-15 to 2026-07-01 |
| Missing dates for required asset | 17 |

Missing required-asset dates:

```text
2026-04-13, 2026-04-14, 2026-04-17, 2026-04-22, 2026-04-23,
2026-04-24, 2026-05-11, 2026-05-26, 2026-06-01, 2026-06-02,
2026-06-03, 2026-06-08, 2026-06-09, 2026-06-15, 2026-06-16,
2026-06-17, 2026-06-29
```

Contiguous provider-calendar segments for `CN_ETF_XSHG_501222`:

| Segment | Provider rows |
| --- | ---: |
| 2026-04-15 to 2026-04-16 | 2 |
| 2026-04-20 to 2026-04-21 | 2 |
| 2026-04-27 to 2026-05-08 | 7 |
| 2026-05-12 to 2026-05-25 | 10 |
| 2026-05-27 to 2026-05-29 | 3 |
| 2026-06-04 to 2026-06-05 | 2 |
| 2026-06-10 to 2026-06-12 | 3 |
| 2026-06-18 to 2026-06-26 | 6 |
| 2026-06-30 to 2026-07-01 | 2 |

The longest complete suffix ending at 2026-07-01 contains only 2 provider dates. Therefore, rerunning the refresh with a narrower complete window would not satisfy the 20-fill observation policy.

Raw Tushare parquet partitions were also inspected for every missing date. Each missing date had full-market raw rows present, but the target symbol `501222.SH` was absent:

| Check | Value |
| --- | ---: |
| Missing dates inspected | 17 |
| Dates with peer raw rows present | 17 |
| Dates where `501222.SH` raw row was found | 0 |
| Raw rows per inspected date | 1,940 to 2,035 |

Root-cause hypothesis confirmed: the blocker is caused by required-asset provider coverage gaps for `CN_ETF_XSHG_501222`, not by a script window bug or a failed all-market download.

## Post-Refresh Replay Stop

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\round473_recent_data_refresh_expanded_20260704\recent_data_refresh_pack.json --report-dir data\reports\round473_post_refresh_replay_blocked_20260704 --promotion-review data\reports\promotion_review\promotion_review_packet.json --readiness-board data\reports\pre_api_readiness_board\pre_api_readiness_board.json --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --run-date 2026-07-01 --portfolio-value 100000
```

Result:

| Item | Value |
| --- | --- |
| Stage | `phase_5_8_post_refresh_replay` |
| Status | `blocked` |
| Recent data ready | false |
| Post-refresh replay allowed | false |
| Daily Ops paper allowed | false |
| Profile observation allowed | false |
| Blockers | `required_assets_not_covered`, `target_start_not_covered`, `missing_date_rows` |

Because the recent-data refresh was not ready, the replay correctly stopped before new Daily Ops signal generation or profile observation.

## Decision

Do not claim live readiness or paper-observation sufficiency for this expanded window.

Do not bypass the required-asset coverage gate by forward-filling missing rows, ignoring the observed asset, relaxing the 20-fill rule, or treating all-market provider coverage as enough. The current evidence says the active observed asset does not have a complete enough provider trail for the expanded replay.

Allowed next actions:

- verify whether `501222.SH` had exchange suspension/no-trade days or a provider-specific fund-daily omission on the 17 missing dates;
- continue waiting for real paper observations if the asset remains the active paper candidate;
- choose a replacement paper-observation asset/profile only through a pre-registered paper workflow, not by retrofitting this blocked replay;
- hand this branch to the laptop integration workflow after review, while keeping generated `data\processed` and `data\reports` artifacts out of Git.

Blocked:

- live readiness;
- manual live-review enablement;
- broker connection, account reads, order placement, or automatic trading;
- threshold relaxation before valid expanded-window evidence exists.
