const state = {
  snapshot: null,
  research: null,
  signals: null,
};

const titles = {
  dashboard: "总览",
  data: "数据中心",
  research: "因子研究",
  backtest: "回测报告",
  signals: "信号快照",
  risk: "风险监控",
  logs: "日志报告",
};

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  await loadSnapshot();
  await runResearch();
  await runSignals();
});

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const page = button.dataset.page;
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelectorAll(".page").forEach((section) => section.classList.remove("active-page"));
      document.getElementById(`page-${page}`).classList.add("active-page");
      document.getElementById("page-title").textContent = titles[page] || page;
    });
  });
}

function bindActions() {
  document.getElementById("run-research").addEventListener("click", runResearch);
  document.getElementById("run-signals").addEventListener("click", runSignals);
}

async function loadSnapshot() {
  state.snapshot = await fetchJson("/api/snapshot");
  document.getElementById("mode-pill").textContent = `${state.snapshot.data_mode} / local`;
  fillFactorSelect(state.snapshot.available_factors || []);
  renderDashboard();
  renderDataCenter();
  renderRisk();
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
  });
  await withBusy("run-research", async () => {
    state.research = await fetchJson(`/api/research/demo?${params.toString()}`);
    renderDashboard();
    renderFactorResearch();
    renderBacktest();
    renderRisk();
    showToast("研究已更新");
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
    renderRisk();
    showToast("信号快照已生成");
  });
}

function fillFactorSelect(factors) {
  const select = document.getElementById("factor-select");
  select.innerHTML = factors.map((factor) => `<option value="${escapeHtml(factor)}">${escapeHtml(factor)}</option>`).join("");
}

function renderDashboard() {
  const dashboard = state.snapshot?.dashboard || {};
  const metrics = state.research?.metrics || {};
  const signals = state.signals || {};
  document.getElementById("dashboard-metrics").innerHTML = [
    metric("策略数量", dashboard.strategy_count ?? 0, "demo strategies"),
    metric("数据源状态", `${state.snapshot?.markets?.length ?? 0}/4`, "local checks"),
    metric("回测数量", dashboard.backtest_count ?? 0, "research runs"),
    metric("信号日期", signals.signal_date || "--", "latest snapshot"),
  ].join("");
  document.getElementById("dashboard-equity").innerHTML = lineChart(state.research?.equity_curve || [], "date", "equity", {
    color: "#0f8b8d",
    title: `Demo equity ${formatPercent(metrics.total_return)}`,
  });
  document.getElementById("dashboard-status").innerHTML = statusRows([
    ["Tushare", readyText(state.snapshot?.readiness?.tushare), state.snapshot?.readiness?.tushare?.ready ? "ok" : "warn"],
    ["Parquet", readyText(state.snapshot?.readiness?.parquet), state.snapshot?.readiness?.parquet?.ready ? "ok" : "warn"],
    ["交易边界", dashboard.risk_notice || "Research only", "danger"],
    ["数据说明", state.snapshot?.notice || "", "muted"],
  ]);
}

