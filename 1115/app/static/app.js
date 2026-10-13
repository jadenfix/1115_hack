const byId = (id) => document.getElementById(id);
const form = byId("research-form");
const statusPill = byId("status-pill");
const progressSteps = byId("progress-steps");
const snapshotCard = byId("snapshot-card");
const snapshotTitle = byId("snapshot-title");
const policyChip = byId("policy-chip");
const briefContent = byId("brief-content");
const outreachContent = byId("outreach-content");
const evidenceBody = byId("evidence-body");
const visualWrapper = byId("visual-wrapper");
const historyList = byId("history-list");
const agentWall = byId("agent-wall");
const modeBanner = byId("mode-banner");
let wallInterval = null;

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined && text !== null) item.textContent = String(text);
  return item;
}

function replaceChildren(target, children) {
  target.replaceChildren(...children.filter(Boolean));
}

function safeHttpUrl(value) {
  try {
    const parsed = new URL(String(value));
    return ["http:", "https:"].includes(parsed.protocol) ? parsed : null;
  } catch (_) {
    return null;
  }
}

function setStatus(text, state = "idle") {
  statusPill.textContent = text;
  statusPill.className = `status status-${state}`;
}

function setMode(mode) {
  if (mode === "fixture") {
    modeBanner.textContent = "FICTIONAL FIXTURE · deterministic checked-in evidence · zero provider calls";
    modeBanner.classList.remove("hidden");
  } else {
    modeBanner.textContent = "";
    modeBanner.classList.add("hidden");
  }
}

function setActiveTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.toggle("hidden", pane.id !== `tab-${tab}`));
}

document.querySelectorAll(".tab-btn").forEach((button) => button.addEventListener("click", () => setActiveTab(button.dataset.tab)));

