# Quant Robot v2

轻量、清晰、真正可落地的本地多市场量化研究与模拟盘框架（支持 **A 股 ETF** 与 **美股 ETF**）。

> **安全边界**：本项目严格限定为 **研究到模拟盘（Research-to-Paper Only）**。不连接任何实盘券商、不读取真实账户、不下单、不自动实盘交易；所有本地行情与账本留在 `data/`（已加入 `.gitignore`），密钥仅通过环境变量 `TUSHARE_TOKEN` 读取。

---

## 核心特性

1. **增量容错行情缓存 (`data/market_cache/`)**：
   - A 股 ETF 通过 Tushare (`fund_daily` + `fund_adj` 后复权) 自动增量更新；
   - 美股 ETF 通过 `yfinance` 自动增量更新，并自动检测分红/拆股复权偏移；
   - 内置指数退避重试与**自动补采**，偶发网络抖动或电脑关机几天后再次运行即可无缝追平。
2. **真实交易口径回测引擎 (`backtest/simulator.py`)**：
   - 严格 **T+1 因果执行**（收盘生成信号、次日开盘/收盘成交，无未来函数）；
   - 精确模拟**整手约束**（A 股 ETF 100 股整手、美股 ETF 1 股整手）、**单笔最低佣金**（如华宝证券万 1 最低 ¥5、美股最低 $1）、单边滑点、复权总收益与回撤熔断冷却恢复；
   - 自动附带同资金、同费率、同标的池的**等权买入持有基准**对照与分年度明细。
3. **统一、幂等、可自动补采的模拟盘账本 (`paper/`)**：
   - 单一配置 [configs/portfolios.json](configs/portfolios.json) 同时管理多套 A 股与美股模拟组合；
   - 原子落盘 (`state.json`、`equity.csv`、`trades.csv`、`latest_signal.json`)，重复运行幂等安全，漏跑自动补齐。
4. **滚动样本外 Walk-Forward 验证 (`validation/walk_forward.py`)**：
   - 滚动训练期优选参数、严格在样本外测试期打分，避免单一区间过拟合。
5. **轻量本地 Web 中控台 (`http://127.0.0.1:8765`)**：
   - 零前端构建依赖，一键查看所有模拟组合净值曲线/持仓/交易记录、一键更新行情并推进模拟盘、内置真实数据回测实验室与安全审计页。

---

## 快速开始（Windows PowerShell）

```powershell
# 1. 拉取/更新 A股ETF + 美股ETF 日线缓存
.\.venv\Scripts\python.exe scripts\run_update_data.py

# 2. 运行多策略真实数据回测并生成 Markdown / SVG 对比报告（输出到 data/reports/backtests/）
.\.venv\Scripts\python.exe scripts\run_backtest.py

# 3. 运行滚动样本外 Walk-Forward 验证
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --market CN_ETF
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --market US_ETF

# 4. 推进全部启用组合的每日模拟盘（幂等 + 自动补采）
.\.venv\Scripts\python.exe scripts\run_paper_daily.py

# 5. 启动本地 Web 中控台（或直接双击 scripts\start_quant_robot_desktop.bat）
.\.venv\Scripts\python.exe scripts\run_dashboard.py --open

# 6. （可选）注册单个稳定的 Windows 每日计划任务（每天 07:30 自动更新）
.\.venv\Scripts\python.exe scripts\install_daily_task.py --repo-root F:\lhjqr --time 07:30
```

## 运行测试与安全审计

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py
```

执行四步核心校验：单元测试 (`unittest`)、字节码编译 (`compileall`)、安全边界与单文件规模审计 (`run_project_audit.py`)。

## 目录结构

```text
configs/                 # 仅 3 个清晰配置：portfolios.json / backtest_presets.json / workstations.json
docs/                    # 简洁架构说明
scripts/                 # 8 个清晰入口脚本 + 1 个桌面启动 .bat
src/quant_robot/
  ├── assets/            # 标的定义与 CN/US ETF 解析
  ├── audit/             # 安全边界与代码健康审计
  ├── backtest/          # 因果多资产回测引擎、成本与指标
  ├── config/            # Pydantic 配置与环境变量密钥读取
  ├── data/              # Tushare / yfinance / AKShare / CCXT 适配器与增量更新器
  ├── factors/           # 通用量价/技术因子
  ├── gui/               # 轻量本地 Web 中控台 (stdlib HTTP + 原生 HTML/CSS/JS)
  ├── paper/             # 统一模拟盘账本与每日容错推进器
  ├── portfolio/         # 仓位约束与调仓计划
  ├── reports/           # Markdown 报告与 SVG 曲线图
  ├── schema/            # 标准化行情/因子字段
  ├── storage/           # 原子落盘与按标的 Parquet 行情缓存
  ├── strategies/        # 固定配置 / 被动漂移 / 双动量 / 风险平价趋势
  └── validation/        # 滚动样本外 Walk-Forward 验证
tests/                   # 覆盖全链路的快速单元测试与集成测试
```

> 历史归档：重构前的全部 Codex 历史提交与文档已完整保存在 Git tag `archive-codex-20261119`，可随时回查。
