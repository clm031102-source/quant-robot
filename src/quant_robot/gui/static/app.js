const state = {
  snapshot: null,
  research: null,
};

const titles = {
  dashboard: "Dashboard",
  data: "数据中心",
  research: "因子研究",
  backtest: "回测报告",
  risk: "风险监控",
  logs: "日志/报告",
};

document.addEventListener("DOMContentLoaded", async () => {
  bindNavigation();
  bindActions();
  await loadSnapshot();
  await runResearch();
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
  document.getElementById("run-backtest").addEventListener("click", runResearch);
}

async function loadSnapshot() {
  state.snapshot = await fetchJson("/api/snapshot");
  document.getElementById("mode-pill").textContent = `${state.snapshot.data_mode} · local only`;
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
    top_n: valueOf("top-n") || "2",
    cost_bps: valueOf("cost-bps") || "5",
    start_date: valueOf("start-date"),
    end_date: valueOf("end-date"),
  });
  state.research = await fetchJson(`/api/research/demo?${params.toString()}`);
  renderDashboard();
  renderFactorResearch();
  renderBacktest();
  renderRisk();
}

function fillFactorSelect(factors) {
  const select = document.getElementById("factor-select");
  if (select.children.length > 0) return;
  select.innerHTML = factors.map((factor) => `<option value="${escapeHtml(factor)}">${escapeHtml(factor)}</option>`).join("");
}

function renderDashboard() {
  const dashboard = state.snapshot?.dashboard;
  const metrics = state.research?.metrics || {};
  document.getElementById("dashboard-metrics").innerHTML = [
    metric("策略数量", dashboard?.strategy_count ?? 0, "demo strategies"),
    metric("数据源状态", `${state.snapshot?.markets?.length ?? 0}/4`, "local status checks"),
    metric("最近报告", dashboard?.latest_report || "--", "demo fixture"),
    metric("回测数量", dashboard?.backtest_count ?? 0, "research runs"),
  ].join("");
  document.getElementById("dashboard-equity").innerHTML = lineChart(state.research?.equity_curve || [], "date", "equity", {
    color: "#0f8b8d",
    title: `Demo equity · ${formatPercent(metrics.total_return)}`,
  });
  document.getElementById("dashboard-risk").innerHTML = `
    <p class="warning-text">${escapeHtml(dashboard?.risk_notice || "")}</p>
    <p class="muted">${escapeHtml(state.snapshot?.notice || "")}</p>
  `;
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
    metric("Mean IC", formatDecimal(summary.mean_ic), "demo"),
    metric("Rank IC", formatDecimal(summary.mean_rank_ic), "demo"),
    metric("ICIR", formatDecimal(summary.icir), "mean / std"),
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

function renderRisk() {
  const risk = state.research?.risk || state.snapshot?.risk || {};
  document.getElementById("risk-metrics").innerHTML = [
    metric("波动率", formatPercent(risk.volatility), "demo"),
    metric("最大回撤", formatPercent(risk.max_drawdown), "demo"),
    metric("VaR 95", formatPercent(risk.var_95), "demo"),
    metric("仓位暴露", formatDecimal(risk.gross_exposure), "gross"),
    metric("连续亏损", risk.loss_streak ?? 0, "periods"),
  ].join("");
  const exposure = Object.entries(risk.exposure_by_market || {}).map(([market, value]) => ({ market, value }));
  document.getElementById("exposure-chart").innerHTML = barChart(exposure, "market", "value", "#c56b2d");
  document.getElementById("risk-log").innerHTML = (risk.anomalies || []).map((item) => `
    <div class="risk-row"><strong>${escapeHtml(item.level)}</strong><span class="muted">${escapeHtml(item.message)}</span></div>
  `).join("");
}

function renderLogs() {
  const logs = state.snapshot?.logs || {};
  const research = logs.research || [];
  const backtest = logs.backtest || [];
  const errors = logs.errors || [];
  document.getElementById("task-log").innerHTML = [...research, ...backtest, ...errors].map((item) => `
    <div class="log-row">
      <strong>${escapeHtml(item.level)} · ${escapeHtml(item.time || "")}</strong>
      <span class="muted">${escapeHtml(item.message)}</span>
    </div>
  `).join("");
  document.getElementById("report-list").innerHTML = (state.snapshot?.reports || []).map((report) => `
    <div class="report-row">
      <strong>${escapeHtml(report.name)}</strong>
      <span class="muted">${escapeHtml(report.kind)} · ${escapeHtml(report.path)}</span>
    </div>
  `).join("");
}

function metric(label, value, meta) {
  return `<div class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(meta || "")}</span></div>`;
}

function tableRows(rows, columns) {
  const head = `<tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
  const body = rows.slice(0, 40).map((row) => `
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
  const width = 720;
  const height = 260;
  const pad = { left: 46, right: 22, top: 26, bottom: 38 };
  const all = series.flatMap((item) => item.points);
  if (all.length === 0) {
    return emptyChart("No demo points");
  }
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
    <g transform="translate(${pad.left + index * 140}, 14)">
      <rect width="16" height="4" fill="${item.color}"></rect>
      <text x="22" y="5" font-size="12" fill="#686c62">${escapeSvg(item.label)}</text>
    </g>
  `).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="line chart">
      <rect width="${width}" height="${height}" fill="#fbf8f0"></rect>
      ${legend}
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="#d7d1c3"></line>
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="#d7d1c3"></line>
      <text x="8" y="${pad.top + 5}" font-size="11" fill="#686c62">${maxY.toFixed(3)}</text>
      <text x="8" y="${height - pad.bottom}" font-size="11" fill="#686c62">${minY.toFixed(3)}</text>
      ${paths}
    </svg>
  `;
}

function barChart(rows, xKey, yKey, color) {
  const points = rows
    .map((row) => ({ label: String(row[xKey]), value: Number(row[yKey]) }))
    .filter((point) => Number.isFinite(point.value));
  if (points.length === 0) return emptyChart("No demo bars");
  const width = 520;
  const height = 250;
  const pad = { left: 44, right: 18, top: 22, bottom: 44 };
  const minY = Math.min(0, ...points.map((point) => point.value));
  const maxY = Math.max(0.001, ...points.map((point) => point.value));
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const zeroY = pad.top + innerH - ((0 - minY) / (maxY - minY)) * innerH;
  const barW = Math.max(16, innerW / points.length - 10);
  const bars = points.map((point, index) => {
    const x = pad.left + index * (innerW / points.length) + 5;
    const y = pad.top + innerH - ((point.value - minY) / (maxY - minY)) * innerH;
    const h = Math.abs(zeroY - y);
    return `
      <rect x="${x}" y="${Math.min(y, zeroY)}" width="${barW}" height="${h}" fill="${color}"></rect>
      <text x="${x}" y="${height - 18}" font-size="11" fill="#686c62">${escapeSvg(point.label.slice(0, 8))}</text>
    `;
  }).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="bar chart">
      <rect width="${width}" height="${height}" fill="#fbf8f0"></rect>
      <line x1="${pad.left}" y1="${zeroY}" x2="${width - pad.right}" y2="${zeroY}" stroke="#d7d1c3"></line>
      ${bars}
    </svg>
  `;
}

function emptyChart(label) {
  return `<svg viewBox="0 0 520 240" role="img" aria-label="${escapeHtml(label)}"><rect width="520" height="240" fill="#fbf8f0"></rect><text x="32" y="120" fill="#686c62">${escapeSvg(label)}</text></svg>`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

function valueOf(id) {
  return document.getElementById(id)?.value || "";
}

function formatCell(value) {
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
