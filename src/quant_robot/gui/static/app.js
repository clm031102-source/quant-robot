const state = {
  snapshot: null,
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

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  await loadSnapshot();
  await loadProjectStatus();
  await loadDailyOps();
  await loadRiskCandidates();
  await loadConstrainedSearch();
  await loadPaperProfiles();
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
  await withBusy("run-daily-ops", async () => {
    state.dailyOps = await fetchJson(`/api/daily/ops?${params.toString()}`);
    state.riskCandidates = await fetchJson(`/api/risk/candidates?${riskParams.toString()}`);
    state.constrainedSearch = await fetchJson(`/api/risk/constrained-search?${constrainedParams.toString()}`);
    state.paperProfiles = await fetchJson(`/api/risk/paper-profiles?${profileParams.toString()}`);
    renderDailyOps();
    renderRiskCandidates();
    renderConstrainedSearch();
    renderPaperProfiles();
    renderDashboard();
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
  const riskCandidates = state.riskCandidates || {};
  const constrained = state.constrainedSearch || {};
  const profiles = state.paperProfiles || {};
  const candidate = project.selected_candidate || {};
  const dataGaps = project.data_gaps || {};
  const provider = project.provider_remediation || {};
  byId("dashboard-equity-source").textContent = state.research?.data_source || valueOf("data-source-select") || state.snapshot?.data_mode || "local";
  byId("dashboard-metrics").innerHTML = [
    metric("项目状态", project.overall_status || "--", `阻塞 ${project.blocker_count ?? "--"}`),
    metric("Daily Ops", dailyDecision.status || "--", dailyDecision.paper_trading_allowed ? "paper allowed" : "blocked"),
    metric("风险候选", riskCandidates.summary?.risk_eligible_candidates ?? "--", riskCandidates.selection_status || "selector"),
    metric("Frontier", constrained.summary?.frontier_candidates ?? "--", constrained.selection_status || "constrained search"),
    metric("Profiles", profiles.summary?.eligible_profiles ?? "--", profiles.selection_status || "paper optimizer"),
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
    ["Risk candidates", `${riskCandidates.selection_status || "--"} / eligible ${riskCandidates.summary?.risk_eligible_candidates ?? "--"}`, riskCandidates.selection_status === "risk_candidate_selected" ? "ok" : "warn"],
    ["Constrained frontier", `${constrained.summary?.frontier_candidates ?? "--"} near miss`, constrained.summary?.frontier_candidates > 0 ? "warn" : "muted"],
    ["Paper profiles", `${profiles.selection_status || "--"} / eligible ${profiles.summary?.eligible_profiles ?? "--"}`, profiles.selection_status === "paper_profile_selected" ? "ok" : "warn"],
    ["Promotion blockers", (state.promotion?.live_review_blockers || []).join(" / ") || "none", state.promotion?.live_review_allowed ? "ok" : "warn"],
    ["Tushare", readyText(state.snapshot?.readiness?.tushare), state.snapshot?.readiness?.tushare?.ready ? "ok" : "warn"],
    ["Parquet", readyText(state.snapshot?.readiness?.parquet), state.snapshot?.readiness?.parquet?.ready ? "ok" : "warn"],
    ["纸面权益", formatNumber(paperMetrics.ending_equity), state.paper ? "ok" : "muted"],
    ["保护事件", formatNumber(paperMetrics.guard_event_count), paperMetrics.guard_event_count > 0 ? "warn" : "muted"],
    ["安全边界", dashboard.risk_notice || "Research only", "danger"],
  ]);
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
  const status = decision.status || (daily.artifact_present ? "unknown" : "missing");
  const tag = byId("daily-ops-tag");
  if (tag) {
    tag.textContent = status;
    tag.classList.toggle("tag-warn", status !== "paper_ready");
  }
  byId("daily-ops-metrics").innerHTML = [
    metric("运营状态", status, daily.run_date || "latest artifact"),
    metric("主候选", candidate.case_id || "--", candidate.market || "--"),
    metric("建议票据", daily.ticket_count ?? 0, "advisory only"),
    metric("纸面允许", decision.paper_trading_allowed ? "true" : "false", "no broker"),
    metric("最大回撤", formatPercent(risk.max_equity_drawdown), "simulation"),
    metric("回撤阈值", formatPercent(riskPolicy.max_drawdown_limit), riskPolicy.max_drawdown_breached ? "breached" : "clear"),
  ].join("");
  byId("daily-ops-status").innerHTML = statusRows([
    ["Artifact", daily.artifact_present ? daily.source_path || "present" : "missing", daily.artifact_present ? "ok" : "warn"],
    ["Decision", status, status === "paper_ready" ? "ok" : "warn"],
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
    tag.classList.toggle("tag-warn", status !== "risk_candidate_selected");
  }
  byId("risk-candidate-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, status === "risk_candidate_selected" ? "ok" : "warn"],
    ["Eligible candidates", String(summary.risk_eligible_candidates ?? 0), summary.risk_eligible_candidates > 0 ? "ok" : "warn"],
    ["Paper matched", String(summary.paper_matched_candidates ?? 0), "muted"],
    ["Selected", selected.case_id || "none", selected.case_id ? "ok" : "warn"],
    ["Max drawdown limit", formatPercent(policy.max_drawdown_limit), "muted"],
    ["Live boundary", pack.live_boundary_allowed ? "allowed" : "blocked", "danger"],
  ]);
  byId("risk-candidate-action-table").innerHTML = tableRows(pack.next_actions || [], ["action", "reason", "local_only"]);
  byId("risk-candidate-table").innerHTML = tableRows(pack.candidates || [], [
    "screen_rank",
    "case_id",
    "risk_status",
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
    tag.classList.toggle("tag-warn", status !== "risk_candidate_selected");
  }
  byId("constrained-search-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, status === "risk_candidate_selected" ? "ok" : "warn"],
    ["Walk-forward accepted", `${summary.walk_forward_accepted ?? 0} / ${summary.walk_forward_cases ?? 0}`, summary.walk_forward_accepted > 0 ? "ok" : "warn"],
    ["Paper completed", String(summary.paper_completed ?? 0), summary.paper_completed > 0 ? "ok" : "warn"],
    ["Risk eligible", String(summary.risk_eligible_candidates ?? 0), summary.risk_eligible_candidates > 0 ? "ok" : "warn"],
    ["Frontier", String(summary.frontier_candidates ?? frontier.length), frontier.length > 0 ? "warn" : "muted"],
    ["Selected", selected.case_id || "none", selected.case_id ? "ok" : "warn"],
  ]);
  byId("constrained-frontier-table").innerHTML = tableRows(frontier, [
    "case_id",
    "paper_sharpe",
    "paper_sharpe_gap",
    "paper_max_drawdown",
    "paper_drawdown_headroom",
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
    tag.classList.toggle("tag-warn", status !== "paper_profile_selected");
  }
  byId("paper-profile-status").innerHTML = statusRows([
    ["Artifact", pack.artifact_present ? pack.source_path || "present" : "missing", pack.artifact_present ? "ok" : "warn"],
    ["Selection", status, status === "paper_profile_selected" ? "ok" : "warn"],
    ["Attempts", String(summary.profile_attempts ?? attempts.length), attempts.length > 0 ? "ok" : "warn"],
    ["Eligible profiles", String(summary.eligible_profiles ?? 0), summary.eligible_profiles > 0 ? "ok" : "warn"],
    ["Selected", selected.profile_id || "none", selected.profile_id ? "ok" : "warn"],
    ["Min Sharpe", formatDecimal(policy.min_paper_sharpe), "muted"],
    ["Max drawdown", formatPercent(policy.max_drawdown_limit), "muted"],
  ]);
  byId("paper-profile-attempt-table").innerHTML = tableRows(attempts, [
    "profile_id",
    "profile_status",
    "paper_sharpe",
    "paper_max_drawdown",
    "paper_total_return",
    "max_asset_weight",
    "max_drawdown_guard",
    "guard_cooldown_periods",
    "rejection_reasons",
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
