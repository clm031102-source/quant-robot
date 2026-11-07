"""Render retained five-year accounts; never run a strategy or fetch prices."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_us_unit_feasibility import bound, pin

LABELS = {"old_primary": "原篮子 · 基础费用", "old_stress": "原篮子 · 较高费用",
          "new_primary": "低单价篮子 · 基础费用", "new_stress": "低单价篮子 · 较高费用", "cash": "现金对照"}
COLORS = {"old_primary": "#778fb6", "old_stress": "#a5b6cf", "new_primary": "#087e6d", "new_stress": "#d78827", "cash": "#949494"}


def money(value):
    return f"{Decimal(str(value)):,.2f}"


def pct(value):
    return f"{Decimal(str(value))*100:.2f}%"


def chart(accounts, labels=None, colors=None):
    labels = LABELS if labels is None else labels
    colors = COLORS if colors is None else colors
    values = {role: [float(d["NAV"]) for d in account["days"]] for role, account in accounts.items()}
    lo = min(min(v) for v in values.values())
    hi = max(max(v) for v in values.values())
    padding = max(20, (hi-lo)*.08)
    lo, hi = lo-padding, hi+padding
    width, height = 1050, 350
    x = lambda i, n: 70 + i/max(1, n-1)*950
    y = lambda v: 20 + (hi-v)/(hi-lo)*285
    body = ['<svg viewBox="0 0 1050 350" role="img" aria-label="五个账户每日账面净值曲线，美元">']
    for i in range(5):
        value = lo+(hi-lo)*i/4
        yy = y(value)
        body.append(f'<line x1="70" y1="{yy:.2f}" x2="1020" y2="{yy:.2f}" stroke="#e5e9ed"/><text x="60" y="{yy+4:.2f}" text-anchor="end" fill="#6b7280" font-size="12">{value:,.0f}</text>')
    for role, vector in values.items():
        points = " ".join(f"{x(i,len(vector)):.2f},{y(v):.2f}" for i, v in enumerate(vector))
        body.append(f'<polyline id="line-{role}" points="{points}" fill="none" stroke="{colors[role]}" stroke-width="{2.4 if role.startswith("new") else 1.6}"><title>{labels[role]}</title></polyline>')
    dates = [d["date"] for d in next(iter(accounts.values()))["days"]]
    for year in range(2021, 2026):
        indices = [i for i, d in enumerate(dates) if d.startswith(str(year))]
        if indices:
            body.append(f'<text x="{x(indices[0],len(dates)):.2f}" y="335" fill="#6b7280" font-size="12">{year}</text>')
    return "".join(body)+"</svg>"


def render(result_path, output):
    result_ref = pin(result_path)
    result = json.loads(bound(result_ref))
    if result["schema"] != "us_low_unit_allocation_result_v1" or result["account_count"] != 5:
        raise ValueError("completed_fixed_five_account_result_required")
    accounts = {role: json.loads(bound(ref)) for role, ref in result["accounts"].items()}
    for role, ref in result["verifications"].items():
        check = json.loads(bound(ref))
        if check["account"] != result["accounts"][role] or check["status"] != "recorded_account_consistent":
            raise ValueError("independent_saved_account_verification_required")
    output.mkdir(parents=True, exist_ok=True)
    summaries = result["summaries"]
    ordered = ["old_primary", "old_stress", "new_primary", "new_stress", "cash"]
    rows, csv_rows = [], []
    for role in ordered:
        s = summaries[role]
        cells = [LABELS[role], money(s["cash_and_locked_sale_proceeds_net_profit"]), money(s["terminal_book_net_profit"]),
                 pct(s["book_CAGR"]), pct(s["observed_maxDD"]), pct(s["average_market_deployment_ratio"]),
                 str(s["fills"]), money(s["same_path_total_execution_cost"])]
        rows.append('<tr>'+''.join(f'<td>{escape(c)}</td>' for c in cells)+'</tr>')
        csv_rows.append(cells)
    headers = ["账户", "现金＋待到账卖款净赚", "账面净赚", "账面年化", "最大回撤", "平均投入", "成交笔数", "全部执行成本"]
    table = '<table><thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    annual = '<table><thead><tr><th>年份</th>'+''.join(f'<th>{LABELS[r]}</th>' for r in ordered)+'</tr></thead><tbody>'
    for year in range(2021, 2026):
        annual += f'<tr><td>{year}</td>'+''.join(f'<td>{money(accounts[r]["annual_contributions"].get(str(year),0))}</td>' for r in ordered)+'</tr>'
    annual += '</tbody></table>'
    terminal = '<table><thead><tr><th>账户</th><th>已到账现金</th><th>待到账卖款</th><th>待收分红</th><th>待收零股款</th><th>剩余持仓</th></tr></thead><tbody>'
    for role in ordered:
        s = summaries[role]
        terminal += '<tr><td>'+LABELS[role]+'</td>'+''.join(f'<td>{money(s[k])}</td>' for k in
            ('terminal_settled_cash','terminal_locked_cash','terminal_dividend_receivable','terminal_cash_in_lieu_receivable','terminal_inventory_value'))+'</tr>'
    terminal += '</tbody></table>'
    new = summaries["new_primary"]
    stress = summaries["new_stress"]
    delta = Decimal(new["cash_and_locked_sale_proceeds_net_profit"])-Decimal(summaries["old_primary"]["cash_and_locked_sale_proceeds_net_profit"])
    stress_delta = Decimal(stress["cash_and_locked_sale_proceeds_net_profit"])-Decimal(summaries["old_stress"]["cash_and_locked_sale_proceeds_net_profit"])
    passed = result["fixed_conditional_evaluation_passed"]
    verdict = "完成五年条件检验" if passed else "本轮未达到预定条件"
    verdict_body = "低单价篮子在两档费用下均为正收益，回撤低于40%，终点已平仓，独立核账通过。" if passed else "按执行前固定的判据，这次比较未通过；保留全部结果，不改参数重算。"
    if stress_delta < 0:
        verdict_body += f" 但在较高费用下，它比原篮子少赚{money(-stress_delta)}美元，不能认定有稳健优势。"
    legends = ''.join(f'<label><input type="checkbox" checked onchange="document.getElementById(\'line-{r}\').style.display=this.checked?\'\':\'none\'"><span style="color:{COLORS[r]}">{LABELS[r]}</span></label>' for r in ordered)
    cards = [("低单价篮子 · 五年净赚", f'${money(new["cash_and_locked_sale_proceeds_net_profit"])}', "已到账现金＋待到账卖款，扣除初始$1,000"),
             ("较高费用下 · 五年净赚", f'${money(stress["cash_and_locked_sale_proceeds_net_profit"])}', "最低佣金$2.50／笔，单边滑点0.30%"),
             ("相对原篮子 · 净利润变化", f'${money(delta)}', "基础费用，同起点、同风险、同调仓规则"),
             ("低单价篮子 · 最大回撤", pct(new["observed_maxDD"]), "每日账面净值观察值")]
    card_html = ''.join(f'<div class="card"><small>{a}</small><strong>{b}</strong><p>{c}</p></div>' for a,b,c in cards)
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>五年整股配置对比</title>
<style>body{{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f4f6f8;color:#1e2b38;margin:0}}main{{max-width:1180px;margin:32px auto;padding:0 22px}}h1{{font-size:34px;margin:12px 0}}h2{{font-size:21px;margin-top:0}}p{{line-height:1.7;color:#526170}}.top{{color:#087e6d;font-weight:700}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}}.card,section{{background:white;border:1px solid #e1e7eb;border-radius:14px;padding:23px;margin:18px 0}}.card strong{{display:block;font-size:29px;margin-top:12px}}.card p{{font-size:12px;margin-bottom:0}}small{{color:#657586}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}th,td{{padding:13px 10px;text-align:right;border-bottom:1px solid #e8edf0}}th:first-child,td:first-child{{text-align:left}}th{{color:#627383;font-weight:600}}svg{{width:100%;height:auto}}.legend{{display:flex;flex-wrap:wrap;gap:17px;font-size:13px}}a{{color:#087e6d}}.note{{font-size:13px}}@media(max-width:850px){{.cards{{grid-template-columns:1fr 1fr}}h1{{font-size:28px}}}}@media(max-width:500px){{.cards{{grid-template-columns:1fr}}}}</style>
<main><div class="top">量化工程 · 已保存账户的真实结果</div><h1>用更低的单价，把四类资产真正配起来</h1><p>2021–2025 · 初始1,000美元 · 每月四等份 · 整股交易 · 单独计费与到账</p>
<section><h2>{verdict}</h2><p>{verdict_body}</p><p class="note">这是已知历史上的条件模型比较。合格策略仍为0，真实前向记录仍为0；此页不把历史盈利当作未来盈利承诺，也不更改已部署的模拟任务。</p></section>
<div class="cards">{card_html}</div><section><h2>五个账户的每日账面净值</h2><div class="legend">{legends}</div>{chart(accounts)}<p class="note">单位：美元。曲线包含尚未到账的应收款；末日按开盘价格清仓。点击图例可显示或隐藏曲线。</p></section>
<section><h2>相同本金，实际差多少</h2><p class="note">原篮子：SPY／EFA／IEF／GLD；低单价篮子：SPYM／EFA／IEF／GLDM。基础费用为最低$1／笔、单边滑点0.10%；较高费用为最低$2.50／笔、单边滑点0.30%。这些是美元账户的情景假设。</p><div class="scroll">{table}</div><p class="note">全部执行成本包括佣金、卖出费、滑点及零股处理成本。平均投入反映资金实际进入持仓的比例，不是收益率。</p></section>
<section><h2>逐年赚亏金额</h2><div class="scroll">{annual}</div><p class="note">每年账面损益，单位美元；不是各年复投后的单独收益率。</p></section>
<section><h2>终点的钱在哪里</h2><div class="scroll">{terminal}</div><p class="note">待到账卖款仍未进入可用现金；分红和零股应收款另列，均不计入本页“现金＋待到账卖款净赚”。这里的“已到账”是模型账本状态，实际券商提款规则未核实。</p></section>
<section><h2>本次固定规则</h2><p>每月收盘确定目标，下一交易日卖出，第3个交易日锁定各自买入预算，第4个交易日买入。保留10美元现金，不借款。日亏2%或从连续净值高点回撤40%触发暂停，完整空仓5日后等待下一次月度机会。</p><p class="note">包含2022年GLDM二合一反向拆股；零股款按事件开盘价和固定费用估算，基础情景45日、较高费用90日后才计入可用现金。历史价格还原、成交容量、分红税费及到账日期仍有条件假设。本次先固定方法，再运行5个账户一次；未搜索参数。</p><p><a href="summary.csv" download>下载账户对比表</a></p></section></main></html>'''
    (output / "index.html").write_text(page, encoding="utf-8")
    with (output / "summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(csv_rows)
    (output / "source.json").write_text(json.dumps(dict(result=result_ref, accounts=result["accounts"],
        verifications=result["verifications"], rendering_only=True), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return dict(page=str(output / "index.html"), accounts=5, financial_runs=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.result, args.output), ensure_ascii=False))
