# 项目进度审计报告 - 2026-06-15

## 审计结论

- GitHub 提交历史同步：当前分支 `phase-one-research-framework` 与 `origin/phase-one-research-framework` ahead/behind 为 `0 / 0`。
- 工作区尚未同步：本地存在未提交代码、测试、文档和 CI workflow 改动，GitHub 还没有这些最新内容。
- 真实 Tushare readiness 已通过，token 未写入项目文件。
- Phase 5.12 真实 Tushare activation gate 状态为 `paper_observation_ready`。
- 当前仍是 research-to-paper 阶段：无券商连接、无账户读取、无下单、无自动实盘交易，`live_boundary_allowed=false`。

## 当前真实门禁状态

- Source: `tushare`
- Mode: `execute`
- Status: `paper_observation_ready`
- Recent data ready: `true`
- Activation chain allowed: `true`
- Paper continuation allowed: `true`
- Blockers: none
- Final observation sufficiency: `sufficient`
- Final fills: `21 / 20`
- Iterative expansion rounds: `2 / 3`
- Live boundary allowed: `false`

## 数据覆盖审计

- 决策范围：`required_assets`
- Required asset: `CN_ETF_XSHG_516160`
- Requested target window: `2026-05-23` to `2026-06-14`
- Effective trading window: `2026-05-25` to `2026-06-12`
- Required asset coverage: pass
- Required asset expected rows: `15`
- Processed rows: `30106`
- Scoped missing date rows: `0`
- Provider missing date rows: `226`
- Duplicate bars: `0`
- Zero-volume rows: `0`

Provider-level missing rows 仍需后续治理，但不再阻塞当前已激活 advisory asset 的纸面观察门禁。

## 已修复的问题

- Profile Observation 现在会从 Daily Ops advisory tickets 记录 `observed_assets`。
- Recent Data Refresh 在存在 `observed_assets` 时，按 required assets 判断纸面门禁覆盖，同时保留 provider-level 缺失行作为审计字段。
- Recent Data Refresh 优先用 ingest trade-date 清单折算有效交易窗口，并校验 required asset 行数是否覆盖窗口内交易日；没有交易日清单时才使用周末 fallback。
- Post-refresh Replay 默认使用 recent refresh target end date 作为 paper run date。
- Expanded Observation Replay 会把扩窗建议的 end date 传给 post-refresh replay，避免用系统当天日期误触发 `signal_data_stale`。
- Project audit 已允许显式禁用的 live-order boundary 字段，不再把 `live_order_allowed=False` 误报为风险。
- 新增 GitHub Actions CI，push/PR 时运行 tests、compileall 和 project audit pass check。

## 主要风险

- 目前仅证明一个激活 profile 和一个 required asset 的纸面观察门禁可通过，不能外推为全市场、全策略可实盘。
- 初始 post-refresh replay 只有 `3 / 20` fills，需要扩窗到第 2 轮才达到 `21 / 20`，说明策略换手偏低，样本效率仍需持续观察。
- Provider-level missing date rows 为 `226`，虽然不阻塞当前标的，但后续扩大 candidate universe 前必须治理。
- 当前工作区未提交，GitHub 上没有本轮修复、文档和 CI 配置。

## 后续推进计划

1. 固化本轮成果：完成测试、审阅 diff、提交并推送当前 Phase 5.12 修复。
2. 启动连续纸面观察：每日或每个交易日刷新 Tushare 数据，记录 observation ledger、fills、drawdown、guard events、advisory asset 变化。
3. 扩大真实数据验证：对候选池 top profiles 批量跑 required-asset scoped refresh、post-refresh replay 和 observation sufficiency。
4. 治理 provider data gaps：把 `provider_missing_date_rows` 转成数据质量工单，区分新上市、停牌、真实缺口和供应商缺失。
5. 加强稳健性：增加滚动窗口、交易成本压力、成交量容量约束、行业/主题集中度和极端行情 replay。
6. 完善 paper operations：生成每日纸面指令审计、持仓漂移、风险预算、异常停止和人工复核 checklist。
7. 设计 broker boundary，但不启用 live trading：先实现只读 broker adapter mock、权限隔离、kill switch、人工确认链路和审计日志。
8. 达到多周期 paper evidence 后再讨论 live-readiness；在此之前保持 `live_boundary_allowed=false`。