async function runResearch(payload) {
  setStatus("Running", "running");
  setMode(payload.mode);
  progressSteps.querySelectorAll("li").forEach((item) => { item.style.opacity = ".48"; });
  try {
    const response = await fetch("/api/run_research", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    if (!response.ok) throw new Error("Failed to start run");
    const data = await response.json();
    startAgentWallPolling(data.workflow_id);
    pollStatus(data.workflow_id);
  } catch (error) {
    console.error(error);
    setStatus("Error", "error");
  }
}

async function runDemo() {
  setStatus("Running", "running");
  setMode("fixture");
  progressSteps.querySelectorAll("li").forEach((item) => { item.style.opacity = ".48"; });
  try {
    const response = await fetch("/api/demo", {method: "POST"});
    if (!response.ok) throw new Error("Failed to start fixture");
    const data = await response.json();
    startAgentWallPolling(data.workflow_id);
    pollStatus(data.workflow_id);
  } catch (error) {
    console.error(error);
    setStatus("Error", "error");
  }
}

function pollStatus(workflowId) {
  const poll = setInterval(async () => {
    try {
      const response = await fetch(`/api/run_status?workflow_id=${encodeURIComponent(workflowId)}`);
      if (!response.ok) throw new Error("Status request failed");
      const data = await response.json();
      if (data.status === "RUNNING") return;
      clearInterval(poll);
      stopAgentWallPolling();
      if (data.status !== "COMPLETED") throw new Error(data.error || "Workflow failed");
      setStatus("Completed", "success");
      progressSteps.querySelectorAll("li").forEach((item) => { item.style.opacity = "1"; });
      if (data.snapshot_id) await loadSnapshot(data.snapshot_id);
      await loadHistory();
      setActiveTab("brief");
    } catch (error) {
      console.error(error);
      clearInterval(poll);
      stopAgentWallPolling();
      setStatus("Error", "error");
    }
  }, 800);
}

function renderAgentWall(windows = []) {
  const values = new Map(windows.filter((item) => Number.isInteger(item.slot) && item.slot >= 0 && item.slot < 9).map((item) => [item.slot, item]));
  const cards = Array.from({length: 9}, (_, slot) => {
    const value = values.get(slot) || {slot, status: "idle", last_action: "Waiting for task…", page_type: "standby"};
    const card = node("article", `agent-card ${value.status === "idle" ? "" : "active"}`);
    const url = safeHttpUrl(value.url);
    const top = node("div", "agent-top");
    top.append(node("span", "agent-host", url ? url.hostname : `Agent ${slot + 1}`), node("span", "agent-type", value.page_type || "unknown"));
    const status = node("div", `agent-bottom ${value.status === "done" ? "done" : value.status === "error" ? "error" : value.status === "idle" ? "" : "working"}`);
    const state = node("span", "agent-type");
    state.append(node("i", "dot"), document.createTextNode(String(value.status || "idle").toUpperCase()));
    status.append(state);
    card.append(top, status);
    if (value.usefulness_score !== null && value.usefulness_score !== undefined) card.append(node("div", "agent-score", `${Math.round(Number(value.usefulness_score) * 100)}%`));
    card.append(node("p", "agent-action", value.last_action || ""));
    return card;
  });
  replaceChildren(agentWall, cards);
}

async function refreshAgentWall(runId) {
  try {
    const response = await fetch(`/api/run/${encodeURIComponent(runId)}/windows`);
    if (!response.ok) return;
    const data = await response.json();
    renderAgentWall(Array.isArray(data.items) ? data.items : []);
  } catch (error) { console.error("Agent wall request failed", error); }
}

function startAgentWallPolling(runId) {
  stopAgentWallPolling();
  renderAgentWall([]);
  refreshAgentWall(runId);
  wallInterval = setInterval(() => refreshAgentWall(runId), 700);
}

function stopAgentWallPolling() {
  if (wallInterval) clearInterval(wallInterval);
  wallInterval = null;
}

function metric(label, value) {
  const box = node("div", "metric");
  box.append(node("strong", "", value), node("span", "", label));
  return box;
}

function renderSnapshotSummary(snapshot) {
  const wrapper = node("div", "snapshot-meta");
  if (snapshot.mode === "fixture") wrapper.append(node("span", "fixture-stamp", "● FICTIONAL FIXTURE · NO PROVIDER CALLS"));
  wrapper.append(node("div", "snapshot-name", snapshot.company?.name || "Snapshot"));
  wrapper.append(node("p", "muted", `${snapshot.company?.domain || "No domain"} · ${snapshot.company?.persona || "No persona"}`));
  const grid = node("div", "meta-grid");
  grid.append(metric("Evidence pages", snapshot.pages?.length || 0), metric("Discovery results", snapshot.linkup_results?.length || 0), metric("Policy", snapshot.policy_version || "?"));
  wrapper.append(grid);
  if (snapshot.fixture_notice) wrapper.append(node("p", "muted", snapshot.fixture_notice));
  snapshotCard.className = "snapshot-meta";
  replaceChildren(snapshotCard, Array.from(wrapper.childNodes));
}

function renderEvidence(pages) {
  const rows = pages.map((page) => {
    const row = document.createElement("tr");
    const linkCell = document.createElement("td");
    const url = safeHttpUrl(page.url);
    if (url) {
      const link = node("a", "", url.href);
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      linkCell.append(link);
    } else linkCell.textContent = "Invalid URL";
    const typeCell = node("td", "", page.page_type || "—");
    const score = Math.max(0, Math.min(1, Number(page.usefulness_score) || 0));
    const scoreCell = document.createElement("td");
    const bar = node("div", "score-bar");
    const fill = node("div", "score-fill");
    fill.style.width = `${score * 100}%`;
    bar.append(fill);
    scoreCell.append(bar, node("span", "muted", score.toFixed(2)));
    row.append(linkCell, typeCell, scoreCell, node("td", "", Array.isArray(page.signals) ? page.signals.slice(0, 3).join(", ") : "—"));
    return row;
  });
  replaceChildren(evidenceBody, rows);
}

function renderVisual(snapshot) {
  visualWrapper.className = "visual-card empty-state";
  if (snapshot.mode === "fixture") {
    const content = node("div", "visual-content");
    content.append(node("span", "mark", "NORTHSTAR / FIXTURE 01"), node("h3", "", snapshot.company?.name || "Fictional company"), node("p", "", (snapshot.pages?.[0]?.signals || []).slice(0, 3).join(" · ")));
    replaceChildren(visualWrapper, [content]);
    return;
  }
  const asset = safeHttpUrl(snapshot.freepik_asset_url);
  if (!asset) { visualWrapper.textContent = "No visual available for this run."; return; }
  const image = document.createElement("img");
  image.src = asset.href;
  image.alt = "Generated company visual";
  image.loading = "lazy";
  replaceChildren(visualWrapper, [image]);
}

async function loadSnapshot(snapshotId) {
  try {
    const response = await fetch(`/api/snapshot/${encodeURIComponent(snapshotId)}`);
    if (!response.ok) throw new Error("Snapshot not ready");
    const snapshot = await response.json();
    snapshotTitle.textContent = snapshot.company?.name || "Snapshot";
    policyChip.textContent = `Policy ${snapshot.policy_version || "?"}`;
    setMode(snapshot.mode);
    renderSnapshotSummary(snapshot);
    briefContent.textContent = snapshot.brief_md || "No brief";
    outreachContent.textContent = snapshot.outreach_message || "No outreach message";
    renderEvidence(Array.isArray(snapshot.pages) ? snapshot.pages : []);
    renderVisual(snapshot);
  } catch (error) { console.error(error); }
}

function policyItem(label, value) {
  const item = node("div", "policy-item");
  item.append(node("span", "", label), node("div", "", value));
  return item;
}

async function loadPolicy() {
  try {
    const response = await fetch("/api/policy");
    if (!response.ok) throw new Error("Policy request failed");
    const data = await response.json();
    policyChip.textContent = `Policy ${data.version || "v?"}`;
    replaceChildren(byId("policy-panel"), [policyItem("QUERY", data.linkup_query_template || "—"), policyItem("PREFERRED PATHS", (data.preferred_paths || []).join(", ") || "—"), policyItem("MAX PAGES / DOMAIN", data.max_pages_per_domain ?? "—"), policyItem("MIN USEFULNESS", data.min_usefulness_threshold ?? "—")]);
  } catch (error) { console.error(error); }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) throw new Error("History request failed");
    const data = await response.json();
    const items = Array.isArray(data.items) ? data.items.slice(0, 5) : [];
    if (!items.length) { replaceChildren(historyList, [node("p", "muted", "No history yet.")]); return; }
    replaceChildren(historyList, items.map((row) => {
      const wrapper = node("div", "history-row");
      const head = node("div", "");
      head.append(node("strong", "", row.company?.name || "Unknown"), node("span", "fixture-stamp", row.mode === "fixture" ? "FIXTURE" : "LIVE"));
      const score = Number(row.avg_usefulness);
      wrapper.append(head, node("p", "", `Usefulness ${Number.isFinite(score) ? score.toFixed(2) : "—"} · ${row.num_pages_visited || 0} pages`));
      return wrapper;
    }));
  } catch (error) { console.error(error); }
}

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  runResearch({...Object.fromEntries(new FormData(form).entries()), mode: "live"});
});

byId("demo-btn")?.addEventListener("click", () => {
  form.name.value = "Northstar Labs";
  form.domain.value = "northstar-labs.invalid";
  form.persona.value = "SDR researching an account";
  form.notes.value = "Checked-in fictional fixture";
  runDemo();
});

byId("refresh-policy")?.addEventListener("click", () => { loadPolicy(); loadHistory(); });
setActiveTab("brief");
loadPolicy();
loadHistory();
renderAgentWall();
