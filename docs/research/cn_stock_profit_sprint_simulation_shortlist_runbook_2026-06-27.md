# CN Stock Profit Sprint Simulation Shortlist Runbook

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

This runbook packages the current 24h sprint candidates for the next simulation/backtest stage.

Round425 supersession note:

The current paper-simulation handoff is now cohort-entry-timed only. Older event-level shortlist candidates remain useful research context, but they are not the default paper-simulation payload unless rebuilt and passed through `scripts\run_simulation_shortlist_paper_handoff.py`.

Round428 risk note:

The current 10 bps default remains the best ordinary-metric cohort handoff, but it is no longer a clean default. Round428 found that 190 active trades with `abs(gross_return) > 50%` contribute about 25% of total return. Excluding those trades is a diagnostic stress haircut only because realized `gross_return` is future information. Before simulation, either repair the tail dependency with entry-known features or explicitly paper-test it as a conditional high-tail-risk lane.

Round430 repair note:

Round430 added trade-level cohort output and an extreme-trade profiling tool. The best repair candidate is `round430_roundtrip_m150_stress`, which uses `roundtrip_cash_proxy_weighted_return` and improves full-sample drawdown, overlap Sharpe, beta-hedged overlap, and contributing extreme-trade dependence. It is not a clean entry-factor promotion because roundtrip cash proxy uses exit-date tradeability evidence. Treat it as the best execution-stress research candidate until a causal delayed-exit simulation confirms the effect.

Round432 delayed-exit note:

Round432 replaced the Round430 roundtrip proxy with a more causal delayed-exit repair. If a planned exit is not sellable, the repair delays to the first sellable exit within 10 calendar days and preserves zero-return events at the planned exit date. `round432_delayed_exit_m150` is now the strongest research-to-paper candidate by full-sample return, Sharpe, OOS annualized return, beta-hedged annualized return, and alpha t-stat. It is not paper-ready until heavy-cost stress and the replay/handoff gate pass.

Round433 cost-stress note:

Round433 ran delayed-exit cost stress. The 20 bps lane remains positive with annualized return +6.060% and max drawdown -28.07%. The raw 30 bps lane breached the user's -30% drawdown line at -30.19%, so a small risk-budget variant, VT 7.5% with max exposure 1.00, is the 30 bps fallback at +5.415% annualized return and -29.66% max drawdown. The delayed-exit pack now replaces the old Round425 default in the active paper-simulation handoff set; the old pack remains a research reference because of the Round428 extreme-trade dependency warning.

Current handoff pack:

Fresh Round446 handoff output:

`data/reports/round446_24h_profit_sprint_range_observation_paper_handoff_20260627`

The handoff gate now reports 8 total candidates, 5 ready candidates, and 3 blocked research references. The ready candidates are the delayed-exit 10/20/30 bps lanes plus two range-contraction diagnostic observation lanes. The blocked references are superseded older cohort packs.

Default paper lane:

`paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`

Heavy-cost lanes:

- `paper_ready_delayed_exit_m150_cost20_vt08_max100_self_roll21_x08`
- `paper_ready_delayed_exit_m150_cost30_vt075_max100_self_roll21_x08`

Range-contraction observation lanes:

