# Project Round472 Post-Refresh Replay And Observation Refresh

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: refresh the paper-only post-refresh replay chain after a ready recent-data refresh pack was found locally. This is paper observation only; it does not enable broker connections, account reads, order placement, automatic trading, or live readiness.

## Progress Snapshot

Estimated project completion after this audit: 95%.

This round moved the paper-observation blocker from missing artifact to measured sample insufficiency. Round469 reported `profile_observation_artifact_missing`; Round472 produced a fresh Daily Ops pack, profile observation ledger, and observation sufficiency pack from the ready recent-data refresh window.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / factor_review |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The run stayed inside the research-to-paper boundary.

## Post-Refresh Replay

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\recent_data_refresh\recent_data_refresh_pack.json --report-dir data\reports\round472_post_refresh_replay_20260704 --promotion-review data\reports\promotion_review\promotion_review_packet.json --readiness-board data\reports\pre_api_readiness_board\pre_api_readiness_board.json --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --run-date 2026-07-01 --portfolio-value 100000
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

The blocker is now a sample-size rule, not stale refresh data or missing profile-observation output.

## Daily Ops Evidence

Daily Ops candidate:

| Item | Value |
| --- | --- |
| Case | `CN_ETF_liquidity_10_top1_cost5_reb5` |
| Factor | `liquidity_10` |
| Market | `CN_ETF` |
| Run date | 2026-07-01 |
| Promotion status | `paper_ready` |
| Daily Ops status | `paper_ready` |
| Paper trading allowed | true |
| Signal age | 0 days |
| Observed signal market | `CN_ETF` |
| Advisory tickets | 1 |
| Live boundary allowed | false |

Daily Ops risk snapshot:

| Item | Value |
| --- | ---: |
| Ending equity | 102,739.81 |
| Total return | 2.74% |
| Max equity drawdown | -0.17% |
| Guard events | 0 |
| Execution blocks | 0 |

The only Daily Ops blocking reason remains `manual_live_review_not_enabled`, which is intentional.

## Profile Observation

Fresh profile observation result:

| Item | Value |
| --- | ---: |
| Run date | 2026-07-01 |
| Observation start | 2026-06-08 |
| Observation end | 2026-07-01 |
| Ledger rows | 1 |
| Equity points | 5 |
| Fills observed | 6 |
| Fills required | 20 |
| Stop count | 1 |
| Warning count | 0 |
| Current drawdown | 0.00% |
| Ending equity | 102,739.81 |

Stop reason:

```text
minimum_fills_observed
```

All other stop rules passed: Daily Ops was paper-ready, live boundary disabled, signal fresh, drawdown within policy, no execution blocks, no profile parameter drift, and guard-event ratio was acceptable.

## Observation Sufficiency

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\round472_post_refresh_replay_20260704\post_refresh_replay_pack.json --output-dir data\reports\round472_observation_sufficiency_20260704 --minimum-relaxation-fills 10
```

Result:

| Item | Value |
| --- | ---: |
| Status | `needs_more_observation_data` |
| Observed fills | 6 |
| Required fills | 20 |
| Fill deficit | 14 |
| Observation days | 24 |
| Fill rate per day | 0.25 |
| Estimated total observation days | 80 |
| Additional observation days | 56 |
| Threshold relaxation allowed | false |

Recommended expansion window:

```text
2026-04-13 to 2026-07-01
```

## Expanded Observation Dry Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_expanded_observation_replay.py --observation-sufficiency-pack data\reports\round472_observation_sufficiency_20260704\observation_sufficiency_pack.json --profile-observation-pack data\reports\round472_post_refresh_replay_20260704\profile_observation\profile_observation_pack.json --report-dir data\reports\round472_expanded_observation_replay_dryrun_20260704 --source tushare --market CN_ETF --dry-run
```

Result:

| Item | Value |
| --- | --- |
| Can extend observation window | true |
| Expanded observation cleared | false |
| Status | `expanded_replay_blocked` |
| Dry-run recent refresh status | `ready_to_execute` |
| Window | 2026-04-13 to 2026-07-01 |

The dry run intentionally did not download or refresh data. It confirms the next real execution should refresh the expanded window, then rerun post-refresh replay and observation sufficiency.

## Decision

Continue paper-only observation, but do not claim live readiness.

Allowed next actions:

- run the expanded recent-data refresh for 2026-04-13 to 2026-07-01 on the assigned ETF/paper workstation with data-pipeline permission;
- rerun post-refresh replay after the expanded refresh completes;
- rerun observation sufficiency and paper ops guardrail after the replay;
- keep the current CN ETF candidate as paper-only until the 20-fill policy clears.

Blocked:

- live readiness;
- manual live review enablement;
- broker connection, account reads, order placement, or automatic trading;
- threshold relaxation before at least 10 fills and expanded-window evidence.
