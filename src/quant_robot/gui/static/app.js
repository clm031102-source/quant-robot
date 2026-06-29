const state = {
  snapshot: null,
  controlCenter: null,
  research: null,
  signals: null,
  paper: null,
  promotion: null,
  promotionReview: null,
  evidenceRefresh: null,
  projectStatus: null,
  dailyOps: null,
  riskCandidates: null,
  constrainedSearch: null,
  paperProfiles: null,
  profileObservation: null,
  recentDataRefresh: null,
  postRefreshReplay: null,
  observationSufficiency: null,
  expandedObservationReplay: null,
  iterativeObservationExpansion: null,
  tushareActivationGate: null,
  factorLeaderboard: null,
  leaderboardTab: "primary_cn_etf",
  verificationResult: null,
  activeOperation: null,
  runHistory: [],
  executionReceipts: [],
  safeRunResolver: null,
};

const titles = {
  dashboard: "总览",
  research: "因子研究",
  backtest: "回测报告",
  decision: "决策风控",
  signals: "信号快照",
  paper: "纸面模拟",
  daily: "日常运营",
  promotion: "候选推广",
  data: "数据中心",
  logs: "日志报告",
};

const chartTheme = {
  strategy: "#00796b",
  benchmark: "#bd6c21",
  positive: "#367754",
  negative: "#ad3f3c",
  paper: "#3f6f94",
  background: "#f8faf7",
  grid: "#d7dfd8",
  muted: "#65706a",
};

const sourcePresets = {
  "processed-bars": {
    dataRoot: "data/processed/etf_csv",
    market: "CN_ETF",
    factor: "momentum_2",
    factorWindows: "2,5,10,20,60,120",
    startDate: "2016-01-01",
    endDate: "2026-05-21",
    signalDate: "2026-05-21",
    paperStartDate: "2016-01-01",
    paperEndDate: "2026-05-21",
    executionLag: "1",
    forwardHorizon: "1",
    rebalanceInterval: "5",
  },
  demo_fixture: {
    dataRoot: "",
    market: "CN_ETF",
    factor: "momentum_2",
    factorWindows: "2,3",
    startDate: "2024-01-02",
    endDate: "2024-01-13",
    signalDate: "2024-01-13",
    paperStartDate: "2024-01-04",
    paperEndDate: "2024-01-12",
    executionLag: "1",
    forwardHorizon: "1",
    rebalanceInterval: "1",
  },
};

const RUN_HISTORY_STORAGE_KEY = "quant_robot.gui.run_history.v1";
const RUN_HISTORY_LIMIT = 20;
const EXECUTION_RECEIPT_STORAGE_KEY = "quant_robot.gui.execution_receipts.v1";
const EXECUTION_RECEIPT_LIMIT = 20;
const REQUEST_PREVIEW_INPUT_IDS = [
  "data-source-select",
  "data-root-input",
  "market-select",
  "factor-select",
  "factor-windows",
  "start-date",
  "end-date",
  "execution-lag",
  "forward-horizon",
  "research-top-n",
  "research-cost-bps",
  "rebalance-interval",
  "benchmark-asset-id",
  "cash-annual-return",
  "regime-filter",
  "regime-lookback",
  "min-relative-return",
  "max-drawdown-limit",
  "signal-top-n",
  "signal-as-of",
  "max-asset-weight",
  "max-market-weight",
  "max-gross-exposure",
  "min-cash-weight",
  "paper-market-select",
  "paper-factor-select",
  "paper-top-n",
  "paper-start-date",
  "paper-end-date",
  "paper-initial-cash",
  "paper-commission-bps",
  "paper-slippage-bps",
  "paper-max-asset-weight",
  "paper-max-market-weight",
  "paper-max-gross-exposure",
  "paper-min-cash-weight",
  "paper-drawdown-guard",
  "paper-guard-cooldown",
];
const GLOSSARY_TERMS = [
  ["Sharpe", "单位波动换来的收益。越高越好，但异常高要先怀疑过拟合。"],
  ["最大回撤", "从最高点跌到最低点的最大亏损幅度。收益高但回撤大，需要看你是否能承受。"],
  ["胜率", "盈利交易或盈利周期占比。高胜率不等于高收益，还要看亏损大小。"],
  ["RankIC", "因子排序和未来收益排序的相关性。正值且稳定，说明排序有信息量。"],
  ["年化", "把样本收益折算到一年。样本短时容易失真，必须看长周期/OOS。"],
  ["bps", "万分之一。5 bps 就是 0.05%，常用来表示佣金或滑点。"],
  ["TopN", "每次选择排名最靠前的 N 个标的。N 越小越集中，收益和回撤都可能更极端。"],
  ["case", "一次具体参数组合的编号，不等于唯一因子。"],
  ["Regime", "市场状态过滤，例如只在宽松/强趋势环境交易。"],
  ["Gross cap", "总仓位上限。0.9 表示最多用 90% 资金，留 10% 现金。"],
  ["processed-bars", "本地已经清洗好的行情数据，用于回测和模拟，不会联网下单。"],
  ["paper", "本地模拟盘或纸面回放，只产生模拟成交，不连接账户。"],
];
const BEGINNER_STEPS = [
  {
    id: "safety",
    title: "先确认安全",
    plain: "确认软件只做研究和本地模拟，不会连接券商、账户或真实订单。",
    button: "看安全边界",
    target: "control-safety-boundary",
  },
  {
    id: "leaderboard",
    title: "只看 ETF 主线",
    plain: "默认先看 CN_ETF 主线榜，CN 个股只是辅助研究。",
    button: "看 CN_ETF 主线榜",
    target: "factor-leaderboard-table",
    leaderboardTab: "primary_cn_etf",
  },
  {
    id: "research",
    title: "跑一次本地回测",
    plain: "用当前参数做本地回测，先看收益、回撤、胜率和夏普。",
    button: "本地回测当前参数",
    action: "research_backtest",
  },
  {
    id: "result",
    title: "看结果能不能信",
    plain: "看回测来源、闸门、是否缺 OOS、是否疑似过拟合。",
    button: "看回测闸门",
    target: "control-backtest-gate",
  },
  {
    id: "paper",
    title: "再做模拟盘回放",
    plain: "只有研究结果看起来合理，才进入本地模拟盘回放。",
    button: "本地模拟盘回放",
    action: "paper_simulation",
  },
];

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  bindRequestPreviewInputs();
  renderFactorGlossary();
  renderBeginnerVerdict();
  renderBeginnerGuide();
  renderBeginnerProgress();
  await loadSnapshot();
  await loadFactorLeaderboard();
  await loadControlCenter();
  await loadProjectStatus();
  await loadDailyOps();
  await loadRiskCandidates();
  await loadConstrainedSearch();
  await loadPaperProfiles();
  await loadProfileObservation();
  await loadRecentDataRefresh();
  await loadPostRefreshReplay();
  await loadObservationSufficiency();
  await loadExpandedObservationReplay();
  await loadIterativeObservationExpansion();
  await loadTushareActivationGate();
});

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const page = button.dataset.page;
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelectorAll(".page").forEach((section) => section.classList.remove("active-page"));
      byId(`page-${page}`).classList.add("active-page");
      byId("page-title").textContent = titles[page] || page;
      document.querySelector(".workspace")?.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function bindActions() {
  byId("run-startup-workflows").addEventListener("click", runStartupWorkflows);
  byId("run-research").addEventListener("click", runResearch);
  byId("run-signals").addEventListener("click", runSignals);
  byId("run-paper").addEventListener("click", runPaper);
  byId("run-daily-ops").addEventListener("click", runDailyOps);
  byId("run-promotion").addEventListener("click", runPromotionOps);
  byId("safe-run-cancel")?.addEventListener("click", () => resolveSafeWorkflow(false));
  byId("safe-run-confirm")?.addEventListener("click", () => resolveSafeWorkflow(true));
  byId("safe-run-modal")?.addEventListener("click", (event) => {
    if (event.target?.id === "safe-run-modal") resolveSafeWorkflow(false);
  });
  byId("data-source-select").addEventListener("change", () => {
    applySourcePreset(true);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !byId("safe-run-modal")?.hidden) resolveSafeWorkflow(false);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".segmented-button[data-leaderboard-tab]");
    if (!button) return;
    setLeaderboardTab(button.dataset.leaderboardTab || "primary_cn_etf");
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-next]");
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    runBeginnerNext(button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-target]");
    if (!button) return;
    jumpToBeginnerTarget(button.dataset.beginnerTarget || "", button.dataset.leaderboardTab || "");
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-factor-beginner-jump]");
    if (!button) return;
    jumpToBeginnerTarget(button.dataset.factorBeginnerJump || "factor-leaderboard-table", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-parameter-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerParameterJump || "control-request-preview", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-result-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerResultJump || "control-backtest-gate", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-progress-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerProgressJump || "control-operation-ledger", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-recovery-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerRecoveryJump || "control-active-operation", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-action]");
    if (!button) return;
    runBeginnerAction(button.dataset.beginnerAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-verification-gate]");
    if (!button) return;
    runVerificationGate(button.dataset.verificationGate || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action-workflow], [data-console-action]");
    if (!button) return;
    runActionCenterWorkflow(button.dataset.actionWorkflow || "", button);
  });
}

function bindRequestPreviewInputs() {
  REQUEST_PREVIEW_INPUT_IDS.forEach((id) => {
    const element = byId(id);
    if (!element) return;
    element.addEventListener("input", renderRequestPreview);
    element.addEventListener("change", renderRequestPreview);
  });
}

async function loadSnapshot() {
  state.snapshot = await fetchJson("/api/snapshot");
  byId("mode-pill").textContent = `${zhConsoleText(state.snapshot.data_mode)} / 本地`;
  byId("data-mode-label").textContent = zhConsoleText(state.snapshot.data_mode || "local");
  byId("broker-status-label").textContent = state.snapshot.risk?.account_connected ? "已连接" : "无券商连接";
  byId("run-state-label").textContent = "就绪";
  fillFactorSelect(state.snapshot.available_factors || []);
  applySourcePreset(false);
  renderDashboard();
  renderDataCenter();
  renderLogs();
}

async function loadFactorLeaderboard() {
  state.factorLeaderboard = await fetchJson("/api/factors/leaderboard?limit=20");
  renderFactorLeaderboard();
  renderDashboard();
}

async function loadControlCenter() {
  state.controlCenter = await fetchJson("/api/control/status");
  applyControlDefaults();
  state.runHistory = loadRunHistory(state.controlCenter?.run_history || {});
  renderControlCenter();
}

async function loadProjectStatus() {
  state.projectStatus = await fetchJson("/api/project/status");
  renderProjectStatus();
  renderDashboard();
}

async function loadDailyOps() {
  state.dailyOps = await fetchJson("/api/daily/ops");
  renderDailyOps();
  renderDashboard();
}

async function loadRiskCandidates() {
  state.riskCandidates = await fetchJson("/api/risk/candidates");
  renderRiskCandidates();
  renderDashboard();
}

async function loadConstrainedSearch() {
  state.constrainedSearch = await fetchJson("/api/risk/constrained-search");
  renderConstrainedSearch();
  renderDashboard();
}

async function loadPaperProfiles() {
  state.paperProfiles = await fetchJson("/api/risk/paper-profiles");
  renderPaperProfiles();
  renderDashboard();
}

async function loadProfileObservation() {
  state.profileObservation = await fetchJson("/api/risk/profile-observation");
  renderProfileObservation();
  renderDashboard();
}

async function loadRecentDataRefresh() {
  state.recentDataRefresh = await fetchJson("/api/data/recent-refresh");
  renderRecentDataRefresh();
  renderDashboard();
}

async function loadPostRefreshReplay() {
  state.postRefreshReplay = await fetchJson("/api/data/post-refresh-replay");
  renderPostRefreshReplay();
  renderDashboard();
}

async function loadObservationSufficiency() {
  state.observationSufficiency = await fetchJson("/api/risk/observation-sufficiency");
  renderObservationSufficiency();
  renderDashboard();
}

async function loadExpandedObservationReplay() {
  state.expandedObservationReplay = await fetchJson("/api/risk/expanded-observation-replay");
  renderExpandedObservationReplay();
  renderDashboard();
}

async function loadIterativeObservationExpansion() {
  state.iterativeObservationExpansion = await fetchJson("/api/risk/iterative-observation-expansion");
  renderIterativeObservationExpansion();
  renderDashboard();
}

async function loadTushareActivationGate() {
  state.tushareActivationGate = await fetchJson("/api/risk/tushare-activation-gate");
  renderTushareActivationGate();
  renderDashboard();
}

function addSourceParams(params) {
  params.set("source", valueOf("data-source-select") || "demo_fixture");
  const dataRoot = valueOf("data-root-input");
  if (dataRoot) params.set("data_root", dataRoot);
}

function factorWindowCsvForFactor(factor, rawWindows) {
  const windows = new Set();
  String(rawWindows || "")
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((value) => Number.isInteger(value) && value > 0)
    .forEach((value) => windows.add(value));
  const suffix = String(factor || "").match(/_(\d+)$/);
  if (suffix) windows.add(Number(suffix[1]));
  return Array.from(windows).sort((left, right) => left - right).join(",");
}

function buildResearchParams() {
  const factor = valueOf("factor-select") || "momentum_2";
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor,
    factor_windows: factorWindowCsvForFactor(factor, valueOf("factor-windows")),
    top_n: valueOf("research-top-n") || "2",
    cost_bps: valueOf("research-cost-bps") || "5",
    start_date: valueOf("start-date"),
    end_date: valueOf("end-date"),
    execution_lag: valueOf("execution-lag") || "1",
    forward_horizon: valueOf("forward-horizon") || "1",
    rebalance_interval: valueOf("rebalance-interval") || "1",
    benchmark_asset_id: valueOf("benchmark-asset-id"),
    cash_annual_return: valueOf("cash-annual-return") || "0",
    regime_filter: byId("regime-filter")?.checked ? "true" : "false",
    regime_lookback: valueOf("regime-lookback") || "20",
    min_relative_return: valueOf("min-relative-return"),
    max_drawdown_limit: valueOf("max-drawdown-limit"),
  });
  addSourceParams(params);
  return params;
}

function buildSignalParams() {
  const factor = valueOf("factor-select") || "momentum_2";
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor,
    factor_windows: factorWindowCsvForFactor(factor, valueOf("factor-windows")),
    top_n: valueOf("signal-top-n") || "2",
    as_of_date: valueOf("signal-as-of"),
    max_asset_weight: valueOf("max-asset-weight") || "1",
    max_market_weight: valueOf("max-market-weight") || "1",
    max_gross_exposure: valueOf("max-gross-exposure") || "1",
    min_cash_weight: valueOf("min-cash-weight") || "0",
  });
  addSourceParams(params);
  return params;
}

function buildPaperParams() {
  const factor = valueOf("paper-factor-select") || "momentum_2";
  const params = new URLSearchParams({
    market: valueOf("paper-market-select"),
    factor,
    factor_windows: factorWindowCsvForFactor(factor, valueOf("factor-windows")),
    top_n: valueOf("paper-top-n") || "2",
    rebalance_interval: valueOf("rebalance-interval") || "1",
    start_date: valueOf("paper-start-date"),
    end_date: valueOf("paper-end-date"),
    initial_cash: valueOf("paper-initial-cash") || "100000",
    commission_bps: valueOf("paper-commission-bps") || "5",
    slippage_bps: valueOf("paper-slippage-bps") || "5",
    max_asset_weight: valueOf("paper-max-asset-weight") || "1",
    max_market_weight: valueOf("paper-max-market-weight") || "1",
    max_gross_exposure: valueOf("paper-max-gross-exposure") || "1",
    min_cash_weight: valueOf("paper-min-cash-weight") || "0",
    max_drawdown_guard: valueOf("paper-drawdown-guard"),
    guard_cooldown_periods: valueOf("paper-guard-cooldown") || "0",
  });
  addSourceParams(params);
  return params;
}

