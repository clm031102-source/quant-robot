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
  dailyTradeAdvisory: null,
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
  beginnerTaskId: "",
  manualFormOverride: false,
  manualFormOverrideReason: "",
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
const PAGE_IDS = new Set(Object.keys(titles));

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
const RUNTIME_GUARDED_ACTIONS = new Set(["research_backtest", "startup_workflows"]);
const FORBIDDEN_CURRENT_POSITION_COLUMNS = new Set(["account", "account_id", "broker", "broker_id", "client_id", "order_id"]);
const DEFAULT_TICKET_REVIEW_CHECKLIST = [
  { check_id: "asset_code_match", label: "核对 ETF 代码", plain_check: "券商端确认 ETF 代码和目标市场一致；不认识就跳过。" },
  { check_id: "broker_realtime_price", label: "核对实时价格", plain_check: "券商端实时价格明显偏离本地参考价时，重新估算数量和金额。" },
  { check_id: "quantity_and_lot_size", label: "核对方向和数量", plain_check: "方向、数量、整手和金额都看懂后再人工决定。" },
  { check_id: "cash_and_weight_limit", label: "核对现金和仓位上限", plain_check: "现金不足、单 ETF 或总仓位超限时跳过。" },
  { check_id: "final_human_decision", label: "最终本人确认", plain_check: "票据不是订单；只能离开系统后在券商端人工决定。" },
];
const DEFAULT_TICKET_RED_FLAGS = [
  { flag_id: "price_changed_from_reference", plain_flag: "券商端实时价明显偏离本地参考价。" },
  { flag_id: "cash_or_position_limit_breach", plain_flag: "现金不足、仓位上限或回撤预算超限。" },
  { flag_id: "asset_not_tradeable", plain_flag: "停牌、涨跌停、无法成交或代码不匹配。" },
  { flag_id: "manual_discomfort", plain_flag: "本人无法解释交易或不愿承担回撤。" },
];
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
  "daily-trade-as-of",
  "daily-trade-portfolio-value",
  "daily-trade-risk-profile",
  "daily-current-positions",
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
const BEGINNER_TASKS = [
  {
    id: "safety",
    title: "我想先确认安全吗",
    plain: "适合第一次打开软件，先确认这里只有本地研究和纸面模拟。",
    result: "不会连接券商、不会读取账户、不会真实下单。",
    evidence: "看安全边界",
    target: "control-safety-boundary",
    primaryLabel: "看安全边界",
    tone: "ok",
  },
  {
    id: "backtest",
    title: "我想跑一次回测",
    plain: "适合已经选好 CN_ETF、因子、日期和成本后，跑当前参数。",
    result: "会打开安全确认，确认后只调用本地回测接口。",
    evidence: "跑完看收益、回撤、胜率和 Sharpe。",
    action: "research_backtest",
    target: "beginner-result-interpreter",
    primaryLabel: "本地回测当前参数",
    tone: "warn",
  },
  {
    id: "trust",
    title: "我想判断结果能不能信",
    plain: "适合已经有回测或回执时，核对数据源、样本长度、当前参数和闸门。",
    result: "会跳到数据可信度、请求预览或回测闸门，不会重新运行。",
    evidence: "先看是否 CN_ETF、是否长样本、是否只是历史回执。",
    target: "beginner-data-trust-card",
    secondaryTarget: "control-backtest-gate",
    primaryLabel: "看可信度",
    secondaryLabel: "看回测闸门",
    tone: "ok",
  },
  {
    id: "paper",
    title: "我想做模拟盘回放",
    plain: "适合回测结果已经复核过，再进入本地纸面模拟。",
    result: "会打开安全确认，确认后只生成本地模拟盘回放。",
    evidence: "跑完看模拟盘交接、成交、权益和风控事件。",
    action: "paper_simulation",
    target: "control-paper-readiness",
    primaryLabel: "本地模拟盘回放",
    requiresResearch: true,
    tone: "warn",
  },
];

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindActions();
  bindRequestPreviewInputs();
  bindPostCloseManualFormStatus();
  renderFactorGlossary();
  renderBeginnerVerdict();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  renderBeginnerTaskWizard();
  renderBeginnerTroubleshooter();
  renderBeginnerGuide();
  renderBeginnerProgress();
  activatePageFromHash();
  initializeApp();
});

async function initializeApp() {
  await safeLoadPanel("snapshot", loadSnapshot);
  await Promise.allSettled([
    safeLoadPanel("factor_leaderboard", loadFactorLeaderboard),
    safeLoadPanel("control_center", loadControlCenter),
  ]);
  await safeLoadPanel("daily_trade_advisory", loadDailyTradeAdvisory);
  loadSecondaryPanels();
}

async function loadSecondaryPanels() {
  await Promise.allSettled([
    safeLoadPanel("project_status", loadProjectStatus),
    safeLoadPanel("daily_ops", loadDailyOps),
    safeLoadPanel("risk_candidates", loadRiskCandidates),
    safeLoadPanel("constrained_search", loadConstrainedSearch),
    safeLoadPanel("paper_profiles", loadPaperProfiles),
    safeLoadPanel("profile_observation", loadProfileObservation),
    safeLoadPanel("recent_data_refresh", loadRecentDataRefresh),
    safeLoadPanel("post_refresh_replay", loadPostRefreshReplay),
    safeLoadPanel("observation_sufficiency", loadObservationSufficiency),
    safeLoadPanel("expanded_observation_replay", loadExpandedObservationReplay),
    safeLoadPanel("iterative_observation_expansion", loadIterativeObservationExpansion),
    safeLoadPanel("tushare_activation_gate", loadTushareActivationGate),
  ]);
}

async function safeLoadPanel(panelId, loader) {
  try {
    await loader();
  } catch (error) {
    console.error(`panel load failed: ${panelId}`, error);
  }
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      activatePage(button.dataset.page || "dashboard", true);
    });
  });
  window.addEventListener("hashchange", () => activatePageFromHash());
}

function activatePageFromHash() {
  const { pageId, targetIdFromHash } = routeFromHash();
  activatePage(pageId, false);
  if (targetIdFromHash) {
    window.setTimeout(() => jumpToBeginnerTarget(targetIdFromHash), 0);
  }
}

function routeFromHash() {
  const route = (window.location.hash || "").replace(/^#/, "");
  const [pagePart, targetPart = ""] = route.split(":", 2);
  const pageId = PAGE_IDS.has(pagePart) ? pagePart : "dashboard";
  const targetIdFromHash = /^[A-Za-z0-9_-]+$/.test(targetPart) ? targetPart : "";
  return { pageId, targetIdFromHash };
}

function activatePage(page, updateHash = false) {
  const pageId = PAGE_IDS.has(page) ? page : "dashboard";
  const pageSection = byId(`page-${pageId}`);
  const navButton = Array.from(document.querySelectorAll(".nav-item")).find((item) => item.dataset.page === pageId);
  if (!pageSection || !navButton) return;

  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  navButton.classList.add("active");
  document.querySelectorAll(".page").forEach((section) => section.classList.remove("active-page"));
  pageSection.classList.add("active-page");
  byId("page-title").textContent = titles[pageId] || pageId;
  if (updateHash && window.location.hash !== `#${pageId}`) {
    window.history.replaceState(null, "", `#${pageId}`);
  }
  document.querySelector(".workspace")?.scrollTo({ top: 0, behavior: "smooth" });
}

function updateHashForBeginnerTarget(pageName, targetId) {
  if (!PAGE_IDS.has(pageName) || !/^[A-Za-z0-9_-]+$/.test(targetId || "")) return;
  const nextHash = `#${pageName}:${targetId}`;
  if (window.location.hash !== nextHash) window.history.replaceState(null, "", nextHash);
}

function bindActions() {
  byId("run-startup-workflows").addEventListener("click", runStartupWorkflows);
  byId("run-research").addEventListener("click", runResearch);
  byId("run-signals").addEventListener("click", runSignals);
  byId("run-paper").addEventListener("click", runPaper);
  byId("run-daily-ops").addEventListener("click", runDailyOps);
  byId("run-daily-trade-advisory").addEventListener("click", runDailyTradeAdvisory);
  byId("run-promotion").addEventListener("click", runPromotionOps);
  byId("safe-run-cancel")?.addEventListener("click", () => resolveSafeWorkflow(false));
  byId("safe-run-confirm")?.addEventListener("click", () => resolveSafeWorkflow(true));
  byId("safe-run-modal")?.addEventListener("click", (event) => {
    if (event.target?.id === "safe-run-modal") resolveSafeWorkflow(false);
  });
  byId("data-source-select").addEventListener("change", () => {
    markManualFormOverride("data_source_select");
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
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-ordinary-daily-action]");
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const actionId = button.dataset.ordinaryDailyAction || "";
    const targetId = button.dataset.ordinaryDailyTarget || "daily-trade-decision-sheet";
    if (actionId) {
      await runBeginnerAction(actionId, button);
      return;
    }
    jumpToBeginnerTarget(targetId, button.dataset.leaderboardTab || state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-target]");
    if (!button) return;
    jumpToBeginnerTarget(button.dataset.beginnerTarget || "", button.dataset.leaderboardTab || "");
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy-ticket-text]");
    if (!button) return;
    event.preventDefault();
    await copyTicketTextToClipboard(button.dataset.copyTicketText || "");
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-factor-beginner-jump]");
    if (!button) return;
    jumpToBeginnerTarget(button.dataset.factorBeginnerJump || "factor-leaderboard-table", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-factor-apply-row], [data-factor-run-row]");
    if (!button) return;
    event.preventDefault();
    if (button.matches("[data-factor-run-row]") && button.disabled) return;
    const row = leaderboardRowFromButton(button);
    applyLeaderboardRowToForms(row);
    if (button.matches("[data-factor-run-row]")) {
      await runBeginnerAction("research_backtest", button);
    }
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-factor-runtime-gap-action]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget("factor-leaderboard-table", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-factor-runtime-gap-apply]");
    if (!button) return;
    event.preventDefault();
    applyLeaderboardRowToForms(leaderboardRowFromButton(button));
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-daily-paper-handoff-apply]");
    if (!button) return;
    event.preventDefault();
    applyDailyPaperHandoffToForm(dailyPaperHandoffFromButton(button));
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-daily-paper-handoff-run]");
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    await runDailyPaperHandoffSimulation(button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-parameter-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerParameterJump || "control-request-preview", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-parameter-runtime-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerParameterRuntimeJump || "factor-runtime-gap-panel", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-runtime-guard-help-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.runtimeGuardHelpJump || "factor-runtime-gap-panel", state.leaderboardTab);
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
    const button = event.target.closest("[data-beginner-data-trust-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerDataTrustJump || "control-request-preview", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-evidence-match-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerEvidenceMatchJump || "control-result-freshness", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-beginner-evidence-match-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.beginnerEvidenceMatchAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-task-select]");
    if (!button) return;
    event.preventDefault();
    state.beginnerTaskId = button.dataset.beginnerTaskSelect || "";
    renderBeginnerTaskWizard();
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-beginner-task-run]");
    if (!button) return;
    event.preventDefault();
    const actionId = button.dataset.beginnerTaskAction || "";
    const targetId = button.dataset.beginnerTaskTarget || "";
    if (actionId) {
      await runBeginnerAction(actionId, button);
      return;
    }
    jumpToBeginnerTarget(targetId, button.dataset.leaderboardTab || state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-troubleshooter-jump]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerTroubleshooterJump || "control-active-operation", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-beginner-troubleshooter-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.beginnerTroubleshooterAction || "", button);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-live-handoff-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.liveHandoffAction || "", button);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-trade-system-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.tradeSystemAction || "", button);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-beginner-trade-action-workflow]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.beginnerTradeActionWorkflow || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-trade-system-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.tradeSystemTarget || "beginner-live-handoff-board", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-trade-action-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerTradeActionTarget || "beginner-trade-system-board", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-pretrade-receipt-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerPretradeReceiptTarget || "beginner-trade-system-board", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-beginner-live-pilot-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.beginnerLivePilotAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-beginner-live-pilot-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.beginnerLivePilotTarget || "beginner-trade-system-board", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-daily-command-action]");
    if (!button) return;
    event.preventDefault();
    await runDailyCommandRailAction(button.dataset.dailyCommandAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-daily-command-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.dailyCommandTarget || "daily-command-rail", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-manual-ticket-export-copy]");
    if (!button) return;
    event.preventDefault();
    await copyTicketTextToClipboard(state.dailyTradeAdvisory?.manual_ticket_export?.csv_text || "");
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-manual-ticket-export-download]");
    if (!button) return;
    event.preventDefault();
    downloadManualTicketExport();
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-daily-rehearsal-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.dailyRehearsalAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-daily-rehearsal-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.dailyRehearsalTarget || "beginner-daily-rehearsal-board", state.leaderboardTab);
  });
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-post-close-journal-action]");
    if (!button) return;
    event.preventDefault();
    await runBeginnerAction(button.dataset.postCloseJournalAction || "", button);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-post-close-journal-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.postCloseJournalTarget || "beginner-post-close-journal-board", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-live-handoff-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.liveHandoffTarget || "daily-readiness-primary-action", state.leaderboardTab);
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-live-transition-target]");
    if (!button) return;
    event.preventDefault();
    jumpToBeginnerTarget(button.dataset.liveTransitionTarget || "daily-live-transition-board", state.leaderboardTab);
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
    const renderWithManualOverride = (event) => {
      if (event?.isTrusted) markManualFormOverride(id);
      renderRequestPreview();
      if (id === "daily-current-positions") renderDailyCurrentPositionHelp();
      if (id === "daily-trade-portfolio-value" || id === "daily-trade-risk-profile") renderDailyPortfolioValueHelp();
    };
    element.addEventListener("input", renderWithManualOverride);
    element.addEventListener("change", renderWithManualOverride);
  });
  renderDailyCurrentPositionHelp();
  renderDailyPortfolioValueHelp();
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

async function loadDailyTradeAdvisory() {
  const params = buildDailyTradeAdvisoryParams();
  state.dailyTradeAdvisory = await fetchJson(`/api/trade/daily-advisory?${params.toString()}`);
  renderDailyTradeAdvisory();
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

function buildDailyTradeAdvisoryParams() {
  const params = new URLSearchParams({
    market: valueOf("market-select") || "CN_ETF",
    limit: "3",
    top_n: valueOf("signal-top-n") || "2",
    as_of_date: valueOf("daily-trade-as-of") || valueOf("signal-as-of"),
    portfolio_value: valueOf("daily-trade-portfolio-value") || valueOf("paper-initial-cash") || "100000",
    risk_profile_id: valueOf("daily-trade-risk-profile") || "balanced_20dd",
    current_positions: valueOf("daily-current-positions"),
    max_asset_weight: valueOf("max-asset-weight") || "0.4",
    max_market_weight: valueOf("max-market-weight") || "1",
    max_gross_exposure: valueOf("max-gross-exposure") || "1",
    min_cash_weight: valueOf("min-cash-weight") || "0.1",
  });
  addSourceParams(params);
  const evidence = dailyTradeAdvisoryEvidencePayload();
  if (evidence) params.set("evidence_snapshot", JSON.stringify(evidence));
  return params;
}

function buildPaperParams() {
  const factor = valueOf("paper-factor-select") || "momentum_2";
  const operationDate = valueOf("daily-trade-as-of") || valueOf("signal-as-of") || valueOf("paper-end-date");
  const params = new URLSearchParams({
    market: valueOf("paper-market-select"),
    factor,
    factor_windows: factorWindowCsvForFactor(factor, valueOf("factor-windows")),
    top_n: valueOf("paper-top-n") || "2",
    rebalance_interval: valueOf("rebalance-interval") || "1",
    start_date: valueOf("paper-start-date"),
    end_date: valueOf("paper-end-date"),
    as_of_date: operationDate,
    run_date: operationDate,
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

function parameterRuntimeStatus(researchParams = buildResearchParams()) {
  const factor = parameterPlainValue(researchParams, "factor", "");
  return factorRuntimeStatus({ factor_name: factor });
}

function isRuntimeGuardedAction(actionId) {
  return RUNTIME_GUARDED_ACTIONS.has(actionId);
}

function runtimeGuardAttr(actionId) {
  return isRuntimeGuardedAction(actionId) ? `data-runtime-guard="${escapeHtml(actionId)}"` : "";
}

function currentBacktestRuntimeGuard() {
  const runtime = parameterRuntimeStatus();
  return {
    ...runtime,
    blocked: !runtime.runnable,
    blockedLabel: "需先注册后回测",
    target: "factor-runtime-gap-panel",
  };
}

function syncCurrentBacktestRuntimeGuard() {
  const guard = currentBacktestRuntimeGuard();
  document.querySelectorAll("[data-runtime-guard]").forEach((button) => {
    if (!isRuntimeGuardedAction(button.dataset.runtimeGuard || "")) return;
    const currentText = (button.textContent || "").trim();
    if (currentText && currentText !== guard.blockedLabel && currentText !== "运行中") {
      button.dataset.runtimeOriginalText = currentText;
    }
    if (guard.blocked) {
      button.dataset.runtimeGuardState = "blocked";
      button.classList.add("runtime-guarded-action");
      button.disabled = true;
      button.textContent = guard.blockedLabel;
      button.title = guard.detail;
      return;
    }
    if (button.dataset.runtimeGuardState === "blocked") {
      button.disabled = false;
      button.textContent = button.dataset.runtimeOriginalText || "本地回测当前参数";
    }
    button.dataset.runtimeGuardState = "ready";
    button.classList.remove("runtime-guarded-action");
    if (button.title === guard.detail) button.removeAttribute("title");
  });
  return guard;
}

function renderRuntimeGuardHelp(actionId = "research_backtest", guard = currentBacktestRuntimeGuard()) {
  if (!isRuntimeGuardedAction(actionId) || !guard.blocked) return "";
  const factor = parameterPlainValue(buildResearchParams(), "factor", "当前因子");
  const actionText = actionId === "startup_workflows" ? "一键刷新也会先跑当前回测" : "当前回测入口";
  return `
    <div class="runtime-guard-help warn" data-runtime-guard-help="${escapeHtml(actionId)}">
      <strong>为什么现在不能运行</strong>
      <span>${escapeHtml(`${actionText} 已暂停：${factor} 还没有注册到后端运行因子，下拉框不能直接生成回测结果。`)}</span>
      <button class="secondary-button" type="button" data-runtime-guard-help-jump="${escapeHtml(guard.target)}">看运行缺口</button>
    </div>
  `;
}

function blockCurrentBacktestRuntime(guard = currentBacktestRuntimeGuard()) {
  if (!guard.blocked) return false;
  syncCurrentBacktestRuntimeGuard();
  showToast(guard.detail, true);
  jumpToBeginnerTarget(guard.target, state.leaderboardTab);
  return true;
}

function renderBeginnerParameterActions(runtime = { runnable: true }) {
  const runtimeState = runtime.runnable ? "runtime" : "missing";
  if (runtime.runnable) {
    return `
      <button class="secondary-button" type="button" data-beginner-parameter-jump="control-request-preview">看请求详情</button>
      <button class="primary-button" type="button" data-beginner-action="research_backtest" data-beginner-parameter-runtime="${runtimeState}" ${runtimeGuardAttr("research_backtest")}>本地回测当前参数</button>
    `;
  }
  return `
    <button class="secondary-button" type="button" data-beginner-parameter-jump="control-request-preview">看请求详情</button>
    <button class="secondary-button" type="button" data-beginner-parameter-runtime-jump="factor-runtime-gap-panel">看运行缺口</button>
    <button class="primary-button" type="button" data-beginner-parameter-runtime="${runtimeState}" disabled>需先注册后回测</button>
  `;
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
  const runtime = parameterRuntimeStatus(researchParams);
  const tone = market === "CN_ETF" && source === "processed-bars" && runtime.runnable ? "ok" : "warn";
  summaryTarget.innerHTML = `
    <div class="beginner-parameter-head ${escapeHtml(tone)}">
      <div>
        <strong>${escapeHtml(`现在会用 ${market} 的 ${factor} 做本地研究`)}</strong>
        <span>${escapeHtml(`${dateWindow} / Top${topN} / 成本 ${cost}`)}</span>
        <span class="beginner-parameter-runtime ${escapeHtml(runtime.tone)}" data-beginner-parameter-runtime="${runtime.runnable ? "runtime" : "missing"}">
          <strong>${escapeHtml(runtime.label)}</strong>
          <small>${escapeHtml(runtime.detail)}</small>
        </span>
      </div>
      <div class="beginner-parameter-actions">
        ${renderBeginnerParameterActions(runtime)}
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
      ? `data-beginner-action="${escapeHtml(action.action)}" ${runtimeGuardAttr(action.action)}`
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
      label: "研究回测",
      status: "ok",
      endpoint: `/api/research?${researchParams.toString()}`,
      params: researchParams,
      detail: "full parameter backtest request",
    },
    {
      label: "建议信号",
      status: "warn",
      endpoint: `/api/signals?${signalParams.toString()}`,
      params: signalParams,
      detail: "advisory target-weight request",
    },
    {
      label: "本地模拟盘",
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
        <span>${escapeHtml(friendlyCommandText(row.endpoint))}</span>
        <span>${escapeHtml(requestPreviewSummary(row.params))}</span>
        <span>${escapeHtml(row.detail)}</span>
      </div>
    `).join("");
  }
  renderBeginnerParameterExplainer(researchParams, signalParams, paperParams);
  renderResultFreshness();
  renderParameterConsistency();
  syncCurrentBacktestRuntimeGuard();
}

function applyControlDefaults() {
  const defaults = state.controlCenter?.form_defaults || {};
  if (defaults.stage !== "gui_form_defaults") return;
  if (state.manualFormOverride) {
    renderRequestPreview();
    return;
  }
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

  applyDailyTradeDateDefault();
  renderRequestPreview();
}

function requestPreviewSummary(params) {
  return [
    `数据源=${params.get("source") || "--"}`,
    `市场=${params.get("market") || "--"}`,
    `因子=${params.get("factor") || "--"}`,
    `窗口=${params.get("factor_windows") || "--"}`,
    `TopN=${params.get("top_n") || "--"}`,
    `成本=${params.get("cost_bps") || params.get("commission_bps") || "--"}bps`,
    `日期=${params.get("start_date") || params.get("as_of_date") || "--"} 至 ${params.get("end_date") || params.get("as_of_date") || "--"}`,
  ].join(" / ");
}

function renderResultFreshness() {
  const target = byId("control-result-freshness");
  if (!target) return;
  const rows = [
    resultFreshnessRow(
      "研究回测结果",
      state.research,
      buildResearchParams(),
      ["market", "factor_name", "top_n", "cost_bps", "start_date", "end_date"],
      "修改市场、因子、TopN、成本或日期后，需要重新跑研究回测。",
    ),
    resultFreshnessRow(
      "信号快照结果",
      state.signals,
      buildSignalParams(),
      ["market", "factor_name", "top_n", "as_of_date"],
      "修改因子、TopN 或信号日期后，需要重新生成建议信号。",
    ),
    resultFreshnessRow(
      "模拟盘结果",
      state.paper,
      buildPaperParams(),
      ["market", "factor_name", "top_n", "start_date", "end_date", "initial_cash"],
      "修改市场、因子、TopN、日期窗口或初始资金后，需要重新跑本地模拟盘。",
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
      <strong>${escapeHtml(`参数权威 / ${headerStatus}`)}</strong>
      <span>${escapeHtml(`工作流=${rows.length} / 偏离=${driftCount}`)}</span>
      <span>${escapeHtml(summary.next_action || "当前表单参数匹配标准工作流请求。")}</span>
    </div>
  `;
  const body = rows.map((row) => `
    <div class="list-row ${escapeHtml(row.status === "current" ? "ok" : "warn")}">
      <strong>${escapeHtml(`${row.label} / ${row.status}`)}</strong>
        <span>${escapeHtml(`不一致=${row.mismatchKeys.length ? row.mismatchKeys.join(", ") : "无"}`)}</span>
        <span>${escapeHtml(`表单=${requestFreshnessSummary(row.formRequest)}`)}</span>
        <span>${escapeHtml(`标准=${requestFreshnessSummary(row.canonicalRequest)}`)}</span>
    </div>
  `).join("");
  target.innerHTML = header + (body || `
    <div class="list-row warn">
      <strong>暂无参数权威表</strong>
      <span>加载中控状态后，会比较当前表单参数和标准工作流请求。</span>
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
      status: "未运行",
      statusClass: "warn",
      currentSummary: `当前参数=${requestFreshnessSummary(currentRequest)}`,
      resultSummary: "页面结果=暂无",
      detail,
    };
  }
  const isCurrent = requestMatchesCurrentParams(resultRequest, params, keys);
  return {
    label,
    status: isCurrent ? "当前" : "已过期",
    statusClass: isCurrent ? "ok" : "warn",
    currentSummary: `当前参数=${requestFreshnessSummary(currentRequest)}`,
    resultSummary: `页面结果=${requestFreshnessSummary(resultRequest)}`,
    detail: isCurrent ? "页面指标匹配当前表单参数。" : detail,
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
    request.top_n != null && request.top_n !== "" ? `TopN=${request.top_n}` : "",
    request.cost_bps != null && request.cost_bps !== "" ? `成本=${request.cost_bps}bps` : "",
    request.initial_cash != null && request.initial_cash !== "" ? `初始资金=${request.initial_cash}` : "",
    request.start_date || request.as_of_date || "",
    request.end_date || "",
  ].filter(Boolean).join(" / ") || "--";
}

function applySourcePreset(force) {
  if (force) markManualFormOverride("source_preset");
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
  applyDailyTradeDateDefault(true);
  byId("data-mode-label").textContent = source;
  byId("mode-pill").textContent = `${zhConsoleText(source)} / 本地`;
  renderRequestPreview();
}

function setFactorValue(id, value) {
  const select = byId(id);
  if (!select) return;
  ensureFactorOption(select, value);
  if ([...select.options].some((option) => option.value === value)) {
    select.value = value;
  }
}

function ensureFactorOption(selectOrId, value) {
  const select = typeof selectOrId === "string" ? byId(selectOrId) : selectOrId;
  const factor = String(value || "").trim();
  if (!select || !factor) return;
  if ([...select.options].some((option) => option.value === factor)) return;
  const option = document.createElement("option");
  option.value = factor;
  option.textContent = `${factor}（排行榜候选）`;
  option.dataset.factorSource = "leaderboard";
  select.appendChild(option);
}

function paramsObject(params) {
  if (!params || typeof params.entries !== "function") return {};
  return Object.fromEntries(params.entries());
}

function markManualFormOverride(reason = "manual") {
  state.manualFormOverride = true;
  state.manualFormOverrideReason = reason;
}

function endpointWithParams(path, params) {
  const query = params && typeof params.toString === "function" ? params.toString() : "";
  return query ? `${path}?${query}` : path;
}

function friendlyCommandText(value = "") {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const command = raw.replace(/^GET\s+/i, "");
  const apiIndex = command.indexOf("/api/");
  if (apiIndex >= 0) {
    const apiText = command.slice(apiIndex);
    try {
      return friendlyApiText(new URL(apiText, "http://local"));
    } catch (_error) {
      return zhConsoleText(command.split("?")[0] || raw);
    }
  }
  return zhConsoleText(raw);
}

function friendlyApiText(url) {
  const params = url.searchParams;
  const labels = {
    "/api/research": "研究回测接口",
    "/api/paper": "本地模拟盘接口",
    "/api/signals": "建议信号接口",
    "/api/control/verification": "本地验证接口",
    "/api/control/status": "中控状态接口",
    "/api/daily/ops": "日常运营接口",
    "/api/promotion/ops": "候选推广接口",
  };
  const market = params.get("market");
  const factor = params.get("factor") || params.get("factor_name");
  const topN = params.get("top_n");
  const cost = params.get("cost_bps");
  const start = params.get("start_date");
  const end = params.get("end_date");
  const asOf = params.get("as_of_date");
  const gate = params.get("gate_id");
  return [
    labels[url.pathname] || zhConsoleText(url.pathname),
    market || "",
    factor || "",
    topN ? `TopN=${topN}` : "",
    cost ? `成本=${cost}bps` : "",
    start || end ? `${start || "--"} 至 ${end || "--"}` : "",
    asOf ? `日期=${asOf}` : "",
    gate ? `闸门=${gate}` : "",
  ].filter(Boolean).join(" / ");
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
  if (blockCurrentBacktestRuntime()) return;
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
  if (blockCurrentBacktestRuntime()) return;
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
      detail: `TopN=${valueOf("signal-top-n") || "2"}`,
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
      detail: `${valueOf("paper-market-select") || "ALL"} / TopN=${valueOf("paper-top-n") || "2"}`,
    });
    appendExecutionReceipt(paperReceipt(state.paper));
    showToast("纸面模拟已更新");
  });
}

async function runDailyTradeAdvisory() {
  const params = buildDailyTradeAdvisoryParams();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "daily_trade_advisory",
    label: "生成今日前三因子手工交易建议",
    endpoint: endpointWithParams("/api/trade/daily-advisory", params),
    request: paramsObject(params),
  });
  if (!confirmed) return;
  await withBusy("run-daily-trade-advisory", async () => {
    state.dailyTradeAdvisory = await fetchJson(`/api/trade/daily-advisory?${params.toString()}`);
    renderDailyTradeAdvisory();
    renderDashboard();
    appendRunHistory({
      workflow_id: "daily_trade_advisory",
      label: "Generate top-three manual trade advisory",
      status: "completed",
      detail: `signals ${state.dailyTradeAdvisory?.summary?.signal_count ?? 0} / manual only`,
    });
    appendExecutionReceipt(dailyTradeAdvisoryReceipt(state.dailyTradeAdvisory));
    showToast("今日前三交易建议已生成");
  });
}

async function runDailyPretradeCheckup(button = null) {
  const params = buildDailyTradeAdvisoryParams();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "daily_pretrade_checkup",
    label: "开盘前一键体检",
    endpoint: "/api/daily/ops + /api/trade/daily-advisory",
    request: {
      daily_ops: true,
      daily_trade_advisory: paramsObject(params),
      paper_simulation_auto_run: false,
      manual_handoff_only: true,
    },
  });
  if (!confirmed) return;
  const label = button?.textContent || "";
  const activeOperation = beginActiveOperation({
    workflow_id: "daily_pretrade_checkup",
    label: "开盘前一键体检",
    detail: "刷新日常运营和今日前三建议，再回到红黄灯人工交接",
    safety: "本地体检和人工票据交接；不会连接券商、读取账户或自动下单",
  });
  if (button) {
    button.disabled = true;
    button.textContent = "运行中";
  }
  byId("run-state-label").textContent = "运行中";
  try {
    await loadDailyOps();
    await loadDailyTradeAdvisory();
    const decision = dailyReadinessDecision();
    appendRunHistory({
      workflow_id: "daily_pretrade_checkup",
      label: "开盘前一键体检",
      status: "completed",
      detail: decision.title || "pretrade checkup completed",
    });
    appendExecutionReceipt(dailyPretradeCheckupReceipt({
      decision,
      daily_ops: state.dailyOps,
      daily_trade_advisory: state.dailyTradeAdvisory,
    }));
    finishActiveOperation(activeOperation, "completed", decision.title || "pretrade checkup completed");
    showToast(`开盘前体检完成：${decision.title || "查看红黄灯"}`, decision.tone === "danger");
  } catch (error) {
    finishActiveOperation(activeOperation, "failed", error.message || "Pretrade checkup failed");
    showToast(error.message || "开盘前体检失败", true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = label || "运行";
    }
    byId("run-state-label").textContent = "就绪";
  }
}

async function runPostCloseJournal(button = null) {
  const trade = state.dailyTradeAdvisory || {};
  const template = trade.post_close_journal_template || {};
  const paper = latestExecutionReceipt("paper_simulation");
  const manualReview = postCloseManualReviewForm();
  const confirmed = await confirmSafeWorkflow({
    workflow_id: "post_close_journal",
    label: "生成收盘后复盘回执",
    endpoint: "browser://post_close_journal",
    request: {
      market: trade.market || template.summary?.primary_market || "CN_ETF",
      run_date: trade.run_date || template.run_date || "",
      signal_count: trade.summary?.signal_count || 0,
      paper_receipt_present: Boolean(paper),
      manual_outcome: manualReview.manual_outcome,
      manual_note_count: manualReview.manual_note_count,
      manual_execution_review_count: manualReview.manual_execution_review_count,
      manual_execution_decision: manualReview.manual_execution_audit?.summary?.decision,
      manual_handoff_only: true,
    },
  });
  if (!confirmed) return;
  const label = button?.textContent || "";
  if (button) {
    button.disabled = true;
    button.textContent = "记录中";
  }
  try {
    appendRunHistory({
      workflow_id: "post_close_journal",
      label: "收盘后复盘回执",
      status: "completed",
      detail: `${trade.run_date || template.run_date || "--"} / paper=${paper ? "yes" : "no"} / outcome=${manualReview.manual_outcome}`,
    });
    appendExecutionReceipt(postCloseJournalReceipt({
      trade,
      template,
      paper_receipt: paper,
      manual_review: manualReview,
      manual_execution_audit: manualReview.manual_execution_audit,
      decision: dailyReadinessDecision(),
    }));
    renderBeginnerPostCloseJournal();
    showToast("收盘后复盘回执已记录");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = label || "生成本地复盘回执";
    }
  }
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
  const dailyClosureLedger = control.daily_closure_ledger || {};
  const serverCapitalObservationGate = control.server_capital_observation_gate || {};
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
  byId("control-daily-closure-ledger").innerHTML = renderDailyClosureLedger(dailyClosureLedger);
  byId("control-server-capital-observation-gate").innerHTML = renderServerCapitalObservationGate(serverCapitalObservationGate);
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
      <span>${escapeHtml(item.status || "")} / ${escapeHtml(friendlyCommandText(item.command || ""))}</span>
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
      <span>${escapeHtml(item.status || "")} / ${escapeHtml(friendlyCommandText(item.command || ""))}</span>
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
  renderBeginnerTaskWizard();
  renderBeginnerTroubleshooter();
  renderBeginnerProgress();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  syncCurrentBacktestRuntimeGuard();
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
  const dailyTrade = state.dailyTradeAdvisory || {};
  const dailyTradeSummary = dailyTrade.summary || {};
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
  renderBeginnerTaskWizard();
  renderBeginnerTroubleshooter();
  renderBeginnerGuide();
  renderBeginnerProgress();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  renderFactorBeginnerExplainer(activeFactorBoard, activeFactorBoard.rows || []);
  byId("dashboard-equity-source").textContent = state.research?.data_source || valueOf("data-source-select") || state.snapshot?.data_mode || "local";
  byId("dashboard-metrics").innerHTML = [
    metric("项目状态", project.overall_status || "--", `阻塞 ${project.blocker_count ?? "--"}`),
    metric("因子总数", factorSummary.unique_factor_names ?? "--", "配置/报告/下拉框并集"),
    metric("候选记录", factorSummary.candidate_rows ?? "--", "历史参数组合"),
    metric("报告唯一因子", factorSummary.report_factor_names ?? "--", "本地报告"),
    metric("Top20", (factorLedger.top20 || []).length || "--", "排行榜"),
    metric("今日前三建议", dailyTradeSummary.signal_count ?? "--", dailyTradeSummary.manual_execution_required ? "人工复核" : "等待信号"),
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
    ["今日前三建议", `${dailyTradeSummary.signal_count ?? "--"} / factors ${dailyTradeSummary.selected_factor_count ?? "--"}`, dailyTradeSummary.signal_count > 0 ? "ok" : "warn"],
    ["今日执行边界", dailyTradeSummary.order_placement_allowed ? "允许下单" : "禁止自动下单；仅人工复核", "danger"],
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
    ["排序依据", leaderboardRankingBasisText(summary.ranking_basis || "--"), "muted"],
    ["跳过文件", `${summary.report_files_skipped ?? 0}`, summary.report_files_skipped > 0 ? "warn" : "ok"],
  ]);
  renderFactorBeginnerExplainer(activeBoard, rows);
  byId("factor-leaderboard-table").innerHTML = renderFactorLeaderboardTable(rows);
  syncCurrentBacktestRuntimeGuard();
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

function leaderboardMetricLabel(metric = "") {
  const labels = {
    sharpe: "夏普",
    total_return: "总收益",
    annualized_return: "年化收益",
    max_drawdown: "最大回撤",
    win_rate: "胜率",
    rank_ic: "RankIC",
    mean_ic: "平均IC",
    paper_sharpe: "模拟盘夏普",
    walk_forward_sharpe: "走前夏普",
    oos_sharpe: "样本外夏普",
    test_sharpe: "测试夏普",
    score: "综合分",
  };
  const key = String(metric || "").toLowerCase();
  return labels[key] || String(metric || "--").replaceAll("_", " ");
}

function leaderboardQualityText(value = "") {
  const normalized = String(value || "").toLowerCase();
  const labels = {
    qualified: "合格",
    ok: "正常",
    rejected: "已拒绝",
    thin_sample: "样本偏薄",
    missing_metric: "缺少指标",
    no_score: "无评分",
  };
  return labels[normalized] || zhConsoleText(value || "--");
}

function leaderboardReasonText(value = "") {
  return String(zhConsoleText(value || ""))
    .replaceAll("sharpe=", "夏普=")
    .replaceAll("rank_ic=", "RankIC=")
    .replaceAll("total_return=", "总收益=")
    .replaceAll("annualized_return=", "年化收益=")
    .replaceAll("max_drawdown=", "最大回撤=")
    .replaceAll("win_rate=", "胜率=")
    .replaceAll("qualified", "合格")
    .replaceAll("ok", "正常");
}

function leaderboardRankingBasisText(value = "") {
  const raw = String(value || "");
  if (raw.toLowerCase().includes("qualified rows first")) {
    return "先看合格候选，再按模拟盘/走前/样本外/测试夏普、夏普、RankIC、平均IC、综合分、总收益排序。";
  }
  return leaderboardReasonText(raw)
    .replaceAll("paper/walk-forward/oos/test sharpe", "模拟盘/走前/样本外/测试夏普")
    .replaceAll("sharpe", "夏普")
    .replaceAll("rank IC", "RankIC")
    .replaceAll("mean IC", "平均IC")
    .replaceAll("score", "综合分")
    .replaceAll("total return", "总收益");
}

function leaderboardParamsText(row = {}) {
  const payload = leaderboardRowPayload(row);
  const pieces = [
    payload.factor_windows ? `窗口=${payload.factor_windows}` : "",
    payload.top_n ? `TopN=${payload.top_n}` : "",
    payload.cost_bps ? `成本=${payload.cost_bps}bps` : "",
    payload.rebalance_interval ? `调仓=${payload.rebalance_interval}` : "",
    payload.execution_lag ? `执行滞后=${payload.execution_lag}` : "",
    payload.forward_horizon ? `预测=${payload.forward_horizon}` : "",
    payload.start_date && payload.end_date ? `日期=${payload.start_date} 至 ${payload.end_date}` : "",
  ].filter(Boolean);
  return pieces.join(" / ") || "--";
}

function leaderboardScoreText(row = {}) {
  const metric = leaderboardMetricLabel(row.score_metric || "--");
  return `${metric}=${formatDecimal(row.primary_score)}`;
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
  const reasons = leaderboardReasonText((row.ranking_reasons || []).join(" / ") || row.ranking_quality || "暂无额外风险说明");
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
          ["为什么排这里", `${leaderboardScoreText(row)} / ${leaderboardQualityText(row.ranking_quality)}`, tone],
          ["需要注意", reasons, tone === "ok" ? "warn" : tone],
        ])}
      </div>
      <div class="factor-beginner-actions">
        <button class="secondary-button" type="button" data-factor-beginner-jump="factor-leaderboard-table">看完整排行榜</button>
        <button class="primary-button" type="button" data-beginner-action="research_backtest" ${runtimeGuardAttr("research_backtest")}>本地回测当前参数</button>
      </div>
    </div>
  `;
}

function renderFactorLeaderboardTable(rows) {
  const head = `
    <tr>
      <th>排名</th>
      <th>因子 / 编号</th>
      <th>市场</th>
      <th>总收益</th>
      <th>年化</th>
      <th>夏普</th>
      <th>最大回撤</th>
      <th>胜率</th>
      <th>排序相关性</th>
      <th>交易数</th>
      <th>参数</th>
      <th>质量</th>
      <th>排序依据</th>
      <th>来源</th>
      <th>全部数据</th>
    </tr>
  `;
  const body = rows.map((row) => {
    const params = leaderboardParamsText(row);
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
        <td><code>${escapeHtml(params)}</code></td>
        <td>${escapeHtml(leaderboardQualityText(row.ranking_quality))}<br><span class="muted">${escapeHtml(leaderboardReasonText((row.ranking_reasons || []).join(" / ") || "ok"))}</span></td>
        <td>${escapeHtml(leaderboardScoreText(row))}</td>
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
  renderBeginnerTaskWizard();
  renderBeginnerTroubleshooter();
  renderBeginnerProgress();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  renderDailyCommandRail();
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
      next: {
        id: "repair",
        title: "先处理阻断项",
        plain: "打开修复队列，先看为什么不能推进模拟盘。",
        button: "看阻断与修复队列",
        target: "control-audit-repair-queue",
      },
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
  if (next.action === "research_backtest") {
    button.dataset.runtimeGuard = "research_backtest";
  } else {
    delete button.dataset.runtimeGuard;
    button.dataset.runtimeGuardState = "ready";
    button.classList.remove("runtime-guarded-action");
    button.disabled = false;
  }
  syncCurrentBacktestRuntimeGuard();
}

function renderBeginnerTradeSystem() {
  const summaryTarget = byId("beginner-trade-system-summary");
  const evidenceTarget = byId("beginner-trade-system-evidence");
  const actionsTarget = byId("beginner-trade-system-actions");
  if (!summaryTarget || !evidenceTarget || !actionsTarget) return;
  renderBeginnerTradeActionCard();
  renderBeginnerPretradeReceiptCard();
  renderBeginnerLivePilotBrief();
  renderBeginnerTradeSystemCapitalLadder();
  const decision = dailyReadinessDecision();
  const trade = state.dailyTradeAdvisory || {};
  const tradeSystem = trade.trade_system || {};
  const systemDecision = tradeSystem.go_live_decision || {};
  const readiness = trade.pretrade_readiness || {};
  const summary = trade.summary || {};
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  summaryTarget.innerHTML = statusRows([
    ["最终结论", decision.title || "等待今日体检", decision.tone || "warn"],
    ["原因", decision.reason || "先运行开盘前一键体检，再看是否进入人工复核。", decision.tone || "warn"],
    ["交易边界", systemDecision.status || "manual_review_only", "danger"],
    ["主线市场", tradeSystem.primary_market || "CN_ETF", "ok"],
  ]);
  evidenceTarget.innerHTML = beginnerTradeSystemEvidenceRows(trade, paperReceipt).map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.value)}</span>
      <span>${escapeHtml(item.detail)}</span>
    </div>
  `).join("");
  actionsTarget.innerHTML = beginnerTradeSystemActionRows(decision, readiness, summary, paperReceipt).map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <span class="beginner-task-actions">
        ${item.workflow ? `<button class="primary-button" type="button" data-trade-system-action="${escapeRawHtml(item.workflow)}">${escapeHtml(item.button)}</button>` : ""}
        ${item.target ? `<button class="secondary-button" type="button" data-trade-system-target="${escapeRawHtml(item.target)}">${escapeHtml(item.target_label || "看证据")}</button>` : ""}
      </span>
    </div>
  `).join("");
}

function renderBeginnerTradeSystemCapitalLadder() {
  const target = byId("beginner-trade-system-capital-ladder");
  if (!target) return;
  const gate = state.dailyTradeAdvisory?.real_world_manual_handoff_gate || {};
  const ladder = Array.isArray(gate.capital_deployment_ladder) ? gate.capital_deployment_ladder : [];
  if (!ladder.length) {
    target.innerHTML = statusRows([["资金阶段", "等待今日交易系统加载，先生成今日前三建议。", "warn"]]);
    return;
  }
  target.innerHTML = ladder.map((item) => {
    const status = item.status || "waiting";
    const tone = status.includes("done") ? "ok" : status.includes("locked") || status.includes("blocked") ? "danger" : "warn";
    const gateText = [
      item.minimum_matched_paper_receipts != null ? `模拟盘≥${formatNumber(item.minimum_matched_paper_receipts)}` : "",
      item.minimum_post_close_journals != null ? `复盘≥${formatNumber(item.minimum_post_close_journals)}` : "",
      item.minimum_paper_ready_observations != null ? `观察≥${formatNumber(item.minimum_paper_ready_observations)}` : "",
    ].filter(Boolean).join(" / ");
    const actionButton = item.workflow_id ? `
      <button class="primary-button" type="button" data-trade-system-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>
    ` : "";
    const targetButton = item.target_id ? `
      <button class="secondary-button" type="button" data-trade-system-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>
    ` : "";
    return `
      <div class="list-row ${escapeHtml(tone)}">
        <strong>${escapeHtml(`${item.stage_number || "--"}. ${item.label || item.stage_id || ""}`)}</strong>
        <span>${escapeHtml(`${zhConsoleText(status)} / ${item.capital_mode || ""}`)}</span>
        <span>${escapeHtml(gateText || item.plain_requirement || "")}</span>
        <span class="beginner-task-actions">${actionButton}${targetButton}</span>
      </div>
    `;
  }).join("");
}

function renderBeginnerTradeActionCard() {
  const target = byId("beginner-trade-action-card");
  if (!target) return;
  const card = state.dailyTradeAdvisory?.beginner_trade_action_card || {};
  const summary = card.summary || {};
  const next = card.next_action || {};
  const tone = summary.answer_code === "no" ? "danger" : summary.answer_code === "ready" ? "ok" : "warn";
  const rows = beginnerTradeActionCardRows(card);
  target.innerHTML = [
    `
      <div class="list-row ${escapeHtml(tone)}">
        <strong>${escapeHtml(summary.plain_answer || "先生成今日建议，再判断能不能进入人工复核。")}</strong>
        <span>${escapeHtml(summary.why || "等待今日交易系统给出普通人可读结论。")}</span>
        <span class="beginner-task-actions">
          ${next.workflow_id ? `<button class="primary-button" type="button" data-beginner-trade-action-workflow="${escapeRawHtml(next.workflow_id)}">${escapeHtml(next.button_label || "运行下一步")}</button>` : ""}
          ${next.target_id ? `<button class="secondary-button" type="button" data-beginner-trade-action-target="${escapeRawHtml(next.target_id)}">${escapeHtml(next.workflow_id ? "看证据" : next.button_label || "看证据")}</button>` : ""}
        </span>
      </div>
    `,
    ...rows.map((item) => `
      <div class="list-row ${escapeHtml(item.tone)}">
        <strong>${escapeHtml(item.label)}</strong>
        <span>${escapeHtml(item.value)}</span>
        <span>${escapeHtml(item.detail)}</span>
      </div>
    `),
  ].join("");
}

function beginnerTradeActionCardRows(card = {}) {
  const summary = card.summary || {};
  const evidence = card.evidence || {};
  const checklist = Array.isArray(card.plain_checklist) ? card.plain_checklist : [];
  const blockers = Array.isArray(evidence.blockers) ? evidence.blockers : [];
  const checklistText = checklist
    .slice(0, 6)
    .map((item) => `${item.label || item.check_id || "--"}=${zhConsoleText(item.status || "waiting")}`)
    .join(" / ");
  return [
    {
      label: "今天结论",
      value: zhConsoleText(summary.recommended_mode || summary.answer_code || "waiting"),
      detail: summary.can_manual_review_today ? "可进入人工复核，但仍必须先看模拟盘和风险。" : "还不能进入人工复核或买入。",
      tone: summary.answer_code === "no" ? "danger" : "warn",
    },
    {
      label: "证据数量",
      value: `因子=${formatNumber(evidence.selected_factor_count || 0)} / 信号=${formatNumber(evidence.signal_count || 0)} / 票据=${formatNumber(evidence.manual_ticket_count || 0)}`,
      detail: `灯号=${zhConsoleText(evidence.traffic_light || "unknown")} / 阻断=${blockers.length ? blockers.join(", ") : "无"}`,
      tone: blockers.length ? "danger" : "warn",
    },
    {
      label: "检查清单",
      value: checklistText || "等待生成今日检查清单",
      detail: "先按清单补齐证据；不要把前三因子直接当成买入指令。",
      tone: blockers.length ? "danger" : "warn",
    },
    {
      label: "安全边界",
      value: summary.auto_order_allowed ? "异常：允许自动下单" : "不自动下单",
      detail: "软件只输出研究、模拟盘和人工复核材料；券商端动作必须由人另行决定。",
      tone: summary.auto_order_allowed ? "danger" : "ok",
    },
  ];
}

function renderBeginnerPretradeReceiptCard() {
  const target = byId("beginner-pretrade-receipt-card");
  if (!target) return;
  const receipt = latestExecutionReceipt("daily_pretrade_checkup");
  if (!receipt) {
    target.innerHTML = `
      <div class="list-row warn">
        <strong>${escapeHtml("还没有开盘前体检回执")}</strong>
        <span>${escapeHtml("先运行开盘前一键体检，软件会把 daily_ops 和今日前三建议合成一张本地回执。")}</span>
        <span class="beginner-task-actions">
          <button class="secondary-button" type="button" data-beginner-pretrade-receipt-target="control-command-deck">${escapeHtml("去运行体检")}</button>
        </span>
      </div>
    `;
    return;
  }
  const rows = beginnerPretradeReceiptRows(receipt);
  target.innerHTML = rows.map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.value)}</span>
      <span>${escapeHtml(item.detail)}</span>
      ${item.target ? `<span class="beginner-task-actions"><button class="secondary-button" type="button" data-beginner-pretrade-receipt-target="${escapeRawHtml(item.target)}">${escapeHtml(item.button || "看证据")}</button></span>` : ""}
    </div>
  `).join("");
}

function beginnerPretradeReceiptRows(receipt = {}) {
  const metrics = receipt.metrics || {};
  const request = receipt.request || {};
  const blockerCount = Number(metrics.blocker_count || 0);
  const trafficLight = metrics.traffic_light || "unknown";
  const tone = blockerCount > 0 || trafficLight === "red" ? "danger" : "warn";
  return [
    {
      label: "最近体检回执",
      value: `${receipt.time || "--"} / ${receipt.workflow_id || "daily_pretrade_checkup"}`,
      detail: receipt.decision || "等待开盘前体检结论",
      target: "daily-pretrade-readiness-verdict",
      button: "看体检结论",
      tone,
    },
    {
      label: "体检做了什么",
      value: request.workflow || "daily_ops + daily_trade_advisory",
      detail: `市场=${request.market || "CN_ETF"} / 日期=${request.as_of_date || "--"} / 自动跑模拟盘=${request.paper_simulation_auto_run ? "是" : "否"}`,
      target: "daily-evidence-chain",
      button: "看闭环证据",
      tone: "warn",
    },
    {
      label: "关键结果",
      value: `灯号=${zhConsoleText(trafficLight)} / 阻断=${formatNumber(blockerCount)} / 票据=${formatNumber(metrics.manual_ticket_count || 0)}`,
      detail: `信号=${formatNumber(metrics.signal_count || 0)} / 可复制票据=${formatNumber(metrics.copyable_ticket_count || 0)}`,
      target: blockerCount > 0 ? "daily-pretrade-readiness-status" : "daily-manual-broker-handoff-ticket-table",
      button: blockerCount > 0 ? "看阻断项" : "看人工票据",
      tone,
    },
    {
      label: "安全边界",
      value: "pretrade_receipt_only",
      detail: receipt.safety || "本地体检回执，只做人工复核；不连接券商、不读账户、不自动下单。",
      target: "control-safety-boundary",
      button: "看安全边界",
      tone: "ok",
    },
  ];
}

function renderDailyCommandRail() {
  const statusTarget = byId("daily-command-rail-status");
  const actionsTarget = byId("daily-command-rail-actions");
  if (!statusTarget || !actionsTarget) return;
  const trade = state.dailyTradeAdvisory || {};
  const brief = trade.daily_live_pilot_brief || {};
  const briefSummary = brief.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const rows = dailyCommandRailRows();
  const next = rows.find((row) => row.workflow && row.tone !== "ok") || rows.find((row) => row.tone !== "ok") || rows[0] || {};
  const ticketText = tickets.length
    ? tickets.slice(0, 3).map((ticket) => `${ticket.asset_id || "--"} ${zhConsoleText(ticket.side || "")} ${formatNumber(ticket.rounded_quantity || 0)}份`).join("；")
    : "暂无人工票据";
  statusTarget.innerHTML = statusRows([
    ["主路径", "每日交易主路径：前三因子 -> 体检 -> 模拟盘 -> 人工票据 -> 盘后复盘", "warn"],
    ["当前结论", briefSummary.plain_answer || dailyReadinessDecision().title || "等待今日交易建议加载", blockers.length ? "danger" : "warn"],
    ["今天买什么", ticketText, tickets.length && blockers.length === 0 ? "warn" : "danger"],
    ["下一步", next.title || "先生成今日前三建议", next.tone || "warn"],
    ["安全边界", "不连接券商、不读取账户、不自动下单；券商端动作必须由人手工决定。", "danger"],
  ]);
  actionsTarget.innerHTML = rows.map((row, index) => `
    <div class="list-row ${escapeHtml(row.tone)}">
      <strong>${escapeHtml(`${index + 1}. ${row.title}`)}</strong>
      <span>${escapeHtml(row.value)}</span>
      <span>${escapeHtml(row.detail)}</span>
      <span class="beginner-task-actions">
        ${row.workflow ? `<button class="primary-button" type="button" data-daily-command-action="${escapeRawHtml(row.workflow)}">${escapeHtml(row.button || "运行")}</button>` : ""}
        ${row.target ? `<button class="secondary-button" type="button" data-daily-command-target="${escapeRawHtml(row.target)}">${escapeHtml(row.targetLabel || "看证据")}</button>` : ""}
      </span>
    </div>
  `).join("");
}

function dailyCommandRailRows() {
  const trade = state.dailyTradeAdvisory || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const freshness = readiness.freshness || {};
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const selectedCount = Number(summary.selected_factor_count || 0);
  const signalCount = Number(summary.signal_count || 0);
  const targetCount = Number(summary.combined_target_count ?? trade.combined_target_count ?? 0);
  const pretradeReceipt = latestExecutionReceipt("daily_pretrade_checkup");
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const journalReceipt = latestExecutionReceipt("post_close_journal");
  const signalFreshText = freshness.latest_signal_date
    ? `运行日=${freshness.run_date || trade.run_date || "--"} / 最新信号=${freshness.latest_signal_date}`
    : `运行日=${trade.run_date || "--"}`;
  return [
    {
      title: "生成今日前三因子和信号",
      value: signalCount > 0 ? `${formatNumber(signalCount)} 条信号 / ${formatNumber(selectedCount)} 个因子` : "还没有今日前三信号",
      detail: signalCount > 0 ? `${signalFreshText} / 目标ETF=${formatNumber(targetCount)}` : "每天先从 CN_ETF 可运行候选里取前三，并生成当日目标 ETF。",
      workflow: signalCount > 0 ? "" : "daily_trade_advisory",
      button: "生成今日前三建议",
      target: "daily-trade-factor-table",
      targetLabel: "看前三因子",
      tone: signalCount > 0 ? "ok" : "warn",
    },
    {
      title: "开盘前一键体检",
      value: pretradeReceipt ? `已有体检回执 ${pretradeReceipt.time || "--"}` : `灯号=${zhConsoleText(readiness.traffic_light || "未体检")}`,
      detail: pretradeReceipt ? "体检会把日常运营、今日前三、红黄灯和人工票据合成一张本地回执。" : "先跑体检，再谈今天能不能进入人工复核。",
      workflow: pretradeReceipt ? "" : "daily_pretrade_checkup",
      button: "跑开盘前体检",
      target: blockers.length ? "daily-pretrade-readiness-status" : "daily-pretrade-readiness-verdict",
      targetLabel: blockers.length ? "看红灯阻断" : "看体检结论",
      tone: blockers.length ? "danger" : pretradeReceipt ? "ok" : "warn",
    },
    {
      title: "模拟盘复核",
      value: paperReceipt ? `收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}` : "还没有模拟盘回执",
      detail: "真实买卖前先看同一套参数的收益、回撤、胜率、成交和保护事件。",
      workflow: signalCount > 0 && !paperReceipt ? "paper_simulation" : "",
      button: "跑模拟盘",
      target: "paper-metrics",
      targetLabel: "看模拟盘",
      tone: paperReceipt ? "ok" : signalCount > 0 ? "warn" : "danger",
    },
    {
      title: "人工票据核对",
      value: tickets.length ? `${formatNumber(tickets.length)} 张票据 / 自动下单=禁止` : "还没有可核对票据",
      detail: tickets.length ? "只作为人工核对清单：ETF代码、方向、参考价、数量、金额、现金和风险都要再确认。" : "没有票据时不能进入券商端人工操作。",
      workflow: "",
      target: tickets.length ? "daily-manual-broker-handoff-ticket-table" : "daily-trade-factor-table",
      targetLabel: tickets.length ? "看人工票据" : "看信号",
      tone: tickets.length && blockers.length === 0 ? "warn" : "danger",
    },
    {
      title: "收盘后复盘",
      value: journalReceipt ? `已有复盘回执 ${journalReceipt.time || "--"}` : "还没有盘后复盘回执",
      detail: "记录今天执行、跳过、偏差、回撤、保护事件和明天要复核的问题，反哺因子审计。",
      workflow: signalCount > 0 && !journalReceipt ? "post_close_journal" : "",
      button: "写盘后复盘",
      target: "beginner-post-close-journal-board",
      targetLabel: "看复盘",
      tone: journalReceipt ? "ok" : signalCount > 0 ? "warn" : "warn",
    },
  ];
}

async function runDailyCommandRailAction(actionId, button = null) {
  if (!actionId) return;
  await runBeginnerAction(actionId, button);
  renderDailyCommandRail();
}

function renderBeginnerLivePilotBrief() {
  const target = byId("beginner-live-pilot-brief");
  if (!target) return;
  const brief = state.dailyTradeAdvisory?.daily_live_pilot_brief || {};
  const rows = beginnerLivePilotBriefRows(brief)
    .concat(smallCapitalObservationDecisionRow(brief))
    .concat(beginnerLivePilotEvidenceRows(brief))
    .concat(beginnerSmallCapitalGateRows(brief));
  target.innerHTML = rows.map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.value)}</span>
      <span>${escapeHtml(item.detail)}</span>
      <span class="beginner-task-actions">
        ${item.workflow ? `<button class="primary-button" type="button" data-beginner-live-pilot-action="${escapeRawHtml(item.workflow)}">${escapeHtml(item.button || "运行")}</button>` : ""}
        ${item.target ? `<button class="secondary-button" type="button" data-beginner-live-pilot-target="${escapeRawHtml(item.target)}">${escapeHtml(item.targetLabel || "看证据")}</button>` : ""}
      </span>
    </div>
  `).join("");
}

function beginnerLivePilotBriefRows(brief = {}) {
  const summary = brief.summary || {};
  const signalRule = brief.today_signal_rule || {};
  const steps = Array.isArray(brief.manual_operation_steps) ? brief.manual_operation_steps : [];
  const tickets = Array.isArray(brief.manual_ticket_preview) ? brief.manual_ticket_preview : [];
  const risk = brief.risk_budget || {};
  const boundary = brief.execution_boundary || {};
  const blockers = Array.isArray(brief.blockers) ? brief.blockers : [];
  const firstRequired = steps.find((item) => item.status === "blocked" || item.status === "required" || item.status === "waiting") || steps[0] || {};
  const ticketText = tickets.length
    ? tickets.slice(0, 3).map((item) => `${item.asset_id || "--"} ${zhConsoleText(item.side || "")} ${formatPercent(item.target_weight)} / ${formatNumber(item.rounded_quantity || 0)}份`).join("；")
    : "暂无可人工核对票据";
  const status = summary.status || "waiting_for_daily_signal";
  const tone = blockers.length || status.includes("blocked") ? "danger" : status.includes("candidate") ? "warn" : "warn";
  return [
    {
      label: "实盘前简报",
      value: summary.plain_answer || "等待今日实盘前操作简报",
      detail: summary.primary_action || "先生成今日前三建议，再跑盘前体检。",
      workflow: firstRequired.workflow_id || "",
      target: firstRequired.gui_target || "beginner-live-handoff-board",
      button: firstRequired.workflow_id ? firstRequired.title || "运行下一步" : "",
      targetLabel: "看下一步",
      tone,
    },
    {
      label: "前三因子规则",
      value: `${summary.today_signal_count || 0}条信号 / ${summary.manual_ticket_count || 0}张票据`,
      detail: signalRule.plain_warning || "不能把前三因子直接当买入指令；必须经过复核。",
      target: "daily-trade-factor-table",
      targetLabel: "看前三因子",
      tone: summary.today_signal_count > 0 ? "warn" : "danger",
    },
    {
      label: "今天买什么",
      value: ticketText,
      detail: "这是人工核对清单，不是订单；券商端价格、现金和风险仍需本人确认。",
      target: tickets.length ? "daily-manual-broker-handoff-ticket-table" : "daily-trade-factor-table",
      targetLabel: tickets.length ? "看人工票据" : "看信号",
      tone: tickets.length && !blockers.length ? "warn" : "danger",
    },
    {
      label: "风险预算",
      value: `${risk.risk_profile_label || risk.risk_profile_id || "未选择"} / 总仓位=${formatPercent(risk.applied_max_gross_exposure)} / 单ETF=${formatPercent(risk.max_single_etf_weight)}`,
      detail: risk.plain_review || "收益高也不能跳过回撤、仓位、流动性和价格偏差核对。",
      target: "daily-pretrade-readiness-verdict",
      targetLabel: "看风险",
      tone: "warn",
    },
    {
      label: "操作边界",
      value: boundary.auto_order_allowed ? "异常：允许自动下单" : "不自动下单",
      detail: boundary.plain_boundary || "券商端由人手工决定；软件只生成研究、模拟盘和人工复核材料。",
      target: "control-safety-boundary",
      targetLabel: "看边界",
      tone: boundary.auto_order_allowed ? "danger" : "ok",
    },
  ];
}

function beginnerLivePilotEvidenceRows(brief = {}) {
  const summary = brief.summary || {};
  const boundary = brief.execution_boundary || {};
  const blockers = Array.isArray(brief.blockers) ? brief.blockers : [];
  const tickets = Array.isArray(brief.manual_ticket_preview) ? brief.manual_ticket_preview : [];
  const pretradeReceipt = latestExecutionReceipt("daily_pretrade_checkup");
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const journalReceipt = latestExecutionReceipt("post_close_journal");
  const missing = [];
  if (blockers.length) missing.push(`盘前红灯阻断=${blockers.join("/")}`);
  if (!pretradeReceipt) missing.push("缺开盘前体检回执");
  if (!paperReceipt) missing.push("缺模拟盘回执");
  if (!journalReceipt) missing.push("缺盘后复盘回执");
  if (!tickets.length) missing.push("缺人工票据");
  missing.push("小资金观察闸门仍未打开");
  let workflow = "";
  let target = "beginner-live-handoff-board";
  if (!pretradeReceipt) {
    workflow = "daily_pretrade_checkup";
    target = "beginner-trade-system-board";
  } else if (!paperReceipt) {
    workflow = "paper_simulation";
    target = "paper-metrics";
  } else if (!journalReceipt) {
    workflow = "post_close_journal";
    target = "beginner-post-close-journal-board";
  } else if (blockers.length) {
    target = "daily-pretrade-readiness-status";
  } else {
    target = "control-operation-ledger";
  }
  const receiptTone = pretradeReceipt && paperReceipt && journalReceipt ? "ok" : "warn";
  return [
    {
      label: "离实盘还差什么",
      value: `还差 ${formatNumber(missing.length)} 项`,
      detail: missing.slice(0, 5).join("；"),
      workflow,
      target,
      button: workflow ? "补这一项" : "",
      targetLabel: "看证据",
      tone: missing.length > 1 || blockers.length ? "danger" : "warn",
    },
    {
      label: "本机回执",
      value: `体检=${pretradeReceipt ? "有" : "无"} / 模拟盘=${paperReceipt ? "有" : "无"} / 复盘=${journalReceipt ? "有" : "无"}`,
      detail: "这些回执只证明本机流程跑过，不证明真实账户已经可交易。",
      target: "control-execution-receipts",
      targetLabel: "看回执",
      tone: receiptTone,
    },
    {
      label: "小资金观察",
      value: summary.status === "manual_review_candidate" ? "可准备观察材料" : "还不能进入",
      detail: "小资金观察闸门仍未打开；必须先积累模拟盘、盘后复盘、风险和人工票据证据。",
      target: "beginner-live-handoff-board",
      targetLabel: "看交接",
      tone: "warn",
    },
    {
      label: "权限复核",
      value: boundary.order_placement_allowed || boundary.broker_connection_allowed ? "异常：权限越界" : "仍是研究到模拟盘",
      detail: "系统仍然不连接券商、不读取账户、不生成实盘委托；任何券商动作必须由人手工决定。",
      target: "control-safety-boundary",
      targetLabel: "看边界",
      tone: boundary.order_placement_allowed || boundary.broker_connection_allowed ? "danger" : "ok",
    },
  ];
}

function smallCapitalObservationDecisionRow(brief = {}) {
  const gate = brief.small_capital_observation_gate || {};
  const card = gate.decision_card || {};
  const gateRows = beginnerSmallCapitalGateRows(brief);
  const missingGateCount = gateRows.filter((row) => row.tone !== "ok").length;
  const completedGateCount = gateRows.length - missingGateCount;
  const firstMissing = gateRows.find((row) => row.tone !== "ok") || {};
  const progressText = `小资金观察进度 ${formatNumber(completedGateCount)}/${formatNumber(gateRows.length)}`;
  const nextLabel = firstMissing.label || card.next_step_label || "补齐证据";
  const ready = missingGateCount === 0 && gateRows.length > 0;
  const workflow = ready ? "" : firstMissing.workflow || card.next_workflow_id || "";
  const target = ready ? "control-safety-boundary" : firstMissing.target || card.next_gui_target || "beginner-live-handoff-board";
  return [{
    label: card.title || "今天能不能小资金观察",
    value: ready ? `${progressText} / 证据已齐，仍需人工确认` : `${progressText} / 还差 ${formatNumber(missingGateCount)} 项`,
    detail: ready
      ? "可准备小资金人工观察材料，但软件仍不连接券商、不读取账户、不自动下单。"
      : `${card.plain_answer || "还不能小资金观察：先补齐模拟盘、盘后复盘和风险证据。"} 下一步：${nextLabel}`,
    workflow,
    target,
    button: workflow ? card.next_step_label || "补下一项" : "",
    targetLabel: ready ? "看安全边界" : "看下一步",
    tone: ready ? "ok" : "warn",
  }];
}

function beginnerSmallCapitalGateRows(brief = {}) {
  const risk = brief.risk_budget || {};
  const boundary = brief.execution_boundary || {};
  const blockers = Array.isArray(brief.blockers) ? brief.blockers : [];
  const tickets = Array.isArray(brief.manual_ticket_preview) ? brief.manual_ticket_preview : [];
  const specRows = smallCapitalGateSpecRows(brief);
  const paperReceipts = executionReceiptsForWorkflow("paper_simulation");
  const journalReceipts = executionReceiptsForWorkflow("post_close_journal");
  const latestPaper = paperReceipts[0] || latestExecutionReceipt("paper_simulation");
  const paperMetrics = latestPaper?.metrics || {};
  const drawdownBudget = Number(risk.max_acceptable_drawdown ?? risk.max_drawdown_limit ?? 0.2);
  const observedDrawdown = Math.abs(Number(paperMetrics.max_drawdown));
  const guardEvents = Number(paperMetrics.guard_event_count);
  const fillCount = Number(paperMetrics.fill_count);
  const boundaryUnlocked = Boolean(
    boundary.auto_order_allowed ||
    boundary.order_placement_allowed ||
    boundary.broker_connection_allowed
  );
  const gateContext = {
    paperReceipts,
    journalReceipts,
    observedDrawdown,
    guardEvents,
    fillCount,
    tickets,
    blockers,
    boundaryUnlocked,
  };
  const gates = specRows.length ? specRows.map((row) => smallCapitalGateFromSpec(row, gateContext)) : [
    {
      label: "模拟盘观察次数",
      current: paperReceipts.length,
      required: 5,
      pass: paperReceipts.length >= 5,
      detail: "至少 5 次模拟盘和复盘回执，避免把单日表现当规律。",
      target: "paper-metrics",
      workflow: "paper_simulation",
    },
    {
      label: "盘后复盘次数",
      current: journalReceipts.length,
      required: 5,
      pass: journalReceipts.length >= 5,
      detail: "至少 5 次模拟盘和复盘回执，记录跳过、执行、偏差和情绪原因。",
      target: "beginner-post-close-journal-board",
      workflow: "post_close_journal",
    },
    {
      label: "最大回撤预算",
      current: Number.isFinite(observedDrawdown) ? observedDrawdown : null,
      required: Number.isFinite(drawdownBudget) ? drawdownBudget : 0.2,
      pass: Number.isFinite(observedDrawdown) && observedDrawdown <= (Number.isFinite(drawdownBudget) ? drawdownBudget : 0.2),
      detail: "最新模拟盘最大回撤必须低于当前风险档位，收益高也不能绕过回撤预算。",
      target: "paper-metrics",
      valueType: "percent",
      comparator: "<=",
    },
    {
      label: "保护事件",
      current: Number.isFinite(guardEvents) ? guardEvents : null,
      required: 0,
      pass: Number.isFinite(guardEvents) && guardEvents === 0,
      detail: "最新模拟盘不应触发风控保护事件；触发过就先复盘原因。",
      target: "paper-metrics",
      comparator: "=",
    },
    {
      label: "成交样本",
      current: Number.isFinite(fillCount) ? fillCount : null,
      required: 1,
      pass: Number.isFinite(fillCount) && fillCount >= 1,
      detail: "模拟盘必须至少产生一次成交，空跑不能当小资金观察证据。",
      target: "paper-metrics",
      comparator: ">=",
    },
    {
      label: "人工票据和红灯",
      current: tickets.length,
      required: 1,
      pass: tickets.length > 0 && blockers.length === 0,
      detail: blockers.length ? `仍有盘前红灯阻断：${blockers.join(" / ")}` : "人工票据存在且盘前无红灯阻断。",
      target: "daily-manual-broker-handoff-ticket-table",
      comparator: ">=",
    },
    {
      label: "权限边界",
      current: boundaryUnlocked ? 1 : 0,
      required: 0,
      pass: !boundaryUnlocked,
      detail: "系统仍必须保持无券商、无账户、无下单权限；真实买卖只能人工决定。",
      target: "control-safety-boundary",
      comparator: "=",
    },
  ];
  return gates.map((gate) => {
    const currentText = gate.valueType === "percent"
      ? formatPercent(gate.current)
      : gate.valueType === "boolean" ? (gate.current ? "是" : "否") : gate.current == null ? "--" : formatNumber(gate.current);
    const requiredText = gate.valueType === "percent"
      ? `${gate.comparator || ">="}${formatPercent(gate.required)}`
      : gate.valueType === "boolean" ? `${gate.comparator || "="}${gate.required ? "是" : "否"}` : `${gate.comparator || ">="}${formatNumber(gate.required)}`;
    return {
      label: gate.label,
      value: `${currentText} / 要求${requiredText}`,
      detail: gate.detail,
      workflow: gate.pass ? "" : gate.workflow || "",
      target: gate.target,
      button: gate.pass ? "" : gate.workflow ? "补证据" : "",
      targetLabel: gate.pass ? "看证据" : "去处理",
      tone: gate.pass ? "ok" : "warn",
    };
  });
}

function smallCapitalGateSpecRows(brief = {}) {
  const gate = brief.small_capital_observation_gate || {};
  return Array.isArray(gate.gate_rows) ? gate.gate_rows : [];
}

function smallCapitalGateFromSpec(row = {}, context = {}) {
  const gateId = row.gate_id || "";
  const required = row.required_value;
  const comparator = row.comparator || ">=";
  const base = {
    label: row.label || gateId || "小资金观察门槛",
    required,
    comparator,
    detail: row.plain_requirement || "按小资金观察闸门补齐证据。",
    target: row.gui_target || "beginner-live-handoff-board",
    workflow: row.workflow_id || "",
    valueType: gateId === "latest_paper_drawdown" ? "percent" : typeof required === "boolean" ? "boolean" : "",
  };
  if (gateId === "paper_simulation_receipts") {
    const current = context.paperReceipts?.length ?? 0;
    return { ...base, current, pass: current >= Number(required || 0) };
  }
  if (gateId === "post_close_journal_receipts") {
    const current = context.journalReceipts?.length ?? 0;
    return { ...base, current, pass: current >= Number(required || 0) };
  }
  if (gateId === "latest_paper_drawdown") {
    const current = context.observedDrawdown;
    return { ...base, current: Number.isFinite(current) ? current : null, pass: Number.isFinite(current) && current <= Number(required) };
  }
  if (gateId === "latest_paper_guard_events") {
    const current = context.guardEvents;
    return { ...base, current: Number.isFinite(current) ? current : null, pass: Number.isFinite(current) && current === Number(required || 0) };
  }
  if (gateId === "latest_paper_fills") {
    const current = context.fillCount;
    return { ...base, current: Number.isFinite(current) ? current : null, pass: Number.isFinite(current) && current >= Number(required || 0) };
  }
  if (gateId === "manual_ticket_and_red_light") {
    const current = context.tickets?.length ?? 0;
    return { ...base, current, pass: current > 0 && (context.blockers?.length ?? 0) === 0 };
  }
  if (gateId === "research_only_safety_boundary") {
    const current = Boolean(context.boundaryUnlocked);
    return { ...base, current, pass: !current, valueType: "boolean" };
  }
  return {
    ...base,
    current: null,
    pass: row.status === "ready" || row.status === "locked",
  };
}

function beginnerTradeSystemEvidenceRows(trade = {}, paperReceipt = null) {
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const freshness = readiness.freshness || {};
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  return [
    {
      label: "前三因子",
      value: `${formatNumber(summary.selected_factor_count || 0)} 个`,
      detail: "只从 CN_ETF 可运行候选里取，不把 CN 个股信号直接当 ETF 操作。",
      tone: Number(summary.selected_factor_count || 0) > 0 ? "ok" : "warn",
    },
    {
      label: "今日信号",
      value: `${formatNumber(summary.signal_count || 0)} 条`,
      detail: `运行日=${freshness.run_date || trade.run_date || "--"} / 最新信号=${freshness.latest_signal_date || "--"}`,
      tone: freshness.fresh_for_run_date ? "ok" : "danger",
    },
    {
      label: "模拟盘回执",
      value: paperReceipt ? "已有" : "缺失",
      detail: paperReceipt ? `最近回执=${paperReceipt.time || "--"}` : "还不能把单日信号当成可操作结论。",
      tone: paperReceipt ? "ok" : "warn",
    },
    {
      label: "人工票据",
      value: `${formatNumber(tickets.length)} 张`,
      detail: blockers.length ? `阻断=${blockers.join(" / ")}` : "票据只用于人工核对，系统不自动提交。",
      tone: tickets.length && blockers.length === 0 ? "warn" : "danger",
    },
  ];
}

function beginnerTradeSystemActionRows(decision = {}, readiness = {}, summary = {}, paperReceipt = null) {
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const rows = [
    {
      label: "下一步",
      detail: decision.detail || "先运行开盘前一键体检，再根据红黄灯处理。",
      workflow: decision.action_workflow || "daily_pretrade_checkup",
      target: decision.target_id || "beginner-live-handoff-board",
      button: decision.cta_label || "运行开盘前体检",
      target_label: "看对应证据",
      tone: decision.tone || "warn",
    },
  ];
  if (!paperReceipt && Number(summary.signal_count || 0) > 0 && blockers.length === 0) {
    rows.push({
      label: "缺口",
      detail: "有信号但没有模拟盘回执，先跑本地模拟盘复核收益、回撤和成交。",
      workflow: "paper_simulation",
      target: "paper-metrics",
      button: "跑模拟盘",
      target_label: "看模拟盘",
      tone: "warn",
    });
  }
  rows.push({
    label: "安全边界",
    detail: "软件只生成研究、信号、模拟和人工复核清单，不连接券商、不读账户、不下单。",
    target: "control-safety-boundary",
    target_label: "看安全边界",
    tone: "danger",
  });
  return rows;
}

function renderBeginnerDailyRehearsal() {
  const summaryTarget = byId("beginner-daily-rehearsal-summary");
  const timelineTarget = byId("beginner-daily-rehearsal-timeline");
  const actionsTarget = byId("beginner-daily-rehearsal-actions");
  if (!summaryTarget || !timelineTarget || !actionsTarget) return;
  const trade = state.dailyTradeAdvisory || {};
  const daybook = trade.daily_rehearsal_daybook || {};
  const summary = daybook.summary || {};
  const phases = beginnerDailyRehearsalRows(daybook);
  const current = phases.find((phase) => phase.current) || phases.find((phase) => phase.tone !== "ok") || phases[0] || {};
  summaryTarget.innerHTML = statusRows([
    ["今日阶段", current.title || summary.current_phase_title || "等待今日体检", current.tone || "warn"],
    ["进度", `${formatNumber(phases.filter((phase) => phase.tone === "ok").length)} / ${formatNumber(phases.length || summary.phase_count || 0)}`, current.tone || "warn"],
    ["主线市场", summary.primary_market || "CN_ETF", "ok"],
    ["安全边界", "本地研究、模拟盘、人工复核；不自动下单。", "danger"],
  ]);
  timelineTarget.innerHTML = phases.map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.title)}</span>
      <span>${escapeHtml(item.detail)}</span>
    </div>
  `).join("");
  actionsTarget.innerHTML = beginnerDailyRehearsalActionRows(phases, daybook).map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <span class="beginner-task-actions">
        ${item.workflow ? `<button class="primary-button" type="button" data-daily-rehearsal-action="${escapeRawHtml(item.workflow)}">${escapeHtml(item.button)}</button>` : ""}
        ${item.target ? `<button class="secondary-button" type="button" data-daily-rehearsal-target="${escapeRawHtml(item.target)}">${escapeHtml(item.targetLabel || "看证据")}</button>` : ""}
      </span>
    </div>
  `).join("");
}

function beginnerDailyRehearsalRows(daybook = {}) {
  const trade = state.dailyTradeAdvisory || {};
  const fallbackPhases = [
    {
      phase_id: "scope_and_data",
      phase_number: 1,
      title: "确认主线和数据日期",
      status: "waiting",
      evidence: "等待今日交易建议加载。",
    },
    {
      phase_id: "top3_signal_generation",
      phase_number: 2,
      title: "生成前三因子和今日信号",
      status: "waiting",
      evidence: "等待今日交易建议加载。",
    },
    {
      phase_id: "paper_simulation_review",
      phase_number: 3,
      title: "本地模拟盘复核",
      status: "required",
      evidence: "需要本地模拟盘回执。",
    },
    {
      phase_id: "risk_cash_review",
      phase_number: 4,
      title: "人工核对风险和现金",
      status: "waiting",
      evidence: "等待盘前体检结果。",
    },
    {
      phase_id: "manual_broker_review",
      phase_number: 5,
      title: "人工券商端核对",
      status: "waiting",
      evidence: "系统不会自动下单。",
    },
    {
      phase_id: "post_close_journal",
      phase_number: 6,
      title: "收盘后复盘记录",
      status: "waiting",
      evidence: "记录今天信号和决策质量。",
    },
  ];
  const phases = Array.isArray(daybook.phases) && daybook.phases.length ? daybook.phases : fallbackPhases;
  const summary = daybook.summary || {};
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const dailyReceipt = latestExecutionReceipt("daily_trade_advisory");
  const readiness = trade.pretrade_readiness || {};
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const currentPhaseId = summary.current_phase_id || phases.find((phase) => phase.status !== "done")?.phase_id || "";
  return phases.map((phase) => {
    const phaseId = phase.phase_id || "";
    let status = phase.status || "waiting";
    let detail = phase.evidence || phase.plain_action || "";
    if (phaseId === "top3_signal_generation" && dailyReceipt) {
      detail = `${detail} / 今日建议回执=${dailyReceipt.time || "--"}`;
    }
    if (phaseId === "paper_simulation_review" && paperReceipt) {
      status = "done";
      detail = `模拟盘回执=${paperReceipt.time || "--"} / 收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}`;
    }
    if (phaseId === "manual_broker_review" && blockers.length > 0) {
      status = "blocked";
      detail = `阻断=${blockers.join(" / ")}。红灯时不要人工补单。`;
    }
    return {
      phaseId,
      label: `${formatNumber(phase.phase_number || 0)}. ${beginnerDailyStatusText(status)}`,
      title: phase.title || phaseId || "--",
      detail,
      tone: beginnerDailyStatusTone(status),
      status,
      current: phaseId === currentPhaseId && status !== "done",
      target: phase.gui_target || "beginner-daily-rehearsal-board",
    };
  });
}

function beginnerDailyRehearsalActionRows(phases = [], daybook = {}) {
  const firstBlocked = phases.find((phase) => phase.status === "blocked");
  const firstRequired = phases.find((phase) => phase.status === "required");
  const firstWaiting = phases.find((phase) => phase.status === "waiting");
  const next = firstBlocked || firstRequired || firstWaiting || phases[phases.length - 1] || {};
  const workflowByPhase = {
    scope_and_data: "daily_ops",
    top3_signal_generation: "daily_trade_advisory",
    paper_simulation_review: "paper_simulation",
  };
  const buttonByWorkflow = {
    daily_ops: "刷新日常数据",
    daily_trade_advisory: "生成今日建议",
    paper_simulation: "运行模拟盘",
  };
  const workflow = workflowByPhase[next.phaseId] || "";
  const rows = [
    {
      label: "下一步",
      detail: next.title ? `先处理：${next.title}` : "先运行开盘前一键体检生成今日流程。",
      workflow: workflow || (next.phaseId ? "" : "daily_pretrade_checkup"),
      target: next.target || "beginner-daily-rehearsal-board",
      button: buttonByWorkflow[workflow] || "运行开盘前体检",
      targetLabel: "看这一步证据",
      tone: next.tone || "warn",
    },
    {
      label: "日终复盘",
      detail: "收盘后记录信号、模拟盘、人工决策和偏差，给下一轮因子审计提供反馈。",
      target: "control-operation-ledger",
      targetLabel: "看回执台账",
      tone: "warn",
    },
    {
      label: "禁止越界",
      detail: daybook.safety || "不连接券商、不读取账户、不生成实盘委托、不自动下单。",
      target: "control-safety-boundary",
      targetLabel: "看安全边界",
      tone: "danger",
    },
  ];
  return rows;
}

function beginnerDailyStatusText(status = "") {
  if (status === "done") return "已完成";
  if (status === "blocked") return "阻断";
  if (status === "required") return "必做";
  if (status === "manual_only") return "人工";
  return "等待";
}

function beginnerDailyStatusTone(status = "") {
  if (status === "done") return "ok";
  if (status === "blocked") return "danger";
  if (status === "manual_only" || status === "required") return "warn";
  return "muted";
}

function renderBeginnerPostCloseJournal() {
  const summaryTarget = byId("beginner-post-close-journal-summary");
  const checklistTarget = byId("beginner-post-close-journal-checklist");
  const actionsTarget = byId("beginner-post-close-journal-actions");
  if (!summaryTarget || !checklistTarget || !actionsTarget) return;
  const trade = state.dailyTradeAdvisory || {};
  const template = trade.post_close_journal_template || {};
  const summary = template.summary || {};
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const journalReceipt = latestExecutionReceipt("post_close_journal");
  const rows = beginnerPostCloseJournalRows(template);
  summaryTarget.innerHTML = statusRows([
    ["复盘状态", journalReceipt ? "已有本地复盘回执" : "等待收盘后复盘", journalReceipt ? "ok" : "warn"],
    ["运行日期", template.run_date || trade.run_date || "--", "muted"],
    ["模拟盘回执", paperReceipt ? `已有 ${paperReceipt.time || "--"}` : "缺失", paperReceipt ? "ok" : "warn"],
    ["安全边界", summary.order_placement_allowed ? "异常：允许下单" : "不自动下单", summary.order_placement_allowed ? "danger" : "danger"],
  ]);
  renderPostCloseManualFormStatus(journalReceipt);
  renderPostCloseExecutionAudit(localManualExecutionAudit(trade));
  checklistTarget.innerHTML = rows.map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.prompt)}</span>
      <span>${escapeHtml(item.evidence)}</span>
    </div>
  `).join("");
  actionsTarget.innerHTML = beginnerPostCloseJournalActionRows(template, journalReceipt, paperReceipt).map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <span class="beginner-task-actions">
        ${item.workflow ? `<button class="primary-button" type="button" data-post-close-journal-action="${escapeRawHtml(item.workflow)}">${escapeHtml(item.button)}</button>` : ""}
        ${item.target ? `<button class="secondary-button" type="button" data-post-close-journal-target="${escapeRawHtml(item.target)}">${escapeHtml(item.targetLabel || "看证据")}</button>` : ""}
      </span>
    </div>
  `).join("");
}

function renderPostCloseManualFormStatus(journalReceipt = null) {
  const target = byId("beginner-post-close-journal-form-status");
  if (!target) return;
  const form = postCloseManualReviewForm();
  const executionSummary = form.manual_execution_audit?.summary || {};
  const recorded = form.manual_note_count > 0 || Boolean(journalReceipt);
  target.innerHTML = statusRows([
    ["人工记录状态", recorded ? "manual_review_recorded" : "waiting_manual_review_notes", recorded ? "ok" : "warn"],
    ["今天实际选择", manualOutcomeLabel(form.manual_outcome), "warn"],
    ["备注数量", `${formatNumber(form.manual_note_count)} 条 / 不要填写账户号、委托号、券商客户号`, form.manual_note_count ? "ok" : "warn"],
    ["人工成交审计", `${executionSummary.decision || "waiting_for_manual_tickets"} / 回执=${formatNumber(executionSummary.review_count)} / 异常=${formatNumber(executionSummary.blocked_count)}`, executionSummary.blocked_count ? "danger" : executionSummary.missing_review_count ? "warn" : "ok"],
  ]);
}

function bindPostCloseManualFormStatus() {
  const form = document.querySelector("[data-post-close-manual-form-root]");
  if (!form) return;
  const refresh = () => {
    renderPostCloseManualFormStatus(latestExecutionReceipt("post_close_journal"));
    renderPostCloseExecutionAudit(localManualExecutionAudit(state.dailyTradeAdvisory || {}));
  };
  form.addEventListener("input", refresh);
  form.addEventListener("change", refresh);
}

function postCloseManualReviewForm() {
  const manualNote = sanitizePostCloseJournalText(valueOf("post-close-manual-note"));
  const riskNote = sanitizePostCloseJournalText(valueOf("post-close-risk-note"));
  const nextDayNote = sanitizePostCloseJournalText(valueOf("post-close-next-day-note"));
  const manualOutcome = valueOf("post-close-manual-outcome") || "skipped_no_trade";
  const manualExecutionReviews = manualExecutionReviewRowsFromInput();
  const manualExecutionAudit = localManualExecutionAudit(state.dailyTradeAdvisory || {}, manualExecutionReviews);
  return {
    manual_outcome: manualOutcome,
    manual_outcome_label: manualOutcomeLabel(manualOutcome),
    manual_note: manualNote,
    risk_note: riskNote,
    next_day_note: nextDayNote,
    manual_note_count: [manualNote, riskNote, nextDayNote].filter(Boolean).length,
    manual_execution_reviews: manualExecutionReviews,
    manual_execution_review_count: manualExecutionReviews.length,
    manual_execution_audit: manualExecutionAudit,
    manual_review_recorded: true,
    broker_connection_allowed: false,
    account_read_allowed: false,
    order_placement_allowed: false,
    auto_order_allowed: false,
  };
}

function manualExecutionReviewRowsFromInput() {
  const raw = valueOf("post-close-execution-reviews");
  if (!raw.trim()) return [];
  return raw.split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^ticket_id\s*,/i.test(line))
    .map((line) => splitManualExecutionCsvLine(line))
    .filter((parts) => parts.some((part) => String(part || "").trim()))
    .map((parts) => ({
      ticket_id: String(parts[0] || "").trim(),
      manual_outcome: String(parts[1] || valueOf("post-close-manual-outcome") || "skipped_no_trade").trim(),
      actual_fill_price: numberOrNull(parts[2]),
      fill_quantity: numberOrNull(parts[3]),
      execute_or_skip_reason: sanitizePostCloseJournalText(parts.slice(4).join(",")),
    }))
    .filter((row) => row.ticket_id || row.execute_or_skip_reason);
}

function splitManualExecutionCsvLine(line = "") {
  const cells = [];
  let current = "";
  let quoted = false;
  String(line).split("").forEach((char) => {
    if (char === '"') {
      quoted = !quoted;
      return;
    }
    if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
      return;
    }
    current += char;
  });
  cells.push(current.trim());
  return cells;
}

function localManualExecutionAudit(trade = {}, reviews = null) {
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const reviewRows = Array.isArray(reviews) ? reviews : manualExecutionReviewRowsFromInput();
  const reviewsByKey = new Map();
  reviewRows.forEach((review) => {
    const ticketId = String(review.ticket_id || "").trim();
    const assetId = String(review.asset_id || "").trim();
    if (ticketId) reviewsByKey.set(`ticket:${ticketId}`, review);
    if (assetId && !reviewsByKey.has(`asset:${assetId}`)) reviewsByKey.set(`asset:${assetId}`, review);
  });
  const rows = tickets.map((ticket, index) => localManualExecutionAuditRow(index + 1, ticket, reviewsByKey));
  const countReason = (reason) => rows.filter((row) => Array.isArray(row.breach_reasons) && row.breach_reasons.includes(reason)).length;
  const blockedCount = rows.filter((row) => row.review_status === "blocked").length;
  const missingReviewCount = rows.filter((row) => row.review_status === "missing_review").length;
  const guardrailBreachCount = countReason("broker_price_outside_guardrail");
  const slippageBreachCount = countReason("slippage_limit_breached");
  const sensitiveFieldCount = countReason("sensitive_field_removed");
  const executedCount = rows.filter((row) => row.manual_outcome === "manual_trade_by_human").length;
  const skippedCount = rows.filter((row) => ["skipped_no_trade", "paper_only", "manual_review_no_trade", "blocked_by_risk"].includes(row.manual_outcome)).length;
  let decision = "waiting_for_manual_tickets";
  if (rows.length && (blockedCount || guardrailBreachCount || slippageBreachCount || sensitiveFieldCount)) {
    decision = "guardrail_breach_review_required";
  } else if (rows.length && missingReviewCount) {
    decision = "manual_execution_review_incomplete";
  } else if (rows.length) {
    decision = "manual_execution_evidence_ready";
  }
  return {
    stage: "phase_6_23_manual_execution_audit",
    run_date: trade.run_date || handoff.run_date || "",
    summary: {
      decision,
      ticket_count: rows.length,
      review_count: reviewRows.length,
      executed_count: executedCount,
      skipped_count: skippedCount,
      guardrail_breach_count: guardrailBreachCount,
      slippage_breach_count: slippageBreachCount,
      quantity_mismatch_count: countReason("quantity_mismatch"),
      sensitive_field_count: sensitiveFieldCount,
      missing_review_count: missingReviewCount,
      blocked_count: blockedCount,
      manual_review_required: true,
      manual_execution_only: true,
      live_trading_allowed: false,
      broker_connection_allowed: false,
      account_read_allowed: false,
      order_placement_allowed: false,
      auto_order_allowed: false,
    },
    rows,
    safety: "local manual execution audit only; no broker, account, or order side effects",
  };
}

function localManualExecutionAuditRow(index, ticket = {}, reviewsByKey = new Map()) {
  const ticketId = String(ticket.ticket_id || `daily-top3-${String(index).padStart(3, "0")}`);
  const assetId = String(ticket.asset_id || "");
  const review = reviewsByKey.get(`ticket:${ticketId}`) || reviewsByKey.get(`asset:${assetId}`) || {};
  const hasReview = Object.keys(review).length > 0;
  const guardrails = ticket.execution_guardrails || {};
  const side = String(ticket.side || "buy_or_adjust");
  const manualOutcome = String(review.manual_outcome || (hasReview ? "skipped_no_trade" : "missing_review"));
  const referencePrice = numberOrNull(guardrails.reference_price ?? ticket.reference_price ?? ticket.latest_price);
  const actualFillPrice = numberOrNull(review.actual_fill_price ?? review.fill_price);
  const fillQuantity = numberOrNull(review.fill_quantity ?? review.quantity);
  const roundedDelta = numberOrNull(ticket.rounded_quantity_delta) || 0;
  const roundedQuantity = numberOrNull(ticket.rounded_quantity) || 0;
  const plannedQuantity = Math.abs(roundedDelta || roundedQuantity);
  const lowerBound = numberOrNull(guardrails.lower_price_bound);
  const upperBound = numberOrNull(guardrails.upper_price_bound);
  const maxSlippageBps = numberOrNull(guardrails.max_slippage_bps) ?? 10;
  const sensitiveFields = ["account_id", "broker_id", "client_id", "order_id"].filter((field) => Object.prototype.hasOwnProperty.call(review, field));
  const breachReasons = [];
  if (sensitiveFields.length) breachReasons.push("sensitive_field_removed");
  let priceWithinGuardrail = null;
  let adverseSlippageBps = null;
  let slippageWithinLimit = null;
  let quantityMatchesTicket = null;
  if (manualOutcome === "manual_trade_by_human") {
    if (!Number.isFinite(actualFillPrice) || !Number.isFinite(fillQuantity) || fillQuantity <= 0) {
      breachReasons.push("missing_fill_detail");
    }
    if (Number.isFinite(actualFillPrice) && Number.isFinite(lowerBound) && Number.isFinite(upperBound)) {
      priceWithinGuardrail = lowerBound <= actualFillPrice && actualFillPrice <= upperBound;
      if (!priceWithinGuardrail) breachReasons.push("broker_price_outside_guardrail");
    }
    if (Number.isFinite(actualFillPrice) && Number.isFinite(referencePrice) && referencePrice > 0) {
      adverseSlippageBps = side.toLowerCase().startsWith("sell")
        ? ((referencePrice - actualFillPrice) / referencePrice) * 10000
        : ((actualFillPrice - referencePrice) / referencePrice) * 10000;
      slippageWithinLimit = adverseSlippageBps <= maxSlippageBps;
      if (!slippageWithinLimit) breachReasons.push("slippage_limit_breached");
    }
    if (Number.isFinite(fillQuantity)) {
      quantityMatchesTicket = plannedQuantity <= 0 || Math.abs(fillQuantity) === plannedQuantity;
      if (!quantityMatchesTicket) breachReasons.push("quantity_mismatch");
    }
  }
  const reviewStatus = !hasReview
    ? "missing_review"
    : breachReasons.length
      ? "blocked"
      : manualOutcome === "manual_trade_by_human"
        ? "passed"
        : "skipped";
  return {
    step_number: index,
    ticket_id: ticketId,
    asset_id: assetId,
    side,
    manual_outcome: manualOutcome,
    reference_price: referencePrice,
    actual_fill_price: actualFillPrice,
    fill_quantity: fillQuantity,
    planned_quantity: plannedQuantity,
    adverse_slippage_bps: Number.isFinite(adverseSlippageBps) ? Number(adverseSlippageBps.toFixed(6)) : null,
    price_within_guardrail: priceWithinGuardrail,
    slippage_within_limit: slippageWithinLimit,
    quantity_matches_ticket: quantityMatchesTicket,
    lower_price_bound: lowerBound,
    upper_price_bound: upperBound,
    max_slippage_bps: maxSlippageBps,
    review_status: reviewStatus,
    breach_reasons: breachReasons,
    execute_or_skip_reason: sanitizePostCloseJournalText(review.execute_or_skip_reason || ""),
    sensitive_fields_removed: sensitiveFields,
    review_only: true,
    manual_execution_only: true,
    live_trading_allowed: false,
    broker_connection_allowed: false,
    account_read_allowed: false,
    order_placement_allowed: false,
    auto_order_allowed: false,
  };
}

function renderPostCloseExecutionAudit(audit = null) {
  const target = byId("beginner-post-close-execution-audit");
  if (!target) return;
  const pack = audit || localManualExecutionAudit(state.dailyTradeAdvisory || {});
  const summary = pack.summary || {};
  const rows = Array.isArray(pack.rows) ? pack.rows : [];
  const tone = summary.blocked_count || summary.guardrail_breach_count || summary.slippage_breach_count
    ? "danger"
    : summary.missing_review_count
      ? "warn"
      : rows.length
        ? "ok"
        : "warn";
  const table = rows.length
    ? `<table>${tableRows(rows, [
      "ticket_id",
      "asset_id",
      "manual_outcome",
      "reference_price",
      "actual_fill_price",
      "fill_quantity",
      "planned_quantity",
      "adverse_slippage_bps",
      "price_within_guardrail",
      "slippage_within_limit",
      "quantity_matches_ticket",
      "review_status",
      "breach_reasons",
    ])}</table>`
    : statusRows([["人工成交审计", "暂无人工票据或尚未填写成交/跳过回执", "warn"]]);
  target.innerHTML = `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("人工成交审计")}</strong>
      <span>${escapeHtml(`${summary.decision || "waiting_for_manual_tickets"} / 票据=${formatNumber(summary.ticket_count)} / 回执=${formatNumber(summary.review_count)} / 执行=${formatNumber(summary.executed_count)} / 追价=${formatNumber(summary.guardrail_breach_count)} / 滑点超限=${formatNumber(summary.slippage_breach_count)}`)}</span>
      <span>${escapeHtml("只审计人工执行事实，不连接券商、不读取账户、不自动下单。")}</span>
    </div>
    ${table}
  `;
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(number) ? number : null;
}

function manualOutcomeLabel(outcome = "") {
  const labels = {
    skipped_no_trade: "跳过，没有人工交易",
    paper_only: "只做模拟盘观察",
    manual_review_no_trade: "人工复核后未交易",
    manual_trade_by_human: "本人离开系统后在券商端手动操作",
    blocked_by_risk: "因风险或数据问题停止",
  };
  return labels[outcome] || "未记录";
}

function sanitizePostCloseJournalText(value = "") {
  let text = String(value || "").slice(0, 300).replace(/[\r\n\t]+/g, " ").replace(/\s+/g, " ").trim();
  ["account_id", "broker_id", "client_id", "order_id", "账户号", "委托号", "客户号"].forEach((token) => {
    text = text.replace(new RegExp(token, "gi"), "[已移除敏感字段]");
  });
  return text;
}

function beginnerPostCloseJournalRows(template = {}) {
  const fallbackItems = [
    {
      item_id: "signal_evidence",
      title: "今日信号证据",
      status: "needs_review",
      prompt: "确认今日前三因子、信号日期和目标 ETF。",
      evidence: "等待今日建议加载。",
      gui_target: "daily-trade-factor-table",
    },
    {
      item_id: "paper_simulation",
      title: "模拟盘表现",
      status: "required",
      prompt: "记录收益、回撤、成交和保护事件。",
      evidence: "等待模拟盘回执。",
      gui_target: "paper-metrics",
    },
    {
      item_id: "manual_decision",
      title: "人工决策",
      status: "required",
      prompt: "写下今天执行、跳过或减仓的原因。",
      evidence: "人工填写，不读账户。",
      gui_target: "daily-manual-broker-handoff-ticket-table",
    },
    {
      item_id: "risk_observation",
      title: "风险观察",
      status: "required",
      prompt: "记录回撤、集中度、现金或异常价格问题。",
      evidence: "等待盘前体检证据。",
      gui_target: "daily-pretrade-readiness-verdict",
    },
    {
      item_id: "next_day_follow_up",
      title: "次日跟进",
      status: "required",
      prompt: "写下明天要复核的数据、因子和风险。",
      evidence: "作为下一轮审计输入。",
      gui_target: "control-operation-ledger",
    },
  ];
  const items = Array.isArray(template.items) && template.items.length ? template.items : fallbackItems;
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  return items.map((item) => {
    let status = item.status || "required";
    let evidence = item.evidence || "";
    if (item.item_id === "paper_simulation" && paperReceipt) {
      status = "done";
      evidence = `模拟盘=${paperReceipt.time || "--"} / 收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}`;
    }
    return {
      itemId: item.item_id || "",
      title: item.title || item.item_id || "--",
      prompt: item.prompt || "",
      evidence,
      target: item.gui_target || "beginner-post-close-journal-board",
      tone: status === "done" ? "ok" : status === "needs_review" ? "warn" : "warn",
      status,
    };
  });
}

function beginnerPostCloseJournalActionRows(template = {}, journalReceipt = null, paperReceipt = null) {
  return [
    {
      label: "生成复盘回执",
      detail: journalReceipt
        ? `最近复盘回执=${journalReceipt.time || "--"}`
        : "收盘后点这里，把今日信号、模拟盘和人工决策问题写入本地回执台账。",
      workflow: "post_close_journal",
      target: "control-execution-receipts",
      button: journalReceipt ? "更新复盘回执" : "生成本地复盘回执",
      targetLabel: "看回执",
      tone: journalReceipt ? "ok" : "warn",
    },
    {
      label: "模拟盘证据",
      detail: paperReceipt ? "已有模拟盘证据，可以写入复盘。" : "还缺模拟盘回执，先跑本地模拟盘。",
      workflow: paperReceipt ? "" : "paper_simulation",
      target: "paper-metrics",
      button: "运行模拟盘",
      targetLabel: "看模拟盘",
      tone: paperReceipt ? "ok" : "warn",
    },
    {
      label: "安全提醒",
      detail: template.safety || "复盘回执不是账户记录；不连接券商、不读取账户、不自动下单。",
      target: "control-safety-boundary",
      targetLabel: "看安全边界",
      tone: "danger",
    },
  ];
}

function beginnerRecommendedTaskId() {
  const active = state.activeOperation || {};
  if (active.status === "running") return "trust";
  if (!state.snapshot) return "safety";
  if (!state.research) return "backtest";
  if (!state.paper) return "trust";
  return "trust";
}

function beginnerTaskRows(task = {}) {
  const running = state.activeOperation?.status === "running";
  const needsResearch = Boolean(task.requiresResearch && !state.research);
  return [
    ["适合什么时候", task.plain || "--", "ok"],
    ["点了会发生什么", needsResearch ? "还不能直接模拟盘，会先引导你跑当前参数回测。" : task.result || "--", needsResearch ? "warn" : "ok"],
    ["点完看哪里", task.evidence || "看控制台证据。", "ok"],
    ["当前限制", running ? "当前已有本地任务在运行，先等它结束。" : "仍然只在本地研究/纸面模拟边界内。", running ? "warn" : "muted"],
  ];
}

function renderBeginnerTaskWizard() {
  const root = byId("beginner-task-wizard");
  const list = byId("beginner-task-intent-list");
  const detail = byId("beginner-task-detail");
  const tag = byId("beginner-task-tag");
  if (!root || !list || !detail || !tag) return;
  const recommendedId = beginnerRecommendedTaskId();
  const selectedId = state.beginnerTaskId || recommendedId;
  const selected = BEGINNER_TASKS.find((task) => task.id === selectedId) || BEGINNER_TASKS[0];
  const running = state.activeOperation?.status === "running";
  const needsResearch = Boolean(selected.requiresResearch && !state.research);
  const primaryAction = needsResearch ? "research_backtest" : selected.action || "";
  const primaryTarget = primaryAction ? "" : selected.target || "control-action-center";
  const primaryLabel = needsResearch ? "先本地回测" : selected.primaryLabel || "查看";
  const tagTone = running ? "tag tag-warn" : selected.id === recommendedId ? "tag" : "tag tag-warn";
  ["ok", "warn", "danger", "muted"].forEach((tone) => root.classList.remove(tone));
  root.classList.add(running ? "warn" : selected.tone || "ok");
  tag.className = tagTone;
  tag.textContent = selected.id === recommendedId ? "推荐" : "已选择";
  list.innerHTML = BEGINNER_TASKS.map((task) => {
    const isActive = task.id === selected.id;
    const isRecommended = task.id === recommendedId;
    return `
      <button
        class="beginner-task-card ${escapeHtml(isActive ? "active" : "")}"
        type="button"
        data-beginner-task-select="${escapeHtml(task.id)}"
      >
        <small>${escapeHtml(isRecommended ? "推荐" : "可选")}</small>
        <strong>${escapeHtml(task.title)}</strong>
        <span>${escapeHtml(task.plain)}</span>
      </button>
    `;
  }).join("");
  const secondaryButton = selected.secondaryTarget ? `
    <button
      class="secondary-button"
      type="button"
      data-beginner-task-run="true"
      data-beginner-task-target="${escapeHtml(selected.secondaryTarget)}"
    >${escapeHtml(selected.secondaryLabel || "看更多证据")}</button>
  ` : "";
  detail.innerHTML = `
    <div class="beginner-task-detail-head">
      <div>
        <small>当前任务</small>
        <strong>${escapeHtml(selected.title)}</strong>
        <span>${escapeHtml(needsResearch ? "这一步需要先有当前参数回测结果，软件会先带你跑回测。" : selected.result)}</span>
      </div>
    </div>
    <div class="status-list compact-status beginner-task-rows">
      ${statusRows(beginnerTaskRows(selected))}
    </div>
    <div class="beginner-task-actions">
      <button
        class="primary-button"
        type="button"
        data-beginner-task-run="true"
        data-beginner-task-action="${escapeHtml(primaryAction)}"
        data-beginner-task-target="${escapeHtml(primaryTarget)}"
        ${runtimeGuardAttr(primaryAction)}
        ${running ? "disabled" : ""}
      >${escapeHtml(running ? "等待当前任务结束" : primaryLabel)}</button>
      ${secondaryButton}
      <button
        class="secondary-button"
        type="button"
        data-beginner-task-run="true"
        data-beginner-task-target="${escapeHtml(selected.target || "control-action-center")}"
      >看证据位置</button>
    </div>
    ${renderRuntimeGuardHelp(primaryAction)}
  `;
}

function beginnerTroubleshooterState() {
  const progress = beginnerProgressState();
  const trust = beginnerDataTrustState(progress);
  const project = state.projectStatus || {};
  const blockerCount = Number(project.blocker_count || 0);
  const active = state.activeOperation || {};
  const latestReceipt = beginnerLatestReceipt() || {};
  const latestHistory = beginnerLatestRunHistory() || {};
  const failed = active.status === "failed" || latestReceipt.status === "failed" || latestHistory.status === "failed";
  const latestWorkflow = active.workflow_id || latestReceipt.workflow_id || latestHistory.workflow_id || "research_backtest";

  let stateInfo = {
    tone: "ok",
    tag: "可继续",
    title: "暂时没有明显问题",
    summary: "可以继续看数据可信度、回测闸门和模拟盘交接，不要跳过证据。",
    reason: "当前没有发现运行失败、项目阻断、演示数据、非 CN_ETF 主线或短样本硬问题。",
    avoid: "不要把单次高收益直接当成可推广盈利因子。",
    next: "继续核对回测闸门和结果证据。",
    target: "control-backtest-gate",
    targetLabel: "看回测闸门",
    action: state.research && !state.paper ? "paper_simulation" : "",
    actionLabel: state.research && !state.paper ? "本地模拟盘回放" : "",
  };

  if (progress.status === "running") {
    stateInfo = {
      tone: "warn",
      tag: "运行中",
      title: "当前已有任务在运行",
      summary: "先等当前本地任务结束，不要连续点多个运行按钮。",
      reason: active.detail || progress.summary || "浏览器已经记录了一个正在运行的本地工作流。",
      avoid: "不要重复点击回测、信号或模拟盘按钮。",
      next: "去看当前操作和运行队列，等状态变成完成或失败。",
      target: "control-active-operation",
      targetLabel: "看当前操作",
    };
  } else if (failed) {
    stateInfo = {
      tone: "danger",
      tag: "刚失败",
      title: "刚才的本地任务失败了",
      summary: "先看失败原因，再决定是修参数还是重新跑。",
      reason: active.detail || latestReceipt.detail || latestHistory.detail || progress.summary || "最新回执标记为 failed。",
      avoid: "不要在失败原因没看清前继续做模拟盘或推广判断。",
      next: "先看失败原因；如果只是参数或临时接口问题，再重新跑当前回测。",
      target: "control-active-operation",
      targetLabel: "看失败原因",
      action: latestWorkflow === "research_backtest" ? "research_backtest" : "",
      actionLabel: latestWorkflow === "research_backtest" ? "重新跑当前回测" : "",
    };
  } else if (blockerCount > 0) {
    stateInfo = {
      tone: "danger",
      tag: "有阻断",
      title: "项目还有阻断项",
      summary: `当前项目有 ${blockerCount} 个阻断项，先修复再谈模拟盘或推广。`,
      reason: project.overall_status || "项目状态里仍有 blocker。",
      avoid: "不要绕过审计修复队列，也不要只看收益指标。",
      next: "打开审计修复队列和运行前检查。",
      target: "control-audit-repair-queue",
      targetLabel: "看修复队列",
    };
  } else if (trust.isDemo || trust.wrongMarket || trust.tone === "danger") {
    stateInfo = {
      tone: "danger",
      tag: "不可下结论",
      title: trust.title || "当前数据不能下结论",
      summary: trust.summary || "先修正数据源、市场或样本窗口。",
      reason: trust.resultText || "数据可信度卡给出了红灯。",
      avoid: "不要把演示数据、非 CN_ETF 或一年以内样本当成盈利因子证据。",
      next: "先看当前参数和请求预览，确认数据源、市场和日期窗口。",
      target: trust.target || "beginner-data-trust-card",
      targetLabel: trust.button || "看可信度",
    };
  } else if (trust.onlyReceipt || trust.tone === "warn") {
    stateInfo = {
      tone: "warn",
      tag: trust.tag || "需核对",
      title: trust.title || "当前结果需要核对",
      summary: trust.summary || "先确认这是不是当前参数对应的结果。",
      reason: trust.resultText || "数据可信度卡给出了黄灯。",
      avoid: "不要把历史回执或偏短样本直接当成当前结论。",
      next: "不确定时重新跑当前参数，跑完再看回测闸门。",
      target: trust.target || "beginner-data-trust-card",
      targetLabel: trust.button || "看可信度",
      action: !state.research || trust.onlyReceipt ? "research_backtest" : "",
      actionLabel: !state.research || trust.onlyReceipt ? "重新跑当前回测" : "",
    };
  } else if (!state.research) {
    stateInfo = {
      tone: "warn",
      tag: "未回测",
      title: "当前参数还没有页面结果",
      summary: "先跑一次本地回测，才有收益、回撤、胜率和 Sharpe 可以看。",
      reason: "当前页面没有 state.research 结果。",
      avoid: "不要只看排行榜就判断因子可用。",
      next: "看当前参数，确认无误后本地回测。",
      target: "beginner-parameter-explainer",
      targetLabel: "看当前参数",
      action: "research_backtest",
      actionLabel: "本地回测当前参数",
    };
  }

  return stateInfo;
}

function beginnerTroubleshooterRows(info = beginnerTroubleshooterState()) {
  return [
    ["为什么", info.reason || "--", info.tone],
    ["先不要做", info.avoid || "不要跳过证据。", info.tone === "ok" ? "muted" : "danger"],
    ["下一步", info.next || "先看证据位置。", info.tone === "danger" ? "warn" : "ok"],
    ["安全边界", "所有按钮仍然只做本地研究/纸面模拟，不连接券商、不读账户、不真实下单。", "danger"],
  ];
}

function renderBeginnerTroubleshooter() {
  const root = byId("beginner-troubleshooter");
  const summary = byId("beginner-troubleshooter-summary");
  const rows = byId("beginner-troubleshooter-rows");
  const tag = byId("beginner-troubleshooter-tag");
  if (!root || !summary || !rows || !tag) return;
  const info = beginnerTroubleshooterState();
  ["ok", "warn", "danger", "muted"].forEach((tone) => root.classList.remove(tone));
  root.classList.add(info.tone || "warn");
  tag.className = info.tone === "danger" ? "tag tag-danger" : info.tone === "warn" ? "tag tag-warn" : "tag";
  tag.textContent = info.tag || "检查";
  const actionButton = info.action ? `
    <button
      class="primary-button"
      type="button"
      data-beginner-troubleshooter-action="${escapeHtml(info.action)}"
      ${state.activeOperation?.status === "running" ? "disabled" : ""}
    >${escapeHtml(info.actionLabel || "重新运行")}</button>
  ` : "";
  summary.innerHTML = `
    <div class="beginner-troubleshooter-head">
      <div>
        <strong>${escapeHtml(info.title)}</strong>
        <span>${escapeHtml(info.summary)}</span>
      </div>
      <div class="beginner-troubleshooter-actions">
        <button class="secondary-button" type="button" data-beginner-troubleshooter-jump="${escapeHtml(info.target || "control-active-operation")}">${escapeHtml(info.targetLabel || "看证据")}</button>
        ${actionButton}
      </div>
    </div>
  `;
  rows.innerHTML = statusRows(beginnerTroubleshooterRows(info));
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

function beginnerResearchReceipts() {
  const rows = Array.isArray(state.executionReceipts) && state.executionReceipts.length
    ? state.executionReceipts
    : loadExecutionReceipts(state.controlCenter?.execution_receipts || {});
  return rows.filter((receipt) => receipt?.workflow_id === "research_backtest");
}

function beginnerLatestResearchReceipt() {
  return beginnerResearchReceipts()[0] || null;
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

function dayCountBetween(startDate, endDate) {
  if (!startDate || !endDate) return NaN;
  const start = Date.parse(`${startDate}T00:00:00Z`);
  const end = Date.parse(`${endDate}T00:00:00Z`);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return NaN;
  return Math.round((end - start) / 86400000) + 1;
}

function beginnerEvidenceMatchState() {
  const params = buildResearchParams();
  const currentRequest = requestObjectFromParams(params);
  const resultRequest = state.research?.request || {};
  const receipt = beginnerLatestResearchReceipt();
  const hasResult = Boolean(state.research?.request);
  const hasReceipt = Boolean(receipt);
  const resultCurrent = hasResult && requestMatchesCurrentParams(
    resultRequest,
    params,
    ["market", "factor_name", "top_n", "cost_bps", "start_date", "end_date"],
  );
  const receiptCurrent = hasReceipt && requestMatchesReceipt(receipt, currentRequest);
  const resultSummary = hasResult ? requestFreshnessSummary(resultRequest) : "暂无页面回测结果";
  const receiptSummary = hasReceipt ? requestFreshnessSummary(receipt.request || {}) : "暂无浏览器研究回执";
  const currentSummary = requestFreshnessSummary(currentRequest);

  if (state.activeOperation?.status === "running") {
    return {
      tone: "warn",
      tag: "等待新结果",
      title: "正在运行，先不要读收益曲线",
      summary: "等当前本地任务返回以后，再判断收益、回撤、胜率和 Sharpe 是否属于当前参数。",
      currentRequest,
      resultRequest,
      receipt,
      hasResult,
      hasReceipt,
      resultCurrent,
      receiptCurrent,
      rows: [
        ["当前参数", currentSummary, "ok"],
        ["页面结果", "运行中，旧指标暂时不能当结论", "warn"],
        ["浏览器回执", receiptSummary, hasReceipt ? "warn" : "muted"],
      ],
    };
  }

  if (resultCurrent) {
    return {
      tone: "ok",
      tag: "已匹配",
      title: "页面结果匹配当前参数",
      summary: "现在看到的收益、回撤、胜率和 Sharpe 可以继续进入闸门复核；仍然不能跳过 OOS、回撤和样本检查。",
      currentRequest,
      resultRequest,
      receipt,
      hasResult,
      hasReceipt,
      resultCurrent,
      receiptCurrent,
      rows: [
        ["当前参数", currentSummary, "ok"],
        ["页面结果", resultSummary, "ok"],
        ["浏览器回执", receiptSummary, receiptCurrent ? "ok" : hasReceipt ? "warn" : "muted"],
      ],
    };
  }

  if (receiptCurrent) {
    return {
      tone: "warn",
      tag: "只有回执",
      title: "浏览器回执匹配，但页面结果还没加载",
      summary: "可以先核对回执；如果要看完整收益曲线和闸门，建议重新跑当前参数。",
      currentRequest,
      resultRequest,
      receipt,
      hasResult,
      hasReceipt,
      resultCurrent,
      receiptCurrent,
      rows: [
        ["当前参数", currentSummary, "ok"],
        ["页面结果", hasResult ? resultSummary : "暂无页面回测结果", hasResult ? "warn" : "muted"],
        ["浏览器回执", receiptSummary, "ok"],
      ],
    };
  }

  if (hasResult || hasReceipt) {
    return {
      tone: "danger",
      tag: "不匹配",
      title: "不要信这条收益曲线",
      summary: "页面结果或浏览器回执不是当前参数；当前选择变过以后，旧收益、Sharpe、胜率都不能当作当前因子的证据。",
      currentRequest,
      resultRequest,
      receipt,
      hasResult,
      hasReceipt,
      resultCurrent,
      receiptCurrent,
      rows: [
        ["当前参数", currentSummary, "ok"],
        ["页面结果", resultSummary, hasResult ? "danger" : "muted"],
        ["浏览器回执", receiptSummary, hasReceipt ? "danger" : "muted"],
      ],
    };
  }

  return {
    tone: "warn",
    tag: "无证据",
    title: "当前参数还没有回测证据",
    summary: "先跑一次当前参数，跑完再看收益、回撤、胜率和 Sharpe；不要把排行榜或历史回执当当前结论。",
    currentRequest,
    resultRequest,
    receipt,
    hasResult,
    hasReceipt,
    resultCurrent,
    receiptCurrent,
    rows: [
      ["当前参数", currentSummary, "ok"],
      ["页面结果", "暂无页面回测结果", "warn"],
      ["浏览器回执", "暂无浏览器研究回执", "warn"],
    ],
  };
}

function renderBeginnerEvidenceMatch(match = beginnerEvidenceMatchState()) {
  const tagClass = match.tone === "danger" ? "tag tag-danger" : match.tone === "warn" ? "tag tag-warn" : "tag";
  return `
    <div class="beginner-evidence-match ${escapeHtml(match.tone)}" data-beginner-evidence-match-root="true">
      <div class="beginner-evidence-match-head">
        <div>
          <small>当前证据匹配</small>
          <strong>${escapeHtml(match.title)}</strong>
          <span>${escapeHtml(match.summary)}</span>
        </div>
        <span class="${escapeHtml(tagClass)}">${escapeHtml(match.tag)}</span>
      </div>
      <div class="status-list compact-status beginner-evidence-match-rows">
        ${statusRows(match.rows || [])}
      </div>
      <div class="beginner-evidence-match-actions">
        <button class="primary-button" type="button" data-beginner-evidence-match-action="research_backtest" ${runtimeGuardAttr("research_backtest")}>重新跑当前参数</button>
        <button class="secondary-button" type="button" data-beginner-evidence-match-jump="control-execution-receipts">核对回执</button>
        <button class="secondary-button" type="button" data-beginner-evidence-match-jump="control-result-freshness">看新旧匹配</button>
      </div>
    </div>
  `;
}

function beginnerDataTrustState(progress = beginnerProgressState()) {
  const evidence = beginnerEvidenceMatchState();
  const source = valueOf("data-source-select")
    || state.research?.data_source
    || state.research?.source
    || state.snapshot?.data_mode
    || "processed-bars";
  const market = valueOf("market-select") || state.research?.market || "CN_ETF";
  const startDate = valueOf("start-date") || state.research?.start_date || "";
  const endDate = valueOf("end-date") || state.research?.end_date || "";
  const sampleDays = dayCountBetween(startDate, endDate);
  const sourceKey = String(source).toLowerCase();
  const marketKey = String(market).toUpperCase();
  const isDemo = sourceKey.includes("demo");
  const wrongMarket = marketKey !== "CN_ETF";
  const hasCurrentResearch = evidence.resultCurrent;
  const onlyReceipt = !hasCurrentResearch && evidence.receiptCurrent;
  const hasStaleEvidence = !hasCurrentResearch && !onlyReceipt && (evidence.hasResult || evidence.hasReceipt);
  const hasNoResult = !hasCurrentResearch && !onlyReceipt && progress.status !== "running";
  const veryShortSample = Number.isFinite(sampleDays) && sampleDays < 365;
  const shortSample = Number.isFinite(sampleDays) && sampleDays < 1095;
  const resultText = progress.status === "running"
    ? "当前正在本地运行，还不能把结果当结论。"
    : hasCurrentResearch
      ? "当前页面回测结果匹配当前参数，可以继续看结果判读和闸门。"
      : onlyReceipt
        ? "只有浏览器回执匹配当前参数，页面结果还需要重新加载或复跑。"
        : hasStaleEvidence
          ? "已有历史结果或回执，但不是当前参数，不能当结论。"
          : "当前参数还没跑出页面结果。";

  let tone = "ok";
  let tag = "可继续研究";
  let title = "数据来源可继续研究";
  let summary = "当前是 CN_ETF 主线、非演示数据，并且样本窗口足够做进一步检查。";
  let target = "control-backtest-gate";
  let button = "看回测闸门";

  if (progress.status === "running") {
    tone = "warn";
    tag = "等待结果";
    title = "正在运行，先别下结论";
    summary = "等当前本地任务完成，再判断收益、回撤、胜率和 Sharpe 是否可信。";
    target = "control-active-operation";
    button = "看当前操作";
  } else if (isDemo) {
    tone = "danger";
    tag = "演示数据";
    title = "演示数据不能下结论";
    summary = "这只能用来熟悉按钮和流程，不能判断因子是否赚钱。";
    target = "beginner-parameter-explainer";
    button = "看数据源";
  } else if (wrongMarket) {
    tone = "danger";
    tag = "非主线";
    title = "当前不是 CN_ETF 主线";
    summary = "如果目标是 ETF 轮动，非 CN_ETF 结果不能直接当作可用结论。";
    target = "beginner-parameter-explainer";
    button = "看市场参数";
  } else if (onlyReceipt) {
    tone = "warn";
    tag = "仅回执";
    title = "只有浏览器回执匹配当前参数";
    summary = "先核对回执；如果要看完整收益曲线和闸门，建议重新跑当前参数。";
    target = "control-execution-receipts";
    button = "核对回执";
  } else if (hasStaleEvidence) {
    tone = "danger";
    tag = "证据不匹配";
    title = "当前页面证据不是当前参数";
    summary = "参数变过以后，旧收益、Sharpe、胜率不能当作当前因子的证据。";
    target = "control-result-freshness";
    button = "看新旧匹配";
  } else if (hasNoResult) {
    tone = "warn";
    tag = "未回测";
    title = "当前参数还没有结果";
    summary = "先本地回测当前参数，再看收益、回撤、胜率和 Sharpe。";
    target = "beginner-parameter-explainer";
    button = "看当前参数";
  } else if (veryShortSample) {
    tone = "danger";
    tag = "样本太短";
    title = "样本不到一年，不能下结论";
    summary = "短样本很容易被单一行情周期误导，必须拉长窗口复核。";
    target = "control-request-preview";
    button = "看日期窗口";
  } else if (shortSample) {
    tone = "warn";
    tag = "样本偏短";
    title = "样本不足三年，需要谨慎";
    summary = "可以试跑流程，但不能把它当成稳定盈利因子的证据。";
    target = "control-request-preview";
    button = "看日期窗口";
  }

  return {
    tone,
    tag,
    title,
    summary,
    target,
    button,
    source,
    market,
    startDate,
    endDate,
    sampleDays,
    resultText,
    isDemo,
    wrongMarket,
    hasCurrentResearch,
    onlyReceipt,
    hasStaleEvidence,
    evidence,
  };
}

function beginnerDataTrustRows(trust = beginnerDataTrustState()) {
  const sourceTone = trust.isDemo ? "danger" : "ok";
  const marketTone = trust.wrongMarket ? "danger" : "ok";
  const sampleText = Number.isFinite(trust.sampleDays)
    ? `${trust.startDate || "--"} 至 ${trust.endDate || "--"} / ${formatNumber(trust.sampleDays)} 天`
    : `${trust.startDate || "--"} 至 ${trust.endDate || "--"} / 天数未知`;
  const sampleTone = Number.isFinite(trust.sampleDays)
    ? trust.sampleDays < 365
      ? "danger"
      : trust.sampleDays < 1095
        ? "warn"
        : "ok"
    : "warn";
  const resultTone = trust.hasCurrentResearch ? "ok" : "warn";
  return [
    ["数据源", parameterSourceText(trust.source, valueOf("data-root-input")), sourceTone],
    ["研究主线", `${trust.market || "--"} / 目标主线应为 CN_ETF`, marketTone],
    ["样本窗口", sampleText, sampleTone],
    ["结果状态", trust.resultText, resultTone],
  ];
}

function renderBeginnerDataTrust(progress = beginnerProgressState()) {
  const target = byId("beginner-data-trust-card");
  if (!target) return;
  const trust = beginnerDataTrustState(progress);
  const tagClass = trust.tone === "danger" ? "tag tag-danger" : trust.tone === "warn" ? "tag tag-warn" : "tag";
  target.className = `beginner-data-trust-card ${trust.tone}`;
  target.innerHTML = `
    <div class="beginner-data-trust-head">
      <div>
        <small>数据可信度</small>
        <strong>${escapeHtml(trust.title)}</strong>
        <span>${escapeHtml(trust.summary)}</span>
      </div>
      <span class="${escapeHtml(tagClass)}">${escapeHtml(trust.tag)}</span>
    </div>
    <div class="status-list compact-status beginner-data-trust-rows">
      ${statusRows(beginnerDataTrustRows(trust))}
    </div>
    ${renderBeginnerEvidenceMatch(trust.evidence)}
    <div class="beginner-data-trust-actions">
      <button class="secondary-button" type="button" data-beginner-data-trust-jump="beginner-parameter-explainer">看当前参数</button>
      <button class="secondary-button" type="button" data-beginner-data-trust-jump="control-request-preview">看请求预览</button>
      <button class="primary-button" type="button" data-beginner-data-trust-jump="${escapeHtml(trust.target)}">${escapeHtml(trust.button)}</button>
    </div>
  `;
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
      ? `data-beginner-action="${escapeHtml(item.action)}" data-beginner-progress-action="${escapeHtml(item.action)}" ${runtimeGuardAttr(item.action)}`
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
    ${renderRuntimeGuardHelp("research_backtest")}
  `;
  recoveryTarget.innerHTML = renderBeginnerProgressRecovery(progress);
  renderBeginnerDataTrust(progress);
  syncCurrentBacktestRuntimeGuard();
}

function renderBeginnerGuide() {
  const listNode = byId("beginner-step-list");
  const actionNode = byId("beginner-primary-action");
  const helpNode = byId("beginner-help-text");
  if (!listNode || !actionNode || !helpNode) return;
  listNode.innerHTML = BEGINNER_STEPS.map((step, index) => {
    const stateInfo = beginnerStepState(step.id);
    const buttonAttrs = step.action
      ? `data-beginner-action="${escapeHtml(step.action)}" ${runtimeGuardAttr(step.action)}`
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
    ? `data-beginner-action="${escapeHtml(nextStep.action)}" ${runtimeGuardAttr(nextStep.action)}`
    : `data-beginner-target="${escapeHtml(nextStep.target || "")}" data-leaderboard-tab="${escapeHtml(nextStep.leaderboardTab || "")}"`;
  actionNode.innerHTML = `
    <div class="beginner-primary-card ${escapeHtml(nextState.tone)}">
      <small>下一步建议</small>
      <strong>${escapeHtml(nextStep.title)}</strong>
      <span>${escapeHtml(nextStep.plain)}</span>
      <button class="primary-button" type="button" ${nextAttrs}>${escapeHtml(nextStep.button)}</button>
      ${renderRuntimeGuardHelp(nextStep.action || "")}
    </div>
  `;
  helpNode.innerHTML = statusRows([
    ["小白规则", "先确认安全，再只看 CN_ETF 主线，再回测，再看闸门，最后才做本地模拟。", "ok"],
    ["不要直接用", "CN 个股榜、全部历史榜、单次高收益都不能直接变成实盘 ETF 信号。", "danger"],
    ["点执行前", "所有执行按钮都会弹出安全确认，取消不会产生任何结果。", "warn"],
  ]);
  syncCurrentBacktestRuntimeGuard();
}

function jumpToBeginnerTarget(targetId, leaderboardTab = "") {
  if (leaderboardTab) setLeaderboardTab(leaderboardTab);
  const target = byId(targetId);
  if (!target) return;
  const scrollTarget = jumpTargetForScroll(target);
  const page = target.closest(".page");
  if (page?.id?.startsWith("page-")) {
    const pageName = page.id.replace("page-", "");
    const nav = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (nav && !page.classList.contains("active-page")) nav.click();
    updateHashForBeginnerTarget(pageName, targetId);
  }
  const workspace = document.querySelector(".workspace");
  const workspaceOverflowY = workspace ? getComputedStyle(workspace).overflowY : "";
  if (workspace && /auto|scroll|overlay/.test(workspaceOverflowY) && workspace.scrollHeight > workspace.clientHeight + 1) {
    const workspaceRect = workspace.getBoundingClientRect();
    const targetRect = scrollTarget.getBoundingClientRect();
    const targetTop = workspace.scrollTop + targetRect.top - workspaceRect.top - 96;
    workspace.scrollTo({
      top: Math.max(0, targetTop),
      behavior: scrollBehaviorForDistance(workspace.scrollTop, targetTop),
    });
    return;
  }
  const documentScroller = document.scrollingElement || document.documentElement;
  if (documentScroller?.scrollTo) {
    const targetTop = documentScroller.scrollTop + scrollTarget.getBoundingClientRect().top - 96;
    documentScroller.scrollTo({
      top: Math.max(0, targetTop),
      behavior: scrollBehaviorForDistance(documentScroller.scrollTop, targetTop),
    });
    return;
  }
  const windowTargetTop = scrollTarget.getBoundingClientRect().top + window.scrollY - 96;
  window.scrollTo({
    top: Math.max(0, windowTargetTop),
    behavior: scrollBehaviorForDistance(window.scrollY, windowTargetTop),
  });
}

function jumpTargetForScroll(target) {
  if (!target) return null;
  const rect = target.getBoundingClientRect();
  if (rect.width > 0 && rect.height > 0) return target;
  return target.closest(".control-cell, .panel") || target;
}

function scrollBehaviorForDistance(currentTop, targetTop) {
  return Math.abs(Number(targetTop || 0) - Number(currentTop || 0)) > 2400 ? "auto" : "smooth";
}

async function runBeginnerAction(actionId, button = null) {
  if (!actionId) return;
  if (actionId === "research_backtest" && blockCurrentBacktestRuntime()) return;
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
  const dailyActionNode = byId("ordinary-daily-action-card");
  const warningNode = byId("ordinary-mainline-warning");
  if (!metricsNode || !actionNode || !dailyActionNode || !warningNode) return;
  const ledger = state.factorLeaderboard || {};
  const summary = ledger.summary || {};
  const primaryBoard = ledger.leaderboards?.primary_cn_etf || {};
  const primaryRows = primaryBoard.rows || [];
  const topPrimary = primaryRows[0] || null;
  const project = state.projectStatus || {};
  const paperMetrics = state.paper?.metrics || {};
  const liveGateRows = ordinaryLiveGateActionRows();
  metricsNode.innerHTML = [
    metric("当前主线", summary.primary_market || "CN_ETF", "默认只看 ETF 轮动"),
    metric("主线候选", summary.primary_market_deduped_candidate_rows ?? "--", "CN_ETF 去重参数组合"),
    metric("全部候选", summary.deduped_candidate_rows ?? "--", "所有市场历史去重"),
    metric("模拟权益", formatNumber(paperMetrics.ending_equity), "本地 paper 结果"),
  ].join("");
  actionNode.innerHTML = liveGateRows + statusRows([
    ["现在该看", primaryRows.length ? "CN_ETF 主线榜 Top20" : "先补 CN_ETF 主线候选", primaryRows.length ? "ok" : "warn"],
    ["最靠前候选", topPrimary ? `${topPrimary.factor_name || "--"} / ${topPrimary.promotion_label || "--"}` : "暂无主线候选", topPrimary ? "ok" : "warn"],
    ["项目状态", project.overall_status || "加载中", project.blocker_count ? "warn" : "ok"],
  ]);
  renderOrdinaryDailyActionCard(dailyActionNode);
  warningNode.innerHTML = statusRows([
    ["主线提醒", "默认榜单只展示 CN_ETF。CN 个股资金流、择股类结果只能辅助研究，不能直接替代 ETF 轮动信号。", "danger"],
    ["推广口径", "只有通过长周期、OOS、滚动、成本和风险审计的主线候选，才可能进入模拟盘观察。", "warn"],
    ["安全边界", "本软件当前只做研究和本地模拟盘，不连接券商、不读取账户、不真实下单。", "danger"],
  ]);
}

function ordinaryLiveGateActionRows() {
  const decision = dailyLiveGateDecision();
  if (!decision) {
    return statusRows([
      ["今日总闸门", "等待今日建议加载；先看 CN_ETF 主线和安全边界。", "warn"],
    ]);
  }
  const targetId = decision.target_id || "daily-live-readiness-gate";
  const actionButton = decision.action_workflow ? `
    <button
      class="primary-button"
      type="button"
      data-ordinary-live-gate-action="${escapeRawHtml(decision.action_workflow)}"
      data-beginner-action="${escapeRawHtml(decision.action_workflow)}"
    >${escapeHtml(decision.cta_label || "运行这一步")}</button>
  ` : "";
  const targetButton = `
    <button
      class="${escapeHtml(actionButton ? "secondary-button" : "primary-button")}"
      type="button"
      data-ordinary-live-gate-target="${escapeRawHtml(targetId)}"
      data-beginner-target="${escapeRawHtml(targetId)}"
    >${escapeHtml(actionButton ? "看证据" : decision.cta_label || "看证据")}</button>
  `;
  return `
    <div class="list-row ${escapeHtml(decision.tone || "warn")}">
      <strong>${escapeHtml("今日总闸门")}</strong>
      <span>${escapeHtml(`${decision.title || "等待判断"} / ${decision.reason || ""}`)}</span>
      <span class="beginner-task-actions">${actionButton}${targetButton}</span>
    </div>
  `;
}

function ordinaryDailyActionDecision() {
  const sheet = state.dailyTradeAdvisory?.daily_trade_decision_sheet || {};
  const hasSheet = Object.keys(sheet).length > 0;
  if (!hasSheet) {
    return {
      tone: "warn",
      title: "还没有今日交易决策单",
      plain_action: "先生成今日前三 CN_ETF 建议，再进入模拟盘和人工复核。",
      button_label: "生成今日前三建议",
      workflow_id: "daily_trade_advisory",
      target_id: "daily-trade-decision-sheet",
      factor_count: 0,
      target_count: 0,
      manual_ticket_count: 0,
      completedEvidenceCount: 0,
      missingEvidenceCount: 1,
      next_gate: "今日前三建议",
      order_boundary: "不会自动下单",
    };
  }
  const summary = sheet.summary || {};
  const next = sheet.what_to_do_now || {};
  const system = sheet.trade_system_state || {};
  const permissions = system.permissions || {};
  const progress = system.progress || {};
  const nextGate = system.next_gate || {};
  const runtime = dailyTradeDecisionRuntimeState(sheet);
  const decision = summary.decision || system.mode || "waiting_for_daily_signal";
  const runtimeNext = dailyTradeDecisionNextAction(runtime, next, decision);
  const top3 = Array.isArray(sheet.daily_top3) ? sheet.daily_top3 : [];
  const targetRows = Array.isArray(sheet.combined_targets) ? sheet.combined_targets : [];
  const manualRows = Array.isArray(sheet.manual_broker_handoff_tickets) ? sheet.manual_broker_handoff_tickets : [];
  const dangerousPermission = Boolean(permissions.order_placement_allowed);
  const blocked = decision.includes("blocked") || dangerousPermission || progress.blocked_stage_count > 0;
  return {
    tone: blocked ? "danger" : "warn",
    title: system.mode_label || summary.plain_answer || "等待今日交易决策",
    plain_action: runtimeNext.plain_action || next.plain_action || "先补齐今日证据，再人工核对票据。",
    button_label: runtimeNext.button_label || next.button_label || "查看今日决策",
    workflow_id: runtimeNext.workflow_id || next.workflow_id || "",
    target_id: runtimeNext.target_id || next.target_id || "daily-trade-decision-sheet",
    factor_count: top3.length || summary.selected_factor_count || summary.signal_count || 0,
    target_count: targetRows.length || summary.target_count || 0,
    manual_ticket_count: manualRows.length || summary.manual_ticket_count || 0,
    completedEvidenceCount: runtime.completedEvidenceCount || 0,
    missingEvidenceCount: runtime.missingEvidenceCount || 0,
    next_gate: nextGate.label || nextGate.stage_id || "人工复核",
    order_boundary: dangerousPermission ? "异常：出现下单权限" : "不会自动下单",
  };
}

function renderOrdinaryDailyActionCard(target = byId("ordinary-daily-action-card")) {
  if (!target) return;
  const decision = ordinaryDailyActionDecision();
  const primaryButton = decision.workflow_id ? `
    <button
      class="primary-button"
      type="button"
      data-ordinary-daily-action="${escapeRawHtml(decision.workflow_id)}"
      data-ordinary-daily-target="${escapeRawHtml(decision.target_id)}"
    >${escapeHtml(decision.button_label || "运行下一步")}</button>
  ` : "";
  const evidenceButton = `
    <button
      class="${escapeHtml(primaryButton ? "secondary-button" : "primary-button")}"
      type="button"
      data-ordinary-daily-action=""
      data-ordinary-daily-target="${escapeRawHtml(decision.target_id || "daily-trade-decision-sheet")}"
    >${escapeHtml(primaryButton ? "看证据" : decision.button_label || "看今日决策")}</button>
  `;
  target.innerHTML = `
    <div class="list-row ${escapeHtml(decision.tone || "warn")}">
      <strong>${escapeHtml("今天先做哪一步")}</strong>
      <span>${escapeHtml(decision.title || "等待今日决策")}</span>
      <span>${escapeHtml(decision.plain_action || "先生成今日建议，再跑模拟盘和人工复核。")}</span>
      <span class="beginner-task-actions">${primaryButton}${evidenceButton}</span>
    </div>
  ` + statusRows([
    ["Top 因子/票据", `因子=${formatNumber(decision.factor_count)} / 目标=${formatNumber(decision.target_count)} / 票据=${formatNumber(decision.manual_ticket_count)}`, decision.factor_count ? "ok" : "warn"],
    ["证据进度", `已补=${formatNumber(decision.completedEvidenceCount)} / 还缺=${formatNumber(decision.missingEvidenceCount)} / 下一道门=${decision.next_gate || "--"}`, decision.missingEvidenceCount ? "warn" : "ok"],
    ["实盘边界", decision.order_boundary || "不会自动下单", decision.order_boundary === "不会自动下单" ? "ok" : "danger"],
  ]) + renderOrdinaryExecutionBridgeStrip(state.dailyTradeAdvisory?.daily_signal_execution_bridge || {});
  target.innerHTML += renderOrdinaryRealWorldHandoffStrip(state.dailyTradeAdvisory?.real_world_manual_handoff_gate || {});
}

function renderOrdinaryExecutionBridgeStrip(bridge = {}) {
  const summary = bridge.summary || {};
  if (!Object.keys(summary).length) {
    return statusRows([["落地桥", "等待每日信号落地状态加载。", "warn"]]);
  }
  const status = summary.status || "waiting_for_candidate_pool";
  const tone = status.includes("blocked") ? "danger" : "warn";
  const workflowButton = summary.next_workflow_id ? `
    <button
      class="primary-button"
      type="button"
      data-ordinary-daily-action="${escapeRawHtml(summary.next_workflow_id)}"
      data-ordinary-daily-target="${escapeRawHtml(summary.next_target_id || "daily-signal-execution-bridge")}"
    >${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = `
    <button
      class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}"
      type="button"
      data-ordinary-daily-action=""
      data-ordinary-daily-target="${escapeRawHtml(summary.next_target_id || "daily-signal-execution-bridge")}"
    >${escapeHtml(workflowButton ? "看落地桥" : summary.next_label || "看落地桥")}</button>
  `;
  return `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("落地桥")}</strong>
      <span>${escapeHtml(`${zhConsoleText(status)} / ${summary.next_label || "--"}`)}</span>
      <span>${escapeHtml(`前三直买=${summary.direct_buy_from_top3_allowed ? "异常允许" : "禁止"} / 自动下单=${summary.order_placement_allowed ? "异常允许" : "禁止"}`)}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;
}

function renderOrdinaryRealWorldHandoffStrip(gate = {}) {
  const summary = gate.summary || {};
  if (!Object.keys(summary).length) {
    return statusRows([["实盘前总闸门", "等待人工观察总闸门加载。", "warn"]]);
  }
  const decision = summary.decision || "waiting_for_cn_etf_candidate_pool";
  const tone = dailyRealWorldHandoffTone(decision);
  const workflowButton = summary.next_workflow_id ? `
    <button
      class="primary-button"
      type="button"
      data-ordinary-daily-action="${escapeRawHtml(summary.next_workflow_id)}"
      data-ordinary-daily-target="${escapeRawHtml(summary.next_target_id || "daily-real-world-handoff-gate")}"
    >${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = `
    <button
      class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}"
      type="button"
      data-ordinary-daily-action=""
      data-ordinary-daily-target="${escapeRawHtml(summary.next_target_id || "daily-real-world-handoff-gate")}"
    >${escapeHtml(workflowButton ? "看总闸门" : summary.next_label || "看总闸门")}</button>
  `;
  return `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("实盘前总闸门")}</strong>
      <span>${escapeHtml(summary.plain_answer || zhConsoleText(decision))}</span>
      <span>${escapeHtml(`人工观察=${summary.manual_observation_candidate ? "可准备材料" : "未放行"} / 自动下单=${summary.order_placement_allowed ? "异常允许" : "禁止"}`)}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;
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
    ["排序依据", leaderboardRankingBasisText(summary.ranking_basis || "--"), "muted"],
    ["跳过文件", `${summary.report_files_skipped ?? 0}`, summary.report_files_skipped > 0 ? "warn" : "ok"],
  ]);
  byId("factor-leaderboard-explanation").innerHTML = statusRows([
    ["当前榜单", activeBoard.label || "--", rows.length ? "ok" : "warn"],
    ["榜单说明", activeBoard.description || activeBoard.empty_message || "--", state.leaderboardTab === "primary_cn_etf" ? "ok" : "warn"],
    ["安全边界", "排行榜只用于研究和本地模拟盘观察，不代表可实盘自动交易。", "danger"],
  ]);
  renderFactorRuntimeGapPanel(rows);
  byId("factor-leaderboard-table").innerHTML = renderFactorLeaderboardTable(rows);
}

function leaderboardValue(row = {}, ...keys) {
  const sources = [row.params || {}, row, row.all_data || {}];
  for (const key of keys) {
    for (const source of sources) {
      if (source[key] != null && source[key] !== "") return source[key];
    }
  }
  return "";
}

function leaderboardInputValue(value) {
  if (Array.isArray(value)) return value.join(",");
  if (value == null) return "";
  return String(value).trim();
}

function normalizeLeaderboardWindowValue(value) {
  const text = leaderboardInputValue(value);
  if (!text) return "";
  const numbers = text
    .replaceAll("[", "")
    .replaceAll("]", "")
    .split(",")
    .map((item) => Number(String(item).trim()))
    .filter((item) => Number.isInteger(item) && item > 0);
  return numbers.length ? Array.from(new Set(numbers)).join(",") : text;
}

function leaderboardRowPayload(row = {}) {
  return {
    case_id: leaderboardInputValue(row.case_id),
    market: leaderboardInputValue(leaderboardValue(row, "market")),
    factor_name: leaderboardInputValue(leaderboardValue(row, "factor_name", "factor")),
    factor_windows: normalizeLeaderboardWindowValue(leaderboardValue(row, "factor_windows", "windows", "lookback_windows")),
    top_n: leaderboardInputValue(leaderboardValue(row, "top_n", "topN", "top")),
    cost_bps: leaderboardInputValue(leaderboardValue(row, "cost_bps", "cost", "transaction_cost_bps")),
    start_date: leaderboardInputValue(leaderboardValue(row, "start_date", "train_start_date", "backtest_start_date")),
    end_date: leaderboardInputValue(leaderboardValue(row, "end_date", "test_end_date", "backtest_end_date")),
    execution_lag: leaderboardInputValue(leaderboardValue(row, "execution_lag", "lag")),
    forward_horizon: leaderboardInputValue(leaderboardValue(row, "forward_horizon", "horizon")),
    rebalance_interval: leaderboardInputValue(leaderboardValue(row, "rebalance_interval", "rebalance", "holding_period")),
  };
}

function runtimeFactorNames() {
  return new Set((state.snapshot?.available_factors || [])
    .map((name) => leaderboardInputValue(name))
    .filter(Boolean));
}

function factorRuntimeStatus(row = {}) {
  const factor = leaderboardInputValue(row.factor_name);
  const runnable = Boolean(factor && runtimeFactorNames().has(factor));
  if (runnable) {
    return {
      runnable: true,
      label: "可直接回测",
      tone: "ok",
      detail: "当前后端已注册这个因子，可以直接套用并本地回测。",
    };
  }
  return {
    runnable: false,
    label: factor ? "需先注册" : "因子缺失",
    tone: "warn",
    detail: factor
      ? "榜单里有这个候选，但当前运行下拉框没有；可以先套用查看参数，注册到运行因子后再回测。"
      : "这行没有可识别的因子名，不能直接回测。",
  };
}

function leaderboardRuntimeRows(rows = []) {
  const runtimeRows = rows.map((row) => {
    const payload = leaderboardRowPayload(row);
    return {
      ...payload,
      promotion_label: leaderboardInputValue(row.promotion_label),
      plain_conclusion: leaderboardInputValue(row.plain_conclusion),
      source_file: leaderboardInputValue(row.source_file || row.source_path),
      runtime: factorRuntimeStatus(payload),
    };
  });
  const missing = runtimeRows.filter((row) => !row.runtime.runnable);
  const byFactor = new Map();
  missing.forEach((row) => {
    const key = row.factor_name || "unknown";
    const item = byFactor.get(key) || { factor_name: key, count: 0, case_id: row.case_id, source_file: row.source_file, sample_row: row };
    item.count += 1;
    if (!item.case_id && row.case_id) item.case_id = row.case_id;
    if (!item.source_file && row.source_file) item.source_file = row.source_file;
    if (!item.sample_row) item.sample_row = row;
    byFactor.set(key, item);
  });
  return {
    rows: runtimeRows,
    runnable: runtimeRows.filter((row) => row.runtime.runnable),
    missing,
    unique_missing: Array.from(byFactor.values()),
  };
}

function leaderboardRuntimeGapRowPayload(item = {}) {
  const row = item.sample_row || item;
  return encodeURIComponent(JSON.stringify(leaderboardRowPayload(row)));
}

function renderFactorRuntimeGapPanel(rows = []) {
  const panel = byId("factor-runtime-gap-panel");
  const summaryTarget = byId("factor-runtime-gap-summary");
  const listTarget = byId("factor-runtime-gap-list");
  if (!panel || !summaryTarget || !listTarget) return;
  const audit = leaderboardRuntimeRows(rows);
  const missingCount = audit.missing.length;
  const runnableCount = audit.runnable.length;
  panel.classList.toggle("ok", missingCount === 0);
  panel.classList.toggle("warn", missingCount > 0);
  summaryTarget.innerHTML = statusRows([
    ["可直接回测", `${runnableCount} 个榜单参数组合`, runnableCount ? "ok" : "warn"],
    ["需要先注册", `${missingCount} 个榜单参数组合 / ${audit.unique_missing.length} 个唯一因子`, missingCount ? "warn" : "ok"],
    ["新手该怎么做", missingCount ? "黄色行先别点回测；先套用参数查看，等因子注册到运行下拉框后再回测。" : "当前榜单都能从 GUI 直接套用并本地回测。", missingCount ? "warn" : "ok"],
  ]);
  if (!missingCount) {
    listTarget.innerHTML = `
      <div class="factor-runtime-gap-row ok">
        <strong>当前没有运行缺口</strong>
        <span>排行榜里的因子都在当前运行下拉框里。</span>
      </div>
    `;
    return;
  }
  listTarget.innerHTML = audit.unique_missing.slice(0, 5).map((item) => {
    const rowPayload = leaderboardRuntimeGapRowPayload(item);
    return `
      <div class="factor-runtime-gap-row warn">
        <strong>${escapeHtml(item.factor_name)}</strong>
        <span>${escapeHtml(`${item.count} 个参数组合需要注册；示例 ${item.case_id || "--"}`)}</span>
        <span class="factor-runtime-gap-actions">
          <button class="secondary-button factor-runtime-gap-apply" type="button" data-factor-runtime-gap-apply="true" data-factor-row="${escapeHtml(rowPayload)}">套用示例参数</button>
          <button class="secondary-button factor-runtime-gap-action" type="button" data-factor-runtime-gap-action="true">看榜单行</button>
        </span>
      </div>
    `;
  }).join("");
}

function leaderboardRowFromButton(button) {
  try {
    return JSON.parse(decodeURIComponent(button?.dataset?.factorRow || "{}"));
  } catch (_error) {
    return {};
  }
}

function applyLeaderboardRowToForms(row = {}) {
  markManualFormOverride("factor_leaderboard_row");
  const factor = leaderboardInputValue(row.factor_name);
  const market = leaderboardInputValue(row.market);
  if (market) {
    setValue("market-select", market);
    setValue("paper-market-select", market);
  }
  if (factor) {
    setFactorValue("factor-select", factor);
    setFactorValue("paper-factor-select", factor);
  }
  if (row.factor_windows) setValue("factor-windows", leaderboardInputValue(row.factor_windows));
  if (row.top_n) {
    setValue("research-top-n", leaderboardInputValue(row.top_n));
    setValue("signal-top-n", leaderboardInputValue(row.top_n));
    setValue("paper-top-n", leaderboardInputValue(row.top_n));
  }
  if (row.cost_bps) setValue("research-cost-bps", leaderboardInputValue(row.cost_bps));
  if (row.start_date) {
    setValue("start-date", leaderboardInputValue(row.start_date));
    setValue("paper-start-date", leaderboardInputValue(row.start_date));
  }
  if (row.end_date) {
    setValue("end-date", leaderboardInputValue(row.end_date));
    setValue("signal-as-of", leaderboardInputValue(row.end_date));
    setValue("paper-end-date", leaderboardInputValue(row.end_date));
  }
  if (row.execution_lag) setValue("execution-lag", leaderboardInputValue(row.execution_lag));
  if (row.forward_horizon) setValue("forward-horizon", leaderboardInputValue(row.forward_horizon));
  if (row.rebalance_interval) setValue("rebalance-interval", leaderboardInputValue(row.rebalance_interval));
  renderRequestPreview();
  renderControlCenter();
  showToast(`已套用排行榜候选：${factor || row.case_id || "当前行"}`);
  jumpToBeginnerTarget("beginner-parameter-explainer", state.leaderboardTab);
}

function dailyPaperHandoffFromButton(button) {
  try {
    const payload = button?.dataset?.dailyPaperHandoffApply || button?.dataset?.dailyPaperHandoffRun || "{}";
    return JSON.parse(decodeURIComponent(payload));
  } catch (_error) {
    return {};
  }
}

function applyDailyPaperHandoffToForm(request = {}) {
  markManualFormOverride("daily_paper_handoff");
  if (request.market) setValue("paper-market-select", String(request.market));
  if (request.factor) setFactorValue("paper-factor-select", String(request.factor));
  if (request.factor_windows) setValue("factor-windows", leaderboardInputValue(request.factor_windows));
  if (request.top_n != null) setValue("paper-top-n", leaderboardInputValue(request.top_n));
  if (request.rebalance_interval != null) setValue("rebalance-interval", leaderboardInputValue(request.rebalance_interval));
  if (request.initial_cash != null) setValue("paper-initial-cash", leaderboardInputValue(request.initial_cash));
  if (request.commission_bps != null) setValue("paper-commission-bps", leaderboardInputValue(request.commission_bps));
  if (request.slippage_bps != null) setValue("paper-slippage-bps", leaderboardInputValue(request.slippage_bps));
  if (request.max_asset_weight != null) setValue("paper-max-asset-weight", leaderboardInputValue(request.max_asset_weight));
  if (request.max_market_weight != null) setValue("paper-max-market-weight", leaderboardInputValue(request.max_market_weight));
  if (request.max_gross_exposure != null) setValue("paper-max-gross-exposure", leaderboardInputValue(request.max_gross_exposure));
  if (request.min_cash_weight != null) setValue("paper-min-cash-weight", leaderboardInputValue(request.min_cash_weight));
  renderRequestPreview();
  renderControlCenter();
  showToast(`已填入模拟盘参数：${request.factor || "当前因子"}`);
  activatePage("paper", true);
  jumpToBeginnerTarget("paper-metrics");
}

async function runDailyPaperHandoffSimulation(button) {
  const request = dailyPaperHandoffFromButton(button);
  applyDailyPaperHandoffToForm(request);
  await runBeginnerAction("paper_simulation", button);
}

function renderFactorLeaderboardTable(rows) {
  if (!rows.length) {
    const board = getActiveLeaderboard();
    return `<tr><td colspan="18">${escapeHtml(board.empty_message || "暂无候选")}</td></tr>`;
  }
  const head = `
    <tr>
      <th>排名</th>
      <th>结论</th>
      <th>因子 / 编号</th>
      <th>操作</th>
      <th>市场</th>
      <th>总收益</th>
      <th>年化</th>
      <th>夏普</th>
      <th>最大回撤</th>
      <th>胜率</th>
      <th>排序相关性</th>
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
    const params = leaderboardParamsText(row);
    const allData = row.all_data && Object.keys(row.all_data).length ? JSON.stringify(row.all_data, null, 2) : "{}";
    const badges = (row.audit_badges || []).map((badge) => `<span class="mini-badge">${escapeHtml(leaderboardReasonText(badge))}</span>`).join(" ");
    const rowPayload = encodeURIComponent(JSON.stringify(leaderboardRowPayload(row)));
    const runtime = factorRuntimeStatus(leaderboardRowPayload(row));
    return `
      <tr>
        <td>${formatNumber(row.rank)}</td>
        <td><strong>${escapeHtml(row.promotion_label || "--")}</strong><br><span class="muted">${escapeHtml(row.plain_conclusion || "--")}</span></td>
        <td><strong>${escapeHtml(row.factor_name || "--")}</strong><br><span class="muted">${escapeHtml(row.case_id || "--")}</span></td>
        <td>
          <span class="factor-row-actions">
            <span class="mini-badge factor-row-runtime ${escapeHtml(runtime.tone)}" data-factor-runtime="${runtime.runnable ? "runtime" : "missing"}" title="${escapeHtml(runtime.detail)}">${escapeHtml(runtime.label)}</span>
            <button class="secondary-button" type="button" data-factor-apply-row="true" data-factor-row="${escapeHtml(rowPayload)}">套用参数</button>
            <button class="primary-button" type="button" data-factor-run-row="true" data-factor-row="${escapeHtml(rowPayload)}" title="${escapeHtml(runtime.detail)}"${runtime.runnable ? "" : " disabled"}>套用并回测</button>
          </span>
        </td>
        <td>${escapeHtml(row.market || "--")}</td>
        <td>${formatPercent(row.total_return)}</td>
        <td>${formatPercent(row.annualized_return)}</td>
        <td>${formatDecimal(row.sharpe)}</td>
        <td>${formatPercent(row.max_drawdown)}</td>
        <td>${formatPercent(row.win_rate)}</td>
        <td>${formatDecimal(row.rank_ic)}</td>
        <td>${formatNumber(row.trade_count)}</td>
        <td><code>${escapeHtml(params)}</code></td>
        <td>${badges || "--"}</td>
        <td>${escapeHtml(leaderboardQualityText(row.ranking_quality))}<br><span class="muted">${escapeHtml(leaderboardReasonText((row.ranking_reasons || []).join(" / ") || "ok"))}</span></td>
        <td>${escapeHtml(leaderboardScoreText(row))}</td>
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
  renderDailyReadinessCard();
  renderDailyEvidenceChain();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  renderDailyRealWorldHandoffGate(state.dailyTradeAdvisory?.real_world_manual_handoff_gate || {});
}

function renderDailyTradeAdvisory() {
  const pack = state.dailyTradeAdvisory || {};
  const summary = pack.summary || {};
  const positionValidation = pack.current_position_validation || {};
  const tag = byId("daily-trade-advisory-tag");
  const signalCount = Number(summary.signal_count || 0);
  const selectedCount = Number(summary.selected_factor_count || 0);
  const status = signalCount > 0 ? "manual_advisory_ready" : "waiting_for_signals";
  if (tag) {
    tag.textContent = zhConsoleText(status);
    tag.classList.toggle("tag-warn", signalCount === 0);
  }
  byId("daily-trade-advisory-metrics").innerHTML = [
    metric("前三因子", selectedCount || "--", pack.fallback_used ? "可运行基线兜底" : "排行榜候选"),
    metric("信号数", signalCount || "--", pack.run_date || "today"),
    metric("目标ETF", summary.combined_target_count ?? pack.combined_target_count ?? "--", pack.market || "CN_ETF"),
    metric("手工工单", summary.manual_ticket_count ?? pack.manual_trade_plan?.length ?? "--", "系统不下单"),
    metric("已填持仓", summary.current_position_count ?? 0, summary.current_position_count ? "按净差额" : "按目标仓位"),
    metric("实盘自动化", summary.live_trading_allowed ? "允许" : "禁止", "research-to-paper"),
    metric("下单权限", summary.order_placement_allowed ? "允许" : "禁止", "manual only"),
  ].join("");
  byId("daily-trade-advisory-status").innerHTML = statusRows([
    ["来源", pack.fallback_used ? "排行榜无可运行前三，使用可运行基线兜底" : "从 CN_ETF 排行榜取可运行前三候选", pack.fallback_used ? "warn" : "ok"],
    ["信号状态", `${signalCount} / ${selectedCount}`, signalCount > 0 ? "ok" : "warn"],
    ["当前持仓", positionValidation.plain_summary || "未填写当前持仓；将按目标仓位估算。", positionValidation.status === "error" ? "danger" : positionValidation.status === "ok" ? "ok" : "warn"],
    ["执行边界", pack.safety || "Research-to-paper only", "danger"],
    ["下一步", summary.next_action || "先复核信号，再看模拟盘，不自动下单。", "warn"],
    ["错误", (pack.signal_errors || []).map((item) => item.factor_name || item.case_id).join(" / ") || "无", pack.signal_errors?.length ? "warn" : "ok"],
  ]);
  renderDailyBeginnerActionSummary(pack.beginner_action_summary || {});
  renderDailyCurrentPositionHelp(positionValidation);
  renderDailyPortfolioValueHelp();
  renderDailyLiveReadinessGate(pack.daily_live_readiness_gate || {});
  renderDailyTradeDecisionSheet(pack.daily_trade_decision_sheet || {});
  renderDailySignalExecutionBridge(pack.daily_signal_execution_bridge || {});
  renderDailyDeploymentReadiness(pack.daily_deployment_readiness || {});
  renderLiveProfitabilityReadiness(pack.live_profitability_readiness || {});
  renderDailyClosureStreak(pack.live_profitability_readiness || {});
  renderDailyRealMoneyTransitionGate(pack.daily_real_money_transition_gate || {});
  renderDailyFactorHealthMonitor(pack.daily_factor_health_monitor || {});
  renderDailyRealWorldHandoffGate(pack.real_world_manual_handoff_gate || {});
  renderDailyTradingSystemBlueprint(pack.trading_system_blueprint || {});
  renderDailyPretradeReadiness(pack.pretrade_readiness || {});
  renderDailyPretradeNextActions(pack.operator_next_actions || pack.pretrade_workflow?.operator_next_actions || []);
  renderManualBrokerHandoff(pack.manual_broker_handoff || {});
  renderDailyPretradeWorkflow(pack.pretrade_workflow || {});
  renderDailyLiveTransitionPlan(pack.live_transition_plan || {});
  renderDailyCommandRail();
  renderOrdinaryHome();
  renderDailyReadinessCard();
  renderDailyEvidenceChain();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
  byId("daily-trade-factor-table").innerHTML = tableRows(pack.factors || [], [
    "rank",
    "factor_name",
    "case_id",
    "market",
    "sharpe",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "rank_ic",
    "promotion_label",
  ]);
  byId("daily-trade-target-table").innerHTML = tableRows(pack.combined_targets || [], [
    "asset_id",
    "market",
    "target_weight",
    "target_value",
    "latest_price",
    "source_factors",
    "executable",
  ]);
  byId("daily-trade-manual-table").innerHTML = tableRows(pack.manual_trade_plan || [], [
    "ticket_id",
    "asset_id",
    "side",
    "current_quantity",
    "current_value",
    "target_weight",
    "target_value",
    "delta_value",
    "latest_price",
    "estimated_quantity",
    "rounded_quantity",
    "rounded_quantity_delta",
    "rounded_value",
    "cash_delta_after_rounding",
    "source_factors",
    "live_order_allowed",
    "manual_instruction",
  ]);
}

function currentPositionInputState(validation = {}) {
  const raw = valueOf("daily-current-positions").trim();
  if (!raw) {
    return {
      tone: "warn",
      title: "当前持仓安全检查",
      summary: "可留空；留空时系统按目标仓位估算，不按净差额调仓。",
      columns: "模板：asset_id,quantity,latest_price",
      issue: "不要粘贴账户号、券商号、真实委托号。",
    };
  }
  const header = raw.split(/\r?\n/)[0] || "";
  const columns = header.split(",").map((item) => item.trim().toLowerCase()).filter(Boolean);
  const forbidden = columns.filter((item) => FORBIDDEN_CURRENT_POSITION_COLUMNS.has(item));
  if (forbidden.length) {
    return {
      tone: "danger",
      title: "当前持仓安全检查",
      summary: "红灯：发现真实账户或券商字段，先删掉这些列再生成今日建议。",
      columns: `危险字段=${forbidden.join(", ")}`,
      issue: "current_position_forbidden_field：只允许纸面持仓字段，不允许账户、券商或订单字段。",
    };
  }
  const missing = ["asset_id", "quantity"].filter((item) => !columns.includes(item));
  if (missing.length) {
    return {
      tone: "warn",
      title: "当前持仓安全检查",
      summary: "黄灯：当前持仓格式还不完整，生成建议前请补齐必要列。",
      columns: `缺少=${missing.join(", ")} / 当前列=${columns.join(", ") || "--"}`,
      issue: "最少需要 asset_id 和 quantity；latest_price 可用于更准确估算。",
    };
  }
  const backendIssue = validation.status === "error" ? validation.plain_summary : "";
  return {
    tone: backendIssue ? "danger" : "ok",
    title: "当前持仓安全检查",
    summary: backendIssue || "格式可用于纸面净差额估算；系统仍不会读取账户或自动下单。",
    columns: `当前列=${columns.join(", ")}`,
    issue: "只用于本地人工复核，不连接券商、不读取账户。",
  };
}

function renderDailyCurrentPositionHelp(validation = {}) {
  const target = byId("daily-current-position-help");
  if (!target) return;
  const stateInfo = currentPositionInputState(validation);
  target.innerHTML = statusRows([
    [stateInfo.title, stateInfo.summary, stateInfo.tone],
    ["允许格式", stateInfo.columns, stateInfo.tone === "danger" ? "danger" : "muted"],
    ["安全边界", stateInfo.issue, stateInfo.tone === "danger" ? "danger" : "warn"],
  ]);
}

function portfolioValueInputState() {
  const raw = valueOf("daily-trade-portfolio-value");
  const value = Number(raw);
  if (!raw || !Number.isFinite(value) || value <= 0) {
    return {
      tone: "danger",
      title: "纸面资金规模",
      summary: "红灯：先填一个大于 0 的纸面资金数值。",
      detail: "paper_capital_only：它只用于估算目标仓位和人工复核票据，不读取真实账户。",
    };
  }
  const riskProfile = valueOf("daily-trade-risk-profile") || "balanced_20dd";
  return {
    tone: value < 10000 ? "warn" : "ok",
    title: "纸面资金规模",
    summary: `当前按 ${formatNumber(value)} 作为纸面估算资金。`,
    detail: `paper_capital_only：风险档位=${riskProfile}；这个数不会读取账户、不会连接券商、不会自动下单。`,
  };
}

function renderDailyPortfolioValueHelp() {
  const target = byId("daily-portfolio-value-help");
  if (!target) return;
  const info = portfolioValueInputState();
  target.innerHTML = statusRows([
    [info.title, info.summary, info.tone],
    ["用途", "只用于估算目标仓位、一手取整和人工复核票据。", "warn"],
    ["安全边界", info.detail, info.tone === "danger" ? "danger" : "ok"],
  ]);
}

function renderDailyBeginnerActionSummary(actionSummary = {}) {
  const target = byId("daily-beginner-action-summary");
  if (!target) return;
  const summary = actionSummary.summary || {};
  const tickets = actionSummary.ticket_summary || {};
  const steps = Array.isArray(actionSummary.steps) ? actionSummary.steps : [];
  const decision = summary.decision || "waiting_for_daily_signal";
  const tone = decision === "fix_current_positions_first" || decision === "resolve_blockers_first" ? "danger" : decision === "manual_review_only" ? "warn" : "warn";
  const overview = statusRows([
    ["结论", zhConsoleText(decision), tone],
    ["先做什么", summary.primary_action || "先生成今日前三建议。", tone],
    ["原因", summary.primary_reason || "等待今日建议加载。", "muted"],
    ["票据统计", `买入=${formatNumber(tickets.buy_ticket_count || 0)} / 卖出=${formatNumber(tickets.sell_ticket_count || 0)} / 保持=${formatNumber(tickets.hold_ticket_count || 0)}`, "muted"],
    ["自动下单", summary.order_placement_allowed ? "异常开启" : "禁止", summary.order_placement_allowed ? "danger" : "ok"],
  ]);
  const stepRows = steps.length ? steps.map((item) => `
    <div class="list-row ${escapeHtml(item.status?.includes("blocked") ? "danger" : "warn")}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.title || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.gui_target ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("看这一步")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["等待建议", "先生成今日前三交易建议。", "warn"]]);
  target.innerHTML = overview + stepRows;
}

function renderDailyLiveReadinessGate(gate = {}) {
  const summaryTarget = byId("daily-live-readiness-summary");
  const rowTarget = byId("daily-live-readiness-rows");
  const ladderTarget = byId("daily-live-readiness-ladder");
  const shortcutTarget = byId("daily-live-readiness-shortcuts");
  if (!summaryTarget || !rowTarget || !ladderTarget || !shortcutTarget) return;
  const summary = gate.summary || {};
  const decision = summary.decision || "waiting_for_daily_signal";
  const tone = decision.includes("blocked") ? "danger" : decision === "paper_rehearsal_required" ? "warn" : "warn";
  const rows = Array.isArray(gate.gate_rows) ? gate.gate_rows : [];
  const ladder = Array.isArray(gate.mode_ladder) ? gate.mode_ladder : [];
  const shortcuts = Array.isArray(gate.forbidden_shortcuts) ? gate.forbidden_shortcuts : [];
  summaryTarget.innerHTML = statusRows([
    ["总判定", zhConsoleText(decision), tone],
    ["先做什么", summary.primary_action || "先生成今日前三 CN_ETF 因子信号。", tone],
    ["原因", summary.primary_reason || "等待今日建议加载。", "muted"],
    ["自动下单", summary.order_placement_allowed ? "异常开启" : "锁定禁止", summary.order_placement_allowed ? "danger" : "ok"],
  ]);
  rowTarget.innerHTML = rows.length ? rows.map((item) => {
    const rowTone = item.status === "blocked" ? "danger" : item.status === "ready" ? "ok" : item.status === "locked" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
        <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_check || ""}`)}</span>
        <span class="beginner-task-actions">
          ${item.gui_target ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("看证据")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["等待闸门", "生成今日建议后显示每个实盘前门槛。", "warn"]]);
  ladderTarget.innerHTML = ladder.length ? ladder.map((item, index) => {
    const rowTone = item.status === "ready" ? "ok" : item.status === "locked" || item.status === "blocked" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(`${index + 1}. ${item.label || item.mode_id || ""}`)}</strong>
        <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_state || ""}`)}</span>
      </div>
    `;
  }).join("") : statusRows([["阶段", "研究信号 → 模拟盘 → 人工复核 → 小资金观察 → 实盘交易锁定。", "warn"]]);
  shortcutTarget.innerHTML = shortcuts.length ? shortcuts.map((item) => `
    <div class="list-row danger">
      <strong>${escapeHtml(zhConsoleText(item.shortcut_id || "禁止捷径"))}</strong>
      <span>${escapeHtml(item.plain_warning || "不要绕过实盘前闸门。")}</span>
    </div>
  `).join("") : statusRows([["禁止捷径", "不要把今日前三、旧信号或单次高收益直接当成实盘交易指令。", "danger"]]);
}

function renderDailyTradeDecisionSheet(sheet = {}) {
  const root = byId("daily-trade-decision-sheet");
  const summaryTarget = byId("daily-trade-decision-summary");
  const top3Target = byId("daily-trade-decision-top3");
  const candidatePoolTarget = byId("daily-trade-decision-candidate-pool");
  const actionTarget = byId("daily-trade-decision-actions");
  const evidenceTarget = byId("daily-trade-decision-evidence");
  const systemTarget = byId("daily-trade-system-state");
  const packageTarget = byId("daily-trade-package-checklist");
  if (!root || !summaryTarget || !systemTarget || !packageTarget || !top3Target || !candidatePoolTarget || !actionTarget || !evidenceTarget) return;
  const summary = sheet.summary || {};
  const next = sheet.what_to_do_now || {};
  const decision = summary.decision || "waiting_for_daily_signal";
  const tone = decision.includes("blocked") ? "danger" : decision === "paper_first_manual_review" ? "warn" : "warn";
  const runtime = dailyTradeDecisionRuntimeState(sheet);
  const runtimeNext = dailyTradeDecisionNextAction(runtime, next, decision);
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const journalReceiptCount = executionReceiptsForWorkflow("post_close_journal").length;
  summaryTarget.innerHTML = statusRows([
    ["证据进度", `已补=${formatNumber(runtime.completedEvidenceCount)} / 还缺=${formatNumber(runtime.missingEvidenceCount)} / 下一步=${runtimeNext.button_label || "--"}`, runtime.missingEvidenceCount ? "warn" : "ok"],
    ["今日结论", zhConsoleText(decision), tone],
    ["一句话", summary.plain_answer || "先生成今日前三 CN_ETF 建议，再按证据链复核。", tone],
    ["下一步", next.plain_action || next.button_label || "查看今日建议", tone],
    ["信号/票据", `信号=${formatNumber(summary.signal_count || 0)} / 目标=${formatNumber(summary.target_count || 0)} / 票据=${formatNumber(summary.manual_ticket_count || 0)}`, "muted"],
    ["自动下单", summary.order_placement_allowed ? "异常开启" : "禁止", summary.order_placement_allowed ? "danger" : "ok"],
  ]);
  renderDailyTradeSystemState(sheet.trade_system_state || {}, runtime, systemTarget);
  renderDailyTradePackageChecklist(sheet.trade_package_checklist || {}, runtime, packageTarget);

  const top3 = Array.isArray(sheet.daily_top3) ? sheet.daily_top3 : [];
  top3Target.innerHTML = top3.length ? top3.map((item, index) => `
    <div class="list-row ${escapeHtml(item.signal_status === "signal_ready" ? "ok" : "warn")}">
      <strong>${escapeHtml(`${item.rank || index + 1}. ${item.factor_name || "--"}`)}</strong>
      <span>${escapeHtml(`信号=${zhConsoleText(item.signal_status || "missing")} / 日期=${item.signal_date || "--"} / 目标=${formatNumber(item.target_count || 0)}`)}</span>
      <span>${escapeHtml(`Sharpe=${formatDecimal(item.sharpe)} / 年化=${formatPercent(item.annualized_return)} / 回撤=${formatPercent(item.max_drawdown)} / 胜率=${formatPercent(item.win_rate)} / RankIC=${formatDecimal(item.rank_ic)}`)}</span>
      <span>${escapeHtml(item.plain_conclusion || item.promotion_label || "只作为今日复核输入，不是直接买入指令。")}</span>
    </div>
  `).join("") : statusRows([["Top3 因子", "暂无今日候选。先生成今日前三 CN_ETF 建议。", "warn"]]);

  renderDailyCandidatePoolTop20(sheet.candidate_pool_top20 || {}, candidatePoolTarget);

  const actions = Array.isArray(sheet.today_actions) ? sheet.today_actions : [];
  actionTarget.innerHTML = actions.length ? actions.map((item) => `
    <div class="list-row warn">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.asset_id || "--"} / ${zhConsoleText(item.side || "review")}`)}</strong>
      <span>${escapeHtml(`参考价=${formatNumber(item.reference_price)} / 数量=${formatNumber(item.rounded_quantity)} / 金额=${formatNumber(item.rounded_value)} / 权重=${formatPercent(item.target_weight)}`)}</span>
      <span>${escapeHtml(item.plain_instruction || "仅供人工复核，不是订单。")}</span>
      <span>${escapeHtml(item.order_placement_allowed ? "异常：允许下单" : "系统下单=禁止")}</span>
    </div>
  `).join("") : statusRows([["今日票据", "暂无可复核票据。红灯或无信号时不要手工买卖。", "danger"]]);

  const evidenceRows = runtime.evidenceRows;
  evidenceTarget.innerHTML = evidenceRows.length ? evidenceRows.map((item) => {
    const localStatus = item.runtime_status || item.status || "missing";
    const rowTone = dailyTradeDecisionEvidenceTone(localStatus);
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(zhConsoleText(localStatus))}</span>
        <span>${escapeHtml(item.why || "")}</span>
        <span class="beginner-task-actions">
          ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("看证据")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["缺失证据", "暂无结构化缺失项；仍需人工确认模拟盘、风险、现金和券商端实时价格。", "warn"]]);
}

function renderDailyCandidatePoolTop20(pool = {}, target) {
  if (!target) return;
  const summary = pool.summary || {};
  const rows = Array.isArray(pool.rows) ? pool.rows.slice(0, 20) : [];
  const displayRows = rows.map((row) => ({
    "排名": row.rank ?? "--",
    "因子 / 参数": `${row.factor_name || "--"} / ${dailyCandidatePoolParamsText(row.params || {})}`,
    "状态": zhConsoleText(row.selection_status || "--"),
    "为什么": row.selection_reason || row.advisory_eligibility_reason || "--",
    "核心数据": `Sharpe=${formatDecimal(row.sharpe)} / 年化=${formatPercent(row.annualized_return)} / 回撤=${formatPercent(row.max_drawdown)} / 胜率=${formatPercent(row.win_rate)} / RankIC=${formatDecimal(row.rank_ic)}`,
    "可运行": row.runnable_today ? "是" : "否",
    "可直买": row.direct_buy_allowed || summary.direct_buy_from_leaderboard_allowed ? "异常允许" : "不允许",
  }));
  const emptyRow = {
    "排名": "--",
    "因子 / 参数": "暂无候选池",
    "状态": "等待生成今日建议",
    "为什么": summary.plain_rule || "先生成今日前三建议，再查看 Top20 候选池。",
    "核心数据": "--",
    "可运行": "--",
    "可直买": "不允许",
  };
  target.innerHTML = tableRows(displayRows.length ? displayRows : [emptyRow], [
    "排名",
    "因子 / 参数",
    "状态",
    "为什么",
    "核心数据",
    "可运行",
    "可直买",
  ]);
}

function dailyCandidatePoolParamsText(params = {}) {
  if (!params || typeof params !== "object" || Array.isArray(params)) return "--";
  const entries = Object.entries(params)
    .filter(([key, value]) => key && value !== undefined && value !== null && String(value) !== "")
    .slice(0, 8)
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("/") : value}`);
  return entries.length ? entries.join(", ") : "--";
}

function renderDailySignalExecutionBridge(bridge = {}) {
  const summaryTarget = byId("daily-signal-execution-summary");
  const paperTarget = byId("daily-signal-execution-paper");
  const stepsTarget = byId("daily-signal-execution-steps");
  const gatesTarget = byId("daily-signal-execution-gates");
  if (!summaryTarget || !paperTarget || !stepsTarget || !gatesTarget) return;
  const summary = bridge.summary || {};
  const status = summary.status || "waiting_for_candidate_pool";
  const statusTone = status.includes("blocked") ? "danger" : status.includes("ready") ? "warn" : "warn";
  const nextTarget = summary.next_target_id || "daily-signal-execution-bridge";
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const nextButton = `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(nextTarget)}">${escapeHtml(workflowButton ? "看证据" : summary.next_label || "看下一步")}</button>
  `;
  summaryTarget.innerHTML = statusRows([
    ["落地状态", zhConsoleText(status), statusTone],
    ["下一步", summary.next_label || "--", statusTone],
    ["今日链路", `候选=${formatNumber(summary.selected_factor_count || 0)} / 信号=${formatNumber(summary.signal_count || 0)} / 目标=${formatNumber(summary.target_count || 0)} / 票据=${formatNumber(summary.manual_ticket_count || 0)}`, summary.blocker_count ? "danger" : "warn"],
    ["前三因子", summary.direct_buy_from_top3_allowed ? "异常：允许直买" : "只进候选池，不能直接买", summary.direct_buy_from_top3_allowed ? "danger" : "ok"],
    ["实盘权限", summary.order_placement_allowed ? "异常：允许下单" : "系统不连接券商、不读账户、不自动下单", summary.order_placement_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(statusTone)}">
      <strong>${escapeHtml("现在点这里")}</strong>
      <span>${escapeHtml(summary.next_label || "等待下一步")}</span>
      <span class="beginner-task-actions">${workflowButton}${nextButton}</span>
    </div>
  `;
  const handoff = bridge.paper_simulation_handoff || {};
  const handoffSummary = handoff.summary || {};
  const paperRequest = handoff.recommended_request || {};
  const paperReceiptStatus = dailyPaperReceiptStatus(handoff);
  const handoffPayload = encodeURIComponent(JSON.stringify(paperRequest));
  paperTarget.innerHTML = Object.keys(paperRequest).length ? statusRows([
    ["模拟盘交接", `${handoffSummary.default_factor_name || paperRequest.factor || "--"} / 窗口=${paperRequest.factor_windows || "--"} / TopN=${formatNumber(paperRequest.top_n || 0)}`, handoffSummary.status === "ready" ? "warn" : "danger"],
    ["同参数请求", `资金=${formatNumber(paperRequest.initial_cash)} / 成本=${formatNumber(paperRequest.commission_bps)}bps+${formatNumber(paperRequest.slippage_bps)}bps / 调仓=${formatNumber(paperRequest.rebalance_interval)}`, "warn"],
    ["接口边界", handoff.plain_warning || "模拟盘参数只用于本地回放，不是订单。", "danger"],
  ]) + renderDailyPaperReceiptStatusRows(paperReceiptStatus) + `
    <div class="list-row warn">
      <strong>${escapeHtml("填入模拟盘表单")}</strong>
      <span>${escapeHtml("把排名第一候选参数填到纸面模拟页，运行前仍会弹出安全确认。")}</span>
      <span class="beginner-task-actions">
        <button class="primary-button" type="button" data-daily-paper-handoff-apply="${escapeRawHtml(handoffPayload)}">${escapeHtml("填入模拟盘参数")}</button>
        <button class="primary-button" type="button" data-daily-paper-handoff-run="${escapeRawHtml(handoffPayload)}" data-beginner-action="paper_simulation">${escapeHtml("填参并运行模拟盘复核")}</button>
        <button class="secondary-button" type="button" data-beginner-target="paper-metrics">${escapeHtml("看模拟盘")}</button>
      </span>
    </div>
  ` : statusRows([["模拟盘交接", "等待每日前三候选生成后，显示同参数模拟盘请求。", "warn"]]);
  const steps = Array.isArray(bridge.daily_operating_steps) ? bridge.daily_operating_steps : [];
  stepsTarget.innerHTML = steps.length ? steps.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["落地步骤", "等待每日交易建议加载。", "warn"]]);
  const gates = Array.isArray(bridge.deployment_gates) ? bridge.deployment_gates : [];
  gatesTarget.innerHTML = gates.length ? gates.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_requirement || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["闸门", "等待 OOS、成本、模拟盘、人工复核等闸门信息。", "warn"]]);
}

function renderDailyDeploymentReadiness(readiness = {}) {
  const summaryTarget = byId("daily-deployment-readiness-summary");
  const sequenceTarget = byId("daily-deployment-readiness-sequence");
  const ticketTarget = byId("daily-deployment-readiness-tickets");
  const gateTarget = byId("daily-deployment-readiness-gates");
  const controlTarget = byId("daily-deployment-readiness-controls");
  if (!summaryTarget || !sequenceTarget || !ticketTarget || !gateTarget || !controlTarget) return;
  const summary = readiness.summary || {};
  const decision = summary.decision || "waiting_for_candidate_pool";
  const tone = decision.includes("blocked") ? "danger" : decision.includes("candidate") ? "warn" : "warn";
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = summary.next_target_id ? `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(summary.next_target_id)}">${escapeHtml(workflowButton ? "看证据" : summary.next_label || "看下一步")}</button>
  ` : "";
  summaryTarget.innerHTML = statusRows([
    ["今日结论", summary.plain_answer || zhConsoleText(decision), tone],
    ["下一步", summary.next_label || "等待今日交易准备包", tone],
    ["Top3 规则", summary.direct_buy_from_top3_allowed ? "异常：允许直买" : "前三只是候选，禁止直买", summary.direct_buy_from_top3_allowed ? "danger" : "ok"],
    ["模拟盘", summary.paper_rehearsal_allowed ? "可进入同参数模拟盘复核" : "暂时不能进入模拟盘复核", summary.paper_rehearsal_allowed ? "warn" : "danger"],
    ["人工材料", summary.manual_review_material_ready ? "已有可复核票据" : "还没有可复核票据", summary.manual_review_material_ready ? "warn" : "danger"],
    ["人工成交审计", `干净=${formatNumber(summary.manual_execution_clean_receipts || 0)} / 异常=${formatNumber(summary.manual_execution_blocked_receipts || 0)} / 缺回执=${formatNumber(summary.manual_execution_missing_review_receipts || 0)}`, summary.manual_execution_blocked_receipts || summary.manual_execution_missing_review_receipts ? "danger" : summary.manual_execution_clean_receipts >= 5 ? "ok" : "warn"],
    ["系统权限", summary.order_placement_allowed || summary.broker_connection_allowed ? "异常：权限越界" : "不连接券商、不读账户、不自动下单", summary.order_placement_allowed || summary.broker_connection_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("现在点这里")}</strong>
      <span>${escapeHtml(summary.next_label || "先生成今日前三建议")}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;

  const sequence = Array.isArray(readiness.daily_operating_sequence) ? readiness.daily_operating_sequence : [];
  sequenceTarget.innerHTML = sequence.length ? sequence.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["落地顺序", "等待生成今日交易准备包。", "warn"]]);

  const tickets = Array.isArray(readiness.manual_buy_sell_preview) ? readiness.manual_buy_sell_preview : [];
  ticketTarget.innerHTML = tickets.length ? tickets.map((item) => `
    <div class="list-row warn">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.asset_id || "--"} / ${zhConsoleText(item.operation || item.side || "review")}`)}</strong>
      <span>${escapeHtml(`参考价=${formatNumber(item.reference_price)} / 数量=${formatNumber(item.rounded_quantity)} / 金额=${formatNumber(item.rounded_value)} / 权重=${formatPercent(item.target_weight)}`)}</span>
      <span>${escapeHtml(item.plain_instruction || "只用于人工复核，不是订单。")}</span>
      <span class="beginner-task-actions">
        <button class="secondary-button" type="button" data-beginner-target="daily-manual-broker-handoff-ticket-table">${escapeHtml("看完整票据")}</button>
      </span>
    </div>
  `).join("") : statusRows([["买卖预览", "暂无可人工核对票据；没有票据就不要进入券商端操作。", "danger"]]);

  const gates = Array.isArray(readiness.readiness_gates) ? readiness.readiness_gates : [];
  gateTarget.innerHTML = gates.length ? gates.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_requirement || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["准备闸门", "等待准备包加载。", "warn"]]);

  const controls = Array.isArray(readiness.profitability_controls) ? readiness.profitability_controls : [];
  controlTarget.innerHTML = controls.length ? controls.map((item) => `
    <div class="list-row warn">
      <strong>${escapeHtml(item.label || item.control_id || "")}</strong>
      <span>${escapeHtml(item.plain_control || "")}</span>
      <span class="beginner-task-actions">
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["盈利控制", "等待长样本、样本外、成本、回撤、容量和未来函数控制项。", "warn"]]);
}

function liveProfitabilityRuntimeEvidence(readiness = {}) {
  const backendEvidence = readiness.evidence_snapshot || {};
  const backendCounts = backendEvidence.counts || {};
  const backendFlags = backendEvidence.flags || {};
  const paperRequest = dailyEvidencePaperRequest();
  const hasPaperRequest = Object.keys(paperRequest).length > 0;
  const paperReceipts = executionReceiptsForWorkflow("paper_simulation")
    .filter((item) => item?.status === "completed")
    .filter((item) => !hasPaperRequest || paperReceiptMatchesRequest(item, paperRequest).matches);
  const postCloseReceipts = executionReceiptsForWorkflow("post_close_journal")
    .filter((item) => item?.status === "completed")
    .filter((item) => item?.metrics?.manual_review_recorded !== false);
  const manualExecutionCleanReceipts = postCloseReceipts.filter((item) => manualExecutionAuditReceiptStatus(item) === "clean");
  const manualExecutionBlockedReceipts = postCloseReceipts.filter((item) => manualExecutionAuditReceiptStatus(item) === "blocked");
  const manualExecutionMissingReviewReceipts = postCloseReceipts.filter((item) => manualExecutionAuditReceiptStatus(item) === "missing_review");
  const paperReadyObservations = Math.min(paperReceipts.length, postCloseReceipts.length);
  const counts = {
    matched_paper_receipts: Math.max(Number(backendCounts.matched_paper_receipts || 0), paperReceipts.length),
    post_close_journal_receipts: Math.max(Number(backendCounts.post_close_journal_receipts || 0), postCloseReceipts.length),
    manual_execution_clean_receipts: Math.max(Number(backendCounts.manual_execution_clean_receipts || 0), manualExecutionCleanReceipts.length),
    manual_execution_blocked_receipts: Math.max(Number(backendCounts.manual_execution_blocked_receipts || 0), manualExecutionBlockedReceipts.length),
    manual_execution_missing_review_receipts: Math.max(Number(backendCounts.manual_execution_missing_review_receipts || 0), manualExecutionMissingReviewReceipts.length),
    paper_ready_observations: Math.max(Number(backendCounts.paper_ready_observations || 0), paperReadyObservations),
  };
  return {
    mode: hasPaperRequest && (paperReceipts.length || postCloseReceipts.length)
      ? "same_parameter_browser_execution_receipts"
      : paperReceipts.length || postCloseReceipts.length
        ? "browser_execution_receipts"
        : backendEvidence.mode || "empty",
    matched_paper_request: paperRequest,
    same_parameter_required: hasPaperRequest,
    counts,
    flags: {
      walk_forward_oos_passed: Boolean(backendFlags.walk_forward_oos_passed),
      lookahead_bias_audit_passed: Boolean(backendFlags.lookahead_bias_audit_passed),
      multiple_testing_control_passed: Boolean(backendFlags.multiple_testing_control_passed),
      transaction_cost_capacity_passed: Boolean(backendFlags.transaction_cost_capacity_passed),
    },
    missing_counts: {
      matched_paper_receipts: Math.max(0, 5 - counts.matched_paper_receipts),
      post_close_journal_receipts: Math.max(0, 5 - counts.post_close_journal_receipts),
      manual_execution_clean_receipts: Math.max(0, 5 - counts.manual_execution_clean_receipts),
      paper_ready_observations: Math.max(0, 20 - counts.paper_ready_observations),
    },
    paper_simulation_receipts: paperReceipts.length,
    post_close_journal_receipts: postCloseReceipts.length,
    manual_execution_clean_receipts: manualExecutionCleanReceipts.length,
    manual_execution_blocked_receipts: manualExecutionBlockedReceipts.length,
    manual_execution_missing_review_receipts: manualExecutionMissingReviewReceipts.length,
  };
}

function manualExecutionAuditReceiptStatus(receipt = {}) {
  const audit = receipt.manual_execution_audit || receipt.manual_review?.manual_execution_audit || {};
  const summary = audit.summary || {};
  if (!Object.keys(summary).length) return "not_recorded";
  const decision = String(summary.decision || "");
  const blockedCount = Number(summary.blocked_count || 0)
    + Number(summary.guardrail_breach_count || 0)
    + Number(summary.slippage_breach_count || 0)
    + Number(summary.quantity_mismatch_count || 0)
    + Number(summary.sensitive_field_count || 0);
  const missingCount = Number(summary.missing_review_count || 0);
  if (decision === "guardrail_breach_review_required" || blockedCount > 0) return "blocked";
  if (decision === "manual_execution_review_incomplete" || missingCount > 0) return "missing_review";
  if (decision === "manual_execution_evidence_ready") return "clean";
  return "not_recorded";
}

function dailyEvidencePaperRequest() {
  const handoff = state.dailyTradeAdvisory?.daily_signal_execution_bridge?.paper_simulation_handoff || {};
  const request = handoff.recommended_request || {};
  return request && typeof request === "object" ? request : {};
}

function dailyTradeAdvisoryEvidencePayload() {
  const readiness = state.dailyTradeAdvisory?.live_profitability_readiness || {};
  const evidence = liveProfitabilityRuntimeEvidence(readiness);
  const counts = evidence.counts || {};
  const flags = evidence.flags || {};
  const hasCounts = [
    counts.matched_paper_receipts,
    counts.post_close_journal_receipts,
    counts.paper_ready_observations,
  ].some((value) => Number(value || 0) > 0);
  const hasFlags = Object.values(flags).some(Boolean);
  if (!evidence.same_parameter_required && evidence.mode === "browser_execution_receipts") return null;
  if (!hasCounts && !hasFlags) return null;
  return {
    mode: evidence.mode || "same_parameter_browser_execution_receipts",
    source: "gui_runtime_receipts",
    same_parameter_required: Boolean(evidence.same_parameter_required),
    matched_paper_request: evidence.matched_paper_request || {},
    counts: {
      matched_paper_receipts: Number(counts.matched_paper_receipts || 0),
      post_close_journal_receipts: Number(counts.post_close_journal_receipts || 0),
      manual_execution_clean_receipts: Number(counts.manual_execution_clean_receipts || 0),
      manual_execution_blocked_receipts: Number(counts.manual_execution_blocked_receipts || 0),
      manual_execution_missing_review_receipts: Number(counts.manual_execution_missing_review_receipts || 0),
      paper_ready_observations: Number(counts.paper_ready_observations || 0),
    },
    flags: {
      walk_forward_oos_passed: Boolean(flags.walk_forward_oos_passed),
      lookahead_bias_audit_passed: Boolean(flags.lookahead_bias_audit_passed),
      multiple_testing_control_passed: Boolean(flags.multiple_testing_control_passed),
      transaction_cost_capacity_passed: Boolean(flags.transaction_cost_capacity_passed),
    },
    safety: "manual advisory evidence only; no broker connection, account read, order placement, or live trading",
  };
}

function mergeLiveProfitabilityRuntimeEvidence(readiness = {}, runtimeEvidence = {}) {
  const counts = runtimeEvidence.counts || {};
  const flags = runtimeEvidence.flags || {};
  const next = {
    ...readiness,
    summary: { ...(readiness.summary || {}) },
    hard_gates: Array.isArray(readiness.hard_gates) ? readiness.hard_gates.map((item) => ({ ...item })) : [],
    evidence_snapshot: runtimeEvidence,
  };
  const countByGate = {
    matched_paper_receipts: counts.matched_paper_receipts || 0,
    post_close_journals: counts.post_close_journal_receipts || 0,
    manual_execution_quality: counts.manual_execution_clean_receipts || 0,
    production_sample_size: counts.paper_ready_observations || 0,
  };
  const flagByGate = {
    walk_forward_oos: flags.walk_forward_oos_passed,
    lookahead_bias_audit: flags.lookahead_bias_audit_passed,
    multiple_testing_control: flags.multiple_testing_control_passed,
    transaction_cost_capacity: flags.transaction_cost_capacity_passed,
  };
  next.hard_gates = next.hard_gates.map((gate) => {
    const gateId = gate.gate_id || "";
    if (Object.prototype.hasOwnProperty.call(countByGate, gateId)) {
      const observed = Math.max(Number(gate.observed_count || 0), Number(countByGate[gateId] || 0));
      const minimum = Number(gate.minimum_required_observations || 0);
      if (
        gateId === "manual_execution_quality"
        && (
          Number(counts.manual_execution_blocked_receipts || 0) > 0
          || Number(counts.manual_execution_missing_review_receipts || 0) > 0
        )
      ) {
        return {
          ...gate,
          observed_count: observed,
          missing_count: Math.max(0, minimum - observed),
          status: "blocked",
        };
      }
      return {
        ...gate,
        observed_count: observed,
        missing_count: Math.max(0, minimum - observed),
        status: minimum > 0 && observed >= minimum ? "pass" : observed > 0 ? "partial" : gate.status,
      };
    }
    if (flagByGate[gateId]) {
      return { ...gate, status: "pass" };
    }
    return gate;
  });
  const passed = next.hard_gates.filter((gate) => gate.status === "pass").length;
  const total = next.hard_gates.length;
  const researchReady = Boolean(
    flags.walk_forward_oos_passed
    && flags.lookahead_bias_audit_passed
    && flags.multiple_testing_control_passed
    && flags.transaction_cost_capacity_passed
  );
  const matchedReady = Number(counts.matched_paper_receipts || 0) >= 5;
  const postCloseReady = Number(counts.post_close_journal_receipts || 0) >= 5;
  const manualExecutionReady = Number(counts.manual_execution_clean_receipts || 0) >= 5;
  const manualExecutionDirty = Number(counts.manual_execution_blocked_receipts || 0) > 0
    || Number(counts.manual_execution_missing_review_receipts || 0) > 0;
  const productionReady = Number(counts.paper_ready_observations || 0) >= 20;
  const smallCandidate = Boolean(
    next.summary.manual_review_material_ready
    && researchReady
    && matchedReady
    && postCloseReady
    && manualExecutionReady
    && !manualExecutionDirty
  );
  next.summary = {
    ...next.summary,
    evidence_mode: runtimeEvidence.mode || next.summary.evidence_mode || "empty",
    matched_paper_receipts: counts.matched_paper_receipts || 0,
    post_close_journal_receipts: counts.post_close_journal_receipts || 0,
    manual_execution_clean_receipts: counts.manual_execution_clean_receipts || 0,
    manual_execution_blocked_receipts: counts.manual_execution_blocked_receipts || 0,
    manual_execution_missing_review_receipts: counts.manual_execution_missing_review_receipts || 0,
    paper_ready_observations: counts.paper_ready_observations || 0,
    small_capital_observation_candidate: Boolean(next.summary.small_capital_observation_candidate || smallCandidate),
    production_manual_review_candidate: Boolean(next.summary.production_manual_review_candidate || (smallCandidate && productionReady)),
    passed_gate_count: total ? passed : next.summary.passed_gate_count || 0,
    total_gate_count: total || next.summary.total_gate_count || 0,
    readiness_score_pct: total ? Math.round((passed / total) * 100) : Number(next.summary.readiness_score_pct || 0),
    real_money_allowed: false,
    order_placement_allowed: false,
    broker_connection_allowed: false,
    account_read_allowed: false,
    auto_order_allowed: false,
  };
  return next;
}

function normalizeClosureDateKey(value) {
  const text = String(value ?? "").trim();
  if (!text) return "";
  const match = text.match(/\d{4}-\d{2}-\d{2}/);
  if (match) return match[0];
  const parsed = new Date(text);
  if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10);
  return "";
}

function receiptClosureDateKey(receipt = {}, fallback = "") {
  const request = receipt.request || {};
  return normalizeClosureDateKey(
    request.as_of_date
      || request.run_date
      || receipt.as_of_date
      || receipt.run_date
      || fallback
      || receipt.time
  );
}

function dailyClosureStreakEvidence(readiness = {}) {
  const trade = state.dailyTradeAdvisory || {};
  const summary = trade.summary || {};
  const runtimeEvidence = liveProfitabilityRuntimeEvidence(readiness);
  const paperRequest = dailyEvidencePaperRequest();
  const hasPaperRequest = Object.keys(paperRequest).length > 0;
  const runDate = normalizeClosureDateKey(
    trade.run_date
      || summary.run_date
      || valueOf("daily-trade-as-of")
      || valueOf("signal-as-of")
      || new Date().toISOString()
  );
  const rowsByDate = new Map();
  const ensureRow = (dateValue) => {
    const date = normalizeClosureDateKey(dateValue) || runDate || normalizeClosureDateKey(new Date().toISOString());
    if (!rowsByDate.has(date)) {
      rowsByDate.set(date, {
        date,
        top3_signal_ready: false,
        same_parameter_paper_ready: false,
        post_close_journal_ready: false,
        manual_execution_clean: false,
        manual_execution_blocked: false,
        manual_execution_missing_review: false,
        signal_detail: "waiting",
        paper_detail: "waiting",
        journal_detail: "waiting",
        manual_execution_detail: "waiting",
        missing_steps: [],
        completed_loop: false,
      });
    }
    return rowsByDate.get(date);
  };

  const currentRow = ensureRow(runDate);
  if (Number(summary.selected_factor_count || 0) > 0 && Number(summary.signal_count || 0) > 0) {
    currentRow.top3_signal_ready = true;
    currentRow.signal_detail = `current pack: factor=${formatNumber(summary.selected_factor_count)} / signal=${formatNumber(summary.signal_count)}`;
  }

  executionReceiptsForWorkflow("daily_trade_advisory")
    .filter((receipt) => receipt?.status === "completed")
    .forEach((receipt) => {
      const row = ensureRow(receiptClosureDateKey(receipt, runDate));
      const metrics = receipt.metrics || {};
      if (Number(metrics.selected_factor_count || 0) > 0 && Number(metrics.signal_count || 0) > 0) {
        row.top3_signal_ready = true;
        row.signal_detail = `receipt: factor=${formatNumber(metrics.selected_factor_count)} / signal=${formatNumber(metrics.signal_count)}`;
      }
    });

  executionReceiptsForWorkflow("paper_simulation")
    .filter((receipt) => receipt?.status === "completed")
    .forEach((receipt) => {
      const row = ensureRow(receiptClosureDateKey(receipt, receipt.time || runDate));
      const match = hasPaperRequest && row.date === runDate ? paperReceiptMatchesRequest(receipt, paperRequest) : { matches: true, mismatch_keys: [] };
      if (match.matches) {
        row.same_parameter_paper_ready = true;
        row.paper_detail = `matched: return=${formatPercent(receipt.metrics?.total_return)} / dd=${formatPercent(receipt.metrics?.max_drawdown)}`;
      } else {
        row.paper_detail = `parameter mismatch: ${match.mismatch_keys.join(", ") || "unknown"}`;
      }
    });

  executionReceiptsForWorkflow("post_close_journal")
    .filter((receipt) => receipt?.status === "completed")
    .filter((receipt) => receipt?.metrics?.manual_review_recorded !== false)
    .forEach((receipt) => {
      const row = ensureRow(receiptClosureDateKey(receipt, receipt.time || runDate));
      const status = manualExecutionAuditReceiptStatus(receipt);
      row.post_close_journal_ready = true;
      row.journal_detail = `review=${receipt.metrics?.manual_outcome || "recorded"} / tickets=${formatNumber(receipt.metrics?.target_count || 0)}`;
      if (status === "clean") {
        row.manual_execution_clean = true;
        row.manual_execution_detail = `clean: executed=${formatNumber(receipt.metrics?.executed_ticket_count || 0)} / missing=0`;
      } else if (status === "blocked") {
        row.manual_execution_blocked = true;
        row.manual_execution_detail = "blocked: guardrail or slippage breach";
      } else if (status === "missing_review") {
        row.manual_execution_missing_review = true;
        row.manual_execution_detail = "missing review: ticket-level evidence incomplete";
      } else {
        row.manual_execution_detail = "not recorded";
      }
    });

  const rows = Array.from(rowsByDate.values())
    .map((row) => {
      const missingSteps = [];
      if (!row.top3_signal_ready) missingSteps.push("top3_signal");
      if (!row.same_parameter_paper_ready) missingSteps.push("same_parameter_paper");
      if (!row.post_close_journal_ready) missingSteps.push("post_close_journal");
      if (!row.manual_execution_clean) missingSteps.push("manual_execution_clean");
      return {
        ...row,
        missing_steps: missingSteps,
        completed_loop: missingSteps.length === 0 && !row.manual_execution_blocked && !row.manual_execution_missing_review,
      };
    })
    .sort((left, right) => String(right.date).localeCompare(String(left.date)))
    .slice(0, 5);

  const closedLoopDays = rows.filter((row) => row.completed_loop).length;
  const blockedExecutionDays = rows.filter((row) => row.manual_execution_blocked || row.manual_execution_missing_review).length;
  const cleanExecutionDays = rows.filter((row) => row.manual_execution_clean).length;
  const missingTodaySteps = rows[0]?.missing_steps || [];
  const ready = rows.length >= 5 && closedLoopDays >= 5 && blockedExecutionDays === 0;
  const decision = ready
    ? "closure_streak_ready"
    : blockedExecutionDays > 0
      ? "closure_streak_blocked_by_execution"
      : "closure_streak_incomplete";

  return {
    stage: "phase_6_24_daily_closure_streak",
    summary: {
      decision,
      lookback_days: 5,
      observed_days: rows.length,
      closed_loop_days: closedLoopDays,
      clean_execution_days: cleanExecutionDays,
      blocked_execution_days: blockedExecutionDays,
      missing_today_steps: missingTodaySteps,
      streak_ready_for_small_capital_observation: ready,
      same_parameter_required: hasPaperRequest,
      evidence_mode: runtimeEvidence.mode || "empty",
      real_money_allowed: false,
      order_placement_allowed: false,
      broker_connection_allowed: false,
      auto_order_allowed: false,
    },
    rows,
    safety: "manual trading-system evidence only; no broker connection, account read, order placement, or live trading",
  };
}

function renderDailyClosureStreak(readiness = {}) {
  const summaryTarget = byId("daily-closure-streak-summary");
  const rowTarget = byId("daily-closure-streak-rows");
  if (!summaryTarget || !rowTarget) return;
  const evidence = dailyClosureStreakEvidence(readiness);
  const summary = evidence.summary || {};
  const decision = summary.decision || "closure_streak_incomplete";
  const tone = decision === "closure_streak_ready" ? "ok" : decision === "closure_streak_blocked_by_execution" ? "danger" : "warn";
  summaryTarget.innerHTML = statusRows([
    [
      "连续闭环结论",
      decision === "closure_streak_ready"
        ? "最近 5 个操作日都完成闭环，可进入人工小资金观察候选，但仍不能自动下单。"
        : decision === "closure_streak_blocked_by_execution"
          ? "发现人工执行审计异常，不能进入真实资金观察。"
          : "闭环样本不足，先继续生成信号、跑同参数模拟、写盘后复盘。",
      tone,
    ],
    ["闭环天数", `${formatNumber(summary.closed_loop_days || 0)} / ${formatNumber(summary.lookback_days || 5)}`, summary.closed_loop_days >= 5 ? "ok" : "warn"],
    ["人工执行审计", `干净=${formatNumber(summary.clean_execution_days || 0)} / 异常=${formatNumber(summary.blocked_execution_days || 0)}`, summary.blocked_execution_days ? "danger" : summary.clean_execution_days >= 5 ? "ok" : "warn"],
    ["今天缺什么", (summary.missing_today_steps || []).join(" / ") || "今天闭环已完整", summary.missing_today_steps?.length ? "warn" : "ok"],
    ["实盘权限", "这里只能形成手工观察证据：不连接券商、不读账户、不自动下单。", "danger"],
  ]);

  rowTarget.innerHTML = evidence.rows.length ? evidence.rows.map((row) => {
    const rowTone = row.completed_loop ? "ok" : row.manual_execution_blocked || row.manual_execution_missing_review ? "danger" : "warn";
    const stepText = [
      `前三=${row.top3_signal_ready ? "完成" : "缺失"}`,
      `模拟=${row.same_parameter_paper_ready ? "完成" : "缺失"}`,
      `复盘=${row.post_close_journal_ready ? "完成" : "缺失"}`,
      `执行审计=${row.manual_execution_clean ? "干净" : row.manual_execution_blocked ? "异常" : row.manual_execution_missing_review ? "缺回执" : "缺失"}`,
    ].join(" / ");
    const detailText = [
      row.signal_detail,
      row.paper_detail,
      row.journal_detail,
      row.manual_execution_detail,
    ].filter(Boolean).join(" | ");
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(row.date || "--")}</strong>
        <span>${escapeHtml(stepText)}</span>
        <span>${escapeHtml(detailText)}</span>
      </div>
    `;
  }).join("") : statusRows([[
    "暂无闭环样本",
    "先运行今日前三建议，再跑同参数模拟盘，收盘后写复盘和人工执行审计。",
    "warn",
  ]]);
}

function renderLiveProfitabilityReadiness(readiness = {}) {
  const summaryTarget = byId("daily-live-profitability-summary");
  const ladderTarget = byId("daily-live-profitability-ladder");
  const gateTarget = byId("daily-live-profitability-gates");
  const actionTarget = byId("daily-live-profitability-actions");
  const forbiddenTarget = byId("daily-live-profitability-forbidden");
  const controlTarget = byId("daily-live-profitability-controls");
  if (!summaryTarget || !ladderTarget || !gateTarget || !actionTarget || !forbiddenTarget || !controlTarget) return;
  readiness = mergeLiveProfitabilityRuntimeEvidence(readiness, liveProfitabilityRuntimeEvidence(readiness));
  const summary = readiness.summary || {};
  const decision = summary.decision || "waiting_for_qualified_cn_etf_candidates";
  const score = Number(summary.readiness_score_pct || 0);
  const tone = summary.real_money_allowed ? "ok" : decision.includes("blocked") ? "danger" : "warn";
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = summary.next_target_id ? `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(summary.next_target_id)}">${escapeHtml(workflowButton ? "看证据" : summary.next_label || "看下一步")}</button>
  ` : "";
  summaryTarget.innerHTML = statusRows([
    ["实盘盈利结论", summary.plain_answer || zhConsoleText(decision), tone],
    ["就绪评分", `${formatNumber(score)} / 100；通过 ${formatNumber(summary.passed_gate_count || 0)} / ${formatNumber(summary.total_gate_count || 0)} 个硬闸门`, score >= 80 ? "ok" : score >= 50 ? "warn" : "danger"],
    ["能否宣称稳定盈利", summary.profitability_claim_allowed ? "可以" : "不可以", summary.profitability_claim_allowed ? "ok" : "danger"],
    ["真实资金", summary.real_money_allowed ? "允许" : "不允许", summary.real_money_allowed ? "ok" : "danger"],
    ["今天允许", summary.paper_rehearsal_allowed ? "同参数模拟盘 / 人工复核材料准备" : "只观察或先修阻断", summary.paper_rehearsal_allowed ? "warn" : "danger"],
    ["本机证据", `模拟盘=${formatNumber(summary.matched_paper_receipts || 0)} / 复盘=${formatNumber(summary.post_close_journal_receipts || 0)} / 观察=${formatNumber(summary.paper_ready_observations || 0)}`, summary.production_manual_review_candidate ? "ok" : summary.matched_paper_receipts || summary.post_close_journal_receipts ? "warn" : "muted"],
    ["人工成交审计", `干净=${formatNumber(summary.manual_execution_clean_receipts || 0)} / 异常=${formatNumber(summary.manual_execution_blocked_receipts || 0)} / 缺回执=${formatNumber(summary.manual_execution_missing_review_receipts || 0)}`, summary.manual_execution_blocked_receipts || summary.manual_execution_missing_review_receipts ? "danger" : summary.manual_execution_clean_receipts >= 5 ? "ok" : "warn"],
    ["系统权限", summary.order_placement_allowed || summary.broker_connection_allowed ? "异常：权限越界" : "不连接券商、不读账户、不自动下单", summary.order_placement_allowed || summary.broker_connection_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("现在最该做")}</strong>
      <span>${escapeHtml(summary.next_label || "先补齐缺失证据")}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;

  const ladder = Array.isArray(readiness.beginner_ladder) ? readiness.beginner_ladder : [];
  ladderTarget.innerHTML = ladder.length ? ladder.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_state || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["实盘路线", "等待每日交易建议加载后显示从信号到模拟盘、人工观察、生产化复核的路线。", "warn"]]);

  const gates = Array.isArray(readiness.hard_gates) ? readiness.hard_gates : [];
  gateTarget.innerHTML = gates.length ? gates.map((item) => {
    const rowTone = item.status === "pass" ? "ok" : item.status === "blocked" ? "danger" : "warn";
    const observationText = item.minimum_required_observations ? ` / 样本=${formatNumber(item.observed_count || 0)}/${formatNumber(item.minimum_required_observations)}` : "";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
        <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")}${observationText} / ${item.plain_requirement || ""}`)}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
          ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["硬闸门", "等待加载长样本、OOS、成本、容量、模拟盘、复盘和安全边界检查。", "warn"]]);

  const actions = Array.isArray(readiness.today_allowed_actions) ? readiness.today_allowed_actions : [];
  actionTarget.innerHTML = actions.length ? actions.map((item) => `
    <div class="list-row ${escapeHtml(item.status === "allowed" || item.status === "next" ? "warn" : "muted")}">
      <strong>${escapeHtml(item.label || item.action_id || "")}</strong>
      <span>${escapeHtml(item.plain_action || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["今天允许动作", "还没有可执行动作；先生成或刷新今日交易建议。", "warn"]]);

  const forbidden = Array.isArray(readiness.forbidden_actions) ? readiness.forbidden_actions : [];
  forbiddenTarget.innerHTML = forbidden.length ? forbidden.map((item) => `
    <div class="list-row danger">
      <strong>${escapeHtml(item.label || item.action_id || "")}</strong>
      <span>${escapeHtml(item.plain_action || "")}</span>
      <span class="beginner-task-actions">
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("看原因")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["禁止动作", "禁止直接买前三、跳过模拟盘、自动连券商或只因年化高就加仓。", "danger"]]);

  const controls = Array.isArray(readiness.stability_controls) ? readiness.stability_controls : [];
  controlTarget.innerHTML = controls.length ? controls.map((item) => `
    <div class="list-row warn">
      <strong>${escapeHtml(item.label || item.control_id || "")}</strong>
      <span>${escapeHtml(item.plain_control || "")}</span>
      <span class="beginner-task-actions">
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["稳定性控制", "等待加载回撤熔断、参数敏感性、滑点复盘、因子衰减和退役闭环。", "warn"]]);
}

function renderDailyRealMoneyTransitionGate(gate = {}) {
  const summaryTarget = byId("daily-real-money-transition-summary");
  const preflightTarget = byId("daily-real-money-transition-preflight");
  const scriptTarget = byId("daily-real-money-transition-script");
  const ticketsTarget = byId("daily-real-money-transition-tickets");
  if (!summaryTarget || !preflightTarget || !scriptTarget || !ticketsTarget) return;
  const summary = gate.summary || {};
  const decision = summary.decision || "generate_same_day_signal_first";
  const tone = decision.includes("blocked") || decision.includes("rotate") ? "danger" : decision.includes("candidate") ? "warn" : "warn";
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = summary.next_target_id ? `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(summary.next_target_id)}">${escapeHtml(workflowButton ? "看证据" : summary.next_label || "看下一步")}</button>
  ` : "";
  summaryTarget.innerHTML = statusRows([
    ["今日总结论", summary.plain_answer || zhConsoleText(decision), tone],
    ["资金阶段", `${summary.capital_mode || "--"} / 评分=${formatNumber(summary.readiness_score_pct || 0)}/100`, summary.production_manual_review_candidate ? "ok" : "warn"],
    ["今日证据", `信号=${formatNumber(summary.signal_count || 0)} / 目标=${formatNumber(summary.target_count || 0)} / 票据=${formatNumber(summary.manual_ticket_count || 0)}`, summary.manual_ticket_count ? "warn" : "danger"],
    ["观察样本", `模拟=${formatNumber(summary.matched_paper_receipts || 0)} / 复盘=${formatNumber(summary.post_close_journal_receipts || 0)} / paper-ready=${formatNumber(summary.paper_ready_observations || 0)}`, summary.production_manual_review_candidate ? "ok" : "warn"],
    ["人工成交审计", `干净=${formatNumber(summary.manual_execution_clean_receipts || 0)} / 异常=${formatNumber(summary.manual_execution_blocked_receipts || 0)} / 缺回执=${formatNumber(summary.manual_execution_missing_review_receipts || 0)}`, summary.manual_execution_blocked_receipts || summary.manual_execution_missing_review_receipts ? "danger" : summary.manual_execution_clean_receipts >= 5 ? "ok" : "warn"],
    ["真实资金权限", summary.real_money_allowed || summary.order_placement_allowed ? "异常：权限越界" : "不连接券商、不读账户、不自动下单", summary.real_money_allowed || summary.order_placement_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("现在先做")}</strong>
      <span>${escapeHtml(summary.next_label || "先生成今日信号或补齐证据")}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;

  const preflightRows = Array.isArray(gate.preflight_rows) ? gate.preflight_rows : [];
  preflightTarget.innerHTML = preflightRows.length ? preflightRows.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_requirement || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["前置闸门", "等待每日交易建议加载后显示范围、健康、红灯、模拟回执、复盘和票据风险。", "warn"]]);

  const scriptRows = Array.isArray(gate.operator_script) ? gate.operator_script : [];
  scriptTarget.innerHTML = scriptRows.length ? scriptRows.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["操作脚本", "等待系统生成今日总闸门后显示从 Top3 到模拟盘、票据、人工决策和收盘复盘的步骤。", "warn"]]);

  const tickets = Array.isArray(gate.manual_execution_preview) ? gate.manual_execution_preview : [];
  ticketsTarget.innerHTML = tickets.length ? tickets.map((item) => {
    const risk = item.risk_budget || {};
    const blocked = Array.isArray(item.manual_skip_conditions) && item.manual_skip_conditions.some((condition) => condition.status === "blocked");
    return `
      <div class="list-row ${escapeHtml(blocked ? "danger" : "warn")}">
        <strong>${escapeHtml(`${item.step_number || "--"}. ${item.asset_id || "--"} ${zhConsoleText(item.side || "")}`)}</strong>
        <span>${escapeHtml(`数量=${formatNumber(item.rounded_quantity || 0)} / 金额=${formatNumber(item.rounded_value)} / 单ETF上限=${formatPercent(risk.max_single_etf_weight)} / 票据风险=${formatNumber(risk.ticket_adverse_move_loss)}`)}</span>
        <span>${escapeHtml(blocked ? "触发跳过条件，不能推进。" : "仅供人工核对，不是订单。")}</span>
      </div>
    `;
  }).join("") : statusRows([["人工票据", "暂无可人工核对票据；没有票据就不要进入券商端操作。", "danger"]]);
}

function renderDailyFactorHealthMonitor(monitor = {}) {
  const summaryTarget = byId("daily-factor-health-summary");
  const rowTarget = byId("daily-factor-health-rows");
  const actionTarget = byId("daily-factor-health-actions");
  const ruleTarget = byId("daily-factor-health-rules");
  if (!summaryTarget || !rowTarget || !actionTarget) return;
  const summary = monitor.summary || {};
  const packSummary = state.dailyTradeAdvisory?.summary || {};
  const decision = summary.decision || packSummary.factor_health_status || "waiting_for_top3_candidates";
  const tone = dailyFactorHealthTone(decision);
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = summary.next_target_id ? `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(summary.next_target_id)}">${escapeHtml(workflowButton ? "查看证据" : summary.next_label || "查看下一步")}</button>
  ` : "";
  summaryTarget.innerHTML = statusRows([
    ["因子健康结论", summary.plain_answer || zhConsoleText(decision), tone],
    ["Top3 健康分布", `健康=${formatNumber(summary.healthy_count || 0)} / 观察=${formatNumber(summary.watch_count || 0)} / 退役候选=${formatNumber(summary.retire_candidate_count || 0)}`, summary.retire_candidate_count ? "danger" : summary.watch_count ? "warn" : summary.healthy_count ? "ok" : "warn"],
    ["研究证据", summary.research_evidence_ready ? "OOS、未来函数、多重检验、成本容量证据已标记通过" : "还缺 OOS、未来函数、多重检验或成本容量证据", summary.research_evidence_ready ? "ok" : "warn"],
    ["排行榜直买", summary.top3_auto_buy_allowed || summary.direct_buy_from_top3_allowed ? "异常：允许直买" : "禁止：Top3 只是候选入口", summary.top3_auto_buy_allowed || summary.direct_buy_from_top3_allowed ? "danger" : "ok"],
    ["系统权限", summary.order_placement_allowed || summary.broker_connection_allowed ? "异常：权限越界" : "不连接券商、不读账户、不自动下单", summary.order_placement_allowed || summary.broker_connection_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("现在先做")}</strong>
      <span>${escapeHtml(summary.next_label || "先生成今日前三建议")}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;

  const rows = Array.isArray(monitor.factor_rows) ? monitor.factor_rows : [];
  rowTarget.innerHTML = rows.length ? rows.map((item, index) => {
    const metrics = item.metrics || {};
    const rowTone = dailyFactorHealthTone(item.health_status || item.decision || "");
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(`${item.rank || index + 1}. ${item.factor_name || "--"} / ${zhConsoleText(item.health_status || "watch")}`)}</strong>
        <span>${escapeHtml(`Sharpe=${formatDecimal(metrics.sharpe)} / 年化=${formatPercent(metrics.annualized_return)} / 回撤=${formatPercent(metrics.max_drawdown)} / 胜率=${formatPercent(metrics.win_rate)} / RankIC=${formatDecimal(metrics.rank_ic)} / 样本=${formatNumber(metrics.trade_count || 0)}`)}</span>
        <span>${escapeHtml(item.plain_diagnosis || item.required_action || "只作为候选，不是买入指令。")}</span>
        <span>${escapeHtml(item.required_action || "先复核，再模拟盘观察。")}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
          ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["等待因子健康检查", "先生成今日前三 CN_ETF 建议，系统再判断哪些因子可观察、哪些要退役。", "warn"]]);

  const actions = Array.isArray(monitor.recommended_actions) ? monitor.recommended_actions : [];
  actionTarget.innerHTML = actions.length ? actions.map((item) => `
    <div class="list-row ${escapeHtml(dailyFactorHealthTone(item.status || ""))}">
      <strong>${escapeHtml(item.label || item.action_id || "")}</strong>
      <span>${escapeHtml(item.plain_action || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["下一步", "等待因子健康结论加载。", "warn"]]);

  if (ruleTarget) {
    const rules = Array.isArray(monitor.health_rules) ? monitor.health_rules : [];
    ruleTarget.innerHTML = rules.length ? rules.map((item) => `
      <div class="list-row ${escapeHtml(item.rule_id === "retire_candidate" ? "danger" : "warn")}">
        <strong>${escapeHtml(zhConsoleText(item.rule_id || "health_rule"))}</strong>
        <span>${escapeHtml(item.plain_rule || "")}</span>
      </div>
    `).join("") : statusRows([["健康规则", "退役候选先处理；健康也只代表可以模拟盘观察，不代表可以买。", "warn"]]);
  }
}

function dailyFactorHealthTone(status = "") {
  const text = String(status || "").toLowerCase();
  if (text.includes("retire") || text.includes("exclude") || text.includes("forbidden") || text.includes("danger")) return "danger";
  if (text.includes("healthy") || text.includes("clear") || text.includes("allowed")) return "ok";
  return "warn";
}

function renderDailyRealWorldHandoffGate(gate = {}) {
  const summaryTarget = byId("daily-real-world-handoff-summary");
  const ladderTarget = byId("daily-real-world-handoff-ladder");
  const runbookTarget = byId("daily-real-world-handoff-runbook");
  const ticketsTarget = byId("daily-real-world-handoff-tickets");
  const blockersTarget = byId("daily-real-world-handoff-blockers");
  if (!summaryTarget || !ladderTarget || !runbookTarget || !ticketsTarget || !blockersTarget) return;
  const summary = gate.summary || {};
  const contract = gate.daily_top3_signal_contract || {};
  const risk = gate.risk_budget || {};
  const ladder = Array.isArray(gate.capital_deployment_ladder) ? gate.capital_deployment_ladder : [];
  const runbook = Array.isArray(gate.manual_operation_runbook) ? gate.manual_operation_runbook : [];
  const tickets = Array.isArray(gate.manual_ticket_preview) ? gate.manual_ticket_preview : [];
  const blockers = Array.isArray(gate.go_live_blockers) ? gate.go_live_blockers : [];
  const boundaries = Array.isArray(gate.safety_boundaries) ? gate.safety_boundaries : [];
  const decision = summary.decision || "waiting_for_cn_etf_candidate_pool";
  const tone = dailyRealWorldHandoffTone(decision);
  const workflowButton = summary.next_workflow_id ? `
    <button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(summary.next_workflow_id)}">${escapeHtml(summary.next_label || "运行下一步")}</button>
  ` : "";
  const targetButton = summary.next_target_id ? `
    <button class="${escapeHtml(workflowButton ? "secondary-button" : "primary-button")}" type="button" data-beginner-target="${escapeRawHtml(summary.next_target_id)}">${escapeHtml(workflowButton ? "看证据" : summary.next_label || "看下一步")}</button>
  ` : "";
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  summaryTarget.innerHTML = statusRows([
    ["今日结论", summary.plain_answer || zhConsoleText(decision), tone],
    ["下一步", summary.next_label || "等待今日交易系统加载", tone],
    ["前三因子规则", `${contract.selection_scope || "CN_ETF"} / Top${formatNumber(contract.candidate_limit || summary.daily_top_factor_limit || 3)} / 直买=${summary.direct_buy_from_top3_allowed ? "允许" : "禁止"}`, summary.direct_buy_from_top3_allowed ? "danger" : "ok"],
    ["今日证据", `信号=${formatNumber(summary.today_signal_count || 0)} / 目标=${formatNumber(summary.target_count || 0)} / 票据=${formatNumber(summary.manual_ticket_count || 0)} / 阻断=${formatNumber(summary.blocker_count || 0)}`, summary.blocker_count ? "danger" : "warn"],
    ["风险预算", `${risk.risk_profile_label || risk.risk_profile_id || "--"} / 总仓位=${formatPercent(risk.max_gross_exposure)} / 单ETF=${formatPercent(risk.max_single_etf_weight)} / 回撤预算=${formatPercent(risk.max_acceptable_drawdown)}`, "warn"],
    ["本机模拟盘回执", paperReceipt ? `${paperReceipt.time || "--"} / 收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}` : "还没有同参数模拟盘回执", paperReceipt ? "ok" : "warn"],
    ["实盘权限", summary.order_placement_allowed || summary.broker_connection_allowed ? "异常：权限越界" : "不连接券商、不读账户、不自动下单", summary.order_placement_allowed || summary.broker_connection_allowed ? "danger" : "ok"],
  ]) + `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("现在应该点什么")}</strong>
      <span>${escapeHtml(summary.next_label || "先生成今日前三建议")}</span>
      <span class="beginner-task-actions">${workflowButton}${targetButton}</span>
    </div>
  `;
  renderDailyRealWorldCapitalLadder(ladderTarget, ladder);
  runbookTarget.innerHTML = runbook.length ? runbook.map((item) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["人工观察步骤", "等待今日前三建议加载。", "warn"]]);
  ticketsTarget.innerHTML = tickets.length ? tickets.map((item) => `
    <div class="list-row warn">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.asset_id || "--"} ${zhConsoleText(item.side || "")}`)}</strong>
      <span>${escapeHtml(`数量=${formatNumber(item.rounded_quantity || 0)} / 金额=${formatNumber(item.rounded_value)} / 参考价=${formatNumber(item.reference_price)}`)}</span>
      <span>${escapeHtml(item.plain_instruction || "仅供人工核对，不是订单。")}</span>
      <span class="beginner-task-actions">
        <button class="secondary-button" type="button" data-beginner-target="daily-manual-broker-handoff-ticket-table">${escapeHtml("看票据")}</button>
      </span>
    </div>
  `).join("") : statusRows([
    ["人工票据", "暂无可人工核对票据；没有票据就不要进入券商端操作。", "danger"],
  ]);
  blockersTarget.innerHTML = blockers.concat(boundaries).map((item) => {
    const id = item.gate_id || item.boundary_id || "";
    const label = item.label || id || "安全项";
    const status = item.status || (item.enforced ? "enforced" : "required");
    const detail = item.plain_requirement || item.plain_boundary || "";
    const rowTone = status === "pass" || status === "enforced" ? "ok" : status === "blocked" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(label)}</strong>
        <span>${escapeHtml(`${zhConsoleText(status)} / ${detail}`)}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
          ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") || statusRows([["安全闸门", "等待实盘前人工观察总闸门加载。", "warn"]]);
}

function renderDailyRealWorldCapitalLadder(target, ladder = []) {
  target.innerHTML = ladder.length ? ladder.map((item) => {
    const status = item.status || "waiting";
    const tone = status.includes("done") ? "ok" : status.includes("locked") || status.includes("blocked") ? "danger" : "warn";
    const thresholds = [
      item.minimum_matched_paper_receipts != null ? `模拟盘回执≥${formatNumber(item.minimum_matched_paper_receipts)}` : "",
      item.minimum_post_close_journals != null ? `复盘回执≥${formatNumber(item.minimum_post_close_journals)}` : "",
      item.minimum_paper_ready_observations != null ? `纸面观察≥${formatNumber(item.minimum_paper_ready_observations)}` : "",
    ].filter(Boolean).join(" / ");
    return `
      <div class="list-row ${escapeHtml(tone)}">
        <strong>${escapeHtml(`${item.stage_number || "--"}. ${item.label || item.stage_id || ""}`)}</strong>
        <span>${escapeHtml(`${zhConsoleText(status)} / ${item.capital_mode || ""}`)}</span>
        <span>${escapeHtml([item.plain_requirement || "", thresholds].filter(Boolean).join(" / "))}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
          ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("查看")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["资金阶段", "等待今日实盘前人工观察总闸门加载。", "warn"]]);
}

function dailyRealWorldHandoffTone(decision = "") {
  if (decision.includes("blocked")) return "danger";
  if (decision.includes("candidate")) return "warn";
  return "warn";
}

function dailyPaperReceiptStatus(handoff = {}) {
  const request = handoff.recommended_request || {};
  const receipt = latestExecutionReceipt("paper_simulation");
  if (!Object.keys(request).length) {
    return {
      status: "waiting_for_handoff",
      tone: "warn",
      label: "等待模拟盘交接",
      detail: "先生成今日前三交易建议，再填入同参数模拟盘请求。",
      receipt: null,
      matches: false,
      mismatch_keys: [],
    };
  }
  if (!receipt) {
    return {
      status: "missing",
      tone: "warn",
      label: "还没有同参数模拟盘回执",
      detail: "先点填入模拟盘参数，再运行模拟盘复核。",
      receipt: null,
      matches: false,
      mismatch_keys: [],
    };
  }
  const match = paperReceiptMatchesRequest(receipt, request);
  const metrics = receipt.metrics || {};
  return {
    status: match.matches ? "matched" : "mismatch",
    tone: match.matches ? "ok" : "warn",
    label: match.matches ? "已看到同参数模拟盘回执" : "已有模拟盘回执，但参数需要复核",
    detail: match.matches
      ? `收益=${formatPercent(metrics.total_return)} / 回撤=${formatPercent(metrics.max_drawdown)}`
      : `不一致字段=${match.mismatch_keys.join(", ") || "未知"}；建议重新填参后再跑。`,
    receipt,
    matches: match.matches,
    mismatch_keys: match.mismatch_keys,
  };
}

function renderDailyPaperReceiptStatusRows(status = {}) {
  const receipt = status.receipt || null;
  const metrics = receipt?.metrics || {};
  const request = receipt?.request || {};
  const rows = [
    ["模拟盘回执", status.label || "等待模拟盘回执", status.tone || "warn"],
    [
      "回执参数",
      receipt
        ? `${request.market || "--"} / ${request.factor_name || request.factor || "--"} / TopN=${formatNumber(request.top_n)}`
        : "尚未运行同参数模拟盘",
      status.matches ? "ok" : "warn",
    ],
    [
      "模拟盘指标",
      receipt
        ? `权益=${formatNumber(metrics.ending_equity)} / 收益=${formatPercent(metrics.total_return)} / 回撤=${formatPercent(metrics.max_drawdown)} / 成交=${formatNumber(metrics.fill_count)} / 保护=${formatNumber(metrics.guard_event_count)}`
        : "先生成本地模拟成交、权益和风控事件，再进入人工复核。",
      status.tone || "warn",
    ],
    ["实盘边界", "这里只给人工复核证据；不连接券商、不读账户、不自动下单。", "danger"],
  ];
  return statusRows(rows) + renderDailyPaperManualReviewRows(status);
}

function renderDailyPaperManualReviewRows(status = {}) {
  const row = dailyPaperManualReviewRow(status);
  return `
    <div class="list-row ${escapeHtml(row.tone)}">
      <strong>${escapeHtml(row.label)}</strong>
      <span>${escapeHtml(row.detail)}</span>
      <span class="beginner-task-actions">
        ${row.target_id ? `<button class="primary-button" type="button" data-beginner-target="${escapeRawHtml(row.target_id)}">${escapeHtml(row.button_label)}</button>` : ""}
      </span>
    </div>
  `;
}

function dailyPaperManualReviewRow(status = {}) {
  if (status.matches) {
    return {
      tone: "ok",
      label: "下一步：查看人工复核票据",
      detail: "同参数模拟盘回执已匹配；继续核对 ETF、数量、参考价、现金和风险，系统仍不会下单。",
      button_label: "查看人工复核票据",
      target_id: "daily-manual-broker-handoff-ticket-table",
    };
  }
  return {
    tone: "warn",
    label: "下一步：先补同参数模拟盘",
    detail: "模拟盘回执缺失或参数不一致时，不要进入人工票据复核。",
    button_label: "",
    target_id: "",
  };
}

function paperReceiptMatchesRequest(receipt = {}, request = {}) {
  const receiptRequest = receipt.request || {};
  const comparisons = [
    ["market", normalizeReceiptText(receiptRequest.market), normalizeReceiptText(request.market)],
    ["factor", normalizeReceiptText(receiptRequest.factor_name || receiptRequest.factor), normalizeReceiptText(request.factor || request.factor_name)],
    ["factor_windows", normalizeReceiptText(receiptRequest.factor_windows), normalizeReceiptText(request.factor_windows)],
    ["top_n", normalizeReceiptNumber(receiptRequest.top_n), normalizeReceiptNumber(request.top_n)],
    ["rebalance_interval", normalizeReceiptNumber(receiptRequest.rebalance_interval), normalizeReceiptNumber(request.rebalance_interval)],
    ["initial_cash", normalizeReceiptNumber(receiptRequest.initial_cash), normalizeReceiptNumber(request.initial_cash)],
    ["commission_bps", normalizeReceiptNumber(receiptRequest.commission_bps), normalizeReceiptNumber(request.commission_bps)],
    ["slippage_bps", normalizeReceiptNumber(receiptRequest.slippage_bps), normalizeReceiptNumber(request.slippage_bps)],
    ["max_asset_weight", normalizeReceiptNumber(receiptRequest.max_asset_weight), normalizeReceiptNumber(request.max_asset_weight)],
    ["max_market_weight", normalizeReceiptNumber(receiptRequest.max_market_weight), normalizeReceiptNumber(request.max_market_weight)],
    ["max_gross_exposure", normalizeReceiptNumber(receiptRequest.max_gross_exposure), normalizeReceiptNumber(request.max_gross_exposure)],
    ["min_cash_weight", normalizeReceiptNumber(receiptRequest.min_cash_weight), normalizeReceiptNumber(request.min_cash_weight)],
  ].filter((item) => item[2] !== "");
  const mismatchKeys = comparisons
    .filter((item) => item[1] === "" || item[1] !== item[2])
    .map((item) => item[0]);
  return {
    matches: comparisons.length > 0 && mismatchKeys.length === 0,
    compared_keys: comparisons.map((item) => item[0]),
    mismatch_keys: mismatchKeys,
  };
}

function normalizeReceiptText(value) {
  return String(value ?? "").trim().replace(/\s+/g, "").toUpperCase();
}

function normalizeReceiptNumber(value) {
  if (value === undefined || value === null || value === "") return "";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(6) : normalizeReceiptText(value);
}

function renderDailyTradingSystemBlueprint(blueprint = {}) {
  const summaryTarget = byId("daily-trading-system-blueprint-summary");
  const flowTarget = byId("daily-trading-system-blueprint-flow");
  const evidenceTarget = byId("daily-trading-system-blueprint-evidence");
  const actionTarget = byId("daily-trading-system-blueprint-actions");
  if (!summaryTarget || !flowTarget || !evidenceTarget || !actionTarget) return;
  const summary = blueprint.summary || {};
  const policy = blueprint.candidate_pool_policy || {};
  const layers = Array.isArray(blueprint.system_layers) ? blueprint.system_layers : [];
  const evidence = Array.isArray(blueprint.evidence_chain) ? blueprint.evidence_chain : [];
  const actions = Array.isArray(blueprint.operator_buy_process) ? blueprint.operator_buy_process : [];
  const status = summary.status || "waiting_for_today_signal";
  const statusTone = status.includes("blocked") ? "danger" : "warn";
  summaryTarget.innerHTML = statusRows([
    ["系统状态", zhConsoleText(status), statusTone],
    ["今日前三", summary.daily_top3_signal_supported ? "支持，但只能进证据链" : "不支持", summary.daily_top3_signal_supported ? "warn" : "danger"],
    ["候选池", `${policy.selection_scope || "CN_ETF"} / Top${formatNumber(policy.top_factor_limit || 3)} / 排行榜直买=${policy.direct_buy_from_leaderboard_allowed ? "允许" : "禁止"}`, policy.direct_buy_from_leaderboard_allowed ? "danger" : "ok"],
    ["今日证据", `信号=${formatNumber(summary.today_signal_count || 0)} / 目标=${formatNumber(summary.target_count || 0)} / 票据=${formatNumber(summary.manual_ticket_count || 0)} / 阻断=${formatNumber(summary.blocker_count || 0)}`, summary.blocker_count ? "danger" : "warn"],
    ["实盘自动化", summary.direct_live_trading_supported ? "异常开启" : "不支持", summary.direct_live_trading_supported ? "danger" : "ok"],
    ["下一句", summary.operator_summary || "按每日交易系统证据链逐步推进。", statusTone],
  ]);
  flowTarget.innerHTML = layers.length ? layers.map((item, index) => `
    <div class="list-row warn">
      <strong>${escapeHtml(`${index + 1}. ${item.label || item.layer_id || ""}`)}</strong>
      <span>${escapeHtml(item.responsibility || "")}</span>
      <span>${escapeHtml(item.order_placement_allowed ? "异常：允许下单" : "下单权限=禁止")}</span>
    </div>
  `).join("") : statusRows([["系统分层", "等待今日交易系统蓝图加载。", "warn"]]);
  evidenceTarget.innerHTML = evidence.length ? evidence.map((item) => {
    const rowTone = item.status === "ready" ? "ok" : item.status === "blocked" || item.status === "locked" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(item.label || item.evidence_id || "")}</strong>
        <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.evidence || ""}`)}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行这一步")}</button>` : ""}
          ${item.gui_target ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("看证据")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["证据链", "等待今日前三信号、模拟盘和人工票据证据。", "warn"]]);
  actionTarget.innerHTML = actions.length ? actions.map((item) => {
    const rowTone = dailyTradeSystemStageTone(item.status || "");
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(`${item.step_number || "--"}. ${item.title || item.step_id || ""}`)}</strong>
        <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
        <span>${escapeHtml(item.order_placement_allowed ? "异常：允许下单" : "系统下单=禁止")}</span>
        <span class="beginner-task-actions">
          ${item.workflow_id ? `<button class="primary-button" type="button" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行")}</button>` : ""}
          ${item.gui_target ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("查看")}</button>` : ""}
        </span>
      </div>
    `;
  }).join("") : statusRows([["操作步骤", "先生成今日前三建议，再看是否进入模拟盘和人工复核。", "warn"]]);
}

function renderDailyTradeSystemState(system = {}, runtime = {}, target = byId("daily-trade-system-state")) {
  if (!target) return;
  const candidate_pool_policy = system.candidate_pool_policy || {};
  const permissions = system.permissions || {};
  const progress = system.progress || {};
  const nextGate = system.next_gate || {};
  const mode = system.mode || "waiting_for_daily_signal";
  const stages = Array.isArray(system.stages) ? system.stages : [];
  const overview = statusRows([
    ["交易系统阶段", system.mode_label || zhConsoleText(mode), dailyTradeSystemModeTone(mode)],
    ["候选池规则", `${candidate_pool_policy.selection_scope || "CN_ETF"} / Top${formatNumber(candidate_pool_policy.top_factor_limit || 3)} / 榜单直买=${candidate_pool_policy.direct_buy_from_leaderboard_allowed ? "允许" : "禁止"}`, candidate_pool_policy.direct_buy_from_leaderboard_allowed ? "danger" : "ok"],
    ["流程进度", `已完成=${formatNumber(progress.completed_stage_count || 0)} / 待补=${formatNumber(progress.required_stage_count || 0)} / 阻断=${formatNumber(progress.blocked_stage_count || 0)} / 锁定=${formatNumber(progress.locked_stage_count || 0)}`, progress.blocked_stage_count ? "danger" : progress.required_stage_count ? "warn" : "ok"],
    ["下一道门", `${nextGate.label || "--"} / ${zhConsoleText(nextGate.status || "--")}`, dailyTradeSystemStageTone(nextGate.status || "")],
    ["系统权限", permissions.order_placement_allowed ? "异常：允许下单" : "只允许研究、模拟盘、人工复核", permissions.order_placement_allowed ? "danger" : "ok"],
  ]);
  const stageRows = stages.length ? stages.map((item, index) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${index + 1}. ${item.label || item.stage_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_check || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
      <span class="beginner-task-actions">
        ${item.workflow_id ? `<button class="secondary-button" type="button" data-beginner-next="${escapeRawHtml(item.workflow_id)}" data-beginner-action="${escapeRawHtml(item.workflow_id)}">${escapeHtml("运行这一步")}</button>` : ""}
        ${item.target_id ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.target_id)}">${escapeHtml("看这一步")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["交易系统状态", "等待今日交易建议加载。", "warn"]]);
  target.innerHTML = overview + stageRows;
}

function renderDailyTradePackageChecklist(packageChecklist = {}, runtime = {}, target = byId("daily-trade-package-checklist")) {
  if (!target) return;
  const summary = packageChecklist.summary || {};
  const items = Array.isArray(packageChecklist.items) ? packageChecklist.items : [];
  if (!items.length) {
    target.innerHTML = statusRows([
      ["交易包完整度", "等待今日交易决策单生成后显示完整证据链。", "warn"],
    ]);
    return;
  }
  const runtimeItems = items.map((item) => {
    if (item.step_id === "paper_simulation_receipt" && runtime.paperReceipt) {
      return {
        ...item,
        status: "done",
        evidence: `${runtime.paperReceipt.time || "--"} / 收益=${formatPercent(runtime.paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(runtime.paperReceipt.metrics?.max_drawdown)}`,
      };
    }
    if (item.step_id === "post_close_journal" && runtime.journalReceipt) {
      return {
        ...item,
        status: "done",
        evidence: `${runtime.journalReceipt.time || "--"} / 复盘项=${formatNumber(runtime.journalReceipt.metrics?.journal_item_count)}`,
      };
    }
    return item;
  });
  const doneCount = runtimeItems.filter((item) => item.status === "done").length;
  const requiredCount = runtimeItems.filter((item) => item.status === "required").length;
  const blockedCount = runtimeItems.filter((item) => item.status === "blocked").length;
  const nextItem = runtimeItems.find((item) => item.status === "blocked" || item.status === "required") || runtimeItems.find((item) => item.status === "manual_locked") || {};
  const headerTone = blockedCount ? "danger" : requiredCount ? "warn" : "ok";
  const header = statusRows([
    ["交易包完整度", `已完成=${formatNumber(doneCount)} / 待补=${formatNumber(requiredCount)} / 阻断=${formatNumber(blockedCount)} / 下一步=${nextItem.label || summary.next_step_id || "--"}`, headerTone],
    ["下单边界", summary.order_placement_allowed ? "异常：出现下单权限" : "研究到人工复核，不自动下单", summary.order_placement_allowed ? "danger" : "ok"],
  ]);
  const rows = runtimeItems.map((item, index) => `
    <div class="list-row ${escapeHtml(dailyTradeSystemStageTone(item.status || ""))}">
      <strong>${escapeHtml(`${index + 1}. ${item.label || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.evidence || ""}`)}</span>
      <span>${escapeHtml(item.plain_action || "")}</span>
      <span class="beginner-task-actions">
        ${item.gui_target ? `<button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("看这一步")}</button>` : ""}
      </span>
    </div>
  `).join("");
  target.innerHTML = header + rows;
}

function dailyTradeSystemModeTone(mode = "") {
  if (mode.includes("blocked")) return "danger";
  if (mode === "paper_rehearsal_required" || mode === "manual_ticket_required") return "warn";
  return "warn";
}

function dailyTradeSystemStageTone(status = "") {
  if (status === "done") return "ok";
  if (status === "blocked") return "danger";
  if (status === "manual_locked") return "danger";
  if (status === "required") return "warn";
  return "warn";
}

function dailyTradeDecisionRuntimeState(sheet = {}) {
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const journalReceipt = latestExecutionReceipt("post_close_journal");
  const evidenceRows = (Array.isArray(sheet.missing_evidence) ? sheet.missing_evidence : []).map((item) => {
    let runtimeStatus = item.status || "missing";
    let runtimeEvidence = "";
    if (item.check_id === "paper_simulation_receipt" && paperReceipt) {
      runtimeStatus = "local_receipt_seen";
      runtimeEvidence = `${paperReceipt.time || "--"} / 收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}`;
    }
    if (item.check_id === "post_close_journal_plan" && journalReceipt) {
      runtimeStatus = "local_receipt_seen";
      runtimeEvidence = `${journalReceipt.time || "--"} / 复盘项=${formatNumber(journalReceipt.metrics?.journal_item_count)}`;
    }
    return {
      ...item,
      runtime_status: runtimeStatus,
      runtime_evidence: runtimeEvidence,
      locally_completed: runtimeStatus === "local_receipt_seen" || runtimeStatus === "pass" || runtimeStatus === "ready",
    };
  });
  const completedEvidenceCount = evidenceRows.filter((item) => item.locally_completed).length;
  const missingEvidenceCount = evidenceRows.length - completedEvidenceCount;
  return {
    paperReceipt,
    journalReceipt,
    evidenceRows,
    completedEvidenceCount,
    missingEvidenceCount,
  };
}

function dailyTradeDecisionNextAction(runtime = {}, next = {}, decision = "") {
  const evidenceRows = Array.isArray(runtime.evidenceRows) ? runtime.evidenceRows : [];
  if (decision.includes("blocked")) {
    return { ...next, tone: "danger" };
  }
  const missing = evidenceRows.find((item) => !item.locally_completed);
  if (!missing) {
    return {
      button_label: "核对人工票据",
      target_id: "daily-manual-broker-handoff-ticket-table",
      workflow_id: "",
      plain_action: "证据已在本浏览器补齐，继续人工核对票据、现金、价格和风险；系统仍不会下单。",
      tone: "warn",
    };
  }
  if (missing.check_id === "paper_simulation_receipt") {
    return {
      button_label: "运行模拟盘复核",
      target_id: "paper-metrics",
      workflow_id: "paper_simulation",
      plain_action: "先补同参数模拟盘回执，再看收益、回撤、成交和保护事件。",
      tone: "warn",
    };
  }
  if (missing.check_id === "post_close_journal_plan") {
    return {
      button_label: "记录收盘后复盘",
      target_id: "beginner-post-close-journal-board",
      workflow_id: "post_close_journal",
      plain_action: "模拟盘和人工复核后，把今天执行或跳过的原因写成收盘后复盘回执。",
      tone: "warn",
    };
  }
  return {
    button_label: missing.label || next.button_label || "查看缺失证据",
    target_id: missing.target_id || next.target_id || "daily-trade-decision-evidence",
    workflow_id: missing.workflow_id || next.workflow_id || "",
    plain_action: missing.why || next.plain_action || "先补齐缺失证据，再进入人工复核。",
    tone: "warn",
  };
}

function dailyTradeDecisionEvidenceTone(status = "") {
  if (["pass", "ready", "local_receipt_seen"].includes(status)) return "ok";
  if (["blocked", "failed"].includes(status)) return "danger";
  return "warn";
}

function renderDailyLiveTransitionPlan(plan = {}) {
  const summaryTarget = byId("daily-live-transition-summary");
  const loopTarget = byId("daily-live-transition-loop");
  const profileTarget = byId("daily-live-transition-risk-profiles");
  const gateTarget = byId("daily-live-transition-gates");
  if (!summaryTarget || !loopTarget || !profileTarget || !gateTarget) return;
  const summary = plan.summary || {};
  const status = summary.status || "waiting_for_daily_top3_signal";
  const tone = status.includes("blocked") ? "danger" : status.includes("candidate") ? "warn" : "warn";
  summaryTarget.innerHTML = statusRows([
    ["当前状态", zhConsoleText(status), tone],
    ["主线市场", summary.primary_market || "CN_ETF", "ok"],
    ["今日信号", `${formatNumber(summary.today_signal_count || 0)} / 前三因子=${formatNumber(summary.selected_factor_count || 0)}`, summary.today_signal_count > 0 ? "ok" : "warn"],
    ["模拟盘", summary.paper_simulation_required ? "必须先跑" : "未要求", "warn"],
    ["小资金观察闸门", summary.small_capital_review_required ? "必须通过" : "未要求", "warn"],
    ["下单权限", summary.order_placement_allowed ? "异常开启" : "禁止自动下单", summary.order_placement_allowed ? "danger" : "ok"],
  ]);
  const loopRows = Array.isArray(plan.operating_loop) ? plan.operating_loop : [];
  loopTarget.innerHTML = loopRows.length ? loopRows.map((item) => `
    <div class="list-row ${escapeHtml(dailyLiveTransitionTone(item.status || ""))}">
      <strong>${escapeHtml(`${item.step_number || "--"}. ${item.title || item.step_id || ""}`)}</strong>
      <span>${escapeHtml(`${zhConsoleText(item.status || "waiting")} / ${item.plain_action || ""}`)}</span>
      <span>${escapeHtml(item.evidence || "")}</span>
      <span class="beginner-task-actions">
        ${item.gui_target ? `<button class="secondary-button" type="button" data-live-transition-target="${escapeRawHtml(item.gui_target)}">${escapeHtml("看这一步")}</button>` : ""}
      </span>
    </div>
  `).join("") : statusRows([["等待今日建议", "先生成今日前三交易建议。", "warn"]]);
  const profiles = Array.isArray(plan.risk_profiles) ? plan.risk_profiles : [];
  profileTarget.innerHTML = profiles.length ? profiles.map((item) => `
    <div class="list-row ${escapeHtml(item.selected ? "warn" : item.profile_id === "aggressive_30dd" ? "warn" : "ok")}">
      <strong>${escapeHtml(`${item.selected ? "已选择 / " : ""}${item.label || item.profile_id || ""}`)}</strong>
      <span>${escapeHtml(`最大回撤=${formatPercent(item.max_acceptable_drawdown)} / 总仓位=${formatPercent(item.max_gross_exposure)} / 单ETF=${formatPercent(item.max_single_etf_weight)}`)}</span>
      <span>${escapeHtml(item.plain_use || "")}</span>
    </div>
  `).join("") : statusRows([["暂无风险档位", "等待今日建议加载。", "warn"]]);
  const gates = Array.isArray(plan.evidence_gates) ? plan.evidence_gates : [];
  gateTarget.innerHTML = gates.length ? gates.map((item) => `
    <div class="list-row ${escapeHtml(item.required ? "warn" : "ok")}">
      <strong>${escapeHtml(item.label || item.gate_id || "")}</strong>
      <span>${escapeHtml(item.plain_requirement || "")}</span>
    </div>
  `).join("") : statusRows([["暂无闸门", "等待今日建议加载。", "warn"]]);
}

function dailyLiveTransitionTone(status = "") {
  if (status === "done") return "ok";
  if (status === "blocked") return "danger";
  if (status === "required") return "warn";
  return "warn";
}

function renderDailyReadinessCard() {
  const lightTarget = byId("daily-readiness-light");
  const actionTarget = byId("daily-readiness-primary-action");
  const safetyTarget = byId("daily-readiness-safety");
  if (!lightTarget || !actionTarget || !safetyTarget) return;
  const decision = dailyReadinessDecision();
  lightTarget.innerHTML = statusRows([
    ["状态灯", decision.title, decision.tone],
    ["原因", decision.reason, decision.tone],
    ["证据摘要", decision.evidence, "muted"],
  ]);
  actionTarget.innerHTML = `
    <div class="list-row ${escapeHtml(decision.tone)}">
      <strong>${escapeHtml(decision.primary_action)}</strong>
      <span>${escapeHtml(decision.detail)}</span>
      ${dailyReadinessButtons(decision)}
    </div>
  `;
  safetyTarget.innerHTML = statusRows([
    ["实盘边界", "仍然禁止自动下单", "danger"],
    ["系统权限", "不连接券商，不读取账户，不真实下单。", "danger"],
    ["人工复核", "只有信号新鲜、模拟盘回执和手工票据齐全后，才看券商端人工核对。", "warn"],
  ]);
}

function dailyReadinessButtons(decision = {}) {
  const targetId = decision.target_id || "daily-readiness-primary-action";
  if (decision.action_workflow) {
    return `
      <span class="beginner-task-actions">
        <button class="primary-button" type="button" data-daily-readiness-workflow="${escapeRawHtml(decision.action_workflow)}" data-beginner-action="${escapeRawHtml(decision.action_workflow)}">${escapeHtml(decision.cta_label || "运行这一步")}</button>
        <button class="secondary-button" type="button" data-daily-readiness-target="${escapeRawHtml(targetId)}" data-beginner-target="${escapeRawHtml(targetId)}">看证据位置</button>
      </span>
    `;
  }
  return `
    <span class="beginner-task-actions">
      <button class="primary-button" type="button" data-daily-readiness-target="${escapeRawHtml(targetId)}" data-beginner-target="${escapeRawHtml(targetId)}">${escapeHtml(decision.cta_label || "看证据位置")}</button>
    </span>
  `;
}

function dailyLiveGateDecision() {
  const trade = state.dailyTradeAdvisory || {};
  const liveGate = trade.daily_live_readiness_gate || {};
  const summary = liveGate.summary || {};
  const gateDecision = summary.decision || "";
  if (!gateDecision) return null;
  const gateRows = Array.isArray(liveGate.gate_rows) ? liveGate.gate_rows : [];
  const blockedRows = gateRows.filter((row) => row.status === "blocked");
  const tone = gateDecision.includes("blocked") ? "danger" : "warn";
  const titleMap = {
    blocked_fix_current_positions: "红灯：先修正当前持仓",
    blocked_pretrade_red_light: "红灯：先处理盘前阻断",
    paper_rehearsal_required: "黄灯：先跑模拟盘复核",
    waiting_for_trade_ticket: "黄灯：先补齐人工票据",
    waiting_for_daily_signal: "黄灯：先生成今日信号",
  };
  return {
    tone,
    title: titleMap[gateDecision] || `总闸门：${zhConsoleText(gateDecision)}`,
    reason: summary.primary_reason || "等待实盘前总闸门给出原因。",
    evidence: `总闸门=${zhConsoleText(gateDecision)} / 阻断=${formatNumber(blockedRows.length)} / 自动下单=${summary.order_placement_allowed ? "异常开启" : "禁止"}`,
    primary_action: summary.primary_action || "先看实盘前总闸门。",
    detail: summary.primary_action || "先按总闸门提示处理。",
    cta_label: summary.cta_label || "看实盘前总闸门",
    target_id: summary.cta_target || "daily-live-readiness-gate",
    action_workflow: summary.action_workflow || "",
    liveGateDecision: gateDecision,
  };
}

function dailyReadinessDecision() {
  const liveGateDecision = dailyLiveGateDecision();
  if (liveGateDecision) return liveGateDecision;
  const trade = state.dailyTradeAdvisory || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const freshness = readiness.freshness || {};
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const actions = Array.isArray(trade.operator_next_actions)
    ? trade.operator_next_actions
    : Array.isArray(trade.pretrade_workflow?.operator_next_actions)
      ? trade.pretrade_workflow.operator_next_actions
      : [];
  const firstAction = actions[0] || {};
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const dailyReceipt = latestExecutionReceipt("daily_trade_advisory");
  const selectedCount = Number(summary.selected_factor_count || 0);
  const signalCount = Number(summary.signal_count || 0);
  const signalFresh = freshness.fresh_for_run_date === true;
  const evidence = `因子=${formatNumber(selectedCount)} / 信号=${formatNumber(signalCount)} / 票据=${formatNumber(tickets.length)} / 模拟盘回执=${paperReceipt ? "有" : "无"}`;
  if (!signalFresh || blockers.includes("stale_signal_date")) {
    return {
      tone: "danger",
      title: "红灯：今天先别买",
      reason: `信号日期不新鲜：运行=${freshness.run_date || "--"} / 最新=${freshness.latest_signal_date || "--"}`,
      evidence,
      primary_action: firstAction.title || "先刷新 CN_ETF 数据",
      detail: firstAction.plain_action || "刷新数据后重新生成今日前三因子信号。",
      cta_label: firstAction.cta_label || "去看数据刷新",
      target_id: firstAction.cta_target || firstAction.gui_target || "recent-data-refresh-status",
      action_workflow: "daily_ops",
    };
  }
  if (!paperReceipt) {
    return {
      tone: "warn",
      title: "黄灯：先跑模拟盘复核",
      reason: dailyReceipt ? `已有今日建议回执：${dailyReceipt.time || "--"}` : "已有信号，但还缺少本地模拟盘回执。",
      evidence,
      primary_action: "运行模拟盘复核",
      detail: "先看收益、回撤、保护事件和成交笔数，再决定是否进入人工复核。",
      cta_label: "去跑模拟盘",
      target_id: "paper-metrics",
      action_workflow: "paper_simulation",
    };
  }
  if (tickets.length > 0 && (readiness.traffic_light || "") === "yellow" && blockers.length === 0) {
    return {
      tone: "warn",
      title: "黄灯：可以进入人工复核",
      reason: "信号、模拟盘回执和手工票据都有了，但系统仍然禁止自动下单。",
      evidence,
      primary_action: "打开人工券商复核卡",
      detail: "按票据人工核对 ETF、价格、数量、现金和风险，不让系统下单。",
      cta_label: "查看手工票据",
      target_id: "daily-manual-broker-handoff-ticket-table",
    };
  }
  return {
    tone: "warn",
    title: "黄灯：先补齐人工复核证据",
    reason: readiness.operator_verdict || "信号存在，但票据或复核证据还不完整。",
    evidence,
    primary_action: firstAction.title || "生成今日前三交易建议",
    detail: firstAction.plain_action || "补齐今日建议、模拟盘回执和手工票据后再看人工复核。",
    cta_label: firstAction.cta_label || "查看下一步",
    target_id: firstAction.cta_target || firstAction.gui_target || "daily-pretrade-next-actions",
    action_workflow: "daily_trade_advisory",
  };
}

function renderBeginnerLiveHandoff() {
  const statusTarget = byId("beginner-live-handoff-status");
  const stepsTarget = byId("beginner-live-handoff-steps");
  const ticketsTarget = byId("beginner-live-handoff-tickets");
  if (!statusTarget || !stepsTarget || !ticketsTarget) return;
  const decision = dailyReadinessDecision();
  const trade = state.dailyTradeAdvisory || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  statusTarget.innerHTML = statusRows([
    ["今天结论", decision.title || "等待今日建议", decision.tone || "warn"],
    ["总闸门", decision.liveGateDecision || "等待实盘前总闸门", decision.tone || "warn"],
    ["为什么", decision.reason || "先加载今日前三因子、信号和模拟盘回执。", decision.tone || "warn"],
    ["操作边界", "这是人工实盘前交接，不会自动下单，也不会连接券商。", "danger"],
    ["当前证据", `因子=${formatNumber(summary.selected_factor_count || 0)} / 信号=${formatNumber(summary.signal_count || 0)} / 灯号=${readiness.traffic_light || "unknown"}`, "muted"],
  ]);
  stepsTarget.innerHTML = beginnerLiveHandoffSteps().map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.step)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <span class="beginner-task-actions">
        ${beginnerLiveHandoffButton(item)}
      </span>
    </div>
  `).join("");
  ticketsTarget.innerHTML = beginnerLiveHandoffTickets().map((item) => `
    <div class="list-row ${escapeHtml(item.tone)}">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <span>${escapeHtml(item.note)}</span>
    </div>
  `).join("");
}

function beginnerLiveHandoffSteps() {
  const trade = state.dailyTradeAdvisory || {};
  const gateSteps = dailyLiveGateStepRows(trade.daily_live_readiness_gate || {});
  if (gateSteps.length) return gateSteps;
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const freshness = readiness.freshness || {};
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const tickets = beginnerLiveTicketRows();
  const selectedCount = Number(summary.selected_factor_count || 0);
  const signalCount = Number(summary.signal_count || 0);
  const signalFresh = freshness.fresh_for_run_date === true;
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const dailyReceipt = latestExecutionReceipt("daily_trade_advisory");
  const ticketReady = tickets.length > 0 && blockers.length === 0;
  const decision = dailyReadinessDecision();
  return [
    {
      step: "0. 开盘前一键体检",
      tone: decision.tone || "warn",
      detail: "先刷新日常运营和今日前三因子/信号，再回到红黄灯；不会自动跑模拟盘或下单。",
      workflow: "daily_pretrade_checkup",
      target: "beginner-live-handoff-board",
      button: "运行开盘前体检",
    },
    {
      step: "1. 刷新 CN_ETF 数据",
      tone: signalFresh ? "ok" : "danger",
      detail: signalFresh
        ? `信号日期已匹配 ${freshness.run_date || "--"}。`
        : `信号过期：运行日=${freshness.run_date || "--"} / 最新信号=${freshness.latest_signal_date || "--"}。`,
      workflow: signalFresh ? "" : "daily_ops",
      target: "recent-data-refresh-status",
      button: signalFresh ? "看数据证据" : "刷新日常运营",
    },
    {
      step: "2. 生成今日前三因子/信号",
      tone: signalFresh && selectedCount > 0 && signalCount > 0 ? "ok" : "warn",
      detail: `前三因子=${formatNumber(selectedCount)} / 建议信号=${formatNumber(signalCount)} / 回执=${dailyReceipt ? "有" : "无"}。`,
      workflow: signalFresh && signalCount > 0 ? "" : "daily_trade_advisory",
      target: "daily-trade-factor-table",
      button: signalFresh && signalCount > 0 ? "看前三因子" : "生成今日建议",
    },
    {
      step: "3. 跑本地模拟盘复核",
      tone: paperReceipt ? "ok" : "warn",
      detail: paperReceipt
        ? `最近模拟盘回执=${paperReceipt.time || "--"}。`
        : "还没有模拟盘回执，不能把单日信号当成可操作结论。",
      workflow: paperReceipt ? "" : "paper_simulation",
      target: "paper-metrics",
      button: paperReceipt ? "看模拟盘指标" : "运行模拟盘",
    },
    {
      step: "4. 生成人工券商票据",
      tone: ticketReady ? "warn" : "danger",
      detail: ticketReady
        ? `已有 ${formatNumber(tickets.length)} 张人工券商票据，仍需人工核对。`
        : "票据为空或仍有阻断项，今天不能照着买。",
      workflow: ticketReady ? "" : "daily_trade_advisory",
      target: "daily-manual-broker-handoff-ticket-table",
      button: ticketReady ? "看人工票据" : "补齐票据",
    },
    {
      step: "5. 人工核对后再去券商端操作",
      tone: ticketReady ? "warn" : "danger",
      detail: ticketReady
        ? "只把下方票据作为手工核对清单；价格、数量、现金和风险都要在券商端再确认。"
        : "红灯或票据缺失时，先不要买，也不要手工补单。",
      target: "daily-trade-manual-table",
      button: "看手工执行计划",
    },
  ];
}

function dailyLiveGateStepRows(liveGate = {}) {
  const rows = Array.isArray(liveGate.gate_rows) ? liveGate.gate_rows : [];
  if (!rows.length) return [];
  return rows.map((row, index) => {
    const status = row.status || "waiting";
    const tone = status === "ready"
      ? "ok"
      : status === "blocked" || status === "locked"
        ? "danger"
        : "warn";
    return {
      step: `${index + 1}. ${row.label || row.gate_id || "实盘前闸门"}`,
      tone,
      detail: `${zhConsoleText(status)} / ${row.plain_check || row.evidence || ""}`,
      target: row.gui_target || "daily-live-readiness-gate",
      button: "看证据",
    };
  });
}

function beginnerLiveHandoffButton(item = {}) {
  if (item.workflow) {
    return `<button class="primary-button" type="button" data-live-handoff-action="${escapeRawHtml(item.workflow)}">${escapeHtml(item.button || "运行")}</button>`;
  }
  if (item.target) {
    return `<button class="secondary-button" type="button" data-live-handoff-target="${escapeRawHtml(item.target)}">${escapeHtml(item.button || "看证据")}</button>`;
  }
  return "";
}

function beginnerLiveHandoffTickets() {
  const tickets = beginnerLiveTicketRows();
  if (tickets.length === 0) {
    return [{
      title: "人工券商票据：暂无",
      detail: "没有可复制给人工核对的买卖清单。",
      note: "不会自动下单；红灯时今天先别买。",
      tone: "danger",
    }];
  }
  return tickets.slice(0, 3).map((ticket, index) => {
    const asset = ticket.asset_id || ticket.symbol || "--";
    const side = ticket.side || ticket.action || "review";
    const quantity = ticket.rounded_quantity ?? ticket.estimated_quantity ?? "--";
    const value = ticket.rounded_value ?? ticket.target_value;
    return {
      title: `人工券商票据 ${index + 1}: ${asset}`,
      detail: `${side} / 数量=${formatNumber(quantity)} / 金额=${formatNumber(value)} / 权重=${formatPercent(ticket.target_weight)}`,
      note: ticket.manual_instruction || ticket.copy_text || "人工核对 ETF、价格、数量、现金和风险后，再在券商端手动处理。",
      tone: "warn",
    };
  });
}

function beginnerLiveTicketRows() {
  const trade = state.dailyTradeAdvisory || {};
  const readiness = trade.pretrade_readiness || {};
  const handoff = trade.manual_broker_handoff || {};
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const manualPlan = Array.isArray(trade.manual_trade_plan) ? trade.manual_trade_plan : [];
  const handoffStatus = handoff.status || "";
  if (tickets.length) return tickets;
  if (blockers.length > 0) return [];
  if (!readiness.manual_action_candidate) return [];
  return ["ready", "manual_review_required"].includes(handoffStatus) ? manualPlan : [];
}

function renderDailyEvidenceChain() {
  const target = byId("daily-evidence-chain");
  if (!target) return;
  const trade = state.dailyTradeAdvisory || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const freshness = readiness.freshness || {};
  const handoff = trade.manual_broker_handoff || {};
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const recent = state.recentDataRefresh || {};
  const recentDecision = recent.decision || {};
  const recentCoverage = recent.coverage || {};
  const targetWindow = recent.target_window || {};
  const paperReceipt = latestExecutionReceipt("paper_simulation");
  const dailyReceipt = latestExecutionReceipt("daily_trade_advisory");
  const selectedCount = Number(summary.selected_factor_count || 0);
  const signalCount = Number(summary.signal_count || 0);
  const signalFresh = freshness.fresh_for_run_date === true;
  const rows = [
    {
      step: "数据刷新",
      status: recentDecision.signal_data_stale_cleared ? "ok" : "warn",
      detail: `最新数据=${recentCoverage.latest_data_date || "--"} / 目标信号日=${targetWindow.signal_date || freshness.run_date || "--"}`,
      action: recentDecision.signal_data_stale_cleared ? "数据闸门已通过；继续看今日信号。" : "先刷新 CN_ETF 数据，避免用旧信号做人工操作。",
      target_id: "recent-data-refresh-status",
    },
    {
      step: "今日前三因子",
      status: signalFresh && selectedCount > 0 && signalCount > 0 ? "ok" : blockers.includes("stale_signal_date") ? "danger" : "warn",
      detail: `因子=${formatNumber(selectedCount)} / 信号=${formatNumber(signalCount)} / 信号日=运行${freshness.run_date || "--"}，最新${freshness.latest_signal_date || "--"}`,
      action: dailyReceipt ? `已生成今日建议回执：${dailyReceipt.time || "--"}` : "生成今日前三交易建议，先拿到 ETF、权重和手工票据。",
      target_id: "daily-trade-factor-table",
    },
    {
      step: "模拟盘复核",
      status: paperReceipt ? "ok" : "warn",
      detail: paperReceipt
        ? `最近回执=${paperReceipt.time || "--"} / 收益=${formatPercent(paperReceipt.metrics?.total_return)} / 回撤=${formatPercent(paperReceipt.metrics?.max_drawdown)}`
        : "暂无本地模拟盘回执；单日信号不能直接当作可实盘盈利。",
      action: "下单前先跑本地模拟盘，看费用、回撤、保护事件和成交笔数。",
      target_id: "paper-metrics",
    },
    {
      step: "人工券商复核",
      status: tickets.length && blockers.length === 0 ? "warn" : "danger",
      detail: `票据=${formatNumber(tickets.length)} / 灯号=${readiness.traffic_light || "red"} / 自动下单=禁止`,
      action: tickets.length ? "只把票据作为人工核对清单；价格、数量、现金和风险都要在券商端再确认。" : "还没有可读票据，不能进入人工买卖步骤。",
      target_id: "daily-manual-broker-handoff-ticket-table",
    },
  ];
  target.innerHTML = rows.map((row, index) => `
    <div class="list-row ${escapeHtml(row.status)} daily-evidence-step">
      <strong>${escapeHtml(`${index + 1}. ${row.step}`)}</strong>
      <span>${escapeHtml(row.detail)}</span>
      <span>${escapeHtml(row.action)}</span>
      <span class="beginner-task-actions">
        <button class="secondary-button" type="button" data-daily-evidence-target="${escapeRawHtml(row.target_id)}" data-beginner-target="${escapeRawHtml(row.target_id)}">看对应位置</button>
      </span>
    </div>
  `).join("");
}

function latestExecutionReceipt(workflowId) {
  const rows = Array.isArray(state.executionReceipts) && state.executionReceipts.length
    ? state.executionReceipts
    : loadExecutionReceipts(state.controlCenter?.execution_receipts || {});
  return rows.find((item) => item.workflow_id === workflowId) || null;
}

function executionReceiptsForWorkflow(workflowId) {
  const rows = Array.isArray(state.executionReceipts) && state.executionReceipts.length
    ? state.executionReceipts
    : loadExecutionReceipts(state.controlCenter?.execution_receipts || {});
  return rows.filter((item) => item?.workflow_id === workflowId);
}

function renderDailyPretradeReadiness(readiness) {
  const summary = readiness.summary || {};
  const freshness = readiness.freshness || {};
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const warnings = Array.isArray(readiness.warnings) ? readiness.warnings : [];
  const confirmations = Array.isArray(readiness.required_confirmations) ? readiness.required_confirmations : [];
  const light = readiness.traffic_light || "red";
  const verdictTone = light === "red" ? "danger" : "warn";
  byId("daily-pretrade-readiness-verdict").innerHTML = statusRows([
    ["总灯号", light === "yellow" ? "黄灯：只能进入人工复核" : "红灯：不能进入人工操作", verdictTone],
    ["结论", readiness.operator_verdict || "等待今日信号和手工票据生成。", verdictTone],
    ["目标金额", formatNumber(summary.target_value), "muted"],
    ["取整后金额", formatNumber(summary.rounded_value), "muted"],
    ["取整后剩余", formatNumber(summary.cash_delta_after_rounding), "muted"],
    ["信号日期", `运行=${freshness.run_date || "--"} / 最新=${freshness.latest_signal_date || "--"}`, freshness.fresh_for_run_date ? "ok" : "danger"],
    ["自动下单", readiness.live_order_allowed ? "允许" : "禁止", "danger"],
    ["阻断项", blockers.length ? blockers.join(" / ") : "无结构化阻断项", blockers.length ? "danger" : "ok"],
    ["提醒", warnings.join(" / ") || "即使黄灯，也必须人工核对模拟盘、价格、现金和风险。", "warn"],
  ]);
  byId("daily-pretrade-readiness-status").innerHTML = confirmations.length
    ? confirmations.map((item) => `
      <div class="list-row ${escapeHtml(item.status === "pass" ? "ok" : item.status === "blocked" ? "danger" : "warn")}">
        <strong>${escapeHtml(item.check_id || "")}</strong>
        <span>${escapeHtml(zhConsoleText(item.status || "--"))}</span>
        <span>${escapeHtml(item.text || "")}</span>
      </div>
    `).join("")
    : statusRows([["signal_freshness", "暂无信号日期判定；先生成今日前三交易建议。", "warn"]]);
  byId("daily-pretrade-readiness-action-table").innerHTML = tableRows(readiness.action_sequence || [], [
    "step_number",
    "ticket_id",
    "asset_id",
    "side",
    "current_quantity",
    "current_value",
    "target_value",
    "delta_value",
    "latest_price",
    "rounded_quantity",
    "rounded_quantity_delta",
    "rounded_value",
    "cash_delta_after_rounding",
    "live_order_allowed",
  ]);
}

function renderDailyPretradeNextActions(actions) {
  const rows = Array.isArray(actions) ? actions : [];
  const toneForAction = (status) => {
    if (["blocked_until_done"].includes(status)) return "danger";
    if (["required_before_manual_ticket", "manual_only", "waiting"].includes(status)) return "warn";
    return "muted";
  };
  byId("daily-pretrade-next-actions").innerHTML = rows.length
    ? rows.map((item, index) => `
      <div class="list-row ${escapeHtml(toneForAction(item.status || ""))}">
        <strong>${escapeHtml(`${index + 1}. ${item.title || item.action_id || ""}`)}</strong>
        <span>${escapeHtml(zhConsoleText(`${item.status || "--"} / ${item.action_id || ""}`))}</span>
        <span>${escapeHtml(item.plain_action || "")}</span>
        <span>${escapeHtml(item.why || "")}</span>
        ${dailyNextActionButtons(item)}
      </div>
    `).join("")
    : statusRows([["refresh_cn_etf_data", "暂无下一步动作；先生成今日前三交易建议。", "warn"]]);
}

function dailyNextActionButtons(item = {}) {
  const actionId = item.action_id || "";
  const workflow = item.action_workflow || "";
  const target = item.cta_target || item.gui_target || "daily-pretrade-next-actions";
  const label = item.cta_label || (workflow ? "运行这一步" : "查看位置");
  if (workflow) {
    return `
      <span class="beginner-task-actions daily-next-action-buttons">
        <button class="primary-button" type="button" data-daily-next-action="${escapeRawHtml(actionId)}" data-beginner-action="${escapeRawHtml(workflow)}">${escapeHtml(label)}</button>
        <button class="secondary-button" type="button" data-beginner-target="${escapeRawHtml(target)}">看对应位置</button>
      </span>
    `;
  }
  return `
    <span class="beginner-task-actions daily-next-action-buttons">
      <button class="primary-button" type="button" data-daily-next-action="${escapeRawHtml(actionId)}" data-beginner-target="${escapeRawHtml(target)}">${escapeHtml(label)}</button>
    </span>
  `;
}

function renderManualBrokerHandoff(handoff) {
  const summary = handoff.summary || {};
  const checklist = Array.isArray(handoff.confirmation_checklist) ? handoff.confirmation_checklist : [];
  const tickets = Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets : [];
  byId("daily-manual-broker-handoff-status").innerHTML = statusRows([
    ["状态", handoff.status || "waiting_for_tickets", tickets.length ? "warn" : "danger"],
    ["结论", handoff.operator_summary || "还没有可核对票据。", tickets.length ? "warn" : "danger"],
    ["票据数量", formatNumber(summary.ticket_count), tickets.length ? "warn" : "muted"],
    ["取整后金额", formatNumber(summary.rounded_value), "muted"],
    ["取整后剩余", formatNumber(summary.cash_delta_after_rounding), "muted"],
    ["自动下单", handoff.ready_for_auto_order ? "允许" : "禁止", "danger"],
    ["模拟盘复核", handoff.paper_simulation_required ? "必需" : "未要求", handoff.paper_simulation_required ? "warn" : "muted"],
  ]);
  byId("daily-manual-broker-handoff-checklist").innerHTML = checklist.length
    ? checklist.map((item) => `
      <div class="list-row ${escapeHtml(item.status === "blocked_for_automation" ? "danger" : "warn")}">
        <strong>${escapeHtml(item.check_id || "")}</strong>
        <span>${escapeHtml(zhConsoleText(item.status || "--"))}</span>
        <span>${escapeHtml(item.text || "")}</span>
      </div>
    `).join("")
    : statusRows([["暂无手工核对清单", "先生成今日前三交易建议。", "warn"]]);
  renderManualBrokerBeginnerChecklist(handoff, tickets);
  renderManualTicketExport(state.dailyTradeAdvisory?.manual_ticket_export || {}, tickets);
  renderManualBrokerCopyCards(tickets);
  const ticketRows = tickets.map((ticket) => ({
    ...ticket,
    lower_price_bound: ticket.execution_guardrails?.lower_price_bound,
    upper_price_bound: ticket.execution_guardrails?.upper_price_bound,
    max_slippage_bps: ticket.execution_guardrails?.max_slippage_bps,
  }));
  byId("daily-manual-broker-handoff-ticket-table").innerHTML = tableRows(ticketRows, [
    "step_number",
    "asset_id",
    "side",
    "reference_price",
    "lower_price_bound",
    "upper_price_bound",
    "max_slippage_bps",
    "rounded_quantity",
    "rounded_value",
    "cash_delta_after_rounding",
    "live_order_allowed",
    "copy_text",
  ]);
}

function renderManualBrokerBeginnerChecklist(handoff = {}, tickets = []) {
  const target = byId("daily-manual-broker-handoff-beginner-checklist");
  if (!target) return;
  const hasTickets = tickets.length > 0;
  const statusTone = hasTickets ? "warn" : "danger";
  target.innerHTML = statusRows([
    [
      "1. 核对 ETF代码",
      hasTickets ? "逐行确认 asset_id 是否是你准备在券商端手动查看的 ETF，不认识就跳过。" : "暂无票据，不能进入券商端人工操作。",
      statusTone,
    ],
    [
      "2. 核对方向和数量",
      "逐行核对 side、rounded_quantity、rounded_value；数量为 0 或方向不确定时不要操作。",
      "warn",
    ],
    [
      "3. 核对实时价格",
      "reference_price 只是参考价，不是订单价格；券商端实时价格和涨跌停状态优先。",
      "warn",
    ],
    [
      "4. 核对现金和风险",
      "人工确认现金、仓位、单 ETF 权重和最大可承受回撤；现金不足或风险超限就跳过。",
      "warn",
    ],
    [
      "5. 记住这不是订单",
      handoff.ready_for_auto_order ? "异常：出现自动下单标记，请停止并审计。" : "票据只是人工复核材料；软件不连接券商、不读账户、不自动下单。",
      handoff.ready_for_auto_order ? "danger" : "ok",
    ],
  ]);
}

function renderManualTicketExport(exportPack = {}, tickets = []) {
  const target = byId("daily-manual-ticket-export");
  if (!target) return;
  const summary = exportPack.summary || {};
  const rows = Array.isArray(exportPack.rows) ? exportPack.rows : [];
  const csvText = exportPack.csv_text || "";
  const ticketCount = Number(summary.ticket_count ?? rows.length ?? tickets.length ?? 0);
  const status = summary.export_status || (ticketCount ? "review_only" : "waiting_for_tickets");
  const preview = csvText.split(/\r?\n/).slice(0, 4).join("\n");
  const tone = ticketCount > 0 ? "warn" : "danger";
  target.innerHTML = `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("导出人工复核票据")}</strong>
      <span>${escapeHtml(`${zhConsoleText(status)} / 票据=${formatNumber(ticketCount)} / 自动下单=禁止`)}</span>
      <span>${escapeHtml("CSV 只用于人工核对 ETF、方向、参考价、数量、金额和风险，不包含账户、券商或订单字段。")}</span>
      <span class="beginner-task-actions">
        <button class="secondary-button" type="button" data-manual-ticket-export-copy="csv" ${ticketCount ? "" : "disabled"}>${escapeHtml("复制 CSV")}</button>
        <button class="secondary-button" type="button" data-manual-ticket-export-download="csv" ${ticketCount ? "" : "disabled"}>${escapeHtml("下载 CSV")}</button>
      </span>
    </div>
    <pre class="json-cell manual-ticket-export-preview">${escapeHtml(preview || "暂无可导出的人工复核票据。")}</pre>
  `;
}

function renderManualBrokerCopyCards(tickets = []) {
  const target = byId("daily-manual-broker-copy-cards");
  if (!target) return;
  if (!tickets.length) {
    target.innerHTML = statusRows([["复制人工票据", "暂无可复制票据；先生成今日前三建议并处理红灯。", "warn"]]);
    return;
  }
  target.innerHTML = tickets.slice(0, 5).map((ticket, index) => {
    const text = ticket.copy_text || ticket.manual_instruction || "";
    return `
      <div class="list-row warn">
        <strong>${escapeHtml(`复制人工票据 ${index + 1}: ${ticket.asset_id || "--"}`)}</strong>
        <span>${escapeHtml(`方向=${zhConsoleText(ticket.side || "--")} / 数量=${formatNumber(ticket.rounded_quantity)} / 金额=${formatNumber(ticket.rounded_value)}`)}</span>
        <span>${escapeHtml("复制后仍要人工核对：ETF代码、实时价格、数量、现金、风险；系统不会下单。")}</span>
        <span class="beginner-task-actions">
          <button class="secondary-button" type="button" data-copy-ticket-text="${escapeRawHtml(text)}">复制票据文本</button>
        </span>
        ${renderTicketExecutionGuardrails(ticket)}
        ${renderTicketRiskBudget(ticket)}
        ${renderTicketReviewChecklist(ticket)}
      </div>
    `;
  }).join("");
}

function renderTicketExecutionGuardrails(ticket = {}) {
  const guardrails = ticket.execution_guardrails || {};
  if (!Object.keys(guardrails).length) return "";
  return `
    <div class="ticket-review-checklist ticket-execution-guardrails">
      <div class="mini-row warn">
        <strong>${escapeHtml("execution_guardrails")}</strong>
        <span>${escapeHtml(`实时价区间=${formatNumber(guardrails.lower_price_bound)} - ${formatNumber(guardrails.upper_price_bound)} / 最大滑点=${formatNumber(guardrails.max_slippage_bps)}bps / 滑点成本=${formatNumber(guardrails.max_estimated_slippage_cost)}`)}</span>
      </div>
      <div class="mini-row warn">
        <strong>${escapeHtml("manual_input_fields")}</strong>
        <span>${escapeHtml(Array.isArray(guardrails.manual_input_fields) ? guardrails.manual_input_fields.join(", ") : "broker_realtime_price, actual_fill_price, fill_quantity, execute_or_skip_reason")}</span>
      </div>
    </div>
  `;
}

function renderTicketRiskBudget(ticket = {}) {
  const risk = ticket.risk_budget || {};
  const skipConditions = Array.isArray(ticket.manual_skip_conditions) ? ticket.manual_skip_conditions : [];
  if (!Object.keys(risk).length && !skipConditions.length) return "";
  const breach = risk.single_etf_limit_breached || risk.rounded_value_limit_breached;
  const summaryRows = Object.keys(risk).length ? `
    <div class="mini-row ${escapeHtml(breach ? "danger" : "warn")}">
      <strong>${escapeHtml("票据风险预算")}</strong>
      <span>${escapeHtml(`档位=${risk.risk_profile_id || "--"} / 单ETF上限=${formatPercent(risk.max_single_etf_weight)} / 当日亏损预算=${formatNumber(risk.portfolio_daily_loss_budget)} / 票据不利波动=${formatNumber(risk.ticket_adverse_move_loss)} / 占预算=${formatPercent(risk.ticket_loss_budget_share)}`)}</span>
    </div>
  ` : "";
  const skipRows = skipConditions.length ? skipConditions.map((item) => `
    <div class="mini-row ${escapeHtml(item.status === "blocked" ? "danger" : item.status === "pass" ? "ok" : "warn")}">
      <strong>${escapeHtml(item.condition_id || "")}</strong>
      <span>${escapeHtml(item.plain_condition || "")}</span>
    </div>
  `).join("") : `
    <div class="mini-row warn">
      <strong>${escapeHtml("manual_skip_conditions")}</strong>
      <span>${escapeHtml("现金不足、单ETF超限、没有模拟盘回执、价格偏离或本人无法解释时都要跳过。")}</span>
    </div>
  `;
  return `
    <div class="ticket-review-checklist ticket-risk-budget">
      ${summaryRows}
      ${skipRows}
    </div>
  `;
}

function renderTicketReviewChecklist(ticket = {}) {
  const checklist = Array.isArray(ticket.review_checklist) && ticket.review_checklist.length
    ? ticket.review_checklist
    : DEFAULT_TICKET_REVIEW_CHECKLIST;
  const redFlags = Array.isArray(ticket.red_flags) && ticket.red_flags.length
    ? ticket.red_flags
    : DEFAULT_TICKET_RED_FLAGS;
  if (!checklist.length && !redFlags.length) return "";
  const checklistRows = checklist.map((item) => `
    <div class="mini-row warn">
      <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
      <span>${escapeHtml(item.plain_check || "")}</span>
    </div>
  `).join("");
  const flagRows = redFlags.map((item) => `
    <div class="mini-row danger" data-ticket-red-flag="${escapeRawHtml(item.flag_id || "")}">
      <strong>${escapeHtml(item.flag_id || "")}</strong>
      <span>${escapeHtml(item.plain_flag || "")}</span>
    </div>
  `).join("");
  return `
    <div class="ticket-review-checklist">
      <div class="mini-row muted">
        <strong>${escapeHtml("逐票核对")}</strong>
        <span>${escapeHtml("每一张票据都必须逐项人工确认；任何红灯出现就跳过。")}</span>
      </div>
      ${checklistRows}
      ${flagRows}
    </div>
  `;
}

async function copyTicketTextToClipboard(text) {
  if (!text) {
    showToast("没有可复制的票据文本", true);
    return;
  }
  if (!navigator.clipboard?.writeText) {
    showToast("clipboard_unavailable：请在票据表里手工选择 copy_text。", true);
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    showToast("已复制。复制后仍要人工核对，系统不会下单。");
  } catch (_error) {
    showToast("复制失败，请在票据表里手工选择 copy_text。", true);
  }
}

function downloadManualTicketExport() {
  const exportPack = state.dailyTradeAdvisory?.manual_ticket_export || {};
  const csvText = exportPack.csv_text || "";
  if (!csvText) {
    showToast("暂无可下载的人工复核票据", true);
    return;
  }
  const filename = exportPack.summary?.download_filename || "daily_manual_ticket_export.csv";
  const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("已生成 CSV。导出内容仅供人工复核，系统不会下单。");
}

function renderDailyPretradeWorkflow(workflow) {
  const steps = Array.isArray(workflow.steps) ? workflow.steps : [];
  const cards = Array.isArray(workflow.beginner_cards) ? workflow.beginner_cards : [];
  const stepTone = (status) => {
    if (["ready", "done", "completed"].includes(status)) return "ok";
    if (["blocked", "failed"].includes(status)) return "danger";
    return "warn";
  };
  byId("daily-pretrade-workflow-steps").innerHTML = steps.length
    ? steps.map((step) => `
      <div class="list-row ${escapeHtml(stepTone(step.status || ""))}">
        <strong>${escapeHtml(`${step.step_number || ""}. ${step.title || step.step_id || ""}`)}</strong>
        <span>${escapeHtml(zhConsoleText(`${step.status || "--"} / ${step.evidence || ""}`))}</span>
        <span>${escapeHtml(zhConsoleText(step.plain_action || ""))}</span>
      </div>
    `).join("")
    : statusRows([["暂无今日流程", "先点击生成今日前三交易建议。", "warn"]]);
  byId("daily-pretrade-beginner-cards").innerHTML = cards.length
    ? cards.map((card) => `
      <div class="list-row warn">
        <strong>${escapeHtml(card.title || card.card_id || "")}</strong>
        <span>${escapeHtml(card.text || "")}</span>
      </div>
    `).join("")
    : statusRows([["暂无新手提示", "等待今日建议生成后展示。", "warn"]]);
}

function renderDailyOps() {
  const daily = state.dailyOps || {};
  const decision = daily.decision || {};
  const candidate = daily.candidate || {};
  const signal = daily.signal || {};
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
    metric("信号年龄", signal.signal_age_days ?? "--", `max ${signal.max_signal_age_days ?? "--"} days`),
    metric("纸面允许", decision.paper_trading_allowed ? "true" : "false", "no broker"),
    metric("最大回撤", formatPercent(risk.max_equity_drawdown), "simulation"),
    metric("回撤阈值", formatPercent(riskPolicy.max_drawdown_limit), riskPolicy.max_drawdown_breached ? "breached" : "clear"),
  ].join("");
  byId("daily-ops-status").innerHTML = statusRows([
    ["Artifact", daily.artifact_present ? daily.source_path || "present" : "missing", daily.artifact_present ? "ok" : "warn"],
    ["Decision", status, status === "paper_ready" ? "ok" : "warn"],
    ["Paper profile", `${dailyPaperProfile.profile_id || "none"} / ${dailyPaperProfile.risk_tier || "--"}`, dailyPaperProfile.profile_id ? "ok" : "muted"],
    ["Signal freshness", `${signal.signal_date || "--"} -> ${daily.run_date || signal.run_date || "--"} / ${signal.freshness_status || "--"}`, signal.freshness_status === "fresh" ? "ok" : "warn"],
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
  renderDailyReadinessCard();
  renderDailyEvidenceChain();
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
  ["Daily trade advisory receipt", "今日交易建议回执"],
  ["Daily pretrade checkup receipt", "开盘前体检回执"],
  ["Post-close journal receipt", "收盘后复盘回执"],
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
  ["Default mode: research", "默认模式：研究"],
  ["Use research or paper simulation endpoints; live trading remains blocked.", "只允许研究和本地模拟盘入口；实盘交易保持阻断。"],
  ["Simulation output is local evidence; promotion gates still decide operator use.", "模拟盘输出只是本地证据；是否可给操作员使用仍由推广闸门决定。"],
  ["No extra GUI worker jobs detected; launch research, paper, or verification workflows from the console.", "没有额外 GUI 工作进程；需要时从控制台启动研究、模拟盘或验证任务。"],
  ["Local process observation only; no broker, account, order, or live-trading side effects.", "仅本地查看进程；不会触碰券商、账户、订单或实盘交易。"],
  ["Current control-center defaults target CN_ETF local processed bars.", "当前中控默认使用 CN_ETF 本地清洗行情。"],
  ["Paper workflows are local simulations only; promotion gates must pass before operator use.", "模拟盘流程只在本地运行；必须通过推广闸门后才可给操作员使用。"],
  ["The local GUI server and /api/control/status must respond before operator use.", "给操作员使用前，本地 GUI 服务和 /api/control/status 必须正常响应。"],
  ["Run verification gate", "运行验证闸门"],
  ["Run startup workflows", "运行启动工作流"],
  ["research, signals, paper, and promotion refreshed", "研究、信号、模拟盘和候选推广已刷新"],
  ["Run a local verification gate and inspect the receipt.", "运行一个本地验证闸门，并检查回执。"],
  ["No allowlisted gates", "暂无允许的验证闸门"],
  ["Verification runner is disabled until gate metadata is restored.", "验证闸门元数据恢复前，验证执行器会保持禁用。"],
  ["Allowed gates", "允许的验证闸门"],
  ["Local startup", "本地启动"],
  ["Local startup smoke", "本地启动冒烟"],
  ["Desktop browser smoke", "桌面浏览器冒烟"],
  ["Mobile browser smoke", "移动端浏览器冒烟"],
  ["Control status API", "中控状态 API"],
  ["GUI browser smoke evidence", "GUI 浏览器冒烟证据"],
  ["Local /api/control/status returns stage=gui_control_center.", "本地 /api/control/status 已返回 gui_control_center 阶段。"],
  ["Control API must return stage=gui_control_center.", "中控 API 必须返回 gui_control_center 阶段。"],
  ["Run queue and verification gates render with no horizontal overflow or console errors.", "运行队列和验证闸门渲染正常，没有横向溢出或控制台错误。"],
  ["Critical control center blocks remain visible and responsive on mobile.", "移动端仍能看清并操作关键中控模块。"],
  ["Evidence packet present at", "证据包位于"],
  ["GUI browser smoke evidence packet is missing.", "GUI 浏览器冒烟证据包缺失。"],
  ["Computes metrics only; no broker, account, or order side effects.", "仅计算指标；无券商、账户或下单副作用。"],
  ["research calculation only; no broker, account, or order side effects", "仅研究计算；无券商、账户或下单副作用"],
  ["advisory targets only; executable=false and no order routing", "仅建议信号；不可执行且不路由订单"],
  ["local simulated fills only; no broker, account, or order side effects", "仅本地模拟成交；无券商、账户或下单副作用"],
  ["daily advisory only; manual review required; no broker, account, or order side effects", "仅今日建议；必须人工复核；无券商、账户或下单副作用"],
  ["pretrade_receipt_only; local pretrade checkup only; manual review required; no broker, account, or order side effects", "仅开盘前体检回执；必须人工复核；无券商、账户或下单副作用"],
  ["local post-close journal only; no broker, account, or order side effects", "仅本地盘后复盘；无券商、账户或下单副作用"],
  ["blocked by research-to-paper boundary", "按研究到模拟盘边界阻断"],
  ["Blocked by research-to-paper boundary", "按研究到模拟盘边界阻断"],
  ["after preflight review.", "完成运行前检查后执行。"],
  ["Run allowlisted verification gates locally and inspect the returned receipt before publishing.", "发布前在本地运行白名单验证闸门，并检查返回回执。"],
  ["No local verification receipt", "暂无本地验证回执"],
  ["Run gui_compile first before publishing GUI changes.", "发布 GUI 改动前先运行 gui_compile。"],
  ["GUI tests, project audit, compile check, sync audit, and browser smoke checks.", "GUI 测试、项目审计、编译检查、安全同步审计和浏览器冒烟都要通过。"],
  ["GUI tests, compile checks, project audit, browser smoke, and sync audit must pass before publishing.", "发布前必须通过 GUI 测试、编译检查、项目审计、浏览器冒烟和安全同步审计。"],
  ["Research metrics populate total return, annualized return, Sharpe, drawdown, win rate, trade count, and benchmark comparison.", "研究指标会展示总收益、年化收益、夏普、回撤、胜率、交易次数和基准对比。"],
  ["Structured receipts connect displayed metrics to the workflow that produced them.", "结构化回执会把页面指标和生成它的工作流连起来。"],
  ["Paper fills are local simulations only and do not touch broker, account, or order systems.", "模拟盘成交只在本地模拟，不会触碰券商、账户或订单系统。"],
  ["Local processed bars or demo fixtures; no broker/account/order access.", "使用本地清洗行情或演示数据；不访问券商、账户或订单。"],
  ["Run promotion/readiness gates before operator use; generated data stays out of Git.", "给操作员使用前先跑推广和就绪闸门；生成数据不进 Git。"],
  ["Browser check", "浏览器检查"],
  ["Run research backtest with the displayed current command.", "运行当前显示命令完成研究回测。"],
  ["Run local paper simulation with the displayed current command.", "运行当前显示命令完成本地模拟盘。"],
  ["preflight row(s) still need review before treating this as a paper-observation candidate.", "条预检仍需复核，暂不能当作模拟盘观察候选。"],
  ["Keep live trading disabled; only research and local paper simulation are allowed.", "保持实盘交易禁用；只允许研究和本地模拟盘。"],
  ["The GUI must see passing backtest-gate metrics and matching current receipts before any paper-observation handoff.", "进入模拟盘观察交接前，GUI 必须看到通过的回测闸门指标和匹配当前参数的回执。"],
  ["The control API must expose metric thresholds before paper-observation decisions are shown.", "显示模拟盘观察判断前，中控 API 必须给出指标门槛。"],
  ["no current server receipt", "暂无当前服务端回执"],
  ["no server receipt", "暂无服务端回执"],
  ["current server receipt", "当前服务端回执"],
  ["paper-observation", "模拟盘观察"],
  ["status=", "状态="],
  ["browser=", "浏览器="],
  ["gui=", "界面="],
  ["live=", "实盘="],
  ["live=false", "实盘=否"],
  ["orders=false", "订单=否"],
  ["evidence is current", "证据为当前"],
  ["matches_current_request=False", "匹配当前请求=否"],
  ["matches_current_request=True", "匹配当前请求=是"],
  ["freshness=", "新旧状态="],
  ["awaiting=", "等待="],
  ["sharpe, total_return, annualized_return, max_drawdown, win_rate, trade_count, benchmark_relative_return, paper_ending_equity, stored_receipts", "夏普、总收益、年化收益、最大回撤、胜率、交易次数、相对基准收益、模拟盘期末权益、存储回执"],
  ["Data scope", "数据范围"],
  ["Factor inputs", "因子输入"],
  ["Execution model", "执行模型"],
  ["Cost and risk model", "成本和风控模型"],
  ["Output metrics", "输出指标"],
  ["processed-bars reads", "读取本地清洗行情"],
  ["with windows", "按窗口"],
  ["ranks top", "选择排名前"],
  ["assets against", "个标的，对比基准"],
  ["Rebalance every", "每"],
  ["bars with lag", "根K线调仓，执行滞后"],
  ["and forward horizon", "预测周期"],
  ["Cost ", "成本 "],
  ["bps, cash annual return", "bps，现金年化收益"],
  ["regime filter=", "市场状态过滤="],
  [" lookback=", " 回看周期="],
  ["max drawdown limit=", "最大回撤限制="],
  ["Reports total return, annualized return, Sharpe, max drawdown, win rate, trades, benchmark relative return, and paper equity.", "报告总收益、年化收益、夏普、最大回撤、胜率、交易次数、相对基准收益和模拟盘权益。"],
  ["Advisory signal snapshot", "建议信号快照"],
  ["advisory signal snapshot", "建议信号快照"],
  ["research_backtest", "研究回测"],
  ["verification_runner", "验证执行器"],
  ["observing", "监控中"],
  ["research_api", "研究接口"],
  ["paper_sim", "模拟盘"],
  ["paper_simulation", "模拟盘"],
  ["advisory_signal", "建议信号"],
  ["local_verification", "本地验证"],
  ["server_receipt", "服务端回执"],
  ["server_receipts", "服务端回执"],
  ["refresh_after_run", "运行后刷新"],
  ["requires_gates", "需要闸门"],
  ["allowlist", "白名单"],
  ["live_trading_allowed", "允许实盘交易"],
  ["order_placement_allowed", "允许下单"],
  ["ledger_evidence", "证据账本"],
  ["live_boundary", "实盘边界"],
  ["live_trading", "实盘交易"],
  ["broker_connection", "券商连接"],
  ["paper_only", "仅模拟盘"],
  ["browser_smoke_ready", "浏览器冒烟就绪"],
  ["returncode", "返回码"],
  ["metric_passed", "指标通过"],
  ["candidate", "候选"],
  ["orders", "订单"],
  ["jobs", "任务"],
  ["related", "相关"],
  ["pid", "进程号"],
  ["awaiting_workflow_run", "等待工作流运行"],
  ["browser_receipts", "浏览器回执"],
  ["packet_missing", "审计包缺失"],
  ["workflow_preflight", "工作流预检"],
  ["stored_receipts", "存储回执"],
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
  ["manual_only", "仅人工操作"],
  ["required", "必需"],
  ["manual_advisory_ready", "今日建议已生成"],
  ["waiting_for_signals", "等待信号生成"],
  ["fallback_baseline_not_tradeable", "兜底基线仅供观察"],
  ["blocked_current_position_input", "当前持仓输入红灯"],
  ["blocked_pretrade_red_light", "盘前红灯阻断"],
  ["paper_first_manual_review_ready", "先模拟盘再人工复核"],
  ["build_manual_ticket_pack", "补齐人工票据"],
  ["generate_today_signal", "生成今日信号"],
  ["waiting_for_candidate_pool", "等待候选池"],
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
  if (all.length === 0) return emptyChart("暂无数据");
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
  if (points.length === 0) return emptyChart("暂无数据");
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
        <strong>暂无审计包配置</strong>
        <span>运行 GUI 中控台审计后，会生成证据主线。</span>
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
      <strong>暂无审计反馈动作</strong>
      <span>下一轮 GUI 优化前，先复核独立审计包。</span>
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
      <span>${escapeHtml(`节奏=${summary.cadence_rounds ?? 5}轮 / 已汇总=${summary.completed_rounds ?? 0} / 剩余=${summary.rounds_until_next_audit ?? "--"}`)}</span>
      <span>${escapeHtml(summary.next_review_trigger || "每五轮 GUI 工作生成一次复盘报告。")}</span>
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
      <strong>暂无近期 GUI 轮次</strong>
      <span>运行 GUI 工作流或验证闸门后，会填充五轮复盘报告。</span>
    </div>
  `) + (planRows || `
    <div class="list-row warn">
      <strong>暂无下一步流程计划</strong>
      <span>运行独立 GUI 审计后，会生成下一步流程计划。</span>
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
      <span>${escapeHtml(`动作=${summary.active_actions ?? "--"} / 节奏=${summary.cadence_rounds ?? 5}轮`)}</span>
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
      <strong>暂无审计迭代动作</strong>
      <span>下一轮优化前，先运行独立 GUI 审计。</span>
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
      <strong>暂无审计调度数据</strong>
      <span>中控 API 需要展示 gui-5h 心跳状态和最近审计时间。</span>
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
      <span>${escapeHtml(`${summary.evidence_storage_key || "--"} / ${friendlyCommandText(summary.next_endpoint || "")}`)}</span>
    </div>
  `;
  const body = rows.slice(0, 9).map((item) => {
    const status = item.status || "";
    const statusClass = status === "blocked" ? "danger" : ["active", "ready", "publish_ready"].includes(status) ? "ok" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.trace_id || "")}</strong>
        <span>${escapeHtml(`${status || "--"} / ${item.source_workflow || ""}`)}</span>
        <span>${escapeHtml(friendlyCommandText(item.command || item.endpoint || ""))}</span>
        <span>${escapeHtml(item.evidence || item.next_action || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>暂无工作流追踪</strong>
      <span>中控 API 需要展示当前工作流、队列步骤、证据存储、验证闸门和实盘边界。</span>
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
        <button class="secondary-button verification-run-button" type="button" data-verification-gate="${escapeHtml(item.gate_id || "")}">${escapeHtml(item.button_label || "Run")}</button>
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
      <strong>暂无本地验证回执</strong>
      <span>发布 GUI 改动前先运行 gui_compile。</span>
    </div>
  `;
  return header + (body || `
    <div class="list-row danger">
      <strong>暂无允许的验证闸门</strong>
      <span>验证闸门元数据恢复前，验证执行器会保持禁用。</span>
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
      <span>${escapeHtml(`落后=${summary.behind ?? "--"} / 超前=${summary.ahead ?? "--"} / 变更=${summary.changed_paths ?? "--"}`)}</span>
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
      <strong>暂无工作区同步状态</strong>
      <span>发布前需要看到 Git 分支、工作区、上游和同步策略。</span>
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
        <span>${escapeHtml(friendlyCommandText(item.command || ""))}</span>
        <span>${button}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>暂无下一步动作</strong>
      <span>运行中控状态接口后，会生成下一步安全操作建议。</span>
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
  const body = rows.map((item) => {
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
  return body + renderRuntimeGuardHelp("startup_workflows");
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

function workflowPreflightModeText(item = {}) {
  return zhConsoleText(item.mode || "--");
}

function workflowPreflightCheckText(check = {}) {
  const labels = {
    parameter_authority: "参数一致",
    execution_boundary: "执行边界",
    readiness: "运行就绪",
    server_receipt: "服务端回执",
    live_boundary: "实盘边界",
    broker_connection: "券商连接",
    order_placement: "下单权限",
    whitelist: "白名单",
  };
  const id = check.check_id || check.label || "check";
  return `${labels[id] || zhConsoleText(id)}=${zhConsoleText(check.status || "--")}`;
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
      <strong>${escapeHtml(`运行前检查 / ${zhConsoleText(summary.status || "--")}`)}</strong>
      <span>${escapeHtml(`可运行=${summary.runnable_count ?? 0} / 阻断=${summary.blocked_count ?? 0}`)}</span>
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
      ? item.checks.map((check) => workflowPreflightCheckText(check)).join(" / ")
      : "";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(`${item.label || item.workflow_id || ""} / ${status || "--"}`))}</strong>
        <span>${escapeHtml(`模式=${workflowPreflightModeText(item)} / 可运行=${item.runnable ? "是" : "否"}`)}</span>
        <span>${escapeHtml(checks)}</span>
        <span>${escapeHtml(workflowPreflightEndpointSummary(item))}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>暂无运行前检查行</strong>
      <span>使用工作流按钮前，中控状态应展示运行就绪情况。</span>
    </div>
  `);
}

function workflowPreflightEndpointSummary(item = {}) {
  const endpoint = item.endpoint || "";
  if (endpoint.startsWith("/api/control/verification")) return friendlyCommandText(endpoint);
  if (endpoint.startsWith("/api/")) return friendlyCommandText(endpoint.split("?")[0]);
  const command = item.command || "";
  if (command.startsWith("GET /api/control/verification")) return friendlyCommandText(command.replace("GET ", ""));
  if (command.startsWith("GET /api/")) return friendlyCommandText(command.replace("GET ", "").split("?")[0]);
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
      <strong>暂无进程监控数据</strong>
      <span>中控 API 需要展示当前 GUI、审计、冒烟和研究进程。</span>
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

function operationLedgerText(value = "") {
  return String(zhConsoleText(value || ""))
    .replaceAll("market=", "市场=")
    .replaceAll("factor_name=", "因子=")
    .replaceAll("factor=", "因子=")
    .replaceAll("top_n=", "TopN=")
    .replaceAll("cost_bps=", "成本bps=")
    .replaceAll("start_date=", "开始=")
    .replaceAll("end_date=", "结束=")
    .replaceAll("cash=", "初始资金=")
    .replaceAll("gate_id=", "闸门=")
    .replaceAll("returncode=", "返回码=")
    .replaceAll("live=enabled", "实盘=启用")
    .replaceAll("live=disabled", "实盘=禁用")
    .replaceAll("orders=enabled", "下单=启用")
    .replaceAll("orders=disabled", "下单=禁用");
}

function renderOperationLedger(ledger = {}) {
  const summary = ledger.summary || {};
  const rows = ledger.rows || [];
  const hasRows = rows.length > 0;
  const header = `
    <div class="list-row ${escapeHtml(hasRows ? "ok" : "warn")}">
      <strong>${escapeHtml(hasRows ? "最近服务端操作" : "暂无服务端操作记录")}</strong>
      <span>${escapeHtml(`记录=${summary.entry_count ?? 0} / 最新=${summary.latest_workflow_id || "--"} / ${summary.latest_status || "--"}`)}</span>
      <span>${escapeHtml(`账本=${summary.path || "data/reports/gui_operation_ledger/gui_operation_ledger.json"}`)}</span>
      <span>${escapeHtml(`实盘=${summary.live_trading_allowed ? "启用" : "禁用"} / 下单=${summary.order_placement_allowed ? "启用" : "禁用"}`)}</span>
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
        <span>${escapeHtml(operationLedgerText(item.request_summary || item.command || ""))}</span>
        <span>${escapeHtml(operationLedgerText(item.metric_summary || item.stage || ""))}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>等待工作流回执</strong>
      <span>从这个 GUI 运行研究、信号、模拟盘或验证任务后，会生成服务端回执。</span>
    </div>
  `);
}

function renderDailyClosureLedger(ledger = {}) {
  const summary = ledger.summary || {};
  const rows = Array.isArray(ledger.rows) ? ledger.rows : [];
  const status = summary.status || "needs_more_closure_receipts";
  const tone = status === "server_closure_ready" ? "ok" : status === "blocked_by_manual_execution" ? "danger" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("服务端每日闭环")}</strong>
      <span>${escapeHtml(`闭环=${formatNumber(summary.closed_loop_days || 0)}/${formatNumber(summary.lookback_days || 5)} / 观察日=${formatNumber(summary.server_observed_days || 0)}`)}</span>
      <span>${escapeHtml(summary.next_action || "先运行今日建议、模拟盘和盘后复盘。")}</span>
      <span>${escapeHtml("不连接券商 / 不读账户 / 不自动下单")}</span>
    </div>
  `;
  const body = rows.slice(0, 5).map((row) => {
    const rowTone = row.completed_loop ? "ok" : row.manual_execution_blocked || row.manual_execution_missing_review ? "danger" : "warn";
    const stepText = [
      `前三=${row.top3_signal_ready ? "完成" : "缺失"}`,
      `模拟=${row.same_parameter_paper_ready ? "完成" : "缺失"}`,
      `复盘=${row.post_close_journal_ready ? "完成" : "缺失"}`,
      `执行审计=${row.manual_execution_clean ? "干净" : row.manual_execution_blocked ? "异常" : row.manual_execution_missing_review ? "缺回执" : "缺失"}`,
    ].join(" / ");
    const missing = Array.isArray(row.missing_steps) ? row.missing_steps.join(" / ") : "";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(row.date || "--")}</strong>
        <span>${escapeHtml(stepText)}</span>
        <span>${escapeHtml(missing ? `缺=${missing}` : "服务端闭环完整")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>${escapeHtml("暂无服务端闭环样本")}</strong>
      <span>${escapeHtml("从 GUI 运行今日前三建议、模拟盘，并提交盘后复盘回执后，这里会沉淀跨端可审计样本。")}</span>
    </div>
  `);
}

function renderServerCapitalObservationGate(gate = {}) {
  const summary = gate.summary || {};
  const rows = Array.isArray(gate.rows) ? gate.rows : [];
  const status = summary.status || "blocked_need_clean_server_closure_days";
  const tone = status === "manual_small_capital_observation_candidate" ? "warn" : status.includes("blocked") ? "danger" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(tone)}">
      <strong>${escapeHtml("小资金人工观察候选")}</strong>
      <span>${escapeHtml(summary.manual_small_capital_observation_candidate ? "可准备材料，不自动下单" : "未放行，继续模拟和闭环")}</span>
      <span>${escapeHtml(`服务端闭环=${formatNumber(summary.server_closed_loop_days || 0)}/5 / 同参数模拟盘=${formatNumber(summary.matched_paper_days || 0)}/5 / 旧未校验=${formatNumber(summary.legacy_unverified_paper_days || 0)}`)}</span>
      <span>${escapeHtml(`执行异常=${formatNumber(summary.blocked_execution_days || 0)}`)}</span>
      <span>${escapeHtml(summary.next_action || "继续收集干净闭环样本。")}</span>
    </div>
  `;
  const body = rows.map((row) => {
    const rowStatus = row.status || "";
    const rowTone = rowStatus === "pass" ? "ok" : rowStatus === "blocked_expected" ? "danger" : rowStatus.includes("blocked") ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(rowTone)}">
        <strong>${escapeHtml(row.label || row.gate_id || "")}</strong>
        <span>${escapeHtml(`${zhConsoleText(rowStatus)} / ${row.evidence || ""}`)}</span>
      </div>
    `;
  }).join("");
  return header + (body || statusRows([[
    "小资金观察闸门",
    "等待服务端每日闭环台账生成后评估；系统仍不连接券商、不读账户、不下单。",
    "warn",
  ]]));
}

function renderTradeModeControl(control = {}) {
  const summary = control.summary || {};
  const rows = control.rows || [];
  const header = `
    <div class="list-row ${escapeHtml(summary.live_trading_allowed ? "danger" : "ok")}">
      <strong>${escapeHtml(`Default mode: ${summary.default_mode || "research"}`)}</strong>
      <span>${escapeHtml(`paper_sim=${summary.paper_simulation_available ? "available" : "blocked"} / live=${summary.live_trading_allowed ? "enabled" : "blocked"}`)}</span>
      <span>${escapeHtml(summary.next_action || "只允许研究和本地模拟盘模式。")}</span>
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
        <span>${escapeHtml(friendlyCommandText(item.entrypoint || ""))}</span>
        <span>${escapeHtml(item.guardrail || item.scope || "")}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>暂无模式行</strong>
      <span>中控 API 需要展示研究、模拟盘和实盘模式。</span>
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
      <strong>${escapeHtml(ready ? "本地启动就绪" : "需要启动证据")}</strong>
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
      <strong>暂无启动健康行</strong>
      <span>给操作员使用前，先运行本地 GUI 启动和浏览器冒烟。</span>
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
      <span>${escapeHtml(friendlyCommandText(summary.research_endpoint || ""))}</span>
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
      <strong>暂无回测溯源</strong>
      <span>中控 API 需要展示每次回测的数据源、参数、端点、输出和安全溯源。</span>
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
      <strong>暂无结果证据</strong>
      <span>运行研究、信号或模拟盘后，会把结果指标连接到工作流回执。</span>
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
  const serverReceiptText = `服务端回执=${serverReceipts}/${requiredServerReceipts || "--"}`;
  const browserReceiptText = `浏览器回执=${browserReceipts}/${requiredBrowserReceipts || "--"}`;
  const metricSummaryText = `指标通过=${metricPassed}/${metricGateRows.length || "--"} / 等待=${metricAwaiting} / 失败=${metricFailures}`;
  const liveSummaryText = `实盘边界=${liveBlockedExpected ? "预期阻断" : "需复核"}`;
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Paper readiness / ${dynamicStatus}`))}</strong>
      <span>${escapeHtml(`${serverReceiptText} / ${browserReceiptText} / 候选=${candidateReady ? "是" : "否"}`)}</span>
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
      <strong>暂无模拟盘交接</strong>
      <span>先运行当前研究和模拟盘工作流，再评估回执、指标、预检、闸门和实盘边界。</span>
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
      <strong>${escapeHtml(`服务端回执 / ${summary.status || "--"}`)}</strong>
      <span>${escapeHtml(`当前=${summary.current_receipts ?? 0} / 缺失或过期=${summary.missing_or_stale ?? 0}`)}</span>
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
      <strong>暂无服务端回执账本</strong>
      <span>从这个 GUI 运行研究、信号、模拟盘或验证任务后，会生成服务端回执。</span>
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
        : "只检查指标门槛";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(zhConsoleText(`Backtest gate / ${headerStatus}`))}</strong>
      <span>${escapeHtml(`passed=${passed} / awaiting=${awaiting} / failed=${failures}`)}</span>
      <span>${escapeHtml(`风险=${summary.risk_profile || "--"} / live=${summary.live_trading_allowed ? "enabled" : "disabled"}`)}</span>
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
      <strong>暂无回测闸门</strong>
      <span>显示模拟盘观察判断前，中控 API 必须给出指标门槛。</span>
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

function releaseReadinessText(value = "") {
  return operationLedgerText(value)
    .replaceAll("Push ready", "可以推送")
    .replaceAll("Manual verification required", "需要人工验证")
    .replaceAll("No audit repair actions queued", "暂无审计修复动作排队")
    .replaceAll("No audit repair actions 排队", "暂无审计修复动作排队")
    .replaceAll("Verification pack", "验证包")
    .replaceAll("required", "必需")
    .replaceAll("before push", "推送前")
    .replaceAll("ready", "就绪")
    .replaceAll("missing", "缺失");
}

function renderReleaseReadiness(readiness = {}) {
  const summary = readiness.summary || {};
  const rows = readiness.rows || [];
  const headerClass = summary.push_ready ? "ok" : summary.missing_required ? "danger" : "warn";
  const header = `
    <div class="list-row ${escapeHtml(headerClass)}">
      <strong>${escapeHtml(summary.push_ready ? "可以推送" : "需要人工验证")}</strong>
      <span>${escapeHtml(`证据=${summary.evidence_ready ? "就绪" : "缺失"} / 人工=${summary.manual_required ?? "--"} / 缺失=${summary.missing_required ?? "--"}`)}</span>
      <span>${escapeHtml(releaseReadinessText(summary.next_action || ""))}</span>
    </div>
  `;
  const body = rows.slice(0, 8).map((item) => {
    const status = item.status || "";
    const statusClass = status === "passed_evidence" || status === "blocked_expected" ? "ok" : status === "missing_required" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(item.label || item.check_id || "")}</strong>
        <span>${escapeHtml(status || "--")}</span>
        <span>${escapeHtml(releaseReadinessText(item.evidence || item.command || ""))}</span>
      </div>
    `;
  }).join("");
  return header + (body || `
    <div class="list-row warn">
      <strong>暂无发布就绪检查行</strong>
      <span>刷新中控台快照后会填充本地发布闸门。</span>
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
  renderBeginnerTaskWizard();
  renderBeginnerTroubleshooter();
  renderBeginnerProgress();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
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

function syncExecutionReceiptToServer(receipt) {
  if (!receipt || !receipt.workflow_id) return;
  const payload = {
    workflow_id: receipt.workflow_id,
    label: receipt.label || receipt.workflow_id,
    status: receipt.status || "completed",
    request: receipt.request || {},
    metrics: receipt.metrics || {},
    decision: receipt.decision || "",
    stage: receipt.stage || "",
    safety: receipt.safety || "",
  };
  fetch("/api/control/execution-receipt", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(payload),
  })
    .then((response) => (response.ok ? response.json() : null))
    .then((packet) => {
      if (!packet || packet.status !== "recorded") return;
      return loadControlCenter().then(() => renderControlCenter());
    })
    .catch((_error) => {
      // Browser receipts remain usable locally if the server-side ledger is unavailable.
    });
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
  syncExecutionReceiptToServer(nextReceipt);
  renderExecutionReceipts(spec);
  renderDailyTradeDecisionSheet(state.dailyTradeAdvisory?.daily_trade_decision_sheet || {});
  renderDailySignalExecutionBridge(state.dailyTradeAdvisory?.daily_signal_execution_bridge || {});
  renderDailyDeploymentReadiness(state.dailyTradeAdvisory?.daily_deployment_readiness || {});
  renderLiveProfitabilityReadiness(state.dailyTradeAdvisory?.live_profitability_readiness || {});
  renderDailyClosureStreak(state.dailyTradeAdvisory?.live_profitability_readiness || {});
  renderDailyFactorHealthMonitor(state.dailyTradeAdvisory?.daily_factor_health_monitor || {});
  renderDailyRealWorldHandoffGate(state.dailyTradeAdvisory?.real_world_manual_handoff_gate || {});
  renderOrdinaryHome();
  renderDailyCommandRail();
  renderDailyReadinessCard();
  renderDailyEvidenceChain();
  renderBeginnerTradeSystem();
  renderBeginnerDailyRehearsal();
  renderBeginnerPostCloseJournal();
  renderBeginnerLiveHandoff();
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
        <strong>暂无本机运行历史</strong>
        <span>${escapeHtml(spec.empty_state || "运行一次本地工作流后会在本浏览器记录历史。")}</span>
      </div>
    `;
    return;
  }
  target.innerHTML = rows.map((item) => {
    const status = item.status || "";
    const statusClass = status === "completed" ? "ok" : status === "failed" ? "danger" : "warn";
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(item.label || item.workflow_id || ""))}</strong>
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
        <strong>暂无执行回执</strong>
        <span>${escapeHtml(spec.empty_state || "运行研究回测、信号快照、今日建议、开盘前体检或模拟盘后会记录结构化回执。")}</span>
      </div>
    `;
    return;
  }
  target.innerHTML = rows.map((item) => {
    const metrics = item.metrics || {};
    const request = item.request || {};
    const statusClass = item.status === "completed" ? "ok" : item.status === "failed" ? "danger" : "warn";
    const metricText = [
      metrics.traffic_light ? `灯号=${metrics.traffic_light}` : "",
      metrics.signal_count != null ? `信号=${formatNumber(metrics.signal_count)}` : "",
      metrics.manual_ticket_count != null ? `票据=${formatNumber(metrics.manual_ticket_count)}` : "",
      metrics.total_return != null ? `收益=${formatPercent(metrics.total_return)}` : "",
      metrics.sharpe != null ? `夏普=${formatDecimal(metrics.sharpe)}` : "",
      metrics.max_drawdown != null ? `回撤=${formatPercent(metrics.max_drawdown)}` : "",
      metrics.ending_equity != null ? `权益=${formatNumber(metrics.ending_equity)}` : "",
      metrics.target_count != null ? `目标数=${formatNumber(metrics.target_count)}` : "",
      metrics.journal_item_count != null ? `复盘项=${formatNumber(metrics.journal_item_count)}` : "",
      metrics.paper_receipt_present != null ? `模拟盘回执=${metrics.paper_receipt_present ? "有" : "无"}` : "",
      metrics.manual_outcome ? `人工选择=${zhConsoleText(metrics.manual_outcome)}` : "",
      metrics.manual_note_count != null ? `人工备注=${formatNumber(metrics.manual_note_count)}` : "",
      metrics.manual_execution_decision ? `成交审计=${zhConsoleText(metrics.manual_execution_decision)}` : "",
      metrics.manual_execution_review_count != null ? `成交回执=${formatNumber(metrics.manual_execution_review_count)}` : "",
      metrics.executed_ticket_count != null ? `实际执行=${formatNumber(metrics.executed_ticket_count)}` : "",
      metrics.manual_execution_guardrail_breach_count != null ? `价格护栏=${formatNumber(metrics.manual_execution_guardrail_breach_count)}` : "",
      metrics.manual_execution_slippage_breach_count != null ? `滑点超限=${formatNumber(metrics.manual_execution_slippage_breach_count)}` : "",
    ].filter(Boolean).join(" / ");
    const requestText = [
      request.market,
      request.factor_name || request.factor,
      request.top_n != null ? `TopN=${request.top_n}` : "",
      request.cost_bps != null ? `成本=${request.cost_bps}bps` : "",
    ].filter(Boolean).join(" / ");
    return `
      <div class="list-row ${escapeHtml(statusClass)}">
        <strong>${escapeHtml(zhConsoleText(item.label || item.workflow_id || ""))}</strong>
        <span>${escapeHtml(`${item.time || "--"} / ${requestText || "--"}`)}</span>
        <span>${escapeHtml(metricText || item.decision || item.safety || "")}</span>
        <span>${escapeHtml(zhConsoleText(item.safety || ""))}</span>
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
      source: request.source,
      market: request.market,
      factor_name: request.factor_name || request.factor,
      factor: request.factor || request.factor_name,
      factor_windows: request.factor_windows,
      top_n: request.top_n,
      rebalance_interval: request.rebalance_interval,
      start_date: request.start_date,
      end_date: request.end_date,
      as_of_date: request.as_of_date || request.run_date || request.end_date,
      run_date: request.run_date || request.as_of_date || request.end_date,
      initial_cash: request.initial_cash,
      commission_bps: request.commission_bps,
      slippage_bps: request.slippage_bps,
      max_asset_weight: request.max_asset_weight,
      max_market_weight: request.max_market_weight,
      max_gross_exposure: request.max_gross_exposure,
      min_cash_weight: request.min_cash_weight,
      max_drawdown_guard: request.max_drawdown_guard,
      guard_cooldown_periods: request.guard_cooldown_periods,
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

function dailyPaperRequestSignature(result = {}) {
  const bridge = result.daily_signal_execution_bridge || {};
  const handoff = bridge.paper_simulation_handoff || result.paper_simulation_handoff || {};
  const request = handoff.recommended_request || {};
  return {
    source: request.source,
    market: request.market,
    factor_name: request.factor_name || request.factor,
    factor: request.factor || request.factor_name,
    factor_windows: request.factor_windows,
    top_n: request.top_n,
    rebalance_interval: request.rebalance_interval,
    as_of_date: result.run_date || request.as_of_date || request.run_date,
    run_date: result.run_date || request.run_date || request.as_of_date,
    initial_cash: request.initial_cash,
    commission_bps: request.commission_bps,
    slippage_bps: request.slippage_bps,
    max_asset_weight: request.max_asset_weight,
    max_market_weight: request.max_market_weight,
    max_gross_exposure: request.max_gross_exposure,
    min_cash_weight: request.min_cash_weight,
    max_drawdown_guard: request.max_drawdown_guard,
    guard_cooldown_periods: request.guard_cooldown_periods,
  };
}

function dailyTradeAdvisoryReceipt(result = {}) {
  const summary = result.summary || {};
  const readiness = result.pretrade_readiness || {};
  const handoff = result.manual_broker_handoff || {};
  const firstAction = Array.isArray(result.operator_next_actions) ? result.operator_next_actions[0] || {} : {};
  return {
    workflow_id: "daily_trade_advisory",
    label: "Daily trade advisory receipt",
    request: {
      market: result.market,
      source: result.source,
      as_of_date: result.run_date,
      portfolio_value: summary.target_value,
      risk_profile_id: summary.risk_profile_id,
      applied_max_gross_exposure: summary.applied_max_gross_exposure,
      paper_request_signature: dailyPaperRequestSignature(result),
    },
    metrics: {
      selected_factor_count: summary.selected_factor_count,
      signal_count: summary.signal_count,
      target_count: summary.combined_target_count ?? result.combined_target_count,
      manual_ticket_count: summary.manual_ticket_count,
      traffic_light: readiness.traffic_light,
      blocker_count: Array.isArray(readiness.blockers) ? readiness.blockers.length : 0,
      copyable_ticket_count: Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets.length : 0,
    },
    decision: firstAction.action_id || readiness.traffic_light || "daily_advisory",
    safety: "daily advisory only; manual review required; no broker, account, or order side effects",
  };
}

function dailyPretradeCheckupReceipt(result = {}) {
  const decision = result.decision || {};
  const trade = result.daily_trade_advisory || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const handoff = trade.manual_broker_handoff || {};
  return {
    workflow_id: "daily_pretrade_checkup",
    label: "Daily pretrade checkup receipt",
    request: {
      market: trade.market || "CN_ETF",
      as_of_date: trade.run_date,
      workflow: "daily_ops + daily_trade_advisory",
      paper_simulation_auto_run: false,
    },
    metrics: {
      selected_factor_count: summary.selected_factor_count,
      signal_count: summary.signal_count,
      manual_ticket_count: summary.manual_ticket_count,
      traffic_light: readiness.traffic_light,
      blocker_count: Array.isArray(readiness.blockers) ? readiness.blockers.length : 0,
      copyable_ticket_count: Array.isArray(handoff.copyable_tickets) ? handoff.copyable_tickets.length : 0,
    },
    decision: decision.title || readiness.traffic_light || "pretrade_checkup",
    receipt_scope: "pretrade_receipt_only",
    permissions: {
      broker_connection_allowed: false,
      account_read_allowed: false,
      order_placement_allowed: false,
      auto_order_allowed: false,
    },
    safety: "pretrade_receipt_only; local pretrade checkup only; manual review required; no broker, account, or order side effects",
  };
}

function postCloseJournalReceipt(result = {}) {
  const trade = result.trade || {};
  const template = result.template || {};
  const summary = trade.summary || {};
  const readiness = trade.pretrade_readiness || {};
  const items = Array.isArray(template.items) ? template.items : [];
  const paper = result.paper_receipt || null;
  const decision = result.decision || {};
  const manualReview = result.manual_review || postCloseManualReviewForm();
  const manualExecutionAudit = result.manual_execution_audit || manualReview.manual_execution_audit || localManualExecutionAudit(trade);
  const manualExecutionSummary = manualExecutionAudit.summary || {};
  return {
    workflow_id: "post_close_journal",
    label: "Post-close journal receipt",
    request: {
      market: trade.market || template.summary?.primary_market || "CN_ETF",
      as_of_date: trade.run_date || template.run_date,
      manual_handoff_only: true,
      broker_connection_allowed: false,
    },
    metrics: {
      journal_item_count: items.length,
      selected_factor_count: summary.selected_factor_count,
      signal_count: summary.signal_count,
      target_count: summary.combined_target_count ?? trade.combined_target_count,
      traffic_light: readiness.traffic_light,
      paper_receipt_present: Boolean(paper),
      blocker_count: Array.isArray(readiness.blockers) ? readiness.blockers.length : 0,
      manual_outcome: manualReview.manual_outcome,
      manual_note_count: manualReview.manual_note_count,
      manual_review_recorded: Boolean(manualReview.manual_review_recorded),
      manual_execution_decision: manualExecutionSummary.decision,
      manual_execution_review_count: manualExecutionSummary.review_count,
      executed_ticket_count: manualExecutionSummary.executed_count,
      manual_execution_guardrail_breach_count: manualExecutionSummary.guardrail_breach_count,
      manual_execution_slippage_breach_count: manualExecutionSummary.slippage_breach_count,
      manual_execution_missing_review_count: manualExecutionSummary.missing_review_count,
    },
    decision: manualReview.manual_outcome || decision.title || "post_close_review_recorded",
    manual_review: manualReview,
    manual_execution_audit: manualExecutionAudit,
    safety: "local post-close journal only; no broker, account, or order side effects",
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
    label: `运行验证闸门 ${gateId}`,
    detail: `/api/control/verification?gate_id=${gateId}`,
    safety: "仅运行白名单本地验证；无券商、账户、订单或实盘交易副作用",
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
    showToast(`验证${zhConsoleText(result.status || "完成")}：${gateId}`, result.status !== "passed");
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
      button.textContent = label || "运行";
    }
    byId("run-state-label").textContent = "就绪";
  }
}

async function runActionCenterWorkflow(workflowId, button = null) {
  if (!workflowId) return;
  if (workflowId === "research_backtest" && blockCurrentBacktestRuntime()) return;
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
    if (workflowId === "daily_trade_advisory") {
      await runDailyTradeAdvisory();
      return;
    }
    if (workflowId === "daily_pretrade_checkup") {
      await runDailyPretradeCheckup(button);
      return;
    }
    if (workflowId === "daily_ops") {
      await runDailyOps();
      return;
    }
    if (workflowId === "paper_simulation") {
      await runPaper();
      return;
    }
    if (workflowId === "post_close_journal") {
      await runPostCloseJournal(button);
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
      button.textContent = original || "运行";
    }
    syncCurrentBacktestRuntimeGuard();
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
      detail: () => `${valueOf("market-select") || "ALL"} / ${valueOf("factor-select") || "momentum_2"} / TopN=${valueOf("research-top-n") || "2"}`,
      safety: "research calculation only; no broker, account, or order side effects",
    },
    "run-signals": {
      workflow_id: "signal_snapshot",
      label: "Generate advisory signal snapshot",
      detail: () => `${valueOf("market-select") || "ALL"} / TopN=${valueOf("signal-top-n") || "2"}`,
      safety: "advisory targets only; executable=false and no order routing",
    },
    "run-paper": {
      workflow_id: "paper_simulation",
      label: "Run local paper simulation",
      detail: () => `${valueOf("paper-market-select") || "ALL"} / TopN=${valueOf("paper-top-n") || "2"} / 初始资金=${valueOf("paper-initial-cash") || "100000"}`,
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

function todayIsoDate() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function staleDailyDateDefaults() {
  return new Set([
    sourcePresets["processed-bars"]?.signalDate,
    sourcePresets["processed-bars"]?.endDate,
    sourcePresets.demo_fixture?.signalDate,
    sourcePresets.demo_fixture?.endDate,
    "2026-05-21",
    "2024-01-13",
  ].filter(Boolean));
}

function applyDailyTradeDateDefault(force = false) {
  const today = todayIsoDate();
  const staleDefaults = staleDailyDateDefaults();
  const dailyValue = valueOf("daily-trade-as-of");
  const signalValue = valueOf("signal-as-of");
  if (force || !dailyValue || staleDefaults.has(dailyValue)) {
    setValue("daily-trade-as-of", today);
  }
  if (force || !signalValue || staleDefaults.has(signalValue)) {
    setValue("signal-as-of", today);
  }
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
