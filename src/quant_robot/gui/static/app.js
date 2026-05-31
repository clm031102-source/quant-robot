const state = {
  snapshot: null,
  research: null,
  signals: null,
  paper: null,
};

const titles = {
  dashboard: "总览",
  research: "因子研究",
  backtest: "回测报告",
  decision: "决策风控",
  signals: "信号快照",
  paper: "纸面模拟",
  data: "数据中心",
  logs: "日志报告",
};

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  await loadSnapshot();
  await runResearch();
  await runSignals();
  await runPaper();
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
    });
  });
}

function bindActions() {
  byId("run-research").addEventListener("click", runResearch);
  byId("run-signals").addEventListener("click", runSignals);
  byId("run-paper").addEventListener("click", runPaper);
}

async function loadSnapshot() {
  state.snapshot = await fetchJson("/api/snapshot");
  byId("mode-pill").textContent = `${state.snapshot.data_mode} / local`;
  fillFactorSelect(state.snapshot.available_factors || []);
  renderDashboard();
  renderDataCenter();
  renderLogs();
}

async function runResearch() {
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor: valueOf("factor-select") || "momentum_2",
    top_n: valueOf("research-top-n") || "2",
    cost_bps: valueOf("research-cost-bps") || "5",
    start_date: valueOf("start-date"),
    end_date: valueOf("end-date"),
    benchmark_asset_id: valueOf("benchmark-asset-id"),
    cash_annual_return: valueOf("cash-annual-return") || "0",
    regime_filter: byId("regime-filter").checked ? "true" : "false",
    regime_lookback: valueOf("regime-lookback") || "20",
    min_relative_return: valueOf("min-relative-return"),
    max_drawdown_limit: valueOf("max-drawdown-limit"),
  });
  await withBusy("run-research", async () => {
    state.research = await fetchJson(`/api/research/demo?${params.toString()}`);
    renderDashboard();
    renderFactorResearch();
    renderBacktest();
    renderDecision();
    showToast("研究结果已更新");
  });
}

async function runSignals() {
  const params = new URLSearchParams({
    market: valueOf("market-select"),
    factor: valueOf("factor-select") || "momentum_2",
    top_n: valueOf("signal-top-n") || "2",
    as_of_date: valueOf("signal-as-of"),
    max_asset_weight: valueOf("max-asset-weight") || "1",
    max_market_weight: valueOf("max-market-weight") || "1",
    max_gross_exposure: valueOf("max-gross-exposure") || "1",
    min_cash_weight: valueOf("min-cash-weight") || "0",
  });
  await withBusy("run-signals", async () => {
    state.signals = await fetchJson(`/api/signals/demo?${params.toString()}`);
    renderSignals();
    renderDashboard();
    showToast("信号快照已生成");
  });
}

