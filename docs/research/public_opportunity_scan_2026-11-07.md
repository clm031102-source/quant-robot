# 跨市场公开盘口扫描

用户已明确研究不限 ETF、股票、美港股、期权或 Polymarket。原有 CN_ETF
主线不再限制新提案的市场选择；旧研究结果和研究到纸面边界保留。
华宝证券 ETF 的新研究佣金采用用户确认的 `max(成交额 × 0.0001, 5元)`。
此费率不用于其他市场，也不回写旧研究。

已实现无需账户的 Polymarket 完整份额成本扫描：从最多五页、500个公开市场中，
选择普通二元市场，按流动性排序读取最多100个市场的两个结果盘口。以5、25、100对
净份额分别走卖盘深度，计算费用、最小金额、报价时间差和额外成本预留；无成交模拟。

2026-11-07 15:54:55 UTC 首轮：500个市场、216个符合采样条件，100个市场实际读取
200份盘口，0个正报价余量候选。所有最优卖价合计均高于1，最低1.001、最高1.04。
因此这批快照在交易费之前已经没有完整份额买入价差，不扩展相同扫描充当研究进展。
有限采样不能证明全市场永远没有机会。真实成交和已实现利润均未发生。

运行：

```powershell
.venv/Scripts/python.exe scripts/run_polymarket_complete_set_scan.py --output-dir data/reports/polymarket_complete_set/<新的快照目录>
```

输出独立 `report.html`、`report.json` 及公开响应原件；已有目录不会覆盖。
已验收快照可复制到 `data/reports/polymarket_complete_set/latest/` 后由首页
“查看公开盘口扫描结果”打开。页面刷新仅查看，不发新行情请求。

费用按官方当前的 `份额 × rate × p × (1-p)` 模型，且只支持显式费率和指数1。
同时核算现金收费与买入扣份额两种解释，保留较高成本；L2盘口不含逐订单拆分，
费用舍入仍是估算。额外预留成交成本0.2%和固定1单位是情景假设，不是兑换、网络
或资金费用的核实。双边报价不等于同时成交，未认证原子成交、钱包或实际兑换。
金额为平台抵押资产单位，不换算人民币。

官方依据：[盘口](https://docs.polymarket.com/market-data/prices-order-books)、
[市场与费用字段](https://docs.polymarket.com/market-data/market-details)、
[费用](https://docs.polymarket.com/trading/fees)、
[完整份额](https://docs.polymarket.com/concepts/positions-tokens)。

首轮本地原件：`data/reports/polymarket_complete_set/20261107_160500/`。
目录名是预先指定标识；准确采样时间以请求回执和报告UTC时间为准。
