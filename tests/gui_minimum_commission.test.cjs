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

test('browser transmits the selected minimum, including explicit zero', () => {
  const values = {'paper-minimum-commission': '5'};
  const context = {URLSearchParams, valueOf: id => values[id] ?? '',
    factorWindowCsvForFactor: () => '2', addSourceParams() {}, appendSameParameterPaperMetadata() {}};
  vm.createContext(context);
  vm.runInContext(actualFunction('buildPaperParams'), context);
  assert.equal(context.buildPaperParams().get('minimum_commission'), '5');
  values['paper-minimum-commission'] = '0';
  assert.equal(context.buildPaperParams().get('minimum_commission'), '0');
});

test('browser rejects a different fee and treats omitted legacy fee as zero', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(['paperReceiptMatchesRequest', 'normalizeReceiptText', 'normalizeReceiptNumber']
    .map(actualFunction).join('\n'), context);
  for (const expected of [{market: 'CN_ETF'}, {market: 'CN_ETF', minimum_commission: 0},
    {market: 'CN_ETF', minimum_commission: ''}, {market: 'CN_ETF', minimum_commission: null}]) {
    const result = context.paperReceiptMatchesRequest({request: {market: 'CN_ETF', minimum_commission: 5}}, expected);
    assert.equal(result.matches, false);
    assert.ok(result.mismatch_keys.includes('minimum_commission'));
  }
  assert.equal(context.paperReceiptMatchesRequest({request: {market: 'CN_ETF', minimum_commission: '5'}},
    {market: 'CN_ETF', minimum_commission: 5}).matches, true);
  assert.equal(context.paperReceiptMatchesRequest({}, {}).matches, false);
  assert.equal(context.paperReceiptMatchesRequest({}, {unrelated: 'field'}).matches, false);
  assert.equal(context.paperReceiptMatchesRequest({}, {minimum_commission: 0}).matches, false);
});

test('handoff resets an old request to its zero-minimum scenario and preserves a new fee', () => {
  const values = {};
  const context = {markManualFormOverride() {}, setValue: (id, value) => values[id] = value,
    leaderboardInputValue: value => String(value), renderRequestPreview() {}, renderControlCenter() {},
    showToast() {}, activatePage() {}, jumpToBeginnerTarget() {}};
  vm.createContext(context);
  vm.runInContext(actualFunction('applyDailyPaperHandoffToForm'), context);
  context.applyDailyPaperHandoffToForm({minimum_commission: 5});
  assert.equal(values['paper-minimum-commission'], '5');
  context.applyDailyPaperHandoffToForm({});
  assert.equal(values['paper-minimum-commission'], '0');
});

test('saved receipt preserves the applied fee', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(actualFunction('paperReceipt'), context);
  const receipt = context.paperReceipt({request: {minimum_commission: 5}, metrics: {}});
  assert.equal(JSON.parse(JSON.stringify(receipt)).request.minimum_commission, 5);
});

test('changing a fee marks the displayed paper result as stale', () => {
  const target = {innerHTML: ''};
  const params = new URLSearchParams({market: 'CN_ETF', initial_cash: '10000', minimum_commission: '0'});
  const context = {URLSearchParams, state: {paper: {request: Object.fromEntries(params)}},
    byId: () => target, escapeHtml: value => String(value),
    buildPaperParams: () => params, buildResearchParams: () => new URLSearchParams(),
    buildSignalParams: () => new URLSearchParams(), buildDailyTradeAdvisoryParams: () => new URLSearchParams()};
  vm.createContext(context);
  vm.runInContext(['renderResultFreshness', 'resultFreshnessRow', 'requestMatchesCurrentParams',
    'requestObjectFromParams', 'requestValue', 'normalizeRequestValue', 'requestFreshnessSummary']
    .map(actualFunction).join('\n'), context);
  context.renderResultFreshness();
  assert.match(target.innerHTML, /模拟盘结果 \/ 当前/);
  params.set('minimum_commission', '5');
  context.renderResultFreshness();
  assert.match(target.innerHTML, /模拟盘结果 \/ 已过期/);
});
