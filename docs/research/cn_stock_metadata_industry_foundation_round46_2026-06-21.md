# CN Stock Metadata Industry Foundation - Round46

日期: 2026-06-21
机器: office_desktop
任务: factor_validation
分支: codex/factor-validation-cn-stock-long-cycle-20260618

## 目标

Round46 原计划继续从公开 ETF 轮动指标切换方向，但审计发现以下公开 ETF 线已经跑过且失败:

- Round29 basic momentum / risk-adjusted momentum: 0 promotable
- Round35 raw ETF theme breadth: 0 positive Sharpe and capacity issues
- Round36 liquid-adjusted ETF theme breadth: capacity fixed, still 0 positive Sharpe
- Round45 OBV/SuperTrend strict capacity: capacity fixed, returns negative

因此本轮不再重复这些已失败路径。根据 CN stock Round15/16 审计，下一条高价值路径是:

股票因子 -> 行业/主题/ETF 广度或中性化翻译层。

这个路径需要股票行业元数据。此前本地数据只有 daily、daily_basic、moneyflow，没有 `stock_basic` 行业/板块字段。本轮补齐这个基础能力。

## 工程变更

扩展 `stock_basic` 支持字段:

- `area`
- `industry`
- `stock_market`
- `list_date`
- `delist_date`
- `is_hs`

新增脚本:

- `scripts/ingest_tushare_stock_basic.py`

新增测试:

- `tests/unit/test_tushare_stock_basic_ingest.py`

更新测试:

- `tests/unit/test_tushare_mapping.py`
- `tests/unit/test_tushare_adapter.py`

## 本地真实数据快照

命令:

```powershell
python scripts\ingest_tushare_stock_basic.py --source tushare --output-dir data\processed\cn_stock_metadata --snapshot 2026-06-21
```

结果:

- dataset: `metadata/tushare_stock_basic`
- list_status: `L`
- snapshot: `2026-06-21`
- rows: 5529
- 本地路径: `data/processed/cn_stock_metadata/metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-21/part-00000.parquet`

该数据留在本地，不提交 Git。

## 覆盖审计

- A 股当前上市股票: 5529
- 行业数: 110
- 行业缺失: 9

股票板块分布:

| 板块 | 数量 |
|---|---:|
| 主板 | 3199 |
| 创业板 | 1399 |
| 科创板 | 610 |
| 北交所 | 321 |

前 10 大行业:

| 行业 | 数量 |
|---|---:|
| 电气设备 | 347 |
| 元器件 | 308 |
| 专用机械 | 291 |
| 软件服务 | 281 |
| 汽车配件 | 265 |
| 化工原料 | 256 |
| 半导体 | 194 |
| 医疗保健 | 182 |
| 化学制药 | 148 |
| 通信设备 | 137 |

## 验证

- `python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_stock_basic_ingest`
- `python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_stock_basic_ingest tests.unit.test_project_audit`
- `python scripts/run_project_audit.py --json`

结果: 42 个相关单测通过，项目审计通过。

## 结论

本轮新增盈利因子: 0

本轮有用成果:

- 补齐了行业/板块元数据入口。
- 为后续行业中性、行业内 RankIC、股票到 ETF/theme 广度桥接提供可重复数据基础。
- 避免在缺映射数据时伪造“ETF 桥接”。

下一步不应继续发明单一价格/资金流指标。Round47 复盘后，优先选择:

1. 行业内中性化/行业内 RankIC 审计。
2. 股票强 RankIC 因子的行业广度翻译。
3. 若需要 ETF 桥接，再补 ETF 成分或指数权重映射，而不是用主题名称硬凑。
