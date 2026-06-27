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
  runHistory: [],
  executionReceipts: [],
};

const titles = {
  dashboard: "总览",
  research: "因子研究",
  backtest: "回测报告",
  decision: "决策风控",
  signals: "信号快照",
  paper: "纸面模拟",
  daily: "Daily Ops",
  promotion: "Promotion Ops",
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
    factor: "liquidity_10",
    factorWindows: "5,10,20,60,120",
    startDate: "2026-01-01",
    endDate: "2026-05-21",
    signalDate: "2026-05-21",
    paperStartDate: "2026-01-01",
    paperEndDate: "2026-05-21",
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
    rebalanceInterval: "1",
  },
};

const RUN_HISTORY_STORAGE_KEY = "quant_robot.gui.run_history.v1";
const RUN_HISTORY_LIMIT = 20;
const EXECUTION_RECEIPT_STORAGE_KEY = "quant_robot.gui.execution_receipts.v1";
const EXECUTION_RECEIPT_LIMIT = 20;

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  await loadSnapshot();
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
  byId("data-source-select").addEventListener("change", () => {
    applySourcePreset(true);
  });
}

async function loadSnapshot() {
  state.snapshot = await fetchJson("/api/snapshot");
  byId("mode-pill").textContent = `${state.snapshot.data_mode} / local`;
  byId("data-mode-label").textContent = state.snapshot.data_mode || "local";
  byId("broker-status-label").textContent = state.snapshot.risk?.account_connected ? "connected" : "No broker";
  byId("run-state-label").textContent = "ready";
  fillFactorSelect(state.snapshot.available_factors || []);
  applySourcePreset(false);
  renderDashboard();
  renderDataCenter();
  renderLogs();
}

async function loadControlCenter() {
  state.controlCenter = await fetchJson("/api/control/status");
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
  setValue("rebalance-interval", preset.rebalanceInterval);
  if (force || !valueOf("market-select") || valueOf("market-select") === "ALL") {
    setValue("market-select", preset.market);
  }
  setValue("paper-market-select", valueOf("market-select") || preset.market);
  setFactorValue("factor-select", preset.factor);
  setFactorValue("paper-factor-select", preset.factor);
  byId("data-mode-label").textContent = source;
  byId("mode-pill").textContent = `${source} / local`;
}

function setFactorValue(id, value) {
  const select = byId(id);
  if (!select) return;
  if ([...select.options].some((option) => option.value === value)) {
    select.value = value;
  }
}

async function runStartupWorkflows() {
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
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor: valueOf("factor-select") || "momentum_2",
    factor_windows: valueOf("factor-windows"),
    top_n: valueOf("research-top-n") || "2",
    cost_bps: valueOf("research-cost-bps") || "5",
    start_date: valueOf("start-date"),
    end_date: valueOf("end-date"),
    rebalance_interval: valueOf("rebalance-interval") || "1",
    benchmark_asset_id: valueOf("benchmark-asset-id"),
    cash_annual_return: valueOf("cash-annual-return") || "0",
    regime_filter: byId("regime-filter").checked ? "true" : "false",
    regime_lookback: valueOf("regime-lookback") || "20",
    min_relative_return: valueOf("min-relative-return"),
    max_drawdown_limit: valueOf("max-drawdown-limit"),
  });
  addSourceParams(params);
  state.research = await fetchJson(`/api/research?${params.toString()}`);
  renderDashboard();
  renderFactorResearch();
  renderBacktest();
  renderDecision();
}

async function runResearch() {
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
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor: valueOf("factor-select") || "momentum_2",
    factor_windows: valueOf("factor-windows"),
    top_n: valueOf("signal-top-n") || "2",
    as_of_date: valueOf("signal-as-of"),
    max_asset_weight: valueOf("max-asset-weight") || "1",
    max_market_weight: valueOf("max-market-weight") || "1",
    max_gross_exposure: valueOf("max-gross-exposure") || "1",
    min_cash_weight: valueOf("min-cash-weight") || "0",
  });
  addSourceParams(params);
  state.signals = await fetchJson(`/api/signals?${params.toString()}`);
  renderSignals();
  renderDashboard();
}

async function runSignals() {
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
  const params = new URLSearchParams({
    market: valueOf("paper-market-select"),
    factor: valueOf("paper-factor-select") || "momentum_2",
    factor_windows: valueOf("factor-windows"),
    top_n: valueOf("paper-top-n") || "2",
    rebalance_interval: valueOf("rebalance-interval") || "1",
    start_date: valueOf("paper-start-date"),
    end_date: valueOf("paper-end-date"),
    initial_cash: valueOf("paper-initial-cash") || "100000",
    commission_bps: valueOf("paper-commission-bps") || "5",
    slippage_bps: valueOf("paper-slippage-bps") || "5",
    max_asset_weight: valueOf("paper-max-asset-weight") || "1",
    max_market_weight: "1",
    max_gross_exposure: "1",
    min_cash_weight: valueOf("paper-min-cash-weight") || "0",
    max_drawdown_guard: valueOf("paper-drawdown-guard"),
    guard_cooldown_periods: valueOf("paper-guard-cooldown") || "0",
  });
  addSourceParams(params);
  state.paper = await fetchJson(`/api/paper?${params.toString()}`);
  renderDashboard();
  renderPaper();
}