function parameterPlainValue(params, key, fallback = "--") {
  const value = params?.get ? params.get(key) : params?.[key];
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

function parameterSourceText(source, dataRoot) {
  if (source === "processed-bars") {
    return `本地清洗行情${dataRoot && dataRoot !== "--" ? `：${dataRoot}` : ""}`;
  }
  if (source === "demo_fixture") return "演示数据，只适合试操作，不适合判断因子";
  return source || "--";
}

function parameterBpsText(value, fallback = "--") {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return `${number} bps（约 ${formatPercent(number / 10000)}）`;
}

function parameterWeightText(value, fallback = "--") {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  if (number <= 1) return formatPercent(number);
  return String(value);
}

function parameterDateWindow(params, startKey = "start_date", endKey = "end_date") {
  const start = parameterPlainValue(params, startKey);
  const end = parameterPlainValue(params, endKey);
  if (start === "--" && end === "--") return "--";
  return `${start} 至 ${end}`;
}

function beginnerParameterRows(researchParams, signalParams, paperParams) {
  const source = parameterPlainValue(researchParams, "source");
  const market = parameterPlainValue(researchParams, "market");
  const factor = parameterPlainValue(researchParams, "factor");
  const windows = parameterPlainValue(researchParams, "factor_windows");
  const topN = parameterPlainValue(researchParams, "top_n");
  const paperTopN = parameterPlainValue(paperParams, "top_n");
  const signalTopN = parameterPlainValue(signalParams, "top_n");
  const dataRoot = parameterPlainValue(researchParams, "data_root");
  const regimeFilter = parameterPlainValue(researchParams, "regime_filter", "false");
  const regimeLookback = parameterPlainValue(researchParams, "regime_lookback");
  const maxAsset = parameterPlainValue(paperParams, "max_asset_weight");
  const maxMarket = parameterPlainValue(paperParams, "max_market_weight");
  const maxGross = parameterPlainValue(paperParams, "max_gross_exposure");
  const minCash = parameterPlainValue(paperParams, "min_cash_weight");
  const drawdownGuard = parameterPlainValue(paperParams, "max_drawdown_guard");
  const guardText = drawdownGuard === "--" ? "未设置自动止损闸门" : `回撤到 ${parameterWeightText(drawdownGuard)} 后触发保护`;

  return [
    [
      "数据来源",
      `${parameterSourceText(source, dataRoot)}。这决定回测是不是用本地清洗后的真实 ETF 数据。`,
      source === "processed-bars" ? "ok" : "warn",
    ],
    [
      "研究标的",
      `${market}。主线应该是 CN_ETF；如果不是，先别把结果当成 ETF 轮动结论。`,
      market === "CN_ETF" ? "ok" : "warn",
    ],
    [
      "回测区间",
      `${parameterDateWindow(researchParams)}。这是用来判断因子长期表现的样本范围。`,
      "ok",
    ],
    [
      "因子和窗口",
      `${factor}，窗口 ${windows}。窗口越短越敏感，窗口越长越偏趋势确认。`,
      "ok",
    ],
    [
      "每次买几只",
      `研究 Top${topN}，信号 Top${signalTopN}，模拟盘 Top${paperTopN}。TopN 越小越集中，收益和回撤都可能更极端。`,
      topN === signalTopN && topN === paperTopN ? "ok" : "warn",
    ],
    [
      "交易成本",
      `研究成本 ${parameterBpsText(parameterPlainValue(researchParams, "cost_bps"))}；模拟盘佣金 ${parameterBpsText(parameterPlainValue(paperParams, "commission_bps"))}，滑点 ${parameterBpsText(parameterPlainValue(paperParams, "slippage_bps"))}。`,
      "ok",
    ],
    [
      "执行假设",
      `信号延迟 ${parameterPlainValue(researchParams, "execution_lag")} 天，预测 ${parameterPlainValue(researchParams, "forward_horizon")} 天，换仓间隔 ${parameterPlainValue(researchParams, "rebalance_interval")} 天。`,
      "ok",
    ],
    [
      "市场状态过滤",
      regimeFilter === "true"
        ? `已开启，回看 ${regimeLookback} 天；只在允许的市场状态里交易。`
        : "未开启；会完整承受样本里的牛熊震荡。",
      regimeFilter === "true" ? "ok" : "warn",
    ],
    [
      "模拟盘风控",
      `单资产 ${parameterWeightText(maxAsset)}，单市场 ${parameterWeightText(maxMarket)}，总仓位 ${parameterWeightText(maxGross)}，最低现金 ${parameterWeightText(minCash)}；${guardText}。`,
      maxGross !== "--" && Number(maxGross) <= 1 ? "ok" : "warn",
    ],
    [
      "安全边界",
      "这里只做本地研究、建议信号和纸面模拟；不会读取账户、连接券商或真实下单。",
      "ok",
    ],
  ];
}

function renderBeginnerParameterExplainer(
  researchParams = buildResearchParams(),
  signalParams = buildSignalParams(),
  paperParams = buildPaperParams(),
) {
  const root = byId("beginner-parameter-explainer");
  const summaryTarget = byId("beginner-parameter-summary");
  const rowsTarget = byId("beginner-parameter-rows");
  if (!root || !summaryTarget || !rowsTarget) return;
  const source = parameterPlainValue(researchParams, "source");
  const market = parameterPlainValue(researchParams, "market");
  const factor = parameterPlainValue(researchParams, "factor");
  const dateWindow = parameterDateWindow(researchParams);
  const topN = parameterPlainValue(researchParams, "top_n");
  const cost = parameterBpsText(parameterPlainValue(researchParams, "cost_bps"));
  const tone = market === "CN_ETF" && source === "processed-bars" ? "ok" : "warn";
  summaryTarget.innerHTML = `
    <div class="beginner-parameter-head ${escapeHtml(tone)}">
      <div>
        <strong>${escapeHtml(`现在会用 ${market} 的 ${factor} 做本地研究`)}</strong>
        <span>${escapeHtml(`${dateWindow} / Top${topN} / 成本 ${cost}`)}</span>
      </div>
      <div class="beginner-parameter-actions">
        <button class="secondary-button" type="button" data-beginner-parameter-jump="control-request-preview">看请求详情</button>
        <button class="primary-button" type="button" data-beginner-action="research_backtest">本地回测当前参数</button>
      </div>
    </div>
  `;
  rowsTarget.innerHTML = statusRows(beginnerParameterRows(researchParams, signalParams, paperParams));
}

function beginnerResultMetric(label, value, detail, tone = "muted") {
  return `
    <div class="beginner-result-metric ${escapeHtml(tone)}">
      <small>${escapeHtml(label)}</small>
      <strong>${escapeHtml(value)}</strong>
      <span>${escapeHtml(detail)}</span>
    </div>
  `;
}

function beginnerResultGateSummary(evaluatedRows = []) {
  return {
    failed: evaluatedRows.filter((row) => row.result?.status === "failed").length,
    awaiting: evaluatedRows.filter((row) => row.result?.status === "awaiting_metric").length,
    passed: evaluatedRows.filter((row) => ["passed", "blocked_expected"].includes(row.result?.status)).length,
    total: evaluatedRows.length,
  };
}

function beginnerResultVerdict(
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  evaluatedRows = [],
  paperReadiness = {},
  safety = {},
) {
  const hasResearch = Number.isFinite(Number(metrics.total_return)) || Number.isFinite(Number(metrics.sharpe));
  const hasPaper = Number.isFinite(Number(paperMetrics.ending_equity)) || Number.isFinite(Number(paperMetrics.total_return));
  const gates = beginnerResultGateSummary(evaluatedRows);
  const totalReturn = Number(metrics.total_return);
  const annualized = Number(metrics.annualized_return);
  const sharpe = Number(metrics.sharpe);
  const maxDrawdown = Number(metrics.max_drawdown);
  const winRate = Number(metrics.win_rate);
  const relativeReturn = Number(benchmark.relative_return);
  const paperStatus = paperReadiness.summary?.status || "review";
  const liveBlocked = safety.live_trading_allowed === false && safety.order_placement_allowed === false;
  const metricRows = [
    beginnerResultMetric("总收益", formatPercent(metrics.total_return), "赚了多少", Number.isFinite(totalReturn) && totalReturn > 0 ? "ok" : "warn"),
    beginnerResultMetric("年化", formatPercent(metrics.annualized_return), "折算到一年", Number.isFinite(annualized) && annualized > 0 ? "ok" : "warn"),
    beginnerResultMetric("Sharpe", formatDecimal(metrics.sharpe), "收益是否平稳", Number.isFinite(sharpe) && sharpe >= 1 ? "ok" : "warn"),
    beginnerResultMetric("最大回撤", formatPercent(metrics.max_drawdown), "中途最大亏损", Number.isFinite(maxDrawdown) && Math.abs(maxDrawdown) <= 0.3 ? "ok" : "warn"),
    beginnerResultMetric("胜率", formatPercent(metrics.win_rate), "赚钱周期占比", Number.isFinite(winRate) && winRate >= 0.5 ? "ok" : "warn"),
    beginnerResultMetric("相对基准", formatPercent(benchmark.relative_return), "是否跑赢基准", Number.isFinite(relativeReturn) && relativeReturn > 0 ? "ok" : "warn"),
  ];

  if (!hasResearch) {
    return {
      tone: "warn",
      title: "还没有当前回测结果",
      summary: "先运行一次本地回测，软件才知道这组参数的收益、回撤、胜率和 Sharpe。",
      metricRows,
      reasonRows: [
        ["现在能做", "点击本地回测当前参数，先得到一份可判读的研究结果。", "warn"],
        ["先别做", "不要在没有当前回测结果时直接生成模拟盘结论。", "danger"],
        ["安全边界", "本地回测只读取本地数据，不连接券商、不读取账户、不下单。", "ok"],
      ],
      actions: [
        { label: "本地回测当前参数", action: "research_backtest", tone: "primary-button" },
        { label: "看当前参数", jump: "beginner-parameter-explainer", tone: "secondary-button" },
      ],
    };
  }

  if (gates.failed > 0) {
    return {
      tone: "danger",
      title: "结果还不能推进",
      summary: `当前有 ${gates.failed} 个关键闸门未通过。收益再好看，也要先解释失败项。`,
      metricRows,
      reasonRows: [
        ["收益质量", `总收益 ${formatPercent(metrics.total_return)}，Sharpe ${formatDecimal(metrics.sharpe)}；先看是否只是单段行情贡献。`, "warn"],
        ["回撤风险", `最大回撤 ${formatPercent(metrics.max_drawdown)}；你能接受 30% 左右回撤，但闸门失败仍要复核原因。`, "danger"],
        ["证据状态", `${gates.passed}/${gates.total} 个闸门通过，${gates.awaiting} 个等待指标。`, "warn"],
        ["下一步", "打开回测闸门，逐条看失败项，而不是直接进入模拟盘。", "danger"],
      ],
      actions: [
        { label: "看回测闸门", jump: "control-backtest-gate", tone: "primary-button" },
        { label: "看结果证据", jump: "control-result-evidence", tone: "secondary-button" },
      ],
    };
  }

  if (gates.awaiting > 0 || !hasPaper || paperStatus !== "paper_candidate") {
    return {
      tone: "warn",
      title: "可以复核，但还不是可推广信号",
      summary: "研究回测已有结果，下一步应补齐当前模拟盘和证据链，仍然不能当实盘信号。",
      metricRows,
      reasonRows: [
        ["收益质量", `总收益 ${formatPercent(metrics.total_return)}，年化 ${formatPercent(metrics.annualized_return)}，Sharpe ${formatDecimal(metrics.sharpe)}。`, Number.isFinite(sharpe) && sharpe >= 1 ? "ok" : "warn"],
        ["回撤风险", `最大回撤 ${formatPercent(metrics.max_drawdown)}，胜率 ${formatPercent(metrics.win_rate)}；回撤高时要看能否长期承受。`, Math.abs(maxDrawdown) <= 0.3 ? "ok" : "warn"],
        ["证据状态", hasPaper ? `已有模拟盘权益 ${formatNumber(paperMetrics.ending_equity)}。` : "还缺当前参数的本地模拟盘回放。", hasPaper ? "ok" : "warn"],
        ["下一步", "先做本地模拟盘回放，再看模拟盘交接和结果证据。", "warn"],
      ],
      actions: [
        { label: "本地模拟盘回放", action: "paper_simulation", tone: "primary-button" },
        { label: "看模拟盘交接", jump: "control-paper-readiness", tone: "secondary-button" },
      ],
    };
  }

  return {
    tone: "ok",
    title: "可以进入纸面观察",
    summary: "当前研究结果和模拟盘证据相对完整，但仍只属于本地研究到纸面模拟，不是实盘下单信号。",
    metricRows,
    reasonRows: [
      ["收益质量", `总收益 ${formatPercent(metrics.total_return)}，Sharpe ${formatDecimal(metrics.sharpe)}，相对基准 ${formatPercent(benchmark.relative_return)}。`, "ok"],
      ["回撤风险", `最大回撤 ${formatPercent(metrics.max_drawdown)}；继续观察不同市场阶段是否恶化。`, Math.abs(maxDrawdown) <= 0.3 ? "ok" : "warn"],
      ["证据状态", `闸门 ${gates.passed}/${gates.total} 已通过，模拟盘权益 ${formatNumber(paperMetrics.ending_equity)}。`, "ok"],
      ["安全边界", liveBlocked ? "实盘仍被硬阻断：无券商、无账户、无订单。" : "安全边界异常，必须先审计。", liveBlocked ? "ok" : "danger"],
    ],
    actions: [
      { label: "看模拟盘交接", jump: "control-paper-readiness", tone: "primary-button" },
      { label: "看结果证据", jump: "control-result-evidence", tone: "secondary-button" },
    ],
  };
}

function renderBeginnerResultInterpreter(
  backtestGate = {},
  paperReadiness = {},
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  executionReceipts = [],
  researchRequest = {},
  paperRequest = {},
  safety = {},
) {
  const root = byId("beginner-result-interpreter");
  const summaryTarget = byId("beginner-result-summary");
  const metricsTarget = byId("beginner-result-metrics");
  const rowsTarget = byId("beginner-result-rows");
  if (!root || !summaryTarget || !metricsTarget || !rowsTarget) return;
  const evaluatedRows = evaluateBacktestGateRows(
    backtestGate,
    metrics,
    benchmark,
    paperMetrics,
    executionReceipts,
    researchRequest,
    paperRequest,
    safety,
  );
  const verdict = beginnerResultVerdict(metrics, benchmark, paperMetrics, evaluatedRows, paperReadiness, safety);
  ["ok", "warn", "danger", "muted"].forEach((tone) => root.classList.remove(tone));
  root.classList.add(verdict.tone);
  const actions = (verdict.actions || []).map((action) => {
    const attrs = action.action
      ? `data-beginner-action="${escapeHtml(action.action)}"`
      : `data-beginner-result-jump="${escapeHtml(action.jump || "control-backtest-gate")}"`;
    return `<button class="${escapeHtml(action.tone || "secondary-button")}" type="button" ${attrs}>${escapeHtml(action.label)}</button>`;
  }).join("");
  summaryTarget.innerHTML = `
    <div class="beginner-result-head ${escapeHtml(verdict.tone)}">
      <div>
        <strong>${escapeHtml(verdict.title)}</strong>
        <span>${escapeHtml(verdict.summary)}</span>
      </div>
      <div class="beginner-result-actions">${actions}</div>
    </div>
  `;
  metricsTarget.innerHTML = verdict.metricRows.join("");
  rowsTarget.innerHTML = statusRows(verdict.reasonRows);
}

function renderRequestPreview() {
  const target = byId("control-request-preview");
  const researchParams = buildResearchParams();
  const signalParams = buildSignalParams();
  const paperParams = buildPaperParams();
  const rows = [
    {
      label: "Research backtest",
      status: "ok",
      endpoint: `/api/research?${researchParams.toString()}`,
      params: researchParams,
      detail: "full parameter backtest request",
    },
    {
      label: "Signal snapshot",
      status: "warn",
      endpoint: `/api/signals?${signalParams.toString()}`,
      params: signalParams,
      detail: "advisory target-weight request",
    },
    {
      label: "Paper simulation",
      status: "warn",
      endpoint: `/api/paper?${paperParams.toString()}`,
      params: paperParams,
      detail: "local paper-only simulation request",
    },
  ];
  if (target) {
    target.innerHTML = rows.map((row) => `
      <div class="list-row ${escapeHtml(row.status)}">
        <strong>${escapeHtml(row.label)}</strong>
        <span>${escapeHtml(row.endpoint)}</span>
        <span>${escapeHtml(requestPreviewSummary(row.params))}</span>
        <span>${escapeHtml(row.detail)}</span>
      </div>
    `).join("");
  }
  renderBeginnerParameterExplainer(researchParams, signalParams, paperParams);
  renderResultFreshness();
  renderParameterConsistency();
}

function applyControlDefaults() {
  const defaults = state.controlCenter?.form_defaults || {};
  if (defaults.stage !== "gui_form_defaults") return;
  const research = defaults.research || {};
  const signal = defaults.signal || {};
  const paper = defaults.paper || {};

  setValue("data-source-select", research.source || "processed-bars");
  setValue("data-root-input", research.data_root || "");
  setValue("market-select", research.market || "CN_ETF");
  setFactorValue("factor-select", research.factor || "momentum_2");
  setValue("factor-windows", research.factor_windows || "");
  setValue("start-date", research.start_date || "");
  setValue("end-date", research.end_date || "");
  setValue("execution-lag", research.execution_lag ?? "");
  setValue("forward-horizon", research.forward_horizon ?? "");
  setValue("research-top-n", research.top_n ?? "");
  setValue("research-cost-bps", research.cost_bps ?? "");
  setValue("rebalance-interval", research.rebalance_interval ?? "");
  setValue("benchmark-asset-id", research.benchmark_asset_id || "");
  setValue("cash-annual-return", research.cash_annual_return ?? "");
  if (byId("regime-filter")) byId("regime-filter").checked = Boolean(research.regime_filter);
  setValue("regime-lookback", research.regime_lookback ?? "");
  setValue("min-relative-return", research.min_relative_return ?? "");
  setValue("max-drawdown-limit", research.max_drawdown_limit ?? "");

  setValue("signal-top-n", signal.top_n ?? research.top_n ?? "");
  setValue("signal-as-of", signal.as_of_date || research.end_date || "");
  setValue("max-asset-weight", signal.max_asset_weight ?? "");
  setValue("max-market-weight", signal.max_market_weight ?? "");
  setValue("max-gross-exposure", signal.max_gross_exposure ?? "");
  setValue("min-cash-weight", signal.min_cash_weight ?? "");

  setValue("paper-market-select", paper.market || research.market || "CN_ETF");
  setFactorValue("paper-factor-select", paper.factor || research.factor || "momentum_2");
  setValue("paper-top-n", paper.top_n ?? research.top_n ?? "");
  setValue("paper-start-date", paper.start_date || research.start_date || "");
  setValue("paper-end-date", paper.end_date || research.end_date || "");
  setValue("paper-initial-cash", paper.initial_cash ?? "");
  setValue("paper-commission-bps", paper.commission_bps ?? "");
  setValue("paper-slippage-bps", paper.slippage_bps ?? "");
  setValue("paper-max-asset-weight", paper.max_asset_weight ?? "");
  setValue("paper-max-market-weight", paper.max_market_weight ?? "");
  setValue("paper-max-gross-exposure", paper.max_gross_exposure ?? "");
  setValue("paper-min-cash-weight", paper.min_cash_weight ?? "");
  setValue("paper-drawdown-guard", paper.max_drawdown_guard ?? "");
  setValue("paper-guard-cooldown", paper.guard_cooldown_periods ?? "");

  renderRequestPreview();
}

function requestPreviewSummary(params) {
  return [
    `source=${params.get("source") || "--"}`,
    `market=${params.get("market") || "--"}`,
    `factor=${params.get("factor") || "--"}`,
    `windows=${params.get("factor_windows") || "--"}`,
    `top_n=${params.get("top_n") || "--"}`,
    `cost=${params.get("cost_bps") || params.get("commission_bps") || "--"}bps`,
    `window=${params.get("start_date") || params.get("as_of_date") || "--"} to ${params.get("end_date") || params.get("as_of_date") || "--"}`,
  ].join(" / ");
}

function renderResultFreshness() {
  const target = byId("control-result-freshness");
  if (!target) return;
  const rows = [
    resultFreshnessRow(
      "Research result",
      state.research,
      buildResearchParams(),
      ["market", "factor_name", "top_n", "cost_bps", "start_date", "end_date"],
      "Run research after changing market, factor, TopN, cost, or date window.",
    ),
    resultFreshnessRow(
      "Signal result",
      state.signals,
      buildSignalParams(),
      ["market", "factor_name", "top_n", "as_of_date"],
      "Regenerate advisory signals after changing factor, TopN, or signal date.",
    ),
    resultFreshnessRow(
      "Paper result",
      state.paper,
      buildPaperParams(),
      ["market", "factor_name", "top_n", "start_date", "end_date", "initial_cash"],
      "Rerun paper simulation after changing market, factor, TopN, date window, or initial cash.",
    ),
  ];
  target.innerHTML = rows.map((row) => `
    <div class="list-row ${escapeHtml(row.statusClass)}">
      <strong>${escapeHtml(`${row.label} / ${row.status}`)}</strong>
      <span>${escapeHtml(row.currentSummary)}</span>
      <span>${escapeHtml(row.resultSummary)}</span>
      <span>${escapeHtml(row.detail)}</span>
    </div>
  `).join("");
}

function renderParameterConsistency(authority = state.controlCenter?.parameter_authority || {}) {
  const target = byId("control-parameter-consistency");
  if (!target) return;
  const rows = parameterConsistencyRows(authority);
  const driftCount = rows.filter((row) => row.status !== "current").length;
  const summary = authority.summary || {};
  const headerClass = driftCount > 0 ? "warn" : "ok";
  const headerStatus = driftCount > 0 ? "drift" : (summary.status || "current");
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Parameter authority / ${headerStatus}`)}</strong>
      <span>${escapeHtml(`workflows=${rows.length} / drift=${driftCount}`)}</span>
      <span>${escapeHtml(summary.next_action || "Current form parameters match canonical workflow requests.")}</span>
    </div>
  `;
  const body = rows.map((row) => `
    <div class="list-row ${escapeHtml(row.status === "current" ? "ok" : "warn")}">
      <strong>${escapeHtml(`${row.label} / ${row.status}`)}</strong>
      <span>${escapeHtml(`mismatch=${row.mismatchKeys.length ? row.mismatchKeys.join(", ") : "none"}`)}</span>
      <span>${escapeHtml(`form=${requestFreshnessSummary(row.formRequest)}`)}</span>
      <span>${escapeHtml(`canonical=${requestFreshnessSummary(row.canonicalRequest)}`)}</span>
    </div>
  `).join("");
  target.innerHTML = header + (body || `
    <div class="list-row warn">
      <strong>No parameter authority</strong>
      <span>Load control-center status to compare current form parameters with workflow requests.</span>
    </div>
  `);
}

function parameterConsistencyRows(authority = {}) {
  const authorityRows = Array.isArray(authority.rows) ? authority.rows : [];
  return authorityRows.map((item) => {
    const workflowId = item.workflow_id || "";
    const currentParams = paramsForWorkflow(workflowId);
    const formRequest = requestObjectFromParams(currentParams);
    const canonicalRequest = item.canonical_request || {};
    const comparisonKeys = Array.isArray(item.comparison_keys) ? item.comparison_keys : [];
    const mismatchKeys = parameterMismatchKeys(formRequest, canonicalRequest, comparisonKeys);
    return {
      workflowId,
      label: item.label || workflowId,
      status: mismatchKeys.length === 0 ? "current" : "drift",
      mismatchKeys,
      formRequest,
      canonicalRequest,
    };
  });
}

function paramsForWorkflow(workflowId) {
  if (workflowId === "research_backtest") return buildResearchParams();
  if (workflowId === "signal_snapshot") return buildSignalParams();
  if (workflowId === "paper_simulation") return buildPaperParams();
  return new URLSearchParams();
}

function parameterMismatchKeys(formRequest = {}, canonicalRequest = {}, keys = []) {
  return keys.filter((key) => (
    normalizeRequestValue(requestValue(formRequest, key))
    !== normalizeRequestValue(requestValue(canonicalRequest, key))
  ));
}

function resultFreshnessRow(label, result, params, keys, detail) {
  const currentRequest = requestObjectFromParams(params);
  const resultRequest = result?.request || {};
  if (!result || !result.request) {
    return {
      label,
      status: "not_run",
      statusClass: "warn",
      currentSummary: `current=${requestFreshnessSummary(currentRequest)}`,
      resultSummary: "result=not available yet",
      detail,
    };
  }
  const isCurrent = requestMatchesCurrentParams(resultRequest, params, keys);
  return {
    label,
    status: isCurrent ? "current" : "stale",
    statusClass: isCurrent ? "ok" : "warn",
    currentSummary: `current=${requestFreshnessSummary(currentRequest)}`,
    resultSummary: `result=${requestFreshnessSummary(resultRequest)}`,
    detail: isCurrent ? "Displayed metrics match the current form parameters." : detail,
  };
}

function requestObjectFromParams(params) {
  return {
    market: params.get("market") || "",
    factor_name: params.get("factor") || params.get("factor_name") || "",
    factor_windows: params.get("factor_windows") || "",
    top_n: params.get("top_n") || "",
    cost_bps: params.get("cost_bps") || "",
    start_date: params.get("start_date") || "",
    end_date: params.get("end_date") || "",
    as_of_date: params.get("as_of_date") || "",
    execution_lag: params.get("execution_lag") || "",
    forward_horizon: params.get("forward_horizon") || "",
    rebalance_interval: params.get("rebalance_interval") || "",
    benchmark_asset_id: params.get("benchmark_asset_id") || "",
    cash_annual_return: params.get("cash_annual_return") || "",
    regime_filter: params.get("regime_filter") || "",
    regime_lookback: params.get("regime_lookback") || "",
    max_drawdown_limit: params.get("max_drawdown_limit") || "",
    initial_cash: params.get("initial_cash") || "",
    commission_bps: params.get("commission_bps") || "",
    slippage_bps: params.get("slippage_bps") || "",
    max_asset_weight: params.get("max_asset_weight") || "",
    max_market_weight: params.get("max_market_weight") || "",
    max_gross_exposure: params.get("max_gross_exposure") || "",
    min_cash_weight: params.get("min_cash_weight") || "",
  };
}

function requestMatchesCurrentParams(resultRequest = {}, currentParams = new URLSearchParams(), keys = []) {
  const currentRequest = requestObjectFromParams(currentParams);
  const comparableKeys = keys.filter((key) => (
    normalizeRequestValue(requestValue(resultRequest, key)) !== ""
    || normalizeRequestValue(requestValue(currentRequest, key)) !== ""
  ));
  if (comparableKeys.length === 0) return false;
  return comparableKeys.every((key) => (
    normalizeRequestValue(requestValue(resultRequest, key)) === normalizeRequestValue(requestValue(currentRequest, key))
  ));
}

function requestFreshnessSummary(request = {}) {
  return [
    request.market || "",
    request.factor_name || request.factor || "",
    request.top_n != null && request.top_n !== "" ? `top_n=${request.top_n}` : "",
    request.cost_bps != null && request.cost_bps !== "" ? `cost=${request.cost_bps}bps` : "",
    request.initial_cash != null && request.initial_cash !== "" ? `cash=${request.initial_cash}` : "",
    request.start_date || request.as_of_date || "",
    request.end_date || "",
  ].filter(Boolean).join(" / ") || "--";
}

function applySourcePreset(force) {
  const source = valueOf("data-source-select") || "processed-bars";
  const preset = sourcePresets[source] || sourcePresets.demo_fixture;
  setValue("data-root-input", preset.dataRoot);
  setValue("factor-windows", preset.factorWindows);
  setValue("start-date", preset.startDate);
  setValue("end-date", preset.endDate);
  setValue("signal-as-of", preset.signalDate);
  setValue("paper-start-date", preset.paperStartDate);
  setValue("paper-end-date", preset.paperEndDate);
  setValue("execution-lag", preset.executionLag);
  setValue("forward-horizon", preset.forwardHorizon);
  setValue("rebalance-interval", preset.rebalanceInterval);
  if (force || !valueOf("market-select") || valueOf("market-select") === "ALL") {
    setValue("market-select", preset.market);
  }
  setValue("paper-market-select", valueOf("market-select") || preset.market);
  setFactorValue("factor-select", preset.factor);
  setFactorValue("paper-factor-select", preset.factor);
  byId("data-mode-label").textContent = source;
  byId("mode-pill").textContent = `${zhConsoleText(source)} / 本地`;
  renderRequestPreview();
}

function setFactorValue(id, value) {
  const select = byId(id);
  if (!select) return;
  if ([...select.options].some((option) => option.value === value)) {
    select.value = value;
  }
}

function paramsObject(params) {
  if (!params || typeof params.entries !== "function") return {};
  return Object.fromEntries(params.entries());
}

function endpointWithParams(path, params) {
  const query = params && typeof params.toString === "function" ? params.toString() : "";
  return query ? `${path}?${query}` : path;
}

function safeWorkflowPlainOutcome(spec = {}) {
  const request = spec.request || {};
  const workflowId = spec.workflow_id || "local_workflow";
  const market = request.market || request.paper_market || "CN_ETF";
  const factor = request.factor || request.factor_name || "当前因子";
  if (workflowId === "research_backtest") {
    return `会用 ${market} / ${factor} 跑本地回测，生成总收益、年化、Sharpe、最大回撤和胜率。`;
  }
  if (workflowId === "signal_snapshot") {
    return `会用 ${market} / ${factor} 生成本地建议信号和目标仓位，不会发出真实订单。`;
  }
  if (workflowId === "paper_simulation") {
    return `会用 ${market} / ${factor} 做本地模拟盘回放，生成模拟成交、权益和回撤。`;
  }
  if (workflowId === "verification_runner") {
    return `会运行允许名单里的本地检查：${request.gate_id || "verification"}，只返回检查结果。`;
  }
  if (workflowId === "startup_workflows") {
    return "会刷新研究回测、信号快照、纸面模拟和候选推广面板，仍然全部在本地执行。";
  }
  if (workflowId === "daily_ops") {
    return "会读取本地报告包，刷新日常运营、风险候选、观察样本和数据状态。";
  }
  if (workflowId === "promotion_ops") {
    return "会读取本地推广证据包，刷新候选推广、复核清单和证据刷新状态。";
  }
  return spec.label || "会执行一个本地研究工作流。";
}

function safeWorkflowNextPlace(spec = {}) {
  const workflowId = spec.workflow_id || "local_workflow";
  if (workflowId === "research_backtest") return "完成后看：结果人话判读、结果指标、回测闸门。";
  if (workflowId === "signal_snapshot") return "完成后看：信号快照、目标仓位、运行历史。";
  if (workflowId === "paper_simulation") return "完成后看：模拟盘权益、模拟盘交接、结果证据。";
  if (workflowId === "verification_runner") return "完成后看：验证执行器、操作回执、审计评分。";
  if (workflowId === "startup_workflows") return "完成后看：首页状态灯、结果判读、排行榜和模拟盘交接。";
  if (workflowId === "daily_ops") return "完成后看：日常运营、风险候选、观察样本和数据闸门。";
  if (workflowId === "promotion_ops") return "完成后看：候选推广、复核清单、证据刷新。";
  return "完成后看：控制台操作回执和运行历史。";
}

function safeWorkflowBeginnerSummary(spec = {}) {
  return {
    title: spec.label || spec.workflow_id || "本地工作流",
    outcome: safeWorkflowPlainOutcome(spec),
    risk: "不会连接券商、不会读取真实账户、不会生成真实订单、不会自动实盘交易。",
    next: safeWorkflowNextPlace(spec),
  };
}

function renderSafeWorkflowBeginnerSummary(spec = {}) {
  const summary = safeWorkflowBeginnerSummary(spec);
  const summaryTarget = byId("safe-run-beginner-summary");
  const outcomeTarget = byId("safe-run-outcome");
  const riskTarget = byId("safe-run-risk-boundary");
  const nextTarget = byId("safe-run-next-place");
  if (!summaryTarget || !outcomeTarget || !riskTarget || !nextTarget) return;
  summaryTarget.innerHTML = `
    <strong>${escapeHtml(summary.title)}</strong>
    <span>${escapeHtml("确认后只会在本机执行，完成前可以取消。")}</span>
  `;
  outcomeTarget.innerHTML = `
    <small>${escapeHtml("会发生什么")}</small>
    <strong>${escapeHtml(summary.outcome)}</strong>
  `;
  riskTarget.innerHTML = `
    <small>${escapeHtml("不会发生什么")}</small>
    <strong>${escapeHtml(summary.risk)}</strong>
  `;
  nextTarget.innerHTML = `
    <small>${escapeHtml("跑完看哪里")}</small>
    <strong>${escapeHtml(summary.next)}</strong>
  `;
}

async function confirmSafeWorkflow(spec = {}) {
  const modal = byId("safe-run-modal");
  if (!modal) {
    return window.confirm("确认只在本地运行，不连接券商、不读取账户、不真实下单？");
  }
  if (state.safeRunResolver) {
    state.safeRunResolver(false);
    state.safeRunResolver = null;
  }
  byId("safe-run-title").textContent = spec.title || "确认本地运行";
  renderSafeWorkflowBeginnerSummary(spec);
  byId("safe-run-body").innerHTML = statusRows([
    ["将要执行", spec.label || spec.workflow_id || "本地工作流", "warn"],
    ["运行边界", "只读取本地数据或本地报告，只生成研究、信号、回测、模拟或验证结果。", "ok"],
    ["绝不会做", "不连接券商，不读取真实账户，不生成真实订单，不进行自动实盘交易。", "danger"],
    ["接口/命令", spec.endpoint || spec.command || "--", "muted"],
  ]);
  byId("safe-run-params").textContent = JSON.stringify(
    {
      workflow_id: spec.workflow_id || "local_workflow",
      request: spec.request || {},
      endpoint: spec.endpoint || "",
      safety: "local only; no broker; no account; no real order; no live trading",
    },
    null,
    2,
  );
  modal.hidden = false;
  return new Promise((resolve) => {
    state.safeRunResolver = resolve;
  });
}

function resolveSafeWorkflow(confirmed) {
  const modal = byId("safe-run-modal");
  if (modal) modal.hidden = true;
  const resolver = state.safeRunResolver;
  state.safeRunResolver = null;
  if (resolver) resolver(Boolean(confirmed));
}

async function runStartupWorkflows() {
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "startup_workflows",
    label: "刷新研究、信号、模拟盘和候选推广面板",
    endpoint: "/api/research + /api/signals + /api/paper + /api/promotion/ops",
    request: {
      market: valueOf("market-select") || "CN_ETF",
      factor_name: valueOf("factor-select") || "momentum_2",
      paper_market: valueOf("paper-market-select") || "CN_ETF",
    },
  });
  if (!confirmed) return;
  await withBusy("run-startup-workflows", async () => {
    await refreshResearch();
    await refreshSignals();
    await refreshPaper();
    await refreshPromotionOps();
    appendRunHistory({
      workflow_id: "startup_workflows",
      label: "Run startup workflows",
      status: "completed",
      detail: "research, signals, paper, and promotion refreshed",
    });
    appendExecutionReceipt(researchReceipt(state.research));
    appendExecutionReceipt(signalReceipt(state.signals));
    appendExecutionReceipt(paperReceipt(state.paper));
    showToast("Workflows refreshed");
  });
}

async function refreshResearch() {
  byId("active-market-label").textContent = valueOf("market-select") || "ALL";
  const params = buildResearchParams();
  state.research = await fetchJson(`/api/research?${params.toString()}`);
  renderDashboard();
  renderFactorResearch();
  renderBacktest();
  renderDecision();
  renderControlCenter();
}

async function runResearch() {
  const params = buildResearchParams();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "research_backtest",
    label: "本地回测当前参数",
    endpoint: endpointWithParams("/api/research", params),
    request: paramsObject(params),
  });
  if (!confirmed) return;
  await withBusy("run-research", async () => {
    await refreshResearch();
    appendRunHistory({
      workflow_id: "research_backtest",
      label: "Run research backtest",
      status: "completed",
      detail: `${valueOf("market-select") || "ALL"} / ${valueOf("factor-select") || "momentum_2"}`,
    });
    appendExecutionReceipt(researchReceipt(state.research));
    showToast("研究结果已更新");
  });
}

async function refreshSignals() {
  const params = buildSignalParams();
  state.signals = await fetchJson(`/api/signals?${params.toString()}`);
  renderSignals();
  renderDashboard();
  renderControlCenter();
}

async function runSignals() {
  const params = buildSignalParams();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "signal_snapshot",
    label: "生成本地建议信号",
    endpoint: endpointWithParams("/api/signals", params),
    request: paramsObject(params),
  });
  if (!confirmed) return;
  await withBusy("run-signals", async () => {
    await refreshSignals();
    appendRunHistory({
      workflow_id: "signal_snapshot",
      label: "Generate advisory signal snapshot",
      status: "completed",
      detail: `top_n=${valueOf("signal-top-n") || "2"}`,
    });
    appendExecutionReceipt(signalReceipt(state.signals));
    showToast("信号快照已生成");
  });
}

async function refreshPaper() {
  const params = buildPaperParams();
  state.paper = await fetchJson(`/api/paper?${params.toString()}`);
  renderDashboard();
  renderPaper();
  renderControlCenter();
}

async function runPaper() {
  const params = buildPaperParams();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "paper_simulation",
    label: "本地模拟盘回放",
    endpoint: endpointWithParams("/api/paper", params),
    request: paramsObject(params),
  });
  if (!confirmed) return;
  await withBusy("run-paper", async () => {
    await refreshPaper();
    appendRunHistory({
      workflow_id: "paper_simulation",
      label: "Run local paper simulation",
      status: "completed",
      detail: `${valueOf("paper-market-select") || "ALL"} / top_n=${valueOf("paper-top-n") || "2"}`,
    });
    appendExecutionReceipt(paperReceipt(state.paper));
    showToast("纸面模拟已更新");
  });
}

async function runDailyOps() {
  const params = new URLSearchParams({
    daily_ops_pack: valueOf("daily-ops-pack-path"),
  });
  const riskParams = new URLSearchParams({
    risk_candidate_pack: valueOf("risk-candidate-pack-path"),
  });
  const constrainedParams = new URLSearchParams({
    constrained_search_pack: valueOf("constrained-search-pack-path"),
  });
  const profileParams = new URLSearchParams({
    paper_profile_pack: valueOf("paper-profile-pack-path"),
  });
  const observationParams = new URLSearchParams({
    profile_observation_pack: valueOf("profile-observation-pack-path"),
  });
  const recentRefreshParams = new URLSearchParams({
    recent_data_refresh_pack: valueOf("recent-data-refresh-pack-path"),
  });
  const postRefreshParams = new URLSearchParams({
    post_refresh_replay_pack: valueOf("post-refresh-replay-pack-path"),
  });
  const sufficiencyParams = new URLSearchParams({
    observation_sufficiency_pack: valueOf("observation-sufficiency-pack-path"),
  });
  const expandedParams = new URLSearchParams({
    expanded_observation_replay_pack: valueOf("expanded-observation-replay-pack-path"),
  });
  const iterativeParams = new URLSearchParams({
    iterative_observation_expansion_pack: valueOf("iterative-observation-expansion-pack-path"),
  });
  const activationParams = new URLSearchParams({
    tushare_activation_gate_pack: valueOf("tushare-activation-gate-pack-path"),
  });
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "daily_ops",
    label: "刷新本地日常运营与风险闸门",
    endpoint: "/api/daily/ops + /api/risk/* + /api/data/*",
    request: {
      daily_ops_pack: valueOf("daily-ops-pack-path"),
      risk_candidate_pack: valueOf("risk-candidate-pack-path"),
      paper_profile_pack: valueOf("paper-profile-pack-path"),
    },
  });
  if (!confirmed) return;
  await withBusy("run-daily-ops", async () => {
    state.dailyOps = await fetchJson(`/api/daily/ops?${params.toString()}`);
    state.riskCandidates = await fetchJson(`/api/risk/candidates?${riskParams.toString()}`);
    state.constrainedSearch = await fetchJson(`/api/risk/constrained-search?${constrainedParams.toString()}`);
    state.paperProfiles = await fetchJson(`/api/risk/paper-profiles?${profileParams.toString()}`);
    state.profileObservation = await fetchJson(`/api/risk/profile-observation?${observationParams.toString()}`);
    state.recentDataRefresh = await fetchJson(`/api/data/recent-refresh?${recentRefreshParams.toString()}`);
    state.postRefreshReplay = await fetchJson(`/api/data/post-refresh-replay?${postRefreshParams.toString()}`);
    state.observationSufficiency = await fetchJson(`/api/risk/observation-sufficiency?${sufficiencyParams.toString()}`);
    state.expandedObservationReplay = await fetchJson(`/api/risk/expanded-observation-replay?${expandedParams.toString()}`);
    state.iterativeObservationExpansion = await fetchJson(`/api/risk/iterative-observation-expansion?${iterativeParams.toString()}`);
    state.tushareActivationGate = await fetchJson(`/api/risk/tushare-activation-gate?${activationParams.toString()}`);
    renderDailyOps();
    renderRiskCandidates();
    renderConstrainedSearch();
    renderPaperProfiles();
    renderProfileObservation();
    renderRecentDataRefresh();
    renderPostRefreshReplay();
    renderObservationSufficiency();
    renderExpandedObservationReplay();
    renderIterativeObservationExpansion();
    renderTushareActivationGate();
    renderDashboard();
    appendRunHistory({
      workflow_id: "daily_ops",
      label: "Refresh Daily Ops",
      status: "completed",
      detail: "risk gates and observation packs refreshed",
    });
    showToast("Daily operations refreshed");
  });
}

