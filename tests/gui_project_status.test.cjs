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
function harness() {
  const nodes = new Map();
  function element() {
    return {children: [], textContent: '', innerHTML: '', disabled: false, listeners: {},
      set id(id) { this._id = id; nodes.set(id, this); }, get id() { return this._id; },
      append(...items) { this.children.push(...items); },
      appendChild(item) { this.children.push(item); },
      setAttribute(name, value) { this[name] = value; },
      addEventListener(name, handler) { this.listeners[name] = handler; },
      classList: {add() {}, toggle() {}}};
  }
  const head = element();
  nodes.set('ordinary-home-board', {querySelector: () => head});
  const context = {state: {projectStatus: {state_label: '旧记录'}},
    byId: id => nodes.get(id), document: {createElement: element},
    renderProjectStatus() {}, renderDashboard() {}};
  vm.createContext(context);
  vm.runInContext(['installProjectStatusRefresh', 'refreshProjectStatus', 'loadProjectStatus', 'fetchJson']
    .map(actualFunction).join('\n'), context);
  return {context, nodes, head, element};
}

test('explicit button refresh calls only status once and blocks duplicate pending clicks', async () => {
  const {context, nodes, head} = harness();
  const calls = [];
  let resolve;
  context.fetch = url => { calls.push(url); return new Promise(done => { resolve = done; }); };
  assert.match(actualFunction('bindActions'), /installProjectStatusRefresh\(\)/);
  context.installProjectStatusRefresh();
  context.installProjectStatusRefresh();
  assert.equal(head.children.length, 1);
  assert.deepEqual(calls, []); // Installing the control neither polls nor reads history.
  const button = nodes.get('refresh-project-status');
  const pending = button.listeners.click();
  await button.listeners.click();
  assert.equal(button.disabled, true);
  assert.deepEqual(calls, ['/api/project/status']);
  resolve({ok: true, json: async () => ({state_label: '新记录', actual_fees_verified: false})});
  await pending;
  assert.equal(context.state.projectStatus.state_label, '新记录');
  assert.equal(button.disabled, false);
  assert.match(nodes.get('project-status-refresh-feedback').textContent, /只读/);
});

test('failed refresh preserves last record, explains failure, and permits an explicit retry', async () => {
  const {context, nodes} = harness();
  const previous = context.state.projectStatus;
  const calls = [];
  context.fetch = async url => { calls.push(url); throw new Error('offline'); };
  context.installProjectStatusRefresh();
  const button = nodes.get('refresh-project-status');
  await button.listeners.click();
  assert.equal(context.state.projectStatus, previous);
  assert.equal(button.disabled, false);
  assert.match(nodes.get('project-status-refresh-feedback').textContent, /刷新失败.*上次记录/);
  context.fetch = async url => { calls.push(url); return {ok: true, json: async () => ({state_label: '重试后记录'})}; };
  await button.listeners.click();
  assert.equal(context.state.projectStatus.state_label, '重试后记录');
  assert.deepEqual(calls, ['/api/project/status', '/api/project/status']);
});

test('home and status cards retain partial ETF fee meaning and checkpoint is not liveness', () => {
  const {context, nodes, element} = harness();
  for (const id of ['ordinary-status-metrics', 'ordinary-next-action', 'ordinary-daily-action-card',
    'ordinary-mainline-warning', 'project-status-tag', 'project-status-list', 'project-action-table']) {
    const node = element(); node.id = id;
  }
  Object.assign(context, {statusRows: rows => JSON.stringify(rows), tableRows: () => '',
    metric: (...items) => JSON.stringify(items), groupHistoricalDashboard() {},
    renderOrdinaryTradingCockpit() {}, formatPercent: value => String(value)});
  vm.runInContext(['projectFeeSummary', 'renderOrdinaryHome', 'renderProjectStatus'].map(actualFunction).join('\n'), context);
  context.state.projectStatus = {authority: 'current_project_state', actual_fees_verified: false,
    user_confirmed_costs: {ETF_minimum_commission_CNY_per_transaction: 5,
      source: 'user_reported_2026-11-07UTC', broker_and_rate_unconfirmed: true},
    campaign: {campaign_id: 'test', checkpoint_available: true, checkpoint_at: '2026-11-07T04:00:00Z'}};
  context.renderProjectStatus();
  for (const id of ['ordinary-next-action', 'project-status-list']) {
    assert.match(nodes.get(id).innerHTML, /ETF每笔最低5元已由用户确认；其他费用待核实/);
  }
  assert.match(nodes.get('project-status-list').innerHTML, /最近一次保存的工作记录/);
  assert.equal(context.state.projectStatus.actual_fees_verified, false);
});

test('missing or malformed fee projection cannot become confirmed all-product fees', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(actualFunction('projectFeeSummary'), context);
  for (const costs of [undefined, null, [], {}, false,
    {ETF_minimum_commission_CNY_per_transaction: true},
    {ETF_minimum_commission_CNY_per_transaction: '5'},
    {ETF_minimum_commission_CNY_per_transaction: 5, source: 'unverified', broker_and_rate_unconfirmed: true}]) {
    assert.equal(context.projectFeeSummary({user_confirmed_costs: costs, actual_fees_verified: true}),
      'ETF最低佣金及其他费用待核实');
  }
});

test('user confirmed Huabao rate and minimum remain ETF specific', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(actualFunction('projectFeeSummary'), context);
  const text = context.projectFeeSummary({user_confirmed_costs: {
    ETF_minimum_commission_CNY_per_transaction: 5,
    source: 'user_reported_2026-11-07UTC', broker_and_rate_unconfirmed: false,
    broker: '华宝证券', ETF_commission_rate: 0.0001,
  }});
  assert.equal(text, '华宝ETF佣金：万一，每笔最低5元（用户确认）；其他品种费用另计');
});
