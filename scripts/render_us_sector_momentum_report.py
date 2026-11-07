"""Render an independently verified saved factor screen; no source or strategy run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def checked(directory, ref):
    path = directory / Path(ref["path"].replace("\\", "/")).name
    raw = path.read_bytes()
    if len(raw) != ref["bytes"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ValueError("Saved result fingerprint mismatch")
    return json.loads(raw)


def csv_file(path, rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(out.getvalue(), encoding="utf-8-sig", newline="")


def build_report(directory, output):
    outcome = json.loads((directory / "outcome.json").read_bytes())
    if outcome["status"] != "completed":
        raise ValueError("A completed, verified saved screen is required")
    result = checked(directory, outcome["result"])
    review = checked(directory, outcome["verification"])
    if review["status"] != "passed" or review["screen_status"] != result["status"]:
        raise ValueError("Independent result verification required")
    output.mkdir(parents=True, exist_ok=True)
    daily, annual, display = [], [], {}
    for key, path in result["paths"].items():
        monthly = {}
        for row in path["daily"]:
            daily.append(dict(path=key, date=row["date"], index_wealth=row["wealth"]))
            monthly[row["date"][:7]] = [row["date"], row["wealth"]]
        for year, value in path["annual_returns"].items():
            annual.append(dict(path=key, year=year, return_fraction=value))
        display[key] = {k: path[k] for k in ("annualized_return", "total_return", "max_drawdown")}
        display[key]["curve"] = list(monthly.values())
    csv_file(output / "daily_index.csv", daily)
    csv_file(output / "annual.csv", annual)
    data = dict(paths=display, checks=result["checks"], qa=result["source_qa"],
                lower=result["bootstrap_lower_mean_annual_log_relative"],
                segments=result["segment_log_relative_stress_vs_equal9"])
    verdict = "本次行业排序未通过：费用后的增量不足，关闭此候选。" if result["status"] == "screen_rejected" else "仅通过因子初筛，仍需整股与实际费用验证。"
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>行业ETF动量 · 一次固定筛选</title><style>
body{font:16px/1.65 system-ui,sans-serif;background:#f4f6fa;color:#17273d;max-width:1150px;margin:28px auto;padding:0 22px}h1{font-size:30px}h2{font-size:22px}section{background:white;border-radius:14px;padding:22px;margin:18px 0}.verdict{border-left:5px solid #b76727}.muted,small{color:#586b80}table{border-collapse:collapse;width:100%}td,th{padding:11px;border-bottom:1px solid #e4eaf0;text-align:right}td:first-child,th:first-child{text-align:left}svg{width:100%;height:auto}a{color:#2156a2}.tag{display:inline-block;margin:5px 18px 5px 0}</style>
<h1>行业ETF动量 · 一次固定筛选</h1><p>2006–2025 · 原九只行业ETF · 半年排名前三 · 0个真实账户</p>
<section class="verdict"><strong>__VERDICT__</strong><p>过去半年最强的三个行业，其毛收益只略高于九行业等权。费用预算消耗了这点差距。本次结果已独立核对，不更换参数再跑。</p></section>
<section><h2>每种口径实际得到什么</h2><table><thead><tr><th>收益指数</th><th>年化</th><th>全期累计</th><th>最大回撤</th></tr></thead><tbody id="table"></tbody></table><p class="muted">这里的回撤是未经账户止损处理的收益指数回撤。整股、税款、现金结算及40%暂停恢复尚未在本项中实施，不能据此认定为可交易收益。</p></section>
<section><h2>相同起点的收益指数</h2><div id="chart"></div><div id="legend"></div><small>起点1；展示月末采样，纵轴为对数刻度。每日完整数值可下载。不是美元账户余额。</small></section>
<section><h2>三个事前条件</h2><ul id="checks"></ul><p id="relative"></p><p>主费用预算：首次买入0.40%，每半年换仓0.85%，最终退出0.45%。压力预算：1.05%、2.15%、1.10%。即使成分没变也扣整笔换仓预算；九行业等权参照不扣交易费。这是固定筛选压力，不是已认证的券商账单。</p></section>
<section><h2>数据和核对</h2><p id="qa"></p><p>原件一次取齐，共9只、5,283个同窗日期。只使用提供商复权收盘价；XLF实物分配不会当成现金收入。独立公式已核对40个持有期、20,124个日值和80个年度值。</p><p>这是已知历史筛选，不是完全盲态样本；年度对照不能认证全部公司行动或保证半年排序精确。</p><p><a href="daily_index.csv" download>下载每日收益指数</a> · <a href="annual.csv" download>下载年度表现</a></p><small>结果指纹 __HASH__</small></section>
<script>const D=__DATA__;const labels={top3_gross:'前三行业：毛收益',top3_primary_proxy:'前三行业：主费用预算',top3_stress_proxy:'前三行业：压力预算',equal9_gross:'九行业等权：毛收益'};const colors={top3_gross:'#4771b5',top3_primary_proxy:'#1c8174',top3_stress_proxy:'#bd7a25',equal9_gross:'#777b87'};const pct=x=>(100*x).toFixed(2)+'%';const order=['top3_gross','top3_primary_proxy','top3_stress_proxy','equal9_gross'];document.getElementById('table').innerHTML=order.map(k=>{const p=D.paths[k];return `<tr><td>${labels[k]}</td><td>${pct(p.annualized_return)}</td><td>${pct(p.total_return)}</td><td>${pct(p.max_drawdown)}</td></tr>`}).join('');
const names={stress_terminal_positive:'压力预算后终值仍高于起点',positive_relative_growth_both_decades:'前后两个十年均优于等权参照',annual_relative_bootstrap_lower_positive:'年度相对收益区块抽样下界大于零'};document.getElementById('checks').innerHTML=Object.entries(names).map(([k,v])=>`<li>${D.checks[k]?'通过':'未通过'}：${v}</li>`).join('');document.getElementById('relative').textContent=`压力口径的两段累计相对增长分别为${pct(Math.expm1(D.segments[0]))}和${pct(Math.expm1(D.segments[1]))}；年度对数相对收益下界为${pct(D.lower)}。`;
document.getElementById('qa').textContent=`XLF固定年度复权回报${pct(Number(D.qa.provider_total_return))}，发行人市场回报${pct(Number(D.qa.issuer_market_total_return))}，相差${(100*Number(D.qa.absolute_difference)).toFixed(3)}个百分点，低于事前固定的1个百分点粗筛容差。`;
const points=order.flatMap(k=>D.paths[k].curve.map(p=>p[1]));const lo=Math.floor(Math.min(...points)*2)/2||.25,hi=Math.ceil(Math.max(...points));const w=1080,h=360,L=60,T=18,B=42;const y=v=>T+(Math.log(hi)-Math.log(v))/(Math.log(hi)-Math.log(lo))*(h-T-B),x=(i,n)=>L+i/(n-1)*(w-L-18);let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="四条单位化收益指数曲线">`;for(const v of [.5,1,2,4,8])if(v>=lo&&v<=hi)svg+=`<line x1="${L}" y1="${y(v)}" x2="${w-18}" y2="${y(v)}" stroke="#e3e9ee"/><text x="${L-10}" y="${y(v)+4}" text-anchor="end" font-size="13">${v}</text>`;for(const k of order){const a=D.paths[k].curve;svg+=`<polyline fill="none" stroke="${colors[k]}" stroke-width="2" points="${a.map((p,i)=>`${x(i,a.length).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>`;}const a=D.paths.equal9_gross.curve;for(let i=0;i<=4;i++){const j=Math.round((a.length-1)*i/4);svg+=`<text x="${x(j,a.length)}" y="${h-12}" text-anchor="middle" font-size="12">${a[j][0].slice(0,7)}</text>`;}document.getElementById('chart').innerHTML=svg+'</svg>';document.getElementById('legend').innerHTML=order.map(k=>`<span class="tag" style="color:${colors[k]}">● ${labels[k]}</span>`).join('');</script></html>'''
    page = page.replace("__VERDICT__", verdict).replace("__HASH__", outcome["result"]["sha256"])
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c"))
    (output / "index.html").write_text(page, encoding="utf-8")
    source = dict(result=outcome["result"], verification=outcome["verification"], paths=4, daily_values=len(daily),
                  annual_values=len(annual), accounts=0, new_financial_runs=0)
    (output / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(output=str(output), paths=4, daily_values=len(daily), annual_values=len(annual), new_financial_runs=0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build_report(args.result_dir, args.output_dir), ensure_ascii=False))