async function refreshPromotionOps() {
  const params = new URLSearchParams({
    promotion_report: valueOf("promotion-report-path"),
    provider_status: valueOf("promotion-provider-path"),
    quality_report: valueOf("promotion-quality-path"),
  });
  state.promotion = await fetchJson(`/api/promotion/ops?${params.toString()}`);
  state.promotionReview = await fetchJson(`/api/promotion/review?${params.toString()}`);
  state.evidenceRefresh = await fetchJson(`/api/promotion/evidence-refresh?${params.toString()}`);
  renderDashboard();
  renderPromotionOps();
}

async function runPromotionOps() {
  const params = new URLSearchParams({
    promotion_report: valueOf("promotion-report-path"),
    provider_status: valueOf("promotion-provider-path"),
    quality_report: valueOf("promotion-quality-path"),
  });
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "promotion_ops",
    label: "刷新候选推广审计",
    endpoint: endpointWithParams("/api/promotion/ops", params),
    request: paramsObject(params),
  });
  if (!confirmed) return;
  await withBusy("run-promotion", async () => {
    await refreshPromotionOps();
    appendRunHistory({
      workflow_id: "promotion_ops",
      label: "Refresh Promotion Ops",
      status: "completed",
      detail: "promotion review and evidence refresh loaded",
    });
    showToast("Promotion operations refreshed");
  });
}

function fillFactorSelect(factors) {
  const options = factors.map((factor) => `<option value="${escapeHtml(factor)}">${escapeHtml(factor)}</option>`).join("");
  document.querySelectorAll(".factor-select").forEach((select) => {
    const previous = select.value;
    select.innerHTML = options;
    if (previous) select.value = previous;
  });
}

function renderControlCenter() {
  const control = state.controlCenter || {};
  const work = control.work || {};
  const workspaceSync = control.workspace_sync || {};
  const processMonitor = control.process_monitor || {};
  const activeOperationSpec = control.active_operation || {};
  const operationLedger = control.operation_ledger || {};
  const tradeModeControl = control.trade_mode_control || {};
  const backtest = control.backtest || {};
  const backtestProvenance = control.backtest_provenance || {};
  const backtestGate = control.backtest_gate || {};
  const paperReadiness = control.paper_readiness || {};
  const resultEvidence = control.result_evidence || {};
  const ledgerEvidence = control.ledger_evidence || {};
  const method = control.method || {};
  const workflows = control.workflows || [];
  const reportLinks = control.report_links || [];
  const verificationGates = control.verification_gates || [];
  const verificationRunner = control.verification_runner || {};
  const operatorChecklist = control.operator_checklist || {};
  const checklistItems = operatorChecklist.items || [];
  const executionPlan = control.execution_plan || {};
  const executionSteps = executionPlan.steps || [];
  const workflowTrace = control.workflow_trace || {};
  const startupHealth = control.startup_health || {};
  const readinessMatrix = control.readiness_matrix || {};
  const readinessRows = readinessMatrix.rows || [];
  const releaseReadiness = control.release_readiness || {};
  const auditScorecard = control.audit_scorecard || {};
  const auditSummary = auditScorecard.summary || {};
  const auditCategories = auditScorecard.categories || [];
  const auditRepairQueue = auditScorecard.repair_queue || [];
  const auditPackets = control.audit_packets || {};
  const auditPacketRows = auditPackets.rows || [];
  const auditFeedback = control.audit_feedback || {};
  const roundCheckpointReport = control.round_checkpoint_report || {};
  const auditIterationPlan = control.audit_iteration_plan || {};
  const auditScheduler = control.audit_scheduler || {};
  const operatorTimeline = control.operator_timeline || {};
  const timelineEvents = operatorTimeline.events || [];
  const runHistorySpec = control.run_history || {};
  const executionReceiptSpec = control.execution_receipts || {};
  const runQueue = control.run_queue || {};
  const actionCenter = control.action_center || {};
  const workflowPreflight = control.workflow_preflight || {};
  const activeRun = runQueue.active || {};
  const queueSummary = runQueue.summary || {};
  const pendingRuns = runQueue.pending || [];
  const blockedRuns = runQueue.blocked || [];
  const safety = control.safety || {};
  const automation = control.automation || {};
  const metrics = state.research?.metrics || {};
  const benchmark = state.research?.benchmark_metrics || {};
  const paperMetrics = state.paper?.metrics || {};
  const researchRequest = state.research?.request || {};
  const paperRequest = state.paper?.request || {};
  const executionReceipts = loadExecutionReceipts(executionReceiptSpec);
  const statusTag = byId("control-center-status");
  if (statusTag) {
    statusTag.textContent = zhConsoleText(control.status || "loading");
    statusTag.classList.toggle("tag-warn", control.status !== "ready");
  }
  byId("control-work-status").innerHTML = statusRows([
    ["Machine", work.machine || "--", work.machine ? "ok" : "muted"],
    ["Task", work.task || "--", "muted"],
    ["Branch", work.branch || "--", work.branch ? "ok" : "warn"],
    ["Goal", work.goal || "--", "muted"],
  ]);
  byId("control-workspace-sync").innerHTML = renderWorkspaceSync(workspaceSync);
  byId("control-process-monitor").innerHTML = renderProcessMonitor(processMonitor);
  byId("control-active-operation").innerHTML = renderActiveOperation(activeOperationSpec, state.activeOperation);
  byId("control-operation-ledger").innerHTML = renderOperationLedger(operationLedger);
  byId("control-trade-mode-control").innerHTML = renderTradeModeControl(tradeModeControl);
  byId("control-run-queue").innerHTML = statusRows([
    ["Active", activeRun.label || "--", activeRun.workflow_id ? "ok" : "muted"],
    ["Status", activeRun.status || "--", activeRun.status === "ready_to_run" ? "ok" : "warn"],
    ["Pending", `${queueSummary.pending ?? "--"} queued`, (queueSummary.pending ?? 0) > 0 ? "warn" : "muted"],
    ["Blocked", `${queueSummary.blocked ?? "--"} blocked`, (queueSummary.blocked ?? 0) > 0 ? "danger" : "ok"],
    ["Next", pendingRuns[0]?.label || blockedRuns[0]?.label || "--", pendingRuns.length ? "muted" : "warn"],
  ]);
  byId("control-action-center").innerHTML = renderActionCenter(actionCenter);
  byId("control-command-deck-status").innerHTML = renderConsoleCommandDeck(
    activeOperationSpec,
    state.activeOperation,
    executionReceipts,
    state.verificationResult,
    safety,
  );
  byId("control-workflow-preflight").innerHTML = renderWorkflowPreflight(workflowPreflight);
  byId("control-operator-checklist").innerHTML = checklistItems.slice(0, 7).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "ready" ? "ok" : item.status === "blocked" ? "danger" : "warn")}">
      <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
      <span>${escapeHtml(item.status || "")}</span>
      <span>${escapeHtml(item.detail || "")}</span>
    </div>
  `).join("");
  byId("control-execution-plan").innerHTML = executionSteps.slice(0, 7).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "done" || item.status === "active" ? "ok" : item.status === "blocked" ? "danger" : "warn")}">
      <strong>${escapeHtml(item.label || item.step_id || "")}</strong>
      <span>${escapeHtml(item.status || "")} / ${escapeHtml(item.command || "")}</span>
      <span>${escapeHtml(item.detail || "")}</span>
    </div>
  `).join("");
  byId("control-workflow-trace").innerHTML = renderWorkflowTrace(workflowTrace);
  byId("control-startup-health").innerHTML = renderStartupHealth(startupHealth);
  byId("control-readiness-matrix").innerHTML = readinessRows.slice(0, 4).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "ready" ? "ok" : item.status === "blocked" ? "danger" : "warn")}">
      <strong>${escapeHtml(item.label || item.mode_id || "")}</strong>
      <span>${escapeHtml(item.status || "")} / ${escapeHtml(item.scope || "")}</span>
      <span>${escapeHtml(item.guardrail || item.next_action || "")}</span>
    </div>
  `).join("");
  byId("control-release-readiness").innerHTML = renderReleaseReadiness(releaseReadiness);
  byId("control-audit-scorecard").innerHTML = [
    `
    <div class="list-row warn">
      <strong>${escapeHtml(`${auditSummary.independent_audit_score ?? auditSummary.local_self_check_score ?? "--"} / ${auditSummary.max_score ?? "--"} ${auditSummary.score_source === "independent_gui_audit_packet" ? "independent audit" : "local self-check"}`)}</strong>
      <span>${escapeHtml(`${auditSummary.cadence_rounds ?? 5} rounds / ${auditSummary.cadence_hours ?? "--"}h fallback / ${auditSummary.automation_id || "audit automation"}`)}</span>
      <span>${escapeHtml(auditSummary.independent_audit_complete ? `Independent audit complete / ${auditSummary.independent_audit_verdict || "review"}` : "Independent audit still required")}</span>
    </div>
    `,
  ].concat(auditCategories.slice(0, 7).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "good" ? "ok" : item.status === "blocked_live" ? "danger" : "warn")}">
      <strong>${escapeHtml(item.label || item.category_id || "")}</strong>
      <span>${escapeHtml(`${item.score ?? "--"} / ${item.max_score ?? "--"} / ${item.status || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
    </div>
  `)).join("");
  byId("control-audit-packets").innerHTML = renderAuditPackets(auditPacketRows);
  byId("control-audit-feedback").innerHTML = renderAuditFeedback(auditFeedback);
  byId("control-round-checkpoint-report").innerHTML = renderRoundCheckpointReport(roundCheckpointReport);
  byId("control-audit-iteration-plan").innerHTML = renderAuditIterationPlan(auditIterationPlan);
  byId("control-audit-scheduler").innerHTML = renderAuditScheduler(auditScheduler);
  byId("control-operator-timeline").innerHTML = timelineEvents.slice(0, 7).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "done" || item.status === "active" ? "ok" : item.status === "blocked" ? "danger" : "warn")}">
      <strong>${escapeHtml(item.label || item.event_id || "")}</strong>
      <span>${escapeHtml(item.status || "")} / ${escapeHtml(item.command || "")}</span>
      <span>${escapeHtml(item.detail || "")}</span>
    </div>
  `).join("");
  byId("control-audit-repair-queue").innerHTML = auditRepairQueue.slice(0, 4).map((item) => `
    <div class="list-row ${escapeHtml(item.priority === "P0" ? "danger" : item.priority === "P1" ? "warn" : "ok")}">
      <strong>${escapeHtml(`${item.priority || "--"} / ${item.action || ""}`)}</strong>
      <span>${escapeHtml(item.reason || "")}</span>
    </div>
  `).join("");
  byId("control-backtest-status").innerHTML = statusRows([
    ["Source", `${backtest.source || "--"} / ${backtest.data_root || "--"}`, "ok"],
    ["Market", `${backtest.market || "--"} / ${backtest.factor || "--"}`, "ok"],
    ["TopN + cost", `${backtest.top_n ?? "--"} / ${backtest.cost_bps ?? "--"} bps`, "muted"],
    ["Rebalance", `${backtest.rebalance_interval ?? "--"} bars / lag ${backtest.execution_lag ?? "--"}`, "muted"],
    ["Window", `${backtest.start_date || "--"} to ${backtest.end_date || "--"}`, "muted"],
    ["Benchmark", backtest.benchmark_asset_id || "--", "muted"],
  ]);
  byId("control-backtest-provenance").innerHTML = renderBacktestProvenance(backtestProvenance);
  byId("control-backtest-gate").innerHTML = renderBacktestGate(
    backtestGate,
    metrics,
    benchmark,
    paperMetrics,
    executionReceipts,
    researchRequest,
    paperRequest,
    state.controlCenter?.safety || safety,
  );
  byId("control-paper-readiness").innerHTML = renderPaperReadiness(
    paperReadiness,
    backtestGate,
    metrics,
    benchmark,
    paperMetrics,
    executionReceipts,
    researchRequest,
    paperRequest,
    state.controlCenter?.safety || safety,
  );
  byId("control-method-steps").innerHTML = (method.steps || []).map((item) => `
    <div class="method-step">
      <span>${escapeHtml(item.step ?? "")}</span>
      <strong>${escapeHtml(item.name || "")}</strong>
      <em>${escapeHtml(item.detail || "")}</em>
    </div>
  `).join("");
  byId("control-result-slots").innerHTML = [
    metric("Total return", formatPercent(metrics.total_return), "research"),
    metric("Annualized", formatPercent(metrics.annualized_return), "research"),
    metric("Sharpe", formatDecimal(metrics.sharpe), "research"),
    metric("Max drawdown", formatPercent(metrics.max_drawdown), "research"),
    metric("Win rate", formatPercent(metrics.win_rate), "research"),
    metric("Trades", formatNumber(metrics.trade_count), "research"),
    metric("Relative", formatPercent(benchmark.relative_return), "benchmark"),
    metric("Paper equity", formatNumber(paperMetrics.ending_equity), "paper"),
  ].join("");
  renderBeginnerResultInterpreter(
    backtestGate,
    paperReadiness,
    metrics,
    benchmark,
    paperMetrics,
    executionReceipts,
    researchRequest,
    paperRequest,
    state.controlCenter?.safety || safety,
  );
  renderResultFreshness();
  renderParameterConsistency(control.parameter_authority || {});
  byId("control-ledger-evidence").innerHTML = renderLedgerEvidence(ledgerEvidence);
  byId("control-result-evidence").innerHTML = renderResultEvidence(resultEvidence);
  byId("control-workflow-commands").innerHTML = workflows.slice(0, 5).map((item) => `
    <div class="list-row">
      <strong>${escapeHtml(item.label || item.workflow_id || "")}</strong>
      <span>${escapeHtml(item.command || "")}</span>
      <span>${escapeHtml(item.safety || item.mode || "local")}</span>
    </div>
  `).join("");
  byId("control-report-links").innerHTML = reportLinks.slice(0, 8).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "present" || item.status === "available" ? "ok" : "warn")}">
      <strong>${escapeHtml(item.label || item.kind || "")}</strong>
      <span>${escapeHtml(item.kind || "")} / ${escapeHtml(item.path || "")}</span>
    </div>
  `).join("");
  byId("control-verification-gates").innerHTML = verificationGates.slice(0, 7).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "required_before_push" ? "warn" : "ok")}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(item.command || "")}</span>
      <span>${escapeHtml(item.evidence || item.status || "")}</span>
    </div>
  `).join("");
  byId("control-verification-runner").innerHTML = renderVerificationRunner(verificationRunner, state.verificationResult);
  byId("control-safety-boundary").innerHTML = statusRows([
    ["Paper", safety.paper_trading_allowed ? "allowed by gates" : "blocked until gates pass", safety.paper_trading_allowed ? "ok" : "warn"],
    ["Live", safety.live_trading_allowed ? "allowed" : "disabled", safety.live_trading_allowed ? "ok" : "danger"],
    ["Broker", safety.broker_connection_allowed ? "enabled" : "no connection", safety.broker_connection_allowed ? "ok" : "danger"],
    ["Orders", safety.order_placement_allowed ? "enabled" : "no order placement", safety.order_placement_allowed ? "ok" : "danger"],
  ]);
  byId("control-audit-cadence").innerHTML = statusRows([
    ["Cadence", automation.cadence || "--", "ok"],
    ["Audit", `${automation.name || "--"} / ${automation.status || "--"}`, automation.status === "active" ? "ok" : "warn"],
    ["Output", automation.expected_output || "--", "muted"],
    ["Boundary", safety.notice || "Research only", "danger"],
  ]);
  renderRunHistory(runHistorySpec);
  renderExecutionReceipts(executionReceiptSpec);
  renderBeginnerProgress();
}

function renderDashboard() {
  const dashboard = state.snapshot?.dashboard || {};
  const metrics = state.research?.metrics || {};
  const benchmark = state.research?.benchmark_metrics || {};
  const decision = state.research?.decision || {};
  const paperMetrics = state.paper?.metrics || {};
  const promotionSummary = state.promotion?.summary || {};
  const project = state.projectStatus || {};
  const daily = state.dailyOps || {};
  const dailyDecision = daily.decision || {};
  const dailyPaperProfile = daily.paper_profile || {};
  const riskCandidates = state.riskCandidates || {};
  const constrained = state.constrainedSearch || {};
  const profiles = state.paperProfiles || {};
  const observation = state.profileObservation || {};
  const observationDecision = observation.decision || {};
  const recentRefresh = state.recentDataRefresh || {};
  const refreshDecision = recentRefresh.decision || {};
  const refreshCoverage = recentRefresh.coverage || {};
  const postReplay = state.postRefreshReplay || {};
  const postReplayDecision = postReplay.decision || {};
  const sufficiency = state.observationSufficiency || {};
  const sufficiencyDecision = sufficiency.decision || {};
  const sufficiencyFills = sufficiency.fills || {};
  const expandedReplay = state.expandedObservationReplay || {};
  const expandedDecision = expandedReplay.decision || {};
  const expandedFinal = expandedReplay.final_observation_sufficiency || {};
  const expandedFills = expandedFinal.fills || {};
  const iterativeExpansion = state.iterativeObservationExpansion || {};
  const iterativeDecision = iterativeExpansion.decision || {};
  const iterativeFinal = iterativeExpansion.final_observation_sufficiency || {};
  const iterativeFills = iterativeFinal.fills || {};
  const activationGate = state.tushareActivationGate || {};
  const activationDecision = activationGate.decision || {};
  const activationFinal = activationGate.final_observation_sufficiency || {};
  const activationFills = activationFinal.fills || {};
  const candidate = project.selected_candidate || {};
  const dataGaps = project.data_gaps || {};
  const provider = project.provider_remediation || {};
  const factorLedger = state.factorLeaderboard || {};
  const factorSummary = factorLedger.summary || {};
  const activeFactorBoard = getActiveLeaderboard();
  renderOrdinaryHome();
  renderBeginnerVerdict();
  renderBeginnerGuide();
  renderBeginnerProgress();
  renderFactorBeginnerExplainer(activeFactorBoard, activeFactorBoard.rows || []);
  byId("dashboard-equity-source").textContent = state.research?.data_source || valueOf("data-source-select") || state.snapshot?.data_mode || "local";
  byId("dashboard-metrics").innerHTML = [
    metric("项目状态", project.overall_status || "--", `阻塞 ${project.blocker_count ?? "--"}`),
    metric("因子总数", factorSummary.unique_factor_names ?? "--", "配置/报告/下拉框并集"),
    metric("候选记录", factorSummary.candidate_rows ?? "--", "历史参数组合"),
    metric("报告唯一因子", factorSummary.report_factor_names ?? "--", "本地报告"),
    metric("Top20", (factorLedger.top20 || []).length || "--", "排行榜"),
    metric("Daily Ops", dailyDecision.status || "--", dailyDecision.paper_trading_allowed ? "paper allowed" : "blocked"),
    metric("Daily Profile", dailyPaperProfile.profile_id || "--", dailyPaperProfile.risk_tier || "no overlay"),
    metric("风险候选", riskCandidates.summary?.risk_eligible_candidates ?? "--", riskCandidates.selection_status || "selector"),
    metric("Frontier", constrained.summary?.frontier_candidates ?? "--", constrained.selection_status || "constrained search"),
    metric("Profiles", profiles.summary?.eligible_profiles ?? "--", profiles.selection_status || "paper optimizer"),
    metric("Observation", observationDecision.observation_status || "--", `stops ${observation.summary?.stop_count ?? "--"}`),
    metric("Recent Data", recentRefresh.status || "--", refreshDecision.signal_data_stale_cleared ? "fresh" : "blocked"),
    metric("Post Replay", postReplay.status || "--", postReplayDecision.post_refresh_replay_allowed ? "paper cleared" : "blocked"),
    metric("Sample Gate", sufficiency.status || "--", `${sufficiencyFills.observed_fills ?? "--"} / ${sufficiencyFills.required_fills ?? "--"} fills`),
    metric("Expanded Gate", expandedReplay.status || "--", `${expandedFills.observed_fills ?? "--"} / ${expandedFills.required_fills ?? "--"} fills`),
    metric("Iterative Gate", iterativeExpansion.status || "--", `${iterativeFills.observed_fills ?? "--"} / ${iterativeFills.required_fills ?? "--"} fills`),
    metric("Activation Gate", activationGate.status || "--", activationDecision.paper_continuation_allowed ? "paper ready" : "blocked"),
    metric("主候选", candidate.promotion_status || promotionSummary.paper_ready || "--", candidate.case_id || "promotion ops"),
    metric("数据缺口", dataGaps.gap_rows ?? "--", `${dataGaps.target_raw_rows_found ?? 0} raw rows found`),
    metric("Provider 阻塞", provider.blocking_remediation_items ?? "--", "remediation"),
    metric("研究收益", formatPercent(metrics.total_return), "current run"),
    metric("相对基准", formatPercent(benchmark.relative_return), "Phase 2.6"),
    metric("准入状态", decision.decision_status || "--", "research gate"),
    metric("纸面权益", formatNumber(paperMetrics.ending_equity), "simulation"),
  ].join("");
  byId("dashboard-equity").innerHTML = multiLineChart([
    { label: "策略", color: chartTheme.strategy, rows: state.research?.equity_curve || [], yKey: "equity" },
    { label: "基准", color: chartTheme.benchmark, rows: state.research?.benchmark_curve || [], yKey: "benchmark_equity" },
  ]);
  byId("dashboard-status").innerHTML = statusRows([
    ["Daily Ops", `${dailyDecision.status || "--"} / tickets ${daily.ticket_count ?? "--"}`, dailyDecision.status === "paper_ready" ? "ok" : "warn"],
    ["Daily profile", `${dailyPaperProfile.profile_id || "none"} / ${dailyPaperProfile.risk_tier || "--"}`, dailyPaperProfile.profile_id ? "ok" : "muted"],
    ["Risk candidates", `${riskCandidates.selection_status || "--"} / eligible ${riskCandidates.summary?.tier_eligible_candidates ?? riskCandidates.summary?.risk_eligible_candidates ?? "--"}`, ["risk_candidate_selected", "risk_tier_candidate_selected"].includes(riskCandidates.selection_status) ? "ok" : "warn"],
    ["Constrained frontier", `${constrained.summary?.frontier_candidates ?? "--"} near miss`, constrained.summary?.frontier_candidates > 0 ? "warn" : "muted"],
    ["Paper profiles", `${profiles.selection_status || "--"} / eligible ${profiles.summary?.eligible_profiles ?? "--"}`, ["paper_profile_selected", "risk_tier_profile_selected"].includes(profiles.selection_status) ? "ok" : "warn"],
    ["Profile observation", `${observationDecision.observation_status || "--"} / stops ${observation.summary?.stop_count ?? "--"}`, observationDecision.paper_observation_allowed ? "ok" : "warn"],
    ["Recent data", `${recentRefresh.status || "--"} / ${refreshCoverage.coverage_status || "--"}`, refreshDecision.signal_data_stale_cleared ? "ok" : "warn"],
    ["Post-refresh replay", `${postReplay.status || "--"} / blockers ${(postReplayDecision.blockers || []).length}`, postReplayDecision.post_refresh_replay_allowed ? "ok" : "warn"],
    ["Sample sufficiency", `${sufficiency.status || "--"} / deficit ${sufficiencyFills.fill_deficit ?? "--"}`, sufficiencyDecision.observation_sufficiency_cleared ? "ok" : "warn"],
    ["Expanded replay", `${expandedReplay.status || "--"} / deficit ${expandedFills.fill_deficit ?? "--"}`, expandedDecision.expanded_observation_cleared ? "ok" : "warn"],
    ["Iterative expansion", `${iterativeExpansion.status || "--"} / rounds ${iterativeExpansion.round_count ?? "--"}`, iterativeDecision.iterative_observation_cleared ? "ok" : "warn"],
    ["Tushare activation", `${activationGate.status || "--"} / fills ${activationFills.observed_fills ?? "--"}`, activationDecision.paper_continuation_allowed ? "ok" : "warn"],
    ["Promotion blockers", (state.promotion?.live_review_blockers || []).join(" / ") || "none", state.promotion?.live_review_allowed ? "ok" : "warn"],
    ["Tushare", readyText(state.snapshot?.readiness?.tushare), state.snapshot?.readiness?.tushare?.ready ? "ok" : "warn"],
    ["Parquet", readyText(state.snapshot?.readiness?.parquet), state.snapshot?.readiness?.parquet?.ready ? "ok" : "warn"],
    ["纸面权益", formatNumber(paperMetrics.ending_equity), state.paper ? "ok" : "muted"],
    ["保护事件", formatNumber(paperMetrics.guard_event_count), paperMetrics.guard_event_count > 0 ? "warn" : "muted"],
    ["安全边界", dashboard.risk_notice || "Research only", "danger"],
  ]);
  renderControlCenter();
  renderProjectStatus();
  renderFactorLeaderboard();
}

function renderFactorLeaderboard() {
  const ledger = state.factorLeaderboard || {};
  const summary = ledger.summary || {};
  const rows = ledger.top20 || [];
  const tag = byId("factor-leaderboard-tag");
  if (tag) {
    tag.textContent = rows.length ? `${rows.length} 条` : "加载中";
    tag.classList.toggle("tag-warn", rows.length === 0);
  }
  byId("factor-inventory-metrics").innerHTML = [
    metric("运行下拉框", summary.runtime_dropdown_factor_names ?? "--", "可直接手动回测"),
    metric("配置因子名", summary.config_factor_names ?? "--", "configs JSON"),
    metric("报告因子名", summary.report_factor_names ?? "--", "data/reports"),
    metric("候选行数", summary.candidate_rows ?? "--", "case/参数组合"),
    metric("去重候选", summary.deduped_candidate_rows ?? "--", "排行榜池"),
    metric("扫描文件", summary.report_files_scanned ?? "--", `${summary.report_files_with_candidates ?? "--"} 命中`),
  ].join("");
  byId("factor-inventory-note").innerHTML = statusRows([
    ["展示口径", summary.note || "下拉框不是历史挖因子总账；排行榜来自配置和本地报告聚合。", "ok"],
    ["排序依据", summary.ranking_basis || "--", "muted"],
    ["跳过文件", `${summary.report_files_skipped ?? 0}`, summary.report_files_skipped > 0 ? "warn" : "ok"],
  ]);
  renderFactorBeginnerExplainer(activeBoard, rows);
  byId("factor-leaderboard-table").innerHTML = renderFactorLeaderboardTable(rows);
}

function factorBeginnerTone(row = {}) {
  if (state.leaderboardTab !== "primary_cn_etf" || row.market !== "CN_ETF") return "warn";
  const quality = String(row.ranking_quality || "").toLowerCase();
  const label = String(row.promotion_label || "");
  if (quality.includes("rejected") || label.includes("不可")) return "danger";
  if (label.includes("模拟盘") || label.includes("继续研究")) return "ok";
  return "warn";
}

function factorBeginnerMetric(label, value, explanation, tone = "muted") {
  return `
    <div class="factor-beginner-metric ${escapeHtml(tone)}">
      <small>${escapeHtml(label)}</small>
      <strong>${escapeHtml(value)}</strong>
      <span>${escapeHtml(explanation)}</span>
    </div>
  `;
}

function metricTone(value, good, warn = null, direction = "higher") {
  const number = Number(value);
  if (!Number.isFinite(number)) return "muted";
  if (direction === "lower") {
    if (number <= good) return "ok";
    if (warn == null || number <= warn) return "warn";
    return "danger";
  }
  if (number >= good) return "ok";
  if (warn == null || number >= warn) return "warn";
  return "danger";
}

