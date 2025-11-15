const form = document.getElementById("research-form");
const statusPill = document.getElementById("status-pill");
const progressSteps = document.getElementById("progress-steps");
const snapshotCard = document.getElementById("snapshot-card");
const snapshotTitle = document.getElementById("snapshot-title");
const policyChip = document.getElementById("policy-chip");
const briefContent = document.getElementById("brief-content");
const outreachContent = document.getElementById("outreach-content");
const evidenceBody = document.getElementById("evidence-body");
const visualWrapper = document.getElementById("visual-wrapper");
const refreshPolicyBtn = document.getElementById("refresh-policy");
const historyList = document.getElementById("history-list");
const demoBtn = document.getElementById("demo-btn");
const agentWall = document.getElementById("agent-wall");

let currentWorkflowId = null;
let wallInterval = null;

function setStatus(text, state = "idle") {
  statusPill.textContent = text;
  const colors = {
    idle: "bg-slate-800 border-slate-700",
    running: "bg-amber-500/20 border-amber-400/60 text-amber-200",
    success: "bg-emerald-500/20 border-emerald-400/60 text-emerald-100",
    error: "bg-rose-500/20 border-rose-400/60 text-rose-100",
  };
  statusPill.className = `px-3 py-1 rounded-full text-xs ${colors[state] || colors.idle}`;
}

function setActiveTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("hidden", pane.id !== `tab-${tab}`);
  });
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
});

async function runResearch(payload) {
  setStatus("Running", "running");
  progressSteps.querySelectorAll("li").forEach((li) => (li.style.opacity = 0.6));
  try {
    const res = await fetch("/api/run_research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to start run");
    const data = await res.json();
    currentWorkflowId = data.workflow_id;
    startAgentWallPolling(currentWorkflowId);
    pollStatus(data.workflow_id);
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
  }
}

async function pollStatus(workflowId) {
  const poll = setInterval(async () => {
    try {
      const res = await fetch(`/api/run_status?workflow_id=${encodeURIComponent(workflowId)}`);
      const data = await res.json();
      if (data.status === "RUNNING") return;
      if (data.status === "COMPLETED") {
        clearInterval(poll);
        setStatus("Completed", "success");
        progressSteps.querySelectorAll("li").forEach((li) => (li.style.opacity = 1));
        if (data.snapshot_id) {
          loadSnapshot(data.snapshot_id);
          loadHistory();
        }
        stopAgentWallPolling();
      } else {
        clearInterval(poll);
        setStatus("Error", "error");
        stopAgentWallPolling();
      }
    } catch (err) {
      console.error(err);
      clearInterval(poll);
      setStatus("Error", "error");
      stopAgentWallPolling();
    }
  }, 2000);
}

function renderAgentWall(windows = []) {
  if (!agentWall) return;
  const slots = Array.from({ length: 9 }, (_, i) => ({
    slot: i,
    status: "idle",
    last_action: "Waiting for task...",
    screenshot_url: "/static/placeholder.png",
    url: "",
    page_type: "",
    usefulness_score: null,
  }));
  windows.forEach((w) => {
    slots[w.slot] = w;
  });
  agentWall.innerHTML = slots
    .map((w) => {
      const dotClass =
        w.status === "done"
          ? "bg-emerald-400"
          : w.status === "error"
          ? "bg-rose-400"
          : "bg-amber-300 animate-pulse";
      return `
        <div class="relative rounded-xl overflow-hidden border border-slate-800 bg-slate-900/70 min-h-[160px]">
          <img src="${w.screenshot_url || "/static/placeholder.png"}" class="w-full h-40 object-cover opacity-80" alt="slot ${w.slot}" />
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
          <div class="absolute top-2 left-2 px-2 py-1 rounded-full bg-black/60 text-xs text-slate-100 flex items-center gap-1">
            <span class="font-semibold truncate max-w-[120px]">${w.url ? new URL(w.url).hostname : "Idle"}</span>
            <span class="text-slate-400">${w.page_type || ""}</span>
          </div>
          <div class="absolute bottom-2 left-2 right-2 text-[0.7rem] text-slate-100">
            <div class="flex items-center justify-between mb-1">
              <span class="inline-flex items-center gap-1">
                <span class="w-2 h-2 rounded-full ${dotClass}"></span>
                <span class="uppercase tracking-wide">${(w.status || "idle").slice(0, 12)}</span>
              </span>
              ${
                w.usefulness_score != null
                  ? `<span class="text-slate-300">Usefulness ${(w.usefulness_score * 100).toFixed(0)}%</span>`
                  : ""
              }
            </div>
            <p class="text-slate-200 line-clamp-2">${w.last_action || ""}</p>
          </div>
        </div>
      `;
    })
    .join("");
}

