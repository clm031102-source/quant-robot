# CN ETF Range-Contraction Long-Cycle Replay - Round42

日期: 2026-06-21
机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 目标

对 Round32/38/41 中表现最好的 `formula_range_contraction_breakout_20` 参数做同参数全样本复跑和长周期覆盖审计，验证短样本高夏普是否能在更长样本中保持。

本轮不是继续加参数，而是修正流程问题: 短窗挖到的强信号必须先过全样本、容量、显著性、长周期覆盖审计，不能直接进入推广候选。

## 输入

- 候选集: `data/reports/candidate_sets/cn_etf_range_contraction_base_replay_round42.csv`
- 全样本复跑输出: `data/reports/same_parameter_full_sample_replay_cn_etf_range_contraction_base_round42_20260621/`
- 长周期审计输出: `data/reports/long_cycle_factor_replay_cn_etf_range_contraction_base_round42_20260621/`
- 数据 manifest: `data/processed/tushare_etf_wide_history_2023_2026/manifest.json`

## 工程修正

长周期审计器原来只能读取带 `summary.date_start/date_end` 的 manifest，不能识别 Tushare ingest 生成的 `completed["CN_ETF:daily:YYYYMMDD"]` 格式，导致覆盖期显示为缺失。

本轮用 TDD 增加了解析能力:

- 从 completed daily key 推导 `date_start/date_end`
- 统计 `bar_rows`
- 统计年度交易日覆盖 `bar_trade_dates_by_year`
- 用单日最大 rows 作为 `bar_asset_ids` 的近似覆盖信息
- 忽略 failed、非 daily、非目标 market 条目

验证:

- `python -m unittest tests.unit.test_long_cycle_replay.LongCycleReplayTests.test_coverage_can_be_built_from_completed_daily_ingest_manifest`
- `python -m unittest tests.unit.test_long_cycle_replay`

结果: 17 个 long-cycle replay 单测通过。

## 全样本复跑结果

| case_id | Sharpe | 年化收益 | 总收益 | 相对收益 | 胜率 | 最大回撤 | Rank IC t | Rank IC p | 交易数 | 最大参与率 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| top5 cost5 reb10 | 0.4772 | 1.85% | 8.51% | 24.46% | 51.79% | -8.30% | 1.11 | 0.2655 | 540 | 381.84% | rejected |
| top10 cost5 reb10 | 0.4672 | 1.57% | 7.15% | 23.11% | 55.36% | -10.00% | 1.11 | 0.2655 | 1080 | 190.92% | rejected |
| top5 cost5 reb5 | 0.4406 | 2.20% | 9.99% | 25.95% | 52.04% | -9.42% | 2.11 | 0.0349 | 1075 | 652.35% | rejected |
| top10 cost5 reb5 | 0.5261 | 2.55% | 11.67% | 27.62% | 58.82% | -6.89% | 2.11 | 0.0349 | 2150 | 326.18% | rejected |

全样本结论:

- 短窗里 1.5-1.8 的 Sharpe 降到 0.44-0.53。
- 年化收益只有 1.57%-2.55%，不是可推广盈利因子。
- reb5 的 Rank IC p 值较好，但尾部 IC 是显著负向，且容量问题严重。
- 四个候选全部因为 `capacity_limited_trades_present` 被拒绝。

## 长周期覆盖审计

修正 manifest 解析后，真实覆盖为:

- Date range: 2020-01-02 to 2024-06-28
- Rows: 1,119,490
- Max daily assets proxy: 1,363
- Trade dates by year: 2020=241, 2021=243, 2022=242, 2023=242, 2024=117
- Missing required years: 2015, 2016, 2017, 2018, 2019

长周期审计结论:

- Coverage status: insufficient
- Coverage blockers: `history_starts_after_required_cycle_start`, `missing_required_years`
- Candidates: 4
- Research lead: 4
- Validation candidate: 0
- Paper candidate: 0

## 判断

这条线不是完全无信息，但不能推广:

1. 短样本高夏普主要来自阶段性市场环境，全样本回放后显著降级。
2. 收益规模太小，交易容量问题太大，实盘摩擦后大概率没有可用边际。
3. 当前 CN ETF 数据只能证明 2020-2024，不能覆盖 2015 股灾后、2018、完整 2022-2024 等更完整周期。
4. 继续微调 range-contraction 的 topN/rebalance/cost 权重，边际价值很低，容易变成参数挖矿。

## 后续调整

- 停止对 `formula_range_contraction_breakout_20` 做同族细调，只保留为 weak research lead。
- 后续挖因子必须先给出公开指标或经济机制来源，再进入参数网格。
- 每个新因子族先做小网格全样本快速筛，只有全样本弱门槛通过后再做 walk-forward。
- 优先转向公开技术指标族: smart money/量价背离、SuperTrend/ATR 趋势过滤、Donchian/通道突破、RSI/StochRSI 反转、KAMA/效率比、自适应波动目标。
- 数据层面需要补齐 CN ETF 2015-2019 或明确承认 ETF 长周期无法验证，改用可追溯指数代理做研究层验证。
