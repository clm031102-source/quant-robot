# 有限未来 ETF 来源观察器

本模块填补先有合格候选才能采集、先有暖机数据才能激活的循环依赖。它仅保存未来实际收到的来源与身份、日期、字段和时钟证据，不生成账户、信号或资格。当前仅完成工程与人工测试，未创建真实来源准入，未访问凭据或网络。

## 独立入口与默认关闭

`scripts/run_future_etf_source_observer.py --date YYYY-MM-DD --scope-sha256 <exact>` 默认只预览；`--execute` 仍必须通过全部检查。固定 `configs/future_etf_source_observer_admission.json` 不随代码提供。缺失、错误、过期或未双审时，生产入口在 PM、凭据和 HTTP 之前关闭。

准入文件仅四个字段：`artifact_type=future_etf_source_release_v1`，以及 `scope`、`root_review`、`manager_review` 三个原件引用。引用均为绝对 `path/sha256/bytes`。两份独立审查必须精确绑定同一 scope、实现摘要、日期、请求数、截止和授权类别，并在首个观察日北京时间零点前接受。

scope 的固定结构由 `validate_plan`、`load_authority` 定义：

- `artifact_type=finite_future_etf_observer_scope_v1`、`purpose=future_source_observation_only`；上下文 office_desktop/data_pipeline/专用 branch。
- 两只标的固定 510300.SH、518880.SH，接口 fund_daily，字段固定 `ts_code,trade_date,open,high,low,close,vol,amount`。请求只允许单一 `ts_code/trade_date`，不提供 latest、历史范围、分页、补数或修订轮询。
- `calendar` 为明确 Asia/Shanghai 交易日元信息原件；`slots` 是该日历内完整连续区间，每项只有 `date/not_before/deadline`。各时窗不早于当日 15:30 和日历标明的可观察时点，不跨北京时间日界，最长四小时。
- `created_at/expires_at/authority_kind`、精确 `request_budget=2×日期数`、`body_byte_budget=262144×请求数`；最多二十个显式日期。请求体预算不代表底层 TLS/HTTP 流量。
- `campaign_72h` 只接受单日 2026-11-09，截止不得晚于 2026-11-09T16:21:39Z。更长观察必须是两审明确接受的 `separately_authorized_finite` 新来源范围，最长四十五自然日；工程代码或本轮授权不构成该许可。
- `implementation` 绑定 Python/OpenSSL/优化标志、解释器原件、numpy/pandas/pydantic 版本、本地静态 import closure；`head`、`protocol_bindings`、必要来源定义/单位/权限费用依据的 `bindings` 也由 exact scope 双审冻结。所有引用保留 raw bytes 摘要。PM 自身必读文件的通用换行文本摘要只用于核其回执，不替代 raw 绑定。
- 固定全项目 `ledger_directory=F:/lhjqr/data/reports/future_etf_source_observer`，避免换工作树或新 scope 重复取同一天。该生产目录本轮没有被创建或写入。
- `financial_decode_allowed=false/qualified=false/real_forward=0`。

review 的固定字段为 `artifact_type=future_etf_source_exact_review_v1`、`reviewer=root|manager`、`status=accepted_exact_source_observation`、`scope_sha256/implementation_sha256/authority_kind/dates/request_budget/expires_at/source_only/accepted_at`。不自动生成这些回执。

整段有限 release 执行期间，绑定的代码、协议、配置、原件与环境必须冻结。后续合法升级或换 release 要保留旧字节、旧引用及可核恢复映射；不能把当前路径的新摘要追贴为旧来源证据。本模块不自动迁移或改写已消费证据。

## 执行与失败

每次调用仅采一个已授权且正处于时窗中的当日。先核全部原件和真实 PM，再创建独占、flush+fsync 的每日 claim；读取环境凭据后，每只 ETF 请求前另存 claim。复用既有 HTTPS 单次 POST 有界进程：每件 256KiB、40 秒、零重试、零重定向；两件整次最多 150 秒且受时窗截止约束。该调用不会循环等待下个交易日。

每日目录和 claim 保留失败消费记录，同日不得恢复或补另一只。一般失败允许后续已授权独立日期继续，但缺日始终保留。进程退出或 dispatch 状态不明时，精确请求/接收次数保持 unknown，保留已知下界，并写全局 halt 阻止自动继续其他日期。中断留下有日期的目录而缺 claim/outcome，或 outcome 未确认全部进程退出，同样阻断下一日；只查保存的元信息，不读历史响应数值。不能用文件当时不存在推断没有请求。人工恢复核查不由本模块自动执行。

完整响应只有通过秘密回显安全检查后才保存。无效或截断响应不能安全保留时，保存失败原因及接收下界，不把残件称完整。日期暴露分为预约、可能/部分暴露和完整结构观察；没有原件不等于没有暴露。最终逐一核对原始 claim、receipt、原件与 frozen refs，禁止事后重新定义原件摘要。

未来日期的真实响应仍是价格/量额暴露，即使没有数值转换。只投影身份、日期和结构，不把这些新观察改称封存历史，也不打开原 2026 历史价格入口。

完整日的接收时钟要求 `request_started_at ≤ headers_received_at ≤ body_completed_at ≤ retained_at ≤ 当前时钟`，并全部处于已定时窗。缺少 headers 时钟、内部倒序或晚收只能保留未知/失败，不计完整日；HTTP 状态、安全筛过的 headers、失败时点和安全屏未保留原因单独留存。

## 暖机与限制

`capture_synthetic` 显式注入人工 clock/transport，并永久标记人工；它不授网络权限。`paired_coverage` 只核调用者提供的已审原件链，且只累计两标的同日完整、时钟有效的真实来源结构。不能跳过缺日挑二十条；改 outcome 一个标记不能覆盖 claim/receipt 的人工身份。共同二十日只是来源结构计数，始终 `ready_for_candidate=false`。旧单标的二十一日门槛保持。

本模块不确认数值质量、provider 日线终版、ETF 当日停复牌/限价、盘口成交性、公司行动全集或个人到账。单位转换及 portfolio-specific 暖机适配必须另审；工程测试、来源采集和合格真实前向分别记账。当前没有新研究、账户、合格候选或真实前向天数。

PM 专用模式 `finite_future_etf_source_observation_only` 只打开 `future_source_observation_allowed`；其余金融/holdout/live allowed 全部关闭。未准入模式显式 blocked。新 ops hook 在不匹配任务/分支时先早退，不读取任何来源或金融准入文件。原 34 个 research scope 的实际 PM 闭合循环不变，新增 ops hook 另测并加入 `_PM_FILES` 原件目录。