async function runPaper() {
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
  const backtest = control.backtest || {};
  const method = control.method || {};
  const workflows = control.workflows || [];
  const reportLinks = control.report_links || [];
  const verificationGates = control.verification_gates || [];
  const operatorChecklist = control.operator_checklist || {};
  const checklistItems = operatorChecklist.items || [];
  const executionPlan = control.execution_plan || {};
  const executionSteps = executionPlan.steps || [];
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
  const auditIterationPlan = control.audit_iteration_plan || {};
  const operatorTimeline = control.operator_timeline || {};
  const timelineEvents = operatorTimeline.events || [];
  const runHistorySpec = control.run_history || {};
  const executionReceiptSpec = control.execution_receipts || {};
  const runQueue = control.run_queue || {};
  const activeRun = runQueue.active || {};
  const queueSummary = runQueue.summary || {};
  const pendingRuns = runQueue.pending || [];
  const blockedRuns = runQueue.blocked || [];
  const safety = control.safety || {};
  const automation = control.automation || {};
  const metrics = state.research?.metrics || {};
  const benchmark = state.research?.benchmark_metrics || {};
  const paperMetrics = state.paper?.metrics || {};
  const statusTag = byId("control-center-status");
  if (statusTag) {
    statusTag.textContent = control.status || "loading";
    statusTag.classList.toggle("tag-warn", control.status !== "ready");
  }
  byId("control-work-status").innerHTML = statusRows([
    ["Machine", work.machine || "--", work.machine ? "ok" : "muted"],
    ["Task", work.task || "--", "muted"],
    ["Branch", work.branch || "--", work.branch ? "ok" : "warn"],
    ["Goal", work.goal || "--", "muted"],
  ]);
  byId("control-run-queue").innerHTML = statusRows([
    ["Active", activeRun.label || "--", activeRun.workflow_id ? "ok" : "muted"],
    ["Status", activeRun.status || "--", activeRun.status === "ready_to_run" ? "ok" : "warn"],
    ["Pending", `${queueSummary.pending ?? "--"} queued`, (queueSummary.pending ?? 0) > 0 ? "warn" : "muted"],
    ["Blocked", `${queueSummary.blocked ?? "--"} blocked`, (queueSummary.blocked ?? 0) > 0 ? "danger" : "ok"],
    ["Next", pendingRuns[0]?.label || blockedRuns[0]?.label || "--", pendingRuns.length ? "muted" : "warn"],
  ]);
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
      <span>${escapeHtml(`${auditSummary.cadence_hours ?? "--"}h cadence / ${auditSummary.automation_id || "audit automation"}`)}</span>
      <span>${escapeHtml(auditSummary.independent_audit_complete ? `Independent audit complete / ${auditSummary.independent_audit_verdict || "review"}` : "Independent 5h audit still required")}</span>
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
  byId("control-audit-iteration-plan").innerHTML = renderAuditIterationPlan(auditIterationPlan);
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
  byId("control-safety-boundary").innerHTML = statusRows([
    ["Paper", safety.paper_trading_allowed ? "allowed by gates" : "blocked until gates pass", safety.paper_trading_allowed ? "ok" : "warn"],
    ["Live", safety.live_trading_allowed ? "allowed" : "disabled", safety.live_trading_allowed ? "ok" : "danger"],
    ["Broker", safety.broker_connection_allowed ? "enabled" : "no connection", safety.broker_connection_allowed ? "ok" : "danger"],
    ["Orders", safety.order_placement_allowed ? "enabled" : "no order placement", safety.order_placement_allowed ? "ok" : "danger"],
  ]);
  byId("control-audit-cadence").innerHTML = statusRows([
    ["Cadence", automation.cadence || "--", "ok"],
    ["Audit", automation.name || "--", "muted"],
    ["Output", automation.expected_output || "--", "muted"],
    ["Boundary", safety.notice || "Research only", "danger"],
  ]);
  renderRunHistory(runHistorySpec);
  renderExecutionReceipts(executionReceiptSpec);
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
  byId("dashboard-equity-source").textContent = state.research?.data_source || valueOf("data-source-select") || state.snapshot?.data_mode || "local";
  byId("dashboard-metrics").innerHTML = [
    metric("项目状态", project.overall_status || "--", `阻塞 ${project.blocker_count ?? "--"}`),
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
    tag.textContent = status;
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
  return `<div class="metric-card"><small>${escapeHtml(label)}</small><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(meta || "")}</span></div>`;
}

function statusRows(rows) {
  return rows.map(([label, value, tone]) => `
    <div class="list-row ${escapeHtml(tone || "")}"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value || "")}</span></div>
  `).join("");
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

function renderAuditIterationPlan(plan = {}) {
  const summary = plan.summary || {};
  const rows = plan.rows || [];
  const headerClass = summary.active_actions > 0 ? "warn" : "ok";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(`${summary.audit_score ?? "--"} / ${summary.max_score ?? "--"} ${summary.source || "audit source"}`)}</strong>
      <span>${escapeHtml(`actions=${summary.active_actions ?? "--"} / cadence=${summary.cadence_hours ?? "--"}h`)}</span>
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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

async function withBusy(buttonId, action) {
  const button = byId(buttonId);
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "运行中";
  byId("run-state-label").textContent = "running";
  try {
    await action();
  } catch (error) {
    showToast(error.message || "运行失败", true);
  } finally {
    button.disabled = false;
    button.textContent = label;
    byId("run-state-label").textContent = "ready";
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
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeSvg(value) {
  return escapeHtml(value);
}