- cost-robust observation: `paper_ready_cohort_entry_timed_range_q10_m150_cost10_vt08_max100_self_roll21_x08`
- aggressive 10 bps observation: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`

Defensive simulation overlay:

Round434 adds a non-alpha risk overlay for simulation comparison: do not open new cohorts during the final 5 trading days of quarter-end months. This overlay lowers total/annualized return but improves drawdown, overlap Sharpe, beta-hedged overlap Sharpe, and best-month concentration across the 10/20/30 bps delayed-exit lanes. Keep the baseline as the return-seeking default; run the quarter-end overlay as a defensive paper-simulation lane.

Machine role:

`office_desktop`

Task:

`factor_validation`

Config:

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

2026 final holdout remains sealed.

## Candidate Tiers

| Tier | Candidate ID | Use |
|---|---|---|
| High-return default | `primary_high_return` | Main candidate if return is prioritized and around 30% drawdown is acceptable |
| Balanced observation | `primary_balanced_zz500_75` | Return/risk middle lane; useful if the user accepts mid-20% drawdown for higher return |
| Preferred defensive | `primary_defensive_zz500` | Main candidate if drawdown/cost robustness matters more |
| Ultra-defensive reference | `safer_defensive_zz500` | Benchmark for low-drawdown simulation; not the main return candidate |
| Quality-filter defensive observation | `primary_ps_filtered_defensive_zz500` | Defensive comparison that cashes selected high-PS entries instead of replacing them |

## Parameters

### `primary_high_return`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost_rate_0.001 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Core parameters:

- replacement filter: drop bottom 10% `turnover_rate_f` candidates and replace from the remaining candidate list;
- volatility target: target annual vol 6%, lookback 84 event returns;
- no external regime overlay.

Key evidence:

- total return: +177.08%;
- annualized return: +6.35%;
- Sharpe: 0.960;
- overlap Sharpe: 0.517;
- max drawdown: -28.88%;
- mean OOS annualized return: +7.86%;
- worst OOS drawdown: -24.00%;
- 30 bps fixed-exposure cost stress total: +130.29%;
- CSI500 beta R2: 0.251.

### `primary_balanced_zz500_75`

Formula:

`primary_high_return + zz500_mom120_neg_mult_0.75`

External regime:

- benchmark: `CN_ETF_XSHG_510500`;
- signal: 120-day ETF momentum;
- risk-off rule: if momentum is negative before decision date, multiply exposure by 0.75.

Key evidence:

- total return: +161.99%;
- annualized return: +5.99%;
- Sharpe: 0.989;
- overlap Sharpe: 0.530;
- max drawdown: -24.74%;
- mean OOS annualized return: +6.95%;
- worst OOS drawdown: -19.55%;
- 30 bps fixed-exposure cost stress total: +122.57%;
- 30 bps strict pass: 76.67%;
- CSI500 beta-hedged annualized return: +5.96%.

Interpretation:

This is a simulation observation lane, not a replacement for `primary_defensive_zz500`. It is materially stronger on return than the 50% defensive version, but weaker on 30 bps cost strict-pass robustness.

### `primary_defensive_zz500`

Formula:

`primary_high_return + zz500_mom120_neg_half`

External regime:

- benchmark: `CN_ETF_XSHG_510500`;
- signal: 120-day ETF momentum;
- risk-off rule: if momentum is negative before decision date, multiply exposure by 0.5.

Key evidence:

- total return: +147.29%;
- annualized return: +5.62%;
- Sharpe: 1.001;
- overlap Sharpe: 0.536;
- max drawdown: -20.38%;
- mean OOS annualized return: +6.05%;
- worst OOS drawdown: -14.87%;
- 30 bps fixed-exposure cost stress total: +114.75%;
- 30 bps strict pass: 90.00%;
- CSI500 beta-hedged annualized return: +5.59%.

### `safer_defensive_zz500`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost_rate_0.001 + cash_low_turnover_f_bottom20 + entry_cash + vol_target_5_lb84 + zz500_mom120_neg_half`

Core parameters:

- cash bottom 20% `turnover_rate_f` entry trades instead of replacing them;
- volatility target: target annual vol 5%, lookback 84 event returns;
- same CSI500 120-day momentum half-exposure regime overlay.

Key evidence:

- total return: +114.76%;
- annualized return: +4.73%;
- Sharpe: 0.996;
- overlap Sharpe: 0.534;
- max drawdown: -14.94%;
- mean OOS annualized return: +4.72%;
- worst OOS drawdown: -11.68%;
- CSI500 beta-hedged annualized return: +4.69%.

### `primary_ps_filtered_defensive_zz500`

Formula:

`primary_high_return + cash selected entries with top 20% selected-basket ps_ttm + zz500_mom120_neg_half`

Secondary filter:

- start from the selected `primary_low10_vol6` basket;
- rank selected entries by `ps_ttm` on each signal date;
- cash entries in the highest 20% selected-basket PS rank;
- do not replace filtered entries.

External regime:

- same CSI500 120-day momentum half-exposure overlay as `primary_defensive_zz500`.

Key evidence:

- total return: +119.29%;
- annualized return: +4.86%;
- Sharpe: 1.076;
- overlap Sharpe: 0.573;
- max drawdown: -15.90%;
- mean OOS annualized return: +5.01%;
- worst OOS drawdown: -12.02%;
- 30 bps fixed-exposure cost stress total: +96.15%;
- 30 bps strict pass: 76.67%;
- CSI500 beta-hedged annualized return: +4.83%;
- CSI500 beta-hedged overlap Sharpe: 0.943.

Interpretation:

This is a defensive observation lane. It is not the return engine, but it is useful for comparing whether a valuation-quality cash filter can reduce tail risk while keeping positive return.

## Do Not Use

These outputs are superseded and must not be used as evidence:

- `data/reports/round346_24h_profit_sprint_cost_stress_primary_aggressive_20260627`
  - reason: volatility-target exposure recomputation did not reproduce official current-cost events.
- `data/reports/round347_24h_profit_sprint_benchmark_beta_audit_20260627`
  - reason: OLS residual stream subtracted the intercept; corrected audit uses `strategy_return - beta * benchmark_return`.

Rejected defaults:

- aggressive low20/PB candidate;
- hard cash external regime as default;
- strategy self-risk cash overlays;
- direct public-indicator cash filters from Round336.

## Mandatory Replay Gates

Before packaging any shortlist candidate for simulation, run both replay gates:

```powershell
.venv\Scripts\python.exe scripts\run_simulation_shortlist_replay.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round363_24h_profit_sprint_simulation_shortlist_event_schema_replay_20260627 --metric-tolerance 0.005
```

The replay must show:

- `status` is `passed`;
- `blocked_candidate_count` is 0;
- every candidate has a valid return column;
- structured candidates have `decision_date`;
- volatility-target or regime-overlay candidates have `final_exposure`;
- declared ZZ500 risk-off multipliers match the event stream when the event file declares a multiplier.

Round363 passed these checks for all five candidates.

## Exposure / Pre-Rank Gates

Round366-368 added two required controls for any candidate that changes untradeable positions, board eligibility, or replacement behavior:

```powershell
.venv\Scripts\python.exe scripts\run_shortlist_exposure_audit.py --trades <trades_with_tradeability.parquet> --output-dir <exposure_audit_output> --group-column industry --group-column stock_market
```

```powershell
.venv\Scripts\python.exe scripts\run_turnover_low_prerank_replacement.py --output-dir <prerank_replacement_output> --exclude-asset-prefix CN_XBEI --max-abs-daily-return-quarantine 0.50
```

The evidence must distinguish:

- true alpha improvement;
- reduced wasted weight from board-permission or ST/delisting blocks;
- accidental risk reduction from cashing untradeable positions;
- added crash exposure from replacing previously cashed positions.

Round368 rejected `replace_drop_turnover_f_low10_mainboard_prerank` for simulation shortlist use:

- entry allowed rate improved to 95.75%;
- annualized return improved to 6.86%;
- max drawdown worsened to -48.95%;
- even `vol_target_4_lb84` still had -36.71% max drawdown.

So board-permission pre-ranking is now a process control, not a promoted alpha line.

## Before 2026 Holdout

Do not run the 2026 holdout until all are true:

1. The simulation shortlist config has been reviewed.
2. Candidate formulas are implemented or mapped in a repeatable entrypoint.
3. Cost, capacity, and beta audits are linked in the report.
4. The user explicitly starts final validation or simulation-readiness review.
5. The run is recorded as read-once holdout usage.

## Block Dependence Check

Round356 added a reusable block-dependence audit:

`scripts/run_shortlist_return_block_audit.py`

Result:

- all five shortlist candidates stayed positive after removing the most important year;
- the most sensitive removed year is 2015 for every candidate;
- top three months contributed about 43.75% to 48.26% of total log return, below the 70% blocker threshold;
- 2026 final holdout remains sealed.

This does not make the candidates paper-ready. It does reduce the concern that the current shortlist is only one lucky year or one lucky month cluster.

Round357 stress-tested stricter block gates:

- 0 of 5 candidates passed when requiring at least +3% leave-one-year annualized return, at least 0.40 leave-one-year overlap Sharpe, and no more than 45% top-three-month log contribution;
- this is a warning against overselling the family as smooth all-regime alpha;
- the useful ranking is: balanced 75% and defensive 50% are the best core simulation candidates, high-return is a drawdown-tolerant lane, PS-filter is a defensive diagnostic lane, safer defensive is only an ultra-defensive reference.

Round361 added a replay check:

`scripts/run_simulation_shortlist_replay.py`

It verifies that the event-return files reproduce the metrics stored in the config. This caught and fixed the `safer_defensive_zz500` source-column issue: the final CSI500-regime stream is `overlay_return`, not `period_return`.

## Current Recommendation

Use the Round446 handoff pack as the active paper-simulation handoff set. The Round433 delayed-exit pack remains the baseline/cost spine:

- default 10 bps lane: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`;
- heavier-cost 20 bps lane: `paper_ready_delayed_exit_m150_cost20_vt08_max100_self_roll21_x08`;
- stress fallback 30 bps lane: `paper_ready_delayed_exit_m150_cost30_vt075_max100_self_roll21_x08`.

Add two diagnostic range-contraction observation lanes:

- cost-robust range observation: `paper_ready_cohort_entry_timed_range_q10_m150_cost10_vt08_max100_self_roll21_x08`;
- aggressive 10 bps range observation: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`.

Current best default lane:

- `round432_delayed_exit_m150`;
- annualized return: +6.663%;
- total return: +218.46%;
- Sharpe: 0.968;
- overlap Sharpe: 0.496;
- max drawdown: -26.21%;
- mean OOS annualized return: +10.043%;
- mean OOS overlap Sharpe: 0.831;
- worst OOS drawdown: -19.30%;
- beta-hedged annualized return: +7.485%;
- beta-hedged overlap Sharpe: 0.792;
- alpha t-stat: 4.36.

Cost-stress lanes:

- 20 bps: annualized return +6.060%, total return +187.60%, overlap Sharpe 0.456, max drawdown -28.07%, OOS strict pass 76.67%, beta-hedged annualized return +6.744%.
- 30 bps fallback: annualized return +5.415%, total return +157.79%, overlap Sharpe 0.416, max drawdown -29.66%, OOS strict pass 76.67%, beta-hedged annualized return +5.952%.

Defensive quarter-end overlay:

- 10 bps: annualized return +6.400%, total return +204.62%, overlap Sharpe 0.546, max drawdown -23.20%, OOS strict pass 90.00%, beta-hedged overlap Sharpe 0.869.
- 20 bps: annualized return +5.886%, total return +179.27%, overlap Sharpe 0.506, max drawdown -24.06%, OOS strict pass 90.00%, beta-hedged overlap Sharpe 0.802.
- 30 bps: annualized return +5.284%, total return +152.08%, overlap Sharpe 0.465, max drawdown -25.61%, OOS strict pass 76.67%, beta-hedged overlap Sharpe 0.726.

Strict statistical reality check:

- Round437 tested the six delayed-exit baseline and `zero_quarter_end5` lanes with overlap-adjusted Sharpe, effective observations set to `period_count / 4`, and Benjamini-Hochberg FDR across the six hypotheses.
- Deflated-Sharpe probability passed for all six lanes, but FDR-significant count was 0 and statistical-candidate count was 0.
- The best lane by overlap Sharpe was `cost10_zero_qe`: overlap Sharpe 0.546, p-value 0.02066, FDR q-value 0.06400.
- The purged/CPCV-style split audit still favored `cost10_zero_qe` on robustness: mean annualized return 6.468%, mean overlap Sharpe 0.573, positive-annualized split rate 93.33%, and DD <= 30% pass rate 93.33%.
- Interpretation: the pack is eligible for simulation observation, but no lane is a statistically final alpha promotion.