function renderDataCenter() {
  document.getElementById("market-table").innerHTML = (state.snapshot?.markets || []).map((market) => `
    <tr>
      <td><span class="status-dot"></span><strong>${escapeHtml(market.market)}</strong><br><span class="muted">${escapeHtml(market.label)}</span></td>
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
  document.getElementById("factor-metrics").innerHTML = [
    metric("Mean IC", formatDecimal(summary.mean_ic), "cross-section"),
    metric("Rank IC", formatDecimal(summary.mean_rank_ic), "rank"),
    metric("ICIR", formatDecimal(summary.icir), "mean/std"),
    metric("因子", state.research?.request?.factor_name || "--", "selected"),
    metric("市场", state.research?.request?.market || "--", "selected"),
  ].join("");
  document.getElementById("ic-chart").innerHTML = multiLineChart(state.research?.ic || [], "date", [
    { key: "ic", label: "IC", color: "#0f8b8d" },
    { key: "rank_ic", label: "Rank IC", color: "#c56b2d" },
  ]);
  document.getElementById("group-chart").innerHTML = barChart(
    averageByKey(state.research?.group_returns || [], "quantile", "mean_forward_return"),
    "quantile",
    "mean_forward_return",
    "#476f54"
  );
  document.getElementById("long-short-chart").innerHTML = lineChart(state.research?.long_short || [], "date", "long_short_return", {
    color: "#b44336",
    title: "Long-short return",
  });
}

function renderBacktest() {
  const metrics = state.research?.metrics || {};
  document.getElementById("backtest-metrics").innerHTML = [
    metric("年化收益", formatPercent(metrics.annualized_return), "demo"),
    metric("最大回撤", formatPercent(metrics.max_drawdown), "demo"),
    metric("夏普比率", formatDecimal(metrics.sharpe), "demo"),
    metric("胜率", formatPercent(metrics.win_rate), "demo"),
    metric("换手率", formatDecimal(metrics.turnover), "avg"),
  ].join("");
  document.getElementById("equity-chart").innerHTML = lineChart(state.research?.equity_curve || [], "date", "equity", {
    color: "#0f8b8d",
    title: "Equity",
  });
  document.getElementById("drawdown-chart").innerHTML = lineChart(state.research?.drawdown_curve || [], "date", "drawdown", {
    color: "#b44336",
    title: "Drawdown",
  });
  document.getElementById("trade-table").innerHTML = tableRows(state.research?.trades || [], [
    "signal_date",
    "entry_date",
    "exit_date",
    "asset_id",
    "market",
    "target_weight",
    "net_return",
  ]);
  document.getElementById("holding-table").innerHTML = tableRows(state.research?.holdings || [], [
    "date",
    "asset_id",
    "market",
    "factor_name",
    "factor_value",
    "target_weight",
  ]);
}

function renderSignals() {
  const signal = state.signals || {};
  document.getElementById("signal-metrics").innerHTML = [
    metric("信号日期", signal.signal_date || "--", "as-of"),
    metric("目标总仓位", formatPercent(signal.target_gross_exposure), "gross"),
    metric("现金权重", formatPercent(signal.cash_weight), "cash"),
    metric("目标数量", signal.targets?.length ?? 0, "assets"),
    metric("可执行", "false", "research only"),
  ].join("");
  document.getElementById("target-table").innerHTML = tableRows(signal.targets || [], [
    "signal_date",
    "asset_id",
    "market",
    "factor_name",
    "factor_value",
    "latest_price",
    "target_weight",
  ]);
  document.getElementById("rebalance-table").innerHTML = tableRows(signal.rebalance_plan || [], [
    "asset_id",
    "market",
    "action",
    "target_weight",
    "delta_value",
    "estimated_quantity_delta",
    "executable",
  ]);
}

function renderRisk() {
  const risk = state.research?.risk || state.snapshot?.risk || {};
  const signalGross = Number(state.signals?.target_gross_exposure);
  document.getElementById("risk-metrics").innerHTML = [
    metric("波动率", formatPercent(risk.volatility), "demo"),
    metric("最大回撤", formatPercent(risk.max_drawdown), "demo"),
    metric("VaR 95", formatPercent(risk.var_95), "demo"),
    metric("研究暴露", formatDecimal(risk.gross_exposure), "backtest"),
    metric("信号仓位", Number.isFinite(signalGross) ? formatPercent(signalGross) : "--", "targets"),
  ].join("");
  const exposure = Object.entries(risk.exposure_by_market || {}).map(([market, value]) => ({ market, value }));
  document.getElementById("exposure-chart").innerHTML = barChart(exposure, "market", "value", "#c56b2d");
  document.getElementById("risk-log").innerHTML = (risk.anomalies || []).map((item) => `
    <div class="list-row ${escapeHtml(item.level)}"><strong>${escapeHtml(item.level)}</strong><span>${escapeHtml(item.message)}</span></div>
  `).join("");
}

function renderLogs() {
  const logs = state.snapshot?.logs || {};
  const rows = [...(logs.research || []), ...(logs.backtest || []), ...(logs.errors || [])];
  document.getElementById("task-log").innerHTML = rows.map((item) => `
    <div class="list-row"><strong>${escapeHtml(item.level)} / ${escapeHtml(item.time || "")}</strong><span>${escapeHtml(item.message)}</span></div>
  `).join("");
  document.getElementById("report-list").innerHTML = (state.snapshot?.reports || []).map((report) => `
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
  const body = rows.slice(0, 60).map((row) => `
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

function lineChart(rows, xKey, yKey, options = {}) {
  const points = rows
    .map((row) => ({ x: row[xKey], y: Number(row[yKey]) }))
    .filter((point) => Number.isFinite(point.y));
  return renderLineSvg([{ points, color: options.color || "#0f8b8d", label: options.title || yKey }]);
}

function multiLineChart(rows, xKey, series) {
  const chartSeries = series.map((item) => ({
    color: item.color,
    label: item.label,
    points: rows
      .map((row) => ({ x: row[xKey], y: Number(row[item.key]) }))
      .filter((point) => Number.isFinite(point.y)),
  }));
  return renderLineSvg(chartSeries);
}

function renderLineSvg(series) {
  const width = 760;
  const height = 276;
  const pad = { left: 50, right: 24, top: 30, bottom: 38 };
  const all = series.flatMap((item) => item.points);
  if (all.length === 0) return emptyChart("No data");
  let minY = Math.min(...all.map((point) => point.y));
  let maxY = Math.max(...all.map((point) => point.y));
  if (minY === maxY) {
    minY -= 0.5;
    maxY += 0.5;
  }
  const maxLen = Math.max(...series.map((item) => item.points.length));
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const paths = series.map((item) => {
    const coords = item.points.map((point, index) => {
      const x = pad.left + (innerW * index) / Math.max(maxLen - 1, 1);
      const y = pad.top + innerH - ((point.y - minY) / (maxY - minY)) * innerH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return `<polyline points="${coords}" fill="none" stroke="${item.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>`;
  }).join("");
  const legend = series.map((item, index) => `
    <g transform="translate(${pad.left + index * 150}, 16)">
      <rect width="18" height="4" rx="2" fill="${item.color}"></rect>
      <text x="24" y="5" font-size="12" fill="#64685f">${escapeSvg(item.label)}</text>
    </g>
  `).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="line chart">
      <rect width="${width}" height="${height}" fill="#f9f4e8"></rect>
      ${legend}
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="#d9d0be"></line>
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="#d9d0be"></line>
      <text x="10" y="${pad.top + 5}" font-size="11" fill="#64685f">${maxY.toFixed(3)}</text>
      <text x="10" y="${height - pad.bottom}" font-size="11" fill="#64685f">${minY.toFixed(3)}</text>
      ${paths}
    </svg>
  `;
}

function barChart(rows, xKey, yKey, color) {
  const points = rows
    .map((row) => ({ label: String(row[xKey]), value: Number(row[yKey]) }))
    .filter((point) => Number.isFinite(point.value));
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
      <rect x="${x}" y="${Math.min(y, zeroY)}" width="${barW}" height="${h}" rx="4" fill="${color}"></rect>
      <text x="${x}" y="${height - 18}" font-size="11" fill="#64685f">${escapeSvg(point.label.slice(0, 9))}</text>
    `;
  }).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="bar chart">
      <rect width="${width}" height="${height}" fill="#f9f4e8"></rect>
      <line x1="${pad.left}" y1="${zeroY}" x2="${width - pad.right}" y2="${zeroY}" stroke="#d9d0be"></line>
      ${bars}
    </svg>
  `;
}

function emptyChart(label) {
  return `<svg viewBox="0 0 520 240" role="img" aria-label="${escapeHtml(label)}"><rect width="520" height="240" fill="#f9f4e8"></rect><text x="30" y="122" fill="#64685f">${escapeSvg(label)}</text></svg>`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

async function withBusy(buttonId, action) {
  const button = document.getElementById(buttonId);
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
  const toast = document.getElementById("toast");
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

function valueOf(id) {
  return document.getElementById(id)?.value || "";
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