function renderFactorBeginnerExplainer(activeBoard = {}, rows = []) {
  const target = byId("factor-beginner-explainer");
  if (!target) return;
  if (!rows.length) {
    target.innerHTML = `
      <div class="factor-beginner-card warn">
        <div class="factor-beginner-copy">
          <p class="section-kicker">新手因子解读</p>
          <h3>当前榜单还没有候选</h3>
          <p>先确认数据、配置和主线市场，避免把空榜误认为已经没有研究方向。</p>
        </div>
        <div class="factor-beginner-actions">
          <button class="secondary-button" type="button" data-beginner-target="factor-inventory-note">看榜单来源</button>
        </div>
      </div>
    `;
    return;
  }
  const row = rows[0] || {};
  const tone = factorBeginnerTone(row);
  const reasons = (row.ranking_reasons || []).join(" / ") || row.ranking_quality || "暂无额外风险说明";
  const conclusion = row.plain_conclusion || row.promotion_label || activeBoard.description || "先看指标，再看审计。";
  const marketHint = row.market === "CN_ETF"
    ? "这是 ETF 主线候选，仍需长周期、OOS、成本和风控复核。"
    : "这不是 ETF 主线榜，只能辅助研究，不能直接变成 ETF 轮动信号。";
  const maxDrawdownTone = metricTone(row.max_drawdown, -0.3, -0.45, "higher");
  target.innerHTML = `
    <div class="factor-beginner-card ${escapeHtml(tone)}">
      <div class="factor-beginner-copy">
        <p class="section-kicker">新手因子解读</p>
        <h3>${escapeHtml(row.factor_name || "--")}</h3>
        <p>${escapeHtml(conclusion)}</p>
        <div class="factor-beginner-tags">
          <span>${escapeHtml(activeBoard.label || "当前榜单")}</span>
          <span>${escapeHtml(row.case_id || "--")}</span>
          <span>${escapeHtml(row.promotion_label || "待审计")}</span>
        </div>
      </div>
      <div class="factor-beginner-metrics">
        ${factorBeginnerMetric("总收益", formatPercent(row.total_return), "样本期累计收益", metricTone(row.total_return, 0.3, 0.05))}
        ${factorBeginnerMetric("年化", formatPercent(row.annualized_return), "折算到一年后的速度", metricTone(row.annualized_return, 0.12, 0.03))}
        ${factorBeginnerMetric("Sharpe", formatDecimal(row.sharpe), "收益和波动的平衡", metricTone(row.sharpe, 1.0, 0.4))}
        ${factorBeginnerMetric("最大回撤", formatPercent(row.max_drawdown), "最难熬的亏损幅度", maxDrawdownTone)}
        ${factorBeginnerMetric("胜率", formatPercent(row.win_rate), "盈利周期占比", metricTone(row.win_rate, 0.55, 0.48))}
      </div>
      <div class="factor-beginner-risk status-list compact-status">
        ${statusRows([
          ["能不能直接用", marketHint, row.market === "CN_ETF" ? "warn" : "danger"],
          ["为什么排这里", `${row.score_metric || "--"}=${formatDecimal(row.primary_score)} / ${row.ranking_quality || "--"}`, tone],
          ["需要注意", reasons, tone === "ok" ? "warn" : tone],
        ])}
      </div>
      <div class="factor-beginner-actions">
        <button class="secondary-button" type="button" data-factor-beginner-jump="factor-leaderboard-table">看完整排行榜</button>
        <button class="primary-button" type="button" data-beginner-action="research_backtest">本地回测当前参数</button>
      </div>
    </div>
  `;
}

function renderFactorLeaderboardTable(rows) {
  const head = `
    <tr>
      <th>排名</th>
      <th>因子 / case</th>
      <th>市场</th>
      <th>总收益</th>
      <th>年化</th>
      <th>Sharpe</th>
      <th>最大回撤</th>
      <th>胜率</th>
      <th>RankIC</th>
      <th>交易数</th>
      <th>参数</th>
      <th>质量</th>
      <th>排序依据</th>
      <th>来源</th>
      <th>全部数据</th>
    </tr>
  `;
  const body = rows.map((row) => {
    const params = row.params && Object.keys(row.params).length ? JSON.stringify(row.params) : "--";
    const allData = row.all_data && Object.keys(row.all_data).length ? JSON.stringify(row.all_data, null, 2) : "{}";
    return `
      <tr>
        <td>${formatNumber(row.rank)}</td>
        <td><strong>${escapeHtml(row.factor_name || "--")}</strong><br><span class="muted">${escapeHtml(row.case_id || "--")}</span></td>
        <td>${escapeHtml(row.market || "--")}</td>
        <td>${formatPercent(row.total_return)}</td>
        <td>${formatPercent(row.annualized_return)}</td>
        <td>${formatDecimal(row.sharpe)}</td>
        <td>${formatPercent(row.max_drawdown)}</td>
        <td>${formatPercent(row.win_rate)}</td>
        <td>${formatDecimal(row.rank_ic)}</td>
        <td>${formatNumber(row.trade_count)}</td>
        <td><code>${escapeRawHtml(params)}</code></td>
        <td>${escapeHtml(row.ranking_quality || "--")}<br><span class="muted">${escapeHtml((row.ranking_reasons || []).join(" / ") || "ok")}</span></td>
        <td>${escapeHtml(`${row.score_metric || "--"}=${formatDecimal(row.primary_score)}`)}</td>
        <td><span class="muted">${escapeHtml(row.source_file || row.source_path || "--")}</span></td>
        <td><details><summary>展开</summary><pre class="json-cell">${escapeRawHtml(allData)}</pre></details></td>
      </tr>
    `;
  }).join("");
  return `${head}${body}`;
}

function getActiveLeaderboard() {
  const ledger = state.factorLeaderboard || {};
  const boards = ledger.leaderboards || {};
  return boards[state.leaderboardTab] || boards.primary_cn_etf || {
    label: "CN_ETF 主线榜",
    description: "等待因子排行榜加载。",
    rows: ledger.top20 || [],
    empty_message: "排行榜加载中。",
  };
}

function setLeaderboardTab(tab) {
  state.leaderboardTab = tab || "primary_cn_etf";
  renderFactorLeaderboard();
  const activeBoard = getActiveLeaderboard();
  renderFactorBeginnerExplainer(activeBoard, activeBoard.rows || []);
  renderOrdinaryHome();
  renderBeginnerVerdict();
  renderBeginnerProgress();
}

function renderFactorGlossary() {
  const container = byId("factor-glossary-list");
  if (!container) return;
  container.innerHTML = GLOSSARY_TERMS.map(([term, explanation]) => `
    <div class="glossary-item">
      <strong>${escapeHtml(term)}</strong>
      <span>${escapeHtml(explanation)}</span>
    </div>
  `).join("");
}

function beginnerStepState(stepId) {
  const ledger = state.factorLeaderboard || {};
  const primaryRows = ledger.leaderboards?.primary_cn_etf?.rows || [];
  const project = state.projectStatus || {};
  if (stepId === "safety") {
    return state.snapshot ? { label: "已确认", tone: "ok" } : { label: "加载中", tone: "warn" };
  }
  if (stepId === "leaderboard") {
    return primaryRows.length ? { label: `${primaryRows.length} 条可看`, tone: "ok" } : { label: "等待主线榜", tone: "warn" };
  }
  if (stepId === "research") {
    return state.research ? { label: "已有回测", tone: "ok" } : { label: "建议执行", tone: "warn" };
  }
  if (stepId === "result") {
    if (project.blocker_count > 0) return { label: "有阻断项", tone: "danger" };
    return state.research ? { label: "可复核", tone: "ok" } : { label: "先跑回测", tone: "warn" };
  }
  if (stepId === "paper") {
    return state.paper ? { label: "已有模拟", tone: "ok" } : { label: "回测后再做", tone: state.research ? "warn" : "muted" };
  }
  return { label: "--", tone: "muted" };
}

function nextBeginnerStep() {
  const ledger = state.factorLeaderboard || {};
  const primaryRows = ledger.leaderboards?.primary_cn_etf?.rows || [];
  if (!state.snapshot) return BEGINNER_STEPS[0];
  if (!primaryRows.length) return BEGINNER_STEPS[1];
  if (!state.research) return BEGINNER_STEPS[2];
  if (!state.paper) return BEGINNER_STEPS[4];
  return BEGINNER_STEPS[3];
}

function beginnerVerdict() {
  const ledger = state.factorLeaderboard || {};
  const primaryRows = ledger.leaderboards?.primary_cn_etf?.rows || [];
  const project = state.projectStatus || {};
  const blockerCount = Number(project.blocker_count || 0);
  const topPrimary = primaryRows[0] || null;
  if (!state.snapshot) {
    return {
      tone: "warn",
      light: "黄灯",
      title: "正在加载本地研究状态",
      summary: "先等首页、控制台和排行榜加载完成，软件会自动给出下一步。",
      reasonRows: [
        ["当前能做", "查看安全边界和新手流程。", "warn"],
        ["不能做", "不要根据加载中的信息判断因子是否可用。", "danger"],
        ["下一步", "确认安全边界。", "ok"],
      ],
      next: BEGINNER_STEPS[0],
    };
  }
  if (blockerCount > 0) {
    return {
      tone: "danger",
      light: "红灯",
      title: "先处理阻断项",
      summary: "项目当前还有阻断项，不能把候选直接推进到模拟盘观察。",
      reasonRows: [
        ["当前能做", "查看控制台里的阻断项、审计反馈和安全边界。", "warn"],
        ["不能做", "不能因为某个收益指标好看就跳过审计。", "danger"],
        ["下一步", `先清理 ${blockerCount} 个阻断项。`, "danger"],
      ],
      next: { ...BEGINNER_STEPS[0], button: "看安全边界" },
    };
  }
  if (!primaryRows.length) {
    return {
      tone: "warn",
      light: "黄灯",
      title: "还没有可看的 CN_ETF 主线候选",
      summary: "先不要看 CN 个股辅助榜或全部历史榜，把注意力放回 ETF 主线。",
      reasonRows: [
        ["当前能做", "查看 CN_ETF 主线榜是否为空，以及排行榜来源说明。", "warn"],
        ["不能做", "不能把 CN 个股资金流选股结果直接当成 ETF 轮动信号。", "danger"],
        ["下一步", "先定位到 CN_ETF 主线榜。", "ok"],
      ],
      next: BEGINNER_STEPS[1],
    };
  }
  if (!state.research) {
    return {
      tone: "warn",
      light: "黄灯",
      title: "可以先跑一次本地回测",
      summary: "已有 CN_ETF 主线候选，但还没有当前参数的本地回测结果。",
      reasonRows: [
        ["当前能做", `先看排第一的候选：${topPrimary?.factor_name || "--"}。`, "ok"],
        ["不能做", "不能只看排行榜，不看收益、回撤、胜率和夏普。", "danger"],
        ["下一步", "运行本地回测当前参数。", "ok"],
      ],
      next: BEGINNER_STEPS[2],
    };
  }
  if (!state.paper) {
    return {
      tone: "warn",
      light: "黄灯",
      title: "已有回测，先复核再做本地模拟盘",
      summary: "现在需要看回测闸门和证据来源，再决定是否做纸面模拟回放。",
      reasonRows: [
        ["当前能做", "检查收益、回撤、胜率、Sharpe、成本和样本来源。", "ok"],
        ["不能做", "不能把短样本或单次高收益直接当成可推广盈利因子。", "danger"],
        ["下一步", "查看回测闸门；确认后再本地模拟盘回放。", "warn"],
      ],
      next: BEGINNER_STEPS[3],
    };
  }
  return {
    tone: "ok",
    light: "绿灯",
    title: "已完成一轮研究到本地模拟盘回放",
    summary: "可以查看结果证据、回测闸门和模拟盘交接，但仍然不是实盘信号。",
    reasonRows: [
      ["当前能做", "复核结果证据、模拟盘权益和审计包。", "ok"],
      ["不能做", "仍然不能连接券商、读取账户或真实下单。", "danger"],
      ["下一步", "回看回测闸门和结果证据，决定下一轮优化方向。", "ok"],
    ],
    next: BEGINNER_STEPS[3],
  };
}

function renderBeginnerVerdict() {
  const board = byId("beginner-verdict-board");
  const light = byId("beginner-safety-light");
  const title = byId("beginner-verdict-title");
  const summary = byId("beginner-verdict-summary");
  const reason = byId("beginner-verdict-reason");
  const button = byId("beginner-next-button");
  if (!board || !light || !title || !summary || !reason || !button) return;
  const verdict = beginnerVerdict();
  ["ok", "warn", "danger", "muted"].forEach((tone) => {
    board.classList.remove(tone);
    light.classList.remove(tone);
  });
  board.classList.add(verdict.tone);
  light.classList.add(verdict.tone);
  light.textContent = verdict.light;
  title.textContent = verdict.title;
  summary.textContent = verdict.summary;
  reason.innerHTML = statusRows(verdict.reasonRows);
  const next = verdict.next || nextBeginnerStep();
  button.textContent = next.button || "查看下一步";
  button.dataset.beginnerAction = next.action || "";
  button.dataset.beginnerTarget = next.target || "";
  button.dataset.leaderboardTab = next.leaderboardTab || "";
}

function beginnerWorkflowLabel(workflowId = "") {
  const labels = {
    research_backtest: "本地回测",
    signal_snapshot: "信号快照",
    paper_simulation: "模拟盘回放",
    verification_runner: "本地验证",
    startup_workflows: "启动工作流",
    daily_ops: "日常运营刷新",
    promotion_ops: "候选推广刷新",
  };
  return labels[workflowId] || workflowId || "本地工作流";
}

function beginnerWorkflowTarget(workflowId = "", status = "") {
  if (status === "failed") return "control-active-operation";
  if (workflowId === "research_backtest" && !state.research) return "control-execution-receipts";
  const targets = {
    research_backtest: "beginner-result-interpreter",
    signal_snapshot: "control-execution-receipts",
    paper_simulation: "control-paper-readiness",
    verification_runner: "control-verification-runner",
    startup_workflows: "control-execution-receipts",
    daily_ops: "daily-ops-status",
    promotion_ops: "promotion-review-status",
  };
  return targets[workflowId] || "control-operation-ledger";
}

function beginnerLatestReceipt() {
  if (Array.isArray(state.executionReceipts) && state.executionReceipts.length) return state.executionReceipts[0];
  return loadExecutionReceipts(state.controlCenter?.execution_receipts || {})[0] || null;
}

function beginnerLatestRunHistory() {
  if (Array.isArray(state.runHistory) && state.runHistory.length) return state.runHistory[0];
  return loadRunHistory(state.controlCenter?.run_history || {})[0] || null;
}

function beginnerHasReceipt(workflowId = "") {
  const rows = Array.isArray(state.executionReceipts) && state.executionReceipts.length
    ? state.executionReceipts
    : loadExecutionReceipts(state.controlCenter?.execution_receipts || {});
  return rows.some((receipt) => receipt?.workflow_id === workflowId);
}

function beginnerProgressMetricText(receipt = {}) {
  const metrics = receipt.metrics || {};
  const parts = [
    metrics.total_return != null ? `总收益 ${formatPercent(metrics.total_return)}` : "",
    metrics.annualized_return != null ? `年化 ${formatPercent(metrics.annualized_return)}` : "",
    metrics.sharpe != null ? `Sharpe ${formatDecimal(metrics.sharpe)}` : "",
    metrics.max_drawdown != null ? `最大回撤 ${formatPercent(metrics.max_drawdown)}` : "",
    metrics.win_rate != null ? `胜率 ${formatPercent(metrics.win_rate)}` : "",
    metrics.ending_equity != null ? `权益 ${formatNumber(metrics.ending_equity)}` : "",
    metrics.target_count != null ? `目标 ${formatNumber(metrics.target_count)} 个` : "",
  ].filter(Boolean);
  return parts.slice(0, 4).join(" / ");
}

function beginnerProgressState() {
  const active = state.activeOperation || null;
  const latestReceipt = beginnerLatestReceipt();
  const latestHistory = beginnerLatestRunHistory();
  if (active?.status === "running") {
    return {
      tone: "warn",
      tag: "运行中",
      status: "running",
      workflowId: active.workflow_id || "",
      title: `正在运行：${beginnerWorkflowLabel(active.workflow_id)}`,
      summary: active.detail || "本地接口正在计算，请等它返回。这里不会连接券商、账户或真实订单。",
      detail: active.safety || "仅研究到纸面模拟。",
      target: "control-active-operation",
      targetLabel: "看当前操作",
      actionText: "先不要连续点多个运行按钮，等当前任务结束后再看结果。",
    };
  }
  const finalOperation = active && ["completed", "failed"].includes(active.status) ? active : null;
  const latest = finalOperation || latestReceipt || latestHistory;
  if (!latest) {
    return {
      tone: "warn",
      tag: "未开始",
      status: "idle",
      workflowId: "research_backtest",
      title: "还没有开始本轮本地运行",
      summary: "先用当前参数跑一次本地回测，软件会记录运行历史、浏览器回执和结果解释。",
      detail: "所有运行都停留在本地研究/纸面模拟边界内。",
      target: "beginner-parameter-explainer",
      targetLabel: "先看当前参数",
      action: "research_backtest",
      actionLabel: "本地回测当前参数",
      actionText: "第一步建议先跑回测，不要直接跳到模拟盘。",
    };
  }
  const workflowId = latest.workflow_id || "workflow";
  const failed = latest.status === "failed";
  const metricText = beginnerProgressMetricText(latestReceipt || {});
  const hasCurrentResearch = Boolean(state.research);
  return {
    tone: failed ? "danger" : "ok",
    tag: failed ? "失败" : "已完成",
    status: failed ? "failed" : "completed",
    workflowId,
    title: `${failed ? "刚才失败" : "最近完成"}：${beginnerWorkflowLabel(workflowId)}`,
    summary: metricText || latest.detail || latest.decision || "本地运行已经留下记录，可以继续看证据和结果。",
    detail: latest.safety || "仍然只是研究/纸面模拟，不是实盘信号。",
    target: beginnerWorkflowTarget(workflowId, latest.status),
    targetLabel: failed ? "看失败原因" : (workflowId === "research_backtest" && !hasCurrentResearch ? "看浏览器回执" : "看结果证据"),
    action: workflowId === "research_backtest" && !failed && hasCurrentResearch ? "paper_simulation" : "",
    actionLabel: workflowId === "research_backtest" && !failed && hasCurrentResearch ? "本地模拟盘回放" : "",
    actionText: failed
      ? "先修复失败原因，再重新运行。"
      : workflowId === "research_backtest" && !hasCurrentResearch
        ? "先核对这条回执是否对应当前参数，不确定就重新跑当前参数。"
        : "先看结果是否可信，再决定是否推进下一步。",
  };
}

function beginnerProgressStepRows(progress = beginnerProgressState()) {
  const hasResearchResult = Boolean(state.research || beginnerHasReceipt("research_backtest"));
  const hasPaperResult = Boolean(state.paper || beginnerHasReceipt("paper_simulation"));
  return [
    ["1. 参数", valueOf("market-select") ? `${valueOf("market-select")} / ${valueOf("factor-select") || "--"} / TopN ${valueOf("research-top-n") || "--"}` : "等待本地状态加载", valueOf("market-select") ? "ok" : "warn"],
    ["2. 本地运行", progress.status === "running" ? "正在跑，请等待返回" : progress.status === "idle" ? "还没开始本轮运行" : `${progress.tag} / ${beginnerWorkflowLabel(progress.workflowId)}`, progress.tone],
    ["3. 结果解释", hasResearchResult ? (state.research ? "已有当前回测结果可读" : "已有浏览器回测回执可读") : "跑完回测后这里会出现收益、回撤、胜率和 Sharpe", hasResearchResult ? "ok" : "warn"],
    ["4. 模拟盘", hasPaperResult ? (state.paper ? "已有当前本地模拟盘回放" : "已有浏览器模拟盘回执") : "必须先确认回测可信，再做纸面模拟", hasPaperResult ? "ok" : "muted"],
  ];
}

function beginnerProgressActionButtons(progress = beginnerProgressState()) {
  const running = progress.status === "running";
  const actions = [
    {
      label: progress.targetLabel || "看证据",
      title: "先看当前状态对应的证据位置。",
      jump: progress.target || "control-operation-ledger",
      style: "secondary-button",
      disabled: false,
    },
    {
      label: "重新跑当前回测",
      title: "只跑当前表单参数的本地回测。",
      action: "research_backtest",
      style: "secondary-button",
      disabled: running,
    },
    {
      label: "一键安全刷新全流程",
      title: "按安全顺序刷新回测、信号、模拟盘和候选推广。",
      action: "startup_workflows",
      style: "primary-button",
      disabled: running,
    },
  ];
  return actions;
}

function beginnerProgressRecoveryRows(progress = beginnerProgressState()) {
  const project = state.projectStatus || {};
  const blockerCount = Number(project.blocker_count || 0);
  const active = state.activeOperation || {};
  const latestReceipt = beginnerLatestReceipt() || {};
  const latestHistory = beginnerLatestRunHistory() || {};
  const latestFailed = active.status === "failed" || latestReceipt.status === "failed" || latestHistory.status === "failed";
  if (progress.status === "running") {
    return [{
      label: "正在运行",
      value: "先等当前任务结束，不要连续点击多个运行按钮。",
      tone: "warn",
      target: "control-active-operation",
      button: "看当前操作",
    }];
  }
  if (progress.status === "failed" || latestFailed) {
    return [{
      label: "刚才运行失败",
      value: progress.summary || active.detail || latestHistory.detail || latestReceipt.decision || "先看失败原因，再重新运行。",
      tone: "danger",
      target: "control-active-operation",
      button: "看失败原因",
    }];
  }
  if (blockerCount > 0) {
    return [{
      label: "还有阻断项",
      value: `当前项目有 ${blockerCount} 个阻断项，先看修复队列和运行前检查。`,
      tone: "danger",
      target: "control-audit-repair-queue",
      button: "看修复队列",
    }];
  }
  if (!state.research && beginnerHasReceipt("research_backtest")) {
    return [{
      label: "只有浏览器回执",
      value: "已有历史回测回执，但当前页面还没有加载本轮回测结果；不确定就重新跑当前参数。",
      tone: "warn",
      target: "control-execution-receipts",
      button: "核对回执",
    }];
  }
  if (!state.research) {
    return [{
      label: "还没跑当前回测",
      value: "先跑当前参数回测，跑完再看收益、回撤、胜率和 Sharpe。",
      tone: "warn",
      target: "beginner-parameter-explainer",
      button: "看当前参数",
    }];
  }
  return [{
    label: "没有需要恢复的失败",
    value: "现在可以继续看结果闸门和模拟盘交接，不要跳过证据。",
    tone: "ok",
    target: "control-backtest-gate",
    button: "看回测闸门",
  }];
}

function renderBeginnerProgressRecovery(progress = beginnerProgressState()) {
  return beginnerProgressRecoveryRows(progress).map((item) => `
    <div class="list-row ${escapeHtml(item.tone || "warn")}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.value)}</span>
      <span class="beginner-recovery-actions">
        <button class="secondary-button" type="button" data-beginner-recovery-jump="${escapeHtml(item.target || "control-active-operation")}">${escapeHtml(item.button || "去处理")}</button>
      </span>
    </div>
  `).join("");
}

function renderBeginnerProgress() {
  const root = byId("beginner-progress-board");
  const statusTarget = byId("beginner-progress-status");
  const stepsTarget = byId("beginner-progress-steps");
  const nextTarget = byId("beginner-progress-next");
  const recoveryTarget = byId("beginner-progress-recovery");
  const tag = byId("beginner-progress-tag");
  if (!root || !statusTarget || !stepsTarget || !nextTarget || !recoveryTarget || !tag) return;
  const progress = beginnerProgressState();
  ["ok", "warn", "danger", "muted"].forEach((tone) => root.classList.remove(tone));
  root.classList.add(progress.tone);
  tag.textContent = progress.tag;
  tag.classList.toggle("tag-warn", progress.tone === "warn");
  tag.classList.toggle("tag-danger", progress.tone === "danger");
  statusTarget.innerHTML = `
    <div class="beginner-progress-card ${escapeHtml(progress.tone)}">
      <small>${escapeHtml(beginnerWorkflowLabel(progress.workflowId))}</small>
      <strong>${escapeHtml(progress.title)}</strong>
      <span>${escapeHtml(progress.summary)}</span>
      <em>${escapeHtml(progress.detail)}</em>
    </div>
  `;
  stepsTarget.innerHTML = statusRows(beginnerProgressStepRows(progress));
  const actionButtons = beginnerProgressActionButtons(progress).map((item) => {
    const attrs = item.action
      ? `data-beginner-action="${escapeHtml(item.action)}" data-beginner-progress-action="${escapeHtml(item.action)}"`
      : `data-beginner-progress-jump="${escapeHtml(item.jump || progress.target)}"`;
    return `
      <button
        class="${escapeHtml(item.style || "secondary-button")}"
        type="button"
        title="${escapeHtml(item.title || item.label)}"
        ${attrs}
        ${item.disabled ? "disabled" : ""}
      >${escapeHtml(item.label)}</button>
    `;
  }).join("");
  nextTarget.innerHTML = `
    <div class="list-row ${escapeHtml(progress.tone)}">
      <strong>下一步</strong>
      <span>${escapeHtml(progress.actionText || "看完证据后再决定下一步。")}</span>
    </div>
    <div class="list-row ok">
      <strong>新手行动台</strong>
      <span class="beginner-progress-actions">${actionButtons}</span>
    </div>
  `;
  recoveryTarget.innerHTML = renderBeginnerProgressRecovery(progress);
}

function renderBeginnerGuide() {
  const listNode = byId("beginner-step-list");
  const actionNode = byId("beginner-primary-action");
  const helpNode = byId("beginner-help-text");
  if (!listNode || !actionNode || !helpNode) return;
  listNode.innerHTML = BEGINNER_STEPS.map((step, index) => {
    const stateInfo = beginnerStepState(step.id);
    const buttonAttrs = step.action
      ? `data-beginner-action="${escapeHtml(step.action)}"`
      : `data-beginner-target="${escapeHtml(step.target || "")}" data-leaderboard-tab="${escapeHtml(step.leaderboardTab || "")}"`;
    return `
      <article class="beginner-step ${escapeHtml(stateInfo.tone)}">
        <div class="beginner-step-index">${index + 1}</div>
        <div class="beginner-step-copy">
          <strong>${escapeHtml(step.title)}</strong>
          <span>${escapeHtml(step.plain)}</span>
          <small>${escapeHtml(stateInfo.label)}</small>
        </div>
        <button class="secondary-button beginner-step-button" type="button" ${buttonAttrs}>${escapeHtml(step.button)}</button>
      </article>
    `;
  }).join("");
  const nextStep = nextBeginnerStep();
  const nextState = beginnerStepState(nextStep.id);
  const nextAttrs = nextStep.action
    ? `data-beginner-action="${escapeHtml(nextStep.action)}"`
    : `data-beginner-target="${escapeHtml(nextStep.target || "")}" data-leaderboard-tab="${escapeHtml(nextStep.leaderboardTab || "")}"`;
  actionNode.innerHTML = `
    <div class="beginner-primary-card ${escapeHtml(nextState.tone)}">
      <small>下一步建议</small>
      <strong>${escapeHtml(nextStep.title)}</strong>
      <span>${escapeHtml(nextStep.plain)}</span>
      <button class="primary-button" type="button" ${nextAttrs}>${escapeHtml(nextStep.button)}</button>
    </div>
  `;
  helpNode.innerHTML = statusRows([
    ["小白规则", "先确认安全，再只看 CN_ETF 主线，再回测，再看闸门，最后才做本地模拟。", "ok"],
    ["不要直接用", "CN 个股榜、全部历史榜、单次高收益都不能直接变成实盘 ETF 信号。", "danger"],
    ["点执行前", "所有执行按钮都会弹出安全确认，取消不会产生任何结果。", "warn"],
  ]);
}