Round438 public-indicator update:

- Reused the cached Round404 public-factor source after a full rematerialization attempt timed out; do not repeat full materialization during the 24h sprint unless a factor is missing.
- Best return-enhancement lead: `tilt_public_rsrs_z_top10`, using `rsrs_zscore_18_60` top 10% with 1.50x tilt.
- RSRS z top10 improved the repaired delayed-exit lane from annualized return 6.663% to 7.373%, total return 218.46% to 258.74%, and overlap Sharpe 0.496 to 0.506, while max drawdown worsened from -26.21% to -26.75%.
- Best defensive lead: `cash_public_anti_supertrend_top10`, using `supertrend_volume_confirmed_10_3_20` top 10% as a cash mask.
- Anti-supertrend improved overlap Sharpe to 0.526, max drawdown to -23.98%, win rate to 41.99%, and best-three-month concentration to 42.23%, with only modest return uplift.
- Round438 shortlist-level statistical check passed FDR across four rows, but this is not a full accounting of all public-indicator ideas tried today. Treat it as support for formal rebuild, not final alpha proof.
- Next formal rebuild candidate: RSRS z top10 return-enhancement lane. Keep anti-supertrend as a defensive overlay watchlist.

Round439 formal rebuild update:

- RSRS z top10 failed formal cohort-entry rebuild.
- Formal RSRS z top10 returned annualized return 6.337%, total return 201.42%, overlap Sharpe 0.477, max drawdown -27.11%, and OOS strict pass 76.67%.
- Current base remains stronger: annualized return 6.663%, total return 218.46%, overlap Sharpe 0.496, max drawdown -26.21%, and OOS strict pass 90.00%.
- Do not tune RSRS fractions or multipliers after this failure. Classify Round438 RSRS as a projection false positive.
- New process rule: public-indicator projection leads are triage only; they must pass formal cohort-entry rebuild before simulation-shortlist discussion.
- Next formal test: anti-supertrend cash overlay as a defensive candidate.

Round440 formal rebuild update:

- Anti-supertrend cashing also failed formal cohort-entry rebuild.
- Formal anti-supertrend cash returned annualized return 5.768%, total return 173.74%, overlap Sharpe 0.468, max drawdown -27.54%, and OOS strict pass 76.67%.
- It had one useful risk-control sign: worst OOS drawdown improved to -18.05% and beta-hedged drawdown improved to -11.48%.
- The trade-off is not acceptable for the current objective because return, overlap, OOS pass rate, and coverage all deteriorated; selected-trade missing factor share was 83.60%.
- Direction change: stop public technical overlay mining for now. Rotate to event-context underreaction, tradeability/liquidity microstructure, or daily-basic non-price quality only when point-in-time and coverage gates are available.

Round441-442 capacity-safe PV update:

- Added reusable support for `capacity_safe_price_volume` factors in `shortlist_public_factor_source`.
- Added formal incremental overlay mode to `simulation_shortlist_cohort_entry_timed`: use existing `pre_overlay_return_contribution` and `pre_overlay_target_weight`, disable duplicate Dragon cash, add a second public-factor tilt, then rerun entry-timed vol/self-risk.
- First useful new lead after this correction: `range_contraction_lowvol_reversal_20` top10 1.50x as a second-layer overlay on the delayed-exit Alpha101/Dragon base.
- 10 bps result: annualized return 7.083%, total return 241.70%, Sharpe 0.984, overlap Sharpe 0.505, max drawdown -26.99%, OOS strict pass 90.00%, beta-hedged annualized return 8.004%.
- 20 bps result: annualized return 6.458%, total return 207.62%, overlap Sharpe 0.466, max drawdown -28.87%, OOS strict pass 90.00%.
- 30 bps stress fallback uses VT 7.0%: annualized return 5.581%, total return 165.17%, overlap Sharpe 0.422, max drawdown -29.97%, OOS strict pass 76.67%.
- Corrected statistical reality check still has 0 FDR-significant candidates across six cost hypotheses; best row is `incremental_range_cost10` with p-value 0.03229 and FDR q-value 0.07777.
- Treat Round442 as the best current simulation-observation return-enhancement candidate, not final alpha.