function startAgentWallPolling(runId) {
  stopAgentWallPolling();
  renderAgentWall([]);
  wallInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/run/${encodeURIComponent(runId)}/windows`);
      const data = await res.json();
      renderAgentWall(data.items || []);
    } catch (err) {
      console.error("Agent wall poll error", err);
    }
  }, 2000);
}

function stopAgentWallPolling() {
  if (wallInterval) {
    clearInterval(wallInterval);
    wallInterval = null;
  }
}

async function loadSnapshot(snapshotId) {
  try {
    const res = await fetch(`/api/snapshot/${snapshotId}`);
    if (!res.ok) throw new Error("Snapshot not ready");
    const snap = await res.json();
    snapshotTitle.textContent = snap.company?.name || "Snapshot";
    policyChip.textContent = `Policy ${snap.policy_version || "?"}`;
    snapshotCard.innerHTML = `
      <p class="text-sm text-slate-300">Domain: ${snap.company?.domain || "n/a"}</p>
      <p class="text-sm text-slate-300">Persona: ${snap.company?.persona || "n/a"}</p>
      <div class="flex gap-4 mt-2 text-xs text-slate-400">
        <span>Pages: ${snap.pages?.length || 0}</span>
        <span>Linkup results: ${snap.linkup_results?.length || 0}</span>
      </div>
    `;
    briefContent.textContent = snap.brief_md || "No brief";
    outreachContent.textContent = snap.outreach_message || "No outreach message";
    evidenceBody.innerHTML = "";
    (snap.pages || []).forEach((page) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="py-2 pr-2">
          <a href="${page.url}" target="_blank" class="text-cyan-300 hover:underline">${page.url}</a>
        </td>
        <td class="py-2 pr-2 text-slate-300">${page.page_type || "-"}</td>
        <td class="py-2 pr-2">
          <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-2 bg-emerald-400" style="width:${Math.min(100, (page.usefulness_score || 0) * 100)}%"></div>
          </div>
          <span class="text-xs text-slate-400">${(page.usefulness_score || 0).toFixed(2)}</span>
        </td>
        <td class="py-2 pr-2 text-slate-300">${(page.signals || []).slice(0,3).join(", ") || "-"}</td>
      `;
      evidenceBody.appendChild(tr);
    });
    if (snap.freepik_asset_url) {
      visualWrapper.innerHTML = `
        <div class="absolute inset-0">
          <img src="${snap.freepik_asset_url}" class="w-full h-full object-cover" />
        </div>
        <div class="absolute inset-0 bg-gradient-to-t from-slate-950/80 to-transparent"></div>
        <div class="relative z-10 p-4 text-white">
          <p class="text-lg font-semibold">${snap.company?.name || ""}</p>
          <p class="text-sm text-slate-200 mt-1">${(snap.pages?.[0]?.signals || []).slice(0,3).join(" • ")}</p>
        </div>
      `;
    } else {
      visualWrapper.textContent = "No visual available for this run.";
    }
  } catch (err) {
    console.error(err);
  }
}

async function loadPolicy() {
  try {
    const res = await fetch("/api/policy");
    const data = await res.json();
    policyChip.textContent = `Policy ${data.version || "v?"}`;
    document.getElementById("policy-panel").innerHTML = `
      <p><span class="text-slate-400">Query:</span> <code class="text-cyan-300">${data.linkup_query_template || ""}</code></p>
      <p><span class="text-slate-400">Preferred paths:</span> ${(data.preferred_paths || []).join(", ")}</p>
      <p><span class="text-slate-400">Max pages/domain:</span> ${data.max_pages_per_domain || "-"}</p>
      <p><span class="text-slate-400">Min usefulness:</span> ${data.min_usefulness_threshold || "-"}</p>
    `;
  } catch (err) {
    console.error(err);
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    if (!data.items || data.items.length === 0) {
      historyList.innerHTML = `<p class="text-slate-400">No history yet.</p>`;
      return;
    }
    historyList.innerHTML = "";
    data.items.slice(0, 5).forEach((row) => {
      const div = document.createElement("div");
      div.className = "p-3 rounded-lg bg-slate-900 border border-slate-800";
      div.innerHTML = `
        <div class="flex justify-between text-sm">
          <span class="text-slate-200">${row.company?.name || "Unknown"}</span>
          <span class="text-xs text-slate-400">${row.policy_version || ""}</span>
        </div>
        <div class="text-xs text-slate-400 mt-1">Usefulness: ${row.avg_usefulness ? row.avg_usefulness.toFixed(2) : "-"}</div>
      `;
      historyList.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

form?.addEventListener("submit", (e) => {
  e.preventDefault();
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  runResearch(payload);
});

demoBtn?.addEventListener("click", () => {
  form.name.value = "Acme Demo";
  form.domain.value = "acme.com";
  form.persona.value = "SDR researching an account";
  runResearch({
    name: form.name.value,
    domain: form.domain.value,
    persona: form.persona.value,
    notes: "Demo run with stubbed data",
  });
});

refreshPolicyBtn?.addEventListener("click", () => {
  loadPolicy();
  loadHistory();
});

setActiveTab("brief");
loadPolicy();
loadHistory();
renderAgentWall();
