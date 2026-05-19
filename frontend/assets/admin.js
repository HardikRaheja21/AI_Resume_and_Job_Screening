const API_BASE = localStorage.getItem("api_base") || window.location.origin;

function token() {
  return localStorage.getItem("jwt_token") || "";
}

function authHeaders(extra = {}) {
  const t = token();
  return t ? { Authorization: `Bearer ${t}`, ...extra } : extra;
}

function setMessage(el, text, isError = false) {
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? "#b42318" : "#14532d";
}

function formatStatusLine(label, value) {
  return `${label}: ${value ? "configured" : "not configured"}`;
}

async function loadStatus() {
  const summary = document.getElementById("integration-status-summary");
  const response = await fetch(`${API_BASE}/features/integrations/status`, {
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(summary, "Server not reachable.", true);
    return;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.detail || payload?.error?.message || "Could not load integration status.";
    setMessage(summary, String(message), true);
    if (response.status === 401) window.location.href = "login.html";
    return;
  }
  const lines = [
    formatStatusLine("Slack", payload.slack_configured),
    formatStatusLine("Teams", payload.teams_configured),
    formatStatusLine("ATS", payload.ats_configured),
  ];
  setMessage(summary, lines.join(" | "));
}

async function runConnectivityTest() {
  const provider = document.getElementById("provider")?.value;
  const message = document.getElementById("test-message")?.value.trim() || "Connectivity test from ResumeMatch";
  const msg = document.getElementById("test-result-msg");

  setMessage(msg, "Running test...");
  const response = await fetch(`${API_BASE}/features/integrations/test`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ provider, message }),
  }).catch(() => null);

  if (!response) {
    setMessage(msg, "Server not reachable.", true);
    return;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = payload?.detail || payload?.error?.message || "Connectivity test failed.";
    setMessage(msg, String(error), true);
    if (response.status === 401) window.location.href = "login.html";
    return;
  }
  setMessage(msg, `${payload.provider.toUpperCase()} connectivity test succeeded.`);
}

function startAdminOnboarding() {
  const modal = document.getElementById("admin-onboarding-modal");
  const title = document.getElementById("admin-onboarding-title");
  const body = document.getElementById("admin-onboarding-body");
  const next = document.getElementById("btn-admin-next");
  const skip = document.getElementById("btn-admin-skip");
  if (!modal || !title || !body || !next || !skip) return;
  if (localStorage.getItem("admin_onboarding_done") === "1") return;

  const steps = [
    { t: "Integration Status", b: "Refresh to confirm which provider URLs are configured from .env." },
    { t: "Connectivity Test", b: "Select slack/teams/ats and run a live webhook connectivity test." },
    { t: "Role Control", b: "Load users and promote/demote roles when needed." },
    { t: "Next Step", b: "After successful tests, use dashboard actions to send candidate updates." },
  ];
  let idx = 0;
  const render = () => {
    title.textContent = steps[idx].t;
    body.textContent = steps[idx].b;
    next.textContent = idx === steps.length - 1 ? "Done" : "Next";
  };
  const close = () => {
    modal.classList.add("hidden");
    localStorage.setItem("admin_onboarding_done", "1");
  };
  next.onclick = () => {
    if (idx >= steps.length - 1) return close();
    idx += 1;
    render();
  };
  skip.onclick = close;
  render();
  modal.classList.remove("hidden");
}

function renderUsers(users) {
  const list = document.getElementById("admin-users-list");
  if (!list) return;
  if (!users.length) {
    list.innerHTML = "<div class='small-text'>No users found.</div>";
    return;
  }
  list.innerHTML = users
    .map(
      (user) => `
      <div class="leader-row" data-user-id="${user.id}">
        <div class="leader-info">
          <div class="leader-name">${user.full_name || user.email}</div>
          <div class="leader-meta">${user.email}</div>
        </div>
        <div class="leader-actions">
          <select class="input role-select" style="max-width:140px;">
            <option value="recruiter" ${user.role === "recruiter" ? "selected" : ""}>recruiter</option>
            <option value="admin" ${user.role === "admin" ? "selected" : ""}>admin</option>
          </select>
          <button class="btn-chip btn-save-role">Save Role</button>
        </div>
      </div>
    `
    )
    .join("");
}

async function loadUsers() {
  const msg = document.getElementById("admin-users-msg");
  setMessage(msg, "Loading users...");
  const response = await fetch(`${API_BASE}/features/admin/users`, {
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(msg, "Server not reachable.", true);
    return;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = payload?.detail || payload?.error?.message || "Could not load users.";
    setMessage(msg, String(error), true);
    if (response.status === 401) window.location.href = "login.html";
    return;
  }
  renderUsers(payload || []);
  setMessage(msg, `Loaded ${payload.length || 0} user(s).`);
}

async function saveUserRole(userId, role) {
  const msg = document.getElementById("admin-users-msg");
  setMessage(msg, "Saving role...");
  const response = await fetch(`${API_BASE}/features/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ role }),
  }).catch(() => null);
  if (!response) {
    setMessage(msg, "Server not reachable.", true);
    return;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = payload?.detail || payload?.error?.message || "Role update failed.";
    setMessage(msg, String(error), true);
    if (response.status === 401) window.location.href = "login.html";
    return;
  }
  setMessage(msg, `Updated ${payload.email} role to ${payload.role}.`);
}

document.addEventListener("DOMContentLoaded", () => {
  if (!token()) {
    window.location.href = "login.html";
    return;
  }
  const refreshBtn = document.getElementById("btn-refresh-status");
  const runBtn = document.getElementById("btn-run-test");
  const loadUsersBtn = document.getElementById("btn-load-users");
  const usersList = document.getElementById("admin-users-list");
  refreshBtn?.addEventListener("click", loadStatus);
  runBtn?.addEventListener("click", runConnectivityTest);
  loadUsersBtn?.addEventListener("click", loadUsers);
  usersList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (!target.classList.contains("btn-save-role")) return;
    const row = target.closest("[data-user-id]");
    if (!row) return;
    const userId = row.getAttribute("data-user-id");
    const select = row.querySelector(".role-select");
    if (!userId || !(select instanceof HTMLSelectElement)) return;
    await saveUserRole(userId, select.value);
  });
  loadStatus();
  loadUsers();
  startAdminOnboarding();
});
