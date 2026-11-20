let selectedPortfolioId = null;

const fmtPct = (v) => (v == null ? "-" : `${(Number(v) * 100).toFixed(2)}%`);
const fmtNum = (v, d = 2) => (v == null ? "-" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
const clsSign = (v) => (Number(v) >= 0 ? "pos" : "neg");

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 5000);
}

async function apiGet(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function apiPost(url, body = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function renderEquitySvgClient(rows, title) {
  const w = 780, h = 270, l = 62, r = 20, t = 34, b = 32;
  const iw = w - l - r, ih = h - t - b;
  if (!rows || rows.length === 0) return `<div class="muted">暂无净值曲线数据，请点击右上角“更新行情并运行今日模拟盘”。</div>`;
  const vals = rows.map((x) => Number(x.nav));
  let yMin = Math.min(...vals), yMax = Math.max(...vals);
  if (yMax <= yMin) { yMin -= 1; yMax += 1; }
  const pad = (yMax - yMin) * 0.08;
  yMin -= pad; yMax += pad;
  const n = Math.max(rows.length - 1, 1);
  const pts = rows.map((x, i) => `${(l + (iw * i) / n).toFixed(1)},${(t + ih - ((Number(x.nav) - yMin) / (yMax - yMin)) * ih).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
    <text x="${l}" y="22" fill="#f8fafc" font-size="13" font-weight="600">${title}</text>
    <line x1="${l}" y1="${t}" x2="${l}" y2="${h - b}" stroke="#334155"/>
    <line x1="${l}" y1="${h - b}" x2="${w - r}" y2="${h - b}" stroke="#334155"/>
    <text x="6" y="${t + 10}" fill="#94a3b8" font-size="11">${fmtNum(yMax, 1)}</text>
    <text x="6" y="${h - b}" fill="#94a3b8" font-size="11">${fmtNum(yMin, 1)}</text>
    <text x="${l}" y="${h - 10}" fill="#94a3b8" font-size="11">${rows[0].date}</text>
    <text x="${w - r - 76}" y="${h - 10}" fill="#94a3b8" font-size="11">${rows[rows.length - 1].date}</text>
    <polyline fill="none" stroke="#38bdf8" stroke-width="2.4" points="${pts}"/>
  </svg>`;
}

async function loadOverview() {
  const data = await apiGet("/api/overview");
  const wrap = document.getElementById("portfolio-cards");
  wrap.innerHTML = "";
  (data.portfolios || []).forEach((p) => {
    const card = document.createElement("div");
    card.className = "portfolio-card" + (p.portfolio_id === selectedPortfolioId ? " selected" : "");
    card.innerHTML = `
      <div class="meta-row"><span>${p.market} · ${p.strategy_kind}</span><span>${p.last_date || "未启动"}</span></div>
      <h3 style="margin:6px 0 2px">${p.name}</h3>
      <div class="big-num">${fmtNum(p.nav)} <span style="font-size:13px;color:#94a3b8">${p.currency}</span></div>
      <div class="meta-row">
        <span class="${clsSign(p.total_return)}">收益 ${fmtPct(p.total_return)} (${p.net_pnl >= 0 ? "+" : ""}${fmtNum(p.net_pnl)})</span>
        <span>回撤 ${fmtPct(p.max_drawdown)}</span>
      </div>
      <div class="meta-row">
        <span>记录 ${p.days_recorded} 日 · ${p.trade_count} 笔成交</span>
        <span>费用 ${fmtNum(p.total_fees)}</span>
      </div>`;
    card.onclick = () => selectPortfolio(p.portfolio_id);
    wrap.appendChild(card);
  });
  if (!selectedPortfolioId && data.portfolios && data.portfolios.length > 0) {
    selectPortfolio(data.portfolios[0].portfolio_id);
  }
}

async function selectPortfolio(pid) {
  selectedPortfolioId = pid;
  document.querySelectorAll(".portfolio-card").forEach((c) => c.classList.remove("selected"));
  try {
    const detail = await apiGet(`/api/portfolio/${encodeURIComponent(pid)}`);
    const st = detail.state;
    document.getElementById("portfolio-detail").classList.remove("hidden");
    document.getElementById("detail-title").textContent = `${st.name} (${st.portfolio_id})`;
    document.getElementById("detail-sub").textContent = `市场: ${st.market} | 初始资金: ${fmtNum(st.initial_cash)} ${st.currency} | 现金: ${fmtNum(st.cash)} | 持仓市值: ${fmtNum(st.market_value)} | 区间: ${st.first_date || "-"} ~ ${st.last_date || "-"}`;
    document.getElementById("detail-signal-badge").textContent = `最新信号: ${detail.latest_signal?.decision_action || "hold"}`;
    document.getElementById("detail-chart").innerHTML = renderEquitySvgClient(detail.equity, `${st.name} 每日模拟净值 (${st.currency})`);

    const posBody = document.querySelector("#positions-table tbody");
    const posEntries = Object.entries(st.positions || {});
    posBody.innerHTML = posEntries.length
      ? posEntries.map(([sym, p]) => `<tr><td>${sym}</td><td>${p.raw_qty}</td><td>${fmtNum(p.avg_cost, 3)}</td><td>${fmtNum(p.last_price, 3)}</td><td>${fmtNum(p.market_value)}</td><td>${fmtPct(p.market_value / Math.max(st.nav, 1))}</td></tr>`).join("")
      : `<tr><td colspan="6" class="muted">当前空仓（100% 现金）</td></tr>`;

    document.getElementById("signal-json").textContent = JSON.stringify(detail.latest_signal || {}, null, 2);

    const trBody = document.querySelector("#trades-table tbody");
    trBody.innerHTML = (detail.trades || []).length
      ? detail.trades.map((t) => `<tr><td>${t.date}</td><td>${t.symbol}</td><td class="${t.side === "BUY" ? "pos" : "neg"}">${t.side}</td><td>${t.quantity}</td><td>${fmtNum(t.raw_price, 3)}</td><td>${fmtNum(t.notional)}</td><td>${fmtNum(t.commission)}</td><td>${fmtNum(t.slippage)}</td><td>${t.reason}</td></tr>`).join("")
      : `<tr><td colspan="9" class="muted">暂无成交记录</td></tr>`;
  } catch (err) {
    document.getElementById("portfolio-detail").classList.add("hidden");
  }
}

async function loadPresets() {
  const data = await apiGet("/api/presets");
  const bar = document.getElementById("preset-buttons");
  bar.innerHTML = "";
  (data.presets || []).forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn";
    btn.textContent = p.name;
    btn.onclick = () => {
      const f = document.getElementById("bt-form");
      f.market.value = p.market;
      f.strategy_kind.value = p.strategy.kind;
      f.symbols.value = p.symbols.join(",");
      f.defensive_symbol.value = p.strategy.defensive_symbol || "";
      f.initial_cash.value = p.initial_cash;
      f.minimum_commission.value = p.cost.minimum_commission;
      f.commission_bps.value = p.cost.commission_bps;
      f.slippage_bps.value = p.cost.slippage_bps;
      f.start_date.value = p.start_date;
      f.rebalance_frequency.value = p.strategy.rebalance_frequency;
      f.lookback_days.value = p.strategy.lookback_days;
      f.trend_ma_days.value = p.strategy.trend_ma_days;
    };
    bar.appendChild(btn);
  });
}

async function loadSystem() {
  const data = await apiGet("/api/system");
  document.getElementById("audit-json").textContent = JSON.stringify({ providers: data.providers, audit: data.audit }, null, 2);
  const tbody = document.querySelector("#cache-table tbody");
  tbody.innerHTML = (data.cache || []).map((c) => `<tr><td>${c.market}</td><td>${c.symbol}</td><td>${c.rows}</td><td>${c.first_date}</td><td>${c.last_date}</td><td>${c.source}</td></tr>`).join("");
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "system") loadSystem();
  };
});

