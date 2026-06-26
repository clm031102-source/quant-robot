# CN ETF Public Trend-Volume Capacity Strict - Round45

日期: 2026-06-21
机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 目标

Round44 的公开趋势量价指标里，OBV/SuperTrend 在纸面上有较高年化和相对收益，但全部被容量和回撤挡住。本轮不扩大参数网格，而是检验一个更硬的问题:

如果把容量、流动性稳定性、低波动和极端日过滤都收紧，OBV/SuperTrend 的收益是否还能保留。

## 工程变更

新增严格容量版本:

- `supertrend_volume_capacity_strict_10_3_20`
- `obv_breakout_capacity_strict_20`

严格过滤包含:

- 原始趋势量价交易掩码
- ADV20 横截面排名 >= 80%
- 下行波动排名 <= 60%
- 高低价区间排名 <= 70% 或高低价区间 <= 5%
- 20 日成交额稳定性 >= 25%
- 单日绝对收益 <= 20%

同时修复一个决策门禁漏洞:

原先 `decision_summary` 只检查相对收益、回撤和容量，导致“总收益为负但跑赢更差基准”的 case 可能被标记为 `approved`。现在新增 `min_total_return`，本轮配置设为 `0.0`，负总收益必须 rejected。

## 配置和验证

配置:

- `configs/experiment_grid_cn_etf_liquid_public_trend_volume_capacity_strict_round45_20260621.json`
- `configs/experiment_grid_cn_etf_liquid_public_trend_volume_capacity_strict_small100k_round45_20260621.json`

复跑输出:

- `data/reports/experiment_grid_cn_etf_liquid_public_trend_volume_capacity_strict_minret_round45_20260621`
- `data/reports/experiment_grid_cn_etf_liquid_public_trend_volume_capacity_strict_small100k_minret_round45_20260621`

验证:

- `python -m unittest tests.unit.test_decision_risk tests.unit.test_experiment_runner tests.unit.test_research_pipeline tests.unit.test_walk_forward`
- `python scripts/run_project_audit.py --json`

结果: 89 个相关单测通过，项目审计通过。

## 结果概览

| 资金规模 | cases | completed | approved | capacity limited | 结论 |
|---|---:|---:|---:|---:|---|
| 1,000,000 | 16 | 16 | 0 | 0 | 全部 rejected |
| 100,000 | 16 | 16 | 0 | 0 | 全部 rejected |

严格容量过滤确实消除了容量阻塞，但收益同时消失。最佳 case 仍为负收益、负 Sharpe，且 IC 不显著。

## 最好但仍不可用的 case

### 1,000,000 资金规模

| case_id | Sharpe | 年化 | 总收益 | 胜率 | 最大回撤 | 相对收益 | 容量受限交易 | 最大参与率 | Rank IC p | 决策 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| supertrend strict top5 cost5 reb5 | -0.0186 | -0.53% | -2.22% | 50.23% | -20.55% | 13.74% | 0 | 0.183% | 0.5793 | rejected |
| obv strict top5 cost5 reb5 | -0.0785 | -0.98% | -4.10% | 46.95% | -20.22% | 11.86% | 0 | 0.816% | 0.4138 | rejected |
| supertrend strict top5 cost5 reb10 | -0.1660 | -1.11% | -4.59% | 50.00% | -16.01% | 11.37% | 0 | 0.183% | 0.2470 | rejected |

### 100,000 资金规模

| case_id | Sharpe | 年化 | 总收益 | 胜率 | 最大回撤 | 相对收益 | 容量受限交易 | 最大参与率 | Rank IC p | 决策 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| supertrend strict top5 cost5 reb5 | -0.0151 | -0.50% | -2.10% | 50.23% | -20.52% | 13.86% | 0 | 0.018% | 0.5793 | rejected |
| obv strict top5 cost5 reb5 | -0.0744 | -0.95% | -3.96% | 46.95% | -20.19% | 12.00% | 0 | 0.082% | 0.4138 | rejected |
| supertrend strict top5 cost5 reb10 | -0.1633 | -1.10% | -4.53% | 50.00% | -15.98% | 11.43% | 0 | 0.018% | 0.2470 | rejected |

## 判断

Round44 的 OBV/SuperTrend 收益主要来自容量不干净、异常交易或不稳定流动性样本。一旦用实盘更接近的容量和流动性约束过滤，收益不但没有提高，反而变成负收益。

这个族现在不应继续扩参。继续在 OBV/SuperTrend 上调窗口、调 topN、调 rebalance，大概率是在追噪声。

## 结论

本轮新增因子 2 个:

- `supertrend_volume_capacity_strict_10_3_20`
- `obv_breakout_capacity_strict_20`

可推广盈利因子: 0
paper-ready: 0
validation candidate: 0
research lead: 0

家族决策: 公开趋势量价 OBV/SuperTrend 进入休眠。除非后续有更长历史、更明确的 ETF 轮动经济假设或独立数据源确认，否则不再沿这条线继续挖。

## 下一步

Round46 切换到更贴近实盘目标的 ETF 轮动公开框架:

- 相对强弱/双动量: 资产自身趋势 + 横截面相对强度
- 风险过滤: 现金/基准趋势过滤，避免熊市硬扛
- 低波动 tie-break: 在强势 ETF 中优先波动更低者
- 全样本小网格优先，不通过全样本不进 walk-forward

下一轮的目标不是增加参数数量，而是把经济假设从“单一资金流或量价形态”转成“ETF 轮动中更常见的趋势跟随 + 风险开关”。
