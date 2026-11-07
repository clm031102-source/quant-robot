"""Compare saved monthly and passive-drift accounts without rerunning either."""
import argparse
import csv
from decimal import Decimal
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_us_unit_feasibility import pin, bound
from render_us_low_unit_allocation_report import chart, money, pct


def render(result_path, output):
    result_ref = pin(result_path)
    result = json.loads(bound(result_ref))
    if result["schema"] != "us_passive_drift_result_v1" or result["account_count"] != 2:
        raise ValueError("completed_drift_result_required")
    base = json.loads(bound(result["baseline"]))
    accounts, labels, colors = {}, {}, {}
    for cost, cn in (("primary", "基础费用"), ("stress", "较高费用")):
        for policy, parent, role, label, color in (
            ("monthly", base, "new_"+cost, "每月再平衡", "#7b91b5" if cost == "primary" else "#aaa0b7"),
            ("drift", result, cost, "持仓不再平衡", "#087e6d" if cost == "primary" else "#d38d2e"),
        ):
            key = policy+"_"+cost
            account_ref = parent["accounts"][role]
            check = json.loads(bound(parent["verifications"][role]))
            if check["status"] != "recorded_account_consistent" or check["account"] != account_ref:
                raise ValueError("saved_account_verification")
            accounts[key] = json.loads(bound(account_ref))
            labels[key], colors[key] = label+" · "+cn, color
    accounts["cash"] = json.loads(bound(base["accounts"]["cash"]))
    labels["cash"], colors["cash"] = "现金对照", "#929292"
    ordered = [k for k in accounts if k != "cash"]
    headers = ["规则与费用", "五年净赚 USD", "账面年化", "最大回撤", "成交笔数", "执行成本 USD", "平均投入"]
    rows = []
    for key in ordered:
        s = accounts[key]["summary"]
        rows.append([labels[key], money(s["cash_and_locked_sale_proceeds_net_profit"]), pct(s["book_CAGR"]),
            pct(s["observed_maxDD"]), str(s["fills"]), money(s["same_path_total_execution_cost"]), pct(s["average_market_deployment_ratio"])])
    def table(head, body):
        return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in body)+'</tbody></table></div>'
    annual = [[str(y)]+[money(accounts[k]["annual_contributions"].get(str(y), 0)) for k in ordered] for y in range(2021, 2026)]
    terminal = [[labels[k]]+[money(accounts[k]["summary"][f]) for f in
        ("terminal_settled_cash", "terminal_locked_cash", "terminal_dividend_receivable", "terminal_cash_in_lieu_receivable", "terminal_inventory_value")] for k in ordered]
    legends = ''.join(f'<label><input type="checkbox" checked onchange="document.getElementById(\'line-{k}\').style.display=this.checked?\'\':\'none\'"><span style="color:{colors[k]}">{labels[k]}</span></label>' for k in accounts)
    primary, stress = result["differences_from_saved_monthly"]["primary"], result["differences_from_saved_monthly"]["stress"]
    cards = [("较高费用 · 五年净赚", '$'+money(result["summaries"]["stress"]["cash_and_locked_sale_proceeds_net_profit"])),
        ("较高费用 · 比每月调仓多赚", '$'+money(stress["cash_and_locked_sale_proceeds_net_profit"])),
        ("基础费用 · 净利润变化", '$'+money(primary["cash_and_locked_sale_proceeds_net_profit"])),
        ("较高费用 · 最大回撤", pct(result["summaries"]["stress"]["observed_maxDD"]))]
    card_html = ''.join(f'<div class="card"><small>{a}</small><strong>{b}</strong></div>' for a,b in cards)
    passed = "两档费用均为正收益，最大回撤低于40%，末端平仓并通过独立核账。" if result["fixed_conditional_evaluation_passed"] else "未通过执行前固定的数值条件，结果保留，不改规则重算。"
    improved = "较高费用下，净收益增加且执行成本下降。" if result["stress_practical_improvement"] else "较高费用下，没有同时做到净收益增加和成本下降。"
    primary_delta = Decimal(primary["cash_and_locked_sale_proceeds_net_profit"])
    tradeoff = f"基础费用下比每月再平衡{'少赚' if primary_delta < 0 else '多赚'}{money(abs(primary_delta))}美元。"
    if all(Decimal(x["observed_maxDD"]) > 0 for x in (primary, stress)):
        tradeoff += "两档费用下回撤均有所增加。"
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>少调仓是否更赚钱</title>
<style>body{{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f4f6f8;color:#1e2b38;margin:0}}main{{max-width:1180px;margin:32px auto;padding:0 22px}}h1{{font-size:34px}}h2{{font-size:21px;margin-top:0}}p{{line-height:1.75;color:#526170}}.tag{{font-weight:700;color:#087e6d}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}}.card,section{{background:white;border:1px solid #e1e7eb;border-radius:14px;padding:23px;margin:18px 0}}.card strong{{display:block;font-size:28px;margin-top:12px}}small{{color:#657586}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}th,td{{padding:13px 10px;text-align:right;border-bottom:1px solid #e8edf0}}th:first-child,td:first-child{{text-align:left}}th{{color:#627383}}svg{{width:100%;height:auto}}.legend{{display:flex;flex-wrap:wrap;gap:17px;font-size:13px}}.note{{font-size:13px}}a{{color:#087e6d}}@media(max-width:850px){{.cards{{grid-template-columns:1fr 1fr}}}}@media(max-width:500px){{.cards{{grid-template-columns:1fr}}h1{{font-size:27px}}}}</style>
<main><div class="tag">第30项研究 · 同一份五年输入，仅新增两个账户</div><h1>少调仓能省钱，收益仍有取舍</h1><p>2021–2025 · 初始1,000美元 · SPYM／EFA／IEF／GLDM · 原风险退出规则保留</p>
<section><h2>这次实际发现了什么</h2><p>{passed} {improved} {tradeoff} 不能把“少交易”直接等同于“赚更多”。</p><p class="note">这是看过上一项结果后提出的条件诊断，沿用同一历史输入，不是独立盲测。合格策略0、真实前向0，既有日常模拟任务未改变。</p></section>
<div class="cards">{card_html}</div><section><h2>完整账户对比</h2><p class="note">基础费用：最低$1／笔、单边滑点0.10%；较高费用：最低$2.50／笔、滑点0.30%。利润均为已到账现金＋待到账卖款，减初始本金，未计入末端待收分红。</p>{table(headers,rows)}</section>
<section><h2>每日账面净值</h2><div class="legend">{legends}</div>{chart(accounts,labels,colors)}<p class="note">单位美元；净值包含应收款，末日使用开盘价格。点击图例切换曲线。</p></section>
<section><h2>逐年账面损益</h2>{table(['年份']+[labels[k] for k in ordered],annual)}</section>
<section><h2>唯一改变的规则</h2><p>只要还持有任何一只ETF，就跳过普通月末再平衡，分红到账也留作现金。初次建仓或按原风控全部退出后，仍须等正常月末，按原四等份目标和既定交易日期重新建仓。</p><p>日亏2%、连续高点回撤40%、5个完整空仓日冷却以及终点退出全部保留。部分资产买入失败时，只要其他资产有持仓，就不会临时补齐；风险造成的清仓和重新入场仍然会产生成本。</p><p class="note">没有搜索调仓频率或权重偏离阈值；原月度账户只读保存结果，未重跑。两种规则都依赖同样的历史价格还原、费用、成交容量、分红和到账假设，实际美股账户费率仍待确认。</p></section>
<section><h2>期末资金分布</h2>{table(['账户','已到账现金','待到账卖款','待收分红','待收零股款','剩余持仓'],terminal)}<p class="note">待到账卖款不是立即可提款的现金。“已到账”是模型账本状态，不代表真实券商账户。</p><p><a href="summary.csv" download>下载两种规则的对比表</a></p></section></main></html>'''
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(page, encoding="utf-8")
    with (output / "summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(rows)
    (output / "source.json").write_text(json.dumps(dict(result=result_ref, baseline=result["baseline"],
        accounts=result["accounts"], verifications=result["verifications"], financial_runs=0), indent=2)+"\n", encoding="utf-8")
    return dict(page=str(output / "index.html"), compared_accounts=4, new_financial_runs=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.result, args.output), ensure_ascii=False))