function jumpToBeginnerTarget(targetId, leaderboardTab = "") {
  if (leaderboardTab) setLeaderboardTab(leaderboardTab);
  const target = byId(targetId);
  if (!target) return;
  const page = target.closest(".page");
  if (page?.id?.startsWith("page-")) {
    const pageName = page.id.replace("page-", "");
    const nav = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (nav && !page.classList.contains("active-page")) nav.click();
  }
  const workspace = document.querySelector(".workspace");
  const workspaceOverflowY = workspace ? getComputedStyle(workspace).overflowY : "";
  if (workspace && /auto|scroll|overlay/.test(workspaceOverflowY) && workspace.scrollHeight > workspace.clientHeight + 1) {
    const workspaceRect = workspace.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const targetTop = workspace.scrollTop + targetRect.top - workspaceRect.top - 96;
    workspace.scrollTo({
      top: Math.max(0, targetTop),
      behavior: scrollBehaviorForDistance(workspace.scrollTop, targetTop),
    });
    return;
  }
  const documentScroller = document.scrollingElement || document.documentElement;
  if (documentScroller?.scrollTo) {
    const targetTop = documentScroller.scrollTop + target.getBoundingClientRect().top - 96;
    documentScroller.scrollTo({
      top: Math.max(0, targetTop),
      behavior: scrollBehaviorForDistance(documentScroller.scrollTop, targetTop),
    });
    return;
  }
  const windowTargetTop = target.getBoundingClientRect().top + window.scrollY - 96;
  window.scrollTo({
    top: Math.max(0, windowTargetTop),
    behavior: scrollBehaviorForDistance(window.scrollY, windowTargetTop),
  });
}

function scrollBehaviorForDistance(currentTop, targetTop) {
  return Math.abs(Number(targetTop || 0) - Number(currentTop || 0)) > 2400 ? "auto" : "smooth";
}

async function runBeginnerAction(actionId, button = null) {
  if (!actionId) return;
  await runActionCenterWorkflow(actionId, button);
}

async function runBeginnerNext(button) {
  const actionId = button?.dataset?.beginnerAction || "";
  if (actionId) {
    await runBeginnerAction(actionId, button);
    return;
  }
  jumpToBeginnerTarget(button?.dataset?.beginnerTarget || "", button?.dataset?.leaderboardTab || "");
}

function renderOrdinaryHome() {
  const metricsNode = byId("ordinary-status-metrics");
  const actionNode = byId("ordinary-next-action");
  const warningNode = byId("ordinary-mainline-warning");
  if (!metricsNode || !actionNode || !warningNode) return;
  const ledger = state.factorLeaderboard || {};
  const summary = ledger.summary || {};
  const primaryBoard = ledger.leaderboards?.primary_cn_etf || {};
  const primaryRows = primaryBoard.rows || [];
  const topPrimary = primaryRows[0] || null;
  const project = state.projectStatus || {};
  const paperMetrics = state.paper?.metrics || {};
  metricsNode.innerHTML = [
    metric("当前主线", summary.primary_market || "CN_ETF", "默认只看 ETF 轮动"),
    metric("主线候选", summary.primary_market_deduped_candidate_rows ?? "--", "CN_ETF 去重参数组合"),
    metric("全部候选", summary.deduped_candidate_rows ?? "--", "所有市场历史去重"),
    metric("模拟权益", formatNumber(paperMetrics.ending_equity), "本地 paper 结果"),
  ].join("");
  actionNode.innerHTML = statusRows([
    ["现在该看", primaryRows.length ? "CN_ETF 主线榜 Top20" : "先补 CN_ETF 主线候选", primaryRows.length ? "ok" : "warn"],
    ["最靠前候选", topPrimary ? `${topPrimary.factor_name || "--"} / ${topPrimary.promotion_label || "--"}` : "暂无主线候选", topPrimary ? "ok" : "warn"],
    ["项目状态", project.overall_status || "加载中", project.blocker_count ? "warn" : "ok"],
  ]);
  warningNode.innerHTML = statusRows([
    ["主线提醒", "默认榜单只展示 CN_ETF。CN 个股资金流、择股类结果只能辅助研究，不能直接替代 ETF 轮动信号。", "danger"],
    ["推广口径", "只有通过长周期、OOS、滚动、成本和风险审计的主线候选，才可能进入模拟盘观察。", "warn"],
    ["安全边界", "本软件当前只做研究和本地模拟盘，不连接券商、不读取账户、不真实下单。", "danger"],
  ]);
}

function renderFactorLeaderboard() {
  const ledger = state.factorLeaderboard || {};
  const summary = ledger.summary || {};
  const activeBoard = getActiveLeaderboard();
  const rows = activeBoard.rows || [];
  const tag = byId("factor-leaderboard-tag");
  if (tag) {
    tag.textContent = rows.length ? `${activeBoard.label || "排行榜"} ${rows.length} 条` : "无候选";
    tag.classList.toggle("tag-warn", rows.length === 0);
  }
  document.querySelectorAll(".segmented-button[data-leaderboard-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.leaderboardTab === state.leaderboardTab);
  });
  byId("factor-inventory-metrics").innerHTML = [
    metric("可运行下拉因子", summary.runtime_dropdown_factor_names ?? "--", "能直接手动回测"),
    metric("配置因子名", summary.config_factor_names ?? "--", "configs JSON"),
    metric("报告因子名", summary.report_factor_names ?? "--", "data/reports"),
    metric("全部候选记录", summary.candidate_rows ?? "--", "case/参数组合"),
    metric("去重候选记录", summary.deduped_candidate_rows ?? "--", "排行榜池"),
    metric("CN_ETF 主线候选", summary.primary_market_deduped_candidate_rows ?? "--", "默认推广口径"),
    metric("CN 个股辅助候选", summary.cn_stock_candidate_rows ?? "--", "不能直接用于 ETF"),
    metric("扫描文件", summary.report_files_scanned ?? "--", `${summary.report_files_with_candidates ?? "--"} 命中`),
  ].join("");
  byId("factor-inventory-note").innerHTML = statusRows([
    ["口径", summary.note || "下拉因子不是历史挖掘总数；排行榜来自配置和本地报告聚合。", "ok"],
    ["主线", `默认只看 ${summary.primary_market || "CN_ETF"}，CN 个股研究只能辅助，不能直接变成 ETF 轮动信号。`, "danger"],
    ["排序依据", summary.ranking_basis || "--", "muted"],
    ["跳过文件", `${summary.report_files_skipped ?? 0}`, summary.report_files_skipped > 0 ? "warn" : "ok"],
  ]);
  byId("factor-leaderboard-explanation").innerHTML = statusRows([
    ["当前榜单", activeBoard.label || "--", rows.length ? "ok" : "warn"],
    ["榜单说明", activeBoard.description || activeBoard.empty_message || "--", state.leaderboardTab === "primary_cn_etf" ? "ok" : "warn"],
    ["安全边界", "排行榜只用于研究和本地模拟盘观察，不代表可实盘自动交易。", "danger"],
  ]);
  byId("factor-leaderboard-table").innerHTML = renderFactorLeaderboardTable(rows);
}

function renderFactorLeaderboardTable(rows) {
  if (!rows.length) {
    const board = getActiveLeaderboard();
    return `<tr><td colspan="17">${escapeHtml(board.empty_message || "暂无候选")}</td></tr>`;
  }
  const head = `
    <tr>
      <th>排名</th>
      <th>结论</th>
      <th>因子 / case</th>
      <th>市场</th>
      <th>总收益</th>
      <th>年化</th>
      <th>Sharpe</th>
      <th>最大回撤</th>
      <th>胜率</th>
      <th>RankIC</th>
      <th>交易数</th>
      <th>参数</th>
      <th>审计标签</th>
      <th>质量</th>
      <th>排序依据</th>
      <th>来源</th>
      <th>全部数据</th>
    </tr>
  `;
  const body = rows.map((row) => {
    const params = row.params && Object.keys(row.params).length ? JSON.stringify(row.params) : "--";
    const allData = row.all_data && Object.keys(row.all_data).length ? JSON.stringify(row.all_data, null, 2) : "{}";
    const badges = (row.audit_badges || []).map((badge) => `<span class="mini-badge">${escapeHtml(badge)}</span>`).join(" ");
    return `
      <tr>
        <td>${formatNumber(row.rank)}</td>
        <td><strong>${escapeHtml(row.promotion_label || "--")}</strong><br><span class="muted">${escapeHtml(row.plain_conclusion || "--")}</span></td>
        <td><strong>${escapeHtml(row.factor_name || "--")}</strong><br><span class="muted">${escapeHtml(row.case_id || "--")}</span></td>
        <td>${escapeHtml(row.market || "--")}</td>
        <td>${formatPercent(row.total_return)}</td>
        <td>${formatPercent(row.annualized_return)}</td>
        <td>${formatDecimal(row.sharpe)}</td>
        <td>${formatPercent(row.max_drawdown)}</td>
        <td>${formatPercent(row.win_rate)}</td>
        <td>${formatDecimal(row.rank_ic)}</td>
        <td>${formatNumber(row.trade_count)}</td>
        <td><code>${escapeRawHtml(params)}</code></td>
        <td>${badges || "--"}</td>
        <td>${escapeHtml(row.ranking_quality || "--")}<br><span class="muted">${escapeHtml((row.ranking_reasons || []).join(" / ") || "ok")}</span></td>
        <td>${escapeHtml(`${row.score_metric || "--"}=${formatDecimal(row.primary_score)}`)}</td>
        <td><span class="muted">${escapeHtml(row.source_file || row.source_path || "--")}</span></td>
        <td><details><summary>展开</summary><pre class="json-cell">${escapeRawHtml(allData)}</pre></details></td>
      </tr>
    `;
  }).join("");
  return `${head}${body}`;
}

function renderProjectStatus() {
  const project = state.projectStatus || {};
  const candidate = project.selected_candidate || {};
  const dataGaps = project.data_gaps || {};
  const provider = project.provider_remediation || {};
  const focus = project.residual_focus || {};
  const tushare = project.tushare || {};
  const status = project.overall_status || "loading";
  const tag = byId("project-status-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", status !== "clear" && status !== "pass");
  }
  byId("project-status-list").innerHTML = statusRows([
    ["总状态", status, status === "clear" || status === "pass" ? "ok" : "warn"],
    ["主候选", candidate.case_id || "--", candidate.promotion_status === "paper_ready" ? "ok" : "muted"],
    ["数据缺口", `${dataGaps.gap_rows ?? "--"} rows / peer trading ${dataGaps.gaps_with_peer_trading ?? "--"}`, dataGaps.gap_rows > 0 ? "warn" : "ok"],
    ["Provider remediation", `${provider.blocking_remediation_items ?? "--"} blocking / ${provider.remediation_items ?? "--"} total`, provider.blocking_remediation_items > 0 ? "warn" : "ok"],
    ["Residual focus", `${focus.residual_blockers ?? "--"} blockers / ${focus.highest_priority_track || "--"}`, focus.residual_blockers > 0 ? "warn" : "ok"],
    ["Tushare", tushare.required_now ? "现在需要你买/配置" : (tushare.reason || "本地动作还没做完"), tushare.required_now ? "danger" : "muted"],
    ["安全边界", project.safety || "Research only", "danger"],
  ]);
  byId("project-action-table").innerHTML = tableRows(project.next_actions || [], ["priority", "track_id", "command", "reason"]);
}

function renderDataCenter() {
  byId("market-table").innerHTML = (state.snapshot?.markets || []).map((market) => `
    <tr>
      <td><strong>${escapeHtml(market.market)}</strong><br><span class="muted">${escapeHtml(market.label)}</span></td>
      <td>${escapeHtml(market.source)}</td>
      <td>${escapeHtml(market.updated_at)}</td>
      <td>${formatNumber(market.rows)}</td>
      <td>${formatNumber(market.missing_values)}</td>
      <td>${formatNumber(market.anomalies)}</td>
      <td>${escapeHtml(market.status)}<br><span class="muted">${escapeHtml(market.data_mode)}</span></td>
    </tr>
  `).join("");
}

function renderFactorResearch() {
  const summary = state.research?.factor_summary || {};
  byId("factor-metrics").innerHTML = [
    metric("Mean IC", formatDecimal(summary.mean_ic), "cross-section"),
    metric("Rank IC", formatDecimal(summary.mean_rank_ic), "rank"),
    metric("ICIR", formatDecimal(summary.icir), "mean/std"),
    metric("因子", state.research?.request?.factor_name || "--", "selected"),
    metric("市场", state.research?.request?.market || "--", "selected"),
  ].join("");
  byId("ic-chart").innerHTML = multiLineChart([
    { label: "IC", color: chartTheme.strategy, rows: state.research?.ic || [], yKey: "ic" },
    { label: "Rank IC", color: chartTheme.benchmark, rows: state.research?.ic || [], yKey: "rank_ic" },
  ]);
  byId("group-chart").innerHTML = barChart(averageByKey(state.research?.group_returns || [], "quantile", "mean_forward_return"), "quantile", "mean_forward_return", chartTheme.positive);
  byId("long-short-chart").innerHTML = lineChart(state.research?.long_short || [], "long_short_return", chartTheme.negative, "Long-short");
}

function renderBacktest() {
  const metrics = state.research?.metrics || {};
  byId("backtest-metrics").innerHTML = [
    metric("年化收益", formatPercent(metrics.annualized_return), "demo"),
    metric("最大回撤", formatPercent(metrics.max_drawdown), "demo"),
    metric("Sharpe", formatDecimal(metrics.sharpe), "demo"),
    metric("胜率", formatPercent(metrics.win_rate), "demo"),
    metric("换手率", formatDecimal(metrics.turnover), "avg"),
  ].join("");
  byId("equity-chart").innerHTML = lineChart(state.research?.equity_curve || [], "equity", chartTheme.strategy, "Equity");
  byId("drawdown-chart").innerHTML = lineChart(state.research?.drawdown_curve || [], "drawdown", chartTheme.negative, "Drawdown");
  byId("trade-table").innerHTML = tableRows(state.research?.trades || [], ["signal_date", "entry_date", "exit_date", "asset_id", "market", "target_weight", "net_return"]);
  byId("holding-table").innerHTML = tableRows(state.research?.holdings || [], ["date", "asset_id", "market", "factor_name", "factor_value", "target_weight"]);
}

function renderDecision() {
  const decision = state.research?.decision || {};
  const benchmark = state.research?.benchmark_metrics || {};
  const regime = state.research?.regime || {};
  byId("decision-metrics").innerHTML = [
    metric("准入状态", decision.decision_status || "--", "gate"),
    metric("相对基准", formatPercent(benchmark.relative_return), "strategy - benchmark"),
    metric("跑赢现金", formatPercent(benchmark.excess_over_cash), "strategy - cash"),
    metric("基准收益", formatPercent(benchmark.benchmark_total_return), "benchmark"),
    metric("屏蔽日期", formatNumber(regime.blocked_signal_dates), "regime"),
  ].join("");
  byId("benchmark-chart").innerHTML = multiLineChart([
    { label: "策略", color: chartTheme.strategy, rows: state.research?.equity_curve || [], yKey: "equity" },
    { label: "基准", color: chartTheme.benchmark, rows: state.research?.benchmark_curve || [], yKey: "benchmark_equity" },
  ]);
  byId("regime-table").innerHTML = tableRows(state.research?.regime_curve || [], ["date", "regime_momentum", "regime_allowed"]);
  const reasons = decision.rejection_reasons || [];
  byId("decision-log").innerHTML = statusRows([
    ["状态", decision.decision_status || "--", decision.decision_status === "approved" ? "ok" : "warn"],
    ["拒绝原因", reasons.length ? reasons.join(" / ") : "无", reasons.length ? "warn" : "ok"],
    ["回撤上限", formatPercent(decision.max_drawdown_limit), "muted"],
    ["相对收益门槛", formatPercent(decision.min_relative_return), "muted"],
  ]);
}

function renderSignals() {
  const signal = state.signals || {};
  byId("signal-metrics").innerHTML = [
    metric("信号日期", signal.signal_date || "--", "as-of"),
    metric("目标总仓位", formatPercent(signal.target_gross_exposure), "gross"),
    metric("现金权重", formatPercent(signal.cash_weight), "cash"),
    metric("目标数量", signal.targets?.length ?? 0, "assets"),
    metric("可执行", "false", "research only"),
  ].join("");
  byId("target-table").innerHTML = tableRows(signal.targets || [], ["signal_date", "asset_id", "market", "factor_name", "factor_value", "latest_price", "target_weight"]);
  byId("rebalance-table").innerHTML = tableRows(signal.rebalance_plan || [], ["asset_id", "market", "action", "target_weight", "delta_value", "estimated_quantity_delta", "executable"]);
}

function renderPaper() {
  const paper = state.paper || {};
  const metrics = paper.metrics || {};
  byId("paper-metrics").innerHTML = [
    metric("期末权益", formatNumber(metrics.ending_equity), "demo"),
    metric("总收益", formatPercent(metrics.total_return), "simulated"),
    metric("最大回撤", formatPercent(metrics.max_equity_drawdown ?? metrics.max_drawdown), "simulated"),
    metric("成交笔数", paper.fills?.length ?? 0, "fills"),
    metric("保护事件", formatNumber(metrics.guard_event_count), "guard"),
  ].join("");
  byId("paper-equity-chart").innerHTML = lineChart(paper.equity_curve || [], "equity", chartTheme.paper, "Paper equity");
  byId("paper-exposure-chart").innerHTML = lineChart(paper.equity_curve || [], "gross_exposure", chartTheme.benchmark, "Gross exposure");
  byId("paper-fill-table").innerHTML = tableRows(paper.fills || [], ["signal_date", "execution_date", "asset_id", "market", "side", "quantity", "fill_price", "fee"]);
  byId("paper-guard-table").innerHTML = tableRows(paper.guard_events || [], ["date", "event_type", "drawdown", "blocked_buy_intents", "cooldown_remaining"]);
}

function renderDailyOps() {
  const daily = state.dailyOps || {};
  const decision = daily.decision || {};
  const candidate = daily.candidate || {};
  const risk = daily.risk || {};
  const riskPolicy = daily.risk_policy || {};
  const dailyPaperProfile = daily.paper_profile || {};
  const status = decision.status || (daily.artifact_present ? "unknown" : "missing");
  const tag = byId("daily-ops-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", status !== "paper_ready");
  }
  byId("daily-ops-metrics").innerHTML = [
    metric("运营状态", status, daily.run_date || "latest artifact"),
    metric("主候选", candidate.case_id || "--", candidate.market || "--"),
    metric("Profile", dailyPaperProfile.profile_id || "--", dailyPaperProfile.risk_tier || "no overlay"),
    metric("建议票据", daily.ticket_count ?? 0, "advisory only"),
    metric("纸面允许", decision.paper_trading_allowed ? "true" : "false", "no broker"),
    metric("最大回撤", formatPercent(risk.max_equity_drawdown), "simulation"),
    metric("回撤阈值", formatPercent(riskPolicy.max_drawdown_limit), riskPolicy.max_drawdown_breached ? "breached" : "clear"),
  ].join("");
  byId("daily-ops-status").innerHTML = statusRows([
    ["Artifact", daily.artifact_present ? daily.source_path || "present" : "missing", daily.artifact_present ? "ok" : "warn"],
    ["Decision", status, status === "paper_ready" ? "ok" : "warn"],
    ["Paper profile", `${dailyPaperProfile.profile_id || "none"} / ${dailyPaperProfile.risk_tier || "--"}`, dailyPaperProfile.profile_id ? "ok" : "muted"],
    ["Paper trading", decision.paper_trading_allowed ? "allowed" : "blocked", decision.paper_trading_allowed ? "ok" : "warn"],
    ["Live boundary", decision.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", daily.safety || "Research-to-paper only", "danger"],
  ]);
  byId("daily-ops-blocker-table").innerHTML = tableRows(
    (daily.blockers || []).map((blocker) => ({ blocker_id: blocker })),
    ["blocker_id"],
  );
  byId("daily-ops-ticket-table").innerHTML = tableRows(daily.advisory_tickets || [], [
    "ticket_id",
    "ticket_type",
    "asset_id",
    "market",
    "side",
    "estimated_quantity_delta",
    "target_weight",
    "delta_value",
    "live_order_allowed",
  ]);
  byId("daily-ops-risk-policy").innerHTML = statusRows([
    ["Max drawdown limit", formatPercent(riskPolicy.max_drawdown_limit), "muted"],
    ["Drawdown breached", riskPolicy.max_drawdown_breached ? "true" : "false", riskPolicy.max_drawdown_breached ? "warn" : "ok"],
    ["Non-manual blockers", (decision.non_manual_blocking_reasons || []).join(" / ") || "none", decision.non_manual_blocking_reasons?.length ? "warn" : "ok"],
    ["Profile max weight", formatPercent(dailyPaperProfile.max_asset_weight), dailyPaperProfile.profile_id ? "ok" : "muted"],
    ["Profile guard", formatPercent(dailyPaperProfile.max_drawdown_guard), dailyPaperProfile.profile_id ? "ok" : "muted"],
    ["Simulation fills", formatNumber(daily.simulation?.fills), "muted"],
  ]);
}

function renderRiskCandidates() {
  const pack = state.riskCandidates || {};
  const summary = pack.summary || {};
  const policy = pack.policy || {};
  const selected = pack.selected_candidate || {};
  const status = pack.selection_status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("risk-candidate-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !["risk_candidate_selected", "risk_tier_candidate_selected"].includes(status));
  }
  byId("risk-candidate-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, ["risk_candidate_selected", "risk_tier_candidate_selected"].includes(status) ? "ok" : "warn"],
    ["Eligible candidates", String(summary.tier_eligible_candidates ?? summary.risk_eligible_candidates ?? 0), (summary.tier_eligible_candidates ?? summary.risk_eligible_candidates ?? 0) > 0 ? "ok" : "warn"],
    ["Paper matched", String(summary.paper_matched_candidates ?? 0), "muted"],
    ["Selected", selected.case_id || "none", selected.case_id ? "ok" : "warn"],
    ["Risk tier", selected.risk_tier || policy.primary_risk_tier || "legacy_policy", selected.risk_tier ? "ok" : "muted"],
    ["Max drawdown limit", formatPercent(policy.max_drawdown_limit), "muted"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
  ]);
  byId("risk-candidate-action-table").innerHTML = tableRows(pack.next_actions || [], ["action", "reason", "local_only"]);
  byId("risk-candidate-table").innerHTML = tableRows(pack.candidates || [], [
    "screen_rank",
    "case_id",
    "risk_status",
    "risk_tier",
    "walk_forward_sharpe",
    "walk_forward_relative_return",
    "walk_forward_max_drawdown",
    "paper_matched",
    "paper_sharpe",
    "paper_max_drawdown",
    "rejection_reasons",
  ]);
}

function renderConstrainedSearch() {
  const pack = state.constrainedSearch || {};
  const summary = pack.summary || {};
  const frontier = pack.frontier_candidates || [];
  const selected = pack.selected_candidate || {};
  const status = pack.selection_status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("constrained-search-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !["risk_candidate_selected", "risk_tier_candidate_selected"].includes(status));
  }
  byId("constrained-search-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, ["risk_candidate_selected", "risk_tier_candidate_selected"].includes(status) ? "ok" : "warn"],
    ["Walk-forward accepted", `${summary.walk_forward_accepted ?? 0} / ${summary.walk_forward_cases ?? 0}`, summary.walk_forward_accepted > 0 ? "ok" : "warn"],
    ["Paper completed", String(summary.paper_completed ?? 0), summary.paper_completed > 0 ? "ok" : "warn"],
    ["Risk eligible", String(summary.risk_eligible_candidates ?? 0), summary.risk_eligible_candidates > 0 ? "ok" : "warn"],
    ["Frontier", String(summary.frontier_candidates ?? frontier.length), frontier.length > 0 ? "warn" : "muted"],
    ["Selected", selected.case_id || "none", selected.case_id ? "ok" : "warn"],
  ]);
  byId("constrained-frontier-table").innerHTML = tableRows(frontier, [
    "case_id",
    "risk_tier",
    "paper_sharpe",
    "paper_sharpe_gap",
    "paper_max_drawdown",
    "paper_drawdown_headroom",
    "paper_calmar",
    "walk_forward_relative_return",
    "rejection_reasons",
  ]);
}

function renderPaperProfiles() {
  const pack = state.paperProfiles || {};
  const summary = pack.summary || {};
  const policy = pack.policy || {};
  const selected = pack.selected_profile || {};
  const attempts = pack.attempts || [];
  const status = pack.selection_status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("paper-profile-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !["paper_profile_selected", "risk_tier_profile_selected"].includes(status));
  }
  byId("paper-profile-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, ["paper_profile_selected", "risk_tier_profile_selected"].includes(status) ? "ok" : "warn"],
    ["Attempts", String(summary.profile_attempts ?? attempts.length), attempts.length > 0 ? "ok" : "warn"],
    ["Eligible profiles", String(summary.eligible_profiles ?? 0), summary.eligible_profiles > 0 ? "ok" : "warn"],
    ["Selected", selected.profile_id || "none", selected.profile_id ? "ok" : "warn"],
    ["Risk tier", selected.risk_tier || policy.primary_risk_tier || "legacy_policy", selected.risk_tier ? "ok" : "muted"],
    ["Min Sharpe", formatDecimal(policy.min_paper_sharpe), "muted"],
    ["Max drawdown", formatPercent(policy.max_drawdown_limit), "muted"],
  ]);
  byId("paper-profile-attempt-table").innerHTML = tableRows(attempts, [
    "profile_id",
    "profile_status",
    "risk_tier",
    "paper_sharpe",
    "paper_max_drawdown",
    "paper_total_return",
    "paper_calmar",
    "max_asset_weight",
    "max_drawdown_guard",
    "guard_cooldown_periods",
    "rejection_reasons",
  ]);
}

