# CN Stock Round220 Industry Leader-Lag Sharded Full Prescreen

Date: 2026-06-24

Scope: CN A-share stock cross-sectional factor research. This is a residual IC, yearly stability, reference-dedup, and exposure prescreen. It is not ETF rotation, not a portfolio backtest, not a promotion memo, and not live trading.

## Engineering Fix

Round220 previously had a short-window smoke and a sharded entrypoint, but the first sharded implementation still concatenated all yearly factor, reference, exposure, and label matrices before summary. That was not suitable for sustained 2015-2025 mining.

This round changed the sharded path to streaming aggregation:

- yearly shards still use lookback and forward padding for features and labels;
- padding rows are removed before signal IC;
- per-shard matrices are reduced to IC observations, reference-correlation observations, exposure-correlation observations, and industry-coverage observations;
- final summary aggregates those observations without retaining the full cross-year matrices;
- `sharding_policy.streaming_summary` is now true.

Verification:

- `python -m unittest tests.unit.test_industry_leader_lag_residual_prescreen.IndustryLeaderLagResidualPrescreenTests.test_sharded_prescreen_uses_padding_but_keeps_signal_dates_inside_analysis_window tests.unit.test_industry_leader_lag_residual_prescreen_cli.IndustryLeaderLagResidualPrescreenCliTests.test_cli_wrapper_supports_sharded_long_cycle_mode`
- `python -m py_compile src\quant_robot\ops\industry_leader_lag_residual_prescreen.py scripts\run_industry_leader_lag_residual_prescreen.py`
- `python -m unittest tests.unit.test_industry_leader_lag_factors tests.unit.test_industry_leader_lag_residual_prescreen tests.unit.test_industry_leader_lag_residual_prescreen_cli tests.unit.test_market_residual_lead_exposure_dedup tests.unit.test_public_reference_multi_family_prescreen tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_startup_gate`

Result: 59 related tests passed. `git diff --check` on the touched Round220 files passed.

## Full-Sample Run

Artifact:

`data/reports/industry_leader_lag_residual_prescreen_round220_sharded_full_all_20260624/`

Run shape:

`python scripts/run_industry_leader_lag_residual_prescreen.py --sharded --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --sample-every-n-dates 20 --min-cross-section 30 --min-ic-observations 50 --min-industries 2 --min-assets-per-industry 2`

Data footprint:

- Asset count: 5,707
- Bar rows: 10,785,537
- Factor rows: 58,217,687
- Industry-neutral rows: 58,214,654
- Residual rows: 58,079,458
- Label rows: 10,777,095
- Reference factor rows: 60,387,667
- Reference factor count: 9

## Result

All six Round220 candidates were rejected at the residual prescreen gate.

| Factor | Raw IC | Neutral IC | Residual IC | Residual ICIR | Residual t | IC+ | Year Failures | Ref High | Exposure High | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `industry_leader_pullback_resilience_10_5` | 0.0082 | 0.0354 | 0.0262 | 0.374 | 19.28 | 66.45% | 0 | 0 | 0 | reject: raw yearly instability |
| `industry_leader_volume_confirmed_diffusion_5_20` | 0.0355 | 0.0378 | 0.0196 | 0.266 | 13.68 | 60.27% | 0 | 0 | 0 | reject: residual IC below 0.02 |
| `industry_leader_laggard_gap_reversion_5_20` | 0.0454 | 0.0475 | 0.0175 | 0.214 | 11.02 | 57.50% | 1 | 0 | 0 | reject: residual IC below 0.02, 2025 failure |
| `industry_leader_breakout_laggard_followthrough_10_5` | 0.0175 | 0.0376 | 0.0173 | 0.241 | 12.39 | 59.18% | 0 | 0 | 0 | reject: residual IC below 0.02, raw yearly instability |
| `industry_peer_dispersion_compression_reversal_20_5` | 0.0571 | 0.0567 | 0.0152 | 0.180 | 9.26 | 56.37% | 2 | 0 | 0 | reject: residual IC/ICIR/yearly instability |
| `industry_laggard_lowvol_catchup_composite_20` | 0.0506 | 0.0550 | 0.0114 | 0.129 | 6.63 | 53.39% | 4 | 0 | 1 | reject: weak residual IC, high exposure |

## Audit Read

The 2024Q1 and 2015 single-candidate smoke looked promising, but the full 2015-2025 replay did its job:

- the best residual IC by threshold was `industry_leader_pullback_resilience_10_5`, but its raw yearly behavior failed;
- the original smoke lead `industry_leader_laggard_gap_reversion_5_20` fell to residual IC 0.0175 and failed 2025;
- no candidate had high public-reference redundancy, which is good, but that did not create enough residual alpha;
- one candidate had high exposure and several had moderate momentum/volatility exposure;
- zero candidates earned cost/capacity or portfolio preflight permission.

## Decision

Round220 produced a useful engineering upgrade and one family-level negative result. It did not produce a profitable factor, paper-ready factor, or portfolio candidate.

Next direction:

`round221_rotate_after_industry_leader_lag_residual_failure`

Carry forward:

- keep the streaming sharded prescreen infrastructure for future families;
- keep `industry_leader_pullback_resilience_10_5` as a weak structural clue only, not as a candidate;
- if this family is revisited, it must be through a new orthogonal hypothesis that explains raw yearly instability, not window tuning.

Hard rejects:

- direct TopN or cost/capacity preflight from any Round220 result;
- tuning leader definitions after seeing the full-sample failure;
- treating the 2015 or 2024Q1 smoke as evidence over the full cycle.
