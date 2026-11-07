"""Render saved monthly-breadth results; never execute a strategy or source read."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import html
import io
import json
from pathlib import Path

LABELS = {'breadth':'组合趋势仓位', 'monthly_50_50':'每月股金各半', 'own_trend':'各资产独立趋势', 'cash':'持有现金'}
COLORS = {'breadth':'#176b56','monthly_50_50':'#c17b21','own_trend':'#4e62b8','cash':'#8b939e'}


def csv_text(rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v
                         for k,v in row.items()})
    return buffer.getvalue()


def build_report(account_dir: Path, output: Path):
    matrix_path = account_dir / 'result.json'
    matrix = json.loads(matrix_path.read_text(encoding='utf-8'))
    if matrix.get('historical_returns_computed') is not True or matrix.get('account_count') != 28:
        raise ValueError('Expected completed 28-account historical matrix')
    data, curves, fills, rows = {}, {}, [], []
    for identity, ref in matrix['accounts'].items():
        path = account_dir / 'accounts' / identity / 'complete.json'
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['artifact']['sha256']:
            raise ValueError(f'Saved account digest mismatch: {identity}')
        account = json.loads(raw)
        if account.get('historical_returns_computed') is not True:
            raise ValueError('Artificial results cannot be rendered as historical evidence')
        s = account['summary']
        days = account['days']
        elapsed = (datetime.fromisoformat(days[-1]['date'])-datetime.fromisoformat(days[0]['date'])).days
        ending = float(s['terminal_book_NAV'])
        cagr = (ending/10000)**(365.25/elapsed)-1 if elapsed > 0 and ending > 0 else None
        data[identity] = dict(policy=account['policy'], label=LABELS[account['policy']],
            net=float(s['book_netPnL']), ending=ending, drawdown=float(s['observed_maxDD']),
            commission=float(s['total_commission']),slippage=float(s['total_slippage']),
            fills=s['fill_count'], annualized=cagr,
            spendable=float(s['terminal_spendable_cash']), locked=float(s['terminal_locked_sale_cash']),
            years=account['annual_contributions'],
            start=days[0]['date'], end=days[-1]['date'])
        curves[identity] = [[d['date'],float(d['NAV'])] for d in days]
        rows.extend(dict(account=identity,date=d['date'],NAV=d['NAV'],drawdown=d['DD'],
                         paused=d['paused'],terminal_open_stub=d['terminal_open_stub']) for d in days)
        fills.extend(dict(account=identity,**fill) for fill in account['fills'])
    output.mkdir(parents=True,exist_ok=True)
    (output/'daily_nav.csv').write_text(csv_text(rows),encoding='utf-8-sig',newline='')
    (output/'trades.csv').write_text(csv_text(fills),encoding='utf-8-sig',newline='')
    payload=json.dumps(dict(accounts=data,curves=curves),ensure_ascii=False).replace('<','\\u003c')
    matrix_hash=hashlib.sha256(matrix_path.read_bytes()).hexdigest()
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>股金月频策略 · 赚钱能力实测</title><style>
body{font:16px/1.65 system-ui,sans-serif;background:#f4f6fa;color:#18243a;max-width:1250px;margin:30px auto;padding:0 24px}
h1{font-size:30px;margin-bottom:5px}h2{font-size:22px}.cards{display:flex;gap:14px;flex-wrap:wrap}.card,section{background:white;padding:22px;border-radius:14px;margin:14px 0}.card{flex:1;min-width:170px}.n{font-size:29px;font-weight:700;margin:4px 0}.muted,small{color:#566780}.positive{color:#176b56}.negative{color:#ad4141}select{font:inherit;padding:8px;border-radius:8px;border:1px solid #cad4df}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:right;padding:9px;border-bottom:1px solid #e2e7ee}td:first-child,th:first-child{text-align:left}svg{width:100%;height:auto}.legend{display:flex;gap:24px;flex-wrap:wrap}a{color:#285bba}.bar{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}</style>
<h1>股金月频策略 · 赚钱能力实测</h1>
<p>初始资金 10,000 元，股票ETF＋黄金ETF。下列是历史条件回测，未发生实盘盈利，也未累计真实模拟天数。</p>
<div class="bar"><label>费用情景 <select id="cost"></select></label><span class="muted">佣金万一；主情景每笔最低5元、滑点10基点</span></div>
<div id="cards" class="cards"></div><section><div class="bar"><h2>扣费后的资金曲线</h2><small id="period"></small></div>
<div id="chart"></div><div class="legend" id="legend"></div><p id="insight"></p><p class="muted" id="settlement"></p></section>
<section><h2>同资金、同费用、同风控对照</h2><div style="overflow:auto"><table><thead><tr><th>方法</th><th>净利润（元）</th><th>年化</th><th>最大回撤</th><th>成交笔数</th><th>佣金（元）</th><th>滑点成本（元）</th></tr></thead><tbody id="comparison"></tbody></table></div></section>
<section><h2>每年的利润贡献（元）</h2><p class="muted">不是年度收益率；各年贡献合计等于总净利润。最后一个交易开盘结清归入末年。</p><div style="overflow:auto"><table id="years"></table></div></section>
<section><h2>可检查的交易记录</h2><p><a href="daily_nav.csv" download>下载逐日净值</a> · <a href="trades.csv" download>下载逐笔成交</a></p>
<p>两阶段调仓：月末收盘确定目标，下一交易日卖出、再下一交易日买入。允许满仓；日亏2%或回撤40%触发暂停，完整空仓5个交易日后按规则恢复。历史条件成交无法认证当时所有停复牌和实际成交状态。</p>
<p class="muted">最低0元仅作费用敏感性对照。期末账面资金可能仍有卖款结算等待，不等于当时全部可取。正回测不自动证明未来能盈利；候选判定以独立核账和固定比较结果为准。</p>
<small>结果指纹：__HASH__</small></section>
<script>const D=__DATA__;const labels=__LABELS__;const colors=__COLORS__;
const money=n=>n.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=n=>n===null?'—':(100*n).toFixed(2)+'%';const policies=['breadth','monthly_50_50','own_trend'];
const select=document.getElementById('cost');for(const m of [0,5,10])for(const s of [0,10,30]){const o=document.createElement('option');o.value=`min${m}_slip${s}`;o.textContent=`最低佣金${m}元 · 滑点${s}基点${m===0?'（假设对照）':''}`;select.append(o)}select.value='min5_slip10';
function show(){const cost=select.value;const a=policies.map(p=>D.accounts[cost+'/'+p]);const b=a[0];
document.getElementById('cards').innerHTML=[['期末账面资金',money(b.ending)+' 元'],['净利润',money(b.net)+' 元'],['年化收益',pct(b.annualized)],['最大回撤',pct(b.drawdown)]].map(([k,v])=>`<div class="card">${k}<div class="n">${v}</div><small>组合趋势仓位 · 历史回测</small></div>`).join('');
document.getElementById('period').textContent=b.start+' 至 '+b.end+'（末日开盘）';
document.getElementById('comparison').innerHTML=[...a,D.accounts.cash].map(x=>`<tr><td>${x.label}</td><td>${money(x.net)}</td><td>${pct(x.annualized)}</td><td>${pct(x.drawdown)}</td><td>${x.fills}</td><td>${money(x.commission)}</td><td>${money(x.slippage)}</td></tr>`).join('');
document.getElementById('insight').textContent=`组合趋势仓位比每月股金各半${b.net>=a[1].net?'多赚':'少赚'} ${money(Math.abs(b.net-a[1].net))} 元；比各资产独立趋势${b.net>=a[2].net?'多赚':'少赚'} ${money(Math.abs(b.net-a[2].net))} 元。`;
document.getElementById('settlement').textContent=`组合趋势仓位期末账面资金 ${money(b.ending)} 元，其中可支用 ${money(b.spendable)} 元、待结算卖款 ${money(b.locked)} 元。可支用不等于可取。`;
const series=policies.map(p=>({p,points:D.curves[cost+'/'+p]}));series.push({p:'cash',points:D.curves.cash});const vals=series.flatMap(s=>s.points.map(p=>p[1]));let lo=Math.floor(Math.min(...vals)/1000)*1000,hi=Math.ceil(Math.max(...vals)/1000)*1000;if(hi===lo)hi=lo+1000;
const width=1160,height=390,left=70,top=20,bottom=50;const y=v=>top+(hi-v)/(hi-lo)*(height-top-bottom);const x=(i,n)=>left+i/Math.max(1,n-1)*(width-left-20);
let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="四种方法的历史净值曲线">`;for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;svg+=`<line x1="${left}" y1="${y(v)}" x2="${width-20}" y2="${y(v)}" stroke="#e4e9ef"/><text x="${left-10}" y="${y(v)+5}" text-anchor="end" font-size="13" fill="#65758c">${Math.round(v)}</text>`}
for(const s of series){svg+=`<polyline fill="none" stroke="${colors[s.p]}" stroke-width="${s.p==='breadth'?2.3:1.6}" points="${s.points.map((p,i)=>`${x(i,s.points.length).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>`}const pts=series[0].points;for(let i=0;i<=5;i++){const k=Math.round(i*(pts.length-1)/5);svg+=`<text x="${x(k,pts.length)}" y="${height-15}" text-anchor="middle" font-size="12" fill="#65758c">${pts[k][0]}</text>`}document.getElementById('chart').innerHTML=svg+'</svg>';
document.getElementById('legend').innerHTML=series.map(s=>`<span style="color:${colors[s.p]}">● ${labels[s.p]}</span>`).join('');
const years=Object.keys(b.years);document.getElementById('years').innerHTML='<thead><tr><th>年份</th>'+a.map(x=>`<th>${x.label}</th>`).join('')+'</tr></thead><tbody>'+years.map(y=>'<tr><td>'+y+'</td>'+a.map(x=>`<td>${money(Number(x.years[y]))}</td>`).join('')+'</tr>').join('')+'</tbody>';
}select.addEventListener('change',show);show();</script></html>'''
    page=page.replace('__DATA__',payload).replace('__LABELS__',json.dumps(LABELS,ensure_ascii=False)).replace('__COLORS__',json.dumps(COLORS)).replace('__HASH__',matrix_hash)
    (output/'index.html').write_text(page,encoding='utf-8')
    (output/'source.json').write_text(json.dumps(dict(result_path=str(matrix_path.resolve()),
        result_sha256=matrix_hash,account_count=len(data),execution=False),indent=2)+'\n',encoding='utf-8')
    return dict(output=str(output.resolve()),accounts=len(data),daily_rows=len(rows),fills=len(fills))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build_report(args.account_dir,args.output_dir),ensure_ascii=False))


if __name__=='__main__':main()
