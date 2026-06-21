# CN ETF Rounds 40-42 Audit

日期: 2026-06-21
机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 审计范围

- Round40: 同步收口，修复项目审计 registry 漏项并推送到 GitHub
- Round41: range-contraction 公开公式复合因子
- Round42: range-contraction 同参数全样本复跑和长周期覆盖审计

## 本组三轮产出

### Round40

- 修复 `etf_theme_breadth` factor_source 未被项目审计 registry 接受的问题。
- 单元测试从 821 增至 822，项目审计通过。
- 已推送 commit: `200b4ee Sync CN ETF factor validation rounds 31-39`

### Round41

新增 3 个正式注册的 range-contraction 复合因子:

- `formula_range_contraction_breakout_liquid_20`
- `formula_range_contraction_breakout_lowvol_20`
- `formula_range_contraction_breakout_liquid_lowvol_20`

实验:

- 48 个 walk-forward 参数组合
- accepted: 0
- positive Sharpe: 35/48
- best base: Sharpe 1.8334, 年化 1.43%, 胜率 56.25%, 最大回撤 -0.18%
- best composite: Sharpe 1.5688, 年化 2.95%, 胜率 64.58%, 最大回撤 -1.75%

结论:

- 复合项没有超过原始 base。
- 5bps 条件下有弱信号，10bps 后显著变差。
- 全部被 adjusted IC p=1.0 拒绝。

### Round42

同参数全样本复跑 4 个 base 候选:

| 参数 | Sharpe | 年化收益 | 胜率 | 最大回撤 | Rank IC p | 结论 |
|---|---:|---:|---:|---:|---:|---|
| top5 cost5 reb10 | 0.4772 | 1.85% | 51.79% | -8.30% | 0.2655 | rejected |
| top10 cost5 reb10 | 0.4672 | 1.57% | 55.36% | -10.00% | 0.2655 | rejected |
| top5 cost5 reb5 | 0.4406 | 2.20% | 52.04% | -9.42% | 0.0349 | rejected |
| top10 cost5 reb5 | 0.5261 | 2.55% | 58.82% | -6.89% | 0.0349 | rejected |

长周期覆盖:

- 实际 CN ETF 数据: 2020-01-02 到 2024-06-28
- 缺失 2015-2019
- coverage status: insufficient
- validation candidate: 0
- paper candidate: 0

## 审计结论

这组三轮没有挖出可推广盈利因子。

- 可推广: 0
- validation candidate: 0
- paper candidate: 0
- weak research lead: 4
- 新增正式因子名: 3
- 有继续研究但不应继续细调的族: `formula_range_contraction_breakout_20`

Round41 的高夏普在 Round42 全样本里降级明显，说明短窗口和 walk-forward 切片仍然会放大阶段性市场环境。这个结论直接回应前面的问题: 不能只看一段一段日期的回测，也不能用短样本去盲目扩参数。

## 为什么这批东西差

1. 方向上仍在围绕单一价格形态做细调，公开机制来源太窄。
2. 参数网格先于经济假设扩张，容易从“研究”滑向“调参”。
3. ETF 数据长周期不足，不能证明跨大周期稳健。
4. 容量门槛暴露了真实交易问题，部分候选最大参与率过高。
5. 5bps 和 10bps 的表现差异较大，说明信号边际收益薄，成本一上来就被吃掉。

## 方向调整

立即停止:

- 停止继续细调 `range_contraction_breakout_20` 的 topN/rebalance/cost/低波/流动性权重。
- 停止把短窗 Sharpe > 1 当作主要发现标准。
- 停止对同一族连续做超过三轮无 validation candidate 的挖掘。

保留:

- `range_contraction_breakout_20` 作为 weak research lead，只在补齐 2015-2019 ETF 或指数代理后再复核。

转向:

- 公开技术指标族: SuperTrend/ATR、Donchian 通道、RSI/StochRSI、MACD signal candle、KAMA/效率比、Bollinger/波动收缩。
- 公开量价机制族: smart money/量价背离、OBV/ADL、成交量确认动量、异常量反转。
- ETF 轮动特化族: dual momentum、趋势过滤后的相对强弱、波动目标权重、风险平价/低相关篮子。

## 新硬规则

从 Round44 起，每个因子族按以下流程走:

1. 先写一句经济假设和公开来源，不允许无来源盲扫。
2. 先做小网格全样本快速筛，不先做大 walk-forward。
3. 只有全样本 Sharpe > 0.6、年化 > 3%、最大回撤可控、容量无硬阻塞，才进入 walk-forward。
4. walk-forward 后必须做同参数全样本复跑。
5. 三轮内没有 validation candidate，因子族休眠，切到下一族。
6. 十轮收口时只推代码、配置、轻量报告，不推 data/reports 或原始数据。

## 已安装/参考的公开技能和项目

已安装 GitHub skill 包:

- `vectorbt-expert`
- `backtest`
- `optimize`
- `quick-stats`
- `strategy-compare`

来源:

- https://github.com/marketcalls/vectorbt-backtesting-skills

可吸收的方法:

- strategy catalog: EMA、Donchian、Momentum、MACD、SuperTrend、Dual Momentum
- walk-forward: in-sample/out-of-sample、rolling windows、WFE
- robustness testing: Monte Carlo、noise test、parameter sensitivity、delay test、cross-symbol validation
- parameter optimization: 优先找稳定参数区域，而不是孤立最优点

后续公开项目参考方向:

- TA-Lib: 标准技术指标定义
- pandas-ta/ta: 指标公式和实现参考
- vectorbt: 快速组合回测和性能分析参考
- Microsoft Qlib: 因子研究流程、数据集和模型验证参考

## Round44 计划

Round44 不再继续 range-contraction。下一轮先做公开指标族的小网格:

- family: SuperTrend/Donchian/RSI/MACD technical signal factors
- market: CN_ETF
- first gate: same-parameter full-sample quick screen
- only promote to walk-forward if full-sample passes weak viability gates

优先目标不是数量，而是减少假阳性、减少无意义成本，把每一轮失败都变成流程约束。