document.getElementById("btn-run-paper").onclick = async (e) => {
  const btn = e.target;
  btn.disabled = true;
  btn.textContent = "正在更新行情并记账...";
  try {
    const res = await apiPost("/api/paper/run", { skip_fetch: false });
    const totalNew = (res.portfolios || []).reduce((acc, p) => acc + (p.new_days || 0), 0);
    showToast(`更新完成！新增模拟交易日 ${totalNew} 条记录（共 ${res.portfolios.length} 个组合）。`);
    await loadOverview();
    if (selectedPortfolioId) await selectPortfolio(selectedPortfolioId);
  } catch (err) {
    showToast(`更新失败: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "更新行情并运行今日模拟盘";
  }
};

document.getElementById("bt-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  showToast("正在运行真实数据回测...");
  try {
    const res = await apiPost("/api/backtest/run", payload);
    const m = res.summary.metrics;
    const b = res.summary.benchmark_metrics || {};
    document.getElementById("bt-output").classList.remove("hidden");
    const kpis = [
      ["期末净值", `${fmtNum(m.final_nav)} ${res.summary.currency}`],
      ["总收益 / 年化", `${fmtPct(m.total_return)} / ${fmtPct(m.cagr)}`],
      ["等权买入持有", fmtPct(b.total_return)],
      ["夏普比率", fmtNum(m.sharpe, 2)],
      ["最大回撤", fmtPct(m.max_drawdown)],
      ["交易笔数 / 费用", `${m.trade_count} 笔 / ${fmtNum(m.total_commission + m.total_slippage)}`],
    ];
    document.getElementById("bt-kpis").innerHTML = kpis.map(([k, v]) => `<div class="kpi"><div class="label">${k}</div><div class="val">${v}</div></div>`).join("");
    document.getElementById("bt-chart").innerHTML = res.svg;
    document.querySelector("#bt-yearly tbody").innerHTML = (res.summary.yearly_returns || [])
      .map((y) => `<tr><td>${y.year}</td><td class="${clsSign(y.strategy_return)}">${fmtPct(y.strategy_return)}</td><td>${fmtPct(y.benchmark_return)}</td><td>${fmtPct(y.max_drawdown)}</td><td>${y.trades}</td></tr>`).join("");
    document.querySelector("#bt-trades tbody").innerHTML = (res.trades || []).slice().reverse()
      .map((t) => `<tr><td>${t.date}</td><td>${t.symbol}</td><td class="${t.side === "BUY" ? "pos" : "neg"}">${t.side}</td><td>${t.quantity}</td><td>${fmtNum(t.raw_price, 3)}</td><td>${fmtNum(t.commission)}</td></tr>`).join("");
    showToast("回测完成！");
  } catch (err) {
    showToast(`回测失败: ${err.message}`);
  }
};

loadOverview();
loadPresets();
