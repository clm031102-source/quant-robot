const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

const source = readFileSync(join(__dirname, '../src/quant_robot/gui/static/app.js'), 'utf8');
function actualFunction(name) {
  const declarations = [...source.matchAll(/^(?:async )?function ([\w]+)\(/gm)];
  const index = declarations.findIndex(match => match[1] === name);
  assert.ok(index >= 0, name);
  return source.slice(declarations[index].index, declarations[index + 1]?.index ?? source.length);
}

function harness(response) {
  const nodes = new Map();
  const calls = [];
  const render = actualFunction('renderDailyTradeAdvisory');
  const context = {
    state: {dailyTradeAdvisory: {manual_trade_plan: [{ticket_id: 'old-fixture'}], summary: {signal_count: 3}}},
    URLSearchParams,
    fetch: async () => response,
    buildDailyTradeAdvisoryParams: () => new URLSearchParams({source: 'processed-bars', market: 'CN_ETF'}),
    attachRequestToResult: value => value,
    byId: id => {
      if (!nodes.has(id)) nodes.set(id, {textContent: '', innerHTML: '', classList: {toggle() {}}});
      return nodes.get(id);
    },
    zhConsoleText: value => String(value),
    metric: () => '',
    statusRows: value => JSON.stringify(value),
    tableRows: value => JSON.stringify(value),
    renderDashboard() {},
    confirmSafeWorkflow: async () => true,
    endpointWithParams: path => path,
    paramsObject: () => ({}),
    withBusy: async (_name, action) => action(),
    appendRunHistory: value => calls.push(['history', value]),
    appendExecutionReceipt: value => calls.push(['receipt', value]),
    dailyTradeAdvisoryReceipt: value => value,
    showToast: value => calls.push(['toast', value]),
  };
  // Child panels have separate tests. Execute the real parent renderer against
  // isolated DOM nodes, and stub only its unrelated child-rendering boundary.
  for (const [, name] of render.matchAll(/\b(render\w+)\(/g)) {
    if (name !== 'renderDailyTradeAdvisory') context[name] = () => {};
  }
  vm.createContext(context);
  vm.runInContext(['fetchJson', 'loadDailyTradeAdvisory', 'runDailyTradeAdvisory', 'renderDailyTradeAdvisory']
    .map(actualFunction).join('\n'), context);
  return {context, nodes, calls};
}

const denial = {ok: false, json: async () => ({status: 'research_access_denied', error: '请使用专用入口'})};

test('initial denial clears old tickets and renders the reason', async () => {
  const {context, nodes} = harness(denial);
  await assert.rejects(context.loadDailyTradeAdvisory(), /专用入口/);
  assert.equal(context.state.dailyTradeAdvisory.summary.signal_count, 0);
  assert.equal(context.state.dailyTradeAdvisory.manual_trade_plan, undefined);
  assert.equal(nodes.get('daily-trade-advisory-tag').textContent, '研究准入未完成');
  assert.match(nodes.get('daily-trade-advisory-status').innerHTML, /专用入口/);
  assert.equal(nodes.get('daily-trade-manual-table').innerHTML, '[]');
});

test('manual denial does not record completed history or paper evidence', async () => {
  const {context, calls} = harness(denial);
  await assert.rejects(context.runDailyTradeAdvisory(), /专用入口/);
  assert.deepEqual(calls, []);
  assert.equal(context.state.dailyTradeAdvisory.summary.signal_count, 0);
});

test('non-JSON failures also clear stale advice and preserve a useful error', async () => {
  const {context, nodes} = harness({ok: false, json: async () => {throw new Error('not json');}});
  await assert.rejects(context.loadDailyTradeAdvisory(), /Request failed:/);
  assert.equal(context.state.dailyTradeAdvisory.manual_trade_plan, undefined);
  assert.equal(nodes.get('daily-trade-advisory-tag').textContent, '请求未完成');
});

test('successful fixture advice still renders and records its completion', async () => {
  const pack = {summary: {signal_count: 1}, manual_trade_plan: [{ticket_id: 'new-fixture'}]};
  const {context, nodes, calls} = harness({ok: true, json: async () => pack});
  await context.runDailyTradeAdvisory();
  assert.equal(context.state.dailyTradeAdvisory, pack);
  assert.match(nodes.get('daily-trade-manual-table').innerHTML, /new-fixture/);
  assert.deepEqual(calls.map(call => call[0]), ['history', 'receipt', 'toast']);
});
