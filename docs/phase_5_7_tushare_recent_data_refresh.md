# Phase 5.7 Tushare Recent Data Refresh

This phase turns the Phase 5.6 `signal_data_stale` stop into a controlled recent-data refresh gate.

It does not connect to a broker, read an account, or place orders. It only decides whether recent CN ETF market data can be refreshed safely, whether the refreshed data covers the target window, and whether Daily Ops may be rerun on refreshed bars.

## Command

Dry-run, no download:

```powershell
python scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\tushare_etf_recent --report-dir data\reports\recent_data_refresh
```

Execute after Tushare readiness is clear:

```powershell
python scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\profile_observation\profile_observation_pack.json --source tushare --market CN_ETF --output-dir data\processed\tushare_etf_recent --report-dir data\reports\recent_data_refresh --execute
```

Outputs:

- `data/reports/recent_data_refresh/recent_data_refresh_pack.json`
- `data/reports/recent_data_refresh/recent_data_refresh_pack.md`
- `data/reports/recent_data_refresh/recent_data_refresh_coverage.csv`
- `data/reports/recent_data_refresh/recent_data_refresh_next_actions.csv`

Fixture execute rehearsal, no real Tushare token:

```powershell
python scripts\run_recent_data_refresh.py --profile-observation-pack data\reports\profile_observation\profile_observation_pack.json --source tushare-fixture --market CN_ETF --output-dir data\processed\tushare_etf_recent_fixture --report-dir data\reports\recent_data_refresh_fixture --execute
```

Fixture outputs:

- `data/reports/recent_data_refresh_fixture/recent_data_refresh_pack.json`
- `data/reports/recent_data_refresh_fixture/recent_data_refresh_pack.md`
- `data/reports/recent_data_refresh_fixture/recent_data_refresh_coverage.csv`
- `data/reports/recent_data_refresh_fixture/recent_data_refresh_next_actions.csv`
- `data/processed/tushare_etf_recent_fixture`

## GUI/API Surface

The local GUI exposes this phase as a read-only status gate:

- API: `/api/data/recent-refresh`
- default pack: `data/reports/recent_data_refresh/recent_data_refresh_pack.json`
- Daily Ops panel input: `Recent refresh pack`
- dashboard metric: `Recent Data`

The GUI does not execute downloads. It only displays whether the latest refresh artifact clears `signal_data_stale`, the target window, coverage status, blockers, and next actions.

## Current Real Tushare Result

- stage: `phase_5_7_tushare_recent_data_refresh`
- status: `completed`
- mode: `execute`
- source: `tushare`
- market: `CN_ETF`
- target window: `2026-05-23` to `2026-06-14`
- effective trading window: `2026-05-25` to `2026-06-12`
- coverage scope: `required_assets`
- required asset: `CN_ETF_XSHG_516160`
- processed rows: `30106`
- provider missing date rows: `226`
- scoped missing date rows: `0`
- duplicate bars: `0`
- zero-volume rows: `0`
- signal data stale cleared: `true`
- next daily ops allowed: `true`
- live boundary allowed: `false`

The provider-level missing rows remain visible as a warning for universe-level data quality. They do not block this paper gate when the observed advisory asset fully covers the adjusted trading window.

## Fixture Execute Result

The fixture execute rehearsal completed the execution path without using a real token:

- stage: `phase_5_7_tushare_recent_data_refresh`
- status: `completed`
- mode: `execute`
- source: `tushare-fixture`
- market: `CN_ETF`
- target window: `2026-05-23` to `2026-06-14`
- processed rows: `46`
- latest data date: `2026-06-14`
- missing date rows: `0`
- duplicate bars: `0`
- zero-volume rows: `0`
- signal data stale cleared: `true`
- next daily ops allowed: `true`
- live boundary allowed: `false`

## Token Handling

Do not paste the token into commands that are logged.

Set it as a local environment variable before execute mode:

```powershell
setx TUSHARE_TOKEN <your-token>
```

Then open a new PowerShell session so the environment variable is visible, and rerun the execute command above.

## Completion Criteria

Phase 5.7 clears the `signal_data_stale` blocker only if:

- the target window starts after the stale signal date;
- the latest refreshed data reaches the observation run date, adjusted to the nearest available Tushare trade-calendar endpoint when the ingest result includes trade dates, with weekend adjustment as a fallback;
- processed rows are greater than zero;
- missing date rows are zero for the decision scope;
- duplicate bars are zero;
- zero-volume rows are zero.

When Profile Observation provides `observed_assets`, the decision scope is those required assets. Full-provider missing date rows are still recorded as `provider_missing_date_rows`. Required assets must cover the effective start/end dates and have at least the expected number of trade-date rows for that effective window.

If the refresh completes, the next local steps are:

```powershell
python scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\recent_data_refresh\recent_data_refresh_pack.json --report-dir data\reports\post_refresh_replay
```

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase only permits rerunning paper observation on fresher data. It is not permission to trade live.
