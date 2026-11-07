"""Run a bounded public-market quote screen and write a local HTML dashboard."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.research.polymarket_complete_set import market_assets, number, screen


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class PublicReader:
    def __init__(self, output: Path):
        self.output, self.requests = output, []
        (output / 'raw').mkdir(parents=True)

    def read(self, url: str, payload=None):
        allowed = ('https://gamma-api.polymarket.com/markets/keyset?',
                   'https://clob.polymarket.com/books')
        if not (url.startswith(allowed[0]) or url == allowed[1]):
            raise ValueError('only public market discovery and book reads are implemented')
        body = None if payload is None else json.dumps(payload).encode()
        req = Request(url, data=body, headers={'User-Agent': 'QuantRobot-public-research/1.0',
                                             'Content-Type': 'application/json'})
        item = dict(index=len(self.requests), at=utc(), url=url,
                    method='GET' if body is None else 'POST', purpose='public_read')
        self.requests.append(item)
        try:
            with urlopen(req, timeout=20) as response:
                raw = response.read(20_000_001)
                item['status'] = response.status
                item['server_date'] = response.headers.get('Date')
            if len(raw) > 20_000_000:
                raise ValueError('public response exceeds 20 MB')
            item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            (self.output / 'raw' / f'{item["index"]:03d}.json').write_bytes(raw)
            item['received_at'] = utc()
            return json.loads(raw)
        except HTTPError as exc:
            item['status'] = exc.code
            raise
        finally:
            save(self.output / 'requests.json', self.requests)


def run_scan(config: dict, reader: PublicReader):
    markets, cursor, discovery_count = {}, None, 0
    for _ in range(config['discovery_pages']):
        params = {'closed': 'false', 'limit': config['page_size']}
        if cursor:
            params['after_cursor'] = cursor
        page = reader.read('https://gamma-api.polymarket.com/markets/keyset?' + urlencode(params))
        rows = page.get('markets') if isinstance(page, dict) else None
        if not isinstance(rows, list):
            raise ValueError('discovery response is not a markets page')
        discovery_count += len(rows)
        for row in rows:
            markets[str(row['id'])] = row
        next_cursor = page.get('next_cursor')
        if not next_cursor:
            break
        if next_cursor == cursor:
            raise ValueError('repeated discovery cursor')
        cursor = next_cursor
    excluded, eligible = Counter(), []
    for market in markets.values():
        try:
            market_assets(market)
            liquidity = number(market.get('liquidityNum', market.get('liquidity', 0)))
            eligible.append((liquidity, str(market['id']), market))
        except (ValueError, TypeError, KeyError) as exc:
            excluded[str(exc)] += 1
    eligible.sort(key=lambda row: (-row[0], row[1]))
    selected = [row[2] for row in eligible[:config['max_selected_markets']]]
    save(reader.output / 'selected_markets.json', selected)
    if selected:
        assets = [asset for market in selected for asset in market_assets(market)]
        if len(assets) != len(set(assets)):
            raise ValueError('selected markets share an outcome identifier')
        book_rows = reader.read('https://clob.polymarket.com/books',
                                [{'token_id': asset} for asset in assets])
        observed_ms = time.time_ns() // 1_000_000
        if not isinstance(book_rows, list):
            raise ValueError('book response is not an array')
        books = {b['asset_id']: b for b in book_rows}
        if len(books) != len(book_rows):
            raise ValueError('duplicate books in batch response')
    else:
        books, observed_ms = {}, time.time_ns() // 1_000_000
    results = [screen(market, books, observed_ms=observed_ms,
                      quantities=config['net_pair_quantities'],
                      max_age_ms=config['max_book_age_ms'],
                      max_skew_ms=config['max_book_skew_ms'],
                      reserve_bps=config['additional_cost_reserve_bps'],
                      fixed_reserve=config['fixed_additional_cost_reserve_collateral_units'])
               for market in selected]
    return dict(status='completed', at=utc(), source='Polymarket public API',
                discovery_rows=discovery_count, unique_markets=len(markets),
                eligible_markets=len(eligible), selected_markets=len(selected),
                discovery_exclusions=dict(excluded),
                quoted_markets=sum(r['status'] == 'quoted' for r in results),
                positive_quote_markets=sum(any(q['positive_quote_candidate']
                    for q in r['observations']) for r in results),
                results=results, realized_profit=None, fills=0,
                strategy_forward_days=0, config=config,
                limitations=['Quotes are not atomic two-leg fills or realized profits.',
                    'Reserve is an assumption, not verified gas, conversion, or funding fees.',
                    'Fee rounding and buy-fee settlement are modeled, not account-verified.',
                    'Bounded discovery is not a census of all markets.',
                    'No wallet, account, exchange order, or chain transaction is accessed.'])


def render(report: dict) -> str:
    rows = []
    for market in report.get('results', []):
        for quote in market['observations']:
            if quote['net_pairs'] != '100':
                continue
            surplus = quote['quote_surplus']
            rows.append((Decimal(surplus) if surplus is not None else Decimal('-Infinity'),
                         market, quote))
    rows.sort(key=lambda row: row[0], reverse=True)
    body = ''
    for _, market, quote in rows[:30]:
        state = ('正余量候选' if quote['positive_quote_candidate'] else
                 '深度不足' if not quote['depth_complete'] else
                 '扣费后无正价差' if Decimal(quote['quote_surplus']) <= 0 else
                 '低于最小金额' if not quote['minimum_met'] else
                 '报价时间不满足' if not market['fresh'] or not market['synchronous'] else '无正余量')
        body += '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in (
            market['question'], market.get('best_ask_sum', ''),
            f"{Decimal(quote['conservative_cost']):.4f}",
            f"{Decimal(quote['additional_cost_reserve']):.4f}",
            '—' if quote['quote_surplus'] is None else f"{Decimal(quote['quote_surplus']):+.4f}", state)) + '</tr>'
    problem = html.escape(report.get('error', ''))
    unavailable = Counter(r.get('reason', '') for r in report.get('results', []) if r['status'] != 'quoted')
    reserve_percent = Decimal(report['config']['additional_cost_reserve_bps']) / 100
    fixed_reserve = html.escape(str(report['config']['fixed_additional_cost_reserve_collateral_units']))
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Polymarket 公开盘口机会扫描</title><style>
body{{font:16px/1.65 system-ui,sans-serif;background:#f4f6fa;color:#18243a;max-width:1250px;margin:32px auto;padding:0 24px}}
h1{{font-size:28px}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card,section{{background:white;padding:22px;border-radius:14px;margin-bottom:20px}}
.card{{flex:1;min-width:180px}}.n{{font-size:34px;font-weight:700}}small{{color:#566780}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #e3e8ef}}td:first-child{{max-width:430px}}.note{{color:#566780}}a{{color:#285bba}}</style>
<h1>Polymarket 公开盘口机会扫描</h1><p>买齐同一市场的“是”和“否”，检查完整份额的报价成本。</p>
<small>快照：{html.escape(report['at'])} · 手动刷新页面不会重新采集</small>
<div class="cards"><div class="card">采样市场<div class="n">{report.get('unique_markets',0)}</div></div>
<div class="card">实际读盘口<div class="n">{report.get('selected_markets',0)}</div></div>
<div class="card">正余量候选<div class="n">{report.get('positive_quote_markets',0)}</div></div>
<div class="card">成交 / 已实现利润<div class="n">0 / —</div></div></div>
<section><h2>100 对份额的成本比较</h2><p>每对完整份额对应 1 单位抵押资产。先扣交易费估算，再预留成本的 {reserve_percent}% 和固定 {fixed_reserve} 单位。下表为快照报价余量，不是成交利润；两边同时成交与兑换费用仍需验证。</p>
<div style="overflow:auto"><table><thead><tr><th>市场</th><th>最优卖价合计</th><th>买入成本</th><th>额外预留</th><th>报价余量</th><th>状态</th></tr></thead><tbody>{body}</tbody></table></div>
<p>{problem}</p><p class="note">无法完整计算：{html.escape(json.dumps(dict(unavailable),ensure_ascii=False))}</p></section>
<p class="note">本工具只读取公开市场和盘口。有限采样不能代表全市场；没有正候选时如实显示 0。金额为平台抵押资产单位，未换算人民币，也未使用华宝佣金。</p>
<p><a href="https://docs.polymarket.com/market-data/prices-order-books">盘口说明</a> · <a href="https://docs.polymarket.com/trading/fees">费用说明</a> · <a href="https://docs.polymarket.com/concepts/positions-tokens">完整份额机制</a></p></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/polymarket_complete_set_scan.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if not (1 <= config['discovery_pages'] <= 5 and 1 <= config['page_size'] <= 100
            and 1 <= config['max_selected_markets'] <= 100):
        raise ValueError('bounded discovery limits exceeded')
    save(args.output_dir / 'config_used.json', config)
    reader = PublicReader(args.output_dir)
    try:
        report = run_scan(config, reader)
    except Exception as exc:
        report = dict(status='failed', at=utc(), error=f'{type(exc).__name__}: {exc}',
                      config=config, results=[], realized_profit=None, fills=0)
    save(args.output_dir / 'report.json', report)
    (args.output_dir / 'report.html').write_text(render(report), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('results', 'config', 'limitations')},
                     ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