Round443 split/bootstrap update:

- Round443 added a CPCV-style block audit and quarterly block bootstrap for the Round442 range-contraction increment.
- 10 bps incremental range beat the base on annualized return in 90.83% of CPCV splits, had positive excess in 91.67% of CPCV splits, and had positive bootstrap annualized delta in 99.30% of bootstrap paths.
- The risk warning is real: bootstrap paths kept drawdown within 30% only 57.90% of the time for 10 bps and 55.80% for 20 bps.
- Keep `incremental_range_cost10` as the best return-seeking simulation-observation candidate, not as final alpha or automatic default replacement.
- Carry `incremental_range_cost20` as a heavy-cost observation lane and `incremental_range_cost30_vt070` as stress evidence only.

Round444-445 range sensitivity update:

- Round444 tested `bollinger_reversal_lowvol_liquid_20`, `amount_stability_reversal_5_20`, and `pv_corr_reversal_capacity_safe_20` as incremental overlays. All had clean 99.81% shortlist coverage, but none beat Round442 `range_q10_m150` on the combined return/overlap/risk profile.
- Round445 tested a constrained `range_contraction_lowvol_reversal_20` neighborhood: top 5/10/15/20% and multipliers 1.25/1.50/1.75/2.00.
- Best 10 bps full-sample return was `range_q20_m200`: annualized return 8.023%, total return 299.79%, overlap 0.515, but max drawdown -30.30% breaches the approximate line.
- Best 10 bps aggressive observation inside the approximate full-sample line is `range_q20_m175`: annualized return 7.723%, total return 280.30%, overlap 0.512, max drawdown -29.31%, mean OOS annualized return 11.739%, OOS strict pass 90.00%.
- Cost caveat: `range_q20_m175` is too fragile under heavier costs; 20 bps VT 8% max drawdown is -31.07% and 30 bps VT 7% max drawdown is -32.04%.
- Keep `range_q10_m150` as the more cost-robust range observation lane. Add `range_q20_m175` only as an aggressive 10 bps simulation-observation lane.

Round446 paper handoff update:

- Added `range_q10_m150` and `range_q20_m175` to the active paper-simulation handoff config as diagnostic lanes.
- The handoff replay reports 8 total candidates, 5 ready candidates, and 3 blocked research references.
- The default remains `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`; range lanes do not replace it automatically.
- `range_q10_m150` replay: annualized return 7.083%, total return +241.70%, overlap Sharpe 0.505, max drawdown -26.99%, OOS strict pass 90.00%.
- `range_q20_m175` replay: annualized return 7.723%, total return +280.30%, overlap Sharpe 0.512, max drawdown -29.31%, OOS strict pass 90.00%.
- Both are ready for paper-simulation comparison only. They are not final alpha promotions because incremental FDR/bootstrap/cost-stress caveats remain.

Round447 PB risk-cap update:

- Round447 tested an entry-known `pb > 4` risk cap on the aggressive `range_contraction_lowvol_reversal_20` q20/m175 lane.
- The fair-control rerun found PB cap050 is the best risk-budget version: at 20 bps it improves annualized return from 7.233% to 7.301%, overlap Sharpe from 0.484 to 0.498, and max drawdown from -31.76% to -30.26%.
- At 30 bps / VT7 it improves annualized return from 6.197% to 6.290%, overlap Sharpe from 0.435 to 0.450, and max drawdown from -32.72% to -31.40%, but best-month concentration remains above the strict 50% line.
- Incremental CPCV/bootstrap supports PB cap050 as a risk improvement, not a large return engine: cost20 bootstrap overlap-win rate is 98.00% and drawdown-win rate is 97.40%, while annualized-return win rate is 68.80%.
- The 15-row statistical reality check still has 0 FDR-significant candidates. Keep PB cap050 as a simulation observation candidate only if the simulation stage wants an aggressive q20 risk-budget variant.
- Process rule added: rerun fair controls through the same event generator before comparing variants, and use `simulation_shortlist_entry_timed_events.csv` for final metrics rather than pre-overlay `cohort_source_period_returns.csv`.

