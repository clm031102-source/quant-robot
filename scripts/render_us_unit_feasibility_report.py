"""Render saved, verified one-close affordability evidence without rerunning it."""
from __future__ import annotations

import argparse
import csv
import hashlib
from html import escape
import json
from pathlib import Path


def read_bound(ref):
    raw = Path(ref["path"]).read_bytes()
    if len(raw) != ref["bytes"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ValueError("saved_evidence_changed")
    return json.loads(raw)


def render(source, output):
    outcome = json.loads((source / "outcome.json").read_bytes())
    if outcome["status"] != "completed_single_point_quantity_only":
        raise ValueError("completed_quantity_evidence_required")
    result = read_bound(outcome["result"])
    verification = read_bound(outcome["verification"])
    if verification["status"] != "passed" or verification["result"] != outcome["result"]:
        raise ValueError("independent_verification_required")
    labels = {"old_primary": "原组合 · 主费用", "old_stress": "原组合 · 压力费用",
              "proposed_primary": "替代组合 · 主费用", "proposed_stress": "替代组合 · 压力费用"}
    summary_rows, leg_rows, csv_rows = [], [], []
    for key, label in labels.items():
        case = result["results"][key]
        summary = case["summary"]
        deployment = float(summary["economic_deployment_ratio"]) * 100
        summary_rows.append(f'<tr><th>{label}</th><td>{deployment:.2f}%</td>'
                            f'<td>${escape(summary["cash_remaining_usd"])}</td>'
                            f'<td>${escape(summary["commission_usd"])}</td>'
                            f'<td>{summary["zero_share_legs"]}</td></tr>')
        for leg in case["legs"]:
            row = dict(scenario=key, symbol=leg["symbol"], close=result["selected_closes"][leg["symbol"]],
                       quantity=leg["quantity"], modeled_buy_price=leg["buy_price_usd"],
                       commission=leg["commission_usd"], spent=leg["cash_spent_usd"],
                       remainder=leg["budget_remainder_usd"], next_share_cost=leg["next_quantity_cost_usd"])
            csv_rows.append(row)
            leg_rows.append(f'<tr><td>{label}</td><th>{leg["symbol"]}</th><td>{leg["quantity"]}</td>'
                            f'<td>${leg["buy_price_usd"]}</td><td>${leg["commission_usd"]}</td>'
                            f'<td>${leg["cash_spent_usd"]}</td><td>${leg["budget_remainder_usd"]}</td></tr>')
    old = float(result["results"]["old_primary"]["summary"]["economic_deployment_ratio"]) * 100
    proposed = float(result["results"]["proposed_primary"]["summary"]["economic_deployment_ratio"]) * 100
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>1000美元整股份额核算</title>
<style>body{{margin:0;background:#101825;color:#edf3f9;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}}
main{{max-width:1100px;margin:auto;padding:40px 24px}}h1{{font-size:32px;line-height:1.3}}a{{color:#85d7c0}}
.tag{{color:#aab8ca}}.cards{{display:flex;gap:20px;flex-wrap:wrap}}.card{{padding:22px;background:#1c293a;border-radius:14px;flex:1;min-width:200px}}
.value{{font-size:38px;color:#85d7c0}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;margin:18px 0}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #344155;white-space:nowrap}}
section{{margin-top:36px}}.note{{padding:18px;background:#202e40;border-radius:12px}}small{{color:#aab8ca}}</style>
<main><a href="/#dashboard">返回项目</a><p class="tag">已完成的单日份额核算 · 不是收益回测</p>
<h1>1000美元，四类资产能否买齐？</h1>
<p>固定使用 {escape(result["date"])} 纽约市场日线收盘价。将 SPY 换为 SPYM、GLD 换为 GLDM，EFA 与 IEF 保持一致。</p>
<div class="cards"><div class="card">原组合资产敞口<div class="value">{old:.2f}%</div><small>主费用情景，按未加滑点的收盘价计值</small></div>
<div class="card">替代组合资产敞口<div class="value">{proposed:.2f}%</div><small>手续费单列，不计入资产敞口</small></div>
<div class="card">每类资产可用预算<div class="value">$247.50</div><small>含买入费用；另保留10美元现金</small></div></div>
<section><h2>同本金、同费用下的比较</h2><div class="scroll"><table><thead><tr><th>组合与费用</th><th>资产敞口 / 本金</th><th>剩余现金</th><th>买入佣金</th><th>买不到一股的资产数</th></tr></thead>
<tbody>{''.join(summary_rows)}</tbody></table></div>
<p>主费用：每笔至少1美元、滑点10个基点；压力费用：每笔至少2.50美元、滑点30个基点。两者均按每股0.005美元计算佣金并与最低佣金取高。这些是美元费用假设，尚未核实为你的实际美股费率。</p></section>
<section><h2>具体份额和现金</h2><div class="scroll"><table><thead><tr><th>情景</th><th>ETF</th><th>整股份额</th><th>含滑点买价</th><th>佣金</th><th>本腿支出</th><th>本腿余款</th></tr></thead>
<tbody>{''.join(leg_rows)}</tbody></table></div><p><a href="quantities.csv">下载完整份额表</a> · <a href="source.json">查看结果来源与校验记录</a></p></section>
<section class="note">这项结果只说明同一预算下的整股可行性。它没有计算投资收益、回撤或未来盈利，也没有改动已部署的模拟组合。每股递增是纸面假设；报价是已收盘日观察值，不是可成交报价。每腿余款留在现金中，不能挪给其他资产。独立验算已核对16项份额及4组现金守恒。</section>
<p><small>原组合：SPY / EFA / IEF / GLD。替代组合：SPYM / EFA / IEF / GLDM。SPYM当前跟踪标普500；GLDM为黄金产品。后续收益验证必须单独执行。</small></p></main></html>'''
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(page, encoding="utf-8")
    with (output / "quantities.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    (output / "source.json").write_text(json.dumps(dict(outcome=outcome, verification=verification), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output / "index.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(render(args.source.resolve(), args.output.resolve()))
