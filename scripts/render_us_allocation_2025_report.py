"""Render the three saved 2025 accounts; no source reads or strategy execution."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream,fieldnames=keys)
    writer.writeheader()
    writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
    path.write_text(stream.getvalue(),encoding="utf-8-sig",newline="")


def build_report(directory, output):
    raw = (directory/"result.json").read_bytes()
    result = json.loads(raw)
    if result.get("historical_returns_computed") is not True or result.get("account_count") != 3:
        raise ValueError("Expected three completed real historical accounts")
    review_raw = (directory/"actual_independent_accounting_review.json").read_bytes()
    review = json.loads(review_raw)
    if (review.get("status") != "recorded_accounting_consistent"
            or review.get("result_sha256") != hashlib.sha256(raw).hexdigest()
            or review.get("accounts_checked") != 3):
        raise ValueError("Exact saved result needs an independent accounting review")
    data, rows, trades = {}, [], []
    for role in ("primary", "stress", "cash"):
        account_raw = (directory/"accounts"/role/"account.json").read_bytes()
        if hashlib.sha256(account_raw).hexdigest() != result["accounts"][role]["artifact"]["sha256"]:
            raise ValueError("Saved account digest mismatch")
        account = json.loads(account_raw)
        if account["schema"] != "us_fixed_allocation_2025_account_v1" or not account["historical_returns_computed"]:
            raise ValueError("Unexpected account identity")
        summary = account["summary"]
        if float(summary["initial_cash"]) != 1000 or any(not d["date"].startswith("2025-") for d in account["days"]):
            raise ValueError("USD1000 and fixed2025 window required")
        daily = account["days"]
        data[role] = dict(summary=summary, unheld=account["unheld_asset_sessions"],
                         zero_targets=len(account["zero_share_target_legs"]),
                         curve=[[d["date"],float(d["NAV"])] for d in daily])
        for d in daily:
            rows.append(dict(role=role,date=d["date"],NAV=d["NAV"],
                spendable=d["after"]["spendable_cash"],locked=d["after"]["locked_cash"],
                positions=d["after"]["quantities"],receivables=d["after"]["receivables"],
                paused=d["paused"],drawdown=d["observed_maxDD"]))
        trades.extend(dict(role=role,**fill) for fill in account["fills"])
    output.mkdir(parents=True,exist_ok=True)
    write_csv(output/"daily_nav.csv", rows)
    write_csv(output/"trades.csv", trades)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>2025美元低换手配置 · 实际验证</title><style>
body{font:16px/1.65 system-ui,sans-serif;color:#18243a;background:#f4f6fa;max-width:1200px;margin:30px auto;padding:0 24px}h1{font-size:30px}h2{font-size:22px}section,.card{background:white;border-radius:14px;padding:22px;margin:16px 0}.cards{display:flex;gap:14px;flex-wrap:wrap}.card{flex:1;min-width:180px}.value{font-size:29px;font-weight:700;color:#176b56}.muted,small{color:#566780}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #e3e8ef;text-align:right}td:first-child,th:first-child{text-align:left}svg{width:100%;height:auto}a{color:#285bba}</style>
<h1>2025美元低换手配置 · 实际验证</h1>
<p>独立1,000美元全现金冷启动 · 2025年1月2日至12月31日开盘 · 历史条件结果，0真实前向</p>
<section><strong>__VERDICT__</strong><p>这是看过旧年份对照后选择的配置假说。目标SPY、EFA、IEF、GLD各25%，实际按整股取整；它不等于四仓始终各25%，也不证明稳定盈利。</p></section>
<div class="cards" id="cards"></div>
<section><h2>两档费用下的实际净值</h2><div id="chart"></div><p>绿色：中档费用（每单至少1美元、滑点10基点）　金色：高费用（至少2.5美元、滑点30基点）　灰色：现金</p></section>
<section><h2>扣费后到底剩下多少</h2><div style="overflow:auto"><table><thead><tr><th>场景</th><th>账面净值</th><th>账面利润</th><th>排除未付分红后利润</th><th>最大回撤</th><th>成交笔数</th><th>佣金＋卖出费＋滑点</th></tr></thead><tbody id="table"></tbody></table></div><p id="settlement"></p><p class="muted">现金利润包含已成交但尚未解锁的卖款，不能当作立即可取余额。未付分红只计入账面净值。</p></section>
<section><h2>实际持仓与资金限制</h2><p id="positions"></p><p>整股限制会让部分目标持仓变为现金。没有借用旧账户复利本金、追加资金或使用分数股。股息预扣30%、除息后45天到账和卖款T+3均为研究假设，实际券商费用与税费尚未确认。</p></section>
<section><h2>查看每笔交易</h2><p><a href="daily_nav.csv" download>下载每日净值、现金与持仓</a> · <a href="trades.csv" download>下载逐笔成交</a></p><p>按月末固定目标、分日卖出和买入；日亏2%或回撤40%暂停，空仓满5个交易日后等下一正常月末。两档费用、3账户及通过条件均在读取2025价格前固定。</p><small>结果指纹：__HASH__</small></section>
<script>const D=__DATA__;const labels={primary:'中档费用',stress:'高费用',cash:'现金'};const colors={primary:'#176b56',stress:'#c17b21',cash:'#8b939e'};const num=x=>Number(x),money=x=>num(x).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2}),pct=x=>(100*num(x)).toFixed(2)+'%';const p=D.primary.summary,s=D.stress.summary;
document.getElementById('cards').innerHTML=[['中档费用现金利润',money(p.terminal_cash_only_net_profit)+'美元'],['高费用现金利润',money(s.terminal_cash_only_net_profit)+'美元'],['中档最大回撤',pct(p.observed_maxDD)],['中档成交笔数',p.fills]].map(([k,v])=>`<div class="card">${k}<div class="value">${v}</div><small>2025年历史条件回测</small></div>`).join('');
document.getElementById('table').innerHTML=Object.entries(D).map(([role,a])=>{const r=a.summary;return `<tr><td>${labels[role]}</td><td>${money(r.terminal_book_NAV)}</td><td>${money(r.terminal_book_net_profit)}</td><td>${money(r.terminal_cash_only_net_profit)}</td><td>${pct(r.observed_maxDD)}</td><td>${r.fills}</td><td>${money(num(r.total_commission)+num(r.total_sell_levy)+num(r.total_slippage))}</td></tr>`}).join('');
document.getElementById('settlement').textContent=`中档费用期末：可支用${money(p.terminal_spendable_cash)}美元、锁定卖款${money(p.terminal_locked_cash)}美元、未付分红${money(p.terminal_receivables)}美元；股票和ETF库存已全部退出。`;
document.getElementById('positions').textContent=`250个账户记录日中，没有持仓的天数：`+Object.entries(D.primary.unheld).map(([a,n])=>a+' '+n+'日').join('，')+`。共${D.primary.zero_targets}个目标腿因整股限制为0股。`;
const vals=Object.values(D).flatMap(a=>a.curve.map(p=>p[1]));const lo=Math.floor(Math.min(...vals)/20)*20,hi=Math.ceil(Math.max(...vals)/20)*20;const w=1120,h=350,left=70,chartTop=20,bottom=45;const y=v=>chartTop+(hi-v)/(hi-lo||1)*(h-chartTop-bottom),x=(i,n)=>left+i/(n-1)*(w-left-20);let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="两档费用与现金的2025净值曲线">`;for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;svg+=`<line x1="${left}" y1="${y(v)}" x2="${w-20}" y2="${y(v)}" stroke="#e4e9ef"/><text x="${left-10}" y="${y(v)+5}" text-anchor="end" font-size="13">${v.toFixed(0)}</text>`}for(const [role,a] of Object.entries(D))svg+=`<polyline fill="none" stroke="${colors[role]}" stroke-width="2" points="${a.curve.map((p,i)=>`${x(i,a.curve.length).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>`;for(let i=0;i<=4;i++){const k=Math.round(i*(D.primary.curve.length-1)/4);svg+=`<text x="${x(k,D.primary.curve.length)}" y="${h-12}" text-anchor="middle" font-size="12">${D.primary.curve[k][0]}</text>`}document.getElementById('chart').innerHTML=svg+'</svg>';</script></html>'''
    positive = all(float(data[r]["summary"]["terminal_cash_only_net_profit"])>0 and float(data[r]["summary"]["observed_maxDD"])<.4 for r in ("primary","stress"))
    verdict = "两档费用下均有正收益且回撤低于40%；独立核账已通过，进入条件纸面准备，尚未取得真实运行或盈利证据。" if positive else "至少一项固定收益或回撤条件未通过；本次选择不继续。"
    digest = hashlib.sha256(raw).hexdigest()
    page = page.replace("__VERDICT__",verdict).replace("__HASH__",digest).replace("__DATA__",json.dumps(data,ensure_ascii=False).replace("<","\\u003c"))
    (output/"index.html").write_text(page,encoding="utf-8")
    (output/"source.json").write_text(json.dumps(dict(result_sha256=digest,review_sha256=hashlib.sha256(review_raw).hexdigest(),accounts=3,daily_rows=len(rows),fills=len(trades),financial_runs=0),indent=2),encoding="utf-8")
    return dict(accounts=3,daily_rows=len(rows),fills=len(trades),output=str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(build_report(args.account_dir,args.output_dir),ensure_ascii=False))