Round448 entry-known attribute projection update:

- Round448 tested a small set of entry-known valuation, turnover, capacity, board, and dividend-availability filters against the frozen Round339 low10 VT6/LB84 baseline.
- Added reusable incremental robustness tooling: `scripts/run_shortlist_incremental_return_robustness.py` and `src/quant_robot/ops/shortlist_incremental_return_robustness.py`.
- The best projection leads were valuation-risk filters, not new alpha engines: `ps_gt10` added +0.186% annualized return, +8.11% total return, +0.054 overlap Sharpe, and +1.81% drawdown improvement; `pb_gt6` added +0.160% annualized return, +7.00% total return, +0.042 overlap Sharpe, and +0.27% drawdown improvement.
- Incremental robustness is modest: `ps_gt10` CPCV annualized-win rate 67.50% and bootstrap annualized-win rate 62.20%; `pb_gt6` CPCV annualized-win rate 58.33% and bootstrap annualized-win rate 64.20%.
- 2025 alone contributes almost no incremental return, and several years are negative for each lead. Treat both as projection-only valuation risk-filter leads, not paper-ready candidates.
- Decision: do not add Round448 candidates to the paper-simulation handoff set; stop widening PB/PS/PE threshold tuning and rotate to a genuinely different PIT family.

Round449 trade group and entry execution-risk audit:

- Round449 audited the frozen Round339 low10 VT6/LB84 trade tape for group contribution, exposure concentration, and entry/exit tradeability loss.
- The cleanest entry-known observation is `entry_limit_down`: cashing trades whose entry condition is `limit_down_like;limit_down_official` improves annualized return from 6.352% to 6.626%, total return from +177.08% to +189.11%, overlap Sharpe from 0.517 to 0.547, and leaves max drawdown essentially unchanged at -28.87%.
- Incremental robustness for `entry_limit_down` is useful but not decisive: CPCV annualized-win rate 70.83%, bootstrap annualized-win rate 74.80%, and year win rate 45.45%.
- Exit-limit-down cashing has similar numbers but uses exit-time information, so it is diagnostic only.
- Worst-industry cash projections look stronger on paper, with worst10 adding +0.443% annualized return, +19.73% total return, +0.063 overlap Sharpe, and +2.07% drawdown improvement; however, the list was selected from full-sample contribution and is therefore data-snooping until externally justified and formally rebuilt.
- Structural exposure remains concentrated in main-board/XSHG/HS-H names. Simple `non_hs`, `xshe`, and `non_xshg` cash filters reduce return and should not be promoted as filters.
- Decision: promote 0 new independent alpha factors. Keep `entry_limit_down` only as a formal execution-rule rebuild candidate; keep industry blacklist as diagnostic evidence only.

Round450 entry-limit-down formal rebuild update:

- Round450 added reusable cohort-entry support for `--entry-attribute-cash-rule` and rebuilt `entry_limit_down` inside the delayed-exit cohort generator rather than as a projection.
- The rebuilt lane `round450_delayed_exit_m150_entry_limit_down_cash` cashes 178 entry-limit-down trades before cohort aggregation, vol targeting, self-risk, and paper-readiness checks.
- Full-sample metrics improve versus `round432_delayed_exit_m150`: annualized return 6.829% versus 6.663%, total return +227.43% versus +218.46%, overlap Sharpe 0.515 versus 0.496, max drawdown -24.88% versus -26.21%.
- OOS split audit slightly favors the base: mean OOS annualized return 10.043% base versus 10.018% rebuild, mean OOS overlap Sharpe 0.831 versus 0.830, and worst OOS drawdown -19.30% versus -19.38%.
- Incremental robustness is useful but not decisive: CPCV annualized-win rate 68.33%, bootstrap annualized-win rate 78.50%, bootstrap overlap-win rate 85.70%, bootstrap drawdown-win rate 86.90%, but year win rate only 36.36%.
- Decision: this is a paper-simulation comparison observation only. Do not replace the default handoff lane and do not keep tuning entry/exit tradeability strings.

