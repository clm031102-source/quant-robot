const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../src/quant_robot/gui/static/app.js'), 'utf8');
function functions(...names) {
  const declarations = [...source.matchAll(/^(?:async )?function ([\w]+)\(/gm)];
  return names.map(name => {
    const index = declarations.findIndex(match => match[1] === name);
    assert.ok(index >= 0, name);
    return source.slice(declarations[index].index, declarations[index + 1]?.index ?? source.length);
  }).join('\n');
}
const id = 'a'.repeat(64);
function context(overrides = {}) {
  const value = {URLSearchParams, state: {paper: null}, escapeHtml: String,
    renderPaper() {}, renderResultFreshness() {}, activatePage() {}, showToast() {},
    ...overrides};
  vm.createContext(value);
  return value;
}

test('receipt keeps an archive reference without copying curves into browser storage', () => {
  const c = context();
  vm.runInContext(functions('paperReceipt'), c);
  const ref = {status:'saved', archive_id:id};
  const result = c.paperReceipt({request:{minimum_commission:5}, paper_archive:ref, equity_curve:[{equity:10}]});
  assert.equal(result.paper_archive, ref);
  assert.equal(result.equity_curve, undefined);
});

test('archive controls accept only a saved identifier and distinguish legacy or failed saves', () => {
  const c = context();
  vm.runInContext(functions('paperArchiveControls'), c);
  assert.match(c.paperArchiveControls({status:'saved',archive_id:id}), /data-paper-archive=/);
  for (const ref of [{}, {status:'failed',archive_id:id}, {status:'saved',archive_id:'../file'},
                     {status:'saved',archive_id:'<script>'}]) {
    assert.doesNotMatch(c.paperArchiveControls(ref), /data-paper-archive=/);
  }
});

test('restore only reads the verified archive and never adds a fresh execution receipt', async () => {
  const seen = [];
  const payload = {request:{minimum_commission:5},metrics:{ending_equity:9995},equity_curve:[{equity:9995}],
    paper_archive:{status:'verified',archive_id:id,restored:true}};
  const c = context({fetchJson:async url => {seen.push(url);return payload;},
    appendExecutionReceipt() {throw Error('must not create a run');},
    runPaper() {throw Error('must not recompute');}});
  vm.runInContext(functions('restorePaperArchive'), c);
  const button = {disabled:false};
  await c.restorePaperArchive(id,button);
  assert.deepEqual(seen,[`/api/paper/archive?archive_id=${id}`]);
  assert.equal(c.state.paper,payload);
  assert.equal(button.disabled,false);
});

test('failed or mismatched restore clears old displayed results and releases the control', async () => {
  for (const response of [null,{request:{},metrics:{},equity_curve:[],paper_archive:{status:'verified',archive_id:'b'.repeat(64)}}]) {
    const c = context({state:{paper:{metrics:{total_return:1}}},fetchJson:async () => {
      if (response===null) throw Error('missing');
      return response;
    }});
    vm.runInContext(functions('restorePaperArchive'),c);
    const button = {disabled:false};
    await c.restorePaperArchive(id,button);
    assert.equal(c.state.paper,null);
    assert.equal(button.disabled,false);
  }
});

test('restored matching parameters are still labeled as historical results', () => {
  const c = context({requestObjectFromParams:()=>({}),requestMatchesCurrentParams:()=>true,
    requestFreshnessSummary:()=>''});
  vm.runInContext(functions('resultFreshnessRow'),c);
  assert.match(c.resultFreshnessRow('paper',{request:{},paper_archive:{restored:true}},new URLSearchParams(),[],'').status,/历史/);
  assert.equal(c.resultFreshnessRow('paper',{request:{}},new URLSearchParams(),[],'').status,'当前');
});

test('a slower old archive response cannot replace the latest chosen archive', async () => {
  const resolvers = [];
  const c = context({fetchJson:() => new Promise(resolve => resolvers.push(resolve))});
  vm.runInContext(functions('restorePaperArchive'),c);
  const secondId = 'b'.repeat(64);
  const first = c.restorePaperArchive(id);
  const second = c.restorePaperArchive(secondId);
  const payload = archiveId => ({request:{},metrics:{},equity_curve:[],
    paper_archive:{status:'verified',archive_id:archiveId,restored:true}});
  resolvers[1](payload(secondId)); await second;
  resolvers[0](payload(id)); await first;
  assert.equal(c.state.paper.paper_archive.archive_id,secondId);
});

test('starting a new simulation cancels an older archive load and prevents restore during the run', async () => {
  const resolvers = [];
  const c = context({fetchJson:() => new Promise(resolve => resolvers.push(resolve)),
    renderDashboard() {}, renderControlCenter() {},invalidatePaperResult(error) {throw error;}});
  vm.runInContext(functions('restorePaperArchive','refreshPaper'),c);
  const old = c.restorePaperArchive(id);
  const fresh = c.refreshPaper(new URLSearchParams());
  await c.restorePaperArchive('b'.repeat(64));
  assert.equal(resolvers.length,2);
  const result = {request:{minimum_commission:0},metrics:{ending_equity:10000}};
  resolvers[1](result); await fresh;
  resolvers[0]({request:{minimum_commission:5},metrics:{},equity_curve:[],
    paper_archive:{status:'verified',archive_id:id,restored:true}}); await old;
  assert.equal(c.state.paper,result);
  assert.equal(c.state.paperSimulationRunning,false);
});
