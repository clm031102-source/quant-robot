# CN ETF / CN Stock Rounds 44-46 Audit - 2026-06-21

机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 审计范围

这是三轮复盘，覆盖:

- Round44: CN ETF 公开技术指标全样本筛选
- Round45: CN ETF OBV/SuperTrend 严格容量复验
- Round46: CN 股票行业元数据基础设施

本复盘的标准不是“跑了多少 case”，而是是否更接近一个能盈利、能复验、能实盘落地的研究流程。

## 三轮结果

| Round | 方向 | 新增/测试 | 有用结果 | 可推广盈利 |
|---|---|---:|---|---:|
| 44 | CN ETF public technical / trend-volume | 80 cases | 找到 OBV/SuperTrend 纸面弱线索，但容量不干净 | 0 |
| 45 | CN ETF OBV/SuperTrend capacity strict | 2 新因子, 32 cases | 容量修好后收益转负，确认该族休眠 | 0 |
| 46 | CN stock metadata foundation | 1 ingest 能力 | 获得 5529 只 A 股行业元数据，支持后续中性化/桥接 | 0 |

## 关键发现

### 1. 公开 ETF 单体技术指标继续扩参价值很低

已失败或休眠的 ETF 方向:

- basic momentum / risk-adjusted momentum
- RSI/Bollinger/MACD/Donchian
- OBV/SuperTrend/Smart Money
- raw theme breadth
- liquid-adjusted theme breadth
- range contraction tie-breaker variants

这些路径的共性问题:

- 单体指标的 Sharpe 和胜率不稳定。
- 一旦容量严格，纸面收益会消失。
- IC 或 tail IC 通常不显著。
- 多数“相对收益为正”来自基准更差，不等于策略赚钱。

### 2. `min_total_return` 门禁是必要修复

Round45 暴露出决策层漏洞: 只看相对收益会让亏钱但跑赢更差基准的 case 被误标 `approved`。

已修复:

- `decision_summary` 新增 `min_total_return`
- `ResearchPipelineConfig` / `ExperimentGridConfig` / walk-forward mapping 已透传
- Round44/Round45 配置加入 `min_total_return: 0.0`

后续所有新全样本筛选默认要求:

- 总收益 >= 0
- 相对收益 >= 0
- 容量受限交易 = 0
- 回撤不超阈值
- IC / tail IC 不能只靠单次最好参数解释

### 3. 股票因子不是完全没用，但直接 TopN  long-only 翻译失败

CN stock Round12-16 审计显示:

- 某些公开公式在 RankIC 上有显著信息。
- 但直接股票 TopN 组合不赚钱或不跑赢基准。
- 宽篮子降低容量问题，但 Sharpe 和相对收益仍弱。

这说明下一步不是继续原公式 TopN 参数，而是测试翻译层:

- 行业内 RankIC / 行业中性化
- 底部排除
- 行业广度
- ETF/theme 桥接

Round46 补齐的 `stock_basic` 行业数据正是为了这条线。

## 当前方向调整

停止继续扩展:

- OBV/SuperTrend 参数网格
- basic momentum 参数网格
- standalone ETF theme breadth
- range-contraction tie-breaker
- CN stock raw public formula TopN 或更宽 TopN

继续推进:

1. CN 股票行业中性审计

   目标: 判断强 RankIC 是否只是行业暴露，还是行业内仍有信息。

2. 股票因子行业广度翻译

   目标: 把个股强弱变成行业/主题风险状态，而不是买一篮子高分股票。

3. ETF 桥接数据缺口

   目标: 若要真正股票到 ETF，需要 ETF 成分、指数权重或更可靠的 ETF-行业映射。没有这些映射，不做伪桥接。

## 下一组三轮计划

### Round48

实现或运行行业内 RankIC / 行业暴露审计:

- 输入: 已有 CN stock factor leaderboard 或 factor matrix
- 元数据: `data/processed/cn_stock_metadata/metadata/tushare_stock_basic`
- 输出: 哪些因子行业内仍有 RankIC，哪些只是行业 beta

### Round49

若 Round48 发现行业内信息:

- 测试行业中性排序或行业内 top/bottom exclusion
- 不扩大原始 TopN 网格

若 Round48 发现主要是行业暴露:

- 转向行业广度/行业风险状态，而不是 stock TopN

### Round50

整理 Round41-50 轻量成果:

- 更新研究报告索引/ledger
- 运行测试和项目审计
- 用 `scripts/sync_project.py --machine office_desktop --task factor_validation` 做安全同步审计
- 只有无 forbidden data/log/token 路径且审计通过时才 push GitHub

## 审计结论

这三轮没有挖出可推广盈利因子。

但它们把方向从“继续盲扫公开技术指标”推进到更正确的问题:

强信号如何通过行业中性、广度或 ETF 映射转化为可交易策略。

后续效率提升点:

- 先做翻译层审计，再跑组合回测。
- 先查数据映射是否存在，再设计桥接因子。
- 继续执行三轮复盘、十轮同步，弱族及时休眠。
