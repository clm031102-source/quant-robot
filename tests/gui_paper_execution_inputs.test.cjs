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
const pins = {corporate_actions_fingerprint:'a'.repeat(64), fixed_hold_benchmark_sha256:'b'.repeat(64)};
function harness(fail = false) {
  const values = {'paper-market-select':'CN_ETF', 'paper-initial-cash':'10000',
    'paper-impact-bps':'2', 'paper-participation-rate':'0.01',
    'paper-actions-path':'fixture-actions.json', 'paper-fixed-hold-path':'fixture-entries.json'};
  const requests = [], receipts = [], histories = [], nodes = new Map();
  const context = {URLSearchParams, state:{paper:{metrics:{total_return:99}}},
    valueOf:id => values[id] ?? '', factorWindowCsvForFactor:() => '2',
    addSourceParams:params => params.set('source','fixture'),
    byId:id => {if (!nodes.has(id)) nodes.set(id,{innerHTML:''}); return nodes.get(id);},
    renderDashboard() {}, renderPaper() {}, renderControlCenter() {}, showToast() {},
    confirmSafeWorkflow:async () => true, withBusy:async (_id,work) => work(),
    endpointWithParams:(path,params) => path+'?'+params, paramsObject:params => Object.fromEntries(params),
    appendRunHistory:row => histories.push(row), appendExecutionReceipt:row => receipts.push(row),
    fetchJson:async url => {
      requests.push(url);
      if (url.startsWith('/api/paper/inputs?')) return {pins,files:[{path:'fixture-actions.json'}]};
      if (fail) throw Object.assign(new Error('输入文件版本已变化'),{status:'paper_input_error'});
      return {request:Object.fromEntries(new URL(url,'http://fixture').searchParams),metrics:{total_return:0}};
    }};
  vm.createContext(context);
  vm.runInContext(['buildPaperParams','appendSameParameterPaperMetadata','paperInputVersionKey',
    'appendPaperInputPins','preparePaperParams','invalidatePaperResult','refreshPaper','runPaper','paperReceipt']
    .map(actualFunction).join('\n'),context);
  return {context,values,requests,receipts,histories,nodes};
}

test('prepare sends only file identities and run receives all execution conditions and versions', async () => {
  const {context,requests,receipts} = harness();
  await context.runPaper();
  assert.equal(requests.length,2);
  const prep = new URL(requests[0],'http://fixture').searchParams;
  assert.equal(prep.has('factor'),false);
  const actual = new URL(requests[1],'http://fixture').searchParams;
  for (const [key,value] of Object.entries({...pins,market_impact_bps:'2',max_participation_rate:'0.01'})) {
    assert.equal(actual.get(key),value);
    assert.equal(receipts[0].request[key],value);
  }
});

test('a locked request cannot silently adopt a newly read file version', async () => {
  const {context} = harness();
  await assert.rejects(context.preparePaperParams({...pins,corporate_actions_fingerprint:'c'.repeat(64)}), /版本/);
  assert.equal(context.state.paper.metrics,undefined);
  assert.match(context.state.paper.error,/版本/);
});

test('missing frozen pins are not filled into a locked request', async () => {
  const {context} = harness();
  await assert.rejects(context.preparePaperParams({same_parameter_lock_id:'fixture-lock'}), /版本/);
});

test('run failure clears old profitable output and never saves a success receipt', async () => {
  const {context,receipts,histories} = harness(true);
  await assert.rejects(context.runPaper(),/版本/);
  assert.equal(context.state.paper.metrics,undefined);
  assert.equal(receipts.length,0);
  assert.equal(histories.length,0);
});

test('locked run failure restores the button and saves no successful receipt', async () => {
  const {context,receipts,histories} = harness(true);
  context.sameParameterPaperRequestFromButton = () => ({...pins});
  context.applySameParameterPaperToForm = () => {};
  vm.runInContext(actualFunction('runSameParameterPaperSimulation'),context);
  const button = {disabled:false,textContent:'复核'};
  await assert.rejects(context.runSameParameterPaperSimulation(button),/版本/);
  assert.equal(button.disabled,false);
  assert.equal(button.textContent,'复核');
  assert.equal(receipts.length,0);
  assert.equal(histories.length,0);
});

test('changing an input path does not reuse cached versions', async () => {
  const {context,values} = harness();
  await context.preparePaperParams();
  values['paper-actions-path'] = 'other-fixture.json';
  assert.equal(context.buildPaperParams().has('corporate_actions_fingerprint'),false);
});

test('browser identity requires matching constraints and explicit versions for file inputs', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(['paperReceiptMatchesRequest','normalizeReceiptText','normalizeReceiptNumber']
    .map(actualFunction).join('\n'),context);
  const request = {market:'CN_ETF',market_impact_bps:2,max_participation_rate:.01,
    corporate_actions_path:'fixture.json',fixed_hold_benchmark_path:'entries.json',...pins};
  assert.equal(context.paperReceiptMatchesRequest({request},request).matches,true);
  for (const change of [{market_impact_bps:0},{max_participation_rate:null},
    {corporate_actions_fingerprint:undefined},{corporate_actions_fingerprint:'d'.repeat(64)},
    {fixed_hold_benchmark_sha256:undefined}]) {
    assert.equal(context.paperReceiptMatchesRequest({request},{...request,...change}).matches,false);
  }
});

test('comparison panel shows account returns without claiming certified alpha and clears absent comparison', () => {
  const target = {innerHTML:''};
  const context = {state:{paper:{account_comparison:{strategy_total_return:.01,benchmark_total_return:.005,
      relative_return:.005,cash_total_return:0},fixed_hold_benchmark:{risk:{compatible_with_declared_limits:false}}}},
    byId:() => target, statusRows:rows => JSON.stringify(rows), formatPercent:value => String(value),
    escapeHtml:value => String(value)};
  vm.createContext(context);
  vm.runInContext(actualFunction('renderPaperComparison'),context);
  context.renderPaperComparison();
  assert.match(target.innerHTML,/0\.005/);
  assert.match(target.innerHTML,/风险/);
  assert.match(target.innerHTML,/未证实|不等于/);
  context.state.paper = {error:'fixture failure'};
  context.renderPaperComparison();
  assert.doesNotMatch(target.innerHTML,/0\.005/);
});

test('different sources or declared accounting models cannot match a paper receipt', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(['paperReceiptMatchesRequest','normalizeReceiptText','normalizeReceiptNumber']
    .map(actualFunction).join('\n'),context);
  const request = {market:'CN_ETF',source:'demo_fixture',execution_economics:{model:'cash',cost:5}};
  assert.equal(context.paperReceiptMatchesRequest({request},{...request,source:'fixture',
    execution_economics:{cost:5,model:'cash'}}).matches,true);
  for (const change of [{source:'processed-bars'},{execution_economics:{model:'cash',cost:0}}]) {
    assert.equal(context.paperReceiptMatchesRequest({request},{...request,...change}).matches,false);
  }
});