function renderProfileObservation() {
  const pack = state.profileObservation || {};
  const decision = pack.decision || {};
  const summary = pack.summary || {};
  const profile = pack.paper_profile || {};
  const status = decision.observation_status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("profile-observation-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.paper_observation_allowed);
  }
  byId("profile-observation-metrics").innerHTML = [
    metric("Observation", status, decision.paper_observation_allowed ? "paper observe" : "stopped"),
    metric("Profile", profile.profile_id || "--", profile.risk_tier || "no tier"),
    metric("Stops", summary.stop_count ?? 0, `warnings ${summary.warning_count ?? 0}`),
    metric("Signal age", summary.signal_age_days ?? "--", `max ${summary.max_signal_age_days ?? "--"} days`),
    metric("Guard ratio", formatDecimal(summary.guard_event_ratio), "warning signal"),
  ].join("");
  byId("profile-observation-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Decision", status, decision.paper_observation_allowed ? "ok" : "warn"],
    ["Stop reasons", (decision.stop_reasons || []).join(" / ") || "none", decision.stop_reasons?.length ? "warn" : "ok"],
    ["Warning reasons", (decision.warning_reasons || []).join(" / ") || "none", decision.warning_reasons?.length ? "warn" : "muted"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("profile-observation-rule-table").innerHTML = tableRows(pack.stop_rules || [], [
    "rule_id",
    "severity",
    "status",
    "observed_value",
    "threshold",
    "reason",
  ]);
  byId("profile-observation-ledger-table").innerHTML = tableRows(pack.ledger || [], [
    "run_date",
    "case_id",
    "profile_id",
    "risk_tier",
    "observation_status",
    "signal_age_days",
    "max_equity_drawdown",
    "guard_event_ratio",
    "stop_reasons",
  ]);
  byId("profile-observation-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderRecentDataRefresh() {
  const pack = state.recentDataRefresh || {};
  const decision = pack.decision || {};
  const coverage = pack.coverage || {};
  const targetWindow = pack.target_window || {};
  const readiness = pack.readiness || {};
  const blockers = decision.blockers || readiness.missing || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("recent-data-refresh-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.signal_data_stale_cleared);
  }
  byId("recent-data-refresh-metrics").innerHTML = [
    metric("Recent Data", status, pack.mode || "dry_run"),
    metric("Coverage", coverage.coverage_status || "--", coverage.latest_data_date || "no latest date"),
    metric("Processed Rows", coverage.processed_rows ?? 0, `missing ${coverage.missing_date_rows ?? "--"}`),
    metric("Signal Gate", decision.signal_data_stale_cleared ? "cleared" : "blocked", targetWindow.signal_date || "--"),
    metric("Download", pack.will_download ? "execute" : "no", pack.source || "tushare"),
  ].join("");
  byId("recent-data-refresh-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.signal_data_stale_cleared ? "ok" : "warn"],
    ["Target window", `${targetWindow.start_date || "--"} to ${targetWindow.end_date || "--"}`, targetWindow.end_date ? "ok" : "muted"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Will download", pack.will_download ? "yes" : "no", pack.will_download ? "warn" : "muted"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("recent-data-refresh-coverage").innerHTML = statusRows([
    ["Coverage status", coverage.coverage_status || "--", coverage.coverage_status === "ready" ? "ok" : "warn"],
    ["Latest data date", coverage.latest_data_date || "--", coverage.latest_data_date ? "ok" : "warn"],
    ["Processed rows", formatNumber(coverage.processed_rows), coverage.processed_rows > 0 ? "ok" : "warn"],
    ["Missing date rows", formatNumber(coverage.missing_date_rows), coverage.missing_date_rows > 0 ? "warn" : "muted"],
    ["Duplicate bars", formatNumber(coverage.duplicate_bars), coverage.duplicate_bars > 0 ? "warn" : "muted"],
    ["Zero-volume rows", formatNumber(coverage.zero_volume_rows), coverage.zero_volume_rows > 0 ? "warn" : "muted"],
  ]);
  byId("recent-data-refresh-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderPostRefreshReplay() {
  const pack = state.postRefreshReplay || {};
  const decision = pack.decision || {};
  const recent = pack.recent_data_refresh || {};
  const daily = pack.daily_ops || {};
  const observation = pack.profile_observation || {};
  const blockers = decision.blockers || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("post-refresh-replay-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.post_refresh_replay_allowed);
  }
  byId("post-refresh-replay-metrics").innerHTML = [
    metric("Post Replay", status, decision.post_refresh_replay_allowed ? "paper cleared" : "blocked"),
    metric("Recent Ready", decision.recent_data_ready ? "yes" : "no", recent.status || "--"),
    metric("Daily Ops", daily.status || "--", daily.paper_trading_allowed ? "paper allowed" : "blocked"),
    metric("Observation", observation.observation_status || "--", observation.paper_observation_allowed ? "allowed" : "stopped"),
    metric("Blockers", blockers.length, blockers.join(" / ") || "none"),
  ].join("");
  byId("post-refresh-replay-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.post_refresh_replay_allowed ? "ok" : "warn"],
    ["Recent refresh", `${recent.status || "--"} / ${recent.source || "--"}`, decision.recent_data_ready ? "ok" : "warn"],
    ["Daily Ops", `${daily.status || "--"} / paper ${daily.paper_trading_allowed ? "yes" : "no"}`, decision.daily_ops_paper_allowed ? "ok" : "warn"],
    ["Observation", `${observation.observation_status || "--"} / paper ${observation.paper_observation_allowed ? "yes" : "no"}`, decision.profile_observation_allowed ? "ok" : "warn"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("post-refresh-replay-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderObservationSufficiency() {
  const pack = state.observationSufficiency || {};
  const fills = pack.fills || {};
  const recommendation = pack.recommendation || {};
  const decision = pack.decision || {};
  const blockers = decision.blockers || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("observation-sufficiency-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.observation_sufficiency_cleared);
  }
  byId("observation-sufficiency-metrics").innerHTML = [
    metric("Sample Gate", status, decision.observation_sufficiency_cleared ? "cleared" : "blocked"),
    metric("Fills", `${fills.observed_fills ?? "--"} / ${fills.required_fills ?? "--"}`, `deficit ${fills.fill_deficit ?? "--"}`),
    metric("Obs Days", fills.observation_days ?? "--", `rate ${formatDecimal(fills.fill_rate_per_day)}`),
    metric("Suggested Start", recommendation.suggested_start_date || "--", recommendation.suggested_end_date || "--"),
    metric("Relax Min Fills", recommendation.threshold_relaxation_allowed ? "review" : "no", recommendation.threshold_policy || "extend first"),
  ].join("");
  byId("observation-sufficiency-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.observation_sufficiency_cleared ? "ok" : "warn"],
    ["Observed fills", `${fills.observed_fills ?? "--"} / ${fills.required_fills ?? "--"}`, fills.fill_deficit > 0 ? "warn" : "ok"],
    ["Estimated days", recommendation.estimated_total_observation_days ?? "--", "muted"],
    ["Suggested window", `${recommendation.suggested_start_date || "--"} to ${recommendation.suggested_end_date || "--"}`, recommendation.suggested_start_date ? "ok" : "muted"],
    ["Threshold relaxation", recommendation.threshold_relaxation_allowed ? "review allowed" : "not allowed", recommendation.threshold_relaxation_allowed ? "warn" : "muted"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("observation-sufficiency-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderExpandedObservationReplay() {
  const pack = state.expandedObservationReplay || {};
  const decision = pack.decision || {};
  const replayWindow = pack.window || {};
  const recent = pack.recent_data_refresh || {};
  const final = pack.final_observation_sufficiency || {};
  const finalFills = final.fills || {};
  const blockers = decision.blockers || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("expanded-observation-replay-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.expanded_observation_cleared);
  }
  byId("expanded-observation-replay-metrics").innerHTML = [
    metric("Expanded Replay", status, decision.expanded_observation_cleared ? "cleared" : "blocked"),
    metric("Window", replayWindow.start_date || "--", replayWindow.end_date || "--"),
    metric("Refresh Rows", recent.coverage?.processed_rows ?? "--", recent.status || "--"),
    metric("Final Fills", `${finalFills.observed_fills ?? "--"} / ${finalFills.required_fills ?? "--"}`, `deficit ${finalFills.fill_deficit ?? "--"}`),
    metric("Blockers", blockers.length, blockers.join(" / ") || "none"),
  ].join("");
  byId("expanded-observation-replay-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.expanded_observation_cleared ? "ok" : "warn"],
    ["Window", `${replayWindow.start_date || "--"} to ${replayWindow.end_date || "--"}`, replayWindow.start_date ? "ok" : "muted"],
    ["Recent refresh", `${recent.status || "--"} / rows ${recent.coverage?.processed_rows ?? "--"}`, recent.status === "completed" ? "ok" : "warn"],
    ["Final sufficiency", `${final.status || "--"} / ${finalFills.observed_fills ?? "--"} fills`, final.status === "sufficient" ? "ok" : "warn"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("expanded-observation-replay-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderIterativeObservationExpansion() {
  const pack = state.iterativeObservationExpansion || {};
  const decision = pack.decision || {};
  const final = pack.final_observation_sufficiency || {};
  const finalFills = final.fills || {};
  const blockers = decision.blockers || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("iterative-observation-expansion-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.iterative_observation_cleared);
  }
  byId("iterative-observation-expansion-metrics").innerHTML = [
    metric("Iterative Gate", status, decision.iterative_observation_cleared ? "cleared" : "blocked"),
    metric("Rounds", `${pack.round_count ?? "--"} / ${pack.max_rounds ?? "--"}`, decision.initial_extendable ? "extendable" : "blocked"),
    metric("Final Fills", `${finalFills.observed_fills ?? "--"} / ${finalFills.required_fills ?? "--"}`, `deficit ${finalFills.fill_deficit ?? "--"}`),
    metric("Blockers", blockers.length, blockers.join(" / ") || "none"),
  ].join("");
  byId("iterative-observation-expansion-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.iterative_observation_cleared ? "ok" : "warn"],
    ["Rounds", `${pack.round_count ?? "--"} / ${pack.max_rounds ?? "--"}`, pack.round_count > 0 ? "ok" : "muted"],
    ["Final sufficiency", `${final.status || "--"} / ${finalFills.observed_fills ?? "--"} fills`, final.status === "sufficient" ? "ok" : "warn"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("iterative-observation-expansion-round-table").innerHTML = tableRows(
    (pack.rounds || []).map((row) => {
      const expanded = row.expanded_observation_replay || {};
      const window = expanded.window || {};
      const finalRound = expanded.final_observation_sufficiency || {};
      const fills = finalRound.fills || {};
      return {
        round: row.round,
        status: expanded.status,
        start_date: window.start_date,
        end_date: window.end_date,
        observed_fills: fills.observed_fills,
        required_fills: fills.required_fills,
        fill_deficit: fills.fill_deficit,
      };
    }),
    ["round", "status", "start_date", "end_date", "observed_fills", "required_fills", "fill_deficit"],
  );
  byId("iterative-observation-expansion-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderTushareActivationGate() {
  const pack = state.tushareActivationGate || {};
  const decision = pack.decision || {};
  const readiness = pack.readiness || {};
  const recent = pack.recent_data_refresh || {};
  const final = pack.final_observation_sufficiency || {};
  const finalFills = final.fills || {};
  const blockers = decision.blockers || [];
  const status = pack.status || (pack.artifact_present ? "unknown" : "missing");
  const tag = byId("tushare-activation-gate-tag");
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", !decision.paper_continuation_allowed);
  }
  byId("tushare-activation-gate-metrics").innerHTML = [
    metric("Activation Gate", status, decision.paper_continuation_allowed ? "paper ready" : "blocked"),
    metric("Tushare Ready", readiness.ready ? "yes" : "no", (readiness.missing || []).join(" / ") || "ready"),
    metric("Recent Rows", recent.coverage?.processed_rows ?? "--", recent.status || "not run"),
    metric("Final Fills", `${finalFills.observed_fills ?? "--"} / ${finalFills.required_fills ?? "--"}`, `deficit ${finalFills.fill_deficit ?? "--"}`),
  ].join("");
  byId("tushare-activation-gate-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Status", status, decision.paper_continuation_allowed ? "ok" : "warn"],
    ["Mode", `${pack.mode || "--"} / ${pack.source || "--"}`, pack.mode === "execute" ? "ok" : "muted"],
    ["Readiness", readiness.ready ? "ready" : (readiness.missing || []).join(" / ") || "unknown", readiness.ready ? "ok" : "warn"],
    ["Recent data", decision.recent_data_ready ? "ready" : recent.status || "--", decision.recent_data_ready ? "ok" : "warn"],
    ["Post replay", decision.post_refresh_replay_allowed ? "cleared" : "blocked", decision.post_refresh_replay_allowed ? "ok" : "warn"],
    ["Sample gate", decision.observation_sufficiency_cleared || decision.iterative_observation_cleared ? "cleared" : "blocked", decision.paper_continuation_allowed ? "ok" : "warn"],
    ["Blockers", blockers.join(" / ") || "none", blockers.length ? "warn" : "ok"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
    ["Safety", pack.safety || "Research-to-paper only", "danger"],
  ]);
  byId("tushare-activation-gate-ledger-table").innerHTML = tableRows(pack.stage_ledger || [], [
    "stage",
    "status",
    "cleared",
    "blockers",
  ]);
  byId("tushare-activation-gate-action-table").innerHTML = tableRows(pack.next_actions || [], [
    "action",
    "reason",
    "command",
    "local_only",
  ]);
}

function renderPromotionOps() {
  const ops = state.promotion || {};
  const summary = ops.summary || {};
  const top = ops.top_candidate || {};
  byId("promotion-metrics").innerHTML = [
    metric("Top candidate", top.case_id || "--", top.risk_profile_id || "risk profile"),
    metric("Paper ready", summary.paper_ready ?? 0, "candidates"),
    metric("Blocked", summary.blocked ?? 0, "candidates"),
    metric("Duplicates", summary.duplicates ?? 0, "clusters"),
    metric("Live review", ops.live_review_allowed ? "allowed" : "blocked", "pre-API"),
  ].join("");
  byId("promotion-blockers").innerHTML = statusRows((ops.live_review_blockers || []).map((reason) => [reason, "blocking", "warn"]));
  byId("promotion-action-list").innerHTML = statusRows((ops.next_actions || []).map((item) => [item.action, item.reason, "ok"]));
  renderPromotionReview();
  renderEvidenceRefresh();
  byId("promotion-candidate-table").innerHTML = tableRows(ops.candidates || [], [
    "rank",
    "case_id",
    "promotion_status",
    "score",
    "risk_profile_id",
    "test_sharpe",
    "paper_sharpe",
    "paper_max_drawdown",
  ]);
  byId("promotion-duplicate-table").innerHTML = tableRows(ops.duplicate_clusters || [], ["canonical_case_id", "duplicate_count", "duplicates"]);
}

function renderPromotionReview() {
  const packet = state.promotionReview || {};
  const candidate = packet.selected_candidate || {};
  const gate = packet.manual_review_gate || {};
  byId("promotion-review-status").innerHTML = statusRows([
    ["Review status", packet.review_status || "--", packet.review_status === "blocked" ? "warn" : "ok"],
    ["Selected candidate", candidate.case_id || "--", "ok"],
    ["Manual review gate", gate.status || "--", gate.allowed ? "ok" : "warn"],
    ["Safety", packet.safety || "Research only", "danger"],
  ]);
  byId("promotion-review-checklist").innerHTML = tableRows(packet.checklist || [], ["check_id", "status", "evidence"]);
  byId("promotion-review-markdown").textContent = packet.markdown || "";
}

function renderEvidenceRefresh() {
  const plan = state.evidenceRefresh || {};
  const candidate = plan.selected_candidate || {};
  byId("evidence-refresh-status").innerHTML = statusRows([
    ["Refresh status", plan.refresh_status || "--", plan.refresh_status === "clear" ? "ok" : "warn"],
    ["Selected candidate", candidate.case_id || "--", "ok"],
    ["Tracks", String((plan.tracks || []).length), "muted"],
    ["Safety", plan.safety || "Research only", "danger"],
  ].concat((plan.tracks || []).map((track) => [track.track_id, track.status, track.status === "clear" ? "ok" : "warn"])));
  byId("evidence-refresh-action-table").innerHTML = tableRows(plan.ordered_actions || [], ["priority", "track_id", "command", "reason"]);
}

function renderLogs() {
  const logs = state.snapshot?.logs || {};
  const rows = [...(logs.research || []), ...(logs.backtest || []), ...(logs.errors || [])];
  byId("task-log").innerHTML = rows.map((item) => `
    <div class="list-row"><strong>${escapeHtml(item.level)} / ${escapeHtml(item.time || "")}</strong><span>${escapeHtml(item.message)}</span></div>
  `).join("");
  byId("report-list").innerHTML = (state.snapshot?.reports || []).map((report) => `
    <div class="list-row"><strong>${escapeHtml(report.name)}</strong><span>${escapeHtml(report.kind)} / ${escapeHtml(report.path)}</span></div>
  `).join("");
}

function metric(label, value, meta) {
  return `<div class="metric-card"><small>${escapeHtml(zhConsoleText(label))}</small><strong>${escapeHtml(zhConsoleText(String(value)))}</strong><span>${escapeHtml(zhConsoleText(meta || ""))}</span></div>`;
}

function statusRows(rows) {
  return rows.map(([label, value, tone]) => `
    <div class="list-row ${escapeHtml(tone || "")}"><strong>${escapeHtml(zhConsoleText(label))}</strong><span>${escapeHtml(zhConsoleText(value || ""))}</span></div>
  `).join("");
}

const GUI_ZH_REPLACEMENTS = [
  ["Next actions", "下一步动作"],
  ["Control API", "中控 API"],
  ["Browser smoke", "浏览器冒烟"],
  ["Project audit", "项目审计"],
  ["GUI unit tests", "GUI 单元测试"],
  ["GUI compile check", "GUI 编译检查"],
  ["Safe sync audit", "安全同步审计"],
  ["Current API process", "当前 API 进程"],
  ["Processes", "进程"],
  ["detected", "已检测到"],
  ["not detected", "未检测到"],
  ["Current browser operation", "当前浏览器操作"],
  ["Tracked workflows", "已跟踪工作流"],
  ["browser receipts", "浏览器回执"],
  ["The browser marks an operation running before calling a workflow API and keeps the latest receipt visible after completion.", "调用工作流 API 前会标记为运行中，并在完成后保留最新回执。"],
  ["browser localStorage + API receipts", "浏览器本地存储 + API 回执"],
  ["Updated immediately when the operator starts research, signal, paper, or verification work from the GUI.", "操作员从 GUI 启动研究、信号、模拟盘或验证任务时会立即更新。"],
  ["Last browser receipt", "最近浏览器回执"],
  ["Completed operations stay visible with status, timing, request parameters, metrics, or verification return code.", "已完成操作会保留状态、耗时、请求参数、指标或验证返回码。"],
  ["Recent server operation", "最近服务端操作"],
  ["No active operation", "没有正在执行的操作"],
  ["No process monitor data", "暂无进程监控数据"],
  ["The control API should expose current GUI, audit, smoke, and research processes.", "中控 API 应展示当前 GUI、审计、烟测和研究进程。"],
  ["No workflow preflight rows", "暂无工作流预检行"],
  ["Control status should expose run readiness before workflow buttons are used.", "使用工作流按钮前，中控状态应展示运行就绪情况。"],
  ["No local run history", "暂无本机运行历史"],
  ["No execution receipts", "暂无执行回执"],
  ["No backtest provenance", "暂无回测溯源"],
  ["No backtest gate", "暂无回测闸门"],
  ["No release readiness rows", "暂无发布就绪检查行"],
  ["Manual verification required", "需要人工验证"],
  ["Push ready", "可以推送"],
  ["Run a local workflow to record it in this browser.", "运行一次本地工作流后会在本浏览器记录历史。"],
  ["Run research, signals, or paper simulation to record a structured receipt.", "运行研究回测、信号快照或纸面模拟后会记录结构化回执。"],
  ["Run the control-center snapshot to populate local release gates.", "刷新中控台快照后会填充本地发布闸门。"],
  ["The control API must expose source, parameter, endpoint, output, and safety provenance for each backtest.", "中控 API 必须展示每次回测的数据源、参数、端点、输出和安全溯源。"],
  ["Work visibility", "工作可视性"],
  ["Backtest transparency", "回测透明度"],
  ["Paper handoff", "模拟盘交接"],
  ["Audit cadence", "审计节奏"],
  ["Keep live trading boundary blocked", "保持实盘边界阻断"],
  ["No broker connection, account reads, order placement, or live trading.", "无券商连接、账户读取、下单或实盘交易。"],
  ["5-round audit", "五轮审计"],
  ["Write the five-round audit report and next flow plan before continuing GUI implementation.", "继续 GUI 实现前先写五轮审计报告和下一步流程计划。"],
  ["Write the five-round audit report and next flow plan before continuing GUI optimization.", "继续 GUI 优化前先写五轮审计报告和下一步流程计划。"],
  ["GUI audit heartbeat", "GUI 审计心跳"],
  ["Round audit cadence", "轮次审计节奏"],
  ["Result evidence", "结果证据"],
  ["Release readiness", "发布就绪"],
  ["Operator timeline", "操作时间线"],
  ["Audit repair queue", "审计修复队列"],
  ["Round checkpoint", "轮次复盘"],
  ["Audit iteration", "审计迭代"],
  ["Verification runner", "验证执行器"],
  ["Workflow commands", "工作流命令"],
  ["Report links", "报告链接"],
  ["Safety boundary", "安全边界"],
  ["Data source", "数据源"],
  ["Data root", "数据目录"],
  ["Factor windows", "因子窗口"],
  ["Execution lag", "执行滞后"],
  ["Forward horizon", "预测周期"],
  ["Initial cash", "初始资金"],
  ["Commission", "佣金"],
  ["Slippage", "滑点"],
  ["Max drawdown", "最大回撤"],
  ["Win rate", "胜率"],
  ["Total return", "总收益"],
  ["Annualized return", "年化收益"],
  ["Sharpe", "夏普"],
  ["Trade count", "交易次数"],
  ["Benchmark relative return", "相对基准收益"],
  ["Paper ending equity", "模拟盘期末权益"],
  ["Run research backtest", "运行研究回测"],
  ["Refresh Daily Ops", "刷新日常运营"],
  ["Refresh Promotion Ops", "刷新候选推广"],
  ["Daily Ops", "日常运营"],
  ["Promotion Ops", "候选推广"],
  ["Activation Gate", "启用闸门"],
  ["Recent Ready", "近期数据就绪"],
  ["Recent Data", "近期数据"],
  ["Post Replay", "刷新后回放"],
  ["Tushare activation", "Tushare 启用"],
  ["Promotion blockers", "推广阻断项"],
  ["Sample Gate", "样本闸门"],
  ["Expanded Replay", "扩展回放"],
  ["Iterative Gate", "迭代闸门"],
  ["Observation", "观察"],
  ["Blockers", "阻断项"],
  ["Artifact", "产物"],
  ["Decision", "决策"],
  ["Paper profile", "模拟盘参数"],
  ["Paper trading", "纸面交易"],
  ["Live boundary", "实盘边界"],
  ["Safety", "安全边界"],
  ["Selection", "筛选"],
  ["Eligible candidates", "合格候选"],
  ["Paper matched", "纸面匹配"],
  ["Selected", "已选择"],
  ["Risk tier", "风险层级"],
  ["Attempts", "尝试次数"],
  ["Eligible profiles", "合格参数"],
  ["Stop reasons", "停止原因"],
  ["Warning reasons", "预警原因"],
  ["Observed fills", "观察成交"],
  ["Estimated days", "预计天数"],
  ["Suggested window", "建议窗口"],
  ["Threshold relaxation", "阈值放宽"],
  ["Recent refresh", "近期刷新"],
  ["Post replay", "刷新后回放"],
  ["Generate advisory signal snapshot", "生成信号快照"],
  ["Run local paper simulation", "运行本地模拟盘"],
  ["Research backtest", "研究回测"],
  ["Research backtest receipt", "研究回测回执"],
  ["Advisory signal receipt", "建议信号回执"],
  ["Paper simulation receipt", "模拟盘回执"],
  ["full parameter backtest request", "完整参数回测请求"],
  ["advisory target-weight request", "建议目标仓位请求"],
  ["local paper-only simulation request", "本地纸面模拟请求"],
  ["Signal snapshot", "信号快照"],
  ["Paper simulation", "模拟盘"],
  ["Live trading boundary", "实盘交易边界"],
  ["Live trading", "实盘交易"],
  ["Backtest gate", "回测闸门"],
  ["Paper readiness", "模拟盘交接"],
  ["Metric floor", "指标门槛"],
  ["Current research receipt", "当前研究回执"],
  ["Current paper receipt", "当前模拟盘回执"],
  ["Paper observation gate", "模拟盘观察闸门"],
  ["Run preflight", "运行前检查"],
  ["Mode control", "模式控制"],
  ["Workspace", "工作区"],
  ["Machine", "机器"],
  ["Task", "任务"],
  ["Branch", "分支"],
  ["Goal", "目标"],
  ["Active", "当前"],
  ["Status", "状态"],
  ["Pending", "排队"],
  ["Blocked", "阻塞"],
  ["Next", "下一步"],
  ["Source", "来源"],
  ["Market", "市场"],
  ["TopN + cost", "TopN 与成本"],
  ["Rebalance", "调仓"],
  ["Window", "日期窗口"],
  ["Benchmark", "基准"],
  ["ready_to_run", "可运行"],
  ["gate_controlled", "受闸门控制"],
  ["awaiting_metrics", "等待指标"],
  ["awaiting_metric", "等待指标"],
  ["awaiting_current_receipt", "等待当前回执"],
  ["awaiting_browser_receipts", "等待浏览器回执"],
  ["awaiting_server_receipts", "等待服务端回执"],
  ["blocked_expected", "预期阻断"],
  ["expected_block", "预期阻断"],
  ["blocked_live", "实盘已阻断"],
  ["not_run", "未运行"],
  ["missing", "缺失"],
  ["stale", "过期"],
  ["current", "当前"],
  ["ready", "就绪"],
  ["review", "需复核"],
  ["running", "运行中"],
  ["waiting", "等待"],
  ["completed", "完成"],
  ["passed", "通过"],
  ["failed", "失败"],
  ["blocked", "阻断"],
  ["queued", "排队"],
  ["runnable", "可运行"],
  ["idle", "待命"],
  ["loading", "加载中"],
  ["browser_runtime", "浏览器运行态"],
  ["browser_managed", "浏览器管理"],
  ["due_now", "现在到期"],
  ["good", "良好"],
  ["dirty", "有变更"],
  ["clean", "干净"],
  ["clear", "通过"],
  ["unknown", "未知"],
  ["present", "存在"],
  ["available", "可用"],
  ["required_before_push", "推送前必需"],
  ["passed_evidence", "证据通过"],
  ["missing_required", "缺少必需项"],
  ["yes", "是"],
  ["no", "否"],
  ["true", "是"],
  ["false", "否"],
  ["enabled", "启用"],
  ["disabled", "禁用"],
  ["paper_candidate", "模拟盘候选"],
  ["receipt", "回执"],
  ["paper_ready", "模拟盘就绪"],
  ["paper_profile_selected", "已选择模拟盘参数"],
  ["risk_tier_profile_selected", "已选择风险层级参数"],
  ["risk_candidate_selected", "已选择风险候选"],
  ["risk_tier_candidate_selected", "已选择风险层级候选"],
  ["paper_observation_ready", "纸面观察就绪"],
  ["completed_with_blockers", "完成但有阻断项"],
  ["needs_evidence", "需要证据"],
  ["manual_required", "需要人工验证"],
  ["allowed", "允许"],
  ["cleared", "通过"],
  ["stopped", "停止"],
  ["breached", "突破"],
  ["none", "无"],
  ["local", "本地"],
  ["latest", "最新"],
  ["artifact", "产物"],
  ["Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.", "仅研究到模拟盘；不连接券商、不读取账户、不真实下单、不启用实盘。"],
  ["No broker connection, no account reads, no order placement, no live trading.", "不连接券商、不读取账户、不真实下单、不启用实盘。"],
  ["Research only. No broker, no orders, no live trading.", "仅研究模式。无券商连接、无真实下单、无实盘交易。"],
  ["Research only. No broker, 否 orders, 否 live trading.", "仅研究模式。无券商连接、无真实下单、无实盘交易。"],
  ["research calculation only; no broker, account, or order side effects", "仅研究计算；无券商、账户或下单副作用"],
  ["advisory targets only; executable=false and no order routing", "仅建议信号；不可执行且无订单路由"],
  ["local simulated fills only; no broker, account, or order side effects", "仅本地模拟成交；无券商、账户或下单副作用"],
  ["Server receipt is stale; refresh the current command before trusting metrics.", "服务端回执已过期；信任指标前需要按当前参数重跑。"],
  ["Server receipt is missing; refresh the current command before trusting metrics.", "缺少服务端回执；信任指标前需要按当前参数重跑。"],
  ["Run", "运行"],
];

function zhConsoleText(value) {
  let text = String(value ?? "");
  const phraseReplacements = GUI_ZH_REPLACEMENTS
    .filter(([source]) => !/^[a-z_]+$/.test(source))
    .sort(([left], [right]) => String(right).length - String(left).length);
  const tokenReplacements = GUI_ZH_REPLACEMENTS.filter(([source]) => /^[a-z_]+$/.test(source));
  phraseReplacements.forEach(([source, target]) => {
    text = text.replaceAll(source, target);
  });
  tokenReplacements.forEach(([source, target]) => {
    text = text.replace(new RegExp(`\\b${escapeRegExp(source)}\\b`, "g"), target);
  });
  return text;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function tableRows(rows, columns) {
  const head = `<tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
  const body = rows.slice(0, 80).map((row) => `
    <tr>${columns.map((column) => `<td>${formatCell(row[column])}</td>`).join("")}</tr>
  `).join("");
  return `${head}${body}`;
}

function averageByKey(rows, key, valueKey) {
  const buckets = new Map();
  rows.forEach((row) => {
    const bucket = String(row[key]);
    const value = Number(row[valueKey]);
    if (!Number.isFinite(value)) return;
    const current = buckets.get(bucket) || { total: 0, count: 0 };
    current.total += value;
    current.count += 1;
    buckets.set(bucket, current);
  });
  return Array.from(buckets.entries()).map(([bucket, value]) => ({
    [key]: bucket,
    [valueKey]: value.count === 0 ? 0 : value.total / value.count,
  }));
}

function lineChart(rows, yKey, color, label) {
  return multiLineChart([{ label, color, rows, yKey }]);
}

function multiLineChart(series) {
  const width = 760;
  const height = 276;
  const pad = { left: 54, right: 24, top: 30, bottom: 38 };
  const normalized = series.map((item) => ({
    ...item,
    points: (item.rows || []).map((row) => Number(row[item.yKey])).filter((value) => Number.isFinite(value)),
  }));
  const all = normalized.flatMap((item) => item.points);
  if (all.length === 0) return emptyChart("No data");
  let minY = Math.min(...all);
  let maxY = Math.max(...all);
  if (minY === maxY) {
    minY -= 0.5;
    maxY += 0.5;
  }
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const maxLen = Math.max(...normalized.map((item) => item.points.length));
  const paths = normalized.map((item) => {
    const coords = item.points.map((value, index) => {
      const x = pad.left + (innerW * index) / Math.max(maxLen - 1, 1);
      const y = pad.top + innerH - ((value - minY) / (maxY - minY)) * innerH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return `<polyline points="${coords}" fill="none" stroke="${item.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>`;
  }).join("");
  const legend = normalized.map((item, index) => `
    <g transform="translate(${pad.left + index * 120}, 16)">
      <rect width="18" height="4" rx="2" fill="${item.color}"></rect>
      <text x="24" y="5" font-size="12" fill="${chartTheme.muted}">${escapeSvg(item.label)}</text>
    </g>
  `).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="line chart">
      <rect width="${width}" height="${height}" fill="${chartTheme.background}"></rect>
      ${legend}
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="${chartTheme.grid}"></line>
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="${chartTheme.grid}"></line>
      <text x="10" y="${pad.top + 5}" font-size="11" fill="${chartTheme.muted}">${maxY.toFixed(3)}</text>
      <text x="10" y="${height - pad.bottom}" font-size="11" fill="${chartTheme.muted}">${minY.toFixed(3)}</text>
      ${paths}
    </svg>
  `;
}

function barChart(rows, xKey, yKey, color) {
  const points = rows.map((row) => ({ label: String(row[xKey]), value: Number(row[yKey]) })).filter((point) => Number.isFinite(point.value));
  if (points.length === 0) return emptyChart("No data");
  const width = 560;
  const height = 260;
  const pad = { left: 46, right: 18, top: 24, bottom: 44 };
  const minY = Math.min(0, ...points.map((point) => point.value));
  const maxY = Math.max(0.001, ...points.map((point) => point.value));
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const zeroY = pad.top + innerH - ((0 - minY) / (maxY - minY)) * innerH;
  const barW = Math.max(16, innerW / points.length - 12);
  const bars = points.map((point, index) => {
    const x = pad.left + index * (innerW / points.length) + 6;
    const y = pad.top + innerH - ((point.value - minY) / (maxY - minY)) * innerH;
    const h = Math.abs(zeroY - y);
    return `
      <rect x="${x}" y="${Math.min(y, zeroY)}" width="${barW}" height="${h}" rx="3" fill="${color}"></rect>
      <text x="${x}" y="${height - 18}" font-size="11" fill="${chartTheme.muted}">${escapeSvg(point.label.slice(0, 9))}</text>
    `;
  }).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="bar chart">
      <rect width="${width}" height="${height}" fill="${chartTheme.background}"></rect>
      <line x1="${pad.left}" y1="${zeroY}" x2="${width - pad.right}" y2="${zeroY}" stroke="${chartTheme.grid}"></line>
      ${bars}
    </svg>
  `;
}

function emptyChart(label) {
  return `<svg viewBox="0 0 520 240" role="img" aria-label="${escapeHtml(label)}"><rect width="520" height="240" fill="${chartTheme.background}"></rect><text x="30" y="122" fill="${chartTheme.muted}">${escapeSvg(label)}</text></svg>`;
}

function renderAuditPackets(rows) {
  if (!rows || rows.length === 0) {
    return `
      <div class="list-row warn">
        <strong>No audit packets configured</strong>
        <span>Run the GUI control-center audit to create the evidence spine.</span>
      </div>
    `;
  }
  return rows.slice(0, 6).map((item) => {
    const status = item.status || "";
    const statusClass = status === "present" ? "ok" : item.required ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.packet_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.cadence || ""}`)}</span>
        <span>${escapeHtml(item.markdown_path || item.path || "")}</span>
        <span>${escapeHtml(item.command || "")}</span>
      </div>
    `;
  }).join("");
}

function renderAuditFeedback(feedback = {}) {
  const summary = feedback.summary || {};
  const actions = feedback.next_actions || [];
  const status = feedback.status || "packet_missing";
  const statusClass = status === "packet_present" ? "ok" : status === "packet_invalid" ? "danger" : "warn";
  const scoreText = summary.score == null ? "--" : `${summary.score} / ${summary.max_score ?? "--"}`;
  const header = `
    <div class="list-row ${escapeHtml(statusClass)}">
      <strong>${escapeHtml(`${scoreText} / ${summary.verdict || status}`)}</strong>
      <span>${escapeHtml(summary.generated_at || summary.source_path || "")}</span>
      <span>${escapeHtml(feedback.evidence || "")}</span>
    </div>
  `;
  const actionRows = actions.slice(0, 5).map((item) => `
    <div class="list-row ${escapeHtml(item.priority === "P0" ? "danger" : item.priority === "P1" ? "warn" : "ok")}">
      <strong>${escapeHtml(`${item.priority || "--"} / ${item.action || ""}`)}</strong>
      <span>${escapeHtml(item.reason || item.command || "")}</span>
    </div>
  `).join("");
  return header + (actionRows || `
    <div class="list-row warn">
      <strong>No audit feedback actions</strong>
      <span>Review the independent audit packet before the next GUI optimization round.</span>
    </div>
  `);
}

function renderRoundCheckpointReport(report = {}) {
  const summary = report.summary || {};
  const recentWork = report.recent_work || [];
  const flowPlan = report.flow_plan || {};
  const nextSteps = flowPlan.next_steps || [];
  const status = summary.status || "missing";
  const headerClass = summary.live_trading_allowed ? "danger" : status === "missing" ? "warn" : "ok";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Round ${summary.current_round ?? 0} / ${summary.audit_score ?? "--"}-${summary.max_score ?? "--"} / ${summary.verdict || status}`)}</strong>
      <span>${escapeHtml(`cadence=${summary.cadence_rounds ?? 5} rounds / summarized=${summary.completed_rounds ?? 0} / remaining=${summary.rounds_until_next_audit ?? "--"}`)}</span>
      <span>${escapeHtml(summary.next_review_trigger || "Generate a checkpoint report every five GUI rounds.")}</span>
    </div>
  `;
  const workRows = recentWork.slice(0, 5).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "failed" ? "danger" : item.status === "completed" || item.status === "passed" ? "ok" : "warn")}">
      <strong>${escapeHtml(item.label || item.workflow_id || "")}</strong>
      <span>${escapeHtml(`${item.recorded_at || "--"} / ${item.status || "--"}`)}</span>
      <span>${escapeHtml(item.request_summary || item.metric_summary || item.command || "")}</span>
    </div>
  `).join("");
  const planRows = nextSteps.slice(0, 5).map((item) => `
    <div class="list-row ${escapeHtml(item.priority === "P0" ? "danger" : item.priority === "P1" ? "warn" : "ok")}">
      <strong>${escapeHtml(`${item.priority || "--"} / ${item.action || ""}`)}</strong>
      <span>${escapeHtml(item.reason || "")}</span>
      <span>${escapeHtml(item.verification || "")}</span>
    </div>
  `).join("");
  return header + (workRows || `
    <div class="list-row warn">
      <strong>No recent GUI rounds</strong>
      <span>Run GUI workflows or verification gates to populate the five-round report.</span>
    </div>
  `) + (planRows || `
    <div class="list-row warn">
      <strong>No next flow plan</strong>
      <span>Run the independent GUI audit to generate the next flow plan.</span>
    </div>
  `);
}

function renderAuditIterationPlan(plan = {}) {
  const summary = plan.summary || {};
  const rows = plan.rows || [];
  const headerClass = summary.active_actions > 0 ? "warn" : "ok";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`${summary.audit_score ?? "--"} / ${summary.max_score ?? "--"} ${summary.source || "audit source"}`)}</strong>
      <span>${escapeHtml(`actions=${summary.active_actions ?? "--"} / cadence=${summary.cadence_rounds ?? 5} rounds`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 7).map((item) => {
    const status = item.status || "";
    const statusClass = status === "blocked_expected" ? "ok" : status === "blocked_missing_audit" ? "danger" : item.priority === "P1" ? "warn" : "ok";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(`${item.priority || "--"} / ${item.action || item.action_id || ""}`)}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.verification_command || ""}`)}</span>
        <span>${escapeHtml(item.acceptance_evidence || item.next_review || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No audit iteration actions</strong>
      <span>Run the independent GUI audit before the next optimization round.</span>
    </div>
  `);
}

function renderAuditScheduler(scheduler = {}) {
  const summary = scheduler.summary || {};
  const rows = scheduler.rows || [];
  const status = summary.status || "unknown";
  const dueStatus = summary.next_due_status || "unknown";
  const roundDueStatus = summary.next_round_audit_due_status || "unknown";
  const reportRequired = Boolean(summary.next_report_required || summary.next_flow_plan_required);
  const headerClass = reportRequired || dueStatus === "due_now" ? "warn" : status === "active" ? "ok" : "danger";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`${summary.cadence_rounds ?? 5}-round audit / ${roundDueStatus}`)}</strong>
      <span>${escapeHtml(`${summary.automation_id || "--"} / ${summary.automation_kind || "--"} / ${summary.rrule || "--"}`)}</span>
      <span>${escapeHtml(`round=${summary.current_round ?? 0} / remaining=${summary.rounds_until_next_audit ?? "--"} / fallback=${formatSchedulerAge(summary.last_audit_age_hours)}`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 8).map((item) => {
    const rowStatus = item.status || "";
    const statusClass = rowStatus === "ready" || rowStatus === "blocked_expected" ? "ok" : rowStatus === "missing" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(`${rowStatus || "--"} / ${item.value || ""}`)}</span>
        <span>${escapeHtml(item.evidence || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No audit scheduler data</strong>
      <span>The control API should expose gui-5h heartbeat status and latest audit age.</span>
    </div>
  `);
}

function formatSchedulerAge(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(2)}h` : "--";
}

function renderWorkflowTrace(trace = {}) {
  const summary = trace.summary || {};
  const rows = trace.rows || [];
  const headerClass = summary.live_trading_allowed ? "danger" : summary.current_status === "ready_to_run" ? "ok" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`${summary.current_workflow || "--"} / ${summary.current_status || "--"}`)}</strong>
      <span>${escapeHtml(`paper_only=${summary.paper_only ? "true" : "false"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
      <span>${escapeHtml(`${summary.evidence_storage_key || "--"} / ${summary.next_endpoint || ""}`)}</span>
    </div>
  `;
  const body = rows.slice(0, 9).map((item) => {
    const status = item.status || "";
    const statusClass = status === "blocked" ? "danger" : ["active", "ready", "publish_ready"].includes(status) ? "ok" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.trace_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.source_workflow || ""}`)}</span>
        <span>${escapeHtml(item.command || item.endpoint || "")}</span>
        <span>${escapeHtml(item.evidence || item.next_action || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No workflow trace</strong>
      <span>The control API must expose the active workflow, queued steps, evidence storage, verification gates, and live boundary.</span>
    </div>
  `);
}

function renderVerificationRunner(runner = {}, latest = null) {
  const summary = runner.summary || {};
  const rows = runner.rows || [];
  const header = `
    <div class="list-row ok">
      <strong>${escapeHtml(`Allowed gates ${summary.allowed ?? rows.length}`)}</strong>
      <span>${escapeHtml(`live_trading_allowed=${summary.live_trading_allowed === true ? "true" : "false"} / orders=false`)}</span>
      <span>${escapeHtml(summary.next_action || "Run a local verification gate and inspect the receipt.")}</span>
    </div>
  `;
  const body = rows.slice(0, 5).map((item) => `
    <div class="list-row verification-runner-row ${escapeHtml(item.allowed ? "warn" : "danger")}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(item.command || "")}</span>
      <div class="runner-row-actions">
        <button class="secondary-button verification-run-button" type="button" data-verification-gate="${escapeHtml(item.gate_id || "")}">Run</button>
        <span>${escapeHtml(item.endpoint || `/api/control/verification?gate_id=${item.gate_id || ""}`)}</span>
      </div>
    </div>
  `).join("");
  const receipt = latest ? `
    <div class="list-row ${escapeHtml(latest.status === "passed" ? "ok" : latest.status === "blocked" ? "danger" : "warn")}">
      <strong>${escapeHtml(`Latest ${latest.gate_id || "--"} / ${latest.status || "--"}`)}</strong>
      <span>${escapeHtml(`returncode=${latest.returncode ?? "--"} / ${latest.duration_seconds ?? "--"}s`)}</span>
      <span>${escapeHtml(latest.stdout_tail || latest.stderr_tail || latest.safety?.notice || "")}</span>
    </div>
  ` : `
    <div class="list-row warn">
      <strong>No local verification receipt</strong>
      <span>Run gui_compile first before publishing GUI changes.</span>
    </div>
  `;
  return header + (body || `
    <div class="list-row danger">
      <strong>No allowlisted gates</strong>
      <span>Verification runner is disabled until gate metadata is restored.</span>
    </div>
  `) + receipt;
}

function renderWorkspaceSync(sync = {}) {
  const summary = sync.summary || {};
  const rows = sync.rows || [];
  const status = summary.status || "unknown";
  const headerClass = status === "clean" ? "ok" : status === "dirty" ? "warn" : "danger";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Workspace / ${status}`)}</strong>
      <span>${escapeHtml(`${summary.current_branch || "--"} / ${summary.head || "--"}`)}</span>
      <span>${escapeHtml(`behind=${summary.behind ?? "--"} / ahead=${summary.ahead ?? "--"} / changed=${summary.changed_paths ?? "--"}`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 6).map((item) => {
    const rowStatus = item.status || "";
    const statusClass = rowStatus === "ready" || rowStatus === "clean" ? "ok" : rowStatus === "blocked" || rowStatus === "behind" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(`${rowStatus || "--"} / ${item.value || ""}`)}</span>
        <span>${escapeHtml(item.evidence || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No workspace sync status</strong>
      <span>Git branch, worktree, upstream, and sync policy should be visible before publishing.</span>
    </div>
  `);
}

function renderActionCenter(actionCenter = {}) {
  const summary = actionCenter.summary || {};
  const rows = actionCenter.rows || [];
  const headerClass = summary.live_trading_allowed
    ? "danger"
    : summary.runnable_actions > 0
      ? "ok"
      : rows.length > 0
        ? "warn"
        : "danger";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Next actions / ${summary.status || "--"}`))}</strong>
      <span>${escapeHtml(`runnable=${summary.runnable_actions ?? 0} / blocked=${summary.blocked_actions ?? 0}`)}</span>
      <span>${escapeHtml(zhConsoleText(summary.next_action || ""))}</span>
    </div>
  `;
  const body = rows.slice(0, 8).map((item) => {
    const priority = item.priority || "P2";
    const statusClass = item.runnable
      ? (priority === "P0" ? "danger" : priority === "P1" ? "warn" : "ok")
      : "warn";
    const button = item.runnable ? `
      <button
        class="ghost-button verification-run-button"
        type="button"
        data-action-workflow="${escapeHtml(item.workflow_id || "")}"
        data-action-verification-gate="${escapeHtml(item.verification_gate || "")}"
      >${escapeHtml(zhConsoleText(item.button_label || "Run"))}</button>
    ` : "";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(`${priority} / ${item.label || item.action_id || ""}`))}</strong>
        <span>${escapeHtml(zhConsoleText(`${item.status || "--"} / ${item.source || ""}`))}</span>
        <span>${escapeHtml(zhConsoleText(item.reason || ""))}</span>
        <span>${escapeHtml(item.command || "")}</span>
        <span>${button}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No action center rows</strong>
      <span>Run the control status API to derive the next safe GUI action.</span>
    </div>
  `);
}

function renderConsoleCommandDeck(
  activeOperationSpec = {},
  activeOperation = null,
  executionReceipts = [],
  verificationResult = null,
  safety = {},
) {
  const latestResearch = executionReceipts.find((item) => item.workflow_id === "research_backtest") || {};
  const latestPaper = executionReceipts.find((item) => item.workflow_id === "paper_simulation") || {};
  const current = activeOperation || {};
  const activeSpecSummary = activeOperationSpec.summary || {};
  const rows = [
    {
      label: "当前动作",
      status: current.status || activeSpecSummary.status || "idle",
      detail: current.label || activeSpecSummary.next_action || "等待选择操作控制台按钮",
      meta: current.detail || activeSpecSummary.supported_workflow_ids?.join(" / ") || "研究回测 / 信号快照 / 模拟盘 / 本地验证",
    },
    {
      label: "最近研究回执",
      status: latestResearch.status || "missing",
      detail: latestResearch.time || "还没有浏览器研究回执",
      meta: receiptMetricText(latestResearch),
    },
    {
      label: "最近模拟盘回执",
      status: latestPaper.status || "missing",
      detail: latestPaper.time || "还没有浏览器模拟盘回执",
      meta: receiptMetricText(latestPaper),
    },
    {
      label: "最近验证",
      status: verificationResult?.status || "not_run",
      detail: verificationResult?.gate_id || "可运行 GUI 编译、项目安全审计、同步预检",
      meta: verificationResult ? `returncode=${verificationResult.returncode ?? "--"}` : "verification_runner",
    },
    {
      label: "安全边界",
      status: safety.live_trading_allowed ? "danger" : "expected_block",
      detail: safety.live_trading_allowed ? "实盘通道异常开启" : "实盘、券商、账户读取、真实下单全部关闭",
      meta: safety.notice || "Research-to-paper only",
    },
  ];
  return rows.map((item) => {
    const statusClass = item.status === "completed" || item.status === "passed" || item.status === "expected_block"
      ? "ok"
      : item.status === "failed" || item.status === "danger"
        ? "danger"
        : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(`${item.label} / ${item.status}`))}</strong>
        <span>${escapeHtml(zhConsoleText(item.detail || ""))}</span>
        <span>${escapeHtml(zhConsoleText(item.meta || ""))}</span>
      </div>
    `;
  }).join("");
}

function receiptMetricText(receipt = {}) {
  const metrics = receipt.metrics || {};
  return [
    metrics.total_return != null ? `收益=${formatPercent(metrics.total_return)}` : "",
    metrics.sharpe != null ? `Sharpe=${formatDecimal(metrics.sharpe)}` : "",
    metrics.max_drawdown != null ? `回撤=${formatPercent(metrics.max_drawdown)}` : "",
    metrics.ending_equity != null ? `权益=${formatNumber(metrics.ending_equity)}` : "",
  ].filter(Boolean).join(" / ") || "等待运行后写入回执";
}

function renderWorkflowPreflight(preflight = {}) {
  const summary = preflight.summary || {};
  const rows = preflight.rows || [];
  const headerClass = summary.live_trading_allowed
    ? "danger"
    : (summary.blocked_count ?? 0) > 1
      ? "warn"
      : "ok";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Run preflight / ${summary.status || "--"}`))}</strong>
      <span>${escapeHtml(`runnable=${summary.runnable_count ?? 0} / blocked=${summary.blocked_count ?? 0}`)}</span>
      <span>${escapeHtml(zhConsoleText(summary.next_action || ""))}</span>
    </div>
  `;
  const body = rows.slice(0, 6).map((item) => {
    const status = item.status || "";
    const statusClass = item.live_trading_allowed
      ? "danger"
      : status === "blocked"
        ? "danger"
        : item.runnable
          ? "ok"
          : "warn";
    const checks = Array.isArray(item.checks)
      ? item.checks.map((check) => `${check.check_id || check.label || "check"}=${check.status || "--"}`).join(" / ")
      : "";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(`${item.label || item.workflow_id || ""} / ${status || "--"}`))}</strong>
        <span>${escapeHtml(zhConsoleText(`mode=${item.mode || "--"} / runnable=${item.runnable ? "true" : "false"}`))}</span>
        <span>${escapeHtml(checks)}</span>
        <span>${escapeHtml(workflowPreflightEndpointSummary(item))}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No workflow preflight rows</strong>
      <span>Control status should expose run readiness before workflow buttons are used.</span>
    </div>
  `);
}

function workflowPreflightEndpointSummary(item = {}) {
  const endpoint = item.endpoint || "";
  if (endpoint.startsWith("/api/control/verification")) return endpoint;
  if (endpoint.startsWith("/api/")) return endpoint.split("?")[0];
  const command = item.command || "";
  if (command.startsWith("GET /api/control/verification")) return command.replace("GET ", "");
  if (command.startsWith("GET /api/")) return command.replace("GET ", "").split("?")[0];
  return command || item.reason || "";
}

function renderProcessMonitor(monitor = {}) {
  const summary = monitor.summary || {};
  const rows = monitor.rows || [];
  const status = summary.status || "unknown";
  const headerClass = status === "observing" ? "ok" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Processes / ${status}`)}</strong>
      <span>${escapeHtml(`pid=${summary.current_pid ?? "--"} / related=${summary.related_processes ?? "--"} / jobs=${summary.running_jobs ?? "--"}`)}</span>
      <span>${escapeHtml(`gui=${summary.gui_server_detected ? "detected" : "not detected"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 7).map((item) => {
    const role = item.role || "";
    const statusClass = item.live_trading_allowed ? "danger" : role === "current_snapshot" || role === "gui_server" ? "ok" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(`${item.label || item.check_id || ""} / ${item.process_id ?? "--"}`)}</strong>
        <span>${escapeHtml(`${item.status || "--"} / ${role || "--"} / ${item.name || ""}`)}</span>
        <span>${escapeHtml(item.command || "")}</span>
        <span>${escapeHtml(item.evidence || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No process monitor data</strong>
      <span>The control API should expose current GUI, audit, smoke, and research processes.</span>
    </div>
  `);
}

function renderActiveOperation(spec = {}, active = null) {
  const summary = spec.summary || {};
  const rows = spec.rows || [];
  const operation = active || {};
  const isRunning = operation.status === "running";
  const statusClass = isRunning ? "warn" : operation.status === "failed" ? "danger" : operation.status === "completed" ? "ok" : "muted";
  const duration = operation.started_at
    ? `${Math.max(0, Math.round(((operation.finished_at ? Date.parse(operation.finished_at) : Date.now()) - Date.parse(operation.started_at)) / 1000))}s`
    : "--";
  const header = `
    <div class="list-row ${escapeHtml(statusClass)}">
      <strong>${escapeHtml(operation.label || (isRunning ? "Running" : "No active operation"))}</strong>
      <span>${escapeHtml(`${operation.status || "waiting"} / ${operation.workflow_id || "browser_runtime"} / ${duration}`)}</span>
      <span>${escapeHtml(operation.detail || summary.next_action || "")}</span>
    </div>
  `;
  const supported = (summary.supported_workflow_ids || []).join(" / ");
  const body = [
    `
    <div class="list-row ok">
      <strong>${escapeHtml("Tracked workflows")}</strong>
      <span>${escapeHtml(supported || "research_backtest / signal_snapshot / paper_simulation / verification_runner")}</span>
      <span>${escapeHtml(summary.receipt_source || "browser receipts")}</span>
    </div>
    `,
  ].concat(rows.slice(0, 3).map((item) => `
    <div class="list-row ${escapeHtml(item.status === "blocked_live" ? "danger" : item.status === "waiting" ? "warn" : "ok")}">
      <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
      <span>${escapeHtml(`${item.status || "--"} / ${item.source || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
    </div>
  `)).join("");
  return header + body;
}

function renderOperationLedger(ledger = {}) {
  const summary = ledger.summary || {};
  const rows = ledger.rows || [];
  const hasRows = rows.length > 0;
  const header = `
    <div class="list-row ${escapeHtml(hasRows ? "ok" : "warn")}">
      <strong>${escapeHtml(hasRows ? "Recent server operation" : "No server operation logged")}</strong>
      <span>${escapeHtml(`entries=${summary.entry_count ?? 0} / latest=${summary.latest_workflow_id || "--"} / ${summary.latest_status || "--"}`)}</span>
      <span>${escapeHtml(`path=${summary.path || "data/reports/gui_operation_ledger/gui_operation_ledger.json"}`)}</span>
      <span>${escapeHtml(`live=${summary.live_trading_allowed ? "enabled" : "disabled"} / orders=${summary.order_placement_allowed ? "enabled" : "disabled"}`)}</span>
    </div>
  `;
  const body = rows.slice(0, 6).map((item) => {
    const status = item.status || "";
    const statusClass = status === "completed" || status === "passed"
      ? "ok"
      : status === "failed" || status === "blocked"
        ? "danger"
        : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.workflow_id || "")}</strong>
        <span>${escapeHtml(`${item.recorded_at || "--"} / ${status || "--"} / ${item.workflow_id || "--"}`)}</span>
        <span>${escapeHtml(item.request_summary || item.command || "")}</span>
        <span>${escapeHtml(item.metric_summary || item.stage || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>Awaiting workflow receipt</strong>
      <span>Run research, signal, paper, or verification from this GUI to create a server-side receipt.</span>
    </div>
  `);
}

function renderTradeModeControl(control = {}) {
  const summary = control.summary || {};
  const rows = control.rows || [];
  const header = `
    <div class="list-row ${escapeHtml(summary.live_trading_allowed ? "danger" : "ok")}">
      <strong>${escapeHtml(`Default mode: ${summary.default_mode || "research"}`)}</strong>
      <span>${escapeHtml(`paper_sim=${summary.paper_simulation_available ? "available" : "blocked"} / live=${summary.live_trading_allowed ? "enabled" : "blocked"}`)}</span>
      <span>${escapeHtml(summary.next_action || "Use research and paper simulation modes only.")}</span>
    </div>
  `;
  const body = rows.map((item) => {
    const permissions = item.permissions || {};
    const status = item.status || "";
    const statusClass = status === "ready"
      ? "ok"
      : status === "blocked"
        ? "danger"
        : "warn";
    const permissionText = [
      permissions.research_api_allowed ? "research_api" : "",
      permissions.paper_simulation_allowed ? "paper_sim" : "",
      permissions.order_placement_allowed ? "orders" : "orders=false",
      permissions.live_trading_allowed ? "live" : "live=false",
    ].filter(Boolean).join(" / ");
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.mode_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${permissionText}`)}</span>
        <span>${escapeHtml(item.entrypoint || "")}</span>
        <span>${escapeHtml(item.guardrail || item.scope || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No mode rows</strong>
      <span>The control API should expose research, paper simulation, and live trading mode rows.</span>
    </div>
  `);
}

function renderStartupHealth(health = {}) {
  const summary = health.summary || {};
  const rows = health.rows || [];
  const ready = summary.status === "ready";
  const headerClass = ready ? "ok" : summary.missing_required ? "danger" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(ready ? "Local startup ready" : "Startup evidence required")}</strong>
      <span>${escapeHtml(`status=${summary.status || "--"} / browser=${summary.browser_smoke_ready ? "ready" : "missing"}`)}</span>
      <span>${escapeHtml(`${summary.control_status_endpoint || "/api/control/status"} / ${summary.next_action || ""}`)}</span>
    </div>
  `;
  const body = rows.slice(0, 6).map((item) => {
    const status = item.status || "";
    const statusClass = status === "ready" ? "ok" : status === "missing_required" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.command || ""}`)}</span>
        <span>${escapeHtml(item.evidence || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No startup health rows</strong>
      <span>Run the local GUI startup and browser smoke before operator use.</span>
    </div>
  `);
}

function renderBacktestProvenance(provenance = {}) {
  const summary = provenance.summary || {};
  const rows = provenance.rows || [];
  const headerClass = summary.status === "ready" ? "ok" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`${summary.market || "--"} / ${summary.factor || "--"}`)}</strong>
      <span>${escapeHtml(`paper_only=${summary.paper_only ? "true" : "false"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
      <span>${escapeHtml(summary.research_endpoint || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 7).map((item) => {
    const status = item.status || "";
    const statusClass = status === "ready" ? "ok" : status === "blocked_live" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(status || "--")}</span>
        <span>${escapeHtml(item.detail || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No backtest provenance</strong>
      <span>The control API must expose source, parameter, endpoint, output, and safety provenance for each backtest.</span>
    </div>
  `);
}

function renderResultEvidence(evidence = {}) {
  const summary = evidence.summary || {};
  const rows = evidence.rows || [];
  const headerClass = summary.live_trading_allowed ? "danger" : summary.status === "ready" ? "ok" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Result evidence / ${summary.status || "--"}`)}</strong>
      <span>${escapeHtml(`paper_only=${summary.paper_only ? "true" : "false"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
      <span>${escapeHtml(summary.next_action || summary.research_endpoint || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 7).map((item) => {
    const status = item.status || "";
    const statusClass = status === "browser_local" || status === "ready" ? "ok" : status === "blocked_live" ? "danger" : "warn";
    const metricText = Array.isArray(item.metric_keys) ? item.metric_keys.join(", ") : "";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.source_workflow || ""}`)}</span>
        <span>${escapeHtml(metricText || "")}</span>
        <span>${escapeHtml(item.command || "")}</span>
        <span>${escapeHtml(item.detail || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No result evidence</strong>
      <span>Run research, signals, or paper simulation to connect result metrics to workflow receipts.</span>
    </div>
  `);
}

function renderPaperReadiness(
  readiness = {},
  gate = {},
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  executionReceipts = [],
  researchRequest = {},
  paperRequest = {},
  safety = {},
) {
  const summary = readiness.summary || {};
  const rows = readiness.rows || [];
  const evaluated = evaluateBacktestGateRows(
    gate,
    metrics,
    benchmark,
    paperMetrics,
    executionReceipts,
    researchRequest,
    paperRequest,
    safety,
  );
  const nonLiveGateRows = evaluated.filter(({ item }) => item.gate_id !== "live_boundary");
  const metricGateRows = nonLiveGateRows.filter(({ item }) => item.gate_id !== "execution_receipts");
  const receiptGate = evaluated.find(({ item }) => item.gate_id === "execution_receipts") || {};
  const liveGate = evaluated.find(({ item }) => item.gate_id === "live_boundary") || {};
  const metricFailures = metricGateRows.filter((row) => row.result.status === "failed").length;
  const metricAwaiting = metricGateRows.filter((row) => row.result.status === "awaiting_metric").length;
  const metricPassed = metricGateRows.filter((row) => row.result.status === "passed").length;
  const requiredWorkflows = summary.required_workflows || [];
  const serverReceipts = Number(summary.current_receipts || 0);
  const requiredServerReceipts = requiredWorkflows.length || 0;
  const browserReceipts = Number(receiptGate.value || 0);
  const requiredBrowserReceipts = Number(receiptGate.threshold || requiredServerReceipts || 0);
  const serverReady = requiredServerReceipts > 0 && serverReceipts >= requiredServerReceipts;
  const browserReady = requiredBrowserReceipts > 0 && browserReceipts >= requiredBrowserReceipts;
  const liveBlockedExpected = liveGate.result?.status === "blocked_expected";
  const preflightReviewCount = Number((rows.find((item) => item.check_id === "preflight_review") || {}).review_count || 0);
  const candidateReady = (
    metricGateRows.length > 0
    && metricFailures === 0
    && metricAwaiting === 0
    && serverReady
    && browserReady
    && preflightReviewCount === 0
    && liveBlockedExpected
  );
  const dynamicStatus = candidateReady
    ? "paper_candidate"
    : metricFailures > 0
      ? "blocked"
      : metricAwaiting > 0
        ? "awaiting_metrics"
        : !browserReady
          ? "awaiting_browser_receipts"
          : !serverReady
            ? "awaiting_server_receipts"
            : preflightReviewCount > 0
              ? "review"
              : summary.status || "review";
  const headerClass = safety.live_trading_allowed || metricFailures > 0 ? "danger" : candidateReady ? "ok" : "warn";
  const serverReceiptText = `server_receipts=${serverReceipts}/${requiredServerReceipts || "--"}`;
  const browserReceiptText = `browser_receipts=${browserReceipts}/${requiredBrowserReceipts || "--"}`;
  const metricSummaryText = `metric_passed=${metricPassed}/${metricGateRows.length || "--"} / awaiting=${metricAwaiting} / failed=${metricFailures}`;
  const liveSummaryText = `live_boundary=${liveBlockedExpected ? "expected_block" : "review"}`;
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Paper readiness / ${dynamicStatus}`))}</strong>
      <span>${escapeHtml(`${serverReceiptText} / ${browserReceiptText} / candidate=${candidateReady ? "yes" : "no"}`)}</span>
      <span>${escapeHtml(`${metricSummaryText} / ${liveSummaryText}`)}</span>
    </div>
  `;
  const body = rows.slice(0, 7).map((item) => {
    let status = item.status || "";
    let detail = item.evidence || "";
    if (item.check_id === "metric_floor") {
      status = metricFailures > 0 ? "failed" : metricAwaiting > 0 ? "awaiting_metrics" : "passed";
      detail = `${metricSummaryText}; ${metricGateRows.map(({ item: gateItem, value, threshold, result }) => `${gateItem.gate_id}:${result.status} ${formatGateValue(value, gateItem.value_type)}/${formatGateValue(threshold, gateItem.value_type)}`).join(" / ")}`;
    }
    if (item.check_id === "paper_gate") {
      status = candidateReady ? "paper_candidate" : dynamicStatus;
      detail = `${serverReceiptText}; ${browserReceiptText}; ${metricSummaryText}; ${liveSummaryText}`;
    }
    if (item.check_id === "live_boundary" && liveBlockedExpected) {
      status = "expected_block";
    }
    const statusClass = status === "current" || status === "ready" || status === "passed" || status === "paper_candidate" || status === "expected_block"
      ? "ok"
      : status === "blocked" || status === "failed"
        ? "danger"
        : "warn";
    const metricText = Array.isArray(item.metric_keys) ? item.metric_keys.join(", ") : "";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(item.label || item.check_id || ""))}</strong>
        <span>${escapeHtml(zhConsoleText(`${status || "--"} / ${item.source_workflow || item.source || ""}`))}</span>
        <span>${escapeHtml(zhConsoleText(metricText || detail || ""))}</span>
        <span>${escapeHtml(zhConsoleText(item.next_action || item.current_command || ""))}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No paper readiness handoff</strong>
      <span>Run current research and paper workflows, then evaluate receipts, metrics, preflight, gates, and live boundary.</span>
    </div>
  `);
}

function renderLedgerEvidence(evidence = {}) {
  const summary = evidence.summary || {};
  const rows = evidence.rows || [];
  const headerClass = summary.live_trading_allowed
    ? "danger"
    : summary.status === "current"
      ? "ok"
      : summary.status === "partial"
        ? "warn"
        : "danger";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`Server receipts / ${summary.status || "--"}`)}</strong>
      <span>${escapeHtml(`current=${summary.current_receipts ?? 0} / missing_or_stale=${summary.missing_or_stale ?? 0}`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 6).map((item) => {
    const freshness = item.freshness || "";
    const statusClass = freshness === "current" ? "ok" : freshness === "failed_current" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(`${item.label || item.workflow_id || ""} / ${freshness || "--"}`)}</strong>
        <span>${escapeHtml(`${item.status || "--"} / matches=${item.matches_current_command ? "true" : "false"}`)}</span>
        <span>${escapeHtml(item.latest_recorded_at || "no server receipt")}</span>
        <span>${escapeHtml(item.latest_request_summary || item.current_command || "")}</span>
        <span>${escapeHtml(item.next_action || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No server ledger evidence</strong>
      <span>Run research, signals, paper, or verification from this GUI to create server-side receipts.</span>
    </div>
  `);
}

function renderBacktestGate(
  gate = {},
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  executionReceipts = [],
  researchRequest = {},
  paperRequest = {},
  safety = {},
) {
  const summary = gate.summary || {};
  const evaluated = evaluateBacktestGateRows(gate, metrics, benchmark, paperMetrics, executionReceipts, researchRequest, paperRequest, safety);
  const failures = evaluated.filter((row) => row.result.status === "failed").length;
  const awaiting = evaluated.filter((row) => row.result.status === "awaiting_metric").length;
  const passed = evaluated.filter((row) => row.result.status === "passed" || row.result.status === "blocked_expected").length;
  const headerClass = failures > 0 ? "danger" : awaiting > 0 ? "warn" : "ok";
  const headerStatus = failures > 0
    ? "blocked"
    : awaiting > 0
      ? "awaiting metrics"
      : summary.paper_candidate_allowed
        ? "paper candidate"
        : "metrics floor only";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Backtest gate / ${headerStatus}`))}</strong>
      <span>${escapeHtml(`passed=${passed} / awaiting=${awaiting} / failed=${failures}`)}</span>
      <span>${escapeHtml(`risk=${summary.risk_profile || "--"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
    </div>
  `;
  const body = evaluated.slice(0, 10).map(({ item, value, threshold, result }) => `
    <div class="list-row ${escapeHtml(result.statusClass)}">
      <strong>${escapeHtml(zhConsoleText(`${item.label || item.gate_id || ""}: ${formatGateValue(value, item.value_type)}`))}</strong>
      <span>${escapeHtml(zhConsoleText(`${result.status} / ${item.comparator || ""} ${formatGateValue(threshold, item.value_type)}`))}</span>
      <span>${escapeHtml(zhConsoleText(item.evidence || item.command || ""))}</span>
    </div>
  `).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No backtest gate</strong>
      <span>The control API must expose metric thresholds before paper-observation decisions are shown.</span>
    </div>
  `);
}

function evaluateBacktestGateRows(
  gate = {},
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  executionReceipts = [],
  researchRequest = {},
  paperRequest = {},
  safety = {},
) {
  const rows = gate.rows || [];
  return rows.map((item) => {
    const value = gateMetricValue(item, metrics, benchmark, paperMetrics, executionReceipts, researchRequest, paperRequest, safety);
    const threshold = gateThresholdValue(item, paperRequest);
    return { item, value, threshold, result: evaluateGateRow(item, value, threshold) };
  });
}

function gateMetricValue(
  item = {},
  metrics = {},
  benchmark = {},
  paperMetrics = {},
  executionReceipts = [],
  researchRequest = {},
  paperRequest = {},
  safety = {},
) {
  if (item.gate_id === "benchmark_relative_return") return benchmark.relative_return;
  if (item.gate_id === "paper_ending_equity") return paperMetrics.ending_equity;
  if (item.gate_id === "execution_receipts") return matchedExecutionReceiptCount(item, executionReceipts, researchRequest, paperRequest);
  if (item.gate_id === "live_boundary") return safety.live_trading_allowed;
  return metrics[item.metric_key];
}

function gateThresholdValue(item = {}, paperRequest = {}) {
  if (item.threshold_source === "paper_request.initial_cash") return paperInitialCash(paperRequest);
  return item.threshold;
}

function paperInitialCash(paperRequest = {}) {
  const requested = Number(paperRequest.initial_cash);
  if (Number.isFinite(requested)) return requested;
  const inputValue = Number(valueOf("paper-initial-cash") || 100000);
  return Number.isFinite(inputValue) ? inputValue : 100000;
}

function matchedExecutionReceiptCount(item = {}, executionReceipts = [], researchRequest = {}, paperRequest = {}) {
  const requiredWorkflows = Array.isArray(item.receipt_workflow_ids) && item.receipt_workflow_ids.length
    ? item.receipt_workflow_ids
    : ["research_backtest", "paper_simulation"];
  const matchedWorkflows = new Set();
  executionReceipts.forEach((receipt) => {
    const workflowId = receipt?.workflow_id || "";
    if (!requiredWorkflows.includes(workflowId)) return;
    const currentRequest = workflowId === "paper_simulation" ? paperRequest : researchRequest;
    if (item.requires_current_request && !requestMatchesReceipt(receipt, currentRequest)) return;
    matchedWorkflows.add(workflowId);
  });
  return matchedWorkflows.size;
}

function requestMatchesReceipt(receipt = {}, currentRequest = {}) {
  const receiptRequest = receipt.request || {};
  const keys = ["market", "factor_name", "top_n", "cost_bps", "start_date", "end_date", "initial_cash"];
  const comparableKeys = keys.filter((key) => (
    normalizeRequestValue(requestValue(receiptRequest, key)) !== ""
    || normalizeRequestValue(requestValue(currentRequest, key)) !== ""
  ));
  if (comparableKeys.length === 0) return false;
  return comparableKeys.every((key) => (
    normalizeRequestValue(requestValue(receiptRequest, key)) === normalizeRequestValue(requestValue(currentRequest, key))
  ));
}

function requestValue(request = {}, key) {
  if (key === "factor_name") return request.factor_name ?? request.factor;
  return request[key];
}

function normalizeRequestValue(value) {
  if (value == null || value === "") return "";
  if (Array.isArray(value)) return value.map((item) => normalizeRequestValue(item)).join(",");
  if (typeof value === "boolean") return value ? "true" : "false";
  const text = String(value).trim();
  if (!text) return "";
  if (text.includes(",")) {
    return text.split(",").map((item) => normalizeRequestValue(item)).join(",");
  }
  const lower = text.toLowerCase();
  if (lower === "true" || lower === "false") return lower;
  const number = Number(text);
  return Number.isFinite(number) ? String(number) : text;
}

function evaluateGateRow(item = {}, value, thresholdValue = item.threshold) {
  if (item.gate_id === "live_boundary") {
    return value === false
      ? { status: "blocked_expected", statusClass: "ok" }
      : { status: "failed", statusClass: "danger" };
  }
  const number = Number(value);
  if (value == null || value === "" || !Number.isFinite(number)) {
    return { status: "awaiting_metric", statusClass: "warn" };
  }
  if (item.gate_id === "execution_receipts" && number === 0) {
    return { status: "awaiting_metric", statusClass: "warn" };
  }
  const threshold = Number(thresholdValue);
  let passed = false;
  if (item.comparator === ">=") passed = number >= threshold;
  if (item.comparator === ">") passed = number > threshold;
  if (item.comparator === "<=") passed = number <= threshold;
  if (item.comparator === "<") passed = number < threshold;
  if (item.comparator === "==") passed = value === item.threshold;
  return passed ? { status: "passed", statusClass: "ok" } : { status: "failed", statusClass: "danger" };
}

function formatGateValue(value, valueType) {
  if (value == null || value === "") return "--";
  if (valueType === "percent") return formatPercent(value);
  if (valueType === "decimal") return formatDecimal(value);
  if (valueType === "currency") return formatNumber(value);
  if (valueType === "boolean") return String(Boolean(value));
  return formatNumber(value);
}

function renderReleaseReadiness(readiness = {}) {
  const summary = readiness.summary || {};
  const rows = readiness.rows || [];
  const headerClass = summary.push_ready ? "ok" : summary.missing_required ? "danger" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(summary.push_ready ? "Push ready" : "Manual verification required")}</strong>
      <span>${escapeHtml(`evidence=${summary.evidence_ready ? "ready" : "missing"} / manual=${summary.manual_required ?? "--"} / missing=${summary.missing_required ?? "--"}`)}</span>
      <span>${escapeHtml(summary.next_action || "")}</span>
    </div>
  `;
  const body = rows.slice(0, 8).map((item) => {
    const status = item.status || "";
    const statusClass = status === "passed_evidence" || status === "blocked_expected" ? "ok" : status === "missing_required" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(status || "--")}</span>
        <span>${escapeHtml(item.evidence || item.command || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>No release readiness rows</strong>
      <span>Run the control-center snapshot to populate local release gates.</span>
    </div>
  `);
}

function loadRunHistory(spec = {}) {
  const storageKey = spec.storage_key || RUN_HISTORY_STORAGE_KEY;
  const limit = Number(spec.max_entries || RUN_HISTORY_LIMIT);
  try {
    const raw = window.localStorage?.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, limit) : [];
  } catch (_error) {
    return [];
  }
}

function saveRunHistory(rows, spec = {}) {
  const storageKey = spec.storage_key || RUN_HISTORY_STORAGE_KEY;
  const limit = Number(spec.max_entries || RUN_HISTORY_LIMIT);
  state.runHistory = rows.slice(0, limit);
  try {
    window.localStorage?.setItem(storageKey, JSON.stringify(state.runHistory));
  } catch (_error) {
    // Local history should never block the workflow action.
  }
}

function appendRunHistory(entry) {
  const spec = state.controlCenter?.run_history || {};
  const nextEntry = {
    time: new Date().toISOString(),
    workflow_id: entry.workflow_id || "workflow",
    label: entry.label || entry.workflow_id || "Workflow",
    status: entry.status || "completed",
    detail: entry.detail || "",
  };
  saveRunHistory([nextEntry].concat(loadRunHistory(spec)), spec);
  renderRunHistory(spec);
  renderBeginnerProgress();
  return nextEntry;
}

function loadExecutionReceipts(spec = {}) {
  const storageKey = spec.storage_key || EXECUTION_RECEIPT_STORAGE_KEY;
  const limit = Number(spec.max_entries || EXECUTION_RECEIPT_LIMIT);
  try {
    const raw = window.localStorage?.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, limit) : [];
  } catch (_error) {
    return [];
  }
}

function saveExecutionReceipts(rows, spec = {}) {
  const storageKey = spec.storage_key || EXECUTION_RECEIPT_STORAGE_KEY;
  const limit = Number(spec.max_entries || EXECUTION_RECEIPT_LIMIT);
  state.executionReceipts = rows.slice(0, limit);
  try {
    window.localStorage?.setItem(storageKey, JSON.stringify(state.executionReceipts));
  } catch (_error) {
    // Execution receipts are local evidence only; storage failures should not block a workflow.
  }
}

function appendExecutionReceipt(receipt) {
  if (!receipt) return null;
  const spec = state.controlCenter?.execution_receipts || {};
  const nextReceipt = {
    time: new Date().toISOString(),
    status: "completed",
    safety: "research-to-paper only; no broker, account, or order side effects",
    ...receipt,
  };
  saveExecutionReceipts([nextReceipt].concat(loadExecutionReceipts(spec)), spec);
  renderExecutionReceipts(spec);
  renderControlCenter();
  return nextReceipt;
}

function renderRunHistory(spec = {}) {
  const rows = loadRunHistory(spec);
  state.runHistory = rows;
  const target = byId("control-run-history");
  if (!target) return;
  if (rows.length === 0) {
    target.innerHTML = `
      <div class="list-row warn">
        <strong>No local run history</strong>
        <span>${escapeHtml(spec.empty_state || "Run a local workflow to record it in this browser.")}</span>
      </div>
    `;
    return;
  }
  target.innerHTML = rows.map((item) => {
    const status = item.status || "";
    const statusClass = status === "completed" ? "ok" : status === "failed" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.workflow_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.time || "--"}`)}</span>
        <span>${escapeHtml(item.detail || "")}</span>
      </div>
    `;
  }).join("");
}

function renderExecutionReceipts(spec = {}) {
  const rows = loadExecutionReceipts(spec);
  state.executionReceipts = rows;
  const target = byId("control-execution-receipts");
  if (!target) return;
  if (rows.length === 0) {
    target.innerHTML = `
      <div class="list-row warn">
        <strong>No execution receipts</strong>
        <span>${escapeHtml(spec.empty_state || "Run research, signals, or paper simulation to record a structured receipt.")}</span>
      </div>
    `;
    return;
  }
  target.innerHTML = rows.map((item) => {
    const metrics = item.metrics || {};
    const request = item.request || {};
    const statusClass = item.status === "completed" ? "ok" : item.status === "failed" ? "danger" : "warn";
    const metricText = [
      metrics.total_return != null ? `return=${formatPercent(metrics.total_return)}` : "",
      metrics.sharpe != null ? `sharpe=${formatDecimal(metrics.sharpe)}` : "",
      metrics.max_drawdown != null ? `dd=${formatPercent(metrics.max_drawdown)}` : "",
      metrics.ending_equity != null ? `equity=${formatNumber(metrics.ending_equity)}` : "",
      metrics.target_count != null ? `targets=${formatNumber(metrics.target_count)}` : "",
    ].filter(Boolean).join(" / ");
    const requestText = [
      request.market,
      request.factor_name || request.factor,
      request.top_n != null ? `top_n=${request.top_n}` : "",
      request.cost_bps != null ? `cost=${request.cost_bps}bps` : "",
    ].filter(Boolean).join(" / ");
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.workflow_id || "")}</strong>
        <span>${escapeHtml(`${item.time || "--"} / ${requestText || "--"}`)}</span>
        <span>${escapeHtml(metricText || item.decision || item.safety || "")}</span>
        <span>${escapeHtml(item.safety || "")}</span>
      </div>
    `;
  }).join("");
}

function researchReceipt(result = {}) {
  const request = result.request || {};
  const metrics = result.metrics || {};
  const benchmark = result.benchmark_metrics || {};
  const decision = result.decision || {};
  return {
    workflow_id: "research_backtest",
    label: "Research backtest receipt",
    request: {
      market: request.market,
      factor_name: request.factor_name,
      top_n: request.top_n,
      cost_bps: request.cost_bps,
      start_date: request.start_date,
      end_date: request.end_date,
    },
    metrics: {
      total_return: metrics.total_return,
      annualized_return: metrics.annualized_return,
      sharpe: metrics.sharpe,
      max_drawdown: metrics.max_drawdown,
      win_rate: metrics.win_rate,
      trade_count: metrics.trade_count,
      relative_return: benchmark.relative_return,
    },
    decision: decision.decision_status || result.data_mode || "completed",
    safety: "research calculation only; no broker, account, or order side effects",
  };
}

function signalReceipt(result = {}) {
  const request = result.request || {};
  const targets = result.targets || [];
  return {
    workflow_id: "signal_snapshot",
    label: "Advisory signal receipt",
    request: {
      market: request.market,
      factor_name: request.factor_name,
      top_n: request.top_n,
      as_of_date: request.as_of_date,
    },
    metrics: {
      target_count: targets.length,
      target_gross_exposure: result.target_gross_exposure,
      rebalance_count: (result.rebalance_plan || []).length,
    },
    decision: "advisory_only",
    safety: "advisory targets only; executable=false and no order routing",
  };
}

function paperReceipt(result = {}) {
  const request = result.request || {};
  const metrics = result.metrics || {};
  return {
    workflow_id: "paper_simulation",
    label: "Paper simulation receipt",
    request: {
      market: request.market,
      factor_name: request.factor_name,
      top_n: request.top_n,
      start_date: request.start_date,
      end_date: request.end_date,
      initial_cash: request.initial_cash,
    },
    metrics: {
      ending_equity: metrics.ending_equity,
      total_return: metrics.total_return,
      max_drawdown: metrics.max_drawdown,
      guard_event_count: metrics.guard_event_count,
      fill_count: (result.fills || []).length,
    },
    decision: "local_simulation_only",
    safety: "local simulated fills only; no broker, account, or order side effects",
  };
}

async function runVerificationGate(gateId, button = null) {
  if (!gateId) return;
  const label = button?.textContent || "";
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "verification_runner",
    label: `运行本地验证闸门：${gateId}`,
    endpoint: `/api/control/verification?gate_id=${gateId}`,
    request: { gate_id: gateId },
  });
  if (!confirmed) return;
  const activeOperation = beginActiveOperation({
    workflow_id: "verification_runner",
    label: `Run verification gate ${gateId}`,
    detail: `/api/control/verification?gate_id=${gateId}`,
    safety: "allowlisted local verification only; no broker, account, order, or live-trading side effects",
  });
  if (button) {
    button.disabled = true;
    button.textContent = "运行中";
  }
  byId("run-state-label").textContent = "运行中";
  try {
    const result = await fetchJson(`/api/control/verification?gate_id=${encodeURIComponent(gateId)}`);
    state.verificationResult = result;
    finishActiveOperation(activeOperation, result.status === "passed" ? "completed" : "failed", `returncode=${result.returncode ?? "--"} / ${result.status || "--"}`);
    renderControlCenter();
    showToast(`Verification ${result.status || "finished"}: ${gateId}`, result.status !== "passed");
  } catch (error) {
    state.verificationResult = {
      stage: "gui_verification_result",
      gate_id: gateId,
      status: "failed",
      returncode: null,
      duration_seconds: 0,
      stdout_tail: "",
      stderr_tail: error.message || "Verification request failed",
      safety: { live_trading_allowed: false, order_placement_allowed: false },
    };
    finishActiveOperation(activeOperation, "failed", error.message || "Verification request failed");
    renderControlCenter();
    showToast(error.message || "Verification request failed", true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = label || "Run";
    }
    byId("run-state-label").textContent = "就绪";
  }
}

async function runActionCenterWorkflow(workflowId, button = null) {
  if (!workflowId) return;
  const original = button?.textContent || "";
  if (button) {
    button.disabled = true;
    button.textContent = "运行中";
  }
  try {
    if (workflowId === "research_backtest") {
      await runResearch();
      return;
    }
    if (workflowId === "signal_snapshot") {
      await runSignals();
      return;
    }
    if (workflowId === "paper_simulation") {
      await runPaper();
      return;
    }
    if (workflowId === "startup_workflows") {
      await runStartupWorkflows();
      return;
    }
    if (workflowId === "verification_runner") {
      await runVerificationGate(button?.dataset.actionVerificationGate || "gui_compile", button);
      return;
    }
    showToast(`Unsupported action workflow: ${workflowId}`, true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original || "Run";
    }
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

function beginActiveOperation(operation = {}) {
  const now = new Date().toISOString();
  state.activeOperation = {
    operation_id: operation.operation_id || `${operation.workflow_id || "operation"}-${Date.now()}`,
    workflow_id: operation.workflow_id || "browser_operation",
    label: operation.label || "Browser operation",
    status: "running",
    started_at: now,
    finished_at: "",
    detail: operation.detail || "",
    safety: operation.safety || "research-to-paper only; no broker, account, or order side effects",
  };
  renderControlCenter();
  return state.activeOperation;
}

function finishActiveOperation(operation = null, status = "completed", detail = "") {
  const current = operation || state.activeOperation;
  if (!current) return null;
  state.activeOperation = {
    ...current,
    status,
    finished_at: new Date().toISOString(),
    detail: detail || current.detail || "",
  };
  renderControlCenter();
  return state.activeOperation;
}

function operationForButton(buttonId) {
  const specs = {
    "run-research": {
      workflow_id: "research_backtest",
      label: "Run research backtest",
      detail: () => `${valueOf("market-select") || "ALL"} / ${valueOf("factor-select") || "momentum_2"} / top_n=${valueOf("research-top-n") || "2"}`,
      safety: "research calculation only; no broker, account, or order side effects",
    },
    "run-signals": {
      workflow_id: "signal_snapshot",
      label: "Generate advisory signal snapshot",
      detail: () => `${valueOf("market-select") || "ALL"} / top_n=${valueOf("signal-top-n") || "2"}`,
      safety: "advisory targets only; executable=false and no order routing",
    },
    "run-paper": {
      workflow_id: "paper_simulation",
      label: "Run local paper simulation",
      detail: () => `${valueOf("paper-market-select") || "ALL"} / top_n=${valueOf("paper-top-n") || "2"} / cash=${valueOf("paper-initial-cash") || "100000"}`,
      safety: "local simulated fills only; no broker, account, or order side effects",
    },
  };
  const spec = specs[buttonId];
  if (!spec) return null;
  return {
    ...spec,
    detail: typeof spec.detail === "function" ? spec.detail() : spec.detail,
  };
}

async function withBusy(buttonId, action, operation = null) {
  const button = byId(buttonId);
  const label = button.textContent;
  const activeOperationSpec = operation || operationForButton(buttonId);
  const activeOperation = activeOperationSpec ? beginActiveOperation(activeOperationSpec) : null;
  button.disabled = true;
  button.textContent = "运行中";
  byId("run-state-label").textContent = "运行中";
  try {
    await action();
    if (activeOperation) finishActiveOperation(activeOperation, "completed");
  } catch (error) {
    if (activeOperation) finishActiveOperation(activeOperation, "failed", error.message || "Operation failed");
    showToast(error.message || "运行失败", true);
  } finally {
    button.disabled = false;
    button.textContent = label;
    byId("run-state-label").textContent = "就绪";
  }
}

function showToast(message, isError = false) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2200);
}

function readyText(readiness) {
  if (!readiness) return "--";
  if (readiness.ready) return "ready";
  return (readiness.missing || []).join(" / ") || "not ready";
}

function byId(id) {
  return document.getElementById(id);
}

function valueOf(id) {
  return byId(id)?.value || "";
}

function setValue(id, value) {
  const element = byId(id);
  if (element) element.value = value;
}

function formatCell(value) {
  if (typeof value === "boolean") return escapeHtml(String(value));
  if (typeof value === "number") return escapeHtml(formatDecimal(value));
  return escapeHtml(String(value ?? ""));
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("en-US") : "--";
}

function formatDecimal(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : "--";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(2)}%` : "--";
}

function escapeHtml(value) {
  return String(zhConsoleText(value))
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeRawHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeSvg(value) {
  return escapeHtml(value);
}