async function runPaper() {
  const params = new URLSearchParams({
    market: valueOf("paper-market-select"),
    factor: valueOf("paper-factor-select") || "momentum_2",
    top_n: valueOf("paper-top-n") || "2",
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
  await withBusy("run-paper", async () => {
    state.paper = await fetchJson(`/api/paper/demo?${params.toString()}`);
    renderDashboard();
    renderPaper();
    showToast("纸面模拟已更新");
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
  byId("dashboard-metrics").innerHTML = [
    metric("策略数量", dashboard.strategy_count ?? 0, "local"),
    metric("总收益", formatPercent(metrics.total_return), "research"),
    metric("相对基准", formatPercent(benchmark.relative_return), "Phase 2.6"),
    metric("准入状态", decision.decision_status || "--", "research gate"),
  ].join("");
  byId("dashboard-equity").innerHTML = multiLineChart([
    { label: "策略", color: "#007f86", rows: state.research?.equity_curve || [], yKey: "equity" },
    { label: "基准", color: "#b86b24", rows: state.research?.benchmark_curve || [], yKey: "benchmark_equity" },
  ]);
  byId("dashboard-status").innerHTML = statusRows([
    ["Tushare", readyText(state.snapshot?.readiness?.tushare), state.snapshot?.readiness?.tushare?.ready ? "ok" : "warn"],
    ["Parquet", readyText(state.snapshot?.readiness?.parquet), state.snapshot?.readiness?.parquet?.ready ? "ok" : "warn"],
    ["纸面权益", formatNumber(paperMetrics.ending_equity), state.paper ? "ok" : "muted"],
    ["保护事件", formatNumber(paperMetrics.guard_event_count), paperMetrics.guard_event_count > 0 ? "warn" : "muted"],
    ["安全边界", dashboard.risk_notice || "Research only", "danger"],
  ]);
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
    { label: "IC", color: "#007f86", rows: state.research?.ic || [], yKey: "ic" },
    { label: "Rank IC", color: "#b86b24", rows: state.research?.ic || [], yKey: "rank_ic" },
  ]);
  byId("group-chart").innerHTML = barChart(averageByKey(state.research?.group_returns || [], "quantile", "mean_forward_return"), "quantile", "mean_forward_return", "#476f54");
  byId("long-short-chart").innerHTML = lineChart(state.research?.long_short || [], "long_short_return", "#a13d32", "Long-short");
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
  byId("equity-chart").innerHTML = lineChart(state.research?.equity_curve || [], "equity", "#007f86", "Equity");
  byId("drawdown-chart").innerHTML = lineChart(state.research?.drawdown_curve || [], "drawdown", "#a13d32", "Drawdown");
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
    { label: "策略", color: "#007f86", rows: state.research?.equity_curve || [], yKey: "equity" },
    { label: "基准", color: "#b86b24", rows: state.research?.benchmark_curve || [], yKey: "benchmark_equity" },
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
  byId("paper-equity-chart").innerHTML = lineChart(paper.equity_curve || [], "equity", "#007f86", "Paper equity");
  byId("paper-exposure-chart").innerHTML = lineChart(paper.equity_curve || [], "gross_exposure", "#b86b24", "Gross exposure");
  byId("paper-fill-table").innerHTML = tableRows(paper.fills || [], ["signal_date", "execution_date", "asset_id", "market", "side", "quantity", "fill_price", "fee"]);
  byId("paper-guard-table").innerHTML = tableRows(paper.guard_events || [], ["date", "event_type", "drawdown", "blocked_buy_intents", "cooldown_remaining"]);
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
  return `<div class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(meta || "")}</span></div>`;
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
      <text x="24" y="5" font-size="12" fill="#5d6470">${escapeSvg(item.label)}</text>
    </g>
  `).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="line chart">
      <rect width="${width}" height="${height}" fill="#f6f2ea"></rect>
      ${legend}
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="#d7d0c4"></line>
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="#d7d0c4"></line>
      <text x="10" y="${pad.top + 5}" font-size="11" fill="#5d6470">${maxY.toFixed(3)}</text>
      <text x="10" y="${height - pad.bottom}" font-size="11" fill="#5d6470">${minY.toFixed(3)}</text>
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
      <text x="${x}" y="${height - 18}" font-size="11" fill="#5d6470">${escapeSvg(point.label.slice(0, 9))}</text>
    `;
  }).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="bar chart">
      <rect width="${width}" height="${height}" fill="#f6f2ea"></rect>
      <line x1="${pad.left}" y1="${zeroY}" x2="${width - pad.right}" y2="${zeroY}" stroke="#d7d0c4"></line>
      ${bars}
    </svg>
  `;
}

function emptyChart(label) {
  return `<svg viewBox="0 0 520 240" role="img" aria-label="${escapeHtml(label)}"><rect width="520" height="240" fill="#f6f2ea"></rect><text x="30" y="122" fill="#5d6470">${escapeSvg(label)}</text></svg>`;
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
  try {
    await action();
  } catch (error) {
    showToast(error.message || "运行失败", true);
  } finally {
    button.disabled = false;
    button.textContent = label;
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
