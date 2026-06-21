# CN ETF Public Indicator Full-Sample Screen - Round44

日期: 2026-06-21
机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 目标

执行 Round43 审计后的新流程: 不继续盲调 range-contraction，改用有公开来源的技术指标族，先做 CN ETF 全样本小网格筛选。只有通过全样本弱门槛的候选才进入 walk-forward。

公开来源和机制:

- RSI/Bollinger: 均值回归/超买超卖
- Donchian: 通道突破
- MACD: 趋势动量
- SuperTrend/ATR: 趋势确认
- OBV/Smart Money: 量价确认和资金流压力

## 配置

新增配置:

- `configs/experiment_grid_cn_etf_liquid_public_technical_round44_20260621.json`
- `configs/experiment_grid_cn_etf_liquid_public_trend_volume_round44_20260621.json`

共同约束:

- market: CN_ETF
- universe: liquid ETF universe from Round25
- sample: 2020-01-02 to 2024-06-28
- source: processed Tushare ETF bars
- target gross exposure: 0.6
- cost: 5bps/10bps
- rebalance: 5/10 days
- topN: 5/10
- max participation rate: 1%
- min trades: 100
- no regime filter in first screen

验证:

- `python scripts/run_project_audit.py --json`
- `python -m unittest tests.unit.test_public_technical_factors tests.unit.test_public_trend_volume_factors tests.unit.test_project_audit tests.unit.test_experiment_runner tests.unit.test_long_cycle_replay`

结果: 项目审计通过，82 个相关单测通过。

## 结果总览

| 因子族 | cases | completed | accepted | positive Sharpe | 年化 > 3% | capacity clean |
|---|---:|---:|---:|---:|---:|---:|
| public_technical | 32 | 32 | 0 | 5 | 0 | 0 |
| public_trend_volume | 48 | 48 | 0 | 24 | 13 | 0 |

结论: 没有候选通过全样本第一道门槛，因此本轮不进入 walk-forward。

## Public Technical

最好的是 Donchian 通道位置:

| case_id | Sharpe | 年化 | 总收益 | 相对收益 | 胜率 | 最大回撤 | Rank IC p | 最大参与率 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| donchian top5 cost5 reb5 | 0.2672 | 2.22% | 9.69% | 25.64% | 48.11% | -24.01% | 0.0198 | 5964.21% | rejected |
| donchian top5 cost5 reb10 | 0.2223 | 1.29% | 5.54% | 21.50% | 51.89% | -16.15% | 0.0820 | 5964.21% | rejected |
| donchian top10 cost5 reb10 | 0.2094 | 1.20% | 5.13% | 21.08% | 55.66% | -18.97% | 0.0820 | 2982.11% | rejected |

判断:

- Donchian 有一定 rank IC 信号，但组合收益太弱。
- 最大参与率极端异常，说明即便是 liquid universe，仍有交易日/标的容量或数据异常没有挡住。
- RSI、Bollinger、MACD 在这个 ETF 轮动口径下没有可用表现。

## Public Trend-Volume

表现相对更好的候选集中在 OBV/SuperTrend/Smart Money:

| case_id | Sharpe | 年化 | 总收益 | 相对收益 | 胜率 | 最大回撤 | Rank IC p | 最大参与率 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| obv top10 cost5 reb5 | 0.5371 | 5.51% | 25.59% | 41.55% | 51.40% | -17.07% | 0.5425 | 76.82% | rejected |
| obv top5 cost5 reb5 | 0.5243 | 6.92% | 32.66% | 48.62% | 49.77% | -18.54% | 0.5425 | 153.65% | rejected |
| supertrend top5 cost5 reb5 | 0.4935 | 6.40% | 29.98% | 45.94% | 50.70% | -18.12% | 0.7214 | 153.65% | rejected |
| smart_money top5 cost5 reb5 | 0.4505 | 5.99% | 27.85% | 43.81% | 50.23% | -21.04% | 0.2464 | 202.87% | rejected |
| smart_money top5 cost5 reb10 | 0.4869 | 5.78% | 26.68% | 42.63% | 52.83% | -20.57% | 0.4104 | 153.65% | rejected |
| obv top10 cost5 reb10 | 0.4484 | 3.64% | 16.23% | 32.19% | 56.60% | -15.29% | 0.4928 | 76.82% | rejected |

判断:

- OBV/SuperTrend 比前面的 range-contraction 更像一个可研究方向: 年化和相对收益更高，且平均参与率较低。
- 但是 IC 不显著，胜率接近随机，容量仍然有硬阻塞。
- 最大单笔 gross return 达到 183.27%，需要排查是否来自异常价格、复权/分红、上市初期或极低成交额。

## 本轮结论

Round44 没有挖出可用因子。

- 可推广: 0
- validation candidate: 0
- paper candidate: 0
- weak research lead: 2 个因子族
  - `obv_breakout_low_tail_20`
  - `supertrend_volume_confirmed_10_3_20`

这轮的价值在于方向比以前更清楚: 公开量价趋势族优于单纯价格形态和均值回归族，但必须先解决容量和异常交易问题，否则年化收益只是纸面收益。

## Round45 决策

下一轮不扩大参数网格，而是对 OBV/SuperTrend 做容量和异常交易约束:

- 更严格 ADV/liquidity rank 阈值
- 剔除或惩罚极端单笔收益来源
- 降低 `portfolio_value` 做小资金容量对照
- 保持同样全样本口径，只有 capacity clean 后才考虑 walk-forward

如果 Round45 后 OBV/SuperTrend 仍然无法容量清洁，则该公开趋势量价族也进入休眠。