Round451 entry-limit-down cost-stress update:

- Round451 rebuilt the same entry-limit-down rule under the existing 20 bps and 30 bps delayed-exit cost-stress lanes.
- Full-sample cost stress improves: 20 bps annualized return rises from 6.060% to 6.228% and max drawdown improves from -28.07% to -25.83%; 30 bps VT7.5 annualized return rises from 5.415% to 5.590% and max drawdown improves from -29.66% to -27.40%.
- OOS still does not favor the rule: 20 bps mean OOS annualized return is 9.132% base versus 9.108% with the rule; 30 bps VT7.5 is 8.197% base versus 8.177% with the rule.
- Incremental robustness is stronger at 30 bps than 20 bps, but this is still an execution-risk observation rather than a new alpha engine.
- Decision: keep entry-limit-down as a simulation comparison lane only. Do not tune adjacent tradeability strings.

Round450-452 three-round audit:

- Round450-452 promotes 0 new independent alpha factors and 1 simulation-observation execution lane.
- `entry_limit_down` is useful for execution realism but not for alpha promotion: full-sample and beta-hedged metrics improve, while matched OOS mean annualized return and OOS overlap Sharpe still slightly trail the corresponding bases.
- The default remains `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`.
- Process reset: stop `entry_blocked_reasons` / `exit_blocked_reasons` string-neighborhood tuning, stop public technical projection chasing, and route the next mining batch through the startup gate plus candidate-plan gate for a genuinely different point-in-time family.

Round447-449 three-round audit:

- Round447 PB cap050 is a modest risk-budget observation, not a return engine or final alpha.
- Round448 `ps_gt10` and `pb_gt6` are projection-only valuation risk filters and should not be widened into more threshold mining.
- Round449 `entry_limit_down` is the only clean entry-known idea worth a formal rebuild. The industry blacklist is overfit diagnostic evidence unless rebuilt from an ex ante hypothesis.
- Process change: stop range/PB/valuation/industry full-sample tuning; either rebuild `entry_limit_down` at cohort-entry granularity or rotate to a genuinely different point-in-time data source.

Structural exposure disclosure:

- active trades are overwhelmingly main-board: 99.09% active weight;
- XSHG accounts for 83.97% active weight and 79.50% absolute return contribution;
- HS-H accounts for 73.70% active weight and 67.61% absolute return contribution;
- same-day exits account for 98.97% active weight; delayed exits are only 1.03% active weight but contribute -0.0515 return.

Required before treating the pack as simulation-ready:

- use the three Round433 delayed-exit candidates as baseline/cost lanes and the two Round446 range-contraction candidates only as diagnostic observation lanes;
- include the Round434 quarter-end overlay only as a defensive simulation lane, not as independent alpha;
- keep the Round425 pack only as blocked research reference unless the new handoff fails;
- do not use realized `gross_return` as an entry filter;
- explicitly disclose the weaker 20/30 bps OOS strict pass and best-month concentration;
- explicitly disclose main-board/XSHG/HS-H concentration and monitor delayed-exit losses;
- explicitly disclose that Round437 found 0 FDR-significant statistical candidates; `zero_quarter_end5` is a defensive simulation lane, not independent alpha;
- keep the 2026 final holdout sealed until the designated final review.

Keep the older event-level shortlist candidates as research references only unless they are rebuilt at cohort-entry-timed granularity and pass the handoff gate.
